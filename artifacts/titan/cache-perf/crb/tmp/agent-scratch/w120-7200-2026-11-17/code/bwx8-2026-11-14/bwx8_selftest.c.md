# `bwx8_selftest.c` explained, line by line

- Source file: `bwx8-2026-11-14/bwx8_selftest.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 405 lines, 17114 bytes).
- sha256 of the source when this page was built: `a94d917e26c77f1f54aec516613ee6636a5c803e00e798d6dd126e15ae0818d0`.

## Short version: purpose

This file is the self-test of the runner `bwx8`: it checks what each of the 21 kernels does to memory, and the records and output rows of the trial mode. It runs only when `bwx8` is started with `--selftest`, which the build script `build8.sh` does once after the build. The self-test of the next runner version, `bwx10_selftest.c`, is this file plus two checks of the option `--hot-copy`, which `bwx8` does not have.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx8.c`. It includes this file with `#include`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Kind**: the type of a kernel in the table `kernels[]` of the runner source: `T_READ` (a read kernel that returns nothing), `T_OLDREAD` (a read kernel that returns a sum), `T_WRITE` or `T_COPY`.
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Objdump listing**: the name that the comments of this file use for the machine-code listing.
- **Interval mode, trial mode**: the two modes of the runner. In the interval mode (option `--seq`) each thread runs a sequence of kernels, and the function `worker` of the runner source times each kernel. In the trial mode (option `--trial`) one worker thread runs the trials of a plan file.
- **Plan**: the list of trials that the trial mode reads from a file. One line of the plan is one `struct trial`. The tests of this file write such a structure directly, without a file.
- **Worker record**: the `struct tw` of the runner source. It holds the state of the thread that runs the trials: the buffer, the counter group and the trace. In the self-test the main thread runs the trials.
- **Trial, window, target window**: a trial is a list of timed windows that run one directly after the other: 1 window of previous activity, 4 prefix windows, 1 predecessor window, then the target windows. One window runs one kernel on one range for a requested time.
- **Window record**: the `struct win` of one window. Its plan fields (kernel, range size, passes between two clock reads, duration, bin storage) are set before the trial. Its result fields (bytes, start time, end time, number of bins) are written by the timed sequence.
- **Bin**: a record inside a target window: one clock read and the bytes counted from the start of the window to that clock read. The requested width of a bin is 10 ms.
- **`timed_sequence`**: the function of the runner source that runs the windows of a trial.
- **Sink, sink check**: the sink is the variable that receives the sum that an old read kernel returns. After a trial, the sink check compares it with the expected sum: 1 = equal, 0 = not equal, -1 = the trial ran no old read.
- **Trace**: a list of the events of a trial that the trial mode can keep (option `--trace`).
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
- **Guarded buffer, guard page**: a guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one directly after it. These two pages are the guard pages.
- **Stand-in kernels**: on a machine that is not AArch64 (the 64-bit Arm instruction set), plain C loops take the place of the NEON and asm kernels. The header line of the self-test output says which build ran.
- **Nop, vector add**: a nop is an instruction that does nothing. A vector add adds two vector registers. Neither of the two changes memory.
- **d8 to d15**: the low halves of the Arm vector registers v8 to v15. The Arm calling convention requires that a function gives them back unchanged.
- **Build record, CRB build**: the build record is the folder `bwx8-crb-build-1` of the test data. It holds the files that one run of the build script `build8.sh` wrote [Ref2]. This page calls that run the CRB build. A note of the project names this build as the build that was accepted on CRB [Ref4].
- **`build8.sh`**: the build script of `bwx8`. It compiles `bwx8.c`, runs `bwx8 --selftest`, and writes the machine-code listing.
- **Rate**: bytes divided by time, in GB/s.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `bwx8.c` includes this file directly before its `main`. `main` reads the page size into `page_bytes`, removes the CPUs above 119 from the allowed set of the process, and calls `selftest` when an argument is `--selftest`. In every other case no function of this file runs (line 380).
2. `selftest` makes the output line-buffered, prints the header line, and stops with the value 2 if the page size is not a multiple of 256 B (lines 382 to 388).
3. It sets the three buffer sizes (1 page, 3 pages, 1 MiB) and the two block offsets (first and last 256 B of a page) (lines 389 to 392).
4. For each of the 21 kernels: `test_size` on the three sizes, `test_block` at the two offsets, and for a read kernel `test_touch` (lines 393 to 400).
5. Two checks of the trial mode follow: `test_trial` and `test_emit` (lines 401 to 402).
6. `selftest` prints `# failures=N` and returns 1 if a check failed, else 0. `main` returns this value as the exit status (lines 403 to 404).
7. `build8.sh` stores the output in the file `selftest-bwx8.txt`. It stops the build with exit status 4 when the exit status of the self-test is not 0.

## Behavior a reader must know

- The self-test runs only with `bwx8 --selftest`. `build8.sh` starts it once after the build. A timed run starts the runner with `--seq` or `--trial`. So no function of this file runs between two clock reads of a timed run.
- The self-test computes no rate. Only the checks of the trial mode read the clock.
- Result of the CRB build: the self-test output has 319 lines, 181 rows that end with `pass`, no `FAIL` line, and the last line `# failures=0`. Its header line says `page_bytes=4096 kernels=21 (aarch64)` [Ref1]. `build.txt` of the same build holds the line `## selftest bwx8 exit=0 # failures=0`, and its sha256 value of `bwx8_selftest.c` is the value of the file explained here [Ref2].
- What the kernel checks prove for a read kernel: the buffer is unchanged, no byte within one page outside the test buffer is loaded or stored, and at least one byte of each page of a range of 3 pages is accessed. For `oldread` and `oldread2` in addition: the returned sum equals the sum of all words.
- What the kernel checks cannot prove. They see three things only: the content of memory after the call, a fault, and the sum that an old read kernel returns. They cannot see which bytes inside a page a read kernel without return value loads, a nop, the order of loads and stores, the speed, or the saving of the registers d8 to d15. By the file comment the objdump listing is the evidence for the bytes that a read kernel loads (lines 22 to 26).
- By the file comment, the kernel checks are the text of `bwx_selftest.c`, the self-test of the first runner version, and `test_trial` is new (lines 5 to 6). A `diff` of this task shows four blocks that `bwx_selftest.c` does not have in this form: the first lines of the file comment (lines 2 to 6), its two paragraphs on the trial mode (lines 27 to 41), the six functions from `trial_check` to `test_emit` (lines 207 to 378), and the two calls of lines 401 to 402. All other lines are equal in both files [Ref3].
- No check runs the interval mode. The byte count, the clock reads and the stop rule of the function `worker` of the runner source are not tested by this file.
- In `test_size` and `test_block` no `SIGSEGV` handler is installed. A kernel that loads from or stores to a `PROT_NONE` page there ends the process. No result line follows, and the last `call` line of the output names the kernel.
- A failed check does not stop the self-test. It adds 1 to `failures`, and the exit status becomes 1.
- The self-test runs in the main thread and starts no other thread. It pins no thread to one CPU. The test buffers come from `guarded`: plain `mmap` memory, with no request for huge pages.
- On a machine that is not AArch64 the self-test checks the stand-in kernels, not the real ones. The header line of the output says which kernels ran.

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/bwx8_selftest.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (405 lines, 17114 bytes, sha256 `a94d917e26c77f1f54aec516613ee6636a5c803e00e798d6dd126e15ae0818d0`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### File comment: what the self-test checks, and its limits (lines 1 to 42)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Opens the file comment (lines 1 to 42). It says what the self-test checks and what it cannot check. |
| 2 | ` * bwx8_selftest.c - "bwx8 --selftest": checks what every kernel of bwx8.c` | Comment: the purpose. The option `--selftest` of the runner checks what every kernel of the runner source ... |
| 3 | ` * does to memory, and the accounting of the trial mode. bwx8.c includes this` | Comment: ... does to memory, and the accounting of the trial mode (the mode of the runner with the option `--trial`). The runner source includes this ... |
| 4 | ` * file, so the test runs the machine code of the binary that is timed,` | Comment: ... file. So the test runs the machine code of the binary that is timed, ... |
| 5 | ` * through the same call() as the benchmark. The kernel checks are the text of` | Comment: ... through the same function `call` as the benchmark. So the self-test and a timed run are one binary, and both reach a kernel through `call` and the table `kernels[]`. The kernel checks are the text of ... |
| 6 | ` * bwx_selftest.c. test_trial() at the end is new.` | Comment: ... `bwx_selftest.c`, the self-test of the first runner version. The function `test_trial` at the end was new in bwx8. |
| 7 | ` *` | Comment: an empty line of the comment. |
| 8 | ` * Every buffer ends at a page that cannot be read or written (PROT_NONE) and` | Comment: every test buffer ends at a page that cannot be read or written (`PROT_NONE`) and ... |
| 9 | ` * starts after one. A kernel that touches a byte within one page before the` | Comment: ... starts after one. A kernel that touches a byte within one page before the ... So a load or a store up to one page outside the buffer is a fault. The fault ends the process, except in `test_touch` (line 176), which installs a handler. |
| 10 | ` * buffer or within one page after it dies with SIGSEGV. The line "call,..."` | Comment: ... buffer or within one page after it ends with `SIGSEGV`. Linux sends this signal for a forbidden memory access. The line `call,...` ... |
| 11 | ` * printed before each kernel call names the kernel that died.` | Comment: ... that is printed before each kernel call (line 72) names the kernel that ended the process. |
| 12 | ` * Exit status 0 means every check passed.` | Comment: exit status 0 means that every check passed. |
| 13 | ` *` | Comment: an empty line of the comment. |
| 14 | ` * Checks for every kernel that stores (write and copy kinds): every word is` | Comment: the checks for every kernel that stores (the write kind and the copy kind): every word is ... |
| 15 | ` * compared, on whole buffers and on one 256 B block at a page start and at a` | Comment: ... compared, on whole buffers (line 88) and on one 256 B block at a page start and at a ... |
| 16 | ` * page end.` | Comment: ... page end (line 133). |
| 17 | ` * Checks for every read kernel: the buffer is unchanged and no guard page is` | Comment: the checks for every read kernel: the buffer is unchanged and no guard page is ... |
| 18 | ` * touched. The kernel must fault when one page inside its range is made` | Comment: ... touched. The kernel must fault when one page inside its range is made ... |
| 19 | ` * PROT_NONE, for each page of a 3-page range. oldread and oldread2 return a` | Comment: ... `PROT_NONE`, for each page of a 3-page range (line 176). The kernels `oldread` and `oldread2` return a ... |
| 20 | ` * sum: it must equal the sum of all words.` | Comment: ... sum. The test compares it with the sum of all words (line 111). |
| 21 | ` *` | Comment: an empty line of the comment. |
| 22 | ` * Limits. For the read kernels that return nothing, the test proves that` | Comment: the limits. The new read kernel `read` and `asmread` return nothing. For such read kernels the test proves that ... |
| 23 | ` * every page of the range is touched, not every byte: the objdump listing is` | Comment: ... every page of the range is touched. It does not prove that every byte is loaded. For the bytes that such a kernel loads, the objdump listing is ... |
| 24 | ` * the evidence for the bytes. It cannot see in which order a copy kernel` | Comment: ... the evidence for the bytes. The test also cannot see in which order a copy kernel ... |
| 25 | ` * loads and stores. It does not check that a kernel preserves the` | Comment: ... loads and stores. And it does not check that a kernel preserves the ... |
| 26 | ` * callee-saved registers d8-d15.` | Comment: ... registers d8 to d15, which the called function must save (callee-saved). |
| 27 | ` *` | Comment: an empty line of the comment. |
| 28 | ` * Checks of the trial mode (test_trial): one trial with all phases and bins` | Comment: the checks of the trial mode in `test_trial` (line 227). One trial with all phases and with bins ... These checks do not cover the interval mode, the mode of the runner with the option `--seq`. In that mode the function `worker` of the runner source times the kernels. No check of this file runs `worker`. |
| 29 | ` * runs through run_trial(), the function that the trial mode uses. Every` | Comment: ... runs through `run_trial`, the function that the trial mode uses. Every ... |
| 30 | ` * window must hold whole passes and whole groups of passes between clock` | Comment: ... window must hold whole passes and whole groups of passes between clock ... |
| 31 | ` * reads, must last at least its duration, and must not start before the` | Comment: ... reads, must last at least its duration, and must not start before the ... |
| 32 | ` * window before it ended. The last bin of a window must hold the bytes of` | Comment: ... window before it ended. The last bin of a window must hold the bytes of ... A bin is a record inside a target window: one clock read and the bytes counted from the start of the window to that clock read. |
| 33 | ` * the window. The sink check must pass on a clean buffer and must fail after` | Comment: ... the window. The sink check must pass on a clean buffer and must fail after ... The sink is the variable that receives the sum that an old read kernel returns. The sink check compares it with the expected sum. |
| 34 | ` * one word of the buffer is changed.` | Comment: ... one word of the buffer is changed. |
| 35 | ` *` | Comment: an empty line of the comment. |
| 36 | ` * Checks of the rows (test_emit): emit_trial(), the function that prints the` | Comment: the checks of the output rows in `test_emit` (line 332). `emit_trial`, the function that prints the ... |
| 37 | ` * rows of a trial, runs on a record with known values. The printed text is` | Comment: ... rows of a trial, runs on a record with known values. The printed text is ... |
| 38 | ` * compared: the C rows hold differences of two readings, the post P row holds` | Comment: ... compared. The C rows hold differences of two counter readings. The P row with the word `post` holds ... |
| 39 | ` * the second snapshot, the E row holds CPU time and the two context-switch` | Comment: ... the second page snapshot. The E row holds the CPU time and the two context-switch ... |
| 40 | ` * counts in their own fields, and the X rows coverage_na, count_multiplexed` | Comment: ... counts, each in its own field. And the X rows with the codes `coverage_na`, `count_multiplexed` ... |
| 41 | ` * and sink are printed.` | Comment: ... and `sink` are printed. An X row reports a defect that the runner found in a trial. |
| 42 | ` */` | Ends the comment. |

### Global variables (lines 43 to 45)

| Line | Source | Explanation |
|---:|---|---|
| 43 | `static int failures;` | `failures`: the count of failed checks. `check` (line 79) and `trial_check` (line 211) add to it, and `selftest` prints it at the end (line 403). |
| 44 | `static sigjmp_buf fault_jmp;` | `fault_jmp`: the saved place at which `test_touch` continues after a fault (line 193). `sigjmp_buf` is the type of the C library for such a saved place. |
| 45 | `static volatile uintptr_t fault_addr;` | `fault_addr`: the address of the last fault. The handler `on_fault` writes it (line 169). `volatile` tells the compiler to read and write the variable in memory at every use. A variable that a signal handler changes needs this. |

### Functions `guarded` and `unguard`: a buffer between two `PROT_NONE` pages (lines 46 to 63)

| Line | Source | Explanation |
|---:|---|---|
| 47 | `/* n words whose first byte follows a PROT_NONE page and whose last byte` | Comment: `guarded` gives `n` words (8 bytes each) whose first byte follows a `PROT_NONE` page and whose last byte ... |
| 48 | ` * precedes one. n * 8 must be a multiple of the page size. */` | Comment: ... stands directly before one. For this, `n * 8` must be a multiple of the page size. The function does not test it. Every caller in this file passes 1 page, 3 pages or 1 MiB. In the CRB build a page has 4096 B [Ref1]. With this page size each of the three sizes is a multiple of the page size. So the last word ends directly before the `PROT_NONE` page. |
| 49 | `static uint64_t *guarded(size_t n)` | Starts the function `guarded`. It returns the address of `n` words of new memory that lie between two `PROT_NONE` pages. The checks of this file take their test buffers from it. The memory comes from a plain `mmap`, with no request for huge pages. |
| 50 | `{` | Opens the body of `guarded`. |
| 51 | `    size_t len = n * 8;` | `len`: the size of the buffer in bytes. |
| 52 | `    uint8_t *raw = mmap(NULL, len + 2 * (size_t)page_bytes, PROT_NONE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `len` bytes plus two pages of new memory. `page_bytes` is the page size in bytes. `main` of the runner source sets it before it calls the self-test. `PROT_NONE`: at first the process may neither read nor write any byte of the range. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. |
| 53 | `    if (raw == MAP_FAILED \|\| mprotect(raw + page_bytes, len, PROT_READ \| PROT_WRITE) != 0) {` | Tests whether `mmap` failed. If it did not fail, `mprotect` makes the `len` bytes after the first page readable and writable. The first page and the last page stay `PROT_NONE`. A return value other than 0 means that `mprotect` failed. |
| 54 | `        perror("guarded");` | On an error: `perror` prints the word `guarded` and the reason that Linux gave. |
| 55 | `        exit(2);` | On an error: the process ends with exit status 2. |
| 56 | `    }` | Ends the `if` of line 53. |
| 57 | `    return (uint64_t *)(raw + page_bytes);` | Returns the address of the first usable byte, one page after the start of the mapping. |
| 58 | `}` | Ends the function `guarded`. |
| 60 | `static void unguard(uint64_t *p, size_t n)` | Starts the function `unguard`. It releases a buffer of `n` words that `guarded` returned. |
| 61 | `{` | Opens the body of `unguard`. |
| 62 | `    munmap((uint8_t *)p - page_bytes, n * 8 + 2 * (size_t)page_bytes);` | `munmap` gives the whole mapping back to Linux: the buffer and its two `PROT_NONE` pages. The mapping starts one page before `p`. |
| 63 | `}` | Ends the function `unguard`. |

### Functions `pattern`, `calling`, `check` and `is_read` (lines 64 to 85)

| Line | Source | Explanation |
|---:|---|---|
| 65 | `static uint64_t pattern(size_t i, uint64_t salt)` | Starts the function `pattern`. It returns the test value of the word with the number `i`. |
| 66 | `{` | Opens the body of `pattern`. |
| 67 | `    return (i + 1) * 0x9E3779B97F4A7C15ULL ^ salt;` | Returns `(i + 1)` times an odd 64-bit constant, then XOR `salt`. The product is computed first. Two different word numbers `i` always give two different values. Two different `salt` values give two different patterns for the same `i`. |
| 68 | `}` | Ends the function `pattern`. |
| 70 | `static void calling(const struct kdef *kd, size_t n)` | Starts the function `calling`. It names a kernel in the output before the kernel runs. `kd` points to the entry of the kernel in `kernels[]`. `n` is the size of the range in words. |
| 71 | `{` | Opens the body of `calling`. |
| 72 | `    printf("call,%s,%zu\n", kd->name, n * 8);` | Prints the line `call,<kernel>,<bytes>`: the word `call`, the kernel name, and the size of the range in bytes (`n * 8`). The output is line-buffered (line 382), so this line is written before the kernel starts. If the kernel ends the process, this line names it. |
| 73 | `}` | Ends the function `calling`. |
| 75 | `static void check(int ok, const struct kdef *kd, const char *what, size_t n)` | Starts the function `check`. It prints the result line of one kernel check. `ok` is not 0 when the check passed. |
| 76 | `{` | Opens the body of `check`. |
| 77 | `    printf("%s,%s,%zu,%s\n", kd->name, what, n * 8, ok ? "pass" : "FAIL");` | Prints one row with four fields: the kernel name, the name of the check (`what`), the size in bytes (`n * 8`), and `pass` or `FAIL`. |
| 78 | `    if (!ok)` | When the check failed ... |
| 79 | `        failures++;` | ... adds 1 to `failures`. The self-test continues after a failed check. |
| 80 | `}` | Ends the function `check`. |
| 82 | `static int is_read(const struct kdef *kd)` | Starts the function `is_read`. It tells whether a kernel is a read kernel. |
| 83 | `{` | Opens the body of `is_read`. |
| 84 | `    return kd->type == T_READ \|\| kd->type == T_OLDREAD;` | True for the two read kinds. By the table `kernels[]` of the runner source, `T_OLDREAD` is the kind of `oldread` and `oldread2`: they return a sum. `oldread2` is a second copy of `oldread`: the same source under another name. `T_READ` is the kind of every other read kernel, for example `read` and `asmread`: they return nothing. |
| 85 | `}` | Ends the function `is_read`. |

### Function `test_size`: one kernel on a whole guarded buffer (lines 86 to 129)

| Line | Source | Explanation |
|---:|---|---|
| 87 | `/* The kernel on a whole guarded buffer of n words. */` | Comment: `test_size` runs the kernel on a whole guarded buffer of `n` words. A guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one directly after it. |
| 88 | `static void test_size(const struct kdef *kd, size_t n)` | Starts the function `test_size`. It runs the kernel once on a whole guarded buffer and reads no clock. `selftest` passes three sizes: 1 page, 3 pages and 1 MiB (line 390). What it proves for every kernel: no load and no store within one page outside its buffers. Such an access ends the process. Read kernel: the buffer is unchanged after the call. Old read kernel: the returned sum equals the sum of all words. Write and copy kernel: every word of the range holds the right value after the call. What it cannot prove: that `read` or `asmread` load anything. A read kernel without a return value that loads nothing passes here. `test_touch` (line 176) checks a part of this. |
| 89 | `{` | Opens the body of `test_size`. |
| 90 | `    struct thread t = { .a = guarded(n), .b = guarded(n) };` | `t`: a thread record in the form that `call` needs (`struct thread` of the runner source). Its buffers `a` and `b` are two guarded buffers of `n` words each. Every other field is 0. |
| 91 | `    uint64_t *a = t.a, *b = t.b, sum = 0;` | `a` and `b`: short names for the two buffers. `sum`: the sum of all words of `a`, built in line 101. |
| 92 | `    uint64_t v = 0xA5A5F00D12345678ULL + n;` | `v`: the value that a write kernel must store in every word. It depends on `n`, so each buffer size gets another value. |
| 93 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum that an old read kernel returns. |
| 94 | `    int ok = 1;` | `ok`: the result of the check that runs now. 1 means passed. |
| 96 | `    /* Every word of the source is different, so a store of the wrong vector` | Comment: every word of the source buffer gets a different value. So a store of the wrong vector ... |
| 97 | `     * or to the wrong offset is seen. */` | Comment: ... or a store to the wrong offset is seen. |
| 98 | `    for (size_t i = 0; i < n; i++) {` | Loop over all `n` words. |
| 99 | `        a[i] = pattern(i, 1);` | Gives every word of `a` its own value: `pattern` with the salt 1. |
| 100 | `        b[i] = 0;` | Sets every word of `b` to 0. |
| 101 | `        sum += a[i];` | `sum` becomes the sum of all words of `a` in 64-bit arithmetic (an overflow wraps). |
| 102 | `    }` | Ends the loop of line 98. |
| 103 | `    calling(kd, n);` | Prints the `call` line (line 72). |
| 104 | `    call(kd, &t, 0, n * 8, v, &sink);` | Runs the kernel on the whole buffer (offset 0, `n * 8` bytes) through `call` of the runner source. `call` chooses the arguments by the kind. A read kernel gets `a`. A write kernel gets `a` and the value `v`, which it stores in every word. A copy kernel reads `a` and writes `b`. The sum that an old read kernel returns goes to `sink`. No `SIGSEGV` handler is installed here. A kernel that loads from or stores to a `PROT_NONE` page ends the process. No result line follows then, and the last `call` line of the output names the kernel. |
| 105 | `    if (is_read(kd)) {` | Branch for a read kernel. |
| 106 | `        /* read: must leave every word as it was (and must not fault) */` | Comment: a read kernel must leave every word as it was, and it must not fault. |
| 107 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 108 | `            ok &= a[i] == pattern(i, 1);` | Every word of `a` must still hold its pattern value. One changed word sets `ok` to 0. |
| 109 | `        check(ok, kd, "buffer unchanged", n);` | Prints the result row with the check name `buffer unchanged`. |
| 110 | `        if (kd->type == T_OLDREAD)` | For the kind `T_OLDREAD` in addition ... |
| 111 | `            check(sink == sum, kd, "returned sum equals the sum of all words", n);` | ... the sum in `sink` must equal `sum`. A kernel that skips one word, or adds one word twice, returns another sum. The check name is `returned sum equals the sum of all words`. |
| 112 | `    } else if (kd->type == T_WRITE) {` | Branch for a write kernel. |
| 113 | `        /* write: every word must hold v afterwards; no word may keep the old pattern */` | Comment: after a write kernel every word must hold `v`. No word may keep the old pattern. |
| 114 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 115 | `            ok &= a[i] == v;` | Every word of `a` must hold `v`. A word that the kernel did not store keeps its pattern value, and no pattern value equals `v`. So a missing store fails the check. |
| 116 | `        check(ok, kd, "every word equals v", n);` | Prints the result row with the check name `every word equals v`. |
| 117 | `    } else {` | Branch for a copy kernel. |
| 118 | `        /* copy: destination must equal source word for word; source unchanged */` | Comment: after a copy kernel the destination must equal the source word for word, and the source must be unchanged. |
| 119 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `b`. |
| 120 | `            ok &= b[i] == pattern(i, 1);` | Every word of `b` must hold the pattern value of the same word of `a`. `b` held 0 before the call. |
| 121 | `        check(ok, kd, "destination equals source", n);` | Prints the first result row of a copy kernel, with the check name `destination equals source`. |
| 122 | `        ok = 1;` | Sets `ok` back to 1 for the second check. |
| 123 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 124 | `            ok &= a[i] == pattern(i, 1);` | Every word of `a` must be unchanged. |
| 125 | `        check(ok, kd, "source unchanged", n);` | Prints the second result row of a copy kernel, with the check name `source unchanged`. |
| 126 | `    }` | Ends the `if` chain of line 105. |
| 127 | `    unguard(a, n);` | Releases the buffer `a` ... |
| 128 | `    unguard(b, n);` | ... and the buffer `b`. |
| 129 | `}` | Ends the function `test_size`. |

### Function `test_block`: 256 B at a page start or at a page end (lines 130 to 163)

| Line | Source | Explanation |
|---:|---|---|
| 131 | `/* One block of 256 B (32 words) at word offset off inside one guarded page.` | Comment: `test_block` runs the kernel on one block of 256 B (32 words) at the word offset `off` inside one guarded page. |
| 132 | ` * Words of the page outside the 256 B must keep their old value. */` | Comment: the words of the page outside the 256 B must keep their old value. |
| 133 | `static void test_block(const struct kdef *kd, size_t off)` | Starts the function `test_block`. It runs the kernel on one block of 256 B (32 words) inside a buffer of one page. 256 B is the smallest range that a kernel may get. With `off` = 0 the block starts directly after the `PROT_NONE` page before the buffer. With the other value of `off` the block ends directly before the `PROT_NONE` page after the buffer (line 392). What it proves for every kernel: no load and no store up to one page before the block start (first case), and none up to one page after the block end (second case). Such an access ends the process. Write and copy kernel: every word of the page outside the block keeps its value. What it cannot prove: which bytes inside the 256 B a read kernel loads. The sum that an old read kernel returns is not compared here. |
| 134 | `{` | Opens the body of `test_block`. |
| 135 | `    size_t n = (size_t)page_bytes / 8, m = 32;` | `n`: the number of words of one page. `m`: the 32 words of the block (256 B). |
| 136 | `    struct thread t = { .a = guarded(n), .b = guarded(n) };` | `t`: a thread record with two guarded buffers of one page each. |
| 137 | `    uint64_t *a = t.a, *b = t.b;` | `a` and `b`: short names for the two buffers. |
| 138 | `    uint64_t v = 0x0123456789ABCDEFULL;` | `v`: the value that a write kernel must store. |
| 139 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This function does not compare it. |
| 140 | `    int ok = 1;` | `ok`: the result of the check. 1 means passed. |
| 142 | `    for (size_t i = 0; i < n; i++) {` | Loop over all words of the page. |
| 143 | `        a[i] = pattern(i, 3);` | Fills the page of `a` with the pattern of the salt 3 ... |
| 144 | `        b[i] = pattern(i, 4);` | ... and the page of `b` with the pattern of the salt 4. So the two pages hold two different patterns. |
| 145 | `    }` | Ends the loop of line 142. |
| 146 | `    calling(kd, m);` | Prints the `call` line with the size 256. |
| 147 | `    call(kd, &t, off * 8, m * 8, v, &sink);` | Runs the kernel on 256 B (`m * 8`) at the byte offset `off * 8`. As in `test_size`, no `SIGSEGV` handler is installed. |
| 148 | `    if (is_read(kd)) {` | Branch for a read kernel. |
| 149 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 150 | `            ok &= a[i] == pattern(i, 3);` | Read kernel: every word of the page of `a` must be unchanged. |
| 151 | `        check(ok, kd, off ? "256 B at page end: page unchanged" : "256 B at page start: page unchanged", m);` | Prints the result row. The name of the check says `page start` for `off` = 0 and `page end` for the other value. The size field is 256. |
| 152 | `    } else if (kd->type == T_WRITE) {` | Branch for a write kernel. |
| 153 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 154 | `            ok &= a[i] == (i >= off && i < off + m ? v : pattern(i, 3));` | Write kernel: the 32 words of the block must hold `v`. Every other word of the page must keep its pattern value. |
| 155 | `        check(ok, kd, off ? "256 B at page end: only those 256 B written" : "256 B at page start: only those 256 B written", m);` | Prints the result row. The check name ends with `only those 256 B written`. |
| 156 | `    } else {` | Branch for a copy kernel. |
| 157 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 158 | `            ok &= b[i] == (i >= off && i < off + m ? pattern(i, 3) : pattern(i, 4)) && a[i] == pattern(i, 3);` | Copy kernel: in `b` the 32 words of the block must hold the values of `a`. Every other word of `b` must keep its own pattern value. `a` must be unchanged. |
| 159 | `        check(ok, kd, off ? "256 B at page end: only those 256 B copied" : "256 B at page start: only those 256 B copied", m);` | Prints the result row. The check name ends with `only those 256 B copied`. |
| 160 | `    }` | Ends the `if` chain of line 148. |
| 161 | `    unguard(a, n);` | Releases the buffer `a` ... |
| 162 | `    unguard(b, n);` | ... and the buffer `b`. |
| 163 | `}` | Ends the function `test_block`. |

### Functions `on_fault` and `test_touch`: a read kernel must touch every page (lines 164 to 205)

| Line | Source | Explanation |
|---:|---|---|
| 165 | `static void on_fault(int sig, siginfo_t *si, void *ctx)` | Starts the function `on_fault`, the `SIGSEGV` handler of `test_touch`. Linux calls it when a kernel accesses a page that it may not access. `si` holds the details of the fault. |
| 166 | `{` | Opens the body of `on_fault`. |
| 167 | `    (void)sig;` | Marks the argument `sig` as not used. Then the compiler does not warn about it. |
| 168 | `    (void)ctx;` | Marks the argument `ctx` as not used. |
| 169 | `    fault_addr = (uintptr_t)si->si_addr;` | Stores the address of the faulting access in `fault_addr`. |
| 170 | `    siglongjmp(fault_jmp, 1);` | Jumps back to the `sigsetjmp` call of line 193, which now returns 1. The kernel call that faulted does not continue. |
| 171 | `}` | Ends the function `on_fault`. |
| 173 | `/* Read kernels: a range of 3 pages, with one page inside it made PROT_NONE.` | Comment: for read kernels, `test_touch` uses a range of 3 pages, with one page inside it made `PROT_NONE`. |
| 174 | ` * The kernel must fault, and the fault address must lie in that page. This` | Comment: the kernel must fault, and the fault address must lie in that page. This ... |
| 175 | ` * shows that the kernel touches every page of its range. */` | Comment: ... shows that the kernel touches every page of its range. |
| 176 | `static void test_touch(const struct kdef *kd)` | Starts the function `test_touch`. It is for read kernels only. The buffer has 3 pages. The loop runs three times. Each time another one of the pages is `PROT_NONE`, and the kernel runs on the whole buffer. The kernel must fault, and the fault address must lie in that page. What it proves: the kernel accesses at least one byte of each of the 3 pages. A kernel that loads nothing, or that leaves out a page, fails. What it cannot prove: that every byte or every 64 B line of a page is loaded. One load per page passes. A page has 4096 B in the CRB build [Ref1]. By the file comment the objdump listing is the evidence for the loads (lines 22 to 24). The check also cannot prove anything about a nop, a vector add, or the use of a loaded value. They change no memory and raise no fault. |
| 177 | `{` | Opens the body of `test_touch`. |
| 178 | `    size_t n = 3 * (size_t)page_bytes / 8;` | `n`: the number of words of 3 pages. |
| 179 | `    struct thread t = { .a = guarded(n) };` | `t`: a thread record with one guarded buffer of 3 pages. A read kernel needs no buffer `b`. |
| 180 | `    struct sigaction sa, old;` | `sa`: the new setting for the signal. `old`: the setting from before. |
| 181 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This function does not compare it. |
| 183 | `    memset(&sa, 0, sizeof sa);` | Sets every byte of `sa` to 0. |
| 184 | `    sa.sa_sigaction = on_fault;` | The handler is `on_fault`. |
| 185 | `    sa.sa_flags = SA_SIGINFO;` | The flag `SA_SIGINFO` makes Linux pass the fault address to the handler. |
| 186 | `    sigaction(SIGSEGV, &sa, &old);` | Installs `on_fault` as the handler of `SIGSEGV`. `old` keeps the setting from before. |
| 187 | `    for (volatile int j = 0; j < 3; j++) {` | The loop runs three times, once per page `j`. `j` is `volatile`: it keeps its value across the jump of line 170. |
| 188 | `        uint8_t *pg = (uint8_t *)t.a + (size_t)j * (size_t)page_bytes;` | `pg`: the address of page `j` of the buffer. |
| 189 | `        volatile int faulted = 0;` | `faulted`: becomes 1 when the kernel faulted. It is `volatile` for the same reason as `j`. |
| 190 | `        mprotect(pg, (size_t)page_bytes, PROT_NONE);` | `mprotect` makes this page `PROT_NONE`. |
| 191 | `        fault_addr = 0;` | Clears the fault address of the pass before. |
| 192 | `        calling(kd, n);` | Prints the `call` line. |
| 193 | `        if (sigsetjmp(fault_jmp, 1) == 0)` | `sigsetjmp` saves this place in `fault_jmp` and returns 0 at its direct call. The argument 1 saves the signal mask, and the jump restores it. So `SIGSEGV` can be caught again for the next page. |
| 194 | `            call(kd, &t, 0, n * 8, 0, &sink);` | The value 0: the kernel is called on the whole range of 3 pages. |
| 195 | `        else` | The other value: when the kernel faults, `on_fault` jumps back to line 193, and `sigsetjmp` returns 1 there. |
| 196 | `            faulted = 1;` | Then `faulted` becomes 1. |
| 197 | `        mprotect(pg, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | Makes the page readable and writable again. |
| 198 | `        check(faulted && fault_addr >= (uintptr_t)pg && fault_addr < (uintptr_t)pg + (uintptr_t)page_bytes, kd,` | The check passes when the kernel faulted and the fault address lies in the `PROT_NONE` page. The call goes on in the next three lines. |
| 199 | `              j == 0 ? "faults in page 0 of 3 when it is PROT_NONE"` | Continues the call of line 198: the name of the check gives the page number. This is the name for page 0. |
| 200 | `                     : j == 1 ? "faults in page 1 of 3 when it is PROT_NONE" : "faults in page 2 of 3 when it is PROT_NONE",` | Continues the call: the names for page 1 and for page 2. |
| 201 | `              n);` | Ends the call: the size of the range in words. The row prints it in bytes. |
| 202 | `    }` | Ends the loop of line 187. |
| 203 | `    sigaction(SIGSEGV, &old, NULL);` | Restores the `SIGSEGV` setting from before. |
| 204 | `    unguard(t.a, n);` | Releases the buffer. |
| 205 | `}` | Ends the function `test_touch`. |

### Functions `trial_check` and `kernel_named` (lines 206 to 224)

| Line | Source | Explanation |
|---:|---|---|
| 207 | `static void trial_check(int ok, const char *what, size_t bytes)` | Starts the function `trial_check`. It works like `check` (line 75), for a check that belongs to no single kernel. |
| 208 | `{` | Opens the body of `trial_check`. |
| 209 | `    printf("trial,%s,%zu,%s\n", what, bytes, ok ? "pass" : "FAIL");` | Prints one row with four fields: the word `trial`, the name of the check (`what`), a number of bytes, and `pass` or `FAIL`. |
| 210 | `    if (!ok)` | When the check failed ... |
| 211 | `        failures++;` | ... adds 1 to `failures`. The self-test continues. |
| 212 | `}` | Ends the function `trial_check`. |
| 214 | `static int kernel_named(const char *name)` | Starts the function `kernel_named`. It returns the index of the kernel with this name in the table `kernels[]`. |
| 215 | `{` | Opens the body of `kernel_named`. |
| 216 | `    int k = 0;` | `k`: the index, from 0. |
| 217 | `    while (k < K_COUNT && strcmp(name, kernels[k].name))` | Goes through the table until the name is equal (`strcmp` returns 0 then) or the table ends. `K_COUNT` is the number of entries of `kernels[]`. |
| 218 | `        k++;` | Goes to the next entry. |
| 219 | `    if (k == K_COUNT) {` | Tests whether the table ended. Then no kernel has the name. |
| 220 | `        fprintf(stderr, "selftest: no kernel %s\n", name);` | Prints the message `selftest: no kernel` with the name to the error output. |
| 221 | `        exit(2);` | Ends the process with exit status 2. |
| 222 | `    }` | Ends the `if` of line 219. |
| 223 | `    return k;` | Returns the index. |
| 224 | `}` | Ends the function `kernel_named`. |

### Function `test_trial`: the records of one trial (trial mode) (lines 225 to 297)

| Line | Source | Explanation |
|---:|---|---|
| 226 | `/* The trial mode on a guarded buffer of 1 MiB whose words all hold w.v. */` | Comment: `test_trial` runs the trial mode on a guarded buffer of 1 MiB whose words all hold the value `w.v`. |
| 227 | `static void test_trial(void)` | Starts the function `test_trial`. It runs trials on a guarded buffer of 1 MiB through `run_trial` of the runner source, the function that the trial mode uses. A trial is a list of timed windows that run one directly after the other. What it proves: `timed_sequence` writes consistent window records, and the sink check can pass and can fail. What it cannot prove: that the byte count of a window equals the bytes that the kernel read. The checks test multiples, not the number of kernel calls. It also cannot prove anything about the timing code of the interval mode. That code is the function `worker` of the runner source, and no check of this file runs it. |
| 228 | `{` | Opens the body of `test_trial`. |
| 229 | `    size_t bytes = 1UL << 20, n = bytes / 8;` | `bytes`: the buffer size, 1 MiB (1048576 bytes). `n`: the same size in words (131072 words of 8 bytes). |
| 230 | `    int oldread = kernel_named("oldread"), rd = kernel_named("read"), asmread = kernel_named("asmread");` | The indexes of three kernels in `kernels[]`: `oldread` (the old read kernel), `read` (the new read kernel, kept in the variable `rd`) and `asmread`. |
| 231 | `    struct trial p = { .nwin = 3, .win_ms = 12, .count = CS_CLOSED, .bins = 1,` | `p`: the plan of the trial (`struct trial` of the runner source). `.nwin = 3`: 3 target windows. `.win_ms = 12`: the requested duration of each target window is 12 ms. A window ends at the first clock read at or after its requested duration. So it lasts at least that long. `.count = CS_CLOSED`: the trial opens no counter group. `.bins = 1`: bins are on. |
| 232 | `                       .prev = { asmread, bytes, 4 }, .pfx = { oldread, bytes, 8 },` | Continues the plan. `.prev`: 1 window of previous activity, `asmread` on 1 MiB for 4 ms. `.pfx`: 4 prefix windows of `oldread` on 1 MiB, 8 ms for all four, so 2 ms each. |
| 233 | `                       .pred = { rd, 65536, 3 }, .tgt = { oldread, bytes, 0 } };` | Ends the plan. `.pred`: 1 predecessor window, `read` on 65536 B for 3 ms. `.tgt`: the target windows run `oldread` on 1 MiB. The 0 is the time field. A target window does not use it: its time is `win_ms`. |
| 234 | `    struct win win[9];` | `win`: the 9 window records of the trial. A window record holds the plan and the result of one window. |
| 235 | `    struct bin bin[9]; /* 3 target windows, window_bins() = 3 each */` | `bin`: storage for 9 bins. Comment: there are 3 target windows, and `window_bins` gives room for 3 bins in each. |
| 236 | `    struct trec r = { .win = win, .nw = trial_windows(&p) };` | `r`: the record of the trial (`struct trec` of the runner source). It points to the window records. `nw` is the number of windows that `trial_windows` of the runner source computes from the plan. |
| 237 | `    struct tw w;` | `w`: the worker record (`struct tw` of the runner source). It holds the state of the thread that runs the trials: the buffer, the counter group and the trace. In the self-test the main thread runs the trials. |
| 238 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum that an old read kernel returns. |
| 239 | `    int whole = 1, groups = 1, lasts = 1, order = 1, bins_ok = 1;` | Five result flags, one per check of the loop of lines 252 to 266. Each starts as 1. The value 1 stands for passed. |
| 241 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 242 | `    w.t.group_fd = -1;` | `group_fd = -1`: the worker has no counter group. |
| 243 | `    w.v = 0x9E3779B97F4A7C15ULL * 7;` | `w.v`: the value that every word of the buffer gets. `run_trial` computes the expected sum of an old read as `w.v` times the number of words. |
| 244 | `    w.t.a = guarded(n);` | The buffer of the worker: a guarded buffer of 1 MiB. |
| 245 | `    for (size_t i = 0; i < n; i++)` | Loop over all words of the buffer. |
| 246 | `        w.t.a[i] = w.v;` | Every word of the buffer gets the same value `w.v`. This is also the first write to the new buffer, outside every timed window. |
| 248 | `    trial_check(r.nw == 9 && window_bins(&p) == 3, "prev 1 + prefix 4 + pred 1 + target 3 windows", bytes);` | First check: the plan gives 9 windows (1 + 4 + 1 + 3), and a target window has room for 3 bins: 1 bin for the 10 ms that end inside the 12 ms, 1 bin for the end of the window, and 1 spare bin. |
| 249 | `    set_windows(&p, win, bin);` | `set_windows` of the runner source fills the plan fields of the 9 window records: kernel, range size, passes between two clock reads, duration and bin storage. |
| 250 | `    printf("call,trial,%zu\n", bytes);` | Prints the line `call,trial,1048576` before the trial runs. |
| 251 | `    run_trial(&w, &p, &r, &sink);` | `run_trial` runs the 9 windows through `timed_sequence` and then sets `r.sink_ok`. In `timed_sequence` each window reads the clock at its start and again after each group of passes. The window ends at the first clock read at or after its duration. |
| 252 | `    for (int i = 0; i < r.nw; i++) {` | Loop over the 9 window records after the trial. |
| 253 | `        const struct win *x = &win[i];` | `x`: the record of window `i`. |
| 254 | `        whole &= x->bytes > 0 && x->bytes % x->size == 0;` | `whole`: the window counted more than 0 bytes, and a multiple of its range size. |
| 255 | `        groups &= x->bytes % CHECK_BYTES == 0; /* every size here divides 8 MiB */` | `groups`: the bytes are a multiple of 8 MiB (`CHECK_BYTES`). The window loop reads the clock after each 8 MiB. Comment: every range size of this plan divides 8 MiB. |
| 256 | `        lasts &= x->t_end - x->t_start >= x->dur_ns;` | `lasts`: end time minus start time is at least the requested duration. All three values are in ns. |
| 257 | `        order &= x->t_end > x->t_start && (i == 0 \|\| x->t_start >= win[i - 1].t_end);` | `order`: the end is later than the start, and the start is not earlier than the end of the window before. |
| 258 | `        if (x->phase == PH_TARGET) {` | Branch for a target window. |
| 259 | `            bins_ok &= x->nbin >= 1 && x->nbin <= x->bin_cap && x->bin[x->nbin - 1].bytes == x->bytes &&` | `bins_ok`, target window: it has 1 to `bin_cap` bins, and the last bin holds the bytes of the window ... |
| 260 | `                       x->bin[x->nbin - 1].t_end == x->t_end;` | ... and the end time of the window. |
| 261 | `            for (int b = 1; b < x->nbin; b++)` | Loop over the bins after the first one. |
| 262 | `                bins_ok &= x->bin[b].t_end > x->bin[b - 1].t_end && x->bin[b].bytes > x->bin[b - 1].bytes;` | Time and bytes must rise from bin to bin. |
| 263 | `        } else {` | Branch for every other window. |
| 264 | `            bins_ok &= x->nbin == 0;` | `bins_ok`, other window: it has no bin. |
| 265 | `        }` | Ends the `if` of line 258. |
| 266 | `    }` | Ends the loop of line 252. |
| 267 | `    trial_check(whole, "every window holds whole passes and more than 0 bytes", bytes);` | Prints the result of `whole`, the first of the five results of the loop. |
| 268 | `    trial_check(groups, "every window holds a multiple of 8 MiB (clock read after 8 MiB)", bytes);` | Prints the result of `groups`. |
| 269 | `    trial_check(lasts, "every window lasts at least its requested duration", bytes);` | Prints the result of `lasts`. |
| 270 | `    trial_check(order, "timestamps do not go back from window to window", bytes);` | Prints the result of `order`. |
| 271 | `    trial_check(bins_ok, "the last bin of a target window ends the window and holds its bytes", bytes);` | Prints the result of `bins_ok`. |
| 272 | `    trial_check(r.sink_ok == 1, "sink holds the sum after a trial that ends in old read", bytes);` | One more check: `r.sink_ok` is 1. So after a trial that ends with `oldread`, the sink holds the expected sum. |
| 274 | `    p.tgt.k = rd;` | Second trial: the target kernel is now `read`, the new read kernel. |
| 275 | `    set_windows(&p, win, bin);` | Fills the window records again from the changed plan. |
| 276 | `    run_trial(&w, &p, &r, &sink);` | Runs the second trial. |
| 277 | `    trial_check(r.sink_ok == 1, "sink holds the sum of the last old read when the target is new read", bytes);` | The last old read is now a prefix window. `sink_ok` must still be 1. So the `read` windows after it left the sink unchanged. |
| 279 | `    p.pfx.k = asmread;` | Third trial: the prefix kernel is now `asmread` too. So the trial holds no old read. |
| 280 | `    set_windows(&p, win, bin);` | Fills the window records again. |
| 281 | `    run_trial(&w, &p, &r, &sink);` | Runs the third trial. |
| 282 | `    trial_check(r.sink_ok == -1, "sink check is NA for a trial without old read", bytes);` | `sink_ok` must be -1. This value stands for not applicable. |
| 284 | `    /* The sink check must be able to fail: one changed word changes the sum. */` | Comment: the sink check must be able to fail. One changed word changes the sum. |
| 285 | `    p.tgt.k = oldread;` | Fourth trial: the target is `oldread` again. |
| 286 | `    w.t.a[n - 1] ^= 1;` | Flips the lowest bit of the last word of the buffer. The sum now differs from the expected sum by 1. |
| 287 | `    set_windows(&p, win, bin);` | Fills the window records again. |
| 288 | `    run_trial(&w, &p, &r, &sink);` | Runs the fourth trial. |
| 289 | `    trial_check(r.sink_ok == 0, "sink check fails after one word of the buffer is changed", bytes);` | So `sink_ok` must be 0. This proves that the sink check can fail, and that `oldread` reads the last word of its range. |
| 291 | `    struct counts c[3] = { { .enabled = 0, .running = 0 }, { .enabled = 100, .running = 100 }, { .enabled = 200, .running = 150 } };` | `c`: three counter readings that are written here. They stand for the borders of two target windows. `enabled` and `running` are the times in ns for which the counter group was enabled and for which it ran. In target window 1 (the second one, the count starts at 0) the counters ran 50 ns of 100 ns. |
| 292 | `    trial_check(first_multiplexed(c, 2) == 1, "running time below enabled time is found in target window 1", 0);` | Checks `first_multiplexed` of the runner source on the three readings. It must return 1: the index of the first target window whose counters ran for less time than they were enabled. |
| 293 | `    c[2].running = 200;` | Makes the running time of target window 1 equal to its enabled time. |
| 294 | `    trial_check(first_multiplexed(c, 2) == -1, "equal running and enabled time is not called multiplexed", 0);` | With equal times `first_multiplexed` must return -1. |
| 295 | `    unguard(w.t.a, n);` | Releases the buffer. |
| 296 | `}` | Ends the function `test_trial`. |

### Functions `has_line` and `emitted`: the text that `emit_trial` prints (lines 298 to 328)

| Line | Source | Explanation |
|---:|---|---|
| 298 | `static int has_line(const char *text, const char *line)` | Starts the function `has_line`. It is true when `text` holds `line` as a whole line. |
| 299 | `{` | Opens the body of `has_line`. |
| 300 | `    size_t n = strlen(line);` | `n`: the length of `line` in characters. |
| 301 | `    for (const char *s = text; (s = strstr(s, line)) != NULL; s += n)` | `strstr` finds the next place in the text that holds `line`. The loop goes from match to match until there is no more. |
| 302 | `        if ((s == text \|\| s[-1] == '\n') && s[n] == '\n')` | The match counts when it starts at the text start or directly after a line end, and a line end follows it. |
| 303 | `            return 1;` | Then the result is 1. |
| 304 | `    return 0;` | No such match: the result is 0. |
| 305 | `}` | Ends the function `has_line`. |
| 307 | `/* The text that emit_trial() prints for the record r of the trial p. stdout` | Comment: `emitted` returns the text that `emit_trial` prints for the record `r` of the trial `p`. The standard output ... |
| 308 | ` * is a memory stream during the call (glibc lets a program assign stdout). */` | Comment: ... is a memory stream during the call. The C library glibc lets a program assign `stdout`. |
| 309 | `static char *emitted(struct tw *w, struct trial *p, struct trec *r)` | Starts the function `emitted`. It returns the text that `emit_trial` of the runner source prints for a given plan and record. |
| 310 | `{` | Opens the body of `emitted`. |
| 311 | `    char *text = NULL;` | `text`: will point to the printed text. |
| 312 | `    size_t len = 0;` | `len`: will hold its length in bytes. |
| 313 | `    FILE *out = stdout, *mem = open_memstream(&text, &len);` | `out`: keeps the real standard output. `mem`: a stream that writes into memory (`open_memstream`). The C library sets `text` and `len` when the stream is flushed or closed. |
| 314 | `    if (!mem) {` | Tests whether the stream could not be opened. |
| 315 | `        perror("open_memstream");` | On failure: prints the word `open_memstream` and the reason. |
| 316 | `        exit(2);` | On failure: the process ends with exit status 2. |
| 317 | `    }` | Ends the `if` of line 314. |
| 318 | `    fflush(out);` | Writes out what the real standard output still holds in its buffer. |
| 319 | `    plan.tr = p;` | Points the global `plan.tr` to the test plan ... |
| 320 | `    rec = r;` | ... and the global `rec` to the test record. So `emit_trial(w, 0)` prints trial 0 from them. |
| 321 | `    stdout = mem;` | Replaces `stdout` by the memory stream. |
| 322 | `    emit_trial(w, 0);` | `emit_trial` prints the rows of trial 0. They go into memory, not to the output of the self-test. |
| 323 | `    stdout = out;` | Restores the real `stdout`. |
| 324 | `    fclose(mem);` | Closes the memory stream. After this `text` holds the whole printed text. |
| 325 | `    plan.tr = NULL;` | Sets `plan.tr` back to `NULL` ... |
| 326 | `    rec = NULL;` | ... and `rec` back to `NULL`. |
| 327 | `    return text;` | Returns the printed text. The caller frees it. |
| 328 | `}` | Ends the function `emitted`. |

### Function `test_emit`: the output rows of one trial (lines 329 to 378)

| Line | Source | Explanation |
|---:|---|---|
| 330 | `/* emit_trial() on a record with known values. Every value differs from the` | Comment: `test_emit` runs `emit_trial` on a record with known values. Every value differs from the ... |
| 331 | ` * value of the field beside it, so a row that prints the wrong field fails. */` | Comment: ... value of the field beside it. So a row that prints the wrong field fails. The record does not keep this rule in one place: reading 0 and reading 1 hold the same value for the enabled time and for the running time (lines 342 to 343). So the first C row must show 100 ns in both fields (line 357). The second C row must show 100 ns and 50 ns. So the check still fails for a row that swaps the two fields. |
| 332 | `static void test_emit(void)` | Starts the function `test_emit`. It writes a trial record by hand: 1 predecessor window, 2 target windows, three counter readings, two page snapshots, CPU times and context-switch counts. The record holds three intended defects: no huge-page value in the second snapshot (-1), counters that ran 50 ns of 100 ns in target window 1, and `sink_ok = 0`. What it proves: `emit_trial` prints the values of this record in the right fields of the C, P, E and X rows. What it cannot prove: anything about the rows of the interval mode. In the runner source only the trial mode calls `emit_trial`. The W rows are printed here, and no check compares them. |
| 333 | `{` | Opens the body of `test_emit`. |
| 334 | `    int oldread = kernel_named("oldread");` | The index of the kernel `oldread` in `kernels[]`. |
| 335 | `    struct trial p = { .nwin = 2, .count = CS_READ };` | `p`: the plan. It has 2 target windows and the counter state `CS_READ`: the timed sequence reads the counter group at the borders of the target windows. |
| 336 | `    struct win win[3] = {` | `win`: three window records, written by hand. |
| 337 | `        { .k = oldread, .phase = PH_PRED, .widx = 0, .size = 4096, .bytes = 8192, .t_start = t_base_ns + 1000, .t_end = t_base_ns + 2000 },` | Window 0, the predecessor window: kernel `oldread`, range size 4096 B, 8192 bytes counted, start 1000 ns and end 2000 ns after `t_base_ns`. `t_base_ns` is the clock value at the start of the process. The rows print times relative to it. |
| 338 | `        { .k = oldread, .phase = PH_TARGET, .widx = 0, .size = 4096, .bytes = 12288, .t_start = t_base_ns + 2100, .t_end = t_base_ns + 3100 },` | Window 1, target window 0: 12288 bytes, from 2100 ns to 3100 ns. It starts 100 ns after the end of the predecessor window. |
| 339 | `        { .k = oldread, .phase = PH_TARGET, .widx = 1, .size = 4096, .bytes = 16384, .t_start = t_base_ns + 3400, .t_end = t_base_ns + 4400 },` | Window 2, target window 1: 16384 bytes, from 3400 ns to 4400 ns. It starts 300 ns after the end of target window 0. |
| 340 | `    };` | Ends the three window records. |
| 341 | `    /* three readings; the second window ran its counters for 50 of 100 ns */` | Comment: three counter readings follow. The second target window ran its counters for 50 ns of 100 ns. |
| 342 | `    struct counts c[3] = { { .cpu_ns = 500, .enabled = 1000, .running = 1000, .val = { 70 } },` | `c`: the three counter readings. Reading 0: thread CPU time 500 ns, enabled time 1000 ns, running time 1000 ns, event count 70. |
| 343 | `                           { .cpu_ns = 800, .enabled = 1100, .running = 1100, .val = { 75 } },` | Reading 1: thread CPU time 800 ns, enabled time 1100 ns, running time 1100 ns, event count 75. |
| 344 | `                           { .cpu_ns = 1400, .enabled = 1200, .running = 1150, .val = { 82 } } };` | Reading 2: thread CPU time 1400 ns, enabled time 1200 ns, running time 1150 ns, event count 82. So between reading 1 and reading 2 the counters were enabled for 100 ns and ran for 50 ns. This is the second intended defect. |
| 345 | `    struct trec r = { .win = win, .nw = 3, .cnt = c, .pg = { { 8192, 4096 }, { 8192, -1 } },` | `r`: the trial record. It has the 3 windows, the readings `c`, and two page snapshots. The first snapshot: 8192 kB, of them 4096 kB in huge pages. The second: 8192 kB and -1, which stands for no huge-page value. This is the first intended defect. |
| 346 | `                      .vm = { { 1, 2, 3, 4 }, { 5, 6, 7, 8 } }, .cpu = { 10000, 13000 },` | Continues the record: the four counters of `/proc/vmstat` in each snapshot (1 to 4, then 5 to 8), and the thread CPU time before and after the timed sequence (10000 ns and 13000 ns). |
| 347 | `                      .nvcsw = { 5, 7 }, .nivcsw = { 10, 13 }, .state = CS_READ, .sink_ok = 0 };` | Ends the record: 5 and 7 voluntary context switches before and after, 10 and 13 involuntary ones, the counter state `CS_READ`, and `sink_ok = 0`. The value 0 says that the sink check failed. This is the third intended defect. |
| 348 | `    struct tw w;` | `w`: a worker record for `emit_trial`. |
| 349 | `    int nev = cfg.nev;` | `nev`: keeps the value of `cfg.nev`, the number of counter events in the configuration of the runner. |
| 350 | `    char *text;` | `text`: the printed text. |
| 352 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 353 | `    w.t.group_fd = 0; /* emit_trial() only asks whether a group is open */` | `group_fd = 0` makes `emit_trial` treat the counter group as open. Comment: `emit_trial` only asks whether a group is open. |
| 354 | `    w.t.nopen = 1;` | One event counts as open. |
| 355 | `    cfg.nev = 1;` | `cfg.nev = 1` makes `emit_trial` print one event column. |
| 356 | `    text = emitted(&w, &p, &r);` | Gets the text that `emit_trial` prints for this record. |
| 357 | `    trial_check(has_line(text, "C,0,0,100,100,300,5") && has_line(text, "C,0,1,100,50,600,7"),` | The C rows must be `C,0,0,100,100,300,5` and `C,0,1,100,50,600,7`. After the trial number and the window number come four differences of two readings: enabled time, running time, thread CPU time (all in ns) and the event count. |
| 358 | `                "C rows hold the differences of two readings", 0);` | Continues the call of line 357: the name of the check, and 0 for the bytes field. |
| 359 | `    trial_check(has_line(text, "P,0,pre,8192,4096,1,2,3,4") && has_line(text, "P,0,post,8192,NA,5,6,7,8"),` | The P rows must be `P,0,pre,8192,4096,1,2,3,4` and `P,0,post,8192,NA,5,6,7,8`. The row with `pre` holds the first snapshot. The row with `post` holds the second, with `NA` for the missing huge-page value. |
| 360 | `                "P rows: pre holds the first snapshot and post the second", 0);` | Continues the call of line 359: the name of the check. |
| 361 | `    trial_check(has_line(text, "E,0,3400,3000,2,3,100,300,0,read"),` | The E row must be `E,0,3400,3000,2,3,100,300,0,read`: wall time 3400 ns, CPU time 3000 ns, 2 voluntary and 3 involuntary context switches, a gap of 100 ns before the first target window, a largest gap of 300 ns, sink check 0, counter state `read`. |
| 362 | `                "E row holds wall time and CPU time and both switch counts and both gaps each in its own field", 0);` | Continues the call of line 361: the name of the check. |
| 363 | `    trial_check(strstr(text, "\nX,0,coverage_na,") != NULL, "X row coverage_na when a snapshot has no huge-page value", 0);` | X row for defect 1: the text must hold a line that starts with `X,0,coverage_na,`. |
| 364 | `    trial_check(strstr(text, "\nX,0,count_multiplexed,target window 1: running_ns 50 below enabled_ns 100\n") != NULL,` | X row for defect 2: the text must hold the line `X,0,count_multiplexed,target window 1: running_ns 50 below enabled_ns 100`. |
| 365 | `                "X row count_multiplexed names the window that ran its counters for less time", 0);` | Continues the call of line 364: the name of the check. |
| 366 | `    trial_check(strstr(text, "\nX,0,sink,") != NULL, "X row sink when the sink check failed", 0);` | X row for defect 3: the text must hold a line that starts with `X,0,sink,`. |
| 367 | `    free(text);` | Frees the text. |
| 369 | `    /* The same record without the three defects must print no X row. */` | Comment: the same record without the three defects must print no X row. |
| 370 | `    r.pg[1].kb_huge = 4096;` | Removes defect 1: the second snapshot gets a huge-page value of 4096 kB. |
| 371 | `    c[2].running = 1200;` | Removes defect 2: the running time of reading 2 becomes 1200 ns. So the counters of target window 1 ran for the whole 100 ns. |
| 372 | `    r.sink_ok = 1;` | Removes defect 3: the sink check counts as passed. |
| 373 | `    text = emitted(&w, &p, &r);` | Prints the record again into a new text. |
| 374 | `    trial_check(strstr(text, "\nX,") == NULL && has_line(text, "E,0,3400,3000,2,3,100,300,1,read"),` | The text must now hold no line that starts with `X,`, and the E row must show sink check 1: `E,0,3400,3000,2,3,100,300,1,read`. |
| 375 | `                "no X row for a record without a defect", 0);` | Continues the call of line 374: the name of the check. |
| 376 | `    free(text);` | Frees the text. |
| 377 | `    cfg.nev = nev;` | Restores `cfg.nev`. |
| 378 | `}` | Ends the function `test_emit`. |

### Function `selftest`: the entry point of the option `--selftest` (lines 379 to 405)

| Line | Source | Explanation |
|---:|---|---|
| 380 | `static int selftest(void)` | Starts the function `selftest`. `main` of the runner source calls it for the argument `--selftest` and returns its value as the exit status. The self-test runs in the main thread and computes no rate. Only the checks of the trial mode read the clock. |
| 381 | `{` | Opens the body of `selftest`. |
| 382 | `    setvbuf(stdout, NULL, _IOLBF, 0); /* a kernel that faults must not take the earlier lines with it */` | `setvbuf` with `_IOLBF` makes the output line-buffered: each line is written when it is complete. So a kernel that ends the process cannot remove earlier lines. |
| 383 | `    printf("# selftest: page_bytes=%ld kernels=%d (%s); columns: kernel,check,bytes,result\n", page_bytes, K_COUNT,` | Prints the header line. It gives the page size in bytes, the number of kernels and the kind of build (line 384). It also names the four columns of a result row: `kernel`, `check`, `bytes`, `result`. |
| 384 | `           STANDIN ? "STAND-IN kernels, not AArch64" : "aarch64");` | Continues the call of line 383: the kind of build. The text is `aarch64` for a build with the real kernels. It is `STAND-IN kernels, not AArch64` for a build on a machine that is not AArch64 (the 64-bit Arm instruction set). There plain C loops take the place of the NEON and asm kernels. |
| 385 | `    if (page_bytes % 256 != 0) {` | A page size that is not a multiple of 256 B ... |
| 386 | `        fprintf(stderr, "page size is not a multiple of 256\n");` | ... prints a message to the error output ... |
| 387 | `        return 2;` | ... and ends the self-test with the value 2. |
| 388 | `    }` | Ends the `if` of line 385. |
| 389 | `    /* whole buffers of 1 page, 3 pages and 1 MiB */` | Comment: `test_size` gets whole buffers of 1 page, 3 pages and 1 MiB. |
| 390 | `    size_t words[] = { (size_t)page_bytes / 8, 3 * (size_t)page_bytes / 8, (1UL << 20) / 8 };` | `words`: the three buffer sizes of `test_size`, in words of 8 bytes: 1 page, 3 pages and 1 MiB. With a page of 4096 B these are 4096 B, 12288 B and 1048576 B. |
| 391 | `    /* one block: at the start of a page (guard before it) and at the end (guard after it) */` | Comment: `test_block` gets one block at the start of a page, with a guard page before it, and one at the end, with a guard page after it. |
| 392 | `    size_t offs[] = { 0, (size_t)page_bytes / 8 - 32 };` | `offs`: the two block offsets of `test_block`, in words: 0 for the first 256 B of a page, and the page size minus 32 words for the last 256 B. |
| 393 | `    for (int k = 0; k < K_COUNT; k++) {` | The loop takes every kernel in the order of `kernels[]`. |
| 394 | `        for (size_t i = 0; i < sizeof words / sizeof words[0]; i++)` | Loop over the three sizes of `words`. |
| 395 | `            test_size(&kernels[k], words[i]);` | Per kernel: `test_size` with each of the three sizes. |
| 396 | `        for (size_t i = 0; i < 2; i++)` | Loop over the two block offsets. |
| 397 | `            test_block(&kernels[k], offs[i]);` | Per kernel: `test_block` at each of the two offsets. |
| 398 | `        if (is_read(&kernels[k]))` | For a read kernel in addition ... |
| 399 | `            test_touch(&kernels[k]);` | ... `test_touch`. |
| 400 | `    }` | Ends the loop of line 393. |
| 401 | `    test_trial();` | Then the checks of the trial mode follow. The first is `test_trial`. |
| 402 | `    test_emit();` | `test_emit`: the output rows of a trial. |
| 403 | `    printf("# failures=%d\n", failures);` | The last line of the output is `# failures=N`, with the count of the failed checks for N. CRB build: 181 rows end with `pass`, no line holds `FAIL`, and the last line is `# failures=0` [Ref1]. |
| 404 | `    return failures ? 1 : 0;` | Return value: 1 if a check failed, else 0. `main` of the runner source returns it as the exit status. The build script of the runner ends with exit status 4 when the value is not 0. |
| 405 | `}` | Ends the function `selftest`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/selftest-bwx8.txt`: the self-test output of the CRB build, 319 lines. The first line is `# selftest: page_bytes=4096 kernels=21 (aarch64); columns: kernel,check,bytes,result`. 136 lines begin with `call,`. 181 rows end with `pass`. No line holds `FAIL`. The last line is `# failures=0`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/build.txt`: the record of the CRB build. It holds the line `## selftest bwx8 exit=0 # failures=0`. Its sha256 value of `bwx8_selftest.c` begins with `a94d917e`. Computed in this task with `sha256sum`: the file `bwx8_selftest.c` of the code folder has the same value.
- [Ref3] A `diff` in this task of `bwx8_selftest.c` against `bwx_selftest.c`, both of the code repo. It prints four blocks: lines 2 to 6 are changed, and lines 27 to 41, lines 207 to 378 with the blank line after them, and lines 401 to 402 stand in `bwx8_selftest.c` only.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "CRB acceptance, 2026-11-15" names the build `crb-build-1` with a sha256 of `bwx8` that begins with `f84be912`, and says that the self-test ends with `failures=0`. `build.txt` of the build record holds the same sha256 of `bwx8`.
