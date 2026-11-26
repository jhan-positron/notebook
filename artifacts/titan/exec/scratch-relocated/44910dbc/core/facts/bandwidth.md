# Fact sheet: bandwidth (one-core bandwidth, CPU 2)

All numbers are computed by `scripts/bw_main.py` and `scripts/bw_extra.py` from the raw CSV files. Machine-readable copy: `facts/bandwidth.json`.
Tags: **[M]** measured fact, **[D]** documented fact with source, **[H]** hypothesis with the test that would settle it, **[I]** Insufficient data.

## Short version

- On boot F1 one core reads 56.1 GB/s from a 16 KiB buffer (inside the L1) and 27.3 to 24.6 GB/s from every larger buffer, 48 KiB to 32 MiB. It writes 30.6 to 32.0 GB/s at every footprint.
- The write rate equals the documented store throughput of the core (16 bytes per cycle, 32 GB/s at 2.0 GHz). The L1 read rate is 88 % of the documented load throughput (32 bytes per cycle, 64 GB/s) in the looped form and up to 95 % in the single-call form (boot E).
- Past the L1 the read stream depends on the prefetchers: with prefetchers off (boot B) the 32 MiB read is 2.38 GB/s, and a software prefetch hint then raises it 2.7 times. With prefetchers on (boot E) the same hint lowers it by 17 %.

## 0. Conventions and checks

- **Best row rule [M]**: each kernel and footprint runs 3 reps (5 reps in the L1 forms). `bandwidth.c` prints one `best` row per kernel, the largest `aggregate_GBps` of the reps. The script recomputes the maximum and asserts it equals the `best` row in every block (all blocks pass).
- **GB = 1e9 bytes** (header line 1 of every file). 1 GB/s = 1 byte per ns.
- **Clock [M]**: 2.0 cycles per ns. `scripts/bw_clock.py`: cycles over time in the counter rows has a median of 2.0004 (boot F1 `latency-dram-large.csv`, 22 rows, range 2.0000 to 2.0041) and 2.0006 (boot E `bandwidth-read-prefetch.csv`, 30 rows, range 1.9987 to 2.0032). The operator's README of boot R3 (`membench-jibin-004/README.md` line 33) states "core 2.000 GHz against the 1 GHz generic timer" [D].
- **Bytes per cycle** = best GB/s / 2.0. **Effective cycles per 64 bytes transferred** = 128 / best GB/s. Both are loop throughput. They are not the time of one load or one store.
- **Copy counts both directions**: the `copy` kernel counts 2 x the buffer size per pass (bytes read plus bytes written, `bandwidth.c` line 341). A copy row of 31.4 GB/s copies 15.7 GB of data per second. Copy uses two buffers, so its footprint is twice the listed size.
- **Timer step**: the generic timer runs at 1 GHz (`cntfrq_hz=1000000000` in every header), one tick = 1 ns. A rep lasts 75,000 ns or more, so one tick is under 0.002 % of a rep.
- **ns per pass** = bytes counted per pass / best GB/s. The `elapsed_s` column has only 1 us resolution, so the script uses the GB/s column (3 decimals).
- **The kernels [M, source]**: `read` = 8 x `ldp q,q` per 256 bytes, `write` = 8 x `stp q,q` per 256 bytes, `copy` = 8 `ldp` + 8 `stp` per 256 bytes copied (`bandwidth.c` lines 132 to 250). `--kernel all` runs read, write and copy only. Boot F1 has no `ldr16` or `str16` row on DRAM.
- **Failures [M]**: boot F1 `log.txt` line 80 reads `run_asimov.sh done ...: 0 measurement command(s) failed`. `perf_cov` is 1.0000 in every counter row used here.

## 1. Boot F1, `bandwidth-dram-1core.csv`: every kernel and footprint [M]

Conditions: boot F1, L3 on, prefetchers on, CPU 2, 2 MiB huge pages (`# backing=hugetlb`), no counters in this file.

| kernel | footprint | passes | best GB/s | file line (best rep) | reps GB/s | spread of reps % | bytes per cycle | eff. cycles per 64 B | ns per 64 B | ns per pass |
|---|---|---|---|---|---|---|---|---|---|---|
| read | 16 KiB | 256 | 56.085 | 6 | 55.715, 55.853, 56.085 | 0.66 | 28.043 | 2.282 | 1.141 | 292.13 |
| read | 48 KiB | 128 | 27.299 | 19 | 27.299, 26.808, 26.958 | 1.80 | 13.649 | 4.689 | 2.344 | 1800.51 |
| read | 96 KiB | 64 | 26.877 | 35 | 26.715, 26.877, 26.674 | 0.76 | 13.438 | 4.762 | 2.381 | 3657.55 |
| read | 256 KiB | 32 | 26.297 | 51 | 26.122, 26.150, 26.297 | 0.67 | 13.149 | 4.867 | 2.434 | 9968.59 |
| read | 2 MiB | 4 | 25.044 | 66 | 24.957, 24.948, 25.044 | 0.38 | 12.522 | 5.111 | 2.556 | 83738.70 |
| read | 32 MiB | 2 | 24.575 | 79 | 24.575, 24.532, 24.494 | 0.33 | 12.287 | 5.209 | 2.604 | 1365388.89 |
| write | 16 KiB | 256 | 30.608 | 9 | 30.603, 30.608, 30.608 | 0.02 | 15.304 | 4.182 | 2.091 | 535.28 |
| write | 48 KiB | 128 | 31.437 | 25 | 31.430, 31.436, 31.437 | 0.02 | 15.719 | 4.072 | 2.036 | 1563.51 |
| write | 96 KiB | 64 | 31.711 | 40 | 31.705, 31.709, 31.711 | 0.02 | 15.855 | 4.036 | 2.018 | 3100.00 |
| write | 256 KiB | 32 | 31.887 | 55 | 31.882, 31.886, 31.887 | 0.02 | 15.944 | 4.014 | 2.007 | 8221.03 |
| write | 2 MiB | 4 | 31.981 | 70 | 31.968, 31.980, 31.981 | 0.04 | 15.991 | 4.002 | 2.001 | 65574.94 |
| write | 32 MiB | 2 | 31.997 | 84 | 31.994, 31.997, 31.997 | 0.01 | 15.998 | 4.000 | 2.000 | 1048674.31 |
| copy | 16 KiB | 256 | 39.433 | 12 | 39.433, 39.231, 39.355 | 0.51 | 19.716 | 3.246 | 1.623 | 830.98 |
| copy | 48 KiB | 128 | 34.323 | 29 | 34.185, 34.273, 34.323 | 0.40 | 17.162 | 3.729 | 1.865 | 2864.09 |
| copy | 96 KiB | 64 | 32.780 | 42 | 32.780, 32.766, 32.777 | 0.04 | 16.390 | 3.905 | 1.952 | 5997.80 |
| copy | 256 KiB | 32 | 32.015 | 58 | 31.979, 32.015, 31.989 | 0.11 | 16.008 | 3.998 | 1.999 | 16376.32 |
| copy | 2 MiB | 4 | 31.460 | 74 | 31.417, 31.426, 31.460 | 0.14 | 15.730 | 4.069 | 2.034 | 133321.81 |
| copy | 32 MiB | 2 | 31.438 | 87 | 31.438, 31.434, 31.437 | 0.01 | 15.719 | 4.072 | 2.036 | 2134641.64 |

File: `results/membench-jibin-011/results/bootF1/bandwidth-dram-1core.csv`. Spread = (max - min) / max over the 3 reps.

- **Repeatability [M]**: read reps spread 0.33 to 1.80 % (largest at 48 KiB), write 0.01 to 0.04 %, copy 0.01 to 0.51 %.
- **Level transitions [M]** (ratio of best GB/s to the next smaller footprint):

| kernel | 16 -> 48 KiB | 48 -> 96 KiB | 96 -> 256 KiB | 256 KiB -> 2 MiB | 2 -> 32 MiB |
|---|---|---|---|---|---|
| read | -51.3 % | -1.5 % | -2.2 % | -4.8 % | -1.9 % |
| write | +2.7 % | +0.9 % | +0.6 % | +0.3 % | +0.1 % |
| copy | -13.0 % | -4.5 % | -2.3 % | -1.7 % | -0.1 % |

- **Where each footprint sits [M sizes, sysinfo]**: boot F1 `sysinfo.txt` lines 101 to 104 give L1 data 32 KiB (per core), L2 128 KiB and L3 256 KiB (per two-core cluster). So 16 KiB fits the L1, 48 and 96 KiB fit the L2, 256 KiB exceeds the L2 and fits L2 plus L3, 2 MiB exceeds the cluster caches (SLC range), 32 MiB exceeds the SLC (DRAM model). For copy double each footprint (16 KiB copy = 32 KiB = the whole L1).
- **Read [M]**: one step only. The rate falls 51.3 % between 16 and 48 KiB (L1 to L2). From 48 KiB to 32 MiB it falls from 27.299 to 24.575 GB/s (10.0 % in total), which is 4.69 to 5.21 effective cycles per 64 bytes.
- **Write [M]**: no step. 30.608 GB/s at 16 KiB, 31.437 to 31.997 GB/s from 48 KiB to 32 MiB (4.000 effective cycles per 64 bytes at 32 MiB).
- **Copy [M]**: 39.433 GB/s at 16 KiB, then 34.323 falling to 31.438 GB/s (both directions counted). At 32 MiB a copy takes 8.14 effective cycles per 64 bytes copied. The read row plus the write row at 32 MiB take 9.21. The copy loop is a separate loop, so the two numbers are a comparison of loops, not a sum of parts.

## 2. Against the documented throughput [D + M]

Source: Arm C1-Nano Core Software Optimization Guide, 109590_0001_04, issue 04 (`refs/arm-c1-nano-r0p1-sog-109590_0001_04.pdf`).

- **[D] page 8, Table 1-1**: the core has two memory pipelines, "Load/Store: Load and store" and "Load: Load". The LLVM model in `refs/AArch64SchedC1Nano.td` lines 57 and 58 has the same two (`C1NanoUnitLdSt` "Load/Store shared pipe", `C1NanoUnitLd1` "Load pipe").
- **[D] page 9, section 2.1**: "Execution Throughput is maximum throughput (in instructions per cycle) of the specified instruction group".
- **[D] page 21, Table 2-13 (AArch64 FP load instructions)**: "Load vector pair, immediate offset, Q-form", LDP, latency 3, throughput 1, pipelines Load/Store and Load. One `ldp q,q` moves 32 bytes, so the documented read ceiling of the kernel is 32 bytes per cycle = 64 GB/s at 2.0 GHz. ("Load vector reg, unsigned immediate", LDR, has throughput 2: 2 x 16 bytes, the same 32 bytes per cycle.)
- **[D] page 22, Table 2-14 (AArch64 FP Store instructions)**: "Store vector pair, immediate offset, Q-form", STP, throughput 1/2, pipeline Load/Store. One `stp q,q` moves 32 bytes every 2 cycles, so the documented write ceiling is 16 bytes per cycle = 32 GB/s. ("Store vector reg, unsigned immediate", STR, has throughput 1: 16 bytes per cycle.)
- **[D] page 14, Table 2-6**: PRFM is listed in the load groups with throughput 2, pipelines Load/Store and Load. A software prefetch hint therefore uses a load pipeline slot.
- **[I]** The lead "read dual 128-bit, write 128-bit (C1-Nano TRM)" could not be checked: the TRM is not in `refs/`. The guide states instruction throughput, not datapath width. The page should cite the guide's throughput rows (32 and 16 bytes per cycle), which give the same two ceilings.
- **Copy ceiling est. [H]**: 64 bytes copied = 2 LDP + 2 STP. If an LDP holds both pipelines for 1 cycle and an STP holds the Load/Store pipeline for 2 cycles, that is 6 cycles per 128 bytes counted = 21.33 bytes per cycle est. = 42.67 GB/s est. The guide gives no mixed-loop figure. Test: a copy row in the single-call form at 4 to 8 KiB per buffer.

| kernel | footprint | best GB/s | bytes per cycle | documented bytes per cycle | % of documented | excess ns per pass over the documented rate | excess cycles per pass |
|---|---|---|---|---|---|---|---|
| read | 16 KiB | 56.085 | 28.043 | 32.00 | 87.6 | +36.13 | +72.3 |
| read | 48 KiB | 27.299 | 13.649 | 32.00 | 42.7 | +1032.51 | +2065.0 |
| read | 96 KiB | 26.877 | 13.438 | 32.00 | 42.0 | +2121.55 | +4243.1 |
| read | 256 KiB | 26.297 | 13.149 | 32.00 | 41.1 | +5872.59 | +11745.2 |
| read | 2 MiB | 25.044 | 12.522 | 32.00 | 39.1 | +50970.70 | +101941.4 |
| read | 32 MiB | 24.575 | 12.287 | 32.00 | 38.4 | +841100.89 | +1682201.8 |
| write | 16 KiB | 30.608 | 15.304 | 16.00 | 95.7 | +23.28 | +46.6 |
| write | 48 KiB | 31.437 | 15.719 | 16.00 | 98.2 | +27.51 | +55.0 |
| write | 96 KiB | 31.711 | 15.855 | 16.00 | 99.1 | +28.00 | +56.0 |
| write | 256 KiB | 31.887 | 15.944 | 16.00 | 99.6 | +29.03 | +58.1 |
| write | 2 MiB | 31.981 | 15.991 | 16.00 | 99.9 | +38.94 | +77.9 |
| write | 32 MiB | 31.997 | 15.998 | 16.00 | 100.0 | +98.31 | +196.6 |
| copy | 16 KiB | 39.433 | 19.716 | 21.33 est. | 92.4 | +62.98 | +126.0 |
| copy | 48 KiB | 34.323 | 17.162 | 21.33 est. | 80.4 | +560.09 | +1120.2 |
| copy | 96 KiB | 32.780 | 16.390 | 21.33 est. | 76.8 | +1389.80 | +2779.6 |
| copy | 256 KiB | 32.015 | 16.008 | 21.33 est. | 75.0 | +4088.32 | +8176.6 |
| copy | 2 MiB | 31.460 | 15.730 | 21.33 est. | 73.7 | +35017.81 | +70035.6 |
| copy | 32 MiB | 31.438 | 15.719 | 21.33 est. | 73.7 | +561777.64 | +1123555.3 |

- **[M] Write is at the documented rate plus a fixed cost per pass.** The four F1 write rows of 16 to 256 KiB fit ns per pass = 25.12 ns + bytes / 31.982 GB/s (15.991 bytes per cycle). Largest residual 2.12 ns against the 2 % limit of 10.71 ns: the fit is valid. All six rows fit 28.21 ns + bytes / 31.998 GB/s (largest residual 6.32 ns, valid).
- **[M] Read in the L1 is 87.6 % of the documented rate** in the looped form: 292.13 ns per 16 KiB pass against 256 ns at 32 bytes per cycle, 36.1 ns (72 cycles) over. Section 3 splits this excess with the boot E forms.
- **[M] Read past the L1 is 43 to 38 % of the documented load rate**, at every source level.

## 3. Supplementary: the two L1 forms, boot E `bandwidth-l1-passes.csv` (looped) and `bandwidth-l1-asmpasses.csv` (single-call)

**Why boot F1 has no row that measures the same thing**: boot F1's core sweep has one footprint inside the L1 (16 KiB) and only the looped form (`asm_passes=0` in every header of `bandwidth-dram-1core.csv`). A cost per call needs the single-call form, and a fit needs several L1 footprints. The only `*-l1-*` files of boot F1 are CME files (`cme-bandwidth-l1-*.csv`). Boot E has the same firmware state as F1 (L3 on, prefetchers on).
**Cross-check [M]**: the boot E looped 16 KiB rows repeat boot F1's: read 56.004 against 56.085 GB/s (-0.14 %), write 30.494 against 30.608 GB/s (-0.37 %).

Forms (`bandwidth.c` lines 32 to 41, 196 to 232): looped = one kernel call per pass. Single-call = all passes of a rep in one kernel call. 5 reps, about 4 MiB moved per rep, counters per 64-byte line (`--perf`).

| form | kernel | footprint | best GB/s | file line | spread % | bytes per cycle | % of documented | ns per pass | excess over documented, ns (cycles) | L1 refills per pass | L2 refills per pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| looped | read | 4 KiB | 40.910 | 8 | 0.16 | 20.455 | 63.9 | 100.122 | +36.12 (+72.2) | 0.026 | 0.001 |
| looped | read | 8 KiB | 50.426 | 25 | 0.13 | 25.213 | 78.8 | 162.456 | +34.46 (+68.9) | 0.128 | 0.000 |
| looped | read | 16 KiB | 56.004 | 43 | 0.35 | 28.002 | 87.5 | 292.551 | +36.55 (+73.1) | 0.870 | 0.051 |
| looped | read | 24 KiB | 57.258 | 61 | 1.82 | 28.629 | 89.5 | 429.215 | +45.22 (+90.4) | 4.109 | 1.267 |
| looped | write | 4 KiB | 26.589 | 15 | 0.39 | 13.294 | 83.1 | 154.049 | +26.05 (+52.1) | 0.006 | 0.002 |
| looped | write | 8 KiB | 29.139 | 34 | 0.40 | 14.569 | 91.1 | 281.135 | +25.14 (+50.3) | 0.013 | 0.004 |
| looped | write | 16 KiB | 30.494 | 52 | 0.10 | 15.247 | 95.3 | 537.286 | +25.29 (+50.6) | 0.026 | 0.008 |
| looped | write | 24 KiB | 30.972 | 70 | 0.13 | 15.486 | 96.8 | 793.491 | +25.49 (+51.0) | 0.017 | 0.000 |
| single-call | read | 4 KiB | 53.096 | 8 | 0.19 | 26.548 | 83.0 | 77.143 | +13.14 (+26.3) | 0.032 | 0.003 |
| single-call | read | 8 KiB | 57.890 | 24 | 5.37 | 28.945 | 90.5 | 141.510 | +13.51 (+27.0) | 0.154 | 0.004 |
| single-call | read | 16 KiB | 60.331 | 44 | 0.38 | 30.166 | 94.3 | 271.569 | +15.57 (+31.1) | 0.922 | 0.026 |
| single-call | read | 24 KiB | 60.586 | 61 | 1.74 | 30.293 | 94.7 | 405.638 | +21.64 (+43.3) | 4.070 | 1.267 |
| single-call | write | 4 KiB | 29.034 | 17 | 0.09 | 14.517 | 90.7 | 141.076 | +13.08 (+26.2) | 0.003 | 0.002 |
| single-call | write | 8 KiB | 30.434 | 35 | 0.19 | 15.217 | 95.1 | 269.173 | +13.17 (+26.3) | 0.026 | 0.000 |
| single-call | write | 16 KiB | 31.191 | 53 | 0.13 | 15.595 | 97.5 | 525.280 | +13.28 (+26.6) | 0.026 | 0.000 |
| single-call | write | 24 KiB | 31.558 | 70 | 0.45 | 15.779 | 98.6 | 778.757 | +10.76 (+21.5) | 0.038 | 0.000 |

Files: `results/membench-jibin-010/results/bootE/bandwidth-l1-passes.csv` and `.../bandwidth-l1-asmpasses.csv`. Refills per pass = refill per line x lines per pass, best rep. The refill counters include prefetch fills.

### 3.1 Straight-line fits of ns per pass against bytes (4, 8, 16, 24 KiB), with the 2 % rule

Rule: a fit is void when its largest residual exceeds 2 % of the smallest pass time. A void intercept or rate is not a result.

| form | kernel | rep used | intercept ns | slope rate GB/s | slope bytes per cycle | residuals ns (4, 8, 16, 24 KiB) | largest residual ns | limit ns (2 % of smallest pass) | largest residual % | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| looped | read | best | 32.05 | 62.194 | 31.097 | +2.22, -1.31, -2.93, +2.02 | 2.929 | 2.002 | 2.93 | VOID |
| looped | read | median | 31.49 | 61.886 | 30.943 | +2.47, -1.35, -3.49, +2.36 | 3.489 | 2.003 | 3.48 | VOID |
| looped | write | best | 25.70 | 32.016 | 16.008 | +0.41, -0.44, -0.16, +0.18 | 0.437 | 3.081 | 0.28 | VALID |
| looped | write | median | 25.70 | 32.010 | 16.005 | +0.40, -0.43, -0.13, +0.16 | 0.433 | 3.081 | 0.28 | VALID |
| single-call | read | best | 10.52 | 62.367 | 31.183 | +0.95, -0.36, -1.65, +1.06 | 1.653 | 1.543 | 2.14 | VOID |
| single-call | read | median | 10.26 | 62.229 | 31.114 | +1.07, -0.37, -1.93, +1.23 | 1.930 | 1.543 | 2.50 | VOID |
| single-call | write | best | 13.97 | 32.108 | 16.054 | -0.46, +0.06, +1.03, -0.63 | 1.031 | 2.822 | 0.73 | VALID |
| single-call | write | median | 13.90 | 32.097 | 16.048 | -0.43, +0.06, +0.95, -0.58 | 0.954 | 2.822 | 0.68 | VALID |

- **[M] Write fits are valid in both forms.** Looped: 25.70 ns (51.4 cycles) per pass + bytes / 32.016 GB/s (16.008 bytes per cycle). Single-call: 13.97 ns (27.9 cycles) per pass + bytes / 32.108 GB/s (16.054 bytes per cycle). The slope rate equals the documented 16 bytes per cycle within 0.3 %.
- **[M] Read fits are void in both forms** (largest residual 2.93 % looped, 2.14 % single-call, limit 2 %). No read intercept and no read slope rate may be quoted. Quote the read rows themselves.
- **[M] The read residuals have the same shape in both forms** (positive at 4 KiB, negative at 8 and 16 KiB, positive at 24 KiB): the points curve upward at 24 KiB.
- **[H] The curve comes from L1 refills that grow with the footprint.** The single-call read rows count 0.03, 0.15, 0.92 and 4.07 L1 refills per pass at 4, 8, 16 and 24 KiB, and the excess over the documented rate is 13.1, 13.5, 15.6 and 21.6 ns per pass. Aggregate refill counts do not prove which pass paid for which refill. Test: the same rows with the buffer placed so that it cannot share L1 sets with the stack, or a row with L1 refills forced to zero (2 KiB steps up to 16 KiB).
- **Boot C cross-check [M]** (prefetchers on, L3 off, same script): write fits valid (looped 23.71 ns + bytes / 31.935 GB/s, single-call 9.05 ns + bytes / 31.984 GB/s), read fits void (5.39 % and 4.45 %). Same verdicts. The write intercepts differ from boot E by 2.0 ns (looped) and 4.9 ns (single-call), so an intercept is known to about 5 ns only. Boot C is not proposed for the page.

### 3.2 Looped minus single-call: the measured difference between two loops [M]

| kernel | footprint | looped GB/s (line) | single-call GB/s (line) | looped ns per pass | single-call ns per pass | difference ns per pass | difference cycles per pass |
|---|---|---|---|---|---|---|---|
| read | 4 KiB | 40.910 (8) | 53.096 (8) | 100.122 | 77.143 | +22.979 | +45.96 |
| read | 8 KiB | 50.426 (25) | 57.890 (24) | 162.456 | 141.510 | +20.946 | +41.89 |
| read | 16 KiB | 56.004 (43) | 60.331 (44) | 292.551 | 271.569 | +20.982 | +41.96 |
| read | 24 KiB | 57.258 (61) | 60.586 (61) | 429.215 | 405.638 | +23.577 | +47.15 |
| write | 4 KiB | 26.589 (15) | 29.034 (17) | 154.049 | 141.076 | +12.973 | +25.95 |
| write | 8 KiB | 29.139 (34) | 30.434 (35) | 281.135 | 269.173 | +11.963 | +23.93 |
| write | 16 KiB | 30.494 (52) | 31.191 (53) | 537.286 | 525.280 | +12.006 | +24.01 |
| write | 24 KiB | 30.972 (70) | 31.558 (70) | 793.491 | 778.757 | +14.734 | +29.47 |

- **[M]** One kernel call per pass costs 20.9 to 23.6 ns (42 to 47 cycles) more per pass than the single-call form for read, and 12.0 to 14.7 ns (24 to 29 cycles) for write. This is the net cost of the per-pass machinery (call, return, register save, the C loop step and byte accounting) against the assembly's own loop step. It is not the cost of the call and return alone (`bandwidth.c` lines 35 to 38).
- **[M, source]** The read kernel saves and restores d8 to d15 on every call. The write kernel clobbers only v0 and saves nothing (`bandwidth.c` lines 129 to 131 and 199). That is consistent with the larger read difference. [H] for the size of the effect: no row isolates the register save.
- **[M]** The best L1 rates are in the single-call form: read 60.586 GB/s at 24 KiB (94.7 % of 64 GB/s), write 31.558 GB/s at 24 KiB (98.6 % of 32 GB/s).
- **[M] Caution**: the single-call read 8 KiB row has a rep spread of 5.37 % (one rep of 54.780 GB/s, four of 57.87 to 57.89). The best-row rule removes it.

## 4. Supplementary: read variants and per-line counters, boot E `bandwidth-read-prefetch.csv`; prefetchers off, boot B (twin: boot D)

**Why boot F1 has no row that measures the same thing**:
- Boot F1 runs only the plain `read` kernel at 2 MiB and 32 MiB (`--kernel all` = read, write, copy, `run_asimov.sh` line 148) and without `--perf`. It has no row with a PRFM hint, no two-stream row and no per-line counters on any core bandwidth row.
- The plain rows of boot E repeat boot F1: 24.945 against 25.044 GB/s at 2 MiB (-0.40 %), 24.546 against 24.575 GB/s at 32 MiB (-0.12 %). So the plain rate is quoted from boot F1. Boot E supplies only the counters of the plain row and the variant rows.
- Boot F1 has prefetchers on. The only boot with prefetchers off and core rows of this kind is boot B (and its twin D). Boot F2 (prefetchers off, L3 on) has CME rows only.
- **Confound, must be stated on the page**: boot B differs from boot E in two ways, prefetchers off and the L3 of CPUs 2 to 9 holding no data (operator's README of boot B, `membench-jibin-006/README.md` lines 7 and 8). Boot D equals boot B except that the OCM is mapped with 2 MiB pages, which these DRAM rows do not use. Boot D agrees with boot B within 0.48 % on all ten rows, so boot D adds nothing: use boot B only.

Kernels (`bandwidth.c` lines 14 to 18, 146 to 180): `read` = plain loop. `read-pf4`, `read-pf8`, `read-pf16` = the plain loop plus one `PRFM PLDL1KEEP` per line, 4, 8 or 16 lines ahead. `read-2s` = two streams (the two halves of the buffer), 128 bytes from each per iteration.

| boot | kernel | footprint | best GB/s | file line | spread % | ratio to plain | cycles per line | L1 refill | L2 refill | L3 read refill (0xA2) | L1 refill by prefetcher (0x81BC) | L2 refill by L2 prefetcher (0x81BD) | L2 refill by L1 prefetcher (0x0111) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E | read | 2 MiB | 24.945 | 6 | 0.40 | 1.000 | 5.13 | 0.9947 | 0.9645 | 0.0003 | 0.9928 | 4.578e-05 | 0.9635 |
| E | read-pf4 | 2 MiB | 20.196 | 12 | 0.17 | 0.810 | 6.34 | 1.0004 | 1.0010 | 0.0009 | 0.4626 | 0.0022 | 0.4619 |
| E | read-pf8 | 2 MiB | 18.425 | 20 | 0.53 | 0.739 | 6.95 | 1.0004 | 1.0005 | 0.001 | 0.2836 | 0.0046 | 0.2821 |
| E | read-pf16 | 2 MiB | 18.446 | 26 | 3.18 | 0.739 | 6.94 | 1.0004 | 1.0005 | 0.001 | 0.3427 | 0.0034 | 0.3419 |
| E | read-2s | 2 MiB | 17.982 | 32 | 5.53 | 0.721 | 7.12 | 1.1656 | 1.1463 | 0.0032 | 0.9903 | 0.0066 | 0.9813 |
| E | read | 32 MiB | 24.546 | 39 | 0.07 | 1.000 | 5.22 | 0.9998 | 0.9998 | 4.768e-05 | 0.9994 | 1.144e-05 | 0.9994 |
| E | read-pf4 | 32 MiB | 20.353 | 47 | 0.07 | 0.829 | 6.29 | 1.0000 | 1.0001 | 0.0001 | 0.4507 | 0.0004 | 0.4505 |
| E | read-pf8 | 32 MiB | 18.486 | 53 | 0.18 | 0.753 | 6.93 | 1.0000 | 1.0001 | 0.0002 | 0.2959 | 0.0099 | 0.2928 |
| E | read-pf16 | 32 MiB | 18.285 | 62 | 0.43 | 0.745 | 7.00 | 1.0000 | 1.0001 | 0.0002 | 0.3219 | 0.0124 | 0.3177 |
| E | read-2s | 32 MiB | 18.911 | 68 | 0.23 | 0.770 | 6.77 | 1.0988 | 1.0896 | 0.0012 | 0.99 | 0.0009 | 0.9897 |
| B | read | 2 MiB | 5.031 | 6 | 10.04 | 1.000 | 25.44 | 1.0003 | 1.0003 | 1 | 0 | 0 | 0 |
| B | read-pf4 | 2 MiB | 12.146 | 13 | 8.50 | 2.414 | 10.54 | 1.0003 | 1.0003 | 1 | 0 | 0 | 0 |
| B | read-pf8 | 2 MiB | 10.878 | 20 | 5.96 | 2.162 | 11.77 | 1.0003 | 1.0003 | 1 | 0 | 0 | 0 |
| B | read-pf16 | 2 MiB | 9.475 | 27 | 4.78 | 1.883 | 13.51 | 1.0004 | 1.0003 | 1 | 0 | 0 | 0 |
| B | read-2s | 2 MiB | 5.033 | 34 | 5.30 | 1.000 | 25.44 | 1.0003 | 1.0002 | 1 | 0 | 0 | 0 |
| B | read | 32 MiB | 2.377 | 39 | 0.00 | 1.000 | 53.84 | 1.0000 | 1.0000 | 1 | 0 | 9.537e-07 | 0 |
| B | read-pf4 | 32 MiB | 6.334 | 48 | 0.03 | 2.665 | 20.21 | 1.0000 | 1.0000 | 1 | 8.583e-06 | 0 | 8.583e-06 |
| B | read-pf8 | 32 MiB | 5.705 | 53 | 0.05 | 2.400 | 22.44 | 1.0000 | 1.0000 | 1 | 3.91e-05 | 1.907e-06 | 3.91e-05 |
| B | read-pf16 | 32 MiB | 4.919 | 62 | 0.39 | 2.069 | 26.02 | 1.0000 | 1.0000 | 1 | 4.387e-05 | 0 | 4.387e-05 |
| B | read-2s | 32 MiB | 2.370 | 67 | 0.00 | 0.997 | 54.02 | 1.0000 | 1.0000 | 1 | 0 | 9.537e-07 | 0 |

Files: `results/membench-jibin-010/results/bootE/bandwidth-read-prefetch.csv`, `results/membench-jibin-006/results/bootB/bandwidth-read-prefetch.csv`. Counters are per 64-byte line moved, from the best rep. Event numbers: `common.h` lines 330 to 338. `perf_cov` = 1.0000 in all rows.

- **[M] Prefetchers on (boot E), plain read**: 0.9998 L1 refills per line at 32 MiB, of which 0.9994 per line are refills requested by the prefetcher. 0.9994 L2 refills per line come from the L1 prefetcher's requests and 1.1e-05 from the L2 prefetcher. At 2 MiB: 0.9947, 0.9928, 0.9635. These are aggregate counts. They show that about one prefetcher-requested L1 refill happens per line moved. They do not give each line's history.
- **[M] Prefetchers on, every variant is slower than the plain loop**: PRFM 4, 8, 16 lines ahead gives 20.353, 18.486, 18.285 GB/s at 32 MiB (-17.1, -24.7, -25.5 %). Two streams give 18.911 GB/s (-23.0 %). At 2 MiB: -19.0, -26.1, -26.1 and -27.9 %.
- **[M] With the PRFM hint the prefetcher's share of L1 refills falls** from 1.00 per line to 0.45, 0.30 and 0.32 per line (32 MiB), while L1 refills stay at 1.00 per line. The loop costs 1.07, 1.71 and 1.78 more cycles per line than the plain loop (measured difference between loops).
- **[H] Why the hint slows the loop**: (a) each PRFM takes a load pipeline slot (documented throughput 2 per cycle, guide page 14) and adds one instruction per line, which accounts for at most about 0.5 cycle per line. (b) the hint's refills replace the prefetcher's refills and arrive later or interfere with its training. Test: the PRFM rows on a 16 KiB buffer (no refills) give the pure instruction cost of the hint.
- **[M] Two streams with prefetchers on**: 1.0988 L1 refills per line (32 MiB) and 1.1656 (2 MiB), more than one refill per line moved, with 0.9900 of them requested by the prefetcher. [H] Some prefetched lines are refilled twice. No counter in this set separates them.
- **[M] Prefetchers off (boot B), plain read**: 5.031 GB/s at 2 MiB (25.44 cycles per line) and 2.377 GB/s at 32 MiB (53.84 cycles per line). All three prefetcher refill counters read 0 (largest 4e-05 per line). L1, L2 and L3 read refills are 1.000 per line.
- **[M] Prefetchers off, the PRFM hint helps**: 4 lines ahead gives 2.41 x the plain rate at 2 MiB and 2.66 x at 32 MiB (6.334 GB/s). 8 lines: 2.40 x. 16 lines: 2.07 x. The shortest distance is the best of the three. Two streams give 0.997 x (no gain).
- **[M] Even the best software-prefetch row with prefetchers off (6.334 GB/s) is 0.26 x the plain row with prefetchers on (24.546 GB/s).** Boot B also has the L3 holding no data, so this ratio is not the prefetcher effect alone.
- **[M] 2 MiB rows of boot B are noisy**: rep spread 4.8 to 10.0 %, the first rep being the slowest in every kernel. The 32 MiB rows spread under 0.4 %. Prefer the 32 MiB rows for the figure.
- **Counter status**: 0x81BC, 0x81BD and 0x0111 read 0 with prefetchers off and about 1 per line with prefetchers on, which is a two-state check of the events. The split between "L1 prefetcher" and "L2 prefetcher" rests on the event names only: treat that split as exploratory.

## 5. Lines in flight est. [estimate]

Definition: lines in flight est. = chain load at the same footprint (walked once, best rep) / ns per 64-byte line of the stream. It is the number of line fetches that must overlap for the stream to reach its rate if each fetch takes one chain load from request to data. It is an estimate: the chain load is a separate loop with dependent loads, and nothing counts overlapping fetches directly.

| stream row | footprint | chain load ns (file:line) | stream GB/s (file:line) | ns per line | lines in flight est. |
|---|---|---|---|---|---|
| F1 read | 2 MiB | 23.714 (boot F1 latency-dram-large.csv:22) | 25.044 (boot F1 bandwidth-dram-1core.csv:66) | 2.556 | 9.28 est. |
| F1 write | 2 MiB | 23.714 (boot F1 latency-dram-large.csv:22) | 31.981 (boot F1 bandwidth-dram-1core.csv:70) | 2.001 | 11.85 est. |
| F1 copy | 2 MiB | 23.714 (boot F1 latency-dram-large.csv:22) | 31.460 (boot F1 bandwidth-dram-1core.csv:74) | 2.034 | 11.66 est. |
| E read-pf4 (chain of boot E) | 2 MiB | 24.177 (boot E latency-dram-large.csv:22) | 20.196 (boot E bandwidth-read-prefetch.csv:12) | 3.169 | 7.63 est. |
| E read-2s (chain of boot E) | 2 MiB | 24.177 (boot E latency-dram-large.csv:22) | 17.982 (boot E bandwidth-read-prefetch.csv:32) | 3.559 | 6.79 est. |
| B read (chain of boot B) | 2 MiB | 23.902 (boot B latency-dram-large.csv:21) | 5.031 (boot B bandwidth-read-prefetch.csv:6) | 12.721 | 1.88 est. |
| B read-pf4 (chain of boot B) | 2 MiB | 23.902 (boot B latency-dram-large.csv:21) | 12.146 (boot B bandwidth-read-prefetch.csv:13) | 5.269 | 4.54 est. |
| B read-pf8 (chain of boot B) | 2 MiB | 23.902 (boot B latency-dram-large.csv:21) | 10.878 (boot B bandwidth-read-prefetch.csv:20) | 5.883 | 4.06 est. |
| B read-pf16 (chain of boot B) | 2 MiB | 23.902 (boot B latency-dram-large.csv:21) | 9.475 (boot B bandwidth-read-prefetch.csv:27) | 6.755 | 3.54 est. |
| B read-2s (chain of boot B) | 2 MiB | 23.902 (boot B latency-dram-large.csv:21) | 5.033 (boot B bandwidth-read-prefetch.csv:34) | 12.716 | 1.88 est. |
| R3 read (chain of boot R3) | 2 MiB | 24.096 (boot R3 latency-dram-large.csv:21) | 9.311 (boot R3 bandwidth-dram-1core.csv:66) | 6.874 | 3.51 est. |
| F1 read | 32 MiB | 52.212 (boot F1 latency-dram-large.csv:45) | 24.575 (boot F1 bandwidth-dram-1core.csv:79) | 2.604 | 20.05 est. |
| F1 write | 32 MiB | 52.212 (boot F1 latency-dram-large.csv:45) | 31.997 (boot F1 bandwidth-dram-1core.csv:84) | 2.000 | 26.10 est. |
| F1 copy | 32 MiB | 52.212 (boot F1 latency-dram-large.csv:45) | 31.438 (boot F1 bandwidth-dram-1core.csv:87) | 2.036 | 25.65 est. |
| E read-pf4 (chain of boot E) | 32 MiB | 52.875 (boot E latency-dram-large.csv:45) | 20.353 (boot E bandwidth-read-prefetch.csv:47) | 3.144 | 16.82 est. |
| E read-2s (chain of boot E) | 32 MiB | 52.875 (boot E latency-dram-large.csv:45) | 18.911 (boot E bandwidth-read-prefetch.csv:68) | 3.384 | 15.62 est. |
| B read (chain of boot B) | 32 MiB | 52.248 (boot B latency-dram-large.csv:46) | 2.377 (boot B bandwidth-read-prefetch.csv:39) | 26.925 | 1.94 est. |
| B read-pf4 (chain of boot B) | 32 MiB | 52.248 (boot B latency-dram-large.csv:46) | 6.334 (boot B bandwidth-read-prefetch.csv:48) | 10.104 | 5.17 est. |
| B read-pf8 (chain of boot B) | 32 MiB | 52.248 (boot B latency-dram-large.csv:46) | 5.705 (boot B bandwidth-read-prefetch.csv:53) | 11.218 | 4.66 est. |
| B read-pf16 (chain of boot B) | 32 MiB | 52.248 (boot B latency-dram-large.csv:46) | 4.919 (boot B bandwidth-read-prefetch.csv:62) | 13.011 | 4.02 est. |
| B read-2s (chain of boot B) | 32 MiB | 52.248 (boot B latency-dram-large.csv:46) | 2.370 (boot B bandwidth-read-prefetch.csv:67) | 27.004 | 1.93 est. |
| R3 read (chain of boot R3) | 32 MiB | 52.185 (boot R3 latency-dram-large.csv:45) | 9.172 (boot R3 bandwidth-dram-1core.csv:79) | 6.978 | 7.48 est. |

- **Boot F1 read, 32 MiB**: 52.212 ns chain load / 2.604 ns per line = 20.0 lines in flight est. At 2 MiB: 23.714 / 2.556 = 9.3 est.
- **Boot B read (prefetchers off), 32 MiB**: 52.248 / 26.925 = 1.94 est. At 2 MiB 1.88 est. With the PRFM hint 4 lines ahead: 5.17 est. (32 MiB).
- **[H]** With prefetchers off the plain loop keeps about 2 line fetches in flight, the prefetchers raise that to about 20 at 32 MiB. Test: a counter of outstanding L1 or L2 fill requests, or the read loop with a stride that defeats the prefetcher on an L3-on boot.
- **Write and copy rows**: the same division gives 26.1 and 25.7 est. at 32 MiB. For stores the estimate has a weaker meaning: a store need not wait for its line the way a dependent load does. Do not put the write and copy values on the page as lines in flight without that caveat. Recommended: quote the read rows only.
- The DRAM level is an emulator memory model, not silicon timing (operator's README of boot F1, `membench-jibin-011/README.md` line 15: the four memory models have no configured delay). The estimate at 32 MiB inherits that.

## 6. Decision on `bandwidth-write-small.csv` and `bandwidth-write-small-r2prog.csv`: no reader value, leave out

- The two files run the same four write footprints (16, 48, 96, 256 KiB) with two preserved builds of the bandwidth program (`run_followup.sh` lines 209 to 222: `bandwidth_r3` and `bandwidth_r2`). The question they answer is which program build caused a difference between two earlier result sets. That is history of the benchmark program, not a property of the chip.
- **Boot F1 has rows that measure the same thing**: the write kernel at the same four footprints, with the current program build (`bandwidth-dram-1core.csv` lines 9, 25, 40, 55). On boot E the two preserved builds read within 0.25 % and 0.28 % of the boot F1 rows [M]:

| footprint | boot F1 current build GB/s | boot E `bandwidth_r3` build GB/s (line) | boot E `bandwidth_r2` build GB/s (line) | r3 minus r2, ns per pass |
|---|---|---|---|---|
| 16 KiB | 30.608 | 30.684 (5) | 30.637 (5) | -0.82 |
| 48 KiB | 31.437 | 31.368 (11) | 31.526 (12) | +7.85 |
| 96 KiB | 31.711 | 31.679 (19) | 31.755 (20) | +7.43 |
| 256 KiB | 31.887 | 31.872 (26) | 31.902 (27) | +7.73 |

- The only durable fact in them, a fixed cost per pass of the looped write, is carried better by the boot F1 write fit (section 2) and the boot E forms (section 3). Recommendation: do not use either file on the page.

## 7. Lead for the open item only: sequential read with the L3 on against off

Not part of the bandwidth section. Rows for the `open` researcher [M]:

| footprint | read, boot F1 (L3 on) GB/s | read, boot R3 (L3 holds no data) GB/s | F1 / R3 | write F1 / R3 | copy F1 / R3 |
|---|---|---|---|---|---|
| 16 KiB | 56.085 | 58.127 | 0.965 | 1.016 | 0.994 |
| 48 KiB | 27.299 | 17.483 | 1.561 | 1.003 | 1.307 |
| 96 KiB | 26.877 | 12.057 | 2.229 | 1.001 | 1.541 |
| 256 KiB | 26.297 | 10.164 | 2.587 | 1.001 | 1.658 |
| 2 MiB | 25.044 | 9.311 | 2.690 | 1.000 | 1.719 |
| 32 MiB | 24.575 | 9.172 | 2.679 | 1.000 | 1.750 |

- Read: boot F1 is 1.56 to 2.69 x boot R3 from 48 KiB up. Write differs by at most 1.60 % (16 KiB) and under 0.3 % from 48 KiB up.
- A cleaner pair with counters exists: boot E against boot C (prefetchers on in both, L3 on against off, same script and program). Plain read: 24.945 against 9.294 GB/s at 2 MiB and 24.546 against 9.196 GB/s at 32 MiB (`bootC/bandwidth-read-prefetch.csv` lines 6 and 39). In both boots about 1 L1 refill per line is requested by the prefetcher (boot C: 0.9994 at 32 MiB). The cycles per line are 5.22 against 13.92.
- Lines in flight est. on boot R3: 7.48 est. at 32 MiB against 20.0 est. on boot F1. The chain loads are equal (52.185 and 52.212 ns).

## Proposed figures

1. **One-core bandwidth by footprint (boot F1)**. Line chart with markers, x = footprint on a log axis (16 KiB to 32 MiB, six points), y = GB/s from 0, right-hand scale in bytes per cycle. Series: read (orange `#eb6834`), write (aqua `#1baf7a`), copy (violet `#6250d6`, labelled "both directions counted"). Grey capacity markers at 32 KiB (L1), 128 KiB (L2), 384 KiB (L2 + L3), 3.75 MiB est. (SLC). Grey reference lines at 64 GB/s (documented load throughput) and 32 GB/s (documented store throughput). Direct labels on the 16 KiB and 32 MiB points. Annotation on the figure: "read: -51 % from 16 to 48 KiB, then within 10 %". Takeaway: "write sits on the 32 GB/s line at every footprint, read leaves its line as soon as the buffer leaves the L1".
2. **The two L1 forms (boot E)**. Dumbbell plot, two panels (read, write), rows = 4, 8, 16, 24 KiB, x = GB/s. Hollow dot = looped form, filled dot = single-call form, grey vertical line at the documented rate (64 or 32 GB/s). The gap is labelled with the difference in ns per pass (read 21.0 to 23.6 ns, write 12.0 to 14.7 ns). Beside it a small table of the four fits with VALID / VOID. Takeaway: "removing the call per pass moves read to 83 to 95 % and write to 91 to 99 % of the documented rate".
3. **Read variants with prefetchers on and off (32 MiB)**. Horizontal dot plot, rows = plain, PRFM 4, PRFM 8, PRFM 16, two streams. Two dots per row: boot E orange (prefetchers on), boot B blue (prefetchers off, L3 holds no data). Value label on every dot. Annotation: "PRFM: -17 to -26 % with prefetchers on, x2.1 to x2.7 with prefetchers off". A second small panel repeats it at 2 MiB, or the 2 MiB numbers stay in the table only (boot B 2 MiB reps spread 5 to 10 %).
4. **Wall-clock lanes: the 32 MiB read stream (est.)**. Lane 1 "read loop": one block per line, 2.60 ns each. Lane 2 "line fetches": bars of 52.2 ns (the chain load), about 20 overlapping (est.), one starting every 2.60 ns. Lane 3 "same loop, prefetchers off (boot B)": 26.9 ns per line, about 2 fetches overlapping (est.), the waiting part dashed. Critical slice in red: the 26.9 ns per line of the prefetchers-off loop. Caption: "durations to scale, overlap schematic, lines in flight are estimates".
5. Optional small multiple under figure 3: per-line counters of the five boot E kernels (L1 refill, L1 refill by prefetcher) as paired bars, to show the prefetcher share falling from 1.00 to 0.30 to 0.45 with the hint.

## Numbers to quote

- One-core read, boot F1: 56.1 GB/s at 16 KiB (28.0 bytes per cycle, 2.28 effective cycles per 64 bytes), 27.3 GB/s at 48 KiB, 25.0 GB/s at 2 MiB, 24.6 GB/s at 32 MiB (12.3 bytes per cycle, 5.21 effective cycles per 64 bytes).
- One-core write, boot F1: 30.6 GB/s at 16 KiB, 32.0 GB/s at 2 MiB, 32.0 GB/s at 32 MiB (16.00 bytes per cycle, 4.00 effective cycles per 64 bytes). Rep spread at most 0.04 %.
- One-core copy, boot F1 (both directions counted): 39.4 GB/s at 16 KiB, 31.4 GB/s at 32 MiB.
- Documented ceilings (C1-Nano Software Optimization Guide, pages 21 and 22): 32 bytes per cycle for the LDP loop (64 GB/s), 16 bytes per cycle for the STP loop (32 GB/s).
- L1, single-call form, boot E: read up to 60.6 GB/s (94.7 % of documented), write up to 31.6 GB/s.
- Write fit, boot E: looped 25.7 ns per pass + bytes at 32.02 GB/s, single-call 14.0 ns per pass + bytes at 32.11 GB/s (both valid). Boot F1's own write rows: 25.1 ns + bytes at 31.98 GB/s (valid). Read fits: void.
- Looped minus single-call per pass, boot E: read 20.9 to 23.6 ns, write 12.0 to 14.7 ns.
- Plain read with prefetchers on, boot E, 32 MiB: 0.9994 prefetcher-requested L1 refills per line. PRFM 4 / 8 / 16 lines ahead: -17 / -25 / -26 %. Two streams: -23 %.
- Plain read with prefetchers off (boot B, L3 holds no data), 32 MiB: 2.38 GB/s (53.8 cycles per line). PRFM 4 lines ahead: 6.33 GB/s (2.66 x).
- Lines in flight est., read at 32 MiB: 20 est. on boot F1 (52.2 ns / 2.60 ns), 1.9 est. on boot B.

## Open or unexplained

1. **Read is flat at 5.2 to 4.7 effective cycles per 64 bytes from the L2 to the DRAM model.** The source level changes the chain load by a large factor, but not the stream rate. [H] The rate past the L1 is set by how fast lines enter the L1 (the prefetcher's fill rate), not by the source. Boot F1 has no counters on these rows, and boot E has them only at 2 MiB and 32 MiB. Test: the plain read row with `--perf` at 48, 96 and 256 KiB on an L3-on boot.
2. **Write at 32 MiB equals the documented store throughput (100.0 %).** One core writes 32 GB/s into a buffer larger than the SLC. [I] No write row above 24 KiB carries counters, so it is unknown whether each written line is first read from memory. The DRAM level is an emulator memory model with no configured delay (operator's README of boot F1), so this rate is not a silicon DRAM write rate. Test: the write rows at 2 MiB and 32 MiB with `--perf`, and the mesh counters around one write row.
3. **Read fits of the L1 forms are void.** The 24 KiB point lies above the line of the smaller three. [H] L1 refills (0.03 to 4.1 per pass, growing with footprint). See section 3.1 for the test.
4. **The L1 read does not reach the documented 32 bytes per cycle even in the single-call form** (13.1 to 21.6 ns per pass over, 83 to 95 %). [H] A fixed cost per rep is excluded (it would be divided by 176 to 1,024 passes), so the excess is per pass: the pass-end branch mispredict plus loop re-entry is a candidate. Test: a single-call row with twice the footprint per pass at constant refills, or the branch-mispredict counter per pass.
5. **Software prefetch lowers the rate with prefetchers on** (section 4, hypothesis and test there).
6. **Two streams with prefetchers on are 23 to 28 % slower than one stream** and refill more than one line per line moved. [H] the two streams share the prefetcher or the fill path. Test: the two-stream row with counters of prefetcher stream allocation, or two streams on two cores.
7. **Prefetchers-off rows exist only on boots where the L3 holds no data** (B, D). The prefetcher effect on the core read stream with the L3 on is not measured. Test: the `bandwidth-read-prefetch.csv` commands on a boot with prefetchers off and the L3 on (the firmware state of boot F2).
8. **Read with the L3 on against off** (section 7): open item owned by the `open` researcher.
9. **Not measured on any boot**: one-core `ldr16` / `str16` on DRAM, copy in the single-call form, any core bandwidth row with counters on boot F1.
