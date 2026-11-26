# `latency.c` explained, line by line

- Source file: `bench/latency.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 290 lines, 10051 bytes).
- sha256 of the source when this page was built: `9f5054721efed1945bd9db2b9a95f7f39668fd87cca297c8dfb97a279340add9`.

## Short version: purpose

`latency.c` is a benchmark with one thread that measures the latency of a load for each buffer size, in nanoseconds per load. It fills the buffer with one random cycle of pointers, one pointer per 64-byte cache line, and times how long the thread needs to follow them. Each load needs the result of the load before it, so the time per load shows how long one load takes from the cache level, or from the memory, that holds a buffer of this size.

## Words used here

- **Line**: a cache line, 64 bytes. The caches of the chip hold memory in pieces of this size.
- **Pointer chase**: a loop in which each load reads the address of the next load.
- **Dependent load**: a load whose address is the value that the load before it delivered.
- **Load-to-use latency**: the time from the start of a load until the next instruction can use the loaded value.
- **Chain**: one cycle of pointers through all lines of the buffer. Chain number `c` uses the 8-byte word number `c` of each line.
- **Cycle**: a closed walk along the pointers. It starts at any line, visits every line of the buffer once and arrives at its start again. One cycle has as many loads as the buffer has lines.
- **Shuffle of Sattolo**: an algorithm that puts the lines into a random order that forms one single cycle.
- **Prefetcher**: the part of a core that loads memory in advance when it finds a pattern in the addresses.
- **Temporal prefetcher**: a prefetcher that records the order of earlier cache misses and fetches the same lines in the same order again.
- **Standard mode**: the mode without the option `--fresh`. Every timed interval walks chain 0 repeatedly.
- **Fresh mode**: the mode of the option `--fresh`. Every timed interval is one pass over a chain that was never walked before.
- **Chunk**: the loads between two clock reads in the standard mode. A chunk is a whole number of cycles, about 1048576 loads for a small buffer.
- **Warm-up**: loads that run before a timed interval and are not timed.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **`AnonHugePages`**: a value that Linux reports for a process: the memory without a file behind it that lies on transparent huge pages, in kB.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **KiB, MiB, GiB**: 1024 bytes, 1048576 bytes and 1073741824 bytes.

## Main flow

1. `main` sets the defaults and reads the arguments (lines 230 to 268).
2. It adds the sizes of the doubling range of `--min` and `--max` to the size list and checks the settings (lines 269 to 279).
3. It pins the thread to the CPU of `--cpu` when that option was given (lines 280 to 282).
4. It prints the two header lines of the output (lines 284 to 286).
5. It calls `run_size` once per size, in the order of the list (lines 287 to 288). The steps 6 to 11 happen inside `run_size`.
6. Reserve the buffer and build the chains: `alloc_buf` reserves a range whose start is a multiple of 2 MiB, and `build_cycle` writes every line for the first time and builds one random cycle of pointers per chain (lines 144 to 156).
7. With `--build-cpu`: walk chain 0 once on the build CPU, then pin the thread to the CPU of `--cpu` (lines 157 to 160).
8. Print a comment line with the size and the `AnonHugePages` value of the process (line 161).
9. Fresh mode: walk chain 0 twice as a warm-up, then time exactly one pass over each other chain (lines 166 to 188). With `--build-cpu` the two warm-up walks are left out, and the walk of step 7 is the only warm-up.
10. Standard mode: walk one cycle as a warm-up, then run the timed intervals. Each interval is a row of chunks, with one clock read after each chunk (lines 189 to 210).
11. Print the `best` row and release the buffer (lines 211 to 213).

## Behavior a reader must know

- What is timed: only the calls of `chase` and, in the standard mode, one clock read per chunk. The build of the buffer, the first write, the warm-up walks and the output are outside every timed interval.
- The clock is `CLOCK_MONOTONIC`. It is read directly before the first load of an interval and directly after each chunk (line 196, line 200), or directly before and after the one pass of the fresh mode (line 178, line 180).
- The latency of a row is the elapsed time divided by the number of loads of the interval, in nanoseconds per load. The `best` row holds the smallest value of the size.
- The time per load also holds the loop control of `chase`: one step of the counter and one test per 8 loads.
- In the standard mode an interval ends at the first clock read at which two conditions hold: the time of `--min-ms` has passed (300 ms by default), and the cycles of `--min-cycles` were walked (2 by default). There are 3 intervals per size by default.
- In the fresh mode an interval is one pass of `n` loads, where `n` is the number of lines. The options `--reps`, `--min-ms` and `--min-cycles` have no effect there.
- Thread placement: the program has one thread. With `--cpu` it is pinned to that CPU for the whole run. With `--build-cpu` the buffer is written and built on the build CPU, and the timed chase runs on the CPU of `--cpu`. Without `--cpu` nothing is pinned.
- The buffer: one new buffer per size. The reserved range is rounded up to a multiple of 2 MiB, but the chains use only the bytes of the size. By default the program asks Linux for 2 MiB pages (`MADV_HUGEPAGE`). With `--no-thp` it asks for no 2 MiB pages (`MADV_NOHUGEPAGE`). It does not test the result. It prints the `AnonHugePages` value in the comment line of each size.
- The order of the pointers is random but fixed: the start value of the random numbers is a constant. So a size has the same order of the lines in every run.
- A size must be a multiple of 512 bytes. If not, the program ends with exit status 2. A wrong argument also ends it with exit status 2, after the usage text.

## Source and explanation, line by line

- Text shown: the file `bench/latency.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (290 lines, 10051 bytes, sha256 `9f5054721efed1945bd9db2b9a95f7f39668fd87cca297c8dfb97a279340add9`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment (lines 1 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Comment: starts the header comment of the file. It ends in line 10. |
| 2 | ` * latency.c - single-thread dependent-load pointer chase.` | Comment: the name and the purpose of the program: a pointer chase with one thread. In a pointer chase each load reads the address of the next load. The comment calls such a load a dependent load. |
| 3 | ` *` | Comment: an empty line inside the header comment. |
| 4 | ` * The buffer holds one 8-byte pointer per 64-byte line. The pointers form` | Comment: the buffer holds one pointer of 8 bytes in each cache line of 64 bytes. With the option `--fresh` a line holds up to 8 pointers (lines 155 to 156). |
| 5 | ` * one random cycle through all lines, built with Sattolo's algorithm (a` | Comment: the pointers form one random cycle through all lines. A walk that starts at any line visits every line once and then comes back to its start. The cycle is built with the algorithm of Sattolo (lines 114 to 119). |
| 6 | ` * Fisher-Yates shuffle that swaps element i only with an element j < i, which` | Comment: this algorithm is a Fisher-Yates shuffle, a standard way to put a list into a random order, with one change. Element `i` is swapped only with an element `j` below `i`, never with itself. |
| 7 | ` * yields a single n-cycle). Each load depends on the previous one, so the` | Comment: the change gives one single cycle of length `n`, where `n` is the number of lines. The next sentence starts here: each load depends on the load before it. |
| 8 | ` * hardware prefetcher cannot run ahead and elapsed / loads is the load-to-use` | Comment: so the hardware prefetcher cannot fetch lines ahead of the chase. The prefetcher is the part of a core that loads memory in advance when it finds a pattern in the addresses. The comment goes on: the measured time divided by the number of loads (`elapsed / loads`) is the load-to-use latency. |
| 9 | ` * latency of one dependent load at that footprint.` | Comment: the end of the sentence: the latency of one dependent load at this buffer size, which the comment calls footprint. Load-to-use latency is the time from the start of a load until the next instruction can use the loaded value. |
| 10 | ` */` | Comment: the end of the header comment. |

### Include lines, constants and global variables (lines 11 to 27)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include line. This makes the Linux-only calls of the headers visible, for example `sched_setaffinity` and `CPU_SET` (lines 63 to 66). |
| 12 | `#include <sched.h>` | Includes the header for the CPU pinning: the type `cpu_set_t`, the macros `CPU_ZERO` and `CPU_SET`, and the call `sched_setaffinity`. |
| 13 | `#include <stdint.h>` | Includes the integer types of fixed size: `uint64_t` (64 bits), `uint8_t` (8 bits) and `uintptr_t` (an integer that can hold an address). |
| 14 | `#include <stdio.h>` | Includes the output functions `printf`, `fprintf`, `perror` and `fflush`, and the file functions `fopen`, `fgets`, `sscanf` and `fclose` that `anon_huge_kb` uses. |
| 15 | `#include <stdlib.h>` | Includes `exit` and the functions that turn text into a number: `strtod`, `atoi` and `atof`. |
| 16 | `#include <string.h>` | Includes the text functions `strcmp` (compare two texts) and `strtok` (cut a text into pieces). |
| 17 | `#include <sys/mman.h>` | Includes `mmap`, `madvise` and `munmap`, the Linux calls that reserve the buffer, set its page size request and release it. |
| 18 | `#include <time.h>` | Includes `clock_gettime` and the type `struct timespec`. The function `now_s` reads the clock with them. |
| 20 | `#define LINE_BYTES 64` | `LINE_BYTES`: 64, the size of one cache line in bytes. The program treats the buffer as a row of such lines. The chase loads one pointer from each line. |
| 21 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2 MiB (2097152 bytes), the size of one huge page. The expression shifts the number 2 left by 20 bits. `alloc_buf` aligns the buffer to this size (line 76, line 83). |
| 22 | `#define MAX_SIZES 64` | `MAX_SIZES`: one start of the program accepts at most 64 buffer sizes (line 232). |
| 23 | `#define MIN_CHUNK_LOADS (1UL << 20)` | `MIN_CHUNK_LOADS`: 1048576 loads (2 to the power 20). In the standard mode the program reads the clock only after a group of loads, which the source calls a chunk (line 192). For a buffer with fewer than 1048576 lines a chunk has at most this many loads and more than half of this number. For a buffer with 1048576 lines or more a chunk is one whole cycle, so it has as many loads as the buffer has lines. |
| 25 | `static void *volatile sink; /* the pointer object is volatile, so the store survives */` | `sink`: a global pointer variable. The word `volatile` stands after the star, so the variable itself is volatile: the compiler must carry out every store to it. The program stores the last pointer of a chase there (line 175, line 181, line 209). So the result of the loads is used, and the compiler has no reason to remove them. The comment says the same: the store survives. |
| 26 | `static uint64_t rng_state;` | `rng_state`: the 64-bit state of the random number generator `xorshift64`. `build_cycle` sets it to a start value (line 111). |

### Function `now_s`: read the clock (lines 28 to 34)

| Line | Source | Explanation |
|---:|---|---|
| 28 | `static double now_s(void)` | Starts the function `now_s`. It reads the clock and returns the time in seconds. Every time value of the program comes from this function (line 178, line 180, line 196, line 200). |
| 29 | `{` | Opens the body of `now_s`. |
| 30 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 31 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | Reads `CLOCK_MONOTONIC` into `ts`. This is the Linux clock that only moves forward. A change of the date of the machine does not change it. It is the only clock that the file reads. |
| 32 | `    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;` | Returns the time in seconds as a `double`: the seconds plus the nanoseconds times 1e-9. |
| 33 | `}` | Ends the function `now_s`. |

### Function `xorshift64`: the random number generator (lines 35 to 42)

| Line | Source | Explanation |
|---:|---|---|
| 35 | `static uint64_t xorshift64(void)` | Starts the function `xorshift64`. It is a small generator of pseudo-random numbers. Each call changes the state `rng_state` in three steps and returns the new state. The same start value always gives the same row of numbers. |
| 36 | `{` | Opens the body of `xorshift64`. |
| 37 | `    rng_state ^= rng_state << 13;` | Step 1: shifts the state left by 13 bits and combines the result with the state by exclusive or (the operator `^=`). |
| 38 | `    rng_state ^= rng_state >> 7;` | Step 2: the same with a shift right by 7 bits. |
| 39 | `    rng_state ^= rng_state << 17;` | Step 3: the same with a shift left by 17 bits. |
| 40 | `    return rng_state;` | Returns the new state as the random number. |
| 41 | `}` | Ends the function `xorshift64`. |

### Function `parse_bytes`: read a size such as `1.5M` (lines 43 to 60)

| Line | Source | Explanation |
|---:|---|---|
| 43 | `/* Accepts "4096", "16K", "1.5M", "2G" (K/M/G are powers of 1024). */` | Comment: the function accepts sizes such as `4096`, `16K`, `1.5M` and `2G`. The letters K, M and G stand for powers of 1024. |
| 44 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text into a number of bytes. `main` calls it for the options `--min`, `--max` and `--sizes` (line 245, line 247, line 263). |
| 45 | `{` | Opens the body of `parse_bytes`. |
| 46 | `    char *end;` | `end`: will point to the first character after the number. |
| 47 | `    double v = strtod(s, &end);` | `strtod` reads a number from the start of the text `s` into `v`. The number may have a decimal point. `strtod` sets `end` to the first character that is not part of the number. |
| 48 | `    double mul = 1;` | `mul`: the factor of the suffix. It stays 1 when the text has no suffix. |
| 49 | `    switch (*end) {` | Looks at the character after the number. |
| 50 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | `k` or `K`: the factor is 1024 (2 to the power 10, which is 1 KiB). `end++` steps over the suffix. |
| 51 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | `m` or `M`: the factor is 1048576 (2 to the power 20, which is 1 MiB). So `1.5M` gives 1572864 bytes. |
| 52 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | `g` or `G`: the factor is 1073741824 (2 to the power 30, which is 1 GiB). |
| 53 | `    }` | Ends the `switch` of line 49. |
| 54 | `    if (end == s \|\| *end != '\0' \|\| v <= 0) {` | Tests three error cases. No number was read (`end == s`). Or other text follows the number and its suffix. Or the value is 0 or below. |
| 55 | `        fprintf(stderr, "bad size: %s\n", s);` | On an error: prints `bad size:` and the text to the error output. |
| 56 | `        exit(2);` | On an error: the program ends with exit status 2. |
| 57 | `    }` | Ends the `if` of line 54. |
| 58 | `    return (uint64_t)(v * mul);` | Returns the number times the factor as a whole number of bytes. A fraction of a byte is cut off. |
| 59 | `}` | Ends the function `parse_bytes`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 61 to 71)

| Line | Source | Explanation |
|---:|---|---|
| 61 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It pins the calling thread to the CPU with the number `cpu`: Linux then runs the thread on that CPU only. The program has one thread, so the call places the whole program. `main` calls it for the option `--cpu` (line 282), and `run_size` for the option `--build-cpu` (line 145, line 159). |
| 62 | `{` | Opens the body of `pin_cpu`. |
| 63 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 64 | `    CPU_ZERO(&set);` | Empties the set. |
| 65 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 66 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 67 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 68 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 69 | `    }` | Ends the `if` of line 66. |
| 70 | `}` | Ends the function `pin_cpu`. |

### Function `alloc_buf`: one buffer, aligned for huge pages (lines 72 to 90)

| Line | Source | Explanation |
|---:|---|---|
| 72 | `/* Maps round_up(bytes, 2 MiB) at a 2 MiB-aligned address. The mapping is returned in raw and raw_len` | Comment: the function maps `bytes` rounded up to a multiple of 2 MiB, at an address that is a multiple of 2 MiB. To map means to ask Linux for a range of memory addresses. The second sentence of the comment starts at the end of this line. Its words are damaged. Line 73 gives its meaning. |
| 73 | ` * receive the mapping to pass to munmap. */` | Comment: the end of the comment. Its meaning by the code: `raw` and `raw_len` receive the start and the length of the whole mapping. The caller passes both to `munmap` later (line 213). |
| 74 | `static uint8_t *alloc_buf(uint64_t bytes, int use_thp, void **raw, size_t *raw_len)` | Starts the function `alloc_buf`. It reserves a buffer of at least `bytes` bytes and returns its address. The buffer starts at a multiple of 2 MiB. `use_thp` chooses the page size request (line 86). Through `raw` and `raw_len` the function gives back the start and the length of the whole reserved range. |
| 75 | `{` | Opens the body of `alloc_buf`. |
| 76 | `    size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | `len`: `bytes` rounded up to the next multiple of `HUGE_BYTES` (2 MiB). The expression adds `HUGE_BYTES - 1` and then clears the low bits. This gives the right value when `HUGE_BYTES` is a power of two. A size of 4096 bytes gives 2 MiB. |
| 77 | `    *raw_len = len + HUGE_BYTES;` | The length of the range to reserve: `len` plus 2 MiB. The extra 2 MiB make it possible to move the start of the buffer to an aligned address (line 83). |
| 78 | `    *raw = mmap(NULL, *raw_len, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for that many bytes of new memory and stores the start in `*raw`. `NULL`: Linux chooses the address. `PROT_READ \| PROT_WRITE`: the program may read and write the memory. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. `mmap` reserves addresses only. Linux assigns the physical memory when a page is first written (line 113). |
| 79 | `    if (*raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 80 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 81 | `        exit(2);` | On failure: the program ends with exit status 2. |
| 82 | `    }` | Ends the `if` of line 79. |
| 83 | `    uint8_t *p = (uint8_t *)(((uintptr_t)*raw + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the first address in the reserved range that is a multiple of 2 MiB. The buffer starts there. The expression rounds the address `*raw` up in the same way as line 76 rounds the size. |
| 84 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: `MADV_NOHUGEPAGE` matters on a machine where the Linux setting for transparent huge pages (THP) is `always`. Transparent huge pages are memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages. The sentence ends in line 85. |
| 85 | `     * would still get 2 MiB pages. */` | Comment: the end of the sentence: without `MADV_NOHUGEPAGE`, a run with `--no-thp` would still get 2 MiB pages on such a machine. |
| 86 | `    if (madvise(p, len, use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` gives Linux a request for the `len` bytes that start at `p`. When `use_thp` is not 0, the request is `MADV_HUGEPAGE`: use 2 MiB pages for this range. With the option `--no-thp` the request is `MADV_NOHUGEPAGE`: use no 2 MiB pages for this range. A return value other than 0 means that the call failed. |
| 87 | `        perror("madvise (continuing)");` | On failure: `perror` prints a message that starts with `madvise (continuing)`. The program goes on. It never tests here whether the buffer in fact lies on 2 MiB pages. Line 161 prints a value that shows it. |
| 88 | `    return p;` | Returns the aligned address. The function writes nothing into the buffer. The first write happens in `build_cycle` (lines 112 to 113). |
| 89 | `}` | Ends the function `alloc_buf`. |

### Function `anon_huge_kb`: how much memory of the process lies on huge pages (lines 91 to 104)

| Line | Source | Explanation |
|---:|---|---|
| 91 | `static long anon_huge_kb(void)` | Starts the function `anon_huge_kb`. It returns how many kB of the memory of this process lie on transparent huge pages at this moment. It returns -1 when it cannot find the value. |
| 92 | `{` | Opens the body of `anon_huge_kb`. |
| 93 | `    FILE *f = fopen("/proc/self/smaps_rollup", "r");` | Opens the file `/proc/self/smaps_rollup` for reading. Linux provides this file for each process. It holds one line per memory value, each summed over all memory ranges of the process. |
| 94 | `    if (!f)` | Tests whether the file could not be opened. |
| 95 | `        return -1;` | Then the function returns -1. |
| 96 | `    char line[256];` | `line`: room for one text line of at most 255 characters. |
| 97 | `    long kb = -1;` | `kb`: the result. It stays -1 when no line fits. |
| 98 | `    while (fgets(line, sizeof line, f))` | Reads the file line by line. `fgets` returns `NULL` at the end of the file, which ends the loop. |
| 99 | `        if (sscanf(line, "AnonHugePages: %ld kB", &kb) == 1)` | `sscanf` tests whether the line has the form `AnonHugePages:`, then a number, then `kB`. When it has, the number goes to `kb` and `sscanf` returns 1. `AnonHugePages` is the memory without a file behind it that lies on transparent huge pages. |
| 100 | `            break;` | Leaves the loop at the first such line. |
| 101 | `    fclose(f);` | Closes the file. |
| 102 | `    return kb;` | Returns the value in kB, or -1. |
| 103 | `}` | Ends the function `anon_huge_kb`. |

### Function `build_cycle`: the first write and one random cycle of pointers (lines 105 to 124)

| Line | Source | Explanation |
|---:|---|---|
| 105 | `/* First touch, then Sattolo shuffle of line indices, then index -> pointer.` | Comment: the three steps of `build_cycle`. Step 1 is the first touch: the first write to every line. Step 2 is the shuffle of Sattolo over the line numbers. Step 3 turns each line number into a pointer. |
| 106 | ` * slot selects which 8-byte word of each line carries this chain; the stored` | Comment: `slot` selects which 8-byte word of each 64-byte line holds this chain. A chain is one cycle of pointers. A line has room for 8 such words, numbered 0 to 7. The sentence goes on in line 107. |
| 107 | ` * pointer targets the same slot of the next line, so chase() needs no offset. */` | Comment: the stored pointer points to the same word number of the next line of the chain. So `chase` uses a loaded pointer directly as the address of its next load and adds no offset. |
| 108 | `static void build_cycle(uint8_t *buf, uint64_t n, int slot, uint64_t seed)` | Starts the function `build_cycle`. It writes one chain into the buffer. `buf` is the buffer, `n` its number of 64-byte lines, `slot` the word of each line that the chain uses, and `seed` the start value of the random number generator. No part of this function is timed. |
| 109 | `{` | Opens the body of `build_cycle`. |
| 110 | `#define AT(i) (*(uint64_t *)(buf + (i) * LINE_BYTES + (slot) * 8))` | Defines the macro `AT(i)`: the 8-byte word number `slot` of line `i`, used as a 64-bit integer. Its address is `buf` plus `i` times 64 plus `slot` times 8. |
| 111 | `    rng_state = seed;` | Sets the random number generator to `seed`. So the same `seed` and the same `n` always give the same order of the lines. |
| 112 | `    for (uint64_t i = 0; i < n; i++)` | Step 1: a loop over all `n` lines, from the first line to the last. The lines are numbered from 0. |
| 113 | `        AT(i) = i;` | Stores the line number `i` into the word of line `i`. For chain 0 this is the first write to every line, and so to every memory page of the buffer (first touch). Linux assigns the pages at this moment. The thread runs on the build CPU then (line 145), or on the CPU of `--cpu` when no `--build-cpu` was given (line 282). |
| 114 | `    for (uint64_t i = n - 1; i > 0; i--) {` | Step 2, the shuffle of Sattolo: `i` goes from the number of the last line (`n - 1`) down to 1. |
| 115 | `        uint64_t j = xorshift64() % i;` | `j`: a random line number from 0 to `i - 1`. It is the next random number modulo `i`. So `j` is never equal to `i`. This is the difference to the standard Fisher-Yates shuffle. |
| 116 | `        uint64_t tmp = AT(i);` | Keeps the word of line `i` in `tmp`. Lines 116 to 118 swap the words of line `i` and line `j`. |
| 117 | `        AT(i) = AT(j);` | Copies the word of line `j` to line `i`. |
| 118 | `        AT(j) = tmp;` | Stores the kept value into line `j`. The swap is complete. |
| 119 | `    }` | Ends the loop of line 114. The word of each line now holds the number of another line. Read as the rule "after line `i` comes the line whose number stands in line `i`", the words form one single cycle through all `n` lines. |
| 120 | `    for (uint64_t i = 0; i < n; i++)` | Step 3: a loop over all `n` lines. |
| 121 | `        AT(i) = (uint64_t)(uintptr_t)(buf + AT(i) * LINE_BYTES + slot * 8);` | Replaces the line number in the word of line `i` with an address: the address of word number `slot` of the line with that number. So the word of line `i` now points to the same word of the line that follows line `i` in the cycle. |
| 122 | `#undef AT` | Removes the macro `AT`. It is used only inside this function. |
| 123 | `}` | Ends the function `build_cycle`. |

### Function `chase`: the loads that are timed (lines 125 to 139)

| Line | Source | Explanation |
|---:|---|---|
| 125 | `__attribute__((noinline)) static void *chase(void *p, uint64_t loads)` | Starts the function `chase`, the measured loop of the program. It follows the pointers that start at `p` for `loads` loads and returns the last pointer. `noinline` forbids the compiler to merge the function into its caller. |
| 126 | `{` | Opens the body of `chase`. |
| 127 | `    for (uint64_t i = 0; i < loads; i += 8) {` | The loop. One loop pass does 8 loads (lines 128 to 135), and `i` grows by 8. So the loop is unrolled 8 times. Every caller passes a count that is a multiple of 8, which the test of line 146 makes sure. So the function does exactly `loads` loads. |
| 128 | `        p = *(void **)p;` | Load 1 of 8: loads the 8-byte pointer that is stored at the address `p` and makes it the new `p`. The loaded value is the address of the next load. So the next load cannot start before this load has delivered its value. The value is used for nothing else. |
| 129 | `        p = *(void **)p;` | Load 2 of 8: the same statement. It loads from the address that load 1 delivered. |
| 130 | `        p = *(void **)p;` | Load 3 of 8: the same statement. |
| 131 | `        p = *(void **)p;` | Load 4 of 8: the same statement. |
| 132 | `        p = *(void **)p;` | Load 5 of 8: the same statement. |
| 133 | `        p = *(void **)p;` | Load 6 of 8: the same statement. |
| 134 | `        p = *(void **)p;` | Load 7 of 8: the same statement. |
| 135 | `        p = *(void **)p;` | Load 8 of 8: the same statement. One loop pass has loaded one pointer from each of 8 lines. |
| 136 | `    }` | Ends the loop of line 127. Beside the 8 loads, a loop pass only adds 8 to `i` and compares it with `loads`. |
| 137 | `    return p;` | Returns the pointer that the last load delivered. After a whole cycle this is the start pointer again. |
| 138 | `}` | Ends the function `chase`. |

### Function `run_size`: pin, reserve the buffer and build the chains for one size (lines 140 to 162)

| Line | Source | Explanation |
|---:|---|---|
| 140 | `static int build_cpu = -1, chase_cpu = -1; /* --build-cpu: build and first-touch the chain there, then chase on --cpu */` | `build_cpu`: the CPU of the option `--build-cpu`, or -1 without it. `chase_cpu`: the CPU of the option `--cpu` (line 280). The comment explains `--build-cpu`: the thread builds the chain and writes the buffer for the first time on that CPU, and then it chases on the CPU of `--cpu`. |
| 142 | `static void run_size(uint64_t bytes, int reps, double min_s, int min_cycles, int use_thp, int fresh)` | Starts the function `run_size`. It measures one buffer size: it reserves and builds the buffer, times the chase and prints the rows of this size. `bytes`: the buffer size. `reps`: the number of timed repetitions. `min_s`: the minimum time of a repetition in seconds. `min_cycles`: the minimum number of whole cycles per repetition. `use_thp`: the page size request. `fresh`: 0 for the standard mode, or the number of chains per line for the fresh mode. |
| 143 | `{` | Opens the body of `run_size`. |
| 144 | `    if (build_cpu >= 0)` | Tests whether the option `--build-cpu` was given. |
| 145 | `        pin_cpu(build_cpu);` | Then pins the thread to the build CPU. The buffer of this size is reserved, written and built there (lines 153 to 158). |
| 146 | `    if (bytes % (8 * LINE_BYTES) != 0) {` | Tests whether the size is not a multiple of 512 bytes, which is 8 lines of 64 bytes. The loop of `chase` does 8 loads per pass. So the number of lines must be a multiple of 8. |
| 147 | `        fprintf(stderr, "size %lu is not a multiple of 512 bytes\n", (unsigned long)bytes);` | In that case: prints the size and the text `is not a multiple of 512 bytes` to the error output. |
| 148 | `        exit(2);` | In that case: the program ends with exit status 2. |
| 149 | `    }` | Ends the `if` of line 146. |
| 150 | `    uint64_t n = bytes / LINE_BYTES;` | `n`: the number of 64-byte lines of the buffer. A size of 32 KiB gives 512 lines. One cycle has `n` loads. |
| 151 | `    void *raw;` | `raw`: will hold the start of the reserved address range. |
| 152 | `    size_t raw_len;` | `raw_len`: will hold the length of that range. |
| 153 | `    uint8_t *buf = alloc_buf(bytes, use_thp, &raw, &raw_len);` | Reserves the buffer (`alloc_buf`). `buf` is its start, an address that is a multiple of 2 MiB. |
| 154 | `    build_cycle(buf, n, 0, 0x9E3779B97F4A7C15ULL);` | Builds chain 0 in word 0 of each line (`build_cycle`), with a fixed start value for the random numbers. This call also writes the buffer for the first time. The start value is the same in every run. So a given size has the same order of the lines in every run. |
| 155 | `    for (int c = 1; c < fresh; c++)` | Loop over the extra chains of the fresh mode: `c` from 1 to `fresh - 1`. In the standard mode `fresh` is 0, and the loop does nothing. |
| 156 | `        build_cycle(buf, n, c, 0x9E3779B97F4A7C15ULL * (uint64_t)(c + 1) + 12345);` | Builds chain `c` in word `c` of each line, with a start value of its own. So each chain visits the same lines in another random order. |
| 157 | `    if (build_cpu >= 0) {` | Tests again whether `--build-cpu` was given. |
| 158 | `        chase(buf, n); /* the builder walks it once so its chiplet holds every line */` | Then the thread walks chain 0 once on the build CPU: `n` loads, each line once. By the comment, the chiplet of the build CPU then holds every line. A chiplet is one of the parts of the chip. The returned pointer is not used. This walk is not timed. |
| 159 | `        pin_cpu(chase_cpu);` | Then pins the thread to the CPU of `--cpu`. Everything after this line runs there, also the timed chase. |
| 160 | `    }` | Ends the `if` of line 157. |
| 161 | `    printf("# size_bytes=%lu AnonHugePages_kB=%ld build_cpu=%d\n", (unsigned long)bytes, anon_huge_kb(), build_cpu);` | Prints one comment line for this size: the size in bytes, the result of `anon_huge_kb` in kB, and the build CPU (-1 without `--build-cpu`). The kB value is the memory of the whole process that lies on transparent huge pages. It is read after the chains were built, so after the first write. By the file `README.md` of this folder, 0 kB means that Linux gave pages of 4 KiB. |

### Function `run_size`: the fresh mode, one timed pass per chain (lines 163 to 188)

| Line | Source | Explanation |
|---:|---|---|
| 163 | `    double best = 1e30;` | `best`: the smallest time per load of this size so far, in ns. It starts at a value that every measurement is below. |
| 164 | `    uint64_t best_loads = 0;` | `best_loads`: the number of loads of the repetition that gave `best`. |
| 165 | `    void *p = buf;` | `p`: the pointer of the chase. It starts at word 0 of the first line of the buffer. Chain 0 uses this word. |
| 166 | `    if (fresh) {` | Tests whether the fresh mode is on (option `--fresh`). Lines 167 to 188 are the fresh mode. Lines 190 to 209 are the standard mode. |
| 167 | `        /* Fresh mode: chain 0 is walked twice (data resident, prefetcher trained on` | Comment: in the fresh mode chain 0 is walked twice first. The comment names two effects. The data is resident: every line was loaded before. And the prefetcher was trained on chain 0 only. The sentence ends in line 168. |
| 168 | `         * chain 0 only); then each rep is exactly one pass over a chain that has` | Comment: then each repetition is exactly one pass over a chain that was never walked before. |
| 169 | `         * never been walked. A temporal prefetcher that replays a learned miss` | Comment: a temporal prefetcher cannot help in this mode. That is a prefetcher that records the order of earlier cache misses and fetches the same lines in the same order again. |
| 170 | `         * sequence cannot help here. */` | Comment: the end of the comment on the fresh mode. |
| 171 | `        if (build_cpu < 0) { /* with --build-cpu the builder's walk is the only warm-up */` | Tests whether `--build-cpu` was not given. By the comment, with `--build-cpu` the walk of the builder (line 158) is the only warm-up. |
| 172 | `            p = chase(p, n);` | Warm-up walk 1 over chain 0: `n` loads, not timed. |
| 173 | `            p = chase(p, n);` | Warm-up walk 2 over chain 0: `n` loads, not timed. |
| 174 | `        }` | Ends the `if` of line 171. |
| 175 | `        sink = p;` | Stores the pointer into `sink`. So the warm-up walks have a result that is used. |
| 176 | `        for (int c = 1; c < fresh; c++) {` | Loop over the chains 1 to `fresh - 1`. Each chain is timed once. The options `--reps`, `--min-ms` and `--min-cycles` have no effect in the fresh mode. |
| 177 | `            void *q = buf + c * 8;` | `q`: the start of chain `c`: word `c` of the first line of the buffer. |
| 178 | `            double t0 = now_s();` | Reads the clock: `t0`, the start of the timed interval. |
| 179 | `            q = chase(q, n);` | The timed work: one pass over chain `c`. This is `n` loads, one from each line of the buffer. The lines are the same as in chain 0, but the order is new. |
| 180 | `            double t1 = now_s();` | Reads the clock again: `t1`, the end of the timed interval. The interval holds the one call of `chase` and nothing else. |
| 181 | `            sink = q;` | Stores the last pointer into `sink`. This store is outside the timed interval. |
| 182 | `            double ns = (t1 - t0) * 1e9 / (double)n;` | `ns`: the latency in nanoseconds per load. It is the elapsed time `t1 - t0` in seconds, times 1e9, divided by the `n` loads. |
| 183 | `            printf("%lu,fresh%d,%lu,%.3f\n", (unsigned long)bytes, c, (unsigned long)n, ns);` | Prints one data row with four columns: the size in bytes, the text `fresh` with the chain number (for example `fresh1`), the number of loads (`n`), and the nanoseconds per load with 3 decimals. |
| 184 | `            if (ns < best) {` | Tests whether this value is the smallest of the size so far. |
| 185 | `                best = ns;` | Then keeps it as `best`. |
| 186 | `                best_loads = n;` | Then keeps its number of loads. |
| 187 | `            }` | Ends the `if` of line 184. |
| 188 | `        }` | Ends the loop of line 176. |

### Function `run_size`: the standard mode, the `best` row and the release of the buffer (lines 189 to 215)

| Line | Source | Explanation |
|---:|---|---|
| 189 | `    } else {` | Starts the standard mode, which runs without the option `--fresh`. |
| 190 | `        /* Chunk = whole cycles, at least MIN_CHUNK_LOADS loads, so the clock` | Comment: a chunk is a whole number of cycles with at least `MIN_CHUNK_LOADS` loads. The clock is read only between two chunks. So the cost of the clock reads is very small against the cost of the loads. For a small buffer the code of line 192 gives at most that many loads, not at least. |
| 191 | `         * read between chunks is negligible. */` | Comment: the end of the sentence of line 190. |
| 192 | `        uint64_t chunk = n * (n >= MIN_CHUNK_LOADS ? 1 : MIN_CHUNK_LOADS / n);` | `chunk`: the number of loads between two clock reads. For a buffer of 1048576 lines or more (64 MiB or more) it is `n`, one cycle. For a smaller buffer it is `n` times the number of whole cycles that fit into 1048576 loads. The division drops the remainder. So the chunk is 1048576 loads when `n` divides that number. In the other cases it is fewer, but always more than 524288 loads (half of that number). A size of `1.5M` has 24576 lines and gives 42 cycles, which is 1032192 loads. |
| 193 | `        p = chase(p, n); /* warm-up: one full cycle */` | Warm-up: one whole cycle (`n` loads), not timed. It loads every line once before the first timed interval. After a whole cycle `p` points to the first line of the buffer again. |
| 194 | `        for (int rep = 0; rep < reps; rep++) {` | Loop over the repetitions: `reps` timed intervals (option `--reps`, 3 by default). |
| 195 | `            uint64_t loads = 0;` | `loads`: the loads of this interval so far. It starts at 0. |
| 196 | `            double t0 = now_s(), t1;` | Reads the clock: `t0`, the start of the timed interval. `t1` will hold the latest clock value. |
| 197 | `            do {` | Starts a loop that runs at least once. It repeats while the condition of line 201 holds. |
| 198 | `                p = chase(p, chunk);` | The timed work: one chunk of loads. The chase goes on from the pointer where the chunk before ended. No buffer is built and no pointer is reset between two intervals. |
| 199 | `                loads += chunk;` | Adds the chunk to the count of loads. |
| 200 | `                t1 = now_s();` | Reads the clock after the chunk: `t1`. This clock read lies inside the timed interval. |
| 201 | `            } while (t1 - t0 < min_s \|\| loads < (uint64_t)min_cycles * n);` | Repeats while the elapsed time is below `min_s` (option `--min-ms`) or the loads are fewer than `min_cycles` times `n` (option `--min-cycles`). So the interval ends at the first clock read at which both conditions hold: at least `min_s` seconds have passed, and at least `min_cycles` whole cycles were walked. |
| 202 | `            double ns = (t1 - t0) * 1e9 / (double)loads;` | `ns`: the latency in nanoseconds per load. It is the elapsed time `t1 - t0` in seconds, times 1e9, divided by all loads of the interval. The time holds the calls of `chase` and one clock read per chunk. |
| 203 | `            printf("%lu,%d,%lu,%.3f\n", (unsigned long)bytes, rep, (unsigned long)loads, ns);` | Prints one data row with four columns: the size in bytes, the number of the repetition counted from 0, the number of loads, and the nanoseconds per load with 3 decimals. |
| 204 | `            if (ns < best) {` | Tests whether this value is the smallest of the size so far. |
| 205 | `                best = ns;` | Then keeps it as `best`. |
| 206 | `                best_loads = loads;` | Then keeps its number of loads. |
| 207 | `            }` | Ends the `if` of line 204. |
| 208 | `        }` | Ends the loop of line 194. |
| 209 | `        sink = p;` | Stores the last pointer into `sink`. So the result of all loads is used. |
| 210 | `    }` | Ends the `else` of line 189. |
| 211 | `    printf("%lu,best,%lu,%.3f\n", (unsigned long)bytes, (unsigned long)best_loads, best);` | Prints the `best` row of the size: the size in bytes, the word `best`, the loads of the best repetition, and the smallest nanoseconds per load of all repetitions (in the fresh mode: of all timed chains). |
| 212 | `    fflush(stdout);` | `fflush` writes the buffered output now. So the rows of a size are in the output before the next size starts. |
| 213 | `    munmap(raw, raw_len);` | `munmap` gives the whole reserved range back to Linux. The next size gets a new buffer. |
| 214 | `}` | Ends the function `run_size`. |

### Function `usage`: print the usage text and stop (lines 216 to 227)

| Line | Source | Explanation |
|---:|---|---|
| 216 | `static void usage(void)` | Starts the function `usage`. It prints the usage text to the error output and ends the program with exit status 2. |
| 217 | `{` | Opens the body of `usage`. |
| 218 | `    fprintf(stderr,` | Starts the `fprintf` call to the error output. Lines 219 to 224 are one text. |
| 219 | `            "usage: latency [--cpu N] [--build-cpu N] [--min S] [--max S] [--sizes a,b,c] "` | Usage text: the options `--cpu`, `--build-cpu`, `--min`, `--max` and `--sizes`. |
| 220 | `            "[--min-ms MS] [--min-cycles C] [--reps R] [--no-thp] [--fresh K]\n"` | Usage text: the options `--min-ms`, `--min-cycles`, `--reps`, `--no-thp` and `--fresh`. |
| 221 | `            "  sizes accept K/M/G suffixes; --min..--max doubles\n"` | Usage text: a size accepts the suffixes K, M and G. `--min` and `--max` give a range in which the size doubles from step to step. |
| 222 | `            "  --fresh K (2..8): K chains per line; warm up on chain 0, then time one\n"` | Usage text: `--fresh K` with K from 2 to 8 puts K chains into each line. The program warms up on chain 0. The sentence goes on in line 223. |
| 223 | `            "    single pass over each of chains 1..K-1 (defeats temporal prefetchers;\n"` | Usage text: then it times one single pass over each of the chains 1 to K-1. By the text, this defeats temporal prefetchers. |
| 224 | `            "    one pass of a small size is too short to time: use it for >= 256K)\n");` | Usage text: one pass over a small buffer is too short to time. So the text says to use the mode for sizes of 256 KiB and above. The closing parenthesis ends the `fprintf` call. |
| 225 | `    exit(2);` | Ends the program with exit status 2. |
| 226 | `}` | Ends the function `usage`. |

### Function `main`: the defaults and the arguments (lines 228 to 268)

| Line | Source | Explanation |
|---:|---|---|
| 228 | `int main(int argc, char **argv)` | Starts `main`. `argc` and `argv` hold the arguments of the command line. |
| 229 | `{` | Opens the body of `main`. |
| 230 | `    int cpu = -1, reps = 3, min_cycles = 2, use_thp = 1, fresh = 0;` | The defaults. `cpu = -1`: no pinning. `reps = 3`: 3 timed repetitions per size. `min_cycles = 2`: at least 2 whole cycles per repetition. `use_thp = 1`: ask for 2 MiB pages. `fresh = 0`: the standard mode. |
| 231 | `    double min_s = 0.3;` | `min_s`: the minimum time of a repetition, 0.3 s by default. |
| 232 | `    uint64_t min = 0, max = 0, sizes[MAX_SIZES];` | `min`, `max`: the bounds of the options `--min` and `--max`, 0 when not given. `sizes`: the list of the buffer sizes to measure, at most 64. |
| 233 | `    int nsizes = 0;` | `nsizes`: the number of sizes in the list. |
| 235 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments. `argv[0]` is the program name, so the loop starts at 1. |
| 236 | `        const char *a = argv[i];` | `a`: the argument that is handled in this loop pass. |
| 237 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value needs it. |
| 238 | `        if (!strcmp(a, "--no-thp")) {` | Option `--no-thp`. |
| 239 | `            use_thp = 0;` | Then `use_thp` becomes 0. `alloc_buf` then passes `MADV_NOHUGEPAGE` in place of `MADV_HUGEPAGE` (line 86). |
| 240 | `        } else if (!strcmp(a, "--cpu") && more) {` | Option `--cpu N`. |
| 241 | `            cpu = atoi(argv[++i]);` | `cpu`: the CPU on which the chase runs. `atoi` turns the next argument into a number, and `++i` steps over that argument. |
| 242 | `        } else if (!strcmp(a, "--build-cpu") && more) {` | Option `--build-cpu N`. |
| 243 | `            build_cpu = atoi(argv[++i]);` | `build_cpu`: the CPU on which the buffer is built (lines 144 to 145). |
| 244 | `        } else if (!strcmp(a, "--min") && more) {` | Option `--min S`. |
| 245 | `            min = parse_bytes(argv[++i]);` | `min`: the first size of the doubling range (line 271), read by `parse_bytes`. |
| 246 | `        } else if (!strcmp(a, "--max") && more) {` | Option `--max S`. |
| 247 | `            max = parse_bytes(argv[++i]);` | `max`: the upper bound of the doubling range. |
| 248 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Option `--min-ms MS`. |
| 249 | `            min_s = atof(argv[++i]) / 1000.0;` | `min_s`: the value in milliseconds divided by 1000, so in seconds. `--min-ms 300` gives 0.3 s. |
| 250 | `        } else if (!strcmp(a, "--min-cycles") && more) {` | Option `--min-cycles C`. |
| 251 | `            min_cycles = atoi(argv[++i]);` | `min_cycles`: the minimum number of whole cycles per timed repetition. |
| 252 | `        } else if (!strcmp(a, "--reps") && more) {` | Option `--reps R`. |
| 253 | `            reps = atoi(argv[++i]);` | `reps`: the number of timed repetitions per size. |
| 254 | `        } else if (!strcmp(a, "--fresh") && more) {` | Option `--fresh K`. |
| 255 | `            fresh = atoi(argv[++i]);` | `fresh`: the number of chains per line. One of them is the warm-up chain, so K - 1 chains are timed. |
| 256 | `            if (fresh < 2 \|\| fresh > 8)` | Tests whether K is below 2 or above 8. A 64-byte line has room for 8 pointers of 8 bytes. |
| 257 | `                usage();` | Then prints the usage text and ends the program (`usage`). |
| 258 | `        } else if (!strcmp(a, "--sizes") && more) {` | Option `--sizes a,b,c`. |
| 259 | `            char *list = argv[++i];` | `list`: the text of the size list. |
| 260 | `            for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Loop over the pieces of the list. `strtok` cuts the text at each comma and returns one piece per call. After the last piece it returns `NULL`, which ends the loop. |
| 261 | `                if (nsizes == MAX_SIZES)` | Tests whether the list already holds 64 sizes. |
| 262 | `                    usage();` | Then prints the usage text and ends the program. |
| 263 | `                sizes[nsizes++] = parse_bytes(tok);` | Turns the piece into a number of bytes (`parse_bytes`) and appends it to the list. |
| 264 | `            }` | Ends the loop of line 260. |
| 265 | `        } else {` | Every other argument, and also an option whose value is missing. |
| 266 | `            usage();` | Then prints the usage text and ends the program with exit status 2. |
| 267 | `        }` | Ends the chain of tests that began in line 238. |
| 268 | `    }` | Ends the loop of line 235. |

### Function `main`: the size list, the checks, the pinning and the loop over the sizes (lines 269 to 290)

| Line | Source | Explanation |
|---:|---|---|
| 269 | `    if (max == 0)` | Tests whether no `--max` was given. |
| 270 | `        max = min;` | Then `max` becomes `min`. So `--min` alone gives one size. |
| 271 | `    for (uint64_t s = min; s && s <= max; s *= 2) {` | Loop for the doubling range: `s` starts at `min` and doubles until it is above `max`. When `min` is 0 (no `--min`), the loop does not run. These sizes stand in the list after the sizes of `--sizes`. |
| 272 | `        if (nsizes == MAX_SIZES)` | Tests whether the list already holds 64 sizes. |
| 273 | `            usage();` | Then prints the usage text and ends the program. |
| 274 | `        sizes[nsizes++] = s;` | Appends the size `s` to the list. |
| 275 | `    }` | Ends the loop of line 271. |
| 276 | `    if (nsizes == 0 \|\| reps < 1 \|\| min_cycles < 1)` | Tests three error cases: no size at all, fewer than 1 repetition, or fewer than 1 cycle per repetition. |
| 277 | `        usage();` | Then prints the usage text and ends the program. |
| 278 | `    if (build_cpu >= 0 && cpu < 0)` | Tests whether `--build-cpu` was given without `--cpu`. |
| 279 | `        usage();` | Then prints the usage text and ends the program. After the build the thread must move to the CPU of `--cpu` (line 159). |
| 280 | `    chase_cpu = cpu;` | Copies the chase CPU into the global variable `chase_cpu`, for `run_size`. |
| 281 | `    if (cpu >= 0)` | Tests whether `--cpu` was given. |
| 282 | `        pin_cpu(cpu);` | Then pins the thread to that CPU, before any buffer exists. Without `--cpu` the program pins nothing. Linux may then move the thread between the CPUs that the process is allowed to use. |
| 284 | `    printf("# latency pointer chase: ns_per_load = elapsed_ns / loads; cpu=%d thp=%s min_ms=%.0f min_cycles=%d reps=%d fresh=%d\n",` | Prints the first comment line of the output. It gives the formula (`ns_per_load` is the elapsed nanoseconds divided by the loads) and the settings: the CPU, the page size request, the minimum time in ms, the minimum cycles, the repetitions and the value of `--fresh`. |
| 285 | `           cpu, use_thp ? "madvise" : "nohugepage", min_s * 1000.0, min_cycles, reps, fresh);` | Continues the call of line 284: the values. The page size request is printed as `madvise` when the program asked for 2 MiB pages, and as `nohugepage` with `--no-thp`. `min_s * 1000.0` turns the time back into milliseconds. |
| 286 | `    printf("size_bytes,rep,loads,ns_per_load\n");` | Prints the header row of the data: `size_bytes,rep,loads,ns_per_load`. |
| 287 | `    for (int i = 0; i < nsizes; i++)` | Loop over the sizes, in the order of the list. |
| 288 | `        run_size(sizes[i], reps, min_s, min_cycles, use_thp, fresh);` | Measures one size (`run_size`). The sizes run one after the other in the same process. Each size gets a new buffer (line 153, line 213). |
| 289 | `    return 0;` | Returns 0, the exit status for success. |
| 290 | `}` | Ends `main`. |
