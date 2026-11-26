# critic.md - completeness check of the seven fact sheets

## Short version

- I recomputed 467 numbers of the seven sheets from the raw files of boots F1 and F2, and six are wrong (section 2 gives the right values).
- Fourteen statements differ between two sheets, and section 1 names the sheet to follow for each (five more differ only in scope).
- Section 3 lists 20 questions that a reader of a CME memory performance page would ask and no sheet answers, ten of them answered here from the raw files.

## Words used here

- CME: the Arm C1-SME2 matrix engine unit. One per cluster, shared by two cores.
- F1: `/home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/results/bootF1/` (L3 on, hardware prefetchers on).
- F2: `/home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-012/results/bootF2/` (L3 on, hardware prefetchers off, CME rows only).
- Bracket time: the time between two clock reads in C around the kernel call or calls.
- Span time: the time between the two counter reads inside the kernel, after SMSTART and before SMSTOP.
- Outside-span time: bracket time minus span time.
- Chain load: one dependent load of the latency test. Round-trip baseline: the DUP+LASTB row (`cme-roundtrip`).
- Looped form: one kernel call per pass. Single-call form: all passes of a rep in one assembly call.
- Counting window: the interval between the counter start and the counter stop of one latency row. It encloses the bracket.
- "Plan rule": the fit rule of `follow-up-run-plan.md` line 271. A fit's intercept is void when the largest residual is over 2 % of the smallest pass time.

## Method

- Scripts, all run with `python3 -I`, in `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/scripts/`:
  - `critic_lib.py`: my own parser of the latency, bandwidth and mesh-counter CSV files. It shares no code with the sheets' scripts.
  - `critic_cross.py`: section 1 (items X1 to X9 in its output).
  - `critic_spot.py`: section 2. It compares 115 sheet statements (467 numbers) with values recomputed from the raw files.
  - `critic_extra.py`: section 3 (items E1 to E11 in its output).
- Row rule: the program's own `-best` rows (`cme-best`, `cme-roundtrip-best`, `cme-call-best`, bandwidth `rep=best`). For span and counters I take the first rep whose `ns_per_load` equals the best row. This is the same rule the sheets state.
- Bandwidth times: bracket ns = `total_bytes / (aggregate_GBps x 1e9)`. Span ns = `span_s`. Per pass = divided by the `passes=` value of the command line.
- Earlier runs (004 to 010) were opened only to check the numbers that open.md part (b) quotes when it names a gap.

---

## 1. Cross-check: statements that two sheets give differently

"Right" names the sheet to follow. "Both" means both are right for their own scope, and the page must state the scope.

| # | Topic | Sheet A | Sheet B | Recomputed from raw (script item) | Right |
|---|---|---|---|---|---|
| 1 | Evidence for the 2.000 GHz core clock | platform.md section 2: raw, `dmesg.txt` line 79, "2000.00 BogoMIPS" | method.md section 9: BogoMIPS is derived from the timer, so it is not evidence | `dmesg.txt` line 79 reads "value calculated using timer frequency.. 2000.00 BogoMIPS (lpj=10000000)". That is 2 x the 1 GHz timer. The measured ratio `cycles_per_load / ns_per_load` is 1.9999 to 2.0019 (F1) and 1.9994 to 2.0016 (F2) over 156 rep rows per boot. | method.md. Cite the measured ratio. Drop BogoMIPS. |
| 2 | Is the 2 GHz core clock raw or README only | open.md unit notes: "(README only)" | method.md, latency.md: measured from the counters | Same numbers as item 1. | method.md. The tag in open.md is wrong. |
| 3 | Core cache sizes (L1 32 KiB, L2 128 KiB, L3 256 KiB) | bandwidth.md "Sources": "(README only)" | platform.md section 4, latency.md: raw, F1 `sysinfo.txt` lines 101 to 104 | The four lines are in F1 `sysinfo.txt` at lines 101 to 104 (`size=32K`, `32K`, `128K`, `256K`). | platform.md. Raw on F1. F2 has no `sysinfo.txt`. |
| 4 | The 2 % fit rule and its percentages | bandwidth.md table 6: residual / measured value at that point | open.md A2 to A4: residual / smallest pass time | The plan (line 271) says "over 2 % of the smallest pass time". Under both rules the pass or fail verdict is the same in all 24 fits (X5). The percentages differ. Plan-rule values: F1 looped read 0.60 % bracket, 0.44 % span. F2 looped read 3.16 % and 1.17 %. Looped write 18.37 % and 33.68 % (F1), 17.78 % and 35.88 % (F2). Single-call read 19.09 % and 18.83 % (F1), 17.61 % and 17.77 % (F2). Single-call write 1.09 % and 1.12 % (F1), 0.81 % and 0.84 % (F2). No-fold read 1.52 % and 2.13 % (F1), 1.14 % and 0.20 % (F2). DSB ST write 5.02 % and 8.19 % (F1), 5.10 % and 8.19 % (F2). | open.md for the percentages. The intercepts and rates of bandwidth.md table 6 are right (all 24 recomputed). |
| 5 | Table 6 columns "Largest residual ns" and "At" | bandwidth.md table 6 | - | In 16 of the 24 rows the ns value is not at the size named in "At". "At" and the % column give the point of the largest relative residual. The ns column gives the largest absolute residual, which sits at another size. Example, F1 looped write, bracket: 27.89 ns is at 8 KiB. 17.62 % is at 4 KiB, where the residual is 26.75 ns. | Use the X5 output: largest absolute residual and its own size. |
| 6 | Do the L3 hit and miss columns feed a fit | l3events.md short version and section 7: a fit gives 29.8 ns est. for an L3-served load | open.md A7 and (c) 3, 4: "no fit or attribution reads the hit and miss columns" | The fit numbers themselves are right (A2: 29.833, 37.422, 44.432 ns, rms 0.089 ns. C1: 29.841, 37.407, 44.106 ns, rms 0.190 ns). The conflict is the rule. `common.h` lines 439 to 446 and the plan line 267 say no fit reads these columns until a control validates them. | open.md for the page's main text. The 29.8 ns est. may appear only inside a block labelled hypothesis, never as a headline. |
| 7 | "Stores are not waited for by the span" | bandwidth.md oddity 7 and "Where the write rate changes": stated as a fact | open.md A3 and (c) 9: hypothesis. method.md 1.2: whether the closing ISB waits is Insufficient data | The rows show the numbers (8 KiB looped write in-span 93.5 GB/s, single-call 52.2 GB/s, with DSB ST 44.2 GB/s). They do not show the mechanism. | open.md. Label it hypothesis. |
| 8 | Cause of the extra 220 ns of a call alone in its bracket | method.md 2.2: hypothesis, the first SMSTART after the counter-enable system call | open.md A6: two hypotheses (CME leaves a low-power state. First call after a flush, counter start or thread barrier) | The single-call bandwidth reps have no counter call (the program refuses `--perf` with `--cme`), and each timed call follows an untimed warm-up pass. They still spend 280.0 to 300.9 ns outside the span (read, later reps, both boots, X6). So the counter call cannot be the only cause. | open.md. Also see gap G6 for a new observation. |
| 9 | SLC size behind the 1 to 3 MiB level | latency.md "Words" and section 2: "the 5 MiB SLC" | platform.md section 10, open.md A11: 4 of 16 ways of each home node are locked as OCM (README only) | 12/16 of 5 MiB = 3.75 MiB est. left as cache (arithmetic on README-only facts). The F2 curve is flat from 1 to 3 MiB (42.125 to 43.666 ns) and rises at 4 MiB (47.328 ns). | platform.md and open.md. Say "the SLC, 3.75 MiB est. after the OCM ways are taken out (README only)". |
| 10 | What "inside the cluster" can be for a CME refill | latency.md section 2: hypothesis "the core's 128 KiB L2 holds the rest" at 384 KiB | ocm.md section 2, platform.md section 14 step 4: the core's L1 and L2 are not levels on the CME's path. A line can come by a snoop of a core's cache (README only) | No raw column separates the two. `cme-latency-dram-small-l3.csv` on F2 gives hit 0.6318 to 0.6375 per load at 384 KiB. | platform.md wording. Say "a snoop of a core's cache", not "the L2 holds the rest". Also: latency.md gap 2 says the L3 split is Insufficient data. l3events.md has those counts. |
| 11 | Kernel calls of an all-five OCM bandwidth pass | ocm.md section 6: "20,480 lines (all five) in one kernel call" | method.md 4.2 and section 7: five kernel calls per pass (one per region). The write rep is 40 calls | `bandwidth.c` lines 314 to 323 loop over the segments and call the kernel once per segment. | method.md. See section 2, item W5, for the numbers this changes. |
| 12 | `bracket_overhead_ns` | open.md A6: "39.0, comment line of each CME latency file" | method.md 2.2, ocm.md section 2: 39.0 in 23 files and 40.0 in one | F1: 39.0 in all 12 CME latency files. F2: 39.0 in 11, 40.0 in `cme-latency-ocm-region1.csv` (X1). | method.md and ocm.md. |
| 13 | Outside-span time of a 1 KiB read call, F2 | bandwidth.md table 9: 83.1 to 88.0 ns | open.md A4: 83.1 to 88.1 ns | Reps: 87.602, 88.047, 83.069 ns (from `span_s`, 1 ns print step). | bandwidth.md (88.0). |
| 14 | Largest outside-span time of a looped call | open.md A4 and (c) 1: "up to 101.8 ns" | bandwidth.md oddity 11: 75.8 to 106.2 ns at 16 to 256 KiB, 118.5 to 398.0 ns at 1 to 32 MiB | 101.8 ns is the largest of the read best reps only. Over all reps and kernels of the sweep: 76.0 to 106.2 ns (F1) and 75.8 to 105.6 ns (F2) at 16 to 256 KiB. 118.5 to 357.8 ns (F1) and 120.5 to 398.0 ns (F2) at 1 to 32 MiB (X7). | bandwidth.md. |

Same statement, different scope (both right, no change needed):

- `cme-call` best: 124.547 to 125.547 ns (latency.md, the 6 plain DRAM files). 124.5 to 125.6 ns (ocm.md, the 14 OCM files). 124.516 to 125.531 ns (open.md, F1's 12 files). Over all 24 files: 124.516 to 125.609 ns (X3).
- `cme-call` span: 61.000 ns in 17 of 18 reps (latency.md, 6 files). 61.000 to 61.250 ns (open.md, all files). Over all 72 reps: 68 read 61.000 ns, the largest is 61.250 ns (F1).
- Round-trip CME cycles per step: 42.0039 to 42.0065 (latency.md, 6 files). 42.0039 to 42.0068 (platform.md, 24 files). Both recomputed.
- Backing lines: method.md counts 98 `hugetlb` and 14 `ocm` per boot (47 + 7 `# size=` lines of the latency files plus 51 + 7 `# backing=` lines of the bandwidth files, CME files only). platform.md counts only `# backing=` lines of every CSV: 71 and 15 on F1 (core files included), 51 and 7 on F2 (X2).
- Single-call outside-span time, F1: open.md A6 gives 281 to 295 ns and 349 to 405 ns (read), 372 to 401 ns and 475 to 522 ns (write) for 48 to 256 KiB. From `span_s` I get 282.5 to 294.4, 348.5 to 404.0, 371.8 to 401.6 and 476.3 to 521.2 ns. The differences are at most 1.5 ns (rounding of a 3-decimal GB/s value). bandwidth.md table 7 (4 to 256 KiB) recomputes exactly: use it.

Terms that differ between sheets for one thing (pick one for the page):

- "span" (method.md, latency.md, open.md) and "in-span" (bandwidth.md, l3events.md, ocm.md).
- "bracket minus span" (method.md), "outside-span interval" (open.md), "outside-span time" (bandwidth.md), "outside the span" (ocm.md).
- The timed walks of the walked-once rows are "reps" in latency.md and "passes" in ocm.md and l3events.md. In bandwidth.md a "pass" is one walk over the buffer and a "rep" is a group of passes.
- platform.md numbers the home nodes "HN-S #0 to #4" as the mesh map does. That index is not the OCM region number. Region 0 = node id 88 = HN-S #0 at (1,3). Region 1 = 160 = HN-S #3 at (2,4). Region 2 = 216 = HN-S #1 at (3,3). Region 3 = 288 = HN-S #4 at (4,4). Region 4 = 344 = HN-S #2 at (5,3) (F1 `sysinfo.txt` lines 489 to 551, node id decoded as x = id >> 6, y = (id >> 3) & 7).

---

## 2. Spot-check

Coverage (`critic_spot.py`): 115 statements, 467 numbers.

| Sheet | Statements checked | What was checked |
|---|---|---|
| method.md | 19 | row counts per mode label, rep and best row counts per kernel, clock ratios, bracket minus span on the OCM passes, `elapsed_s` error, mesh-counter row counts |
| platform.md | 7 | prefetch refill range over 104 rows per boot, command counts, uptime stamps, node request ranges |
| latency.md | 23 | 13 CME footprint rows of both boots (best, span, cycles, five counters, rep values), counter sums, 5 core rows |
| l3events.md | 13 | counter checks of section 3, 5 footprint rows, ratios to the plain rows, the correlation, the straight line, fits A2 and C1 |
| bandwidth.md | 21 | tables 1, 2, 3, 5, 7, 9, oddities 1 to 4 and 8 |
| ocm.md | 25 | all per-region bests of both boots, counters, the F1 correlation and line, OCM bandwidth, core twins, tables T6 and T7 |
| open.md | 7 | the A8 fit, A1, A3, A6, A13 |

Also checked by shell: `sha256sum -c` gives 88 of 88 OK (F1) and 30 of 30 OK (F2). `dmesg.txt` lines 37, 154 to 156, 286 and 319 (F1) and 203 and 236 (F2) hold what platform.md says. The log line numbers of method.md section 7 hold (F1 lines 85 to 156, F2 lines 4 to 75, 15 commands under `cmn` per boot). The 24 fits of bandwidth.md table 6 recompute (intercept and rate). The earlier-run numbers of open.md part (b) recompute: 21.417, 71.740, 71.738 ns (address-order rows), 40.700 ns (boot B, 256 KiB), 42.516 to 43.609 ns (boot E `cme-call` best, 21 files), 63.731 to 63.865 and 61.971 GB/s (run 004 `cme-write`).

Wrong numbers found:

| # | Sheet, place | Sheet says | Right value | Source |
|---|---|---|---|---|
| W1 | open.md B8 | "139 `--cme` commands in the `log.txt` files of runs 004 to 012" | 278 commands: 33 (run 004), 21 each in runs 005, 006, 007, 008 and 010, 70 (F1), 70 (F2). 138 of them are in runs 004 to 010. All 278 name CPU 2. Folder 009 does not exist. | `log.txt` of each run, lines with `--cme` |
| W2 | open.md A2, title | "A CME store of 64 bytes takes 2.4 times as long as a load" | 2.31 times on F1 (121.107 / 52.342 GB/s) and 2.33 times on F2 (122.237 / 52.464 GB/s), span rates at 16 KiB. The "2.45" in the body is the store's time in core cycles per 64 B, not the ratio. | `cme-bandwidth-l1-asmpasses.csv`, best rows, `span_GBps` (X9) |
| W3 | open.md A4, table | 1 KiB read call, F2: "83.1 to 88.1 ns" | 83.1 to 88.0 ns (reps 87.602, 88.047, 83.069 ns) | `cme-bandwidth-call-cost.csv`, `cme-read`, reps (E5) |
| W4 | open.md A6 | "`bracket_overhead_ns=39.0`, comment line of each CME latency file" | 39.0 ns in 23 of the 24 files, 40.0 ns in F2 `cme-latency-ocm-region1.csv` | comment line 3 of each file (X1) |
| W5 | ocm.md section 6 and table T5 | "An all-five read call spends 677 to 776 ns outside its span". "A write call spends 439 to 471 ns ... (one of the 8 calls of a rep)" | These are per pass of five kernel calls. Per kernel call: 135.5 to 155.2 ns (F1) and 136.4 to 154.1 ns (F2) for the all-five read. 87.8 to 94.3 ns (F1) and 89.9 to 93.4 ns (F2) for the write. A write rep is 40 kernel calls. The "38 to 40 us" and "42 to 43 us" are per pass. The one-region read values (328 to 485 ns per call) are right. | `cme-bandwidth-ocm-all5.csv`, `cme-bandwidth-ocm-write.csv`, reps. `bandwidth.c` lines 314 to 323 |
| W6 | latency.md section 2, last claim | "Bracket minus span is 0.001 to 0.041 ns per load in all F2 footprint rows" | True for the best reps. Over all rep rows the range is 0.000 to 0.041 ns. The 32 MiB `cme-fresh2` row reads 71.116 ns in both columns. | `cme-latency-dram-large.csv` (E1) |

Smaller defects (no wrong measurement):

- open.md short version says "Thirteen observations" and "seven kinds of row". The body has 17 items in part (a) (A1 to A13 are observations, A14 to A17 are things not measured) and 10 rows in part (b) (5 with an earlier run, 5 with none).
- ocm.md section 1 points to "section 6" for the mesh counters. They are in section 7.
- bandwidth.md table 4 intro has a stray backslash before "The first table".
- ocm.md section 7 gives the two all-node events of the flushed DRAM command for F1 only (3,054,121 and 2,246,799). F2 reads 2,490,045 (`hns_mc_reqs_local_all`) and 1,687,164 (`hns_cache_miss_all`).

Everything else checked matches the raw files to the printed digit.

---

## 3. What a reader would ask that no sheet answers

"Raw" means I computed the answer from the named file. "Insufficient data" names what would resolve it.

### Missing comparisons that the raw files answer

**G1. One table of what a CME chain load costs by where the line comes from, DRAM-backed rows and OCM together.** latency.md and ocm.md never meet. Boot F2 (prefetchers off), best bracket, span of the best rep (E7):

| Row | File | Bracket ns | Span ns | Above the 21.005 ns round-trip baseline | Outer refills per load |
|---|---|---|---|---|---|
| CME L1 (4 to 64 KiB walked many times) | `cme-latency-dram-small.csv` | 21.015 to 21.240 | 21.011 to 21.236 | 0.010 to 0.235 ns | 0.0000 |
| Inside the cluster (256 KiB walked many times) | same | 32.779 | 32.775 | 11.774 ns | 0.0030 |
| Outside the cluster, 1 MiB walked once | `cme-latency-dram-large.csv` | 42.125 | 42.107 | 21.120 ns | 0.8134 |
| Outside the cluster, 3 MiB walked once | same | 43.666 | 43.659 | 22.661 ns | 0.9311 |
| OCM, all five regions, every line flushed first, every line | `cme-latency-ocm-all5-dense.csv` | 45.546 | 45.532 | 24.541 ns | 1.0000 |
| DRAM model, 8 MiB, every line flushed first | `cme-latency-dram-flushed.csv` | 71.714 | 71.712 | 50.709 ns | 1.0000 |
| 32 MiB walked once | `cme-latency-dram-large.csv` | 71.068 | 71.067 | 50.063 ns | 0.9953 |

- So on F2 an OCM load is 1.9 to 3.4 ns slower than the 1 to 3 MiB rows and 26.2 ns faster than the flushed 8 MiB row.
- Limit: the OCM rows use 4 KiB pages and a flush. The 1 to 3 MiB rows use 2 MiB pages, no flush, and count 0.81 to 0.93 outer refills per load, not 1.00.

**G2. The measured rates against the documented limits.** platform.md section 14 has the limits and bandwidth.md has the rates. No sheet puts them side by side.

- Documented: at most 2 loads or stores per cycle (Arm C1-Nano Software Optimization Guide 109590, section 2.33.3). The LLVM model has one CME load pipe and one CME store pipe (`refs/AArch64SchedC1Nano.td` lines 84 to 86).
- Measured read, single-call form, 4 to 48 KiB: 54.45 to 65.82 B per cycle on F1 and 55.40 to 66.18 on F2. That is 0.85 to 1.03 vectors of 64 B per cycle, or 15.5 to 18.8 cycles per 1 KiB loop iteration of 23 instructions (E8).
- Measured write, single-call form, 4 to 48 KiB: 25.72 to 26.86 B per cycle. That is 2.38 to 2.49 cycles per 64 B vector on both boots.
- Hypothesis: the read rate is one vector load per cycle, the one-load-pipe limit of the LLVM model, and half of the "two wide" figure. The read kernel also runs one EOR per vector, so the rows cannot separate the load limit from the fold work. A read kernel with no EOR in the loop would confirm or reject it.

**G3. Core against CME inside the L1 with the per-call cost removed.** bandwidth.md table 3 compares the core with the looped CME form only. At 16 KiB on F1 (E9):

- Read: core 56.085 GB/s, CME single-call 120.132 GB/s, 2.142 times.
- Write: core 30.608 GB/s, CME single-call 52.098 GB/s, 1.702 times.
- Files: `bandwidth-dram-1core.csv` and `cme-bandwidth-l1-asmpasses.csv`, best rows.

**G4. Latency against bandwidth: how many loads overlap in a streaming read.** est., hypothesis. Chain load time divided by the time per 64 B line of the read row at the same footprint and boot (E6):

| Boot | Footprint | Chain load ns | Read GB/s | ns per 64 B line | Ratio (lines in flight, est.) |
|---|---|---|---|---|---|
| F2 | 256 KiB | 32.779 | 41.866 | 1.529 | 21.4 |
| F2 | 2 MiB | 42.960 | 32.758 | 1.954 | 22.0 |
| F2 | 32 MiB | 71.068 | 17.699 | 3.616 | 19.7 |
| F1 | 256 KiB | 51.100 | 41.562 | 1.540 | 33.2 |
| F1 | 2 MiB | 56.103 | 36.921 | 1.733 | 32.4 |
| F1 | 32 MiB | 70.482 | 36.583 | 1.749 | 40.3 |

- On F2 the ratio is 19.7 to 22.0 at all three footprints. Hypothesis: without the prefetcher the CME keeps about 20 line requests in flight. This answers the question open.md A17 leaves open, as an estimate only. The chain load includes the 21.005 ns round trip, which a streaming read does not pay, so the ratio is an upper bound. With the baseline subtracted the F2 ratios are 7.7, 11.2 and 13.8 (est.).

**G5. Does a new streaming span start with an empty CME L1?** latency.md oddity 5 has the observation. open.md does not list it, and bandwidth.md does not use it.

- F2, walked many times, 4 to 64 KiB: every timed rep counts 0.99 to 1.02 inner read refills per line of the chain, in all 21 rep rows, although two untimed walks ran before the first rep (`cme-latency-dram-small.csv`, `cme_l1d_refill_inner_per_load x loads / lines`, E2).
- The looped bandwidth rows say the opposite for calls back to back: the fitted span rate of the looped read at 4 to 24 KiB is 134.7 GB/s (F1) and 132.9 GB/s (F2), an L1 rate (both fits pass the plan rule).
- Difference between the two cases: a latency rep has a counter stop, a print and a counter start (system calls) before its call. A looped bandwidth pass has none.
- Insufficient data for the cause. A latency run without `--perf`, or a rep loop with no system call between the reps, would show whether the refills go away.
- Hypothesis, with a consequence for the page: the 0.010 to 0.235 ns "above the baseline" at 4 to 64 KiB is this once-per-rep refill, not the cost of an L1 hit. Support: the excess divided by the refills is 10.0 to 15.1 ns per refill (latency.md 2d), close to the 11.8 to 15.2 ns per refill of the 96 to 384 KiB rows.

**G6. Does the CME's cycle counter run for the whole counting window?** New observation, no sheet has it. Core cycles minus CME cycles per counting window (`cycles_per_load - cme_cycles_per_load`, times `loads`):

| Rows | F1 | F2 |
|---|---|---|
| OCM passes of 64 loads, one call per window (35 rows per boot) | 554 to 663 cycles, median 591 | 556 to 706 cycles, median 583 |
| OCM passes of 320 loads, one call per window (7 rows per boot) | 566 to 649 cycles | 586 to 674 cycles |
| `cme-call` rows, 64 calls per window (36 rows per boot) | 571 to 632 cycles, median 599 | 567 to 658 cycles, median 599 |

- The gap is the same per window with 1 call or with 64 calls: about 590 to 600 cycles, which is 295 to 300 ns at 2 cycles per ns.
- So the CME counter counts through the outside-span time of calls that run back to back, and it misses about 300 ns once per window.
- This is close to the 286 to 292 ns that a call alone in its bracket spends outside its span.
- Hypothesis: the CME's clock, or its counter, is not running from the counter start until the first streaming entry of the window. It supports reading the 220 ns of open.md A6 as a cost paid once per window, not per call. Check: (4,065 ns - 286 ns) / 63 = 60.0 ns per later call (est.).
- Longer rows cannot test this: the core column prints 2 decimals, which is 82 cycles or more per window from 8,192 loads up.
- Would settle it: the CME power controller status read before and after a lone call, or a stamp before SMSTART.

**G7. Does the prefetcher add mesh traffic?** ocm.md gives the per-node counts of the flushed 8 MiB DRAM command but not the comparison. Sum of the five home nodes, whole command (`cmn-counts.csv`, label `cme-dram-flushed-8M-cpu2`, E11): 7,061,170 requests on F1 and 4,525,175 on F2. That is 53.87 and 34.52 requests per line of the 131,072-line buffer, 1.56 times. The counts cover the fill, the warm-up walks and the flushes too. The command lived 70.428 ms on F1 and 102.733 ms on F2.

**G8. One repeatability table.** The page needs an error bar and no sheet gathers it. The raw files hold three kinds of repeat:

- 12 copies per boot of the round-trip baseline (21.005 ns in all 24 files) and of `cme-call` (124.516 to 125.609 ns).
- Two sweeps per boot of every DRAM-backed latency footprint (plain and `-l3`): within 1.0 % at all 23 footprints on F2, at 20 of 23 on F1, worst 5.6 % (16 KiB on F1) (l3events.md section 5).
- Two files per boot with the same looped rows: the 16 KiB read differs by 1.6 % (F1) and 5.3 % (F2) and the 4 KiB write span by 12 % on F1 (bandwidth.md oddities 5 and 10).
- No boot was repeated: Insufficient data for the boot-to-boot spread.

**G9. Region number against home node index.** See the last bullet of section 1. The page needs one table with region, node id, HN-S index, position and mesh steps. ocm.md T1 has four of the five columns.

**G10. Which footprints have both chain kinds.** None. "Walked many times" stops at 384 KiB and "walked once" starts at 512 KiB. So the F1 drop of 10.594 ns between 384 KiB and 512 KiB (latency.md oddity 1) cannot be assigned to the footprint or to the chain kind. Insufficient data: one footprint run with both kinds.

### Missing measurements (Insufficient data)

**G11. What the 21.005 ns (42 cycles) of the round-trip baseline is made of.** No sheet splits it into the core-to-CME issue, the CME's execution and the return to the core. The LLVM model gives 2 cycles for a streaming vector load (platform.md section 14). Insufficient data: an RTL waveform of one DUP+LASTB step, or the interface timing in the C1-SME2 TRM (not on this host). The page must say that the baseline is a register transfer cost and that no row gives a CME load-to-use time without it.

**G12. Load-to-use latency that stays in the vector registers.** Every latency row returns the value to the core through LASTB. Insufficient data: no kernel measures a dependent load chain inside the CME.

**G13. OCM against DRAM bandwidth, like for like.** The OCM read rows are one pass after a flush. Every DRAM bandwidth row runs 2 to 4,096 passes after a warm-up pass with no flush. Insufficient data: DRAM rows with `--flush-before --passes 1` at 256 KiB and 1,280 KiB.

**G14. Copy rows.** `cme-copy` exists only in the looped sweep (16 KiB to 32 MiB). There is no single-call copy, no copy at 4, 8 or 24 KiB, and no copy on OCM. Insufficient data.

**G15. Access kinds that were not run.** Loads and stores of the ZA array, gather loads, vectors that are not 64 B aligned or that cross a page, loads with a partial predicate (other than the 8-byte chain load), stores followed by loads of the same line. Insufficient data: no kernel in `cme_kern.S` does any of these.

**G16. Translation cost.** The CME rows carry no TLB counter. The OCM rows use 4 KiB pages and the DRAM rows 2 MiB pages. The one-line-per-4-KiB-page shape touches 64 pages per region and 320 over all five, more than the 24 entries of the CME's TLB (README only). The two OCM shapes agree within 0.212 ns in the span on F2 (45.744 and 45.532 ns), but both walk the pages in random order, so this does not bound the cost. Insufficient data: the same OCM rows on a 64 KiB or 2 MiB mapping on a prefetchers-off, L3-on boot.

**G17. Chip time against silicon.** All times are chip time at a measured 2.000 cycles per ns. No sheet says whether the silicon target clock is 2 GHz. Insufficient data: the design's clock specification.

**G18. A CME write rate with a known destination level.** bandwidth.md and open.md A1 show the step from about 52 to about 41 GB/s between 256 KiB and 1 MiB with no counter. The OCM write (30.659 and 30.994 GB/s) is the only write row under the mesh counters. Insufficient data, as open.md A1 says. For the page: no write row can be labelled "to the L3", "to the SLC" or "to DRAM".

### Missing definitions

**G19. Terms used in the sheets and defined in none of them.** The page needs one line each:

- ISB (the instruction that makes the core finish what is in flight before the next instruction). Used in method.md, bandwidth.md, open.md.
- DSB ST and DSB SY (barriers that wait for stores, or for all memory accesses, to complete). method.md explains DSB ST once. DSB SY is not explained.
- PMU (the core's performance counters), TRM (Arm Technical Reference Manual), SOG (Arm Software Optimization Guide).
- Snoop (a request to another cache in the cluster for a line it holds).
- PPU, PWPR, PWSR (the power controller and its registers) in platform.md.
- `nohz_full` and SCHED_FIFO in platform.md section 3.
- RN-F, SBSX, HN-I: platform.md gives short forms. The page needs "cluster port", "bridge to memory" and nothing more.
- "Fold" (the XOR of all loaded words into one value): bandwidth.md and method.md explain it in the kernel table only.

**G20. A "numbers to quote" list.** Each sheet says which of its rows to quote, in different places. No sheet gives one list. From the sheets, and consistent with sections 1 and 2:

- Round-trip baseline: 21.005 ns (both boots, 24 files).
- CME L1 chain load, F2: 21.015 to 21.240 ns (4 to 64 KiB).
- Inside the cluster, F2: 32.779 to 35.979 ns (96 to 384 KiB).
- OCM, F2, span: 43.453 to 44.391 ns (regions 0 to 2), 47.266 and 47.734 ns (regions 3 and 4), 45.532 ns (all five, every line).
- DRAM model, F2: 71.714 ns (8 MiB, every line flushed first). Emulator memory model, not silicon.
- L1 read, single-call form: 108.9 to 131.6 GB/s (F1), 110.8 to 132.4 GB/s (F2), 4 to 48 KiB.
- Write, single-call form: 51.4 to 53.7 GB/s, 4 to 256 KiB, both boots.
- Read above the L1, looped form: 41.4 to 43.7 GB/s at 96 to 256 KiB (F1), 36.6 to 36.9 GB/s at 1 to 32 MiB (F1), 17.7 GB/s at 32 MiB (F2).
- OCM read: 33.6 to 39.8 GB/s per region (F1), 27.7 to 33.9 GB/s (F2). OCM write: 30.7 and 31.0 GB/s.
- Not to quote as results: the fitted 29.8 ns est. of l3events.md (section 1, item 6), the looped write's fitted intercept (void by the plan rule), the single-call read's fitted rate (void), "a CME call costs 186 ns" without its conditions (open.md (c) 2).
