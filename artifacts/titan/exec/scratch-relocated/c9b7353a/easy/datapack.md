# Data pack for tackle-8mb-report-easy-read.html

Every value below was printed by `mkpack.py` (same folder) from `final8.json` on 2026-11-15, unless a line says "from file". J = the loaded JSON of
`/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb-analysis/final8.json`. R = `/home/jhan/workspace/titan/cache-perf/crb/results`.
Helper used in the paths: `rows(path, **kw)` = the list at the dotted path, filtered by equal fields (compare as strings). It is `Report.rows` of `report_final.py` (line 375). `one()` = first row (`Report.one`, line 385).
Cell = one CPU (2 or 41) in one session (1 or 2). Cell keys in the JSON are `"cpu2/s1"`, `"cpu2/s2"`, `"cpu41/s1"`, `"cpu41/s2"`.

## 0. Deviations from the task context (read first)

See section 8 at the end. The three that change what the page may say:
- Step ZS has no 32 KiB size. Its 13 sizes run from 1 MiB to 32 MiB. 11 are counted (1 and 8 MiB are printed, not counted).
- Old read is not 2.67 cycles per line at every size in step ZS: 37 of 44 rows from 1 to 16 MiB lie within 0.02 of 2.671. 7 rows at 2, 2.5 and 3 MiB lie at 2.707 to 2.817.
- "2.50 to 2.67 cycles at 8 MiB" pools three steps (`Report.cycles8`). Step ZS alone gives 2.505 to 2.596.

## 1. Step S2: the effect is real and comes from the new loop

- Step `S2`, binary `bwx8`. Result folders: `R/bwx8-S2-s1-20261115T003207Z` (session 1), `R/bwx8-S2-s2-20261115T042130Z` (session 2). JSON: `J["folders"]["S2/s1"]`, `["S2/s2"]`.
- Metric: rate in GB/s (1 GB = 1e9 bytes), cell value of the fourth 0.3 s window of the target (`widx` 3), median of the 6 unit values of the cell as `analyze8.py` stores it (`rate_table`, line 572, field `median` of the filtered contrast; source `s12-summary.json`, `J["round1"]["source"]`). Window and unit definitions: `DECISIONS-bwx8.md` lines 135 to 138. Gain = 100 x (new / old - 1), in %.
- Selection: `one("round1.cells", size=S, cpu=C, session=N)` = `Report.r1cell(size, cpu, ses)` (line 407). Fields: `oldread`, `read`, `asmread` (GB/s), `new_minus_old.gain_pct` (gain of `read`, %), `asm_minus_old.gain_pct` (gain of `asmread`, %), `new_minus_old.median` (GB/s). Sizes present: 32K, 1M, 4M, 8M, 16M.
- Reusable: `Report.gain_rows(cpu, ses)` (line 847) gives (size, bytes, old, new, gain, step) for S2 plus XF sizes.

| CPU | session | size | old read GB/s | read GB/s | asmread GB/s | gain read % | gain asmread % |
|---|---|---|---|---|---|---|---|
| 2 | 1 | 1M | 67.11 | 85.25 | 85.24 | 27.03 | 27.01 |
| 2 | 1 | 8M | 67.05 | 70.98 | 71.06 | 5.83 | 6.00 |
| 2 | 2 | 1M | 67.11 | 85.25 | 85.24 | 27.02 | 27.01 |
| 2 | 2 | 8M | 67.07 | 71.07 | 71.04 | 5.97 | 5.91 |
| 41 | 1 | 1M | 67.11 | 85.25 | 85.24 | 27.03 | 27.01 |
| 41 | 1 | 8M | 67.09 | 69.34 | 70.47 | 3.35 | 5.05 |
| 41 | 2 | 1M | 67.11 | 85.25 | 85.24 | 27.03 | 27.01 |
| 41 | 2 | 8M | 67.09 | 71.60 | 71.59 | 6.75 | 6.72 |

- Gain of `read` at 1 MiB: 27.02 to 27.03 % (4 cells). At 8 MiB: 3.35 to 6.75 %.
- Gain of `asmread` at 8 MiB: 5.05 to 6.72 %.
- Also available for a line chart: sizes 32K, 4M, 16M in the same rows (gain at 16 MiB is negative, -2.02 to -1.59 %).

Prediction P1 (old read keeps its rate from 1 to 8 MiB) and P2 (the new loop loses rate). Path `J["round1"]["per_cell"][cell]`:

| cell | P1.median: old(8M)-old(1M) GB/s | P1.largest_abs_plus_limit GB/s | P1.margin GB/s | P1.outcome (verbatim) | P2.read.median: read(8M)-read(1M) GB/s | P2.read.repeatable | P2.asmread.median GB/s | decomposition.new_share_pct % |
|---|---|---|---|---|---|---|---|---|
| cpu2/s1 | -0.046 | 0.170 | 0.3 | equivalent | -14.27 | True | -14.17 | 100.3 |
| cpu2/s2 | -0.045 | 0.201 | 0.3 | equivalent | -14.18 | True | -14.21 | 100.3 |
| cpu41/s1 | -0.024 | 0.080 | 0.3 | equivalent | -15.92 | True | -14.77 | 100.1 |
| cpu41/s2 | -0.026 | 0.093 | 0.3 | equivalent | -13.65 | True | -13.65 | 100.2 |

Recorded verdict strings (verbatim):
- `J["round1"]["P1"]["overall"]` = "meets its equivalence margin". Per CPU `J["round1"]["P1"]["per_cpu"]["cpu2"|"cpu41"]["outcome"]` = "equivalent", "equivalent".
- `J["round1"]["P2"]["read"]`: `confirmed_both` = True, `sign` = -1, per CPU `outcome` = "supported" (cpu2), "supported" (cpu41).
- `J["round1"]["P2"]["asmread"]`: `confirmed_both` = True, `sign` = -1, per CPU `outcome` = "supported" (cpu2), "supported" (cpu41).
- `J["round1"]["candidate"]` = "supported".
- Claim row `Report.claim("H1 / P1")` (id "H1 / P1 / P2"): `overall` = "P1 meets its equivalence margin; P2 read confirmed on both CPUs: True; P2 asmread confirmed on both CPUs: True; candidate supported".
- `per_session.s1` = "cpu2/s1: P1 equivalent, P2 read -14.27 GB/s (repeatable), new loop carries 100.3 % of the lost advantage; cpu41/s1: P1 equivalent, P2 read -15.92 GB/s (repeatable), new loop carries 100.1 % of the lost advantage"
- `per_session.s2` = "cpu2/s2: P1 equivalent, P2 read -14.18 GB/s (repeatable), new loop carries 100.3 % of the lost advantage; cpu41/s2: P1 equivalent, P2 read -13.65 GB/s (repeatable), new loop carries 100.2 % of the lost advantage"
- Rule text: `DECISIONS-bwx8.md` lines 141 to 145 ("P1, P2, the decomposition"): P1 "equivalent if every |d_r| + L <= 0.30"; P2 "supported if confirmed negative on the CPU".

## 2. Step ZS ("size as dose"): the cost of the new loop follows r

- Step `ZS`, binary `bwx11`, schedule generator `schedule_zs.py`. Folders: `R/bwx11-ZS-s1-20261115T100610Z`, `R/bwx11-ZS-s2-20261115T143012Z` (`J["ZS"]["folders"]`). 1 process per kernel, size and CPU, 6 s with counters, 52 processes per session.
- Selection: `sorted(rows("ZS.rows", kernel=K, cpu=C, session=N), key=size_bytes)` = `Report.zs(kernel, cpu, ses)` (line 396). Fields: `rate` (GB/s), `cyc` (processor cycles per 64-byte line, event `cpu_cycles`), `r` (event `l2d_cache_refill` per 64-byte line), `band_low`, `band_high` (cycles per line, asmread rows only), `inside` (asmread rows only), `size`, `size_bytes`. Also `l2_wb`, `l1_long_miss`, `bus_access` (not needed).
- Sizes: 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 12, 16, 24, 32 MiB (13). No 32 KiB row exists in ZS.
- Counted flag per size: `J["ZS"]["rule"][cell]["sizes"][size]["counted"]`. False for "1M" and "8M" in every cell, so 11 sizes are counted.
- Fitted line: `J["ZS"]["rule"][cell]["intercept"]`, `["slope"]` = `Report.zs_fit(cpu, ses)` (line 399). Median slope: `Report.slope()` (line 403).
- Reusable figure code: `Report.fig_cycles` (line 635), `Report.fig_dose` (line 1324).

Fitted line and count per cell (`J["ZS"]["rule"][cell]`):

| cell | intercept cycles/line | slope cycles per L2 refill | evaluated (counted sizes) | inside | outside | size outside (cyc, band) | exceeds (rule broken) |
|---|---|---|---|---|---|---|---|
| cpu2/s1 | 2.089 | 0.658 | 11 | 10 | 1 | 32M: cyc 2.822, band 2.533 to 2.817 | False |
| cpu2/s2 | 2.083 | 0.667 | 11 | 10 | 1 | 32M: cyc 2.816, band 2.530 to 2.813 | False |
| cpu41/s1 | 2.079 | 0.646 | 11 | 10 | 1 | 6M: cyc 2.412, band 2.429 to 2.673 | False |
| cpu41/s2 | 2.074 | 0.663 | 11 | 10 | 1 | 6M: cyc 2.416, band 2.429 to 2.673 | False |

- Slope range 0.646 to 0.667, median 0.660 cycles per L2 refill. Intercept range 2.074 to 2.089 cycles per line.
- Recorded verdict (verbatim), `J["ZS"]["overall"]`: "H1c in its simple form is not contradicted (cpu2/s1: 1 of 11 sizes outside, cpu2/s2: 1 of 11 sizes outside, cpu41/s1: 1 of 11 sizes outside, cpu41/s2: 1 of 11 sizes outside)"
- Claim row `Report.claim("H1c")` (id "H1c (via ZS)"): `statement` = "Each line that must come from the SLC costs a fixed number of extra cycles (0.50 to 0.69 per L2 refill)."; `rule` = "rule of step ZS".
- `per_session.s1` = "cpu2/s1: 1 of 11 counted sizes outside the band, line 2.089 + 0.658 r; cpu41/s1: 1 of 11 counted sizes outside the band, line 2.079 + 0.646 r"; `per_session.s2` = "cpu2/s2: 1 of 11 counted sizes outside the band, line 2.083 + 0.667 r; cpu41/s2: 1 of 11 counted sizes outside the band, line 2.074 + 0.663 r"

The band fixed before the data. File `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx8-2026-11-14/DECISIONS-bwx8.md`:
- Line 362, heading: "### Round 4, session 1: `ZC` read at 08:46 UTC, and the added step `ZS` (rule written before any `ZS` data)".
- Line 365 (why 0.50 and 0.69): "From the 8 MiB numbers of session 1 that cost is 0.50 (high level) to 0.69 (low level) cycles per L2 refill."
- Line 367 (the rule, verbatim): "Rule: r = `l2d_cache_refill` per 64 B (median over the windows). H1c predicts for `asmread` at every size: cycles per 64 B lie between 2.10 + 0.50 r - 0.05 and 2.10 + 0.69 r + 0.05. H1c in this simple form is contradicted if more than 2 of the 11 sizes other than 1 and 8 MiB lie outside the band on both CPUs in both sessions. For old read the prediction is: cycles per 64 B stay within 0.02 of 2.671 while 2.10 + 0.69 r is below 2.671, that is while r is below 0.83."
- The band was built from session 1 numbers of steps ZC and XC* at 1 and 8 MiB. That is why 1 and 8 MiB are not counted.

### ZS rows, kernel `asmread`

CPU 2, session 1:

| size | rate GB/s | cyc per line | r | band_low | band_high | inside | counted |
|---|---|---|---|---|---|---|---|
| 1M | 85.24 | 2.102 | 0.000 | 2.050 | 2.150 | True | False |
| 1.5M | 85.07 | 2.106 | 0.001 | 2.050 | 2.150 | True | True |
| 2M | 81.69 | 2.193 | 0.069 | 2.085 | 2.198 | True | True |
| 2.5M | 78.71 | 2.275 | 0.341 | 2.220 | 2.385 | True | True |
| 3M | 76.42 | 2.344 | 0.463 | 2.281 | 2.469 | True | True |
| 4M | 71.02 | 2.522 | 0.620 | 2.360 | 2.578 | True | True |
| 5M | 73.89 | 2.424 | 0.702 | 2.401 | 2.634 | True | True |
| 6M | 68.34 | 2.621 | 0.758 | 2.429 | 2.673 | True | True |
| 8M | 71.09 | 2.519 | 0.826 | 2.463 | 2.720 | True | False |
| 12M | 67.45 | 2.655 | 0.893 | 2.496 | 2.766 | True | True |
| 16M | 65.73 | 2.725 | 0.923 | 2.512 | 2.787 | True | True |
| 24M | 64.21 | 2.789 | 0.953 | 2.526 | 2.807 | True | True |
| 32M | 63.47 | 2.822 | 0.967 | 2.533 | 2.817 | False | True |

CPU 2, session 2:

| size | rate GB/s | cyc per line | r | band_low | band_high | inside | counted |
|---|---|---|---|---|---|---|---|
| 1M | 85.23 | 2.102 | 0.000 | 2.050 | 2.150 | True | False |
| 1.5M | 85.13 | 2.104 | 0.001 | 2.050 | 2.150 | True | True |
| 2M | 82.50 | 2.171 | 0.068 | 2.084 | 2.197 | True | True |
| 2.5M | 76.84 | 2.331 | 0.347 | 2.224 | 2.390 | True | True |
| 3M | 76.23 | 2.349 | 0.462 | 2.281 | 2.469 | True | True |
| 4M | 74.68 | 2.399 | 0.614 | 2.357 | 2.573 | True | True |
| 5M | 73.93 | 2.422 | 0.702 | 2.401 | 2.635 | True | True |
| 6M | 67.74 | 2.644 | 0.764 | 2.432 | 2.677 | True | True |
| 8M | 70.94 | 2.525 | 0.827 | 2.463 | 2.720 | True | False |
| 12M | 66.28 | 2.703 | 0.883 | 2.492 | 2.759 | True | True |
| 16M | 65.73 | 2.725 | 0.923 | 2.512 | 2.787 | True | True |
| 24M | 64.18 | 2.791 | 0.952 | 2.526 | 2.807 | True | True |
| 32M | 63.61 | 2.816 | 0.960 | 2.530 | 2.813 | False | True |

CPU 41, session 1:

| size | rate GB/s | cyc per line | r | band_low | band_high | inside | counted |
|---|---|---|---|---|---|---|---|
| 1M | 85.24 | 2.102 | 0.000 | 2.050 | 2.150 | True | False |
| 1.5M | 85.28 | 2.101 | 0.001 | 2.050 | 2.150 | True | True |
| 2M | 82.71 | 2.165 | 0.069 | 2.084 | 2.198 | True | True |
| 2.5M | 77.96 | 2.298 | 0.350 | 2.225 | 2.392 | True | True |
| 3M | 77.22 | 2.320 | 0.462 | 2.281 | 2.469 | True | True |
| 4M | 73.07 | 2.451 | 0.616 | 2.358 | 2.575 | True | True |
| 5M | 69.62 | 2.573 | 0.720 | 2.410 | 2.647 | True | True |
| 6M | 74.27 | 2.412 | 0.758 | 2.429 | 2.673 | False | True |
| 8M | 71.50 | 2.505 | 0.826 | 2.463 | 2.720 | True | False |
| 12M | 67.26 | 2.663 | 0.882 | 2.491 | 2.758 | True | True |
| 16M | 65.95 | 2.716 | 0.923 | 2.512 | 2.787 | True | True |
| 24M | 64.56 | 2.774 | 0.944 | 2.522 | 2.802 | True | True |
| 32M | 63.87 | 2.804 | 0.960 | 2.530 | 2.812 | True | True |

CPU 41, session 2:

| size | rate GB/s | cyc per line | r | band_low | band_high | inside | counted |
|---|---|---|---|---|---|---|---|
| 1M | 85.24 | 2.102 | 0.000 | 2.050 | 2.150 | True | False |
| 1.5M | 85.31 | 2.100 | 0.001 | 2.050 | 2.150 | True | True |
| 2M | 83.27 | 2.151 | 0.068 | 2.084 | 2.197 | True | True |
| 2.5M | 79.23 | 2.261 | 0.340 | 2.220 | 2.384 | True | True |
| 3M | 76.28 | 2.348 | 0.471 | 2.286 | 2.475 | True | True |
| 4M | 72.52 | 2.470 | 0.622 | 2.361 | 2.579 | True | True |
| 5M | 69.85 | 2.564 | 0.715 | 2.407 | 2.643 | True | True |
| 6M | 74.12 | 2.416 | 0.758 | 2.429 | 2.673 | False | True |
| 8M | 69.00 | 2.596 | 0.820 | 2.460 | 2.716 | True | False |
| 12M | 67.71 | 2.645 | 0.892 | 2.496 | 2.766 | True | True |
| 16M | 66.15 | 2.708 | 0.913 | 2.506 | 2.780 | True | True |
| 24M | 64.70 | 2.768 | 0.944 | 2.522 | 2.801 | True | True |
| 32M | 63.70 | 2.812 | 0.966 | 2.533 | 2.817 | True | True |

### ZS rows, kernel `oldread`

CPU 2, session 1:

| size | rate GB/s | cyc per line | r | old-read rule applies | holds |
|---|---|---|---|---|---|
| 1M | 67.08 | 2.670 | 0.000 | True | True |
| 1.5M | 66.87 | 2.679 | 0.001 | True | True |
| 2M | 66.08 | 2.710 | 0.070 | True | False |
| 2.5M | 67.05 | 2.671 | 0.334 | True | True |
| 3M | 67.04 | 2.671 | 0.455 | True | True |
| 4M | 67.04 | 2.671 | 0.606 | True | True |
| 5M | 66.90 | 2.677 | 0.695 | True | True |
| 6M | 67.04 | 2.672 | 0.751 | True | True |
| 8M | 67.04 | 2.672 | 0.819 | True | True |
| 12M | 67.03 | 2.672 | 0.884 | False | None |
| 16M | 66.93 | 2.676 | 0.914 | False | None |
| 24M | 66.53 | 2.692 | 0.933 | False | None |
| 32M | 63.89 | 2.803 | 0.961 | False | None |

CPU 2, session 2:

| size | rate GB/s | cyc per line | r | old-read rule applies | holds |
|---|---|---|---|---|---|
| 1M | 67.11 | 2.669 | 0.000 | True | True |
| 1.5M | 66.89 | 2.678 | 0.000 | True | True |
| 2M | 66.17 | 2.707 | 0.072 | True | False |
| 2.5M | 63.58 | 2.817 | 0.350 | True | False |
| 3M | 65.95 | 2.716 | 0.461 | True | False |
| 4M | 66.87 | 2.679 | 0.603 | True | True |
| 5M | 66.89 | 2.678 | 0.684 | True | True |
| 6M | 66.95 | 2.675 | 0.735 | True | True |
| 8M | 66.98 | 2.674 | 0.803 | True | True |
| 12M | 67.01 | 2.673 | 0.867 | False | None |
| 16M | 67.07 | 2.671 | 0.900 | False | None |
| 24M | 66.67 | 2.687 | 0.933 | False | None |
| 32M | 66.06 | 2.711 | 0.950 | False | None |

CPU 41, session 1:

| size | rate GB/s | cyc per line | r | old-read rule applies | holds |
|---|---|---|---|---|---|
| 1M | 67.11 | 2.669 | 0.000 | True | True |
| 1.5M | 66.94 | 2.676 | 0.001 | True | True |
| 2M | 66.80 | 2.681 | 0.065 | True | True |
| 2.5M | 65.43 | 2.737 | 0.344 | True | False |
| 3M | 67.07 | 2.671 | 0.455 | True | True |
| 4M | 67.06 | 2.671 | 0.606 | True | True |
| 5M | 67.01 | 2.673 | 0.683 | True | True |
| 6M | 67.06 | 2.671 | 0.751 | True | True |
| 8M | 67.08 | 2.670 | 0.801 | True | True |
| 12M | 67.03 | 2.672 | 0.867 | False | None |
| 16M | 67.09 | 2.670 | 0.899 | False | None |
| 24M | 66.49 | 2.694 | 0.933 | False | None |
| 32M | 66.13 | 2.708 | 0.950 | False | None |

CPU 41, session 2:

| size | rate GB/s | cyc per line | r | old-read rule applies | holds |
|---|---|---|---|---|---|
| 1M | 67.11 | 2.669 | 0.000 | True | True |
| 1.5M | 66.96 | 2.675 | 0.001 | True | True |
| 2M | 66.76 | 2.683 | 0.070 | True | True |
| 2.5M | 63.96 | 2.801 | 0.353 | True | False |
| 3M | 66.16 | 2.707 | 0.466 | True | False |
| 4M | 67.00 | 2.674 | 0.605 | True | True |
| 5M | 67.01 | 2.673 | 0.684 | True | True |
| 6M | 67.05 | 2.671 | 0.738 | True | True |
| 8M | 67.10 | 2.669 | 0.801 | True | True |
| 12M | 67.05 | 2.671 | 0.867 | False | None |
| 16M | 66.95 | 2.675 | 0.900 | False | None |
| 24M | 66.95 | 2.675 | 0.933 | False | None |
| 32M | 66.09 | 2.710 | 0.950 | False | None |

Old read summary (computed here from `ZS.rows`, kernel oldread, sizes 1 to 16 MiB, 44 rows): cycles per line 2.669 to 2.817, median 2.673. 37 rows within 0.02 of 2.671. Outside: [(2, 1, '2M', 2.71), (41, 1, '2.5M', 2.737), (2, 2, '2M', 2.707), (2, 2, '2.5M', 2.817), (2, 2, '3M', 2.716), (41, 2, '2.5M', 2.801), (41, 2, '3M', 2.707)].
- Recorded old-read check per cell: `J["ZS"]["rule"][cell]["oldread_checked"]` / `["oldread_fails"]` = cpu2/s1 9/1, cpu2/s2 9/3, cpu41/s1 9/1, cpu41/s2 9/2. The old-read prediction has no verdict string of its own in `J["ZS"]["overall"]`.
- asmread at 8 MiB in ZS: r = 0.826, 0.826, 0.827, 0.820; cyc = 2.519, 2.505, 2.525, 2.596. asmread at 1 MiB: r = 0.000, cyc = 2.102, 2.102, 2.102, 2.102.
- old read at 8 MiB in ZS: cyc = 2.672, 2.670, 2.674, 2.669.
- The range "2.50 to 2.67 cycles per line at 8 MiB" of the report is `Report.cycles8()` (line 498). It pools: `counters.rows` event cpu_cycles, size 8M, kernels read and asmread, fields low/high/single (steps XCA, XCB, XCC: 2.496 to 2.654); `ZS.rows` asmread 8M (2.505 to 2.596); `prefetch.YC` asmread 8M `per64.cpu_cycles` (2.580 to 2.671). Pooled: 2.496 to 2.671.
- Conversion used by the report: cycles per line = 2.8 GHz x 64 B / rate (CLOCK_GHZ = 2.8, `report_final.py` line 35). Example: 2.8 x 64 / 67.05 GB/s = 2.673 cycles (est., from the nominal clock).

## 3. Step ZN: slowed load-only loops keep their rate at 8 MiB

- Step `ZN`, binary `bwx11`. Folders: `R/bwx11-ZN-s1-20261115T092141Z`, `R/bwx11-ZN-s2-20261115T134554Z` (`J["folders"]["ZN/s1"]`, `["ZN/s2"]`). Kernels `read_nop64`, `read_nop96`, `read_nop128` (the asmread loop with 64, 96, 128 no-operation instructions) at 32K, 1M, 8M, 16M. 6 processes per cell.
- Selection: `one("families.ZN.rows", kernel=K, size=S, cpu=C, session=N)` = `Report.fam(kernel, size, cpu, ses)` (line 952). Fields: `median` (GB/s, median over the 6 processes of the process median rate), `p5`, `p95`, `n`, `asmread_gain_pct`.
- asmread of the same session comes from step YF, not ZN: `J["families"]["ZN"]["asmread_source"]` = s1 step "YF" folder `bwx10-YF-s1-20261115T073754Z`, s2 step "YF" folder `bwx10-YF-s2-20261115T120146Z`. Selection `one("prefetch.YF", kernel="asmread", size=S, cpu=C, session=N)`; fields `median`, `p5` (low level), `p95` (high level). `Report.asm8_for("ZN", cpu, ses)` (line 967) returns the 8 MiB median.
- Rule numbers per cell: `J["families"]["ZN"]["rule2"][cell]["kernels"][K]` with `C` (32 KiB median, GB/s), `median_8M`, `p95_8M`, `loss_32K_to_8M` (= C - median_8M, GB/s), `class`, `prediction_holds`, `contradicts`; and `["S8_low"]`, `["S8_high"]` (asmread 8 MiB p5 and p95 of step YF).

| cell | kernel | 32 KiB GB/s (C) | 8 MiB median GB/s | loss 32K to 8M GB/s | class | prediction_holds | contradicts |
|---|---|---|---|---|---|---|---|
| cpu2/s1 | read_nop96 | 54.94 | 54.96 | -0.011 | slow (C_k at most 66) | True | False |
| cpu2/s1 | read_nop128 | 42.89 | 42.91 | -0.020 | slow (C_k at most 66) | True | False |
| cpu2/s1 | asmread (step YF) | 132.45 | 67.78 (p5 67.24, p95 71.01) | 64.677 | - | - | - |
| cpu2/s2 | read_nop96 | 54.94 | 54.95 | -0.002 | slow (C_k at most 66) | True | False |
| cpu2/s2 | read_nop128 | 42.89 | 42.91 | -0.022 | slow (C_k at most 66) | True | False |
| cpu2/s2 | asmread (step YF) | 132.41 | 71.03 (p5 67.35, p95 71.08) | 61.384 | - | - | - |
| cpu41/s1 | read_nop96 | 54.94 | 55.02 | -0.078 | slow (C_k at most 66) | True | False |
| cpu41/s1 | read_nop128 | 42.89 | 42.96 | -0.063 | slow (C_k at most 66) | True | False |
| cpu41/s1 | asmread (step YF) | 132.47 | 71.49 (p5 69.06, p95 71.55) | 60.971 | - | - | - |
| cpu41/s2 | read_nop96 | 54.94 | 55.01 | -0.069 | slow (C_k at most 66) | True | False |
| cpu41/s2 | read_nop128 | 42.89 | 42.95 | -0.062 | slow (C_k at most 66) | True | False |
| cpu41/s2 | asmread (step YF) | 132.50 | 70.73 (p5 68.98, p95 71.58) | 61.774 | - | - | - |

- Largest |loss| of the two slow kernels: 0.078 GB/s (limit of the rule: 1.0 GB/s). All 8 `loss_32K_to_8M` values are negative: the 8 MiB median is slightly above the 32 KiB median.
- asmread loses 60.97 to 64.68 GB/s from 32 KiB to 8 MiB in the same sessions (step YF).
- Recorded verdict strings (verbatim), `J["families"]["ZN"]["overall"][K]`:
  - read_nop128: "H1 not contradicted by this kernel (loses more than 1.0 GB/s in 0 of 4 cells)"
  - read_nop64: "not a slow kernel (C_k above 66 GB/s): the contradiction rule does not apply"
  - read_nop96: "H1 not contradicted by this kernel (loses more than 1.0 GB/s in 0 of 4 cells)"
- Claim row id "H1 two limits (rule 2 of round 4, ZN)": `statement` = "A slow load-only kernel keeps its 32 KiB rate at 8 MiB."; `rule` = "rule 2 of round 4".
- `per_session.s1` = "cpu2/s1: read_nop64 C_k 75.10, 8M median 63.64, prediction fails, read_nop96 C_k 54.94, 8M median 54.96, prediction holds, read_nop128 C_k 42.89, 8M median 42.91, prediction holds; cpu41/s1: read_nop64 C_k 75.10, 8M median 70.99, prediction fails, read_nop96 C_k 54.94, 8M median 55.02, prediction holds, read_nop128 C_k 42.89, 8M median 42.96, prediction holds"
- `per_session.s2` = "cpu2/s2: read_nop64 C_k 74.63, 8M median 62.64, prediction holds, read_nop96 C_k 54.94, 8M median 54.95, prediction holds, read_nop128 C_k 42.89, 8M median 42.91, prediction holds; cpu41/s2: read_nop64 C_k 75.10, 8M median 71.82, prediction fails, read_nop96 C_k 54.94, 8M median 55.01, prediction holds, read_nop128 C_k 42.89, 8M median 42.95, prediction holds"
- Rule text, `DECISIONS-bwx8.md` line 350 (rule 2 of round 4, written before the data), quote: "Prediction: a kernel with C_k at most 66 GB/s has an 8 MiB cell median within 1.0 GB/s of C_k (it does not feel the supply limit, as old read does not). ... H1 (two limits, the smaller one holds) is contradicted if a slow kernel loses more than 1.0 GB/s from 32 KiB to 8 MiB on both CPUs in both sessions."
- `read_nop64` (C about 75 GB/s) is in ZN too. Its class is "between 66 and 76" and its `prediction_holds` is False in 3 of 4 cells. The page should not present it as proof. See section 8.

### Supplementary: gain predicted from two rates (12 of 12)

- Label (verbatim), `J["supplementary"]["gain_from_two_rates"]["label"]`: "supplementary, defined after the data was seen". It must be shown with this label.
- `cells` = 12, `cells_inside` = 12, `outside` = []. `summary_text` (verbatim): "the measured gain lies inside the predicted range in 12 of 12 cells of kernel, CPU and session"
- Rows: `J["supplementary"]["gain_from_two_rates"]["rows"]` (12 rows: kernels oldread, read_nop96, read_nop128 x 4 cells). Reusable: `Report.sup("gain_from_two_rates")` (line 470), table code `Report.sec4_sup` (line 1211).
- Formula (`final8.py` lines 2529 to 2535): C = 32 KiB cell median of the kernel. predicted_low_pct = 100 x (asmread 8 MiB p5 / C - 1). predicted_high_pct = 100 x (asmread 8 MiB p95 / C - 1). measured_pct = 100 x (asmread 8 MiB median / kernel 8 MiB median - 1). inside = low <= measured <= high. asmread from step YF (`asmread_step`).

| kernel | CPU | session | step | C GB/s | kernel 8M median GB/s | asmread 8M low / median / high GB/s | predicted gain % (low to high) | measured gain % | inside |
|---|---|---|---|---|---|---|---|---|---|
| oldread | 2 | 1 | S2 | 66.74 | 67.06 | 67.24 / 67.78 / 71.01 | 0.76 to 6.40 | 1.07 | True |
| oldread | 2 | 2 | S2 | 66.74 | 67.06 | 67.35 / 71.03 / 71.08 | 0.91 to 6.51 | 5.92 | True |
| oldread | 41 | 1 | S2 | 66.62 | 67.08 | 69.06 / 71.49 / 71.55 | 3.67 to 7.41 | 6.58 | True |
| oldread | 41 | 2 | S2 | 66.74 | 67.08 | 68.98 / 70.73 / 71.58 | 3.36 to 7.25 | 5.45 | True |
| read_nop128 | 2 | 1 | ZN | 42.89 | 42.91 | 67.24 / 67.78 / 71.01 | 56.77 to 65.55 | 57.94 | True |
| read_nop128 | 2 | 2 | ZN | 42.89 | 42.91 | 67.35 / 71.03 / 71.08 | 57.01 to 65.72 | 65.51 | True |
| read_nop128 | 41 | 1 | ZN | 42.89 | 42.96 | 69.06 / 71.49 / 71.55 | 61.01 to 66.82 | 66.44 | True |
| read_nop128 | 41 | 2 | ZN | 42.89 | 42.95 | 68.98 / 70.73 / 71.58 | 60.82 to 66.88 | 64.66 | True |
| read_nop96 | 2 | 1 | ZN | 54.94 | 54.96 | 67.24 / 67.78 / 71.01 | 22.38 to 29.24 | 23.33 | True |
| read_nop96 | 2 | 2 | ZN | 54.94 | 54.95 | 67.35 / 71.03 / 71.08 | 22.57 to 29.37 | 29.27 | True |
| read_nop96 | 41 | 1 | ZN | 54.94 | 55.02 | 69.06 / 71.49 / 71.55 | 25.69 to 30.23 | 29.94 | True |
| read_nop96 | 41 | 2 | ZN | 54.94 | 55.01 | 68.98 / 70.73 / 71.58 | 25.55 to 30.27 | 28.57 | True |

- Note for the author: the oldread rows of this table use the S2 old-read medians against the YF asmread medians. Their measured gains (1.07 to 6.58 %) are therefore not the S2 gains of section 1.

## 4. Step H2: why the first measurement said 0.94 %

- Step `H2`, script `run_h2.sh`, original binaries `bw_old` and `bw_new` of 2026-11-13, options `--threads 1 --bytes 8M --kernel read --reps 3 --min-ms 500`. Folders `R/h2-s1-20261115T063514Z`, `R/h2-s2-20261115T112456Z` (`J["H2"]["folders"]`). Per CPU and session: 12 processes per binary, 3 repetitions each = 36 new-read repetitions, 12 old/new pairs.
- Selection: `rows("H2.rows", cpu=C, session=N)`. Note: `cpu` is a string in these rows ("0", "2", "41"). Fields: `new_repetitions`, `low`, `between`, `high` (counts of new-read repetitions), `share_low`, `pairs`, `low_pairs`, `median_gain_pct` (median over the 12 pairs, %), `median_gain_low_pct`.
- Level limits of the rule (`final8.py` line 1025, `DECISIONS-bwx8.md` line 279): low = at or below 69.5 GB/s, high = at or above 70.5 GB/s.
- Rule (line 279, verbatim): "H2 (\"the original 0.94 % gain was measured at the low level\") is supported on a CPU if at least 75 % of the new-read repetitions are low in both sessions, and the median gain of the low processes is within 1.5 percentage points of 0.94 %. It is rejected if fewer than 25 % are low in both sessions. Otherwise undecided."

| CPU | session | new repetitions | low | between | high | share_low | median gain % | median gain of low pairs % | verdict of the CPU (verbatim) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 36 | 0 | 3 | 33 | 0.000 | 5.73 | - | rejected |
| 0 | 2 | 36 | 0 | 3 | 33 | 0.000 | 5.71 | - | rejected |
| 2 | 1 | 36 | 36 | 0 | 0 | 1.000 | 0.22 | 0.22 | supported |
| 2 | 2 | 36 | 35 | 0 | 1 | 0.972 | 0.17 | 0.17 | supported |
| 41 | 1 | 36 | 21 | 7 | 8 | 0.583 | 3.17 | 2.66 | undecided |
| 41 | 2 | 36 | 33 | 2 | 1 | 0.917 | 2.39 | 2.39 | undecided |

- Verdict strings: `J["H2"]["verdict"]` = {"cpu0": "rejected", "cpu2": "supported", "cpu41": "undecided"}. Claim row `Report.claim("H2")`: `overall` = "cpu0: rejected; cpu2: supported; cpu41: undecided".
- Reusable: `Report.read_h2(folder)` (line 1832) reads the 36 repetition rates per binary and CPU from `R/<folder>/H2.csv`; `Report.fig_h2` (line 1853) draws them.
- From file `H2.csv` (computed here with the `read_h2` parsing, not in the JSON), new-read repetition rates min / median / max in GB/s: session 1 CPU 0 70.15 / 70.86 / 71.12, CPU 2 66.75 / 67.14 / 67.43, CPU 41 68.12 / 69.33 / 71.59. Session 2 CPU 0 70.29 / 70.81 / 70.94, CPU 2 66.58 / 67.07 / 70.57, CPU 41 68.19 / 68.63 / 70.59. Old read medians 66.97 to 67.04 GB/s in all 6 groups.

### The two levels (GB/s) per CPU, step S4

- Step `S4`, binary `bwx8`, 60 s runs at 8 MiB, 200 windows of 0.3 s, 3 processes per kernel and CPU. Folders `R/bwx8-S4-s1-20261115T010216Z`, `R/bwx8-S4-s2-20261115T045137Z`.
- Selection: `one("levels.rows", step="S4", kernel=K, cpu=C, session=N)`. Fields `low`, `high` (GB/s, medians over the processes with two levels), `two_levels`, `one_level`, `processes`, `share_high`. Old read: `two_levels` = 0, `one_level` = 3 in all 4 cells (one rate for 60 s), rates in `one_level_rates`.

| kernel | CPU | session | low GB/s | high GB/s | processes with two levels | with one level | share of windows high | median of one-level rates GB/s |
|---|---|---|---|---|---|---|---|---|
| asmread | 2 | 1 | 67.65 | 71.08 | 3 | 0 | 0.54 | - |
| asmread | 2 | 2 | 67.85 | 71.01 | 2 | 1 | 0.87 | 71.21 |
| asmread | 41 | 1 | 69.03 | 71.60 | 3 | 0 | 0.29 | - |
| asmread | 41 | 2 | 69.30 | 71.53 | 2 | 1 | 0.78 | 68.95 |
| read | 2 | 1 | 68.50 | 71.08 | 2 | 1 | 0.73 | 71.07 |
| read | 2 | 2 | 67.85 | 71.05 | 3 | 0 | 0.88 | - |
| read | 41 | 1 | 69.17 | 71.59 | 3 | 0 | 0.24 | - |
| read | 41 | 2 | 69.30 | 71.52 | 3 | 0 | 0.68 | - |
| oldread | 2 | 1 | - | - | 0 | 3 | - | 67.05 |
| oldread | 2 | 2 | - | - | 0 | 3 | - | 67.01 |
| oldread | 41 | 1 | - | - | 0 | 3 | - | 67.07 |
| oldread | 41 | 2 | - | - | 0 | 3 | - | 67.05 |

- Pooled over both S4 sessions (`J["counters"]["acceptance"][i]["s4_low"]`, `["s4_high"]`, same value in every row of a CPU): CPU 2 low 67.79, high 71.05 GB/s. CPU 41 low 69.17, high 71.56 GB/s.
- No level values exist for CPU 0 in the JSON (S4 ran on CPUs 2 and 41 only).
- Example trace source: `report_final.py` `Report.fig_traces` (line 1687) reads `R/bwx8-S4-s1-20261115T010216Z/S4.csv` through `Report.read_s4(folder)` (line 1669). It draws the processes tagged `oldread-cpu2-p1` (idx 0), `asmread-cpu2-p1` (idx 1), `oldread-cpu41-p1` (idx 3), `asmread-cpu41-p1` (idx 4). Row format: `W,trial,phase,widx,kernel,pass_bytes,bytes,t_start_ns,t_end_ns`; keep phase "target"; rate GB/s = bytes / (t_end_ns - t_start_ns); x = t_start_ns / 1e9 s. Process blocks start at lines "-- step S4 session 1 idx N tag T ...".

## 5. The original observation (27 % and 0.94 %)

- Not in `final8.json` (only the constant 0.94 of the H2 rule, `final8.py` line 1025).
- Source file: `R/kernels-20261113T181222Z/one-thread.csv` (run of 2026-11-13 18:12 UTC, binaries `bw_old` and `bw_new`, CPUs 0 and 2, 2 rounds, 3 repetitions of 0.5 s per process).
- Table: `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md` lines 43 to 48, text line 50. Also `tackle-8mb-handoff.md` line 7.
- Recomputed here from the CSV (kernel read, best of the 12 repetitions of the 4 processes per binary and size; gain = 100 x (new / old - 1)):

| size | old read best GB/s | new read best GB/s | gain % | where the best sits |
|---|---|---|---|---|
| 32 KiB | 66.76 | 133.22 | 99.55 | CPU 2, round 1 |
| 1 MiB | 67.13 | 85.26 | 27.01 | CPU 2, round 2 |
| 8 MiB | 67.08 | 67.71 | 0.94 | CPU 2, round 1 (both) |

- All 12 new-read repetitions at 8 MiB of the original run lie between 67.36 and 67.71 GB/s (CPU 0: 67.39 to 67.58; CPU 2: 67.36 to 67.71). All are below the 69.5 GB/s low limit of the H2 rule. So the original run sat at the low level on CPU 0 as well as on CPU 2.
- Pair medians at 8 MiB quoted in `tackle-8mb.md` line 50: 0.51 %, 0.69 %, 0.94 %, 0.51 %.

## 6. Dead ends: recorded verdict and one number each

### H1b (count of L1 misses is the limit), steps YC and YF, binary `bwx10`
- Recorded overall verdict (verbatim), `J["prefetch"]["overall"]`: "not confirmed (cpu2/s1: H1b rejected: read_pf2048 halves the misses and is -7.99 GB/s against asmread; cpu2/s2: Insufficient data: no prefetch kernel has at most half of the asmread L1 long misses; cpu41/s1: Insufficient data: no prefetch kernel has at most half of the asmread L1 long misses; cpu41/s2: Insufficient data: no prefetch kernel has at most half of the asmread L1 long misses)"
- Short form for the page: "not confirmed". Rule: rule 3 of round 3, `DECISIONS-bwx8.md` line 309.
- One number (recorded cell, `J["prefetch"]["rule3"]["cpu2/s1"]["rise"]["read_pf2048"]`): -7.99 GB/s (the prefetch kernel that halves the misses is slower than asmread at 8 MiB, CPU 2 session 1).
- Alternative number, supplementary (label "supplementary, defined after the data was seen"), `J["supplementary"]["prefetch_1M"]["summary_text"]["1M"]`: "at 1 MiB (both sessions) the prefetch removes 94.2 to 99.2 % of the asmread first-level long misses, and the rate is 7.73 to 7.80 GB/s lower than asmread in all 16 cells of kernel, CPU and session"
- Folders: {"s1": {"YC": ["bwx10-YC-s1-20261115T073339Z"], "YF": ["bwx10-YF-s1-20261115T073754Z"]}, "s2": {"YC": ["bwx10-YC-s2-20261115T115731Z"], "YF": ["bwx10-YF-s2-20261115T120146Z"]}}.

### H1d (dirty lines / write-backs), steps ZC and ZD, binary `bwx11`
- Recorded overall verdict (verbatim), `J["evict"]["overall"]`: "Insufficient data: H1d stays open (s1: Insufficient data: with evict the L2 write-backs per 64 B stay at [0.819 0.821] (the check needs below 0.2), so the intervention did not change the mechanism and H1d stays open; s2: Insufficient data: with evict the L2 write-backs per 64 B stay at [0.823 0.824] (the check needs below 0.2), so the intervention did not change the mechanism and H1d stays open)"
- Short form: "Insufficient data". Rule: rule 1 of round 4, `DECISIONS-bwx8.md` line 349.
- One number: L2 write-backs per 64-byte line of asmread at 8 MiB with the evict step, `J["evict"]["rule1"]["s1"]["wb_evict"]` = {"2": 0.821, "41": 0.819}, `["s2"]["wb_evict"]` = {"2": 0.824, "41": 0.823} (the check needs below 0.2; without evict about 0.82).
- Folders: {"s1": {"ZC": ["bwx11-ZC-s1-20261115T084158Z"], "ZD": ["bwx11-ZD-s1-20261115T084528Z"]}, "s2": {"ZC": ["bwx11-ZC-s2-20261115T130613Z"], "ZD": ["bwx11-ZD-s2-20261115T130943Z"]}}.

### H3a (a kernel timer or host activity triggers the level switch), step XW, binary `bwx8` with host sampler
- Recorded overall verdict (verbatim), claim row `Report.claim("H3a")` `overall`: "H3a not supported in both sessions". `per_session.s1` = "rule 4: no listed key accompanies the switches; rule 5: K=read|S=8M|prev=oldread@8M: tied to the start of the target; process-start prediction rejected; K=read|S=8M|prev=read@1M: tied to the start of the target; process-start prediction rejected"
- Rule: rules 4 and 5 of round 2, `DECISIONS-bwx8.md` lines 268 and 269.
- One number: `J["switch_timing"]["XW_sampler"][s]["any_key_accompanies"]` = False (s1), False (s2): none of the 21 sampler keys in `[s]["keys"]` accompanies a switch. Switches examined (sum of `cpus[*].up_switches + down_switches` over both sessions): 236.
- Folders: {"s1": ["bwx9-XW-s1-20261115T052114Z"], "s2": ["bwx9-XW-s2-20261115T101125Z"]}.

### H7 (address of the runner's window record), steps YL (binary `bwx8`) and YP (binary `bwx10`)
- Recorded verdicts (verbatim), `J["YP"]["verdict"]`: s1 = "H7 supported (CPU 2: 5 of 5 pads match, CPU 41: 4 of 5 pads match)"; s2 = "undecided (CPU 2: 3 of 5 pads match, CPU 41: 4 of 5 pads match)".
- `J["YP"]["overall"]` = "not confirmed (s1: H7 supported (CPU 2: 5 of 5 pads match, CPU 41: 4 of 5 pads match); s2: undecided (CPU 2: 3 of 5 pads match, CPU 41: 4 of 5 pads match))"
- `J["YL"]["overall"]` = "not confirmed (verdicts of the cells that exist: cpu2/s1 undecided; cpu2/s2 undecided; cpu41/s1 undecided; cpu41/s2 undecided)"
- Claim row `Report.claim("H7")` `overall` = "YL: not confirmed (verdicts of the cells that exist: cpu2/s1 undecided; cpu2/s2 undecided; cpu41/s1 undecided; cpu41/s2 undecided). YP: not confirmed (s1: H7 supported (CPU 2: 5 of 5 pads match, CPU 41: 4 of 5 pads match); s2: undecided (CPU 2: 3 of 5 pads match, CPU 41: 4 of 5 pads match))"
- Rule: rules 1 and 2 of round 3, `DECISIONS-bwx8.md` lines 307 and 308. Claim `rule` field: "rules 1 and 2 of round 3 (rule 2 with the replaced statistic, see item 10)".
- One number (recorded): pads that match, from the verdict strings: session 1 CPU 2 5 of 5, CPU 41 4 of 5; session 2 CPU 2 3 of 5, CPU 41 4 of 5 (the rule needs at least 4 of 5 on both CPUs).
- Alternative number, supplementary (label "supplementary, defined after the data was seen"), `J["supplementary"]["yp_round1"]["summary_text"]["up"]["overall"]`: "ups, padded runs, both sessions: 122 of 136 ups lie within 1 window of a predicted window (89.7 %). 113 of 122 predicted windows with the process at the low level before show an up within 1 window (92.6 %)"
- Folders: {"s1": ["bwx10-YL-s1-20261115T070335Z", "bwx10-YP-s1-20261115T071937Z"], "s2": ["bwx10-YL-s2-20261115T112727Z", "bwx10-YP-s2-20261115T114329Z"]}.

## 7. Run facts

- Selection: `J["inventory"]["rows"]` (41 rows, one per result folder). Fields: `step`, `session`, `folder`, `processes`, `killed`, `failed`, `incomplete`, `x_rows`, `load_min`, `load_median`, `load_max` (1-minute load average at the launch of each process, from the "-- step" lines / `launches.txt`), `launches_with_load`, `first_launch_utc`, `last_launch_utc`.
- Folders: 41 (`len(rows)`; also `len(J["folders"])` = 41). Processes: 2946 (`sum(processes)`). Killed 0, failed 0, incomplete 0, failure rows (`x_rows`) 0.
- Load at launch over all steps: `min(load_min)` = 0.00, `max(load_max)` = 1.23. The maximum is in step bwx10-YF-s2-20261115T120146Z.
- "About 1.00 is the test itself, est." is a statement of `tackle-8mb-results.md` ("What ran"), not a JSON field. `load_median` of the folders with at least 40 processes is 0.70 to 1.00 (0.98 to 1.00 except steps H2 and ZC).
- CPUs: 2 and 41 (`CPUS` in `report_final.py` line 37). Step H2 also CPU 0. One process at a time, no root.
- Sessions: 2 per step, except the acceptance steps XEV, YA, ZA (session 1 only; `SESSION1_ONLY` in `report_final.py`). Session 2 at least 3 hours later, reversed CPU order (`DECISIONS-bwx8.md` line 247).

The four proving steps and step S4 (levels, trace):

| step | folder s1 | folder s2 | processes s1 + s2 | s1 UTC | s2 UTC | gap end s1 to start s2, h | load s1 | load s2 |
|---|---|---|---|---|---|---|---|---|
| S2 | bwx8-S2-s1-20261115T003207Z | bwx8-S2-s2-20261115T042130Z | 180 + 180 | 00:32:07 to 01:02:06 | 04:21:30 to 04:51:27 | 3.32 | 0.55 to 1.08 | 0.54 to 1.07 |
| ZS | bwx11-ZS-s1-20261115T100610Z | bwx11-ZS-s2-20261115T143012Z | 52 + 52 | 10:06:10 to 10:11:19 | 14:30:12 to 14:35:21 | 4.31 | 0.72 to 1.00 | 0.85 to 1.00 |
| ZN | bwx11-ZN-s1-20261115T092141Z | bwx11-ZN-s2-20261115T134554Z | 144 + 144 | 09:21:41 to 09:45:37 | 13:45:54 to 14:09:50 | 4.00 | 0.67 to 1.08 | 0.54 to 1.00 |
| H2 | h2-s1-20261115T063514Z | h2-s2-20261115T112456Z | 72 + 72 | 06:35:14 to 06:37:38 | 11:24:56 to 11:27:20 | 4.79 | 0.54 to 0.81 | 0.75 to 1.01 |
| S4 | bwx8-S4-s1-20261115T010216Z | bwx8-S4-s2-20261115T045137Z | 18 + 18 | 01:02:16 to 01:19:18 | 04:51:37 to 05:08:39 | 3.54 | 0.92 to 1.00 | 0.97 to 1.00 |

- All dates 2026-11-15. Binary digests (first 8 digits of sha256, from `tackle-8mb-results.md` "What ran"): `bwx8` f84be912, `bwx10` 22cbb1ee, `bwx11` f1215f9e.

## 8. Numbers of the task context that final8.json does not confirm as stated

| Context statement | What the data says | Where |
|---|---|---|
| ZS: "all counted sizes, 32 KiB to the largest" | ZS has 13 sizes from 1 MiB to 32 MiB. No 32 KiB. 11 sizes are counted. 1 and 8 MiB are printed and not counted, because the band was built from them. | `J["ZS"]["rule"][cell]["sizes"][size]["counted"]`; `DECISIONS-bwx8.md` lines 366, 367 |
| "old read costs about 2.67 at every size from 1 to 16 MiB" | In ZS, 37 of 44 old-read rows (1 to 16 MiB, 4 cells) lie within 0.02 of 2.671. 7 rows lie at 2.707 to 2.817 (2 MiB, 2.5 MiB, 3 MiB). Median 2.673. The recorded old-read check fails at 1, 3, 1, 2 of 9 checked sizes per cell. Safe wording: "about 2.67 at 8 MiB in all 4 cells (2.669 to 2.674), and within 0.02 of 2.671 in 37 of 44 rows from 1 to 16 MiB". | section 2; `J["ZS"]["rule"][cell]["oldread_fails"]` |
| "the new loop costs about 2.08 + 0.66 x r" | Fitted per cell: 2.089 + 0.658 r, 2.083 + 0.667 r, 2.079 + 0.646 r, 2.074 + 0.663 r. The fit is descriptive. The decision rule is the band 2.10 + 0.50 r - 0.05 to 2.10 + 0.69 r + 0.05. | `J["ZS"]["rule"][cell]` |
| "At 8 MiB r = 0.83, so the new loop costs 2.50 to 2.67" | r at 8 MiB in ZS: 0.820 to 0.827. 2.50 to 2.67 is `Report.cycles8()`, pooled over steps XCA, XCB, XCC, ZS and YC (2.496 to 2.671). ZS alone: 2.505 to 2.596. Line value 2.08 + 0.66 x 0.83 = 2.63 (est.). | section 2 |
| "10 of 11 counted sizes inside in each of the 4 cells" | Confirmed. The size outside is 32 MiB on CPU 2 (above the band) and 6 MiB on CPU 41 (below the band), in both sessions. The rule allows 2 outside. Recorded verdict: "H1c in its simple form is not contradicted". It is not "confirmed". | `J["ZS"]["overall"]` |
| "old read keeps 67 GB/s at both sizes (P1, margin 0.30 GB/s)" | Confirmed: 67.11 GB/s at 1 MiB, 67.05 to 67.09 GB/s at 8 MiB. 0.30 GB/s is the equivalence margin of the rule; the largest |d| + limit is 0.201 GB/s. | section 1 |
| "gain 27 % at 1 MiB; 3.35 to 6.75 % at 8 MiB" | Confirmed for kernel `read` (27.02 to 27.03 %; 3.35 to 6.75 %). For `asmread` at 8 MiB: 5.05 to 6.72 %. The results file says "0.2 to 6.7 %" because it also counts step H2. | section 1; `Report.gains8()` line 493 |
| ZN: "keep their 32 KiB rate at 8 MiB in 4 of 4 cells" | Confirmed for read_nop96 and read_nop128. Verdict wording is "H1 not contradicted by this kernel (loses more than 1.0 GB/s in 0 of 4 cells)". The third ZN kernel read_nop64 fails its prediction in 3 of 4 cells and its verdict is "not a slow kernel ... the contradiction rule does not apply". | section 3 |
| ZN supplementary "12 of 12 cells" | Confirmed. 4 of the 12 rows are old read (step S2), 8 are read_nop96 and read_nop128. The predicted range is wide for CPU 2 (for example 0.76 to 6.40 %), because it spans the low and the high level. | section 3 |
| H2: "on CPU 2 ... median gain 0.22 % and 0.17 %; on CPU 0 5.73 % and 5.71 %" | Confirmed. CPU 41: 3.17 % and 2.39 %, verdict "undecided". The original run itself used CPUs 0 and 2, and all its 12 new-read repetitions were low (67.36 to 67.71 GB/s), on CPU 0 too. In step H2 CPU 0 was high in 33 of 36 repetitions. So "CPU 0 is always high" is not supported; the original 0.94 % best pair is from CPU 2. | sections 4, 5 |
| "0.94 %" and "27 %" of the first measurement | Not in final8.json. Recomputed from `R/kernels-20261113T181222Z/one-thread.csv`: 0.94 % and 27.01 % (best of 12 repetitions per binary). | section 5 |
| H1b verdict "not confirmed" | Confirmed as the overall string. Per cell: 1 "H1b rejected", 3 "Insufficient data". | section 6 |
| H1d verdict "Insufficient data" | Confirmed. | section 6 |
| H3a "not supported" | Confirmed: "H3a not supported in both sessions". | section 6 |
| H7 "supported session 1, undecided session 2" | Confirmed for step YP. Step YL is "undecided" in all 4 cells. Both overall strings start with "not confirmed". | section 6 |
| "every step ran in 2 sessions ... on CPUs 2 and 41" | 38 of 41 folders are session pairs. XEV, YA, ZA (acceptance) ran in session 1 only. H2 also ran on CPU 0. Gap between the end of session 1 and the start of session 2 for the proving steps: 3.32 h (S2) to 4.79 h (H2). | section 7 |
| "load at launch 0.00 to 1.23" | Confirmed. | section 7 |
| "Not explained" items (0.66 cycles per SLC line, which part switches the levels, 2.67 cycles of old read) | No JSON field. They are statements of `tackle-8mb-results.md`, section "Which share is explained, and what stays open". | results file |

