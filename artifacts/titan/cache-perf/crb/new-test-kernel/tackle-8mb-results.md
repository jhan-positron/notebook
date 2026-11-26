# Result handoff: why the new read kernel gains so little at 8 MiB

Written 2026-11-15 14:50 UTC by the agent that ran rounds 1 to 4 under `tackle-8mb-handoff.md`.

## Short version

- The new load-only read loop and the old read loop cost almost the same number of processor cycles per 64-byte line at 8 MiB, so the gain there is 0.2 to 6.7 %. At 1 MiB the new loop costs 2.10 cycles per line and the old loop 2.67, so the gain is 27 %.
- The old loop costs 2.67 cycles per line at every size from 1 to 16 MiB. The new loop costs about 2.08 cycles per line plus about 0.66 cycles for each line that must come from the shared cache (the SLC). At 8 MiB 83 % of the lines come from the SLC.
- Two controlled tests support this in both sessions on both CPUs. Not explained: why a line from the SLC costs 0.66 cycles more, and which hardware part moves the new loop between two rates at 8 MiB. Those questions need root.

## Words used here

| Term | Meaning |
|---|---|
| CRB | The Arm Phoenix Reference Server, 128 cores, 2.8 GHz. Each core has a 64 KiB first-level cache (L1) and a 2 MiB second-level cache (L2). All cores share a 128 MiB system-level cache (SLC). |
| old read, `oldread` | The read loop of the original benchmark: loads and vector adds. |
| new read, `read`, `asmread` | The load-only loop, in C and in assembly. |
| line | One 64-byte cache line. |
| gain | new rate / old rate - 1, in percent. |
| r | Count of L2 refills per line (event `l2d_cache_refill`). It is the share of lines that enter L2 from the SLC. |
| level | At 8 MiB a load-only loop runs at one of two rates: low (about 67.5 GB/s on CPU 2, 69.1 on CPU 41) or high (about 71.1 and 71.6 GB/s). |
| session | One visit set on CRB. Session 2 repeats session 1 at least 3 hours later with the reversed CPU order. |
| step | One batch of processes. The step names are listed in "What ran". |
| confirmed | Same result in both sessions on both CPUs by the rule that was recorded before the data. |
| supplementary | An evaluation that was defined after the data was seen. It never replaces a recorded verdict. |
| A | `new-test-kernel/tackle-8mb-analysis/` |
| X, Y, Z | `tmp/agent-scratch/bwx8-2026-11-14/`, `bwx10-2026-11-15/`, `bwx11-2026-11-15/` (runner sources, schedules, run scripts) |

## Deliverables

- The HTML report: `new-test-kernel/tackle-8mb-report.html` [Ref2]. It is built by `A/report_final.py` from `A/final8.json`.
- Every number and every verdict: `A/final8.txt` and `A/final8.json`, built by `A/final8.py` from the result folders [Ref1].
- The decisions file with every rule, written before the data of each step: `X/DECISIONS-bwx8.md`, from the heading "Second agent, 2026-11-15" [Ref3].
- The progress file, in time order, with the load of every visit: `new-test-kernel/tackle-8mb-progress.md` [Ref4].
- This file.

## The answer, with its evidence

1. **The old loop does not depend on the size.** Old read at 8 MiB minus old read at 1 MiB is inside the 0.30 GB/s margin in all four CPU and session cells (prediction P1, step `S2`). Its counted cost is 2.67 cycles per line from 1 to 16 MiB (step `ZS`) [Ref1].
2. **The new loop loses rate with the size.** It loses 13.65 to 15.92 GB/s from 1 MiB to 8 MiB (prediction P2, confirmed). The new loop carries 100.1 to 100.3 % of the lost advantage (step `S2`) [Ref1].
3. **The cost of the new loop follows the share of lines from the SLC.** Step `ZS` counted cycles and L2 refills at 13 sizes from 1 to 32 MiB. The band 2.10 + 0.50 r - 0.05 to 2.10 + 0.69 r + 0.05 cycles per line was fixed before the data. 10 of 11 counted sizes lie inside it in each of the four cells. The fitted lines are 2.089 + 0.658 r, 2.083 + 0.667 r (CPU 2) and 2.079 + 0.646 r, 2.074 + 0.663 r (CPU 41). Verdict by the rule: hypothesis H1c is not contradicted [Ref1].
4. **So the gain is small where the two costs meet.** At 8 MiB r is 0.83. The new loop then costs 2.50 to 2.67 cycles per line, and the old loop 2.67. There is no step at 8 MiB. The falling rate of the new loop crosses the flat rate of the old loop between 8 and 16 MiB (step `XF`, step `ZS`) [Ref1].
5. **Changing the core cost of a loop changes the gain as the two rates predict.** The kernels `read_nop96` and `read_nop128` are the load-only loop with 96 or 128 no-operation instructions. They run at 54.9 and 42.9 GB/s at 32 KiB and keep that rate at 8 MiB (loss at most 0.08 GB/s in 4 of 4 cells each, rule 2 of round 4, step `ZN`). The gain of `asmread` over them at 8 MiB lies inside the range that the two rates predict in 12 of 12 cells (supplementary) [Ref1].
6. **The count of first-level cache misses is not the limit.** Software prefetch removes 94.2 to 99.2 % of the L1 misses of the load-only loop at 1 MiB, and the rate is 7.73 to 7.80 GB/s lower in all 16 cells (supplementary, steps `YC`, `YF`). The recorded verdict for hypothesis H1b at 8 MiB is "not confirmed": one cell "rejected", three cells "Insufficient data" [Ref1].
7. **The original 0.94 % was a low-level value.** The original program on CPU 2 gives the low level in 36 of 36 and 35 of 36 new-read repetitions, median gain 0.22 % and 0.17 % (hypothesis H2, supported on CPU 2). On CPU 0 it gives the high level in 33 of 36 repetitions in both sessions, median gain 5.73 % and 5.71 % (H2 rejected for CPU 0). CPU 41 is undecided (step `H2`) [Ref1].

## The two levels at 8 MiB

- No activity of the host on the worker's CPU accompanies a switch. Hypothesis H3a (a kernel timer) is not supported in both sessions (step `XW`, host sampler) [Ref1].
- Three events differ between the levels in both sessions on both CPUs: `cpu_cycles`, `l1d_cache_lmiss_rd` (0.30 per line at the high level, 0.36 to 0.37 at the low level) and `l2d_cache_lmiss_rd` (steps `XCA`, `XCB`, `XCC`) [Ref1].
- The switches follow the index of the runner's own window record. In 60 s runs the up-switches sit at windows 21, 44, 67, 90, 114, 137, 179 and the falls at 16, 42, 69, 95, 122, 148, 168, 194, with a spread of 5 to 20 ms over the processes (step `S4`) [Ref1].
- Moving the record array by a pad of P bytes moves the switches by P / 80 windows. Supplementary evaluation against the round 1 series: 113 of 122 predicted up windows show an up when the process is at the low level before (92.6 %, both sessions, step `YP`). The recorded verdicts for hypothesis H7 are weaker: `YL` "undecided" in all four cells, `YP` "supported" in session 1 and "undecided" in session 2. The reason is in "Protocol changes" [Ref1].
- So the level is tied to the address of a record that the runner touches at the end of each window. Which hardware part reacts is not known.

## Tests that did not decide

- **Clean lines (hypothesis H1d, steps `ZC`, `ZD`).** The evict step did not change the L2 write-back count (0.82 per line with and without). By its rule the result is "Insufficient data". Two readings fit: the buffer did not leave the caches, or L2 writes back a clean line like a dirty one. The rate changed by -0.09 to +0.08 GB/s.
- **`read_nop16` and `read_nop64`.** `read_nop16` never reaches the high level at 8 MiB (rule 6 part (a) fails on both CPUs in both sessions). `read_nop64` reaches 73.2 to 73.9 GB/s at 8 MiB in three of four cells, above the high level of `asmread` (71.0 to 71.6 GB/s). So the supply rate at 8 MiB is not one number for all loops.

## Which share is explained, and what stays open

- Explained by tests that passed their recorded rule in both sessions on both CPUs: the gain at 8 MiB is small because the new loop pays for lines from the SLC and the old loop does not (items 1 to 5). The cycle model reproduces the fall of the gain from 1 MiB to 8 MiB. The report gives the share per CPU, session and level in its table 20. That share is a number of the report. No rule fixed it before the data [Ref2].
- Not explained, "Insufficient data":
  - Why a line from the SLC costs about 0.66 cycles more. Needed: mesh counters of the SLC (root).
  - Why the load-only loop does not pass 85 GB/s from L2 (93 GB/s with one load per line). Needed: documentation of the core's fill path, or counters that need root.
  - Which hardware part reacts to the record address. Needed: physical page addresses and mesh counters (root). Without root, pad tests for other kernels would map the effect further. They were not run.
  - Why old read needs 2.67 cycles per line. One supplementary comparison exists: `read_sparse` has the loads of old read and no adds, and it runs at 133.1 GB/s at 32 KiB against 66.7 GB/s for old read. The two kernels also differ in loop offset (4 against 40 modulo 64).

## What ran

All on CRB, CPUs 2 and 41 (step `H2` also CPU 0), one process at a time, no root. Load at launch per step: block 1 of `A/final8.txt` (0.00 to 1.23 over all steps; a load near 1.00 is the test itself, est.) [Ref1].

| Round | Steps | Binary (sha256, first 8 digits) | Session 1 (UTC) | Session 2 (UTC) |
|---|---|---|---|---|
| 1 | `B6W`, `S2`, `S4` | `bwx8` (`f84be912`) | 00:31 to 01:20 | 04:20 to 05:09 |
| 2 | `XEV`, `XW`, `XCA`, `XCB`, `XCC`, `XN`, `XF` | `bwx8` | 05:21 to 06:34 | 10:11 to 11:24 |
| H2 | `H2` | `bw_old`, `bw_new` of 2026-11-13 | 06:35 to 06:37 | 11:24 to 11:27 |
| 3 | `YA`, `YL`, `YP`, `YC`, `YF` | `bwx8` for `YL`, `bwx10` (`22cbb1ee`) | 07:03 to 08:26 | 11:27 to 12:49 |
| 4 | `ZA`, `ZC`, `ZD`, `ZN`, `ZM`, `ZS` | `bwx11` (`f1215f9e`) | 08:41 to 10:11 | 13:06 to 14:35 |

2,946 processes in 41 result folders, 0 killed, 0 failed, 0 incomplete, 0 failure rows [Ref1].

## Protocol changes and deviations

- **Counters without the three-mode gate of the design.** I used counters to compare the two levels inside one process. The check was that the counted traces show the uncounted levels and switch times. Reason and rule: decisions file, round 2, rule 1 [Ref3].
- **Statistics that did not fit.** Rule 2 of round 3 named "the first fall after window 30" for step `YP`. That fall is absent in some processes. I replaced it by the series of all switch windows and recorded this before session 2. Rule 1 of round 3 (step `YL`) uses the median of the first fall and first up. Many processes start at the other level, so the literal verdict is "undecided". Both recorded verdicts are printed as they are. The supplementary evaluations are printed beside them.
- **Extra logins while a visit ran.** 6 logins fetched finished step folders while later steps of the same visit ran (steps `XW`, `XCA` to `XCC`, `YL`, `YP`, `YC`, `ZC`). Each ran one `tar` after the marker check.
- **One file outside `~/cache-perf`.** The build login of `bwx10` wrote `/tmp/.x` on CRB. The next login removed it 1 minute later.
- **No human review of new code.** Each new tool had one review round by a second agent, its local tests, the listing check of each new binary and a trace-mode acceptance step on CRB (`YA`, `ZA`).
- **Missing control.** The prefetch kernels have a longer loop than `asmread`. `read_nop4` has the same loop length and no prefetch, and it was not in step `YF`.
- Slack #phoenix-crb was read before every login and every 10 minutes during every run. No block was announced on 2026-11-15. `STOP_AT=none` in every visit.

## State on CRB

- Nothing of this work runs. I created no stop file. The marker file was absent at every login.
- Folders under `~/cache-perf`: `bwx8-20261114/` (with `sched9/`, `run_bwx9.sh`, `hostwatch.py`, `run_h2.sh`), `bwx10-20261115/`, `bwx11-20261115/`, and `results/` with the 41 folders, all copied to `crb/results/`.

## If someone continues

- Tests without root that were not run: pad tests for `read_nop16` and `read_nop64` (do they have the same switch windows?), an old-loop variant with fewer vector adds at loop offset 40, `read_nop4` as the layout control of the prefetch family.
- Tests with root: mesh counters of the SLC while the loop runs at each level, and the physical addresses of the buffer pages and of the record block (the design's Part D).

## References

- [Ref1] `new-test-kernel/tackle-8mb-analysis/final8.txt` and `final8.json`: block 1 inventory and load, block 2 round 1, block 3 size curve, block 5 switch timing, block 6 counters by level, block 7 kernel families, block 8 H2, blocks 9 and 10 `YL` and `YP`, block 11 prefetch family, block 12 evict, block 13 `ZS`, block 15 verdicts, block 16 supplementary evaluations. Result folders: `crb/results/bwx8-*`, `bwx9-*`, `bwx10-*`, `bwx11-*`, `h2-*` of 2026-11-15.
- [Ref2] `new-test-kernel/tackle-8mb-report.html`.
- [Ref3] `tmp/agent-scratch/bwx8-2026-11-14/DECISIONS-bwx8.md`, from "Second agent, 2026-11-15" to the end.
- [Ref4] `new-test-kernel/tackle-8mb-progress.md`.
