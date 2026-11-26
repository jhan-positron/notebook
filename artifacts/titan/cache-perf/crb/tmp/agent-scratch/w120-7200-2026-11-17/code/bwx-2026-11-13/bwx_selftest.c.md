# `bwx_selftest.c` explained, line by line

- Source file: `bwx-2026-11-13/bwx_selftest.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 214 lines, 8273 bytes).
- sha256 of the source when this page was built: `1c25fc53f4dbbf742b487134f9814cf2035ff5f92da8b083a74acf3a40d0d21d`.

## Short version: purpose

This file is the self-test of the first runner `bwx`: it checks what each of the 21 kernels does to memory. It runs only when a binary of `bwx` is started with `--selftest`, which the build script `build.sh` does once for each of its four binaries. The self-test of the next runner version, `bwx8_selftest.c`, keeps these kernel checks unchanged and adds checks of the trial mode, which `bwx` does not have.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx.c`. It includes this file with `#include`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Kind**: the type of a kernel in the table `kernels[]` of the runner source: `T_READ` (a read kernel that returns nothing), `T_OLDREAD` (a read kernel that returns a sum), `T_WRITE` or `T_COPY`.
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Objdump listing**: the name that the comments of this file use for the machine-code listing.
- **Word**: 8 bytes, one `uint64_t`.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Page, `page_bytes`**: the unit of memory protection. `page_bytes` holds its size in bytes. It was 4096 B in the self-tests of CRB build 1 [Ref1].
- **`PROT_NONE` page**: a page that the process may neither read nor write. A load from it or a store to it is a fault.
- **Fault, `SIGSEGV`**: a fault is a forbidden memory access. Linux answers it with the signal `SIGSEGV`. Without a handler the signal ends the process.
- **Guarded buffer, guard page**: a guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one directly after it. These two pages are the guard pages.
- **Stand-in kernels**: on a machine that is not AArch64 (the 64-bit Arm instruction set), plain C loops take the place of the NEON and asm kernels. The header line of the self-test output says which build ran.
- **Nop, vector add**: a nop is an instruction that does nothing. A vector add adds two vector registers. Neither of the two changes memory.
- **d8 to d15**: the low halves of the Arm vector registers v8 to v15. The Arm calling convention requires that a function gives them back unchanged.
- **Build records, CRB build 1, CRB build 2**: the build records are the folders `bwx-crb-build-1` and `bwx-crb-build-2` of the test data. Each holds files that one run of the build script `build.sh` wrote on 2026-11-13 [Ref2]. This page calls the two runs CRB build 1 and CRB build 2. Only the record of CRB build 1 holds self-test outputs.
- **`build.sh`**: the build script of `bwx`. It compiles `bwx.c` into the four binaries `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`, runs each with `--selftest`, and writes the machine-code listing.
- **Rate**: bytes divided by time, in GB/s.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `bwx.c` includes this file directly before its `main`. `main` reads the page size into `page_bytes`, removes the CPUs above 119 from the allowed set of the process, and calls `selftest` when an argument is `--selftest`. In every other case no function of this file runs (line 191).
2. `selftest` makes the output line-buffered, prints the header line, and stops with the value 2 if the page size is not a multiple of 256 B (lines 193 to 199).
3. It sets the three buffer sizes (1 page, 3 pages, 1 MiB) and the two block offsets (first and last 256 B of a page) (lines 200 to 203).
4. For each of the 21 kernels: `test_size` on the three sizes, `test_block` at the two offsets, and for a read kernel `test_touch` (lines 204 to 211).
5. `selftest` prints `# failures=N` and returns 1 if a check failed, else 0. `main` returns this value as the exit status (lines 212 to 213).
6. `build.sh` stores the output of each binary in a file `selftest-<binary>.txt`. It stops the build with exit status 4 when the exit status of a self-test is not 0.

## Behavior a reader must know

- The self-test runs only with the option `--selftest`. `build.sh` starts it once per binary after the build. A timed run starts the runner with `--seq`. So no function of this file runs between two clock reads of a timed run.
- The self-test computes no rate, and no function of this file reads the clock.
- Result of CRB build 1: each of the four self-test outputs has 299 lines, 162 rows that end with `pass`, no `FAIL` line, and the last line `# failures=0`. The header line says `page_bytes=4096 kernels=21 (aarch64)` [Ref1]. `build.txt` of both CRB builds holds four lines with `exit=0 # failures=0`, and its sha256 value of `bwx_selftest.c` is the value of the file explained here [Ref2].
- What the checks prove for a read kernel: the buffer is unchanged, no byte within one page outside the test buffer is loaded or stored, and at least one byte of each page of a range of 3 pages is accessed. For `oldread` and `oldread2` in addition: the returned sum equals the sum of all words.
- What the checks cannot prove. They see three things only: the content of memory after the call, a fault, and the sum that an old read kernel returns. They cannot see which bytes inside a page a read kernel without return value loads, a nop, the order of loads and stores, the speed, or the saving of the registers d8 to d15. By the file comment the objdump listing is the evidence for the bytes that a read kernel loads (lines 21 to 25).
- By a note of the project, two checks go beyond the model `selftest.c`: the fault check of `test_touch` for every read kernel, and the sum check for `oldread` and `oldread2` [Ref3].
- No check runs the timing code of the runner. The byte count, the clock reads and the stop rule of the function `worker` of the runner source are not tested by this file.
- In `test_size` and `test_block` no `SIGSEGV` handler is installed. A kernel that loads from or stores to a `PROT_NONE` page there ends the process. No result line follows, and the last `call` line of the output names the kernel.
- A failed check does not stop the self-test. It adds 1 to `failures`, and the exit status becomes 1.
- The self-test runs in the main thread and starts no other thread. It pins no thread to one CPU. The test buffers come from `guarded`: plain `mmap` memory, with no request for huge pages.
- On a machine that is not AArch64 the self-test checks the stand-in kernels, not the real ones. The header line of the output says which kernels ran.

## Source and explanation, line by line

- Text shown: the file `bwx-2026-11-13/bwx_selftest.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (214 lines, 8273 bytes, sha256 `1c25fc53f4dbbf742b487134f9814cf2035ff5f92da8b083a74acf3a40d0d21d`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### File comment: what the self-test checks, and its limits (lines 1 to 26)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Opens the file comment (lines 1 to 26). It says what the self-test checks and what it cannot check. |
| 2 | ` * bwx_selftest.c - "bwx --selftest": checks what every kernel of bwx.c does` | Comment: the purpose. The option `--selftest` of the runner checks what every kernel of the runner source does ... |
| 3 | ` * to memory. bwx.c includes this file, so the test runs the machine code of` | Comment: ... to memory. The runner source includes this file. So the test runs the machine code of ... |
| 4 | ` * the binary that is timed, through the same call() as the benchmark.` | Comment: ... the binary that is timed, through the same function `call` as the benchmark. So the self-test and a timed run are one binary, and both reach a kernel through `call` and the table `kernels[]`. |
| 5 | ` * Model: kernels-2026-11-13/selftest.c.` | Comment: the model of this file is `selftest.c` in the folder `kernels-2026-11-13`. By its header comment that file checks what the six kernels of the benchmark `bandwidth.c` do to memory. By the header comment of the runner source, `bwx.c` is a scratch copy of `bandwidth.c`. |
| 6 | ` *` | Comment: an empty line of the comment. |
| 7 | ` * Every buffer ends at a page that cannot be read or written (PROT_NONE) and` | Comment: every test buffer ends at a page that cannot be read or written (`PROT_NONE`) and ... |
| 8 | ` * starts after one. A kernel that touches a byte within one page before the` | Comment: ... starts after one. A kernel that touches a byte within one page before the ... So a load or a store up to one page outside the buffer is a fault. The fault ends the process, except in `test_touch` (line 160), which installs a handler. |
| 9 | ` * buffer or within one page after it dies with SIGSEGV. The line "call,..."` | Comment: ... buffer or within one page after it ends with `SIGSEGV`. Linux sends this signal for a forbidden memory access. The line `call,...` ... |
| 10 | ` * printed before each kernel call names the kernel that died.` | Comment: ... that is printed before each kernel call (line 56) names the kernel that ended the process. |
| 11 | ` * Exit status 0 means every check passed.` | Comment: exit status 0 means that every check passed. |
| 12 | ` *` | Comment: an empty line of the comment. |
| 13 | ` * Checks for every kernel that stores (write and copy kinds): every word is` | Comment: the checks for every kernel that stores (the write kind and the copy kind): every word is ... |
| 14 | ` * compared, on whole buffers and on one 256 B block at a page start and at a` | Comment: ... compared, on whole buffers (line 72) and on one 256 B block at a page start and at a ... |
| 15 | ` * page end.` | Comment: ... page end (line 117). |
| 16 | ` * Checks for every read kernel: the buffer is unchanged and no guard page is` | Comment: the checks for every read kernel: the buffer is unchanged and no guard page is ... |
| 17 | ` * touched. The kernel must fault when one page inside its range is made` | Comment: ... touched. The kernel must fault when one page inside its range is made ... |
| 18 | ` * PROT_NONE, for each page of a 3-page range. oldread and oldread2 return a` | Comment: ... `PROT_NONE`, for each page of a 3-page range (line 160). The kernels `oldread` and `oldread2` return a ... |
| 19 | ` * sum: it must equal the sum of all words.` | Comment: ... sum. The test compares it with the sum of all words (line 95). |
| 20 | ` *` | Comment: an empty line of the comment. |
| 21 | ` * Limits. For the read kernels that return nothing, the test proves that` | Comment: the limits. The new read kernel `read` and `asmread` return nothing. For such read kernels the test proves that ... |
| 22 | ` * every page of the range is touched, not every byte: the objdump listing is` | Comment: ... every page of the range is touched. It does not prove that every byte is loaded. For the bytes that such a kernel loads, the objdump listing is ... |
| 23 | ` * the evidence for the bytes. It cannot see in which order a copy kernel` | Comment: ... the evidence for the bytes. The test also cannot see in which order a copy kernel ... |
| 24 | ` * loads and stores. It does not check that a kernel preserves the` | Comment: ... loads and stores. And it does not check that a kernel preserves the ... |
| 25 | ` * callee-saved registers d8-d15.` | Comment: ... registers d8 to d15, which the called function must save (callee-saved). |
| 26 | ` */` | Ends the comment. |

### Global variables (lines 27 to 29)

| Line | Source | Explanation |
|---:|---|---|
| 27 | `static int failures;` | `failures`: the count of failed checks. `check` (line 63) adds to it, and `selftest` prints it at the end (line 212). |
| 28 | `static sigjmp_buf fault_jmp;` | `fault_jmp`: the saved place at which `test_touch` continues after a fault (line 177). `sigjmp_buf` is the type of the C library for such a saved place. |
| 29 | `static volatile uintptr_t fault_addr;` | `fault_addr`: the address of the last fault. The handler `on_fault` writes it (line 153). `volatile` tells the compiler to read and write the variable in memory at every use. A variable that a signal handler changes needs this. |

### Functions `guarded` and `unguard`: a buffer between two `PROT_NONE` pages (lines 30 to 47)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `/* n words whose first byte follows a PROT_NONE page and whose last byte` | Comment: `guarded` gives `n` words (8 bytes each) whose first byte follows a `PROT_NONE` page and whose last byte ... |
| 32 | ` * precedes one. n * 8 must be a multiple of the page size. */` | Comment: ... stands directly before one. For this, `n * 8` must be a multiple of the page size. The function does not test it. Every caller in this file passes 1 page, 3 pages or 1 MiB. In CRB build 1 a page has 4096 B [Ref1]. With this page size each of the three sizes is a multiple of the page size. So the last word ends directly before the `PROT_NONE` page. |
| 33 | `static uint64_t *guarded(size_t n)` | Starts the function `guarded`. It returns the address of `n` words of new memory that lie between two `PROT_NONE` pages. The checks of this file take their test buffers from it. The memory comes from a plain `mmap`, with no request for huge pages. |
| 34 | `{` | Opens the body of `guarded`. |
| 35 | `    size_t len = n * 8;` | `len`: the size of the buffer in bytes. |
| 36 | `    uint8_t *raw = mmap(NULL, len + 2 * (size_t)page_bytes, PROT_NONE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `len` bytes plus two pages of new memory. `page_bytes` is the page size in bytes. `main` of the runner source sets it before it calls the self-test. `PROT_NONE`: at first the process may neither read nor write any byte of the range. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. |
| 37 | `    if (raw == MAP_FAILED \|\| mprotect(raw + page_bytes, len, PROT_READ \| PROT_WRITE) != 0) {` | Tests whether `mmap` failed. If it did not fail, `mprotect` makes the `len` bytes after the first page readable and writable. The first page and the last page stay `PROT_NONE`. A return value other than 0 means that `mprotect` failed. |
| 38 | `        perror("guarded");` | On an error: `perror` prints the word `guarded` and the reason that Linux gave. |
| 39 | `        exit(2);` | On an error: the process ends with exit status 2. |
| 40 | `    }` | Ends the `if` of line 37. |
| 41 | `    return (uint64_t *)(raw + page_bytes);` | Returns the address of the first usable byte, one page after the start of the mapping. |
| 42 | `}` | Ends the function `guarded`. |
| 44 | `static void unguard(uint64_t *p, size_t n)` | Starts the function `unguard`. It releases a buffer of `n` words that `guarded` returned. |
| 45 | `{` | Opens the body of `unguard`. |
| 46 | `    munmap((uint8_t *)p - page_bytes, n * 8 + 2 * (size_t)page_bytes);` | `munmap` gives the whole mapping back to Linux: the buffer and its two `PROT_NONE` pages. The mapping starts one page before `p`. |
| 47 | `}` | Ends the function `unguard`. |

### Functions `pattern`, `calling`, `check` and `is_read` (lines 48 to 69)

| Line | Source | Explanation |
|---:|---|---|
| 49 | `static uint64_t pattern(size_t i, uint64_t salt)` | Starts the function `pattern`. It returns the test value of the word with the number `i`. |
| 50 | `{` | Opens the body of `pattern`. |
| 51 | `    return (i + 1) * 0x9E3779B97F4A7C15ULL ^ salt;` | Returns `(i + 1)` times an odd 64-bit constant, then XOR `salt`. The product is computed first. Two different word numbers `i` always give two different values. Two different `salt` values give two different patterns for the same `i`. |
| 52 | `}` | Ends the function `pattern`. |
| 54 | `static void calling(const struct kdef *kd, size_t n)` | Starts the function `calling`. It names a kernel in the output before the kernel runs. `kd` points to the entry of the kernel in `kernels[]`. `n` is the size of the range in words. |
| 55 | `{` | Opens the body of `calling`. |
| 56 | `    printf("call,%s,%zu\n", kd->name, n * 8);` | Prints the line `call,<kernel>,<bytes>`: the word `call`, the kernel name, and the size of the range in bytes (`n * 8`). The output is line-buffered (line 193), so this line is written before the kernel starts. If the kernel ends the process, this line names it. |
| 57 | `}` | Ends the function `calling`. |
| 59 | `static void check(int ok, const struct kdef *kd, const char *what, size_t n)` | Starts the function `check`. It prints the result line of one kernel check. `ok` is not 0 when the check passed. |
| 60 | `{` | Opens the body of `check`. |
| 61 | `    printf("%s,%s,%zu,%s\n", kd->name, what, n * 8, ok ? "pass" : "FAIL");` | Prints one row with four fields: the kernel name, the name of the check (`what`), the size in bytes (`n * 8`), and `pass` or `FAIL`. |
| 62 | `    if (!ok)` | When the check failed ... |
| 63 | `        failures++;` | ... adds 1 to `failures`. The self-test continues after a failed check. |
| 64 | `}` | Ends the function `check`. |
| 66 | `static int is_read(const struct kdef *kd)` | Starts the function `is_read`. It tells whether a kernel is a read kernel. |
| 67 | `{` | Opens the body of `is_read`. |
| 68 | `    return kd->type == T_READ \|\| kd->type == T_OLDREAD;` | True for the two read kinds. By the table `kernels[]` of the runner source, `T_OLDREAD` is the kind of `oldread` and `oldread2`: they return a sum. `oldread2` is a second copy of `oldread`: the same source under another name. `T_READ` is the kind of every other read kernel, for example `read` and `asmread`: they return nothing. |
| 69 | `}` | Ends the function `is_read`. |

### Function `test_size`: one kernel on a whole guarded buffer (lines 70 to 113)

| Line | Source | Explanation |
|---:|---|---|
| 71 | `/* The kernel on a whole guarded buffer of n words. */` | Comment: `test_size` runs the kernel on a whole guarded buffer of `n` words. A guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one directly after it. |
| 72 | `static void test_size(const struct kdef *kd, size_t n)` | Starts the function `test_size`. It runs the kernel once on a whole guarded buffer and reads no clock. `selftest` passes three sizes: 1 page, 3 pages and 1 MiB (line 201). What it proves for every kernel: no load and no store within one page outside its buffers. Such an access ends the process. Read kernel: the buffer is unchanged after the call. Old read kernel: the returned sum equals the sum of all words. Write and copy kernel: every word of the range holds the right value after the call. What it cannot prove: that `read` or `asmread` load anything. A read kernel without a return value that loads nothing passes here. `test_touch` (line 160) checks a part of this. |
| 73 | `{` | Opens the body of `test_size`. |
| 74 | `    struct thread t = { .a = guarded(n), .b = guarded(n) };` | `t`: a thread record in the form that `call` needs (`struct thread` of the runner source). Its buffers `a` and `b` are two guarded buffers of `n` words each. Every other field is 0. |
| 75 | `    uint64_t *a = t.a, *b = t.b, sum = 0;` | `a` and `b`: short names for the two buffers. `sum`: the sum of all words of `a`, built in line 85. |
| 76 | `    uint64_t v = 0xA5A5F00D12345678ULL + n;` | `v`: the value that a write kernel must store in every word. It depends on `n`, so each buffer size gets another value. |
| 77 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum that an old read kernel returns. |
| 78 | `    int ok = 1;` | `ok`: the result of the check that runs now. 1 means passed. |
| 80 | `    /* Every word of the source is different, so a store of the wrong vector` | Comment: every word of the source buffer gets a different value. So a store of the wrong vector ... |
| 81 | `     * or to the wrong offset is seen. */` | Comment: ... or a store to the wrong offset is seen. |
| 82 | `    for (size_t i = 0; i < n; i++) {` | Loop over all `n` words. |
| 83 | `        a[i] = pattern(i, 1);` | Gives every word of `a` its own value: `pattern` with the salt 1. |
| 84 | `        b[i] = 0;` | Sets every word of `b` to 0. |
| 85 | `        sum += a[i];` | `sum` becomes the sum of all words of `a` in 64-bit arithmetic (an overflow wraps). |
| 86 | `    }` | Ends the loop of line 82. |
| 87 | `    calling(kd, n);` | Prints the `call` line (line 56). |
| 88 | `    call(kd, &t, 0, n * 8, v, &sink);` | Runs the kernel on the whole buffer (offset 0, `n * 8` bytes) through `call` of the runner source. `call` chooses the arguments by the kind. A read kernel gets `a`. A write kernel gets `a` and the value `v`, which it stores in every word. A copy kernel reads `a` and writes `b`. The sum that an old read kernel returns goes to `sink`. No `SIGSEGV` handler is installed here. A kernel that loads from or stores to a `PROT_NONE` page ends the process. No result line follows then, and the last `call` line of the output names the kernel. |
| 89 | `    if (is_read(kd)) {` | Branch for a read kernel. |
| 90 | `        /* read: must leave every word as it was (and must not fault) */` | Comment: a read kernel must leave every word as it was, and it must not fault. |
| 91 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 92 | `            ok &= a[i] == pattern(i, 1);` | Every word of `a` must still hold its pattern value. One changed word sets `ok` to 0. |
| 93 | `        check(ok, kd, "buffer unchanged", n);` | Prints the result row with the check name `buffer unchanged`. |
| 94 | `        if (kd->type == T_OLDREAD)` | For the kind `T_OLDREAD` in addition ... |
| 95 | `            check(sink == sum, kd, "returned sum equals the sum of all words", n);` | ... the sum in `sink` must equal `sum`. A kernel that skips one word, or adds one word twice, returns another sum. The check name is `returned sum equals the sum of all words`. |
| 96 | `    } else if (kd->type == T_WRITE) {` | Branch for a write kernel. |
| 97 | `        /* write: every word must hold v afterwards; no word may keep the old pattern */` | Comment: after a write kernel every word must hold `v`. No word may keep the old pattern. |
| 98 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 99 | `            ok &= a[i] == v;` | Every word of `a` must hold `v`. A word that the kernel did not store keeps its pattern value, and no pattern value equals `v`. So a missing store fails the check. |
| 100 | `        check(ok, kd, "every word equals v", n);` | Prints the result row with the check name `every word equals v`. |
| 101 | `    } else {` | Branch for a copy kernel. |
| 102 | `        /* copy: destination must equal source word for word; source unchanged */` | Comment: after a copy kernel the destination must equal the source word for word, and the source must be unchanged. |
| 103 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `b`. |
| 104 | `            ok &= b[i] == pattern(i, 1);` | Every word of `b` must hold the pattern value of the same word of `a`. `b` held 0 before the call. |
| 105 | `        check(ok, kd, "destination equals source", n);` | Prints the first result row of a copy kernel, with the check name `destination equals source`. |
| 106 | `        ok = 1;` | Sets `ok` back to 1 for the second check. |
| 107 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 108 | `            ok &= a[i] == pattern(i, 1);` | Every word of `a` must be unchanged. |
| 109 | `        check(ok, kd, "source unchanged", n);` | Prints the second result row of a copy kernel, with the check name `source unchanged`. |
| 110 | `    }` | Ends the `if` chain of line 89. |
| 111 | `    unguard(a, n);` | Releases the buffer `a` ... |
| 112 | `    unguard(b, n);` | ... and the buffer `b`. |
| 113 | `}` | Ends the function `test_size`. |

### Function `test_block`: 256 B at a page start or at a page end (lines 114 to 147)

| Line | Source | Explanation |
|---:|---|---|
| 115 | `/* One block of 256 B (32 words) at word offset off inside one guarded page.` | Comment: `test_block` runs the kernel on one block of 256 B (32 words) at the word offset `off` inside one guarded page. |
| 116 | ` * Words of the page outside the 256 B must keep their old value. */` | Comment: the words of the page outside the 256 B must keep their old value. |
| 117 | `static void test_block(const struct kdef *kd, size_t off)` | Starts the function `test_block`. It runs the kernel on one block of 256 B (32 words) inside a buffer of one page. 256 B is the smallest range that a kernel may get. With `off` = 0 the block starts directly after the `PROT_NONE` page before the buffer. With the other value of `off` the block ends directly before the `PROT_NONE` page after the buffer (line 203). What it proves for every kernel: no load and no store up to one page before the block start (first case), and none up to one page after the block end (second case). Such an access ends the process. Write and copy kernel: every word of the page outside the block keeps its value. What it cannot prove: which bytes inside the 256 B a read kernel loads. The sum that an old read kernel returns is not compared here. |
| 118 | `{` | Opens the body of `test_block`. |
| 119 | `    size_t n = (size_t)page_bytes / 8, m = 32;` | `n`: the number of words of one page. `m`: the 32 words of the block (256 B). |
| 120 | `    struct thread t = { .a = guarded(n), .b = guarded(n) };` | `t`: a thread record with two guarded buffers of one page each. |
| 121 | `    uint64_t *a = t.a, *b = t.b;` | `a` and `b`: short names for the two buffers. |
| 122 | `    uint64_t v = 0x0123456789ABCDEFULL;` | `v`: the value that a write kernel must store. |
| 123 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This function does not compare it. |
| 124 | `    int ok = 1;` | `ok`: the result of the check. 1 means passed. |
| 126 | `    for (size_t i = 0; i < n; i++) {` | Loop over all words of the page. |
| 127 | `        a[i] = pattern(i, 3);` | Fills the page of `a` with the pattern of the salt 3 ... |
| 128 | `        b[i] = pattern(i, 4);` | ... and the page of `b` with the pattern of the salt 4. So the two pages hold two different patterns. |
| 129 | `    }` | Ends the loop of line 126. |
| 130 | `    calling(kd, m);` | Prints the `call` line with the size 256. |
| 131 | `    call(kd, &t, off * 8, m * 8, v, &sink);` | Runs the kernel on 256 B (`m * 8`) at the byte offset `off * 8`. As in `test_size`, no `SIGSEGV` handler is installed. |
| 132 | `    if (is_read(kd)) {` | Branch for a read kernel. |
| 133 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 134 | `            ok &= a[i] == pattern(i, 3);` | Read kernel: every word of the page of `a` must be unchanged. |
| 135 | `        check(ok, kd, off ? "256 B at page end: page unchanged" : "256 B at page start: page unchanged", m);` | Prints the result row. The name of the check says `page start` for `off` = 0 and `page end` for the other value. The size field is 256. |
| 136 | `    } else if (kd->type == T_WRITE) {` | Branch for a write kernel. |
| 137 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 138 | `            ok &= a[i] == (i >= off && i < off + m ? v : pattern(i, 3));` | Write kernel: the 32 words of the block must hold `v`. Every other word of the page must keep its pattern value. |
| 139 | `        check(ok, kd, off ? "256 B at page end: only those 256 B written" : "256 B at page start: only those 256 B written", m);` | Prints the result row. The check name ends with `only those 256 B written`. |
| 140 | `    } else {` | Branch for a copy kernel. |
| 141 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 142 | `            ok &= b[i] == (i >= off && i < off + m ? pattern(i, 3) : pattern(i, 4)) && a[i] == pattern(i, 3);` | Copy kernel: in `b` the 32 words of the block must hold the values of `a`. Every other word of `b` must keep its own pattern value. `a` must be unchanged. |
| 143 | `        check(ok, kd, off ? "256 B at page end: only those 256 B copied" : "256 B at page start: only those 256 B copied", m);` | Prints the result row. The check name ends with `only those 256 B copied`. |
| 144 | `    }` | Ends the `if` chain of line 132. |
| 145 | `    unguard(a, n);` | Releases the buffer `a` ... |
| 146 | `    unguard(b, n);` | ... and the buffer `b`. |
| 147 | `}` | Ends the function `test_block`. |

### Functions `on_fault` and `test_touch`: a read kernel must touch every page (lines 148 to 190)

| Line | Source | Explanation |
|---:|---|---|
| 149 | `static void on_fault(int sig, siginfo_t *si, void *ctx)` | Starts the function `on_fault`, the `SIGSEGV` handler of `test_touch`. Linux calls it when a kernel accesses a page that it may not access. `si` holds the details of the fault. |
| 150 | `{` | Opens the body of `on_fault`. |
| 151 | `    (void)sig;` | Marks the argument `sig` as not used. Then the compiler does not warn about it. |
| 152 | `    (void)ctx;` | Marks the argument `ctx` as not used. |
| 153 | `    fault_addr = (uintptr_t)si->si_addr;` | Stores the address of the faulting access in `fault_addr`. |
| 154 | `    siglongjmp(fault_jmp, 1);` | Jumps back to the `sigsetjmp` call of line 177, which now returns 1. The kernel call that faulted does not continue. |
| 155 | `}` | Ends the function `on_fault`. |
| 157 | `/* Read kernels: a range of 3 pages, with one page inside it made PROT_NONE.` | Comment: for read kernels, `test_touch` uses a range of 3 pages, with one page inside it made `PROT_NONE`. |
| 158 | ` * The kernel must fault, and the fault address must lie in that page. This` | Comment: the kernel must fault, and the fault address must lie in that page. This ... |
| 159 | ` * shows that the kernel touches every page of its range. */` | Comment: ... shows that the kernel touches every page of its range. |
| 160 | `static void test_touch(const struct kdef *kd)` | Starts the function `test_touch`. It is for read kernels only. The buffer has 3 pages. The loop runs three times. Each time another one of the pages is `PROT_NONE`, and the kernel runs on the whole buffer. The kernel must fault, and the fault address must lie in that page. What it proves: the kernel accesses at least one byte of each of the 3 pages. A kernel that loads nothing, or that leaves out a page, fails. What it cannot prove: that every byte or every 64 B line of a page is loaded. One load per page passes. A page has 4096 B in CRB build 1 [Ref1]. By the file comment the objdump listing is the evidence for the loads (lines 21 to 23). The check also cannot prove anything about a nop, a vector add, or the use of a loaded value. They change no memory and raise no fault. |
| 161 | `{` | Opens the body of `test_touch`. |
| 162 | `    size_t n = 3 * (size_t)page_bytes / 8;` | `n`: the number of words of 3 pages. |
| 163 | `    struct thread t = { .a = guarded(n) };` | `t`: a thread record with one guarded buffer of 3 pages. A read kernel needs no buffer `b`. |
| 164 | `    struct sigaction sa, old;` | `sa`: the new setting for the signal. `old`: the setting from before. |
| 165 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This function does not compare it. |
| 167 | `    memset(&sa, 0, sizeof sa);` | Sets every byte of `sa` to 0. |
| 168 | `    sa.sa_sigaction = on_fault;` | The handler is `on_fault`. |
| 169 | `    sa.sa_flags = SA_SIGINFO;` | The flag `SA_SIGINFO` makes Linux pass the fault address to the handler. |
| 170 | `    sigaction(SIGSEGV, &sa, &old);` | Installs `on_fault` as the handler of `SIGSEGV`. `old` keeps the setting from before. |
| 171 | `    for (volatile int j = 0; j < 3; j++) {` | The loop runs three times, once per page `j`. `j` is `volatile`: it keeps its value across the jump of line 154. |
| 172 | `        uint8_t *pg = (uint8_t *)t.a + (size_t)j * (size_t)page_bytes;` | `pg`: the address of page `j` of the buffer. |
| 173 | `        volatile int faulted = 0;` | `faulted`: becomes 1 when the kernel faulted. It is `volatile` for the same reason as `j`. |
| 174 | `        mprotect(pg, (size_t)page_bytes, PROT_NONE);` | `mprotect` makes this page `PROT_NONE`. |
| 175 | `        fault_addr = 0;` | Clears the fault address of the pass before. |
| 176 | `        calling(kd, n);` | Prints the `call` line. |
| 177 | `        if (sigsetjmp(fault_jmp, 1) == 0)` | `sigsetjmp` saves this place in `fault_jmp` and returns 0 at its direct call. The argument 1 saves the signal mask, and the jump restores it. So `SIGSEGV` can be caught again for the next page. |
| 178 | `            call(kd, &t, 0, n * 8, 0, &sink);` | The value 0: the kernel is called on the whole range of 3 pages. |
| 179 | `        else` | The other value: when the kernel faults, `on_fault` jumps back to line 177, and `sigsetjmp` returns 1 there. |
| 180 | `            faulted = 1;` | Then `faulted` becomes 1. |
| 181 | `        mprotect(pg, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | Makes the page readable and writable again. |
| 182 | `        check(faulted && fault_addr >= (uintptr_t)pg && fault_addr < (uintptr_t)pg + (uintptr_t)page_bytes, kd,` | The check passes when the kernel faulted and the fault address lies in the `PROT_NONE` page. The call goes on in the next three lines. |
| 183 | `              j == 0 ? "faults in page 0 of 3 when it is PROT_NONE"` | Continues the call of line 182: the name of the check gives the page number. This is the name for page 0. |
| 184 | `                     : j == 1 ? "faults in page 1 of 3 when it is PROT_NONE" : "faults in page 2 of 3 when it is PROT_NONE",` | Continues the call: the names for page 1 and for page 2. |
| 185 | `              n);` | Ends the call: the size of the range in words. The row prints it in bytes. |
| 186 | `    }` | Ends the loop of line 171. |
| 187 | `    sigaction(SIGSEGV, &old, NULL);` | Restores the `SIGSEGV` setting from before. |
| 188 | `    unguard(t.a, n);` | Releases the buffer. |
| 189 | `}` | Ends the function `test_touch`. |

### Function `selftest`: the entry point of the option `--selftest` (lines 191 to 214)

| Line | Source | Explanation |
|---:|---|---|
| 191 | `static int selftest(void)` | Starts the function `selftest`. `main` of the runner source calls it for the argument `--selftest` and returns its value as the exit status. The self-test runs in the main thread. It computes no rate, and no function of this file reads the clock. |
| 192 | `{` | Opens the body of `selftest`. |
| 193 | `    setvbuf(stdout, NULL, _IOLBF, 0); /* a kernel that faults must not take the earlier lines with it */` | `setvbuf` with `_IOLBF` makes the output line-buffered: each line is written when it is complete. So a kernel that ends the process cannot remove earlier lines. |
| 194 | `    printf("# selftest: page_bytes=%ld kernels=%d (%s); columns: kernel,check,bytes,result\n", page_bytes, K_COUNT,` | Prints the header line. It gives the page size in bytes, the number of kernels and the kind of build (line 195). It also names the four columns of a result row: `kernel`, `check`, `bytes`, `result`. |
| 195 | `           STANDIN ? "STAND-IN kernels, not AArch64" : "aarch64");` | Continues the call of line 194: the kind of build. The text is `aarch64` for a build with the real kernels. It is `STAND-IN kernels, not AArch64` for a build on a machine that is not AArch64 (the 64-bit Arm instruction set). There plain C loops take the place of the NEON and asm kernels. |
| 196 | `    if (page_bytes % 256 != 0) {` | A page size that is not a multiple of 256 B ... |
| 197 | `        fprintf(stderr, "page size is not a multiple of 256\n");` | ... prints a message to the error output ... |
| 198 | `        return 2;` | ... and ends the self-test with the value 2. |
| 199 | `    }` | Ends the `if` of line 196. |
| 200 | `    /* whole buffers of 1 page, 3 pages and 1 MiB */` | Comment: `test_size` gets whole buffers of 1 page, 3 pages and 1 MiB. |
| 201 | `    size_t words[] = { (size_t)page_bytes / 8, 3 * (size_t)page_bytes / 8, (1UL << 20) / 8 };` | `words`: the three buffer sizes of `test_size`, in words of 8 bytes: 1 page, 3 pages and 1 MiB. With a page of 4096 B these are 4096 B, 12288 B and 1048576 B. |
| 202 | `    /* one block: at the start of a page (guard before it) and at the end (guard after it) */` | Comment: `test_block` gets one block at the start of a page, with a guard page before it, and one at the end, with a guard page after it. |
| 203 | `    size_t offs[] = { 0, (size_t)page_bytes / 8 - 32 };` | `offs`: the two block offsets of `test_block`, in words: 0 for the first 256 B of a page, and the page size minus 32 words for the last 256 B. |
| 204 | `    for (int k = 0; k < K_COUNT; k++) {` | The loop takes every kernel in the order of `kernels[]`. |
| 205 | `        for (size_t i = 0; i < sizeof words / sizeof words[0]; i++)` | Loop over the three sizes of `words`. |
| 206 | `            test_size(&kernels[k], words[i]);` | Per kernel: `test_size` with each of the three sizes. |
| 207 | `        for (size_t i = 0; i < 2; i++)` | Loop over the two block offsets. |
| 208 | `            test_block(&kernels[k], offs[i]);` | Per kernel: `test_block` at each of the two offsets. |
| 209 | `        if (is_read(&kernels[k]))` | For a read kernel in addition ... |
| 210 | `            test_touch(&kernels[k]);` | ... `test_touch`. |
| 211 | `    }` | Ends the loop of line 204. |
| 212 | `    printf("# failures=%d\n", failures);` | The last line of the output is `# failures=N`, with the count of the failed checks for N. CRB build 1: in the output of each of the four binaries 162 rows end with `pass`, no line holds `FAIL`, and the last line is `# failures=0` [Ref1]. |
| 213 | `    return failures ? 1 : 0;` | Return value: 1 if a check failed, else 0. `main` of the runner source returns it as the exit status. The build script of the runner ends with exit status 4 when the value is not 0. |
| 214 | `}` | Ends the function `selftest`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-1/selftest-bwx.txt` and the three files `selftest-bwx_o0.txt`, `selftest-bwx_o36.txt` and `selftest-bwx_o52.txt` beside it: the self-test outputs of CRB build 1. The four files are equal (checked with `cmp`). Each has 299 lines. The first line is `# selftest: page_bytes=4096 kernels=21 (aarch64); columns: kernel,check,bytes,result`. 135 lines begin with `call,`. 162 rows end with `pass`. No line holds `FAIL`. The last line is `# failures=0`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-1/build.txt` and the file `build.txt` of the folder `bwx-crb-build-2`: the records of the two CRB builds. Each holds four lines of the form `## selftest <binary> exit=0 # failures=0`, for `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`. In both, the sha256 value of `bwx_selftest.c` begins with `1c25fc53`. Computed in this task with `sha256sum`: the file `bwx_selftest.c` of the code folder has the same value. The folder `bwx-crb-build-2` holds no self-test output file.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-bwx.md`: a note of the project. Its item 20 says that the self-test is a mode of `bwx`, and it names two checks beyond `selftest.c`: each read kernel must fault when one page of a 3-page range is made `PROT_NONE`, and `oldread` and `oldread2` must return the sum of all words.
