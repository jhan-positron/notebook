# Progress file: why the new read kernel gains so little at 8 MiB

This file replaces progress messages. Newest entry last. Terms are those of `tackle-8mb-handoff.md`.

## 2026-11-15 04:10 UTC, round 1 (second agent)

- Read the handoff, the design, the rules file and the decisions file.
- Slack #phoenix-crb: no block announced. `STOP_AT=none`.
- One read-only login at 03:56 UTC for host facts (`tackle-8mb-analysis/h3/hostfacts-20261115T0403Z.txt`). Load at that time: 0.00.
- Session 1 traces, new observation (one session, not confirmed): the up-switches of the load-only loops sit at fixed times after process start (60 s runs: 6.3 s, then every 6.9 or 7.2 s; 9.6 s runs: 3.9 s). The 1 MiB runs and old read do not switch. Details and the hypothesis H3a (a kernel timer on the worker's CPU) are in `DECISIONS-bwx8.md`, section "Second agent".
- Round 2 is defined in `DECISIONS-bwx8.md` (steps `XEV`, `XW`, `XCA`, `XCB`, `XCC`, `XN`, `XF`, with decision rules). Its tools are being built and reviewed by sub-agents (local only).
- Next: session 2 of `B6W`, `S2`, `S4` at 04:20:18 UTC. Then session 1 of round 2.

## 2026-11-15 05:15 UTC, session 2 of `B6W`, `S2`, `S4` done and analysed

- Ran: session 2, 04:20:25 to 05:09:39 UTC, `ssh` status 0. 202 processes, 738 trials, 0 rejected, 0 disturbed (host limit 3.0 involuntary context switches per second). Load at launch: 0.00 to 1.07 (`launches.txt` of the three folders). Folders: `results/bwx8-B6W-s2-20261115T042025Z`, `results/bwx8-S2-s2-20261115T042130Z`, `results/bwx8-S4-s2-20261115T045137Z`.
- Analysis of both sessions: `tackle-8mb-analysis/s12-summary.txt` and `.json`.
- Confirmed on both CPUs (same sign in both sessions, repeatability rule of the design):
  - P1: old read at 8 MiB equals old read at 1 MiB inside the 0.30 GB/s margin in all four CPU/session cells (largest difference plus limit 0.201 GB/s).
  - P2: `read` and `asmread` lose 13.65 to 15.92 GB/s from 1 MiB to 8 MiB (cell medians).
  - The new loop carries 100.1 to 100.3 % of the lost advantage. The old loop carries -0.1 to -0.3 %.
  - New minus old at 8 MiB is positive in all four cells: +3.91 and +4.01 GB/s on CPU 2, +2.25 and +4.53 GB/s on CPU 41 (gains 5.83, 5.97, 3.35, 6.75 %). At 16 MiB it is negative in all four cells (-1.07 to -1.35 GB/s).
- Not explained yet: which limit holds the new loop near 67 to 72 GB/s at 8 MiB, why it is below old read at 16 MiB, and what switches the two levels.
- Session 2 sustained traces (`S4`): the level switches again sit at fixed times after process start. Falls: windows 16, 42, 69, 95, 122, 148, 168, 194. Ups: window 21 and 44 as in session 1, and often 1.2 to 1.5 s after a fall. One process (`asmread`, CPU 41) stayed low for 60 s.
- Next: session 1 of round 2 (host sampler, counters split by level, onset test, core-limit family, finer sizes) as soon as its tools pass review.

## 2026-11-15 06:00 UTC, round 2 session 1 running; first results

- Running since 05:21 UTC: `XW`, `XCA`, `XCB`, `XCC` done, `XN` and `XF` in progress. Load at launch in `XW`: see `results/bwx9-XW-s1-20261115T052114Z/launches.txt`.
- H3a (kernel timer on the worker's CPU) is not supported: no sampler key accompanies the switches (`tackle-8mb-analysis/h3/xw-s1-watch.txt`).
- New finding: the switches are locked to the index of the runner's own window record. Hypothesis H7: the level depends on the address of that record. Round 3 tests it with a controlled change (`--rec-pad`) and with other window lengths.
- New finding (counters, session 1): load-only loops at 8 MiB have 0.30 to 0.37 first-level cache long misses per line, old read 0.007. Hypothesis H1b: these misses limit the new loop at 8 MiB. Round 3 tests it with software prefetch kernels.
- Round 3 is defined in `DECISIONS-bwx8.md`. Its tools are being built and reviewed (local only).
- Next: finish round 2 session 1, read `XN` and `XF`, build `bwx10` on CRB, run round 3 session 1, then the second sessions (round 2 not before 3 hours after its session 1 end).

## 2026-11-15 06:45 UTC, round 2 session 1 complete, H2 session 1 done

- Round 2 session 1 ran 05:21:14 to 06:34:47 UTC, `ssh` status 0, all 7 steps complete. Load at launch 0.00 to 1.15 (`launches.txt` of the `bwx9-X*-s1-*` folders). Session 2 of round 2 may start at 09:34:47 UTC.
- `XN`, session 1 (`tackle-8mb-analysis/h3/XN-s1-cells.txt`), cell medians in GB/s:
  - 32 KiB: `asmread` 132.7, `read_nop16` 132.4, `read_nop32` 118.8, `read_sparse` 133.1.
  - 1 MiB: all four 85.2 to 85.5.
  - 8 MiB: all four 67.3 to 67.7 on CPU 2 and 68.9 to 71.4 on CPU 41. The 95th-percentile rates are 70.7 to 71.5, except `read_nop16` (67.4 on CPU 2, 69.1 on CPU 41), which never reached the high level.
  - Reading by rule 6: part (c) holds (spread at 8 MiB is 3 % of the spread at 32 KiB). Part (a) fails for `read_nop16` on both CPUs in session 1. No kernel of this family is slower than 118 GB/s at 32 KiB, so part (b) (a slow kernel keeps its rate) is not tested. Round 3 or 4 needs a slower load-only kernel.
- `XF`, session 1 (`h3/XF-s1-cells.txt`): the `read` rate falls step by step with the size: 85.2 (1.5 MiB), 81.6 to 82.7 (2 MiB), 77.5 to 79.0 (2.5 MiB), 74.6 to 77.1 (3 MiB), 69.3 to 74.3 (5 MiB), 72.6 to 74.2 (6 MiB), 66.3 to 67.7 (12 MiB), 64.1 to 64.4 (24 MiB), 63.5 to 63.7 (32 MiB), 53.2 to 53.8 (64 MiB). Old read stays at 66.1 to 67.1 from 2 to 12 MiB and is 64.8 to 65.9 at 32 MiB. So 8 MiB is the size where the falling curve of the new loop meets the flat curve of the old loop. There is no step at 8 MiB.
- H2, session 1 (`results/h2-s1-20261115T063514Z`, `h3/h2-s1.txt`, 72 processes, 06:35 to 06:37 UTC): the original program on CPU 2 gave 36 of 36 new-read repetitions at the low level, median gain 0.22 % (original: 0.51 to 0.94 %). On CPU 0 it gave 33 of 36 at the high level, median gain 5.73 %. On CPU 41: 21 low, 7 between, 8 high, median gain 3.17 %. So the original small gain is reproduced on CPU 2, and the same program gives 5.7 % on CPU 0 today. The original run had the low level on CPU 0 too.
- Open: what selects the level (CPU, occasion, record address). Round 3 tests the record address.
- Next: build `bwx10` on CRB when its review ends, run `YA`, then round 3 session 1. At 09:35 UTC: session 2 of round 2 and of H2.

## 2026-11-15 07:05 UTC, `bwx10` built and accepted, round 3 session 1 started

- `bwx10` (software prefetch kernels, `--rec-pad`, `--hot-copy`) is built on CRB and accepted (listing check, self-test, trace step `YA`). Details in `DECISIONS-bwx8.md`.
- Round 3 session 1 runs since 07:04 UTC: `YL` (window length), `YP` (record pad), `YC` (counters of the prefetch family), `YF` (prefetch family). Expected end about 08:45 UTC.
- Then: session 2 of round 2 and of H2 at 09:35 UTC, session 2 of round 3 three hours after its session 1 end.

## 2026-11-15 07:45 UTC, round 3 session 1: first results (`YL`, `YP`, `YC`)

- H7 is supported in session 1 by two tests. `YL`: the switches keep their window index when the window length changes (100, 300, 1000 ms), and a single 30 s window shows no switch. `YP`: moving the record array by P bytes moves the switch windows by P / 80 for all 5 pads on both CPUs.
- `--hot-copy` (the loop does not touch the record inside a window): 3 of 4 processes show no switch, one still does. So the access at the window end is what moves the level.
- H1b (the count of first-level cache misses limits the new loop) is not supported: software prefetch removes 94 to 99 % of the misses at 1 MiB, and the rate falls from 85.2 to 77.4 GB/s. Details and numbers: `DECISIONS-bwx8.md`.
- New hypotheses H1c and H1d and round 4 (clean lines by `--evict-mb`, slow load-only kernels, kick map) are recorded in `DECISIONS-bwx8.md`. The tools are being built (local only).
- `YF` still runs (ends about 08:35 UTC).

## 2026-11-15 08:30 UTC, round 3 session 1 complete

- Ran 07:03:35 to 08:26:08 UTC, `ssh` status 0, steps `YL`, `YP`, `YC`, `YF` complete. Load at launch 0.06 to 1.07. Session 2 of round 3 may start at 11:26:08 UTC.
- `YF`, session 1 (`tackle-8mb-analysis/h3/YF-s1-cells.txt`), cell medians in GB/s (CPU 2 / CPU 41):
  - 32 KiB: `asmread` 132.5 / 132.5; the four prefetch kernels 101.6 to 105.4; `read_1pl` 323.4 / 324.1.
  - 1 MiB: `asmread` 85.24 / 85.24; prefetch kernels 77.44 to 77.50; `read_1pl` 93.19 / 93.18.
  - 8 MiB: `asmread` 67.78 / 71.49 (95th percentile 71.01 / 71.55); `read_pf256` 65.22 / 66.52; `read_pf512` 64.40 / 66.10; `read_pf1024` 65.96 / 67.47; `read_pf2048` 62.60 / 58.49; `read_1pl` 57.00 / 57.88.
  - 16 MiB: `asmread` 65.45 / 65.91; prefetch kernels 62.95 to 67.51; `read_1pl` 53.86 / 54.71.
- Reading by rule 3 of round 3: no prefetch kernel is faster than `asmread` at 1 MiB or 8 MiB, although the prefetch removes 94 to 99 % of the first-level cache misses at 1 MiB and 47 to 48 % at 8 MiB (`YC`). H1b is not supported in session 1.
- What the family shows instead (hypothesis H1c, to be confirmed in session 2): the rate into the first-level cache has a ceiling. From L2 the best rate is 93.2 GB/s (`read_1pl`, one load per line) and 85.2 GB/s for the 4-loads-per-line loop. The software prefetch costs 7.8 GB/s at 1 MiB.
- Next: build `bwx11` and run round 4 session 1 when its tools pass review. 09:35 UTC or later: session 2 of round 2 and of H2. 11:26 UTC or later: session 2 of round 3.

## 2026-11-15 08:45 UTC, `bwx11` built and accepted, round 4 session 1 started

- `bwx11` (`--evict-mb`, slow nop kernels) is built on CRB and accepted. Round 4 session 1 runs since 08:42 UTC (`ZC`, `ZD`, `ZN`, `ZM`), expected end about 10:20 UTC.
- Queue after it: session 2 of round 2 and of H2 (allowed since 09:35 UTC), session 2 of round 3 (allowed from 11:26 UTC), session 2 of round 4 (3 hours after its session 1 end).

## 2026-11-15 08:55 UTC, round 4 first reading (`ZC`)

- `ZC`, session 1, counts per 64 B line, `asmread` at 8 MiB: without evict 0.818 to 0.826 L2 write-backs and 66.99 to 71.06 GB/s; with `--evict-mb 512` 0.817 to 0.823 write-backs and 67.69 to 69.84 GB/s. Old read: 67.0 GB/s in all 16 processes.
- The evict step did not change the write-back count. H1d stays open (rule 1 of round 4). The data cannot tell whether the buffer left the caches.
- Added step `ZS` (cycles per line against L2 refills per line at 13 sizes) with its rule in `DECISIONS-bwx8.md`.

## 2026-11-15 10:10 UTC, round 4 session 1 complete

- Ran 08:41:58 to 10:05:50 UTC, `ssh` status 0, steps `ZC`, `ZD`, `ZN`, `ZM` complete. Load at launch (lowest and highest): 0.01 1.16 . Session 2 of round 4 may start at 13:05:50 UTC.
- The script `tackle-8mb-analysis/final8.py` now extracts every reported number and applies the recorded rules (`final8.txt`, `final8.json`). It was reviewed by a second agent: 140 of 140 checks, 22 numbers recomputed independently.
- `ZN`, session 1 (cell medians, GB/s, CPU 2 / CPU 41), the slow load-only kernels:
  - `read_nop96`: 54.94 / 54.94 at 32 KiB, 55.08 / 55.08 at 1 MiB, 54.96 / 55.02 at 8 MiB, 55.07 / 55.08 at 16 MiB.
  - `read_nop128`: 42.89 / 42.89, 42.97 / 42.97, 42.91 / 42.96, 42.96 / 42.97.
  - `read_nop64`: 75.10 / 75.10 at 32 KiB, 75.29 / 75.29 at 1 MiB, 63.64 / 70.99 at 8 MiB (95th percentile 73.71 / 73.87), 62.05 / 68.54 at 16 MiB.
  - Reading by rule 2 of round 4: the two slow kernels keep their rate at every size (loss from 32 KiB to 8 MiB 0.01 to 0.08 GB/s), as old read does. So the gain of the fast loop over a slow loop at 8 MiB follows from the two rates: 23 to 30 % over `read_nop96` and 58 to 66 % over `read_nop128`, against 141 % and 209 % at 32 KiB. The middle kernel `read_nop64` fails the simple form of the rule: its high level at 8 MiB (73.7 to 73.9 GB/s) is above the high level of `asmread` (71.0 to 71.6 GB/s). So the supply rate at 8 MiB is not one number for all loops.
- `ZD`, session 1: the evict step changes the 8 MiB 95th-percentile rate of `asmread` and `read` by 0.00 to 0.08 GB/s. The write-back count stays at 0.82 per line, so H1d stays open by its rule ("Insufficient data").
- `ZM`, session 1 (descriptive): the up-switches sit in bands of record offsets about 100 B wide (1688 to 1784, 3552 to 3584, 7224 to 7296, 9096 to 9176, 10936 to 11008, 14336 to 14392 B after the start of the record array).
- Running now: `ZS` session 1, then session 2 of round 2, then session 2 of H2. Then session 2 of round 3 (from 11:26 UTC) and of round 4 (from 13:06 UTC).

## 2026-11-15 11:35 UTC, session 2 of round 2 and of H2 done, `ZS` session 1 done

- Ran: `ZS` session 1 (10:06 to 10:11 UTC), round 2 session 2 (10:11:25 to 11:24:55 UTC), H2 session 2 (11:24:56 to about 11:27 UTC). All with `ssh` status 0. Load at launch (lowest and highest): 0.55 1.11 .
- Confirmed in both sessions (verdicts from `tackle-8mb-analysis/final8.txt`, block 15):
  - H3a (a kernel timer on the worker's CPU triggers the switch): not supported in both sessions. No sampler key accompanies the switches. The first up-switch is tied to the start of the target, not to the process start.
  - Counters by level: `cpu_cycles`, `l1d_cache_lmiss_rd` and `l2d_cache_lmiss_rd` differ between the low and the high level on both CPUs in both sessions.
  - Rule 6 of round 2 (`XN`): part (c) holds in all four cells. `read_nop16` fails part (a) on both CPUs in both sessions (it does not reach the high level). `read_nop32` and `read_sparse` hold.
  - H2: on CPU 2 the original program is at the low level in 36 of 36 and 35 of 36 new-read repetitions, median gain 0.22 % and 0.17 %: supported. On CPU 0 it is at the high level in 33 of 36 repetitions in both sessions, median gain 5.73 % and 5.71 %: rejected for CPU 0. CPU 41: undecided (21 and 33 low).
- `ZS`, session 1 (one session): for `asmread` the cycles per 64 B line follow 2.09 + 0.66 r on CPU 2 and 2.08 + 0.65 r on CPU 41, where r is the count of L2 refills per line (0.00 at 1 MiB, 0.62 at 4 MiB, 0.83 at 8 MiB, 0.92 at 16 MiB, 0.96 at 32 MiB). 10 of 11 sizes lie inside the band that was fixed before the data, on each CPU. Old read stays at 2.67 cycles per line up to 16 MiB.
- This gives the size answer in one line: the new loop costs 2.09 cycles per line plus 0.65 cycles for each line that comes from the SLC, old read costs 2.67 cycles per line, and at 8 MiB 83 % of the lines come from the SLC, so both cost about the same.
- Running: session 2 of round 3 (since 11:27 UTC). Then session 2 of round 4 (from 13:06 UTC) and of `ZS` (from 13:11 UTC). The final report generator is being built.

## 2026-11-15 13:10 UTC, session 2 of round 3 done

- Ran 11:27:27 to 12:49:59 UTC, `ssh` status 0, steps `YL`, `YP`, `YC`, `YF` complete. Load at launch (lowest and highest): 0.54 1.23 .
- Verdicts by the recorded rules (`tackle-8mb-analysis/final8.txt`, block 15):
  - H1b (rule 3 of round 3): not confirmed. CPU 2 in session 1 is "rejected". The other three cells are "Insufficient data", because no prefetch kernel has at most half of the `asmread` first-level cache misses at 8 MiB there.
  - H7 by `YL` (rule 1): "undecided" in all four cells. The statistic of the rule (median of the first fall and of the first up) does not fit, because many processes start at the other level.
  - H7 by `YP` (rule 2 with the replaced statistic): "supported" in session 1, "undecided" in session 2 (CPU 2: 3 of 5 pads match).
- What the raw `YP` rows show in both sessions (block 10 of `final8.txt`): the up-switch windows of the padded runs are the same in session 1 and session 2. Pad 80: 20, 43, 66, 89. Pad 400: 16, 39, 62, 85. Pad 1040: 8, 31, 54, 77. Pad 2080: 18, 41, 64, 88. Pad 4000: 17, 40, 64, 87. Each list equals the up windows of the 60 s runs of round 1 (21, 44, 67, 90, 114, 137) minus pad / 80. The session 2 verdict "undecided" comes from the comparison series: the two pad 0 processes of CPU 2 in session 2 show ups at 21, 44, 90 and 8, 21, 44, 77, so the spacing that the evaluator derives from them is not 23 windows. I will add a second evaluation against the round 1 series and report both.
- The recurring falls move by pad / 80 in all 10 pad and CPU cells in both sessions ("fall series: holds").
- `--hot-copy`: 3 of 4 processes without a switch in each session.
- Running: session 2 of round 4 (since 13:06 UTC, ends about 14:30 UTC). Then session 2 of `ZS`.

## 2026-11-15 14:50 UTC, all sessions done, goal reached, final deliverables written

- Ran: session 2 of round 4 (13:06:13 to 14:30:03 UTC) and of `ZS` (14:30:12 to 14:35:27 UTC), both with `ssh` status 0. Load at launch: `ZC` 0.00 to 0.94, `ZD` 0.55 to 1.15, `ZN` 0.54 to 1.00, `ZM` 0.83 to 1.08, `ZS` 0.85 to 1.00 (block 1 of `tackle-8mb-analysis/final8.txt`).
- All 41 result folders hold 2,946 processes with 0 killed, 0 failed, 0 incomplete and 0 failure rows.
- Verdicts with both sessions (block 15 of `final8.txt`):
  - P1 and P2 confirmed on both CPUs. The new loop carries 100.1 to 100.3 % of the lost advantage.
  - H1c (step `ZS`): not contradicted. 10 of 11 counted sizes inside the band in each of the four cells. Fitted lines 2.074 to 2.089 + 0.646 to 0.667 r cycles per line.
  - Slow kernels (step `ZN`): `read_nop96` and `read_nop128` keep their rate at 8 MiB in 4 of 4 cells each. Supplementary: the gain of `asmread` over old read, `read_nop96` and `read_nop128` at 8 MiB lies inside the range predicted from the two rates in 12 of 12 cells.
  - H1b: not confirmed by its rule. Supplementary: at 1 MiB the prefetch removes 94.2 to 99.2 % of the first-level cache misses and the rate is 7.73 to 7.80 GB/s lower in all 16 cells.
  - H1d: "Insufficient data" in both sessions (write-backs 0.82 per line with and without evict).
  - H2: supported on CPU 2, rejected on CPU 0, undecided on CPU 41.
  - H3a: not supported in both sessions.
  - H7: `YL` undecided, `YP` supported in session 1 and undecided in session 2 by the recorded evaluation. Supplementary against the round 1 series: 113 of 122 predicted up windows show an up (92.6 %).
- Goal check against the handoff:
  1. Named mechanism: the new loop pays about 0.66 cycles for each line from the SLC on top of 2.08 cycles, the old loop pays 2.67 cycles at every size, and at 8 MiB 83 % of the lines come from the SLC.
  2. Controlled tests on both CPUs in both sessions: the core cost of the loop was changed (step `ZN`) and the share of lines from the SLC was changed (step `ZS`), and the gain and the cost changed as the rules predicted.
  3. Share and open points: section 8 of the report and the result handoff.
- Deliverables: `tackle-8mb-report.html` (HTML report), `tackle-8mb-results.md` (result handoff), `tackle-8mb-analysis/final8.txt` and `.json` (all numbers and verdicts). Tests of the two generators: 183 of 183 and 116 of 116 checks.
- Nothing of this work runs on CRB.
