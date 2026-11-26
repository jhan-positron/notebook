# `bwx13_selftest.c` explained, line by line

- Source file: `bwx13-2026-11-15/bwx13_selftest.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 865 lines, 36263 bytes).
- sha256 of the source when this page was built: `2c554063cc91fc21844cdcfea32bd77faa1143306989336db31979cb13819a13`.

## Short version: purpose

This file is the self-test of the runner `bwx13`: it checks what each of the 58 kernels does to memory, and the records and output rows of the trial mode. It runs only when `bwx13` is started with `--selftest`, which the build script `build13.sh` does once after the build. It is `bwx12_selftest.c`, the self-test of the runner version before, plus the checks of the three `rand` kernels (function `test_rand`), and the older check that the kernel table has 55 entries is not compiled any more.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx13.c`. It includes this file with `#include`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Kind**: the type of a kernel in the table `kernels[]` of the runner source: `T_READ` (a read kernel that returns nothing), `T_OLDREAD` (a read kernel that returns a sum), `T_WRITE` or `T_COPY`.
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`rand_nop0`, `rand_nop96`, `rand_nop256`**: the three kernels that `bwx13` adds to `bwx12`. By the file comment of `bwx13.c` they read the same 256 B blocks as `asmread`, in another order, with 0, 96 or 256 nop instructions after the loads of a block. This page calls them the `rand` kernels.
- **Block, `rand_index`, loop 1, loop 2**: a block is 256 B of the range of a `rand` kernel. `rand_index` is a C function of the runner source. It gives the number of the block that a step reads. For a number of blocks `nb` that is a power of two, step `i` reads block `i * (2 * i + 1)` modulo `nb`. For another `nb`, step `i` reads block `i`. Loop 1 of the asm text is the loop for the first case. Loop 2 is the loop for the second case.
- **Round 3, round 4, round 5**: three sets of additions to the runner. Round 3 made bwx10 out of bwx8, round 4 made bwx11 out of bwx10, and round 5 made bwx12 out of bwx11. In this file "round" never means a repeat of a kernel sequence.
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Objdump listing**: the name that the comments of this file use for the machine-code listing.
- **Interval mode, trial mode**: the two modes of the runner. In the interval mode (option `--seq`) each thread runs a sequence of kernels, and the function `worker` of the runner source times each kernel. In the trial mode (option `--trial`) one worker thread runs the trials of a plan file.
- **Plan**: the list of trials that the trial mode reads from a file. One line of the plan is one `struct trial`. The tests of this file write such a structure directly, without a file.
- **Worker record**: the `struct tw` of the runner source. It holds the state of the thread that runs the trials: the buffer, the counter group and the trace. In the self-test the main thread runs the trials.
- **Trial, window, target window**: a trial is a list of timed windows that run one directly after the other: 1 window of previous activity, 4 prefix windows, 1 predecessor window, then the target windows. One window runs one kernel on one range for a requested time.
- **Window record**: the `struct win` of one window. Its plan fields (kernel, range size, passes between two clock reads, duration, bin storage) are set before the trial. Its result fields (bytes, start time, end time, number of bins) are written by the timed sequence.
- **Bin**: a record inside a target window: one clock read and the bytes counted from the start of the window to that clock read. The requested width of a bin is 10 ms.
- **`timed_sequence`, `timed_sequence_hot`**: the two functions of the runner source that run the windows of a trial. With the option `--hot-copy` the second one runs. It copies the plan fields of a window record to local variables before the start clock read of the window.
- **Sink, sink check**: the sink is the variable that receives the sum that an old read kernel returns. After a trial, the sink check compares it with the expected sum: 1 = equal, 0 = not equal, -1 = the trial ran no old read.
- **Evict step**: option `--evict-mb N` of the trial mode. Before the first trial the worker writes N MiB of other memory twice. By the runner source the purpose is that the lines of the benchmark buffer leave the caches.
- **Trace, `EV_KERNEL_FIRST`**: the trial mode can keep a list of the events of a trial (option `--trace`). `EV_KERNEL_FIRST` is the event of the first kernel call of a window.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter group, multiplexed**: the counter group holds the counters that the runner opens for a thread. Linux reports how long the group was enabled and how long it ran. "Multiplexed" means here: in a target window the running time is below the enabled time.
- **Counter state**: what a trial does with the counter group. The plan sets it in the field `count`, and the last field of the E row prints it. `closed`: no counter group is open. `open`: the group is open, and the timed sequence does not read it. `read`: the timed sequence reads the group at the borders of the target windows. `fail`: the plan asked for `open` or `read`, and an event did not open.
- **Rows of the trial mode**: `emit_trial` of the runner source prints them. The first field is the kind of the row. P is a page snapshot before (`pre`) or after (`post`) the trial. W is one window. B is one bin. C holds the counter differences of one target window. E holds the totals of the trial. X is a defect that the runner found.
- **Page snapshot**: the page state of the buffer that the trial mode reads before and after a trial: the size in kB and the kB in huge pages from `/proc/self/smaps`, and four counters from `/proc/vmstat`. A value that is not available is -1 and is printed as `NA`.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Word**: 8 bytes, one `uint64_t`.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Page, `page_bytes`**: the unit of memory protection. `page_bytes` holds its size in bytes. It was 4096 B in the self-test of the CRB build [Ref1].
- **`PROT_NONE` page**: a page that the process may neither read nor write. A load from it or a store to it is a fault.
- **Fault, `SIGSEGV`**: a fault is a forbidden memory access. Linux answers it with the signal `SIGSEGV`. Without a handler the signal ends the process.
- **Guarded buffer, guard page**: a guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one after it. These two pages are the guard pages. The second one starts directly after the buffer only when the buffer size is a multiple of the page size.
- **Stand-in kernels, stand-in build**: on a machine that is not AArch64 (the 64-bit Arm instruction set), plain C loops take the place of the NEON and asm kernels. Such a build is a stand-in build. The header line of the self-test output says which build ran.
- **Nop, vector add, prefetch**: a nop is an instruction that does nothing. A vector add adds two vector registers. A prefetch asks for a cache line: it reads no data and never faults. None of the three changes memory.
- **d8 to d15**: the low halves of the Arm vector registers v8 to v15. The Arm calling convention requires that a function gives them back unchanged.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Build record, CRB build**: the build record is the folder `bwx13-crb-build-1` of the test data. It holds the files that one run of the build script `build13.sh` wrote [Ref2]. This page calls that run the CRB build. The folder name says that the run was on CRB.
- **`build13.sh`, `check_listing13.py`**: two scripts of the same folder. `build13.sh` compiles `bwx13.c`, runs `bwx13 --selftest`, and writes the machine-code listing. `check_listing13.py` checks that listing.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `bwx13.c` includes this file directly before its `main`. `main` reads the page size into `page_bytes`, removes the CPUs above 119 from the allowed set of the process, and calls `selftest` when an argument is `--selftest`. In every other case no function of this file runs (line 827).
2. `selftest` makes the output line-buffered, prints the header line, and stops with the value 2 if the page size is not a multiple of 256 B (lines 829 to 835).
3. It sets the three buffer sizes (1 page, 3 pages, 1 MiB) and the two block offsets (first and last 256 B of a page) (lines 836 to 839).
4. `test_round5` checks the table `kernels[]`: the 26 names of round 5 and their kinds (line 841).
5. `test_rand` checks the three `rand` kernels: their entries in `kernels[]`, the number of 58 entries, the C model of the block order, each kernel on five guarded buffers, and a fault in each page of a range of 4 pages (line 844).
6. For each of the 58 kernels: `test_size` on the three sizes, `test_block` at the two offsets, and for a read kernel `test_touch` (lines 846 to 853).
7. Five checks of the trial mode follow: `test_trial`, `test_trial_hot`, `test_hot_touch`, `test_evict`, `test_emit` (lines 854 to 862).
8. `selftest` prints `# failures=N` and returns 1 if a check failed, else 0. `main` returns this value as the exit status (lines 863 to 864).
9. `build13.sh` stores the output in the file `selftest-bwx13.txt`. It stops the build with exit status 4 when the exit status of the self-test is not 0.

## Behavior a reader must know

- The self-test runs only with `bwx13 --selftest`. `build13.sh` starts it once after the build. A timed run starts the runner with `--seq` or `--trial`. So no function of this file runs between two clock reads of a timed run.
- The self-test computes no rate. Only the checks of the trial mode read the clock.
- Result of the CRB build: the self-test output has 966 lines, 520 rows that end with `pass`, no `FAIL` line, and the last line `# failures=0`. Its header line says `page_bytes=4096 kernels=58 (aarch64)` [Ref1]. `build.txt` of the same build holds the line `## selftest bwx13 exit=0 # failures=0`, and its sha256 value of `bwx13_selftest.c` is the value of the file explained here [Ref2].
- What the kernel checks prove for a read kernel: the buffer is unchanged, no byte within one page outside the test buffer is loaded or stored, and at least one byte of each page of a range of 3 pages is accessed. For `oldread` and `oldread2` in addition: the returned sum equals the sum of all words.
- What the kernel checks cannot prove. They see three things only: the content of memory after the call, a fault, and the sum that an old read kernel returns. They cannot see which bytes inside a page a read kernel without return value loads, a nop, a vector add, the order of loads and stores, the speed, or the saving of the registers d8 to d15. By the file comment the objdump listing is the evidence for the instructions (lines 22 to 25, lines 44 to 48, lines 108 to 112).
- For the three `rand` kernels the checks of the block order run on the C function `rand_index`, not on the asm text. On AArch64 no check sees the order in which a `rand` kernel reads its blocks, or that it reads each block once. The stand-in kernels count their visits, and that check exists in a stand-in build only (lines 704 to 711).
- Three buffers of `test_rand` are smaller than a page of 4096 B: 256 B, 512 B and 2048 B. They start directly after a guard page, but they do not end directly before one. A load of up to 3840 B, 3584 B or 2048 B behind such a buffer does not fault (line 134, line 691) [Ref4].
- `test_rand` calls each `rand` kernel once on a guarded buffer of 256 MiB (1048576 blocks). So the self-test of `bwx13` needs this much free memory (line 632, lines 689 to 691).
- The check of `test_round5` that `kernels[]` has 55 entries is not compiled in this file (lines 618 to 622). `test_rand` checks the number 58 (line 649).
- No check runs the interval mode. The byte count, the clock reads and the stop rule of the function `worker` of the runner source are not tested by this file.
- In `test_size`, in `test_block` and in the first block of `test_rand` (lines 689 to 713) no `SIGSEGV` handler is installed. A kernel that loads from or stores to a `PROT_NONE` page there ends the process. No result line follows, and the last `call` line of the output names the kernel.
- A failed check does not stop the self-test. It adds 1 to `failures`, and the exit status becomes 1.
- The self-test runs in the main thread. `test_hot_touch` adds one helper thread. No thread is pinned to one CPU. The test buffers come from `guarded`: plain `mmap` memory, with no request for huge pages.
- On a machine that is not AArch64 the self-test checks the stand-in kernels, not the real ones. The header line of the output says which kernels ran.

## Source and explanation, line by line

- Text shown: the file `bwx13-2026-11-15/bwx13_selftest.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (865 lines, 36263 bytes, sha256 `2c554063cc91fc21844cdcfea32bd77faa1143306989336db31979cb13819a13`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### File comment: checks added for bwx13 (the three `rand` kernels) (lines 1 to 27)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/* bwx13+ */` | Comment: the marker `bwx13+`. It starts a block of text that was added for bwx13. The next line with `bwx13-` ends the block (line 27). |
| 2 | `/*` | Opens the comment that describes the additions of bwx13. |
| 3 | ` * bwx13_selftest.c - bwx12_selftest.c plus the checks of the three rand_nop` | Comment: `bwx13_selftest.c` is `bwx12_selftest.c` plus the checks of the three `rand_nop` ... The three are `rand_nop0`, `rand_nop96` and `rand_nop256`, the kernels that the runner `bwx13` adds to `bwx12`. A kernel is one inner loop of the benchmark that reads, writes or copies memory. |
| 4 | ` * kernels. Every addition stands between a line "bwx13+" and a line "bwx13-".` | Comment: ... kernels. Every addition stands between a line `bwx13+` and a line `bwx13-`. |
| 5 | ` * Without these blocks this file is bwx12_selftest.c byte for byte.` | Comment: without the `bwx13` blocks the text is `bwx12_selftest.c` byte for byte. A script of this task removed the blocks and found the rest equal to `bwx12_selftest.c` [Ref3]. |
| 6 | ` *` | Comment: an empty line of the comment. |
| 7 | ` * The loop over kernels[] gives the three new kernels the checks of a read` | Comment: the loop over the table `kernels[]` in the function `selftest` (lines 846 to 853) gives the three new kernels the checks of a read ... |
| 8 | ` * kernel. test_rand adds:` | Comment: ... kernel. The new function `test_rand` (line 629) adds the checks that lines 9 to 20 list. |
| 9 | ` *   the three kernels stand once in kernels[] as read kernels, and kernels[]` | Comment: first, the three kernels must stand once in `kernels[]` as read kernels, and `kernels[]` ... |
| 10 | ` *     has 58 entries;` | Comment: ... must have 58 entries (lines 648 to 649). |
| 11 | ` *   rand_index (the C model of the block order) sends 0 .. nb - 1 onto` | Comment: second, `rand_index` is the C model of the block order. It is a function of the runner source that gives the number of the block that a step reads. It must send the numbers 0 to `nb - 1` onto ... |
| 12 | ` *     0 .. nb - 1, each value once, for nb = 1, 2, 8, 8192 and 2^20. For` | Comment: ... the numbers 0 to `nb - 1`, each value once. `nb` is the number of blocks: 1, 2, 8, 8192 and `2^20` (1048576) (lines 654 to 673). One block is 256 B. For ... |
| 13 | ` *     nb = 8 the order is also compared with the list worked out by hand.` | Comment: ... `nb` = 8 the order is also compared with a list that was computed by hand (lines 674 to 677). |
| 14 | ` *     For nb = 3, 48 and 12288 (not powers of two) the order is 0, 1, 2, ...;` | Comment: for `nb` = 3, 48 and 12288, which are not powers of two, the order must be 0, 1, 2 and so on (lines 678 to 684). |
| 15 | ` *   each kernel runs on a guarded buffer of 1, 2, 8, 8192 and 2^20 blocks and` | Comment: third, each kernel runs on a guarded buffer of 1, 2, 8, 8192 and `2^20` blocks and ... A guarded buffer is a test buffer that `guarded` (line 135) puts between two pages that the process may neither read nor write. |
| 16 | ` *     returns, and the buffer is unchanged;` | Comment: ... must return, and the buffer must be unchanged (lines 689 to 713). |
| 17 | ` *   stand-in build only: each block of these buffers is visited exactly once` | Comment: fourth, for a stand-in build only: each block of these buffers must be visited exactly once ... A stand-in build is a build on a machine that is not AArch64 (the 64-bit Arm instruction set). There plain C loops take the place of the NEON and asm kernels. |
| 18 | ` *     (the stand-in counts its visits);` | Comment: ... The stand-in kernel counts its visits (lines 704 to 711). |
| 19 | ` *   each kernel faults in page j of a range of 4 pages when page j is` | Comment: fifth, each kernel must fault in page `j` of a range of 4 pages when page `j` is ... A fault is a forbidden memory access. |
| 20 | ` *     PROT_NONE (4 pages are a power of two of blocks, so this is loop 1).` | Comment: ... `PROT_NONE` (lines 714 to 740). The process may neither read nor write such a page. 4 pages hold a number of blocks that is a power of two. So the kernel runs its loop 1 here. By the runner source, loop 1 of a `rand` kernel reads the blocks in the computed order. Loop 2 reads them in address order, and the kernel uses it when the number of blocks is not a power of two. |
| 21 | ` *` | Comment: an empty line of the comment. |
| 22 | ` * Limits. On AArch64 the test cannot see the order in which the asm text` | Comment: the limits of the new checks. On AArch64 the test cannot see the order in which the asm text ... |
| 23 | ` * reads the blocks, or that it reads a block only once: a read changes no` | Comment: ... reads the blocks, and it cannot see that the asm text reads a block only once. The reason: a read changes no ... |
| 24 | ` * memory. The objdump listing is the evidence that the asm text computes` | Comment: ... memory. The objdump listing is the evidence that the asm text computes ... The objdump listing is the machine code of every kernel as text. |
| 25 | ` * rand_index (check_listing13.py compares every instruction).` | Comment: ... `rand_index`. The script `check_listing13.py` compares every instruction of the three kernels with an expected list. |
| 26 | ` */` | Ends the comment. |
| 27 | `/* bwx13- */` | Comment: the marker `bwx13-`. It ends the block that line 1 started. |

### File comment: checks added for bwx12 (round 5) (lines 28 to 50)

| Line | Source | Explanation |
|---:|---|---|
| 28 | `/* bwx12+ */` | Comment: the marker `bwx12+`. It starts a block of text that was added for bwx12. The next line with `bwx12-` ends the block (line 50). |
| 29 | `/*` | Opens the comment that describes the additions of bwx12. |
| 30 | ` * bwx12_selftest.c - bwx11_selftest.c plus the checks of round 5. Every` | Comment: `bwx12_selftest.c` is `bwx11_selftest.c` plus the checks of round 5. Round 5 is the set of additions that made bwx12 out of bwx11, the runner version before: 26 new kernels. A kernel is one inner loop of the benchmark that reads, writes or copies memory. |
| 31 | ` * addition stands between a line "bwx12+" and a line "bwx12-". Without these` | Comment: every addition stands between a line `bwx12+` and a line `bwx12-`. |
| 32 | ` * blocks this file is bwx11_selftest.c byte for byte.` | Comment: without the `bwx12` blocks the text is `bwx11_selftest.c` byte for byte. The sentence was written for `bwx12_selftest.c`. In this file the `bwx13` blocks must be removed first. |
| 33 | ` *` | Comment: an empty line of the comment. |
| 34 | ` * The loop over kernels[] gives each of the 26 new kernels the checks of its` | Comment: the loop over the table `kernels[]` in the function `selftest` gives each of the 26 new kernels the checks of its kind. The kind is the type of the kernel in that table: read, write or copy. |
| 35 | ` * kind. The 20 read kernels: buffer unchanged, no guard page touched, a fault` | Comment: the checks of the 20 new read kernels: the buffer is unchanged, no guard page is touched, and the kernel faults ... A guard page is a page next to the test buffer that the process may neither read nor write. |
| 36 | ` * in each page of a 3-page range. The 4 write kernels: every word equals v,` | Comment: ... in each page of a 3-page range. The checks of the 4 new write kernels: every word equals `v`, the value that the kernel must store, ... |
| 37 | ` * and only the 256 B of a block are written. The 2 copy kernels: destination` | Comment: ... and only the 256 B of a block are written. The checks of the 2 new copy kernels: the destination ... |
| 38 | ` * equals source, source unchanged, and only the 256 B of a block are copied.` | Comment: ... equals the source, the source is unchanged, and only the 256 B of a block are copied. |
| 39 | ` * The kind comes from kernels[]. test_round5: every new kernel is in` | Comment: the kind comes from `kernels[]`. The function `test_round5` checks that every new kernel stands in ... |
| 40 | ` * kernels[] once, with the kind that its name says, and kernels[] has 55` | Comment: ... `kernels[]` exactly once, with the kind that its name says, and that `kernels[]` has 55 ... The comment describes `bwx12_selftest.c`. In this file the check of the 55 entries is not compiled (lines 618 to 622). |
| 41 | ` * entries. A write kernel entered as a read kernel would pass the read` | Comment: ... entries. The reason for this check: a write kernel that was entered as a read kernel would pass the read ... |
| 42 | ` * checks only by accident, so this check stands before them.` | Comment: ... checks only by accident. So this check runs before them. |
| 43 | ` *` | Comment: an empty line of the comment. |
| 44 | ` * Limits, in addition to the limits below. The test cannot see the vector` | Comment: the limits of the new checks, in addition to the limits that the oldest part of the comment names. The test cannot see the vector ... |
| 45 | ` * adds of read_dadd2 to read_iadd16 or any nop: they change no memory. The` | Comment: ... adds of the kernels `read_dadd2` to `read_iadd16`, or any nop. A vector add adds two vector registers, and a nop is an instruction that does nothing. They change no memory. The ... |
| 46 | ` * objdump listing is the evidence (check_listing12.py). It does not check` | Comment: ... objdump listing is the evidence for them. It is the machine code of every kernel as text, and the script `check_listing12.py` checks it. The self-test also does not check ... |
| 47 | ` * that these kernels preserve d8-d15: check_listing12.py checks the stores` | Comment: ... that these kernels preserve the registers d8 to d15. They are the low halves of the Arm vector registers v8 to v15. The Arm calling convention requires that a function gives them back unchanged. `check_listing12.py` checks the stores ... |
| 48 | ` * and loads of the listing.` | Comment: ... and the loads of these registers in the listing. |
| 49 | ` */` | Ends the comment. |
| 50 | `/* bwx12- */` | Comment: the marker `bwx12-`. It ends the block that the line with `bwx12+` started. |

### File comment: checks added for bwx11 (round 4) (lines 51 to 64)

| Line | Source | Explanation |
|---:|---|---|
| 51 | `/* bwx11+ */` | Comment: the marker `bwx11+`. It starts a block of text that was added for bwx11. The next line with `bwx11-` ends the block. |
| 52 | `/*` | Opens the comment that describes the additions of bwx11. |
| 53 | ` * bwx11_selftest.c - bwx10_selftest.c plus the checks of round 4. Every` | Comment: `bwx11_selftest.c` is `bwx10_selftest.c` plus the checks of round 4. Round 4 is the set of additions that made bwx11 out of bwx10. |
| 54 | ` * addition stands between a line "bwx11+" and a line "bwx11-". Without these` | Comment: every addition stands between a line `bwx11+` and a line `bwx11-`. |
| 55 | ` * blocks this file is bwx10_selftest.c byte for byte.` | Comment: without the `bwx11` blocks the text is `bwx10_selftest.c` byte for byte. |
| 56 | ` *` | Comment: an empty line of the comment. |
| 57 | ` * The three new kernels (read_nop64, read_nop96, read_nop128) are read` | Comment: the three new kernels of round 4 are `read_nop64`, `read_nop96` and `read_nop128`. They are read ... |
| 58 | ` * kernels, so the loop over kernels[] gives them the checks of every read` | Comment: ... kernels. So the loop over `kernels[]` gives them the checks of every read ... |
| 59 | ` * kernel.` | Comment: ... kernel. |
| 60 | ` * test_evict: evict_step() with 4 MiB returns no error, its two clock reads` | Comment: the new function `test_evict` checks three things. First: `evict_step` with 4 MiB returns no error. `evict_step` is the function behind the option `--evict-mb`. It stands in the runner source, the C file of the runner, which includes this file. Second: its two clock reads ... |
| 61 | ` * are in order, and the range is unmapped again (the mapping count of the` | Comment: ... are in order. Third: the range is unmapped again. For this the test compares the count of memory mappings of the ... |
| 62 | ` * process in /proc/self/maps is the same before and after).` | Comment: ... process in the file `/proc/self/maps` before and after the step. |
| 63 | ` */` | Ends the comment. |
| 64 | `/* bwx11- */` | Comment: the marker `bwx11-`. It ends the block that the line with `bwx11+` started. |

### File comment: checks added for bwx10 (round 3) (lines 65 to 86)

| Line | Source | Explanation |
|---:|---|---|
| 65 | `/* bwx10+ */` | Comment: the marker `bwx10+`. It starts a block of text that was added for bwx10. The next line with `bwx10-` ends the block. |
| 66 | `/*` | Opens the comment that describes the additions of bwx10. |
| 67 | ` * bwx10_selftest.c - bwx8_selftest.c plus the checks of round 3. Every` | Comment: `bwx10_selftest.c` is `bwx8_selftest.c` plus the checks of round 3. Round 3 is the set of additions that made bwx10 out of bwx8. |
| 68 | ` * addition stands between a line "bwx10+" and a line "bwx10-". Without these` | Comment: every addition stands between a line `bwx10+` and a line `bwx10-`. |
| 69 | ` * blocks this file is bwx8_selftest.c byte for byte.` | Comment: without the `bwx10` blocks the text is `bwx8_selftest.c` byte for byte. |
| 70 | ` *` | Comment: an empty line of the comment. |
| 71 | ` * The five new kernels are read kernels, so the loop over kernels[] gives` | Comment: the five new kernels of round 3 are read kernels. So the loop over `kernels[]` gives ... |
| 72 | ` * them the checks of every read kernel. A read_pf kernel prefetches past the` | Comment: ... them the checks of every read kernel. A `read_pf` kernel prefetches past the ... A prefetch asks for a cache line. It reads no data and never faults. |
| 73 | ` * end of its range, into the PROT_NONE page after the buffer: the test shows` | Comment: ... end of its range, into the page after the buffer. That page is `PROT_NONE`: the process may neither read nor write it. The test shows ... |
| 74 | ` * that this does not fault. read_1pl reads 16 B of every 64 B line: the test` | Comment: ... that this prefetch does not fault. The kernel `read_1pl` reads 16 B of every 64 B line. The test ... |
| 75 | ` * shows that it touches every page.` | Comment: ... shows that it touches every page. |
| 76 | ` *` | Comment: an empty line of the comment. |
| 77 | ` * test_trial_hot: the window checks of test_trial() with --hot-copy, so they` | Comment: the new function `test_trial_hot` repeats the window checks of `test_trial` with the option `--hot-copy`. So they ... |
| 78 | ` * run through timed_sequence_hot().` | Comment: ... run through `timed_sequence_hot`, the function of the runner source that runs the windows of a trial when `--hot-copy` is given. |
| 79 | ` * test_hot_touch: the window record of a 200 ms window stands in a page of` | Comment: the new function `test_hot_touch`. The window record of a 200 ms window stands in a page of ... A window record is the `struct win` that holds the plan and the result of one timed window. |
| 80 | ` * its own. A second thread waits for the first kernel call of the window,` | Comment: ... its own. A second thread waits for the first kernel call of the window, ... |
| 81 | ` * makes the page PROT_NONE for 20 ms, and makes it usable again. A fault in` | Comment: ... makes the page `PROT_NONE` for 20 ms, and makes it usable again. A fault in ... |
| 82 | ` * that page is counted, and the handler makes the page usable. timed_sequence()` | Comment: ... that page is counted, and the signal handler makes the page usable. The function `timed_sequence` ... |
| 83 | ` * must fault (it reads the record after every pass), so the check can see a` | Comment: ... must fault: it reads the record after every pass. So the check can see a ... |
| 84 | ` * touch. timed_sequence_hot() must not fault.` | Comment: ... touch. The function `timed_sequence_hot` must not fault. |
| 85 | ` */` | Ends the comment. |
| 86 | `/* bwx10- */` | Comment: the marker `bwx10-`. It ends the block that the line with `bwx10+` started. |

### File comment: the base self-test (text written for bwx8) (lines 87 to 128)

| Line | Source | Explanation |
|---:|---|---|
| 87 | `/*` | Opens the oldest part of the file comment. It names bwx8. It holds for `bwx13` in the same way: `bwx13.c` includes this file with `#include`. |
| 88 | ` * bwx8_selftest.c - "bwx8 --selftest": checks what every kernel of bwx8.c` | Comment: the purpose. The option `--selftest` of the runner checks what every kernel of the runner source ... |
| 89 | ` * does to memory, and the accounting of the trial mode. bwx8.c includes this` | Comment: ... does to memory, and the accounting of the trial mode (the mode of the runner with the option `--trial`). The runner source includes this ... |
| 90 | ` * file, so the test runs the machine code of the binary that is timed,` | Comment: ... file. So the test runs the machine code of the binary that is timed, ... |
| 91 | ` * through the same call() as the benchmark. The kernel checks are the text of` | Comment: ... through the same function `call` as the benchmark. So the self-test and a timed run are one binary, and both reach a kernel through `call` and the table `kernels[]`. The kernel checks are the text of ... |
| 92 | ` * bwx_selftest.c. test_trial() at the end is new.` | Comment: ... `bwx_selftest.c`, the self-test of the first runner version. The function `test_trial` at the end was new in bwx8. |
| 93 | ` *` | Comment: an empty line of the comment. |
| 94 | ` * Every buffer ends at a page that cannot be read or written (PROT_NONE) and` | Comment: every test buffer ends at a page that cannot be read or written (`PROT_NONE`) and ... |
| 95 | ` * starts after one. A kernel that touches a byte within one page before the` | Comment: ... starts after one. A kernel that touches a byte within one page before the ... So a load or a store up to one page outside the buffer is a fault. The fault ends the process, except in `test_touch` (line 262) and in the 4-page check of `test_rand` (lines 714 to 740), which install a handler. The row of line 134 names three small buffers of `test_rand` that do not end at such a page. |
| 96 | ` * buffer or within one page after it dies with SIGSEGV. The line "call,..."` | Comment: ... buffer or within one page after it ends with `SIGSEGV`. Linux sends this signal for a forbidden memory access. The line `call,...` ... |
| 97 | ` * printed before each kernel call names the kernel that died.` | Comment: ... that is printed before each kernel call (line 158) names the kernel that ended the process. |
| 98 | ` * Exit status 0 means every check passed.` | Comment: exit status 0 means that every check passed. |
| 99 | ` *` | Comment: an empty line of the comment. |
| 100 | ` * Checks for every kernel that stores (write and copy kinds): every word is` | Comment: the checks for every kernel that stores (the write kind and the copy kind): every word is ... |
| 101 | ` * compared, on whole buffers and on one 256 B block at a page start and at a` | Comment: ... compared, on whole buffers (line 174) and on one 256 B block at a page start and at a ... |
| 102 | ` * page end.` | Comment: ... page end (line 219). |
| 103 | ` * Checks for every read kernel: the buffer is unchanged and no guard page is` | Comment: the checks for every read kernel: the buffer is unchanged and no guard page is ... |
| 104 | ` * touched. The kernel must fault when one page inside its range is made` | Comment: ... touched. The kernel must fault when one page inside its range is made ... |
| 105 | ` * PROT_NONE, for each page of a 3-page range. oldread and oldread2 return a` | Comment: ... `PROT_NONE`, for each page of a 3-page range (line 262). The kernels `oldread` and `oldread2` return a ... |
| 106 | ` * sum: it must equal the sum of all words.` | Comment: ... sum. The test compares it with the sum of all words (line 197). |
| 107 | ` *` | Comment: an empty line of the comment. |
| 108 | ` * Limits. For the read kernels that return nothing, the test proves that` | Comment: the limits. The new read kernel `read` and `asmread` return nothing. For such read kernels the test proves that ... |
| 109 | ` * every page of the range is touched, not every byte: the objdump listing is` | Comment: ... every page of the range is touched. It does not prove that every byte is loaded. For the bytes that such a kernel loads, the objdump listing is ... |
| 110 | ` * the evidence for the bytes. It cannot see in which order a copy kernel` | Comment: ... the evidence for the bytes. The test also cannot see in which order a copy kernel ... |
| 111 | ` * loads and stores. It does not check that a kernel preserves the` | Comment: ... loads and stores. And it does not check that a kernel preserves the ... |
| 112 | ` * callee-saved registers d8-d15.` | Comment: ... registers d8 to d15, which the called function must save (callee-saved). |
| 113 | ` *` | Comment: an empty line of the comment. |
| 114 | ` * Checks of the trial mode (test_trial): one trial with all phases and bins` | Comment: the checks of the trial mode in `test_trial` (line 313). One trial with all phases and with bins ... These checks do not cover the interval mode, the mode of the runner with the option `--seq`. In that mode the function `worker` of the runner source times the kernels. No check of this file runs `worker`. |
| 115 | ` * runs through run_trial(), the function that the trial mode uses. Every` | Comment: ... runs through `run_trial`, the function that the trial mode uses. Every ... |
| 116 | ` * window must hold whole passes and whole groups of passes between clock` | Comment: ... window must hold whole passes and whole groups of passes between clock ... |
| 117 | ` * reads, must last at least its duration, and must not start before the` | Comment: ... reads, must last at least its duration, and must not start before the ... |
| 118 | ` * window before it ended. The last bin of a window must hold the bytes of` | Comment: ... window before it ended. The last bin of a window must hold the bytes of ... A bin is a record inside a target window: one clock read and the bytes counted from the start of the window to that clock read. |
| 119 | ` * the window. The sink check must pass on a clean buffer and must fail after` | Comment: ... the window. The sink check must pass on a clean buffer and must fail after ... The sink is the variable that receives the sum that an old read kernel returns. The sink check compares it with the expected sum. |
| 120 | ` * one word of the buffer is changed.` | Comment: ... one word of the buffer is changed. |
| 121 | ` *` | Comment: an empty line of the comment. |
| 122 | ` * Checks of the rows (test_emit): emit_trial(), the function that prints the` | Comment: the checks of the output rows in `test_emit` (line 779). `emit_trial`, the function that prints the ... |
| 123 | ` * rows of a trial, runs on a record with known values. The printed text is` | Comment: ... rows of a trial, runs on a record with known values. The printed text is ... |
| 124 | ` * compared: the C rows hold differences of two readings, the post P row holds` | Comment: ... compared. The C rows hold differences of two counter readings. The P row with the word `post` holds ... |
| 125 | ` * the second snapshot, the E row holds CPU time and the two context-switch` | Comment: ... the second page snapshot. The E row holds the CPU time and the two context-switch ... |
| 126 | ` * counts in their own fields, and the X rows coverage_na, count_multiplexed` | Comment: ... counts, each in its own field. And the X rows with the codes `coverage_na`, `count_multiplexed` ... |
| 127 | ` * and sink are printed.` | Comment: ... and `sink` are printed. An X row reports a defect that the runner found in a trial. |
| 128 | ` */` | Ends the comment. |

### Global variables (lines 129 to 131)

| Line | Source | Explanation |
|---:|---|---|
| 129 | `static int failures;` | `failures`: the count of failed checks. `check` (line 165) and `trial_check` (line 297) add to it, and `selftest` prints it at the end (line 863). |
| 130 | `static sigjmp_buf fault_jmp;` | `fault_jmp`: the saved place at which `test_touch` (line 279) or `test_rand` (line 730) continues after a fault. `sigjmp_buf` is the type of the C library for such a saved place. |
| 131 | `static volatile uintptr_t fault_addr;` | `fault_addr`: the address of the last fault. The handler `on_fault` writes it (line 255). `volatile` tells the compiler to read and write the variable in memory at every use. A variable that a signal handler changes needs this. |

### Functions `guarded` and `unguard`: a buffer between two `PROT_NONE` pages (lines 132 to 149)

| Line | Source | Explanation |
|---:|---|---|
| 133 | `/* n words whose first byte follows a PROT_NONE page and whose last byte` | Comment: `guarded` gives `n` words (8 bytes each) whose first byte follows a `PROT_NONE` page and whose last byte ... |
| 134 | ` * precedes one. n * 8 must be a multiple of the page size. */` | Comment: ... stands directly before one. For this, `n * 8` must be a multiple of the page size. The function does not test it. In the CRB build a page has 4096 B [Ref1]. With this page size the callers `test_size`, `test_block`, `test_touch`, `test_trial`, `test_trial_hot` and `hot_touch_run` pass a multiple of the page size. `test_rand` also passes 256 B, 512 B and 2048 B (lines 690 to 691). These three buffers start directly after the first `PROT_NONE` page. But they end 3840 B, 3584 B and 2048 B before the second one, and the bytes between are readable. So a load in that gap does not fault. The comment does not fit these three calls. |
| 135 | `static uint64_t *guarded(size_t n)` | Starts the function `guarded`. It returns the address of `n` words of new memory that lie between two `PROT_NONE` pages. The checks of this file take their test buffers from it. The memory comes from a plain `mmap`, with no request for huge pages. |
| 136 | `{` | Opens the body of `guarded`. |
| 137 | `    size_t len = n * 8;` | `len`: the size of the buffer in bytes. |
| 138 | `    uint8_t *raw = mmap(NULL, len + 2 * (size_t)page_bytes, PROT_NONE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `len` bytes plus two pages of new memory. `page_bytes` is the page size in bytes. `main` of the runner source sets it before it calls the self-test. `PROT_NONE`: at first the process may neither read nor write any byte of the range. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. |
| 139 | `    if (raw == MAP_FAILED \|\| mprotect(raw + page_bytes, len, PROT_READ \| PROT_WRITE) != 0) {` | Tests whether `mmap` failed. If it did not fail, `mprotect` makes the `len` bytes after the first page readable and writable. The first page and the last page stay `PROT_NONE`. A return value other than 0 means that `mprotect` failed. |
| 140 | `        perror("guarded");` | On an error: `perror` prints the word `guarded` and the reason that Linux gave. |
| 141 | `        exit(2);` | On an error: the process ends with exit status 2. |
| 142 | `    }` | Ends the `if` of line 139. |
| 143 | `    return (uint64_t *)(raw + page_bytes);` | Returns the address of the first usable byte, one page after the start of the mapping. |
| 144 | `}` | Ends the function `guarded`. |
| 146 | `static void unguard(uint64_t *p, size_t n)` | Starts the function `unguard`. It releases a buffer of `n` words that `guarded` returned. |
| 147 | `{` | Opens the body of `unguard`. |
| 148 | `    munmap((uint8_t *)p - page_bytes, n * 8 + 2 * (size_t)page_bytes);` | `munmap` gives the whole mapping back to Linux: the buffer and its two `PROT_NONE` pages. The mapping starts one page before `p`. |
| 149 | `}` | Ends the function `unguard`. |

### Functions `pattern`, `calling`, `check` and `is_read` (lines 150 to 171)

| Line | Source | Explanation |
|---:|---|---|
| 151 | `static uint64_t pattern(size_t i, uint64_t salt)` | Starts the function `pattern`. It returns the test value of the word with the number `i`. |
| 152 | `{` | Opens the body of `pattern`. |
| 153 | `    return (i + 1) * 0x9E3779B97F4A7C15ULL ^ salt;` | Returns `(i + 1)` times an odd 64-bit constant, then XOR `salt`. The product is computed first. Two different word numbers `i` always give two different values. Two different `salt` values give two different patterns for the same `i`. |
| 154 | `}` | Ends the function `pattern`. |
| 156 | `static void calling(const struct kdef *kd, size_t n)` | Starts the function `calling`. It names a kernel in the output before the kernel runs. `kd` points to the entry of the kernel in `kernels[]`. `n` is the size of the range in words. |
| 157 | `{` | Opens the body of `calling`. |
| 158 | `    printf("call,%s,%zu\n", kd->name, n * 8);` | Prints the line `call,<kernel>,<bytes>`: the word `call`, the kernel name, and the size of the range in bytes (`n * 8`). The output is line-buffered (line 829), so this line is written before the kernel starts. If the kernel ends the process, this line names it. |
| 159 | `}` | Ends the function `calling`. |
| 161 | `static void check(int ok, const struct kdef *kd, const char *what, size_t n)` | Starts the function `check`. It prints the result line of one kernel check. `ok` is not 0 when the check passed. |
| 162 | `{` | Opens the body of `check`. |
| 163 | `    printf("%s,%s,%zu,%s\n", kd->name, what, n * 8, ok ? "pass" : "FAIL");` | Prints one row with four fields: the kernel name, the name of the check (`what`), the size in bytes (`n * 8`), and `pass` or `FAIL`. |
| 164 | `    if (!ok)` | When the check failed ... |
| 165 | `        failures++;` | ... adds 1 to `failures`. The self-test continues after a failed check. |
| 166 | `}` | Ends the function `check`. |
| 168 | `static int is_read(const struct kdef *kd)` | Starts the function `is_read`. It tells whether a kernel is a read kernel. |
| 169 | `{` | Opens the body of `is_read`. |
| 170 | `    return kd->type == T_READ \|\| kd->type == T_OLDREAD;` | True for the two read kinds. By the table `kernels[]` of the runner source, `T_OLDREAD` is the kind of `oldread` and `oldread2`: they return a sum. `oldread2` is a second copy of `oldread`: the same source under another name. `T_READ` is the kind of every other read kernel, for example `read`, `asmread` and the three `rand` kernels: they return nothing. |
| 171 | `}` | Ends the function `is_read`. |

### Function `test_size`: one kernel on a whole guarded buffer (lines 172 to 215)

| Line | Source | Explanation |
|---:|---|---|
| 173 | `/* The kernel on a whole guarded buffer of n words. */` | Comment: `test_size` runs the kernel on a whole guarded buffer of `n` words. A guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one directly after it. |
| 174 | `static void test_size(const struct kdef *kd, size_t n)` | Starts the function `test_size`. It runs the kernel once on a whole guarded buffer and reads no clock. `selftest` passes three sizes: 1 page, 3 pages and 1 MiB (line 837). What it proves for every kernel: no load and no store within one page outside its buffers. Such an access ends the process. A prefetch raises no fault, so the check does not see one. Read kernel: the buffer is unchanged after the call. Old read kernel: the returned sum equals the sum of all words. Write and copy kernel: every word of the range holds the right value after the call. What it cannot prove: that `read` or `asmread` load anything. A read kernel without a return value that loads nothing passes here. `test_touch` (line 262) checks a part of this. |
| 175 | `{` | Opens the body of `test_size`. |
| 176 | `    struct thread t = { .a = guarded(n), .b = guarded(n) };` | `t`: a thread record in the form that `call` needs (`struct thread` of the runner source). Its buffers `a` and `b` are two guarded buffers of `n` words each. Every other field is 0. |
| 177 | `    uint64_t *a = t.a, *b = t.b, sum = 0;` | `a` and `b`: short names for the two buffers. `sum`: the sum of all words of `a`, built in line 187. |
| 178 | `    uint64_t v = 0xA5A5F00D12345678ULL + n;` | `v`: the value that a write kernel must store in every word. It depends on `n`, so each buffer size gets another value. |
| 179 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum that an old read kernel returns. |
| 180 | `    int ok = 1;` | `ok`: the result of the check that runs now. 1 means passed. |
| 182 | `    /* Every word of the source is different, so a store of the wrong vector` | Comment: every word of the source buffer gets a different value. So a store of the wrong vector ... |
| 183 | `     * or to the wrong offset is seen. */` | Comment: ... or a store to the wrong offset is seen. |
| 184 | `    for (size_t i = 0; i < n; i++) {` | Loop over all `n` words. |
| 185 | `        a[i] = pattern(i, 1);` | Gives every word of `a` its own value: `pattern` with the salt 1. |
| 186 | `        b[i] = 0;` | Sets every word of `b` to 0. |
| 187 | `        sum += a[i];` | `sum` becomes the sum of all words of `a` in 64-bit arithmetic (an overflow wraps). |
| 188 | `    }` | Ends the loop of line 184. |
| 189 | `    calling(kd, n);` | Prints the `call` line (line 158). |
| 190 | `    call(kd, &t, 0, n * 8, v, &sink);` | Runs the kernel on the whole buffer (offset 0, `n * 8` bytes) through `call` of the runner source. `call` chooses the arguments by the kind. A read kernel gets `a`. A write kernel gets `a` and the value `v`, which it stores in every word. A copy kernel reads `a` and writes `b`. The sum that an old read kernel returns goes to `sink`. No `SIGSEGV` handler is installed here. A kernel that loads from or stores to a `PROT_NONE` page ends the process. No result line follows then, and the last `call` line of the output names the kernel. |
| 191 | `    if (is_read(kd)) {` | Branch for a read kernel. |
| 192 | `        /* read: must leave every word as it was (and must not fault) */` | Comment: a read kernel must leave every word as it was, and it must not fault. |
| 193 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 194 | `            ok &= a[i] == pattern(i, 1);` | Every word of `a` must still hold its pattern value. One changed word sets `ok` to 0. |
| 195 | `        check(ok, kd, "buffer unchanged", n);` | Prints the result row with the check name `buffer unchanged`. |
| 196 | `        if (kd->type == T_OLDREAD)` | For the kind `T_OLDREAD` in addition ... |
| 197 | `            check(sink == sum, kd, "returned sum equals the sum of all words", n);` | ... the sum in `sink` must equal `sum`. A kernel that skips one word, or adds one word twice, returns another sum. The check name is `returned sum equals the sum of all words`. |
| 198 | `    } else if (kd->type == T_WRITE) {` | Branch for a write kernel. |
| 199 | `        /* write: every word must hold v afterwards; no word may keep the old pattern */` | Comment: after a write kernel every word must hold `v`. No word may keep the old pattern. |
| 200 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 201 | `            ok &= a[i] == v;` | Every word of `a` must hold `v`. A word that the kernel did not store keeps its pattern value, and no pattern value equals `v`. So a missing store fails the check. |
| 202 | `        check(ok, kd, "every word equals v", n);` | Prints the result row with the check name `every word equals v`. |
| 203 | `    } else {` | Branch for a copy kernel. |
| 204 | `        /* copy: destination must equal source word for word; source unchanged */` | Comment: after a copy kernel the destination must equal the source word for word, and the source must be unchanged. |
| 205 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `b`. |
| 206 | `            ok &= b[i] == pattern(i, 1);` | Every word of `b` must hold the pattern value of the same word of `a`. `b` held 0 before the call. |
| 207 | `        check(ok, kd, "destination equals source", n);` | Prints the first result row of a copy kernel, with the check name `destination equals source`. |
| 208 | `        ok = 1;` | Sets `ok` back to 1 for the second check. |
| 209 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 210 | `            ok &= a[i] == pattern(i, 1);` | Every word of `a` must be unchanged. |
| 211 | `        check(ok, kd, "source unchanged", n);` | Prints the second result row of a copy kernel, with the check name `source unchanged`. |
| 212 | `    }` | Ends the `if` chain of line 191. |
| 213 | `    unguard(a, n);` | Releases the buffer `a` ... |
| 214 | `    unguard(b, n);` | ... and the buffer `b`. |
| 215 | `}` | Ends the function `test_size`. |

### Function `test_block`: 256 B at a page start or at a page end (lines 216 to 249)

| Line | Source | Explanation |
|---:|---|---|
| 217 | `/* One block of 256 B (32 words) at word offset off inside one guarded page.` | Comment: `test_block` runs the kernel on one block of 256 B (32 words) at the word offset `off` inside one guarded page. |
| 218 | ` * Words of the page outside the 256 B must keep their old value. */` | Comment: the words of the page outside the 256 B must keep their old value. |
| 219 | `static void test_block(const struct kdef *kd, size_t off)` | Starts the function `test_block`. It runs the kernel on one block of 256 B (32 words) inside a buffer of one page. 256 B is the smallest range that a kernel may get. With `off` = 0 the block starts directly after the `PROT_NONE` page before the buffer. With the other value of `off` the block ends directly before the `PROT_NONE` page after the buffer (line 839). What it proves for every kernel: no load and no store up to one page before the block start (first case), and none up to one page after the block end (second case). Such an access ends the process. Write and copy kernel: every word of the page outside the block keeps its value. What it cannot prove: which bytes inside the 256 B a read kernel loads. The sum that an old read kernel returns is not compared here. |
| 220 | `{` | Opens the body of `test_block`. |
| 221 | `    size_t n = (size_t)page_bytes / 8, m = 32;` | `n`: the number of words of one page. `m`: the 32 words of the block (256 B). |
| 222 | `    struct thread t = { .a = guarded(n), .b = guarded(n) };` | `t`: a thread record with two guarded buffers of one page each. |
| 223 | `    uint64_t *a = t.a, *b = t.b;` | `a` and `b`: short names for the two buffers. |
| 224 | `    uint64_t v = 0x0123456789ABCDEFULL;` | `v`: the value that a write kernel must store. |
| 225 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This function does not compare it. |
| 226 | `    int ok = 1;` | `ok`: the result of the check. 1 means passed. |
| 228 | `    for (size_t i = 0; i < n; i++) {` | Loop over all words of the page. |
| 229 | `        a[i] = pattern(i, 3);` | Fills the page of `a` with the pattern of the salt 3 ... |
| 230 | `        b[i] = pattern(i, 4);` | ... and the page of `b` with the pattern of the salt 4. So the two pages hold two different patterns. |
| 231 | `    }` | Ends the loop of line 228. |
| 232 | `    calling(kd, m);` | Prints the `call` line with the size 256. |
| 233 | `    call(kd, &t, off * 8, m * 8, v, &sink);` | Runs the kernel on 256 B (`m * 8`) at the byte offset `off * 8`. As in `test_size`, no `SIGSEGV` handler is installed. |
| 234 | `    if (is_read(kd)) {` | Branch for a read kernel. |
| 235 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 236 | `            ok &= a[i] == pattern(i, 3);` | Read kernel: every word of the page of `a` must be unchanged. |
| 237 | `        check(ok, kd, off ? "256 B at page end: page unchanged" : "256 B at page start: page unchanged", m);` | Prints the result row. The name of the check says `page start` for `off` = 0 and `page end` for the other value. The size field is 256. |
| 238 | `    } else if (kd->type == T_WRITE) {` | Branch for a write kernel. |
| 239 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 240 | `            ok &= a[i] == (i >= off && i < off + m ? v : pattern(i, 3));` | Write kernel: the 32 words of the block must hold `v`. Every other word of the page must keep its pattern value. |
| 241 | `        check(ok, kd, off ? "256 B at page end: only those 256 B written" : "256 B at page start: only those 256 B written", m);` | Prints the result row. The check name ends with `only those 256 B written`. |
| 242 | `    } else {` | Branch for a copy kernel. |
| 243 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 244 | `            ok &= b[i] == (i >= off && i < off + m ? pattern(i, 3) : pattern(i, 4)) && a[i] == pattern(i, 3);` | Copy kernel: in `b` the 32 words of the block must hold the values of `a`. Every other word of `b` must keep its own pattern value. `a` must be unchanged. |
| 245 | `        check(ok, kd, off ? "256 B at page end: only those 256 B copied" : "256 B at page start: only those 256 B copied", m);` | Prints the result row. The check name ends with `only those 256 B copied`. |
| 246 | `    }` | Ends the `if` chain of line 234. |
| 247 | `    unguard(a, n);` | Releases the buffer `a` ... |
| 248 | `    unguard(b, n);` | ... and the buffer `b`. |
| 249 | `}` | Ends the function `test_block`. |

### Functions `on_fault` and `test_touch`: a read kernel must touch every page (lines 250 to 291)

| Line | Source | Explanation |
|---:|---|---|
| 251 | `static void on_fault(int sig, siginfo_t *si, void *ctx)` | Starts the function `on_fault`, the `SIGSEGV` handler of `test_touch` and of the 4-page check of `test_rand` (line 721). Linux calls it when a kernel accesses a page that it may not access. `si` holds the details of the fault. |
| 252 | `{` | Opens the body of `on_fault`. |
| 253 | `    (void)sig;` | Marks the argument `sig` as not used. Then the compiler does not warn about it. |
| 254 | `    (void)ctx;` | Marks the argument `ctx` as not used. |
| 255 | `    fault_addr = (uintptr_t)si->si_addr;` | Stores the address of the faulting access in `fault_addr`. |
| 256 | `    siglongjmp(fault_jmp, 1);` | Jumps back to the `sigsetjmp` call that saved the place last: line 279 in `test_touch`, line 730 in `test_rand`. That call now returns 1. The kernel call that faulted does not continue. |
| 257 | `}` | Ends the function `on_fault`. |
| 259 | `/* Read kernels: a range of 3 pages, with one page inside it made PROT_NONE.` | Comment: for read kernels, `test_touch` uses a range of 3 pages, with one page inside it made `PROT_NONE`. |
| 260 | ` * The kernel must fault, and the fault address must lie in that page. This` | Comment: the kernel must fault, and the fault address must lie in that page. This ... |
| 261 | ` * shows that the kernel touches every page of its range. */` | Comment: ... shows that the kernel touches every page of its range. |
| 262 | `static void test_touch(const struct kdef *kd)` | Starts the function `test_touch`. It is for read kernels only. The buffer has 3 pages. The loop runs three times. Each time another one of the pages is `PROT_NONE`, and the kernel runs on the whole buffer. The kernel must fault, and the fault address must lie in that page. What it proves: the kernel accesses at least one byte of each of the 3 pages. A kernel that loads nothing, or that leaves out a page, fails. What it cannot prove: that every byte or every 64 B line of a page is loaded. One load per page passes. A page has 4096 B in the CRB build [Ref1]. By the file comment the objdump listing is the evidence for the loads (lines 109 to 110). The check also cannot prove anything about a nop, a vector add, or the use of a loaded value. They change no memory and raise no fault. For a `rand` kernel 3 pages of 4096 B are 48 blocks, which is not a power of two. So this check runs loop 2 of such a kernel, and `test_rand` adds a check on 4 pages for loop 1 (lines 714 to 740). |
| 263 | `{` | Opens the body of `test_touch`. |
| 264 | `    size_t n = 3 * (size_t)page_bytes / 8;` | `n`: the number of words of 3 pages. |
| 265 | `    struct thread t = { .a = guarded(n) };` | `t`: a thread record with one guarded buffer of 3 pages. A read kernel needs no buffer `b`. |
| 266 | `    struct sigaction sa, old;` | `sa`: the new setting for the signal. `old`: the setting from before. |
| 267 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This function does not compare it. |
| 269 | `    memset(&sa, 0, sizeof sa);` | Sets every byte of `sa` to 0. |
| 270 | `    sa.sa_sigaction = on_fault;` | The handler is `on_fault`. |
| 271 | `    sa.sa_flags = SA_SIGINFO;` | The flag `SA_SIGINFO` makes Linux pass the fault address to the handler. |
| 272 | `    sigaction(SIGSEGV, &sa, &old);` | Installs `on_fault` as the handler of `SIGSEGV`. `old` keeps the setting from before. |
| 273 | `    for (volatile int j = 0; j < 3; j++) {` | The loop runs three times, once per page `j`. `j` is `volatile`: it keeps its value across the jump of line 256. |
| 274 | `        uint8_t *pg = (uint8_t *)t.a + (size_t)j * (size_t)page_bytes;` | `pg`: the address of page `j` of the buffer. |
| 275 | `        volatile int faulted = 0;` | `faulted`: becomes 1 when the kernel faulted. It is `volatile` for the same reason as `j`. |
| 276 | `        mprotect(pg, (size_t)page_bytes, PROT_NONE);` | `mprotect` makes this page `PROT_NONE`. |
| 277 | `        fault_addr = 0;` | Clears the fault address of the pass before. |
| 278 | `        calling(kd, n);` | Prints the `call` line. |
| 279 | `        if (sigsetjmp(fault_jmp, 1) == 0)` | `sigsetjmp` saves this place in `fault_jmp` and returns 0 at its direct call. The argument 1 saves the signal mask, and the jump restores it. So `SIGSEGV` can be caught again for the next page. |
| 280 | `            call(kd, &t, 0, n * 8, 0, &sink);` | The value 0: the kernel is called on the whole range of 3 pages. |
| 281 | `        else` | The other value: when the kernel faults, `on_fault` jumps back to line 279, and `sigsetjmp` returns 1 there. |
| 282 | `            faulted = 1;` | Then `faulted` becomes 1. |
| 283 | `        mprotect(pg, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | Makes the page readable and writable again. |
| 284 | `        check(faulted && fault_addr >= (uintptr_t)pg && fault_addr < (uintptr_t)pg + (uintptr_t)page_bytes, kd,` | The check passes when the kernel faulted and the fault address lies in the `PROT_NONE` page. The call goes on in the next three lines. |
| 285 | `              j == 0 ? "faults in page 0 of 3 when it is PROT_NONE"` | Continues the call of line 284: the name of the check gives the page number. This is the name for page 0. |
| 286 | `                     : j == 1 ? "faults in page 1 of 3 when it is PROT_NONE" : "faults in page 2 of 3 when it is PROT_NONE",` | Continues the call: the names for page 1 and for page 2. |
| 287 | `              n);` | Ends the call: the size of the range in words. The row prints it in bytes. |
| 288 | `    }` | Ends the loop of line 273. |
| 289 | `    sigaction(SIGSEGV, &old, NULL);` | Restores the `SIGSEGV` setting from before. |
| 290 | `    unguard(t.a, n);` | Releases the buffer. |
| 291 | `}` | Ends the function `test_touch`. |

### Functions `trial_check` and `kernel_named` (lines 292 to 310)

| Line | Source | Explanation |
|---:|---|---|
| 293 | `static void trial_check(int ok, const char *what, size_t bytes)` | Starts the function `trial_check`. It works like `check` (line 161), for a check that belongs to no single kernel. |
| 294 | `{` | Opens the body of `trial_check`. |
| 295 | `    printf("trial,%s,%zu,%s\n", what, bytes, ok ? "pass" : "FAIL");` | Prints one row with four fields: the word `trial`, the name of the check (`what`), a number of bytes, and `pass` or `FAIL`. |
| 296 | `    if (!ok)` | When the check failed ... |
| 297 | `        failures++;` | ... adds 1 to `failures`. The self-test continues. |
| 298 | `}` | Ends the function `trial_check`. |
| 300 | `static int kernel_named(const char *name)` | Starts the function `kernel_named`. It returns the index of the kernel with this name in the table `kernels[]`. |
| 301 | `{` | Opens the body of `kernel_named`. |
| 302 | `    int k = 0;` | `k`: the index, from 0. |
| 303 | `    while (k < K_COUNT && strcmp(name, kernels[k].name))` | Goes through the table until the name is equal (`strcmp` returns 0 then) or the table ends. `K_COUNT` is the number of entries of `kernels[]`. |
| 304 | `        k++;` | Goes to the next entry. |
| 305 | `    if (k == K_COUNT) {` | Tests whether the table ended. Then no kernel has the name. |
| 306 | `        fprintf(stderr, "selftest: no kernel %s\n", name);` | Prints the message `selftest: no kernel` with the name to the error output. |
| 307 | `        exit(2);` | Ends the process with exit status 2. |
| 308 | `    }` | Ends the `if` of line 305. |
| 309 | `    return k;` | Returns the index. |
| 310 | `}` | Ends the function `kernel_named`. |

### Function `test_trial`: the records of one trial (trial mode) (lines 311 to 382)

| Line | Source | Explanation |
|---:|---|---|
| 312 | `/* The trial mode on a guarded buffer of 1 MiB whose words all hold w.v. */` | Comment: `test_trial` runs the trial mode on a guarded buffer of 1 MiB whose words all hold the value `w.v`. |
| 313 | `static void test_trial(void)` | Starts the function `test_trial`. It runs trials on a guarded buffer of 1 MiB through `run_trial` of the runner source, the function that the trial mode uses. A trial is a list of timed windows that run one directly after the other. What it proves: `timed_sequence` writes consistent window records, and the sink check can pass and can fail. What it cannot prove: that the byte count of a window equals the bytes that the kernel read. The checks test multiples, not the number of kernel calls. It also cannot prove anything about the timing code of the interval mode. That code is the function `worker` of the runner source, and no check of this file runs it. |
| 314 | `{` | Opens the body of `test_trial`. |
| 315 | `    size_t bytes = 1UL << 20, n = bytes / 8;` | `bytes`: the buffer size, 1 MiB (1048576 bytes). `n`: the same size in words (131072 words of 8 bytes). |
| 316 | `    int oldread = kernel_named("oldread"), rd = kernel_named("read"), asmread = kernel_named("asmread");` | The indexes of three kernels in `kernels[]`: `oldread` (the old read kernel), `read` (the new read kernel, kept in the variable `rd`) and `asmread`. |
| 317 | `    struct trial p = { .nwin = 3, .win_ms = 12, .count = CS_CLOSED, .bins = 1,` | `p`: the plan of the trial (`struct trial` of the runner source). `.nwin = 3`: 3 target windows. `.win_ms = 12`: the requested duration of each target window is 12 ms. A window ends at the first clock read at or after its requested duration. So it lasts at least that long. `.count = CS_CLOSED`: the trial opens no counter group. `.bins = 1`: bins are on. |
| 318 | `                       .prev = { asmread, bytes, 4 }, .pfx = { oldread, bytes, 8 },` | Continues the plan. `.prev`: 1 window of previous activity, `asmread` on 1 MiB for 4 ms. `.pfx`: 4 prefix windows of `oldread` on 1 MiB, 8 ms for all four, so 2 ms each. |
| 319 | `                       .pred = { rd, 65536, 3 }, .tgt = { oldread, bytes, 0 } };` | Ends the plan. `.pred`: 1 predecessor window, `read` on 65536 B for 3 ms. `.tgt`: the target windows run `oldread` on 1 MiB. The 0 is the time field. A target window does not use it: its time is `win_ms`. |
| 320 | `    struct win win[9];` | `win`: the 9 window records of the trial. A window record holds the plan and the result of one window. |
| 321 | `    struct bin bin[9]; /* 3 target windows, window_bins() = 3 each */` | `bin`: storage for 9 bins. Comment: there are 3 target windows, and `window_bins` gives room for 3 bins in each. |
| 322 | `    struct trec r = { .win = win, .nw = trial_windows(&p) };` | `r`: the record of the trial (`struct trec` of the runner source). It points to the window records. `nw` is the number of windows that `trial_windows` of the runner source computes from the plan. |
| 323 | `    struct tw w;` | `w`: the worker record (`struct tw` of the runner source). It holds the state of the thread that runs the trials: the buffer, the counter group and the trace. In the self-test the main thread runs the trials. |
| 324 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum that an old read kernel returns. |
| 325 | `    int whole = 1, groups = 1, lasts = 1, order = 1, bins_ok = 1;` | Five result flags, one per check of the loop of lines 338 to 352. Each starts as 1. The value 1 stands for passed. |
| 327 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 328 | `    w.t.group_fd = -1;` | `group_fd = -1`: the worker has no counter group. |
| 329 | `    w.v = 0x9E3779B97F4A7C15ULL * 7;` | `w.v`: the value that every word of the buffer gets. `run_trial` computes the expected sum of an old read as `w.v` times the number of words. |
| 330 | `    w.t.a = guarded(n);` | The buffer of the worker: a guarded buffer of 1 MiB. |
| 331 | `    for (size_t i = 0; i < n; i++)` | Loop over all words of the buffer. |
| 332 | `        w.t.a[i] = w.v;` | Every word of the buffer gets the same value `w.v`. This is also the first write to the new buffer, outside every timed window. |
| 334 | `    trial_check(r.nw == 9 && window_bins(&p) == 3, "prev 1 + prefix 4 + pred 1 + target 3 windows", bytes);` | First check: the plan gives 9 windows (1 + 4 + 1 + 3), and a target window has room for 3 bins: 1 bin for the 10 ms that end inside the 12 ms, 1 bin for the end of the window, and 1 spare bin. |
| 335 | `    set_windows(&p, win, bin);` | `set_windows` of the runner source fills the plan fields of the 9 window records: kernel, range size, passes between two clock reads, duration and bin storage. |
| 336 | `    printf("call,trial,%zu\n", bytes);` | Prints the line `call,trial,1048576` before the trial runs. |
| 337 | `    run_trial(&w, &p, &r, &sink);` | `run_trial` runs the 9 windows through `timed_sequence` and then sets `r.sink_ok`. In `timed_sequence` each window reads the clock at its start and again after each group of passes. The window ends at the first clock read at or after its duration. |
| 338 | `    for (int i = 0; i < r.nw; i++) {` | Loop over the 9 window records after the trial. |
| 339 | `        const struct win *x = &win[i];` | `x`: the record of window `i`. |
| 340 | `        whole &= x->bytes > 0 && x->bytes % x->size == 0;` | `whole`: the window counted more than 0 bytes, and a multiple of its range size. |
| 341 | `        groups &= x->bytes % CHECK_BYTES == 0; /* every size here divides 8 MiB */` | `groups`: the bytes are a multiple of 8 MiB (`CHECK_BYTES`). The window loop reads the clock after each 8 MiB. Comment: every range size of this plan divides 8 MiB. |
| 342 | `        lasts &= x->t_end - x->t_start >= x->dur_ns;` | `lasts`: end time minus start time is at least the requested duration. All three values are in ns. |
| 343 | `        order &= x->t_end > x->t_start && (i == 0 \|\| x->t_start >= win[i - 1].t_end);` | `order`: the end is later than the start, and the start is not earlier than the end of the window before. |
| 344 | `        if (x->phase == PH_TARGET) {` | Branch for a target window. |
| 345 | `            bins_ok &= x->nbin >= 1 && x->nbin <= x->bin_cap && x->bin[x->nbin - 1].bytes == x->bytes &&` | `bins_ok`, target window: it has 1 to `bin_cap` bins, and the last bin holds the bytes of the window ... |
| 346 | `                       x->bin[x->nbin - 1].t_end == x->t_end;` | ... and the end time of the window. |
| 347 | `            for (int b = 1; b < x->nbin; b++)` | Loop over the bins after the first one. |
| 348 | `                bins_ok &= x->bin[b].t_end > x->bin[b - 1].t_end && x->bin[b].bytes > x->bin[b - 1].bytes;` | Time and bytes must rise from bin to bin. |
| 349 | `        } else {` | Branch for every other window. |
| 350 | `            bins_ok &= x->nbin == 0;` | `bins_ok`, other window: it has no bin. |
| 351 | `        }` | Ends the `if` of line 344. |
| 352 | `    }` | Ends the loop of line 338. |
| 353 | `    trial_check(whole, "every window holds whole passes and more than 0 bytes", bytes);` | Prints the result of `whole`, the first of the five results of the loop. |
| 354 | `    trial_check(groups, "every window holds a multiple of 8 MiB (clock read after 8 MiB)", bytes);` | Prints the result of `groups`. |
| 355 | `    trial_check(lasts, "every window lasts at least its requested duration", bytes);` | Prints the result of `lasts`. |
| 356 | `    trial_check(order, "timestamps do not go back from window to window", bytes);` | Prints the result of `order`. |
| 357 | `    trial_check(bins_ok, "the last bin of a target window ends the window and holds its bytes", bytes);` | Prints the result of `bins_ok`. |
| 358 | `    trial_check(r.sink_ok == 1, "sink holds the sum after a trial that ends in old read", bytes);` | One more check: `r.sink_ok` is 1. So after a trial that ends with `oldread`, the sink holds the expected sum. |
| 360 | `    p.tgt.k = rd;` | Second trial: the target kernel is now `read`, the new read kernel. |
| 361 | `    set_windows(&p, win, bin);` | Fills the window records again from the changed plan. |
| 362 | `    run_trial(&w, &p, &r, &sink);` | Runs the second trial. |
| 363 | `    trial_check(r.sink_ok == 1, "sink holds the sum of the last old read when the target is new read", bytes);` | The last old read is now a prefix window. `sink_ok` must still be 1. So the `read` windows after it left the sink unchanged. |
| 365 | `    p.pfx.k = asmread;` | Third trial: the prefix kernel is now `asmread` too. So the trial holds no old read. |
| 366 | `    set_windows(&p, win, bin);` | Fills the window records again. |
| 367 | `    run_trial(&w, &p, &r, &sink);` | Runs the third trial. |
| 368 | `    trial_check(r.sink_ok == -1, "sink check is NA for a trial without old read", bytes);` | `sink_ok` must be -1. This value stands for not applicable. |
| 370 | `    /* The sink check must be able to fail: one changed word changes the sum. */` | Comment: the sink check must be able to fail. One changed word changes the sum. |
| 371 | `    p.tgt.k = oldread;` | Fourth trial: the target is `oldread` again. |
| 372 | `    w.t.a[n - 1] ^= 1;` | Flips the lowest bit of the last word of the buffer. The sum now differs from the expected sum by 1. |
| 373 | `    set_windows(&p, win, bin);` | Fills the window records again. |
| 374 | `    run_trial(&w, &p, &r, &sink);` | Runs the fourth trial. |
| 375 | `    trial_check(r.sink_ok == 0, "sink check fails after one word of the buffer is changed", bytes);` | So `sink_ok` must be 0. This proves that the sink check can fail, and that `oldread` reads the last word of its range. |
| 377 | `    struct counts c[3] = { { .enabled = 0, .running = 0 }, { .enabled = 100, .running = 100 }, { .enabled = 200, .running = 150 } };` | `c`: three counter readings that are written here. They stand for the borders of two target windows. `enabled` and `running` are the times in ns for which the counter group was enabled and for which it ran. In target window 1 (the second one, the count starts at 0) the counters ran 50 ns of 100 ns. |
| 378 | `    trial_check(first_multiplexed(c, 2) == 1, "running time below enabled time is found in target window 1", 0);` | Checks `first_multiplexed` of the runner source on the three readings. It must return 1: the index of the first target window whose counters ran for less time than they were enabled. |
| 379 | `    c[2].running = 200;` | Makes the running time of target window 1 equal to its enabled time. |
| 380 | `    trial_check(first_multiplexed(c, 2) == -1, "equal running and enabled time is not called multiplexed", 0);` | With equal times `first_multiplexed` must return -1. |
| 381 | `    unguard(w.t.a, n);` | Releases the buffer. |
| 382 | `}` | Ends the function `test_trial`. |

### Function `test_trial_hot`: the same checks with the option `--hot-copy` (lines 383 to 443)

| Line | Source | Explanation |
|---:|---|---|
| 384 | `/* bwx10+ */` | Comment: the marker `bwx10+`. The text up to the line with `bwx10-` (line 553) was added for bwx10. |
| 385 | `/* The window checks of test_trial() with --hot-copy: run_trial() then calls` | Comment: `test_trial_hot` holds the window checks of `test_trial` with the option `--hot-copy`. `run_trial` then calls ... |
| 386 | ` * timed_sequence_hot(). */` | Comment: ... `timed_sequence_hot`. |
| 387 | `static void test_trial_hot(void)` | Starts the function `test_trial_hot`. It holds the plan and the window checks of `test_trial`, with `plan.hot_copy = 1`. `run_trial` then calls `timed_sequence_hot` in place of `timed_sequence`. What it proves: `timed_sequence_hot` writes consistent window records too, and it leaves the plan fields of each record unchanged. `--hot-copy` is an option of the trial mode only. So this check says nothing about the interval mode. |
| 388 | `{` | Opens the body of `test_trial_hot`. |
| 389 | `    size_t bytes = 1UL << 20, n = bytes / 8;` | `bytes`: the buffer size, 1 MiB. `n`: the same size in words. |
| 390 | `    int oldread = kernel_named("oldread"), rd = kernel_named("read"), asmread = kernel_named("asmread");` | The indexes of the kernels `oldread`, `read` (in `rd`) and `asmread`, as in line 316. |
| 391 | `    struct trial p = { .nwin = 3, .win_ms = 12, .count = CS_CLOSED, .bins = 1,` | `p`: the same plan as in `test_trial` (lines 317 to 319): 3 target windows of 12 ms, no counters, bins on. |
| 392 | `                       .prev = { asmread, bytes, 4 }, .pfx = { oldread, bytes, 8 },` | Continues the plan: 1 window of `asmread` for 4 ms, and 4 prefix windows of `oldread` with 2 ms each. |
| 393 | `                       .pred = { rd, 65536, 3 }, .tgt = { oldread, bytes, 0 } };` | Ends the plan: 1 predecessor window of `read` on 65536 B for 3 ms, and `oldread` as the target kernel. |
| 394 | `    struct win win[9], win0[9];` | `win`: the 9 window records of the trial. `win0`: a second set of the 9 records. The trial does not use it. It keeps the plan fields for the comparison of lines 415 to 416. |
| 395 | `    struct bin bin[9];` | `bin`: storage for 9 bins. |
| 396 | `    struct trec r = { .win = win, .nw = trial_windows(&p) };` | `r`: the record of the trial, with the number of windows from `trial_windows`. |
| 397 | `    struct tw w;` | `w`: the worker record. |
| 398 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum of an old read kernel. |
| 399 | `    int whole = 1, groups = 1, lasts = 1, order = 1, bins_ok = 1, kept = 1;` | Six result flags: the five of `test_trial` and `kept`. |
| 401 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 402 | `    w.t.group_fd = -1;` | `group_fd = -1`: the worker has no counter group. |
| 403 | `    w.v = 0x9E3779B97F4A7C15ULL * 11;` | `w.v`: the value of every word of the buffer. It differs from the value of `test_trial`. |
| 404 | `    w.t.a = guarded(n);` | The buffer of the worker: a guarded buffer of 1 MiB. |
| 405 | `    for (size_t i = 0; i < n; i++)` | Loop over all words of the buffer. |
| 406 | `        w.t.a[i] = w.v;` | Every word gets the value `w.v`. |
| 408 | `    plan.hot_copy = 1;` | Sets the global switch of the option `--hot-copy`. With it `run_trial` calls `timed_sequence_hot`. |
| 409 | `    set_windows(&p, win, bin);` | Fills `win` from the plan. |
| 410 | `    set_windows(&p, win0, bin);` | Fills `win0` from the same plan. |
| 411 | `    printf("call,trial_hot,%zu\n", bytes);` | Prints the line `call,trial_hot,1048576` before the trial runs. |
| 412 | `    run_trial(&w, &p, &r, &sink);` | Runs the trial on `win`. |
| 413 | `    for (int i = 0; i < r.nw; i++) {` | Loop over the 9 window records after the trial. |
| 414 | `        const struct win *x = &win[i], *x0 = &win0[i];` | `x`: the record of window `i` in `win`. `x0`: the same record in `win0`. |
| 415 | `        kept &= x->k == x0->k && x->phase == x0->phase && x->widx == x0->widx && x->size == x0->size &&` | `kept`: after the trial, the eight plan fields of the record in `win` equal those in `win0`. This line compares the kernel, the phase, the window index and the range size ... |
| 416 | `                x->passes == x0->passes && x->dur_ns == x0->dur_ns && x->bin == x0->bin && x->bin_cap == x0->bin_cap;` | ... and the passes between two clock reads, the duration, the bin storage and the bin capacity. |
| 417 | `        whole &= x->bytes > 0 && x->bytes % x->size == 0;` | `whole`: more than 0 bytes, and a multiple of the range size (line 340). |
| 418 | `        groups &= x->bytes % CHECK_BYTES == 0;` | `groups`: the bytes are a multiple of 8 MiB (line 341). |
| 419 | `        lasts &= x->t_end - x->t_start >= x->dur_ns;` | `lasts`: the window lasted at least its requested duration (line 342). |
| 420 | `        order &= x->t_end > x->t_start && (i == 0 \|\| x->t_start >= win[i - 1].t_end);` | `order`: the times do not go back (line 343). |
| 421 | `        if (x->phase == PH_TARGET) {` | Branch for a target window. |
| 422 | `            bins_ok &= x->nbin >= 1 && x->nbin <= x->bin_cap && x->bin[x->nbin - 1].bytes == x->bytes &&` | `bins_ok`, target window: 1 to `bin_cap` bins, and the last bin holds the bytes of the window ... |
| 423 | `                       x->bin[x->nbin - 1].t_end == x->t_end;` | ... and the end time of the window. |
| 424 | `            for (int b = 1; b < x->nbin; b++)` | Loop over the bins after the first one. |
| 425 | `                bins_ok &= x->bin[b].t_end > x->bin[b - 1].t_end && x->bin[b].bytes > x->bin[b - 1].bytes;` | Time and bytes must rise from bin to bin. |
| 426 | `        } else {` | Branch for every other window. |
| 427 | `            bins_ok &= x->nbin == 0;` | `bins_ok`, other window: it has no bin. |
| 428 | `        }` | Ends the `if` of line 421. |
| 429 | `    }` | Ends the loop of line 413. |
| 430 | `    trial_check(kept, "hot copy: the plan fields of every window record are unchanged", bytes);` | Prints the result of `kept`. Every check name of this function starts with `hot copy:`. |
| 431 | `    trial_check(whole, "hot copy: every window holds whole passes and more than 0 bytes", bytes);` | Prints the result of `whole`. |
| 432 | `    trial_check(groups, "hot copy: every window holds a multiple of 8 MiB (clock read after 8 MiB)", bytes);` | Prints the result of `groups`. |
| 433 | `    trial_check(lasts, "hot copy: every window lasts at least its requested duration", bytes);` | Prints the result of `lasts`. |
| 434 | `    trial_check(order, "hot copy: timestamps do not go back from window to window", bytes);` | Prints the result of `order`. |
| 435 | `    trial_check(bins_ok, "hot copy: the last bin of a target window ends the window and holds its bytes", bytes);` | Prints the result of `bins_ok`. |
| 436 | `    trial_check(r.sink_ok == 1, "hot copy: sink holds the sum after a trial that ends in old read", bytes);` | The sink check: `r.sink_ok` must be 1 after this trial, which ends with `oldread`. |
| 437 | `    w.t.a[n - 1] ^= 1;` | Flips the lowest bit of the last word of the buffer. |
| 438 | `    set_windows(&p, win, bin);` | Fills the window records again. |
| 439 | `    run_trial(&w, &p, &r, &sink);` | Runs the trial again. |
| 440 | `    trial_check(r.sink_ok == 0, "hot copy: sink check fails after one word of the buffer is changed", bytes);` | The sink check must fail now: `r.sink_ok` must be 0. |
| 441 | `    plan.hot_copy = 0;` | Sets `plan.hot_copy` back to 0. |
| 442 | `    unguard(w.t.a, n);` | Releases the buffer. |
| 443 | `}` | Ends the function `test_trial_hot`. |

### `on_touch`, `struct toucher` and `toucher`: the helpers of `test_hot_touch` (lines 444 to 487)

| Line | Source | Explanation |
|---:|---|---|
| 445 | `static uint8_t *touch_page; /* the page that holds the window record of test_hot_touch */` | `touch_page`: the address of the page that holds the window record of `test_hot_touch`. |
| 446 | `static volatile int touch_faults;` | `touch_faults`: the count of the faults in that page. It is `volatile`: a signal handler changes it. |
| 448 | `/* A fault in the page of the window record: count it and make the page` | Comment: on a fault in the page of the window record the handler counts the fault and makes the page ... |
| 449 | ` * usable, so the access runs again. Any other fault ends the process. */` | Comment: ... usable, so the access runs again. Any other fault ends the process. |
| 450 | `static void on_touch(int sig, siginfo_t *si, void *ctx)` | Starts the function `on_touch`, the `SIGSEGV` handler of `test_hot_touch`. |
| 451 | `{` | Opens the body of `on_touch`. |
| 452 | `    uintptr_t at = (uintptr_t)si->si_addr;` | `at`: the address of the faulting access. |
| 453 | `    (void)ctx;` | Marks the argument `ctx` as not used. |
| 454 | `    if (at < (uintptr_t)touch_page \|\| at >= (uintptr_t)touch_page + (uintptr_t)page_bytes) {` | Tests whether the address lies outside the page of the window record. |
| 455 | `        signal(sig, SIG_DFL);` | A fault at any other address: the handler sets `SIGSEGV` back to its default action. |
| 456 | `        return;` | After the return the access faults again and ends the process. |
| 457 | `    }` | Ends the `if` of line 454. |
| 458 | `    touch_faults++;` | A fault inside this page: the handler adds 1 to the count ... |
| 459 | `    mprotect(touch_page, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | ... and makes the page readable and writable. After the return the access runs again and succeeds. |
| 460 | `}` | Ends the function `on_touch`. |
| 462 | `struct toucher {` | `struct toucher`: the data of the second thread of `test_hot_touch`. |
| 463 | `    struct tw *w;` | `w`: the worker record whose trace the second thread reads. |
| 464 | `    int found;              /* the first kernel call of the window was seen in the trace */` | `found`: the flag that the second thread sets when it has seen the first kernel call of the window in the trace. |
| 465 | `    int64_t t_none, t_done; /* after the page became PROT_NONE; after it became usable again */` | Two clock values in ns. `t_none`: read after the page became `PROT_NONE`. `t_done`: read after the page became usable again. |
| 466 | `};` | Ends the definition of `struct toucher`. |
| 468 | `static void *toucher(void *arg)` | Starts the function `toucher`, the body of the second thread. |
| 469 | `{` | Opens the body of `toucher`. |
| 470 | `    struct toucher *h = arg;` | `h`: the data of the thread, passed through `arg`. |
| 471 | `    struct timespec ms20 = { 0, 20000000L };` | `ms20`: a time of 0 s and 20000000 ns, which is 20 ms. |
| 472 | `    int64_t limit = now_ns() + 5000000000L;` | `limit`: the clock value 5 s after this moment. `now_ns` of the runner source reads the clock `CLOCK_MONOTONIC` in ns. |
| 473 | `    while (!h->found && now_ns() < limit) {` | Reads the trace of the worker again and again, for at most 5 s, until it holds the event. The loop does not sleep between two passes. |
| 474 | `        long nlog = *(volatile long *)&h->w->nlog;` | `nlog`: the number of events in the trace at this moment. The `volatile` cast makes the compiler read the number from memory in every pass. The other thread changes it. |
| 475 | `        for (long i = 0; i < nlog; i++)` | Loop over the events of the trace. |
| 476 | `            if (h->w->log[i].ev == EV_KERNEL_FIRST)` | Looks for the event `EV_KERNEL_FIRST`. The worker writes this event at the first kernel call of a window. |
| 477 | `                h->found = 1;` | The event was found. |
| 478 | `    }` | Ends the loop of line 473. |
| 479 | `    if (!h->found)` | If the event did not appear within 5 s ... |
| 480 | `        return NULL;` | ... the thread returns and changes nothing. |
| 481 | `    mprotect(touch_page, (size_t)page_bytes, PROT_NONE);` | Makes the page of the window record `PROT_NONE` ... |
| 482 | `    h->t_none = now_ns();` | ... and reads the clock (`t_none`). |
| 483 | `    nanosleep(&ms20, NULL);` | Sleeps 20 ms. |
| 484 | `    mprotect(touch_page, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | Makes the page readable and writable again ... |
| 485 | `    h->t_done = now_ns();` | ... and reads the clock (`t_done`). |
| 486 | `    return NULL;` | Ends the thread. |
| 487 | `}` | Ends the function `toucher`. |

### Functions `hot_touch_run` and `test_hot_touch` (lines 488 to 551)

| Line | Source | Explanation |
|---:|---|---|
| 489 | `/* One target window of 200 ms of asmread on 1 MiB, with or without` | Comment: `hot_touch_run` runs one target window of 200 ms of `asmread` on 1 MiB, with or without ... |
| 490 | ` * --hot-copy. faults: faults in the page of the window record. inside: the` | Comment: ... the option `--hot-copy`. The result `faults` is the number of faults in the page of the window record. The result `inside` says whether the ... |
| 491 | ` * time in which the page was PROT_NONE lies between the start clock read and` | Comment: ... time in which the page was `PROT_NONE` lies between the start clock read and ... |
| 492 | ` * the end clock read of the window. */` | Comment: ... the end clock read of the window. |
| 493 | `static void hot_touch_run(int hot, int *faults, int *inside)` | Starts the function `hot_touch_run`. `hot` selects the function under test: 0 is `timed_sequence`, 1 is `timed_sequence_hot`. Result `faults`: the number of faults in the page of the record. Result `inside`: 1 when the `PROT_NONE` time lay between the start clock read and the end clock read of the window. |
| 494 | `{` | Opens the body of `hot_touch_run`. |
| 495 | `    size_t bytes = 1UL << 20, n = bytes / 8, wn = (size_t)page_bytes / 8;` | `bytes` and `n`: the buffer size, 1 MiB, in bytes and in words. `wn`: the number of words of one page, for the page of the window record. |
| 496 | `    struct trial p = { .nwin = 1, .win_ms = 200, .count = CS_CLOSED, .bins = 0,` | `p`: the plan. One trial with a single target window of 200 ms. No counters (`CS_CLOSED`), no bins. |
| 497 | `                       .prev = { -1, 0, 0 }, .pfx = { -1, 0, 0 }, .pred = { -1, 0, 0 },` | Continues the plan: no other window. A kernel index of -1 means that the part is absent. |
| 498 | `                       .tgt = { kernel_named("asmread"), bytes, 0 } };` | Ends the plan: the target window runs `asmread` on 1 MiB. |
| 499 | `    struct win *win = (struct win *)guarded(wn);` | The window record `win` lies alone in a guarded page. So the page can be made `PROT_NONE` without an effect on other data. |
| 500 | `    struct trec r = { .win = win, .nw = 1 };` | `r`: the record of the trial, with 1 window. |
| 501 | `    struct tw w;` | `w`: the worker record. |
| 502 | `    struct toucher h = { .w = &w };` | `h`: the data of the second thread. It points to the worker record. |
| 503 | `    struct sigaction sa, old;` | `sa`: the new setting for `SIGSEGV`. `old`: the setting from before. |
| 504 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This trial runs no old read. |
| 505 | `    pthread_t tid;` | `tid`: the identifier of the second thread. |
| 507 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 508 | `    w.t.group_fd = -1;` | `group_fd = -1`: the worker has no counter group. |
| 509 | `    w.v = 0x9E3779B97F4A7C15ULL * 13;` | `w.v`: the value of every word of the buffer. |
| 510 | `    w.t.a = guarded(n);` | The buffer of the worker: a guarded buffer of 1 MiB. |
| 511 | `    for (size_t i = 0; i < n; i++)` | Loop over all words of the buffer. |
| 512 | `        w.t.a[i] = w.v;` | Every word gets the value `w.v`. |
| 513 | `    w.log = calloc(TRACE_CAP, sizeof *w.log); /* the trace shows the second thread that the window runs */` | Allocates a trace (`w.log`) with room for `TRACE_CAP` events. The runner source sets `TRACE_CAP` to 1048576 events. `run_trial` writes events to the trace, and the second thread reads them. Comment: the trace shows the second thread that the window runs. |
| 514 | `    w.cur_phase = -1;` | `cur_phase = -1` makes the first kernel call write the event `EV_KERNEL_FIRST`. |
| 515 | `    if (!w.log) {` | Tests whether the allocation failed. |
| 516 | `        perror("calloc");` | On failure: prints the word `calloc` and the reason. |
| 517 | `        exit(2);` | On failure: the process ends with exit status 2. |
| 518 | `    }` | Ends the `if` of line 515. |
| 519 | `    set_windows(&p, win, NULL);` | Fills the window record from the plan. `NULL`: there is no bin storage. |
| 520 | `    touch_page = (uint8_t *)win;` | Stores the address of the page of the record for the handler and for the second thread. |
| 521 | `    touch_faults = 0;` | Sets the fault count to 0. |
| 522 | `    memset(&sa, 0, sizeof sa);` | Sets every byte of `sa` to 0. |
| 523 | `    sa.sa_sigaction = on_touch;` | The handler is `on_touch`. |
| 524 | `    sa.sa_flags = SA_SIGINFO;` | The flag `SA_SIGINFO` makes Linux pass the fault address to the handler. |
| 525 | `    sigaction(SIGSEGV, &sa, &old);` | Installs `on_touch` for `SIGSEGV`. `old` keeps the setting from before. |
| 526 | `    plan.hot_copy = hot;` | Sets `plan.hot_copy` to `hot`. |
| 527 | `    printf("call,%s,%zu\n", hot ? "hot_touch_hot" : "hot_touch_plain", bytes);` | Prints the `call` line: `call,hot_touch_hot,1048576` or `call,hot_touch_plain,1048576`. |
| 528 | `    if (pthread_create(&tid, NULL, toucher, &h) != 0) {` | Starts the second thread with the function `toucher`. The self-test pins neither this thread nor the main thread to one CPU. |
| 529 | `        perror("pthread_create");` | On failure: prints the word `pthread_create` and the reason. |
| 530 | `        exit(2);` | On failure: the process ends with exit status 2. |
| 531 | `    }` | Ends the `if` of line 528. |
| 532 | `    run_trial(&w, &p, &r, &sink);` | Runs the trial in this thread. |
| 533 | `    pthread_join(tid, NULL);` | Waits for the second thread. |
| 534 | `    plan.hot_copy = 0;` | Sets `plan.hot_copy` back to 0. |
| 535 | `    sigaction(SIGSEGV, &old, NULL);` | Restores the `SIGSEGV` setting from before. |
| 536 | `    *faults = touch_faults;` | Result `faults`: the fault count. |
| 537 | `    *inside = h.found && h.t_none > win[0].t_start && h.t_done < win[0].t_end;` | `inside` is 1 when the event was found, `t_none` is later than the start clock read of the window, and `t_done` is earlier than its end clock read. |
| 538 | `    free(w.log);` | Releases the trace ... |
| 539 | `    unguard(w.t.a, n);` | ... the buffer ... |
| 540 | `    unguard((uint64_t *)win, wn);` | ... and the page of the record. |
| 541 | `}` | Ends the function `hot_touch_run`. |
| 543 | `static void test_hot_touch(void)` | Starts the function `test_hot_touch`. It runs `hot_touch_run` twice and makes three checks. What it proves: the machine code of `timed_sequence_hot` did not read or write the page of the record while it was `PROT_NONE` (20 ms). What it cannot prove: the same for the rest of the 200 ms window. |
| 544 | `{` | Opens the body of `test_hot_touch`. |
| 545 | `    int f_plain, in_plain, f_hot, in_hot;` | The four results: faults and `inside` of the plain run, faults and `inside` of the hot run. |
| 546 | `    hot_touch_run(0, &f_plain, &in_plain);` | First run, with `timed_sequence`. |
| 547 | `    hot_touch_run(1, &f_hot, &in_hot);` | Second run, with `timed_sequence_hot`. |
| 548 | `    trial_check(in_plain && in_hot, "hot touch: the 20 ms with the window record in a PROT_NONE page lie inside the window", 0);` | Check 1: in both runs the `PROT_NONE` time lay inside the window. |
| 549 | `    trial_check(f_plain >= 1, "hot touch: timed_sequence touches the window record between the first and the last pass", 0);` | Check 2: `timed_sequence` faulted at least once. It reads the record in every pass. So this run shows that the method can see a touch. |
| 550 | `    trial_check(f_hot == 0, "hot touch: timed_sequence_hot does not touch the window record between the first and the last pass", 0);` | Check 3: `timed_sequence_hot` did not fault. |
| 551 | `}` | Ends the function `test_hot_touch`. |

### Functions `map_lines` and `test_evict`: the evict step unmaps its memory (lines 552 to 582)

| Line | Source | Explanation |
|---:|---|---|
| 553 | `/* bwx10- */` | Comment: the marker `bwx10-`. It ends the block of text that was added for bwx10. |
| 554 | `/* bwx11+ */` | Comment: the marker `bwx11+`. The text up to the line with `bwx11-` (line 582) was added for bwx11. |
| 555 | `static long map_lines(void)` | Starts the function `map_lines`. It counts the lines of the file `/proc/self/maps`. Linux prints one line per memory mapping of the process in this file. |
| 556 | `{` | Opens the body of `map_lines`. |
| 557 | `    FILE *f = fopen("/proc/self/maps", "r");` | Opens the file for reading. |
| 558 | `    long n = 0;` | `n`: the count of lines. |
| 559 | `    int c;` | `c`: the character that was read last. |
| 560 | `    if (!f)` | If the file cannot be opened ... |
| 561 | `        return -1;` | ... the result is -1. |
| 562 | `    while ((c = getc(f)) != EOF)` | Reads the file character by character up to its end (`EOF`). |
| 563 | `        n += c == '\n';` | Adds 1 to `n` for every line end. |
| 564 | `    fclose(f);` | Closes the file. |
| 565 | `    return n;` | Returns the count. |
| 566 | `}` | Ends the function `map_lines`. |
| 568 | `static void test_evict(void)` | Starts the function `test_evict`. It checks the evict step of the trial mode (option `--evict-mb`) with 4 MiB. What it proves: the step returns no error, its second clock read is later than its first, and the number of mappings is the same as before. What it cannot prove: that the step removes the benchmark buffer from the caches. No check measures the content of a cache. |
| 569 | `{` | Opens the body of `test_evict`. |
| 570 | `    long before = (map_lines(), map_lines()), saved = evict_mb; /* the first call lets stdio take its memory */` | Calls `map_lines` twice and keeps the second count in `before`. The comma operator gives the value of the second call. The comment gives the reason: the first call lets the C library take its memory for file reading. `saved` keeps the value of the global `evict_mb`, the size of the evict step in MiB. |
| 571 | `    int bad;` | `bad`: the return value of the step. |
| 572 | `    evict_mb = 4;` | Sets the size of the step to 4 MiB. |
| 573 | `    evict_t[0] = evict_t[1] = 0;` | Sets the two clock values of the step to 0. |
| 574 | `    bad = evict_step();` | Calls `evict_step` of the runner source. That function maps 4 MiB, writes one word per 64 B line in two passes, and unmaps the range. It returns 0, or -1 on an error. |
| 575 | `    evict_mb = saved;` | Sets `evict_mb` back to its old value. |
| 576 | `    trial_check(bad == 0, "evict: the step with 4 MiB returns no error", 0);` | Check 1: the step returned no error. |
| 577 | `    trial_check(evict_t[0] > 0 && evict_t[1] > evict_t[0], "evict: the clock read after the step is later than the one before it", 0);` | Check 2: the first clock value is above 0, and the second one is later than the first. `evict_step` reads the clock before its `mmap` and after its `munmap`. |
| 578 | `    trial_check(before > 0 && map_lines() == before, "evict: the range is unmapped again", 0);` | Check 3: the first count is above 0, and a new count of the mappings equals it. So the range is unmapped again. |
| 579 | `    evict_t[0] = evict_t[1] = 0;` | Sets the two clock values back to 0. |
| 580 | `}` | Ends the function `test_evict`. |
| 582 | `/* bwx11- */` | Comment: the marker `bwx11-`. It ends the block of line 554. |

### Function `test_round5`: the 26 kernels of round 5 in `kernels[]` (lines 583 to 626)

| Line | Source | Explanation |
|---:|---|---|
| 583 | `/* bwx12+ */` | Comment: the marker `bwx12+`. The text up to the line with `bwx12-` (line 626) was added for bwx12. Two short blocks inside it were added for bwx13 (lines 617 to 619 and lines 621 to 623). |
| 584 | `/* Every kernel of round 5 stands in kernels[] exactly once, with the kind` | Comment: every kernel of round 5 must stand in `kernels[]` exactly once, with the kind ... |
| 585 | ` * that its name says. */` | Comment: ... that its name says. |
| 586 | `static void test_round5(void)` | Starts the function `test_round5`. `want` lists the 26 kernel names of round 5, each with the kind that its name says: 20 read, 4 write, 2 copy. What it proves: each name stands exactly once in `kernels[]` with that kind. In this file it does not check the number of entries: the line of that check is not compiled (lines 618 to 622), and `test_rand` checks the number 58 (line 649). The reason for the name check: the loop of `selftest` chooses the checks by the kind in `kernels[]`. A wrong kind gives a kernel the wrong checks. What it cannot prove: that the function behind a name holds the instructions that the name says, for example 256 nop in `read_nop256`. By the file comment the objdump listing is the evidence (lines 44 to 48). The name check covers no kernel of bwx11 or older, and none of the three `rand` kernels. |
| 587 | `{` | Opens the body of `test_round5`. |
| 588 | `    static const struct {` | Starts the table `want`. It is constant and exists once for the whole program. |
| 589 | `        const char *name;` | `name`: the name of a kernel. |
| 590 | `        enum ktype type;` | `type`: the kind that the kernel must have in `kernels[]`. |
| 591 | `    } want[] = {` | Ends the type of one entry. The entries follow. |
| 592 | `        { "read_nop48", T_READ }, { "read_nop56", T_READ }, { "read_nop72", T_READ }, { "read_nop80", T_READ },` | Four read kernels with nop instructions: `read_nop48`, `read_nop56`, `read_nop72`, `read_nop80`. By the file comment of the runner source they are the `asmread` loop with that many nop after its 8 loads. The kind is `T_READ`, a read kernel that returns nothing. |
| 593 | `        { "read_nop88", T_READ }, { "read_nop112", T_READ }, { "read_nop160", T_READ }, { "read_nop192", T_READ },` | Four more of the same family: `read_nop88`, `read_nop112`, `read_nop160`, `read_nop192`. |
| 594 | `        { "read_nop256", T_READ },` | The last one of this family, `read_nop256`. |
| 595 | `        { "read_dadd2", T_READ }, { "read_dadd4", T_READ }, { "read_dadd8", T_READ }, { "read_dadd16", T_READ },` | Four read kernels with vector adds: `read_dadd2`, `read_dadd4`, `read_dadd8`, `read_dadd16`. By the file comment of the runner source they are the `asmread` loop with 2, 4, 8 or 16 vector adds after its 8 loads. Each add takes a register that the same loop pass loaded. |
| 596 | `        { "read_iadd16", T_READ },` | `read_iadd16`: the `asmread` loop with 16 vector adds that take no loaded register. By the same comment it is the control of `read_dadd16`. |
| 597 | `        { "read_sp24", T_READ }, { "read_sp32", T_READ }, { "read_sp40", T_READ }, { "read_sp48", T_READ },` | Four read kernels `read_sp24`, `read_sp32`, `read_sp40`, `read_sp48`. By the same comment they are the `read_sparse` loop (128 B and 4 loads per loop pass) with that many nop in place of 9. |
| 598 | `        { "read_sp56", T_READ },` | `read_sp56`, the last one of this family. |
| 599 | `        { "read_1pl_nop96", T_READ },` | `read_1pl_nop96`: by the same comment the `read_1pl` loop with 96 nop after its 4 loads. |
| 600 | `        { "write_nop32", T_WRITE }, { "write_nop96", T_WRITE }, { "write_nop128", T_WRITE }, { "write_nop256", T_WRITE },` | The four write kernels `write_nop32`, `write_nop96`, `write_nop128`, `write_nop256`, with the kind `T_WRITE`. By the same comment they are the `asmwrite` loop with that many nop after its 8 stores. |
| 601 | `        { "copy_nop96", T_COPY }, { "copy_nop192", T_COPY },` | The two copy kernels `copy_nop96` and `copy_nop192`, with the kind `T_COPY`. By the same comment they are the `asmcopy` loop with that many nop after its 8 stores. |
| 602 | `    };` | Ends the table `want`. |
| 603 | `    int ok = 1;` | `ok`: the result of the name check. 1 means passed. |
| 604 | `    for (size_t i = 0; i < sizeof want / sizeof want[0]; i++) {` | Loop over the entries of `want`. `sizeof want / sizeof want[0]` is the number of entries. |
| 605 | `        int found = 0, kind = 1;` | `found`: how many entries of `kernels[]` have the wanted name. `kind`: 1 as long as each of them has the wanted kind. |
| 606 | `        for (int k = 0; k < K_COUNT; k++)` | Loop over all entries of `kernels[]`. |
| 607 | `            if (!strcmp(want[i].name, kernels[k].name)) {` | Tests whether the names are equal (`strcmp` returns 0). |
| 608 | `                found++;` | Counts the entry. |
| 609 | `                kind &= kernels[k].type == want[i].type;` | Compares its kind with the wanted kind. |
| 610 | `            }` | Ends the `if` of line 607. |
| 611 | `        if (found != 1 \|\| !kind) {` | A name that is missing, that stands twice or more, or that has another kind ... |
| 612 | `            printf("# round 5: kernel %s stands %d times in kernels[]%s\n", want[i].name, found, kind ? "" : ", with another kind");` | ... prints a line that starts with `#`: the kernel name, how many times it stands in `kernels[]`, and the words `, with another kind` when a kind differs. |
| 613 | `            ok = 0;` | Then the name check fails. |
| 614 | `        }` | Ends the `if` of line 611. |
| 615 | `    }` | Ends the loop of line 604. |
| 616 | `    trial_check(ok, "round 5: each of the 26 new kernels stands once in kernels[] with its kind", 0);` | Prints the result row of the name check. Its check name starts with `round 5: each of the 26 new kernels`. |
| 617 | `/* bwx13+ */` | Comment: the marker `bwx13+`. The next line was added for bwx13. |
| 618 | `#if 0` | `#if 0`: the compiler leaves out every line up to the `#endif` of line 622. So the check of line 620 is not compiled in `bwx13`. |
| 619 | `/* bwx13- */` | Comment: the marker `bwx13-` ends the addition. The line after it is old text of `bwx12_selftest.c`. |
| 620 | `    trial_check(K_COUNT == 55, "round 5: kernels[] has 55 entries (29 of bwx11 and 26 new)", 0);` | Not compiled: this line stands between the `#if 0` of line 618 and the `#endif` of line 622. In `bwx12_selftest.c` it is a second check: `kernels[]` must have 55 entries, the 29 kernels of bwx11 and the 26 new ones. The table of `bwx13.c` has 58 entries, so this check would fail. `test_rand` checks the number 58 (line 649). The self-test output of the CRB build holds no row with the name of this check [Ref1]. |
| 621 | `/* bwx13+ */` | Comment: the marker `bwx13+`. The next line was added for bwx13. |
| 622 | `#endif` | `#endif`: ends the range that the `#if 0` of line 618 left out. |
| 623 | `/* bwx13- */` | Comment: the marker `bwx13-` ends the addition. |
| 624 | `}` | Ends the function `test_round5`. |
| 626 | `/* bwx12- */` | Comment: the marker `bwx12-`. It ends the block of line 583. |

### Function `test_rand`: the names in `kernels[]` and the C model of the block order (lines 627 to 685)

| Line | Source | Explanation |
|---:|---|---|
| 627 | `/* bwx13+ */` | Comment: the marker `bwx13+`. The text up to the line with `bwx13-` (line 744) was added for bwx13. |
| 628 | `/* The checks of rand_nop0, rand_nop96 and rand_nop256 (see the top of this file). */` | Comment: `test_rand` holds the checks of the kernels `rand_nop0`, `rand_nop96` and `rand_nop256`. The comment at the top of this file lists them (lines 7 to 25). |
| 629 | `static void test_rand(void)` | Starts the function `test_rand`. It checks the three kernels that `bwx13` adds. What it proves: the three names stand once in `kernels[]` as read kernels, and the table has 58 entries. The C function `rand_index` names every block exactly once when the number of blocks is one of five powers of two, and it gives the order 0, 1, 2 and so on for three other numbers. Each kernel returns from a call on 1, 2, 8, 8192 and 1048576 blocks and leaves the buffer unchanged. Each kernel accesses each page of a range of 4 pages. What it cannot prove on AArch64: the order in which the asm text reads the blocks, and that it reads each block exactly once. A read changes no memory. By the file comment the objdump listing is the evidence (lines 22 to 25). The function reads no clock. |
| 630 | `{` | Opens the body of `test_rand`. |
| 631 | `    static const char *const names[] = { "rand_nop0", "rand_nop96", "rand_nop256" };` | `names`: the names of the three new kernels. The table is constant and exists once for the whole program (`static const`). |
| 632 | `    static const size_t pow2[] = { 1, 2, 8, 8192, 1UL << 20 };` | `pow2`: five numbers of blocks that are powers of two: 1, 2, 8, 8192 and 1048576 (`1UL << 20`). One block is 256 B. So the sizes are 256 B, 512 B, 2048 B, 2 MiB and 256 MiB. By the file comment of `bwx13.c`, 8192 blocks are one chunk of the interval mode with the stop rule `--stop common`. |
| 633 | `    static const size_t other[] = { 3, 48, 12288 };` | `other`: three numbers of blocks that are not powers of two: 3, 48 and 12288. |
| 634 | `    static const size_t by_hand[8] = { 0, 3, 2, 5, 4, 7, 6, 1 }; /* i * (2 * i + 1) mod 8 */` | `by_hand`: the block order for 8 blocks, computed by hand. Step `i` reads the block with the number `i * (2 * i + 1)` modulo 8. For the steps 0 to 7 this gives 0, 3, 2, 5, 4, 7, 6, 1. |
| 635 | `    char what[160];` | `what`: room for the name of a check, 160 characters. |
| 636 | `    int ok = 1, kidx[3];` | `ok`: the result of the check that runs now. 1 means passed. `kidx`: the index in `kernels[]` of each of the three kernels. |
| 638 | `    for (int r = 0; r < 3; r++) {` | Loop over the three names. `r` is the number of the name. |
| 639 | `        int found = 0;` | `found`: how many entries of `kernels[]` have this name and the kind of a read kernel. |
| 640 | `        kidx[r] = -1;` | `kidx[r]` starts as -1, which stands for not found. |
| 641 | `        for (int k = 0; k < K_COUNT; k++)` | Loop over all entries of `kernels[]`. `K_COUNT` is the number of entries. |
| 642 | `            if (!strcmp(names[r], kernels[k].name) && kernels[k].type == T_READ) {` | Tests whether the names are equal (`strcmp` returns 0) and the kind is `T_READ`, a read kernel that returns nothing. |
| 643 | `                found++;` | Counts the entry. |
| 644 | `                kidx[r] = k;` | Keeps its index in `kidx[r]`. |
| 645 | `            }` | Ends the `if` of line 642. |
| 646 | `        ok &= found == 1;` | `ok` stays 1 only when exactly one entry has this name and the kind `T_READ`. A name that is missing, or that stands only with another kind, gives 0 entries and sets `ok` to 0. Two such entries also set it to 0. The count does not see an entry that has this name and another kind. |
| 647 | `    }` | Ends the loop of line 638. |
| 648 | `    trial_check(ok, "rand: each of the 3 new kernels stands once in kernels[] as a read kernel", 0);` | Prints the result row of the name check through `trial_check` (line 293). Its check name starts with `rand: each of the 3 new kernels`. The bytes field is 0. Why this matters: the loop of `selftest` chooses the checks by the kind in `kernels[]` (line 851). |
| 649 | `    trial_check(K_COUNT == 58, "rand: kernels[] has 58 entries (55 of bwx12 and 3 new)", 0);` | Second check: the number of entries of `kernels[]` must be 58. By the check name these are the 55 kernels of bwx12 and the 3 new ones. This check takes the place of the check of line 620, which is not compiled. CRB build: this row and the row of line 648 end with `pass` [Ref1]. |
| 650 | `    if (!ok)` | When the name check failed ... |
| 651 | `        return;` | ... the function returns here. The other checks need the three indexes in `kidx`. |
| 653 | `    /* the C model of the order */` | Comment: the next block checks the C model of the order. The model is the function `rand_index` of the runner source. `rand_index(i, nb)` gives the number of the block that step `i` reads in a range of `nb` blocks. For a power of two it is `i * (2 * i + 1)` modulo `nb`. For another `nb` it is `i`. |
| 654 | `    for (size_t s = 0; s < sizeof pow2 / sizeof pow2[0]; s++) {` | Loop over the five numbers of `pow2`. `sizeof pow2 / sizeof pow2[0]` is the number of entries, 5. |
| 655 | `        size_t nb = pow2[s], moved = 0;` | `nb`: the number of blocks of this pass. `moved`: the count of the steps whose block number differs from the step number. |
| 656 | `        uint8_t *seen = calloc(nb, 1);` | `seen`: one byte per block, set to 0 by `calloc`. It counts how many times the model names each block. |
| 657 | `        ok = seen != NULL;` | `ok` is 1 when the allocation worked. A failed allocation makes the check fail. |
| 658 | `        for (size_t i = 0; ok && i < nb; i++) {` | Loop over the steps `i` from 0 to `nb - 1`. It stops early when `ok` is 0. |
| 659 | `            size_t j = rand_index(i, nb);` | `j`: the block that the model names for step `i`. |
| 660 | `            if (j >= nb \|\| seen[j]++)` | Tests two defects. First: the block number lies outside the range (`j >= nb`). Second: the model named this block before (`seen[j]` is not 0). `seen[j]++` reads the old count and then adds 1. The right side of `\|\|` runs only when `j` lies inside the range. |
| 661 | `                ok = 0;` | Then the check fails. |
| 662 | `            moved += j != i;` | Adds 1 to `moved` when the block number differs from the step number. |
| 663 | `        }` | Ends the loop of line 658. |
| 664 | `        for (size_t j = 0; ok && j < nb; j++)` | Second loop, over all blocks. It also stops when `ok` is 0. |
| 665 | `            ok &= seen[j] == 1;` | Every block must have the count 1. |
| 666 | `        free(seen);` | Releases `seen`. |
| 667 | `        snprintf(what, sizeof what, "rand: the index map reaches each of %zu blocks once", nb);` | `snprintf` writes the name of the check into `what`: `rand: the index map reaches each of N blocks once`, with the number of blocks for N. |
| 668 | `        trial_check(ok, what, nb * 256);` | Prints the result row. The bytes field is the size of the range, `nb * 256` bytes. What it proves: for this number of blocks the model names every block of the range exactly once. So a loop that follows the model reads the same bytes as a loop in address order, each byte once. It proves this for the C model, not for the asm text. |
| 669 | `        if (nb >= 8192) {` | For the two large numbers of blocks, 8192 and 1048576, one more check follows. |
| 670 | `            snprintf(what, sizeof what, "rand: the index map of %zu blocks moves more than half of the steps", nb);` | Writes the name of the check: `rand: the index map of N blocks moves more than half of the steps`. |
| 671 | `            trial_check(moved > nb / 2, what, nb * 256);` | The check passes when more than half of the steps read a block whose number differs from the step number. This shows that the model does not give the address order. It does not measure how irregular the order is. |
| 672 | `        }` | Ends the `if` of line 669. |
| 673 | `    }` | Ends the loop of line 654. |
| 674 | `    ok = 1;` | Sets `ok` back to 1 for the next check. |
| 675 | `    for (size_t i = 0; i < 8; i++)` | Loop over the 8 steps of a range of 8 blocks. |
| 676 | `        ok &= rand_index(i, 8) == by_hand[i];` | The model must name the block of the list `by_hand` at every step. |
| 677 | `    trial_check(ok, "rand: the index map of 8 blocks is 0,3,2,5,4,7,6,1", 8 * 256);` | Prints the result row with the check name `rand: the index map of 8 blocks is 0,3,2,5,4,7,6,1`. The bytes field is 2048 (`8 * 256`). |
| 678 | `    for (size_t s = 0; s < sizeof other / sizeof other[0]; s++) {` | Loop over the three numbers of `other`, which are not powers of two. |
| 679 | `        ok = 1;` | Sets `ok` to 1 for this number of blocks. |
| 680 | `        for (size_t i = 0; i < other[s]; i++)` | Loop over all steps. |
| 681 | `            ok &= rand_index(i, other[s]) == i;` | The model must name block `i` at step `i`. This is the address order. |
| 682 | `        snprintf(what, sizeof what, "rand: the index map of %zu blocks (not a power of two) is 0,1,2,...", other[s]);` | Writes the name of the check: `rand: the index map of N blocks (not a power of two) is 0,1,2,...`. |
| 683 | `        trial_check(ok, what, other[s] * 256);` | Prints the result row. The bytes field is `other[s] * 256`. |
| 684 | `    }` | Ends the loop of line 678. |

### Function `test_rand`: each new kernel on guarded buffers (lines 686 to 744)

| Line | Source | Explanation |
|---:|---|---|
| 686 | `    for (int r = 0; r < 3; r++) {` | Loop over the three kernels. The two blocks of this loop run each kernel on real buffers. |
| 687 | `        const struct kdef *kd = &kernels[kidx[r]];` | `kd`: the entry of kernel `r` in `kernels[]`, found through the index of line 644. |
| 688 | `        /* the kernel on 1, 2, 8, 8192 and 2^20 blocks */` | Comment: the kernel runs on 1, 2, 8, 8192 and 1048576 blocks. |
| 689 | `        for (size_t s = 0; s < sizeof pow2 / sizeof pow2[0]; s++) {` | Loop over the five numbers of `pow2`. |
| 690 | `            size_t nb = pow2[s], n = nb * 32;` | `nb`: the number of blocks. `n`: the size in words of 8 bytes. One block of 256 B is 32 words. |
| 691 | `            struct thread t = { .a = guarded(n) };` | `t`: a thread record with one guarded buffer of `n` words (line 135). A read kernel needs no buffer `b`. For 1, 2 and 8 blocks the buffer has 256 B, 512 B and 2048 B. With a page of 4096 B such a buffer starts directly after a `PROT_NONE` page, but it does not end directly before one. The row of line 134 gives the details. |
| 692 | `            volatile uint64_t sink = 0;` | `sink`: the variable that `call` needs for the sum of an old read kernel. A `rand` kernel returns nothing. |
| 693 | `            for (size_t i = 0; i < n; i++)` | Loop over all words of the buffer. |
| 694 | `                t.a[i] = pattern(i, 5);` | Every word gets its own value: `pattern` with the salt 5 (line 151). |
| 695 | `#if STANDIN` | `#if STANDIN`: the next line is compiled only in a stand-in build. The runner source sets `STANDIN` to 0 on AArch64 and to 1 on every other machine. |
| 696 | `            rand_visit = calloc(nb, 1);` | Stand-in build only: `rand_visit` gets one byte per block, set to 0. `rand_visit` is a global pointer of the runner source. While it is not `NULL`, the stand-in kernel adds 1 to the byte of each block that it visits. |
| 697 | `#endif` | Ends the `#if` of line 695. |
| 698 | `            calling(kd, n);` | Prints the `call` line (line 158). |
| 699 | `            call(kd, &t, 0, n * 8, 0, &sink);` | Runs the kernel once on the whole buffer (offset 0, `n * 8` bytes) through `call` of the runner source. The first 0 is the offset. The second 0 is the store value, which a read kernel does not use. No `SIGSEGV` handler is installed here. A kernel that accesses a `PROT_NONE` page ends the process, and the last `call` line of the output names it. |
| 700 | `            ok = 1;` | Sets `ok` to 1. |
| 701 | `            for (size_t i = 0; i < n; i++)` | Loop over all words. |
| 702 | `                ok &= t.a[i] == pattern(i, 5);` | Every word must still hold its pattern value. |
| 703 | `            check(ok, kd, "rand: returns, buffer unchanged", n);` | Prints the result row with the check name `rand: returns, buffer unchanged`. The row appears only when the kernel came back from the call. What it proves: for this number of blocks the kernel ends, stores nothing in the buffer, and makes no access to the page before the buffer. For 8192 and 1048576 blocks it also makes no access to the page after the buffer. What it cannot prove: that the kernel loads anything. |
| 704 | `#if STANDIN` | `#if STANDIN`: lines 705 to 710 are compiled only in a stand-in build. |
| 705 | `            ok = rand_visit != NULL;` | `ok` is 1 when the allocation of line 696 worked. |
| 706 | `            for (size_t j = 0; ok && j < nb; j++)` | Loop over all blocks. It stops when `ok` is 0. |
| 707 | `                ok &= rand_visit[j] == 1;` | Every block must have the visit count 1. |
| 708 | `            check(ok, kd, "rand: the stand-in visits each block exactly once", n);` | Prints the result row with the check name `rand: the stand-in visits each block exactly once`. A build on AArch64 has no such row. The self-test output of the CRB build holds none [Ref1]. |
| 709 | `            free(rand_visit);` | Releases the visit counts. |
| 710 | `            rand_visit = NULL;` | Sets `rand_visit` back to `NULL`. Then the stand-in kernels count nothing in the later checks. |
| 711 | `#endif` | Ends the `#if` of line 704. |
| 712 | `            unguard(t.a, n);` | Releases the buffer. |
| 713 | `        }` | Ends the loop of line 689. |
| 714 | `        /* 4 pages, one of them PROT_NONE: the kernel must fault in that page */` | Comment: the next block uses 4 pages, and one of them is `PROT_NONE`. The kernel must fault in that page. |
| 715 | `        {` | Opens a block of its own. Its variables exist only up to line 740. |
| 716 | `            size_t n = 4 * (size_t)page_bytes / 8;` | `n`: the number of words of 4 pages. |
| 717 | `            struct thread t = { .a = guarded(n) };` | `t`: a thread record with one guarded buffer of 4 pages. With a page of 4096 B this is 64 blocks, a power of two. So the kernel runs its loop 1, the loop with the computed order (lines 19 to 20). |
| 718 | `            struct sigaction sa, old;` | `sa`: the new setting for the signal `SIGSEGV`. `old`: the setting from before. |
| 719 | `            volatile uint64_t sink = 0;` | `sink`: the variable that `call` needs. A `rand` kernel does not use it. |
| 720 | `            memset(&sa, 0, sizeof sa);` | Sets every byte of `sa` to 0. |
| 721 | `            sa.sa_sigaction = on_fault;` | The handler is `on_fault` (line 251), the handler that `test_touch` uses too. |
| 722 | `            sa.sa_flags = SA_SIGINFO;` | The flag `SA_SIGINFO` makes Linux pass the fault address to the handler. |
| 723 | `            sigaction(SIGSEGV, &sa, &old);` | Installs `on_fault` as the handler of `SIGSEGV`. `old` keeps the setting from before. |
| 724 | `            for (volatile int j = 0; j < 4; j++) {` | The loop runs four times, once per page `j`. `j` is `volatile`: it keeps its value across the jump of line 256. |
| 725 | `                uint8_t *pg = (uint8_t *)t.a + (size_t)j * (size_t)page_bytes;` | `pg`: the address of page `j` of the buffer. |
| 726 | `                volatile int faulted = 0;` | `faulted`: becomes 1 when the kernel faulted. It is `volatile` for the same reason as `j`. |
| 727 | `                mprotect(pg, (size_t)page_bytes, PROT_NONE);` | `mprotect` makes this page `PROT_NONE`. |
| 728 | `                fault_addr = 0;` | Clears the fault address of the pass before. |
| 729 | `                calling(kd, n);` | Prints the `call` line. |
| 730 | `                if (sigsetjmp(fault_jmp, 1) == 0)` | `sigsetjmp` saves this place in `fault_jmp` and returns 0 at its direct call. The argument 1 saves the signal mask, and the jump restores it. So `SIGSEGV` can be caught again for the next page. |
| 731 | `                    call(kd, &t, 0, n * 8, 0, &sink);` | The value 0: the kernel is called on the whole range of 4 pages. |
| 732 | `                else` | The other value: when the kernel faults, `on_fault` jumps back to line 730, and `sigsetjmp` returns 1 there. |
| 733 | `                    faulted = 1;` | Then `faulted` becomes 1. |
| 734 | `                mprotect(pg, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | Makes the page readable and writable again. |
| 735 | `                snprintf(what, sizeof what, "rand: faults in page %d of 4 when it is PROT_NONE", (int)j);` | Writes the name of the check: `rand: faults in page J of 4 when it is PROT_NONE`, with the page number for J. |
| 736 | `                check(faulted && fault_addr >= (uintptr_t)pg && fault_addr < (uintptr_t)pg + (uintptr_t)page_bytes, kd, what, n);` | The check passes when the kernel faulted and the fault address lies in the `PROT_NONE` page. What it proves: loop 1 of the kernel accesses at least one byte of each of the 4 pages. What it cannot prove: that the kernel reads every block of a page. One load per page passes. |
| 737 | `            }` | Ends the loop of line 724. |
| 738 | `            sigaction(SIGSEGV, &old, NULL);` | Restores the `SIGSEGV` setting from before. |
| 739 | `            unguard(t.a, n);` | Releases the buffer. |
| 740 | `        }` | Ends the block of line 715. |
| 741 | `    }` | Ends the loop of line 686. |
| 742 | `}` | Ends the function `test_rand`. |
| 744 | `/* bwx13- */` | Comment: the marker `bwx13-`. It ends the block of line 627. |

### Functions `has_line` and `emitted`: the text that `emit_trial` prints (lines 745 to 775)

| Line | Source | Explanation |
|---:|---|---|
| 745 | `static int has_line(const char *text, const char *line)` | Starts the function `has_line`. It is true when `text` holds `line` as a whole line. |
| 746 | `{` | Opens the body of `has_line`. |
| 747 | `    size_t n = strlen(line);` | `n`: the length of `line` in characters. |
| 748 | `    for (const char *s = text; (s = strstr(s, line)) != NULL; s += n)` | `strstr` finds the next place in the text that holds `line`. The loop goes from match to match until there is no more. |
| 749 | `        if ((s == text \|\| s[-1] == '\n') && s[n] == '\n')` | The match counts when it starts at the text start or directly after a line end, and a line end follows it. |
| 750 | `            return 1;` | Then the result is 1. |
| 751 | `    return 0;` | No such match: the result is 0. |
| 752 | `}` | Ends the function `has_line`. |
| 754 | `/* The text that emit_trial() prints for the record r of the trial p. stdout` | Comment: `emitted` returns the text that `emit_trial` prints for the record `r` of the trial `p`. The standard output ... |
| 755 | ` * is a memory stream during the call (glibc lets a program assign stdout). */` | Comment: ... is a memory stream during the call. The C library glibc lets a program assign `stdout`. |
| 756 | `static char *emitted(struct tw *w, struct trial *p, struct trec *r)` | Starts the function `emitted`. It returns the text that `emit_trial` of the runner source prints for a given plan and record. |
| 757 | `{` | Opens the body of `emitted`. |
| 758 | `    char *text = NULL;` | `text`: will point to the printed text. |
| 759 | `    size_t len = 0;` | `len`: will hold its length in bytes. |
| 760 | `    FILE *out = stdout, *mem = open_memstream(&text, &len);` | `out`: keeps the real standard output. `mem`: a stream that writes into memory (`open_memstream`). The C library sets `text` and `len` when the stream is flushed or closed. |
| 761 | `    if (!mem) {` | Tests whether the stream could not be opened. |
| 762 | `        perror("open_memstream");` | On failure: prints the word `open_memstream` and the reason. |
| 763 | `        exit(2);` | On failure: the process ends with exit status 2. |
| 764 | `    }` | Ends the `if` of line 761. |
| 765 | `    fflush(out);` | Writes out what the real standard output still holds in its buffer. |
| 766 | `    plan.tr = p;` | Points the global `plan.tr` to the test plan ... |
| 767 | `    rec = r;` | ... and the global `rec` to the test record. So `emit_trial(w, 0)` prints trial 0 from them. |
| 768 | `    stdout = mem;` | Replaces `stdout` by the memory stream. |
| 769 | `    emit_trial(w, 0);` | `emit_trial` prints the rows of trial 0. They go into memory, not to the output of the self-test. |
| 770 | `    stdout = out;` | Restores the real `stdout`. |
| 771 | `    fclose(mem);` | Closes the memory stream. After this `text` holds the whole printed text. |
| 772 | `    plan.tr = NULL;` | Sets `plan.tr` back to `NULL` ... |
| 773 | `    rec = NULL;` | ... and `rec` back to `NULL`. |
| 774 | `    return text;` | Returns the printed text. The caller frees it. |
| 775 | `}` | Ends the function `emitted`. |

### Function `test_emit`: the output rows of one trial (lines 776 to 825)

| Line | Source | Explanation |
|---:|---|---|
| 777 | `/* emit_trial() on a record with known values. Every value differs from the` | Comment: `test_emit` runs `emit_trial` on a record with known values. Every value differs from the ... |
| 778 | ` * value of the field beside it, so a row that prints the wrong field fails. */` | Comment: ... value of the field beside it. So a row that prints the wrong field fails. The record does not keep this rule in one place: reading 0 and reading 1 hold the same value for the enabled time and for the running time (lines 789 to 790). So the first C row must show 100 ns in both fields (line 804). The second C row must show 100 ns and 50 ns. So the check still fails for a row that swaps the two fields. |
| 779 | `static void test_emit(void)` | Starts the function `test_emit`. It writes a trial record by hand: 1 predecessor window, 2 target windows, three counter readings, two page snapshots, CPU times and context-switch counts. The record holds three intended defects: no huge-page value in the second snapshot (-1), counters that ran 50 ns of 100 ns in target window 1, and `sink_ok = 0`. What it proves: `emit_trial` prints the values of this record in the right fields of the C, P, E and X rows. What it cannot prove: anything about the rows of the interval mode. In the runner source only the trial mode calls `emit_trial`. The W rows are printed here, and no check compares them. |
| 780 | `{` | Opens the body of `test_emit`. |
| 781 | `    int oldread = kernel_named("oldread");` | The index of the kernel `oldread` in `kernels[]`. |
| 782 | `    struct trial p = { .nwin = 2, .count = CS_READ };` | `p`: the plan. It has 2 target windows and the counter state `CS_READ`: the timed sequence reads the counter group at the borders of the target windows. |
| 783 | `    struct win win[3] = {` | `win`: three window records, written by hand. |
| 784 | `        { .k = oldread, .phase = PH_PRED, .widx = 0, .size = 4096, .bytes = 8192, .t_start = t_base_ns + 1000, .t_end = t_base_ns + 2000 },` | Window 0, the predecessor window: kernel `oldread`, range size 4096 B, 8192 bytes counted, start 1000 ns and end 2000 ns after `t_base_ns`. `t_base_ns` is the clock value at the start of the process. The rows print times relative to it. |
| 785 | `        { .k = oldread, .phase = PH_TARGET, .widx = 0, .size = 4096, .bytes = 12288, .t_start = t_base_ns + 2100, .t_end = t_base_ns + 3100 },` | Window 1, target window 0: 12288 bytes, from 2100 ns to 3100 ns. It starts 100 ns after the end of the predecessor window. |
| 786 | `        { .k = oldread, .phase = PH_TARGET, .widx = 1, .size = 4096, .bytes = 16384, .t_start = t_base_ns + 3400, .t_end = t_base_ns + 4400 },` | Window 2, target window 1: 16384 bytes, from 3400 ns to 4400 ns. It starts 300 ns after the end of target window 0. |
| 787 | `    };` | Ends the three window records. |
| 788 | `    /* three readings; the second window ran its counters for 50 of 100 ns */` | Comment: three counter readings follow. The second target window ran its counters for 50 ns of 100 ns. |
| 789 | `    struct counts c[3] = { { .cpu_ns = 500, .enabled = 1000, .running = 1000, .val = { 70 } },` | `c`: the three counter readings. Reading 0: thread CPU time 500 ns, enabled time 1000 ns, running time 1000 ns, event count 70. |
| 790 | `                           { .cpu_ns = 800, .enabled = 1100, .running = 1100, .val = { 75 } },` | Reading 1: thread CPU time 800 ns, enabled time 1100 ns, running time 1100 ns, event count 75. |
| 791 | `                           { .cpu_ns = 1400, .enabled = 1200, .running = 1150, .val = { 82 } } };` | Reading 2: thread CPU time 1400 ns, enabled time 1200 ns, running time 1150 ns, event count 82. So between reading 1 and reading 2 the counters were enabled for 100 ns and ran for 50 ns. This is the second intended defect. |
| 792 | `    struct trec r = { .win = win, .nw = 3, .cnt = c, .pg = { { 8192, 4096 }, { 8192, -1 } },` | `r`: the trial record. It has the 3 windows, the readings `c`, and two page snapshots. The first snapshot: 8192 kB, of them 4096 kB in huge pages. The second: 8192 kB and -1, which stands for no huge-page value. This is the first intended defect. |
| 793 | `                      .vm = { { 1, 2, 3, 4 }, { 5, 6, 7, 8 } }, .cpu = { 10000, 13000 },` | Continues the record: the four counters of `/proc/vmstat` in each snapshot (1 to 4, then 5 to 8), and the thread CPU time before and after the timed sequence (10000 ns and 13000 ns). |
| 794 | `                      .nvcsw = { 5, 7 }, .nivcsw = { 10, 13 }, .state = CS_READ, .sink_ok = 0 };` | Ends the record: 5 and 7 voluntary context switches before and after, 10 and 13 involuntary ones, the counter state `CS_READ`, and `sink_ok = 0`. The value 0 says that the sink check failed. This is the third intended defect. |
| 795 | `    struct tw w;` | `w`: a worker record for `emit_trial`. |
| 796 | `    int nev = cfg.nev;` | `nev`: keeps the value of `cfg.nev`, the number of counter events in the configuration of the runner. |
| 797 | `    char *text;` | `text`: the printed text. |
| 799 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 800 | `    w.t.group_fd = 0; /* emit_trial() only asks whether a group is open */` | `group_fd = 0` makes `emit_trial` treat the counter group as open. Comment: `emit_trial` only asks whether a group is open. |
| 801 | `    w.t.nopen = 1;` | One event counts as open. |
| 802 | `    cfg.nev = 1;` | `cfg.nev = 1` makes `emit_trial` print one event column. |
| 803 | `    text = emitted(&w, &p, &r);` | Gets the text that `emit_trial` prints for this record. |
| 804 | `    trial_check(has_line(text, "C,0,0,100,100,300,5") && has_line(text, "C,0,1,100,50,600,7"),` | The C rows must be `C,0,0,100,100,300,5` and `C,0,1,100,50,600,7`. After the trial number and the window number come four differences of two readings: enabled time, running time, thread CPU time (all in ns) and the event count. |
| 805 | `                "C rows hold the differences of two readings", 0);` | Continues the call of line 804: the name of the check, and 0 for the bytes field. |
| 806 | `    trial_check(has_line(text, "P,0,pre,8192,4096,1,2,3,4") && has_line(text, "P,0,post,8192,NA,5,6,7,8"),` | The P rows must be `P,0,pre,8192,4096,1,2,3,4` and `P,0,post,8192,NA,5,6,7,8`. The row with `pre` holds the first snapshot. The row with `post` holds the second, with `NA` for the missing huge-page value. |
| 807 | `                "P rows: pre holds the first snapshot and post the second", 0);` | Continues the call of line 806: the name of the check. |
| 808 | `    trial_check(has_line(text, "E,0,3400,3000,2,3,100,300,0,read"),` | The E row must be `E,0,3400,3000,2,3,100,300,0,read`: wall time 3400 ns, CPU time 3000 ns, 2 voluntary and 3 involuntary context switches, a gap of 100 ns before the first target window, a largest gap of 300 ns, sink check 0, counter state `read`. |
| 809 | `                "E row holds wall time and CPU time and both switch counts and both gaps each in its own field", 0);` | Continues the call of line 808: the name of the check. |
| 810 | `    trial_check(strstr(text, "\nX,0,coverage_na,") != NULL, "X row coverage_na when a snapshot has no huge-page value", 0);` | X row for defect 1: the text must hold a line that starts with `X,0,coverage_na,`. |
| 811 | `    trial_check(strstr(text, "\nX,0,count_multiplexed,target window 1: running_ns 50 below enabled_ns 100\n") != NULL,` | X row for defect 2: the text must hold the line `X,0,count_multiplexed,target window 1: running_ns 50 below enabled_ns 100`. |
| 812 | `                "X row count_multiplexed names the window that ran its counters for less time", 0);` | Continues the call of line 811: the name of the check. |
| 813 | `    trial_check(strstr(text, "\nX,0,sink,") != NULL, "X row sink when the sink check failed", 0);` | X row for defect 3: the text must hold a line that starts with `X,0,sink,`. |
| 814 | `    free(text);` | Frees the text. |
| 816 | `    /* The same record without the three defects must print no X row. */` | Comment: the same record without the three defects must print no X row. |
| 817 | `    r.pg[1].kb_huge = 4096;` | Removes defect 1: the second snapshot gets a huge-page value of 4096 kB. |
| 818 | `    c[2].running = 1200;` | Removes defect 2: the running time of reading 2 becomes 1200 ns. So the counters of target window 1 ran for the whole 100 ns. |
| 819 | `    r.sink_ok = 1;` | Removes defect 3: the sink check counts as passed. |
| 820 | `    text = emitted(&w, &p, &r);` | Prints the record again into a new text. |
| 821 | `    trial_check(strstr(text, "\nX,") == NULL && has_line(text, "E,0,3400,3000,2,3,100,300,1,read"),` | The text must now hold no line that starts with `X,`, and the E row must show sink check 1: `E,0,3400,3000,2,3,100,300,1,read`. |
| 822 | `                "no X row for a record without a defect", 0);` | Continues the call of line 821: the name of the check. |
| 823 | `    free(text);` | Frees the text. |
| 824 | `    cfg.nev = nev;` | Restores `cfg.nev`. |
| 825 | `}` | Ends the function `test_emit`. |

### Function `selftest`: the entry point of the option `--selftest` (lines 826 to 865)

| Line | Source | Explanation |
|---:|---|---|
| 827 | `static int selftest(void)` | Starts the function `selftest`. `main` of `bwx13.c` calls it for the argument `--selftest` and returns its value as the exit status. The self-test runs in the main thread and computes no rate. Only the checks of the trial mode read the clock. |
| 828 | `{` | Opens the body of `selftest`. |
| 829 | `    setvbuf(stdout, NULL, _IOLBF, 0); /* a kernel that faults must not take the earlier lines with it */` | `setvbuf` with `_IOLBF` makes the output line-buffered: each line is written when it is complete. So a kernel that ends the process cannot remove earlier lines. |
| 830 | `    printf("# selftest: page_bytes=%ld kernels=%d (%s); columns: kernel,check,bytes,result\n", page_bytes, K_COUNT,` | Prints the header line. It gives the page size in bytes, the number of kernels and the kind of build (line 831). It also names the four columns of a result row: `kernel`, `check`, `bytes`, `result`. |
| 831 | `           STANDIN ? "STAND-IN kernels, not AArch64" : "aarch64");` | Continues the call of line 830: the kind of build. The text is `aarch64` for a build with the real kernels. It is `STAND-IN kernels, not AArch64` for a build on a machine that is not AArch64 (the 64-bit Arm instruction set). There plain C loops take the place of the NEON and asm kernels. |
| 832 | `    if (page_bytes % 256 != 0) {` | A page size that is not a multiple of 256 B ... |
| 833 | `        fprintf(stderr, "page size is not a multiple of 256\n");` | ... prints a message to the error output ... |
| 834 | `        return 2;` | ... and ends the self-test with the value 2. |
| 835 | `    }` | Ends the `if` of line 832. |
| 836 | `    /* whole buffers of 1 page, 3 pages and 1 MiB */` | Comment: `test_size` gets whole buffers of 1 page, 3 pages and 1 MiB. |
| 837 | `    size_t words[] = { (size_t)page_bytes / 8, 3 * (size_t)page_bytes / 8, (1UL << 20) / 8 };` | `words`: the three buffer sizes of `test_size`, in words of 8 bytes: 1 page, 3 pages and 1 MiB. With a page of 4096 B these are 4096 B, 12288 B and 1048576 B. |
| 838 | `    /* one block: at the start of a page (guard before it) and at the end (guard after it) */` | Comment: `test_block` gets one block at the start of a page, with a guard page before it, and one at the end, with a guard page after it. |
| 839 | `    size_t offs[] = { 0, (size_t)page_bytes / 8 - 32 };` | `offs`: the two block offsets of `test_block`, in words: 0 for the first 256 B of a page, and the page size minus 32 words for the last 256 B. |
| 840 | `/* bwx12+ */` | Comment: the marker `bwx12+`. The next line was added for bwx12. |
| 841 | `    test_round5();` | `test_round5` runs first, before the loop uses the kinds of `kernels[]`. |
| 842 | `/* bwx12- */` | Comment: the marker `bwx12-` ends the addition. |
| 843 | `/* bwx13+ */` | Comment: the marker `bwx13+`. The next line was added for bwx13. |
| 844 | `    test_rand();` | `test_rand`: the checks of the three `rand` kernels. It runs after `test_round5` and before the loop over all kernels. |
| 845 | `/* bwx13- */` | Comment: the marker `bwx13-` ends the addition. |
| 846 | `    for (int k = 0; k < K_COUNT; k++) {` | The loop takes every kernel in the order of `kernels[]`. |
| 847 | `        for (size_t i = 0; i < sizeof words / sizeof words[0]; i++)` | Loop over the three sizes of `words`. |
| 848 | `            test_size(&kernels[k], words[i]);` | Per kernel: `test_size` with each of the three sizes. |
| 849 | `        for (size_t i = 0; i < 2; i++)` | Loop over the two block offsets. |
| 850 | `            test_block(&kernels[k], offs[i]);` | Per kernel: `test_block` at each of the two offsets. |
| 851 | `        if (is_read(&kernels[k]))` | For a read kernel in addition ... |
| 852 | `            test_touch(&kernels[k]);` | ... `test_touch`. |
| 853 | `    }` | Ends the loop of line 846. |
| 854 | `    test_trial();` | Then the checks of the trial mode follow. The first is `test_trial`. |
| 855 | `/* bwx10+ */` | Comment: the marker `bwx10+`. The next two lines were added for bwx10. |
| 856 | `    test_trial_hot();` | `test_trial_hot`: the window checks with `--hot-copy`. |
| 857 | `    test_hot_touch();` | `test_hot_touch`: `timed_sequence_hot` must not touch the window record. |
| 858 | `/* bwx10- */` | Comment: the marker `bwx10-` ends the addition. |
| 859 | `/* bwx11+ */` | Comment: the marker `bwx11+`. The next line was added for bwx11. |
| 860 | `    test_evict();` | `test_evict`: the evict step. |
| 861 | `/* bwx11- */` | Comment: the marker `bwx11-` ends the addition. |
| 862 | `    test_emit();` | `test_emit`: the output rows of a trial. |
| 863 | `    printf("# failures=%d\n", failures);` | The last line of the output is `# failures=N`, with the count of the failed checks for N. CRB build: 520 rows end with `pass`, no line holds `FAIL`, and the last line is `# failures=0` [Ref1]. |
| 864 | `    return failures ? 1 : 0;` | Return value: 1 if a check failed, else 0. `main` of `bwx13.c` returns it as the exit status. The build script `build13.sh` ends with exit status 4 when the value is not 0. |
| 865 | `}` | Ends the function `selftest`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/selftest-bwx13.txt`: the self-test output of the CRB build, 966 lines. The first line is `# selftest: page_bytes=4096 kernels=58 (aarch64); columns: kernel,check,bytes,result`. 444 lines begin with `call,`. 520 rows end with `pass`. No line holds `FAIL`. The last line is `# failures=0`. The second line is the row of the name check of round 5, and no row holds the text `has 55 entries`. The next 67 lines come from `test_rand`: 13 rows that begin with `trial,rand:`, and for each of the three kernels 9 `call` lines and 9 result rows (5 with `rand: returns, buffer unchanged`, 4 with `rand: faults in page`). No row holds the text `stand-in visits`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/build.txt`: the record of the CRB build. It holds the line `## selftest bwx13 exit=0 # failures=0`. Its sha256 value of `bwx13_selftest.c` begins with `2c554063`. Computed in this task with `sha256sum`: the file `bwx13_selftest.c` of the code folder has the same value.
- [Ref3] Checked in this task with a script: the text of `bwx13_selftest.c` without the lines from each `/* bwx13+ */` to the next `/* bwx13- */` (both included) equals `bwx12_selftest.c` of the code folder, line for line.
- [Ref4] Test in this task on the agent server (page size 4096 B) with the two calls of `guarded`: `mmap` of the length plus 2 pages with `PROT_NONE`, then `mprotect` of the length at the start of the second page. For the lengths 256 B, 512 B and 2048 B the file `/proc/self/maps` showed 3 pages: the first without access, the second readable and writable as a whole, the third without access.
