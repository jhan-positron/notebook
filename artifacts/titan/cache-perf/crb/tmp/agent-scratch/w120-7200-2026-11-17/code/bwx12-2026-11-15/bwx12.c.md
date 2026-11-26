# `bwx12.c` explained

- Source file: `bwx12-2026-11-15/bwx12.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 3126 lines, 119709 bytes).
- sha256 of the source when this page was built: `e3d4442b83d0aabdb8bf68ec62dfeb43d489df1d7c36de82e64e5482a1089127`.
- Role in the whole-chip test: Source of bwx12, the benchmark program that parts L, C and control I run.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

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

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `bwx12-2026-11-15/bwx12.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (3126 lines, 119709 bytes, sha256 `e3d4442b83d0aabdb8bf68ec62dfeb43d489df1d7c36de82e64e5482a1089127`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### History comment of the version `bwx12`: 26 more kernels and a third pad (lines 1 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/* bwx12+ */` | Comment: a marker. A block of text that the version `bwx12` added starts here. The marker of line 33 ends the block. |
| 2 | `/*` | Opens a history comment. It tells what one version of the runner added. Here it is the version that the marker of line 1 names. |
| 3 | ` * bwx12.c - bwx11.c plus the additions of round 5 (2026-11-15). Every` | Comment: `bwx12.c` is `bwx11.c` plus the additions of round 5, made on 2026-11-15. Round 5 is a round of work on the program. It is not a round of the option `--rounds`. In the file `bwx12.c` this comment is the first of four history comments, one per version of the runner. |
| 4 | ` * addition stands between a line "bwx12+" and a line "bwx12-" (both are` | Comment: every addition of that round stands between a marker line `bwx12+` and a marker line `bwx12-`. |
| 5 | ` * comments). Without these blocks this file is bwx11.c byte for byte. So the` | Comment: both marker lines are comments. Without these blocks the text is `bwx11.c`, byte for byte. The script `test_kernels12.py` in the code folder `bwx12-2026-11-15` tests this for `bwx12.c`. |
| 6 | ` * 29 kernels of bwx11, call(), timed_sequence(), timed_sequence_hot(), the` | Comment: so some parts are the text of `bwx11.c` without a change. This line names the 29 kernels of `bwx11` and the functions `call` (line 1491), `timed_sequence` (line 1995) and `timed_sequence_hot` (line 2056). |
| 7 | ` * interval mode and the trial mode are the text of bwx11.c.` | Comment: the same holds for the two modes of the program. The interval mode (option `--seq`) times one interval for each kernel of a list, in each round of the option `--rounds`. The trial mode (option `--trial`) runs one worker thread through the trials of a plan file. |
| 8 | ` *` | Comment: an empty line of the comment. |
| 9 | ` * Additions: 26 kernels. They stand after the last kernel of bwx11 in the` | Comment: the additions are 26 kernels. In the source they stand after the last kernel of `bwx11`. |
| 10 | ` * source and in kernels[], so the kernels of bwx11 keep their machine code` | Comment: in the kernel table `kernels[]` the new kernels also stand after the last kernel of `bwx11` (lines 1475 to 1481). So the kernels of `bwx11` keep their machine code. |
| 11 | ` * and their loop offsets. No option and no output row is added.` | Comment: the kernels of `bwx11` also keep their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. Round 5 adds no option and no kind of output row. |
| 12 | ` *   read_nop48, read_nop56, read_nop72, read_nop80, read_nop88, read_nop112,` | Comment: names 6 of the 9 new `read_nop` kernels: `read_nop48`, `read_nop56`, `read_nop72`, `read_nop80`, `read_nop88` and `read_nop112` (lines 1191 to 1196). |
| 13 | ` *     read_nop160, read_nop192, read_nop256: the asmread loop with that many` | Comment: names the other 3: `read_nop160`, `read_nop192` and `read_nop256` (lines 1197 to 1199). Each of the 9 is the loop of the kernel `asmread` with as many `nop` instructions as its name says. A `nop` is an instruction that does nothing. Of the 26 new kernels the whole-chip test of 2026-11-17 runs one: `read_nop256` [Ref4]. |
| 14 | ` *     nop instructions after the 8 ldp (the macro of read_nop64).` | Comment: the `nop` instructions stand after the 8 `ldp` instructions, which load the data. The 9 kernels come from the macro `DEF_ASMREAD` (line 616). The same macro defines `read_nop64` (line 1062). |
| 15 | ` *   read_dadd2, read_dadd4, read_dadd8, read_dadd16: the asmread loop with 2,` | Comment: names the kernels `read_dadd2`, `read_dadd4`, `read_dadd8` and `read_dadd16` (lines 1273 to 1279). Each is the `asmread` loop with vector adds. |
| 16 | ` *     4, 8 or 16 vector adds after the 8 ldp. Each add takes a register that` | Comment: they have 2, 4, 8 or 16 vector adds after the 8 `ldp`. Each add takes as an input a register that the same loop pass loaded. |
| 17 | ` *     this iteration loaded, so it cannot run before the load data arrives.` | Comment: so the core cannot execute such an add before the data of the load has arrived. |
| 18 | ` *   read_iadd16: the asmread loop with 16 vector adds that take no loaded` | Comment: the kernel `read_iadd16` (line 1280) is the `asmread` loop with 16 vector adds that take no loaded register as an input. |
| 19 | ` *     register. It is the control of read_dadd16.` | Comment: `read_iadd16` is the control of `read_dadd16`. It has the same number of adds, but no add waits for a load. |
| 20 | ` *   read_sp24, read_sp32, read_sp40, read_sp48, read_sp56: the read_sparse` | Comment: names the kernels `read_sp24`, `read_sp32`, `read_sp40`, `read_sp48` and `read_sp56` (lines 1306 to 1310). Each is the loop of the kernel `read_sparse` (line 652) with another number of `nop`. |
| 21 | ` *     loop (128 B per iteration, 4 ldp) with that many nop in place of 9.` | Comment: the `read_sparse` loop handles 128 B per loop pass with 4 `ldp`. It has 9 `nop`. The new kernels have 24, 32, 40, 48 or 56 `nop` in their place. |
| 22 | ` *   read_1pl_nop96: the read_1pl loop with 96 nop after the 4 loads.` | Comment: the kernel `read_1pl_nop96` (line 1315) is the loop of the kernel `read_1pl` (line 988) with 96 `nop` after its 4 loads. |
| 23 | ` *   write_nop32, write_nop96, write_nop128, write_nop256: the asmwrite loop` | Comment: names the kernels `write_nop32`, `write_nop96`, `write_nop128` and `write_nop256` (lines 1361 to 1364). Each is the loop of the kernel `asmwrite`. |
| 24 | ` *     with that many nop after the 8 stp.` | Comment: they have 32, 96, 128 or 256 `nop` after the 8 `stp` instructions, which store the data. |
| 25 | ` *   copy_nop96, copy_nop192: the asmcopy loop with that many nop after the` | Comment: the kernels `copy_nop96` and `copy_nop192` (lines 1404 to 1405) are the loop of the kernel `asmcopy` with 96 or 192 `nop`. |
| 26 | ` *     8 stp.` | Comment: in the two copy kernels the `nop` instructions stand after the 8 `stp`. |
| 27 | ` *   A third pad after these kernels, so that call() and the code up to the` | Comment: the last addition of the list is a third pad after the new kernels (lines 1446 to 1449). A pad is a run of unused bytes in the code. In `bwx12` this pad sets the start address of the function `call`, which follows the kernels. |
| 28 | ` *     end of timed_sequence_hot() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence_hot` keeps its placement modulo 64. The build record of CRB gives 24 as the start address of `call` modulo 64, for `bwx12` and for `bwx11` [Ref2]. |
| 29 | ` * The line that includes the self-test file is changed by additions only: the` | Comment: the line that includes the self-test file is changed by additions only (lines 2894 to 2900). |
| 30 | ` * old line stands inside "#if 0".` | Comment: the old include line stands inside `#if 0`. So the compiler skips it, and no old line was deleted. |
| 31 | ` * MAX_SEQ stays 64: the 55 kernels fit in one --seq list.` | Comment: `MAX_SEQ` (line 128) stays 64. It is the largest number of entries of a `--seq` list. So one list can name all 55 kernels of `bwx12`. |
| 32 | ` */` | Ends the history comment. |
| 33 | `/* bwx12- */` | Comment: a marker. The block that line 1 opened ends here. |

### History comment of the version `bwx11`: three kernels and the option `--evict-mb` (lines 34 to 59)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `/* bwx11+ */` | Comment: a marker. A block of text that the version `bwx11` added starts here. The marker of line 59 ends the block. |
| 35 | `/*` | Opens a history comment. It tells what the version of the marker in line 34 added. |
| 36 | ` * bwx11.c - bwx10.c plus the additions of round 4 (2026-11-15). Every` | Comment: `bwx11.c` is `bwx10.c` plus the additions of round 4, made on 2026-11-15. Round 4 is a round of work on the program. It is not a round of the option `--rounds`. |
| 37 | ` * addition stands between a line "bwx11+" and a line "bwx11-" (both are` | Comment: every addition of that round stands between a marker line `bwx11+` and a marker line `bwx11-`. |
| 38 | ` * comments). Without these blocks this file is bwx10.c byte for byte:` | Comment: both marker lines are comments. Without these blocks the text of `bwx11.c` is `bwx10.c`, byte for byte. |
| 39 | ` * test_runner11.py checks it. So the 26 kernels of bwx10, call(),` | Comment: the script `test_runner11.py` in the code folder `bwx11-2026-11-15` checks this. So the 26 kernels of `bwx10` and the function `call` (line 1491) are the text of `bwx10.c` without a change. |
| 40 | ` * timed_sequence(), timed_sequence_hot() and the interval mode are the text` | Comment: the same holds for the functions `timed_sequence` (line 1995) and `timed_sequence_hot` (line 2056) and for the interval mode, the mode of the option `--seq`. |
| 41 | ` * of bwx10.c.` | Comment: the end of the sentence of lines 39 to 40. The parts that it names are the text of `bwx10.c`. |
| 42 | ` *` | Comment: an empty line of the comment. |
| 43 | ` * Additions:` | Comment: the heading of the list of additions. |
| 44 | ` *   kernels read_nop64, read_nop96, read_nop128: the asmread loop with 64, 96` | Comment: three kernels: `read_nop64`, `read_nop96` and `read_nop128` (lines 1062 to 1064). Each is the loop of the kernel `asmread` with `nop` instructions added. A `nop` is an instruction that does nothing. The whole-chip test of 2026-11-17 runs `read_nop96` [Ref4]. |
| 45 | ` *     and 128 nop instructions after the 8 ldp. They stand after the last` | Comment: the three kernels have 64, 96 and 128 `nop` after the 8 `ldp` instructions, which load the data. In the source they stand after the last kernel of `bwx10`. |
| 46 | ` *     kernel of bwx10 in the source and in kernels[], so the kernels of bwx10` | Comment: in the kernel table `kernels[]` they also stand after the kernels of `bwx10` (line 1472). |
| 47 | ` *     keep their machine code and their loop offsets.` | Comment: so the kernels of `bwx10` keep their machine code and their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. |
| 48 | ` *   A second pad after these kernels, so that call() and the code up to the` | Comment: a second pad after these kernels (lines 1072 to 1075). A pad is a run of unused bytes in the code. In the version `bwx11` it sets the start address of the function `call`. |
| 49 | ` *     end of timed_sequence_hot() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence_hot` keeps its placement modulo 64. |
| 50 | ` *   --evict-mb N  (trial mode) before the first trial the worker writes N MiB` | Comment: the option `--evict-mb N` of the trial mode. Before the first trial the worker writes N MiB of other memory, twice (line 2428). The whole-chip test of 2026-11-17 does not use the trial mode [Ref4]. |
| 51 | ` *     of other memory twice. This pushes the benchmark buffer out of the` | Comment: after these writes the caches no longer hold the data of the benchmark buffer. |
| 52 | ` *     caches, so its lines are read back from memory.` | Comment: so the next read of the buffer brings its cache lines back from memory. A cache line is a block of 64 B. |
| 53 | ` *   M rows evict_mb and evict_ns. With --trace and N above 0 also the rows` | Comment: two new M rows, `evict_mb` and `evict_ns` (lines 2501 to 2507). An M row prints one setting or one fact of a process in the trial mode. With `--trace` and N above 0 the program also prints two TR rows. |
| 54 | ` *     TR,-1,0,evict_start,<t_ns> and TR,-1,1,evict_end,<t_ns>.` | Comment: the two TR rows are `TR,-1,0,evict_start,<t_ns>` and `TR,-1,1,evict_end,<t_ns>`. They give the clock times of the start and of the end of these writes, in ns (line 2509). |
| 55 | ` * The line that includes the self-test file is changed by additions only: the` | Comment: the line that includes the self-test file is changed by additions only (lines 2888 to 2893). |
| 56 | ` * old line stands inside "#if 0".` | Comment: the old include line stands inside `#if 0`. So the compiler skips it, and no old line was deleted. |
| 57 | ` * The plan file format is unchanged ("# bwx8-plan v1").` | Comment: the format of the plan file is unchanged. Its first line is still `# bwx8-plan v1` (line 1815). |
| 58 | ` */` | Ends the history comment. |
| 59 | `/* bwx11- */` | Comment: a marker. The block that line 34 opened ends here. |

### History comment of the version `bwx10`: five kernels and two options of the trial mode (lines 60 to 84)

| Line | Source | Explanation |
|---:|---|---|
| 60 | `/* bwx10+ */` | Comment: a marker. A block of text that the version `bwx10` added starts here. The marker of line 84 ends the block. |
| 61 | `/*` | Opens a history comment. It tells what the version of the marker in line 60 added. |
| 62 | ` * bwx10.c - bwx8.c plus the additions of round 3 (2026-11-15). Every addition` | Comment: `bwx10.c` is `bwx8.c` plus the additions of round 3, made on 2026-11-15. Round 3 is a round of work on the program. It is not a round of the option `--rounds`. |
| 63 | ` * stands between a line "bwx10+" and a line "bwx10-" (both are comments).` | Comment: every addition of that round stands between a marker line `bwx10+` and a marker line `bwx10-`. Both marker lines are comments. |
| 64 | ` * Without these blocks, and with the name of the included self-test file set` | Comment: one more change separates `bwx10.c` from `bwx8.c`: the name of the included self-test file (line 2891). |
| 65 | ` * back, this file is bwx8.c byte for byte: test_runner10.py checks it. So the` | Comment: without the blocks, and with that name set back, the text of `bwx10.c` is `bwx8.c`, byte for byte. The script `test_runner10.py` in the code folder `bwx10-2026-11-15` checks this. |
| 66 | ` * 21 kernels of bwx8, call(), timed_sequence() and the interval mode are the` | Comment: so the 21 kernels of `bwx8`, the function `call` (line 1491), the function `timed_sequence` (line 1995) and the interval mode are unchanged. The interval mode is the mode of the option `--seq`. |
| 67 | ` * text of bwx8.c.` | Comment: the end of the sentence of line 66. The parts that it names are the text of `bwx8.c`. |
| 68 | ` *` | Comment: an empty line of the comment. |
| 69 | ` * Additions:` | Comment: the heading of the list of additions. |
| 70 | ` *   kernels read_pf256, read_pf512, read_pf1024, read_pf2048, read_1pl. They` | Comment: five kernels: `read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048` (lines 979 to 982) and `read_1pl` (line 988). The whole-chip test of 2026-11-17 runs `read_1pl` [Ref4]. |
| 71 | ` *     stand after the last kernel of bwx8 in the source and in kernels[], so` | Comment: in the source and in the kernel table `kernels[]` (lines 1468 to 1469) the five kernels stand after the last kernel of `bwx8`. |
| 72 | ` *     the kernels of bwx8 keep their machine code and their loop offsets.` | Comment: so the kernels of `bwx8` keep their machine code and their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. |
| 73 | ` *   --rec-pad BYTES  (trial mode) unused bytes before the win[] array of the` | Comment: the option `--rec-pad BYTES` of the trial mode. It puts that many unused bytes before the array `win[]`, which holds the window records (line 2278). |
| 74 | ` *     record block.` | Comment: the array `win[]` is a part of the record block. That is the one memory block that holds the results of all trials (line 2261). |
| 75 | ` *   --hot-copy       (trial mode) timed_sequence_hot() runs the windows: it` | Comment: the option `--hot-copy` of the trial mode. With it the function `timed_sequence_hot` (line 2056) runs the windows of a trial. |
| 76 | ` *     does not read or write win[i] between the first and the last pass of a` | Comment: between the first pass and the last pass of a window that function does not read or write `win[i]`, the record of the window. |
| 77 | ` *     window.` | Comment: the last word of the sentence of lines 75 to 76. |
| 78 | ` *   M rows rec_pad, hot_copy, rec_addr, win_addr, win_size, stack_addr,` | Comment: new M rows of the trial mode (line 2491): `rec_pad`, `hot_copy`, `rec_addr`, `win_addr`, `win_size` and `stack_addr`. An M row prints one setting or one fact of the process. |
| 79 | ` *     buf_addr, tw_addr.` | Comment: two more new M rows: `buf_addr` and `tw_addr`. |
| 80 | ` *   A pad after the new kernels, so that call() and the code up to the end` | Comment: a pad after the new kernels (lines 1036 to 1039). A pad is a run of unused bytes in the code. In the version `bwx10` it sets the start address of the function `call`. |
| 81 | ` *     of timed_sequence() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence` keeps its placement modulo 64. |
| 82 | ` * The plan file format is unchanged ("# bwx8-plan v1").` | Comment: the format of the plan file is unchanged. Its first line is still `# bwx8-plan v1` (line 1815). |
| 83 | ` */` | Ends the history comment. |
| 84 | `/* bwx10- */` | Comment: a marker. The block that line 60 opened ends here. |

### Comment of the version `bwx8`: the two modes and the stand-in kernels (lines 85 to 105)

| Line | Source | Explanation |
|---:|---|---|
| 85 | `/*` | Opens the comment of the version `bwx8`. It is the first version of the runner that has a trial mode. |
| 86 | ` * bwx8.c - scratch copy of bwx.c (crb/tmp/agent-scratch/bwx-2026-11-13) for` | Comment: `bwx8.c` is a scratch copy of `bwx.c`, the first runner. The path in parentheses is the folder of `bwx.c`. In the code repo that folder has the name `bwx-2026-11-13`. |
| 87 | ` * the design crb/new-test-kernel/tackle-8mb.md. The contract with the other` | Comment: the copy was made for the design document `tackle-8mb.md` in the folder `crb/new-test-kernel`. The sentence about the contract continues in line 88. |
| 88 | ` * parts is DECISIONS-bwx8.md in this folder.` | Comment: the contract with the other parts of that work is the file `DECISIONS-bwx8.md`. It fixes the file formats that the parts exchange. The file lies in the code folder `bwx8-2026-11-14`, the folder of `bwx8.c`. |
| 89 | ` *` | Comment: an empty line of the comment. |
| 90 | ` * Two modes:` | Comment: the program has two modes. |
| 91 | ` *   --seq ...    the interval mode of bwx.c. Its code is the text of bwx.c.` | Comment: the option `--seq` selects the interval mode of `bwx.c`. The comment says that the code of this mode is the text of `bwx.c`. `main` runs this mode when no argument is the word `--trial` (lines 2912 to 2914). The whole-chip test of 2026-11-17 uses this mode only [Ref4]. |
| 92 | ` *   --trial ...  one pinned worker runs the trials of a plan file. A trial is` | Comment: the option `--trial` selects the trial mode. One pinned worker thread runs the trials of a plan file. All code of this mode stands after the function `parse_events` (lines 1771 to 1793). |
| 93 | ` *                previous activity, prefix, predecessor and target windows` | Comment: a trial is a list of windows in four phases: previous activity, prefix, predecessor and target. A window runs one kernel on one range of the buffer for a fixed time. |
| 94 | ` *                with nothing but clock reads between them.` | Comment: between two windows the worker does nothing but read the clock. The code has one more step there: for a trial with the counter state `read` it also reads the counter group and the thread CPU time before each target window (lines 2003 to 2004). |
| 95 | ` *` | Comment: an empty line of the comment. |
| 96 | ` * Everything from "#define _GNU_SOURCE" to the end of parse_events() is the` | Comment: names a range of this file. It reaches from the line `#define _GNU_SOURCE` (line 106) to the end of the function `parse_events` (line 1793). |
| 97 | ` * text of bwx.c, so the kernels, PLACE, call() and alloc_buf() are unchanged.` | Comment: that range is the text of `bwx.c`. So the kernels, the macro `PLACE` (line 163), the function `call` (line 1491) and the function `alloc_buf` (line 434) are unchanged. The later versions put their marked blocks into this range too. |
| 98 | ` * All code of the trial mode stands after it. The build uses` | Comment: all code of the trial mode stands after that range. The sentence about the build continues in line 99. |
| 99 | ` * -fno-toplevel-reorder, so the kernels keep their place in the binary.` | Comment: the build uses the gcc flag `-fno-toplevel-reorder`. With it gcc writes the functions in the order of the source. So the kernels keep their place in the binary. The build record of CRB for `bwx12` holds this flag [Ref2]. |
| 100 | ` *` | Comment: an empty line of the comment. |
| 101 | ` * On AArch64 the kernels are the real ones. On any other machine every NEON` | Comment: on AArch64, the 64-bit Arm instruction set, the kernels are the real ones. The sentence about other machines starts here. |
| 102 | ` * and asm kernel is replaced by a plain C stand-in, so that the harness can` | Comment: on any other machine a plain C loop replaces every NEON kernel and every assembly kernel. The comment calls this loop a stand-in. NEON is the vector part of AArch64. |
| 103 | ` * be run on the development machine. Rates of a stand-in build mean nothing.` | Comment: the stand-ins have one purpose: the program can then run on the development machine. The rates of a build with stand-ins mean nothing. The CRB binary of `bwx12` is the AArch64 build: the header of every csv file of the whole-chip test says `kernels=aarch64` [Ref5]. |
| 104 | ` * GB means 1e9 bytes throughout.` | Comment: GB means 1e9 bytes in the whole file. |
| 105 | ` */` | Ends the comment. |

### Includes, constants and the highest CPU that the process may use (lines 106 to 141)

| Line | Source | Explanation |
|---:|---|---|
| 106 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include. It makes the Linux-specific declarations of the C library visible, for example `sched_setaffinity` and `CPU_SET`. |
| 107 | `#ifdef __aarch64__` | Compiles line 108 only when the compiler builds for AArch64, the 64-bit Arm instruction set. gcc defines the macro `__aarch64__` in that case. |
| 108 | `#include <arm_neon.h>` | Includes `arm_neon.h`. It declares the NEON intrinsics, for example `vld1q_u64`. An intrinsic is a C function that maps to one vector instruction. NEON is the vector part of AArch64. |
| 109 | `#endif` | Ends the `#ifdef` of line 107. |
| 110 | `#include <errno.h>` | Includes `errno.h`. It declares `errno`, the error number that a failed library call sets. `parse_long` tests it (lines 356 to 358). |
| 111 | `#include <linux/perf_event.h>` | Includes `linux/perf_event.h`. It declares the structure `perf_event_attr` and the `PERF_FORMAT` constants. `open_counters` (line 1582) opens the hardware counters with them. |
| 112 | `#include <pthread.h>` | Includes `pthread.h`. It declares the thread functions `pthread_create` and `pthread_join` and the barrier function `pthread_barrier_wait`. |
| 113 | `#include <sched.h>` | Includes `sched.h`. It declares the CPU set type `cpu_set_t` and the calls `sched_getaffinity` and `sched_setaffinity`. They read and set the CPUs on which Linux may run a thread. |
| 114 | `#include <setjmp.h>` | Includes `setjmp.h`. It declares `sigsetjmp` and `siglongjmp`. No other line of this file uses them. The self-test file that this file includes uses them. |
| 115 | `#include <signal.h>` | Includes `signal.h`. It declares `sigaction` and the signal numbers. No other line of this file uses them. The included self-test file uses them to catch `SIGSEGV`, the signal that Linux sends at a forbidden memory access. |
| 116 | `#include <stdatomic.h>` | Includes `stdatomic.h`. It declares the atomic types and the functions `atomic_load`, `atomic_store` and `atomic_fetch_add`. The three variables of the common start use them (lines 323 to 325). |
| 117 | `#include <stdint.h>` | Includes `stdint.h`. It declares the integer types of fixed size, for example `uint64_t` (64 bits, without a sign) and `int64_t` (64 bits, with a sign). |
| 118 | `#include <stdio.h>` | Includes `stdio.h`. It declares the input and output functions, for example `printf`, `fprintf`, `fopen` and `fgets`. |
| 119 | `#include <stdlib.h>` | Includes `stdlib.h`. It declares `exit`, `strtol`, `strtod`, `calloc` and `getenv`. |
| 120 | `#include <string.h>` | Includes `string.h`. It declares the text and memory functions, for example `strcmp`, `strtok`, `memset` and `strerror`. |
| 121 | `#include <sys/mman.h>` | Includes `sys/mman.h`. It declares `mmap`, `mprotect` and `madvise`. `alloc_buf` (line 434) uses them for the buffers. |
| 122 | `#include <sys/syscall.h>` | Includes `sys/syscall.h`. It declares the numbers of the system calls, here `SYS_perf_event_open`. `open_counters` passes this number to `syscall` (line 1595). |
| 123 | `#include <time.h>` | Includes `time.h`. It declares `clock_gettime` and the structure `timespec`. `now_ns` (line 327) reads the clock with them. |
| 124 | `#include <unistd.h>` | Includes `unistd.h`. It declares `sysconf`, `getpid` and `read`. |
| 126 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2097152 bytes (2 MiB), the size of one huge page. The expression is 2 shifted left by 20 bits. Every buffer starts at a multiple of this value (line 442). |
| 127 | `#define MAX_CPUS 1024` | `MAX_CPUS`: the `--cpus` list may hold at most 1024 CPUs (line 406). |
| 128 | `#define MAX_SEQ 64` | `MAX_SEQ`: the `--seq` list may hold at most 64 kernels (line 1759). The lists of the whole-chip test hold 5 or 3 kernels [Ref4]. |
| 129 | `#define MAX_EV 8` | `MAX_EV`: the `--events` list may hold at most 8 counter events (line 1776). The argument lines of the whole-chip test name 6 events [Ref4]. |
| 130 | `#define CHECK_BYTES (8UL << 20) /* --stop pass: clock is read after at least this many bytes */` | `CHECK_BYTES`: 8388608 bytes (8 MiB). Comment: with `--stop pass` a thread reads the clock after at least this many bytes. For some sizes the code reads the clock earlier. The number of whole passes between two clock reads is this value divided by the size of the range, rounded down, and at least 1 (lines 1704 to 1706). So with a range of 3 MiB the thread reads the clock after 2 passes, which are 6 MiB. The trial mode computes its passes in the same way (line 2248). The whole-chip test runs with `--stop common`, so it does not use this value [Ref4]. |
| 131 | `#define CHUNK_BYTES HUGE_BYTES  /* --stop common: clock is read after each chunk of this size */` | `CHUNK_BYTES`: the value of `HUGE_BYTES`, 2097152 bytes (2 MiB). It is the size of a chunk. Comment: with `--stop common` a worker calls the kernel on one chunk and then reads the clock (lines 1693 to 1700). When the range of a `--seq` entry is below 2 MiB, the chunk is that whole range (line 1693). |
| 132 | `#define LEAD_NS 2000000L        /* --stop common: the common start is this long after the barrier */` | `LEAD_NS`: 2000000 ns (2 ms). With `--stop common` the main thread reads the clock after its barrier wait and sets the common start time of an interval to that clock value plus 2 ms (lines 3057 to 3059). The release at the barrier is not the start of the timed interval. Each worker waits until the clock reaches the common start time (line 1681). Then it starts its timed interval with its own clock read `t0` (line 1688). |
| 133 | `#define LATE_NS 100000L         /* --stop common: flag "late" if a thread starts later than this */` | `LATE_NS`: 100000 ns (100 us, which is 0.1 ms). With `--stop common` a thread gets the flag `late` when its start clock read is more than this after the common start (line 1725). |
| 134 | `/* Highest CPU that the process may use. Rule of the test machine: CPUs 0 to` | Comment: the macro below gives the highest CPU number that the process may use. The rule of the test machine starts here: only the CPUs 0 to 119. |
| 135 | ` * 119 only, never 126 or 127. main() removes every higher CPU from the` | Comment: the end of the rule: never CPU 126 or CPU 127. `main` calls `restrict_cpus` (line 2911), which removes every higher CPU from the set of CPUs that Linux may use for the process. |
| 136 | ` * allowed set of the process, and --cpus rejects one. Another machine can` | Comment: the option `--cpus` also rejects a higher CPU (line 401). |
| 137 | ` * build with -DMAX_USE_CPU=N. */` | Comment: for another machine the build can set another limit with the compiler option `-DMAX_USE_CPU=N`. |
| 138 | `#ifndef MAX_USE_CPU` | Tests whether the build command has already defined `MAX_USE_CPU`. Only if not, line 139 is compiled. `restrict_cpus` (line 368) and `parse_cpus` (line 388) apply the limit. |
| 139 | `#define MAX_USE_CPU 119` | The default value: the highest CPU that the process may use is CPU 119. The CRB build of `bwx12` gave no `-D` option, so this value was used [Ref2]. |
| 140 | `#endif` | Ends the `#ifndef` of line 138. |

### Loop placement: the macros `PLACE` and `PADOF` (lines 142 to 165)

| Line | Source | Explanation |
|---:|---|---|
| 142 | `/*` | Opens the comment about the placement of the kernel loops. |
| 143 | ` * Loop placement (handoff B.7). PLACE(name) stands directly before kernel` | Comment: the topic is the loop placement. The aim is that the loop of each kernel starts at a known address modulo 64, the loop offset. Section B.7 of the file `handoff.md`, the specification of the first runner, treats this offset as a test factor [Ref10]. The macro `PLACE(name)` stands directly before the kernel function. |
| 144 | ` * k_<name>. It pads .text to a 64 B boundary and then adds PAD_<name> zero bytes,` | Comment: the kernel function has the name `k_` plus the kernel name. `PLACE` first pads the code section `.text` to a 64 B boundary. Then it adds zero bytes. The macro `PAD_` plus the kernel name gives their number. |
| 145 | ` * so the function starts at PAD_<name> modulo 64. This needs the gcc flags` | Comment: so the function starts at that pad value modulo 64. The method needs two gcc flags. |
| 146 | ` * -fno-toplevel-reorder -falign-functions=4, and PAD must be a multiple of 4.` | Comment: the two flags are `-fno-toplevel-reorder` and `-falign-functions=4`. A pad must be a multiple of 4. Both flags are in the build record of CRB for `bwx12` [Ref2]. |
| 147 | ` *` | Comment: an empty line of the comment. |
| 148 | ` * For a kernel with a planned loop offset, PAD = (LOOP - HEAD) mod 64. LOOP` | Comment: the rule for a kernel with a planned loop offset: the pad is `(LOOP - HEAD) mod 64`. |
| 149 | ` * is the planned offset of the loop start modulo 64. HEAD is the number of` | Comment: `LOOP` is the planned offset of the loop start, modulo 64. `HEAD` is a number of bytes. |
| 150 | ` * bytes between the function start and the loop start: 4 or 20 in the` | Comment: `HEAD` counts the bytes of code between the start of the function and the start of its loop. The comment gives the values 4 and 20. |
| 151 | ` * listings of bw_new (results/kernels-20261113T181222Z/probe.txt). HEAD is a` | Comment: these two values come from the listings of the binary `bw_new` in the file `probe.txt` of the result folder `kernels-20261113T181222Z` [Ref7]. `bw_new` is the benchmark binary of 2026-11-13 with the new kernels. |
| 152 | ` * guess until the objdump listing of the CRB build confirms it: override it` | Comment: a `HEAD` value is a guess until the machine-code listing of the CRB build confirms it. |
| 153 | ` * with -DHEAD_<name>=N, or the whole pad with -DPAD_<name>=N.` | Comment: the build can replace one `HEAD` value with `-DHEAD_<name>=N`, or a whole pad with `-DPAD_<name>=N`. The CRB build of `bwx12` used no `-D` option [Ref2]. |
| 154 | ` * -DB3_OFFSET=0\|36\|52 puts the loops of copy, asmcopy and asmcopy2 at that` | Comment: the build option `-DB3_OFFSET=0`, `-DB3_OFFSET=36` or `-DB3_OFFSET=52` moves the loops of the kernels `copy`, `asmcopy` and `asmcopy2`. |
| 155 | ` * offset (step B3).` | Comment: these loops then start at that offset modulo 64 (lines 166 to 168). The option belongs to step B3 of the test plan of the first runner. |
| 156 | ` *` | Comment: an empty line of the comment. |
| 157 | ` * For the other kernels the default PAD is the start offset modulo 64 that` | Comment: the rule for every other kernel: the default pad is a start offset modulo 64 that the function has in an older binary. |
| 158 | ` * the function has in bw_new (new C and asm kernels) or in bw_old (old` | Comment: for a new C kernel or an assembly kernel the older binary is `bw_new`. For an old kernel it is `bw_old`. The old read kernel and the new read kernel show the result. The loop of `k_read` starts at 36 modulo 64 in `bwx12` and in `bw_new`. The loop of `k_oldread` in `bwx12` and the loop of `k_read` in `bw_old` both start at 40 modulo 64 [Ref1] [Ref7]. |
| 159 | ` * kernels). An A/A copy takes the PAD of its original.` | Comment: an A/A copy takes the pad of its original. An A/A copy is the same kernel source under a second name, for example `asmread2`. |
| 160 | ` */` | Ends the comment. |
| 161 | `#define STR2(x) #x` | `STR2(x)` turns its argument into a text in quotes. The preprocessor operator `#` does that. |
| 162 | `#define STR(x) STR2(x)` | `STR(x)` first replaces `x` by its value when `x` is a macro. Then it calls `STR2`. So with the default value 32 of `PAD_read`, `STR(PAD_read)` gives the text `"32"` and not the name in quotes. |
| 163 | `#define PLACE(name) __asm__(".pushsection .text\n.p2align 6\n.fill " STR(PAD_##name) ", 1, 0\n.popsection\n")` | `PLACE(name)` writes an `__asm__` statement outside of a function. gcc passes its text to the assembler without a change. `.pushsection .text` continues in the code section. `.p2align 6` pads the code up to an address that is a multiple of 64. `.fill N, 1, 0` adds N bytes of value 0. N is the value of the macro whose name `PAD_##name` builds from `PAD_` and the argument. `.popsection` returns to the section that was in use before. So the function that follows starts at N modulo 64. |
| 164 | `#define PADOF(loop, head) (((loop) - (head)) & 63)` | `PADOF(loop, head)`: `loop` minus `head`, modulo 64. The operation `& 63` keeps the low 6 bits. So a negative difference also gives a value from 0 to 63. |

### Planned loop offsets, head sizes and pads of the first kernels (lines 166 to 252)

| Line | Source | Explanation |
|---:|---|---|
| 166 | `#ifdef B3_OFFSET` | Tests whether the build command defined `B3_OFFSET`. The CRB build of `bwx12` did not, so the `#else` branch of lines 169 to 171 was compiled [Ref2]. |
| 167 | `#define LOOP_copy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_copy`, the planned loop offset of the kernel `copy`, is N. |
| 168 | `#define LOOP_asmcopy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_asmcopy`, the planned loop offset of the kernel `asmcopy`, is N too. |
| 169 | `#else` | Starts the branch for a build without `B3_OFFSET`. |
| 170 | `#define LOOP_copy 36` | `LOOP_copy`: the loop of the kernel `copy` must start at 36 modulo 64. In the CRB binary of `bwx12` the loop of `k_copy` starts at `0x4a64`, which is 36 modulo 64 [Ref1]. The whole-chip test of 2026-11-17 runs no copy kernel [Ref4]. |
| 171 | `#define LOOP_asmcopy 52` | `LOOP_asmcopy`: the loop of the kernel `asmcopy` must start at 52 modulo 64. In the CRB binary of `bwx12` the loop of `k_asmcopy` starts at `0x5034`, which is 52 modulo 64 [Ref1]. |
| 172 | `#endif` | Ends the `#ifdef` of line 166. |
| 173 | `#define LOOP_asmcopy_c 52` | `LOOP_asmcopy_c`: 52 modulo 64, the planned loop offset of the three kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg` (lines 198 to 206). `B3_OFFSET` does not change it. |
| 174 | `#ifndef HEAD_copy` | Compiles line 175 only when the build command has not defined `HEAD_copy`. Every value up to line 251 has this pattern of three lines: a default that a `-D` option of the build can replace. |
| 175 | `#define HEAD_copy 4` | `HEAD_copy`: 4 bytes of code, which is one instruction, stand between the start of `k_copy` and the start of its loop. The listing of the CRB build of `bwx12` shows this distance [Ref1]. |
| 176 | `#endif` | Ends the `#ifndef` of line 174. |
| 177 | `#ifndef HEAD_asmcopy` | Compiles line 178 only when the build command has not defined `HEAD_asmcopy`. |
| 178 | `#define HEAD_asmcopy 20` | `HEAD_asmcopy`: 20 bytes of code, which are 5 instructions, stand before the loop of `k_asmcopy`. The listing of the CRB build of `bwx12` shows them: 4 `stp` instructions that save the registers `d8` to `d15`, and the `add` that computes the end address [Ref1]. |
| 179 | `#endif` | Ends the `#ifndef` of line 177. |
| 180 | `#ifndef HEAD_asmcopy_c` | Compiles line 181 only when the build command has not defined `HEAD_asmcopy_c`. |
| 181 | `#define HEAD_asmcopy_c 4` | `HEAD_asmcopy_c`: 4 bytes of code stand before the loop of `k_asmcopy_c`. The listing of the CRB build of `bwx12` shows this distance [Ref1]. |
| 182 | `#endif` | Ends the `#ifndef` of line 180. |
| 183 | `#ifndef HEAD_asmcopy_c_add` | Compiles line 184 only when the build command has not defined `HEAD_asmcopy_c_add`. |
| 184 | `#define HEAD_asmcopy_c_add 4` | `HEAD_asmcopy_c_add`: 4 bytes of code stand before the loop of `k_asmcopy_c_add`. The listing of the CRB build of `bwx12` shows this distance [Ref1]. |
| 185 | `#endif` | Ends the `#ifndef` of line 183. |
| 186 | `#ifndef HEAD_asmcopy_c_reg` | Compiles line 187 only when the build command has not defined `HEAD_asmcopy_c_reg`. |
| 187 | `#define HEAD_asmcopy_c_reg 20` | `HEAD_asmcopy_c_reg`: 20 bytes of code stand before the loop of `k_asmcopy_c_reg`. This kernel saves `d8` to `d15`, as `asmcopy` does. The listing of the CRB build of `bwx12` shows this distance [Ref1]. |
| 188 | `#endif` | Ends the `#ifndef` of line 186. |
| 189 | `#ifndef PAD_copy` | Compiles line 190 only when the build command has not defined `PAD_copy`. |
| 190 | `#define PAD_copy PADOF(LOOP_copy, HEAD_copy)` | `PAD_copy`: `PADOF` (line 164) computes it from the two values above. With the defaults it is (36 - 4) modulo 64 = 32 bytes. In the CRB binary of `bwx12` the function `k_copy` starts at `0x4a60`, which is 32 modulo 64 [Ref1]. The whole-chip test of 2026-11-17 does not run the kernel `copy` [Ref4]. |
| 191 | `#endif` | Ends the `#ifndef` of line 189. |
| 192 | `#ifndef PAD_asmcopy` | Compiles line 193 only when the build command has not defined `PAD_asmcopy`. |
| 193 | `#define PAD_asmcopy PADOF(LOOP_asmcopy, HEAD_asmcopy)` | `PAD_asmcopy`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx12` the function `k_asmcopy` starts at `0x5020`, which is 32 modulo 64 [Ref1]. The whole-chip test of 2026-11-17 does not run the kernel `asmcopy` [Ref4]. |
| 194 | `#endif` | Ends the `#ifndef` of line 192. |
| 195 | `#ifndef PAD_asmcopy2` | Compiles line 196 only when the build command has not defined `PAD_asmcopy2`. |
| 196 | `#define PAD_asmcopy2 PAD_asmcopy` | `PAD_asmcopy2`: the A/A copy `asmcopy2` takes the pad of its original `asmcopy`. With the defaults that is 32 bytes. The whole-chip test of 2026-11-17 does not run the kernel `asmcopy2` [Ref4]. |
| 197 | `#endif` | Ends the `#ifndef` of line 195. |
| 198 | `#ifndef PAD_asmcopy_c` | Compiles line 199 only when the build command has not defined `PAD_asmcopy_c`. |
| 199 | `#define PAD_asmcopy_c PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c)` | `PAD_asmcopy_c`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx12` the function `k_asmcopy_c` starts at `0x51b0`, which is 48 modulo 64 [Ref1]. The whole-chip test of 2026-11-17 does not run the kernel `asmcopy_c` [Ref4]. |
| 200 | `#endif` | Ends the `#ifndef` of line 198. |
| 201 | `#ifndef PAD_asmcopy_c_add` | Compiles line 202 only when the build command has not defined `PAD_asmcopy_c_add`. |
| 202 | `#define PAD_asmcopy_c_add PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_add)` | `PAD_asmcopy_c_add`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx12` the function `k_asmcopy_c_add` starts at `0x5270`, which is 48 modulo 64 [Ref1]. The whole-chip test of 2026-11-17 does not run the kernel `asmcopy_c_add` [Ref4]. |
| 203 | `#endif` | Ends the `#ifndef` of line 201. |
| 204 | `#ifndef PAD_asmcopy_c_reg` | Compiles line 205 only when the build command has not defined `PAD_asmcopy_c_reg`. |
| 205 | `#define PAD_asmcopy_c_reg PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_reg)` | `PAD_asmcopy_c_reg`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx12` the function `k_asmcopy_c_reg` starts at `0x5320`, which is 32 modulo 64 [Ref1]. The whole-chip test of 2026-11-17 does not run the kernel `asmcopy_c_reg` [Ref4]. |
| 206 | `#endif` | Ends the `#ifndef` of line 204. |
| 207 | `#ifndef PAD_read` | Compiles line 208 only when the build command has not defined `PAD_read`. |
| 208 | `#define PAD_read 32` | `PAD_read` = 32: the new read kernel `k_read` starts at 32 modulo 64. In the CRB binary of `bwx12` it starts at the address `0x49a0`, which is 32 modulo 64 [Ref1]. |
| 209 | `#endif` | Ends the `#ifndef` of line 207. |
| 210 | `#ifndef PAD_write` | Compiles line 211 only when the build command has not defined `PAD_write`. |
| 211 | `#define PAD_write 0` | `PAD_write` = 0: `k_write`, the function of the first touch, starts at 0 modulo 64. In the CRB binary of `bwx12` it starts at the address `0x4a00` [Ref1]. |
| 212 | `#endif` | Ends the `#ifndef` of line 210. |
| 213 | `#ifndef PAD_asmread` | Compiles line 214 only when the build command has not defined `PAD_asmread`. |
| 214 | `#define PAD_asmread 0` | `PAD_asmread` = 0: `k_asmread` starts at 0 modulo 64. In the CRB binary of `bwx12` it starts at the address `0x4ac0` [Ref1]. |
| 215 | `#endif` | Ends the `#ifndef` of line 213. |
| 216 | `#ifndef PAD_asmread2` | Compiles line 217 only when the build command has not defined `PAD_asmread2`. |
| 217 | `#define PAD_asmread2 PAD_asmread` | `PAD_asmread2`: the A/A copy `asmread2` takes the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `asmread2` [Ref4]. |
| 218 | `#endif` | Ends the `#ifndef` of line 216. |
| 219 | `#ifndef PAD_asmwrite` | Compiles line 220 only when the build command has not defined `PAD_asmwrite`. |
| 220 | `#define PAD_asmwrite 32` | `PAD_asmwrite` = 32: `k_asmwrite` starts at 32 modulo 64. The whole-chip test of 2026-11-17 does not run the kernel `asmwrite` [Ref4]. |
| 221 | `#endif` | Ends the `#ifndef` of line 219. |
| 222 | `#ifndef PAD_asmwrite2` | Compiles line 223 only when the build command has not defined `PAD_asmwrite2`. |
| 223 | `#define PAD_asmwrite2 PAD_asmwrite` | `PAD_asmwrite2`: the A/A copy `asmwrite2` takes the pad of `asmwrite`, which is 32 bytes. The whole-chip test of 2026-11-17 does not run the kernel `asmwrite2` [Ref4]. |
| 224 | `#endif` | Ends the `#ifndef` of line 222. |
| 225 | `#ifndef PAD_oldread` | Compiles line 226 only when the build command has not defined `PAD_oldread`. |
| 226 | `#define PAD_oldread 0` | `PAD_oldread` = 0: the old read kernel `k_oldread` starts at 0 modulo 64. In the CRB binary of `bwx12` it starts at the address `0x4600` [Ref1]. |
| 227 | `#endif` | Ends the `#ifndef` of line 225. |
| 228 | `#ifndef PAD_oldread2` | Compiles line 229 only when the build command has not defined `PAD_oldread2`. |
| 229 | `#define PAD_oldread2 PAD_oldread` | `PAD_oldread2`: the A/A copy `oldread2` takes the pad of `oldread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `oldread2` [Ref4]. |
| 230 | `#endif` | Ends the `#ifndef` of line 228. |
| 231 | `#ifndef PAD_oldwrite` | Compiles line 232 only when the build command has not defined `PAD_oldwrite`. |
| 232 | `#define PAD_oldwrite 32` | `PAD_oldwrite` = 32: `k_oldwrite` starts at 32 modulo 64. The whole-chip test of 2026-11-17 does not run the kernel `oldwrite` [Ref4]. |
| 233 | `#endif` | Ends the `#ifndef` of line 231. |
| 234 | `#ifndef PAD_oldcopy` | Compiles line 235 only when the build command has not defined `PAD_oldcopy`. |
| 235 | `#define PAD_oldcopy 32` | `PAD_oldcopy` = 32: `k_oldcopy` starts at 32 modulo 64. The whole-chip test of 2026-11-17 does not run the kernel `oldcopy` [Ref4]. |
| 236 | `#endif` | Ends the `#ifndef` of line 234. |
| 237 | `#ifndef PAD_read_nop4` | Compiles line 238 only when the build command has not defined `PAD_read_nop4`. |
| 238 | `#define PAD_read_nop4 PAD_asmread` | `PAD_read_nop4`: the kernel `read_nop4` takes the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop4` [Ref4]. |
| 239 | `#endif` | Ends the `#ifndef` of line 237. |
| 240 | `#ifndef PAD_read_nop8` | Compiles line 241 only when the build command has not defined `PAD_read_nop8`. |
| 241 | `#define PAD_read_nop8 PAD_asmread` | `PAD_read_nop8`: the kernel `read_nop8` takes the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop8` [Ref4]. |
| 242 | `#endif` | Ends the `#ifndef` of line 240. |
| 243 | `#ifndef PAD_read_nop16` | Compiles line 244 only when the build command has not defined `PAD_read_nop16`. |
| 244 | `#define PAD_read_nop16 PAD_asmread` | `PAD_read_nop16`: the kernel `read_nop16` takes the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop16` [Ref4]. |
| 245 | `#endif` | Ends the `#ifndef` of line 243. |
| 246 | `#ifndef PAD_read_nop32` | Compiles line 247 only when the build command has not defined `PAD_read_nop32`. |
| 247 | `#define PAD_read_nop32 PAD_asmread` | `PAD_read_nop32`: the kernel `read_nop32` takes the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop32` [Ref4]. |
| 248 | `#endif` | Ends the `#ifndef` of line 246. |
| 249 | `#ifndef PAD_read_sparse` | Compiles line 250 only when the build command has not defined `PAD_read_sparse`. |
| 250 | `#define PAD_read_sparse PAD_asmread` | `PAD_read_sparse`: the kernel `read_sparse` takes the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_sparse` [Ref4]. The pads of three kernels that the test runs stand later in the file: `read_1pl` (lines 927 to 929), `read_nop96` (lines 1056 to 1058) and `read_nop256` (lines 1134 to 1136). |
| 251 | `#endif` | Ends the `#ifndef` of line 249. |

### Kernel types and one entry of the `--seq` list (lines 253 to 263)

| Line | Source | Explanation |
|---:|---|---|
| 253 | `enum ktype { T_READ, T_WRITE, T_COPY, T_OLDREAD };` | `enum ktype`: the four kernel types `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD`. The function `call` (line 1491) chooses the argument list of a kernel by its type. |
| 254 | `typedef void (*read_fn)(const uint64_t *, size_t);` | `read_fn`: the function type of a read kernel (type `T_READ`). The kernel gets the start address and the number of 8-byte words. It returns nothing. Of the six kernels of the whole-chip test, `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl` have this type [Ref4]. |
| 255 | `typedef uint64_t (*oldread_fn)(const uint64_t *, size_t);` | `oldread_fn`: the function type of an old read kernel (type `T_OLDREAD`). The kernel gets the same two arguments and returns a 64-bit sum. The kernel `oldread` of the whole-chip test has this type [Ref4]. |
| 256 | `typedef void (*write_fn)(uint64_t *, size_t, uint64_t);` | `write_fn`: the function type of a write kernel (type `T_WRITE`). The kernel gets the start address, the number of 8-byte words and the 64-bit value to store. No timed interval of the whole-chip test runs a write kernel [Ref4]. |
| 257 | `typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);` | `copy_fn`: the function type of a copy kernel (type `T_COPY`). The kernel gets the destination address, the source address and the number of 8-byte words. `restrict` tells the compiler that the two ranges do not overlap. No timed interval of the whole-chip test runs a copy kernel [Ref4]. |
| 259 | `struct entry {` | Starts `struct entry`: one entry of the `--seq` list. |
| 260 | `    int k;          /* index into kernels[] */` | `k`: the index of the kernel in the kernel table `kernels[]` (line 1458). |
| 261 | `    uint64_t bytes; /* 0 until main() replaces it by --bytes */` | `bytes`: the size of the range that the kernel works on, in bytes. It is 0 when the entry has no `@SIZE` part. `main` then sets it to the `--bytes` value (lines 2989 to 2990). In the whole-chip test no entry has such a part, so every entry gets 268435456 bytes (256 MiB) [Ref4]. |
| 262 | `};` | Ends `struct entry`. |

### The settings structure `cfg` (lines 264 to 283)

| Line | Source | Explanation |
|---:|---|---|
| 264 | `static struct {` | Starts the structure `cfg`. It holds the settings of the process. The code that reads the arguments fills it. |
| 265 | `    int threads;` | `threads`: the number of worker threads (`--threads`). It is 120 in the whole-chip test [Ref4]. |
| 266 | `    int ncpus;` | `ncpus`: the number of entries of `cpus`. It is 120 in the whole-chip test [Ref4]. |
| 267 | `    int cpus[MAX_CPUS];` | `cpus`: the CPU list of `--cpus`, in the order of the list. `parse_cpus` (line 388) fills it. In the whole-chip test `cpus[i]` is i for i from 0 to 119 [Ref4]. |
| 268 | `    uint64_t bytes;` | `bytes`: the value of `--bytes` in bytes. It is the range of each buffer that the program uses: the first touch writes this many bytes (line 1646), and no `--seq` entry may be larger (line 2991). The mapped buffer is this value rounded up to a multiple of 2 MiB (line 428). It is 268435456 (256 MiB) in the whole-chip test, a multiple of 2 MiB [Ref4]. |
| 269 | `    double min_s;` | `min_s`: the `--min-ms` value in seconds. With `--stop common` the deadline of an interval is this long after its common start (line 3061). With `--stop pass` a thread runs at least this long (line 1715). It is 6.0 in the whole-chip test: the deadline is 6 s after the common start [Ref4]. |
| 270 | `    int use_thp;` | `use_thp`: 1 when the program asks Linux for 2 MiB pages (transparent huge pages) for the buffers. The option `--no-thp` sets it to 0. It is 1 in the whole-chip test [Ref4]. |
| 271 | `    struct entry seq[MAX_SEQ];` | `seq`: the kernel list of `--seq`, one `struct entry` per kernel. |
| 272 | `    int nseq;` | `nseq`: the number of entries of `seq`. It is 5 for the spec file `like.spec` and 3 for `cfwd.spec` and `crev.spec` [Ref4]. |
| 273 | `    int rounds;` | `rounds`: how many times the list runs (`--rounds`). It is 2 in the whole-chip test [Ref4]. |
| 274 | `    int stop_common;  /* --stop common */` | `stop_common`: 1 with `--stop common`. With this stop rule all threads of an interval get the same deadline. It is 1 in the whole-chip test [Ref4]. |
| 275 | `    int start_offset; /* --start offset */` | `start_offset`: 1 with `--start offset`. Then the place in its buffer at which a thread starts an interval depends on the number of the thread (line 1662). The option chooses a place in the buffer. It does not set the start time of an interval. It is 0 in the whole-chip test (`--start common`): every thread starts each interval at byte 0 of its own buffer [Ref4]. |
| 276 | `    int two_buffers;  /* buffer b exists: --two-buffers, or a copy kernel in the sequence */` | `two_buffers`: 1 when each thread has a second buffer `b`. The option `--two-buffers` sets it. `main` also sets it when the list holds a copy kernel (lines 2996 to 2997). It is 0 in the whole-chip test: no copy kernel is in a list, and each thread has one buffer [Ref4]. |
| 277 | `    int count;        /* --count */` | `count`: 1 with `--count`. Then each thread opens hardware counters and reads them before and after each interval. It is 1 in the whole-chip test [Ref4]. |
| 278 | `    long pmu_type;    /* --pmu-type: the "type" field of perf_event_attr */` | `pmu_type`: the value of `--pmu-type`. It goes into the field `type` of the structure `perf_event_attr` (line 1589). The field tells Linux which counter hardware to use. It is 11 in the whole-chip test [Ref4]. |
| 279 | `    int nev;` | `nev`: the number of counter events of `--events`. It is 6 in the whole-chip test [Ref4]. |
| 280 | `    char ev_name[MAX_EV][32];` | `ev_name`: the names of the events, at most 31 characters each. |
| 281 | `    uint64_t ev_code[MAX_EV];` | `ev_code`: the codes of the events. A code goes into the field `config` of `perf_event_attr` (line 1591). |
| 282 | `} cfg = { .threads = 1, .min_s = 0.5, .use_thp = 1, .rounds = 1, .pmu_type = -1 };` | Ends the structure and sets the defaults: 1 thread, 0.5 s per interval, a request for 2 MiB pages, 1 round and no PMU type (the value -1). Every other field starts at 0. |

### Structures `page`, `counts`, `result` and `thread` (lines 284 to 315)

| Line | Source | Explanation |
|---:|---|---|
| 284 | `struct page {` | Starts `struct page`: the page state of one buffer. |
| 285 | `    long kb_total, kb_huge; /* -1: no exact entry in /proc/self/smaps */` | `kb_total`: the size of the mapping of the buffer. `kb_huge`: the part of it that lies on 2 MiB pages. Both are in kB (1 kB is 1024 bytes here). `read_smaps` (line 1515) fills them. Comment: -1 means that the Linux file `/proc/self/smaps` has no exact entry for the buffer. Such a value is printed as `NA`. |
| 286 | `};` | Ends `struct page`. |
| 288 | `struct counts {` | Starts `struct counts`: one reading of the counters of a thread. |
| 289 | `    uint64_t cpu_ns;              /* CLOCK_THREAD_CPUTIME_ID */` | `cpu_ns`: the CPU time that the thread has used, in ns. The Linux clock `CLOCK_THREAD_CPUTIME_ID` gives it (line 1612). |
| 290 | `    uint64_t enabled, running;    /* of the counter group */` | `enabled` and `running`: two times of the counter group in ns. They say how long the counters were enabled and how long they really counted. |
| 291 | `    uint64_t val[MAX_EV];` | `val`: one count per event that opened. |
| 292 | `};` | Ends `struct counts`. |
| 294 | `/* One thread, one interval. Written by the worker between the start barrier` | Comment: the structure below holds the result of one thread for one interval. The worker writes it after the start barrier of the interval. The start barrier is the barrier wait that stands before the timed interval (line 1675). The timed interval of a thread does not start at this barrier. It starts later, at the clock read `t0` of the thread (line 1688). |
| 295 | ` * and the end barrier of the interval; read by main() after the end barrier. */` | Comment: the worker writes it before the end barrier of the interval, and `main` reads it after that barrier. In the code the worker stores the structure at line 1726, before its barrier wait of line 1727. `main` reads it after its barrier wait of line 3064. So the two threads never use it at the same time. |
| 296 | `struct result {` | Starts `struct result`. |
| 297 | `    uint64_t bytes;` | `bytes`: the bytes that the thread counted in the interval (line 1721). |
| 298 | `    int64_t t_sched, t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_sched`: the common start time. `t_start`: the start clock read `t0` of the thread. `t_end`: its last clock read `t1`. All three are values of the clock `CLOCK_MONOTONIC` in ns (lines 1722 to 1724). With `--stop pass` there is no common start, and `t_sched` gets the value of `t0`. |
| 299 | `    int late;` | `late`: the late flag. It is 1 when `t0` of the thread was more than `LATE_NS` after the common start (line 1725). |
| 300 | `    struct page pg[2]; /* one-thread process only: read by the worker before the interval */` | `pg`: the page state of the buffers `a` and `b`. Comment: only a process with one thread uses it. There the worker reads the page state before the interval (lines 1670 to 1674). The whole-chip test has 120 threads and does not use this field [Ref4]. |
| 301 | `    long long vm[4];` | `vm`: four counters of the Linux file `/proc/vmstat` (line 1545). As for `pg`, only the worker of a process with one thread fills it. |
| 302 | `    struct counts c0, c1;` | `c0` and `c1`: the counter readings before `t0` (lines 1685 to 1686) and after the last `t1` (lines 1718 to 1719). |
| 303 | `};` | Ends `struct result`. |
| 305 | `struct thread {` | Starts `struct thread`: one record per worker. |
| 306 | `    int idx;` | `idx`: the number of the thread, counted from 0 (line 3010). In the whole-chip test it is 0 to 119 [Ref4]. |
| 307 | `    int cpu;` | `cpu`: the CPU that the thread pins itself to, or -1 without `--cpus` (line 3011). In every T row of the whole-chip test the thread number equals the CPU number [Ref5]. |
| 308 | `    uint64_t *a, *b;` | `a`: the buffer of the thread. `b`: the second buffer, which only a copy kernel or `--two-buffers` needs. Without it `b` stays `NULL`. In the whole-chip test each thread has the buffer `a` only [Ref5]. |
| 309 | `    int group_fd;      /* leader of the counter group, -1 if no event opened */` | `group_fd`: the file descriptor of the leader of the counter group. A file descriptor is the number that Linux returns for an open object. Comment: it is -1 when no event opened. `open_counters` (line 1582) sets it. |
| 310 | `    int ev_pos[MAX_EV]; /* position of the event in the group read, -1 if it did not open */` | `ev_pos`: for each event its position among the values of a group read. Comment: -1 when the event did not open. |
| 311 | `    int nopen;` | `nopen`: the number of events that opened. |
| 312 | `    struct result res;` | `res`: the result of the last interval of this thread. |
| 313 | `    pthread_t tid;` | `tid`: the thread handle that `pthread_create` returns (line 3012). |
| 314 | `};` | Ends `struct thread`. |

### Global variables: the barrier, the base time and the common start (lines 316 to 326)

| Line | Source | Explanation |
|---:|---|---|
| 316 | `static pthread_barrier_t bar;` | `bar`: the barrier. A thread that calls `pthread_barrier_wait` on it blocks until all workers and the main thread have called it. `main` creates it for the number of workers plus 1 (line 3005). In the whole-chip test these are 121 threads [Ref4]. |
| 317 | `static int64_t t_base_ns; /* clock at process start: printed times are relative to it */` | `t_base_ns`: the clock value at the process start (line 2908). Comment: the printed times are relative to it. |
| 318 | `static long page_bytes;` | `page_bytes`: the page size that Linux reports, in bytes (line 2909). `alloc_buf` uses it (line 442). |
| 320 | `/* --stop common (handoff B.4). gen only grows. main() stores the two times` | Comment: the three variables below belong to `--stop common`. The comment cites section B.4 of the file `handoff.md`, the specification of the first runner. `gen` only grows. |
| 321 | ` * before it increments gen, so a worker that sees the new gen reads the new` | Comment: `main` stores the two times before it adds 1 to `gen` (lines 3060 to 3062). A worker first waits for the new value of `gen` (line 1677). |
| 322 | ` * times. */` | Comment: then the worker loads the two times (lines 1679 to 1680). So it never uses the times of the interval before. |
| 323 | `static _Atomic uint64_t gen;` | `gen`: an atomic counter of intervals. It starts at 0. `_Atomic` makes every load and every store of the variable one indivisible step. |
| 324 | `static _Atomic int64_t t_sched_ns;` | `t_sched_ns`: the common start time of the coming interval, as a value of the clock `CLOCK_MONOTONIC` in ns. With `--stop common` every worker waits until the clock reaches this time (line 1681). The timed interval of a worker starts after that, at its own clock read `t0` (line 1688). |
| 325 | `static _Atomic int64_t deadline_ns;` | `deadline_ns`: the common deadline of the coming interval: the common start time plus the `--min-ms` value (line 3061). With `--stop common` a worker ends its timed interval at its first clock read `t1` at or after this deadline (lines 1700 to 1701). So each worker finishes the chunk that it is in. |

### Function `now_ns`: read the clock (lines 327 to 333)

| Line | Source | Explanation |
|---:|---|---|
| 327 | `static int64_t now_ns(void)` | Starts the function `now_ns`. It reads the clock and returns the time in ns. Every time stamp of the program comes from this function. In a timed interval the worker calls it once for the start `t0` (line 1688). With `--stop common` it then calls it once after each chunk for `t1` (line 1700). A chunk is 2 MiB, or the whole range of the `--seq` entry when that is smaller. So one clock read per chunk is inside the timed interval. This is the same for every kernel. |
| 328 | `{` | Opens the body of `now_ns`. |
| 329 | `    struct timespec ts;` | `ts`: a `timespec`, the structure for a time as whole seconds plus ns. |
| 330 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | `clock_gettime` reads the Linux clock `CLOCK_MONOTONIC` into `ts`. This clock cannot be set. It does not jump when the date or the time of the system is changed. |
| 331 | `    return (int64_t)ts.tv_sec * 1000000000L + ts.tv_nsec;` | Returns the seconds times 1000000000 plus the ns part: the time in ns as one 64-bit number. |
| 332 | `}` | Ends the function `now_ns`. |

### Function `parse_bytes`: a size text such as `256M` (lines 334 to 350)

| Line | Source | Explanation |
|---:|---|---|
| 334 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `256M` into a number of bytes. `main` calls it for `--bytes` (line 2937). `parse_seq` calls it for the `@SIZE` part of a `--seq` entry (line 1764). |
| 335 | `{` | Opens the body of `parse_bytes`. |
| 336 | `    char *end;` | `end`: `strtod` sets it to the first character after the number. |
| 337 | `    double v = strtod(s, &end);` | `strtod` reads a decimal number from the start of the text into `v`. The number may have a fraction, for example `1.5`. |
| 338 | `    double mul = 1;` | `mul`: the factor of the unit letter. It stays 1 when no letter follows the number. |
| 339 | `    switch (*end) {` | Looks at the character after the number. |
| 340 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | The letter `k` or `K`: the factor is 1024. `end++` moves `end` to the character after the letter. |
| 341 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | The letter `m` or `M`: the factor is 1048576, which is 1 MiB. In the whole-chip test `--bytes 256M` gives 256 times 1048576, which is 268435456 bytes [Ref4]. |
| 342 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | The letter `g` or `G`: the factor is 1073741824, which is 1024 MiB. |
| 343 | `    }` | Ends the `switch` of line 339. |
| 344 | `    if (end == s \|\| *end != '\0' \|\| v <= 0 \|\| (uint64_t)(v * mul) == 0) { /* 0 bytes after rounding is no size */` | Tests four error cases. The text holds no number (`end == s`). Other text follows the size. The value is 0 or below. The size is 0 bytes after the conversion to a whole number. Comment: 0 bytes after rounding is no size. |
| 345 | `        fprintf(stderr, "bad size: %s\n", s);` | In an error case: prints `bad size:` and the text to stderr, the error output of the program. |
| 346 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 347 | `    }` | Ends the `if` of line 344. |
| 348 | `    return (uint64_t)(v * mul);` | Returns the size in bytes as a whole number. The conversion drops a fraction of a byte. |
| 349 | `}` | Ends the function `parse_bytes`. |

### Function `parse_long`: a whole number inside a range (lines 351 to 364)

| Line | Source | Explanation |
|---:|---|---|
| 351 | `/* A whole number in [lo, hi], with nothing after it. Anything else ends the` | Comment: the function below accepts only a whole number from `lo` to `hi` with no text after it. |
| 352 | ` * program: a malformed value must not run as 0. */` | Comment: any other text ends the program. The reason: a malformed value must not run as the number 0. |
| 353 | `static long parse_long(const char *s, const char *what, long lo, long hi)` | Starts the function `parse_long`. It turns the text `s` into a whole number inside the range `lo` to `hi`. `what` is the name of the option, for the error message. On the path of the whole-chip test: `--threads 120` (allowed 1 to 4096), `--rounds 2` (1 to 1000000) and `--pmu-type 11` (0 to 2147483647) [Ref4]. |
| 354 | `{` | Opens the body of `parse_long`. |
| 355 | `    char *end;` | `end`: `strtol` sets it to the first character after the number. |
| 356 | `    errno = 0;` | Sets `errno` to 0. `strtol` sets it to an error value when the number does not fit the type `long`. |
| 357 | `    long v = strtol(s, &end, 10);` | `strtol` reads a decimal whole number (base 10) from the start of the text into `v`. |
| 358 | `    if (end == s \|\| *end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi) {` | Tests the error cases: no digit was read, other text follows the number, the number does not fit the type `long`, or it lies outside the range `lo` to `hi`. |
| 359 | `        fprintf(stderr, "bad %s: '%s' (a whole number from %ld to %ld is needed)\n", what, s, lo, hi);` | In an error case: prints `bad`, the option name, the text and the allowed range to stderr. |
| 360 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 361 | `    }` | Ends the `if` of line 358. |
| 362 | `    return v;` | Returns the number. |
| 363 | `}` | Ends the function `parse_long`. |

### Function `restrict_cpus`: no CPU above `MAX_USE_CPU` (lines 365 to 386)

| Line | Source | Explanation |
|---:|---|---|
| 365 | `/* Removes every CPU above MAX_USE_CPU from the allowed set of the calling` | Comment: the function below removes every CPU above `MAX_USE_CPU` from the allowed set of the calling thread. The allowed set is the set of CPUs on which Linux may run the thread. |
| 366 | ` * thread. main() calls it before it starts a thread, so the main thread and` | Comment: `main` calls the function before it starts a thread (line 2911). A new thread takes over the allowed set of the thread that creates it. |
| 367 | ` * every worker (also one without --cpus) stay on the permitted CPUs. */` | Comment: so the main thread and every worker stay on the permitted CPUs. This also holds for a worker of a run without `--cpus`. |
| 368 | `static void restrict_cpus(void)` | Starts the function `restrict_cpus`. |
| 369 | `{` | Opens the body of `restrict_cpus`. |
| 370 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 371 | `    int changed = 0;` | `changed`: becomes 1 when the set held a CPU above the limit. |
| 372 | `    if (sched_getaffinity(0, sizeof set, &set) != 0) {` | `sched_getaffinity` with the first argument 0 reads the allowed set of the calling thread into `set`. A return value other than 0 means that the call failed. |
| 373 | `        perror("sched_getaffinity");` | On failure: `perror` prints the word `sched_getaffinity` and the reason that Linux gave. |
| 374 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 375 | `    }` | Ends the `if` of line 372. |
| 376 | `    for (int c = MAX_USE_CPU + 1; c < CPU_SETSIZE; c++)` | Starts a loop over every CPU number above `MAX_USE_CPU`, up to `CPU_SETSIZE - 1`. `CPU_SETSIZE` is the number of CPUs that the set type of the C library can hold. With the default limit the loop starts at CPU 120. |
| 377 | `        if (CPU_ISSET(c, &set)) {` | Tests whether the set holds the CPU `c`. |
| 378 | `            CPU_CLR(c, &set);` | Removes the CPU `c` from the set. |
| 379 | `            changed = 1;` | Records that the set was changed. |
| 380 | `        }` | Ends the `if` of line 377. |
| 381 | `    if (changed && (CPU_COUNT(&set) == 0 \|\| sched_setaffinity(0, sizeof set, &set) != 0)) {` | Runs only when a CPU was removed. An empty set is an error. If the set is not empty, `sched_setaffinity` passes the smaller set to Linux, and a failed call is an error too. In the whole-chip test the script `rx.sh` starts the program under `taskset -c 0-119` [Ref3]. So the set holds no CPU above 119, `changed` stays 0, and the function changes nothing. |
| 382 | `        fprintf(stderr, "cannot keep the process on CPUs 0-%d\n", MAX_USE_CPU);` | On error: prints `cannot keep the process on CPUs 0-` and the limit to stderr. |
| 383 | `        exit(2);` | On error: the whole program ends with exit status 2. |
| 384 | `    }` | Ends the `if` of line 381. |
| 385 | `}` | Ends the function `restrict_cpus`. |

### Function `parse_cpus`: the value of `--cpus` (lines 387 to 414)

| Line | Source | Explanation |
|---:|---|---|
| 387 | `/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */` | Comment: three examples of a CPU list: `0-119`, `0,2,4-7` and `0-118:2`. The last one is a range with a stride: every second CPU from 0 to 118. |
| 388 | `static void parse_cpus(char *list)` | Starts the function `parse_cpus`. It turns the value of `--cpus` into the array `cfg.cpus`, in the order of the list. |
| 389 | `{` | Opens the body of `parse_cpus`. |
| 390 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Starts a loop over the items of the list. `strtok` splits the text at each comma and returns one item per call. It writes into the text to do that. |
| 391 | `        char *e, *e2;` | `e` and `e2`: positions in the item that `strtol` sets. |
| 392 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the item into `lo`. `hi` starts with the same value and `step` with 1. So an item that is one number names one CPU. |
| 393 | `        if (e != tok && *e == '-') {` | When a number was read and a `-` follows it: the item is a range. |
| 394 | `            hi = strtol(e + 1, &e2, 10);` | Reads the upper bound of the range into `hi`. |
| 395 | `            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */` | When no digit follows the `-`, `e` is set back to `tok`, and the test of line 401 then rejects the item. If a number was read, `e` moves to the character after it. Comment: the item `0-` has no upper bound. |
| 396 | `            if (e != tok && *e == ':') {` | When the upper bound was read and a `:` follows it: the range has a stride. |
| 397 | `                step = strtol(e + 1, &e2, 10);` | Reads the stride into `step`. |
| 398 | `                e = e2 == e + 1 ? tok : e2;` | When no digit follows the `:`, `e` is set back to `tok`, and the test of line 401 rejects the item. If a number was read, `e` moves to the character after it. |
| 399 | `            }` | Ends the `if` of line 396. |
| 400 | `        }` | Ends the `if` of line 393. |
| 401 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| hi > MAX_USE_CPU \|\| step < 1) {` | Rejects an item in six cases: it holds no number, other text follows, the start is negative, the end is below the start, the end is above `MAX_USE_CPU` (119 with the default), or the stride is below 1. |
| 402 | `            fprintf(stderr, "bad cpu list: %s (CPUs 0-%d only)\n", tok, MAX_USE_CPU);` | On such an item: prints `bad cpu list:`, the item and the permitted range to stderr. |
| 403 | `            exit(2);` | On such an item: the whole program ends with exit status 2. |
| 404 | `        }` | Ends the `if` of line 401. |
| 405 | `        for (long c = lo; c <= hi; c += step) {` | Starts a loop over the CPU numbers of the item, from `lo` to `hi` in steps of `step`. |
| 406 | `            if (cfg.ncpus == MAX_CPUS) {` | Tests whether the array `cfg.cpus` is full. It holds at most `MAX_CPUS` entries, which is 1024. |
| 407 | `                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);` | When the array is full: prints `bad cpu list: more than 1024 cpus` to stderr. |
| 408 | `                exit(2);` | When the array is full: the whole program ends with exit status 2. |
| 409 | `            }` | Ends the `if` of line 406. |
| 410 | `            cfg.cpus[cfg.ncpus++] = (int)c;` | Appends the CPU number to `cfg.cpus` and counts it in `cfg.ncpus`. In the whole-chip test the list is `0-63,64-119`: two ranges with the stride 1. The result is 120 entries in rising order: `cfg.cpus[i]` is i [Ref4]. `main` gives thread i the CPU `cfg.cpus[i % cfg.ncpus]` (line 3011). With 120 threads and 120 entries that is `cfg.cpus[i]`. So the threads 0 to 63 get the CPUs of mesh 0, and the threads 64 to 119 get CPUs of mesh 1. |
| 411 | `        }` | Ends the loop of line 405. |
| 412 | `    }` | Ends the loop of line 390. |
| 413 | `}` | Ends the function `parse_cpus`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 415 to 425)

| Line | Source | Explanation |
|---:|---|---|
| 415 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It limits the calling thread to the CPU with the number `cpu`. A worker of a run with `--cpus` calls it at its start (lines 1641 to 1642), before it opens its counters and before it maps its buffer. |
| 416 | `{` | Opens the body of `pin_cpu`. |
| 417 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 418 | `    CPU_ZERO(&set);` | Empties the set. |
| 419 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 420 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 421 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 422 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 423 | `    }` | Ends the `if` of line 420. |
| 424 | `}` | Ends the function `pin_cpu`. |

### Function `buf_len`: the length of one buffer (lines 426 to 430)

| Line | Source | Explanation |
|---:|---|---|
| 426 | `static size_t buf_len(void)` | Starts the function `buf_len`. It returns the length of one buffer in bytes. |
| 427 | `{` | Opens the body of `buf_len`. |
| 428 | `    return (cfg.bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | Returns the `--bytes` value rounded up to a multiple of 2 MiB (`HUGE_BYTES`). The expression adds `HUGE_BYTES - 1` and then clears the low 21 bits. In the whole-chip test the value 268435456 is already 128 times 2 MiB. So the result is 268435456 bytes [Ref4]. |
| 429 | `}` | Ends the function `buf_len`. |

### Function `alloc_buf`: map one buffer, aligned to 2 MiB (lines 431 to 452)

| Line | Source | Explanation |
|---:|---|---|
| 431 | `/* The buffer starts at a 2 MiB boundary, at least one page above the start` | Comment: the buffer starts at a 2 MiB boundary. That boundary lies at least one page above the start of the mapping. |
| 432 | ` * of the mapping. The unused parts before and after it are PROT_NONE, so the` | Comment: the unused parts of the mapping before and after the buffer get the access right `PROT_NONE`, which forbids every access. |
| 433 | ` * buffer is one entry of its own in /proc/self/smaps (handoff B.6). */` | Comment: so the buffer is one entry of its own in `/proc/self/smaps`, the Linux file that lists every memory mapping of the process. `read_smaps` (line 1515) looks for an entry with exactly the start and the end of the buffer. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. |
| 434 | `static uint64_t *alloc_buf(void)` | Starts the function `alloc_buf`. It maps one buffer and returns its address. Each worker calls it once (line 1645). A worker of a run with `--cpus` has pinned itself before this call (lines 1641 to 1642). A worker that needs the second buffer calls it once more (line 1648). |
| 435 | `{` | Opens the body of `alloc_buf`. |
| 436 | `    size_t len = buf_len(), maplen = len + 2 * HUGE_BYTES;` | `len`: the buffer length from `buf_len`. `maplen`: 4 MiB more. The extra 4 MiB make room for the alignment of line 442 and for the two no-access ranges of lines 443 to 444. In the whole-chip test `len` is 268435456 bytes (256 MiB) and `maplen` is 272629760 bytes (260 MiB) [Ref4]. |
| 437 | `    uint8_t *raw = mmap(NULL, maplen, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `maplen` bytes of new memory that the process may read and write (`PROT_READ \| PROT_WRITE`). `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process only, and no file backs it. `NULL`: Linux chooses the address. `-1` and `0` are the two file arguments, which are not used here. The call does not yet give physical memory to the pages. That happens at the first touch (line 1646). |
| 438 | `    if (raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 439 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 440 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 441 | `    }` | Ends the `if` of line 438. |
| 442 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + (size_t)page_bytes + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the buffer start. It is the first 2 MiB boundary that lies at least one page above the start `raw` of the mapping. The expression adds the page size `page_bytes` and `HUGE_BYTES - 1` to `raw` and then clears the low 21 bits. The buffer is the range from `p` to `p + len`. So it starts at an address that is a multiple of 2 MiB. |
| 443 | `    if (mprotect(raw, (size_t)(p - raw), PROT_NONE) != 0 \|\|` | `mprotect` with `PROT_NONE` forbids every access to the unused range before the buffer, from `raw` to `p`. |
| 444 | `        mprotect(p + len, (size_t)(raw + maplen - (p + len)), PROT_NONE) != 0)` | Continues the test of line 443: the same for the unused range after the buffer, from `p + len` to the end of the mapping. This second call runs only when the first one succeeded. |
| 445 | `        perror("mprotect of the guard ranges (continuing; page state will be NA)");` | When one of the two calls failed: `perror` prints a message which says that the run continues and that the page state will be `NA`. The program does not stop. The script `rx.sh` appends the error output of the program to the file `stderr.txt` [Ref3]. In the whole-chip test every `stderr.txt` is empty [Ref5]. |
| 446 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: the advice `MADV_NOHUGEPAGE` matters on a host whose setting for transparent huge pages is `always`. |
| 447 | `     * would still get 2 MiB pages. */` | Comment: without that advice a run with `--no-thp` would still get 2 MiB pages on such a host. |
| 448 | `    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` gives Linux advice about the buffer range. With `cfg.use_thp` set, the advice is `MADV_HUGEPAGE`: use 2 MiB pages for this range. With `--no-thp` it is `MADV_NOHUGEPAGE`: do not use them. `cfg.use_thp` is 1 in the whole-chip test: no argument line holds `--no-thp` [Ref4]. The function does not test whether the buffer got 2 MiB pages. The P rows show it: in the test each P row reports 262144 kB of 262144 kB on 2 MiB pages [Ref5]. |
| 449 | `        perror("madvise (continuing)");` | When `madvise` failed: `perror` prints `madvise (continuing)` and the reason that Linux gave. The run continues. |
| 450 | `    return (uint64_t *)p;` | Returns the buffer start as a pointer to 8-byte words. No line of this file unmaps a buffer. So the buffer stays mapped until the process ends. |
| 451 | `}` | Ends the function `alloc_buf`. |

### Old read kernel: the macro `DEF_OLDREAD` and the kernels `oldread` and `oldread2` (lines 453 to 476)

| Line | Source | Explanation |
|---:|---|---|
| 453 | `/*` | Opens the comment about the old kernels. |
| 454 | ` * Old kernels: k_read, k_write and k_copy of bandwidth.orig.c (the benchmark` | Comment: the old kernels below are the functions `k_read`, `k_write` and `k_copy` of the file `bandwidth.orig.c`. |
| 455 | ` * until 2026-11-13), renamed. The old comment of k_read was: "16 independent` | Comment: `bandwidth.orig.c` was the benchmark source until 2026-11-13. Here its three kernels have the new names `k_oldread`, `k_oldwrite` and `k_oldcopy`. The binary `bw_old` of part A was built from that file [Ref12]. Apart from absolute addresses, the machine code of `k_oldread` in `bwx12` has the same instruction text as `k_read` of `bw_old` [Ref7]. A quotation of the old comment of `k_read` starts in this line. |
| 456 | ` * accumulators keep the loop load-bound: on 128-bit NEON gcc folds them into` | Comment, quotation: 16 separate running sums (accumulators) keep the loop load-bound. This means that the loads and not the adds should limit the speed of the loop. This is a statement of the old comment. It is not a measured result. |
| 457 | ` * 8 vector chains, enough to hide a 2-cycle add latency; on AVX-512 they` | Comment, quotation: with the 128-bit NEON registers gcc puts the 16 sums into 8 vector registers. Each register is a chain of adds of its own. The old comment says that 8 chains are enough for an add that takes 2 clock cycles: the adds then do not limit the speed of the loop. The listing of the CRB binary of `bwx12` confirms the 8 registers: the sums are in the registers `v24` to `v31` [Ref1]. |
| 458 | ` * become 2 zmm chains." oldread2 is the A/A copy: the same source under a` | Comment: the end of the quotation: with AVX-512, a vector instruction set of x86 processors, the sums become 2 chains in 512-bit registers. The next sentence: `oldread2` is the A/A copy, the same source under a second name. |
| 459 | ` * second name (the build uses -fno-ipa-icf, so gcc keeps both).` | Comment: the build uses the gcc flag `-fno-ipa-icf`. With it gcc keeps both functions. The flag is in the build record of CRB for `bwx12` [Ref2]. |
| 460 | ` */` | Ends the comment. |
| 461 | `#define DEF_OLDREAD(name) \` | Starts the macro `DEF_OLDREAD(name)`. It writes `PLACE(name)` and one function: the source text of the old read kernel. The backslash at the end of each line continues the macro on the next line. |
| 462 | `    PLACE(name); \` | `PLACE` (line 163) adds the pad of this kernel. So the function starts at the value of `PAD_` plus `name`, modulo 64. |
| 463 | `    __attribute__((noinline)) static uint64_t k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the macro argument into the function name. `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns a 64-bit sum. `noinline`: gcc must keep the function separate from its caller. The listing of the CRB build shows `k_oldread` as a function of its own [Ref1]. In a timed interval of the whole-chip test one call gets one chunk of 2 MiB: `n` is 262144 words (line 1695) [Ref4]. The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1669). In the test that range is the whole buffer of 256 MiB. |
| 464 | `    { \` | Opens the body of the kernel function. |
| 465 | `        uint64_t s[16] = { 0 }; \` | `s`: the 16 running sums. All start at 0. Machine code of `k_oldread`, once per call and before the loop: 4 `stp` instructions write 128 B of zeros to the stack (each stores two 16-byte registers), and the 8 registers `v24` to `v31` are set to 0. During the loop these 8 registers hold the 16 sums, two sums per register [Ref1]. |
| 466 | `        for (size_t i = 0; i < n; i += 16) \` | The outer loop. One pass takes 16 words, which are 128 B. Machine code of `k_oldread`: gcc did not unroll this loop. One pass of the machine loop is one pass of this source loop. Before the loop the code computes the number of passes into the register `x2` [Ref1]. |
| 467 | `            for (int j = 0; j < 16; j++) \` | The inner loop over the 16 words of the block. Machine code of `k_oldread`: gcc compiled this loop to vector instructions. No loop over `j` is left [Ref1]. |
| 468 | `                s[j] += a[i + j]; \` | Adds word `j` of the block to sum `j`. So every loaded word is an input of one add. Machine code of `k_oldread`, one loop pass of 16 instructions for 128 B [Ref1]: 4 `ldp` loads of 32 B each, at the byte offsets 0, 32, 64 and 96 from the read position. 8 vector adds: each one adds one loaded register to one of the sum registers `v24` to `v31` and so performs two of the 16 adds of the source. `add x0, x0, #0x80` moves the read position by 128 B. `add x1, x1, #0x1` counts the pass. `cmp` and `b.cc` branch back while the count is below the number of passes. No instruction of the loop stores to memory. |
| 469 | `        uint64_t sum = 0; \` | `sum`: the total of the 16 sums. It starts at 0. |
| 470 | `        for (int j = 0; j < 16; j++) \` | A loop over the 16 sums. It runs once per call, after the read loop. |
| 471 | `            sum += s[j]; \` | Adds the 16 sums into one value. Machine code of `k_oldread`, once per call [Ref1]: the 8 sum registers are stored to the stack and loaded back. Then 7 vector adds and one `addp` add them into one number. `addp` adds the two 64-bit halves of one register. |
| 472 | `        return sum; \` | Returns the total. Machine code of `k_oldread`: `fmov x0, d31` copies the result into the return register `x0` [Ref1]. `call` stores the returned value into the volatile variable `sink` (line 1500). So the sum is used, and the compiler cannot remove the loads and the adds as unused work. gcc also added a stack check to this function. It saves a guard value on the stack at the start and compares it before the return. A changed value leads to a call of `__stack_chk_fail` [Ref1]. |
| 473 | `    }` | Ends the kernel function and the macro. One call of `k_oldread` runs 53 instructions outside the loop [Ref1]. One chunk of 2 MiB is 16384 loop passes, which are 262144 instructions. |
| 474 | `DEF_OLDREAD(oldread)` | Creates the function `k_oldread`. It is the kernel `oldread` of `--seq`, the old read kernel, with the type `T_OLDREAD` in the kernel table (line 1462). In the CRB binary the function starts at the address `0x4600` and its loop at `0x4668`, which is 40 modulo 64 [Ref1]. For 256 B it runs 2 loop passes: 32 instructions with 8 `ldp` loads, 16 vector adds and 2 branches. The new read kernel runs 11 instructions for 256 B (line 527). Apart from absolute addresses, `k_oldread` has the same instruction text as `k_read` of the binary `bw_old` [Ref7]. The whole-chip test runs `oldread` at position 0 in part L and control I, and at position 0 (`cfwd.spec`) or 2 (`crev.spec`) in part C [Ref4]. |
| 475 | `DEF_OLDREAD(oldread2)` | Creates `k_oldread2`, the A/A copy of the old read kernel. The listing of the CRB build shows the same instruction text for both functions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |

### Old write kernel `oldwrite` and old copy kernel `oldcopy` (lines 477 to 490)

| Line | Source | Explanation |
|---:|---|---|
| 477 | `PLACE(oldwrite);` | `PLACE` adds the pad of the kernel `oldwrite`. `PAD_oldwrite` is 32 (line 232). |
| 478 | `__attribute__((noinline)) static void k_oldwrite(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_oldwrite`, the kernel `oldwrite`: the write kernel of the old benchmark source. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. The whole-chip test of 2026-11-17 does not run it [Ref4]. The first touch of a buffer uses `k_write` (line 531). |
| 479 | `{` | Opens the body of `k_oldwrite`. |
| 480 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 481 | `        a[i] = v;` | Stores `v` to word `i`: one store of 8 B per pass of the source loop. Machine code in the CRB binary of `bwx12`: gcc compiled the loop to instructions of SVE, the scalable vector extension of Arm. One loop pass has 4 instructions with one `st1d` store, which writes one vector of 8-byte words. The program reads the number of words per vector at run time with the instruction `cntd`. The listing does not give this number [Ref1]. |
| 482 | `}` | Ends the function `k_oldwrite`. |
| 484 | `PLACE(oldcopy);` | `PLACE` adds the pad of the kernel `oldcopy`. `PAD_oldcopy` is 32 (line 235). |
| 485 | `__attribute__((noinline)) static void k_oldcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_oldcopy`, the kernel `oldcopy`: the copy kernel of the old benchmark source. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 486 | `{` | Opens the body of `k_oldcopy`. |
| 487 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 488 | `        d[i] = s[i];` | Loads word `i` of the source and stores it to word `i` of the destination. The loaded value is stored and has no other use. Machine code in the CRB binary of `bwx12`: SVE instructions, as in `k_oldwrite`. One loop pass has 5 instructions with one `ld1d` load and one `st1d` store of one vector of 8-byte words [Ref1]. |
| 489 | `}` | Ends the function `k_oldcopy`. |

### AArch64 branch and the function `k_read`: the new read kernel (lines 491 to 529)

| Line | Source | Explanation |
|---:|---|---|
| 491 | `#if defined(__aarch64__)` | The lines from here to the `#else` of line 851 are compiled only for AArch64. The lines from that `#else` to the `#endif` of line 897 hold the stand-ins for other machines. The CRB binary of `bwx12` was compiled from this first branch. Proof: line 3024 prints `kernels=aarch64` only in this case, and the header of every csv file of the whole-chip test holds this text [Ref5]. |
| 492 | `#define STANDIN 0` | `STANDIN` is 0 in the AArch64 branch: the kernels are the real ones. The program then prints `kernels=aarch64` in its header (line 3024). |
| 493 | `/*` | Opens the comment about the C kernels. |
| 494 | ` * C kernels: unchanged from bench/bandwidth.c. Each iteration moves 256 B as` | Comment: the C kernels below are unchanged from the benchmark source `bandwidth.c` in the folder `bench`. One loop pass moves 256 B. |
| 495 | ` * 16 vectors of 16 B and does no arithmetic on the data. Callers guarantee` | Comment: the 256 B move as 16 vectors of 16 B. The loop does no arithmetic on the data. |
| 496 | ` * n * 8 is a multiple of 256 and non-zero. The empty asm statement of k_read` | Comment: the callers guarantee that the size `n * 8` in bytes is a multiple of 256 and is not 0. `main` checks the sizes (line 2973 and line 2991). A chunk of 2 MiB is a multiple of 256. The sentence about the empty `asm` statement starts here. |
| 497 | ` * and k_copy takes the 16 loaded vectors as inputs in NEON registers ("w"):` | Comment: the empty `asm` statement of `k_read` (lines 522 to 525) and of `k_copy` (lines 580 to 583) takes the 16 loaded vectors as inputs. The letter `w` says that each input must be in a NEON register. |
| 498 | ` * see the comment in bench/bandwidth.c.` | Comment: a comment in the file `bandwidth.c` of the folder `bench` explains this statement. |
| 499 | ` */` | Ends the comment. |
| 500 | `PLACE(read);` | `PLACE(read)` with `PAD_read` = 32 (line 208): the function starts at 32 modulo 64. In the CRB binary of `bwx12` the function `k_read` starts at the address `0x49a0` and its loop at `0x49a4`, which is 36 modulo 64 [Ref1]. The loop of `k_read` in `bw_new` has the same offset 36 [Ref7]. |
| 501 | `__attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)` | Starts the function `k_read`: the kernel `read` of `--seq`, the new read kernel, with the type `T_READ` in the kernel table (line 1460). `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns nothing: it computes no sum. `noinline`: gcc must keep the function separate from its caller. The listing shows it as a function of 13 instructions [Ref1]. Apart from absolute addresses, its instruction text equals the text of `k_read` in `bw_new`, one of the two binaries of part A [Ref7]. In the whole-chip test only part C runs it, at position 1 [Ref4]. |
| 502 | `{` | Opens the body of `k_read`. In a timed interval of the whole-chip test one call of the function gets one chunk of 2 MiB: `n` is 262144 words (line 1695) [Ref4]. The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1669). In the test that range is the whole buffer of 256 MiB. |
| 503 | `    const uint64_t *p = a;` | `p`: the read position. It starts at `a`. |
| 504 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx12`, once per call and before the loop: `add x1, x0, x1, lsl #3`. Before this instruction the register `x0` holds `a` and `x1` holds `n`. After it `x1` holds `end` [Ref1]. |
| 505 | `    do {` | Starts the loop. With `do` the loop body runs once before the first test of the end. So the range must not be empty. |
| 506 | `        uint64x2_t v0 = vld1q_u64(p + 0);` | `vld1q_u64(p + 0)` loads 16 B, which are two 8-byte words, from the read position into the vector `v0`. These are the bytes 0 to 15 of the current block of 256 B. |
| 507 | `        uint64x2_t v1 = vld1q_u64(p + 2);` | Loads the bytes 16 to 31 of the block, 2 words after the read position, into `v1`. Machine code of `bwx12`: gcc joined this load and the load of line 506 into one instruction, `ldp q31, q30, [x0]`, which loads 32 B [Ref1]. |
| 508 | `        uint64x2_t v2 = vld1q_u64(p + 4);` | Loads the bytes 32 to 47 of the block into `v2`. |
| 509 | `        uint64x2_t v3 = vld1q_u64(p + 6);` | Loads the bytes 48 to 63 of the block into `v3`. Machine code of `bwx12` for this load and the load of line 508: `ldp q29, q28, [x0, #32]` [Ref1]. |
| 510 | `        uint64x2_t v4 = vld1q_u64(p + 8);` | Loads the bytes 64 to 79 of the block into `v4`. |
| 511 | `        uint64x2_t v5 = vld1q_u64(p + 10);` | Loads the bytes 80 to 95 of the block into `v5`. Machine code of `bwx12` for this load and the load of line 510: `ldp q27, q26, [x0, #64]` [Ref1]. |
| 512 | `        uint64x2_t v6 = vld1q_u64(p + 12);` | Loads the bytes 96 to 111 of the block into `v6`. |
| 513 | `        uint64x2_t v7 = vld1q_u64(p + 14);` | Loads the bytes 112 to 127 of the block into `v7`. Machine code of `bwx12` for this load and the load of line 512: `ldp q25, q24, [x0, #96]` [Ref1]. |
| 514 | `        uint64x2_t v8 = vld1q_u64(p + 16);` | Loads the bytes 128 to 143 of the block into `v8`. |
| 515 | `        uint64x2_t v9 = vld1q_u64(p + 18);` | Loads the bytes 144 to 159 of the block into `v9`. Machine code of `bwx12` for this load and the load of line 514: `ldp q23, q22, [x0, #128]` [Ref1]. |
| 516 | `        uint64x2_t v10 = vld1q_u64(p + 20);` | Loads the bytes 160 to 175 of the block into `v10`. |
| 517 | `        uint64x2_t v11 = vld1q_u64(p + 22);` | Loads the bytes 176 to 191 of the block into `v11`. Machine code of `bwx12` for this load and the load of line 516: `ldp q21, q20, [x0, #160]` [Ref1]. |
| 518 | `        uint64x2_t v12 = vld1q_u64(p + 24);` | Loads the bytes 192 to 207 of the block into `v12`. |
| 519 | `        uint64x2_t v13 = vld1q_u64(p + 26);` | Loads the bytes 208 to 223 of the block into `v13`. Machine code of `bwx12` for this load and the load of line 518: `ldp q19, q18, [x0, #192]` [Ref1]. |
| 520 | `        uint64x2_t v14 = vld1q_u64(p + 28);` | Loads the bytes 224 to 239 of the block into `v14`. |
| 521 | `        uint64x2_t v15 = vld1q_u64(p + 30);` | Loads the bytes 240 to 255 of the block into `v15`. Machine code of `bwx12` for this load and the load of line 520: `ldp q17, q16, [x0, #224]`. One loop pass has 16 loads in the source and 8 `ldp` loads in the machine code. It reads 256 B, each byte once, in rising address order [Ref1]. |
| 522 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text. It adds no instruction to the loop. It names the loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. A comment in the benchmark source `bandwidth.c` gives the purpose: gcc must have all 16 values in registers at this point, and this keeps gcc from deleting the loads. After this statement nothing uses the values. They are dropped. The listing of `bwx12` shows no add and no other instruction that uses a loaded register [Ref1]. This is the difference to the old read kernel, which adds every loaded word to a sum. |
| 523 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 522: the inputs `v4` to `v7`. |
| 524 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 522: the inputs `v8` to `v11`. |
| 525 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 522: the inputs `v12` to `v15`. The statement ends here. |
| 526 | `        p += 32;` | Moves the read position forward by 32 words, which are 256 B. Machine code of `bwx12`: `add x0, x0, #0x100` [Ref1]. |
| 527 | `    } while (p < end);` | Repeats the loop while the read position is below the end. Machine code of `bwx12`: `cmp x1, x0`, then `b.hi` back to the first `ldp`. One loop pass is 11 instructions for 256 B: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1]. One chunk of 2 MiB is 8192 loop passes, which are 90112 instructions. |
| 528 | `}` | Ends the function `k_read`. Machine code of `bwx12`: one `ret` instruction. gcc used the registers `q16` to `q31` for the loads, and the function saves and restores no register [Ref1]. The AArch64 branch of line 491 continues after this function, up to line 851. |

### Function `k_write`: the NEON write kernel, used for the first touch (lines 530 to 556)

| Line | Source | Explanation |
|---:|---|---|
| 530 | `PLACE(write);` | `PLACE(write)` adds the pad of this kernel. `PAD_write` is 0 (line 211). So the function starts at a multiple of 64 bytes: the address `0x4a00` in the listing of the CRB build of `bwx12`. The function stands in the AArch64 branch of line 491, and the CRB binary holds this branch: the listing shows the `dup` and `stp` instructions of this function [Ref1]. |
| 531 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_write`, the NEON write kernel. It stores the value `v` to `n` 8-byte words, from the address `a` on. Each worker calls it once per buffer, directly after the allocation (line 1646). This call is the first touch. It happens before the first interval, and it is not timed. The call writes the first `cfg.bytes` bytes of the buffer, the range of `--bytes`. The buffer is this value rounded up to a multiple of 2 MiB (line 428). So the call writes the whole buffer only when `--bytes` is a multiple of 2 MiB, as in the whole-chip test (256 MiB) [Ref4]. The kernel table also offers this function as the kernel `write` (line 1460). No `--seq` list of the test names `write` [Ref4]. |
| 532 | `{` | Opens the body of `k_write`. |
| 533 | `    uint64_t *p = a;` | `p`: the write position. It starts at `a`. |
| 534 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx12`, before the loop: `add x1, x0, x1, lsl #3` [Ref1]. |
| 535 | `    uint64x2_t q = vdupq_n_u64(v);` | `vdupq_n_u64(v)` builds one 16-byte vector `q` that holds `v` twice. Machine code of `bwx12`, before the loop: `dup v31.2d, x2`. The register `x2` holds `v`. `dup` copies one 8-byte value into both halves of a 16-byte vector register [Ref1]. |
| 536 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 537 | `        vst1q_u64(p + 0, q);` | `vst1q_u64(p + 0, q)` stores the 16 bytes of `q` at the write position. These are the bytes 0 to 15 of the current block of 256 B. |
| 538 | `        vst1q_u64(p + 2, q);` | Stores `q` to the bytes 16 to 31 of the block. Machine code of `bwx12`: gcc joined this store and the store of line 537 into one instruction `stp q31, q31`. `stp` stores two 16-byte registers, which is 32 B. Here both are the register `q31` [Ref1]. |
| 539 | `        vst1q_u64(p + 4, q);` | Stores `q` to the bytes 32 to 47 of the block. |
| 540 | `        vst1q_u64(p + 6, q);` | Stores `q` to the bytes 48 to 63 of the block. |
| 541 | `        vst1q_u64(p + 8, q);` | Stores `q` to the bytes 64 to 79 of the block. |
| 542 | `        vst1q_u64(p + 10, q);` | Stores `q` to the bytes 80 to 95 of the block. |
| 543 | `        vst1q_u64(p + 12, q);` | Stores `q` to the bytes 96 to 111 of the block. |
| 544 | `        vst1q_u64(p + 14, q);` | Stores `q` to the bytes 112 to 127 of the block. |
| 545 | `        vst1q_u64(p + 16, q);` | Stores `q` to the bytes 128 to 143 of the block. |
| 546 | `        vst1q_u64(p + 18, q);` | Stores `q` to the bytes 144 to 159 of the block. |
| 547 | `        vst1q_u64(p + 20, q);` | Stores `q` to the bytes 160 to 175 of the block. |
| 548 | `        vst1q_u64(p + 22, q);` | Stores `q` to the bytes 176 to 191 of the block. |
| 549 | `        vst1q_u64(p + 24, q);` | Stores `q` to the bytes 192 to 207 of the block. |
| 550 | `        vst1q_u64(p + 26, q);` | Stores `q` to the bytes 208 to 223 of the block. |
| 551 | `        vst1q_u64(p + 28, q);` | Stores `q` to the bytes 224 to 239 of the block. |
| 552 | `        vst1q_u64(p + 30, q);` | Stores `q` to the bytes 240 to 255 of the block. The 16 stores of one loop pass fill 256 B. Each byte is written once. The machine loop of `bwx12` has 8 `stp` instructions [Ref1]. |
| 553 | `        p += 32;` | Moves the write position forward by 32 words, which are 256 B. Machine code of `bwx12`: `add x0, x0, #0x100`. gcc put this `add` at the start of the loop pass. So the 8 `stp` instructions use the offsets -256 to -32 [Ref1]. |
| 554 | `    } while (p < end);` | Repeats the loop while the write position is below `end`. Machine code of `bwx12`: `cmp x1, x0` and the branch `b.hi`. One loop pass is 11 instructions for 256 B: 1 `add`, 8 `stp`, 1 `cmp` and 1 branch [Ref1]. With `--bytes 256M`, as in the whole-chip test, the first touch writes 268435456 bytes in 1048576 loop passes [Ref4]. The binary `bw_new` of part A holds the same instruction text for its `k_write` [Ref7]. |
| 555 | `}` | Ends the function `k_write`. |

### Function `k_copy`: the NEON copy kernel (lines 557 to 604)

| Line | Source | Explanation |
|---:|---|---|
| 557 | `PLACE(copy);` | `PLACE(copy)` adds the pad `PAD_copy`, which is 32 bytes with the default values (line 190). |
| 558 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_copy`, the kernel `copy`: the NEON copy kernel. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. The whole-chip test of 2026-11-17 does not run this kernel: no `--seq` list of the test names a copy kernel [Ref4]. |
| 559 | `{` | Opens the body of `k_copy`. |
| 560 | `    uint64_t *dp = d;` | `dp`: the write position in the destination. It starts at `d`. |
| 561 | `    const uint64_t *sp = s;` | `sp`: the read position in the source. It starts at `s`. |
| 562 | `    const uint64_t *end = s + n;` | `end`: the first address after the source range: `s` plus `n` words. |
| 563 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 564 | `        uint64x2_t v0 = vld1q_u64(sp + 0);` | `vld1q_u64(sp + 0)` loads 16 B from the read position into the vector `v0`. These are the bytes 0 to 15 of the current source block of 256 B. |
| 565 | `        uint64x2_t v1 = vld1q_u64(sp + 2);` | Loads the bytes 16 to 31 of the source block into `v1`. |
| 566 | `        uint64x2_t v2 = vld1q_u64(sp + 4);` | Loads the bytes 32 to 47 of the source block into `v2`. |
| 567 | `        uint64x2_t v3 = vld1q_u64(sp + 6);` | Loads the bytes 48 to 63 of the source block into `v3`. |
| 568 | `        uint64x2_t v4 = vld1q_u64(sp + 8);` | Loads the bytes 64 to 79 of the source block into `v4`. |
| 569 | `        uint64x2_t v5 = vld1q_u64(sp + 10);` | Loads the bytes 80 to 95 of the source block into `v5`. |
| 570 | `        uint64x2_t v6 = vld1q_u64(sp + 12);` | Loads the bytes 96 to 111 of the source block into `v6`. |
| 571 | `        uint64x2_t v7 = vld1q_u64(sp + 14);` | Loads the bytes 112 to 127 of the source block into `v7`. |
| 572 | `        uint64x2_t v8 = vld1q_u64(sp + 16);` | Loads the bytes 128 to 143 of the source block into `v8`. |
| 573 | `        uint64x2_t v9 = vld1q_u64(sp + 18);` | Loads the bytes 144 to 159 of the source block into `v9`. |
| 574 | `        uint64x2_t v10 = vld1q_u64(sp + 20);` | Loads the bytes 160 to 175 of the source block into `v10`. |
| 575 | `        uint64x2_t v11 = vld1q_u64(sp + 22);` | Loads the bytes 176 to 191 of the source block into `v11`. |
| 576 | `        uint64x2_t v12 = vld1q_u64(sp + 24);` | Loads the bytes 192 to 207 of the source block into `v12`. |
| 577 | `        uint64x2_t v13 = vld1q_u64(sp + 26);` | Loads the bytes 208 to 223 of the source block into `v13`. |
| 578 | `        uint64x2_t v14 = vld1q_u64(sp + 28);` | Loads the bytes 224 to 239 of the source block into `v14`. |
| 579 | `        uint64x2_t v15 = vld1q_u64(sp + 30);` | Loads the bytes 240 to 255 of the source block into `v15`. One loop pass loads 256 B with 16 NEON loads of 16 B. |
| 580 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text, as in `k_read` (line 522). It adds no instruction. It names the 16 loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. So gcc must have all 16 loaded values in registers at this point. A comment in the benchmark source `bandwidth.c` of the folder `bench` reports the effect on the copy loop with gcc 14.2.0: with the statement the 8 `ldp` stand ahead of the 8 `stp`, and without it loads and stores alternate. |
| 581 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 580: the inputs `v4` to `v7`. |
| 582 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 580: the inputs `v8` to `v11`. |
| 583 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 580: the inputs `v12` to `v15`. The statement ends here. |
| 584 | `        vst1q_u64(dp + 0, v0);` | `vst1q_u64(dp + 0, v0)` stores the vector `v0` to the bytes 0 to 15 of the current destination block. So each loaded value is stored once and has no other use. |
| 585 | `        vst1q_u64(dp + 2, v1);` | Stores `v1` to the bytes 16 to 31 of the destination block. |
| 586 | `        vst1q_u64(dp + 4, v2);` | Stores `v2` to the bytes 32 to 47 of the destination block. |
| 587 | `        vst1q_u64(dp + 6, v3);` | Stores `v3` to the bytes 48 to 63 of the destination block. |
| 588 | `        vst1q_u64(dp + 8, v4);` | Stores `v4` to the bytes 64 to 79 of the destination block. |
| 589 | `        vst1q_u64(dp + 10, v5);` | Stores `v5` to the bytes 80 to 95 of the destination block. |
| 590 | `        vst1q_u64(dp + 12, v6);` | Stores `v6` to the bytes 96 to 111 of the destination block. |
| 591 | `        vst1q_u64(dp + 14, v7);` | Stores `v7` to the bytes 112 to 127 of the destination block. |
| 592 | `        vst1q_u64(dp + 16, v8);` | Stores `v8` to the bytes 128 to 143 of the destination block. |
| 593 | `        vst1q_u64(dp + 18, v9);` | Stores `v9` to the bytes 144 to 159 of the destination block. |
| 594 | `        vst1q_u64(dp + 20, v10);` | Stores `v10` to the bytes 160 to 175 of the destination block. |
| 595 | `        vst1q_u64(dp + 22, v11);` | Stores `v11` to the bytes 176 to 191 of the destination block. |
| 596 | `        vst1q_u64(dp + 24, v12);` | Stores `v12` to the bytes 192 to 207 of the destination block. |
| 597 | `        vst1q_u64(dp + 26, v13);` | Stores `v13` to the bytes 208 to 223 of the destination block. |
| 598 | `        vst1q_u64(dp + 28, v14);` | Stores `v14` to the bytes 224 to 239 of the destination block. |
| 599 | `        vst1q_u64(dp + 30, v15);` | Stores `v15` to the bytes 240 to 255 of the destination block. One loop pass stores 256 B with 16 NEON stores of 16 B. |
| 600 | `        sp += 32;` | Moves the read position forward by 32 words, which are 256 B. |
| 601 | `        dp += 32;` | Moves the write position forward by 32 words, which are 256 B. |
| 602 | `    } while (sp < end);` | Repeats the loop while the read position is below `end`. Machine code of `bwx12`, one loop pass: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.hi`. That is 20 instructions for 256 B loaded and 256 B stored. gcc joined each two neighbour loads into one `ldp` and each two neighbour stores into one `stp` [Ref1]. |
| 603 | `}` | Ends the function `k_copy`. |

### Macro `DEF_ASMREAD`: the hand-written read loop and its first six kernels (lines 605 to 648)

| Line | Source | Explanation |
|---:|---|---|
| 605 | `/*` | Opens the comment about the assembly kernels. |
| 606 | ` * asm kernels: the asm text of bench/bandwidth.c, inside macros so that an` | Comment: the kernels below hold the assembly text of the benchmark source `bandwidth.c` in the folder `bench`. From here to line 849 the loop of each kernel is assembly text inside an `__asm__` statement. gcc copies this text into the function. The text of three loops stands inside macros. |
| 607 | ` * A/A copy is the same source under a second name. Each iteration moves` | Comment: the reason for the macros: one more line then defines the same loop under a second name, an A/A copy. |
| 608 | ` * 256 B with 8 ldp/stp of q registers (16 B each). Callers guarantee n * 8` | Comment: one loop pass moves 256 B with 8 `ldp` or `stp` instructions. Each of them moves two `q` registers of 16 B. The read loop has 8 `ldp`. The write loop has 8 `stp`. The copy loop has 8 `ldp` and 8 `stp`. |
| 609 | ` * is a multiple of 256 and non-zero. v8-v15 are callee-saved in AAPCS64:` | Comment: the callers guarantee that the size in bytes is a multiple of 256 and is not 0. The loop tests the end only after a loop pass. `main` ends the program with status 2 when `--bytes` is 0 or is not a multiple of 256 (line 2973), and when the size of a `--seq` entry is not a multiple of 256 (line 2991). The next sentence: AAPCS64, the calling rules of Arm, say that a function must keep `v8` to `v15` for its caller. |
| 610 | ` * naming them as clobbers makes gcc save d8-d15 once per call, which is` | Comment: the `asm` statement names these registers as changed (clobbers). So gcc saves `d8` to `d15`, the low 8 bytes of these registers, once per call. |
| 611 | ` * outside the loop.` | Comment: this save is outside the loop. |
| 612 | ` *` | Comment: an empty line of the comment. |
| 613 | ` * DEF_ASMREAD(name, nops) puts "nops" nop instructions after the 8 ldp and` | Comment: the macro `DEF_ASMREAD(name, nops)` puts `nops` instructions of the kind `nop` after the 8 `ldp`. |
| 614 | ` * before the add (step B5). asmread and asmread2 have 0 of them.` | Comment: the `nop` instructions stand before the `add`. The comment links them to step B5 of the file `handoff.md`, the specification of the first runner. `asmread` and `asmread2` have 0 `nop`. |
| 615 | ` */` | Ends the comment. |
| 616 | `#define DEF_ASMREAD(name, nops) \` | Starts the macro `DEF_ASMREAD(name, nops)`. It defines one kernel function with a hand-written read loop. The backslash at the end of each line continues the macro on the next line. Three kernels of the whole-chip test come from this macro: `asmread` (line 642), `read_nop96` (line 1063) and `read_nop256` (line 1199) [Ref4]. |
| 617 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function. For the three kernels of the whole-chip test the pad is 0 bytes (line 214, line 1057 and line 1135). So each of these functions starts at a multiple of 64 bytes [Ref1]. |
| 618 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the first macro argument: `DEF_ASMREAD(asmread, 0)` defines the function `k_asmread`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. `noinline` forbids gcc to merge the function into its caller. So the listing of the CRB build shows each kernel as a function of its own [Ref1]. |
| 619 | `    { \` | Opens the body of the kernel function. |
| 620 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 621 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx12`: `add x1, x0, x1, lsl #3`, which adds 8 times `x1` to `x0` and puts the result into `x1`. It runs once per call, before the loop [Ref1]. |
| 622 | `        __asm__ volatile( \` | Starts a gcc statement that holds assembly text. gcc copies the text into the function. `volatile` tells gcc to keep the statement, although no later code uses `p`. The listing of `bwx12` shows the instructions in the order of the text [Ref1]. |
| 623 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. `\n\t` ends one line of the assembly text and indents the next one. In the CRB binary of `bwx12` the loops of `k_asmread`, `k_read_nop96` and `k_read_nop256` start at an address of 20 modulo 64 [Ref1]. |
| 624 | `            "ldp q0, q1, [%[p]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 15 of the current block of 256 B into `q0` and the bytes 16 to 31 into `q1`. `%[p]` stands for the register that gcc chose for `p`. In the listing of `bwx12` it is `x0` [Ref1]. |
| 625 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 626 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 627 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. With this instruction the bytes 0 to 127 of the block are loaded. |
| 628 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 629 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 630 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 631 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once, in rising address order. Nothing uses the loaded values: no instruction of the loop takes `q0` to `q15` as an input, and the next loop pass overwrites the registers. The old read kernel `k_oldread` (line 474) differs in this point. Its loop adds every loaded register to a sum: 8 vector adds per 128 B [Ref1]. The unrolling is part of this text: 8 `ldp` per loop pass. gcc does not change the instructions of assembly text. It only puts register names in the places of `%[p]` and `%[end]`. |
| 632 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the second macro argument into text. For `read_nop96` the assembler sees the three lines `.rept 96`, `nop` and `.endr`. `.rept N` and `.endr` are assembler directives: the assembler repeats the lines between them N times. With `.rept 0` it writes nothing. Result in the listing of `bwx12`, between the last `ldp` and the `add`: 0 `nop` in `k_asmread`, 96 in `k_read_nop96` and 256 in `k_read_nop256` [Ref1]. A `nop` does nothing and loads nothing. So every loop pass still reads 256 B, and only the instruction count of the loop pass grows. |
| 633 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the read pointer forward by 256 B. Machine code of `bwx12`: `add x0, x0, #0x100` [Ref1]. |
| 634 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the read pointer with `end` and sets the condition flags. Machine code of `bwx12`: `cmp x0, x1` [Ref1]. |
| 635 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. `lo` means lower in an unsigned compare. The end test stands after the loop body. So the body runs at least once in every call. The listing of `bwx12` prints `b.cc` for this branch and names `b.lo` as another name of it. Instructions of one loop pass: 8 `ldp`, the `nop` instructions and these 3. That is 11 per 256 B in `asmread`, 107 in `read_nop96` and 267 in `read_nop256` [Ref1]. |
| 636 | `            : [p] "+r"(p) \` | Tells gcc which C variables the text uses. `[p] "+r"(p)`: `p` is in a general register, and the text reads it and changes it. |
| 637 | `            : [end] "r"(end) \` | `[end] "r"(end)`: `end` is an input in a general register. In the listing of `bwx12` it is `x1` [Ref1]. |
| 638 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list. It tells gcc what the text changes besides `p`. This line names the vector registers `v0` to `v7`. |
| 639 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` on the stack before the loop (4 `stp` instructions) and loads them back after it (4 `ldp` instructions) [Ref1]. This save runs once per call of the kernel, not once per loop pass. In a timed interval of the whole-chip test one call covers one chunk of 2 MiB (line 1695) [Ref4]. That is 8192 loop passes. |
| 640 | `              "memory", "cc"); \` | Ends the clobber list and the statement. `"memory"` says that the text accesses memory that no operand names. `"cc"` says that the text changes the condition flags. |
| 641 | `    }` | Ends the kernel function and the macro. In `bwx12` the function `k_asmread` has 21 instructions: 5 before the loop, 11 in the loop and 5 after it, with `ret` as the last one [Ref1]. |
| 642 | `DEF_ASMREAD(asmread, 0)` | Defines `k_asmread`, the kernel `asmread`: the macro loop with 0 `nop`. One loop pass has 8 `ldp` loads of 32 B, `add`, `cmp` and the branch: 11 instructions per 256 B [Ref1]. The whole-chip test runs it at position 1 in part L and control I, and in part C at position 2 (`cfwd.spec`) or position 0 (`crev.spec`) [Ref4]. The worker calls it through the function `call` (line 1491). Before each interval of this kernel one call covers the whole range of the `--seq` entry, which is the whole buffer in the test: the warm-up pass (line 1669). In a timed interval of the test one call covers one chunk of 2 MiB (line 1695). Its instruction text equals the text of `k_asmread` in `bw_new`, one of the two binaries of part A [Ref7]. `k_read` (line 501), the new read kernel, has the same 8 `ldp` loads and the same 11 instructions per 256 B. The two functions differ in four points [Ref1]. Registers: `q0` to `q15` here, `q31` to `q16` in `k_read`. Save of `d8` to `d15`, outside the loop: only here. Loop start: 20 modulo 64 here, 36 in `k_read`. End test: `cmp x0, x1` with `b.cc` here, `cmp x1, x0` with `b.hi` in `k_read`. Both end tests branch back while the pointer is below `end`. |
| 643 | `DEF_ASMREAD(asmread2, 0)` | Defines `k_asmread2`, the A/A copy of `asmread`. The listing of the CRB build shows the same instruction text for both [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 644 | `DEF_ASMREAD(read_nop4, 4)` | Defines `k_read_nop4`: the `asmread` loop with 4 `nop` per loop pass. That is 15 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 645 | `DEF_ASMREAD(read_nop8, 8)` | Defines `k_read_nop8`: the `asmread` loop with 8 `nop` per loop pass. That is 19 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 646 | `DEF_ASMREAD(read_nop16, 16)` | Defines `k_read_nop16`: the `asmread` loop with 16 `nop` per loop pass. That is 27 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 647 | `DEF_ASMREAD(read_nop32, 32)` | Defines `k_read_nop32`: the `asmread` loop with 32 `nop` per loop pass. That is 43 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |

### Function `k_read_sparse`: 128 B per loop pass, 4 loads and 9 `nop` (lines 649 to 670)

| Line | Source | Explanation |
|---:|---|---|
| 649 | `/* Step B5. Per 128 B: 4 ldp, 9 nop, add, cmp, b.lo. That is 16 instructions` | Comment: the kernel below belongs to step B5 of the file `handoff.md`, the specification of the first runner. Per 128 B it has 4 `ldp`, 9 `nop`, `add`, `cmp` and `b.lo`. That is 16 instructions. |
| 650 | ` * per 128 B, as the old read loop has, and no vector add. */` | Comment: the old read loop also has 16 instructions per 128 B. This kernel has the same instruction count, and it has no vector add. |
| 651 | `PLACE(read_sparse);` | `PLACE` adds the pad of the kernel `read_sparse`. It is the pad of `asmread`, 0 bytes (line 250). |
| 652 | `__attribute__((noinline)) static void k_read_sparse(const uint64_t *a, size_t n)` | Starts the function `k_read_sparse`, the kernel `read_sparse`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 653 | `{` | Opens the body of `k_read_sparse`. |
| 654 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 655 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. |
| 656 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text of the loop. |
| 657 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loop starts 4 bytes after the function start, at an address of 4 modulo 64 [Ref1]. |
| 658 | `        "ldp q0, q1, [%[p]]\n\t"` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current block of 128 B into `q0` and `q1`. |
| 659 | `        "ldp q2, q3, [%[p], #32]\n\t"` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 660 | `        "ldp q4, q5, [%[p], #64]\n\t"` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 661 | `        "ldp q6, q7, [%[p], #96]\n\t"` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. One loop pass has 4 load instructions. It reads 128 B, each byte once. Nothing uses the loaded values. |
| 662 | `        ".rept 9\n\tnop\n\t.endr\n\t"` | The assembler writes the instruction `nop` 9 times here. A `nop` does nothing. |
| 663 | `        "add %[p], %[p], #128\n\t"` | Moves the read pointer forward by 128 B. |
| 664 | `        "cmp %[p], %[end]\n\t"` | Compares the read pointer with `end`. |
| 665 | `        "b.lo 1b\n\t"` | Branches back to the label `1` while the pointer is below `end`. One loop pass is 16 instructions per 128 B: 4 `ldp`, 9 `nop`, `add`, `cmp` and the branch. The listing of `bwx12` shows them [Ref1]. |
| 666 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 667 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 668 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc");` | The clobber list: the vector registers `v0` to `v7`, memory and the condition flags. It names none of `v8` to `v15`. So gcc saves no register in this function. The listing of `bwx12` shows one `add` before the loop and one `ret` after it [Ref1]. |
| 669 | `}` | Ends the function `k_read_sparse`. |

### Macro `DEF_ASMWRITE`: the hand-written write loop, kernels `asmwrite` and `asmwrite2` (lines 671 to 697)

| Line | Source | Explanation |
|---:|---|---|
| 671 | `#define DEF_ASMWRITE(name) \` | Starts the macro `DEF_ASMWRITE(name)`. It defines one kernel function with a hand-written write loop. The backslash at the end of each line continues the macro on the next line. |
| 672 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 163). |
| 673 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. |
| 674 | `    { \` | Opens the body of the kernel function. |
| 675 | `        uint64_t *p = a; \` | `p`: the write pointer. It starts at `a`. |
| 676 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 677 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. gcc copies the text into the function. |
| 678 | `            "dup v0.2d, %[v]\n\t" \` | `dup` copies the 8-byte value `v` into both halves of the 16-byte vector register `v0`. It stands before the loop label, so it runs once per call. `%[v]` stands for the register that gcc chose for `v`. |
| 679 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loop of `k_asmwrite` starts at an address of 40 modulo 64 [Ref1]. |
| 680 | `            "stp q0, q0, [%[p]]\n\t" \` | `stp` stores two 16-byte vector registers to memory, which is 32 B. Here both are `q0`. This instruction writes the bytes 0 to 31 of the current block of 256 B. `%[p]` stands for the register of the write pointer `p`. |
| 681 | `            "stp q0, q0, [%[p], #32]\n\t" \` | Stores `q0` twice to the bytes 32 to 63 of the block. |
| 682 | `            "stp q0, q0, [%[p], #64]\n\t" \` | Stores `q0` twice to the bytes 64 to 95 of the block. |
| 683 | `            "stp q0, q0, [%[p], #96]\n\t" \` | Stores `q0` twice to the bytes 96 to 127 of the block. |
| 684 | `            "stp q0, q0, [%[p], #128]\n\t" \` | Stores `q0` twice to the bytes 128 to 159 of the block. |
| 685 | `            "stp q0, q0, [%[p], #160]\n\t" \` | Stores `q0` twice to the bytes 160 to 191 of the block. |
| 686 | `            "stp q0, q0, [%[p], #192]\n\t" \` | Stores `q0` twice to the bytes 192 to 223 of the block. |
| 687 | `            "stp q0, q0, [%[p], #224]\n\t" \` | Stores `q0` twice to the bytes 224 to 255 of the block. One loop pass has 8 store instructions. It writes 256 B, each byte once, in rising address order. The unrolling is part of this text: 8 `stp` per loop pass. |
| 688 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the write pointer forward by 256 B. |
| 689 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the write pointer with `end`. |
| 690 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 691 | `            : [p] "+r"(p) \` | `[p] "+r"(p)`: `p` is in a general register. The text reads it and changes it. |
| 692 | `            : [end] "r"(end), [v] "r"(v) \` | `end` and `v` are inputs in general registers. |
| 693 | `            : "v0", "memory", "cc"); \` | The clobber list: the text changes the vector register `v0`, memory and the condition flags. The calling rules do not require a function to keep `v0`. So gcc saves no register in this function. |
| 694 | `    }` | Ends the kernel function and the macro. |
| 695 | `DEF_ASMWRITE(asmwrite)` | Defines `k_asmwrite`, the kernel `asmwrite`. Machine code in `bwx12`: one loop pass is 11 instructions for 256 B: 8 `stp`, `add x0, x0, #0x100`, `cmp x0, x1` and `b.cc`. Before the loop stand the `add` that computes the end address and the `dup`. After it stands `ret` [Ref1]. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. The first touch uses `k_write` (line 531), not this loop. |
| 696 | `DEF_ASMWRITE(asmwrite2)` | Defines `k_asmwrite2`, the A/A copy of `asmwrite`. The listing of the CRB build shows the same instruction text for both [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |

### Macro `DEF_ASMCOPY`: the hand-written copy loop, kernels `asmcopy` and `asmcopy2` (lines 698 to 735)

| Line | Source | Explanation |
|---:|---|---|
| 698 | `#define DEF_ASMCOPY(name) \` | Starts the macro `DEF_ASMCOPY(name)`. It defines one kernel function with a hand-written copy loop. |
| 699 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 163). |
| 700 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. `noinline`: gcc must keep the function separate from its caller. |
| 701 | `    { \` | Opens the body of the kernel function. |
| 702 | `        uint64_t *dp = d; \` | `dp`: the write pointer in the destination. It starts at `d`. |
| 703 | `        const uint64_t *sp = s; \` | `sp`: the read pointer in the source. It starts at `s`. |
| 704 | `        const uint64_t *end = s + n; \` | `end`: the first address after the source range: `s` plus `n` words. |
| 705 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 706 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loop of `k_asmcopy` starts at an address of 52 modulo 64 [Ref1]. |
| 707 | `            "ldp q0, q1, [%[s]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. `%[s]` stands for the register of the read pointer `sp`. |
| 708 | `            "ldp q2, q3, [%[s], #32]\n\t" \` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 709 | `            "ldp q4, q5, [%[s], #64]\n\t" \` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 710 | `            "ldp q6, q7, [%[s], #96]\n\t" \` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 711 | `            "ldp q8, q9, [%[s], #128]\n\t" \` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 712 | `            "ldp q10, q11, [%[s], #160]\n\t" \` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 713 | `            "ldp q12, q13, [%[s], #192]\n\t" \` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 714 | `            "ldp q14, q15, [%[s], #224]\n\t" \` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 load instructions for 256 B. |
| 715 | `            "stp q0, q1, [%[d]]\n\t" \` | `stp` stores two 16-byte vector registers to memory: `q0` and `q1` to the bytes 0 to 31 of the current destination block. `%[d]` stands for the register of the write pointer `dp`. Each loaded register is stored once and has no other use. |
| 716 | `            "stp q2, q3, [%[d], #32]\n\t" \` | Stores `q2` and `q3` to the bytes 32 to 63 of the destination block. |
| 717 | `            "stp q4, q5, [%[d], #64]\n\t" \` | Stores `q4` and `q5` to the bytes 64 to 95 of the destination block. |
| 718 | `            "stp q6, q7, [%[d], #96]\n\t" \` | Stores `q6` and `q7` to the bytes 96 to 127 of the destination block. |
| 719 | `            "stp q8, q9, [%[d], #128]\n\t" \` | Stores `q8` and `q9` to the bytes 128 to 159 of the destination block. |
| 720 | `            "stp q10, q11, [%[d], #160]\n\t" \` | Stores `q10` and `q11` to the bytes 160 to 191 of the destination block. |
| 721 | `            "stp q12, q13, [%[d], #192]\n\t" \` | Stores `q12` and `q13` to the bytes 192 to 223 of the destination block. |
| 722 | `            "stp q14, q15, [%[d], #224]\n\t" \` | Stores `q14` and `q15` to the bytes 224 to 255 of the destination block. One loop pass has 8 store instructions for 256 B. The unrolling is part of this text: 8 `ldp` and 8 `stp` per loop pass. |
| 723 | `            "add %[s], %[s], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 724 | `            "add %[d], %[d], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 725 | `            "cmp %[s], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 726 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the read pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 727 | `            : [s] "+r"(sp), [d] "+r"(dp) \` | `sp` and `dp` are in general registers. The text reads them and changes them. |
| 728 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 729 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 730 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop, as in the read loop of line 639. |
| 731 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 732 | `    }` | Ends the kernel function and the macro. |
| 733 | `DEF_ASMCOPY(asmcopy)` | Defines `k_asmcopy`, the kernel `asmcopy`. Machine code in `bwx12`: one loop pass is 20 instructions for 256 B loaded and 256 B stored: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.cc`. The function saves `d8` to `d15` before the loop and loads them back after it [Ref1]. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 734 | `DEF_ASMCOPY(asmcopy2)` | Defines `k_asmcopy2`, the A/A copy of `asmcopy`. The listing of the CRB build shows the same instruction text for both [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |

### Function `k_asmcopy_c`: the machine code of the C copy loop as assembly text (lines 736 to 776)

| Line | Source | Explanation |
|---:|---|---|
| 736 | `/*` | Opens the comment about the kernel `asmcopy_c`. |
| 737 | ` * Step B2. asmcopy_c: the loop is the machine code of the C copy loop, from` | Comment: the kernel belongs to step B2 of the file `handoff.md`, the specification of the first runner. Its loop is the machine code of the C copy loop, written as assembly text. |
| 738 | ` * the listing "bw_new k_copy" of probe.txt: same instruction order, same` | Comment: the machine code comes from the listing `bw_new k_copy` of the file `probe.txt` [Ref7]. The loop has the same order of instructions. |
| 739 | ` * offsets, registers q16 to q31, and "cmp end, s; b.hi" as its loop end. The` | Comment: it also has the same offsets and the same registers `q16` to `q31`. Its loop end is `cmp end, s` followed by `b.hi`. |
| 740 | ` * three pointers are bound to x0, x1 and x2, the registers of that listing.` | Comment: the three pointers are bound to the registers `x0`, `x1` and `x2`, the registers of that listing. In the listing of `bwx12` the functions `k_asmcopy_c` and `k_copy` have the same instruction text [Ref1]. |
| 741 | ` */` | Ends the comment. |
| 742 | `PLACE(asmcopy_c);` | `PLACE` adds the pad `PAD_asmcopy_c`, which is 48 bytes with the default values (line 199). |
| 743 | `__attribute__((noinline)) static void k_asmcopy_c(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c`, the kernel `asmcopy_c`. It copies `n` 8-byte words from `s` to `d`. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 744 | `{` | Opens the body of `k_asmcopy_c`. |
| 745 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer. `register ... __asm__("x0")` binds this C variable to the register `x0` for the `asm` statement below. |
| 746 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 747 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 748 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 749 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loop starts 4 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 750 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 751 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 752 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 753 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 754 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 755 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 756 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 757 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 758 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. In this kernel the `add` stands before the stores. |
| 759 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 760 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 761 | `        "stp q29, q28, [%[d], #-224]\n\t"` | Stores `q29` and `q28` at the offset -224 from the moved write pointer. These are the bytes 32 to 63 of the destination block. |
| 762 | `        "stp q27, q26, [%[d], #-192]\n\t"` | Stores `q27` and `q26` at the offset -192: the bytes 64 to 95 of the destination block. |
| 763 | `        "stp q25, q24, [%[d], #-160]\n\t"` | Stores `q25` and `q24` at the offset -160: the bytes 96 to 127 of the destination block. |
| 764 | `        "stp q23, q22, [%[d], #-128]\n\t"` | Stores `q23` and `q22` at the offset -128: the bytes 128 to 159 of the destination block. |
| 765 | `        "stp q21, q20, [%[d], #-96]\n\t"` | Stores `q21` and `q20` at the offset -96: the bytes 160 to 191 of the destination block. |
| 766 | `        "stp q19, q18, [%[d], #-64]\n\t"` | Stores `q19` and `q18` at the offset -64: the bytes 192 to 223 of the destination block. |
| 767 | `        "stp q17, q16, [%[d], #-32]\n\t"` | Stores `q17` and `q16` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 768 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 769 | `        "b.hi 1b\n\t"` | `b.hi 1b` branches back to the label `1` while `end` is higher than the read pointer, as unsigned numbers. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 770 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 771 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 772 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 773 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. The calling rules do not require a function to keep `v16` to `v31`. So gcc saves no register in this function. |
| 774 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 775 | `}` | Ends the function `k_asmcopy_c`. |

### Function `k_asmcopy_c_add`: the same loop with both `add` after the stores (lines 777 to 813)

| Line | Source | Explanation |
|---:|---|---|
| 777 | `/* As asmcopy_c, but the two add stand after the 8 stp, and the 8 stp use the` | Comment: the kernel below is `asmcopy_c` with two changes. The two `add` instructions stand after the 8 `stp`. |
| 778 | ` * offsets 0 to 224, as in asmcopy. Registers stay q16 to q31. */` | Comment: the 8 `stp` use the offsets 0 to 224, as in `asmcopy`. The registers stay `q16` to `q31`. |
| 779 | `PLACE(asmcopy_c_add);` | `PLACE` adds the pad `PAD_asmcopy_c_add`, which is 48 bytes with the default values (line 202). |
| 780 | `__attribute__((noinline)) static void k_asmcopy_c_add(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_add`, the kernel `asmcopy_c_add`. It copies `n` 8-byte words from `s` to `d`. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 781 | `{` | Opens the body of `k_asmcopy_c_add`. |
| 782 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 783 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 784 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 785 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 786 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loop starts at an address of 52 modulo 64 [Ref1]. |
| 787 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 788 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 789 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 790 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 791 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 792 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 793 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 794 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 795 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 796 | `        "stp q29, q28, [%[d], #32]\n\t"` | Stores `q29` and `q28` to the bytes 32 to 63 of the destination block. |
| 797 | `        "stp q27, q26, [%[d], #64]\n\t"` | Stores `q27` and `q26` to the bytes 64 to 95 of the destination block. |
| 798 | `        "stp q25, q24, [%[d], #96]\n\t"` | Stores `q25` and `q24` to the bytes 96 to 127 of the destination block. |
| 799 | `        "stp q23, q22, [%[d], #128]\n\t"` | Stores `q23` and `q22` to the bytes 128 to 159 of the destination block. |
| 800 | `        "stp q21, q20, [%[d], #160]\n\t"` | Stores `q21` and `q20` to the bytes 160 to 191 of the destination block. |
| 801 | `        "stp q19, q18, [%[d], #192]\n\t"` | Stores `q19` and `q18` to the bytes 192 to 223 of the destination block. |
| 802 | `        "stp q17, q16, [%[d], #224]\n\t"` | Stores `q17` and `q16` to the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 803 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. Here both `add` instructions stand after the stores. |
| 804 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. |
| 805 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 806 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 807 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 808 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 809 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 810 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. gcc saves no register for them. |
| 811 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 812 | `}` | Ends the function `k_asmcopy_c_add`. |

### Function `k_asmcopy_c_reg`: the same loop with the registers `q0` to `q15` (lines 814 to 850)

| Line | Source | Explanation |
|---:|---|---|
| 814 | `/* As asmcopy_c, but with the registers q0 to q15 (q31 becomes q0, q30` | Comment: the kernel below is `asmcopy_c` with other registers: `q0` to `q15`. The register `q31` of `asmcopy_c` becomes `q0` here. |
| 815 | ` * becomes q1, and so on), and d8 to d15 named as clobbered, as in asmcopy. */` | Comment: `q30` becomes `q1`, and so on. The clobber list names `v8` to `v15`, as in `asmcopy`. So gcc saves `d8` to `d15`. |
| 816 | `PLACE(asmcopy_c_reg);` | `PLACE` adds the pad `PAD_asmcopy_c_reg`, which is 32 bytes with the default values (line 205). |
| 817 | `__attribute__((noinline)) static void k_asmcopy_c_reg(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_reg`, the kernel `asmcopy_c_reg`. It copies `n` 8-byte words from `s` to `d`. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 818 | `{` | Opens the body of `k_asmcopy_c_reg`. |
| 819 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 820 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 821 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 822 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 823 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loop starts 20 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 824 | `        "ldp q0, q1, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. |
| 825 | `        "ldp q2, q3, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 826 | `        "ldp q4, q5, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 827 | `        "ldp q6, q7, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 828 | `        "ldp q8, q9, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 829 | `        "ldp q10, q11, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 830 | `        "ldp q12, q13, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 831 | `        "ldp q14, q15, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 `ldp` for 256 B. |
| 832 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B, before the stores. |
| 833 | `        "stp q0, q1, [%[d]]\n\t"` | Stores `q0` and `q1` to the bytes 0 to 31 of the current destination block. |
| 834 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 835 | `        "stp q2, q3, [%[d], #-224]\n\t"` | Stores `q2` and `q3` at the offset -224 from the moved write pointer: the bytes 32 to 63 of the destination block. |
| 836 | `        "stp q4, q5, [%[d], #-192]\n\t"` | Stores `q4` and `q5` at the offset -192: the bytes 64 to 95 of the destination block. |
| 837 | `        "stp q6, q7, [%[d], #-160]\n\t"` | Stores `q6` and `q7` at the offset -160: the bytes 96 to 127 of the destination block. |
| 838 | `        "stp q8, q9, [%[d], #-128]\n\t"` | Stores `q8` and `q9` at the offset -128: the bytes 128 to 159 of the destination block. |
| 839 | `        "stp q10, q11, [%[d], #-96]\n\t"` | Stores `q10` and `q11` at the offset -96: the bytes 160 to 191 of the destination block. |
| 840 | `        "stp q12, q13, [%[d], #-64]\n\t"` | Stores `q12` and `q13` at the offset -64: the bytes 192 to 223 of the destination block. |
| 841 | `        "stp q14, q15, [%[d], #-32]\n\t"` | Stores `q14` and `q15` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 842 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 843 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 844 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 845 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 846 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 847 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call: the listing of `bwx12` shows 4 `stp` before the loop and 4 `ldp` after it [Ref1]. |
| 848 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 849 | `}` | Ends the function `k_asmcopy_c_reg`. |

### Stand-ins for a machine that is not AArch64 (lines 851 to 897)

| Line | Source | Explanation |
|---:|---|---|
| 851 | `#else` | `#else` of the `#if defined(__aarch64__)` of line 491. The compiler reads lines 852 to 896 only for a machine that is not AArch64. The CRB binary of `bwx12` does not hold this code: the header of every csv file of the whole-chip test says `kernels=aarch64` [Ref5]. The program prints this word when `STANDIN` is 0 (line 3024). |
| 852 | `/*` | Opens the comment about the stand-ins. |
| 853 | ` * Stand-ins for a machine that is not AArch64: plain C loops that touch` | Comment: the stand-ins are for a machine that is not AArch64. They are plain C loops. |
| 854 | ` * exactly the same bytes as the real kernels. They exist only so that the` | Comment: each stand-in touches exactly the same bytes as the real kernel. The stand-ins have one purpose only. |
| 855 | ` * harness can be compiled and run on the development machine.` | Comment: the purpose: the program can be compiled and run on the development machine. |
| 856 | ` */` | Ends the comment. |
| 857 | `#define STANDIN 1` | `STANDIN` is 1 in this branch. It is 0 in the AArch64 branch (line 492). The header of the output then says that the kernels are stand-ins and that the rates mean nothing (line 3024). |
| 858 | `#define DEF_ASMREAD(name, nops) \` | Starts the stand-in form of the macro `DEF_ASMREAD(name, nops)`. It has the name and the arguments of the AArch64 macro of line 616, with a plain C loop over the same range. A build on CRB, an Arm machine, does not compile this branch. |
| 859 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel, as in the AArch64 branch. |
| 860 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range and `n` its length in 8-byte words. |
| 861 | `    { \` | Opens the body of the kernel function. |
| 862 | `        const volatile uint64_t *p = a; \` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 863 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 864 | `            (void)p[i]; \` | Reads word `i` and drops the value. The cast to `void` says that the value is not used. So the loop reads every word of the range once. The macro argument `nops` is not used in this branch. |
| 865 | `    }` | Ends the kernel function and the macro. |
| 866 | `#define DEF_ASMWRITE(name) \` | Starts the stand-in form of the macro `DEF_ASMWRITE(name)`, with a plain C loop. |
| 867 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 868 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores `v` to `n` 8-byte words, from the address `a` on. |
| 869 | `    { \` | Opens the body of the kernel function. |
| 870 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 871 | `            a[i] = v; \` | Stores `v` to word `i`. |
| 872 | `    }` | Ends the kernel function and the macro. |
| 873 | `#define DEF_ASMCOPY(name) \` | Starts the stand-in form of the macro `DEF_ASMCOPY(name)`, with a plain C loop. |
| 874 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 875 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. |
| 876 | `    { \` | Opens the body of the kernel function. |
| 877 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 878 | `            d[i] = s[i]; \` | Copies word `i` from the source to the destination. |
| 879 | `    }` | Ends the kernel function and the macro. |
| 880 | `DEF_ASMREAD(read, 0)` | Stand-in build only: defines `k_read` as the plain read loop of lines 858 to 865. This line and the 16 lines below define all 17 kernels of lines 500 to 849 from the three stand-in macros. |
| 881 | `DEF_ASMWRITE(write)` | Stand-in build only: defines `k_write` as the plain write loop of lines 866 to 872. In such a build this function also does the first touch (line 1646). |
| 882 | `DEF_ASMCOPY(copy)` | Stand-in build only: defines `k_copy` as the plain copy loop of lines 873 to 879. |
| 883 | `DEF_ASMREAD(asmread, 0)` | Stand-in build only: defines `k_asmread` as the plain read loop. |
| 884 | `DEF_ASMREAD(asmread2, 0)` | Stand-in build only: defines `k_asmread2` as the plain read loop. |
| 885 | `DEF_ASMREAD(read_nop4, 4)` | Stand-in build only: defines `k_read_nop4` as the plain read loop. The stand-in macro does not use the number 4. |
| 886 | `DEF_ASMREAD(read_nop8, 8)` | Stand-in build only: defines `k_read_nop8` as the plain read loop. The number 8 is not used. |
| 887 | `DEF_ASMREAD(read_nop16, 16)` | Stand-in build only: defines `k_read_nop16` as the plain read loop. The number 16 is not used. |
| 888 | `DEF_ASMREAD(read_nop32, 32)` | Stand-in build only: defines `k_read_nop32` as the plain read loop. The number 32 is not used. |
| 889 | `DEF_ASMREAD(read_sparse, 9)` | Stand-in build only: defines `k_read_sparse` as the plain read loop. The number 9 is not used. The real kernel also reads every byte of its range. |
| 890 | `DEF_ASMWRITE(asmwrite)` | Stand-in build only: defines `k_asmwrite` as the plain write loop. |
| 891 | `DEF_ASMWRITE(asmwrite2)` | Stand-in build only: defines `k_asmwrite2` as the plain write loop. |
| 892 | `DEF_ASMCOPY(asmcopy)` | Stand-in build only: defines `k_asmcopy` as the plain copy loop. |
| 893 | `DEF_ASMCOPY(asmcopy2)` | Stand-in build only: defines `k_asmcopy2` as the plain copy loop. |
| 894 | `DEF_ASMCOPY(asmcopy_c)` | Stand-in build only: defines `k_asmcopy_c` as the plain copy loop. |
| 895 | `DEF_ASMCOPY(asmcopy_c_add)` | Stand-in build only: defines `k_asmcopy_c_add` as the plain copy loop. |
| 896 | `DEF_ASMCOPY(asmcopy_c_reg)` | Stand-in build only: defines `k_asmcopy_c_reg` as the plain copy loop. |
| 897 | `#endif` | Ends the `#if` of line 491. |

### Kernels of round 3 (version `bwx10`): the comment and the pads (lines 898 to 930)

| Line | Source | Explanation |
|---:|---|---|
| 898 | `/* bwx10+ */` | Comment: a marker. A block of text that the version `bwx10` added starts here. The marker of line 1040 ends the block. |
| 900 | `/*` | Opens the comment about the kernels of round 3. |
| 901 | ` * Kernels of round 3. They stand after every kernel of bwx8, so those keep` | Comment: the kernels below are those of round 3, a round of work on the program (line 62). It is not a round of the option `--rounds`. They stand after every kernel of `bwx8`. |
| 902 | ` * their place. Each one is a read kernel (T_READ) with the loop start at 20` | Comment: so the kernels of `bwx8` keep their place in the binary. Each new kernel is a read kernel, with the type `T_READ`. Its loop must start at 20 modulo 64. |
| 903 | ` * modulo 64, the loop offset of asmread in the accepted build.` | Comment: 20 modulo 64 is the loop offset of `asmread` in the accepted build. The accepted build is the CRB build whose machine-code listing passed the check script. |
| 904 | ` *` | Comment: an empty line of the comment. |
| 905 | ` * read_pf256, read_pf512, read_pf1024, read_pf2048 have the frame of asmread` | Comment: the kernels `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048` (lines 979 to 982) have the frame of `asmread`. The frame is the code at the start of a function that saves registers. |
| 906 | ` * (d8-d15 are saved), so HEAD is 20 and the pad is the pad of asmread.` | Comment: in that frame `d8` to `d15` are saved. So `HEAD`, the number of bytes of code before the loop, is 20, and these kernels take the pad of `asmread`. |
| 907 | ` * read_1pl names v0-v3 only, so gcc saves nothing: HEAD is 4, as read_sparse` | Comment: `read_1pl` names only `v0` to `v3` as changed. So gcc saves nothing. `HEAD` is then 4, as for `read_sparse`. |
| 908 | ` * has it. HEAD_read_1pl is a guess until the listing of the CRB build` | Comment: `HEAD_read_1pl` is a guess until the listing of the CRB build confirms it. The listing of the CRB build of `bwx12` confirms it: 4 bytes of code stand before the loop of `k_read_1pl` [Ref1]. |
| 909 | ` * confirms it (check_listing10.py checks the loop offset).` | Comment: the script `check_listing10.py` in the code folder `bwx10-2026-11-15` checks the loop offset. |
| 910 | ` */` | Ends the comment. |
| 911 | `#ifndef PAD_read_pf256` | Compiles line 912 only when the build command has not defined `PAD_read_pf256`. A `-D` option of the compiler could give another value. The CRB build of `bwx12` has no `-D` option [Ref2]. |
| 912 | `#define PAD_read_pf256 PAD_asmread` | `PAD_read_pf256`: the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_pf256` [Ref4]. |
| 913 | `#endif` | Ends the `#ifndef` of line 911. |
| 914 | `#ifndef PAD_read_pf512` | Compiles line 915 only when the build command has not defined `PAD_read_pf512`. |
| 915 | `#define PAD_read_pf512 PAD_asmread` | `PAD_read_pf512`: the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_pf512` [Ref4]. |
| 916 | `#endif` | Ends the `#ifndef` of line 914. |
| 917 | `#ifndef PAD_read_pf1024` | Compiles line 918 only when the build command has not defined `PAD_read_pf1024`. |
| 918 | `#define PAD_read_pf1024 PAD_asmread` | `PAD_read_pf1024`: the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_pf1024` [Ref4]. |
| 919 | `#endif` | Ends the `#ifndef` of line 917. |
| 920 | `#ifndef PAD_read_pf2048` | Compiles line 921 only when the build command has not defined `PAD_read_pf2048`. |
| 921 | `#define PAD_read_pf2048 PAD_asmread` | `PAD_read_pf2048`: the pad of `asmread`, which is 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_pf2048` [Ref4]. |
| 922 | `#endif` | Ends the `#ifndef` of line 920. |
| 923 | `#define LOOP_read_1pl 20` | `LOOP_read_1pl` is 20: the planned address of the loop start of `read_1pl`, modulo 64. |
| 924 | `#ifndef HEAD_read_1pl` | Compiles line 925 only when the build command has not defined `HEAD_read_1pl`. |
| 925 | `#define HEAD_read_1pl 4` | `HEAD_read_1pl` is 4: the number of bytes between the function start and the loop start. That is one instruction of 4 bytes. Listing of the CRB build of `bwx12`: `k_read_1pl` starts at `0x55d0`, which is 16 modulo 64. Its loop starts at `0x55d4`, which is 20 modulo 64 [Ref1]. |
| 926 | `#endif` | Ends the `#ifndef` of line 924. |
| 927 | `#ifndef PAD_read_1pl` | Compiles line 928 only when the build command has not defined `PAD_read_1pl`. |
| 928 | `#define PAD_read_1pl PADOF(LOOP_read_1pl, HEAD_read_1pl)` | `PAD_read_1pl` is `PADOF(20, 4)` with the default values. `PADOF` (line 164) computes (20 - 4) modulo 64, which is 16. `PLACE(read_1pl)` (line 987) uses this pad. So the function starts at 16 modulo 64 and its loop at 20 modulo 64. In the CRB binary of `bwx12` the kernel `read_1pl` has the same loop offset as `asmread`, `read_nop96` and `read_nop256`: 20 [Ref1]. |
| 929 | `#endif` | Ends the `#ifndef` of line 927. |

### Macro `DEF_READ_PF`: the `asmread` loop with four prefetch instructions (lines 931 to 983)

| Line | Source | Explanation |
|---:|---|---|
| 931 | `#if defined(__aarch64__)` | Opens a second block of AArch64 kernels. Its `#else` is at line 1005 and its `#endif` at line 1022. The CRB binary of `bwx12` holds this first branch: the listing shows the `prfm` and `ldr` instructions of its kernels [Ref1]. |
| 932 | `/*` | Opens the comment about the macro `DEF_READ_PF`. |
| 933 | ` * DEF_READ_PF(name, d0, d1, d2, d3): the loop of asmread (8 ldp of q` | Comment: `DEF_READ_PF(name, d0, d1, d2, d3)` defines a kernel with the loop of `asmread`: 8 `ldp` of `q` registers per 256 B. |
| 934 | ` * registers per 256 B, same registers, same clobbers) plus four software` | Comment: the loop has the same registers and the same clobber list as `asmread`. The macro adds four software prefetches. |
| 935 | ` * prefetches per iteration, one per 64 B line, after the 8 ldp and before the` | Comment: the four prefetches run once per loop pass, one per 64 B line. A 64 B line here is a block of 64 B of memory, a cache line. They stand after the 8 `ldp` and before the `add`. |
| 936 | ` * add. d0 is the prefetch distance D in bytes ahead of the block that the` | Comment: `d0` is the prefetch distance D in bytes: the offset of the first prefetched 64 B line from the start of the block that the loop pass loads. |
| 937 | ` * iteration loads. d1, d2, d3 are D + 64, D + 128, D + 192.` | Comment: `d1`, `d2` and `d3` are D + 64, D + 128 and D + 192. So the four prefetches name four neighbour 64 B lines. |
| 938 | ` *` | Comment: an empty line of the comment. |
| 939 | ` * prfm pldl1keep asks for the line in the first-level data cache (PLD: for a` | Comment: the instruction `prfm pldl1keep` asks the CPU to bring a 64 B line into the first-level data cache. It loads no data into a register. `PLD` in its name means: for a load. |
| 940 | ` * load, L1: first level, KEEP: normal, not streaming). The form` | Comment: `L1` means the first cache level. `KEEP` means normal use, not streaming. The sentence about the address form starts here. |
| 941 | ` * [base, #offset] needs an offset that is a multiple of 8 from 0 to 32760.` | Comment: the address form `[base, #offset]` needs an offset that is a multiple of 8 from 0 to 32760. |
| 942 | ` * In the last iterations of a pass the prefetch address lies past the end of` | Comment: in the last loop passes of a call the prefetch address lies past the end of the range. |
| 943 | ` * the range, and for the last range of the buffer past the end of the` | Comment: for the last range of the buffer the prefetch address lies past the end of the buffer. |
| 944 | ` * buffer. That is allowed: prfm never faults, not even on an address that is` | Comment: that is allowed. A `prfm` never causes a fault, not even with an address that is not mapped. |
| 945 | ` * not mapped. It reads no data, so the kernel touches the same bytes as` | Comment: a `prfm` reads no data. So the kernel touches the same bytes as `asmread`. |
| 946 | ` * asmread.` | Comment: the last word of the sentence of line 945. |
| 947 | ` */` | Ends the comment. |
| 948 | `#define DEF_READ_PF(name, d0, d1, d2, d3) \` | Starts the macro `DEF_READ_PF(name, d0, d1, d2, d3)`. Its text is the text of `DEF_ASMREAD` (line 616) with four `prfm` instructions in place of the `nop` text. |
| 949 | `    _Static_assert((d0) % 8 == 0 && (d0) >= 0 && (d1) == (d0) + 64 && (d2) == (d0) + 128 && (d3) == (d0) + 192 && \` | `_Static_assert` stops the compilation when the four offsets break the rule of the comment. This line tests that `d0` is a multiple of 8 and not negative, and that `d1`, `d2` and `d3` are `d0` plus 64, 128 and 192. |
| 950 | `                   (d3) <= 32760, "prfm offsets: multiples of 8 from 0 to 32760, one per 64 B line"); \` | Continues the test of line 949: `d3` must be at most 32760. The text in quotes is the error message of the compiler. |
| 951 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function. For the four kernels below it is 0 bytes (lines 911 to 922). |
| 952 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 953 | `    { \` | Opens the body of the kernel function. |
| 954 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 955 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 956 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 957 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loops of the four kernels start at 20 modulo 64, the loop offset of `k_asmread` [Ref1]. |
| 958 | `            "ldp q0, q1, [%[p]]\n\t" \` | Loads the bytes 0 to 31 of the current block of 256 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 959 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 960 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 961 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. |
| 962 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 963 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 964 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 965 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once. Nothing uses the loaded values. |
| 966 | `            "prfm pldl1keep, [%[p], #" #d0 "]\n\t" \` | The first prefetch: `prfm pldl1keep` asks the CPU to bring the 64 B line at the address `p` plus `d0` into the first-level data cache. `#d0` puts the macro argument into the text as a number. The instruction loads no data into a register. |
| 967 | `            "prfm pldl1keep, [%[p], #" #d1 "]\n\t" \` | The second prefetch: the 64 B line at the address `p` plus `d1`, which is 64 B after the first one. |
| 968 | `            "prfm pldl1keep, [%[p], #" #d2 "]\n\t" \` | The third prefetch: the 64 B line at the address `p` plus `d2`. |
| 969 | `            "prfm pldl1keep, [%[p], #" #d3 "]\n\t" \` | The fourth prefetch: the 64 B line at the address `p` plus `d3`. So one loop pass prefetches four neighbour 64 B lines, which are 256 B. |
| 970 | `            "add %[p], %[p], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 971 | `            "cmp %[p], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 972 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. In `bwx12` one loop pass is 15 instructions per 256 B: 8 `ldp`, 4 `prfm`, `add`, `cmp` and the branch [Ref1]. |
| 973 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 974 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 975 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 976 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop, as in `asmread`. |
| 977 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 978 | `    }` | Ends the kernel function and the macro. |
| 979 | `DEF_READ_PF(read_pf256, 256, 320, 384, 448)` | Defines `k_read_pf256`, the kernel `read_pf256`. The number in the name is `d0` in bytes. The four prefetch offsets are 256, 320, 384 and 448: the four 64 B lines of the block after the current one. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 980 | `DEF_READ_PF(read_pf512, 512, 576, 640, 704)` | Defines `k_read_pf512`, the kernel `read_pf512`. The four prefetch offsets are 512, 576, 640 and 704: the block 512 B after the start of the current one. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 981 | `DEF_READ_PF(read_pf1024, 1024, 1088, 1152, 1216)` | Defines `k_read_pf1024`, the kernel `read_pf1024`. The four prefetch offsets are 1024, 1088, 1152 and 1216. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 982 | `DEF_READ_PF(read_pf2048, 2048, 2112, 2176, 2240)` | Defines `k_read_pf2048`, the kernel `read_pf2048`. The four prefetch offsets are 2048, 2112, 2176 and 2240. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |

### Function `k_read_1pl`: one load of 16 B per 64 B line (lines 984 to 1004)

| Line | Source | Explanation |
|---:|---|---|
| 984 | `/* read_1pl, "one load per line". Per 256 B: four loads of 16 B, one at the` | Comment: the name `read_1pl` means one load per line. A line here is a 64 B line, a block of 64 B of memory (a cache line). Per 256 B the loop has four loads of 16 B. |
| 985 | ` * start of each 64 B line, then add, cmp, b.lo. It reads bytes 0 to 15 of` | Comment: one load stands at the start of each 64 B line. Then come `add`, `cmp` and `b.lo`. The sentence about the bytes starts here. |
| 986 | ` * every line and no other byte. */` | Comment: the kernel reads the bytes 0 to 15 of every 64 B line and no other byte. |
| 987 | `PLACE(read_1pl);` | `PLACE(read_1pl)` adds a pad of 16 bytes (line 928). In the CRB binary of `bwx12` the function starts at `0x55d0`, which is 16 modulo 64 [Ref1]. |
| 988 | `__attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)` | Starts the function `k_read_1pl`, the kernel `read_1pl`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. `noinline` forbids gcc to merge it into its caller. The whole-chip test runs this kernel at position 4, the last position, in part L and control I. Part C does not run it [Ref4]. |
| 989 | `{` | Opens the body of `k_read_1pl`. |
| 990 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 991 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx12`: `add x1, x0, x1, lsl #3`. It is the only instruction before the loop [Ref1]. |
| 992 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text of the loop, as in `DEF_ASMREAD` (line 622). |
| 993 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loop starts at an address of 20 modulo 64 [Ref1]. |
| 994 | `        "ldr q0, [%[p]]\n\t"` | `ldr` loads 16 B from memory into one vector register: the bytes 0 to 15 of the current block of 256 B into `q0`. These are the first 16 B of the first 64 B line of the block. |
| 995 | `        "ldr q1, [%[p], #64]\n\t"` | Loads the bytes 64 to 79 of the block into `q1`: the first 16 B of the second 64 B line. |
| 996 | `        "ldr q2, [%[p], #128]\n\t"` | Loads the bytes 128 to 143 of the block into `q2`: the first 16 B of the third 64 B line. |
| 997 | `        "ldr q3, [%[p], #192]\n\t"` | Loads the bytes 192 to 207 of the block into `q3`: the first 16 B of the fourth 64 B line. So one loop pass loads 64 B of its block of 256 B: the bytes 0 to 15 of each 64 B line. It does not load the other 48 B of a 64 B line. `asmread` has 8 load instructions of 32 B per loop pass. This kernel has 4 load instructions of 16 B per loop pass. Nothing uses the loaded values: no instruction of the loop takes `q0` to `q3` as an input. |
| 998 | `        "add %[p], %[p], #256\n\t"` | `add` moves the read pointer forward by 256 B. |
| 999 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the read pointer with `end`. |
| 1000 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the pointer is below `end`. Machine code of `bwx12`, one loop pass: 4 `ldr`, `add x0, x0, #0x100`, `cmp x0, x1` and `b.cc`. That is 7 instructions per block of 256 B [Ref1]. The worker counts the bytes outside the kernel. For each call it adds the size of the chunk (line 1696), which is 2097152 B in the whole-chip test [Ref4]. So the rate of `read_1pl` counts 256 B per loop pass, although the loop pass loads 64 B. |
| 1001 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 1002 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 1003 | `        : "v0", "v1", "v2", "v3", "memory", "cc");` | The clobber list. Of the vector registers it names only `v0` to `v3`. The calling rules do not require a function to keep these registers. So gcc saves nothing. In `bwx12` the whole function has 9 instructions: 1 before the loop, 7 in the loop, then `ret` [Ref1]. `asmread` differs here: it saves `d8` to `d15` and loads them back at each call. |
| 1004 | `}` | Ends the function `k_read_1pl`. |

### Stand-ins of the kernels of round 3 (lines 1005 to 1023)

| Line | Source | Explanation |
|---:|---|---|
| 1005 | `#else` | `#else` of the `#if` of line 931. The compiler reads the lines up to line 1021 only for a machine that is not AArch64. The CRB binary of `bwx12` does not hold this code: the header of every csv file of the whole-chip test says `kernels=aarch64` [Ref5]. |
| 1006 | `/* Stand-ins. A prefetch touches no byte, so the stand-in of a read_pf kernel` | Comment: the stand-ins of the kernels of this block. A prefetch touches no byte. |
| 1007 | ` * is the stand-in of asmread. The stand-in of read_1pl reads the first two` | Comment: so the stand-in of a `read_pf` kernel is the stand-in of `asmread` (lines 858 to 865). The sentence about `read_1pl` starts here. |
| 1008 | ` * words (16 B) of every 64 B line, as the real kernel does. */` | Comment: the stand-in of `read_1pl` reads the first two words, which are 16 B, of every 64 B line. The real kernel reads the same bytes. |
| 1009 | `DEF_ASMREAD(read_pf256, 0)` | Stand-in build only: defines `k_read_pf256` as the plain read loop of lines 858 to 865, which reads every word of the range. |
| 1010 | `DEF_ASMREAD(read_pf512, 0)` | Stand-in build only: defines `k_read_pf512` as the plain read loop. |
| 1011 | `DEF_ASMREAD(read_pf1024, 0)` | Stand-in build only: defines `k_read_pf1024` as the plain read loop. |
| 1012 | `DEF_ASMREAD(read_pf2048, 0)` | Stand-in build only: defines `k_read_pf2048` as the plain read loop. |
| 1013 | `PLACE(read_1pl);` | `PLACE` adds the pad of `read_1pl`, as in the AArch64 branch. |
| 1014 | `__attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)` | Starts the stand-in function `k_read_1pl`. A build on CRB, an Arm machine, does not compile it. |
| 1015 | `{` | Opens the body of the stand-in. |
| 1016 | `    const volatile uint64_t *p = a;` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 1017 | `    for (size_t i = 0; i < n; i += 8) {` | A loop over the range in steps of 8 words, which are 64 B. |
| 1018 | `        (void)p[i];` | Reads the first word of the 64 B line and drops the value. |
| 1019 | `        (void)p[i + 1];` | Reads the second word of the 64 B line and drops the value. So the loop reads 16 B of every 64 B. |
| 1020 | `    }` | Ends the loop of line 1017. |
| 1021 | `}` | Ends the stand-in function `k_read_1pl`. |
| 1022 | `#endif` | Ends the `#if` of line 931. |

### Pad after the kernels of round 3 (lines 1024 to 1042)

| Line | Source | Explanation |
|---:|---|---|
| 1024 | `/*` | Opens the comment about the placement of the code after the kernels. It explains lines 1036 to 1039. |
| 1025 | ` * Placement of the code after the kernels. In the accepted build of bwx8 the` | Comment: the topic is the placement of the code that follows the kernels. The comment first gives a fact about the accepted build of `bwx8`. |
| 1026 | ` * last kernel ends at 0x4a14 (ref-bwx8/listing.txt), so the function after` | Comment: in that build the last kernel ends at the address `0x4a14`. The comment names the file `ref-bwx8/listing.txt` as its source. |
| 1027 | ` * the kernels starts at 0x4a18: 24 modulo 64. That function is call(), or` | Comment: so the function after the kernels starts at `0x4a18` in that build, which is 24 modulo 64. That function is `call` (line 1491). The build record of CRB reports `call=24` for `bwx12`: its function `call` also starts at 24 modulo 64 [Ref2]. |
| 1028 | ` * read_smaps() if gcc inlines every call of call(). The pad below gives it` | Comment: if gcc merges `call` into all of its callers, the function after the kernels is `read_smaps` (line 1515). The pad below gives this function the same start address modulo 64 in `bwx10`. |
| 1029 | ` * the same start modulo 64 in bwx10. No code is added between call() and the` | Comment: no code was added between `call` and the end of `timed_sequence` (line 1995), a function of the trial mode. |
| 1030 | ` * end of timed_sequence(), so that code keeps the placement modulo 64 that it` | Comment: so the code from `call` to the end of `timed_sequence` keeps its placement modulo 64. The whole-chip test of 2026-11-17 does not use the trial mode [Ref4]. |
| 1031 | ` * has in bwx8. build10.sh prints the placement of both binaries.` | Comment: it is the placement that this code has in `bwx8`. The script `build10.sh` in the code folder `bwx10-2026-11-15` prints the placement of both binaries. |
| 1032 | ` * The value 24 holds for the AArch64 build with the accepted compiler. On` | Comment: the value 24 holds for the AArch64 build with the accepted compiler. |
| 1033 | ` * another machine it is only a pad: test_runner10.py builds one copy with the` | Comment: on another machine the value is only a pad. The script `test_runner10.py` in the code folder `bwx10-2026-11-15` builds one copy with another value. |
| 1034 | ` * local value to check the method.` | Comment: that other value is the value of the local machine. The copy checks the method. |
| 1035 | ` */` | Ends the comment. |
| 1036 | `#ifndef PAD_after_kernels` | Compiles line 1037 only when the build command has not defined `PAD_after_kernels`. |
| 1037 | `#define PAD_after_kernels 24` | `PAD_after_kernels` is 24. A `-D` option could give another value, and the CRB build of `bwx12` has none [Ref2]. |
| 1038 | `#endif` | Ends the `#ifndef` of line 1036. |
| 1039 | `PLACE(after_kernels);` | `PLACE(after_kernels)` fills the code up to a multiple of 64 bytes and then adds 24 bytes of value 0. No function with this name exists: the macro only places the code that follows. In `bwx12` more kernels follow this pad, from line 1043 on. So this pad does not stand directly before `call` any more. A later pad with the same value does that (lines 1446 to 1449). |
| 1040 | `/* bwx10- */` | Comment: a marker. The block that line 898 opened ends here. |
| 1041 | `/* bwx11+ */` | Comment: a marker. A block of text that the version `bwx11` added starts here. The marker of line 1076 ends the block. The block holds the kernels `read_nop64`, `read_nop96` and `read_nop128`. |

### Kernels of round 4 (version `bwx11`): `read_nop64`, `read_nop96`, `read_nop128` (lines 1043 to 1065)

| Line | Source | Explanation |
|---:|---|---|
| 1043 | `/*` | Opens the comment about the kernels of round 4. |
| 1044 | ` * Kernels of round 4. They stand after every kernel of bwx10, so those keep` | Comment: the kernels below are those of round 4, the round of work that produced `bwx11` (line 36). It is not a round of the option `--rounds`. They stand after every kernel of `bwx10`. |
| 1045 | ` * their place. Each one is the asmread loop with more nop instructions` | Comment: so the kernels of `bwx10` keep their place in the binary. Each new kernel is the `asmread` loop with more `nop` instructions. |
| 1046 | ` * between the 8 ldp and the add: 64, 96 and 128. The frame is the frame of` | Comment: the `nop` instructions stand between the 8 `ldp` and the `add` of the read address: 64, 96 or 128 of them. Of these three kernels the whole-chip test of 2026-11-17 runs only `read_nop96` [Ref4]. The sentence about the frame starts here. |
| 1047 | ` * asmread (d8-d15 are saved), so the pad is the pad of asmread and the loop` | Comment: the frame is the frame of `asmread`: the function saves `d8` to `d15` before its loop. So each kernel gets the pad of `asmread`. |
| 1048 | ` * starts at 20 modulo 64 (check_listing11.py checks it). DEF_ASMREAD is the` | Comment: the loop then starts at 20 modulo 64. The script `check_listing11.py` in the code folder `bwx11-2026-11-15` checks it. The listing of the CRB build of `bwx12` shows 20 modulo 64 for the three loops [Ref1]. |
| 1049 | ` * macro of the kernels of bwx8: the asm text on AArch64, the stand-in loop on` | Comment: `DEF_ASMREAD` is the macro of the kernels of `bwx8`. On AArch64 it gives the assembly text (line 616). |
| 1050 | ` * another machine. A nop touches no byte, so the stand-in is the stand-in of` | Comment: on another machine it gives the stand-in loop (line 858). A `nop` touches no byte. |
| 1051 | ` * asmread.` | Comment: so the stand-in of these kernels is the stand-in of `asmread`. |
| 1052 | ` */` | Ends the comment. |
| 1053 | `#ifndef PAD_read_nop64` | Compiles line 1054 only when the build command has not defined `PAD_read_nop64`. |
| 1054 | `#define PAD_read_nop64 PAD_asmread` | `PAD_read_nop64`: the value of `PAD_asmread`, which is 0 (line 214). So `PLACE` (line 163) lets the function start on a 64 B boundary. The whole-chip test of 2026-11-17 does not run the kernel `read_nop64` [Ref4]. |
| 1055 | `#endif` | Ends the `#ifndef` of line 1053. |
| 1056 | `#ifndef PAD_read_nop96` | Compiles line 1057 only when the build command has not defined `PAD_read_nop96`. |
| 1057 | `#define PAD_read_nop96 PAD_asmread` | `PAD_read_nop96`: the value of `PAD_asmread`, which is 0 (line 214). The CRB build of `bwx12` has no `-D` option that could change it [Ref2]. So `k_read_nop96`, a kernel of the whole-chip test, starts on a 64 B boundary. |
| 1058 | `#endif` | Ends the `#ifndef` of line 1056. |
| 1059 | `#ifndef PAD_read_nop128` | Compiles line 1060 only when the build command has not defined `PAD_read_nop128`. |
| 1060 | `#define PAD_read_nop128 PAD_asmread` | `PAD_read_nop128`: the value of `PAD_asmread`, which is 0 (line 214). The whole-chip test of 2026-11-17 does not run the kernel `read_nop128` [Ref4]. |
| 1061 | `#endif` | Ends the `#ifndef` of line 1059. |
| 1062 | `DEF_ASMREAD(read_nop64, 64)` | Creates the kernel `read_nop64` from the macro `DEF_ASMREAD` (lines 616 to 641): the `asmread` loop with 64 `nop` instructions per 256 B. That is 75 instructions per loop pass [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1063 | `DEF_ASMREAD(read_nop96, 96)` | Creates the function `k_read_nop96` from the macro `DEF_ASMREAD` (lines 616 to 641) with 96 `nop`. Part L and control I run it at position 2 of the sequence. Part C does not run it [Ref4]. gcc does not change the assembly text of the loop. It only chooses the registers: `x0` holds the read address and `x1` the end address. One loop pass: 8 `ldp` load 256 B, 32 B each at the byte offsets 0, 32 and so on to 224, into `q0` to `q15`. Each byte is read once, and nothing uses the loaded values. Then come 96 `nop` (from `.rept 96`, `nop`, `.endr`), `add x0, x0, #0x100` (256 B forward), `cmp x0, x1` and `b.cc`. The source writes this branch as `b.lo 1b`: back to the first `ldp` while the read address is below the end address. That is 107 instructions (428 B of code) per 256 B of data. The function starts at the address `0x57c0` (0 modulo 64) and the loop at `0x57d4` (20 modulo 64), the loop offset of `k_asmread`. Once per call, outside the loop: 4 `stp` save `d8` to `d15` on the stack, one `add` computes the end address, 4 `ldp` load `d8` to `d15` back, and `ret` returns [Ref1]. In a timed interval of the test one call covers one chunk of 2 MiB, which is 8192 loop passes. |
| 1064 | `DEF_ASMREAD(read_nop128, 128)` | Creates the kernel `read_nop128`: the `asmread` loop with 128 `nop` instructions per 256 B. That is 139 instructions per loop pass [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |

### Second pad after the kernels (version `bwx11`) (lines 1066 to 1078)

| Line | Source | Explanation |
|---:|---|---|
| 1066 | `/*` | Opens the comment about the second pad. |
| 1067 | ` * The pad after the kernels, once more. The pad of bwx10 above now stands` | Comment: the pad after the kernels is needed once more. The pad of `bwx10` (line 1039) now stands before the kernels of round 4. |
| 1068 | ` * before the kernels of round 4, so it no longer places call(). This pad has` | Comment: so the pad of `bwx10` no longer sets the start address of `call`. |
| 1069 | ` * the same value, and the function after the kernels starts at that value` | Comment: the new pad has the same value. The function after the kernels then starts at that value modulo 64. |
| 1070 | ` * modulo 64, as in bwx10 and in bwx8. build11.sh prints the placement.` | Comment: that is the start address modulo 64 that this function has in `bwx10` and in `bwx8`. The script `build11.sh` in the code folder `bwx11-2026-11-15` prints the placement. |
| 1071 | ` */` | Ends the comment. |
| 1072 | `#ifndef PAD_after_kernels11` | Compiles line 1073 only when the build command has not defined `PAD_after_kernels11`. |
| 1073 | `#define PAD_after_kernels11 PAD_after_kernels` | `PAD_after_kernels11` gets the value of `PAD_after_kernels`, which is 24 (line 1037). |
| 1074 | `#endif` | Ends the `#ifndef` of line 1072. |
| 1075 | `PLACE(after_kernels11);` | `PLACE(after_kernels11)` pads the code up to a 64 B boundary and then adds 24 bytes of value 0. In `bwx11` this pad sets the start address of the function that follows the kernels. In `bwx12` more kernels follow here, and the pad of line 1449 sets that start address. |
| 1076 | `/* bwx11- */` | Comment: a marker. The block that line 1041 opened ends here. |
| 1077 | `/* bwx12+ */` | Comment: a marker. A block of text that the version `bwx12` added starts here. The marker of line 1450 ends the block. |

### Kernels of round 5 (version `bwx12`): loop offsets, head sizes and pads (lines 1079 to 1188)

| Line | Source | Explanation |
|---:|---|---|
| 1079 | `/*` | Opens the comment about the placement of the kernels of round 5. |
| 1080 | ` * Kernels of round 5. They stand after every kernel of bwx11, so those keep` | Comment: the kernels below are those of round 5, a round of work on the program (line 3). It is not a round of the option `--rounds`. There are 26 of them (line 9). They stand after every kernel of `bwx11`. |
| 1081 | ` * their place. The pad of each one puts the loop start at the loop offset` | Comment: so the kernels of `bwx11` keep their place in the binary. The pad of each new kernel puts its loop start at a planned address modulo 64. |
| 1082 | ` * modulo 64 of its original in the accepted build: 20 for a read kernel (the` | Comment: the planned address is the loop offset that the original kernel has in the accepted build. For a read kernel it is 20, the loop offset of `asmread`. |
| 1083 | ` * offset of asmread), 40 for a write kernel (asmwrite), 52 for a copy kernel` | Comment: for a write kernel it is 40, the loop offset of `asmwrite`. For a copy kernel it is 52, the loop offset of `asmcopy`. |
| 1084 | ` * (asmcopy). PAD = (LOOP - HEAD) mod 64, where HEAD is the number of bytes` | Comment: the rule is `PAD = (LOOP - HEAD) mod 64`. `LOOP` is the planned loop offset. `HEAD` is the number of bytes of code between the function start and the loop start. |
| 1085 | ` * between the function start and the loop start. Every HEAD below is a guess` | Comment: every `HEAD` value below is a guess until the listing of the CRB build confirms it. |
| 1086 | ` * until the listing of the CRB build confirms it (check_listing12.py checks` | Comment: the script `check_listing12.py` in the code folder `bwx12-2026-11-15` checks the loop offset. The listing of the CRB binary of `bwx12` shows the planned loop offset for each of the 26 kernels [Ref1]. |
| 1087 | ` * the loop offset). Override one with -DHEAD_<group>=N or -DPAD_<name>=N.` | Comment: the build can replace one value with `-DHEAD_<group>=N` or `-DPAD_<name>=N`. Of the 26 kernels the whole-chip test of 2026-11-17 runs only `read_nop256` [Ref4]. |
| 1088 | ` *` | Comment: an empty line of the comment. |
| 1089 | ` *   read_nopN       frame of asmread (gcc saves d8-d15): HEAD 20, pad of asmread.` | Comment: the `read_nop` kernels have the frame of `asmread`: gcc saves `d8` to `d15`. So `HEAD` is 20, and they take the pad of `asmread`. |
| 1090 | ` *   read_daddK      frame of asmread, then 8 movi: HEAD 20 + 32 = 52.` | Comment: the `read_dadd` kernels have the frame of `asmread` and then 8 `movi` instructions of 4 bytes each. So `HEAD` is 20 + 32 = 52. |
| 1091 | ` *   read_iadd16     frame of asmread, then 16 movi: HEAD 20 + 64 = 84.` | Comment: `read_iadd16` has the frame of `asmread` and then 16 `movi` instructions. So `HEAD` is 20 + 64 = 84. |
| 1092 | ` *   read_spN        no frame, as read_sparse: HEAD 4. read_sparse itself has` | Comment: the `read_sp` kernels have no frame, as `read_sparse`. So `HEAD` is 4. The sentence about `read_sparse` starts here. |
| 1093 | ` *                   its loop at 4 modulo 64 (pad of asmread, HEAD 4). The new` | Comment: `read_sparse` itself has its loop at 4 modulo 64. It takes the pad of `asmread`, which is 0, and its `HEAD` is 4. |
| 1094 | ` *                   kernels get 20, the offset of asmread.` | Comment: the new `read_sp` kernels get the loop offset 20, the offset of `asmread`. |
| 1095 | ` *                   -DHEAD_read_sp=20 gives them the offset of read_sparse.` | Comment: a build with `-DHEAD_read_sp=20` gives them the loop offset of `read_sparse`: the pad is then 0, and the loop starts at 4 modulo 64. |
| 1096 | ` *   read_1pl_nop96  no frame, as read_1pl: HEAD 4, pad of read_1pl.` | Comment: `read_1pl_nop96` has no frame, as `read_1pl`. So `HEAD` is 4, and it takes the pad of `read_1pl`. |
| 1097 | ` *   write_nopN      as asmwrite (end pointer, dup): pad of asmwrite.` | Comment: the `write_nop` kernels start as `asmwrite` does, with the computation of the end pointer and the `dup`. So they take the pad of `asmwrite`. |
| 1098 | ` *   copy_nopN       frame of asmcopy: pad of asmcopy.` | Comment: the `copy_nop` kernels have the frame of `asmcopy`. So they take the pad of `asmcopy`. |
| 1099 | ` */` | Ends the comment. |
| 1100 | `#define LOOP_read12 20` | `LOOP_read12`: 20, the planned loop offset modulo 64 of the new read kernels. It is the loop offset of `asmread`. |
| 1101 | `#ifndef HEAD_read_dadd` | Compiles line 1102 only when the build command has not defined `HEAD_read_dadd`. |
| 1102 | `#define HEAD_read_dadd 52` | `HEAD_read_dadd`: 52 bytes of code stand before the loop of a `read_dadd` kernel. The listing of the CRB binary of `bwx12` shows this distance: 13 instructions, which are the save of `d8` to `d15`, the `add` of the end address and 8 `movi` [Ref1]. |
| 1103 | `#endif` | Ends the `#ifndef` of line 1101. |
| 1104 | `#ifndef HEAD_read_iadd` | Compiles line 1105 only when the build command has not defined `HEAD_read_iadd`. |
| 1105 | `#define HEAD_read_iadd 84` | `HEAD_read_iadd`: 84 bytes of code stand before the loop of `read_iadd16`. The listing of the CRB binary of `bwx12` shows this distance: 21 instructions, of which 16 are `movi` [Ref1]. |
| 1106 | `#endif` | Ends the `#ifndef` of line 1104. |
| 1107 | `#ifndef HEAD_read_sp` | Compiles line 1108 only when the build command has not defined `HEAD_read_sp`. |
| 1108 | `#define HEAD_read_sp 4` | `HEAD_read_sp`: 4 bytes of code, one instruction, stand before the loop of a `read_sp` kernel. The listing of the CRB binary of `bwx12` shows this distance [Ref1]. |
| 1109 | `#endif` | Ends the `#ifndef` of line 1107. |
| 1110 | `#ifndef PAD_read_nop48` | Compiles line 1111 only when the build command has not defined `PAD_read_nop48`. |
| 1111 | `#define PAD_read_nop48 PAD_asmread` | `PAD_read_nop48`: the value of `PAD_asmread`, 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop48` [Ref4]. |
| 1112 | `#endif` | Ends the `#ifndef` of line 1110. |
| 1113 | `#ifndef PAD_read_nop56` | Compiles line 1114 only when the build command has not defined `PAD_read_nop56`. |
| 1114 | `#define PAD_read_nop56 PAD_asmread` | `PAD_read_nop56`: the value of `PAD_asmread`, 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop56` [Ref4]. |
| 1115 | `#endif` | Ends the `#ifndef` of line 1113. |
| 1116 | `#ifndef PAD_read_nop72` | Compiles line 1117 only when the build command has not defined `PAD_read_nop72`. |
| 1117 | `#define PAD_read_nop72 PAD_asmread` | `PAD_read_nop72`: the value of `PAD_asmread`, 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop72` [Ref4]. |
| 1118 | `#endif` | Ends the `#ifndef` of line 1116. |
| 1119 | `#ifndef PAD_read_nop80` | Compiles line 1120 only when the build command has not defined `PAD_read_nop80`. |
| 1120 | `#define PAD_read_nop80 PAD_asmread` | `PAD_read_nop80`: the value of `PAD_asmread`, 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop80` [Ref4]. |
| 1121 | `#endif` | Ends the `#ifndef` of line 1119. |
| 1122 | `#ifndef PAD_read_nop88` | Compiles line 1123 only when the build command has not defined `PAD_read_nop88`. |
| 1123 | `#define PAD_read_nop88 PAD_asmread` | `PAD_read_nop88`: the value of `PAD_asmread`, 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop88` [Ref4]. |
| 1124 | `#endif` | Ends the `#ifndef` of line 1122. |
| 1125 | `#ifndef PAD_read_nop112` | Compiles line 1126 only when the build command has not defined `PAD_read_nop112`. |
| 1126 | `#define PAD_read_nop112 PAD_asmread` | `PAD_read_nop112`: the value of `PAD_asmread`, 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop112` [Ref4]. |
| 1127 | `#endif` | Ends the `#ifndef` of line 1125. |
| 1128 | `#ifndef PAD_read_nop160` | Compiles line 1129 only when the build command has not defined `PAD_read_nop160`. |
| 1129 | `#define PAD_read_nop160 PAD_asmread` | `PAD_read_nop160`: the value of `PAD_asmread`, 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop160` [Ref4]. |
| 1130 | `#endif` | Ends the `#ifndef` of line 1128. |
| 1131 | `#ifndef PAD_read_nop192` | Compiles line 1132 only when the build command has not defined `PAD_read_nop192`. |
| 1132 | `#define PAD_read_nop192 PAD_asmread` | `PAD_read_nop192`: the value of `PAD_asmread`, 0 bytes. The whole-chip test of 2026-11-17 does not run the kernel `read_nop192` [Ref4]. |
| 1133 | `#endif` | Ends the `#ifndef` of line 1131. |
| 1134 | `#ifndef PAD_read_nop256` | Compiles line 1135 only when the build command has not defined `PAD_read_nop256`. |
| 1135 | `#define PAD_read_nop256 PAD_asmread` | `PAD_read_nop256`: the value of `PAD_asmread`, 0 bytes. So `k_read_nop256`, a kernel of the whole-chip test, starts on a 64 B boundary. The listing of the CRB binary of `bwx12` shows the start address `0x6cc0`. That is 0 modulo 64 [Ref1]. |
| 1136 | `#endif` | Ends the `#ifndef` of line 1134. |
| 1137 | `#ifndef PAD_read_dadd2` | Compiles line 1138 only when the build command has not defined `PAD_read_dadd2`. |
| 1138 | `#define PAD_read_dadd2 PADOF(LOOP_read12, HEAD_read_dadd)` | `PAD_read_dadd2`: `PADOF` (line 164) computes (20 - 52) modulo 64, which is 32 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_dadd2` [Ref4]. |
| 1139 | `#endif` | Ends the `#ifndef` of line 1137. |
| 1140 | `#ifndef PAD_read_dadd4` | Compiles line 1141 only when the build command has not defined `PAD_read_dadd4`. |
| 1141 | `#define PAD_read_dadd4 PADOF(LOOP_read12, HEAD_read_dadd)` | `PAD_read_dadd4`: (20 - 52) modulo 64, which is 32 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_dadd4` [Ref4]. |
| 1142 | `#endif` | Ends the `#ifndef` of line 1140. |
| 1143 | `#ifndef PAD_read_dadd8` | Compiles line 1144 only when the build command has not defined `PAD_read_dadd8`. |
| 1144 | `#define PAD_read_dadd8 PADOF(LOOP_read12, HEAD_read_dadd)` | `PAD_read_dadd8`: (20 - 52) modulo 64, which is 32 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_dadd8` [Ref4]. |
| 1145 | `#endif` | Ends the `#ifndef` of line 1143. |
| 1146 | `#ifndef PAD_read_dadd16` | Compiles line 1147 only when the build command has not defined `PAD_read_dadd16`. |
| 1147 | `#define PAD_read_dadd16 PADOF(LOOP_read12, HEAD_read_dadd)` | `PAD_read_dadd16`: (20 - 52) modulo 64, which is 32 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_dadd16` [Ref4]. |
| 1148 | `#endif` | Ends the `#ifndef` of line 1146. |
| 1149 | `#ifndef PAD_read_iadd16` | Compiles line 1150 only when the build command has not defined `PAD_read_iadd16`. |
| 1150 | `#define PAD_read_iadd16 PADOF(LOOP_read12, HEAD_read_iadd)` | `PAD_read_iadd16`: (20 - 84) modulo 64, which is 0 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_iadd16` [Ref4]. |
| 1151 | `#endif` | Ends the `#ifndef` of line 1149. |
| 1152 | `#ifndef PAD_read_sp24` | Compiles line 1153 only when the build command has not defined `PAD_read_sp24`. |
| 1153 | `#define PAD_read_sp24 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp24`: (20 - 4) modulo 64, which is 16 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_sp24` [Ref4]. |
| 1154 | `#endif` | Ends the `#ifndef` of line 1152. |
| 1155 | `#ifndef PAD_read_sp32` | Compiles line 1156 only when the build command has not defined `PAD_read_sp32`. |
| 1156 | `#define PAD_read_sp32 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp32`: (20 - 4) modulo 64, which is 16 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_sp32` [Ref4]. |
| 1157 | `#endif` | Ends the `#ifndef` of line 1155. |
| 1158 | `#ifndef PAD_read_sp40` | Compiles line 1159 only when the build command has not defined `PAD_read_sp40`. |
| 1159 | `#define PAD_read_sp40 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp40`: (20 - 4) modulo 64, which is 16 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_sp40` [Ref4]. |
| 1160 | `#endif` | Ends the `#ifndef` of line 1158. |
| 1161 | `#ifndef PAD_read_sp48` | Compiles line 1162 only when the build command has not defined `PAD_read_sp48`. |
| 1162 | `#define PAD_read_sp48 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp48`: (20 - 4) modulo 64, which is 16 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_sp48` [Ref4]. |
| 1163 | `#endif` | Ends the `#ifndef` of line 1161. |
| 1164 | `#ifndef PAD_read_sp56` | Compiles line 1165 only when the build command has not defined `PAD_read_sp56`. |
| 1165 | `#define PAD_read_sp56 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp56`: (20 - 4) modulo 64, which is 16 bytes with the default values. The whole-chip test of 2026-11-17 does not run the kernel `read_sp56` [Ref4]. |
| 1166 | `#endif` | Ends the `#ifndef` of line 1164. |
| 1167 | `#ifndef PAD_read_1pl_nop96` | Compiles line 1168 only when the build command has not defined `PAD_read_1pl_nop96`. |
| 1168 | `#define PAD_read_1pl_nop96 PAD_read_1pl` | `PAD_read_1pl_nop96`: the pad of `read_1pl`, which is 16 bytes with the default values (line 928). The whole-chip test of 2026-11-17 does not run the kernel `read_1pl_nop96` [Ref4]. |
| 1169 | `#endif` | Ends the `#ifndef` of line 1167. |
| 1170 | `#ifndef PAD_write_nop32` | Compiles line 1171 only when the build command has not defined `PAD_write_nop32`. |
| 1171 | `#define PAD_write_nop32 PAD_asmwrite` | `PAD_write_nop32`: the pad of `asmwrite`, which is 32 bytes (line 220). The whole-chip test of 2026-11-17 does not run the kernel `write_nop32` [Ref4]. |
| 1172 | `#endif` | Ends the `#ifndef` of line 1170. |
| 1173 | `#ifndef PAD_write_nop96` | Compiles line 1174 only when the build command has not defined `PAD_write_nop96`. |
| 1174 | `#define PAD_write_nop96 PAD_asmwrite` | `PAD_write_nop96`: the pad of `asmwrite`, which is 32 bytes (line 220). The whole-chip test of 2026-11-17 does not run the kernel `write_nop96` [Ref4]. |
| 1175 | `#endif` | Ends the `#ifndef` of line 1173. |
| 1176 | `#ifndef PAD_write_nop128` | Compiles line 1177 only when the build command has not defined `PAD_write_nop128`. |
| 1177 | `#define PAD_write_nop128 PAD_asmwrite` | `PAD_write_nop128`: the pad of `asmwrite`, which is 32 bytes (line 220). The whole-chip test of 2026-11-17 does not run the kernel `write_nop128` [Ref4]. |
| 1178 | `#endif` | Ends the `#ifndef` of line 1176. |
| 1179 | `#ifndef PAD_write_nop256` | Compiles line 1180 only when the build command has not defined `PAD_write_nop256`. |
| 1180 | `#define PAD_write_nop256 PAD_asmwrite` | `PAD_write_nop256`: the pad of `asmwrite`, which is 32 bytes (line 220). The whole-chip test of 2026-11-17 does not run the kernel `write_nop256` [Ref4]. |
| 1181 | `#endif` | Ends the `#ifndef` of line 1179. |
| 1182 | `#ifndef PAD_copy_nop96` | Compiles line 1183 only when the build command has not defined `PAD_copy_nop96`. |
| 1183 | `#define PAD_copy_nop96 PAD_asmcopy` | `PAD_copy_nop96`: the pad of `asmcopy`, which is 32 bytes with the default values (line 193). The whole-chip test of 2026-11-17 does not run the kernel `copy_nop96` [Ref4]. |
| 1184 | `#endif` | Ends the `#ifndef` of line 1182. |
| 1185 | `#ifndef PAD_copy_nop192` | Compiles line 1186 only when the build command has not defined `PAD_copy_nop192`. |
| 1186 | `#define PAD_copy_nop192 PAD_asmcopy` | `PAD_copy_nop192`: the pad of `asmcopy`, which is 32 bytes with the default values (line 193). The whole-chip test of 2026-11-17 does not run the kernel `copy_nop192` [Ref4]. |
| 1187 | `#endif` | Ends the `#ifndef` of line 1185. |

### Kernels of round 5: nine more `read_nop` kernels (lines 1189 to 1200)

| Line | Source | Explanation |
|---:|---|---|
| 1189 | `/* DEF_ASMREAD is the macro of the kernels of bwx8: the asm text on AArch64,` | Comment: `DEF_ASMREAD` is the macro of the kernels of `bwx8`. On AArch64 it gives the assembly text (line 616). |
| 1190 | ` * the stand-in loop on another machine. */` | Comment: on another machine it gives the stand-in loop (line 858). |
| 1191 | `DEF_ASMREAD(read_nop48, 48)` | Creates the kernel `read_nop48` from the macro `DEF_ASMREAD` (lines 616 to 641): the `asmread` loop with 48 `nop` per loop pass. That is 59 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1192 | `DEF_ASMREAD(read_nop56, 56)` | Creates the kernel `read_nop56`: the `asmread` loop with 56 `nop` per loop pass. That is 67 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1193 | `DEF_ASMREAD(read_nop72, 72)` | Creates the kernel `read_nop72`: the `asmread` loop with 72 `nop` per loop pass. That is 83 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1194 | `DEF_ASMREAD(read_nop80, 80)` | Creates the kernel `read_nop80`: the `asmread` loop with 80 `nop` per loop pass. That is 91 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1195 | `DEF_ASMREAD(read_nop88, 88)` | Creates the kernel `read_nop88`: the `asmread` loop with 88 `nop` per loop pass. That is 99 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1196 | `DEF_ASMREAD(read_nop112, 112)` | Creates the kernel `read_nop112`: the `asmread` loop with 112 `nop` per loop pass. That is 123 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1197 | `DEF_ASMREAD(read_nop160, 160)` | Creates the kernel `read_nop160`: the `asmread` loop with 160 `nop` per loop pass. That is 171 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1198 | `DEF_ASMREAD(read_nop192, 192)` | Creates the kernel `read_nop192`: the `asmread` loop with 192 `nop` per loop pass. That is 203 instructions per 256 B [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1199 | `DEF_ASMREAD(read_nop256, 256)` | Creates the function `k_read_nop256` from the macro `DEF_ASMREAD` (lines 616 to 641) with 256 `nop`. Part L and control I run it at position 3 of the sequence. Part C does not run it [Ref4]. The loop is the loop of `k_read_nop96` (line 1063) with 256 `nop` in place of 96. gcc does not change the assembly text. `x0` holds the read address and `x1` the end address. One loop pass: 8 `ldp` load 256 B, 32 B each at the byte offsets 0, 32 and so on to 224. Each byte is read once, and nothing uses the loaded values. Then come 256 `nop`, `add x0, x0, #0x100`, `cmp x0, x1` and the branch `b.cc` (another name of `b.lo`). That is 267 instructions (1068 B of code) per 256 B of data. The function starts at the address `0x6cc0` (0 modulo 64). The loop starts at `0x6cd4` (20 modulo 64), the loop offset of `k_asmread`. Once per call, outside the loop: 4 `stp` save `d8` to `d15` on the stack, one `add` computes the end address, 4 `ldp` load `d8` to `d15` back, and `ret` returns [Ref1]. In a timed interval of the test one call covers one chunk of 2 MiB, which is 8192 loop passes. |

### Kernels with vector adds: the comment and the text pieces `ACC_ZERO`, `CONST_ONE`, `VADD` (lines 1201 to 1243)

| Line | Source | Explanation |
|---:|---|---|
| 1201 | `#if defined(__aarch64__)` | Opens a third block of AArch64 kernels: lines 1202 to 1405 are compiled only for AArch64. Its `#else` is at line 1406. The CRB binary of `bwx12` holds this branch. Proof: the listing holds `k_read_dadd2` with the `movi` and vector `add` instructions of line 1273 [Ref1]. The whole-chip test of 2026-11-17 runs no kernel of this branch [Ref4]. |
| 1202 | `/*` | Opens the comment about the macro `DEF_READ_ADD` and its five kernels. |
| 1203 | ` * DEF_READ_ADD(name, init, adds): the loop of asmread (8 ldp of q registers` | Comment: `DEF_READ_ADD(name, init, adds)` defines a kernel with the loop of `asmread`: 8 `ldp` of `q` registers per 256 B. |
| 1204 | ` * per 256 B, same registers) with the text "adds" after the 8 ldp and before` | Comment: the loop uses the same registers as `asmread`. The assembly text `adds` stands after the 8 `ldp`. |
| 1205 | ` * the add of the pointer. "init" runs once per call, before the loop.` | Comment: the text `adds` stands before the `add` of the read pointer. The text `init` runs once per call, before the loop. |
| 1206 | ` * v16-v31 are caller-saved in AAPCS64, so gcc saves nothing for them. v8-v15` | Comment: AAPCS64, the calling rules of Arm, do not require a function to keep `v16` to `v31`. So gcc saves nothing for these registers. |
| 1207 | ` * are named as clobbers, so gcc saves d8-d15 once per call, as in asmread.` | Comment: `v8` to `v15` are named as changed (clobbers). So gcc saves `d8` to `d15` once per call, as in `asmread`. |
| 1208 | ` *` | Comment: an empty line of the comment. |
| 1209 | ` * ACC_ZERO sets the accumulators v16-v23 to 0. CONST_ONE sets v24-v31 to the` | Comment: `ACC_ZERO` sets the accumulators `v16` to `v23` to 0. An accumulator is a register that holds a running sum. `CONST_ONE` sets `v24` to `v31` to a constant. |
| 1210 | ` * value 1 in every 32-bit lane.` | Comment: the constant is the value 1 in every 32-bit lane. A lane is one of the equal parts of a vector register. |
| 1211 | ` * VADD(a, b) is "add va.2d, va.2d, vb.2d": two 64-bit adds, the instruction` | Comment: `VADD(a, b)` stands for the instruction `add va.2d, va.2d, vb.2d`. It performs two 64-bit adds. |
| 1212 | ` * of the old read loop (listing of k_oldread).` | Comment: it is the add instruction of the old read loop. The comment names the listing of `k_oldread` as the source. In the listing of `bwx12` the loop of `k_oldread` has 8 adds of this form [Ref1]. |
| 1213 | ` *` | Comment: an empty line of the comment. |
| 1214 | ` * read_daddK: every add takes a register that the 8 ldp of this iteration` | Comment: in a `read_dadd` kernel every add takes as an input a register that the 8 `ldp` of the same loop pass loaded. |
| 1215 | ` * loaded. So the add waits for the load data, and it stays in the` | Comment: so the add waits for the data of the load. Until then it stays in the out-of-order window of the core. |
| 1216 | ` * out-of-order window (the instructions that the core has issued and not yet` | Comment: the comment defines the out-of-order window: the instructions that the core has issued and has not yet retired. |
| 1217 | ` * retired) until the data arrives.` | Comment: the end of the sentence of line 1215: the add stays there until the data arrives. |
| 1218 | ` *   K = 16: v0 to v15, two per accumulator. 8 adds per 128 B, as oldread has.` | Comment: with K = 16 the adds take `v0` to `v15`, two registers per accumulator. That is 8 adds per 128 B, as in `oldread`. |
| 1219 | ` *   K = 8:  v0, v2, ..., v14, one per accumulator.` | Comment: with K = 8 the adds take `v0`, `v2` and so on to `v14`, one register per accumulator. |
| 1220 | ` *   K = 4:  v0, v4, v8, v12 into v16-v19.` | Comment: with K = 4 the adds take `v0`, `v4`, `v8` and `v12` and add them to `v16` to `v19`. |
| 1221 | ` *   K = 2:  v0, v8 into v16, v17.` | Comment: with K = 2 the adds take `v0` and `v8` and add them to `v16` and `v17`. |
| 1222 | ` * read_iadd16: 16 adds of v24-v31 to v16-v23. No add takes a loaded` | Comment: `read_iadd16` has 16 adds of `v24` to `v31` to `v16` to `v23`. No add takes a loaded register. |
| 1223 | ` * register. Same instruction count and same add instruction as read_dadd16.` | Comment: `read_iadd16` has the same instruction count and the same add instruction as `read_dadd16`. The listing of `bwx12` shows 27 instructions per loop pass for both [Ref1]. |
| 1224 | ` */` | Ends the comment. |
| 1225 | `#define ACC_ZERO \` | Starts the macro `ACC_ZERO`: a piece of assembly text with 8 `movi` instructions. `movi` writes a constant into a vector register. The backslash at the end of a line continues the macro on the next line. |
| 1226 | `    "movi v16.4s, #0\n\t" \` | `movi v16.4s, #0` sets the four 32-bit lanes of the sum register `v16` to 0. So the whole register is 0. |
| 1227 | `    "movi v17.4s, #0\n\t" \` | Sets the sum register `v17` to 0. |
| 1228 | `    "movi v18.4s, #0\n\t" \` | Sets the sum register `v18` to 0. |
| 1229 | `    "movi v19.4s, #0\n\t" \` | Sets the sum register `v19` to 0. |
| 1230 | `    "movi v20.4s, #0\n\t" \` | Sets the sum register `v20` to 0. |
| 1231 | `    "movi v21.4s, #0\n\t" \` | Sets the sum register `v21` to 0. |
| 1232 | `    "movi v22.4s, #0\n\t" \` | Sets the sum register `v22` to 0. |
| 1233 | `    "movi v23.4s, #0\n\t"` | Sets the sum register `v23` to 0. This is the last line of `ACC_ZERO`. |
| 1234 | `#define CONST_ONE \` | Starts the macro `CONST_ONE`: a piece of assembly text with 8 `movi` instructions. |
| 1235 | `    "movi v24.4s, #1\n\t" \` | `movi v24.4s, #1` sets each of the four 32-bit lanes of `v24` to 1. |
| 1236 | `    "movi v25.4s, #1\n\t" \` | Sets each 32-bit lane of `v25` to 1. |
| 1237 | `    "movi v26.4s, #1\n\t" \` | Sets each 32-bit lane of `v26` to 1. |
| 1238 | `    "movi v27.4s, #1\n\t" \` | Sets each 32-bit lane of `v27` to 1. |
| 1239 | `    "movi v28.4s, #1\n\t" \` | Sets each 32-bit lane of `v28` to 1. |
| 1240 | `    "movi v29.4s, #1\n\t" \` | Sets each 32-bit lane of `v29` to 1. |
| 1241 | `    "movi v30.4s, #1\n\t" \` | Sets each 32-bit lane of `v30` to 1. |
| 1242 | `    "movi v31.4s, #1\n\t"` | Sets each 32-bit lane of `v31` to 1. This is the last line of `CONST_ONE`. |
| 1243 | `#define VADD(a, b) "add v" #a ".2d, v" #a ".2d, v" #b ".2d\n\t"` | `VADD(a, b)` writes the text of one instruction: `add va.2d, va.2d, vb.2d`. `#a` and `#b` put the two numbers into the register names. The instruction adds the register b to the register a as two 64-bit numbers. |

### Macro `DEF_READ_ADD` and the kernels `read_dadd2` to `read_dadd16` and `read_iadd16` (lines 1244 to 1283)

| Line | Source | Explanation |
|---:|---|---|
| 1244 | `#define DEF_READ_ADD(name, init, adds) \` | Starts the macro `DEF_READ_ADD(name, init, adds)`. It creates one kernel function: the `asmread` loop with vector adds. |
| 1245 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (lines 1137 to 1151). |
| 1246 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 1247 | `    { \` | Opens the body of the kernel function. |
| 1248 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 1249 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 1250 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 1251 | `            init \` | `init`: the assembly text of the second macro argument. It stands before the loop label. So it runs once per call. |
| 1252 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loops of the five kernels start at an address of 20 modulo 64 [Ref1]. |
| 1253 | `            "ldp q0, q1, [%[p]]\n\t" \` | Loads the bytes 0 to 31 of the current block of 256 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 1254 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 1255 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 1256 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. |
| 1257 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 1258 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 1259 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 1260 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once. |
| 1261 | `            adds \` | `adds`: the assembly text of the third macro argument, the vector adds. They run in every loop pass, after the 8 loads. |
| 1262 | `            "add %[p], %[p], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 1263 | `            "cmp %[p], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 1264 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. |
| 1265 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 1266 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 1267 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 1268 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, as in `k_asmread` [Ref1]. |
| 1269 | `              "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23", \` | Continues the clobber list: `v16` to `v23`, the sum registers. The function does not store the sums and does not return them. In the listing of `bwx12` only the load of `d8` to `d15` and `ret` follow the loop [Ref1]. |
| 1270 | `              "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31", \` | Continues the clobber list: `v24` to `v31`, the registers of the constants. |
| 1271 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 1272 | `    }` | Ends the kernel function and the macro. |
| 1273 | `DEF_READ_ADD(read_dadd2, ACC_ZERO, VADD(16, 0) VADD(17, 8))` | Creates `k_read_dadd2`, the kernel `read_dadd2`. `init` is `ACC_ZERO`. The loop has 2 vector adds per 256 B: `v0` is added to `v16`, and `v8` to `v17`. So 2 of the 16 loaded registers are inputs of an add. The other 14 loaded values are not used. In `bwx12` one loop pass is 13 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 1274 | `DEF_READ_ADD(read_dadd4, ACC_ZERO, VADD(16, 0) VADD(17, 4) VADD(18, 8) VADD(19, 12))` | Creates `k_read_dadd4`, the kernel `read_dadd4`. `init` is `ACC_ZERO`. The loop has 4 vector adds per 256 B: `v0`, `v4`, `v8` and `v12` are added to `v16`, `v17`, `v18` and `v19`. The other 12 loaded values are not used. In `bwx12` one loop pass is 15 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 1275 | `DEF_READ_ADD(read_dadd8, ACC_ZERO,` | Starts the definition of `k_read_dadd8`, the kernel `read_dadd8`. `init` is `ACC_ZERO`. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 1276 | `             VADD(16, 0) VADD(17, 2) VADD(18, 4) VADD(19, 6) VADD(20, 8) VADD(21, 10) VADD(22, 12) VADD(23, 14))` | The third argument: 8 vector adds per 256 B. `v0`, `v2`, `v4`, `v6`, `v8`, `v10`, `v12` and `v14` are added to `v16` to `v23`. So every second loaded register is an input of an add. The other 8 loaded values are not used. In `bwx12` one loop pass is 19 instructions [Ref1]. |
| 1277 | `DEF_READ_ADD(read_dadd16, ACC_ZERO,` | Starts the definition of `k_read_dadd16`, the kernel `read_dadd16`. `init` is `ACC_ZERO`. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 1278 | `             VADD(16, 0) VADD(17, 1) VADD(18, 2) VADD(19, 3) VADD(20, 4) VADD(21, 5) VADD(22, 6) VADD(23, 7)` | The first 8 of its 16 vector adds: `v0` to `v7` are added to `v16` to `v23`. |
| 1279 | `             VADD(16, 8) VADD(17, 9) VADD(18, 10) VADD(19, 11) VADD(20, 12) VADD(21, 13) VADD(22, 14) VADD(23, 15))` | The other 8 vector adds: `v8` to `v15` are added to `v16` to `v23`. So every loaded register is an input of one add: 16 adds per 256 B. In `bwx12` one loop pass is 27 instructions [Ref1]. |
| 1280 | `DEF_READ_ADD(read_iadd16, ACC_ZERO CONST_ONE,` | Starts the definition of `k_read_iadd16`, the kernel `read_iadd16`. `init` is `ACC_ZERO` followed by `CONST_ONE`: 16 `movi` instructions run once per call. The whole-chip test of 2026-11-17 does not run this kernel [Ref4]. |
| 1281 | `             VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27) VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31)` | The first 8 of its 16 vector adds: the constants `v24` to `v31` are added to `v16` to `v23`. |
| 1282 | `             VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27) VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31))` | The same 8 adds once more. So the loop has 16 vector adds per 256 B, and no add takes a loaded register. The 16 loaded values are not used. In `bwx12` one loop pass is 27 instructions, as in `k_read_dadd16` [Ref1]. |

### Macro `DEF_READ_SP`: the `read_sparse` loop with another number of `nop` (lines 1284 to 1311)

| Line | Source | Explanation |
|---:|---|---|
| 1284 | `/* DEF_READ_SP(name, nops): the text of read_sparse with "nops" nop` | Comment: `DEF_READ_SP(name, nops)` is the text of `read_sparse` (line 652) with another number of `nop` instructions. The macro argument `nops` gives the number. |
| 1285 | ` * instructions in place of 9. Per 128 B: 4 ldp, the nop, add, cmp, b.lo. */` | Comment: `read_sparse` has 9 `nop` in that place. Per 128 B the loop has 4 `ldp`, the `nop` instructions, `add`, `cmp` and `b.lo`. |
| 1286 | `#define DEF_READ_SP(name, nops) \` | Starts the macro `DEF_READ_SP(name, nops)`. It creates one kernel function. |
| 1287 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (lines 1152 to 1166). |
| 1288 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 1289 | `    { \` | Opens the body of the kernel function. |
| 1290 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 1291 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 1292 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 1293 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loops of the five kernels start at an address of 20 modulo 64 [Ref1]. |
| 1294 | `            "ldp q0, q1, [%[p]]\n\t" \` | Loads the bytes 0 to 31 of the current block of 128 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 1295 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 1296 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 1297 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. One loop pass has 4 load instructions. It reads 128 B, each byte once. Nothing uses the loaded values. |
| 1298 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the macro argument into text. The assembler writes the instruction `nop` that many times. A `nop` does nothing. |
| 1299 | `            "add %[p], %[p], #128\n\t" \` | Moves the read pointer forward by 128 B. |
| 1300 | `            "cmp %[p], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 1301 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. |
| 1302 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 1303 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 1304 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc"); \` | The clobber list: the vector registers `v0` to `v7`, memory and the condition flags. It names none of `v8` to `v15`. So gcc saves no register in these functions [Ref1]. |
| 1305 | `    }` | Ends the kernel function and the macro. |
| 1306 | `DEF_READ_SP(read_sp24, 24)` | Creates the kernel `read_sp24`: 4 `ldp` and 24 `nop` per 128 B. In `bwx12` one loop pass is 31 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1307 | `DEF_READ_SP(read_sp32, 32)` | Creates the kernel `read_sp32`: 4 `ldp` and 32 `nop` per 128 B. In `bwx12` one loop pass is 39 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1308 | `DEF_READ_SP(read_sp40, 40)` | Creates the kernel `read_sp40`: 4 `ldp` and 40 `nop` per 128 B. In `bwx12` one loop pass is 47 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1309 | `DEF_READ_SP(read_sp48, 48)` | Creates the kernel `read_sp48`: 4 `ldp` and 48 `nop` per 128 B. In `bwx12` one loop pass is 55 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1310 | `DEF_READ_SP(read_sp56, 56)` | Creates the kernel `read_sp56`: 4 `ldp` and 56 `nop` per 128 B. In `bwx12` one loop pass is 63 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |

### Function `k_read_1pl_nop96`: the `read_1pl` loop with 96 `nop` (lines 1312 to 1333)

| Line | Source | Explanation |
|---:|---|---|
| 1312 | `/* read_1pl_nop96: the text of read_1pl with 96 nop after the four loads. It` | Comment: `read_1pl_nop96` is the text of `read_1pl` (line 988) with 96 `nop` after the four loads. |
| 1313 | ` * reads bytes 0 to 15 of every 64 B line and no other byte. */` | Comment: the kernel reads the bytes 0 to 15 of every 64 B line and no other byte. A 64 B line is a block of 64 B of memory, a cache line. |
| 1314 | `PLACE(read_1pl_nop96);` | `PLACE` adds the pad of this kernel. It is the pad of `read_1pl`, 16 bytes with the default values (line 1168). |
| 1315 | `__attribute__((noinline)) static void k_read_1pl_nop96(const uint64_t *a, size_t n)` | Starts the function `k_read_1pl_nop96`, the kernel `read_1pl_nop96`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. The whole-chip test of 2026-11-17 does not run this kernel. The test runs `read_1pl`, which has no `nop` [Ref4]. |
| 1316 | `{` | Opens the body of `k_read_1pl_nop96`. |
| 1317 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 1318 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. |
| 1319 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 1320 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loop starts at an address of 20 modulo 64 [Ref1]. |
| 1321 | `        "ldr q0, [%[p]]\n\t"` | `ldr` loads 16 B from memory into one vector register: the bytes 0 to 15 of the current block of 256 B into `q0`. |
| 1322 | `        "ldr q1, [%[p], #64]\n\t"` | Loads the bytes 64 to 79 of the block into `q1`. |
| 1323 | `        "ldr q2, [%[p], #128]\n\t"` | Loads the bytes 128 to 143 of the block into `q2`. |
| 1324 | `        "ldr q3, [%[p], #192]\n\t"` | Loads the bytes 192 to 207 of the block into `q3`. So one loop pass handles a block of 256 B and loads 16 B at the start of each of its four 64 B lines: 64 B in all. Nothing uses the loaded values. |
| 1325 | `        ".rept 96\n\tnop\n\t.endr\n\t"` | The assembler writes the instruction `nop` 96 times here. A `nop` does nothing. |
| 1326 | `        "add %[p], %[p], #256\n\t"` | Moves the read pointer forward by 256 B. |
| 1327 | `        "cmp %[p], %[end]\n\t"` | Compares the read pointer with `end`. |
| 1328 | `        "b.lo 1b\n\t"` | Branches back to the label `1` while the pointer is below `end`. In `bwx12` one loop pass is 103 instructions: 4 `ldr`, 96 `nop`, `add`, `cmp` and the branch [Ref1]. |
| 1329 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 1330 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 1331 | `        : "v0", "v1", "v2", "v3", "memory", "cc");` | The clobber list: the vector registers `v0` to `v3`, memory and the condition flags. gcc saves no register in this function. |
| 1332 | `}` | Ends the function `k_read_1pl_nop96`. |

### Macro `DEF_ASMWRITE_NOP`: the write loop with `nop` (lines 1334 to 1365)

| Line | Source | Explanation |
|---:|---|---|
| 1334 | `/* DEF_ASMWRITE_NOP(name, nops): the text of DEF_ASMWRITE with "nops" nop` | Comment: `DEF_ASMWRITE_NOP(name, nops)` is the text of `DEF_ASMWRITE` (line 671) with `nop` instructions added. The macro argument `nops` gives their number. |
| 1335 | ` * instructions after the 8 stp and before the add. */` | Comment: the `nop` instructions stand after the 8 `stp` and before the `add`. |
| 1336 | `#define DEF_ASMWRITE_NOP(name, nops) \` | Starts the macro `DEF_ASMWRITE_NOP(name, nops)`. It creates one write kernel. |
| 1337 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (lines 1170 to 1181). |
| 1338 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores the value `v` to `n` 8-byte words, from the address `a` on. |
| 1339 | `    { \` | Opens the body of the kernel function. |
| 1340 | `        uint64_t *p = a; \` | `p`: the write pointer. It starts at `a`. |
| 1341 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 1342 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 1343 | `            "dup v0.2d, %[v]\n\t" \` | `dup` copies the 8-byte value `v` into both halves of the 16-byte vector register `v0`. It stands before the loop label, so it runs once per call. |
| 1344 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loops of the four kernels start at an address of 40 modulo 64, the loop offset of `k_asmwrite` [Ref1]. |
| 1345 | `            "stp q0, q0, [%[p]]\n\t" \` | `stp` stores two 16-byte vector registers to memory, which is 32 B. Here both are `q0`. This instruction writes the bytes 0 to 31 of the current block of 256 B. |
| 1346 | `            "stp q0, q0, [%[p], #32]\n\t" \` | Stores `q0` twice to the bytes 32 to 63 of the block. |
| 1347 | `            "stp q0, q0, [%[p], #64]\n\t" \` | Stores `q0` twice to the bytes 64 to 95 of the block. |
| 1348 | `            "stp q0, q0, [%[p], #96]\n\t" \` | Stores `q0` twice to the bytes 96 to 127 of the block. |
| 1349 | `            "stp q0, q0, [%[p], #128]\n\t" \` | Stores `q0` twice to the bytes 128 to 159 of the block. |
| 1350 | `            "stp q0, q0, [%[p], #160]\n\t" \` | Stores `q0` twice to the bytes 160 to 191 of the block. |
| 1351 | `            "stp q0, q0, [%[p], #192]\n\t" \` | Stores `q0` twice to the bytes 192 to 223 of the block. |
| 1352 | `            "stp q0, q0, [%[p], #224]\n\t" \` | Stores `q0` twice to the bytes 224 to 255 of the block. One loop pass has 8 store instructions. It writes 256 B, each byte once. |
| 1353 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the macro argument into text. The assembler writes the instruction `nop` that many times. |
| 1354 | `            "add %[p], %[p], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 1355 | `            "cmp %[p], %[end]\n\t" \` | Compares the write pointer with `end`. |
| 1356 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. |
| 1357 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 1358 | `            : [end] "r"(end), [v] "r"(v) \` | `end` and `v` are inputs in general registers. |
| 1359 | `            : "v0", "memory", "cc"); \` | The clobber list: the vector register `v0`, memory and the condition flags. gcc saves no register in these functions. |
| 1360 | `    }` | Ends the kernel function and the macro. |
| 1361 | `DEF_ASMWRITE_NOP(write_nop32, 32)` | Creates the kernel `write_nop32`: 8 `stp` and 32 `nop` per 256 B. In `bwx12` one loop pass is 43 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1362 | `DEF_ASMWRITE_NOP(write_nop96, 96)` | Creates the kernel `write_nop96`: 8 `stp` and 96 `nop` per 256 B. In `bwx12` one loop pass is 107 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1363 | `DEF_ASMWRITE_NOP(write_nop128, 128)` | Creates the kernel `write_nop128`: 8 `stp` and 128 `nop` per 256 B. In `bwx12` one loop pass is 139 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1364 | `DEF_ASMWRITE_NOP(write_nop256, 256)` | Creates the kernel `write_nop256`: 8 `stp` and 256 `nop` per 256 B. In `bwx12` one loop pass is 267 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |

### Macro `DEF_ASMCOPY_NOP`: the copy loop with `nop` (lines 1366 to 1405)

| Line | Source | Explanation |
|---:|---|---|
| 1366 | `/* DEF_ASMCOPY_NOP(name, nops): the text of DEF_ASMCOPY with "nops" nop` | Comment: `DEF_ASMCOPY_NOP(name, nops)` is the text of `DEF_ASMCOPY` (line 698) with `nop` instructions added. The macro argument `nops` gives their number. |
| 1367 | ` * instructions after the 8 stp and before the two adds. */` | Comment: the `nop` instructions stand after the 8 `stp` and before the two `add`. |
| 1368 | `#define DEF_ASMCOPY_NOP(name, nops) \` | Starts the macro `DEF_ASMCOPY_NOP(name, nops)`. It creates one copy kernel. |
| 1369 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (lines 1182 to 1187). |
| 1370 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 1371 | `    { \` | Opens the body of the kernel function. |
| 1372 | `        uint64_t *dp = d; \` | `dp`: the write pointer in the destination. It starts at `d`. |
| 1373 | `        const uint64_t *sp = s; \` | `sp`: the read pointer in the source. It starts at `s`. |
| 1374 | `        const uint64_t *end = s + n; \` | `end`: the first address after the source range: `s` plus `n` words. |
| 1375 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 1376 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx12` the loops of the two kernels start at an address of 52 modulo 64, the loop offset of `k_asmcopy` [Ref1]. |
| 1377 | `            "ldp q0, q1, [%[s]]\n\t" \` | Loads the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 1378 | `            "ldp q2, q3, [%[s], #32]\n\t" \` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 1379 | `            "ldp q4, q5, [%[s], #64]\n\t" \` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 1380 | `            "ldp q6, q7, [%[s], #96]\n\t" \` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 1381 | `            "ldp q8, q9, [%[s], #128]\n\t" \` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 1382 | `            "ldp q10, q11, [%[s], #160]\n\t" \` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 1383 | `            "ldp q12, q13, [%[s], #192]\n\t" \` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 1384 | `            "ldp q14, q15, [%[s], #224]\n\t" \` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass loads 256 B from the source buffer with 8 `ldp`. |
| 1385 | `            "stp q0, q1, [%[d]]\n\t" \` | Stores `q0` and `q1` to the bytes 0 to 31 of the current destination block. `stp` stores two 16-byte vector registers. |
| 1386 | `            "stp q2, q3, [%[d], #32]\n\t" \` | Stores `q2` and `q3` to the bytes 32 to 63 of the destination block. |
| 1387 | `            "stp q4, q5, [%[d], #64]\n\t" \` | Stores `q4` and `q5` to the bytes 64 to 95 of the destination block. |
| 1388 | `            "stp q6, q7, [%[d], #96]\n\t" \` | Stores `q6` and `q7` to the bytes 96 to 127 of the destination block. |
| 1389 | `            "stp q8, q9, [%[d], #128]\n\t" \` | Stores `q8` and `q9` to the bytes 128 to 159 of the destination block. |
| 1390 | `            "stp q10, q11, [%[d], #160]\n\t" \` | Stores `q10` and `q11` to the bytes 160 to 191 of the destination block. |
| 1391 | `            "stp q12, q13, [%[d], #192]\n\t" \` | Stores `q12` and `q13` to the bytes 192 to 223 of the destination block. |
| 1392 | `            "stp q14, q15, [%[d], #224]\n\t" \` | Stores `q14` and `q15` to the bytes 224 to 255 of the destination block. One loop pass stores 256 B to the destination buffer with 8 `stp`. Each loaded register is stored once and has no other use. |
| 1393 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the macro argument into text. The assembler writes the instruction `nop` that many times. |
| 1394 | `            "add %[s], %[s], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 1395 | `            "add %[d], %[d], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 1396 | `            "cmp %[s], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 1397 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the read pointer is below `end`. |
| 1398 | `            : [s] "+r"(sp), [d] "+r"(dp) \` | `sp` and `dp` are in general registers. The text reads them and changes them. |
| 1399 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 1400 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 1401 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop. |
| 1402 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 1403 | `    }` | Ends the kernel function and the macro. |
| 1404 | `DEF_ASMCOPY_NOP(copy_nop96, 96)` | Creates the copy kernel `copy_nop96`: 8 `ldp`, 8 `stp` and 96 `nop` per 256 B. In `bwx12` one loop pass is 116 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |
| 1405 | `DEF_ASMCOPY_NOP(copy_nop192, 192)` | Creates the copy kernel `copy_nop192`: 8 `ldp`, 8 `stp` and 192 `nop` per 256 B. In `bwx12` one loop pass is 212 instructions [Ref1]. The whole-chip test of 2026-11-17 does not run it [Ref4]. |

### Stand-ins of the kernels of round 5 (lines 1406 to 1439)

| Line | Source | Explanation |
|---:|---|---|
| 1406 | `#else` | `#else` of the `#if` of line 1201. The lines up to line 1437 are compiled only when the target is not AArch64. In that case each kernel of lines 1273 to 1405 becomes a plain C loop. The CRB binary of `bwx12` does not hold this branch: the header of every csv file of the whole-chip test says `kernels=aarch64` [Ref5]. |
| 1407 | `/* Stand-ins. A nop and a vector add of registers touch no byte. So the` | Comment: the stand-ins of the kernels of this block. A `nop` and a vector add of registers touch no byte of memory. |
| 1408 | ` * stand-in of a read_dadd, read_iadd or read_sp kernel is the stand-in of` | Comment: so the stand-in of a `read_dadd`, `read_iadd` or `read_sp` kernel is the stand-in of `asmread` (lines 858 to 865). |
| 1409 | ` * asmread: these kernels read every byte of the range. The stand-in of` | Comment: the reason: these kernels read every byte of the range. The sentence about `read_1pl_nop96` starts here. |
| 1410 | ` * read_1pl_nop96 is the stand-in of read_1pl: the first two words (16 B) of` | Comment: the stand-in of `read_1pl_nop96` has the loop of the stand-in of `read_1pl` (lines 1014 to 1021). It reads the first two words, which are 16 B, of every 64 B line. |
| 1411 | ` * every 64 B line. The stand-ins of the write and copy kernels are the` | Comment: the stand-ins of the `write_nop` kernels and of the `copy_nop` kernels are the stand-ins of `asmwrite` and `asmcopy`. |
| 1412 | ` * stand-ins of asmwrite and asmcopy. */` | Comment: the end of the sentence of line 1411. |
| 1413 | `DEF_ASMREAD(read_dadd2, 0)` | Stand-in build only: defines `k_read_dadd2` as the plain read loop of lines 858 to 865, which reads every word of the range. |
| 1414 | `DEF_ASMREAD(read_dadd4, 0)` | Stand-in build only: defines `k_read_dadd4` as the plain read loop. |
| 1415 | `DEF_ASMREAD(read_dadd8, 0)` | Stand-in build only: defines `k_read_dadd8` as the plain read loop. |
| 1416 | `DEF_ASMREAD(read_dadd16, 0)` | Stand-in build only: defines `k_read_dadd16` as the plain read loop. |
| 1417 | `DEF_ASMREAD(read_iadd16, 0)` | Stand-in build only: defines `k_read_iadd16` as the plain read loop. |
| 1418 | `DEF_ASMREAD(read_sp24, 24)` | Stand-in build only: defines `k_read_sp24` as the plain read loop. The stand-in macro does not use the number 24. |
| 1419 | `DEF_ASMREAD(read_sp32, 32)` | Stand-in build only: defines `k_read_sp32` as the plain read loop. The number 32 is not used. |
| 1420 | `DEF_ASMREAD(read_sp40, 40)` | Stand-in build only: defines `k_read_sp40` as the plain read loop. The number 40 is not used. |
| 1421 | `DEF_ASMREAD(read_sp48, 48)` | Stand-in build only: defines `k_read_sp48` as the plain read loop. The number 48 is not used. |
| 1422 | `DEF_ASMREAD(read_sp56, 56)` | Stand-in build only: defines `k_read_sp56` as the plain read loop. The number 56 is not used. |
| 1423 | `PLACE(read_1pl_nop96);` | `PLACE` adds the pad of `read_1pl_nop96`, as in the AArch64 branch. |
| 1424 | `__attribute__((noinline)) static void k_read_1pl_nop96(const uint64_t *a, size_t n)` | Starts the stand-in function `k_read_1pl_nop96`. A build on CRB, an Arm machine, does not compile it. |
| 1425 | `{` | Opens the body of the stand-in. |
| 1426 | `    const volatile uint64_t *p = a;` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 1427 | `    for (size_t i = 0; i < n; i += 8) {` | A loop over the range in steps of 8 words, which are 64 B. |
| 1428 | `        (void)p[i];` | Reads the first word of the 64 B line and drops the value. |
| 1429 | `        (void)p[i + 1];` | Reads the second word of the 64 B line and drops the value. So the loop reads 16 B of every 64 B. |
| 1430 | `    }` | Ends the loop of line 1427. |
| 1431 | `}` | Ends the stand-in function `k_read_1pl_nop96`. |
| 1432 | `DEF_ASMWRITE(write_nop32)` | Stand-in build only: defines `k_write_nop32` as the plain write loop of lines 866 to 872. |
| 1433 | `DEF_ASMWRITE(write_nop96)` | Stand-in build only: defines `k_write_nop96` as the plain write loop. |
| 1434 | `DEF_ASMWRITE(write_nop128)` | Stand-in build only: defines `k_write_nop128` as the plain write loop. |
| 1435 | `DEF_ASMWRITE(write_nop256)` | Stand-in build only: defines `k_write_nop256` as the plain write loop. |
| 1436 | `DEF_ASMCOPY(copy_nop96)` | Stand-in build only: defines `k_copy_nop96` as the plain copy loop of lines 873 to 879. |
| 1437 | `DEF_ASMCOPY(copy_nop192)` | Stand-in build only: defines `k_copy_nop192` as the plain copy loop. |
| 1438 | `#endif` | Ends the `#if` of line 1201. |

### Third pad after the kernels: the start address of `call` (lines 1440 to 1451)

| Line | Source | Explanation |
|---:|---|---|
| 1440 | `/*` | Opens the comment about the third pad. |
| 1441 | ` * The pad after the kernels, a third time. The pad of bwx11 above now stands` | Comment: the pad after the kernels is needed a third time. The pad of `bwx11` (line 1075) now stands before the kernels of round 5. |
| 1442 | ` * before the kernels of round 5, so it no longer places call(). This pad has` | Comment: so the pad of `bwx11` no longer sets the start address of `call`. |
| 1443 | ` * the same value, and the function after the kernels starts at that value` | Comment: the new pad has the same value. The function after the kernels then starts at that value modulo 64. |
| 1444 | ` * modulo 64, as in bwx11, bwx10 and bwx8. build12.sh prints the placement.` | Comment: that is the start address modulo 64 that this function has in `bwx11`, `bwx10` and `bwx8`. The script `build12.sh` in the code folder `bwx12-2026-11-15` prints the placement. |
| 1445 | ` */` | Ends the comment. |
| 1446 | `#ifndef PAD_after_kernels12` | Compiles line 1447 only when the build command has not defined `PAD_after_kernels12`. |
| 1447 | `#define PAD_after_kernels12 PAD_after_kernels` | `PAD_after_kernels12` gets the value of `PAD_after_kernels`, which is 24 (line 1037). |
| 1448 | `#endif` | Ends the `#ifndef` of line 1446. |
| 1449 | `PLACE(after_kernels12);` | `PLACE(after_kernels12)` pads the code up to a 64 B boundary and then adds 24 bytes of value 0. So the function after it starts at 24 modulo 64. In `bwx12` that function is `call` (line 1491): the build record of CRB gives `call=24` for the start of `call` modulo 64 [Ref2]. |
| 1450 | `/* bwx12- */` | Comment: a marker. The block that line 1077 opened ends here. |

### The kernel table `kernels` (lines 1452 to 1486)

| Line | Source | Explanation |
|---:|---|---|
| 1452 | `/* The function is named k_<name>. The cast to void (*)(void) is undone by` | Comment: the function of a kernel has the name `k_` plus the kernel name. The table stores its address with a cast to the common pointer type `void (*)(void)`. |
| 1453 | ` * call() according to the type. */` | Comment: `call` (line 1491) undoes the cast according to the type of the kernel. |
| 1454 | `static const struct kdef {` | Starts `struct kdef`, the type of one entry of the kernel table. |
| 1455 | `    const char *name;` | `name`: the name of the kernel. It is the word that `--seq` accepts. `parse_seq` (line 1750) compares each word of `--seq` with the names and stores the index of the entry that matches. |
| 1456 | `    enum ktype type;` | `type`: one of `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD` (line 253). It tells `call` which arguments the function takes. |
| 1457 | `    void (*fn)(void);` | `fn`: the pointer to the kernel function, stored as one common pointer type. `call` casts it back to the real type before it calls the function. |
| 1458 | `} kernels[] = {` | Ends the structure and starts the kernel table `kernels[]`. For each interval the worker takes the entry of the kernel from this table (line 1658) and passes it to `call`. |
| 1459 | `#define K(name, type) { #name, type, (void (*)(void))k_##name }` | The macro `K(name, type)` writes one entry. `K(read, T_READ)` becomes `{ "read", T_READ, (void (*)(void))k_read }`. `#name` gives the kernel name as text. `k_##name` gives the function. |
| 1460 | `    K(read, T_READ), K(write, T_WRITE), K(copy, T_COPY),` | Entries 0 to 2: `read`, `write` and `copy`, the C kernels with NEON intrinsics. `read` is entry 0 with the type `T_READ`: the new read kernel, a kernel of the whole-chip test [Ref4]. |
| 1461 | `    K(asmread, T_READ), K(asmwrite, T_WRITE), K(asmcopy, T_COPY),` | Entries 3 to 5: `asmread`, `asmwrite` and `asmcopy`, the hand-written assembly kernels. `asmread` is entry 3 with the type `T_READ`. It is a kernel of the whole-chip test [Ref4]. |
| 1462 | `    K(oldread, T_OLDREAD), K(oldwrite, T_WRITE), K(oldcopy, T_COPY),` | Entries 6 to 8: `oldread`, `oldwrite` and `oldcopy`, the old kernels. `oldread` is entry 6 with the type `T_OLDREAD`: the old read kernel, a kernel of the whole-chip test [Ref4]. |
| 1463 | `    K(asmread2, T_READ), K(asmwrite2, T_WRITE), K(asmcopy2, T_COPY), K(oldread2, T_OLDREAD),` | Entries 9 to 12: the A/A copies `asmread2`, `asmwrite2`, `asmcopy2` and `oldread2`. |
| 1464 | `    K(asmcopy_c, T_COPY), K(asmcopy_c_add, T_COPY), K(asmcopy_c_reg, T_COPY),` | Entries 13 to 15: the copy kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. |
| 1465 | `    K(read_nop4, T_READ), K(read_nop8, T_READ), K(read_nop16, T_READ), K(read_nop32, T_READ),` | Entries 16 to 19: the read kernels `read_nop4`, `read_nop8`, `read_nop16` and `read_nop32`. |
| 1466 | `    K(read_sparse, T_READ),` | Entry 20: the read kernel `read_sparse`. The entries 0 to 20 are the kernels that the first runner `bwx` and the version `bwx8` already have. |
| 1467 | `/* bwx10+ */` | Comment: a marker. The entries that the version `bwx10` added start here. |
| 1468 | `    K(read_pf256, T_READ), K(read_pf512, T_READ), K(read_pf1024, T_READ), K(read_pf2048, T_READ),` | Entries 21 to 24: the read kernels `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048`. |
| 1469 | `    K(read_1pl, T_READ),` | Entry 25: `read_1pl` with the type `T_READ`. It is a kernel of the whole-chip test [Ref4]. The entries 21 to 25 are the 5 kernels that `bwx10` added. |
| 1470 | `/* bwx10- */` | Comment: a marker. The entries of `bwx10` end here. |
| 1471 | `/* bwx11+ */` | Comment: a marker. The entries that the version `bwx11` added start here. |
| 1472 | `    K(read_nop64, T_READ), K(read_nop96, T_READ), K(read_nop128, T_READ),` | Entries 26 to 28: `read_nop64`, `read_nop96` and `read_nop128`, the 3 kernels that `bwx11` added. `read_nop96`, a kernel of the whole-chip test, is entry 27 with the type `T_READ` [Ref4]. |
| 1473 | `/* bwx11- */` | Comment: a marker. The entries of `bwx11` end here. |
| 1474 | `/* bwx12+ */` | Comment: a marker. The entries that the version `bwx12` added start here. |
| 1475 | `    K(read_nop48, T_READ), K(read_nop56, T_READ), K(read_nop72, T_READ), K(read_nop80, T_READ), K(read_nop88, T_READ),` | Entries 29 to 33: the read kernels `read_nop48`, `read_nop56`, `read_nop72`, `read_nop80` and `read_nop88`. |
| 1476 | `    K(read_nop112, T_READ), K(read_nop160, T_READ), K(read_nop192, T_READ), K(read_nop256, T_READ),` | Entries 34 to 37: `read_nop112`, `read_nop160`, `read_nop192` and `read_nop256`. `read_nop256`, a kernel of the whole-chip test, is entry 37 with the type `T_READ`. The test runs no other kernel of lines 1475 to 1481 [Ref4]. |
| 1477 | `    K(read_dadd2, T_READ), K(read_dadd4, T_READ), K(read_dadd8, T_READ), K(read_dadd16, T_READ), K(read_iadd16, T_READ),` | Entries 38 to 42: the read kernels `read_dadd2`, `read_dadd4`, `read_dadd8`, `read_dadd16` and `read_iadd16`. |
| 1478 | `    K(read_sp24, T_READ), K(read_sp32, T_READ), K(read_sp40, T_READ), K(read_sp48, T_READ), K(read_sp56, T_READ),` | Entries 43 to 47: the read kernels `read_sp24`, `read_sp32`, `read_sp40`, `read_sp48` and `read_sp56`. |
| 1479 | `    K(read_1pl_nop96, T_READ),` | Entry 48: the read kernel `read_1pl_nop96`. |
| 1480 | `    K(write_nop32, T_WRITE), K(write_nop96, T_WRITE), K(write_nop128, T_WRITE), K(write_nop256, T_WRITE),` | Entries 49 to 52: the write kernels `write_nop32`, `write_nop96`, `write_nop128` and `write_nop256`, with the type `T_WRITE`. |
| 1481 | `    K(copy_nop96, T_COPY), K(copy_nop192, T_COPY),` | Entries 53 and 54: the copy kernels `copy_nop96` and `copy_nop192`, with the type `T_COPY`. The entries 29 to 54 are the 26 kernels of round 5 (line 9). |
| 1482 | `/* bwx12- */` | Comment: a marker. The entries of `bwx12` end here. |
| 1483 | `#undef K` | Removes the macro `K`. It is needed only inside the table. |
| 1484 | `};` | Ends the kernel table. |
| 1485 | `#define K_COUNT ((int)(sizeof kernels / sizeof kernels[0]))` | `K_COUNT`: the number of entries of the table. It is the size of the table divided by the size of one entry. In `bwx12` it is 55, and the listing of the CRB build holds 55 kernel functions [Ref1]. The `--seq` lists of the whole-chip test name 6 of the 55 kernels [Ref4]. The worker calls `k_write` directly for the first touch (line 1646), not through the table. |

### Function `call`: run one kernel on one range of a buffer (lines 1487 to 1510)

| Line | Source | Explanation |
|---:|---|---|
| 1487 | `/* Runs kernel kd on len bytes at byte offset off of the thread's buffers. A` | Comment: the function below runs the kernel `kd` on `len` bytes that start at the byte offset `off` of the buffers of the thread. |
| 1488 | ` * read or write kernel uses buffer a. A copy kernel reads a and writes b. The` | Comment: a read kernel or a write kernel uses the buffer `a`. A copy kernel reads `a` and writes `b`. |
| 1489 | ` * sink of the old read kernel is on the stack of the thread, as it was in the` | Comment: the sink of the old read kernel is the variable that takes its sum. It lies on the stack of the thread (line 1635), as it did in the function `pass` of the old benchmark source. |
| 1490 | ` * old pass(), so the threads do not all store to one shared cache line. */` | Comment: so the threads do not all store to one shared cache line. |
| 1491 | `static void call(const struct kdef *kd, struct thread *t, size_t off, size_t len, uint64_t v, volatile uint64_t *sink)` | Starts the function `call`. It runs one kernel on one range of a buffer. `kd` is the table entry of the kernel. `t` is the record of the calling thread. `off` and `len` give the range in bytes. `v` is the value that a write kernel stores. `sink` points to the variable that takes the sum of an old read kernel. The worker calls this function once per interval for the warm-up pass (line 1669). With `--stop common` it calls it once for each chunk of the timed loop (line 1695). In the timed loop the function runs between the clock reads `t0` and `t1`. So its own instructions are part of the timed interval, once per chunk. |
| 1492 | `{` | Opens the body of `call`. |
| 1493 | `    uint64_t *a = t->a + off / 8;` | `a`: the address of the first word of the range. `t->a` points to 8-byte words. So `off / 8` words are `off` bytes. |
| 1494 | `    size_t n = len / 8;` | `n`: the length of the range in 8-byte words. One chunk of 2 MiB gives 262144 words. The warm-up pass of a `--seq` entry of 256 MiB gives 33554432 words. |
| 1495 | `    switch (kd->type) {` | Chooses the form of the call by the type of the kernel. |
| 1496 | `    case T_READ:` | The case of a read kernel. The kernels `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl` of the whole-chip test take this path [Ref4]. |
| 1497 | `        ((read_fn)kd->fn)(a, n);` | Casts the pointer to the type `read_fn` (line 254) and calls the kernel with the address and the word count. The kernel returns nothing. |
| 1498 | `        break;` | Leaves the `switch`. |
| 1499 | `    case T_OLDREAD:` | The case of an old read kernel. The kernel `oldread` of the whole-chip test takes this path [Ref4]. |
| 1500 | `        *sink = ((oldread_fn)kd->fn)(a, n);` | Calls the kernel, which returns its sum, and stores the sum to `*sink`. `sink` points to a `volatile` variable on the stack of the worker (line 1635). So the compiler must keep the store and must compute the sum. The listing of `k_oldread` in `bwx12` holds the adds [Ref1]. This path has one store of 8 bytes per call that the `T_READ` path does not have. In the timed loop of `--stop common` that is one store per chunk (line 1695). |
| 1501 | `        break;` | Leaves the `switch`. |
| 1502 | `    case T_WRITE:` | The case of a write kernel. No kernel in a `--seq` list of the whole-chip test has this type. So this case does not run in the test [Ref4]. |
| 1503 | `        ((write_fn)kd->fn)(a, n, v);` | Casts the pointer to the type `write_fn` and calls the write kernel with the address, the word count and the value `v` to store. |
| 1504 | `        break;` | Leaves the `switch`. |
| 1505 | `    case T_COPY:` | The case of a copy kernel. No kernel in a `--seq` list of the whole-chip test has this type. So this case does not run in the test [Ref4]. |
| 1506 | `        ((copy_fn)kd->fn)(t->b + off / 8, a, n);` | Casts the pointer to the type `copy_fn` and calls the copy kernel. The kernel reads the range of the buffer `a` and writes the same range of the buffer `b`. |
| 1507 | `        break;` | Leaves the `switch`. |
| 1508 | `    }` | Ends the `switch` of line 1495. |
| 1509 | `}` | Ends the function `call`. It returns no value. |

### Function `read_smaps`: the page state of the buffers (lines 1511 to 1543)

| Line | Source | Explanation |
|---:|---|---|
| 1511 | `/* Page state (handoff B.6). For each of the n buffers (a NULL entry is` | Comment: the function below reads the page state. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. The function works on `n` buffers and skips an entry that is `NULL`. |
| 1512 | ` * skipped): the entry of /proc/self/smaps whose start is the buffer and whose` | Comment: for each buffer it looks for the entry of the Linux file `/proc/self/smaps` whose start is the buffer address. |
| 1513 | ` * end is the buffer plus buf_len(). Without such an entry both values stay -1` | Comment: the end of that entry must be the buffer address plus `buf_len()`. Without such an entry both values stay -1. |
| 1514 | ` * and are printed as NA. */` | Comment: a value of -1 is printed as `NA`. |
| 1515 | `static void read_smaps(struct page *pg, uint64_t *const *buf, int n)` | Starts the function `read_smaps`. For each of the `n` buffer addresses in `buf` it looks for the mapping of that buffer in `/proc/self/smaps`. It writes two values to `pg`: the size of the mapping and the part of it on 2 MiB pages, both in kB. In a process with more than one thread `main` calls it before the first interval and after each interval (line 3111). During the call all workers wait at the barrier (line 1653 or line 1731). So the call is not timed. In the whole-chip test `main` calls it with 240 entries, two per thread. The 120 entries of the second buffers are `NULL`, and the function skips them [Ref4] [Ref5]. |
| 1516 | `{` | Opens the body of `read_smaps`. In a process with one thread the worker calls the function before each interval (line 1672): after the warm-up pass and before its barrier wait of line 1675. The timed interval starts later, at the clock read `t0` (line 1688). This call is not timed either. |
| 1517 | `    char line[256];` | `line`: the buffer for one line of the file, at most 255 characters. |
| 1518 | `    int cur = -1;` | `cur`: the index of the buffer whose mapping the loop below is reading, or -1 for no buffer. |
| 1519 | `    size_t len = buf_len();` | `len`: the buffer length from `buf_len` (line 426). It is 268435456 bytes in the whole-chip test [Ref4]. |
| 1520 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 1521 | `        pg[i].kb_total = pg[i].kb_huge = -1;` | Sets both values of the entry to -1. The value -1 means that the buffer was not found. |
| 1522 | `    FILE *f = fopen("/proc/self/smaps", "r");` | Opens `/proc/self/smaps` for reading. The file lists every memory mapping of the process. So it holds the buffers of all threads. |
| 1523 | `    if (!f)` | Tests whether the file did not open. |
| 1524 | `        return;` | In that case the function returns, and all values stay -1. |
| 1525 | `    while (fgets(line, sizeof line, f)) {` | Starts a loop that reads the file line by line. It ends at the end of the file. |
| 1526 | `        unsigned long s, e;` | `s` and `e`: the start address and the end address of a mapping. |
| 1527 | `        char perms[8];` | `perms`: the word after the two addresses, at most 7 characters. In the file it holds the access rights of the mapping. The function does not use its content. |
| 1528 | `        if (sscanf(line, "%lx-%lx %7s", &s, &e, perms) == 3) {` | `sscanf` returns 3 when the line starts with `start-end`, two hexadecimal addresses, and a word after them. Such a line is the first line of a mapping. |
| 1529 | `            cur = -1;` | At the first line of a mapping `cur` is first set back to -1. |
| 1530 | `            for (int i = 0; i < n; i++)` | Then a loop compares the mapping with every buffer. |
| 1531 | `                if (buf[i] && (unsigned long)(uintptr_t)buf[i] == s && e == s + len)` | A buffer matches when its entry is not `NULL`, the mapping starts at the buffer address and the mapping ends exactly `len` bytes after it. The comment of `alloc_buf` (lines 431 to 433) gives the reason for the exact test: no-access ranges stand before and after each buffer, so Linux lists the buffer as one mapping of its own. |
| 1532 | `                    cur = i;` | On a match `cur` becomes the index of that buffer. When no buffer matches, `cur` stays -1. Then the next lines of that mapping store nothing, and they cannot change the values of a buffer that was read before. |
| 1533 | `        } else if (cur >= 0) {` | Every other line belongs to the mapping whose first line was read last. This branch runs only when that mapping is a buffer (`cur >= 0`). |
| 1534 | `            sscanf(line, "Size: %ld kB", &pg[cur].kb_total);` | This `sscanf` stores a number only when the line starts with `Size:`. The number is the size of the mapping in kB and goes to `kb_total`. |
| 1535 | `            sscanf(line, "AnonHugePages: %ld kB", &pg[cur].kb_huge);` | This `sscanf` stores a number only when the line starts with `AnonHugePages:`. The number is the part of the mapping on 2 MiB pages in kB and goes to `kb_huge`. All other lines store nothing. |
| 1536 | `        }` | Ends the `else if` of line 1533. |
| 1537 | `    }` | Ends the loop of line 1525. |
| 1538 | `    fclose(f);` | Closes the file. |
| 1539 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 1540 | `        if (pg[i].kb_total < 0 \|\| pg[i].kb_huge < 0)` | Tests whether one of the two values of the entry is still below 0. |
| 1541 | `            pg[i].kb_total = pg[i].kb_huge = -1;` | In that case both values are set to -1. `print_p` (line 1570) prints a value below 0 as `NA`. In the whole-chip test every P row holds 262144 kB for both values [Ref5]. |
| 1542 | `}` | Ends the function `read_smaps`. |

### Function `read_vmstat`: four counters of the whole system (lines 1544 to 1561)

| Line | Source | Explanation |
|---:|---|---|
| 1544 | `/* Four counters of /proc/vmstat. They count for the whole system. -1: not found. */` | Comment: the function below reads four counters of the Linux file `/proc/vmstat`. They count for the whole system, not for one buffer. The value -1 means that a counter was not found. |
| 1545 | `static void read_vmstat(long long vm[4])` | Starts the function `read_vmstat`. It reads the four counters into `vm[0]` to `vm[3]`, in the order of the names in line 1547. They become the last four columns of every P row. In a process with more than one thread `main` calls it once before the first interval and once after each interval (line 3112). In a process with one thread the worker calls it before each interval (line 1673): after the warm-up pass and before its barrier wait of line 1675. The timed interval starts later, at the clock read `t0` (line 1688). It is not timed. |
| 1546 | `{` | Opens the body of `read_vmstat`. |
| 1547 | `    static const char *name[4] = { "thp_fault_alloc", "thp_fault_fallback", "thp_collapse_alloc", "pgmigrate_success" };` | `name`: the names of the four counters. The Linux documentation gives their meanings [Ref13]. `thp_fault_alloc` counts the 2 MiB pages that Linux gave at a page fault. `thp_fault_fallback` counts the page faults at which Linux could not give a 2 MiB page and used small pages. `thp_collapse_alloc` counts the 2 MiB pages that Linux made later from a range of small pages. `pgmigrate_success` counts the pages that Linux moved to another place in physical memory. |
| 1548 | `    char key[64];` | `key`: the buffer for one name of the file, at most 63 characters. |
| 1549 | `    long long val;` | `val`: the number that follows the name. |
| 1550 | `    for (int i = 0; i < 4; i++)` | A loop over the four values. |
| 1551 | `        vm[i] = -1;` | Sets the value to -1. The value -1 means that the counter was not found. |
| 1552 | `    FILE *f = fopen("/proc/vmstat", "r");` | Opens `/proc/vmstat` for reading. |
| 1553 | `    if (!f)` | Tests whether the file did not open. |
| 1554 | `        return;` | In that case the function returns with the four values at -1. |
| 1555 | `    while (fscanf(f, "%63s %lld", key, &val) == 2)` | Each line of the file holds a name and a number. `fscanf` reads one such pair per loop pass. The loop ends when `fscanf` finds no further pair, for example at the end of the file. |
| 1556 | `        for (int i = 0; i < 4; i++)` | A loop over the four names. |
| 1557 | `            if (!strcmp(key, name[i]))` | Tests whether the name from the file equals name `i`. `strcmp` returns 0 for equal texts. |
| 1558 | `                vm[i] = val;` | On a match the number goes to the matching place in `vm`. |
| 1559 | `    fclose(f);` | Closes the file. |
| 1560 | `}` | Ends the function `read_vmstat`. |

### Function `print_na`: one csv field, or `NA` (lines 1562 to 1569)

| Line | Source | Explanation |
|---:|---|---|
| 1562 | `static void print_na(long long v)` | Starts the function `print_na`. It prints one more field of a csv row: a comma and then the number `v`. For a negative `v` it prints `,NA`. The functions `read_smaps` (line 1515) and `read_vmstat` (line 1545) store -1 for a value that they did not find. So such a value shows as `NA` in a P row. |
| 1563 | `{` | Opens the body of `print_na`. |
| 1564 | `    if (v < 0)` | Tests whether `v` is negative. |
| 1565 | `        printf(",NA");` | A negative value prints as a comma and the text `NA` (not available). |
| 1566 | `    else` | The case of a value of 0 or more. |
| 1567 | `        printf(",%lld", v);` | Prints a comma and the number in decimal. |
| 1568 | `}` | Ends the function `print_na`. |

### Function `print_p`: one P row, the page state of one buffer (lines 1570 to 1579)

| Line | Source | Explanation |
|---:|---|---|
| 1570 | `static void print_p(int round, int pos, int tid, char buffer, const struct page *pg, const long long vm[4])` | Starts the function `print_p`. It prints one P row: the page state of one buffer at one reading. `round`, `pos` and `tid` are the round, the position and the thread index. `buffer` is the letter `a` or `b`. `pg` holds the two page values of the buffer. `vm` holds four counters of the Linux file `/proc/vmstat`. In a process with more than one thread `main` calls it once per buffer after each reading of the page state (line 3117). In a process with one thread `main` calls it in line 3073 and line 3075. |
| 1571 | `{` | Opens the body of `print_p`. |
| 1572 | `    printf("P,%d,%d,%d,%c", round, pos, tid, buffer);` | Columns 1 to 5 of the row: the letter `P`, the round, the position, the thread index and the buffer letter. The position is -1 in the rows of the reading before the first interval (line 3043). In every other row of a process with more than one thread it is the position of the interval that has ended directly before the reading. In a process with one thread the row holds the state that the worker read before the interval of that position (line 1670). In the whole-chip test the buffer letter is always `a` [Ref5]. |
| 1573 | `    print_na(pg->kb_total);` | Column 6, `kB_total`: the size of the mapping of the buffer. The unit is kB of 1024 bytes. `read_smaps` (line 1515) took the value from the line `Size` of the Linux file `/proc/self/smaps`. A value that it did not find prints as `NA`. |
| 1574 | `    print_na(pg->kb_huge);` | Column 7, `kB_huge`: the part of the buffer that lies on 2 MiB pages, in kB of 1024 bytes. `read_smaps` took it from the line `AnonHugePages` of the same file. In the whole-chip test columns 6 and 7 are both 262144 kB (256 MiB) in every P row [Ref5]. |
| 1575 | `    for (int i = 0; i < 4; i++)` | Loop over the four counters of `/proc/vmstat`. |
| 1576 | `        print_na(vm[i]);` | Columns 8 to 11: the counters `thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc` and `pgmigrate_success`, in this order (line 1547). They count for the whole system, not for this buffer. `main` passes the same array `vm` for all buffers of one reading (line 3117). So all P rows of one reading hold the same four values. |
| 1577 | `    printf("\n");` | Ends the row with a line break. Example, the first P row of the file `a6456.csv` in the result folder of T72L1 (the first of the 3 processes of part L): `P,0,-1,0,a,262144,262144,611480,0,2,0` [Ref5]. It says: round 0, before the first interval, thread 0, buffer `a`, a mapping of 262144 kB, 262144 kB of it on 2 MiB pages. |
| 1578 | `}` | Ends the function `print_p`. |

### Function `open_counters`: open the counter group of one thread (lines 1580 to 1608)

| Line | Source | Explanation |
|---:|---|---|
| 1580 | `/* Counters (handoff B.8): one group per thread, user mode only, opened by the` | Comment: the counters follow section B.8 of the file `handoff.md`, the specification of the first runner. Each thread has one counter group. The counters count in user mode only. The sentence about who opens them goes on in line 1581. |
| 1581 | ` * pinned thread for itself. An event that does not open is printed as NA. */` | Comment: the pinned thread opens the counters for itself. An event that does not open is printed as `NA` (lines 3097 to 3098). |
| 1582 | `static void open_counters(struct thread *t)` | Starts the function `open_counters`. It opens one counter per entry of `--events` for the calling thread and joins the counters into one group. With `--count` each worker calls it once (line 1644), after the pinning and before it maps its buffer. `t` is the record of the calling thread. In the whole-chip test `--events` has 6 entries [Ref4]. |
| 1583 | `{` | Opens the body of `open_counters`. |
| 1584 | `    t->group_fd = -1;` | Start state: no group leader (`group_fd` is -1). The group leader is the first counter of a counter group. |
| 1585 | `    t->nopen = 0;` | Start state: 0 open counters. |
| 1586 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `--events`, in the order of the list. `cfg.nev` is their number. |
| 1587 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 1588 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. So every option that the next lines do not set is off. The field `disabled` also stays 0. So a counter counts from the moment it is opened. |
| 1589 | `        a.type = (uint32_t)cfg.pmu_type;` | `type` selects the PMU (performance monitoring unit, the hardware event counters of a core). It is the value of `--pmu-type`: 11 in the whole-chip test [Ref4]. |
| 1590 | `        a.size = sizeof a;` | `size` gives Linux the size of the structure. |
| 1591 | `        a.config = cfg.ev_code[e];` | `config` is the event code of this entry, for example 0x198 for `cbusy0` in the whole-chip test [Ref4]. The program passes the code to Linux and does not interpret it. |
| 1592 | `        a.exclude_kernel = 1;` | `exclude_kernel = 1`: the counter does not count while the CPU runs code of the Linux kernel. |
| 1593 | `        a.exclude_hv = 1;` | `exclude_hv = 1`: the counter does not count code of a hypervisor. A hypervisor is the software that runs virtual machines. With these two fields the counter counts in user mode only: while the thread runs the code of the program itself. The specification of the first runner says that counter code without these two fields fails without root rights on CRB [Ref10]. |
| 1594 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | `read_format` chooses what one `read` of the group returns. `PERF_FORMAT_GROUP`: the values of all counters of the group in one reading. The two other flags add the enabled time and the running time of the group [Ref8]. |
| 1595 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, t->group_fd, 0);` | The system call `perf_event_open` opens the counter. It returns a file descriptor: the number that later calls such as `read` use for the open counter. A negative value means failure. The arguments `0` and `-1` are the pid and the cpu argument of the call [Ref10]. Together they mean: count the calling thread, on any CPU that it runs on. With `--cpus` the thread is pinned, so this is one CPU. The argument `t->group_fd` is -1 for the first counter, which starts a new group. A later counter passes the file descriptor of the leader and joins its group. The last argument `0` means no flags. |
| 1596 | `        if (fd < 0) {` | Tests whether the open failed. |
| 1597 | `            if (t->idx == 0)` | Only thread 0 writes a message. So an event that fails in every thread gives one message, not one per thread. |
| 1598 | `                fprintf(stderr, "perf_event_open %s (type %ld code 0x%llx): %s (printed as NA)\n", cfg.ev_name[e],` | The message goes to stderr: the word `perf_event_open`, the event name, the PMU type, the event code in hexadecimal, the error text of Linux and the words `printed as NA`. This line holds the format and the event name. |
| 1599 | `                        cfg.pmu_type, (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 1598: the PMU type, the event code and the error text (`strerror(errno)`). |
| 1600 | `            t->ev_pos[e] = -1;` | The event gets the position -1. `main` prints `NA` for it in the C rows (lines 3096 to 3098). |
| 1601 | `            continue;` | The loop goes on with the next event. The thread does not stop. In the whole-chip test no csv field is `NA` and every file `stderr.txt` is empty [Ref5]. So every open succeeded in all 120 threads, and each thread has 6 open counters. |
| 1602 | `        }` | Ends the `if` of line 1596. |
| 1603 | `        t->ev_pos[e] = t->nopen++;` | The open succeeded. `ev_pos[e]` gets the position of this event in a group reading: 0 for the first open counter, 1 for the next. `nopen` counts the open counters of the thread. |
| 1604 | `        if (t->group_fd < 0)` | Tests whether the group has no leader yet. |
| 1605 | `            t->group_fd = fd;` | The first counter that opens becomes the leader of the group. `group_fd` keeps its file descriptor, and every group reading uses it (line 1622). The file descriptors of the other counters are not kept. The function `worker` never closes, resets or stops a counter. |
| 1606 | `    }` | Ends the loop over the events (line 1586). |
| 1607 | `}` | Ends the function `open_counters`. |

### Function `cpu_ns`: the CPU time of the calling thread (lines 1609 to 1615)

| Line | Source | Explanation |
|---:|---|---|
| 1609 | `static uint64_t cpu_ns(void)` | Starts the function `cpu_ns`. It returns the CPU time that the calling thread has used so far, in ns. With `--count` the worker calls it once before and once after each timed interval (line 1686, line 1718). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 1610 | `{` | Opens the body of `cpu_ns`. |
| 1611 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 1612 | `    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);` | Reads the Linux clock `CLOCK_THREAD_CPUTIME_ID` into `ts`. This clock counts the CPU time of the calling thread only. |
| 1613 | `    return (uint64_t)ts.tv_sec * 1000000000UL + (uint64_t)ts.tv_nsec;` | Returns the time in ns: the seconds times 1000000000, plus the nanoseconds. |
| 1614 | `}` | Ends the function `cpu_ns`. |

### Function `read_group`: one reading of the counter group (lines 1616 to 1631)

| Line | Source | Explanation |
|---:|---|---|
| 1616 | `/* Group read: nr, time_enabled, time_running, then one value per open event. */` | Comment: the layout of one group reading: the number of counters (`nr`), the enabled time, the running time, then one value per open event [Ref8]. |
| 1617 | `static void read_group(const struct thread *t, struct counts *c)` | Starts the function `read_group`. It takes one reading of all counters of the thread `t` and stores it in `c`. With `--count` the worker calls it once before and once after each timed interval (line 1685, line 1719). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 1618 | `{` | Opens the body of `read_group`. |
| 1619 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest reading: 3 header words plus 8 counter values (`MAX_EV` is 8). Each word has 8 bytes. In the whole-chip test a reading has 9 words: 3 header words and 6 counter values [Ref4]. |
| 1620 | `    if (t->group_fd < 0)` | Tests whether the thread has no open counter. |
| 1621 | `        return;` | Such a thread returns here. Then `c` keeps the zeros that the worker wrote in line 1667. |
| 1622 | `    if (read(t->group_fd, buf, sizeof buf) < (ssize_t)(3 * sizeof buf[0]) \|\| buf[0] != (uint64_t)t->nopen) {` | One `read` system call on the leader returns the whole group: the number of counters `nr`, the enabled time, the running time, then one value per counter [Ref8]. The reading is rejected when it has fewer than 24 bytes (the 3 header words). It is also rejected when `nr` is not the number of counters that this thread opened. |
| 1623 | `        perror("read of the counter group");` | A rejected reading: `perror` prints the words `read of the counter group` and the reason that Linux gave to stderr. |
| 1624 | `        exit(2);` | The whole program then ends with exit status 2. In the whole-chip test every file `stderr.txt` is empty [Ref5]. So no reading was rejected. |
| 1625 | `    }` | Ends the `if` of line 1622. |
| 1626 | `    c->enabled = buf[1];` | Stores the enabled time of the group, in ns: how long the counters were enabled. |
| 1627 | `    c->running = buf[2];` | Stores the running time of the group, in ns: how long the counters really counted. `main` prints the difference between the two readings of an interval as `enabled_ns` and `running_ns` in the C row (lines 3092 to 3093). In the whole-chip test the two columns are equal in all 8880 C rows (checked on 2026-11-21) [Ref5]. So the counters counted during all of their enabled time. |
| 1628 | `    for (int i = 0; i < t->nopen; i++)` | Loop over the open counters of the thread. |
| 1629 | `        c->val[i] = buf[3 + i];` | Stores one value per open counter, in the order in which the counters were opened. `main` prints for each event the difference between the reading after the interval and the reading before it (line 3100). |
| 1630 | `}` | Ends the function `read_group`. |

### Function `worker`: start values, pinning, counters, buffers and first touch (lines 1632 to 1655)

| Line | Source | Explanation |
|---:|---|---|
| 1632 | `static void *worker(void *arg)` | Starts the function `worker`, the start function of every worker thread. `main` creates the workers in line 3012: 120 of them in the whole-chip test [Ref4]. `arg` points to the record of the thread. |
| 1633 | `{` | Opens the body of `worker`. |
| 1634 | `    struct thread *t = arg;` | `t`: the record of this thread. `main` has set its index `idx` and its CPU `cpu` (lines 3010 to 3011). |
| 1635 | `    volatile uint64_t sink;` | `sink`: a volatile variable on the stack of this thread. `call` stores there the sum that an old read kernel returns (line 1500). The compiler must keep this store. So it cannot remove the adds of the old read kernel. Each thread has its own `sink`. So the threads do not all store to one shared cache line. |
| 1636 | `    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */` | Comment: the store value is known only when the program runs, and its 8 bytes are not all equal. So the compiler cannot turn the store loop into a call of `memset`, the library function that fills memory with one byte value. |
| 1637 | `    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;` | `v`: the value that `k_write` stores into the 8-byte words of a buffer at the first touch (line 1646). It is the process id (`getpid`) plus the thread index plus 1, times a fixed 64-bit constant. The timed loop gives `v` plus a counter to a write kernel (line 1695, line 1709). The read kernels do not use `v`. |
| 1638 | `    uint64_t k = 0; /* intervals this thread has run (--stop common) */` | `k`: the number of timed intervals that this thread has started. Line 1677 compares it with the shared counter `gen`. The comment says that `--stop common` uses it. |
| 1639 | `    int64_t min_ns = (int64_t)(cfg.min_s * 1e9);` | `min_ns`: the `--min-ms` value in ns. Only the loop of `--stop pass` uses it (line 1715). In the whole-chip test it is 6000000000 ns (6 s), and that test runs with `--stop common` [Ref4]. So this variable does not end an interval of that test. |
| 1641 | `    if (cfg.ncpus)` | Tests whether a CPU list was given (`--cpus`). The whole-chip test gives the CPUs 0 to 119, so `cfg.ncpus` is 120 there [Ref4]. Thread i gets CPU i: the threads 0 to 63 run on mesh 0, the threads 64 to 119 on mesh 1 [Ref5]. |
| 1642 | `        pin_cpu(t->cpu);` | CPU pinning. The thread pins itself to its CPU with `pin_cpu` (line 415). `main` chose the CPU in line 3011. Every later line of the worker runs on that CPU. Without `--cpus` the thread is not pinned. |
| 1643 | `    if (cfg.count)` | Tests whether counting is on (`--count`). The whole-chip test runs with `--count` [Ref4]. |
| 1644 | `        open_counters(t);` | The thread opens its counters with `open_counters` (line 1582). The counters count from this moment on. So they also count during the first touch and the warm-up passes. A C row holds only the change between the two readings of one interval (line 1685, line 1719). |
| 1645 | `    t->a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 434) maps buffer `a` of this thread. The buffer starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. `alloc_buf` also asks Linux for 2 MiB pages for it (with `--no-thp`: for no such pages). Each thread has its own buffer and reads only its own buffer. In the whole-chip test a buffer has 268435456 bytes (256 MiB), which are 33554432 words of 8 bytes [Ref4]. |
| 1646 | `    k_write(t->a, cfg.bytes / 8, v); /* first touch by this thread */` | First touch. `k_write` (line 531) stores `v` into `cfg.bytes / 8` words of 8 bytes, from the start of the buffer: every word of the `--bytes` range. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 428). Then the worker does not write the rest. No kernel call reaches the rest: the size of a `--seq` entry is at most `--bytes` (line 2991). The pinned thread does this write itself, before any read. Linux assigns the memory pages at this first write. This line is not timed. The comment says: first touch by this thread. |
| 1647 | `    if (cfg.two_buffers) {` | Tests whether the thread needs a second buffer `b`. It exists only with `--two-buffers` or with a copy kernel in `--seq` (lines 2996 to 2997). The whole-chip test has neither [Ref4]. So lines 1648 to 1649 did not run there, and every P row of that test is a row of buffer `a` [Ref5]. |
| 1648 | `        t->b = alloc_buf();` | Maps buffer `b` in the same way as buffer `a`. |
| 1649 | `        k_write(t->b, cfg.bytes / 8, v);` | First touch of buffer `b`: the same write as in line 1646. It is not timed. |
| 1650 | `    }` | Ends the `if` of line 1647. |
| 1651 | `    if (cfg.threads > 1) {` | Tests whether the process has more than one worker. Only then the two barrier waits of lines 1652 to 1653 exist. The barrier releases its waiting threads when all workers and the main thread have called it (line 3005). In the whole-chip test these are 121 threads [Ref4]. |
| 1652 | `        pthread_barrier_wait(&bar); /* the buffers exist: main() reads the first page state */` | First wait at the barrier. It returns when all workers have mapped and written their buffers and `main` has arrived in line 3045. Then `main` copies the buffer addresses and reads the page state for the P rows with position -1. The comment says: the buffers exist, and `main` reads the first page state. |
| 1653 | `        pthread_barrier_wait(&bar); /* main() has read it */` | Second wait at the barrier. The worker blocks until that reading is done. `main` releases the workers in line 3114. The comment says: `main` has read it. |
| 1654 | `    }` | Ends the `if` of line 1651. |

### Function `worker`: one interval, from the warm-up pass to the clock read `t0` (lines 1656 to 1689)

| Line | Source | Explanation |
|---:|---|---|
| 1656 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds. `--rounds N` runs the `--seq` list N times, and the rounds count from 0. The whole-chip test has 2 rounds: round 0, then round 1 [Ref4]. |
| 1657 | `        for (int pos = 0; pos < cfg.nseq; pos++) {` | Loop over the positions of the `--seq` list. One pass of this loop is one timed interval. `main` runs the same two loops (lines 3039 to 3040). In the whole-chip test `pos` is 0 to 4 for the spec file `like.spec` and 0 to 2 for `cfwd.spec` and `crev.spec` [Ref4]. |
| 1658 | `            const struct kdef *kd = &kernels[cfg.seq[pos].k];` | `kd`: the entry of the kernel table for this position: name, type and function pointer (line 1458). The kernels run in the order of the `--seq` list. Example of the whole-chip test: position 0 of `like.spec` is `oldread`, with the type `T_OLDREAD` and the function `k_oldread`. There `asmread` always runs after `oldread`, and `oldread` of round 1 runs after `read_1pl` of round 0 [Ref4]. |
| 1659 | `            size_t size = cfg.seq[pos].bytes;` | `size`: the number of bytes of this position. It is the size after `@` in the `--seq` entry, or the `--bytes` value for an entry without `@` (line 2990). In the whole-chip test no entry has an `@SIZE` part, so `size` is 268435456 bytes, the whole buffer [Ref4]. |
| 1660 | `            size_t nchunk = size / HUGE_BYTES;` | `nchunk`: the number of whole 2 MiB pieces in `size`. It is 128 for a size of 256 MiB. Only the start offset of line 1662 uses it. |
| 1661 | `            /* --start offset (handoff B.5): thread i starts at (i * 37 mod n) * 2 MiB */` | Comment: with `--start offset` thread i starts at the 2 MiB piece with the number i times 37 modulo n. Here n is `nchunk`. The comment names section B.5 of the file `handoff.md`, the specification of the first runner. |
| 1662 | `            size_t off = cfg.start_offset && nchunk ? ((size_t)t->idx * 37 % nchunk) * HUGE_BYTES : 0;` | `off`: the byte offset in the buffer at which this thread starts its timed work. With `--start common` it is 0. It is also 0 for a size below 2 MiB. With `--start offset` it is `idx * 37 % nchunk` times 2 MiB. So most threads start at a place of their buffer other than byte 0. Thread 0 starts at byte 0, and with one piece (`nchunk` is 1) every thread does. The whole-chip test passes `--start common` [Ref4]. So every thread starts its timed interval at byte 0 of its own buffer. |
| 1663 | `            uint64_t per_byte = kd->type == T_COPY ? 2 : 1; /* copy counts read+write bytes */` | `per_byte`: 2 for a copy kernel, 1 for every other kernel. A copy kernel counts every byte two times: once read, once written. The kernels of the whole-chip test are read kernels, so `per_byte` is 1 there [Ref4]. |
| 1664 | `            uint64_t bytes = 0, p = 0;` | `bytes`: the byte count of the timed interval. `p`: the number of kernel calls of the interval with `--stop common`, or of passes with `--stop pass`. Both start at 0. |
| 1665 | `            int64_t sched = 0, deadline = 0, t0, t1;` | Clock values in ns: `sched` (the common start time), `deadline`, `t0` (the start of the timed interval) and `t1` (the clock read after the latest kernel work). |
| 1666 | `            struct result r;` | `r`: the result record of this thread for this interval (line 296). |
| 1667 | `            memset(&r, 0, sizeof r);` | `memset` sets every field of `r` to 0. |
| 1669 | `            call(kd, t, 0, size, v, &sink); /* warm-up */` | Warm-up pass, not timed. One call of the kernel of this position over the range from byte 0 to `size`, through `call` (line 1491). So before every timed interval the thread has run the same kernel once over the whole range. Between this pass and the timed interval lie the barrier wait, the wait for the common start and the first counter reading (lines 1675 to 1687). In a process with one thread the page-state reading of lines 1670 to 1674 also lies between them. In the whole-chip test the range is the whole buffer of 268435456 bytes [Ref4]. |
| 1670 | `            if (cfg.threads == 1) {` | Tests whether the process has one worker only. Only such a process reads the page state here, in the worker: after the warm-up pass and before the barrier. The whole-chip test has 120 threads, so lines 1671 to 1673 did not run there [Ref4]. |
| 1671 | `                uint64_t *buf[2] = { t->a, t->b };` | `buf`: the addresses of the two buffers of the thread. `t->b` is NULL when the thread has no second buffer. |
| 1672 | `                read_smaps(r.pg, buf, 2);` | `read_smaps` (line 1515) reads the page state of both buffers into `r.pg`. It skips a NULL entry. |
| 1673 | `                read_vmstat(r.vm);` | `read_vmstat` (line 1545) reads the four counters of `/proc/vmstat` into `r.vm`. `main` prints both readings as P rows after the interval (lines 3072 to 3076). |
| 1674 | `            }` | Ends the `if` of line 1670. |
| 1675 | `            pthread_barrier_wait(&bar);` | Barrier wait after the warm-up pass. The thread blocks until all workers have ended their warm-up pass and `main` has arrived in line 3057. Then all of these threads continue. A thread whose warm-up pass ends early waits here and reads no memory. |
| 1676 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Only then lines 1677 to 1682 run. The whole-chip test uses `--stop common` [Ref4]. |
| 1677 | `                while (atomic_load(&gen) != k + 1)` | Common start, step 1. The thread repeats an empty loop until the shared counter `gen` equals `k + 1`. `main` adds 1 to `gen` in line 3062, after it has stored the start time and the deadline of this interval. In this loop the thread stays on its CPU and does not sleep. |
| 1678 | `                    ;` | The empty body of the loop of line 1677. |
| 1679 | `                sched = atomic_load(&t_sched_ns);` | Copies the common start time into `sched`. `main` computed it in line 3059: its clock reading plus 2 ms (`LEAD_NS`). All workers read the same value. |
| 1680 | `                deadline = atomic_load(&deadline_ns);` | Copies the common deadline into `deadline`. `main` computed it in line 3061: the start time plus the `--min-ms` value. All workers read the same value. In the whole-chip test the deadline is the start time plus 6 s [Ref4]. |
| 1681 | `                while (now_ns() < sched)` | Common start, step 2. The thread reads the clock again and again until the clock reaches `sched`. It leaves the loop at its first clock read at or after the start time. This wait is not timed. |
| 1682 | `                    ;` | The empty body of the loop of line 1681. |
| 1683 | `            }` | Ends the `if` of line 1676. |
| 1684 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). |
| 1685 | `                read_group(t, &r.c0);` | First counter reading (`read_group`, line 1617). It goes into `r.c0`. With `--stop common` it runs after the wait for the common start. With `--stop pass` it runs directly after the barrier. In both cases it runs before the clock read of line 1688. So it is not inside the timed interval. But `t0` is later than the common start time by at least the duration of this line and of line 1686. |
| 1686 | `                r.c0.cpu_ns = cpu_ns();` | Reads the thread CPU time (`cpu_ns`, line 1609) into `r.c0`. In the whole-chip test `t0` is 2 us to 34 us after the common start time (us = microsecond, computed on 2026-11-21 from the columns `t_sched_s` and `t_start_s` of all 8880 T rows) [Ref5]. Both columns are printed with 6 decimal places, so each time is rounded to 1 us. |
| 1687 | `            }` | Ends the `if` of line 1684. |
| 1688 | `            t0 = now_ns();` | Start of the timed interval. The thread reads the clock (`now_ns`, line 327) into `t0`. Each thread has its own `t0`. Nothing above this line is inside the timed interval. |
| 1689 | `            k++;` | Counts this interval. At the next interval line 1677 waits for the next value of `gen`. This line runs after the clock read `t0`, so it is the first statement inside the timed interval. |

### Function `worker`: the timed loop and the two stop rules (lines 1690 to 1716)

| Line | Source | Explanation |
|---:|---|---|
| 1690 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Lines 1693 to 1701 are the timed loop of this stop rule. The whole-chip test uses it [Ref4]. |
| 1691 | `                /* chunks of 2 MiB (or the whole entry if it is smaller); the` | Comment: the kernel runs on chunks of 2 MiB, or on the whole entry when the entry is smaller than 2 MiB. The sentence goes on in line 1692. |
| 1692 | `                 * position continues from chunk to chunk and wraps */` | Comment: the position in the buffer goes on from chunk to chunk. At the end of the entry it returns to the start. |
| 1693 | `                size_t chunk = size < CHUNK_BYTES ? size : CHUNK_BYTES, at = off;` | `chunk`: the number of bytes of one kernel call: 2097152 bytes (2 MiB, `CHUNK_BYTES`), or `size` when `size` is smaller. `at`: the byte offset of the next chunk in the buffer. It starts at `off` (line 1662). |
| 1694 | `                do {` | Starts the timed loop. Its body runs at least once. |
| 1695 | `                    call(kd, t, at, chunk, v + p++, &sink);` | Timed kernel call. `call` (line 1491) runs the kernel on the chunk at byte offset `at`. The kernel gets the address of the chunk and its length in 8-byte words: 262144 words for a chunk of 2 MiB. So the kernel function is entered once per chunk: 128 times per pass over a buffer of 256 MiB. For a kernel of the type `T_OLDREAD`, `call` stores the returned sum in `sink` after each call. A kernel of the type `T_READ` returns nothing. `v + p++` gives a write kernel a new value in every call and counts the calls. A read kernel does not get this argument. |
| 1696 | `                    bytes += per_byte * chunk;` | Bytes counted. Each finished call adds `per_byte * chunk`: 2097152 bytes for a 2 MiB chunk of a read kernel. This is the size of the range that was passed to the kernel. Nothing is counted inside a kernel. So the number is the same for every read kernel. It is also used for `read_1pl`, which loads 16 B of each 64 B line. Example: the first T row of the file `a6456.csv` in the result folder of T72L1 (thread 0, `oldread`) holds 28934406144 bytes. That is 13797 calls [Ref5]. |
| 1697 | `                    at += chunk;` | Moves `at` to the next chunk. |
| 1698 | `                    if (at == size)` | Tests whether `at` has reached the end of the entry. |
| 1699 | `                        at = 0;` | After the last chunk the offset returns to 0. For a size of 256 MiB this is after chunk 127. So the kernel calls go from the start offset `off` to the end of the range. Then they repeat the whole range from byte 0, until the interval ends. With `--start common` the offset `off` is 0, and the first pass is also a whole pass. |
| 1700 | `                    t1 = now_ns();` | Clock read after every chunk: `t1` is the clock value after this call. The last `t1` is the end of the timed interval. So the timed interval is the code from line 1688 to this line: the kernel calls, the byte count, the step of the offset and one clock read per chunk. In the example of line 1696 these are 13797 clock reads [Ref5]. |
| 1701 | `                } while (t1 < deadline);` | Stop rule of `--stop common`. The loop repeats while `t1` is before the common deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted. The deadline is the same for all threads. Each thread has its own end time `t1`. In the whole-chip test the last `t1` is 0 us to 463 us after the deadline, and the elapsed time `t1 - t0` is 5.999979 s to 6.000457 s [Ref5]. Both ranges were computed on 2026-11-21 from all 8880 T rows, with the deadline taken as `t_sched_s` plus 6 s. |
| 1702 | `            } else {` | The branch of `--stop pass`. Lines 1704 to 1715 are the timed loop of this stop rule. The whole-chip test does not use it [Ref4]. |
| 1703 | `                /* whole passes; with an offset a pass is [off, size) then [0, off) */` | Comment: the thread runs whole passes. With a start offset one pass is the range from `off` to the end of the entry and then the range from 0 to `off`. |
| 1704 | `                uint64_t passes_per_check = CHECK_BYTES / size;` | `passes_per_check`: the number of passes between two clock reads. It is 8 MiB (`CHECK_BYTES`) divided by `size`, rounded down. So for a size below 8 MiB that does not divide 8 MiB, the clock is read after less than 8 MiB. |
| 1705 | `                if (passes_per_check == 0)` | Tests whether the division gave 0. That is the case for every size above 8 MiB. |
| 1706 | `                    passes_per_check = 1;` | The value is then 1: the thread reads the clock after every pass. |
| 1707 | `                do {` | Starts the timed loop of `--stop pass`. Its body runs at least once. |
| 1708 | `                    for (uint64_t c = 0; c < passes_per_check; c++, p++) {` | Runs `passes_per_check` passes without a clock read between them. `p` counts the passes. |
| 1709 | `                        call(kd, t, off, size - off, v + p, &sink);` | Timed kernel call: the range from `off` to the end of the entry. With an `off` of 0 this is the whole entry. `v + p` gives a write kernel a new value in every pass. |
| 1710 | `                        if (off)` | Tests whether the thread has a start offset above 0. |
| 1711 | `                            call(kd, t, 0, off, v + p, &sink);` | Second kernel call of the pass: the range from byte 0 to `off`. So each pass covers every byte of the entry once. |
| 1712 | `                        bytes += per_byte * size;` | Bytes counted: each pass adds `per_byte * size`. This is the size of the entry, or twice the size for a copy kernel. Nothing is counted inside a kernel. |
| 1713 | `                    }` | Ends the `for` of line 1708. |
| 1714 | `                    t1 = now_ns();` | Clock read after the passes: `t1`. The clock is never read inside a pass. The last `t1` is the end of the timed interval. So with this stop rule the timed interval is the code from line 1688 to this line. |
| 1715 | `                } while (t1 - t0 < min_ns);` | Stop rule of `--stop pass`. The loop repeats while less than `min_ns` (the `--min-ms` value) has passed after the `t0` of this thread. So a thread stops only at the end of a whole pass, after a full group of `passes_per_check` passes. The threads stop at different times. |
| 1716 | `            }` | Ends the `if` and `else` of line 1690. |

### Function `worker`: after the timed interval, the result record and the barrier waits (lines 1717 to 1736)

| Line | Source | Explanation |
|---:|---|---|
| 1717 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). The timed interval has ended at the last clock read `t1` (line 1700 or line 1714). |
| 1718 | `                r.c1.cpu_ns = cpu_ns();` | Reads the thread CPU time into `r.c1` (`cpu_ns`). |
| 1719 | `                read_group(t, &r.c1);` | Second counter reading, into `r.c1` (`read_group`). The order is the reverse of lines 1685 to 1686. So the timed interval lies between the two readings of the thread CPU time, and these lie between the two counter readings. The counter values of a C row therefore cover the timed interval plus a few calls around it: the two readings of the thread CPU time and the clock read `t0`. |
| 1720 | `            }` | Ends the `if` of line 1717. |
| 1721 | `            r.bytes = bytes;` | Stores the byte count of the interval in the result record. |
| 1722 | `            r.t_start = t0;` | Stores `t0`, the start of the timed interval. |
| 1723 | `            r.t_end = t1;` | Stores the last `t1`, the end of the timed interval. `main` computes the elapsed time of a thread as `t_end - t_start` (line 3069, line 3082). The script `stat_bwx.py` computes the rate of a thread from the T row as bytes / elapsed seconds / 1e9, in GB/s [Ref6]. |
| 1724 | `            r.t_sched = cfg.stop_common ? sched : t0;` | Stores the common start time. `main` prints it in the T row as `t_sched_s` (line 3083). With `--stop pass` there is no common start time, and the field gets `t0`. |
| 1725 | `            r.late = cfg.stop_common && t0 - sched > LATE_NS;` | Late flag. With `--stop common` it is set when `t0` is more than 100000 ns (100 us, `LATE_NS`) after the common start time. `main` then prints `late` in the last column of the T row (line 3084). The program does nothing else with the flag: the interval runs, and its bytes are counted. In the whole-chip test no T row has the flag [Ref5]. |
| 1726 | `            t->res = r;` | Copies the record into the thread structure. `main` reads it there after the barrier wait of line 1727. |
| 1727 | `            pthread_barrier_wait(&bar);` | Barrier wait at the end of the interval. The thread blocks until all workers have ended their interval and `main` waits in line 3064. A thread that has stopped reads no memory while other threads finish their last chunk or pass. |
| 1728 | `            /* main() reads the page state of all buffers. The warm-up pass of` | Comment: `main` reads the page state of all buffers at this point. The sentence about the next warm-up pass starts here. |
| 1729 | `             * the next interval starts only after that reading (handoff B.6). */` | Comment: the warm-up pass of the next interval starts only after that reading. The comment names section B.6 of the file `handoff.md`, the specification of the first runner. |
| 1730 | `            if (cfg.threads > 1)` | Tests whether the process has more than one worker. Only then the second barrier wait exists. |
| 1731 | `                pthread_barrier_wait(&bar);` | Second barrier wait at the end of the interval. While the workers block here, `main` prints the I, T and C rows of the interval and reads the page state of all buffers (lines 3066 to 3113). `main` releases the workers in line 3114. Then each worker starts the warm-up pass of the next interval. `main` prints the P rows and the `# page_read` line after the release (lines 3115 to 3118). So this output can run while the workers do their warm-up pass. The output ends before the next timed interval starts: the barrier of line 1675 lets the workers pass only when `main` has finished the output and waits in line 3057. |
| 1732 | `        }` | Ends the loop over the positions (line 1657). The worker calls no sleep function. So between two intervals lie only the waits, the readings and the warm-up pass of the rows above. |
| 1733 | `    }` | Ends the loop over the rounds (line 1656). |
| 1734 | `    return NULL;` | After the last interval of the last round the thread returns. `main` waits for the end of all threads in line 3124. |
| 1735 | `}` | Ends the function `worker`. |

### Function `usage`: option summary, then exit status 2 (lines 1737 to 1749)

| Line | Source | Explanation |
|---:|---|---|
| 1737 | `static void usage(void)` | Starts the function `usage`. It prints the option summary to stderr and ends the program with exit status 2. `main` calls it for an argument that it does not accept and for settings that fail one of its checks (lines 2969 to 2995), for example `--threads` without `--cpus`. |
| 1738 | `{` | Opens the body of `usage`. |
| 1739 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to stderr. Its text stands in lines 1740 to 1746. |
| 1740 | `            "usage: bwx --seq LIST [--threads T --cpus LIST] [--bytes B] [--min-ms MS] [--no-thp]\n"` | Text of the message: the first usage line, with the options `--seq`, `--threads`, `--cpus`, `--bytes`, `--min-ms` and `--no-thp`. The text names the program `bwx`, the name of the first version of the runner. |
| 1741 | `            "           [--rounds N] [--stop pass\|common] [--start common\|offset] [--two-buffers]\n"` | Text of the message: the options `--rounds`, `--stop`, `--start` and `--two-buffers`. |
| 1742 | `            "           [--count --pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options of the counters (`--count`, `--pmu-type`, `--events`), and the two environment variables that can give the counter settings in their place (lines 2976 to 2982). |
| 1743 | `            "       bwx --selftest \| --list\n"` | Text of the message: the second form of the command, with `--selftest` or `--list`. |
| 1744 | `            "  --seq: comma-separated entries KERNEL or KERNEL@SIZE; --list prints the kernel names\n"` | Text of the message: an entry of `--seq` is a kernel name, or a kernel name with `@` and a size. `--list` prints the kernel names. |
| 1745 | `            "  sizes must be multiples of 256; with --stop common: multiples of 2M, or below 2M\n"` | Text of the message: a size must be a multiple of 256. With `--stop common` it must be a multiple of 2M or below 2M (lines 2991 to 2992). |
| 1746 | `            "  --pmu-type and CODE: the perf_event_attr fields type and config of the core PMU (CODE may be 0x..)\n");` | Text of the message: `--pmu-type` and the code of an event go into the fields `type` and `config` of the structure `perf_event_attr` (line 1589, line 1591). A code may be written in hexadecimal with `0x`. This line ends the `fprintf` call. |
| 1747 | `    exit(2);` | Ends the program with exit status 2. The whole-chip test did not reach this function: every process of that test ended with exit status 0 [Ref5]. |
| 1748 | `}` | Ends the function `usage`. |

### Function `parse_seq`: read the `--seq` list (lines 1750 to 1768)

| Line | Source | Explanation |
|---:|---|---|
| 1750 | `static void parse_seq(char *list)` | Starts the function `parse_seq`. It turns the text after `--seq` into the entries of `cfg.seq`. `main` calls it in line 2950. |
| 1751 | `{` | Opens the body of `parse_seq`. |
| 1752 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. Each pass of the loop handles one entry, in the order of the list. This order is the order in which the kernels run in each round. |
| 1753 | `        char *at = strchr(tok, '@');` | `at`: the place of an `@` in the entry, or NULL when the entry has none. An entry may have the form `KERNEL@SIZE`. No entry of the whole-chip test has an `@` [Ref4]. |
| 1754 | `        int k = 0;` | `k`: the index into the kernel table. The search of line 1757 starts at entry 0. |
| 1755 | `        if (at)` | Tests whether the entry has an `@`. |
| 1756 | `            *at = '\0';` | Ends the name at the `@`: a zero byte replaces the `@`. |
| 1757 | `        while (k < K_COUNT && strcmp(tok, kernels[k].name))` | Searches the kernel table `kernels[]` (line 1458) for the name, from the first entry on. `strcmp` returns 0 when two texts are equal. The loop stops at the entry with this name. When no entry has the name, it stops with `k` equal to `K_COUNT`, the number of entries. |
| 1758 | `            k++;` | The body of the search loop: goes on to the next entry of the table. |
| 1759 | `        if (k == K_COUNT \|\| cfg.nseq == MAX_SEQ) {` | Tests for two defects: the name is not in the table, or `cfg.seq` already holds 64 entries (`MAX_SEQ`). |
| 1760 | `            fprintf(stderr, "bad --seq entry: %s\n", tok);` | Prints `bad --seq entry:` and the name to stderr. |
| 1761 | `            exit(2);` | Ends the program with exit status 2. |
| 1762 | `        }` | Ends the `if` of line 1759. |
| 1763 | `        cfg.seq[cfg.nseq].k = k;` | Stores the index of the kernel in the next free entry of `cfg.seq`. |
| 1764 | `        cfg.seq[cfg.nseq].bytes = at ? parse_bytes(at + 1) : 0;` | Stores the size of the entry: the text after the `@`, read by `parse_bytes` (line 334). An entry without `@` gets the size 0 here. `main` later replaces 0 by the `--bytes` value (line 2990). |
| 1765 | `        cfg.nseq++;` | Counts the entry. |
| 1766 | `    }` | Ends the loop of line 1752. Result in the whole-chip test [Ref4]: `like.spec` gives `oldread`, `asmread`, `read_nop96`, `read_nop256`, `read_1pl` (5 positions). `cfwd.spec` gives `oldread`, `read`, `asmread` (3 positions). `crev.spec` gives `asmread`, `read`, `oldread` (3 positions), the reverse order of `cfwd.spec`. |
| 1767 | `}` | Ends the function `parse_seq`. |

### Function `parse_events`: read the `--events` list (lines 1769 to 1794)

| Line | Source | Explanation |
|---:|---|---|
| 1769 | `/* "NAME=CODE,..." or "CODE,...". A code without a name gets the name of its` | Comment: the list has the form `NAME=CODE,...` or `CODE,...`. The sentence about a code without a name starts here. |
| 1770 | ` * position in the list of handoff B.8. */` | Comment: a code without a name gets the name of its place in the event list of section B.8 of the file `handoff.md`, the specification of the first runner. The code has one more rule that the comment does not name: from the sixth place on the name is `ev` plus the place number (lines 1784 to 1785). |
| 1771 | `static void parse_events(char *list)` | Starts the function `parse_events`. It turns the text of an event list into the names `cfg.ev_name` and the codes `cfg.ev_code`. `main` calls it with the text after `--events` (line 2964), and with the text of the environment variable `BWX_EVENTS` (line 2980). |
| 1772 | `{` | Opens the body of `parse_events`. |
| 1773 | `    static const char *by_pos[5] = { "cycles", "instructions", "l1d_refill", "l2d_refill", "ll_miss_rd" };` | `by_pos`: the names for an entry without a name at one of the first 5 places of the list: `cycles`, `instructions`, `l1d_refill`, `l2d_refill` and `ll_miss_rd`. Every entry of the whole-chip test has a name, so the table is not used there [Ref4]. |
| 1774 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. One pass of the loop handles one entry. |
| 1775 | `        char *eq = strchr(tok, '='), *code = eq ? eq + 1 : tok, *end;` | `eq`: the place of the `=` sign in the entry, or NULL. `code`: the text of the code. It is the text after the `=`, or the whole entry when the entry has no `=`. `end` is used in line 1786. |
| 1776 | `        if (eq == tok \|\| cfg.nev == MAX_EV \|\| (eq && (size_t)(eq - tok) >= sizeof cfg.ev_name[0])) {` | Tests for three defects: an entry with an empty name (the `=` is its first character), a 9th entry (`MAX_EV` is 8), and a name of 32 characters or more (the size of one entry of `cfg.ev_name`). |
| 1777 | `            fprintf(stderr, "bad --events entry: %s\n", tok);` | Prints `bad --events entry:` and the entry to stderr. |
| 1778 | `            exit(2);` | Ends the program with exit status 2. |
| 1779 | `        }` | Ends the `if` of line 1776. |
| 1780 | `        if (eq)` | Tests whether the entry has a name. |
| 1781 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "%.*s", (int)(eq - tok), tok);` | Copies the text before the `=` as the name of the event. The format `%.*s` prints only the first `eq - tok` characters of the entry. The program uses the name as a column title in the header line of the C rows (line 3031) and in the error message of `open_counters` (line 1598). |
| 1782 | `        else if (cfg.nev < 5)` | The case of an entry without a name at one of the first 5 places of the list. |
| 1783 | `            strcpy(cfg.ev_name[cfg.nev], by_pos[cfg.nev]);` | The entry gets the name of `by_pos` for its place. |
| 1784 | `        else` | The case of an entry without a name at place 6 or later. |
| 1785 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "ev%d", cfg.nev);` | The entry gets the name `ev` plus its place number counted from 0, for example `ev5`. |
| 1786 | `        cfg.ev_code[cfg.nev] = strtoull(code, &end, 0);` | `strtoull` with base 0 turns the code text into a number. With base 0 a text that starts with `0x` is read as hexadecimal. |
| 1787 | `        if (end == code \|\| *end != '\0') {` | Tests whether the text is not a whole number: no digit was read, or other text follows the number. |
| 1788 | `            fprintf(stderr, "bad --events code: %s\n", code);` | Prints `bad --events code:` and the code text to stderr. |
| 1789 | `            exit(2);` | Ends the program with exit status 2. |
| 1790 | `        }` | Ends the `if` of line 1787. |
| 1791 | `        cfg.nev++;` | Counts the entry. Result in the whole-chip test: 6 events with the names `cbusy0`, `cbusy1`, `cbusy2`, `cbusy3`, `cbusy_mt`, `bus_access` and the codes 0x198, 0x199, 0x19a, 0x19b, 0x19c, 0x19 [Ref4]. |
| 1792 | `    }` | Ends the loop of line 1774. |
| 1793 | `}` | Ends the function `parse_events`. |

### Trial mode: the comment, the constants and the name tables (lines 1795 to 1830)

| Line | Source | Explanation |
|---:|---|---|
| 1795 | `/*` | Comment: starts the comment about the trial mode. The code of the trial mode goes from here to line 2886. `main` enters it only when an argument is the word `--trial` (lines 2912 to 2914). No argument line of the whole-chip test holds that word [Ref4]. So no function of the trial mode ran in that test. |
| 1796 | ` * Trial mode (--trial). Design: crb/new-test-kernel/tackle-8mb.md, "Runner` | Comment: the option `--trial` selects the trial mode. Its design is the section "Runner design" of the file `tackle-8mb.md`. |
| 1797 | ` * design". Formats: DECISIONS-bwx8.md.` | Comment: the file `DECISIONS-bwx8.md` describes the formats: the plan file and the output rows. |
| 1798 | ` *` | Comment: an empty line inside the comment. |
| 1799 | ` * The plan file gives the trials of the process. The whole plan is read and` | Comment: the plan file lists the trials of the process. The program reads the whole plan first. The sentence goes on in line 1800. |
| 1800 | ` * checked before the process pins, allocates or opens a counter. A defect` | Comment: the program checks the whole plan before it pins a thread, maps a buffer or opens a counter. The sentence about a defect starts here. |
| 1801 | ` * ends the process with status 2.` | Comment: a defect of the plan ends the process with exit status 2 (line 2554). |
| 1802 | ` *` | Comment: an empty line inside the comment. |
| 1803 | ` * One trial is a list of windows: previous activity (1), prefix (4),` | Comment: one trial is a list of windows. A window runs one kernel on one range of the buffer for a fixed time. The list starts with 1 window of previous activity and 4 windows of the prefix. |
| 1804 | ` * predecessor (1), target (nwin). timed_sequence() runs them. It calls only` | Comment: the list goes on with 1 window of the predecessor and `nwin` target windows. The function `timed_sequence` (line 1995) runs the windows. The comment does not name one case: with `--hot-copy` the function `timed_sequence_hot` (line 2056) runs them in its place. The sentence about its calls starts here. |
| 1805 | ` * the kernels and the clock. With count "read" it also reads the counter` | Comment: `timed_sequence` calls only the kernels and the clock. With the counter state `read` it also reads the counter group. The sentence goes on in line 1806. |
| 1806 | ` * group and the thread CPU clock at the boundaries of the target windows.` | Comment: with the counter state `read` it also reads the thread CPU time. Both readings are taken at the boundaries of the target windows. |
| 1807 | ` * Page state, context switches, counter open and close, and all output lie` | Comment: the readings of the page state and of the context switches, the opening and the closing of the counters, and all output are named here. The sentence ends in line 1808. |
| 1808 | ` * outside the timed sequence.` | Comment: all the steps of line 1807 lie outside the timed sequence. |
| 1809 | ` */` | Comment: the end of the comment. |
| 1810 | `#include <stdarg.h>` | Includes the header `stdarg.h`. It gives `va_list`, `va_start` and `va_end` for a function with a variable number of arguments. The function `plan_bad` uses them (line 2554). |
| 1811 | `#include <sys/resource.h>` | Includes the header `sys/resource.h`. It gives the call `getrusage`, which the function `switches` uses (line 2156). |
| 1813 | `#define BIN_NS 10000000L     /* requested width of a bin: 10 ms */` | `BIN_NS`: the requested width of a bin: 10000000 ns (10 ms). A bin is a part of a target window. Its record holds a clock time and the bytes up to that time (line 1846). |
| 1814 | `#define TRACE_CAP (1L << 20) /* --trace: events kept per trial */` | `TRACE_CAP`: the largest number of events that the trace keeps per trial: 1048576 (2 to the power 20). The trace is the event log of the option `--trace`. |
| 1815 | `#define PLAN_LINE1 "# bwx8-plan v1"` | `PLAN_LINE1`: the text that the first line of a plan file must have (line 2760). |
| 1816 | `#define PLAN_LINE3 "# trial cond rep prev pfx pred tgt nwin win_ms count bins"` | `PLAN_LINE3`: the text that the third line of a plan file must have (line 2765). It names the 11 fields of a trial line. |
| 1817 | `#define PLAN_FIELDS 11` | `PLAN_FIELDS`: a trial line of the plan has 11 fields. |
| 1818 | `#define MAX_PAIRS 64` | `MAX_PAIRS`: the second line of a plan holds at most 64 pairs of the form `key=value` (line 2643). |
| 1819 | `#define MAX_NWIN 4096` | `MAX_NWIN`: a trial has at most 4096 target windows (line 2695). |
| 1820 | `#define MAX_MS 3600000L` | `MAX_MS`: a duration of the plan is at most 3600000 ms (1 hour). |
| 1821 | `#define MAX_REC_BYTES (256UL << 20) /* bound of the record storage of one plan */` | `MAX_REC_BYTES`: the records of one plan may need at most 256 MiB (268435456 bytes) of memory (line 2719). |
| 1823 | `enum { PH_PREV, PH_PREFIX, PH_PRED, PH_TARGET };` | Number codes of the four phases of a trial, from 0 to 3: previous activity, prefix, predecessor and target. |
| 1824 | `enum { CS_CLOSED, CS_OPEN, CS_READ, CS_FAIL };` | Number codes of the counter state of a trial, from 0 to 3: closed, open, read and fail. |
| 1825 | `enum { EV_CLOCK, EV_KERNEL_FIRST, EV_COUNT_READ, EV_CPU_CLOCK, EV_PAGE_READ, EV_RUSAGE, EV_OUTPUT, EV_COUNT_OPEN, EV_COUNT_CLOSE };` | Number codes of the nine kinds of trace event: a clock read, the first kernel call of a window, a reading of the counter group, a reading of the thread CPU time, a reading of the page state, a `getrusage` call, an output step, the opening of the counter group and its closing. |
| 1826 | `static const char *const phase_name[] = { "prev", "prefix", "pred", "target" };` | `phase_name`: the printed names of the four phases, in the order of line 1823. The W rows and the TR rows show them (line 2328, line 2394). |
| 1827 | `static const char *const count_name[] = { "closed", "open", "read", "fail" };` | `count_name`: the printed names of the four counter states, in the order of line 1824. The E row shows one of them (line 2389). |
| 1828 | `static const char *const event_name[] = { "clock", "kernel_first", "count_read", "cpu_clock", "page_read",` | `event_name`: the printed names of the trace events, in the order of line 1825. The TR rows show them (line 2394, line 2397). This line holds the first five names. |
| 1829 | `                                          "rusage", "output", "count_open", "count_close" };` | Continues the list of line 1828: the last four names. |

### Trial mode: the structures of the plan, the windows, the records and the trace (lines 1831 to 1886)

| Line | Source | Explanation |
|---:|---|---|
| 1831 | `/* One kernel on a range for a time. k < 0: this part is absent ("-"). */` | Comment: a part is one kernel on one range for a time. A `k` below 0 means that the plan leaves this part out. The plan then holds the text `-` in its place. |
| 1832 | `struct part {` | Starts `struct part`: one kernel field of a trial line of the plan. |
| 1833 | `    int k;` | `k`: the index of the kernel in the kernel table, or -1 for a part that the plan leaves out. |
| 1834 | `    uint64_t size;` | `size`: the number of bytes of the range: the first `size` bytes of the buffer. |
| 1835 | `    long ms;` | `ms`: the duration in ms. The target part has no duration of its own and keeps 0 here. |
| 1836 | `};` | Ends `struct part`. |
| 1838 | `/* One line of the plan. */` | Comment: one line of the plan. |
| 1839 | `struct trial {` | Starts `struct trial`: one trial line of the plan file. |
| 1840 | `    char *f[PLAN_FIELDS]; /* the fields as text, for the S row */` | `f`: the 11 fields of the line as text. `print_s` prints them in the S row (line 2302). The comment says the same. |
| 1841 | `    int nwin, count, bins;` | `nwin`: the number of target windows. `count`: the counter state that the plan asks for (a code of line 1824). `bins`: 1 when the target windows record bins, 0 if not. |
| 1842 | `    long win_ms;` | `win_ms`: the requested duration of one target window, in ms. |
| 1843 | `    struct part prev, pfx, pred, tgt;` | The four parts of the trial: previous activity (`prev`), prefix (`pfx`), predecessor (`pred`) and target (`tgt`). |
| 1844 | `};` | Ends `struct trial`. |
| 1846 | `struct bin {` | Starts `struct bin`: one bin of a target window. |
| 1847 | `    int64_t t_end;  /* a clock read of the window loop */` | `t_end`: the clock time that closed the bin, in ns. The comment says: a clock read of the window loop. The loop reads the clock no more often with bins than without them. |
| 1848 | `    uint64_t bytes; /* bytes since the start of the window */` | `bytes`: the bytes that the window has counted from its start to that clock read. |
| 1849 | `};` | Ends `struct bin`. |
| 1851 | `/* One window. set_windows() fills the first group of fields before the first` | Comment: one window. `set_windows` (line 2231) fills the first group of fields (lines 1854 to 1859) before the first trial. The sentence about the second group starts here. |
| 1852 | ` * trial. timed_sequence() fills the second group. */` | Comment: `timed_sequence` fills the second group of fields (lines 1861 to 1863) when the window runs. The comment does not name one case: with `--hot-copy` the function `timed_sequence_hot` fills them (lines 2086 to 2089). |
| 1853 | `struct win {` | Starts `struct win`: the record of one window. |
| 1854 | `    int k, phase, widx;` | `k`: the index of the kernel in the kernel table. `phase`: the phase of the window (a code of line 1823). `widx`: the number of the window inside its phase, counted from 0. |
| 1855 | `    uint64_t size;` | `size`: the number of bytes that one kernel call covers: the first `size` bytes of the buffer. |
| 1856 | `    uint64_t passes; /* passes between two clock reads */` | `passes`: the number of kernel calls between two clock reads (line 2248). Each call is one whole pass over the range. |
| 1857 | `    int64_t dur_ns;` | `dur_ns`: the requested duration of the window, in ns. |
| 1858 | `    struct bin *bin; /* NULL: no bins */` | `bin`: the storage for the bins of this window. NULL means that the window records no bins. |
| 1859 | `    int bin_cap;` | `bin_cap`: the number of bins that fit into that storage. |
| 1861 | `    int nbin;` | `nbin`: the number of bins that the window closed. |
| 1862 | `    uint64_t bytes;` | `bytes`: the byte count of the window: `size` times the number of kernel calls. |
| 1863 | `    int64_t t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_start`, `t_end`: the clock read at the start of the window and the last clock read of the window, in ns of the Linux clock `CLOCK_MONOTONIC`. |
| 1864 | `};` | Ends `struct win`. |
| 1866 | `/* The record of one trial. */` | Comment: the record of one trial. |
| 1867 | `struct trec {` | Starts `struct trec`: the results of one trial. |
| 1868 | `    struct win *win;` | `win`: the window records of the trial, in the order in which the windows run. |
| 1869 | `    int nw;` | `nw`: the number of windows of the trial. |
| 1870 | `    struct counts *cnt; /* count "read": nwin + 1 readings, one per target boundary */` | `cnt`: the counter readings of the trial, or NULL. Only a trial with the counter state `read` has them: `nwin + 1` readings, one per boundary of the target windows. |
| 1871 | `    struct page pg[2];  /* before and after the timed sequence */` | `pg`: the page state of the buffer before the timed sequence (entry 0) and after it (entry 1). |
| 1872 | `    long long vm[2][4];` | `vm`: the four counters of `/proc/vmstat` before and after the timed sequence. |
| 1873 | `    uint64_t cpu[2];` | `cpu`: the thread CPU time before and after the timed sequence, in ns. |
| 1874 | `    long nvcsw[2], nivcsw[2];` | `nvcsw`, `nivcsw`: the counts of voluntary and of involuntary context switches of the thread, before and after the timed sequence (lines 2157 to 2158). |
| 1875 | `    long minflt[2]; /* minor page faults of the thread, for the --trace check */` | `minflt`: the count of minor page faults of the thread, before and after the timed sequence. A minor page fault is a page fault that Linux serves without disk access. The first touch of a page is one. The comment says that the check of `--trace` uses the count (line 2404). |
| 1876 | `    int state;   /* CS_* */` | `state`: the counter state of the trial as it ran (a code of line 1824). |
| 1877 | `    int sink_ok; /* 1, 0, or -1 if the trial ran no old read */` | `sink_ok`: the result of the sum check of the old read kernel (line 2213): 1 for a right sum, 0 for a wrong sum, -1 when the trial ran no old read kernel. |
| 1878 | `    int read_fail, close_fail;` | `read_fail`: the number of failed counter readings of the trial. `close_fail`: the number of counter file descriptors that did not close when the group was closed for this trial (line 2181). |
| 1879 | `};` | Ends `struct trec`. |
| 1881 | `struct tev {` | Starts `struct tev`: one event of the trace. |
| 1882 | `    int64_t t;` | `t`: the time of the event in ns. It is the time of the latest clock read (line 1932). |
| 1883 | `    int widx;` | `widx`: the window number of the event. Only the event of the first kernel call of a window sets it. |
| 1884 | `    uint8_t ev, phase;` | `ev`: the kind of event (a code of line 1825). `phase`: the phase of the window (a code of line 1823). |
| 1885 | `};` | Ends `struct tev`. |

### Trial mode: the worker state `struct tw` and the global variables (lines 1887 to 1921)

| Line | Source | Explanation |
|---:|---|---|
| 1887 | `/* The worker of the trial mode. */` | Comment: the worker of the trial mode. |
| 1888 | `struct tw {` | Starts `struct tw`: the state of the one worker thread of the trial mode. |
| 1889 | `    struct thread t; /* a, group_fd, ev_pos, nopen: used as in the interval mode */` | `t`: a `struct thread` (line 305), the record that a worker of the interval mode also has. The comment says that the fields `a`, `group_fd`, `ev_pos` and `nopen` are used as in the interval mode. |
| 1890 | `    uint64_t v;      /* every word of the buffer holds v */` | `v`: the value that every 8-byte word of the `--bytes` range of the buffer holds after the first touch (line 2460, line 2466). The comment says: every word of the buffer holds `v`. |
| 1891 | `    int fd[MAX_EV], nfd;` | `fd`: the file descriptors of the open counters. `nfd`: their number. `count_close` closes them (line 2099). |
| 1892 | `    int group_open; /* an open was tried and no close followed */` | `group_open`: 1 when the worker has tried to open the counter group and has not closed it after that. |
| 1893 | `    int open_fail;  /* events that did not open */` | `open_fail`: the number of events that did not open at the last opening of the group. |
| 1894 | `    int close_fail, read_fail;` | `close_fail`, `read_fail`: the numbers of failed `close` calls and of failed group readings. `run_trial` sets both to 0 for each trial (lines 2186 to 2187). |
| 1895 | `    char open_err[160];` | `open_err`: the error text of the first event that did not open. |
| 1896 | `    /* --trace */` | Comment: the fields below belong to the option `--trace`. |
| 1897 | `    struct tev *log;` | `log`: the event log of the trace. It is NULL without `--trace`. |
| 1898 | `    long nlog, ndrop;` | `nlog`: the number of events in the log. `ndrop`: the number of events that did not fit into the log. |
| 1899 | `    int64_t last_t;` | `last_t`: the time of the latest clock read. An event that is not a clock read gets this time. |
| 1900 | `    int cur_phase, cur_widx;` | `cur_phase`, `cur_widx`: the phase and the number of the window whose first kernel call was logged last (line 1956). |
| 1901 | `};` | Ends `struct tw`. |
| 1903 | `static struct {` | Starts the definition of `plan`, the variable that holds the plan and the options of the trial mode. |
| 1904 | `    const char *path;` | `path`: the path of the plan file (option `--plan`). |
| 1905 | `    uint64_t hash;` | `hash`: a 64-bit checksum of the bytes of the plan file (lines 2748 to 2750). |
| 1906 | `    char *pair[MAX_PAIRS];` | `pair`: the `key=value` pairs of the second line of the plan, as text. |
| 1907 | `    int npair;` | `npair`: the number of these pairs. |
| 1908 | `    struct trial *tr;` | `tr`: the trials of the plan, one `struct trial` per trial line. |
| 1909 | `    int n;` | `n`: the number of trials. |
| 1910 | `    int ctl_cpu, trace;` | `ctl_cpu`: the CPU of the controlling thread (option `--ctl-cpu`, default 0). `trace`: 1 with the option `--trace`. |
| 1911 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 1912 | `    size_t rec_pad; /* --rec-pad: unused bytes before win[] in the record block */` | `rec_pad`: the value of `--rec-pad`: the number of unused bytes before the window records in the record block (line 2278). |
| 1913 | `    int hot_copy;   /* --hot-copy: timed_sequence_hot() runs the windows */` | `hot_copy`: 1 with the option `--hot-copy`. Then `timed_sequence_hot` runs the windows (lines 2205 to 2206). |
| 1914 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 1915 | `} plan;` | Ends the definition of `plan`. Every field starts at 0. |
| 1917 | `static struct trec *rec;` | `rec`: the records of all trials, one `struct trec` per trial. `alloc_records` sets the pointer (line 2274). |
| 1918 | `static struct {` | Starts the definition of `recsz`, the sizes of the record storage. |
| 1919 | `    size_t windows, bins, counts, trace, bytes;` | `windows`, `bins`, `counts`, `trace`: the numbers of window records, bins, counter readings and trace events that the plan needs. `bytes`: the size of the record block in bytes. `plan_trial` computes all five (lines 2709 to 2717). |
| 1920 | `} recsz;` | Ends the definition of `recsz`. |

### Trial mode: the trace helpers `tev_add`, `tclock` and `tcpu` (lines 1922 to 1951)

| Line | Source | Explanation |
|---:|---|---|
| 1922 | `/* --trace. An event that is not a clock read carries the time of the latest` | Comment: the option `--trace`. An event that is not a clock read carries the time of the latest clock read. The reason follows in line 1923. |
| 1923 | ` * clock read: the trace adds no clock read of its own. */` | Comment: the trace adds no clock read of its own. |
| 1924 | `static inline void tev_add(struct tw *w, int ev, int phase, int widx)` | Starts the function `tev_add`. It appends one event to the trace: the kind `ev`, the phase and the window number. Without `--trace` it does nothing. |
| 1925 | `{` | Opens the body of `tev_add`. The whole-chip test did not call this function [Ref4]. |
| 1926 | `    if (!w->log)` | Tests whether there is no log. That is the case without `--trace`. |
| 1927 | `        return;` | Without a log the function returns immediately. |
| 1928 | `    if (w->nlog == TRACE_CAP) {` | Tests whether the log is full: it holds `TRACE_CAP` (1048576) events. |
| 1929 | `        w->ndrop++;` | A full log does not keep the event. It only counts it in `ndrop`. |
| 1930 | `        return;` | The function then returns and stores nothing. |
| 1931 | `    }` | Ends the `if` of line 1928. |
| 1932 | `    w->log[w->nlog++] = (struct tev){ .t = w->last_t, .widx = widx, .ev = (uint8_t)ev, .phase = (uint8_t)phase };` | Appends the event to the log. Its time is `last_t`, the time of the latest clock read. |
| 1933 | `}` | Ends the function `tev_add`. |
| 1935 | `static inline int64_t tclock(struct tw *w)` | Starts the function `tclock`. It reads the clock for the trial mode and returns the time in ns. Every clock read of a timed sequence goes through it (line 2005, line 2012). |
| 1936 | `{` | Opens the body of `tclock`. The whole-chip test did not call this function [Ref4]. |
| 1937 | `    int64_t t = now_ns();` | Reads the clock with `now_ns` (line 327). |
| 1938 | `    if (w->log) {` | Tests whether a log exists (`--trace`). |
| 1939 | `        w->last_t = t;` | Stores the time as the time of the latest clock read. |
| 1940 | `        tev_add(w, EV_CLOCK, 0, 0);` | Logs the clock read as an event. |
| 1941 | `    }` | Ends the `if` of line 1938. |
| 1942 | `    return t;` | Returns the time. |
| 1943 | `}` | Ends the function `tclock`. |
| 1945 | `static uint64_t tcpu(struct tw *w)` | Starts the function `tcpu`. It returns the thread CPU time in ns and logs the reading. |
| 1946 | `{` | Opens the body of `tcpu`. The whole-chip test did not call this function [Ref4]. |
| 1947 | `    uint64_t c = cpu_ns();` | Reads the thread CPU time with `cpu_ns` (line 1609). |
| 1948 | `    tev_add(w, EV_CPU_CLOCK, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 1949 | `    return c;` | Returns the CPU time. |
| 1950 | `}` | Ends the function `tcpu`. |

### Trial mode: the functions `tcall` and `tcount` (lines 1952 to 1984)

| Line | Source | Explanation |
|---:|---|---|
| 1952 | `/* Every kernel call of a trial goes through here, and from here through the` | Comment: every kernel call of a trial goes through this function, and from here through the unchanged function `call`. With `--hot-copy` the first part is no longer true: the kernel calls then go through `tcall_hot` (line 2035), and from there through `call`. |
| 1953 | ` * unchanged call(). The trace gets the first call of each window. */` | Comment: the trace gets the first call of each window. |
| 1954 | `static inline void tcall(struct tw *w, const struct win *r, volatile uint64_t *sink)` | Starts the function `tcall`. It runs the kernel of the window `r` once on the first `r->size` bytes of the buffer. |
| 1955 | `{` | Opens the body of `tcall`. The whole-chip test did not call this function [Ref4]. |
| 1956 | `    if (w->log && (r->phase != w->cur_phase \|\| r->widx != w->cur_widx)) {` | Tests, only with `--trace`, whether this call belongs to another window than the call before it. |
| 1957 | `        w->cur_phase = r->phase;` | Remembers the phase of the new window. |
| 1958 | `        w->cur_widx = r->widx;` | Remembers the number of the new window. |
| 1959 | `        tev_add(w, EV_KERNEL_FIRST, r->phase, r->widx);` | Logs the first kernel call of the window as an event. |
| 1960 | `    }` | Ends the `if` of line 1956. |
| 1961 | `    call(&kernels[r->k], &w->t, 0, r->size, 0, sink);` | The kernel call. It goes through `call` (line 1491), the function that the interval mode also uses: offset 0, `r->size` bytes, and 0 as the store value. The plan accepts read kernels only (line 2622), and a read kernel does not use the store value. |
| 1962 | `}` | Ends the function `tcall`. |
| 1964 | `/* Group read and thread CPU clock, at a boundary of a target window. Not` | Comment: the function takes a group reading and reads the thread CPU clock, at a boundary of a target window. The sentence about inlining starts here. |
| 1965 | ` * inlined: build8.sh lists the branch targets of timed_sequence(), and this` | Comment: the function is not inlined. The script `build8.sh` lists the branch targets of `timed_sequence`. The sentence goes on in line 1966. |
| 1966 | ` * function must be one name there. */` | Comment: this function must be one name in that list. |
| 1967 | `__attribute__((noinline)) static void tcount(struct tw *w, struct counts *c)` | Starts the function `tcount`. It reads the counter group and then the thread CPU time into `c`. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 1968 | `{` | Opens the body of `tcount`. The whole-chip test did not call this function [Ref4]. |
| 1969 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest group reading: 3 header words plus 8 counter values, 8 bytes each. |
| 1970 | `    if (w->t.group_fd >= 0) {` | Tests whether a counter group is open. |
| 1971 | `        ssize_t want = (ssize_t)((3 + (size_t)w->t.nopen) * sizeof buf[0]);` | `want`: the size in bytes that a complete reading must have: 3 header words plus one word per open counter, 8 bytes each. |
| 1972 | `        if (read(w->t.group_fd, buf, sizeof buf) != want \|\| buf[0] != (uint64_t)w->t.nopen) {` | One `read` on the group leader. The reading is rejected when its size is not `want`, or when its counter number `nr` is not the number of open counters. |
| 1973 | `            w->read_fail++;` | A rejected reading only adds 1 to `read_fail`. In `read_group` a rejected reading ends the process (lines 1622 to 1625). |
| 1974 | `        } else {` | The case of a good reading. |
| 1975 | `            c->enabled = buf[1];` | Stores the enabled time of the group, in ns. |
| 1976 | `            c->running = buf[2];` | Stores the running time of the group, in ns. |
| 1977 | `            for (int i = 0; i < w->t.nopen; i++)` | Loop over the open counters. |
| 1978 | `                c->val[i] = buf[3 + i];` | Stores one value per open counter. |
| 1979 | `        }` | Ends the `else` of line 1974. |
| 1980 | `        tev_add(w, EV_COUNT_READ, 0, 0);` | Logs the group reading as an event. Without `--trace` this call does nothing. |
| 1981 | `    }` | Ends the `if` of line 1970. |
| 1982 | `    c->cpu_ns = tcpu(w);` | Reads the thread CPU time through `tcpu` (line 1945) and stores it. This line runs also when no group is open. |
| 1983 | `}` | Ends the function `tcount`. |

### Function `timed_sequence` (trial mode): the timed windows of one trial (lines 1985 to 2031)

| Line | Source | Explanation |
|---:|---|---|
| 1985 | `/*` | Comment: starts the comment of the function `timed_sequence`. The comment ends in line 1994. |
| 1986 | ` * The timed sequence of one trial. Each window runs whole passes over` | Comment: the function is the timed sequence of one trial. Each window runs whole passes over its range. The sentence goes on in line 1987. |
| 1987 | ` * [0, size) and reads the clock after every "passes" passes. It ends at the` | Comment: the range is the first `size` bytes of the buffer. The window reads the clock after every `passes` passes. The sentence about the end of a window starts here. |
| 1988 | ` * first clock read at or after its duration. At a boundary the clock is read` | Comment: a window ends at the first clock read at or after its duration. The sentence about a boundary between two windows starts here. |
| 1989 | ` * for the end of the window and again for the start of the next one, so the` | Comment: at a boundary the clock is read once for the end of the window and once more for the start of the next window. The sentence goes on in line 1990. |
| 1990 | ` * gap is measured. No output, allocation, page read, sleep or warm-up pass` | Comment: so the gap between two windows is measured. The function holds no output, no allocation, no reading of the page state, no sleep and no warm-up pass. This sentence ends in line 1991. |
| 1991 | ` * is in here. Not inlined: build8.sh and test_runner8.py read the branch` | Comment: the function is not inlined. The script `build8.sh` and the test `test_runner8.py` read the branch targets of this function from the machine code. The sentence goes on in line 1992. |
| 1992 | ` * targets of this function from the machine code. Only clock_gettime, the` | Comment: only three branch targets are allowed in this function. The first is the library function `clock_gettime`, which reads the clock. The list goes on in line 1993. |
| 1993 | ` * kernel call of call() and tcount() are allowed there.` | Comment: the other two allowed targets are the kernel call of `call` and the function `tcount`. |
| 1994 | ` */` | Comment: the end of the comment. |
| 1995 | `__attribute__((noinline)) static void timed_sequence(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)` | Starts the function `timed_sequence`. It runs all windows of the trial record `r`, one after another. For each window it stores the byte count and two clock times. `count_read` is 1 for a trial with the counter state `read`. `sink` receives the sum of an old read kernel. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 1996 | `{` | Opens the body of `timed_sequence`. The whole-chip test did not call this function [Ref4]. The timed loop of that test is in `worker` (lines 1688 to 1701). |
| 1997 | `    for (int i = 0; i < r->nw; i++) {` | Loop over the windows of the trial, in the order in which they run. |
| 1998 | `        struct win *x = &r->win[i];` | `x`: the record of this window. |
| 1999 | `        uint64_t bytes = 0;` | `bytes`: the byte count of the window. It starts at 0. |
| 2000 | `        int64_t t0, t1, next_bin;` | Clock values in ns: `t0` (the start of the window), `t1` (the latest clock read) and `next_bin` (the requested end of the bin that is open). |
| 2001 | `        int nbin = 0;` | `nbin`: the number of bins that this window has closed. |
| 2003 | `        if (count_read && x->phase == PH_TARGET)` | Tests whether the trial reads counters and this window is a target window. |
| 2004 | `            tcount(w, &r->cnt[x->widx]);` | Counter reading before a target window: `tcount` (line 1967) reads the counter group and the thread CPU time into the reading with the number `widx`. It runs before the start clock read of line 2005. So it lies outside the window. |
| 2005 | `        t0 = tclock(w);` | Start of the window: the clock read `t0` (`tclock`, line 1935). |
| 2006 | `        next_bin = t0 + BIN_NS;` | The first bin has its requested end 10 ms (`BIN_NS`) after `t0`. |
| 2007 | `        do {` | Starts the timed loop of the window. Its body runs at least once. |
| 2008 | `            for (uint64_t c = 0; c < x->passes; c++) {` | Runs `passes` kernel calls without a clock read between them. |
| 2009 | `                tcall(w, x, sink);` | Timed kernel call: one pass of the kernel of the window over the first `size` bytes of the buffer (`tcall`, line 1954). |
| 2010 | `                bytes += x->size;` | Bytes counted: each call adds `size`, the size of the range that was passed to the kernel. Nothing is counted inside a kernel. |
| 2011 | `            }` | Ends the `for` of line 2008. |
| 2012 | `            t1 = tclock(w);` | Clock read after the passes: `t1`. The clock is never read inside a pass. |
| 2013 | `            /* A bin closes on this clock read if its requested end has` | Comment: a bin closes at this clock read when its requested end has passed. The sentence about the last bin starts here. |
| 2014 | `             * passed. The last clock read of the window closes the last bin. */` | Comment: the last clock read of the window closes the last bin. |
| 2015 | `            if (x->bin && (t1 >= next_bin \|\| t1 - t0 >= x->dur_ns) && nbin < x->bin_cap) {` | Tests three things. The window records bins. A bin can close now: its requested end has passed, or the window is over. The storage has room for one more bin. |
| 2016 | `                x->bin[nbin].t_end = t1;` | Stores the clock time `t1` as the end of the bin. |
| 2017 | `                x->bin[nbin].bytes = bytes;` | Stores the bytes that the window has counted up to this clock read. |
| 2018 | `                nbin++;` | Counts the bin. |
| 2019 | `                while (next_bin <= t1)` | Moves the requested end of the next bin forward in steps of 10 ms until it lies after `t1`. |
| 2020 | `                    next_bin += BIN_NS;` | The body of the loop of line 2019: one step of 10 ms. |
| 2021 | `            }` | Ends the `if` of line 2015. |
| 2022 | `        } while (t1 - t0 < x->dur_ns);` | Stop rule of a window. The loop repeats while less than `dur_ns` has passed after `t0`. So a window ends at its first clock read at or after its requested duration, and only at the end of a whole pass. |
| 2023 | `        x->bytes = bytes;` | Stores the byte count in the window record. The W row prints it (line 2329). This function computes no rate. |
| 2024 | `        x->t_start = t0;` | Stores `t0` as the start time of the window. |
| 2025 | `        x->t_end = t1;` | Stores the last `t1` as the end time of the window. The next window reads the clock again for its own start (line 2005). So the time between two windows is measured and belongs to no window. |
| 2026 | `        x->nbin = nbin;` | Stores the number of bins that the window closed. |
| 2027 | `    }` | Ends the loop over the windows (line 1997). |
| 2028 | `    if (count_read)` | Tests whether the trial reads counters. |
| 2029 | `        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);` | Last counter reading, after the last window. It goes into the reading with the number of the last target window plus 1. So a trial with `nwin` target windows has `nwin + 1` readings. |
| 2030 | `}` | Ends the function `timed_sequence`. |

### Function `tcall_hot` (trial mode): `tcall` with value arguments (lines 2032 to 2044)

| Line | Source | Explanation |
|---:|---|---|
| 2032 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. This block ends in line 2095. |
| 2033 | `/* tcall() for timed_sequence_hot(): the kernel index, the phase, the window` | Comment: this function is the `tcall` of `timed_sequence_hot`. The kernel index, the phase and the window number come as values. The list goes on in line 2034. |
| 2034 | ` * index and the size come by value, so no field of win[i] is read here. */` | Comment: the size also comes as a value. So the function reads no field of the window record. |
| 2035 | `static inline void tcall_hot(struct tw *w, int k, int phase, int widx, uint64_t size, volatile uint64_t *sink)` | Starts the function `tcall_hot`. It does the same as `tcall` (line 1954), but the kernel index `k`, the phase, the window number and the size arrive as arguments. So it reads no field of the window record. |
| 2036 | `{` | Opens the body of `tcall_hot`. The whole-chip test did not call this function [Ref4]. |
| 2037 | `    if (w->log && (phase != w->cur_phase \|\| widx != w->cur_widx)) {` | Tests, only with `--trace`, whether this call belongs to another window than the call before it. |
| 2038 | `        w->cur_phase = phase;` | Remembers the phase of the new window. |
| 2039 | `        w->cur_widx = widx;` | Remembers the number of the new window. |
| 2040 | `        tev_add(w, EV_KERNEL_FIRST, phase, widx);` | Logs the first kernel call of the window as an event. |
| 2041 | `    }` | Ends the `if` of line 2037. |
| 2042 | `    call(&kernels[k], &w->t, 0, size, 0, sink);` | The kernel call. It goes through `call` (line 1491): offset 0, `size` bytes, and 0 as the store value. |
| 2043 | `}` | Ends the function `tcall_hot`. |

### Function `timed_sequence_hot` (trial mode): the variant for `--hot-copy` (lines 2045 to 2095)

| Line | Source | Explanation |
|---:|---|---|
| 2045 | `/*` | Comment: starts the comment of the function `timed_sequence_hot`. The comment ends in line 2055. |
| 2046 | ` * --hot-copy: timed_sequence() with one difference. Before the start clock` | Comment: with the option `--hot-copy` this function runs the windows. It is `timed_sequence` with one difference. The sentence about the difference starts here. |
| 2047 | ` * read of a window it copies the fields of win[i] that the window loop needs` | Comment: before the start clock read of a window the function copies the fields of the window record that the window loop needs. The sentence goes on in line 2048. |
| 2048 | ` * into local variables. After the end clock read it stores bytes, t_start,` | Comment: the copies are local variables. After the end clock read the function stores the byte count and the start time. The list goes on in line 2049. |
| 2049 | ` * t_end and nbin. Between the first pass and the last pass of a window it` | Comment: it also stores the end time and the number of bins. The sentence about the time between the first and the last pass starts here. |
| 2050 | ` * does not read or write win[i]. The compiler cannot read a field again` | Comment: between the first pass and the last pass of a window the function does not read or write the window record. The sentence about the compiler starts here. |
| 2051 | ` * inside the loop in place of the local copy: the loop calls a kernel` | Comment: the compiler cannot read a field again inside the loop in place of the local copy. The reason starts here: the loop calls a kernel. |
| 2052 | ` * through a pointer, and such a call may change any memory. The self-test` | Comment: the kernel is called through a pointer, and such a call may change any memory. The sentence about the self-test starts here. |
| 2053 | ` * checks it on the machine code (test_hot_touch). The same rules as for` | Comment: the self-test checks this on the machine code, in its function `test_hot_touch`. The last sentence of the comment starts here. |
| 2054 | ` * timed_sequence() hold for the calls made here.` | Comment: the calls that this function makes follow the same rules as the calls of `timed_sequence` (lines 1991 to 1993). |
| 2055 | ` */` | Comment: the end of the comment. |
| 2056 | `__attribute__((noinline)) static void timed_sequence_hot(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)` | Starts the function `timed_sequence_hot`. It runs the windows of one trial as `timed_sequence` does (line 1995), with the same arguments. The difference: the window loop works on local copies of the fields of the window record. |
| 2057 | `{` | Opens the body of `timed_sequence_hot`. The whole-chip test did not call this function [Ref4]. |
| 2058 | `    for (int i = 0; i < r->nw; i++) {` | Loop over the windows of the trial, in the order in which they run. |
| 2059 | `        struct win *x = &r->win[i];` | `x`: the record of this window. |
| 2060 | `        const int k = x->k, phase = x->phase, widx = x->widx, bin_cap = x->bin_cap;` | Local copies of four fields of the window record: the kernel index, the phase, the window number and the room for bins. |
| 2061 | `        const uint64_t size = x->size, passes = x->passes;` | Local copies of the range size and of the number of passes between two clock reads. |
| 2062 | `        const int64_t dur_ns = x->dur_ns;` | Local copy of the requested duration. |
| 2063 | `        struct bin *const bin = x->bin;` | Local copy of the pointer to the bin storage. |
| 2064 | `        uint64_t bytes = 0;` | `bytes`: the byte count of the window. It starts at 0. |
| 2065 | `        int64_t t0, t1, next_bin;` | Clock values in ns: `t0`, `t1` and `next_bin`, as in line 2000. |
| 2066 | `        int nbin = 0;` | `nbin`: the number of bins that this window has closed. |
| 2068 | `        if (count_read && phase == PH_TARGET)` | Tests whether the trial reads counters and this window is a target window. |
| 2069 | `            tcount(w, &r->cnt[widx]);` | Counter reading before a target window, as in line 2004. It lies outside the window. |
| 2070 | `        t0 = tclock(w);` | Start of the window: the clock read `t0`. |
| 2071 | `        next_bin = t0 + BIN_NS;` | The first bin has its requested end 10 ms (`BIN_NS`) after `t0`. |
| 2072 | `        do {` | Starts the timed loop of the window. Its body runs at least once. |
| 2073 | `            for (uint64_t c = 0; c < passes; c++) {` | Runs `passes` kernel calls without a clock read between them. |
| 2074 | `                tcall_hot(w, k, phase, widx, size, sink);` | Timed kernel call through `tcall_hot` (line 2035): one pass of the kernel over the first `size` bytes of the buffer. |
| 2075 | `                bytes += size;` | Bytes counted: each call adds `size`, the size of the range that was passed to the kernel. |
| 2076 | `            }` | Ends the `for` of line 2073. |
| 2077 | `            t1 = tclock(w);` | Clock read after the passes: `t1`. |
| 2078 | `            if (bin && (t1 >= next_bin \|\| t1 - t0 >= dur_ns) && nbin < bin_cap) {` | The bin test of line 2015, with the local copies: the window records bins, a bin can close now, and the storage has room. |
| 2079 | `                bin[nbin].t_end = t1;` | Stores `t1` as the end of the bin. The bin storage is not a part of the window record. |
| 2080 | `                bin[nbin].bytes = bytes;` | Stores the bytes that the window has counted up to this clock read. |
| 2081 | `                nbin++;` | Counts the bin. |
| 2082 | `                while (next_bin <= t1)` | Moves the requested end of the next bin forward in steps of 10 ms until it lies after `t1`. |
| 2083 | `                    next_bin += BIN_NS;` | The body of the loop of line 2082: one step of 10 ms. |
| 2084 | `            }` | Ends the `if` of line 2078. |
| 2085 | `        } while (t1 - t0 < dur_ns);` | Stop rule of a window, as in line 2022: the window ends at its first clock read at or after its requested duration. |
| 2086 | `        x->bytes = bytes;` | After the end clock read: stores the byte count in the window record. |
| 2087 | `        x->t_start = t0;` | Stores `t0` as the start time of the window. |
| 2088 | `        x->t_end = t1;` | Stores the last `t1` as the end time of the window. |
| 2089 | `        x->nbin = nbin;` | Stores the number of bins that the window closed. |
| 2090 | `    }` | Ends the loop over the windows (line 2058). |
| 2091 | `    if (count_read)` | Tests whether the trial reads counters. |
| 2092 | `        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);` | Last counter reading, after the last window, as in line 2029. |
| 2093 | `}` | Ends the function `timed_sequence_hot`. |
| 2095 | `/* bwx10- */` | Comment: marks the end of the block that `bwx10` added. The block starts in line 2032. The code from here to line 2886 also belongs to the trial mode. The whole-chip test did not run it: no argument line of that test holds the word `--trial` [Ref4]. The self-test also calls some of these functions. It runs only with the option `--selftest` (line 2919), and no argument line of the test holds it [Ref4]. Cross-check with the data: the trial mode prints rows that start with `M` before its first trial (line 2481). In the 9 csv files of the test every line starts with `I`, `T`, `P`, `C` or `#` (counted with awk on 2026-11-21) [Ref5]. |

### Function `count_close` (trial mode): close the counter group (lines 2096 to 2108)

| Line | Source | Explanation |
|---:|---|---|
| 2096 | `static void count_close(struct tw *w)` | Starts the function `count_close`. It closes every counter of the worker and sets the group state of the worker back to closed. |
| 2097 | `{` | Opens the body of `count_close`. The whole-chip test did not call this function [Ref4]. |
| 2098 | `    for (int i = 0; i < w->nfd; i++)` | Loop over the counter file descriptors that `count_open` stored in `w->fd` (line 2136). |
| 2099 | `        if (close(w->fd[i]) != 0)` | Closes one counter and tests whether the `close` call failed. |
| 2100 | `            w->close_fail++;` | A failed `close` adds 1 to `w->close_fail`. |
| 2101 | `    w->nfd = 0;` | No file descriptor is stored any more. |
| 2102 | `    w->t.group_fd = -1;` | The group has no leader. |
| 2103 | `    w->t.nopen = 0;` | No event is open. |
| 2104 | `    w->group_open = 0;` | The group counts as closed. |
| 2105 | `    w->open_fail = 0;` | The count of events that did not open is 0 again. |
| 2106 | `    tev_add(w, EV_COUNT_CLOSE, 0, 0);` | Logs the closing as an event. Without `--trace` this call does nothing. |
| 2107 | `}` | Ends the function `count_close`. |

### Function `count_open` (trial mode): open the counter group (lines 2109 to 2143)

| Line | Source | Explanation |
|---:|---|---|
| 2109 | `/* One group, user mode only, opened by the pinned worker for itself. The` | Comment: the worker has one counter group, which counts in user mode only. The pinned worker opens it for itself. The next sentence starts here. |
| 2110 | ` * events count from the open on. An event that does not open is counted in` | Comment: the events count from the moment of the open. The sentence about an event that does not open starts here. |
| 2111 | ` * open_fail and is printed as NA. */` | Comment: an event that does not open is counted in `open_fail` and is printed as `NA`. |
| 2112 | `static void count_open(struct tw *w)` | Starts the function `count_open`. It is the version of `open_counters` (line 1582) for the trial mode: it opens one counter per event of `cfg` and joins the counters into one group. Two things differ. It keeps every file descriptor in `w->fd`: `count_close` needs them to close the group. And it writes no message to stderr. |
| 2113 | `{` | Opens the body of `count_open`. The whole-chip test did not call this function. That test uses `open_counters` [Ref4]. |
| 2114 | `    w->t.group_fd = -1;` | Start state: no group leader. |
| 2115 | `    w->t.nopen = 0;` | Start state: 0 open events. |
| 2116 | `    w->nfd = 0;` | Start state: no stored file descriptor. |
| 2117 | `    w->open_fail = 0;` | Start state: 0 events that did not open. |
| 2118 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `cfg`, in the order of the option `--events`. |
| 2119 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 2120 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. The field `disabled` stays 0, so a counter counts from the moment it is opened. |
| 2121 | `        a.type = (uint32_t)cfg.pmu_type;` | `type`: the PMU type (`--pmu-type`). |
| 2122 | `        a.size = sizeof a;` | `size`: the size of the structure. |
| 2123 | `        a.config = cfg.ev_code[e];` | `config`: the event code of this event. |
| 2124 | `        a.exclude_kernel = 1;` | The counter does not count code of the Linux kernel. |
| 2125 | `        a.exclude_hv = 1;` | The counter does not count code of a hypervisor. With line 2124 it counts in user mode only. |
| 2126 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | One `read` of the group returns the values of all its counters, the enabled time and the running time, as in line 1594. |
| 2127 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, w->t.group_fd, 0);` | The system call `perf_event_open` opens the counter for the calling thread, on any CPU that it runs on, as in line 1595. The first counter starts a new group. A later counter joins the group of the leader. |
| 2128 | `        if (fd < 0) {` | Tests whether the open failed. |
| 2129 | `            if (w->open_fail++ == 0)` | Counts the event as not opened. The test is true only for the first such event of this opening. |
| 2130 | `                snprintf(w->open_err, sizeof w->open_err, "%s type %ld code 0x%llx: %s", cfg.ev_name[e], cfg.pmu_type,` | For the first such event: stores an error text in `w->open_err`: the event name, the PMU type, the event code and the error text of Linux. `emit_trial` prints it in an X row (line 2364). |
| 2131 | `                         (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 2130: the event code and the error text (`strerror(errno)`). |
| 2132 | `            w->t.ev_pos[e] = -1;` | The event gets the position -1. Its field in the C rows is `NA` (lines 2350 to 2351). |
| 2133 | `            continue;` | The loop goes on with the next event. |
| 2134 | `        }` | Ends the `if` of line 2128. |
| 2135 | `        w->t.ev_pos[e] = w->t.nopen++;` | The open succeeded. The event gets its position in a group reading, and `nopen` counts it. |
| 2136 | `        w->fd[w->nfd++] = fd;` | Keeps the file descriptor for `count_close` (line 2099). |
| 2137 | `        if (w->t.group_fd < 0)` | Tests whether the group has no leader yet. |
| 2138 | `            w->t.group_fd = fd;` | The first counter that opens becomes the leader of the group. |
| 2139 | `    }` | Ends the loop over the events (line 2118). |
| 2140 | `    w->group_open = 1;` | The group counts as open from here on. This is also the case when no event opened. |
| 2141 | `    tev_add(w, EV_COUNT_OPEN, 0, 0);` | Logs the opening as an event. Without `--trace` this call does nothing. |
| 2142 | `}` | Ends the function `count_open`. |

### Functions `page_read`, `switches` and `first_multiplexed` (trial mode) (lines 2144 to 2172)

| Line | Source | Explanation |
|---:|---|---|
| 2144 | `static void page_read(struct tw *w, struct trec *r, int at)` | Starts the function `page_read`. It reads the page state of the one buffer of the worker and the four counters of `/proc/vmstat` into the trial record `r`. `at` is 0 before the timed sequence and 1 after it. |
| 2145 | `{` | Opens the body of `page_read`. The whole-chip test did not call this function [Ref4]. The `# page_read` lines of the csv files of that test do not come from it [Ref5]. `main` prints them in line 3118. |
| 2146 | `    uint64_t *buf[1] = { w->t.a };` | `buf`: the address of the one buffer of the worker. |
| 2147 | `    read_smaps(&r->pg[at], buf, 1);` | `read_smaps` (line 1515) reads the size of the buffer and its part on 2 MiB pages into `r->pg[at]`. |
| 2148 | `    read_vmstat(r->vm[at]);` | `read_vmstat` (line 1545) reads the four counters of `/proc/vmstat` into `r->vm[at]`. |
| 2149 | `    tev_add(w, EV_PAGE_READ, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 2150 | `}` | Ends the function `page_read`. |
| 2152 | `/* Context-switch counts of the calling thread. -1: not readable. */` | Comment: the function reads the context-switch counts of the calling thread. A value of -1 means that a count could not be read. The function also stores the count of minor page faults (line 2159), which the comment does not name. |
| 2153 | `static void switches(struct tw *w, struct trec *r, int at)` | Starts the function `switches`. It stores three counts of the calling thread in the trial record `r`: the voluntary context switches, the involuntary context switches and the minor page faults. `at` is 0 before the timed sequence and 1 after it. |
| 2154 | `{` | Opens the body of `switches`. The whole-chip test did not call this function [Ref4]. |
| 2155 | `    struct rusage ru;` | `ru`: the structure that `getrusage` fills. |
| 2156 | `    int ok = getrusage(RUSAGE_THREAD, &ru) == 0;` | `getrusage` with `RUSAGE_THREAD` asks Linux for the resource use of the calling thread. `ok` is 1 when the call succeeded. |
| 2157 | `    r->nvcsw[at] = ok ? ru.ru_nvcsw : -1;` | Stores `ru_nvcsw`, the number of voluntary context switches: the thread stopped running by its own request, usually to wait for something. A failed call stores -1. |
| 2158 | `    r->nivcsw[at] = ok ? ru.ru_nivcsw : -1;` | Stores `ru_nivcsw`, the number of involuntary context switches: Linux took the CPU away from the thread. A failed call stores -1. |
| 2159 | `    r->minflt[at] = ok ? ru.ru_minflt : -1;` | Stores `ru_minflt`, the number of minor page faults. These are page faults that need no disk access. The first touch of a page is one. A failed call stores -1. |
| 2160 | `    tev_add(w, EV_RUSAGE, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 2161 | `}` | Ends the function `switches`. |
| 2163 | `/* The index of the first target window whose counters ran for less time` | Comment: the function returns the index of the first target window whose counters ran for less time than they were enabled. The sentence ends in line 2164. |
| 2164 | ` * than they were enabled, or -1. cnt holds nwin + 1 readings. */` | Comment: it returns -1 when there is no such window. `cnt` holds `nwin + 1` readings. |
| 2165 | `static int first_multiplexed(const struct counts *cnt, int nwin)` | Starts the function `first_multiplexed`. `cnt` holds one counter reading per boundary of the `nwin` target windows. The function looks for a target window in which the counters did not count all the time. |
| 2166 | `{` | Opens the body of `first_multiplexed`. The whole-chip test did not call this function [Ref4]. |
| 2167 | `    for (int i = 0; i < nwin; i++)` | Loop over the target windows. |
| 2168 | `        if (cnt[i + 1].running - cnt[i].running < cnt[i + 1].enabled - cnt[i].enabled)` | Compares, for one target window, the growth of the running time with the growth of the enabled time between its two readings. A smaller growth of the running time means that the counters did not count all the time in this window. |
| 2169 | `            return i;` | Returns the index of the first such window. |
| 2170 | `    return -1;` | Returns -1 when there is no such window. |
| 2171 | `}` | Ends the function `first_multiplexed`. |

### Function `run_trial` (trial mode): one trial, without output (lines 2173 to 2216)

| Line | Source | Explanation |
|---:|---|---|
| 2173 | `/* One trial: the work before the timed sequence, the timed sequence, the` | Comment: the function runs one trial: the work before the timed sequence, then the timed sequence. The list ends in line 2174. |
| 2174 | ` * work after it. Prints nothing. */` | Comment: then comes the work after the timed sequence. The function prints nothing. |
| 2175 | `static void run_trial(struct tw *w, const struct trial *p, struct trec *r, volatile uint64_t *sink)` | Starts the function `run_trial`. `p` is the trial of the plan. `r` is the record of the trial. `sink` receives the sum of an old read kernel. |
| 2176 | `{` | Opens the body of `run_trial`. The whole-chip test did not call this function [Ref4]. |
| 2177 | `    uint64_t expect = 0;` | `expect`: the sum that the last old read kernel of the trial must return. |
| 2178 | `    int old = -1;` | `old`: the index of the last window with an old read kernel, or -1 when the trial has none. |
| 2180 | `    if (p->count == CS_CLOSED && w->group_open)` | Tests whether the plan wants the counters closed for this trial while the group is open. |
| 2181 | `        count_close(w);` | Then the group is closed (`count_close`, line 2096). |
| 2182 | `    else if (p->count != CS_CLOSED && !w->group_open)` | Tests whether the plan wants counters for this trial (state `open` or `read`) while the group is not open. |
| 2183 | `        count_open(w);` | Then the group is opened (`count_open`, line 2112). It stays open over the next trials until a trial wants it closed. |
| 2184 | `    r->state = p->count != CS_CLOSED && w->open_fail ? CS_FAIL : p->count;` | The record keeps the counter state of the trial. It is `fail` when the trial wants counters and an event did not open. In every other case it is the state of the plan. |
| 2185 | `    r->close_fail = w->close_fail;` | Moves the number of failed `close` calls of line 2181 into the record. |
| 2186 | `    w->close_fail = 0;` | Sets the count of failed `close` calls of the worker to 0. |
| 2187 | `    w->read_fail = 0;` | Sets the count of failed group readings of the worker to 0. |
| 2189 | `    /* The last old read of the trial must leave the sum of its range in the` | Comment: the last old read kernel of the trial must leave the sum of its range in the sink. The sentence ends in line 2190. |
| 2190 | `     * sink. The sink starts with another value, so an old value cannot pass. */` | Comment: the sink starts with another value. So a value from an earlier call cannot pass the check. |
| 2191 | `    for (int i = 0; i < r->nw; i++)` | Loop over the windows of the trial. |
| 2192 | `        if (kernels[r->win[i].k].type == T_OLDREAD)` | Tests whether the kernel of the window has the type `T_OLDREAD`. |
| 2193 | `            old = i;` | `old` keeps the index of the last such window. |
| 2194 | `    if (old >= 0) {` | Tests whether the trial has such a window. |
| 2195 | `        expect = w->v * (r->win[old].size / 8);` | The expected sum. Every 8-byte word of the `--bytes` range of the buffer holds `w->v` (line 2466), and the range of a window lies inside it (line 2624). So the kernel must return `w->v` times the number of words of its range. Only the low 64 bits of the product are kept, as in the sum of the kernel. |
| 2196 | `        *sink = expect + 1;` | The sink starts with the expected sum plus 1. |
| 2197 | `    }` | Ends the `if` of line 2194. |
| 2199 | `    page_read(w, r, 0);` | Before the timed sequence: reads the page state (`page_read`, line 2144). |
| 2200 | `    switches(w, r, 0);` | Before the timed sequence: reads the context switches and the minor page faults (`switches`, line 2153). |
| 2201 | `    r->cpu[0] = tcpu(w);` | Before the timed sequence: reads the thread CPU time (`tcpu`, line 1945). This is the last step before the timed sequence. |
| 2202 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2203 | `    /* --hot-copy selects the other function. The statement after this block` | Comment: the option `--hot-copy` selects the other function. The sentence about the next statement starts here. |
| 2204 | `     * is the else branch. */` | Comment: the statement after this block (line 2209) is the `else` branch. |
| 2205 | `    if (plan.hot_copy)` | Tests for the option `--hot-copy`. |
| 2206 | `        timed_sequence_hot(w, r, p->count == CS_READ, sink);` | With `--hot-copy`: `timed_sequence_hot` (line 2056) runs the timed sequence. The third argument is 1 for the counter state `read`. Then the function also reads the counter group at the boundaries of the target windows. |
| 2207 | `    else` | Starts the `else` branch. Its statement is line 2209. |
| 2208 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2209 | `    timed_sequence(w, r, p->count == CS_READ, sink);` | `timed_sequence` (line 1995) runs the timed sequence. The clock reads that time the windows are inside that function. The third argument is 1 for the counter state `read`. Then the function also reads the counter group at the boundaries of the target windows. This statement is the `else` branch of line 2205: it runs without `--hot-copy`. |
| 2210 | `    r->cpu[1] = tcpu(w);` | After the timed sequence: reads the thread CPU time again. |
| 2211 | `    switches(w, r, 1);` | After the timed sequence: reads the context switches and the minor page faults again. |
| 2212 | `    page_read(w, r, 1);` | After the timed sequence: reads the page state again. So the three readings come in the reverse order of lines 2199 to 2201. |
| 2213 | `    r->sink_ok = old < 0 ? -1 : *sink == expect;` | `sink_ok`: -1 when the trial ran no old read kernel. For a trial that ran one: 1 when the sink holds the expected sum, 0 when it does not. |
| 2214 | `    r->read_fail = w->read_fail;` | Moves the number of failed group readings of the timed sequence into the record. |
| 2215 | `}` | Ends the function `run_trial`. |

### Functions `trial_windows`, `window_bins` and `set_windows` (trial mode) (lines 2217 to 2257)

| Line | Source | Explanation |
|---:|---|---|
| 2217 | `static int trial_windows(const struct trial *p)` | Starts the function `trial_windows`. It returns the number of windows of one trial. |
| 2218 | `{` | Opens the body of `trial_windows`. The whole-chip test did not call this function [Ref4]. |
| 2219 | `    return (p->prev.k >= 0) + 4 * (p->pfx.k >= 0) + (p->pred.k >= 0) + p->nwin;` | Adds the windows of the phases that the trial has: 1 for the previous activity, 4 for the prefix, 1 for the predecessor and `nwin` for the target. The plan may leave out each of the first three. Then the field `k` of that part is -1, and the phase adds 0. |
| 2220 | `}` | Ends the function `trial_windows`. |
| 2222 | `/* Bins that one target window can close: one per 10 ms that ends inside the` | Comment: the number of bins that one target window can close: one per 10 ms that ends inside the window. The list goes on in line 2223. |
| 2223 | ` * window, one at the end of the window, and one spare. */` | Comment: plus one bin at the end of the window, and one extra bin. |
| 2224 | `static int window_bins(const struct trial *p)` | Starts the function `window_bins`. It returns the number of bins for which one target window of the trial gets storage. |
| 2225 | `{` | Opens the body of `window_bins`. The whole-chip test did not call this function [Ref4]. |
| 2226 | `    return p->bins ? (int)(p->win_ms / 10) + 2 : 0;` | For a trial with bins: the window duration `win_ms` divided by 10 and rounded down, plus 2. The 10 is the requested length of a bin in ms (`BIN_NS`, line 1813). For a trial without bins: 0. |
| 2227 | `}` | Ends the function `window_bins`. |
| 2229 | `/* Fills the plan part of the windows of one trial. bin: storage for` | Comment: the function fills the plan part of the windows of one trial. The sentence about `bin` starts here. |
| 2230 | ` * nwin * window_bins(p) bins. */` | Comment: `bin` is the storage for `nwin` times `window_bins(p)` bins. |
| 2231 | `static void set_windows(const struct trial *p, struct win *win, struct bin *bin)` | Starts the function `set_windows`. It fills the plan fields of all window records of the trial `p`, in the order in which the windows run. `win` points to the first window record of the trial. |
| 2232 | `{` | Opens the body of `set_windows`. The whole-chip test did not call this function [Ref4]. |
| 2233 | `    const struct {` | Starts the definition of the table `ph`, with one entry per phase. |
| 2234 | `        const struct part *part;` | `part`: the part of the trial that the phase runs. |
| 2235 | `        int phase, n;` | `phase`: the code of the phase. `n`: the number of windows of the phase. |
| 2236 | `    } ph[4] = { { &p->prev, PH_PREV, 1 }, { &p->pfx, PH_PREFIX, 4 }, { &p->pred, PH_PRED, 1 }, { &p->tgt, PH_TARGET, p->nwin } };` | The four entries, in the order of the run: previous activity (1 window), prefix (4 windows), predecessor (1 window) and target (`nwin` windows). |
| 2237 | `    struct win *x = win;` | `x`: the window record that is filled next. |
| 2238 | `    for (int i = 0; i < 4; i++) {` | Loop over the four phases. |
| 2239 | `        const struct part *part = ph[i].part;` | `part`: the part of this phase. |
| 2240 | `        if (part->k < 0)` | Tests whether the plan leaves this phase out. |
| 2241 | `            continue;` | Such a phase gets no window. |
| 2242 | `        for (int j = 0; j < ph[i].n; j++, x++) {` | Loop over the windows of the phase. After each window `x` moves on to the next record. |
| 2243 | `            memset(x, 0, sizeof *x);` | Sets every field of the record to 0. |
| 2244 | `            x->k = part->k;` | The kernel of the window. |
| 2245 | `            x->phase = ph[i].phase;` | The phase of the window. |
| 2246 | `            x->widx = j;` | The number of the window inside its phase, counted from 0. |
| 2247 | `            x->size = part->size;` | The size of the range of the window, in bytes. |
| 2248 | `            x->passes = CHECK_BYTES / part->size ? CHECK_BYTES / part->size : 1;` | `passes`: the number of kernel calls between two clock reads. It is 8 MiB (`CHECK_BYTES`, line 130) divided by the range size, rounded down, and at least 1. |
| 2249 | `            x->dur_ns = (ph[i].phase == PH_TARGET ? p->win_ms : part->ms / ph[i].n) * 1000000L;` | `dur_ns`: the requested duration of the window in ns. A target window gets `win_ms`. Every other window gets the duration of its phase divided by the number of windows of the phase. So each of the 4 prefix windows gets a quarter of the prefix duration. |
| 2250 | `            if (ph[i].phase == PH_TARGET && p->bins) {` | Tests whether this is a target window of a trial with bins. |
| 2251 | `                x->bin_cap = window_bins(p);` | `bin_cap`: the number of bins that the window can close (`window_bins`, line 2224). |
| 2252 | `                x->bin = bin + (size_t)j * (size_t)x->bin_cap;` | The window gets its own part of the bin storage: target window `j` starts at bin `j * bin_cap`. |
| 2253 | `            }` | Ends the `if` of line 2250. |
| 2254 | `        }` | Ends the loop over the windows of the phase (line 2242). |
| 2255 | `    }` | Ends the loop over the phases (line 2238). |
| 2256 | `}` | Ends the function `set_windows`. |

### Function `alloc_records` (trial mode): one memory block for all trial records (lines 2258 to 2296)

| Line | Source | Explanation |
|---:|---|---|
| 2258 | `/* The record storage of all trials: one block, sized from the plan, written` | Comment: the record storage of all trials is one block. Its size comes from the plan. The sentence goes on in line 2259. |
| 2259 | ` * once here so that no page of it is first touched during a trial.` | Comment: the block is written once here. So no page of it gets its first touch during a trial. |
| 2260 | ` * plan_trial() has filled recsz and has checked its bound. */` | Comment: `plan_trial` has filled `recsz` and has checked its upper limit (line 2719). |
| 2261 | `static void alloc_records(struct tw *w)` | Starts the function `alloc_records`. It allocates the record block, touches every page of it, and divides it into the arrays of the records. |
| 2262 | `{` | Opens the body of `alloc_records`. The whole-chip test did not call this function [Ref4]. |
| 2263 | `    char *mem = malloc(recsz.bytes);` | Allocates one block of `recsz.bytes` bytes with `malloc`. |
| 2264 | `    if (!mem) {` | Tests whether the allocation failed. |
| 2265 | `        fprintf(stderr, "no memory for %zu bytes of records\n", recsz.bytes);` | Prints `no memory for`, the number of bytes and `bytes of records` to stderr. |
| 2266 | `        exit(2);` | Ends the process with exit status 2. |
| 2267 | `    }` | Ends the `if` of line 2264. |
| 2268 | `    memset(mem, 0, recsz.bytes);` | Fills the block with zero bytes. |
| 2269 | `    /* gcc joins malloc and memset into calloc, and calloc does not write a` | Comment: the compiler gcc joins `malloc` and `memset` into one call of `calloc`. `calloc` does not write a new block. The sentence ends in line 2270. |
| 2270 | `     * fresh block. One volatile store per page is the first touch. */` | Comment: one store per page through a `volatile` pointer is the first touch. |
| 2271 | `    for (size_t at = 0; at < recsz.bytes; at += (size_t)page_bytes)` | Loop over the block in steps of one page (`page_bytes`). |
| 2272 | `        ((volatile char *)mem)[at] = 0;` | Stores one zero byte in each page. The pointer is `volatile`, so the compiler must keep the store. |
| 2273 | `    ((volatile char *)mem)[recsz.bytes - 1] = 0;` | Stores one zero byte in the last byte of the block. |
| 2274 | `    rec = (struct trec *)mem;` | `rec`: the trial records stand at the start of the block, one per trial. |
| 2275 | `    struct win *win = (struct win *)(rec + plan.n);` | `win`: the window records follow the trial records. |
| 2276 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2277 | `    /* --rec-pad: win[] starts this many bytes later. With 0 nothing moves. */` | Comment: with `--rec-pad` the window records start that many bytes later. With 0 nothing moves. |
| 2278 | `    win = (struct win *)((char *)win + plan.rec_pad);` | Moves the start of the window records by `plan.rec_pad` bytes. The default is 0 bytes. |
| 2279 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2280 | `    struct counts *cnt = (struct counts *)(win + recsz.windows);` | `cnt`: the counter readings follow the window records. |
| 2281 | `    struct bin *bin = (struct bin *)(cnt + recsz.counts);` | `bin`: the bins follow the counter readings. |
| 2282 | `    if (plan.trace)` | Tests for the option `--trace`. |
| 2283 | `        w->log = (struct tev *)(bin + recsz.bins);` | With `--trace` the event log follows the bins. |
| 2284 | `    for (int i = 0; i < plan.n; i++) {` | Loop over the trials of the plan. |
| 2285 | `        const struct trial *p = &plan.tr[i];` | `p`: the trial of the plan. |
| 2286 | `        rec[i].win = win;` | The trial gets the next free window records. |
| 2287 | `        rec[i].nw = trial_windows(p);` | `nw`: the number of windows of the trial (`trial_windows`, line 2217). |
| 2288 | `        rec[i].cnt = p->count == CS_READ ? cnt : NULL;` | Only a trial with the counter state `read` gets counter readings. Every other trial gets NULL. |
| 2289 | `        set_windows(p, win, bin);` | Fills the plan fields of the windows of the trial (`set_windows`, line 2231). |
| 2290 | `        win += rec[i].nw;` | Moves `win` past the windows of this trial. |
| 2291 | `        bin += (size_t)p->nwin * (size_t)window_bins(p);` | Moves `bin` past the bins of this trial: `nwin` times `window_bins(p)`. |
| 2292 | `        if (p->count == CS_READ)` | Tests whether the trial has the counter state `read`. |
| 2293 | `            cnt += p->nwin + 1;` | Moves `cnt` past the `nwin + 1` readings of this trial. |
| 2294 | `    }` | Ends the loop over the trials (line 2284). |
| 2295 | `}` | Ends the function `alloc_records`. |

### Functions `print_s` and `print_p8` (trial mode): the S row and the P row (lines 2297 to 2315)

| Line | Source | Explanation |
|---:|---|---|
| 2297 | `static void print_s(int i)` | Starts the function `print_s`. It prints the S row of trial `i`: the plan line of the trial and two fields of the trial before it. |
| 2298 | `{` | Opens the body of `print_s`. The whole-chip test did not call this function [Ref4]. |
| 2299 | `    const struct trial *p = &plan.tr[i];` | `p`: trial `i` of the plan. |
| 2300 | `    printf("S");` | Prints the letter `S`. |
| 2301 | `    for (int f = 0; f < PLAN_FIELDS; f++)` | Loop over the 11 fields of the plan line. |
| 2302 | `        printf(",%s", p->f[f]);` | Prints a comma and one field, as the text of the plan file. |
| 2303 | `    printf(",%s,%s\n", i ? plan.tr[i - 1].f[1] : "none", i ? plan.tr[i - 1].f[6] : "none");` | Prints two more fields and the line break: the fields `cond` and `tgt` of the trial before this one. For trial 0 it prints the word `none` two times. |
| 2304 | `}` | Ends the function `print_s`. |
| 2306 | `static void print_p8(int i, const char *when, const struct page *pg, const long long vm[4])` | Starts the function `print_p8`. It prints the P row of the trial mode: the page state of the buffer before or after the timed sequence of trial `i`. `when` is the word `pre` or `post`. |
| 2307 | `{` | Opens the body of `print_p8`. The whole-chip test did not call this function [Ref4]. The P rows of the csv files of that test have other columns: round, position, thread and buffer letter come first [Ref5]. Those rows come from `print_p` (line 1570). |
| 2308 | `    printf("P,%d,%s", i, when);` | Prints the letter `P`, the trial number and the word `pre` or `post`. |
| 2309 | `    print_na(pg->kb_total);` | Prints the size of the mapping of the buffer in kB, or `NA` (`print_na`, line 1562). |
| 2310 | `    print_na(pg->kb_huge);` | Prints the part of the buffer that lies on 2 MiB pages in kB, or `NA`. |
| 2311 | `    for (int k = 0; k < 4; k++)` | Loop over the four counters of `/proc/vmstat`. |
| 2312 | `        print_na(vm[k]);` | Prints one counter, or `NA` for a counter that was not found. |
| 2313 | `    printf("\n");` | Ends the row with a line break. |
| 2314 | `}` | Ends the function `print_p8`. |

### Function `emit_trial` (trial mode): the P, W, B and C rows of one trial (lines 2316 to 2358)

| Line | Source | Explanation |
|---:|---|---|
| 2316 | `/* All rows of one trial after its S row. */` | Comment: the function prints all rows of one trial that come after its S row. |
| 2317 | `static void emit_trial(struct tw *w, int i)` | Starts the function `emit_trial`. It prints the result rows of trial `i` from the record of the trial. It prints bytes and times. It computes no rate. |
| 2318 | `{` | Opens the body of `emit_trial`. The whole-chip test did not call this function [Ref4]. |
| 2319 | `    const struct trial *p = &plan.tr[i];` | `p`: trial `i` of the plan. |
| 2320 | `    const struct trec *r = &rec[i];` | `r`: the record of trial `i`. |
| 2321 | `    int g = r->nw - p->nwin; /* index of target window 0 */` | `g`: the index of target window 0 in the window list of the trial: the number of all windows minus the number of target windows. The comment says the same. |
| 2322 | `    int64_t max_gap = -1;` | `max_gap`: the longest time between two windows of the trial, in ns. It starts at -1, which prints as `NA`. |
| 2324 | `    tev_add(w, EV_OUTPUT, 0, 0);` | Logs the start of the output as an event. Without `--trace` this call does nothing. |
| 2325 | `    print_p8(i, "pre", &r->pg[0], r->vm[0]);` | P row `pre`: the page state before the timed sequence (`print_p8`, line 2306). |
| 2326 | `    for (int k = 0; k < r->nw; k++) {` | Loop over all windows of the trial. |
| 2327 | `        const struct win *x = &r->win[k];` | `x`: the record of window `k`. |
| 2328 | `        printf("W,%d,%s,%d,%s,%lu,%lu,%lld,%lld\n", i, phase_name[x->phase], x->widx, kernels[x->k].name,` | W row, one per window. Its columns: the letter `W`, the trial number, the name of the phase, the number of the window inside the phase, the kernel name, `pass_bytes`, `bytes`, `t_start_ns` and `t_end_ns`. This line holds the format and the first four values. |
| 2329 | `               (unsigned long)x->size, (unsigned long)x->bytes, (long long)(x->t_start - t_base_ns),` | Continues the call of line 2328. `pass_bytes` is the range size of one kernel call. `bytes` is the byte count of the window: the range size times the number of kernel calls. `t_start_ns` is the start clock read of the window, in ns after the process start (`t_base_ns`). |
| 2330 | `               (long long)(x->t_end - t_base_ns));` | Continues the call of line 2328: `t_end_ns`, the last clock read of the window, in ns after the process start. The row holds no rate. The file `DECISIONS-bwx8.md` defines the rate of a window as `bytes` divided by `t_end_ns - t_start_ns`. |
| 2331 | `        if (k && x->t_start - r->win[k - 1].t_end > max_gap)` | Tests, for every window but the first, whether the time from the end clock read of the window before to the start clock read of this window is the longest so far. |
| 2332 | `            max_gap = x->t_start - r->win[k - 1].t_end;` | Keeps the longest such time in `max_gap`. |
| 2333 | `    }` | Ends the loop over the windows (line 2326). |
| 2334 | `    for (int k = g; k < r->nw; k++)` | Loop over the target windows of the trial. |
| 2335 | `        for (int b = 0; b < r->win[k].nbin; b++)` | Loop over the bins that the window closed. |
| 2336 | `            printf("B,%d,%d,%d,%lld,%lu\n", i, r->win[k].widx, b, (long long)(r->win[k].bin[b].t_end - t_base_ns),` | B row, one per bin. Its columns: the letter `B`, the trial number, the number of the target window, the bin number, `t_end_ns` and the byte count of the bin. `t_end_ns` is the clock read that closed the bin, in ns after the process start. This line holds the format and the first four values. |
| 2337 | `                   (unsigned long)r->win[k].bin[b].bytes);` | Continues the call of line 2336: the bytes that the window counted from its start to that clock read. |
| 2338 | `    for (int k = 0; r->cnt && k < p->nwin; k++) {` | Loop over the target windows. It runs only for a trial with counter readings (counter state `read`). |
| 2339 | `        const struct counts *c0 = &r->cnt[k], *c1 = &r->cnt[k + 1];` | `c0`, `c1`: the reading before the start clock read of the window, and the reading after its end clock read. |
| 2340 | `        int group = w->t.group_fd >= 0 && !r->read_fail;` | `group`: 1 when a counter group is open and no group reading of the trial failed. |
| 2341 | `        printf("C,%d,%d", i, k);` | C row, one per target window. It starts with the letter `C`, the trial number and the window number. Every value after them is the difference of the two readings. The C rows of the interval mode have other columns: round, position, kernel name, thread index and CPU come first. `main` prints those rows (lines 3086 to 3103). |
| 2342 | `        if (group)` | Tests whether the group readings can be used. |
| 2343 | `            printf(",%llu,%llu", (unsigned long long)(c1->enabled - c0->enabled),` | Columns 4 and 5, `enabled_ns` and `running_ns`: the growth of the enabled time and of the running time between the two readings, in ns. This line holds the enabled time. |
| 2344 | `                   (unsigned long long)(c1->running - c0->running));` | Continues the call of line 2343: the growth of the running time. |
| 2345 | `        else` | The case of no open group, or of a failed group reading. |
| 2346 | `            printf(",NA,NA");` | Columns 4 and 5 are then `NA`. |
| 2347 | `        printf(",%llu", (unsigned long long)(c1->cpu_ns - c0->cpu_ns));` | Column 6, `cputime_ns`: the growth of the thread CPU time between the two readings, in ns. |
| 2348 | `        for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `cfg`. |
| 2349 | `            int at = w->t.ev_pos[e];` | `at`: the position of the event in a group reading, or -1 for an event that did not open. |
| 2350 | `            if (!group \|\| at < 0)` | Tests whether the value cannot be given: the group readings cannot be used, or the event did not open. |
| 2351 | `                printf(",NA");` | The field is then `NA`. |
| 2352 | `            else` | The case of a value that can be given. |
| 2353 | `                printf(",%llu", (unsigned long long)(c1->val[at] - c0->val[at]));` | One column per event: the count at the second reading minus the count at the first reading. |
| 2354 | `        }` | Ends the loop over the events (line 2348). |
| 2355 | `        printf("\n");` | Ends the row with a line break. |
| 2356 | `    }` | Ends the loop over the target windows (line 2338). |
| 2357 | `    print_p8(i, "post", &r->pg[1], r->vm[1]);` | P row `post`: the page state after the timed sequence. |

### Function `emit_trial` (trial mode): the X rows, the E row and the trace rows (lines 2359 to 2407)

| Line | Source | Explanation |
|---:|---|---|
| 2359 | `    if (r->pg[0].kb_huge < 0 \|\| r->pg[1].kb_huge < 0)` | Tests whether a reading of the page state found no exact entry for the buffer in `/proc/self/smaps`, before or after the timed sequence. |
| 2360 | `        printf("X,%d,coverage_na,the buffer has no exact entry in /proc/self/smaps\n", i);` | X row with the code `coverage_na`. An X row reports a problem: the letter `X`, the trial number, a code and a text. |
| 2361 | `    if (r->close_fail)` | Tests whether a `close` call failed when the counter group was closed at the start of this trial (line 2181). |
| 2362 | `        printf("X,%d,count_close,%d counter descriptors did not close\n", i, r->close_fail);` | X row with the code `count_close` and the number of counter file descriptors that did not close. |
| 2363 | `    if (r->state == CS_FAIL)` | Tests whether the trial wanted counters and an event did not open. |
| 2364 | `        printf("X,%d,count_open,%d of %d events did not open; first: %s\n", i, w->open_fail, cfg.nev, w->open_err);` | X row with the code `count_open`: how many of the events did not open, and the error text of the first one. |
| 2365 | `    if (r->read_fail)` | Tests whether a group reading failed during the timed sequence. |
| 2366 | `        printf("X,%d,count_read,%d reads of the counter group failed\n", i, r->read_fail);` | X row with the code `count_read` and the number of failed group readings. |
| 2367 | `    if (r->cnt && w->t.group_fd >= 0 && !r->read_fail) {` | Tests whether the trial has counter readings that can be used: readings exist, a group is open, and no reading failed. |
| 2368 | `        int m = first_multiplexed(r->cnt, p->nwin);` | `m`: the first target window in which the counters did not count all the time (`first_multiplexed`, line 2165), or -1. |
| 2369 | `        if (m >= 0)` | Tests whether there is such a window. |
| 2370 | `            printf("X,%d,count_multiplexed,target window %d: running_ns %llu below enabled_ns %llu\n", i, m,` | X row with the code `count_multiplexed`: the number of the target window, and its running time and its enabled time in ns. The running time is the smaller one. |
| 2371 | `                   (unsigned long long)(r->cnt[m + 1].running - r->cnt[m].running),` | Continues the call of line 2370: the growth of the running time in that window. |
| 2372 | `                   (unsigned long long)(r->cnt[m + 1].enabled - r->cnt[m].enabled));` | Continues the call of line 2370: the growth of the enabled time in that window. |
| 2373 | `    }` | Ends the `if` of line 2367. |
| 2374 | `    if (r->sink_ok == 0)` | Tests whether the sum check of the old read kernel failed (line 2213). |
| 2375 | `        printf("X,%d,sink,the last old read did not leave the sum of its range in the sink\n", i);` | X row with the code `sink`: the last old read kernel did not leave the sum of its range in the sink. |
| 2377 | `    printf("E,%d,%lld,%llu", i, (long long)(r->win[r->nw - 1].t_end - r->win[0].t_start),` | E row, one per trial: the summary of the trial. Columns 1 to 4: the letter `E`, the trial number, `wall_ns` and `cpu_ns`. `wall_ns` is the time from the start clock read of the first window to the end clock read of the last window, in ns. |
| 2378 | `           (unsigned long long)(r->cpu[1] - r->cpu[0]));` | Continues the call of line 2377: `cpu_ns`, the growth of the thread CPU time between the two `tcpu` calls of `run_trial` (line 2201, line 2210), in ns. |
| 2379 | `    if (r->nvcsw[0] < 0 \|\| r->nvcsw[1] < 0)` | Tests whether a reading of the context switches failed. |
| 2380 | `        printf(",NA,NA");` | Columns 5 and 6 are then `NA`. |
| 2381 | `    else` | The case of two good readings. |
| 2382 | `        printf(",%ld,%ld", r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]);` | Columns 5 and 6, `nvcsw` and `nivcsw`: the numbers of voluntary and of involuntary context switches of the worker between the two `switches` calls of `run_trial` (line 2200, line 2211). |
| 2383 | `    print_na(g ? r->win[g].t_start - r->win[g - 1].t_end : -1);` | Column 7, `gap_ns`: the time from the end clock read of the window before target window 0 to the start clock read of target window 0. A trial without a window before its first target window prints `NA`. |
| 2384 | `    print_na(max_gap);` | Column 8, `max_boundary_gap_ns`: `max_gap`, the longest time between two windows of the trial (lines 2331 to 2332). A trial with one window prints `NA`. |
| 2385 | `    if (r->sink_ok < 0)` | Tests whether the trial ran no old read kernel. |
| 2386 | `        printf(",NA");` | Column 9, `sink_ok`, is then `NA`. |
| 2387 | `    else` | The case of a trial that ran an old read kernel. |
| 2388 | `        printf(",%d", r->sink_ok);` | Column 9 is then 1 for a right sum and 0 for a wrong sum. |
| 2389 | `    printf(",%s\n", count_name[r->state]);` | Column 10, `count_state`: the counter state of the trial as a word: `closed`, `open`, `read` or `fail`. The line break ends the row. |
| 2391 | `    for (long n = 0; n < w->nlog; n++) {` | Loop over the events of the trace. Without `--trace` the log holds no event. |
| 2392 | `        const struct tev *e = &w->log[n];` | `e`: one event of the log. |
| 2393 | `        if (e->ev == EV_KERNEL_FIRST)` | Tests whether the event is the first kernel call of a window. |
| 2394 | `            printf("TR,%d,%ld,%s:%s:%d,%lld\n", i, n, event_name[e->ev], phase_name[e->phase], e->widx,` | TR row of such an event: the letters `TR`, the trial number, the event number, then the event name with the phase name and the window number (joined by colons), then the time of the event. |
| 2395 | `                   (long long)(e->t - t_base_ns));` | Continues the call of line 2394: the time of the event, in ns after the process start. |
| 2396 | `        else` | The case of every other event. |
| 2397 | `            printf("TR,%d,%ld,%s,%lld\n", i, n, event_name[e->ev], (long long)(e->t - t_base_ns));` | TR row of another event: the letters `TR`, the trial number, the event number, the event name and the time in ns after the process start. For an event that is not a clock read this is the time of the clock read before it. |
| 2398 | `    }` | Ends the loop over the events (line 2391). |
| 2399 | `    if (w->ndrop)` | Tests whether events did not fit into the log. |
| 2400 | `        printf("# trace_dropped,%d,%ld\n", i, w->ndrop);` | Prints the line `# trace_dropped` with the trial number and the number of events that the log did not keep. The log keeps 1048576 events per trial (`TRACE_CAP`, line 1814). |
| 2401 | `    /* --trace: minor page faults of the worker between the two rusage reads.` | Comment: with `--trace` the next statement prints the minor page faults of the worker between the two `getrusage` readings. |
| 2402 | `     * Above 0: a page was first touched inside the timed sequence. */` | Comment: a value above 0 means that a page got its first touch inside the timed sequence. The two readings also enclose the two `tcpu` calls of `run_trial` (line 2201, line 2210). |
| 2403 | `    if (w->log)` | Tests whether a log exists (`--trace`). |
| 2404 | `        printf("# minflt,%d,%ld\n", i, r->minflt[0] < 0 \|\| r->minflt[1] < 0 ? -1 : r->minflt[1] - r->minflt[0]);` | Prints the line `# minflt` with the trial number and the number of minor page faults between the two `switches` calls. It prints -1 when a reading failed. |
| 2405 | `    fflush(stdout);` | `fflush` writes the buffered rows to the output before the next trial starts. |
| 2406 | `}` | Ends the function `emit_trial`. |

### The evict step of `--evict-mb` (trial mode): variables and the function `evict_step` (lines 2408 to 2448)

| Line | Source | Explanation |
|---:|---|---|
| 2408 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. This block ends in line 2448. |
| 2409 | `/*` | Comment: starts the comment about the evict step. The comment ends in line 2423. |
| 2410 | ` * --evict-mb N. evict_step() maps N MiB of anonymous private memory (plain` | Comment: the option `--evict-mb N`. The function `evict_step` maps N MiB of anonymous private memory. The sentence goes on in line 2411. |
| 2411 | ` * mmap, no madvise), stores one 8-byte word to every 64 B line in ascending` | Comment: the function uses a plain `mmap` without `madvise`. It stores one 8-byte word to every 64 B line, from the lowest address up. The sentence goes on in line 2412. |
| 2412 | ` * order, in two passes, and unmaps the range. The stores go through a` | Comment: it does this in two passes and then unmaps the range. The sentence about the stores starts here. |
| 2413 | ` * volatile pointer, so gcc keeps every one of them and does not call memset.` | Comment: the stores go through a `volatile` pointer. So gcc keeps every store and does not call `memset`. |
| 2414 | ` * Purpose: the lines of the benchmark buffer leave the caches. The first` | Comment: the purpose: the 64 B lines of the benchmark buffer leave the caches. The reason starts here. |
| 2415 | ` * touch wrote them, so they were dirty. The next read brings them back from` | Comment: the first touch wrote these lines, so they were dirty. A dirty line holds data that the cache has not yet written back to memory. The sentence about the next read starts here. |
| 2416 | ` * memory, clean.` | Comment: the next read brings the lines back from memory, clean. |
| 2417 | ` * trial_worker() calls it once, after the first touch of the buffer and of` | Comment: `trial_worker` calls the function once, after the first touch of the buffer. The sentence goes on in line 2418. |
| 2418 | ` * the record block and before the first trial. No timed sequence holds it.` | Comment: the call also comes after the first touch of the record block and before the first trial. No timed sequence holds the evict step. |
| 2419 | ` * evict_t holds one clock read before the mmap and one after the munmap.` | Comment: `evict_t` holds one clock read before the `mmap` and one after the `munmap`. |
| 2420 | ` * Returns 0, or -1 with the text of the error in evict_err.` | Comment: the function returns 0. On an error it returns -1 and leaves the text of the error in `evict_err`. |
| 2421 | ` * These definitions stand after timed_sequence_hot() and after every other` | Comment: these definitions stand after `timed_sequence_hot` and after every other variable of the trial mode. The sentence ends in line 2422. |
| 2422 | ` * variable of the trial mode, so nothing before them moves.` | Comment: so nothing that stands before them moves to another address. |
| 2423 | ` */` | Comment: the end of the comment. |
| 2424 | `static long evict_mb;      /* --evict-mb: 0 = no evict step */` | `evict_mb`: the value of `--evict-mb` in MiB. The value 0 means no evict step. |
| 2425 | `static int64_t evict_t[2]; /* CLOCK_MONOTONIC, ns */` | `evict_t`: the two clock reads around the evict step, in ns of the Linux clock `CLOCK_MONOTONIC`. |
| 2426 | `static char evict_err[160];` | `evict_err`: the text of an error of the evict step. |
| 2428 | `__attribute__((noinline)) static int evict_step(void)` | Starts the function `evict_step`. It writes `evict_mb` MiB of other memory two times. The aim: the 64 B lines of the benchmark buffer leave the caches. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 2429 | `{` | Opens the body of `evict_step`. The whole-chip test did not call this function [Ref4]. |
| 2430 | `    size_t len = (size_t)evict_mb << 20;` | `len`: the size of the memory in bytes: `evict_mb` times 1048576. |
| 2431 | `    evict_t[0] = now_ns();` | First clock read (`now_ns`, line 327), before the `mmap`. |
| 2432 | `    volatile uint64_t *m = mmap(NULL, len, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `len` bytes of new private anonymous memory. `m` points to `volatile` data. So the compiler must keep every store of line 2439. |
| 2433 | `    if (m == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 2434 | `        snprintf(evict_err, sizeof evict_err, "mmap of %ld MiB failed: %s", evict_mb, strerror(errno));` | Stores the error text in `evict_err`: the words `mmap of`, the size in MiB, the word `failed` and the reason that Linux gave. |
| 2435 | `        return -1;` | Returns -1. |
| 2436 | `    }` | Ends the `if` of line 2433. |
| 2437 | `    for (int pass = 0; pass < 2; pass++)` | Two passes over the whole range. |
| 2438 | `        for (size_t i = 0; i < len / 8; i += 8)` | Loop over the range. `i` counts 8-byte words, so `i += 8` is a step of 64 B: one store per 64 B line, from the lowest address up. |
| 2439 | `            m[i] = (uint64_t)i + (uint64_t)pass + 1;` | Stores one 8-byte word at the start of the 64 B line. The value is the word index plus the pass number plus 1. |
| 2440 | `    if (munmap((void *)m, len) != 0) {` | Unmaps the memory and tests whether `munmap` failed. |
| 2441 | `        snprintf(evict_err, sizeof evict_err, "munmap of %ld MiB failed: %s", evict_mb, strerror(errno));` | Stores the error text in `evict_err`: the words `munmap of`, the size in MiB, the word `failed` and the reason that Linux gave. |
| 2442 | `        return -1;` | Returns -1. |
| 2443 | `    }` | Ends the `if` of line 2440. |
| 2444 | `    evict_t[1] = now_ns();` | Second clock read, after the `munmap`. |
| 2445 | `    return 0;` | Returns 0: the step is done. |
| 2446 | `}` | Ends the function `evict_step`. |
| 2448 | `/* bwx11- */` | Comment: marks the end of the block that `bwx11` added. The block starts in line 2408. |

### Function `trial_worker` (trial mode): pinning, buffer, first touch and records (lines 2449 to 2469)

| Line | Source | Explanation |
|---:|---|---|
| 2449 | `static void *trial_worker(void *arg)` | Starts the function `trial_worker`, the start function of the one worker thread of the trial mode. `trial_main` creates the thread in line 2880. |
| 2450 | `{` | Opens the body of `trial_worker`. The whole-chip test did not run this function [Ref4]. |
| 2451 | `    struct tw *w = arg;` | `w`: the state of the worker (line 1888). |
| 2452 | `    volatile uint64_t sink = 0;` | `sink`: the volatile variable on the stack of the worker that receives the sum of an old read kernel. It starts at 0. |
| 2453 | `    int madvise_ok;` | `madvise_ok`: will hold whether the request for the page policy succeeded (line 2465). |
| 2455 | `    pin_cpu(cfg.cpus[0]);` | CPU pinning. The worker pins itself to the one CPU of `--cpus` (`pin_cpu`, line 415). |
| 2456 | `    if (sched_getcpu() != cfg.cpus[0]) {` | Asks Linux on which CPU the thread runs now (`sched_getcpu`) and tests whether it is another CPU than the one of `--cpus`. |
| 2457 | `        fprintf(stderr, "the worker runs on CPU %d, not on CPU %d\n", sched_getcpu(), cfg.cpus[0]);` | Prints both CPU numbers to stderr. |
| 2458 | `        exit(2);` | Ends the process with exit status 2. |
| 2459 | `    }` | Ends the `if` of line 2456. |
| 2460 | `    w->v = ((uint64_t)getpid() + 1) * 0x9E3779B97F4A7C15ULL;` | `w->v`: the value that the first touch of line 2466 stores into the 8-byte words of the buffer: the process id (`getpid`) plus 1, times a fixed 64-bit constant. |
| 2461 | `    w->t.group_fd = -1;` | The worker has no counter group yet. |
| 2462 | `    w->t.a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 434) maps the one buffer of the worker: it starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. |
| 2463 | `    /* alloc_buf() does not return the result of its madvise. The same request` | Comment: `alloc_buf` does not return the result of its `madvise` call. The sentence about the next statement starts here. |
| 2464 | `     * again gives it. */` | Comment: the same request once more gives the result. |
| 2465 | `    madvise_ok = madvise(w->t.a, buf_len(), cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) == 0;` | Repeats the `madvise` request of `alloc_buf` for the buffer: a request for 2 MiB pages, or with `--no-thp` for no such pages. `madvise_ok` is 1 when the call succeeded. |
| 2466 | `    k_write(w->t.a, cfg.bytes / 8, w->v); /* first touch by the pinned worker */` | First touch. The pinned worker stores `w->v` into `cfg.bytes / 8` words of 8 bytes with `k_write` (line 531): every word of the `--bytes` range of the buffer. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 428). This line is not timed. |
| 2467 | `    alloc_records(w);` | `alloc_records` (line 2261) allocates the record block and touches every page of it. |
| 2468 | `    w->last_t = t_base_ns;` | The trace starts with the process start time as the time of the latest clock read. |

### Function `trial_worker` (trial mode): header lines and the rows before the first trial (lines 2470 to 2536)

| Line | Source | Explanation |
|---:|---|---|
| 2470 | `    printf("# bwx8 trial mode: GB = 1e9 bytes; times are whole ns since process start on CLOCK_MONOTONIC\n"` | Starts the `printf` call that prints the header lines of the trial mode. Each header line starts with `#`. This first line says: GB means 1e9 bytes, and times are whole ns after the process start on the clock `CLOCK_MONOTONIC`. The text names `bwx8`, the version of the runner that added the trial mode. |
| 2471 | `           "# S,trial,cond,rep,prev,pfx,pred,tgt,nwin,win_ms,count,bins,prev_cond,prev_tgt\n"` | Text of the header: the column names of the S rows. |
| 2472 | `           "# P,trial,when,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n"` | Text of the header: the column names of the P rows of the trial mode. |
| 2473 | `           "# W,trial,phase,widx,kernel,pass_bytes,bytes,t_start_ns,t_end_ns\n"` | Text of the header: the column names of the W rows. |
| 2474 | `           "# B,trial,widx,bin,t_end_ns,bytes_since_window_start\n"` | Text of the header: the column names of the B rows. |
| 2475 | `           "# C,trial,widx,enabled_ns,running_ns,cputime_ns");` | Text of the header: the first six column names of the C rows of the trial mode. The header line has no line break yet. |
| 2476 | `    for (int e = 0; e < cfg.nev; e++)` | Loop over the events of `cfg`. |
| 2477 | `        printf(",%s", cfg.ev_name[e]);` | Appends one event name per event to the header line of the C rows. |
| 2478 | `    printf("\n# E,trial,wall_ns,cpu_ns,nvcsw,nivcsw,gap_ns,max_boundary_gap_ns,sink_ok,count_state\n"` | Ends the header line of the C rows. Then comes the header line with the column names of the E rows. |
| 2479 | `           "# X,trial,code,text\n"` | Text of the header: the column names of the X rows. |
| 2480 | `           "# TR,trial,n,event,t_ns; t_ns of an event that is not a clock read is the time of the clock read before it\n");` | Text of the header: the column names of the TR rows. The text adds: the time of an event that is not a clock read is the time of the clock read before it. |
| 2481 | `    printf("M,mode,trial\nM,cpu,%d\nM,ctl_cpu,%d\nM,bytes,%lu\nM,thp,%s\nM,madvise_ok,%d\nM,check_bytes,%lu\nM,kernels,%s\n",` | M rows. Each M row holds one setting or one fact in the form `M,name,value`. This call prints `mode` (the word `trial`), `cpu` (the worker CPU), `ctl_cpu` (the CPU of the controlling thread), `bytes` (the buffer size), `thp` (the page policy), `madvise_ok`, `check_bytes` and `kernels`. |
| 2482 | `           cfg.cpus[0], plan.ctl_cpu, (unsigned long)cfg.bytes, cfg.use_thp ? "madvise" : "nohugepage", madvise_ok,` | Continues the call of line 2481: the values of `cpu`, `ctl_cpu`, `bytes`, `thp` (the word `madvise` or `nohugepage`) and `madvise_ok`. |
| 2483 | `           (unsigned long)CHECK_BYTES, STANDIN ? "STAND-IN" : "aarch64");` | Continues the call of line 2481: `check_bytes` is `CHECK_BYTES` (8388608 bytes, which is 8 MiB). `kernels` is `aarch64`, or `STAND-IN` for a build with stand-in kernels. |
| 2484 | `    printf("M,plan_fnv1a64,%016llx\nM,ntrials,%d\nM,rec_windows,%zu\nM,rec_bins,%zu\nM,rec_counts,%zu\nM,rec_trace,%zu\n"` | More M rows: `plan_fnv1a64` (the checksum of the plan file, 16 hexadecimal digits), `ntrials` (the number of trials), and the sizes of the record storage: `rec_windows`, `rec_bins`, `rec_counts` and `rec_trace`. |
| 2485 | `           "M,rec_bytes,%zu\nM,trace,%d\n",` | Continues the format of line 2484: `rec_bytes` (the size of the record block in bytes) and `trace` (0 or 1). |
| 2486 | `           (unsigned long long)plan.hash, plan.n, recsz.windows, recsz.bins, recsz.counts, recsz.trace, recsz.bytes,` | Continues the call of line 2484: the values of the first seven of these rows. |
| 2487 | `           plan.trace);` | Continues the call of line 2484: the value of `trace`. |
| 2488 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2489 | `    /* Addresses in hex without "0x", as in the K rows. rec_addr: the record` | Comment: the addresses are printed in hexadecimal without `0x`, as in the K rows. `rec_addr` is the address of the record block. The list goes on in line 2490. |
| 2490 | `     * block. win_addr: win[0] of trial 0. stack_addr: the sink of the worker. */` | Comment: `win_addr` is the address of the first window record of trial 0. `stack_addr` is the address of the sink of the worker. |
| 2491 | `    printf("M,rec_pad,%zu\nM,hot_copy,%d\nM,rec_addr,%lx\nM,win_addr,%lx\nM,win_size,%zu\nM,stack_addr,%lx\nM,buf_addr,%lx\n"` | More M rows: `rec_pad`, `hot_copy`, `rec_addr`, `win_addr`, `win_size` (the size of one window record in bytes), `stack_addr` and `buf_addr` (the address of the buffer). |
| 2492 | `           "M,tw_addr,%lx\n",` | Continues the format of line 2491: `tw_addr`, the address of the state of the worker. |
| 2493 | `           plan.rec_pad, plan.hot_copy, (unsigned long)(uintptr_t)rec, (unsigned long)(uintptr_t)rec[0].win,` | Continues the call of line 2491: the values of `rec_pad`, `hot_copy`, `rec_addr` and `win_addr`. |
| 2494 | `           sizeof(struct win), (unsigned long)(uintptr_t)&sink, (unsigned long)(uintptr_t)w->t.a,` | Continues the call of line 2491: the values of `win_size`, `stack_addr` and `buf_addr`. |
| 2495 | `           (unsigned long)(uintptr_t)w);` | Continues the call of line 2491: the value of `tw_addr`. |
| 2496 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2497 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2498 | `    /* The evict step. The buffer and the record block are first touched, and` | Comment: the evict step. At this point the buffer and the record block have got their first touch. The sentence goes on in line 2499. |
| 2499 | `     * no trial has started. With --evict-mb 0 no call is made. A failure` | Comment: no trial has started at this point. With `--evict-mb 0` the function is not called. The sentence about a failure starts here. |
| 2500 | `     * ends the process here: the X row is the last row. */` | Comment: a failure ends the process here, and the X row is the last row of the output. |
| 2501 | `    printf("M,evict_mb,%ld\n", evict_mb);` | M row `evict_mb`: the value of `--evict-mb`. |
| 2502 | `    if (evict_mb > 0 && evict_step() != 0) {` | With a value above 0: runs the evict step (`evict_step`, line 2428) and tests whether it failed. |
| 2503 | `        printf("X,-1,evict,%s\n", evict_err);` | X row with the trial number -1, the code `evict` and the error text. |
| 2504 | `        fflush(stdout);` | Writes the buffered rows to the output. |
| 2505 | `        exit(2);` | Ends the process with exit status 2. |
| 2506 | `    }` | Ends the `if` of line 2502. |
| 2507 | `    printf("M,evict_ns,%lld\n", (long long)(evict_t[1] - evict_t[0]));` | M row `evict_ns`: the time between the two clock reads of the evict step, in ns. It is 0 when no step ran. |
| 2508 | `    if (evict_mb > 0 && plan.trace)` | Tests whether a step ran and the trace is on. |
| 2509 | `        printf("TR,-1,0,evict_start,%lld\nTR,-1,1,evict_end,%lld\n", (long long)(evict_t[0] - t_base_ns),` | Two TR rows with the trial number -1: `evict_start` and `evict_end`, with the two clock reads of the step in ns after the process start. This line holds the time of `evict_start`. |
| 2510 | `               (long long)(evict_t[1] - t_base_ns));` | Continues the call of line 2509: the time of `evict_end`. |
| 2511 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2512 | `    if (cfg.pmu_type < 0)` | Tests whether no PMU type was given. |
| 2513 | `        printf("M,pmu_type,none\n");` | M row `pmu_type` with the word `none`. |
| 2514 | `    else` | The case of a given PMU type. |
| 2515 | `        printf("M,pmu_type,%ld\n", cfg.pmu_type);` | M row `pmu_type` with the number. |
| 2516 | `    printf("M,events,%s", cfg.nev ? "" : "none");` | Starts the M row `events`. Without events its value is the word `none`. |
| 2517 | `    for (int e = 0; e < cfg.nev; e++)` | Loop over the events of `cfg`. |
| 2518 | `        printf("%s%s=0x%llx", e ? ";" : "", cfg.ev_name[e], (unsigned long long)cfg.ev_code[e]);` | Prints one event as its name, the sign `=` and its code in hexadecimal with `0x`. A semicolon separates two events. |
| 2519 | `    printf("\n");` | Ends the row with a line break. |
| 2520 | `    for (int i = 0; i < plan.npair; i++) {` | Loop over the `key=value` pairs of the second line of the plan. |
| 2521 | `        char *eq = strchr(plan.pair[i], '=');` | `eq`: the place of the `=` sign in the pair. |
| 2522 | `        printf("M,plan.%.*s,%s\n", (int)(eq - plan.pair[i]), plan.pair[i], eq + 1);` | One M row per pair: the name is `plan.` plus the key, and the value is the text after the `=` sign. |
| 2523 | `    }` | Ends the loop of line 2520. |
| 2524 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the kernel table. |
| 2525 | `        int used = 0;` | `used`: becomes 1 when a trial of the plan uses kernel `k`. |
| 2526 | `        for (int i = 0; i < plan.n && !used; i++) {` | Loop over the trials. It stops at the first trial that uses the kernel. |
| 2527 | `            const struct trial *p = &plan.tr[i];` | `p`: one trial of the plan. |
| 2528 | `            used = p->prev.k == k \|\| p->pfx.k == k \|\| p->pred.k == k \|\| p->tgt.k == k;` | Tests whether one of the four parts of the trial names kernel `k`. |
| 2529 | `        }` | Ends the loop of line 2526. |
| 2530 | `        if (used)` | Tests whether the plan uses the kernel. |
| 2531 | `            printf("K,%s,%lx,%lu\n", kernels[k].name, (unsigned long)(uintptr_t)kernels[k].fn,` | K row, one per kernel that the plan uses: the letter `K`, the kernel name, the address of its function in hexadecimal, and this address modulo 64. |
| 2532 | `                   (unsigned long)((uintptr_t)kernels[k].fn % 64));` | Continues the call of line 2531: the address modulo 64. |
| 2533 | `    }` | Ends the loop over the kernel table (line 2524). |
| 2534 | `    if (!madvise_ok)` | Tests whether the `madvise` request of line 2465 failed. |
| 2535 | `        printf("X,-1,madvise,the page policy request failed\n");` | X row with the trial number -1 and the code `madvise`: the request for the page policy failed. |

### Function `trial_worker` (trial mode): the loop over the trials and the end (lines 2537 to 2553)

| Line | Source | Explanation |
|---:|---|---|
| 2537 | `    for (int i = 0; i < plan.n; i++) {` | Loop over the trials, in the order of the plan. |
| 2538 | `        w->nlog = w->ndrop = 0;` | Empties the trace: no event in the log, and a count of 0 for the events that did not fit. |
| 2539 | `        w->cur_phase = -1;` | No window counts as logged yet. So the first kernel call of the trial is logged (line 1956). |
| 2540 | `        tev_add(w, EV_OUTPUT, 0, 0);` | Logs the start of the output as an event. Without `--trace` this call does nothing. |
| 2541 | `        print_s(i);` | Prints the S row of the trial (`print_s`, line 2297). |
| 2542 | `        fflush(stdout);` | Writes the buffered rows to the output before the trial runs. |
| 2543 | `        run_trial(w, &plan.tr[i], &rec[i], &sink);` | Runs the trial (`run_trial`, line 2175). That function prints nothing. So the process writes no output inside a timed sequence. |
| 2544 | `        emit_trial(w, i);` | Prints the result rows of the trial (`emit_trial`, line 2317). |
| 2545 | `    }` | Ends the loop over the trials (line 2537). |
| 2546 | `    if (w->group_open)` | Tests whether the counter group is still open after the last trial. |
| 2547 | `        count_close(w);` | Then the group is closed (`count_close`, line 2096). |
| 2548 | `    if (w->close_fail)` | Tests whether a `close` call failed. |
| 2549 | `        printf("X,-1,count_close,%d counter descriptors did not close\n", w->close_fail);` | X row with the trial number -1 and the code `count_close`: the number of counter file descriptors that did not close. |
| 2550 | `    fflush(stdout);` | Writes the buffered rows to the output. |
| 2551 | `    return NULL;` | The worker thread ends. `trial_main` waits for its end in line 2884. |
| 2552 | `}` | Ends the function `trial_worker`. |

### Function `plan_bad` (trial mode): report a defect of the plan file (lines 2554 to 2564)

| Line | Source | Explanation |
|---:|---|---|
| 2554 | `static void plan_bad(int line, const char *fmt, ...)` | Starts the function `plan_bad`. It reports a defect of the plan file on stderr and ends the process with exit status 2. `line` is the number of the plan line. `fmt` and the arguments after it form the message, as in `printf`. |
| 2555 | `{` | Opens the body of `plan_bad`. The whole-chip test did not call this function [Ref4]. |
| 2556 | `    va_list ap;` | `ap`: the list of the arguments that follow `fmt`. |
| 2557 | `    fprintf(stderr, "bad plan %s, line %d: ", plan.path, line);` | Prints the start of the message to stderr: the words `bad plan`, the path of the plan file, the word `line` and the number of the plan line. |
| 2558 | `    va_start(ap, fmt);` | Starts the reading of the arguments that follow `fmt`. |
| 2559 | `    vfprintf(stderr, fmt, ap);` | `vfprintf` prints the message itself to stderr. It builds the text from `fmt` and these arguments. |
| 2560 | `    va_end(ap);` | Ends the reading of the arguments. |
| 2561 | `    fprintf(stderr, "\n");` | Ends the message with a line break. |
| 2562 | `    exit(2);` | Ends the process with exit status 2. |
| 2563 | `}` | Ends the function `plan_bad`. |

### Functions `plan_long` and `plan_size` (trial mode): a number and a size of the plan (lines 2565 to 2598)

| Line | Source | Explanation |
|---:|---|---|
| 2565 | `/* A whole number in [lo, hi] made of digits only. */` | Comment: the function accepts a whole number from `lo` to `hi` that is made of digits only. |
| 2566 | `static int plan_long(const char *s, long lo, long hi, long *out)` | Starts the function `plan_long`. It turns the text `s` into a whole number. For a good text it stores the number in `*out` and returns 1. For any other text it returns 0. The caller then reports the defect with `plan_bad`. |
| 2567 | `{` | Opens the body of `plan_long`. The whole-chip test did not call this function [Ref4]. |
| 2568 | `    char *end;` | `end`: will point to the first character that `strtol` did not read. |
| 2569 | `    if (*s < '0' \|\| *s > '9')` | Tests whether the first character is not a decimal digit. So a sign or a space at the start is rejected. |
| 2570 | `        return 0;` | Such a text returns 0. |
| 2571 | `    errno = 0;` | Sets `errno` to 0. After the next call a value other than 0 shows that the number was too large for the type. |
| 2572 | `    long v = strtol(s, &end, 10);` | `strtol` reads the text as a decimal number. |
| 2573 | `    if (*end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi)` | Tests for four defects: other text follows the number, the number was too large for the type, the number is below `lo`, or it is above `hi`. |
| 2574 | `        return 0;` | A defect returns 0. |
| 2575 | `    *out = v;` | Stores the number. |
| 2576 | `    return 1;` | Returns 1. |
| 2577 | `}` | Ends the function `plan_long`. |
| 2579 | `/* A whole number above 0 with an optional K, M or G. */` | Comment: the function accepts a whole number above 0 with an optional letter `K`, `M` or `G`. |
| 2580 | `static int plan_size(const char *s, uint64_t *out)` | Starts the function `plan_size`. It turns a size text such as `8M` into a number of bytes. For a good text it stores the bytes in `*out` and returns 1. For any other text it returns 0. |
| 2581 | `{` | Opens the body of `plan_size`. The whole-chip test did not call this function [Ref4]. |
| 2582 | `    char *end;` | `end`: will point to the first character that `strtoull` did not read. |
| 2583 | `    int shift = 0;` | `shift`: the number of bits by which a letter shifts the number. It is 0 without a letter. |
| 2584 | `    if (*s < '0' \|\| *s > '9')` | Tests whether the first character is not a decimal digit. |
| 2585 | `        return 0;` | Such a text returns 0. |
| 2586 | `    errno = 0;` | Sets `errno` to 0, as in line 2571. |
| 2587 | `    unsigned long long v = strtoull(s, &end, 10);` | `strtoull` reads the text as a decimal number. |
| 2588 | `    switch (*end) {` | Looks at the character after the number. |
| 2589 | `    case 'K': shift = 10; end++; break;` | The letter `K`: the number times 1024 (a shift by 10 bits). |
| 2590 | `    case 'M': shift = 20; end++; break;` | The letter `M`: the number times 1048576, which gives MiB (a shift by 20 bits). |
| 2591 | `    case 'G': shift = 30; end++; break;` | The letter `G`: the number times 1073741824 (a shift by 30 bits). Only capital letters are accepted in a plan. |
| 2592 | `    }` | Ends the `switch` of line 2588. |
| 2593 | `    if (*end != '\0' \|\| errno != 0 \|\| v == 0 \|\| v > (UINT64_MAX >> shift))` | Tests for four defects: other text follows, the number was too large for the type, the number is 0, or the size in bytes does not fit into 64 bits. |
| 2594 | `        return 0;` | A defect returns 0. |
| 2595 | `    *out = (uint64_t)v << shift;` | Stores the size in bytes: the number shifted left by `shift` bits. |
| 2596 | `    return 1;` | Returns 1. |
| 2597 | `}` | Ends the function `plan_size`. |

### Function `plan_part` (trial mode): one kernel field of a trial line (lines 2599 to 2631)

| Line | Source | Explanation |
|---:|---|---|
| 2599 | `/* "KERNEL@SIZE:MS" (with_ms, where "-" is also allowed) or "KERNEL@SIZE". */` | Comment: the field has the form `KERNEL@SIZE:MS` or the form `KERNEL@SIZE`. The first form holds when `with_ms` is set. Then the text `-` is also allowed. |
| 2600 | `static void plan_part(int line, const char *what, const char *s, int with_ms, struct part *p)` | Starts the function `plan_part`. It reads one kernel field `s` of a trial line into `*p`: the index of the kernel, the size in bytes and the duration in ms. `line` is the number of the plan line and `what` the name of the field. Both are for the error message. A defect ends the process through `plan_bad` (line 2554). |
| 2601 | `{` | Opens the body of `plan_part`. The whole-chip test did not call this function [Ref4]. |
| 2602 | `    char buf[96];` | `buf`: room for a copy of the field of at most 95 characters. The function cuts the copy into pieces. |
| 2603 | `    p->k = -1;` | Start value: no kernel (`k` is -1). |
| 2604 | `    p->size = 0;` | Start value: the size 0. |
| 2605 | `    p->ms = 0;` | Start value: the duration 0. |
| 2606 | `    if (with_ms && !strcmp(s, "-"))` | Tests whether the field may be left out (`with_ms` is 1) and is the text `-`. |
| 2607 | `        return;` | Then the part is absent, and `p->k` stays -1. |
| 2608 | `    if (strlen(s) >= sizeof buf)` | Tests whether the field has 96 characters or more. |
| 2609 | `        plan_bad(line, "%s is too long", what);` | Such a field is a defect. The message says that the field is too long. |
| 2610 | `    strcpy(buf, s);` | Copies the field into `buf`. |
| 2611 | `    char *at = strchr(buf, '@'), *colon = at ? strchr(at, ':') : NULL;` | `at`: the place of the `@` in the field. `colon`: the place of a colon after the `@`. Each is NULL when the character is missing. |
| 2612 | `    if (!at \|\| with_ms != (colon != NULL))` | Tests for a wrong form. The field has no `@`. Or it has no colon although a duration is needed. Or it has a colon although no duration is allowed. |
| 2613 | `        plan_bad(line, "%s '%s' is not %s", what, s, with_ms ? "'-' or KERNEL@SIZE:MS" : "KERNEL@SIZE");` | The message names the field, its text and the form that is needed. |
| 2614 | `    *at = '\0';` | Ends the kernel name at the `@`: a zero byte replaces the `@`. |
| 2615 | `    if (colon)` | Tests whether the field has a colon. |
| 2616 | `        *colon = '\0';` | Ends the size text at the colon. |
| 2617 | `    int k = 0;` | `k`: the index into the kernel table. The search starts at entry 0. |
| 2618 | `    while (k < K_COUNT && strcmp(buf, kernels[k].name))` | Searches the kernel table for the name, as in line 1757. |
| 2619 | `        k++;` | The body of the search loop: goes on to the next entry of the table. |
| 2620 | `    if (k == K_COUNT)` | Tests whether no entry has the name. |
| 2621 | `        plan_bad(line, "%s: unknown kernel '%s'", what, buf);` | The message says that the kernel is unknown. |
| 2622 | `    if (kernels[k].type != T_READ && kernels[k].type != T_OLDREAD)` | Tests whether the kernel is not a read kernel: its type is not `T_READ` and not `T_OLDREAD`. So the trial mode accepts read kernels only. |
| 2623 | `        plan_bad(line, "%s: '%s' is not a read kernel", what, buf);` | The message says that the kernel is not a read kernel. |
| 2624 | `    if (!plan_size(at + 1, &p->size) \|\| p->size % 256 != 0 \|\| p->size > cfg.bytes)` | Reads the size with `plan_size` (line 2580) and tests for three defects: the text is not a size, the size is not a multiple of 256 bytes, or it is above the `--bytes` value. |
| 2625 | `        plan_bad(line, "%s: size '%s' must be a multiple of 256, above 0 and at most --bytes (%lu)", what, at + 1,` | The message names the size text and the rule: a multiple of 256, above 0 and at most the `--bytes` value. |
| 2626 | `                 (unsigned long)cfg.bytes);` | Continues the call of line 2625: the `--bytes` value. |
| 2627 | `    if (colon && !plan_long(colon + 1, 1, MAX_MS, &p->ms))` | For a field with a duration: reads it with `plan_long` (line 2566). It must be a whole number from 1 to 3600000 ms (`MAX_MS`, 1 hour). |
| 2628 | `        plan_bad(line, "%s: bad duration '%s' (whole ms from 1 to %ld)", what, colon + 1, MAX_MS);` | The message names the bad duration and the allowed range. |
| 2629 | `    p->k = k;` | Stores the index of the kernel. From here on the part exists. |
| 2630 | `}` | Ends the function `plan_part`. |

### Function `plan_pairs` (trial mode): the second line of the plan file (lines 2632 to 2662)

| Line | Source | Explanation |
|---:|---|---|
| 2632 | `/* Line 2: "# key=value key=value ...". bytes and cpu must equal the options. */` | Comment: the second line of the plan has the form `# key=value key=value ...`. The values of `bytes` and `cpu` must equal the options. |
| 2633 | `static void plan_pairs(char *s)` | Starts the function `plan_pairs`. It splits the second line of the plan at each space and keeps a pointer to every pair in `plan.pair`. It also checks the pairs `bytes=` and `cpu=`. |
| 2634 | `{` | Opens the body of `plan_pairs`. The whole-chip test did not call this function [Ref4]. |
| 2635 | `    int have_bytes = 0, have_cpu = 0;` | `have_bytes`, `have_cpu`: become 1 when the line holds a pair `bytes=` and a pair `cpu=`. |
| 2636 | `    if (strncmp(s, "# ", 2))` | Tests whether the line does not start with `#` and a space. |
| 2637 | `        plan_bad(2, "the line must start with '# '");` | That is a defect of the plan (`plan_bad`, line 2554). |
| 2638 | `    for (char *tok = s + 2, *sp; tok; tok = sp ? sp + 1 : NULL) {` | Loop over the pairs. `tok` is the start of one pair. `sp` is the space after it, or NULL after the last pair. |
| 2639 | `        sp = strchr(tok, ' ');` | Finds the next space. |
| 2640 | `        if (sp)` | Tests whether a space was found. |
| 2641 | `            *sp = '\0';` | Ends the pair at the space: a zero byte replaces the space. |
| 2642 | `        char *eq = strchr(tok, '=');` | `eq`: the place of the `=` sign in the pair, or NULL. |
| 2643 | `        if (!eq \|\| eq == tok \|\| strchr(tok, ',') \|\| plan.npair == MAX_PAIRS)` | Tests for four defects: no `=` sign, an empty key, a comma in the pair, or a 65th pair (`MAX_PAIRS` is 64). |
| 2644 | `            plan_bad(2, "bad key=value pair '%s'", tok);` | The message names the bad pair. |
| 2645 | `        plan.pair[plan.npair++] = tok;` | Keeps a pointer to the pair. `trial_worker` prints each pair as an M row (lines 2520 to 2523). |
| 2646 | `        if (!strncmp(tok, "bytes=", 6)) {` | Tests whether the pair starts with `bytes=`. |
| 2647 | `            uint64_t b;` | `b`: the size of the pair in bytes. |
| 2648 | `            if (!plan_size(eq + 1, &b) \|\| b != cfg.bytes)` | Reads the size with `plan_size` and tests whether it is no size or differs from the `--bytes` value. |
| 2649 | `                plan_bad(2, "%s differs from --bytes %lu", tok, (unsigned long)cfg.bytes);` | Then the plan has a defect. The message names the pair and the `--bytes` value. |
| 2650 | `            have_bytes = 1;` | Notes that the line has a pair `bytes=`. |
| 2651 | `        }` | Ends the `if` of line 2646. |
| 2652 | `        if (!strncmp(tok, "cpu=", 4)) {` | Tests whether the pair starts with `cpu=`. |
| 2653 | `            long c;` | `c`: the CPU number of the pair. |
| 2654 | `            if (!plan_long(eq + 1, 0, MAX_USE_CPU, &c) \|\| c != cfg.cpus[0])` | Reads the number with `plan_long` (0 to `MAX_USE_CPU`) and tests whether it is no such number or differs from the first CPU of `--cpus`. |
| 2655 | `                plan_bad(2, "%s differs from --cpus %d", tok, cfg.cpus[0]);` | Then the plan has a defect. The message names the pair and the CPU of `--cpus`. |
| 2656 | `            have_cpu = 1;` | Notes that the line has a pair `cpu=`. |
| 2657 | `        }` | Ends the `if` of line 2652. |
| 2658 | `    }` | Ends the loop over the pairs (line 2638). |
| 2659 | `    if (!have_bytes \|\| !have_cpu)` | Tests whether one of the two pairs is missing. |
| 2660 | `        plan_bad(2, "bytes= and cpu= are needed");` | That is a defect. The message says that `bytes=` and `cpu=` are needed. |
| 2661 | `}` | Ends the function `plan_pairs`. |

### Function `plan_trial` (trial mode): one trial line of the plan (lines 2663 to 2723)

| Line | Source | Explanation |
|---:|---|---|
| 2663 | `static void plan_trial(int line, char *s)` | Starts the function `plan_trial`. It reads one trial line `s` of the plan, checks every field and adds one `struct trial` to `plan.tr`. `line` is the number of the plan line. A defect ends the process through `plan_bad` (line 2554). |
| 2664 | `{` | Opens the body of `plan_trial`. The whole-chip test did not call this function [Ref4]. |
| 2665 | `    char *f[PLAN_FIELDS];` | `f`: the 11 fields of the line as text. |
| 2666 | `    int nf = 0;` | `nf`: the number of fields found so far. |
| 2667 | `    long v;` | `v`: a number that `plan_long` returns. |
| 2668 | `    for (char *tok = s, *sp; tok; tok = sp ? sp + 1 : NULL) {` | Loop over the fields. `tok` is the start of one field. `sp` is the space after it, or NULL after the last field. |
| 2669 | `        sp = strchr(tok, ' ');` | Finds the next space. |
| 2670 | `        if (sp)` | Tests whether a space was found. |
| 2671 | `            *sp = '\0';` | Ends the field at the space: a zero byte replaces the space. |
| 2672 | `        if (nf == PLAN_FIELDS \|\| *tok == '\0')` | Tests for two defects: a 12th field, or an empty field. An empty field comes from two spaces one after the other, from a space at the start or at the end of the line, or from an empty line. |
| 2673 | `            plan_bad(line, "%d fields separated by single spaces are needed", PLAN_FIELDS);` | The message says that 11 fields separated by single spaces are needed. |
| 2674 | `        f[nf++] = tok;` | Keeps a pointer to the field and counts it. |
| 2675 | `    }` | Ends the loop over the fields (line 2668). |
| 2676 | `    if (nf != PLAN_FIELDS)` | Tests whether the line has fewer than 11 fields. |
| 2677 | `        plan_bad(line, "%d fields separated by single spaces are needed, %d found", PLAN_FIELDS, nf);` | The message says how many fields are needed and how many were found. |
| 2678 | `    plan.tr = realloc(plan.tr, ((size_t)plan.n + 1) * sizeof *plan.tr);` | `realloc` makes the array `plan.tr` one trial longer. |
| 2679 | `    if (!plan.tr)` | Tests whether the memory could not be given. |
| 2680 | `        plan_bad(line, "no memory");` | That ends the process through `plan_bad` with the message `no memory`. |
| 2681 | `    struct trial *p = &plan.tr[plan.n];` | `p`: the new trial. |
| 2682 | `    memcpy(p->f, f, sizeof f);` | Copies the 11 field pointers into the trial. `print_s` prints these texts in the S row (line 2302). |
| 2683 | `    if (!plan_long(f[0], 0, 1000000, &v) \|\| v != plan.n)` | Field 1, `trial`: it must be the number of this trial, counted from 0 in the order of the file. |
| 2684 | `        plan_bad(line, "trial '%s': the trial numbers must be 0, 1, 2, ... (%d expected)", f[0], plan.n);` | The message names the field and the number that was expected. |
| 2685 | `    if (strchr(f[1], ','))` | Field 2, `cond`, a label of the condition: it must hold no comma. |
| 2686 | `        plan_bad(line, "cond '%s' holds a comma", f[1]);` | The message names the label. |
| 2687 | `    if (!plan_long(f[2], 1, 4, &v))` | Field 3, `rep`: a whole number from 1 to 4. The file `DECISIONS-bwx8.md` calls it the number of this repeat of the condition in the process. |
| 2688 | `        plan_bad(line, "rep '%s' is not 1 to 4", f[2]);` | The message names the bad value. |
| 2689 | `    plan_part(line, "prev", f[3], 1, &p->prev);` | Field 4, `prev`: the previous activity. `plan_part` (line 2600) reads it. It has a duration and may be `-`. |
| 2690 | `    plan_part(line, "pfx", f[4], 1, &p->pfx);` | Field 5, `pfx`: the prefix. It has a duration and may be `-`. |
| 2691 | `    plan_part(line, "pred", f[5], 1, &p->pred);` | Field 6, `pred`: the predecessor. It has a duration and may be `-`. |
| 2692 | `    plan_part(line, "tgt", f[6], 0, &p->tgt);` | Field 7, `tgt`: the target. It has no duration field and cannot be left out. |
| 2693 | `    if (p->pfx.k >= 0 && p->pfx.ms % 4 != 0)` | Tests whether the trial has a prefix whose duration is not a multiple of 4 ms. The prefix runs as 4 windows of a quarter of its duration each (line 2249). |
| 2694 | `        plan_bad(line, "pfx duration %ld ms is not a multiple of 4", p->pfx.ms);` | The message names the duration. |
| 2695 | `    if (!plan_long(f[7], 1, MAX_NWIN, &v))` | Field 8, `nwin`: the number of target windows, a whole number from 1 to 4096 (`MAX_NWIN`). |
| 2696 | `        plan_bad(line, "nwin '%s' is not 1 to %d", f[7], MAX_NWIN);` | The message names the bad value. |
| 2697 | `    p->nwin = (int)v;` | Stores the number of target windows. |
| 2698 | `    if (!plan_long(f[8], 1, MAX_MS, &p->win_ms))` | Field 9, `win_ms`: the duration of one target window, a whole number from 1 to 3600000 ms (`MAX_MS`). |
| 2699 | `        plan_bad(line, "win_ms '%s' is not 1 to %ld", f[8], MAX_MS);` | The message names the bad value. |
| 2700 | `    p->count = !strcmp(f[9], "closed") ? CS_CLOSED : !strcmp(f[9], "open") ? CS_OPEN : !strcmp(f[9], "read") ? CS_READ : -1;` | Field 10, `count`: the counter state. The words `closed`, `open` and `read` give the codes of line 1824. Any other word gives -1. |
| 2701 | `    if (p->count < 0)` | Tests whether the word was none of the three. |
| 2702 | `        plan_bad(line, "count '%s' is not closed, open or read", f[9]);` | The message names the bad word. |
| 2703 | `    if (strcmp(f[10], "0") && strcmp(f[10], "1"))` | Field 11, `bins`: tests whether the text is neither `0` nor `1`. |
| 2704 | `        plan_bad(line, "bins '%s' is not 0 or 1", f[10]);` | The message names the bad text. |
| 2705 | `    p->bins = f[10][0] == '1';` | `bins` becomes 1 for the text `1` and 0 for the text `0`. |
| 2706 | `    plan.n++;` | Counts the trial. |
| 2707 | `    /* The record storage is bounded here, before the process pins or` | Comment: the size of the record storage is limited here. The sentence goes on in line 2708. |
| 2708 | `     * allocates. */` | Comment: this happens before the process pins a thread or allocates the records. |
| 2709 | `    recsz.windows += (size_t)trial_windows(p);` | Adds the windows of this trial to the number of window records (`trial_windows`, line 2217). |
| 2710 | `    recsz.bins += (size_t)p->nwin * (size_t)window_bins(p);` | Adds the bins of this trial: `nwin` times `window_bins(p)` (line 2224). |
| 2711 | `    if (p->count == CS_READ)` | Tests whether the trial has the counter state `read`. |
| 2712 | `        recsz.counts += (size_t)p->nwin + 1;` | Adds the `nwin + 1` counter readings of this trial. |
| 2713 | `    recsz.trace = plan.trace ? TRACE_CAP : 0;` | With `--trace` the storage holds `TRACE_CAP` (1048576) trace events. Without `--trace` it holds none. |
| 2714 | `    recsz.bytes = (size_t)plan.n * sizeof(struct trec) + recsz.windows * sizeof(struct win) +` | `recsz.bytes`: the size of the record block for all trials up to this line: the trial records plus the window records. The sum goes on in line 2715. |
| 2715 | `                  recsz.counts * sizeof(struct counts) + recsz.bins * sizeof(struct bin) + recsz.trace * sizeof(struct tev);` | Continues the sum of line 2714: plus the counter readings, the bins and the trace events. |
| 2716 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2717 | `    recsz.bytes += plan.rec_pad;` | Adds the pad of `--rec-pad` to the size. |
| 2718 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2719 | `    if (recsz.bytes > MAX_REC_BYTES)` | Tests whether the size is above 256 MiB (`MAX_REC_BYTES`). |
| 2720 | `        plan_bad(line, "the records of the plan up to this line need %zu bytes, the bound is %lu bytes", recsz.bytes,` | Then the plan has a defect. The message gives the size that the records up to this line need, and the upper limit. |
| 2721 | `                 MAX_REC_BYTES);` | Continues the call of line 2720: the upper limit. |
| 2722 | `}` | Ends the function `plan_trial`. |

### Function `read_plan` (trial mode): read and check the whole plan (lines 2724 to 2776)

| Line | Source | Explanation |
|---:|---|---|
| 2724 | `/* Reads and checks the whole plan. Returns only if it can run. */` | Comment: the function reads and checks the whole plan. It returns only when the plan can run. |
| 2725 | `static void read_plan(void)` | Starts the function `read_plan`. It reads the plan file `plan.path` into memory, computes its checksum and checks it line by line. A defect ends the process with exit status 2. |
| 2726 | `{` | Opens the body of `read_plan`. The whole-chip test did not call this function [Ref4]. |
| 2727 | `    size_t cap = 1 << 16, len = 0, got;` | `cap`: the size of the text buffer, 65536 bytes at the start. `len`: the number of bytes read so far. `got`: the number of bytes of one read. |
| 2728 | `    FILE *f = fopen(plan.path, "rb");` | Opens the plan file for reading. |
| 2729 | `    char *text = malloc(cap + 1);` | Allocates the text buffer, with room for one more byte at its end. |
| 2730 | `    int line = 0;` | `line`: the number of the plan line that is checked. |
| 2731 | `    if (!f \|\| !text) {` | Tests whether the file could not be opened or the buffer could not be allocated. |
| 2732 | `        fprintf(stderr, "cannot read the plan %s: %s\n", plan.path, strerror(errno));` | Prints `cannot read the plan`, the path and the reason to stderr. |
| 2733 | `        exit(2);` | Ends the process with exit status 2. |
| 2734 | `    }` | Ends the `if` of line 2731. |
| 2735 | `    while ((got = fread(text + len, 1, cap - len, f)) > 0) {` | Loop that reads the file in pieces until no byte is left. |
| 2736 | `        len += got;` | Counts the bytes of the piece. |
| 2737 | `        if (len == cap && !(text = realloc(text, (cap *= 2) + 1))) {` | When the buffer is full, `realloc` doubles its size. The test is true when that fails. |
| 2738 | `            fprintf(stderr, "no memory for the plan\n");` | Prints `no memory for the plan` to stderr. |
| 2739 | `            exit(2);` | Ends the process with exit status 2. |
| 2740 | `        }` | Ends the `if` of line 2737. |
| 2741 | `    }` | Ends the read loop (line 2735). |
| 2742 | `    if (ferror(f)) {` | Tests whether a read failed. |
| 2743 | `        fprintf(stderr, "cannot read the plan %s\n", plan.path);` | Prints `cannot read the plan` and the path to stderr. |
| 2744 | `        exit(2);` | Ends the process with exit status 2. |
| 2745 | `    }` | Ends the `if` of line 2742. |
| 2746 | `    fclose(f);` | Closes the file. |
| 2747 | `    text[len] = '\0';` | Ends the text with a zero byte. |
| 2748 | `    plan.hash = 14695981039346656037ULL; /* FNV-1a, 64 bit, over the bytes of the file */` | `plan.hash`: the start value of the FNV-1a hash, a 64-bit checksum. The comment says that it is computed over the bytes of the file. |
| 2749 | `    for (size_t i = 0; i < len; i++)` | Loop over the bytes of the file. |
| 2750 | `        plan.hash = (plan.hash ^ (uint8_t)text[i]) * 1099511628211ULL;` | One step of the hash per byte: an exclusive or with the byte, then a multiplication by the constant 1099511628211. `trial_worker` prints the result in the M row `plan_fnv1a64` (line 2484). |
| 2751 | `    if (strlen(text) != len)` | Tests whether the text ends before the end of the file. The file then holds a zero byte. |
| 2752 | `        plan_bad(0, "the file holds a zero byte");` | That is a defect of the plan. |
| 2753 | `    for (char *s = text, *next; *s; s = next) {` | Loop over the lines of the text. `s` is the start of a line. `next` is the start of the line after it. |
| 2754 | `        char *nl = strchr(s, '\n');` | `nl`: the line break at the end of the line, or NULL for a last line without one. |
| 2755 | `        next = nl ? nl + 1 : s + strlen(s);` | The next line starts after the line break. Without a line break `next` points to the end of the text, and the loop ends after this line. |
| 2756 | `        if (nl)` | Tests whether the line has a line break. |
| 2757 | `            *nl = '\0';` | Ends the line there: a zero byte replaces the line break. |
| 2758 | `        line++;` | Counts the line. |
| 2759 | `        if (line == 1) {` | Tests for the first line of the plan. |
| 2760 | `            if (strcmp(s, PLAN_LINE1))` | The first line must be the text of `PLAN_LINE1` (line 1815). |
| 2761 | `                plan_bad(1, "the line must be '%s'", PLAN_LINE1);` | If it is not: a defect of the plan. The message gives the text that is needed. |
| 2762 | `        } else if (line == 2) {` | Tests for the second line. |
| 2763 | `            plan_pairs(s);` | `plan_pairs` (line 2633) reads the second line. |
| 2764 | `        } else if (line == 3) {` | Tests for the third line. |
| 2765 | `            if (strcmp(s, PLAN_LINE3))` | The third line must be the text of `PLAN_LINE3` (line 1816): the names of the 11 fields. |
| 2766 | `                plan_bad(3, "the line must be '%s'", PLAN_LINE3);` | If it is not: a defect of the plan. The message gives the text that is needed. |
| 2767 | `        } else {` | The case of every later line. |
| 2768 | `            plan_trial(line, s);` | Every line from the fourth on is one trial. `plan_trial` (line 2663) reads it. |
| 2769 | `        }` | Ends the chain of tests that starts in line 2759. |
| 2770 | `    }` | Ends the loop over the lines (line 2753). |
| 2771 | `    if (line < 3)` | Tests whether the plan has fewer than three lines. |
| 2772 | `        plan_bad(line + 1, "the three header lines are needed");` | That is a defect: the three header lines are needed. |
| 2773 | `    if (plan.n == 0)` | Tests whether the plan has no trial. |
| 2774 | `        plan_bad(line + 1, "no trial");` | That is a defect too. The message is `no trial`. |
| 2775 | `}` | Ends the function `read_plan`. |

### Function `trial_usage` (trial mode): option summary of the trial mode, then exit status 2 (lines 2777 to 2799)

| Line | Source | Explanation |
|---:|---|---|
| 2777 | `static void trial_usage(void)` | Starts the function `trial_usage`. It prints the option summary of the trial mode to stderr and ends the process with exit status 2. |
| 2778 | `{` | Opens the body of `trial_usage`. The whole-chip test did not reach this function [Ref4]. |
| 2779 | `    fprintf(stderr,` | Starts the first `fprintf` call that writes to stderr. Its text stands in lines 2780 to 2783. |
| 2780 | `            "usage: bwx8 --trial --cpus C --bytes B --plan FILE [--ctl-cpu N] [--no-thp] [--trace]\n"` | Text of the message: the usage line with the options `--trial`, `--cpus`, `--bytes`, `--plan`, `--ctl-cpu`, `--no-thp` and `--trace`. The text names the program `bwx8`, the version of the runner that added the trial mode. |
| 2781 | `            "            [--pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options `--pmu-type` and `--events`, and the two environment variables that can give the counter settings in their place. |
| 2782 | `            "  --cpus: exactly one CPU. --ctl-cpu: CPU of the controlling thread (default 0), another CPU.\n"` | Text of the message: `--cpus` takes exactly one CPU. `--ctl-cpu` is the CPU of the controlling thread (default 0), and it must be another CPU. |
| 2783 | `            "  the counter settings are required if a trial of the plan has count open or read\n");` | Text of the message: the counter settings are required when a trial of the plan has the counter state `open` or `read`. This line ends the call. |
| 2784 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2785 | `    fprintf(stderr,` | Starts the second `fprintf` call. |
| 2786 | `            "  bwx10 adds: [--rec-pad BYTES] [--hot-copy]\n"` | Text of the message: `bwx10` adds the options `--rec-pad` and `--hot-copy`. |
| 2787 | `            "  --rec-pad: unused bytes before the window records, a multiple of %zu from 0 to 65536 (default 0)\n"` | Text of the message: `--rec-pad` gives a number of unused bytes before the window records. It must be a multiple of a value that line 2789 gives, from 0 to 65536, and its default is 0. |
| 2788 | `            "  --hot-copy: the window loop works on a local copy of its window record\n",` | Text of the message: with `--hot-copy` the window loop works on a local copy of its window record. |
| 2789 | `            _Alignof(struct win));` | The value for the text of line 2787: `_Alignof(struct win)`, the alignment in bytes that the compiler needs for a window record. This line ends the call. |
| 2790 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2791 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2792 | `    fprintf(stderr,` | Starts the third `fprintf` call. |
| 2793 | `            "  bwx11 adds: [--evict-mb N]\n"` | Text of the message: `bwx11` adds the option `--evict-mb`. |
| 2794 | `            "  --evict-mb: before the first trial the worker writes N MiB of other memory twice, a whole number\n"` | Text of the message: with `--evict-mb` the worker writes N MiB of other memory twice before the first trial. N is a whole number. The sentence goes on in line 2795. |
| 2795 | `            "              from 0 to 4096 (default 0: no such step)\n");` | Text of the message: N goes from 0 to 4096, and the default 0 means no such step. This line ends the call. |
| 2796 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2797 | `    exit(2);` | Ends the process with exit status 2. |
| 2798 | `}` | Ends the function `trial_usage`. |

### Function `trial_main` (trial mode): the arguments (lines 2800 to 2847)

| Line | Source | Explanation |
|---:|---|---|
| 2800 | `static int trial_main(int argc, char **argv)` | Starts the function `trial_main`, the entry of the trial mode. `main` calls it only when an argument is the word `--trial` (lines 2912 to 2914). |
| 2801 | `{` | Opens the body of `trial_main`. No argument line of the whole-chip test holds the word `--trial` [Ref4]. So the test never ran this function. |
| 2802 | `    struct tw w;` | `w`: the state of the one worker of the trial mode (line 1888). |
| 2803 | `    pthread_t tid;` | `tid`: the handle of the worker thread. |
| 2804 | `    cpu_set_t set;` | `set`: a CPU set, for the check of line 2856. |
| 2805 | `    int bytes_given = 0, counting = 0;` | `bytes_given`: becomes 1 when `--bytes` is given. `counting`: becomes 1 when a trial of the plan wants counters. |
| 2807 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 2808 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 2809 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value needs that. |
| 2810 | `        if (!strcmp(a, "--trial")) {` | The word `--trial` itself needs no action. |
| 2811 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 2812 | `            cfg.use_thp = 0;` | `--no-thp`: the program asks Linux for no 2 MiB pages for the buffer. |
| 2813 | `        } else if (!strcmp(a, "--trace")) {` | Tests for `--trace`. |
| 2814 | `            plan.trace = 1;` | `--trace` enables the event log of the trace. |
| 2815 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2816 | `        } else if (!strcmp(a, "--hot-copy")) {` | Tests for `--hot-copy`. |
| 2817 | `            plan.hot_copy = 1;` | `--hot-copy`: `timed_sequence_hot` runs the windows (lines 2205 to 2206). |
| 2818 | `        } else if (!strcmp(a, "--rec-pad") && more) {` | Tests for `--rec-pad` with a value after it. |
| 2819 | `            long pad = parse_long(argv[++i], "--rec-pad", 0, 65536);` | `pad`: the value in bytes, a whole number from 0 to 65536 (`parse_long`, line 353). |
| 2820 | `            if (pad % (long)_Alignof(struct win) != 0) {` | Tests whether the value is not a multiple of the alignment of a window record. |
| 2821 | `                fprintf(stderr, "bad --rec-pad: '%s' (a multiple of %zu is needed: the window records stay aligned)\n",` | Prints a message to stderr: the bad value and the multiple that is needed. The text gives the reason: the window records stay aligned. |
| 2822 | `                        argv[i], _Alignof(struct win));` | Continues the call of line 2821: the value and the alignment. |
| 2823 | `                exit(2);` | Ends the process with exit status 2. |
| 2824 | `            }` | Ends the `if` of line 2820. |
| 2825 | `            plan.rec_pad = (size_t)pad;` | Stores the pad. |
| 2826 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2827 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2828 | `        } else if (!strcmp(a, "--evict-mb") && more) {` | Tests for `--evict-mb` with a value after it. |
| 2829 | `            evict_mb = parse_long(argv[++i], "--evict-mb", 0, 4096);` | `evict_mb`: the value, a whole number from 0 to 4096 (MiB). |
| 2830 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2831 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 2832 | `            parse_cpus(argv[++i]);` | Reads the CPU list with `parse_cpus` (line 388). The check of line 2848 later demands exactly one CPU. |
| 2833 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 2834 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size, read by `parse_bytes` (line 334). |
| 2835 | `            bytes_given = 1;` | Notes that `--bytes` was given. |
| 2836 | `        } else if (!strcmp(a, "--plan") && more) {` | Tests for `--plan` with a value after it. |
| 2837 | `            plan.path = argv[++i];` | The path of the plan file. |
| 2838 | `        } else if (!strcmp(a, "--ctl-cpu") && more) {` | Tests for `--ctl-cpu` with a value after it. |
| 2839 | `            plan.ctl_cpu = (int)parse_long(argv[++i], "--ctl-cpu", 0, MAX_USE_CPU);` | The CPU of the controlling thread, a whole number from 0 to `MAX_USE_CPU`. |
| 2840 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 2841 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. |
| 2842 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 2843 | `            parse_events(argv[++i]);` | Reads the event list with `parse_events` (line 1771). |
| 2844 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 2845 | `            trial_usage();` | Prints the option summary of the trial mode and ends the process (`trial_usage`, line 2777). Options of the interval mode such as `--threads`, `--seq`, `--stop`, `--start`, `--rounds`, `--min-ms` and `--count` have no branch in this loop. So they end here too. |
| 2846 | `        }` | Ends the chain of tests that starts in line 2810. |
| 2847 | `    }` | Ends the loop over the arguments (line 2807). |

### Function `trial_main` (trial mode): checks, the plan and the start of the worker (lines 2848 to 2887)

| Line | Source | Explanation |
|---:|---|---|
| 2848 | `    if (cfg.ncpus != 1 \|\| !bytes_given \|\| !plan.path \|\| cfg.bytes % 256 != 0) {` | Tests the settings: `--cpus` names exactly one CPU, `--bytes` was given and is a multiple of 256 bytes, and `--plan` was given. |
| 2849 | `        fprintf(stderr, "--trial needs --cpus with exactly one CPU, --bytes (a multiple of 256) and --plan\n");` | If one of them fails: prints the rule to stderr. |
| 2850 | `        trial_usage();` | Then prints the option summary and ends the process with exit status 2 (`trial_usage`). |
| 2851 | `    }` | Ends the `if` of line 2848. |
| 2852 | `    if (plan.ctl_cpu == cfg.cpus[0]) {` | Tests whether the controlling thread and the worker would share one CPU. |
| 2853 | `        fprintf(stderr, "the controlling thread and the worker must not share CPU %d\n", plan.ctl_cpu);` | Prints a message with the CPU number to stderr. |
| 2854 | `        exit(2);` | Ends the process with exit status 2. |
| 2855 | `    }` | Ends the `if` of line 2852. |
| 2856 | `    if (sched_getaffinity(0, sizeof set, &set) != 0 \|\| !CPU_ISSET(cfg.cpus[0], &set) \|\| !CPU_ISSET(plan.ctl_cpu, &set)) {` | Reads the allowed CPU set of the process (`sched_getaffinity`) and tests whether the worker CPU or the CPU of the controlling thread is not in it. A failed call counts as a defect too. |
| 2857 | `        fprintf(stderr, "CPU %d or CPU %d is not in the allowed set of the process\n", cfg.cpus[0], plan.ctl_cpu);` | Prints both CPU numbers to stderr. |
| 2858 | `        exit(2);` | Ends the process with exit status 2. |
| 2859 | `    }` | Ends the `if` of line 2856. |
| 2860 | `    read_plan();` | Reads and checks the whole plan (`read_plan`, line 2725). At this point no thread is pinned and no buffer is mapped. |
| 2861 | `    for (int i = 0; i < plan.n; i++)` | Loop over the trials of the plan. |
| 2862 | `        counting \|= plan.tr[i].count != CS_CLOSED;` | `counting` becomes 1 when a trial has the counter state `open` or `read`. |
| 2863 | `    if (counting && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: a plan with counters, no `--pmu-type`, and the environment variable `BWX_PMU_TYPE` is set. |
| 2864 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 2865 | `    if (counting && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: a plan with counters, no `--events`, and the environment variable `BWX_EVENTS` is set. |
| 2866 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 2867 | `        parse_events(copy);` | Reads the event list from the copy. |
| 2868 | `        free(copy);` | Frees the copy. |
| 2869 | `    }` | Ends the `if` of line 2865. |
| 2870 | `    if (counting && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether a plan with counters still has no PMU type or no event. |
| 2871 | `        fprintf(stderr, "the plan has a trial with count open or read: --pmu-type and --events are needed "` | Prints a message to stderr: the plan has a trial with the counter state `open` or `read`, and `--pmu-type` and `--events` are needed. |
| 2872 | `                        "(or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Continues the text of line 2871: or the two environment variables. |
| 2873 | `        exit(2);` | Ends the process with exit status 2. |
| 2874 | `    }` | Ends the `if` of line 2870. |
| 2876 | `    /* The plan can run. The controlling thread pins itself, starts the` | Comment: the plan can run. The controlling thread pins itself and starts the worker. The sentence goes on in line 2877. |
| 2877 | `     * worker and waits. It never touches the buffer. */` | Comment: then the controlling thread waits. It never touches the buffer. |
| 2878 | `    pin_cpu(plan.ctl_cpu);` | The controlling thread pins itself to the CPU of `--ctl-cpu` (`pin_cpu`, line 415). |
| 2879 | `    memset(&w, 0, sizeof w);` | Sets every field of the worker state to 0. |
| 2880 | `    if (pthread_create(&tid, NULL, trial_worker, &w) != 0) {` | Starts the one worker thread. It runs `trial_worker` (line 2449). |
| 2881 | `        perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 2882 | `        return 2;` | `trial_main` then returns 2, which becomes the exit status of the process (line 2914). |
| 2883 | `    }` | Ends the `if` of line 2880. |
| 2884 | `    pthread_join(tid, NULL);` | Waits for the end of the worker thread (`pthread_join`). |
| 2885 | `    return 0;` | Returns 0, which becomes the exit status of the process (line 2914). |
| 2886 | `}` | Ends the function `trial_main`. |

### The include of the self-test file (lines 2888 to 2903)

| Line | Source | Explanation |
|---:|---|---|
| 2888 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2889 | `#if 0` | `#if 0`: the compiler skips the text from here to the `#endif` of line 2893. |
| 2890 | `/* bwx11- */` | Comment: marks the end of a piece of text that `bwx11` added. |
| 2891 | `#include "bwx10_selftest.c"` | The include line of the self-test file of the version `bwx10`. It stands between the `#if 0` of line 2889 and the `#endif` of line 2893. So the compiler skips it. |
| 2892 | `/* bwx11+ */` | Comment: marks the start of more text that `bwx11` added. |
| 2893 | `#endif` | Ends the `#if 0` of line 2889. |
| 2894 | `/* bwx12+ */` | Comment: marks the start of text that the version `bwx12` of the runner added. |
| 2895 | `#if 0` | `#if 0`: the compiler skips the text from here to the `#endif` of line 2899. |
| 2896 | `/* bwx12- */` | Comment: marks the end of a piece of text that `bwx12` added. |
| 2897 | `#include "bwx11_selftest.c"` | The include line of the self-test file of the version `bwx11`. It stands between the `#if 0` of line 2895 and the `#endif` of line 2899. So the compiler skips it too. |
| 2898 | `/* bwx12+ */` | Comment: marks the start of more text that `bwx12` added. |
| 2899 | `#endif` | Ends the `#if 0` of line 2895. |
| 2900 | `#include "bwx12_selftest.c"` | Includes the file `bwx12_selftest.c`. It defines the function `selftest`. `main` calls that function only for the option `--selftest` (line 2920), and no argument line of the whole-chip test holds this option [Ref4]. |
| 2901 | `/* bwx12- */` | Comment: marks the end of the text that `bwx12` added. |
| 2902 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |

### Function `main`: the start of the program (lines 2904 to 2911)

| Line | Source | Explanation |
|---:|---|---|
| 2904 | `int main(int argc, char **argv)` | Starts the function `main`, the entry point of the program. It reads the arguments, starts the workers, sets the common start of each interval and prints all rows. |
| 2905 | `{` | Opens the body of `main`. |
| 2906 | `    int threads_given = 0;` | `threads_given`: becomes 1 when `--threads` is given (line 2933). The check of line 2969 uses it. |
| 2907 | `    char seq_text[1024] = "";` | `seq_text`: will hold a copy of the `--seq` text for the second header line of the output (line 3023). It has room for 1023 characters. |
| 2908 | `    t_base_ns = now_ns();` | Process start time: one reading of the Linux clock `CLOCK_MONOTONIC` through `now_ns` (line 327), in ns. The T rows print the common start, `t0` and `t1` of each thread as seconds after this time (lines 3083 to 3084). |
| 2909 | `    page_bytes = sysconf(_SC_PAGESIZE);` | `page_bytes`: the size of one small memory page in bytes, as Linux reports it (`sysconf`). `alloc_buf` (line 434) uses it when it places a buffer inside its mapping. |
| 2910 | `    cfg.bytes = 1UL << 20;` | `cfg.bytes` gets its default here: 1 MiB (1048576 bytes). The option `--bytes` replaces it (line 2937). The whole-chip test passes `--bytes 256M` [Ref4]. |
| 2911 | `    restrict_cpus();` | `restrict_cpus` (line 368) removes every CPU above `MAX_USE_CPU` from the allowed CPU set of the process. `MAX_USE_CPU` is 119 unless the build sets another value (line 139). The build of `bwx12` on CRB set no other value [Ref2]. In the whole-chip test the script `rx.sh` has already limited the process to the CPUs 0 to 119 with `taskset` [Ref3]. So this call changed nothing there. |

### Function `main`: the choice between the trial mode and the interval mode (lines 2912 to 2915)

| Line | Source | Explanation |
|---:|---|---|
| 2912 | `    for (int i = 1; i < argc; i++)` | Mode choice. The loop compares every argument with the word `--trial`. |
| 2913 | `        if (!strcmp(argv[i], "--trial"))` | Tests one argument. The argument lines of the spec files `like.spec`, `cfwd.spec` and `crev.spec` do not hold the word `--trial` [Ref4]. So in the whole-chip test the loop ended without the call of line 2914. The program went on in the interval mode, which is the rest of `main`. |
| 2914 | `            return trial_main(argc, argv);` | When an argument is `--trial`, `main` returns the result of `trial_main` (line 2800), and no line below runs. This is the only call of `trial_main` in the file. |

### Function `main`: reading the arguments (lines 2916 to 2968)

| Line | Source | Explanation |
|---:|---|---|
| 2916 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 2917 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 2918 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value is accepted only when `more` is 1, and `argv[++i]` then takes the value. |
| 2919 | `        if (!strcmp(a, "--selftest")) {` | Tests for `--selftest`. |
| 2920 | `            return selftest();` | `--selftest` runs the self-test (the function `selftest` of the included self-test file) and ends the program with its result. The argument lines of the whole-chip test do not hold this option [Ref4]. |
| 2921 | `        } else if (!strcmp(a, "--list")) {` | Tests for `--list`. |
| 2922 | `            for (int k = 0; k < K_COUNT; k++)` | Loop over the kernel table. |
| 2923 | `                printf("%s\n", kernels[k].name);` | `--list` prints the name of every kernel of the table, one per line. |
| 2924 | `            return 0;` | Then the program ends with exit status 0. The argument lines of the whole-chip test do not hold `--list` [Ref4]. |
| 2925 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 2926 | `            cfg.use_thp = 0;` | `--no-thp` sets `cfg.use_thp` to 0. Then `alloc_buf` asks Linux for no 2 MiB pages. The whole-chip test does not pass this option [Ref4]. So `cfg.use_thp` keeps its default 1 (line 282) there, and `alloc_buf` asks Linux for 2 MiB pages. |
| 2927 | `        } else if (!strcmp(a, "--two-buffers")) {` | Tests for `--two-buffers`. |
| 2928 | `            cfg.two_buffers = 1;` | `--two-buffers` sets `cfg.two_buffers` to 1. Then every thread gets a second buffer `b`, also without a copy kernel (line 1647). The whole-chip test does not pass this option [Ref4]. |
| 2929 | `        } else if (!strcmp(a, "--count")) {` | Tests for `--count`. |
| 2930 | `            cfg.count = 1;` | `--count` sets `cfg.count` to 1. Then each worker opens its counter group and reads it before and after every timed interval. `main` prints the C rows from these readings. The whole-chip test passes `--count` [Ref4]. |
| 2931 | `        } else if (!strcmp(a, "--threads") && more) {` | Tests for `--threads` with a value after it. |
| 2932 | `            cfg.threads = (int)parse_long(argv[++i], "--threads", 1, 4096);` | The number of worker threads. `parse_long` (line 353) accepts a whole number from 1 to 4096. The whole-chip test passes 120 [Ref4]. |
| 2933 | `            threads_given = 1;` | Notes that `--threads` was given. |
| 2934 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 2935 | `            parse_cpus(argv[++i]);` | `parse_cpus` (line 388) appends the CPUs of each range of the list to `cfg.cpus`, in the order of the text. The whole-chip test passes `0-63,64-119`. The result is the list 0, 1, ... 119, and `cfg.ncpus` becomes 120 [Ref4]. |
| 2936 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 2937 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size of each thread, read by `parse_bytes` (line 334). That function reads the letter `M` as 2 to the power 20. The whole-chip test passes `256M`, so `cfg.bytes` becomes 268435456 bytes (256 MiB) [Ref4]. |
| 2938 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Tests for `--min-ms` with a value after it. |
| 2939 | `            char *end;` | `end`: will point to the first character that `strtod` did not read. |
| 2940 | `            double ms = strtod(argv[++i], &end);` | `strtod` reads the value as a decimal number of milliseconds. A fraction is allowed. |
| 2941 | `            if (end == argv[i] \|\| *end != '\0' \|\| !(ms > 0) \|\| ms > 3.6e6) {` | Tests for a bad value: no number, other text after the number, a value that is not above 0, or a value above 3.6e6 ms (1 hour). |
| 2942 | `                fprintf(stderr, "bad --min-ms: '%s' (a number of milliseconds above 0 is needed)\n", argv[i]);` | Prints a message with the bad value to stderr. |
| 2943 | `                exit(2);` | Ends the program with exit status 2. |
| 2944 | `            }` | Ends the `if` of line 2941. |
| 2945 | `            cfg.min_s = ms / 1000.0;` | `cfg.min_s`: the value in seconds. With `--stop common` it is the time from the common start to the deadline (line 3061). With `--stop pass` it is the least duration of an interval (line 1715). The whole-chip test passes 6000, which gives 6.0 s [Ref4]. |
| 2946 | `        } else if (!strcmp(a, "--rounds") && more) {` | Tests for `--rounds` with a value after it. |
| 2947 | `            cfg.rounds = (int)parse_long(argv[++i], "--rounds", 1, 1000000);` | The number of rounds, a whole number from 1 to 1000000. The program runs the `--seq` list that many times. The whole-chip test passes 2: round 0 and round 1 [Ref4]. |
| 2948 | `        } else if (!strcmp(a, "--seq") && more) {` | Tests for `--seq` with a value after it. |
| 2949 | `            snprintf(seq_text, sizeof seq_text, "%s", argv[++i]);` | Copies the text of the list to `seq_text`, for the second header line (line 3023). The copy is made first: `parse_seq` changes the argument text. |
| 2950 | `            parse_seq(argv[i]);` | `parse_seq` (line 1750) cuts the argument text itself at each comma. It looks up each name in the kernel table and appends its index to `cfg.seq`. An unknown name ends the program. Result in the whole-chip test: 5 entries for `like.spec` (`oldread`, `asmread`, `read_nop96`, `read_nop256`, `read_1pl`) and 3 entries for `cfwd.spec` and `crev.spec` [Ref4]. `cfg.nseq` holds this number. No name of the test has an `@SIZE` part. So the size of every entry stays 0 until line 2990. |
| 2951 | `        } else if (!strcmp(a, "--stop") && more) {` | Tests for `--stop` with a value after it. |
| 2952 | `            const char *s = argv[++i];` | `s`: the value. |
| 2953 | `            if (strcmp(s, "pass") && strcmp(s, "common"))` | Tests whether the value is neither `pass` nor `common`. |
| 2954 | `                usage();` | Any other value prints the option summary and ends the program (`usage`, line 1737). |
| 2955 | `            cfg.stop_common = !strcmp(s, "common");` | `cfg.stop_common` becomes 1 for `common` and 0 for `pass`. With 1 all threads get one common start time and one common deadline for each interval (lines 3058 to 3063). The whole-chip test passes `--stop common` [Ref4]. |
| 2956 | `        } else if (!strcmp(a, "--start") && more) {` | Tests for `--start` with a value after it. |
| 2957 | `            const char *s = argv[++i];` | `s`: the value. |
| 2958 | `            if (strcmp(s, "common") && strcmp(s, "offset"))` | Tests whether the value is neither `common` nor `offset`. |
| 2959 | `                usage();` | Any other value prints the option summary and ends the program (`usage`). |
| 2960 | `            cfg.start_offset = !strcmp(s, "offset");` | `cfg.start_offset` becomes 1 for `offset` and 0 for `common`. With 0 every worker starts its timed work at byte 0 of its own buffer (line 1662). The whole-chip test passes `--start common` [Ref4]. |
| 2961 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 2962 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. It goes into the field `type` of the structure `perf_event_attr` (line 1589). The whole-chip test passes 11 [Ref4]. |
| 2963 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 2964 | `            parse_events(argv[++i]);` | `parse_events` (line 1771) stores the names in `cfg.ev_name` and the codes in `cfg.ev_code`. `cfg.nev` becomes the number of events. `main` does not interpret the codes. Each worker passes them to Linux in `open_counters` (line 1582). The whole-chip test passes 6 events [Ref4]. |
| 2965 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 2966 | `            usage();` | `usage` (line 1737) prints the option summary to stderr and ends the process with exit status 2. Every option of the three argument lines of the whole-chip test has a branch above [Ref4]. So the test did not reach this line. |
| 2967 | `        }` | Ends the chain of tests that starts in line 2919. |
| 2968 | `    }` | Ends the loop over the arguments (line 2916). |

### Function `main`: checks of the settings (lines 2969 to 3001)

| Line | Source | Explanation |
|---:|---|---|
| 2969 | `    if (threads_given && cfg.ncpus == 0) {` | Check: `--threads` is accepted only together with `--cpus`. The test is true when `--threads` was given and the CPU list is empty. |
| 2970 | `        fprintf(stderr, "--threads requires --cpus\n");` | Prints `--threads requires --cpus` to stderr. |
| 2971 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 2972 | `    }` | Ends the `if` of line 2969. |
| 2973 | `    if (cfg.threads < 1 \|\| cfg.rounds < 1 \|\| cfg.nseq < 1 \|\| cfg.bytes == 0 \|\| cfg.bytes % 256 != 0)` | Checks of the values: the thread count, the round count and the number of `--seq` entries are at least 1, and `--bytes` is above 0 and a multiple of 256 bytes. The settings of the whole-chip test pass this check and the check of line 2969 [Ref4]. |
| 2974 | `        usage();` | A failed check prints the option summary and ends the program with exit status 2 (`usage`). |
| 2975 | `    /* run_bwx.sh passes the counter settings in the environment */` | Comment: the script `run_bwx.sh`, the run script of the first runner, passes the counter settings in the environment. |
| 2976 | `    if (cfg.count && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: with `--count`, without `--pmu-type`, and when the environment variable `BWX_PMU_TYPE` is set. The argument lines of the whole-chip test give `--pmu-type` and `--events` [Ref4]. So lines 2976 to 2982 changed nothing there. |
| 2977 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 2978 | `    if (cfg.count && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: with `--count`, without `--events`, and when the environment variable `BWX_EVENTS` is set. |
| 2979 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 2980 | `        parse_events(copy);` | Reads the event list from the copy. |
| 2981 | `        free(copy);` | Frees the copy. |
| 2982 | `    }` | Ends the `if` of line 2978. |
| 2983 | `    if (cfg.count && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether `--count` is given and the PMU type or the events are still missing. In the whole-chip test the type is 11 and there are 6 events [Ref4]. |
| 2984 | `        fprintf(stderr, "--count requires --pmu-type and --events (or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Prints a message to stderr: `--count` requires `--pmu-type` and `--events`, or the two environment variables. |
| 2985 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 2986 | `    }` | Ends the `if` of line 2983. |
| 2987 | `    for (int s = 0; s < cfg.nseq; s++) {` | Loop over the `--seq` entries. |
| 2988 | `        struct entry *e = &cfg.seq[s];` | `e`: one entry. |
| 2989 | `        if (e->bytes == 0)` | Tests whether the entry has no size of its own (no `@SIZE` part). |
| 2990 | `            e->bytes = cfg.bytes;` | Such an entry gets the size of `--bytes`. In the whole-chip test every entry gets 268435456 bytes [Ref4]. |
| 2991 | `        if (e->bytes > cfg.bytes \|\| e->bytes % 256 != 0 \|\|` | Size check of an entry. The size must be at most `--bytes` and a multiple of 256 bytes. The check goes on in line 2992. |
| 2992 | `            (cfg.stop_common && e->bytes > CHUNK_BYTES && e->bytes % CHUNK_BYTES != 0)) {` | With `--stop common` a size above 2 MiB (`CHUNK_BYTES`) must also be a multiple of 2 MiB. With this stop rule the worker calls the kernel on chunks of 2 MiB (line 1693). 268435456 bytes is 128 times 2 MiB. So the entries of the whole-chip test pass [Ref4]. |
| 2993 | `            fprintf(stderr, "bad size of --seq entry %d (%s): %lu\n", s, kernels[e->k].name, (unsigned long)e->bytes);` | A bad size prints a message to stderr: the number of the entry, the kernel name and the size. |
| 2994 | `            usage();` | Then the option summary is printed, and the program ends with exit status 2 (`usage`). |
| 2995 | `        }` | Ends the `if` of line 2991. |
| 2996 | `        if (kernels[e->k].type == T_COPY)` | Tests whether the kernel of the entry is a copy kernel (type `T_COPY`). |
| 2997 | `            cfg.two_buffers = 1;` | A copy kernel in the list sets `cfg.two_buffers` to 1. Then each thread gets a second buffer `b` (line 1647). The six kernels of the whole-chip test have the type `T_READ` or `T_OLDREAD` in the kernel table (lines 1460 to 1476) [Ref4]. So `cfg.two_buffers` stays 0 there, and each thread has one buffer, `a`. The second header line of every csv file of the test says `two_buffers=0` [Ref5]. |
| 2998 | `    }` | Ends the loop over the entries (line 2987). |
| 2999 | `    if (cfg.ncpus && cfg.threads > cfg.ncpus)` | Tests whether a CPU list was given and has fewer CPUs than the process has threads. |
| 3000 | `        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);` | This only gives a warning on stderr, with both numbers. The CPU list is then used again from its start (line 3011). The whole-chip test has 120 threads and 120 CPUs [Ref4]. So no warning was printed: every file `stderr.txt` of that test is empty [Ref5]. |

### Function `main`: thread records, barrier and start of the workers (lines 3002 to 3017)

| Line | Source | Explanation |
|---:|---|---|
| 3002 | `    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);` | `th`: one record per thread, filled with zeros by `calloc`. |
| 3003 | `    uint64_t **bufs = calloc((size_t)cfg.threads * 2, sizeof *bufs);` | `bufs`: two buffer addresses per thread, for buffer `a` and buffer `b`, filled with zeros. |
| 3004 | `    struct page *pg = calloc((size_t)cfg.threads * 2, sizeof *pg);` | `pg`: one page-state record per entry of `bufs`. In the whole-chip test there are 120 thread records and 240 entries in `bufs` and in `pg` [Ref4]. |
| 3005 | `    if (!th \|\| !bufs \|\| !pg \|\| pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {` | Tests the three allocations and creates the barrier `bar` for the thread count plus 1: the workers and the main thread. In the whole-chip test these are 121 threads [Ref4]. |
| 3006 | `        perror("setup");` | On a failure: `perror` prints the word `setup` and the reason. |
| 3007 | `        return 2;` | On a failure: the program ends with exit status 2. |
| 3008 | `    }` | Ends the `if` of line 3005. |
| 3009 | `    for (int i = 0; i < cfg.threads; i++) {` | Loop that starts the workers. |
| 3010 | `        th[i].idx = i;` | Thread `i` gets the index `i`. |
| 3011 | `        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;` | Thread placement. Thread `i` gets the CPU `cfg.cpus[i % cfg.ncpus]`: entry `i` of the CPU list. The list is used again from its start when there are more threads than entries. Without a CPU list the value is -1, and the thread is not pinned (line 1641). With the 120 threads and the CPU list 0 to 119 of the whole-chip test this is CPU `i` [Ref4]. So threads 0 to 63 run on mesh 0 and threads 64 to 119 run on mesh 1 [Ref5]. |
| 3012 | `        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {` | Creates the thread. It runs `worker` (line 1632): it pins itself, opens its counters, maps its buffer and writes it. `main` does not wait for that here. It goes on with the header lines. The function `main` does not pin the main thread. So the main thread may run on any CPU of the allowed CPU set of the process. |
| 3013 | `            perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 3014 | `            return 2;` | The program then ends with exit status 2. |
| 3015 | `        }` | Ends the `if` of line 3012. |
| 3016 | `    }` | Ends the loop of line 3009. |

### Function `main`: the header lines of the csv file (lines 3018 to 3038)

| Line | Source | Explanation |
|---:|---|---|
| 3018 | `    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "` | Starts the `printf` call of the first header line. The line starts with `# bandwidth:`. It gives the meaning of GB (1e9 bytes) and the formula of the rate of the I rows: `aggregate_GBps` is the sum of the bytes of all threads divided by the longest elapsed time of one thread. |
| 3019 | `           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",` | Continues the text of the first header line: a copy kernel counts the bytes read plus the bytes written. Then come four settings: the thread count, the bytes per thread, `min_ms` and `thp`. |
| 3020 | `           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");` | The four values. `min_ms` is `cfg.min_s` times 1000, printed without decimals. `thp` is `madvise` when the program asks for 2 MiB pages, and `nohugepage` with `--no-thp`. It only says what the program asked for. The P rows show what the buffers got. In the whole-chip test the settings are `threads=120 bytes_per_thread=268435456 min_ms=6000 thp=madvise` in all 9 csv files [Ref5]. |
| 3021 | `    printf("# bwx: seq=%s rounds=%d stop=%s start=%s two_buffers=%d count=%d kernels=%s; "` | Starts the `printf` call of the second header line. The line starts with `# bwx:`. It holds the `--seq` text, the rounds, the stop rule, the start rule, `two_buffers`, `count` and the build kind (`kernels=`). |
| 3022 | `           "round and pos count from 0; times are seconds since process start\n",` | Continues the text of the second header line: round and position count from 0, and the times are seconds after the process start. |
| 3023 | `           seq_text, cfg.rounds, cfg.stop_common ? "common" : "pass", cfg.start_offset ? "offset" : "common",` | The values: the `--seq` text, the number of rounds, `common` or `pass` for the stop rule, and `offset` or `common` for the start rule. |
| 3024 | `           cfg.two_buffers, cfg.count, STANDIN ? "STAND-IN (not AArch64: rates mean nothing)" : "aarch64");` | The values of `two_buffers`, `count` and the build kind. `STANDIN` is 0 in the AArch64 build (line 492), and the build kind is then `aarch64`. A build with stand-in kernels prints a text that starts with `STAND-IN` and says that the rates mean nothing. Every csv file of the whole-chip test says `kernels=aarch64` [Ref5]. |
| 3025 | `    printf("# I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps\n"` | Starts the `printf` call of the third, fourth and fifth header line. This line holds the column names of the I rows (line 3077). |
| 3026 | `           "# T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags\n"` | The fourth header line: the column names of the T rows (line 3081). |
| 3027 | `           "# P,round,pos,tid,buffer,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n");` | The fifth header line: the column names of the P rows. `print_p` (line 1570) prints these rows. |
| 3028 | `    if (cfg.count) {` | Tests whether counting is on (`--count`). Only then the header has a sixth line. |
| 3029 | `        printf("# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns");` | Starts the sixth header line: the first nine column names of the C rows, up to `cputime_ns`. |
| 3030 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 3031 | `            printf(",%s", cfg.ev_name[e]);` | Appends the event names in the order of `--events`, one column per event. |
| 3032 | `        printf("; pmu_type=%ld codes=", cfg.pmu_type);` | Appends the PMU type (`pmu_type=`) and the word `codes=`. |
| 3033 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 3034 | `            printf("%s0x%llx", e ? "," : "", (unsigned long long)cfg.ev_code[e]);` | Appends the event codes in hexadecimal, with commas between them. |
| 3035 | `        printf("\n");` | Ends the header line with a line break. In the whole-chip test the line ends with `pmu_type=11 codes=0x198,0x199,0x19a,0x19b,0x19c,0x19` [Ref5]. |
| 3036 | `    }` | Ends the `if` of line 3028. |
| 3037 | `    fflush(stdout);` | `fflush` writes the header lines to the standard output now. In the whole-chip test the standard output is the csv file: the script `rx.sh` redirects it there [Ref3]. |

### Function `main`: the loop over rounds and positions, and the common start (lines 3039 to 3065)

| Line | Source | Explanation |
|---:|---|---|
| 3039 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds, as in `worker` (line 1656). In the whole-chip test `round` runs from 0 to 1 [Ref4]. |
| 3040 | `        for (int pos = -1; pos < cfg.nseq; pos++) {` | Loop over the positions. `pos` starts at -1, not at 0. Position -1 is one extra pass of the loop before the first interval. Each position from 0 up is one timed interval. `main` and the workers go through the same rounds and positions. At each barrier call below a thread waits until all workers and `main` have arrived. The whole-chip test has 10 intervals per process for `like.spec` and 6 for `cfwd.spec` and `crev.spec` [Ref4]. |
| 3041 | `            if (pos < 0 && (round > 0 \|\| cfg.threads == 1))` | Tests whether the pass with position -1 must be skipped: in every round after round 0, and in a process with one thread. |
| 3042 | `                continue;` | Skips that pass. So in a process with more than one thread it runs once, before the first interval. |
| 3043 | `            if (pos < 0) {` | The case of position -1. |
| 3044 | `                /* the workers have allocated and first touched their buffers */` | Comment: at this point the workers have allocated their buffers and have written them for the first time. |
| 3045 | `                pthread_barrier_wait(&bar);` | `main` calls the barrier. The call returns when all workers have mapped and written their buffers and wait in line 1652. |
| 3046 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 3047 | `                    bufs[2 * i] = th[i].a;` | Copies the address of buffer `a` of thread `i` into entry `2 * i` of `bufs`. |
| 3048 | `                    bufs[2 * i + 1] = th[i].b;` | Copies the address of buffer `b` of thread `i` into entry `2 * i + 1`. The entry stays NULL when the thread has no second buffer. Buffer `b` does not exist in the whole-chip test [Ref4]. |
| 3049 | `                }` | Ends the loop of line 3046. This pass of the position loop goes on with the page-state block in line 3105. That block prints the page state before the first interval. |
| 3050 | `            } else {` | The case of a position from 0 up: one interval. |
| 3051 | `                const struct entry *e = &cfg.seq[pos];` | `e`: the `--seq` entry of this position. |
| 3052 | `                const char *name = kernels[e->k].name;` | `name`: the name of its kernel. |
| 3053 | `                double per_pass = (double)e->bytes * (kernels[e->k].type == T_COPY ? 2 : 1);` | `per_pass`: the byte count of one pass over the range of the entry: its size, or twice its size for a copy kernel. The column `passes` of the T rows uses it (line 3084). It is 268435456 bytes in the whole-chip test [Ref4]. |
| 3054 | `                uint64_t total = 0;` | `total`: the sum of the byte counts of all threads. It starts at 0. |
| 3055 | `                int64_t max_el = 0;` | `max_el`: the longest elapsed time of one thread, in ns. It starts at 0. |
| 3057 | `                pthread_barrier_wait(&bar); /* release the workers */` | First barrier call of the interval. It returns when all workers have finished the warm-up pass of this kernel and wait in line 1675. The barrier then lets all of these threads continue. With `--stop common` the workers do not start the kernel yet: each worker waits in an empty loop until `gen` changes (line 1677). The comment says: release the workers. |
| 3058 | `                if (cfg.stop_common) {` | Tests for `--stop common`. Only then `main` sets a common start (lines 3059 to 3062). With `--stop pass` each worker starts its timed interval directly after the barrier. |
| 3059 | `                    int64_t sched = now_ns() + LEAD_NS;` | Common start, set by the main thread. `main` reads the clock once and adds `LEAD_NS` (2 ms, line 132). The result `sched` is the common start time of all threads. `main` is not pinned. In the whole-chip test it runs these lines on one of the CPUs 0 to 119, and a pinned worker waits in the loop of line 1677 on each of these CPUs at that time [Ref3] [Ref4]. |
| 3060 | `                    atomic_store(&t_sched_ns, sched);` | Stores `sched` in the shared variable `t_sched_ns`. The lead of 2 ms is the time that `main` has for lines 3060 to 3062 and that the workers have to see the new `gen`. A worker that sees it only after `sched` has passed starts after the common start time. When its `t0` is then more than 100 us after `sched`, the late flag shows it (line 1725). |
| 3061 | `                    atomic_store(&deadline_ns, sched + (int64_t)(cfg.min_s * 1e9));` | Stores the deadline in the shared variable `deadline_ns`: `sched` plus `cfg.min_s`. In the whole-chip test this is `sched` plus 6 s (6000000000 ns) [Ref4]. |
| 3062 | `                    atomic_fetch_add(&gen, 1);` | Only after both stores `main` adds 1 to `gen`. So a worker that sees the new `gen` reads the new start time and the new deadline. Each worker then reads the clock in a loop until `sched`, and then reads its own start time `t0` (lines 1681 to 1688). After this line `main` passes nothing more to the workers. Each worker stops by itself, at its first clock read at or after the deadline (lines 1700 to 1701). |
| 3063 | `                }` | Ends the `if` of line 3058. |
| 3064 | `                pthread_barrier_wait(&bar); /* all workers finished this interval */` | Second barrier call of the interval. `main` blocks here until all workers have stored their results and wait in line 1727. So between the change of `gen` and the end of the timed interval this call is the only code that `main` runs. It prints nothing in that time. The comment says: all workers finished this interval. |

### Function `main`: the I row, the T rows and the C rows (lines 3066 to 3104)

| Line | Source | Explanation |
|---:|---|---|
| 3066 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the results of the threads. In a process with more than one thread every worker waits at the barrier of line 1731 from here to line 3114. So no kernel runs while `main` prints the I, T and C rows. |
| 3067 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i` for this interval (line 1726). |
| 3068 | `                    total += r->bytes;` | `total` becomes the sum of the byte counts of all threads. |
| 3069 | `                    if (r->t_end - r->t_start > max_el)` | Tests whether the elapsed time of this thread, `t_end - t_start` in ns, is the longest so far. `t_start` is the `t0` of the worker, and `t_end` is its last `t1` (lines 1722 to 1723). |
| 3070 | `                        max_el = r->t_end - r->t_start;` | Keeps the longest elapsed time in `max_el`. |
| 3071 | `                }` | Ends the loop of line 3066. |
| 3072 | `                if (cfg.threads == 1) { /* read by the worker before the interval */` | The branch of a process with one thread. There the worker has read the page state itself before the interval (lines 1670 to 1674), and `main` prints it here. The whole-chip test has 120 threads, so lines 3073 to 3075 did not run there [Ref4]. The comment says: read by the worker before the interval. |
| 3073 | `                    print_p(round, pos, 0, 'a', &th[0].res.pg[0], th[0].res.vm);` | Prints the P row of buffer `a` (`print_p`, line 1570). |
| 3074 | `                    if (th[0].b)` | Tests whether the thread has a second buffer. |
| 3075 | `                        print_p(round, pos, 0, 'b', &th[0].res.pg[1], th[0].res.vm);` | Prints the P row of buffer `b`. It holds the same four counter values as the row of buffer `a`. |
| 3076 | `                }` | Ends the `if` of line 3072. |
| 3077 | `                printf("I,%d,%d,%s,%lu,%d,%lu,%.6f,%.2f\n", round, pos, name, (unsigned long)e->bytes, cfg.threads,` | I row, one per interval, with 9 fields: the letter `I`, round, position, kernel name, `bytes_per_thread`, thread count, `total_bytes`, `max_elapsed_s` and `aggregate_GBps`. `bytes_per_thread` is the size of the `--seq` entry. It is a setting, not a measured value. In the whole-chip test it is 268435456 bytes [Ref4]. |
| 3078 | `                       (unsigned long)total, (double)max_el * 1e-9, (double)total / (double)max_el);` | Continues the call of line 3077. `total_bytes` is `total`. `max_elapsed_s` is `max_el` in seconds, with 6 decimals. `aggregate_GBps` is `total` in bytes divided by `max_el` in ns, with 2 decimals. One byte per ns is 1 GB/s with GB = 1e9 bytes. So this rate is the bytes of all threads divided by the longest elapsed time of one thread. The script `stat_bwx.py` computes the rate of an interval in another way: the sum over the T rows of bytes / elapsed seconds / 1e9, in GB/s. It keeps the I value next to it as `I_agg` [Ref6]. In the 74 intervals of the 9 csv files of the whole-chip test the two values differ by less than 0.004 % (computed on 2026-11-21) [Ref5]. |
| 3079 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 3080 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 3081 | `                    printf("T,%d,%d,%s,%d,%d,%lu,%.6f,%.6f,%.6f,%.6f,%.3f,%s\n", round, pos, name, i, th[i].cpu,` | T row, one per thread and interval, with 13 fields. Fields 1 to 6: the letter `T`, round, position, kernel name, thread index (`tid`) and the CPU of the thread. A thread without a CPU list shows -1. |
| 3082 | `                           (unsigned long)r->bytes, (double)(r->t_end - r->t_start) * 1e-9,` | Continues the call of line 3081. Field 7, `bytes`: the byte count of the worker (line 1696, line 1712). Field 8, `elapsed_s`: `t_end - t_start` in seconds, with 6 decimals. The rate of a thread is field 7 divided by field 8, in bytes per second. The program does not print it. The script `stat_bwx.py` computes it and divides it by 1e9 to get GB/s [Ref6]. |
| 3083 | `                           (double)(r->t_sched - t_base_ns) * 1e-9, (double)(r->t_start - t_base_ns) * 1e-9,` | Continues the call of line 3081. Fields 9 and 10, `t_sched_s` and `t_start_s`: the common start time and `t0`, in seconds after the process start `t_base_ns`, with 6 decimals. With `--stop pass` field 9 equals field 10 (line 1724). |
| 3084 | `                           (double)(r->t_end - t_base_ns) * 1e-9, (double)r->bytes / per_pass, r->late ? "late" : "-");` | Continues the call of line 3081. Field 11, `t_end_s`: the last `t1`, in seconds after the process start. Field 12, `passes`: `bytes / per_pass`, the number of passes over the range of the entry, with 3 decimals. Field 13, `flags`: `late` when `t0` came more than 100 us after the common start (line 1725), and `-` if not. In the 9 csv files of the whole-chip test no T row is `late`. The largest `t_start_s - t_sched_s` is 34 us (0.034 ms, computed on 2026-11-21) [Ref5]. |
| 3085 | `                }` | Ends the loop of line 3079. |
| 3086 | `                for (int i = 0; cfg.count && i < cfg.threads; i++) {` | Loop over the threads. It runs only with `--count`. It prints the C rows: one per thread and interval. |
| 3087 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 3088 | `                    printf("C,%d,%d,%s,%d,%d", round, pos, name, i, th[i].cpu);` | Starts a C row. Fields 1 to 6: the letter `C`, round, position, kernel name, thread index and CPU. |
| 3089 | `                    if (th[i].group_fd < 0)` | Tests whether the thread has no open counter group. |
| 3090 | `                        printf(",NA,NA");` | Fields 7 and 8 are then `NA`. |
| 3091 | `                    else` | The case of a thread with an open group. |
| 3092 | `                        printf(",%llu,%llu", (unsigned long long)(r->c1.enabled - r->c0.enabled),` | Fields 7 and 8, `enabled_ns` and `running_ns`: the enabled time and the running time of the counter group at the second reading minus the same values at the first reading. This line holds the enabled time. |
| 3093 | `                               (unsigned long long)(r->c1.running - r->c0.running));` | Continues the call of line 3092: the running time. |
| 3094 | `                    printf(",%llu", (unsigned long long)(r->c1.cpu_ns - r->c0.cpu_ns));` | Field 9, `cputime_ns`: the thread CPU time at the second reading minus the value at the first reading. The worker takes the first reading (`c0`) directly before `t0` and the second reading (`c1`) directly after its last `t1` (lines 1684 to 1687, lines 1717 to 1720). |
| 3095 | `                    for (int ev = 0; ev < cfg.nev; ev++) {` | Loop over the events, in the order of `--events`. |
| 3096 | `                        int at = th[i].ev_pos[ev];` | `at`: the place of the event in a group reading. It is -1 when the event did not open (line 1600). |
| 3097 | `                        if (at < 0)` | Tests whether the event did not open. |
| 3098 | `                            printf(",NA");` | Its field is then `NA`. |
| 3099 | `                        else` | The case of an event that opened. |
| 3100 | `                            printf(",%llu", (unsigned long long)(r->c1.val[at] - r->c0.val[at]));` | One field per event: the count at the second reading minus the count at the first reading. In the 9 csv files of the whole-chip test no field is `NA` [Ref5]. |
| 3101 | `                    }` | Ends the loop over the events (line 3095). |
| 3102 | `                    printf("\n");` | Ends the row with a line break. |
| 3103 | `                }` | Ends the loop of line 3086. |
| 3104 | `            }` | Ends the `else` of line 3050. |

### Function `main`: the page state, the P rows and the end (lines 3105 to 3126)

| Line | Source | Explanation |
|---:|---|---|
| 3105 | `            if (cfg.threads > 1) {` | Page-state block. It runs only in a process with more than one thread: once at position -1 and once after every interval. At this time every worker waits at a barrier: in line 1653 after position -1, in line 1731 after an interval. So no kernel runs while `main` reads the page state. |
| 3106 | `                /* Page state of all buffers, read between two intervals. It is` | Comment: the page state of all buffers is read between two intervals. The sentence goes on in line 3107. |
| 3107 | `                 * the state after interval pos (pos -1: before the first). The` | Comment: it is the state after interval `pos`. For `pos` -1 it is the state before the first interval. The sentence about the workers starts here. |
| 3108 | `                 * workers wait on the barrier below until it is read. */` | Comment: the workers wait at the barrier below (line 3114) until the state is read. |
| 3109 | `                long long vm[4];` | `vm`: will hold the four counters of `/proc/vmstat`. |
| 3110 | `                int64_t r0 = now_ns();` | `r0`: the clock value before the reading (`now_ns`, line 327). |
| 3111 | `                read_smaps(pg, bufs, 2 * cfg.threads);` | `read_smaps` (line 1515) looks up each entry of `bufs` in `/proc/self/smaps` and skips the NULL entries. It stores the size of each buffer and its part on 2 MiB pages in `pg`. In the whole-chip test `bufs` has 240 entries [Ref4]. |
| 3112 | `                read_vmstat(vm);` | `read_vmstat` (line 1545) reads the four counters of `/proc/vmstat`, once for the whole block. |
| 3113 | `                double ms = (double)(now_ns() - r0) * 1e-6;` | `ms`: the duration of both readings in ms: the clock value now minus `r0`. |
| 3114 | `                pthread_barrier_wait(&bar); /* the reading is done: the workers go on */` | Barrier call that lets the workers continue. Each worker then starts the warm-up pass of the next interval, while `main` prints the P rows below. After the last interval the workers end at this point. The comment says: the reading is done, and the workers go on. |
| 3115 | `                for (int i = 0; i < 2 * cfg.threads; i++)` | Loop over the entries of `bufs`. Entry `i` belongs to thread `i / 2`. An even `i` is buffer `a`, and an odd `i` is buffer `b`. |
| 3116 | `                    if (bufs[i])` | Skips an entry without a buffer. |
| 3117 | `                        print_p(round, pos, i / 2, i % 2 ? 'b' : 'a', &pg[i], vm);` | P row, one per existing buffer, printed by `print_p` (line 1570). The fields: the letter `P`, round, position, thread index, buffer letter, size of the buffer in kB, part on 2 MiB pages in kB, then the four counters of `/proc/vmstat`. The position is that of the interval before the reading, or -1 for the reading before the first interval. All rows of one block carry the same four counter values: they count for the whole system and were read once (line 3112). In the whole-chip test every P row is a row of buffer `a` and reports 262144 kB of 262144 kB on 2 MiB pages [Ref5]. |
| 3118 | `                printf("# page_read,%d,%d,%.3f ms\n", round, pos, ms);` | Prints the line `# page_read` with the round, the position and `ms`, the duration of the page-state reading of this block, with 3 decimals and the unit `ms`. In the 9 csv files of the whole-chip test it lies between 3.745 ms and 4.947 ms (83 lines, read on 2026-11-21) [Ref5]. |
| 3119 | `            }` | Ends the `if` of line 3105. |
| 3120 | `            fflush(stdout);` | `fflush` writes all rows that are still in the output buffer to the standard output. Then the loops go on with the next position. A new timed interval cannot start before `main` has passed line 3057 again, and with `--stop common` also line 3062. So `main` writes no output during a timed interval. |
| 3121 | `        }` | Ends the loop over the positions (line 3040). Measured in the whole-chip test: the time from the latest `t_end_s` of one interval to the `t_sched_s` of the next interval of the same process is 63.8 ms to 139.8 ms (65 pairs in the 9 csv files, computed on 2026-11-21) [Ref5]. In this time lie the output of the rows, the page-state reading, the barrier calls, the warm-up pass of the next kernel and the 2 ms lead. No code of the interval mode calls a sleep function. |
| 3122 | `    }` | Ends the loop over the rounds (line 3039). |
| 3123 | `    for (int i = 0; i < cfg.threads; i++)` | Loop over the threads, after the last interval. |
| 3124 | `        pthread_join(th[i].tid, NULL);` | Waits for the end of worker thread `i` (`pthread_join`). |
| 3125 | `    return 0;` | Returns 0: the process ends with exit status 0. In the whole-chip test the script `rx.sh` writes this status to the file `launches.txt` of the result folder [Ref3]. |
| 3126 | `}` | Ends the function `main`. |

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
