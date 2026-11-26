# Handoff: k_cread, a read loop in C that only loads

Written 2026-11-12 (PST) by Jibin Han's Claude. The test ran on 2026-11-13 from 06:05:10 to 06:06:25 UTC.

## Short version

`k_cread` is a read loop written in C that only loads, like the read loop written by hand in assembly (`k_asmread`). In the one binary that was measured, gcc 14.2 compiles one run of its loop body to 11 instructions of the same kinds and counts as `k_asmread`: 8 load-pair instructions, one add, one compare and one branch. In one test with one thread on CRB (the Arm Phoenix Reference Server), the best rates of the two loops differ by at most 0.6 % at each of four buffer sizes from 32 KiB to 1 GiB.

## Words used here

- **CRB**: the Arm Phoenix Reference Server at 192.168.2.45 (hostname `ubuntu`, 128 cores, aarch64). All runs were made there.
- **bandwidth**: the benchmark program `bench/bandwidth.c`. Each thread runs one loop over its own buffer again and again, and the program prints GB/s.
- **kernel**: the name `bandwidth` uses for one such loop. It is chosen with `--kernel`.
- **k_read**: the read loop in C that the report measured. It adds every 8 B word of the buffer into one of 16 sums. Its kernel name is `read`.
- **k_asmread**: the read loop written by hand in assembly. Its kernel name is `asmread`.
- **k_cread**: the new read loop in C. Its kernel name is `cread`.
- **`ldp q`**: the AArch64 instruction "load pair". With q registers (vector registers of 16 B) it loads 2 values of 16 B.
- **`stp`**: the AArch64 instruction "store pair".
- **d8 to d15**: the low 8 B of the vector registers q8 to q15. A function must keep them unchanged for its caller (AArch64 calling convention, stated from memory).
- **`objdump`**: the GNU tool that prints the instructions of a binary.
- **pass**: one run of the loop body. A pass of `k_asmread` or `k_cread` reads 256 B. A pass of `k_read` reads 128 B.
- **repetition**: one timed interval of at least 0.5 s in which one loop runs over the buffer again and again.
- **best**: the highest rate over the repetitions named.
- **GB**: 10^9 bytes. **KiB, MiB, GiB**: 2^10, 2^20, 2^30 bytes.
- **the report**: `crb/crb-memory-hierarchy.html`.
- **hypothesis A, hypothesis B**: the two explanations that the report gives for the rate of `k_read` [Ref7]. Hypothesis A: loads and adds that write vector registers share a limit of 3 per cycle. Hypothesis B: the adds reach only 1.5 per cycle for a reason that is not known, and the loads follow the adds.
- **block**: a reserved time window in which Jeremy Conner has the whole host CRB for his measurements [Ref10].
- **RUNNING file**: `/tmp/positron-perf.RUNNING` on CRB. It exists for the whole of a block [Ref10].
- **load**: the 1-minute load average of Linux, which is the mean number of threads that run or wait to run over the last minute. CRB has 128 cores, so a load below 1 means that at most one core was busy on average.
- **positron-perf**: Jeremy's test account on CRB.

All paths below are relative to `/home/jhan/workspace/titan/cache-perf/` on the dev machine, unless they start with `~`.

## Context

- **The question.** The report shows the source of `k_read`, the source of `k_asmread`, and the machine code of `k_read` [Ref7]. Jibin asked why `k_read` has a second loop, and asked for C code with the algorithm of the asm loop.
- **What the sums of `k_read` do.** `k_read` uses every word that it loads. It adds each word into one of 16 sums. The loop after the main loop adds the 16 sums into the return value. The caller stores the return value to a `volatile` variable [Ref6]. The comment above `k_read` gives the reason for 16 sums and not one: 16 separate sums keep the adds from limiting the loop [Ref6].
- **A loop that does not use the values loses its loads.** gcc 14.2 deleted every load of one test loop that does not use the loaded values (`k_cread_plain`) [Ref5]. Hypothesis: the sums of `k_read` were written to prevent this. No file states the reason.
- **The two rates in the report.** The compiled loop of `k_read` runs 4 `ldp q` and 8 vector adds per 128 B [Ref2]. The report gives 66.8 GB/s for `k_read` and 132.7 GB/s for `k_asmread`. Both were measured on 2026-10-30 with an earlier build, and the report gives the 66.8 GB/s as 1.5 loads of 16 B per cycle [Ref7]. The report says that the limit of two vector adds per cycle can explain at most part of this gap, and that the cause of the rest is not established [Ref7].
- **Portability is not required.** Jibin stated this on 2026-11-12. So `k_cread` may use Arm intrinsics and a GNU asm statement.

## What k_cread is

```c
#include <arm_neon.h>   /* vld1q_u64: one load of 16 B into a vector register */

/* Same contract as k_asmread: n * 8 is a non-zero multiple of 256. */
__attribute__((noinline)) static void k_cread(const uint64_t *a, size_t n)
{
    const uint64_t *p = a;
    const uint64_t *end = a + n;
    do {
        uint64x2_t v0 = vld1q_u64(p + 0);
        uint64x2_t v1 = vld1q_u64(p + 2);
        uint64x2_t v2 = vld1q_u64(p + 4);
        uint64x2_t v3 = vld1q_u64(p + 6);
        uint64x2_t v4 = vld1q_u64(p + 8);
        uint64x2_t v5 = vld1q_u64(p + 10);
        uint64x2_t v6 = vld1q_u64(p + 12);
        uint64x2_t v7 = vld1q_u64(p + 14);
        uint64x2_t v8 = vld1q_u64(p + 16);
        uint64x2_t v9 = vld1q_u64(p + 18);
        uint64x2_t v10 = vld1q_u64(p + 20);
        uint64x2_t v11 = vld1q_u64(p + 22);
        uint64x2_t v12 = vld1q_u64(p + 24);
        uint64x2_t v13 = vld1q_u64(p + 26);
        uint64x2_t v14 = vld1q_u64(p + 28);
        uint64x2_t v15 = vld1q_u64(p + 30);
        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),
                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),
                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),
                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));
        p += 32;
    } while (p < end);
}
```

How it works:

- Each `vld1q_u64` call reads 16 B (two `uint64_t`).
- The asm statement has an empty instruction string. It emits no instruction.
- The asm statement names the 16 values as inputs with the constraint `"w"` (a vector register).
- Observation: in the two compiles that were checked, gcc 14.2 loads 256 B on every pass [Ref2][Ref5].
- Reasoning, not checked against the gcc manual in this work and not checked with another compiler: an input of an asm statement must hold its value when the statement is reached. The 16 addresses differ, and they change on every pass. So the compiler has to load all 16 values on every pass.

What the source does not fix:

- The source does not fix which instructions do the loading. gcc 14.2 pairs the 16 loads into 8 `ldp q`. Another compiler version or another flag set may choose other instructions.
- So each new build needs one check of the machine code with `objdump`. For the hand-written loop the source itself gives the instructions of the loop body.

## Machine code in the measured binary

The loop of `k_cread` [Ref2]:

```
1e20:  add   x1, x0, x1, lsl #3
1e24:  ldp   q31, q30, [x0]
1e28:  ldp   q29, q28, [x0, #32]
1e2c:  ldp   q27, q26, [x0, #64]
1e30:  ldp   q25, q24, [x0, #96]
1e34:  ldp   q23, q22, [x0, #128]
1e38:  ldp   q21, q20, [x0, #160]
1e3c:  ldp   q19, q18, [x0, #192]
1e40:  ldp   q17, q16, [x0, #224]
1e44:  add   x0, x0, #0x100
1e48:  cmp   x1, x0
1e4c:  b.hi  1e24
1e50:  ret
```

Compared with `k_asmread` in the same binary [Ref2]:

| | `k_asmread` | `k_cread` |
|---|---|---|
| Loop body | 8 `ldp q`, one add, one compare, one branch (11 instructions, 256 B) | the same kinds and counts |
| Registers | q0 to q15 | q16 to q31 |
| Compare and branch | `cmp x0, x1` and `b.cc` | `cmp x1, x0` and `b.hi` (the same condition) |
| Outside the loop | one add that computes the end address, and one `ret`. Also 4 `stp` before and 4 `ldp` after, which save and restore d8 to d15 | one add that computes the end address, and one `ret`. No save and no restore |
| Address of the first loop instruction | 0x1d1c | 0x1e24 |

## The test

**What was built.**

- The source is `bandwidth_cread.c`, a copy of `bench/bandwidth.c` with `k_cread` and two kernel names added [Ref3].
- The kernel name `cread` runs `k_cread`. The kernel name `readcmp` runs `read`, `asmread` and `cread` in one process, in this order.
- `k_cread` was not added to `bench/bandwidth.c`. The copy on CRB had the sha256 `61228754...2fe1b` at the start of the run [Ref2]. The copy on CRB had the same sha256 on 2026-11-11 [Ref11]. The copy on the dev machine has the same sha256 (computed with `sha256sum` on 2026-11-13, output not in a file).
- Compiler: gcc 14.2.0. Flags: `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11` [Ref2]. These are the flags of `bench/Makefile` (line 9).

**What was run.** The script `run_cread.sh` started 16 processes [Ref4]:

- 2 rounds, and in each round CPU 0 and then CPU 2, and for each CPU the buffer sizes 32 KiB, 1 MiB, 8 MiB and 1 GiB.
- Each process: `bandwidth_cread --threads 1 --cpus <cpu> --bytes <size> --kernel readcmp --reps 3 --min-ms 500`.
- So each loop has 12 repetitions for each buffer size (2 CPUs x 2 rounds x 3 repetitions).

**State of the host.**

- No RUNNING file existed, and the script checks for it before every process [Ref4].
- The account positron-perf had 0 processes at 06:04 UTC, and nobody was logged in. This was a check by hand in the login before the run, and its output is not in a file.
- The load was 0.06 before the first process [Ref1][Ref2]. It was 0.71 before the last process [Ref1]. The script itself ran one busy thread during that time. No file shows what else ran.

## Results

One thread. Rates in GB/s over the 12 repetitions of each row [Ref1].

| Buffer | Loop | Best | Median | Lowest | Loads of 16 B per cycle (best, at 2.8 GHz) |
|---|---|---|---|---|---|
| 32 KiB | `k_asmread` | 133.21 | 133.14 | 133.07 | 2.97 |
| 32 KiB | `k_cread` | 133.26 | 133.18 | 131.84 | 2.97 |
| 32 KiB | `k_read` | 66.76 | 66.69 | 66.63 | 1.49 |
| 1 MiB | `k_asmread` | 85.26 | 85.25 | 85.24 | 1.90 |
| 1 MiB | `k_cread` | 85.30 | 85.27 | 85.25 | 1.90 |
| 1 MiB | `k_read` | 67.13 | 67.12 | 67.11 | 1.50 |
| 8 MiB | `k_asmread` | 71.07 | 70.94 | 67.88 | 1.59 |
| 8 MiB | `k_cread` | 71.15 | 71.00 | 67.85 | 1.59 |
| 8 MiB | `k_read` | 67.12 | 67.08 | 67.07 | 1.50 |
| 1 GiB | `k_asmread` | 30.74 | 30.69 | 30.67 | 0.69 |
| 1 GiB | `k_cread` | 30.93 | 30.79 | 30.76 | 0.69 |
| 1 GiB | `k_read` | 28.73 | 28.70 | 28.64 | 0.64 |

The last column is the best rate divided by 2.8 GHz and by 16 B. The 2.8 GHz is the core clock that `bench/README.md` uses [Ref8]. This test did not measure the clock.

Ratio of `k_cread` to `k_asmread` [Ref1]:

| Buffer | Ratio of the best rates | Ratio of the medians |
|---|---|---|
| 32 KiB | 1.0004 | 1.0003 |
| 1 MiB | 1.0005 | 1.0002 |
| 8 MiB | 1.0011 | 1.0008 |
| 1 GiB | 1.0062 | 1.0034 |

What the data shows:

- **The two loops that only load agree.** The best rates differ by at most 0.6 %, and the medians by at most 0.3 % [Ref1].
- **At 32 KiB both reach 2.97 loads of 16 B per cycle, counted at 2.8 GHz.** `k_read` reaches 1.49 [Ref1].
- **`k_read` stays at about 67 GB/s at 32 KiB, 1 MiB and 8 MiB** [Ref1].
- **At 1 GiB the best rate of `k_read` (28.73 GB/s) is 7.1 % below the best rate of `k_cread` (30.93 GB/s) and 6.5 % below that of `k_asmread` (30.74 GB/s)** [Ref1].
- **At 32 KiB this test gives rates close to those of the report.** The report gives 132.7 GB/s for `k_asmread` and 66.8 GB/s for `k_read`, measured on 2026-10-30 with an earlier build [Ref7]. In this test the best of the 12 repetitions at 32 KiB was 133.21 GB/s and 66.76 GB/s, with a binary built on 2026-11-13 [Ref1][Ref2].

A chart and the same table are in `cread-result.html` [Ref9].

## Limits of the test

- **Order.** Every process ran `k_read`, then `k_asmread`, then `k_cread`. At 1 GiB the best rate of `k_cread` was 0.3 % to 0.8 % above the best rate of `k_asmread` in each of the four processes [Ref1]. An effect of the order is not excluded. A run with the order reversed would resolve it.
- **Low repetitions.** The cause of these was not examined [Ref1].
  - At 32 KiB the three repetitions of `k_cread` in the first process (CPU 0, round 1) gave 131.84 to 131.95 GB/s. The other nine gave 133.05 to 133.26 GB/s.
  - At 8 MiB on CPU 2 in round 1, the six repetitions of `k_asmread` and `k_cread` gave 67.85 to 68.31 GB/s. In the other three processes at 8 MiB these two loops gave 69.75 to 71.15 GB/s.
  - At 8 MiB the first repetition of `k_asmread` was low in two more processes (70.01 and 69.75 GB/s).
- **One thread, two CPUs.** Only CPU 0 and CPU 2 ran, one at a time. No run with several threads was made.
- **One build.** The result holds for this binary [Ref2]. The source does not fix the instructions (see "What the source does not fix").
- **Hypotheses A and B stay open.** `k_cread` has no vector adds. Its only add is the integer add that advances the pointer [Ref2]. The test that the report names for A and B is a loop with loads and adds in a 3:2 ratio [Ref7]. That loop was not run.
- **No counters.** The test read no performance counters.

## Not done

- `k_cread` is not in `bench/bandwidth.c`. It exists only in the scratch copy [Ref3].
- The report was not changed.
- `bench/README.md` and the comment above `k_read` were not changed.
- No statement about gcc, the Arm intrinsics or the calling convention was checked against a manual in this work.
- The colors of the chart were not checked with the validator script of the dataviz skill. That script needs `node`, and `node` is not installed on the dev machine.

## How to run it again

1. Check that no block of Jeremy is announced in Slack #phoenix-crb. Announced blocks lie on weekdays between 13:00 and 21:00 UTC [Ref10]. Do not log in to CRB during a block.
2. Run `ssh jhan@192.168.2.45 cache-perf/scratch-cread-20261113/run_cread.sh`. The script stops with exit code 3 if the RUNNING file exists. It builds the binary, writes a new folder `~/cache-perf/results/cread-<UTC time>/` on CRB, and prints the path. It takes about 75 s.
3. Copy the folder to `crb/results/` on the dev machine. Copy `make_html.py` into it and run it there to build the page. The script computes only the chart, the two tables and the two load numbers from the new `cread.csv`. Every other sentence of the page is fixed text about the run of 2026-11-13, so that text must be checked and edited by hand for a new run.

What the script does on CRB [Ref4]:

- It pins itself to CPUs 0 to 119. So it never runs on CPUs 126 and 127, which Ref10 reserves (section D).
- It stops if the RUNNING file exists (section B of Ref10).
- It uses no `sudo`, and its own output goes only under `~/cache-perf`. These two are choices of the script, not rules of Ref10.
- It does not check for an announced block. That check is step 1.

## References

- [Ref1] `crb/results/cread-20261113T060510Z/cread.csv` (every repetition, and the load before each process).
- [Ref2] `crb/results/cread-20261113T060510Z/probe.txt` (load, compiler, flags, sha256 of the source and the binary, sha256 of `bench/bandwidth.c` on CRB, `objdump` of `k_cread`, `k_asmread` and `k_read` in the measured binary).
- [Ref3] `crb/tmp/agent-scratch/cread-2026-11-12/bandwidth_cread.c` (sha256 `40bbf73d...4cc6`). The same file is on CRB at `~/cache-perf/scratch-cread-20261113/bandwidth_cread.c`.
- [Ref4] `crb/tmp/agent-scratch/cread-2026-11-12/run_cread.sh`. A copy was placed on CRB in `~/cache-perf/scratch-cread-20261113/`. No checksum of that copy was recorded.
- [Ref5] `crb/tmp/agent-scratch/cread-2026-11-12/cread.c` (function `k_cread_plain`) and `probe-cread.txt` in the same folder (its machine code; compile check of 2026-11-13 05:35 UTC, no run).
- [Ref6] `bench/bandwidth.c`, lines 135 to 148 (`k_read`), 173 to 195 (`k_asmread`), 260 to 264 and 292 (the `volatile` variable).
- [Ref7] `crb/crb-memory-hierarchy.html`, section "The read loop compiled from C: 1.5 loads per cycle".
- [Ref8] `bench/README.md`, lines 48 and 59.
- [Ref9] `crb/results/cread-20261113T060510Z/cread-result.html`, built by `make_html.py` in the same folder.
- [Ref10] `crb/jeremy-plan-constraints-2026-10-30.md`, sections B and D.
- [Ref11] `crb/results/probe-20261111T210017Z.txt` (sha256 of `bench/bandwidth.c` on CRB on 2026-11-11).
