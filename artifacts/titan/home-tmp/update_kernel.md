# Rewrite of the C test kernels of bandwidth.c, and the test on CRB

## Short version

The three C kernels of `bench/bandwidth.c` (read, write, copy) now use the same algorithm as the hand-written asm kernels. On CRB with one thread, the best rate of each new C kernel differs from the best rate of the asm kernel of the same binary by -2.91 % to +0.41 % over the 12 cells (3 kernels x 4 buffer sizes). With 120 threads and 256 MiB per thread, the best read rate changed from 466.65 GB/s (old C kernel) to 304.05 GB/s (new C kernel), which is -34.8 %.

Three more points:

- The old versions are kept as comments in the same file.
- With one thread, the best rate of the new C kernel is not below the best rate of the old C kernel in any of the 12 cells.
- Read rates measured after this change cannot be compared with read rates measured before it.

## Words used here

- **CRB**: the Arm Phoenix Reference Server (128 cores, AArch64). All machine tests ran there.
- **Kernel**: one timed loop of the benchmark `bench/bandwidth.c`. It is not the Linux kernel.
- **C kernel**: `k_read`, `k_write` or `k_copy`. The command-line names are `read`, `write`, `copy`.
- **asm kernel**: `k_asmread`, `k_asmwrite` or `k_asmcopy`, written as one inline-assembly block each. The command-line names are `asmread`, `asmwrite`, `asmcopy`. This change does not touch them.
- **Old C kernel / new C kernel**: the C kernel before and after this change.
- **`bw_old` / `bw_new`**: the benchmark built on CRB from the source before the change and from the source after the change.
- **NEON**: the 128-bit vector instruction set of AArch64. One NEON register holds 16 B.
- **SVE**: the scalable vector instruction set of AArch64. gcc used it for the old write and copy kernels.
- **Intrinsic**: a C function from `arm_neon.h` that the compiler turns into one vector operation. `vld1q_u64` loads 16 B, `vst1q_u64` stores 16 B, `vdupq_n_u64` fills a vector with one 64-bit value.
- **`ldp` / `stp`**: AArch64 instructions that load or store a pair of registers. With two NEON registers, one instruction moves 32 B.
- **Barrier**: the empty asm statement `__asm__ volatile("" : : "w"(v0), ..., "w"(v15))`. It names the 16 loaded vectors as inputs in NEON registers. It adds no instruction.
- **Rate**: bytes moved per second, in GB/s (1 GB = 10^9 bytes). The copy kernels count the bytes read plus the bytes written.
- **Repetition**: one timed interval of at least 0.5 s. Each process makes 3 repetitions.
- **Cell**: one combination of kernel and buffer size.
- **Best / median / lowest**: the highest, the middle and the lowest rate of the repetitions of one cell.
- **L1, L2, SLC**: the three cache levels of a core. SLC is the system-level cache (L3), shared by all cores.
- **DRAM**: main memory.
- **Load**: the Linux 1-minute load average, which is the average count of tasks that run or wait to run.
- **Round**: one pass of the run script over all CPUs, sizes, kernels and binaries. The script makes 2 rounds.
- **objdump**: the tool that prints the machine code of a compiled program.
- **taskset**: the Linux tool that limits a process to a list of CPUs.
- **sha256**: a digest that identifies one exact version of a file.
- **THP**: transparent huge pages, the Linux feature that backs memory with 2 MiB pages. The benchmark option `--no-thp` asks for 4 KiB pages.
- **Development machine**: the x86-64 Linux server where the source is edited. It has no AArch64 compiler.
- **`k_cread`**: the load-only read loop of the earlier work: 16 loads of 16 B and the barrier per iteration [Ref12].
- **Self-test**: the program `selftest.c`, which checks what each kernel does to memory.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Jeremy's test account creates it while his measurements run.

## Context

- The user asked for three things. First, portability is not a requirement. Second, `k_read` is to be replaced by the load-only loop `k_cread` of the earlier work, and the same principle is to be applied to the other C kernel functions. Third, the old function is to be kept as a comment in the same file.
- The earlier work measured `k_cread` against `k_asmread` with one thread [Ref12].
- The principle is: a C test kernel does only the memory operations that are measured, in the same order and block size as the asm kernel.
- The directory `cache-perf` is not a git repository. The old source is kept in three places: as comments in the file [Ref1], as the copy `bandwidth.orig.c` [Ref5], and as the file `~/cache-perf/bench/bandwidth.c` on CRB, which is not replaced [Ref2].

## Decisions that I made (not stated by the user)

- The function names `k_read`, `k_write`, `k_copy` and the command-line names `read`, `write`, `copy` are kept. The new body of `k_read` is the body of `k_cread`. Reason: the run scripts in `bench/` pass `--kernel read`, `--kernel all` and similar names [Ref9].
- The asm kernels are kept. After this change each C kernel and its asm kernel have the same kinds and counts of instructions in the loop [Ref2]. With one thread, their best rates agree within 0.5 % in 11 of the 12 cells. Copy at 8 MiB differs by 2.91 %, and the cause is not known.
- `bench/README.md` and `bench/Makefile` are changed where the code change made a sentence false or broke the default build.
- The pointer-chase kernels (`chase` in `latency.c` and in `homelat.c`) are not changed. Their compiled loops hold 8 loads, one add, one compare and one branch [Ref2]. The 8 loads are the measured operation.

## Code changes

All line numbers are for `bench/bandwidth.c` after the change [Ref1].

The file has two versions after the change. The timed runs used the first version (sha256 `c1406e02...4ba2`). After the reviewer's comment R1, I changed 3 comment lines into 6 (the text on the order of loads and stores in `k_copy`), which gives the final version (sha256 `f1985072...7824`). A build of the final version on CRB gave a `bw_new` with the same sha256 as the `bw_new` of the timed runs (`fd7c14df...88a6`), and its self-test passed with 0 failures [Ref13]. So the timed binary is the binary of the final source.

| Place | Change |
|---|---|
| line 10 | `#include <arm_neon.h>` is added. The file builds on AArch64 only from now on. |
| lines 136-166 | The old `k_read`, `k_write`, `k_copy` are inside one comment titled "History". The old comment of `k_read` is quoted there. |
| lines 168-183 | New comment for the C kernels. It states the algorithm, the role of the barrier, and that the machine code must be checked with objdump after a change of compiler or flags. It states the load-before-store order of `k_copy` as an observation with gcc 14.2.0, not as a guarantee. |
| line 184 | New `k_read`: 16 loads of 16 B, then the barrier, per iteration of 256 B. It returns nothing. |
| line 213 | New `k_write`: one `vdupq_n_u64` before the loop, then 16 stores of 16 B per iteration. |
| line 239 | New `k_copy`: 16 loads, the barrier, 16 stores per iteration. |
| lines 381-415 | The old `pass()` is inside a comment titled "History". |
| line 418 | New `pass()`: it has no `sink` parameter, and the `K_READ` case calls `k_read(t->a, n)` without storing a result. |
| `worker()` | The local `volatile uint64_t sink` is removed, and the two `pass()` calls lose the `&sink` argument. `worker()` was not copied into a comment. The history comment of `pass()` records these three lines. |
| line 492 | The usage text now says "all kernels: loads/stores only, bytes must be a multiple of 256; the program builds on AArch64 only". |

The new kernels (the 16 load lines, the 16 store lines and the barrier of `k_copy` are shortened here with "..."; the comment on the barrier line of `k_copy` is not in the file):

```c
__attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)
{
    const uint64_t *p = a;
    const uint64_t *end = a + n;
    do {
        uint64x2_t v0 = vld1q_u64(p + 0);
        ...
        uint64x2_t v15 = vld1q_u64(p + 30);
        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),
                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),
                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),
                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));
        p += 32;
    } while (p < end);
}

__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)
{
    uint64_t *p = a;
    const uint64_t *end = a + n;
    uint64x2_t q = vdupq_n_u64(v);
    do {
        vst1q_u64(p + 0, q);
        ...
        vst1q_u64(p + 30, q);
        p += 32;
    } while (p < end);
}

__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
{
    uint64_t *dp = d;
    const uint64_t *sp = s;
    const uint64_t *end = s + n;
    do {
        uint64x2_t v0 = vld1q_u64(sp + 0);
        ...
        uint64x2_t v15 = vld1q_u64(sp + 30);
        __asm__ volatile("" : : "w"(v0), ... , "w"(v15));   /* same 16 inputs as in k_read */
        vst1q_u64(dp + 0, v0);
        ...
        vst1q_u64(dp + 30, v15);
        sp += 32;
        dp += 32;
    } while (sp < end);
}
```

Other files:

- `bench/README.md`: five passages are changed [Ref3]. They are the kernel list, the `make` sentence, the paragraph on why the asm kernels exist, the sentence on the multiple of 256, and the note on the fixed cost per pass. The old README is kept as `README.orig.md` [Ref5].
- `bench/Makefile`: on a host that is not AArch64, `make` now builds only `latency` [Ref4]. Before my edit, the `else` branch of the Makefile was `all: latency bandwidth`. No copy of the old Makefile was kept, so no file shows this.

Why `k_copy` has the barrier: a compile test of the same copy loop without the barrier gave machine code that alternates loads and stores: 8 `ldp`, 7 `stp` and 2 `stur` (a store of one register) [Ref2, function `copy_plain`]. A third candidate without the barrier and without `restrict` kept the 8 `ldp` ahead of the 8 `stp` [Ref2, function `copy_plain_norestrict`]. I kept `restrict`, which the old `k_copy` and `k_asmcopy` have, and added the barrier. With the barrier, gcc 14.2.0 emitted the 8 `ldp` first and the 8 `stp` after them [Ref2, function `copy_barrier`]. This order is an observation of this build. The barrier has only register inputs, and gcc may move code across such a statement, so the order is not guaranteed. The asm kernel `k_asmcopy` has that second order.

## Machine code of the loops

gcc 14.2.0 on CRB compiled the file with the flags of `bench/Makefile` and printed no warning (the build output is 0 bytes) [Ref2]. The table counts the instructions inside each loop, from the objdump listing [Ref2].

| Kernel | Binary | Instructions in the loop | Bytes per iteration |
|---|---|---|---|
| `k_read` new | `bw_new` | 8 `ldp`, 1 `add`, 1 `cmp`, 1 branch (11) | 256 B |
| `k_asmread` | both | 8 `ldp`, 1 `add`, 1 `cmp`, 1 branch (11) | 256 B |
| `k_read` old | `bw_old` | 4 `ldp`, 8 vector `add`, 2 integer `add`, 1 `cmp`, 1 branch (16) | 128 B |
| `k_write` new | `bw_new` | 8 `stp`, 1 `add`, 1 `cmp`, 1 branch (11) | 256 B |
| `k_asmwrite` | both | 8 `stp`, 1 `add`, 1 `cmp`, 1 branch (11) | 256 B |
| `k_write` old | `bw_old` | 1 `st1d` (SVE), 1 `add`, 1 `whilelo`, 1 branch (4) | one SVE vector (length not recorded) |
| `k_copy` new | `bw_new` | 8 `ldp`, 8 `stp`, 2 `add`, 1 `cmp`, 1 branch (20) | 256 B read, 256 B written |
| `k_asmcopy` | both | 8 `ldp`, 8 `stp`, 2 `add`, 1 `cmp`, 1 branch (20) | 256 B read, 256 B written |
| `k_copy` old | `bw_old` | 1 `ld1d`, 1 `st1d` (SVE), 1 `add`, 1 `whilelo`, 1 branch (5) | one SVE vector (length not recorded) |

Differences that remain between a new C kernel and its asm kernel [Ref2]:

- The registers differ. The new `k_read` and `k_copy` use q16 to q31. The new `k_write` uses q31 only, and `k_asmwrite` uses q0 only. `k_asmread` and `k_asmcopy` use q0 to q15. These two asm kernels save and restore d8 to d15 once per call. The new C kernels do not.
- The position of the `add` instructions differs. In the new `k_write` the `add` is the first instruction of the loop, and the stores use negative offsets. In the new `k_copy` one `add` is placed between the last `ldp` and the first `stp`, and the other `add` is placed after the first `stp`. 7 of the 8 `stp` use negative offsets.
- The branch condition is `b.hi` after `cmp end, p` in the C kernels and `b.lo` after `cmp p, end` in the asm kernels.

gcc does not promise this machine code. It is what gcc 14.2.0 produced with these flags, in three builds [Ref2][Ref11][Ref13]. The comment in the file says that the listing must be checked again after a change of compiler or flags [Ref1].

## Tests

### Review of the code before the machine test

Four independent reviewer agents read the changed code, the self-test, the run script and the files that use the kernels. A second agent tried to refute each finding. The review reported no defect in the new kernel code. It confirmed 10 findings in the self-test, the run script, the usage text and the README. One of the 10 was reported twice, and one was a limit of the test design, which is stated under "Limits". I corrected the other 8 before the machine test. The output of the review is not saved as a file in the project.

### Self-test on CRB

- `selftest.c` includes `bandwidth.c` itself, with `main` renamed [Ref6]. So it tests the functions that the benchmark runs.
- Every test buffer lies between two pages that cannot be read or written. A kernel that touches a byte within one page (4096 B on CRB) before or after the buffer is stopped by the operating system.
- Checks per kernel: read leaves the buffer unchanged; write sets every word to the value; copy makes the destination equal to a source in which every word differs. The whole-buffer tests also check that copy leaves the source unchanged. The 256 B tests do not check that.
- Sizes: whole buffers of 4096 B, 12288 B and 1 MiB, and one iteration of 256 B at the start and at the end of a page. In the 256 B tests, the words of the page outside the 256 B must keep their old value.
- Result: 36 checks, 36 pass, 0 failures, exit status 0, for the six kernels [Ref7].
- What the self-test cannot show: that a read kernel loads every byte, the order of loads and stores in a copy kernel, and that a kernel preserves the registers d8 to d15. The objdump listing is the evidence for the first two [Ref2]. The third is not tested.

### Timed runs on CRB

- The script ran once in `probe` mode first (build, machine code, self-test) [Ref11]. Then it ran in `all` mode.
- Run folder of the `all` run: `crb/results/kernels-20261113T181222Z/` [Ref8]. Start 18:12:22 UTC on 2026-11-13, end 18:18:37 UTC [Ref2].
- Two binaries from one compiler call each: `bw_old` from the source before the change (sha256 `61228754...2fe1b`) and `bw_new` from the first version of the changed source (sha256 `c1406e02...4ba2`) [Ref2].
- One process per binary and kernel, so no kernel is timed after another kernel in the same process. Options: `--reps 3 --min-ms 500` [Ref9].
- One thread: 2 rounds x CPUs 0 and 2 x buffer sizes 32 KiB, 1 MiB, 8 MiB, 1 GiB x 6 kernels x 2 binaries = 192 processes. Each cell of one binary has 12 repetitions [Ref8].
- 120 threads on CPUs 0 to 119: 256 MiB per thread x 6 kernels x 2 binaries x 2 rounds = 24 processes. Each cell of one binary has 6 repetitions [Ref8].
- Round 2 reverses the order of the binaries and the order of the kernels [Ref9].
- Control: the asm kernels have the same source in both binaries. The difference of their rates between `bw_old` and `bw_new` shows how much two equal loops differ in this run.

System load and other users:

- Jeremy announced a block on CRB for 15:30 to 18:10 UTC on 2026-11-13 in the Slack channel #phoenix-crb. I did not log in during the block. I read the channel again at 18:12 UTC and found no later announcement. The Slack messages are not saved as a file.
- Load before the run: 0.03 (1 minute), 0.02 (5 minutes), 0.00 (15 minutes). No user was logged in [Ref2].
- Load at the start of the one-thread processes: 0.10 to 1.00 [Ref8]. Our own one-thread processes are part of this value.
- Load at the start of the 120-thread processes: 1.00 to 85.38 [Ref8]. Each earlier process ran 120 threads, so my hypothesis is that this load comes from our own processes. The process list was recorded only before the run, so no file confirms it.
- The script checked the marker file before the builds, before the self-test and before every timed process [Ref9]. The run was confined to CPUs 0 to 119 with `taskset` and wrote only under `~/cache-perf` [Ref9].

## Results

Result page with charts: `crb/results/kernels-20261113T181222Z/kernels-result.html` [Ref10]. All rates below are in GB/s and come from the two csv files through `summarize.py` [Ref8].

### One thread (12 repetitions per value)

| Kernel | Buffer | Old C best | Old C median | New C best | New C median | asm best (`bw_new`) | New C vs old C, best | New C vs asm, best | asm `bw_new` vs asm `bw_old`, best |
|---|---|---|---|---|---|---|---|---|---|
| read | 32 KiB | 66.76 | 66.69 | 133.22 | 133.13 | 133.15 | +99.6 % | +0.05 % | +0.14 % |
| read | 1 MiB | 67.13 | 67.12 | 85.26 | 85.25 | 85.26 | +27.0 % | +0.00 % | +0.01 % |
| read | 8 MiB | 67.08 | 67.03 | 67.71 | 67.46 | 67.99 | +0.9 % | -0.41 % | -0.32 % |
| read | 1 GiB | 28.72 | 28.70 | 30.89 | 30.70 | 30.95 | +7.6 % | -0.19 % | +0.06 % |
| write | 32 KiB | 44.05 | 34.93 | 89.54 | 89.53 | 89.53 | +103.3 % | +0.01 % | +0.00 % |
| write | 1 MiB | 44.75 | 44.74 | 89.53 | 89.52 | 89.53 | +100.1 % | +0.00 % | +0.00 % |
| write | 8 MiB | 44.77 | 44.76 | 72.84 | 72.27 | 72.54 | +62.7 % | +0.41 % | -0.15 % |
| write | 1 GiB | 44.78 | 44.77 | 63.08 | 63.02 | 63.08 | +40.9 % | +0.00 % | +0.00 % |
| copy | 32 KiB | 88.04 | 79.91 | 179.05 | 179.02 | 178.35 | +103.4 % | +0.39 % | +0.01 % |
| copy | 1 MiB | 89.33 | 88.80 | 139.72 | 139.42 | 139.25 | +56.4 % | +0.34 % | -0.02 % |
| copy | 8 MiB | 50.74 | 50.33 | 57.09 | 56.28 | 58.80 | +12.5 % | -2.91 % | -0.31 % |
| copy | 1 GiB | 42.76 | 41.98 | 42.82 | 42.53 | 43.03 | +0.1 % | -0.49 % | -0.35 % |

What the one-thread data shows:

- New C against asm: the best rates differ by -2.91 % to +0.41 % over the 12 cells. In 11 of the 12 cells the difference is inside -0.5 % to +0.5 %.
- The largest difference is copy at 8 MiB: 57.09 GB/s (new C) against 58.80 GB/s (asm). The control difference in that cell is -0.31 %. The -2.91 % is larger than the control. Against the asm kernel of `bw_old` (58.98 GB/s) the difference is -3.20 %. Insufficient data for the cause. A run with more processes per cell, and a build in which the two `add` instructions of `k_copy` are placed as in `k_asmcopy`, would show whether the placement of instructions is the cause.
- New C against old C: the best rate changes by +0.1 % to +103.4 %. The smallest change is copy at 1 GiB, +0.14 %. The asm control of that cell is -0.35 %. This run does not establish that the +0.14 % is repeatable.
- Control: the asm kernels differ between the two binaries by -0.35 % to +0.14 % (best rates). This is an observation of this run. It is not a threshold that excludes a kernel effect.
- The read values agree with the earlier run of `k_cread`: 133.26, 85.30, 71.15 and 30.93 GB/s there [Ref12], and 133.22, 85.26, 67.71 and 30.89 GB/s here. The 8 MiB value is 4.8 % lower in this run. The asm read kernel is lower by a similar amount (71.07 GB/s there, 67.99 GB/s here), so the 8 MiB difference is between the two runs and not between the kernels.

### 120 threads, 256 MiB per thread (6 repetitions per value, total rate of all threads)

| Kernel | Old C best | Old C median | New C best | New C median | New C lowest | asm best (`bw_new`) | asm median (`bw_new`) | New C vs old C, best | asm `bw_new` vs asm `bw_old`, best |
|---|---|---|---|---|---|---|---|---|---|
| read | 466.65 | 465.48 | 304.05 | 289.54 | 279.66 | 305.90 | 289.01 | -34.8 % | +6.20 % |
| write | 186.88 | 144.62 | 147.78 | 131.92 | 123.52 | 152.01 | 117.50 | -20.9 % | +2.83 % |
| copy | 158.56 | 157.21 | 162.41 | 156.09 | 153.91 | 158.37 | 155.37 | +2.4 % | -0.06 % |

What the 120-thread data shows:

- Read: the new C kernel (304.05 GB/s best, 289.54 GB/s median) is at the asm kernel (305.90 GB/s best, 289.01 GB/s median). Both are below the old C kernel (466.65 GB/s best). The change of -34.8 % is much larger than the control difference of +6.20 %.
- So in this configuration the loop that does extra work (the old read kernel with its vector adds) moves more bytes per second than the loop that only loads. Insufficient data for the cause: no hardware counter was read. Counters for cache refills and prefetches for both read kernels at 120 threads, and a sweep over the thread count, would show where the two loops separate.
- Write: the six repetitions of the old C kernel are 140.91, 144.17, 144.60, 144.64, 145.58 and 186.88 GB/s. The six of the new C kernel are 123.52, 123.80, 123.92, 139.92, 143.63 and 147.78 GB/s. The asm write kernel has 5 of 6 repetitions between 117.26 and 117.77 GB/s in `bw_new`, and one at 152.01 GB/s. With this spread, the run does not give one write rate per kernel. The medians are 144.62 (old C), 131.92 (new C) and 117.50 GB/s (asm, `bw_new`).
- Copy: the best rates of the four copy cells are between 158.37 and 162.41 GB/s. From old C to new C the best rate changes by +2.43 % and the median by -0.71 %. The asm copy control changes by -0.06 % (best). Each binary has only 2 copy processes, so this run does not establish a repeatable copy gain.

## Consequences for existing results

- Every earlier result named `read`, `write` or `copy` was measured with the old C kernels. A new run with the same command line now measures a different loop.
- The one-thread best rates of the C kernels rise by 7.6 % to 103.4 % in 10 of the 12 cells. In copy at 1 GiB the change is +0.14 % and the asm control of that cell is -0.35 %. In read at 8 MiB the change is +0.94 % and the asm control of that cell is -0.32 %. This run does not establish whether these two small changes are repeatable: each cell has 4 processes per binary.
- The 120-thread read rate at 256 MiB falls by 34.8 % (best rates).
- The report `crb/crb-memory-hierarchy.html`, the page `crb/perf-measurement-tech.html` (which quotes the old `k_read` and the old `pass()`), and the earlier result folders are not changed. They describe the old kernels.
- The copy of the benchmark on CRB (`~/cache-perf/bench/bandwidth.c`) still holds the old source (sha256 `61228754...2fe1b`) [Ref2]. I copied the new source to CRB into `~/cache-perf/scratch-kernels-20261113/`, the folder of the run script. No result file records this path.

## Limits

- Each one-thread cell has 4 processes per binary. The 3 repetitions of one process use the same buffer, so they are not independent samples.
- Each 120-thread cell has 2 processes per binary, at one buffer size (256 MiB) and one thread count.
- No hardware counter was read. The runs do not show why a rate is what it is.
- The page size that each process received was not recorded. Transparent huge pages were set to "always" on the host [Ref2].
- The self-test does not test that the registers d8 to d15 survive a kernel call.
- The machine code is the choice of gcc 14.2.0 with the current flags. Another compiler version can produce different code from the same source.
- The colors of the charts are three slots of the dataviz skill's palette. Its validator script was not run, because `node` is not installed on the development machine.

## Not done

- `bandwidth.c` on CRB under `~/cache-perf/bench/` is not replaced with the new source.
- The reports and the result pages that describe the old kernels are not updated.
- The x86-64 binary `bench/bandwidth` on the development machine is an old build. It can no longer be rebuilt there, and I did not delete it.
- The cause of the 120-thread read difference and of the 8 MiB copy difference is not examined.
- The report `crb/crb-memory-hierarchy.html` gives two explanations (hypotheses A and B) for the rate of the old `k_read`. The test that separates them is a loop with 3 loads per 2 vector adds [Ref12]. That loop is still not run.
- No run at other thread counts or with `--no-thp`.

## How to run it again

1. Read the Slack channel #phoenix-crb. Do not log in to CRB during an announced block.
2. Copy the five files `bandwidth.c`, `bandwidth.orig.c`, `selftest.c`, `probe.c`, `run_kernels.sh` from `crb/tmp/agent-scratch/kernels-2026-11-13/` into one folder under `~/cache-perf/` on CRB [Ref5].
3. Run `./run_kernels.sh probe` for the build, the machine code and the self-test (1 s between the first and the last time stamp on 2026-11-13) [Ref11]. Run `./run_kernels.sh all` to do the same steps and then the timed runs (6 min 15 s in total on 2026-11-13) [Ref2].
4. Copy the result folder to `crb/results/`, add `summarize.py` and `make_html.py` from the folder of this run, and run `python3 make_html.py` there [Ref8][Ref10]. `make_html.py` is the generator of this recorded run. It computes the charts, the tables and the list "What the data shows". Its Short version, the sentences under the charts, the "Conditions" and the counts of processes and repetitions are typed text for this run. Check and rewrite them before a page of a new run is used.

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c`, sha256 `f198507208e0b010739660dbea178096e030c97cbf88e479d8cc3f1f11967824`. The changed source, final version.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`. Host, load, logins, compiler, flags, sha256 digests, objdump listings of the six kernels of both binaries, of the three copy candidates of `probe.c`, and of `chase` in `latency` and `homelat`; self-test exit status; start and end time. `build.txt` in the same folder is the compiler output (0 bytes).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/bench/README.md`, sha256 `c2271eb3...d942`.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/bench/Makefile`, sha256 `646394d6...4566`.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/`. `bandwidth.orig.c` (source before the change, sha256 `61228754162c504e37faab3da7f423630ab66e32064ba5911455999347c2fe1b`), `bandwidth.c` (copy of Ref1), `README.orig.md`, `selftest.c`, `probe.c`, `run_kernels.sh`.
- [Ref6] `selftest.c` in the folder of Ref5, sha256 `90456a56...4c28`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/selftest.txt`. Output of the self-test on CRB.
- [Ref8] `one-thread.csv` (192 processes), `threads120.csv` (24 processes) and `summarize.py` in `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/`. Each process has a header line with binary, kernel, CPU list, size, round, load and time.
- [Ref9] `run_kernels.sh` in the folder of Ref5, sha256 `6a91bbbe...1842`. The same digest is in Ref2. The run scripts that use the kernel names are `bench/run_crb.sh`, `bench/run_followup.sh`, `bench/run_followup3.sh`, `bench/run_sudo.sh`, `bench/run_uncore.sh`.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/kernels-result.html` and its generator `make_html.py` in the same folder.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181210Z/`. The first call of the script in `probe` mode (build, listing, self-test). Its listings are identical to those of Ref2.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/`. Build, machine code and self-test of the final source on CRB at 18:32:18 UTC (`probe` mode, no timed run). Load 0.00 (1 minute) at the start. The listings of all kernels are identical to those of Ref2, and the sha256 of `bw_new` is the same.
- [Ref12] `/home/jhan/tmp/k_cread.md` and `/home/jhan/workspace/titan/cache-perf/crb/results/cread-20261113T060510Z/`. The earlier handoff and run for `k_cread`.
