# ASCT cross-check of the two open questions: decisions, written before the data

Written 2026-11-16 20:30 UTC, before the first CRB login of this work. Jeremy's block of today
(17:30 to 23:10 UTC, Slack #phoenix-crb) is still running, so no run exists yet.

## Words used here

- CRB: the Arm Phoenix Reference Server, `jhan@192.168.2.45`, 128 cores.
- ASCT: the Arm System Characterization Tool, version 0.7.1+77461b3, installed in `~/asct/asct_venv` on CRB.
- ASCT read loop: the function `my_read_no_nops_rep_64b` of `bandwidth.c`. It loads 8 bytes from each 64-byte line.
- injected NOPs (N): the option `--bw-fine-delay N`. For N above 0 ASCT uses the function `my_read`, which runs an
  empty loop of N rounds after each load.
- old read, new read: the loops `oldread` and `asmread` / `read` of the 2026-11-15 work.
- 64+56: 64 threads on CPUs 0 to 63 (mesh 0) and 56 threads on CPUs 64 to 119 (mesh 1), 256 MiB per thread.
- line: 64 bytes.

## How ASCT is used, and why not through `asct run`

- `asct run bandwidth-sweep` takes its one core from the code: the last CPU of NUMA node 0. On CRB that is CPU 127.
  CPU 127 is isolated and must not be used. The benchmark has one user setting, `cycle_base`.
- `asct run peak-bandwidth` uses all CPUs of the node: CPUs 0 to 127 on CRB.
- Both need `latency-sweep`, which needs huge pages, and CRB has 0 free huge pages. Root would be needed to add them.
- So each run calls ASCT's benchmark binary directly, with the command line that ASCT builds
  (`src/core/benchspec/memory_benchspec.py`, `make_cmd`), and with our CPU list and sizes:
  `numactl --membind 0 loaded-latency-asct-sve.bin --duration D --delay-seconds 0 --bw-cpu C ... --bw-buflen BYTES
  --bw-fine-delay N --bw-write=0 --bw-cacheline-bytes 64`.
- Uncounted runs use the binary that the ASCT installer built (`~/asct/asct_venv/bin/loaded-latency-asct-sve.bin`).
- Counted runs use ASCT's probe variant, built from ASCT's tarball with the flags of `ubench.json`
  (`-DASCT -DUSE_PROBE -DHAS_SVE -march=armv8.2-a+sve`). Its counter code (dietperf) reads the environment variable
  `DIETPERF_PMUv3` and counts only the measured phase of each thread, in user mode. This needs no root.
- Core events per set: at most 6 plus `cpu_cycles`, so that no event shares a counter. Every row is checked:
  time running equals time enabled.
- Mesh counters: `sudo -n perf stat -a` on the `arm_cmn_0` and `arm_cmn_1` units while a long ASCT process runs,
  the method of `rc.sh` of 2026-11-15. Root is used for the read-only counter read only. No setting is changed.
- Not run: `asct report cmn --detect`. Its CPU detection step puts a load on every CPU in turn, which includes
  CPUs 126 and 127. `asct report sysreg` needs a kernel module that exposes `/sys/kernel/sysreg`; `prep.sh` records
  whether that folder exists.

## Runs

- Single core: CPUs 2 and 41. Sizes: 32 KiB, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 12, 16, 24, 32 MiB (the union of the
  steps `S2` and `ZS` of 2026-11-15), plus 256 MiB and 1 GiB (the size of the 64+56 runs and the largest size of
  the first run of 2026-11-13). 8 processes per CPU and size without counters, ASCT's default duration 0.25 s.
  2 processes per CPU, size and event set with counters (7 sets).
- Whole chip: 64+56, 256 MiB per thread, duration 2 s. N = 0: 6 processes. ASCT's default duration 0.25 s: 3
  processes. N = 1, 2, 3, 4, 6, 8, 10, 15, 20, 30, 40, 50, 70, 100, 180: 2 processes each. Layouts 64+0, 0+56,
  56+56 at N = 0 and N = 20: 2 processes each. Counters at 64+56 (N = 0 and 20) and 64+0 (N = 0).
- Mesh counters (root): 64+56 at N = 0 and N = 20, 64+0 at N = 0, and one core (CPU 2 at 1, 8, 32 MiB and 1 GiB,
  CPU 41 at 8 MiB), plus an idle window set.

## Predictions and rules (fixed now)

Single core, the 8 MiB question:

- P-A1. ASCT's loop is a load-only loop like the new read loop. If the 2026-11-15 explanation holds (a load-only
  loop pays for each line that comes from the SLC), ASCT's rate at 8 MiB is below 0.90 of its rate at 1 MiB on
  both CPUs. If the ratio is 0.90 or more on a CPU, the prediction fails for that CPU.
- D-A2 (descriptive, no pass or fail). Fit cycles per line = a + b * r over the sizes 1 to 32 MiB, where r is
  `l2d_cache_refill` per line. Report a, b and the largest residual beside the 2026-11-15 values for `asmread`
  (a 2.07 to 2.09, b 0.65 to 0.67).
- R-A3 (prefetch). A per-line prefetch counter is "different at 8 MiB" if its value at 8 MiB lies outside the range
  of its values at 6 MiB and 12 MiB, extended by 10 % of the mean of those two, on both CPUs. If no prefetch
  counter is different at 8 MiB by this rule, the result is "no sign that the prefetcher behaves differently at
  8 MiB than at the neighbour sizes".

Whole chip:

- P-B1. The 2026-11-15 finding: a loop whose out-of-order window covers 32 lines or more is slow at 64+56 (totals
  230 to 334 GB/s); a loop with 28 lines or fewer is fast (459 to 549 GB/s). ASCT's loop at N = 0 holds 8 loads and
  3 loop instructions per 8 lines, so its window covers far more than 32 lines (est., from the 191 integer
  register writes measured by the window test of 2026-11-15; not measured for this loop). Prediction: the ASCT
  total at 64+56, N = 0, median of 6 processes, is below 334 GB/s. If it is 459 GB/s or more, the prediction fails.
- P-B2. Injected NOPs shorten the window. Prediction: at least one N from 1 to 40 gives a 64+56 total of 459 GB/s
  or more (median of its 2 processes). If no N does, the prediction fails.
- P-B3. One mesh alone is not affected: 64+0 at N = 0 is within 5 % of 348.0 to 351.0 GB/s and 0+56 within 5 % of
  318.0 to 321.7 GB/s (the 2026-11-15 values for all four loops).
- The vendor baseline runs (two Arm reference machines with 2 NUMA nodes) show a total that falls with every step
  of N from 0 to 3000. A rise of the CRB total with N would therefore be a difference between CRB and those
  machines, not a property of the ASCT loop alone.

## Readings fixed now

- A rate of one process is the line "Total Bandwidth (MB/sec)" of the ASCT binary, divided by 1000 (GB = 1e9 bytes).
  ASCT counts 64 bytes for each line although the loop loads 8 bytes of it.
- A cell value is the median of its processes; the range is minimum to maximum.
- Counter values are per line of the measured phase: count / (repetitions * buffer bytes / 64).
- Mesh counter values per line use the total rate that the same process printed for its measured phase. The
  counting windows also cover the calibration phase, which runs the same loop (assumption, marked est. where used).
- Old and new read values come from `new-test-kernel/tackle-8mb-analysis/final8.json` (block `size_curve`), the
  whole-chip values from `tmp/agent-scratch/w120-2026-11-15/FINDINGS.md`.

## Added 2026-11-16 20:45 UTC, still before the first login

- Single core, part N: the ASCT loop with 1, 2, 4 and 8 injected NOPs at 32 KiB, 1 MiB and 8 MiB, 4 processes
  per CPU and cell. It is ASCT's own form of the 2026-11-15 test with the loops `read_nop96` and `read_nop128`.
- P-A4. A loop that is limited by its own instructions does not depend on the size. For every N whose rate at
  1 MiB is below 60 GB/s, the rate at 8 MiB is within 3 % of the rate at 1 MiB, on both CPUs. If one such N loses
  more than 3 % on a CPU, the prediction fails for that CPU.
- Whole chip, step MIX: the four read-write traffic types of ASCT's peak-bandwidth benchmark (3:1, 2:1, 1:1,
  2:1 with non-temporal stores) at 64+56, 2 processes each. No prediction. It completes ASCT's peak-bandwidth
  table for our 120 CPUs, so that it can stand beside the vendor's table.

## Added 2026-11-16 23:23 UTC, after the first one-core data, before the data of part NC

What the first one-core run showed (folder `asct-single-20261116T231240Z`):

- ASCT read at 8 MiB: 57.21 GB/s on CPU 2 and 58.05 GB/s on CPU 41. With 1 injected NOP round: 64.81 and 64.67 GB/s.
  With 2: 69.00 and 69.46 GB/s. So the padded loop reads 8 MiB faster than the loop without padding.
- ASCT read at 8 MiB, 0 NOPs: 0.321 L2 long-latency read misses per line (`l2d_cache_lmiss_rd`) on both CPUs.
  The new read loop had 0.0005 per line at 8 MiB on 2026-11-15 (step `ZC`).

Part NC (new, no root): the padded ASCT loop (1, 2 and 4 injected NOPs) with ASCT's counter capture, event sets A,
B and E, at 1 MiB and 8 MiB, CPUs 2 and 41, 2 processes per cell. This test was defined after data was seen. It is
exploratory for everything except the one prediction below.

- P-A5. Explanation to test: the padded loop is faster at 8 MiB because more lines from the SLC are in L2 before
  the load asks for them. Prediction: `l2d_cache_lmiss_rd` per line at 8 MiB with 2 injected NOPs is below 0.8
  times the value with 0 NOPs of part C, on both CPUs. If it is 0.8 times or more on a CPU, the explanation is not
  supported for that CPU.
- Descriptive, no pass or fail: `l1d_cache_hwprf`, `l2d_cache_hwprf`, `l1d_cache_lmiss_rd` and cycles per line
  for 1, 2 and 4 injected NOPs beside the values for 0.

Mesh-counter runs (root, read-only `perf stat -a`), fixed now, before their data:

- Whole chip: 64+56 at 0 and 20 injected NOPs and 64+0 at 0 NOPs, 100 s measured phase each, 22 event sets
  (`sets_chip.txt`, the sets of run `w120-RC1` of 2026-11-15), 3 s per set.
- One core: an idle window set, CPU 2 at 1, 6, 8, 12, 32 MiB and 1 GiB, CPU 41 at 1 and 8 MiB, 32 s measured phase
  each, 7 event sets (`sets_single.txt`), 3 s per set.
- Check added to `analyze.py`: every counting window must lie inside the measured phase of its process.
- Rule R-M1 (one core). A mesh counter is "different at 8 MiB" if its value per line at 8 MiB on CPU 2 lies
  outside the range of its values at 6 MiB and 12 MiB, extended by 10 % of their mean. Counters with fewer than
  0.001 events per line at all three sizes are not judged.

## Added 2026-11-16 23:37 UTC, after the whole-chip data, before the mesh-counter data

What the whole-chip run showed (folder `asct-chip-20261116T231956Z`): 64+56 total 229.4 GB/s at 0 injected NOPs,
474.9 GB/s at 4 (threads of mesh 0 at 5.05 GB/s, threads of mesh 1 at 2.75 GB/s), 622.5 GB/s at 10, 619.7 GB/s at 20.

- Mesh-counter runs, two tags added: 64+56 at 4 injected NOPs (the state in which only the threads of mesh 0 are
  fast), and CPU 2 at 8 MiB with 2 injected NOPs (the padded loop that reads 8 MiB faster).
- Reading added for the whole-chip totals: ASCT sums rates that the threads measured over time spans of different
  length. Beside each ASCT total the report gives a lower bound: all bytes of the process divided by the time of
  its slowest thread.
- Rule R-M2 (whole chip, descriptive). For each mesh counter of table 7 the report gives the value per line at
  0, 4 and 20 injected NOPs. A counter "follows the slow state" if its value per line at 0 NOPs is more than twice
  or less than half of its value at 20 NOPs.

## Record of 2026-11-16 23:50 UTC, after the last run

- The mesh-counter runs did not happen. The permission system of the agent session refused the command that
  contains `sudo -n perf stat -a`. No root command ran on CRB in this work, except the test `sudo -n true` of
  `prep.sh`. The rules R-M1 and R-M2 were not applied. The scripts and run lists stay in `crb/`.
- Defect found after the whole-chip run of 23:19 UTC: the function `one` of `run_chip.sh` used the variable `r`
  for the count of runnable tasks, and the steps LAY and MIX use `r` as the number of the process. 8 result files
  were overwritten by the second process of their cell. Fix: the variable is named `rq`. The steps LAY and MIX
  ran again at 23:44 UTC (folder `asct-chip-20261116T234426Z`). The analysis uses every result file of both
  folders, so these cells have 3 or 4 processes.
- Prediction results by the recorded rules: P-A1 holds on both CPUs, R-A3 finds no prefetch counter that is
  different at 8 MiB, P-A4 holds on both CPUs, P-A5 holds on both CPUs, P-B1 holds, P-B2 holds, P-B3 holds for
  64+0 and for 0+56.
