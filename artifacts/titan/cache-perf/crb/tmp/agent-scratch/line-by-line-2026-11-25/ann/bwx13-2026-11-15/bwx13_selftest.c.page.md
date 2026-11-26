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

1. `bwx13.c` includes this file directly before its `main`. `main` reads the page size into `page_bytes`, removes the CPUs above 119 from the allowed set of the process, and calls `selftest` when an argument is `--selftest`. In every other case no function of this file runs ({L827}).
2. `selftest` makes the output line-buffered, prints the header line, and stops with the value 2 if the page size is not a multiple of 256 B ({L829-835}).
3. It sets the three buffer sizes (1 page, 3 pages, 1 MiB) and the two block offsets (first and last 256 B of a page) ({L836-839}).
4. `test_round5` checks the table `kernels[]`: the 26 names of round 5 and their kinds ({L841}).
5. `test_rand` checks the three `rand` kernels: their entries in `kernels[]`, the number of 58 entries, the C model of the block order, each kernel on five guarded buffers, and a fault in each page of a range of 4 pages ({L844}).
6. For each of the 58 kernels: `test_size` on the three sizes, `test_block` at the two offsets, and for a read kernel `test_touch` ({L846-853}).
7. Five checks of the trial mode follow: `test_trial`, `test_trial_hot`, `test_hot_touch`, `test_evict`, `test_emit` ({L854-862}).
8. `selftest` prints `# failures=N` and returns 1 if a check failed, else 0. `main` returns this value as the exit status ({L863-864}).
9. `build13.sh` stores the output in the file `selftest-bwx13.txt`. It stops the build with exit status 4 when the exit status of the self-test is not 0.

## Behavior a reader must know

- The self-test runs only with `bwx13 --selftest`. `build13.sh` starts it once after the build. A timed run starts the runner with `--seq` or `--trial`. So no function of this file runs between two clock reads of a timed run.
- The self-test computes no rate. Only the checks of the trial mode read the clock.
- Result of the CRB build: the self-test output has 966 lines, 520 rows that end with `pass`, no `FAIL` line, and the last line `# failures=0`. Its header line says `page_bytes=4096 kernels=58 (aarch64)` [Ref1]. `build.txt` of the same build holds the line `## selftest bwx13 exit=0 # failures=0`, and its sha256 value of `bwx13_selftest.c` is the value of the file explained here [Ref2].
- What the kernel checks prove for a read kernel: the buffer is unchanged, no byte within one page outside the test buffer is loaded or stored, and at least one byte of each page of a range of 3 pages is accessed. For `oldread` and `oldread2` in addition: the returned sum equals the sum of all words.
- What the kernel checks cannot prove. They see three things only: the content of memory after the call, a fault, and the sum that an old read kernel returns. They cannot see which bytes inside a page a read kernel without return value loads, a nop, a vector add, the order of loads and stores, the speed, or the saving of the registers d8 to d15. By the file comment the objdump listing is the evidence for the instructions ({L22-25}, {L44-48}, {L108-112}).
- For the three `rand` kernels the checks of the block order run on the C function `rand_index`, not on the asm text. On AArch64 no check sees the order in which a `rand` kernel reads its blocks, or that it reads each block once. The stand-in kernels count their visits, and that check exists in a stand-in build only ({L704-711}).
- Three buffers of `test_rand` are smaller than a page of 4096 B: 256 B, 512 B and 2048 B. They start directly after a guard page, but they do not end directly before one. A load of up to 3840 B, 3584 B or 2048 B behind such a buffer does not fault ({L134}, {L691}) [Ref4].
- `test_rand` calls each `rand` kernel once on a guarded buffer of 256 MiB (1048576 blocks). So the self-test of `bwx13` needs this much free memory ({L632}, {L689-691}).
- The check of `test_round5` that `kernels[]` has 55 entries is not compiled in this file ({L618-622}). `test_rand` checks the number 58 ({L649}).
- No check runs the interval mode. The byte count, the clock reads and the stop rule of the function `worker` of the runner source are not tested by this file.
- In `test_size`, in `test_block` and in the first block of `test_rand` ({L689-713}) no `SIGSEGV` handler is installed. A kernel that loads from or stores to a `PROT_NONE` page there ends the process. No result line follows, and the last `call` line of the output names the kernel.
- A failed check does not stop the self-test. It adds 1 to `failures`, and the exit status becomes 1.
- The self-test runs in the main thread. `test_hot_touch` adds one helper thread. No thread is pinned to one CPU. The test buffers come from `guarded`: plain `mmap` memory, with no request for huge pages.
- On a machine that is not AArch64 the self-test checks the stand-in kernels, not the real ones. The header line of the output says which kernels ran.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/selftest-bwx13.txt`: the self-test output of the CRB build, 966 lines. The first line is `# selftest: page_bytes=4096 kernels=58 (aarch64); columns: kernel,check,bytes,result`. 444 lines begin with `call,`. 520 rows end with `pass`. No line holds `FAIL`. The last line is `# failures=0`. The second line is the row of the name check of round 5, and no row holds the text `has 55 entries`. The next 67 lines come from `test_rand`: 13 rows that begin with `trial,rand:`, and for each of the three kernels 9 `call` lines and 9 result rows (5 with `rand: returns, buffer unchanged`, 4 with `rand: faults in page`). No row holds the text `stand-in visits`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/build.txt`: the record of the CRB build. It holds the line `## selftest bwx13 exit=0 # failures=0`. Its sha256 value of `bwx13_selftest.c` begins with `2c554063`. Computed in this task with `sha256sum`: the file `bwx13_selftest.c` of the code folder has the same value.
- [Ref3] Checked in this task with a script: the text of `bwx13_selftest.c` without the lines from each `/* bwx13+ */` to the next `/* bwx13- */` (both included) equals `bwx12_selftest.c` of the code folder, line for line.
- [Ref4] Test in this task on the agent server (page size 4096 B) with the two calls of `guarded`: `mmap` of the length plus 2 pages with `PROT_NONE`, then `mprotect` of the length at the start of the second page. For the lengths 256 B, 512 B and 2048 B the file `/proc/self/maps` showed 3 pages: the first without access, the second readable and writable as a whole, the third without access.
