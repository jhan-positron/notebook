# `bandwidth_cread.c` explained, line by line

- Source file: `cread-2026-11-12/bandwidth_cread.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 506 lines, 17754 bytes).
- sha256 of the source when this page was built: `40bbf73d1bef2417e7328460e7f227c02a83370dd7b1c9f8e6366e2874b14cc6`.

## Short version: purpose

`bandwidth_cread.c` is the benchmark program of the cread test: a copy of the old benchmark source with one more read kernel, `k_cread`. `k_cread` is written in C with NEON intrinsics, and it only loads the buffer: 256 B per loop pass, with no arithmetic. Each thread runs the selected kernels in whole passes over its own buffer for a minimum time, and `main` prints one rate in GB/s per timed interval.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Cread test**: the test that compares the read kernels `read`, `asmread` and `cread` with one thread on CRB. It ran on 2026-11-13 [Ref1].
- **`k_read`, kernel `read`**: in this file the read kernel of the old benchmark source: portable C code with 16 running sums. Each load is followed by an add.
- **`k_cread`, kernel `cread`**: the read kernel that this file adds: NEON intrinsics, loads only. The new read kernel `k_read` of the later file `bandwidth.c` has the same loop text.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Asm kernels**: the three kernels `k_asmread`, `k_asmwrite` and `k_asmcopy`. Their loops are assembly text inside a C function.
- **NEON intrinsics**: C functions that map to Arm vector instructions. NEON is the set of 128-bit vector instructions of Arm.
- **`ldp q`, `stp q`**: `ldp q` is the Arm instruction that loads two 16-byte vector registers (32 B). `stp q` is the Arm instruction that stores two 16-byte vector registers (32 B).
- **64-bit Arm (AArch64)**: the instruction set of CRB.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process. The code calls it a repetition (`rep`).
- **Pass, loop pass**: a pass is one call of a kernel. It goes once over the whole buffer of a thread. A loop pass is one run of the loop body inside a kernel: 128 B in `k_read`, 256 B in `k_cread` and in the asm kernels.
- **Warm-up pass**: one pass that a thread runs before each timed interval. It is not timed.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Barrier**: an object of the POSIX thread library. A thread that calls `pthread_barrier_wait` waits until a set number of threads have called it. Then all of them continue together.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **`run_cread.sh`**: the script of the cread test. It builds this file on CRB, prints the machine-code listing of `k_cread`, `k_asmread` and `k_read`, and starts the timed processes.
- **Test binary**: the binary `bandwidth_cread` that `run_cread.sh` built from this file on 2026-11-13 [Ref1].
- **Old benchmark source**: the benchmark source before the change of 2026-11-13. The code repo holds it as the file `bandwidth.orig.c` in the folder `kernels-2026-11-13`.
- **gcc**: the GNU C compiler.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `main` sets the defaults: a buffer of 1 MiB per thread and the kernels `read`, `write` and `copy` (lines 378 to 382).
2. `main` reads the arguments (lines 384 to 430). `run_cread.sh` passes `--threads 1`, `--cpus` with CPU 0 or CPU 2, `--bytes` with `32K`, `1M`, `8M` or `1G`, `--kernel readcmp`, `--reps 3` and `--min-ms 500`.
3. `main` checks the arguments. The buffer size must be a multiple of 256 B (lines 431 to 442).
4. `main` creates the barrier for all worker threads plus itself and starts the worker threads (lines 444 to 456).
5. Each worker pins itself to its CPU, reserves its buffer and writes every element once, which is the first touch. None of this is timed (lines 338 to 345).
6. For each selected kernel and each repetition, each worker runs one warm-up pass and then waits at the barrier (lines 347 to 352). With `readcmp` the kernels run in the order `read`, `asmread`, `cread`.
7. The barrier releases all threads together. Each worker reads the clock, runs whole passes of the kernel and reads the clock again after each group of passes. It stops when the minimum time has passed (lines 353 to 362).
8. `main` waits until all workers have stopped. It divides the bytes of all threads by the longest thread time and prints one row with this rate (lines 467 to 489).
9. After the last repetition of a kernel `main` prints the `best` row (lines 491 to 501).
10. After the last kernel `main` waits for the end of the threads and exits (lines 503 to 505).

## Behavior a reader must know

- What is timed: the passes of the kernel and the clock reads between them (lines 353 to 359). Pinning, buffer allocation, first touch, the warm-up pass and the waits at the barrier are not timed.
- Order in a `readcmp` process: `read`, then `asmread`, then `cread`, each with its own warm-up passes and timed intervals. So `cread` is always timed after the two other kernels in the same process. The comment of line 423 names the kernels in another order.
- Stop rule: a thread tests the time only after `passes_per_check` whole passes (lines 334 to 336). With the sizes that `run_cread.sh` passes, these are 256 passes for `32K`, 8 passes for `1M`, and 1 pass for `8M` and for `1G`.
- Rate: `aggregate_GBps` is the bytes of all threads, divided by the longest thread time, divided by 1e9 (line 484). With 1 thread it equals the rate of that thread.
- `k_cread` in the test binary: one loop pass is 11 instructions for 256 B: 8 `ldp q` loads, 1 `add`, 1 `cmp` and 1 branch. It holds no add of data. `k_read` in the same binary has 4 `ldp q` loads and 8 vector adds per 128 B [Ref1].
- The compiler chooses the machine code of `k_cread`. So each new build needs a check of the machine-code listing. `run_cread.sh` writes the listing into its build record.
- The usage text does not list the kernel names `cread` and `readcmp` (line 372).
- Exit status: 0 after a normal end. 2 after a bad argument or after a failed step of the setup (`calloc`, the barrier, `pthread_create`, `mmap` or `sched_setaffinity`).
- 2 MiB pages: the program asks for them with `madvise` and never checks the result (line 133).
- What this file adds to the old benchmark source: the include of `arm_neon.h` (lines 19 to 21), the seventh kernel in the kernel list (lines 28 to 29), `k_cread` with its comment (lines 257 to 288), its case in `pass` (lines 318 to 320), the names `cread` and `readcmp` (lines 421 to 424) and the test for `cread` in line 437. Every other line equals the old benchmark source [Ref2].

## Source and explanation, line by line

- Text shown: the file `cread-2026-11-12/bandwidth_cread.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (506 lines, 17754 bytes, sha256 `40bbf73d1bef2417e7328460e7f227c02a83370dd7b1c9f8e6366e2874b14cc6`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and include lines (lines 1 to 22)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Comment: starts the header comment of the file. It ends in line 8. |
| 2 | ` * bandwidth.c - multi-thread streaming bandwidth: read, write, copy.` | Comment: the name and the purpose of the program. It measures with several threads how fast memory is read, written and copied in address order (streaming). The comment names `bandwidth.c`. This file is a copy of the old benchmark source with the kernel `k_cread` and two kernel names added [Ref2]. |
| 3 | ` *` | Comment: an empty line inside the header comment. |
| 4 | ` * Every thread owns its buffers (allocated and first-touched by that thread),` | Comment: each thread owns its buffers. The thread itself reserves them and writes them first (first touch). |
| 5 | ` * so timing contains no page faults. All threads start on a barrier, run` | Comment: so a timed interval holds no page fault. A page fault is the work that Linux does when a memory page is used for the first time. All threads start a timed interval together at a barrier (line 56). |
| 6 | ` * whole passes over their buffer until --min-ms has elapsed, and record` | Comment: each thread runs whole passes over its buffer until the time of the option `--min-ms` has passed. A pass is one run of a kernel over the whole buffer. |
| 7 | ` * bytes moved and their own elapsed time. GB means 1e9 bytes throughout.` | Comment: each thread records the bytes that it moved and the time that it measured itself. GB means 1e9 bytes everywhere in this program. |
| 8 | ` */` | Comment: the end of the header comment. |
| 9 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include line. This makes the Linux-only calls of the headers visible, for example `sched_setaffinity` and `CPU_SET` (lines 112 to 115). |
| 10 | `#include <pthread.h>` | Includes the header of the POSIX thread library. It gives the threads (`pthread_create`, `pthread_join`) and the barrier (`pthread_barrier_wait`). |
| 11 | `#include <sched.h>` | Includes the header for the CPU pinning: the type `cpu_set_t`, the macros `CPU_ZERO` and `CPU_SET`, and the call `sched_setaffinity`. |
| 12 | `#include <stdint.h>` | Includes the integer types of fixed size: `uint64_t` (64 bits), `uint8_t` (8 bits) and `uintptr_t` (an integer that can hold an address). |
| 13 | `#include <stdio.h>` | Includes the output functions `printf`, `fprintf`, `perror` and `fflush`. |
| 14 | `#include <stdlib.h>` | Includes `exit`, `calloc` and the functions that turn text into a number: `strtod`, `strtol`, `atoi` and `atof`. |
| 15 | `#include <string.h>` | Includes the text functions `strcmp` and `strtok`, and `memset`. |
| 16 | `#include <sys/mman.h>` | Includes `mmap` and `madvise`, the two Linux calls that `alloc_buf` uses for a buffer. |
| 17 | `#include <time.h>` | Includes `clock_gettime` and the type `struct timespec`. The function `now_s` reads the clock with them. |
| 18 | `#include <unistd.h>` | Includes `getpid`, which gives the process id. The worker uses it for the value that it stores (line 333). |
| 19 | `#if defined(__aarch64__)` | Includes the header of line 20 only in a build for 64-bit Arm (AArch64). The compiler defines `__aarch64__` for that instruction set. |
| 20 | `#include <arm_neon.h>` | Includes the header of the NEON intrinsics (C functions that map to Arm vector instructions). `k_cread` uses its type `uint64x2_t` and its function `vld1q_u64` (lines 261 to 288). |
| 21 | `#endif` | Ends the `#if` of line 19. |

### Constants and the list of the kernels (lines 23 to 30)

| Line | Source | Explanation |
|---:|---|---|
| 23 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2 MiB (2097152 bytes), the size of one huge page. The expression shifts the number 2 left by 20 bits. `alloc_buf` aligns every buffer to this size (line 123, line 130). |
| 24 | `#define MAX_CPUS 1024` | `MAX_CPUS`: the CPU list holds at most 1024 entries (line 34, line 101). |
| 25 | `#define MAX_REPS 32` | `MAX_REPS`: at most 32 timed intervals per kernel (line 52, line 435). |
| 26 | `#define CHECK_BYTES (8UL << 20) /* clock is read after at least this many bytes */` | `CHECK_BYTES`: 8 MiB (8388608 bytes). Line 334 divides it by the buffer size. The result, or 1 when the result is 0 (line 336), is the number of passes between two clock reads. The comment says that the clock is read after at least this many bytes. For the bytes of the buffer this holds only when 8 MiB is a multiple of the buffer size, or when the buffer is larger than 8 MiB. For every other size the passes between two clock reads cover less than 8 MiB (line 334). |
| 28 | `enum kernel { K_READ, K_WRITE, K_COPY, K_ASMREAD, K_ASMWRITE, K_ASMCOPY, K_CREAD, K_COUNT };` | The seven kernels of the program, numbered 0 to 6. `K_CREAD`, the kernel that this file adds, is the last one. `K_COUNT` is 7, the number of kernels. A process runs its selected kernels in this order (loop of line 347). |
| 29 | `static const char *kernel_name[K_COUNT] = { "read", "write", "copy", "asmread", "asmwrite", "asmcopy", "cread" };` | `kernel_name`: the name of each kernel as text, in the order of line 28. It is the text that the first column of an output row shows (line 487, line 491). The name of the added kernel is `cread`. |

### Settings, per-thread data and the barrier (lines 31 to 57)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `static struct {` | Starts the definition of `cfg`, the variable that holds the settings of the process. The definition ends in line 41. |
| 32 | `    int threads;` | `threads`: the number of worker threads (option `--threads`). |
| 33 | `    int ncpus;` | `ncpus`: the number of entries in the CPU list. It is 0 when no option `--cpus` was given. |
| 34 | `    int cpus[MAX_CPUS];` | `cpus`: the CPU list of the option `--cpus`, one CPU number per entry. |
| 35 | `    uint64_t bytes;` | `bytes`: the buffer size of each thread, in bytes (option `--bytes`). |
| 36 | `    int run[K_COUNT];` | `run`: one flag per kernel. `run[k]` is 1 when kernel `k` is selected (option `--kernel`). |
| 37 | `    double min_s;` | `min_s`: the minimum time of a timed interval, in seconds (option `--min-ms`). |
| 38 | `    int reps;` | `reps`: the number of timed intervals per kernel (option `--reps`). |
| 39 | `    int use_thp;` | `use_thp`: 1 when the program asks Linux for 2 MiB pages, 0 with the option `--no-thp` (line 133). |
| 40 | `    int per_thread; /* --per-thread: one line per thread with its CPU and best GB/s */` | `per_thread`: 1 with the option `--per-thread`. The comment says: one line per thread with its CPU and its best rate in GB/s. The comment is out of date. The code prints one line per thread and repetition, with the rate of that repetition (lines 495 to 499). |
| 41 | `} cfg = { .threads = 1, .min_s = 0.5, .reps = 3, .use_thp = 1 };` | Ends the definition and sets the defaults: 1 thread, a minimum time of 0.5 s per interval, 3 intervals per kernel, and a request for 2 MiB pages. Every other field starts at 0. |
| 43 | `struct result {` | Starts `struct result`: the result of one thread for one timed interval. |
| 44 | `    uint64_t bytes;` | `bytes`: the bytes that the thread counted in the interval. |
| 45 | `    double elapsed_s;` | `elapsed_s`: the time that the same thread measured for the interval, in seconds. |
| 46 | `};` | Ends `struct result`. |
| 48 | `struct thread {` | Starts `struct thread`: one entry per worker thread. |
| 49 | `    int idx;` | `idx`: the thread index, counted from 0. |
| 50 | `    int cpu;` | `cpu`: the CPU of the thread, or -1 when no CPU list was given (line 451). |
| 51 | `    uint64_t *a, *b;` | `a`, `b`: the addresses of the two buffers of the thread. Each buffer is an array of 8-byte elements. Only the copy kernels use `b` (line 342). |
| 52 | `    struct result res[K_COUNT][MAX_REPS];` | `res`: one result per kernel and interval: 7 kernels times at most 32 intervals. |
| 53 | `    pthread_t tid;` | `tid`: the handle of the thread. `pthread_create` fills it (line 452), and `pthread_join` uses it (line 504). |
| 54 | `};` | Ends `struct thread`. |
| 56 | `static pthread_barrier_t bar;` | `bar`: a barrier. A thread that calls `pthread_barrier_wait` on it waits until all worker threads and the main thread have called it. Then all of them continue together. Line 445 sets how many threads must arrive. |

### Function `now_s`: read the clock (lines 58 to 64)

| Line | Source | Explanation |
|---:|---|---|
| 58 | `static double now_s(void)` | Starts the function `now_s`. It reads the clock and returns the time in seconds. Every time value of the program comes from this function. The worker calls it at the start of a timed interval (line 353) and after the passes (line 358). |
| 59 | `{` | Opens the body of `now_s`. |
| 60 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 61 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | Reads `CLOCK_MONOTONIC` into `ts`. This is the Linux clock that only moves forward. A change of the date of the machine does not change it. It is the only clock that the file reads. |
| 62 | `    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;` | Returns the time in seconds as a `double`: the seconds plus the nanoseconds times 1e-9. |
| 63 | `}` | Ends the function `now_s`. |

### Function `parse_bytes`: read a size such as `8M` (lines 65 to 81)

| Line | Source | Explanation |
|---:|---|---|
| 65 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `8M` into a number of bytes. `main` calls it for the option `--bytes` (line 397). |
| 66 | `{` | Opens the body of `parse_bytes`. |
| 67 | `    char *end;` | `end`: will point to the first character after the number. |
| 68 | `    double v = strtod(s, &end);` | `strtod` reads a number from the start of the text `s` into `v`. The number may have a decimal point. `strtod` sets `end` to the first character that is not part of the number. |
| 69 | `    double mul = 1;` | `mul`: the factor of the suffix. It stays 1 when the text has no suffix. |
| 70 | `    switch (*end) {` | Looks at the character after the number. |
| 71 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | `k` or `K`: the factor is 1024 (2 to the power 10). `end++` steps over the suffix. So `32K` gives 32768 bytes. |
| 72 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | `m` or `M`: the factor is 1048576 (2 to the power 20, which is 1 MiB). So `1M` gives 1048576 bytes, and `8M` gives 8388608 bytes. |
| 73 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | `g` or `G`: the factor is 1073741824 (2 to the power 30). So `1G` gives 1073741824 bytes. |
| 74 | `    }` | Ends the `switch` of line 70. |
| 75 | `    if (end == s \|\| *end != '\0' \|\| v <= 0) {` | Tests three error cases. No number was read (`end == s`). Or other text follows the number and its suffix. Or the value is 0 or below. |
| 76 | `        fprintf(stderr, "bad size: %s\n", s);` | On an error: prints `bad size:` and the text to the error output. |
| 77 | `        exit(2);` | On an error: the program ends with exit status 2. |
| 78 | `    }` | Ends the `if` of line 75. |
| 79 | `    return (uint64_t)(v * mul);` | Returns the number times the factor as a whole number of bytes. A fraction of a byte is cut off. |
| 80 | `}` | Ends the function `parse_bytes`. |

### Function `parse_cpus`: read the CPU list (lines 82 to 109)

| Line | Source | Explanation |
|---:|---|---|
| 82 | `/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */` | Comment: three examples of a CPU list. `0-119` is a range. `0,2,4-7` is a list of numbers and ranges. `0-118:2` is a range with a step (the comment says stride): every second CPU from 0 to 118. |
| 83 | `static void parse_cpus(char *list)` | Starts the function `parse_cpus`. It reads the text of the option `--cpus` and appends every CPU number to `cfg.cpus`, in the order of the list. `0-119` gives the 120 entries 0, 1, 2 and so on up to 119. |
| 84 | `{` | Opens the body of `parse_cpus`. |
| 85 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Loop over the pieces of the list. `strtok` cuts the text at each comma and returns one piece per call. After the last piece it returns `NULL`, which ends the loop. |
| 86 | `        char *e, *e2;` | `e`, `e2`: each will point to the first character after a number that was read. |
| 87 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the piece (base 10) into `lo`. `hi` starts equal to `lo`, and `step` starts at 1. So a piece that is one number gives one CPU. |
| 88 | `        if (e != tok && *e == '-') {` | Tests whether a number was read and a hyphen follows it. The piece is then a range. |
| 89 | `            hi = strtol(e + 1, &e2, 10);` | Reads the number after the hyphen into `hi`, the last CPU of the range. |
| 90 | `            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */` | When no digit followed the hyphen (`e2 == e + 1`), `e` is set back to `tok`. The test of line 96 then rejects the piece. In every other case `e` moves to the first character after the second number. The comment gives the example `0-`, a range without an upper bound. |
| 91 | `            if (e != tok && *e == ':') {` | Tests whether the range is valid so far and a colon follows it. The piece then has a step. |
| 92 | `                step = strtol(e + 1, &e2, 10);` | Reads the number after the colon into `step`. |
| 93 | `                e = e2 == e + 1 ? tok : e2;` | The same rule as in line 90: when no digit followed the colon, `e` is set back to `tok`. |
| 94 | `            }` | Ends the `if` of line 91. |
| 95 | `        }` | Ends the `if` of line 88. |
| 96 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| hi >= CPU_SETSIZE \|\| step < 1) {` | Tests the piece. It is bad in each of these cases: no number was read, or line 90 or line 93 set `e` back (`e == tok`), or other text follows the numbers, or `lo` is below 0, or `hi` is below `lo`, or `hi` is `CPU_SETSIZE` or above (the number of CPUs that the type `cpu_set_t` can hold), or `step` is below 1. |
| 97 | `            fprintf(stderr, "bad cpu list: %s\n", tok);` | On a bad piece: prints `bad cpu list:` and the piece to the error output. |
| 98 | `            exit(2);` | On a bad piece: the program ends with exit status 2. |
| 99 | `        }` | Ends the `if` of line 96. |
| 100 | `        for (long c = lo; c <= hi; c += step) {` | Loop over the CPU numbers of the piece: from `lo` to `hi` in steps of `step`. |
| 101 | `            if (cfg.ncpus == MAX_CPUS) {` | Tests whether the list already holds 1024 entries (`MAX_CPUS`). |
| 102 | `                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);` | When the list is full: prints `bad cpu list: more than 1024 cpus` to the error output. |
| 103 | `                exit(2);` | When the list is full: the program ends with exit status 2. |
| 104 | `            }` | Ends the `if` of line 101. |
| 105 | `            cfg.cpus[cfg.ncpus++] = (int)c;` | Appends the CPU number to `cfg.cpus` and adds 1 to the count `cfg.ncpus`. |
| 106 | `        }` | Ends the loop of line 100. |
| 107 | `    }` | Ends the loop of line 85. |
| 108 | `}` | Ends the function `parse_cpus`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 110 to 120)

| Line | Source | Explanation |
|---:|---|---|
| 110 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It pins the calling thread to the CPU with the number `cpu`: Linux then runs the thread on that CPU only. |
| 111 | `{` | Opens the body of `pin_cpu`. |
| 112 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 113 | `    CPU_ZERO(&set);` | Empties the set. |
| 114 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 115 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. So only this thread is pinned. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 116 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 117 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 118 | `    }` | Ends the `if` of line 115. |
| 119 | `}` | Ends the function `pin_cpu`. |

### Function `alloc_buf`: one buffer, aligned for huge pages (lines 121 to 137)

| Line | Source | Explanation |
|---:|---|---|
| 121 | `static uint64_t *alloc_buf(uint64_t bytes)` | Starts the function `alloc_buf`. It reserves a buffer of at least `bytes` bytes and returns its address. The buffer starts at a multiple of 2 MiB. |
| 122 | `{` | Opens the body of `alloc_buf`. |
| 123 | `    size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | `len`: `bytes` rounded up to the next multiple of `HUGE_BYTES` (2 MiB). The expression adds `HUGE_BYTES - 1` and then clears the low bits. This gives the right value when `HUGE_BYTES` is a power of two. A size of 32768 bytes becomes 2 MiB. A size of 1073741824 bytes stays as it is. |
| 124 | `    uint8_t *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ \| PROT_WRITE,` | `mmap` asks Linux for `len + HUGE_BYTES` bytes of new memory. The extra `HUGE_BYTES` bytes make it possible to move the start to an aligned address later (line 130). `NULL`: Linux chooses the address. `PROT_READ \| PROT_WRITE`: the program may read and write the memory. |
| 125 | `                        MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | Continues the call of line 124. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. `mmap` reserves addresses only. Linux assigns the physical memory when a page is first written (line 341). |
| 126 | `    if (raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 127 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 128 | `        exit(2);` | On failure: the program ends with exit status 2. |
| 129 | `    }` | Ends the `if` of line 126. |
| 130 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the first address in the reserved range that is a multiple of 2 MiB. The buffer starts there. The expression rounds the address `raw` up in the same way as line 123 rounds the size. |
| 131 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: `MADV_NOHUGEPAGE` matters on a machine where the Linux setting for transparent huge pages (THP) is `always`. |
| 132 | `     * would still get 2 MiB pages. */` | Comment: without it, the buffers of a run with `--no-thp` would still get 2 MiB pages. |
| 133 | `    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` with `MADV_HUGEPAGE` asks Linux to use 2 MiB pages for the `len` bytes that start at `p`. With the option `--no-thp` it passes `MADV_NOHUGEPAGE`, which forbids them. `run_cread.sh` does not pass `--no-thp`. |
| 134 | `        perror("madvise (continuing)");` | A failed `madvise` only prints a message that starts with `madvise (continuing)`. The program goes on. It never checks whether the buffer in fact lies on 2 MiB pages. |
| 135 | `    return (uint64_t *)p;` | Returns the aligned address as a pointer to 8-byte elements. The program never releases the buffer. |
| 136 | `}` | Ends the function `alloc_buf`. |

### Function `k_read`: the read kernel with 16 running sums (one add per load) (lines 138 to 152)

| Line | Source | Explanation |
|---:|---|---|
| 138 | `/* 16 independent accumulators keep the loop load-bound: on 128-bit NEON gcc` | Comment: the intent of the 16 sums of `k_read` (the comment calls them accumulators). An add to one sum does not wait for an add to another sum. So the loads, not the adds, are meant to set the speed of the loop. |
| 139 | ` * folds them into 8 vector chains, enough to hide a 2-cycle add latency;` | Comment: with NEON, the 128-bit vector instructions of Arm, gcc makes 8 chains of vector adds from the 16 sums. The comment says that this is enough for an add that takes 2 cycles: the adds then do not limit the speed of the loop. The count of 8 holds for the test binary: its machine code has 8 vector registers for the sums, each with two 64-bit sums [Ref1]. |
| 140 | ` * on AVX-512 they become 2 zmm chains. */` | Comment: with AVX-512 the sums become 2 chains in `zmm` registers. This sentence is about x86 processors. It does not apply to CRB. |
| 141 | `__attribute__((noinline)) static uint64_t k_read(const uint64_t *a, size_t n)` | Starts the function `k_read`, the read kernel with 16 running sums. It adds every 8-byte element of the buffer to one of 16 sums and returns the total. `noinline` forbids the compiler to merge the kernel into its caller. So the binary holds `k_read` as a function of its own, and `run_cread.sh` prints its machine code by name. `a` is the buffer of the thread. `n` is the number of 8-byte elements in the buffer (line 330). |
| 142 | `{` | Opens the body of `k_read`. |
| 143 | `    uint64_t s[16] = { 0 };` | `s`: 16 running sums of 64 bits each, all 0 at the start. In the test binary the compiler keeps them in the 8 vector registers `v24` to `v31` during the loop. Each register holds two of the sums [Ref1]. |
| 144 | `    for (size_t i = 0; i < n; i += 16)` | The outer loop. One loop pass handles 16 elements, which is 128 B. `main` accepts only buffer sizes that are a multiple of 256 B (line 435), so the loop ends exactly at the end of the buffer. |
| 145 | `        for (int j = 0; j < 16; j++)` | The inner loop of the source: 16 steps per outer loop pass, one step per sum. The machine code of the test binary has no inner loop. gcc turned its 16 loads and 16 adds into vector instructions [Ref1]. One loop pass of the machine code is one loop pass of the outer loop of the source (128 B). |
| 146 | `            s[j] += a[i + j];` | Loads one 8-byte element and adds it to its own sum. Every loaded value is used. One loop pass of the machine code of the test binary has 16 instructions [Ref1]. 4 are `ldp q` loads: each one loads two 16-byte vector registers (32 B). 8 are vector `add` instructions: each one adds a loaded register (two 64-bit values) to its sum register. 2 are scalar `add` instructions: the loop counter plus 1 and the buffer pointer plus 128 B. The last 2 are `cmp` and a conditional branch back to the first load. Per 256 B this is 8 `ldp q` loads and 16 vector adds, 32 instructions in total. `k_cread` has the same 8 `ldp q` loads per 256 B and no vector add, 11 instructions in total [Ref1]. |
| 147 | `    uint64_t sum = 0;` | After the loop: `sum` will hold the total of the 16 sums. |
| 148 | `    for (int j = 0; j < 16; j++)` | Loop over the 16 sums. It runs once per call of `k_read`, so once per pass over the buffer. |
| 149 | `        sum += s[j];` | Adds one of the 16 sums to `sum`. |
| 150 | `    return sum;` | Returns the total. The caller stores it once per pass (line 300). In the test binary the code outside the loop also sets the sums to 0 and stores them to the stack. It also holds a stack check that is not in the source (a call of `__stack_chk_fail`) [Ref1]. |
| 151 | `}` | Ends the function `k_read`. |

### Function `k_write`: the C write kernel, also used for the first touch (lines 153 to 158)

| Line | Source | Explanation |
|---:|---|---|
| 153 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_write`, the C write kernel. It stores the value `v` into each of the `n` elements of the buffer `a`. The worker also calls it once per buffer for the first touch (line 341, line 344). `noinline` keeps it a function of its own, as in line 141. |
| 154 | `{` | Opens the body of `k_write`. |
| 155 | `    for (size_t i = 0; i < n; i++)` | Loop over the `n` elements. One step of the source handles one 8-byte element. |
| 156 | `        a[i] = v;` | Stores `v` into element `i`. The compiler chooses the machine code of this loop. `run_cread.sh` prints no listing of `k_write`. |
| 157 | `}` | Ends the function `k_write`. |

### Function `k_copy`: the C copy kernel (lines 159 to 164)

| Line | Source | Explanation |
|---:|---|---|
| 159 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_copy`, the C copy kernel. It copies `n` elements from `s` to `d`. `restrict` tells the compiler that the two buffers do not overlap. `run_cread.sh` does not select this kernel. |
| 160 | `{` | Opens the body of `k_copy`. |
| 161 | `    for (size_t i = 0; i < n; i++)` | Loop over the `n` elements. One step of the source handles one 8-byte element. |
| 162 | `        d[i] = s[i];` | Loads element `i` of `s` and stores it to element `i` of `d`. |
| 163 | `}` | Ends the function `k_copy`. |

### The asm kernels: comment and the test for 64-bit Arm (lines 165 to 175)

| Line | Source | Explanation |
|---:|---|---|
| 165 | `/*` | Comment: starts the comment on the three asm kernels. It ends in line 172. |
| 166 | ` * asm kernels: the whole hot loop is one inline-asm block, so the compiler` | Comment: in an asm kernel the whole loop is one block of assembly text inside a C function (inline asm). The compiler copies the loop. It only puts a register in the place of each name such as `%[p]`. The listing of `k_asmread` in the test binary shows this [Ref1]. |
| 167 | ` * cannot add arithmetic, reorder, or drop anything. Each iteration moves` | Comment: so the compiler cannot add arithmetic, change the order or remove an instruction. The next sentence of the comment starts here: each loop pass (iteration) moves 256 B. |
| 168 | ` * 256 B with 8 ldp/stp of q registers (16 B each). The loop body is:` | Comment: the 256 B are moved with 8 `ldp` or `stp` instructions on `q` registers of 16 B each. `ldp q` loads two such registers (32 B), and `stp q` stores two (32 B). |
| 169 | ` * 8 x ldp or stp, add, cmp, b.lo. Callers guarantee n * 8 is a multiple of` | Comment: the loop body is 8 `ldp` or `stp`, then `add`, `cmp` and the branch `b.lo`. This fits `k_asmread` and `k_asmwrite`. `k_asmcopy` has 8 `ldp`, 8 `stp` and 2 `add` (lines 230 to 247). The callers guarantee that `n * 8` bytes is a multiple of 256 and not 0. `main` checks this (line 435). |
| 170 | ` * 256 and non-zero. v8-v15 are callee-saved in AAPCS64: naming them as` | Comment: `v8` to `v15` are callee-saved in AAPCS64, the calling rules of 64-bit Arm. These rules say that a function must keep the lower halves (`d8` to `d15`) of the registers `v8` to `v15` for its caller. |
| 171 | ` * clobbers makes gcc save d8-d15 once per call, which is outside the loop.` | Comment: the asm blocks name these registers as changed (as clobbers, line 196). So the compiler saves and restores `d8` to `d15` once per call, outside the loop. The listing of `k_asmread` in the test binary shows this [Ref1]. |
| 172 | ` */` | Comment: the end of the comment on the asm kernels. |
| 173 | `#if defined(__aarch64__)` | Compiles lines 174 to 288 only for 64-bit Arm (AArch64). The compiler defines `__aarch64__` for that instruction set. The block holds the three asm kernels and `k_cread`. |
| 174 | `#define HAVE_ASM_KERNELS 1` | `HAVE_ASM_KERNELS` is 1 when the three asm kernels and `k_cread` exist. Line 308 and line 437 test it. |

### Function `k_asmread`: the hand-written load-only loop (lines 176 to 199)

| Line | Source | Explanation |
|---:|---|---|
| 176 | `__attribute__((noinline)) static void k_asmread(const uint64_t *a, size_t n)` | Starts the function `k_asmread`, the hand-written load-only loop. `a` is the buffer, and `n` is its number of 8-byte elements. The function returns nothing. |
| 177 | `{` | Opens the body of `k_asmread`. |
| 178 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at the first element of the buffer. |
| 179 | `    const uint64_t *end = a + n;` | `end`: the address directly after the last element. |
| 180 | `    __asm__ volatile(` | Starts the asm statement: the assembly text (lines 181 to 192) and its three operand lists (lines 193 to 197). `volatile` forbids the compiler to remove the statement. |
| 181 | `        "1:\n\t"` | The label `1`: the start of the loop. The characters `\n\t` end each line of the assembly text with a line break and a tab. |
| 182 | `        "ldp q0, q1, [%[p]]\n\t"` | `ldp` loads 32 B from the address in `p` into the two 16-byte vector registers `q0` and `q1`. The compiler puts the register that holds `p` in the place of `%[p]`. |
| 183 | `        "ldp q2, q3, [%[p], #32]\n\t"` | Loads the 32 B at the address `p` plus 32 into `q2` and `q3`. |
| 184 | `        "ldp q4, q5, [%[p], #64]\n\t"` | Loads the 32 B at `p` plus 64 into `q4` and `q5`. |
| 185 | `        "ldp q6, q7, [%[p], #96]\n\t"` | Loads the 32 B at `p` plus 96 into `q6` and `q7`. |
| 186 | `        "ldp q8, q9, [%[p], #128]\n\t"` | Loads the 32 B at `p` plus 128 into `q8` and `q9`. |
| 187 | `        "ldp q10, q11, [%[p], #160]\n\t"` | Loads the 32 B at `p` plus 160 into `q10` and `q11`. |
| 188 | `        "ldp q12, q13, [%[p], #192]\n\t"` | Loads the 32 B at `p` plus 192 into `q12` and `q13`. |
| 189 | `        "ldp q14, q15, [%[p], #224]\n\t"` | Loads the 32 B at `p` plus 224 into `q14` and `q15`. The 8 loads of lines 182 to 189 read 256 B, each byte once. The loaded values are never used. The next loop pass overwrites them. |
| 190 | `        "add %[p], %[p], #256\n\t"` | `add` moves the pointer forward by 256 B. |
| 191 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the pointer with `end` and sets the condition flags. |
| 192 | `        "b.lo 1b\n\t"` | `b.lo 1b` jumps back to the label `1` (line 181) while the pointer is below `end`. So one loop pass is 11 instructions per 256 B: 8 loads, `add`, `cmp` and the branch. The listing of the test binary shows the same 11 instructions [Ref1]. |
| 193 | `        : [p] "+r"(p)` | First operand list, the outputs: `p` is read and changed in a register (`+r`). In the assembly text its name is `%[p]`. |
| 194 | `        : [end] "r"(end)` | Second list, the inputs: `end` is read in a register (`r`). |
| 195 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | Third list: what the text changes or accesses without an operand. This line names the registers `v0` to `v7`. `v0` and `q0` are two names of the same 16-byte register. |
| 196 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the list: the registers `v8` to `v15`. The compiler saves the lower halves of these 8 registers once per call (lines 170 to 171). |
| 197 | `          "memory", "cc");` | Ends the list and the asm statement. `memory`: the text accesses memory that no operand names. `cc`: the text changes the condition flags. |
| 198 | `}` | Ends the function `k_asmread`. |

### Function `k_asmwrite`: the hand-written store-only loop (lines 200 to 222)

| Line | Source | Explanation |
|---:|---|---|
| 200 | `__attribute__((noinline)) static void k_asmwrite(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_asmwrite`, the hand-written store-only loop. It stores the value `v` into all `n` elements of the buffer `a`. `run_cread.sh` does not select this kernel. |
| 201 | `{` | Opens the body of `k_asmwrite`. |
| 202 | `    uint64_t *p = a;` | `p`: the write pointer. It starts at the first element of the buffer. |
| 203 | `    const uint64_t *end = a + n;` | `end`: the address directly after the last element. |
| 204 | `    __asm__ volatile(` | Starts the asm statement: the assembly text and its operand lists, as in line 180. |
| 205 | `        "dup v0.2d, %[v]\n\t"` | `dup` fills the register `v0` with two copies of the 64-bit value `v`. It runs once, before the loop. |
| 206 | `        "1:\n\t"` | The label `1`: the start of the loop. |
| 207 | `        "stp q0, q0, [%[p]]\n\t"` | `stp` stores the register `q0` twice, which is 32 B, to the address in `p`. |
| 208 | `        "stp q0, q0, [%[p], #32]\n\t"` | Stores `q0` twice (32 B) to the address `p` plus 32. |
| 209 | `        "stp q0, q0, [%[p], #64]\n\t"` | Stores `q0` twice (32 B) to `p` plus 64. |
| 210 | `        "stp q0, q0, [%[p], #96]\n\t"` | Stores `q0` twice (32 B) to `p` plus 96. |
| 211 | `        "stp q0, q0, [%[p], #128]\n\t"` | Stores `q0` twice (32 B) to `p` plus 128. |
| 212 | `        "stp q0, q0, [%[p], #160]\n\t"` | Stores `q0` twice (32 B) to `p` plus 160. |
| 213 | `        "stp q0, q0, [%[p], #192]\n\t"` | Stores `q0` twice (32 B) to `p` plus 192. |
| 214 | `        "stp q0, q0, [%[p], #224]\n\t"` | Stores `q0` twice (32 B) to `p` plus 224. The 8 stores of lines 207 to 214 write 256 B, each byte once. |
| 215 | `        "add %[p], %[p], #256\n\t"` | `add` moves the pointer forward by 256 B. |
| 216 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the pointer with `end`. |
| 217 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the pointer is below `end`. One loop pass is 11 instructions per 256 B: 8 stores, `add`, `cmp` and the branch. |
| 218 | `        : [p] "+r"(p)` | The outputs: `p` is read and changed in a register. |
| 219 | `        : [end] "r"(end), [v] "r"(v)` | The inputs: `end` and `v` are read in registers. |
| 220 | `        : "v0", "memory", "cc");` | What the text changes without an operand: the register `v0`, memory and the condition flags. This ends the asm statement. |
| 221 | `}` | Ends the function `k_asmwrite`. |

### Function `k_asmcopy`: the hand-written copy loop (lines 223 to 256)

| Line | Source | Explanation |
|---:|---|---|
| 223 | `__attribute__((noinline)) static void k_asmcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy`, the hand-written copy loop. It copies `n` elements from `s` to `d`. `restrict` tells the compiler that the two buffers do not overlap. `run_cread.sh` does not select this kernel. |
| 224 | `{` | Opens the body of `k_asmcopy`. |
| 225 | `    uint64_t *dp = d;` | `dp`: the write pointer. It starts at the first element of `d`. |
| 226 | `    const uint64_t *sp = s;` | `sp`: the read pointer. It starts at the first element of `s`. |
| 227 | `    const uint64_t *end = s + n;` | `end`: the address directly after the last element of `s`. |
| 228 | `    __asm__ volatile(` | Starts the asm statement: the assembly text and its operand lists, as in line 180. |
| 229 | `        "1:\n\t"` | The label `1`: the start of the loop. |
| 230 | `        "ldp q0, q1, [%[s]]\n\t"` | `ldp` loads 32 B from the address in the read pointer into `q0` and `q1`. In the assembly text the read pointer has the name `%[s]`. |
| 231 | `        "ldp q2, q3, [%[s], #32]\n\t"` | Loads the 32 B at the read pointer plus 32 into `q2` and `q3`. |
| 232 | `        "ldp q4, q5, [%[s], #64]\n\t"` | Loads the 32 B at the read pointer plus 64 into `q4` and `q5`. |
| 233 | `        "ldp q6, q7, [%[s], #96]\n\t"` | Loads the 32 B at the read pointer plus 96 into `q6` and `q7`. |
| 234 | `        "ldp q8, q9, [%[s], #128]\n\t"` | Loads the 32 B at the read pointer plus 128 into `q8` and `q9`. |
| 235 | `        "ldp q10, q11, [%[s], #160]\n\t"` | Loads the 32 B at the read pointer plus 160 into `q10` and `q11`. |
| 236 | `        "ldp q12, q13, [%[s], #192]\n\t"` | Loads the 32 B at the read pointer plus 192 into `q12` and `q13`. |
| 237 | `        "ldp q14, q15, [%[s], #224]\n\t"` | Loads the 32 B at the read pointer plus 224 into `q14` and `q15`. The 8 loads of lines 230 to 237 read 256 B. All of them come before the first store. |
| 238 | `        "stp q0, q1, [%[d]]\n\t"` | `stp` stores `q0` and `q1` (32 B) to the address in the write pointer. In the assembly text the write pointer has the name `%[d]`. |
| 239 | `        "stp q2, q3, [%[d], #32]\n\t"` | Stores `q2` and `q3` to the write pointer plus 32. |
| 240 | `        "stp q4, q5, [%[d], #64]\n\t"` | Stores `q4` and `q5` to the write pointer plus 64. |
| 241 | `        "stp q6, q7, [%[d], #96]\n\t"` | Stores `q6` and `q7` to the write pointer plus 96. |
| 242 | `        "stp q8, q9, [%[d], #128]\n\t"` | Stores `q8` and `q9` to the write pointer plus 128. |
| 243 | `        "stp q10, q11, [%[d], #160]\n\t"` | Stores `q10` and `q11` to the write pointer plus 160. |
| 244 | `        "stp q12, q13, [%[d], #192]\n\t"` | Stores `q12` and `q13` to the write pointer plus 192. |
| 245 | `        "stp q14, q15, [%[d], #224]\n\t"` | Stores `q14` and `q15` to the write pointer plus 224. The 8 stores of lines 238 to 245 write the 256 B that the 8 loads read. |
| 246 | `        "add %[s], %[s], #256\n\t"` | `add` moves the read pointer forward by 256 B. |
| 247 | `        "add %[d], %[d], #256\n\t"` | `add` moves the write pointer forward by 256 B. |
| 248 | `        "cmp %[s], %[end]\n\t"` | `cmp` compares the read pointer with `end`. |
| 249 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the read pointer is below `end`. One loop pass is 20 instructions per 256 B: 8 loads, 8 stores, 2 `add`, `cmp` and the branch. |
| 250 | `        : [s] "+r"(sp), [d] "+r"(dp)` | The outputs: the two pointers `sp` and `dp` are read and changed in registers. In the assembly text their names are `%[s]` and `%[d]`. |
| 251 | `        : [end] "r"(end)` | The input: `end` is read in a register. |
| 252 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | What the text changes without an operand. This line names the registers `v0` to `v7`. |
| 253 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the list: the registers `v8` to `v15`. |
| 254 | `          "memory", "cc");` | Ends the list and the asm statement: memory and the condition flags. |
| 255 | `}` | Ends the function `k_asmcopy`. |

### Function `k_cread`: the load-only read kernel in C (16 loads per 256 B) (lines 257 to 292)

| Line | Source | Explanation |
|---:|---|---|
| 257 | `/* cread: the algorithm of k_asmread written in C. 16 loads of 16 B per pass.` | Comment: `cread` is the algorithm of `k_asmread` written in C. It has 16 loads of 16 B per pass. Here the comment means one loop pass of 256 B, not one pass over the whole buffer. |
| 258 | ` * The empty asm statement emits no instruction; it names the 16 values as` | Comment: the empty asm statement (lines 282 to 285) adds no instruction. It names the 16 loaded values as inputs (the sentence ends in line 259). |
| 259 | ` * inputs, so gcc must have each of them in a vector register there. Same` | Comment: so gcc must have each of the 16 values in a vector register at that place. The next sentence starts here: `k_cread` has the same contract as `k_asmread`. |
| 260 | ` * contract as k_asmread: n * 8 is a non-zero multiple of 256. */` | Comment: the contract is that `n * 8` bytes is a multiple of 256 and not 0. `main` checks this (line 435). |
| 261 | `__attribute__((noinline)) static void k_cread(const uint64_t *a, size_t n)` | Starts the function `k_cread`, the read kernel that this file adds. It only loads the buffer: 256 B per loop pass, and no arithmetic. `a` is the start of the buffer. `n` is the number of 8-byte elements in it. `noinline` forbids the compiler to merge the function into its caller. So the binary holds `k_cread` as a function of its own, and `run_cread.sh` prints its machine code by name. The function returns nothing (`void`). |
| 262 | `{` | Opens the body of `k_cread`. |
| 263 | `    const uint64_t *p = a;` | `p`: the read position. It starts at the first element of the buffer. |
| 264 | `    const uint64_t *end = a + n;` | `end`: the first address after the buffer, which is `a` plus `n` elements. The machine code of the test binary computes it with one instruction before the loop: `add x1, x0, x1, lsl #3` [Ref1]. |
| 265 | `    do {` | `do`: the loop body runs before the first test of the end (line 287). `main` rejects a buffer size of 0 (line 435), so the body never runs on an empty buffer. |
| 266 | `        uint64x2_t v0 = vld1q_u64(p + 0);` | `vld1q_u64(p + 0)` loads 16 B, which is two 8-byte elements, from the read position into the vector variable `v0`. The type `uint64x2_t` is a vector of two 64-bit integers. This load reads the bytes 0 to 15 of the current block of 256 B. |
| 267 | `        uint64x2_t v1 = vld1q_u64(p + 2);` | Loads the 16 B at element 2 after the read position into `v1`: the bytes 16 to 31 of the block. |
| 268 | `        uint64x2_t v2 = vld1q_u64(p + 4);` | Loads the bytes 32 to 47 of the block into `v2`. |
| 269 | `        uint64x2_t v3 = vld1q_u64(p + 6);` | Loads the bytes 48 to 63 of the block into `v3`. |
| 270 | `        uint64x2_t v4 = vld1q_u64(p + 8);` | Loads the bytes 64 to 79 of the block into `v4`. |
| 271 | `        uint64x2_t v5 = vld1q_u64(p + 10);` | Loads the bytes 80 to 95 of the block into `v5`. |
| 272 | `        uint64x2_t v6 = vld1q_u64(p + 12);` | Loads the bytes 96 to 111 of the block into `v6`. |
| 273 | `        uint64x2_t v7 = vld1q_u64(p + 14);` | Loads the bytes 112 to 127 of the block into `v7`. |
| 274 | `        uint64x2_t v8 = vld1q_u64(p + 16);` | Loads the bytes 128 to 143 of the block into `v8`. |
| 275 | `        uint64x2_t v9 = vld1q_u64(p + 18);` | Loads the bytes 144 to 159 of the block into `v9`. |
| 276 | `        uint64x2_t v10 = vld1q_u64(p + 20);` | Loads the bytes 160 to 175 of the block into `v10`. |
| 277 | `        uint64x2_t v11 = vld1q_u64(p + 22);` | Loads the bytes 176 to 191 of the block into `v11`. |
| 278 | `        uint64x2_t v12 = vld1q_u64(p + 24);` | Loads the bytes 192 to 207 of the block into `v12`. |
| 279 | `        uint64x2_t v13 = vld1q_u64(p + 26);` | Loads the bytes 208 to 223 of the block into `v13`. |
| 280 | `        uint64x2_t v14 = vld1q_u64(p + 28);` | Loads the bytes 224 to 239 of the block into `v14`. |
| 281 | `        uint64x2_t v15 = vld1q_u64(p + 30);` | Loads the bytes 240 to 255 of the block into `v15`. One loop pass has 16 loads in the source. It reads 256 B, each byte once. In the test binary gcc joined each two neighbour loads into one `ldp` instruction, which loads 32 B into two 16-byte registers. The machine loop has 8 `ldp` instructions at the byte offsets 0, 32, 64 and so on up to 224, in rising order [Ref1]. |
| 282 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | The empty asm statement. Its instruction text (`""`) is empty, so it adds no instruction to the loop. It names the 16 vectors as inputs that must be in vector registers (`"w"`). So the compiler must have all 16 values loaded at this point. `volatile` tells the compiler to keep the statement. This line names `v0` to `v3`. |
| 283 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the list of inputs: `v4` to `v7`. |
| 284 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the list of inputs: `v8` to `v11`. |
| 285 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Ends the list of inputs and the statement: `v12` to `v15`. After this line nothing uses the values. They are dropped. The listing of the test binary shows no instruction that uses a loaded register, and no add of data [Ref1]. |
| 286 | `        p += 32;` | Moves the read position forward by 32 elements, which is 256 B. Machine code in the test binary: `add x0, x0, #0x100` [Ref1]. |
| 287 | `    } while (p < end);` | Repeats the loop while the read position is below the end. Machine code in the test binary: `cmp x1, x0`, then `b.hi` back to the first `ldp`. One loop pass is 11 instructions for 256 B: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1]. |
| 288 | `}` | Ends the function `k_cread`. No value is returned. |
| 289 | `#else` | The other case of the `#if` of line 173: a processor that is not 64-bit Arm. The three asm kernels and `k_cread` are then not compiled. |
| 290 | `#define HAVE_ASM_KERNELS 0` | `HAVE_ASM_KERNELS` is then 0, and `main` refuses to run the asm kernels and `cread` (line 437). |
| 291 | `#endif` | Ends the `#if` of line 173. |

### Function `pass`: one pass of the kernel `k` over the buffer (lines 293 to 326)

| Line | Source | Explanation |
|---:|---|---|
| 293 | `/* One pass over the thread's buffer; returns bytes moved. The sink is per` | Comment: `pass` makes one pass over the buffer of the thread and returns the bytes moved. The sink is the variable that receives the sum of the read kernel `k_read`. The sentence about the sink starts here. |
| 294 | ` * thread (on its stack) so the read kernels of 120 threads do not all store` | Comment: each thread has its own sink, on its stack (line 331). |
| 295 | ` * to one shared cache line. */` | Comment: so the read kernels of 120 threads do not all store to one shared cache line. |
| 296 | `static uint64_t pass(enum kernel k, struct thread *t, size_t n, uint64_t v, volatile uint64_t *sink)` | Starts the function `pass`. It runs the kernel `k` once over the whole buffer of thread `t`. It returns the number of bytes that the caller counts for this pass. `n` is the number of 8-byte elements. `v` is the value for the write kernels. `sink` points to a variable on the stack of the calling thread (line 331). |
| 297 | `{` | Opens the body of `pass`. |
| 298 | `    switch (k) {` | Chooses the kernel by the value of `k`. |
| 299 | `    case K_READ:` | The case of the kernel `read`. |
| 300 | `        *sink = k_read(t->a, n);` | Calls `k_read`, the read kernel with 16 sums, on buffer `a` and stores the returned sum to the variable that `sink` points to. That variable is `volatile`, so the compiler must do this store. It therefore cannot remove the sum, the adds or the loads. This is one 8-byte store per pass over the buffer. |
| 301 | `        return cfg.bytes;` | The pass counts `cfg.bytes`, the buffer size, once. The count is the size that the kernel was asked to read. Nothing is counted inside the kernel. |
| 302 | `    case K_WRITE:` | The case of the kernel `write`. |
| 303 | `        k_write(t->a, n, v);` | Fills buffer `a` with the value `v` (`k_write`). |
| 304 | `        return cfg.bytes;` | The pass counts the buffer size once. |
| 305 | `    case K_COPY:` | The case of the kernel `copy`. |
| 306 | `        k_copy(t->b, t->a, n);` | Copies buffer `a` to buffer `b` (`k_copy`). |
| 307 | `        return 2 * cfg.bytes;` | The pass counts the buffer size twice: the bytes read plus the bytes written. |
| 308 | `#if HAVE_ASM_KERNELS` | Compiles lines 309 to 320 only when the asm kernels exist (`HAVE_ASM_KERNELS` is 1, on 64-bit Arm). The case of `cread` is inside this block. |
| 309 | `    case K_ASMREAD:` | The case of the kernel `asmread`. |
| 310 | `        k_asmread(t->a, n);` | Calls `k_asmread` on buffer `a`. `k_asmread` returns no value, so nothing is stored to `sink`. |
| 311 | `        return cfg.bytes;` | The pass counts the buffer size once. |
| 312 | `    case K_ASMWRITE:` | The case of the kernel `asmwrite`. |
| 313 | `        k_asmwrite(t->a, n, v);` | Fills buffer `a` with the value `v`, with the hand-written loop (`k_asmwrite`). |
| 314 | `        return cfg.bytes;` | The pass counts the buffer size once, as for `write`. |
| 315 | `    case K_ASMCOPY:` | The case of the kernel `asmcopy`. |
| 316 | `        k_asmcopy(t->b, t->a, n);` | Copies buffer `a` to buffer `b`, with the hand-written loop (`k_asmcopy`). |
| 317 | `        return 2 * cfg.bytes;` | The pass counts the buffer size twice, as for `copy`. |
| 318 | `    case K_CREAD:` | The case of the kernel `cread`. |
| 319 | `        k_cread(t->a, n);` | Calls `k_cread` on buffer `a`. `k_cread` returns no value, so nothing is stored to `sink`. |
| 320 | `        return cfg.bytes;` | The pass counts the buffer size once, as for `read` and `asmread`. |
| 321 | `#endif` | Ends the `#if` of line 308. |
| 322 | `    default:` | The case of every other value of `k`. |
| 323 | `        return 0;` | Counts 0 bytes. This line is reached only for an asm kernel or `cread` in a build without them. `main` stops such a run before it creates the threads (line 437). |
| 324 | `    }` | Ends the `switch` of line 298. |
| 325 | `}` | Ends the function `pass`. |

### Function `worker`: start values, pinning and first touch of the buffers (lines 327 to 346)

| Line | Source | Explanation |
|---:|---|---|
| 327 | `static void *worker(void *arg)` | Starts the function `worker`. Each thread that `main` creates (line 452) runs it once. |
| 328 | `{` | Opens the body of `worker`. |
| 329 | `    struct thread *t = arg;` | `t`: the entry of this thread in the thread table. `main` filled its index and its CPU (lines 450 to 451). |
| 330 | `    size_t n = cfg.bytes / 8;` | `n`: the number of 8-byte elements in the buffer. It is 4096 for a buffer of 32768 bytes. |
| 331 | `    volatile uint64_t sink;` | `sink`: the variable that receives the sum of `k_read` (line 300). It lies on the stack of this thread. So the threads of a process with several threads do not store to one shared cache line. |
| 332 | `    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */` | Comment: the store value is known only when the program runs, and its 8 bytes are not all equal. So the compiler cannot turn the write loop into a call of `memset`, the library function that fills memory with one byte value. |
| 333 | `    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;` | `v`: the value that the write kernels store. It is the process id plus the thread index plus 1, times a fixed 64-bit constant. So the compiler does not know it. The read kernels do not use it. |
| 334 | `    uint64_t passes_per_check = CHECK_BYTES / cfg.bytes;` | `passes_per_check`: the number of passes between two clock reads. It is 8 MiB (`CHECK_BYTES`) divided by the buffer size, rounded down. A buffer of 3 MiB, for example, gives 2 passes, which is 6 MiB. So for a buffer below 8 MiB that does not divide 8 MiB, the clock is read after less than 8 MiB. The comment of line 26 says at least 8 MiB. |
| 335 | `    if (passes_per_check == 0)` | Tests whether the division gave 0. That is the case for every buffer above 8 MiB. |
| 336 | `        passes_per_check = 1;` | The value is then set to 1, and the thread reads the clock after every pass. Of the four buffer sizes that `run_cread.sh` passes, only `1G` takes this path. For `32K` the division of line 334 gives 256 passes, for `1M` 8 passes and for `8M` 1 pass. |
| 338 | `    if (cfg.ncpus)` | Tests whether a CPU list was given (option `--cpus`). |
| 339 | `        pin_cpu(t->cpu);` | If so, the thread pins itself to its CPU (`pin_cpu`). The thread does this before it reserves its buffer. `run_cread.sh` starts 1 thread per process, on CPU 0 or on CPU 2. |
| 340 | `    t->a = alloc_buf(cfg.bytes);` | Reserves buffer `a` with `alloc_buf`: `cfg.bytes` bytes that start at a multiple of 2 MiB. |
| 341 | `    k_write(t->a, n, v); /* first touch by this thread */` | Writes `v` into every element of buffer `a` with `k_write`. This write is the first touch: Linux assigns the physical memory of the buffer now, while the thread already runs on its CPU. It is not timed. The comment says: first touch by this thread. |
| 342 | `    if (cfg.run[K_COPY] \|\| cfg.run[K_ASMCOPY]) {` | Tests whether `copy` or `asmcopy` is selected. Only these two kernels use a second buffer. |
| 343 | `        t->b = alloc_buf(cfg.bytes);` | If so, the thread reserves the second buffer `b` of the same size. |
| 344 | `        k_write(t->b, n, v);` | Writes `v` into every element of `b` (first touch, not timed). A process that `run_cread.sh` starts selects no copy kernel. So it has one buffer per thread. |
| 345 | `    }` | Ends the `if` of line 342. |

### Function `worker`: the warm-up pass, the timed interval and the stop rule (lines 347 to 367)

| Line | Source | Explanation |
|---:|---|---|
| 347 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the seven kernels in the order of line 28. |
| 348 | `        if (!cfg.run[k])` | Tests whether kernel `k` is selected. |
| 349 | `            continue;` | A kernel that is not selected is skipped. With `--kernel readcmp`, which `run_cread.sh` passes, three kernels are selected (line 424). The thread times them in one process in this order: `read`, then `asmread`, then `cread`. So `asmread` and `cread` are timed after another kernel in the same process. |
| 350 | `        for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions of this kernel. Each repetition is one timed interval. `run_cread.sh` passes `--reps 3`, which gives 3 intervals per kernel. |
| 351 | `            pass(k, t, n, v, &sink); /* warm-up */` | The warm-up: one whole pass of the same kernel over the buffer. It runs before every timed interval, not only before the first one. It is not timed, and its byte count is dropped. |
| 352 | `            pthread_barrier_wait(&bar);` | Waits at the barrier until all workers and the main thread (line 468) have arrived. A thread that arrives early waits here and runs no kernel. The barrier then releases all threads in one step. The timed interval of a thread starts after this release, at its own clock read (line 353). The program does not store the start times. So it does not show how far apart the starts of the threads are. With 1 thread, as in `run_cread.sh`, the worker and the main thread meet here. |
| 353 | `            double t0 = now_s(), t1;` | `t0`: the clock read directly after the barrier. It is the start of the timed interval of this thread. Each thread has its own `t0`. `t1` will hold the clock read after the passes (line 358). |
| 354 | `            uint64_t bytes = 0, p = 0;` | `bytes` counts the bytes of this interval, and `p` counts its passes. Both start at 0. |
| 355 | `            do {` | Starts the loop of the timed work. Its body runs at least once. |
| 356 | `                for (uint64_t c = 0; c < passes_per_check; c++, p++)` | The inner `for` runs `passes_per_check` passes without a clock read between them (lines 334 to 336). |
| 357 | `                    bytes += pass(k, t, n, v + p, &sink);` | Runs one pass and adds its byte count to `bytes`. For the kernel `cread` each pass is one call of `k_cread` over the whole buffer. `v + p` gives the write kernels a new value in every pass. |
| 358 | `                t1 = now_s();` | `t1`: the clock read after the passes. The clock is never read inside a pass. |
| 359 | `            } while (t1 - t0 < cfg.min_s);` | The stop rule. The loop repeats while less than `cfg.min_s` has passed after `t0`. With `--min-ms 500`, which `run_cread.sh` passes, that is 0.5 s. The test comes only after the passes of lines 356 to 357. So a thread never stops inside a pass. Its interval is 0.5 s or longer. It exceeds 0.5 s by less than the time between its last two clock reads. |
| 360 | `            t->res[k][rep].bytes = bytes;` | Stores the bytes that this thread counted, for this kernel and repetition. |
| 361 | `            t->res[k][rep].elapsed_s = t1 - t0;` | Stores the time `t1 - t0` of this thread. The interval ended at the last clock read of line 358. The time covers the passes and the clock reads between them. It does not cover the warm-up pass or the waits at the barrier. |
| 362 | `            pthread_barrier_wait(&bar);` | Waits at the barrier until all workers have finished the interval and the main thread (line 469) has arrived. A thread that stopped early waits here and runs no kernel while the other threads finish their last pass. |
| 363 | `        }` | Ends the repetition loop of line 350. The next repetition starts with its warm-up pass directly after the barrier. The code has no sleep there. |
| 364 | `    }` | Ends the kernel loop of line 347. With `readcmp` the thread goes on directly from the last interval of one kernel to the warm-up pass of the next kernel. The code has no sleep there. |
| 365 | `    return NULL;` | The thread ends after the last repetition of the last selected kernel. |
| 366 | `}` | Ends the function `worker`. |

### Function `usage`: print the options and stop (lines 368 to 377)

| Line | Source | Explanation |
|---:|---|---|
| 368 | `static void usage(void)` | Starts the function `usage`. It prints the list of options to the error output and ends the program with exit status 2. |
| 369 | `{` | Opens the body of `usage`. |
| 370 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to the error output. Its text is in lines 371 to 374. |
| 371 | `            "usage: bandwidth [--threads T --cpus LIST] [--bytes B] "` | Text of the message: the options for the thread count, the CPU list and the buffer size. |
| 372 | `            "[--kernel read\|write\|copy\|all\|asmread\|asmwrite\|asmcopy\|asmall] "` | Text of the message: names that the option `--kernel` accepts. The text does not list `cread` and `readcmp`, which the code also accepts (lines 421 to 424). |
| 373 | `            "[--min-ms MS] [--reps R] [--no-thp] [--per-thread]\n"` | Text of the message: the options for the minimum time in ms, the number of repetitions, no 2 MiB pages, and one line per thread. |
| 374 | `            "  asm* kernels: aarch64 only, loads/stores only, bytes must be a multiple of 256\n");` | Text of the message, second line: the asm kernels exist only on 64-bit Arm (`aarch64`), they hold loads and stores only, and the buffer size must be a multiple of 256. The check of line 435 applies the rule of 256 to every kernel, not only to the asm kernels. This line ends the `fprintf` call. |
| 375 | `    exit(2);` | Ends the program with exit status 2. |
| 376 | `}` | Ends the function `usage`. |

### Function `main`: defaults and arguments (lines 378 to 430)

| Line | Source | Explanation |
|---:|---|---|
| 378 | `int main(int argc, char **argv)` | Starts the function `main`. It reads the arguments, starts the threads, and prints one rate row per timed interval. |
| 379 | `{` | Opens the body of `main`. |
| 380 | `    int threads_given = 0;` | `threads_given`: becomes 1 when the option `--threads` is given (line 393). The check of line 431 uses it. |
| 381 | `    cfg.bytes = 1UL << 20;` | Default before the arguments are read: a buffer of 1 MiB (1048576 bytes) per thread. |
| 382 | `    cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;` | Default: the three C kernels `read`, `write` and `copy` are selected. |
| 384 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments of the command line. |
| 385 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 386 | `        int more = i + 1 < argc;` | `more`: true when one more argument follows, which an option with a value needs. |
| 387 | `        if (!strcmp(a, "--no-thp")) {` | Tests whether the argument is `--no-thp`. `strcmp` returns 0 when two texts are equal. |
| 388 | `            cfg.use_thp = 0;` | `--no-thp` forbids 2 MiB pages for the buffers (line 133). `run_cread.sh` does not pass it. |
| 389 | `        } else if (!strcmp(a, "--per-thread")) {` | Tests for `--per-thread`. |
| 390 | `            cfg.per_thread = 1;` | `--per-thread` adds one output line per thread and repetition (line 492). `run_cread.sh` does not pass it. |
| 391 | `        } else if (!strcmp(a, "--threads") && more) {` | Tests for `--threads` with a value after it. |
| 392 | `            cfg.threads = atoi(argv[++i]);` | The number of threads. `atoi` turns the next argument into an integer, and `++i` steps over that argument. `run_cread.sh` passes 1. |
| 393 | `            threads_given = 1;` | Notes that `--threads` was given. |
| 394 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 395 | `            parse_cpus(argv[++i]);` | The CPU list, read by `parse_cpus`. `run_cread.sh` passes one CPU: 0 or 2. |
| 396 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 397 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size of each thread, read by `parse_bytes`. `run_cread.sh` passes `32K`, `1M`, `8M` or `1G`. |
| 398 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Tests for `--min-ms` with a value after it. |
| 399 | `            cfg.min_s = atof(argv[++i]) / 1000.0;` | The minimum time of an interval. `atof` reads the value in ms, and the division by 1000 gives seconds. `run_cread.sh` passes 500, which gives 0.5 s. |
| 400 | `        } else if (!strcmp(a, "--reps") && more) {` | Tests for `--reps` with a value after it. |
| 401 | `            cfg.reps = atoi(argv[++i]);` | The number of timed intervals per kernel. `run_cread.sh` passes 3. |
| 402 | `        } else if (!strcmp(a, "--kernel") && more) {` | Tests for `--kernel` with a value after it. |
| 403 | `            const char *k = argv[++i];` | `k`: the kernel name that follows `--kernel`. `run_cread.sh` passes `readcmp`. |
| 404 | `            memset(cfg.run, 0, sizeof cfg.run);` | First clears every selection: `memset` sets all flags of `cfg.run` to 0. Then one of the next lines selects by the name. |
| 405 | `            if (!strcmp(k, "all"))` | Tests for the name `all`. |
| 406 | `                cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;` | `all` selects the three C kernels `read`, `write` and `copy`. |
| 407 | `            else if (!strcmp(k, "read"))` | Tests for the name `read`. |
| 408 | `                cfg.run[K_READ] = 1;` | Selects the kernel `read` only. It is the function `k_read`, the read kernel with 16 sums. |
| 409 | `            else if (!strcmp(k, "write"))` | Tests for the name `write`. |
| 410 | `                cfg.run[K_WRITE] = 1;` | Selects the kernel `write` only. |
| 411 | `            else if (!strcmp(k, "copy"))` | Tests for the name `copy`. |
| 412 | `                cfg.run[K_COPY] = 1;` | Selects the kernel `copy` only. |
| 413 | `            else if (!strcmp(k, "asmall"))` | Tests for the name `asmall`. |
| 414 | `                cfg.run[K_ASMREAD] = cfg.run[K_ASMWRITE] = cfg.run[K_ASMCOPY] = 1;` | `asmall` selects the three asm kernels. |
| 415 | `            else if (!strcmp(k, "asmread"))` | Tests for the name `asmread`. |
| 416 | `                cfg.run[K_ASMREAD] = 1;` | Selects the kernel `asmread` only. |
| 417 | `            else if (!strcmp(k, "asmwrite"))` | Tests for the name `asmwrite`. |
| 418 | `                cfg.run[K_ASMWRITE] = 1;` | Selects the kernel `asmwrite` only. |
| 419 | `            else if (!strcmp(k, "asmcopy"))` | Tests for the name `asmcopy`. |
| 420 | `                cfg.run[K_ASMCOPY] = 1;` | Selects the kernel `asmcopy` only. |
| 421 | `            else if (!strcmp(k, "cread"))` | Tests for the name `cread`. |
| 422 | `                cfg.run[K_CREAD] = 1;` | Selects the kernel `cread` only. It is the function `k_cread`. |
| 423 | `            else if (!strcmp(k, "readcmp")) /* asmread, cread and read in one process */` | Tests for the name `readcmp`. The comment says: `asmread`, `cread` and `read` in one process. The order of the names in the comment is not the order in which the kernels run. |
| 424 | `                cfg.run[K_ASMREAD] = cfg.run[K_CREAD] = cfg.run[K_READ] = 1;` | `readcmp` selects the three read kernels `asmread`, `cread` and `read`. One process then times them in the order of line 28: `read` first, then `asmread`, then `cread` (line 347). |
| 425 | `            else` | The case of every other name. |
| 426 | `                usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 427 | `        } else {` | The case of every other argument: an unknown option, or an option without its value. |
| 428 | `            usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 429 | `        }` | Ends the chain of tests that starts in line 387. |
| 430 | `    }` | Ends the loop over the arguments (line 384). |

### Function `main`: checks of the arguments (lines 431 to 443)

| Line | Source | Explanation |
|---:|---|---|
| 431 | `    if (threads_given && cfg.ncpus == 0) {` | Check: `--threads` is accepted only together with `--cpus`. The test is true when `--threads` was given and the CPU list is empty. |
| 432 | `        fprintf(stderr, "--threads requires --cpus\n");` | Prints `--threads requires --cpus` to the error output. |
| 433 | `        usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 434 | `    }` | Ends the `if` of line 431. |
| 435 | `    if (cfg.threads < 1 \|\| cfg.reps < 1 \|\| cfg.reps > MAX_REPS \|\| cfg.bytes == 0 \|\| cfg.bytes % 256 != 0)` | Checks of the values. The thread count must be 1 or more. The repetitions must be 1 to 32. The buffer size must not be 0, and it must be a multiple of 256 B. Every kernel then ends exactly at the end of the buffer: `k_read` moves in steps of 128 B, the asm kernels and `k_cread` in steps of 256 B. |
| 436 | `        usage();` | A failed check prints the option list and ends the program with exit status 2 (`usage`). |
| 437 | `    if (!HAVE_ASM_KERNELS && (cfg.run[K_ASMREAD] \|\| cfg.run[K_ASMWRITE] \|\| cfg.run[K_ASMCOPY] \|\| cfg.run[K_CREAD])) {` | Tests whether an asm kernel or `cread` is selected in a build without them (a processor that is not 64-bit Arm). |
| 438 | `        fprintf(stderr, "asm kernels need aarch64\n");` | Prints `asm kernels need aarch64` to the error output. The message is the same when only `cread` is selected. |
| 439 | `        return 2;` | The program ends with exit status 2. |
| 440 | `    }` | Ends the `if` of line 437. |
| 441 | `    if (cfg.ncpus && cfg.threads > cfg.ncpus)` | Tests whether a CPU list was given and there are more threads than CPUs in it. |
| 442 | `        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);` | This only gives a warning on the error output, with both numbers. The program goes on. The list is then used again from its start (line 451). |

### Function `main`: thread table, barrier, threads and header lines (lines 444 to 462)

| Line | Source | Explanation |
|---:|---|---|
| 444 | `    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);` | Allocates the thread table with `calloc`: one `struct thread` per thread, filled with zeros. |
| 445 | `    if (!th \|\| pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {` | Tests the allocation and creates the barrier for `cfg.threads + 1` threads: the workers plus the main thread. With 1 thread, as in `run_cread.sh`, this is 2. |
| 446 | `        perror("setup");` | On a failure of one of the two steps: `perror` prints the word `setup` and an error text. |
| 447 | `        return 2;` | On a failure: the program ends with exit status 2. |
| 448 | `    }` | Ends the `if` of line 445. |
| 449 | `    for (int i = 0; i < cfg.threads; i++) {` | Loop that creates the threads. |
| 450 | `        th[i].idx = i;` | Thread `i` gets the index `i`. |
| 451 | `        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;` | Thread `i` gets the CPU `cfg.cpus[i % cfg.ncpus]`: entry `i` of the CPU list. The list is used again from its start when there are more threads than entries. `run_cread.sh` passes 1 thread and one CPU, so thread 0 gets that CPU. Without a CPU list the value is -1, and the thread is not pinned (line 338). |
| 452 | `        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {` | Creates the thread. It starts `worker` immediately: the thread pins itself, reserves and writes its buffer, runs the first warm-up pass and then waits at the barrier. |
| 453 | `            perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and an error text. |
| 454 | `            return 2;` | The program then ends with exit status 2. |
| 455 | `        }` | Ends the `if` of line 452. |
| 456 | `    }` | Ends the loop of line 449. |
| 458 | `    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "` | Prints the first header line to the standard output. It starts with `#` and gives the rate formula: GB = 1e9 bytes, and `aggregate_GBps` is the sum of the bytes of all threads divided by the longest thread time. |
| 459 | `           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",` | Continues the text of the header line: copy counts the bytes read plus the bytes written. Then come the settings of the process: the thread count, the buffer size per thread in bytes, the minimum time in ms and the request for 2 MiB pages. |
| 460 | `           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");` | The four values of the header line. `thp=` shows `madvise` when the program asks for 2 MiB pages and `nohugepage` with `--no-thp`. This text shows the request only. It does not show that the buffers got such pages. |
| 461 | `    printf("kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,"` | Prints the second header line: the 10 column names of the interval rows. This line holds the first 7 names. |
| 462 | `           "per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps\n");` | Continues the column names: the lowest, the highest and the mean thread rate. |

### Function `main`: rate of each interval, output rows and end (lines 463 to 506)

| Line | Source | Explanation |
|---:|---|---|
| 463 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the kernels in the same order as the workers (line 347). |
| 464 | `        if (!cfg.run[k])` | The same skip rule as in the workers (line 348). |
| 465 | `            continue;` | Skips a kernel that is not selected. |
| 466 | `        double best = -1;` | `best`: will hold the highest total rate of the repetitions of this kernel. |
| 467 | `        for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions, as the main thread sees them. |
| 468 | `            pthread_barrier_wait(&bar); /* release the workers */` | First wait: the barrier opens when the main thread and all workers have arrived. Each worker arrives after its warm-up pass (line 352). The workers then start their timed interval (line 353). The comment says: release the workers. |
| 469 | `            pthread_barrier_wait(&bar); /* all workers finished this rep */` | Second wait: it returns when every worker has finished its interval (line 362). The main thread does no work during the interval. The program does not pin the main thread. The comment says: all workers finished this repetition. |
| 470 | `            uint64_t total = 0;` | `total`: the bytes of all threads in this interval. It starts at 0. While the main thread computes and prints the row (lines 470 to 489), the workers already run the warm-up pass of the next interval, when there is one. The next timed interval starts only after the main thread waits at the barrier again (line 468). |
| 471 | `            double max_el = 0, mn = 1e30, mx = 0, sum = 0;` | Start values for one row: `max_el` (the longest thread time), `mn` and `mx` (the lowest and the highest thread rate) and `sum` (the sum of the thread rates). `mn` starts at 1e30, a value above every rate. |
| 472 | `            for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 473 | `                struct result *r = &th[i].res[k][rep];` | `r`: the result of thread `i` for this kernel and repetition (lines 360 to 361). |
| 474 | `                double g = (double)r->bytes / r->elapsed_s / 1e9;` | `g`: the rate of this thread in GB/s. It is the bytes of the thread, divided by the time of the same thread, divided by 1e9. |
| 475 | `                total += r->bytes;` | Adds the bytes of the thread to `total`. |
| 476 | `                if (r->elapsed_s > max_el)` | Tests whether the time of this thread is the longest so far. |
| 477 | `                    max_el = r->elapsed_s;` | Keeps the longest thread time in `max_el`. |
| 478 | `                if (g < mn)` | Tests whether the rate of this thread is the lowest so far. |
| 479 | `                    mn = g;` | Keeps the lowest thread rate in `mn`. |
| 480 | `                if (g > mx)` | Tests whether the rate of this thread is the highest so far. |
| 481 | `                    mx = g;` | Keeps the highest thread rate in `mx`. |
| 482 | `                sum += g;` | Adds the thread rate to `sum` for the mean. |
| 483 | `            }` | Ends the loop over the threads (line 472). |
| 484 | `            double agg = (double)total / max_el / 1e9;` | `agg`: the total rate of the interval in GB/s. It is the bytes of all threads, divided by the longest thread time, divided by 1e9. The output column is `aggregate_GBps`. A thread with a shorter time adds no bytes after its own stop. So `agg` is never above the sum of the thread rates. It is lower when the times of the threads differ. |
| 485 | `            if (agg > best)` | Tests whether this `agg` is the highest of the repetitions so far. |
| 486 | `                best = agg;` | Keeps the highest `agg` in `best`. |
| 487 | `            printf("%s,%d,%lu,%d,%lu,%.4f,%.2f,%.2f,%.2f,%.2f\n", kernel_name[k], cfg.threads,` | Prints one interval row with 10 columns, separated by commas. This line holds the format and the values of columns 1 and 2: the kernel name and the thread count. |
| 488 | `                   (unsigned long)cfg.bytes, rep, (unsigned long)total, max_el, agg, mn, mx,` | The values of columns 3 to 9: the buffer size per thread in bytes, the repetition number (counted from 0), `total_bytes` (`total`), `elapsed_s` (`max_el`, with 4 decimals), `aggregate_GBps` (`agg`, with 2 decimals), and the lowest and the highest thread rate in GB/s (2 decimals each). |
| 489 | `                   sum / cfg.threads);` | The value of column 10: the mean thread rate in GB/s, which is `sum / cfg.threads`, with 2 decimals. |
| 490 | `        }` | Ends the repetition loop of line 467. |
| 491 | `        printf("%s,%d,%lu,best,,,%.2f,,,\n", kernel_name[k], cfg.threads, (unsigned long)cfg.bytes, best);` | After the last repetition: prints the `best` row. It has the word `best` in column 4 and the highest `agg` of the repetitions in column 7 (`aggregate_GBps`). The columns 5, 6, 8, 9 and 10 are empty. The script `make_html.round2.py` skips this row. |
| 492 | `        if (cfg.per_thread) {` | Only with `--per-thread`: lines 495 to 499 print one more line per thread and repetition. `run_cread.sh` does not pass this option. |
| 493 | `            /* thread,<index>,<cpu>,<kernel>,<rep>,<GB/s>: one line per thread and repetition, so that` | Comment: the form of the line: the word `thread`, the thread index, the CPU, the kernel, the repetition and the rate in GB/s. One line per thread and repetition. |
| 494 | `             * concurrent per-group totals can be formed from one repetition (reviewer's request) */` | Comment: the purpose of these lines. The rates of a group of threads that ran at the same time can be added from one repetition. The comment says that a reviewer asked for this. |
| 495 | `            for (int i = 0; i < cfg.threads; i++)` | Loop over the threads. |
| 496 | `                for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions. |
| 497 | `                    struct result *r = &th[i].res[k][rep];` | `r`: the result of thread `i` for this kernel and repetition. |
| 498 | `                    printf("thread,%d,%d,%s,%d,%.2f\n", i, th[i].cpu, kernel_name[k], rep, (double)r->bytes / r->elapsed_s / 1e9);` | Prints the line: the word `thread`, the thread index, the CPU, the kernel name, the repetition and the thread rate in GB/s with 2 decimals. The rate is the bytes of the thread, divided by the time of the same thread, divided by 1e9. |
| 499 | `                }` | Ends the loop of line 496. |
| 500 | `        }` | Ends the `if` of line 492. |
| 501 | `        fflush(stdout);` | `fflush` writes the buffered rows of this kernel to the output now. |
| 502 | `    }` | Ends the kernel loop of line 463. |
| 503 | `    for (int i = 0; i < cfg.threads; i++)` | Loop over the threads. |
| 504 | `        pthread_join(th[i].tid, NULL);` | Waits until worker thread `i` has ended (`pthread_join`). After the loop every worker has ended. |
| 505 | `    return 0;` | Ends the process with exit status 0. |
| 506 | `}` | Ends the function `main`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-cread/cread-20261113T060510Z/probe.txt`: the build record that `run_cread.sh` wrote on CRB on 2026-11-13. It holds the compiler (gcc 14.2.0), the compiler flags and three sha256 values. The sha256 of `bandwidth_cread.c` in it equals the sha256 of the file that this page explains. Under the headings `=== k_cread ===`, `=== k_asmread ===` and `=== k_read ===` it holds the machine-code listing of these three functions of the test binary.
- [Ref2] Check made for this page on 2026-11-25: the command `diff` on the files `kernels-2026-11-13/bandwidth.orig.c` and `cread-2026-11-12/bandwidth_cread.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code`. It prints 6 places: the include of `arm_neon.h`, the two lines of the kernel list, the function `k_cread` with its comment, the case `K_CREAD` in `pass`, the names `cread` and `readcmp`, and the test for a build without the asm kernels.
