# Code map: the test code behind steps S2, ZS, ZN and H2

Written 2026-11-15 for the "Test code" section of tackle-8mb-report-easy-read.html.
Every line range below was read from the file on that day. A range marked "fn" is one whole function, so the generator can cut it by function name as well.

## Short version

- Steps S2, ZS and ZN use one C runner in trial mode. S2 ran the binary bwx8 and ZS and ZN ran the binary bwx11. With the marked addition blocks removed, bwx11.c equals bwx8.c except one include line, and the machine loops of oldread, read and asmread are the same instructions in both builds.
- Step H2 uses the ORIGINAL benchmark, two binaries built on 2026-11-13: bw_old (source bandwidth.orig.c) and bw_new (source bench/bandwidth.c).
- A rate is bytes / (t_end - t_start) of one window. Cycles per line and r are counter differences of one window times 64 / bytes.

## Path shorthands

| Short | Full path |
|---|---|
| X8 | /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx8-2026-11-14 |
| X10 | /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx10-2026-11-15 |
| X11 | /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx11-2026-11-15 |
| K13 | /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13 |
| BENCH | /home/jhan/workspace/titan/cache-perf/bench |
| A | /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb-analysis |
| N | /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel |
| R | /home/jhan/workspace/titan/cache-perf/crb/results |

## (a) The chain from the login to the kernel

One "visit" is one ssh login from the development machine. The visit script checks the marker file /tmp/positron-perf.RUNNING on CRB and then starts one run script there. The run script starts one runner process at a time.

```
S2 (round 1)        ZS, ZN (round 4)       H2
visit8.sh           visit11.sh             visit_h2.sh        development machine, 1 ssh login
   |                   |                      |
run_bwx8.sh         run_bwx11.sh           run_h2.sh          on CRB, loops over the processes
   |  reads            |  reads               |  builds the order itself
sched/s<n>/S2.tsv   sched11/s<n>/ZS.tsv    (12 pairs per CPU, ABBA)
 + S2/NNNN.plan     ZN.tsv + NNNN.plan        |
   |                   |                      |
bwx8 --trial ...    bwx11 --trial ...      bw_old / bw_new --kernel read ...
   |                   |                      |
main > trial_main > trial_worker           main > worker > pass
 > run_trial > timed_sequence > tcall > call   > k_read
 > k_oldread / k_read / k_asmread / k_read_nop96 / k_read_nop128
```

| Step | Visit script (dev machine) | Run script (CRB) | Schedule generator | Runner |
|---|---|---|---|---|
| S2 | X8/visit8.sh:15-16 | X8/run_bwx8.sh | X8/schedule8.py, method Gen.S2 :110-128 | bwx8 (sha256 f84be912...) |
| ZN | X11/visit11.sh:17-18 | X11/run_bwx11.sh | X11/schedule11.py, method Gen.ZN :180-195 | bwx11 (sha256 f1215f9e...) |
| ZS | X11/visit11.sh:17-18 | X11/run_bwx11.sh | X11/schedule_zs.py :12-45 (whole main) | bwx11 |
| H2 | X8/visit_h2.sh:16-17 | X8/run_h2.sh | none (order built in run_h2.sh:115-128) | bw_old, bw_new of 2026-11-13 |

Facts with their source lines:

- The ssh command of a visit: X8/visit8.sh:14-17, X11/visit11.sh:16-19, X8/visit_h2.sh:15-18. Each is "marker check; cd to the folder on CRB; STOP_AT=... SESSION=... ./run_*.sh STEP...". The log of the login goes to N/<log name>.log.
- The one recorded visit command line is in N/tackle-8mb-handoff.md:200-205: `STOP_AT=none SESSION=2 SESSION1_END=2026-11-15T01:20:18Z BWX8_SHA256=f84be912... ./visit8.sh visit8-s2-B6W-S2-S4 B6W S2 S4`. The other visit command lines are not recorded verbatim. The visit logs show which steps one login ran: N/visit8-s1-B6W-S2-S4.log and N/visit8-s2-B6W-S2-S4.log (B6W, S2, S4), N/visit11-s1-main.log and N/visit11-s2-main.log (ZC, ZD, ZN, ZM), N/visit11-s1-ZS.log and N/visit11-s2-ZS.log (ZS alone), N/visit-h2-s1.log and N/visit-h2-s2.log (H2).
- run_bwx8.sh functions called for every process, in order: `load_step` :131-158 (reads the .tsv, adds up the nominal work), then per process `one` :74-93, which calls `check_marker` :66, `check_deadline` :67, `settle` :72 (waits until at most 2 tasks are runnable, 20 s at most), writes the load evidence to launches.txt :80, writes the header line "-- step ..." :82 and starts the runner :84. The step loop is :160-201 and the per-process call is :193-197.
- run_bwx11.sh is a copy with two additions: `pick_bin` :143-153 chooses the binary from sched11/s<n>/<STEP>.bin, and an optional host sampler (hostwatch.py) that runs only if a <STEP>.watch file exists. ZS.bin and ZN.bin hold "bwx11". No .watch file exists for ZS or ZN. `one` is :109-134 and the launch is :119. The step loop is :236-296 and the per-process call is :287-292.
- run_h2.sh: order built :115-128, digest check of both binaries :144-147, `one` :84-103, launch :94, loop :181-183.
- The system load is recorded at every launch (1-minute load average, field "loadavg" of the header line and of launches.txt): run_bwx8.sh:80-82, run_bwx11.sh:115-117, run_h2.sh:90-92. The analysis reads it in A/final8.py `scan_folder` :245-283.

Proposed excerpts for (a):

| Id | What | Path:lines |
|---|---|---|
| a1 | the ssh line of a visit | X11/visit11.sh:16-19 |
| a2 | `one`: load evidence, header line, launch of the runner | X8/run_bwx8.sh:74-93 |
| a3 | the per-process loop of a step | X8/run_bwx8.sh:193-197 |
| a4 | `pick_bin` (which binary a round 4 step runs) | X11/run_bwx11.sh:143-153 |
| a5 | schedule of S2: every kernel order once per size and CPU, 4 trials per process | X8/schedule8.py:110-128 |
| a6 | schedule of ZN | X11/schedule11.py:180-195 |
| a7 | schedule of ZS (13 sizes, 2 kernels, events) | X11/schedule_zs.py:8-11 and :21-33 |
| a8 | H2: the order and the launch line | X8/run_h2.sh:112-128 and :94 |

## (b) The C runner: every function on the path of one measured window

Source for S2: X8/bwx8.c. Source for ZS and ZN: X11/bwx11.c. Line numbers are given for both. "same" means the function text is byte-identical in the two files (checked with a script, see (e)).

Order of calls for one plan process (`bwx --trial --cpus C --bytes B --plan FILE [--pmu-type 11 --events ...]`):

| # | Function | bwx8.c | bwx11.c | Text | What it does for the measurement |
|---|---|---|---|---|---|
| 1 | `main` | 2061-2283 | 2481-2703 | same | Reads the process start time `t_base_ns`, calls `restrict_cpus`, sees `--trial` and returns `trial_main` (bwx11.c:2485-2491). |
| 2 | `now_ns` | 243-248 | 294-299 | same | One `clock_gettime(CLOCK_MONOTONIC)` in whole ns. The only clock of the window times. |
| 3 | `restrict_cpus` | 284-301 | 335-352 | same | Removes CPUs above 119 from the allowed set of the process. |
| 4 | `trial_main` | 1987-2057 | 2384-2470 | differs: 3 added options | Parses the options with `parse_cpus`, `parse_bytes`, `parse_long`, `parse_events`. Calls `read_plan`. Pins the controlling thread with `pin_cpu(plan.ctl_cpu)` (CPU 0). Starts `trial_worker` in a second thread and waits. |
| 5 | `parse_events` | 1118-1140 | 1355-1377 | same | Only with `--events`: stores each NAME=CODE pair. |
| 6 | `read_plan` | 1925-1975 | 2309-2359 | same | Reads the plan file, checks the 3 header lines, calls `plan_pairs` for line 2 and `plan_trial` for every trial line. |
| 7 | `plan_trial` | 1866-1922 | 2247-2306 | differs: 1 added line (rec-pad) | Splits the 11 fields of one trial line. Calls `plan_long`, `plan_part` (kernel@size[:ms], looks the kernel up in `kernels[]`), `plan_size`, `trial_windows`, `window_bins`. |
| 8 | `trial_worker` | 1676-1755 | 2033-2136 | differs: added M rows and the evict call | The worker thread. Calls, in order: `pin_cpu` (the worker CPU), `alloc_buf`, `k_write` (first touch of the buffer by the pinned worker, bwx11.c:2050), `alloc_records`, prints the header and M rows, then for each trial `print_s`, `run_trial`, `emit_trial` (bwx11.c:2121-2129). |
| 9 | `pin_cpu` | 331-340 | 382-391 | same | `sched_setaffinity` to one CPU. |
| 10 | `alloc_buf` (uses `buf_len`) | 350-367 | 401-418 | same | Maps the buffer at a 2 MiB boundary and asks for 2 MiB pages (`MADV_HUGEPAGE`). |
| 11 | `alloc_records` | 1533-1563 | 1845-1879 | differs: 1 added line (rec-pad) | Allocates and first-touches the record block of all trials. Calls `set_windows` for every trial. |
| 12 | `set_windows` | 1503-1528 | 1815-1840 | same | Fills each window record: kernel, size, duration, and passes per clock read = 8 MiB / size, at least 1 (bwx11.c:1832). |
| 13 | `evict_step` | absent | 2012-2030 | bwx11 only | Only with `--evict-mb N` above 0. Not used in S2, ZS or ZN. |
| 14 | `run_trial` | 1454-1487 | 1759-1799 | differs: added hot-copy branch | Opens or closes the counter group as the plan says, then `page_read`, `switches`, `tcpu`, then `timed_sequence`, then `tcpu`, `switches`, `page_read`. |
| 15 | `count_open` | 1391-1421 | 1696-1726 | same | Only when the trial has count "open" or "read" (ZS: "read"). One `perf_event_open` per event, one group, user mode only. |
| 16 | `count_close` | 1375-1386 | 1680-1691 | same | Only when a counter group is open and the trial has count "closed", and once at the end of the worker. |
| 17 | `page_read` (calls `read_smaps`, `read_vmstat`) | 1423-1429 | 1728-1734 | same | Huge-page coverage of the buffer before and after the timed sequence (P rows). Outside the timed sequence. |
| 18 | `switches` | 1432-1440 | 1737-1745 | same | Context-switch counts of the thread before and after (E row). |
| 19 | `tcpu` (calls `cpu_ns`) | 1288-1293 | 1529-1534 | same | Thread CPU time before and after (E row). |
| 20 | `timed_sequence` | 1338-1373 | 1579-1614 | same | THE MEASUREMENT. For each window: `tclock` for t0, then repeat { `passes` times `tcall`; `tclock` for t1 } until t1 - t0 reaches the window length. Stores bytes, t_start, t_end in the window record. Only `clock_gettime`, the kernel and `tcount` are called inside. |
| 21 | `tcount` | 1310-1326 | 1551-1567 | same | Only when the trial has count "read" (ZS). One `read()` of the counter group and one thread CPU clock read at each boundary of a target window. |
| 22 | `tclock` | 1278-1286 | 1519-1527 | same | `now_ns()`. With `--trace` it also logs the time (not used in S2, ZS, ZN). |
| 23 | `tcall` | 1297-1305 | 1538-1546 | same | One kernel call through `call`. With `--trace` it logs the first call of a window. |
| 24 | `call` | 838-856 | 1075-1093 | same | Chooses by kernel type: a T_READ kernel is called as `fn(a, n)`. The T_OLDREAD kernel returns a sum that is stored to the sink. |
| 25 | the kernel | see (c) | see (c) | | `k_oldread`, `k_read`, `k_asmread`, `k_read_nop96`, `k_read_nop128`. One call = one pass over the buffer. |
| 26 | `emit_trial` | 1585-1674 | 1901-1990 | same | Prints the rows of the trial after the timed sequence: P, W (one per window), B, C (one per counted target window), X (failures), E. Calls `print_p8`, `print_na`, `first_multiplexed`. |
| 27 | `print_s` | 1565-1572 | 1881-1888 | same | Prints the S row (the plan line) before the trial runs. |

Options that change the path:

- Counters (`--pmu-type`, `--events`, plan field count = "read"): rows 5, 15, 16, 21 and the C rows of row 26. Used by ZS only. S2 and ZN have count = "closed": no counter is open.
- `--evict-mb`: row 13. bwx11 only. Not used by S2, ZS, ZN (`M,evict_mb,0` in R/bwx11-ZS-s1-20261115T100610Z/ZS.csv).
- `--rec-pad`, `--hot-copy`: bwx10 and bwx11 only. Not used by S2, ZS, ZN (`M,rec_pad,0`, `M,hot_copy,0`). With `--hot-copy` `run_trial` would call `timed_sequence_hot` (bwx11.c:1640-1677) in place of `timed_sequence`.
- `--trace`: `tev_add` (bwx11.c:1508-1517) records events. Not used by S2, ZS, ZN (`M,trace,0`).

Proposed excerpts for (b):

| Id | What | bwx11.c (ZS, ZN) | bwx8.c (S2) |
|---|---|---|---|
| b1 | `timed_sequence`: the window loop (core of the page) | 1579-1614 (fn), or the loop only 1589-1609 | 1338-1373 |
| b2 | `tcall` and `call`: from the window loop to the kernel | 1538-1546 and 1075-1093 | 1297-1305 and 838-856 |
| b3 | `set_windows`: size and passes per clock read | 1822-1839 (line 1832 is the passes rule) | 1510-1527 |
| b4 | `run_trial`: what stands before and after the timed sequence | 1759-1799 (fn) | 1454-1487 |
| b5 | `trial_worker`: pin, buffer, first touch, records | 2039-2052 | 1682-1695 |
| b6 | `trial_worker`: the trial loop | 2121-2129 | 1740-1748 |
| b7 | `tcount`: the counter read at a window boundary | 1551-1567 (fn) | 1310-1326 |
| b8 | `count_open`: how the counters are opened | 1702-1723 | 1397-1418 |
| b9 | `emit_trial`: the W row and the C row | 1910-1914 and 1922-1940 | 1594-1598 and 1606-1624 |
| b10 | `main` to `trial_main` | 2485-2491 | 2065-2071 |
| b11 | `trial_main`: plan, pin of the controlling thread, worker thread | 2444 and 2460-2469 | 2031 and 2047-2056 |

The bwx8.c ranges of b5, b6, b10 and b11 were printed and compared with the bwx11.c ranges: the same statements.

## (c) The kernels

| Kernel (name in a plan) | C function | Source, bwx11.c | Source, bwx8.c | Loop in X11/crb-build-1/listing.txt | Loop in X8/crb-build-1/listing.txt | Bytes per loop turn | Loop start modulo 64 |
|---|---|---|---|---|---|---|---|
| oldread (old read: loads and vector adds) | `k_oldread` | macro DEF_OLDREAD 428-441 | 377-390 | function 134-204, loop 161-176 | function 134-204, loop 161-176 | 128 (4 `ldp` of two 16 B registers, 8 `add`) | 40 |
| read (new read, load-only, C with NEON intrinsics) | `k_read` | 467-495 | 416-444 | function 2-15, loop 4-14 | function 2-15, loop 4-14 | 256 (8 `ldp`) | 36 |
| asmread (load-only, assembly text) | `k_asmread` | macro DEF_ASMREAD 583-609 | 532-558 | function 60-81, loop 66-76 | function 60-81, loop 66-76 | 256 (8 `ldp`) | 20 |
| read_nop96 | `k_read_nop96` | DEF_ASMREAD(read_nop96, 96) line 1030, comment 1010-1031 | absent | function 855-972, loop 861-967 (96 `nop`, counted) | absent | 256 | 20 |
| read_nop128 | `k_read_nop128` | DEF_ASMREAD(read_nop128, 128) line 1031 | absent | function 975-1124, loop 981-1119 (128 `nop`, counted) | absent | 256 | 20 |

- The loop offsets come from X11/crb-build-1/offsets.tsv and X8/crb-build-1/offsets.tsv (columns binary, kernel, function, start, loop_start, loop_mod64).
- The `nop` line of the macro is bwx11.c:599: `".rept " #nops "\n\tnop\n\t.endr\n\t"`. It stands after the 8 `ldp` and before the `add`.
- The kernel table that maps a plan name to a function is `kernels[]`, bwx11.c:1047-1068 (bwx8.c:817 onward).
- Build flags of both binaries (X8/crb-build-1/build.txt and X11/crb-build-1/build.txt, line "## CFLAGS="): `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4`, gcc 14.2.0.
- Buffer size: option `--bytes` (bwx11.c:2417-2419), repeated as the size after "@" in the plan field tgt. `call` passes n = size / 8 words (bwx11.c:1077-1078).
- Passes per window: not fixed. A window runs whole passes until its length (300 ms in S2, ZS, ZN) is reached. The clock is read after every `passes` passes, and `passes` = 8 MiB / size, at least 1 (constant `CHECK_BYTES`, bwx11.c:97, rule at bwx11.c:1832). Computed values: 32 KiB 256, 1 MiB 8, 1.5 MiB 5, 2 MiB 4, 2.5 MiB 3, 3 and 4 MiB 2, 5 MiB and above 1.
- Example from a result row: at 1 MiB one 300 ms window of `read` moved 25,576,865,792 bytes = 24,392 passes (R/bwx8-S2-s1-20261115T003207Z/S2.csv:46).

Proposed excerpts for (c):

| Id | What | Path:lines |
|---|---|---|
| c1 | source of old read | X11/bwx11.c:428-441 |
| c2 | machine loop of old read (16 lines) | X11/crb-build-1/listing.txt:161-176 |
| c3 | source of the load-only assembly kernel with the `nop` parameter | X11/bwx11.c:583-609 |
| c4 | machine code of asmread (whole function, 22 lines) | X11/crb-build-1/listing.txt:60-81 |
| c5 | source of new read (C) | X11/bwx11.c:468-495 (the page can shorten the 16 `vld1q_u64` lines) |
| c6 | machine code of new read (14 lines) | X11/crb-build-1/listing.txt:2-15 |
| c7 | read_nop96, first lines of the loop and its end | X11/crb-build-1/listing.txt:861-871 and :963-967 |
| c8 | the three round 4 kernels | X11/bwx11.c:1029-1031 |

## (d) From a window to GB/s, cycles per line and r

What is timed and counted in the runner:

- Window time: `t_start` = the clock read before the first pass, `t_end` = the first clock read at or after the window length (bwx11.c:1589, 1596, 1606-1609). Clock: CLOCK_MONOTONIC, whole ns.
- Window bytes: size x passes done (bwx11.c:1594, 1607).
- Counters (ZS only): one group, opened by the pinned worker for itself, user mode only (`exclude_kernel = 1`, `exclude_hv = 1`, bwx11.c:1702-1723). The group is read at each boundary of a target window (`tcount`, bwx11.c:1587-1588 and 1612-1613). The C row holds the difference of two readings (bwx11.c:1922-1940).
- Events of step ZS (X11/schedule_zs.py:10, PMU type 11 = armv8_pmuv3_0 on CRB):

| Name | Raw code | Used for |
|---|---|---|
| cpu_cycles | 0x11 | cycles per line |
| l2d_cache_refill | 0x17 | r |
| l1d_cache_lmiss_rd | 0x39 | printed, not in the ZS rule |
| l2d_cache_wb | 0x18 | printed, not in the ZS rule |
| bus_access | 0x19 | printed, not in the ZS rule |
| l2d_cache_lmiss_rd | 0x4009 | printed, not in the ZS rule |

Where the analysis turns rows into numbers:

| Number | Code | Path:lines |
|---|---|---|
| rows of one process (M, W, S, C, E, P, X, K) | `parse_csv` | A/levels9.py:246-302 |
| rate of a window in GB/s = bytes / (t_end - t_start), bytes per ns | `Window.rate` | A/levels9.py:102-104 |
| the same in the round 1 analysis | `Trial.rate` | A/analyze8.py:125-127 |
| count per 64 B line = count x 64 / bytes | `per64` | A/levels9.py:919-920 |
| counted windows of a process, with the multiplex flag (enabled_ns not equal running_ns) | `counter_windows` | A/levels9.py:892-912 |
| per process: median rate and median count per line over the counted windows that are not multiplexed | `counter_proc` | A/final8.py:218-227 |
| cell value of an S2-style step: per process the median, 5th and 95th percentile of all windows, then the median over the 6 processes | `proc_cell_values`, `cell_stats`, `cells_of` | A/levels9.py:1419-1434, A/final8.py:174-191 |
| result folders by step and session | class `Data` | A/final8.py:114-164 |
| all blocks, final8.json and final8.txt | `build`, `main` | A/final8.py:2581-2627 |

Where the recorded rules are applied:

| Step | Rule (recorded in X8/DECISIONS-bwx8.md) | Code | Path:lines |
|---|---|---|---|
| S2 | P1, P2, decomposition: DECISIONS line 143 and the lines after it | `stage2` builds the contrasts on the rate of the fourth target window. `contrast` gives median, A/A limit and "repeatable". `p1_cell` applies the 0.30 GB/s margin (`P1_MARGIN`, :38). `confirm` asks for both sessions and both CPUs. `decomposition` gives the share of the new loop. | A/analyze8.py:687-761, 500-549, 633-645, 583-592, 648-666 |
| S2 | matched sets (one process per kernel with the same rep_set) | `s2_units` | A/analyze8.py:610-626 |
| S2 | one process value R = median of the 4 trials, A/A value | `cell_rate` | A/analyze8.py:473-490 |
| S2 | which trials are usable (CPU time at least 99 % of wall time, gap at most 100 us, huge pages unchanged) | `Trial.check`, `Trial.usable` | A/analyze8.py:129-200 |
| S2 | into final8.json | `item2` reads A/s12-summary.json, which `analyze8.py summary` wrote (`summary` :1291-1314, `main` :1446-1487) | A/final8.py:315-421 |
| ZS | band 2.10 + 0.50 r - 0.05 to 2.10 + 0.69 r + 0.05; contradicted if more than 2 of the 11 counted sizes are outside on both CPUs in both sessions: DECISIONS line 367 | constants :1815-1817, `zs_band` :1820-1821, `rule_zs_cell` :1837-1867, `rule_zs_overall` :1870-1881, `item13` :1884-1939, fitted line `lsq` :1824-1834 | A/final8.py |
| ZN | rule 2 of round 4: DECISIONS line 350 | `rule_zn_kernel` :899-912 (a kernel with C_k at most 66 GB/s is "slow"; prediction holds if the 8 MiB median is within 1.0 GB/s of C_k), `item7` :915-1021 | A/final8.py |
| ZN (supplementary, defined after the data was seen) | gain of asmread over a slow kernel from two rates | `sup_gain` :2503-2555, kernels listed in `SUP_SLOW` :2198 | A/final8.py |
| H2 | DECISIONS line 279: low at or below 69.5 GB/s, high at or above 70.5; supported if at least 75 % low in both sessions and the median gain of the low pairs is within 1.5 points of 0.94 % | constants :1025, `h2_cpu_session` :1028-1041, `h2_verdict` :1044-1063, `item8` :1066-1104 | A/final8.py |
| H2 | parsing and pairing | `parse` :57-89, `complete` :92-93, `pairs_of` :96-112, `gain` :43-45, `classify` :48-54 | A/h2_analyze.py |

H2 rate: the original program prints one row per repetition with `aggregate_GBps` = total bytes / elapsed seconds / 1e9 (BENCH/bandwidth.c:598-603). `parse` takes column 7 (A/h2_analyze.py:88). The gain of a pair is 100 x (median of the 3 new repetitions / median of the 3 old repetitions - 1) (A/final8.py:1033-1034).

Proposed excerpts for (d):

| Id | What | Path:lines |
|---|---|---|
| d1 | rate of a window | A/levels9.py:102-104 |
| d2 | count per line | A/levels9.py:919-920 |
| d3 | per-process medians of rate and counts | A/final8.py:218-227 |
| d4 | the ZS band and the per-cell rule | A/final8.py:1815-1821 and :1840-1853 |
| d5 | the ZN rule for one kernel | A/final8.py:899-912 |
| d6 | the supplementary gain prediction | A/final8.py:2531-2535 |
| d7 | P1 for one cell | A/analyze8.py:633-645 |
| d8 | "repeatable" of a contrast | A/analyze8.py:543-549 |
| d9 | the H2 rule | A/final8.py:1044-1063 |

Worked check from real rows (computed here, for the page to show one window end to end):

- R/bwx8-S2-s1-20261115T003207Z/S2.csv:46 `W,0,target,0,read,1048576,25576865792,1200618748,1500619506`: 25,576,865,792 bytes / 300,000,758 ns = 85.26 GB/s.
- R/bwx11-ZS-s1-20261115T100610Z/ZS.csv:51 (W row of window 0, asmread at 6 MiB, CPU 2) and :71 (its C row `C,0,0,300072480,300072480,299908396,839656786,112271970,239890291,...`): cycles per line = 839,656,786 x 64 / 20,459,814,912 = 2.627. r = 239,890,291 x 64 / 20,459,814,912 = 0.750. enabled_ns equals running_ns, so the window is not multiplexed.

## (e) Which binary, and is the code the same

| Step | Binary | Evidence |
|---|---|---|
| S2 | bwx8 | result folders R/bwx8-S2-s1-20261115T003207Z and R/bwx8-S2-s2-20261115T042130Z; run_bwx8.sh:97 `BIN=$SRC/bwx8` |
| ZS | bwx11 | X11/sched11/s1/ZS.bin and s2/ZS.bin hold "bwx11"; log line "step ZS binary: bwx11" in N/visit11-s1-ZS.log; folders R/bwx11-ZS-s1-20261115T100610Z, R/bwx11-ZS-s2-20261115T143012Z |
| ZN | bwx11 | X11/sched11/s1/ZN.bin; log line "step ZN binary: bwx11" in N/visit11-s1-main.log; folders R/bwx11-ZN-s1-20261115T092141Z, R/bwx11-ZN-s2-20261115T134554Z |
| YF (gives asmread at 8 MiB to the ZN evaluation, see "Notes for the page author") | bwx10 | X10/sched10/s1/YF.bin; "step YF binary: bwx10" in N/visit10-s1-main.log; folders R/bwx10-YF-s1-20261115T073754Z, R/bwx10-YF-s2-20261115T120146Z |
| H2 | bw_old, bw_new | sha256 lines in R/h2-s1-20261115T063514Z/env.txt equal the digests in X8/run_h2.sh:110-111 |

Source comparison, bwx8.c against bwx11.c (run today):

- Whole file. I removed from bwx11.c every block between a line `/* bwx10+ */` or `/* bwx11+ */` and its closing line `/* bwx10- */` or `/* bwx11- */`. The result has 2,283 lines, as bwx8.c has. `diff` shows 1 changed line: the include of the self-test file (`bwx8_selftest.c` against `bwx10_selftest.c`). So bwx11.c is bwx8.c plus marked additions.
- Functions of (b), compared as whole text. Identical: `main`, `now_ns`, `restrict_cpus`, `parse_cpus`, `parse_bytes`, `parse_long`, `parse_events`, `read_plan`, `plan_pairs`, `plan_part`, `plan_long`, `plan_size`, `trial_windows`, `window_bins`, `pin_cpu`, `alloc_buf`, `buf_len`, `k_write`, `set_windows`, `print_s`, `count_open`, `count_close`, `page_read`, `read_smaps`, `read_vmstat`, `switches`, `tcpu`, `cpu_ns`, `timed_sequence`, `tcount`, `tclock`, `tcall`, `tev_add`, `call`, `k_read`, `emit_trial`, `print_p8`, `print_na`, `first_multiplexed`.
- Functions that differ, and exactly how (additions only, each inside a marked block):
  - `trial_main`: options `--hot-copy`, `--rec-pad` (bwx11.c:2399-2410) and `--evict-mb` (bwx11.c:2411-2414).
  - `plan_trial`: `recsz.bytes += plan.rec_pad;` (bwx11.c:2300-2302).
  - `alloc_records`: `win = (struct win *)((char *)win + plan.rec_pad);` (bwx11.c:1860-1863). With pad 0 nothing moves.
  - `run_trial`: `if (plan.hot_copy) timed_sequence_hot(...); else` before the unchanged call of `timed_sequence` (bwx11.c:1786-1792).
  - `trial_worker`: 8 more M rows (bwx11.c:2072-2080) and the evict block (bwx11.c:2081-2095). With `--evict-mb 0` no call is made.
- Kernels: the macros DEF_OLDREAD and DEF_ASMREAD and the function `k_read` are identical text. `read_nop96` and `read_nop128` exist in bwx11.c only (bwx11.c:1008-1043).

Machine code comparison (X8/crb-build-1/listing.txt against X11/crb-build-1/listing.txt, addresses removed, run today):

- `k_read`, `k_asmread`, `k_oldread`: the same instructions in bwx8 and bwx11. The only textual difference is absolute addresses.
- Loop start modulo 64 is the same in both builds: oldread 40, read 36, asmread 20 (offsets.tsv of both builds).
- Placement of the timed functions modulo 64 is the same: X11/crb-build-1/build.txt, line "## placement up to timed_sequence against bwx8: same" (`call` 24, `tcount` 52, `timed_sequence` 28).

H2 binaries against the runner:

- bw_old is built from K13/bandwidth.orig.c (sha256 61228754...) and bw_new from bandwidth.c (K13/run_kernels.sh:31-32). R/kernels-20261113T183218Z/probe.txt:14-20 records source sha256 f1985072... for bandwidth.c with binary digests e8fc0205... (bw_old) and fd7c14df... (bw_new). BENCH/bandwidth.c has sha256 f1985072... today, so it is the source of bw_new.
- Flags of bw_old and bw_new: `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11` (K13/run_kernels.sh:19). The runner adds `-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4`.
- `k_read` of bw_old has the same instructions as `k_oldread` of bwx8 (70 lines compared). `k_read` of bw_new has the same instructions as `k_read` of bwx8. Listings: R/kernels-20261113T183218Z/probe.txt:23-37 (bw_new k_read) and :155 onward (bw_old k_read). Loop start modulo 64: 36 for bw_new k_read (0x1c64) and 40 for bw_old k_read (0x1b68), the same values as in bwx8.

## (b-H2) The original benchmark: functions called in step H2

Command line of every H2 process (X8/run_h2.sh:94): `<bw_old|bw_new> --threads 1 --cpus <cpu> --bytes 8M --kernel read --reps 3 --min-ms 500`.

| # | Function | bw_new: BENCH/bandwidth.c | bw_old: K13/bandwidth.orig.c | What it does |
|---|---|---|---|---|
| 1 | `main` | 496-620 | 339 onward | Parses the options (`parse_cpus` 81, `parse_bytes` 63). Creates 1 worker thread (:563-570). For each of the 3 repetitions it releases the worker and waits (`pthread_barrier_wait` twice, :582-583), then prints one row (:584-603) and the "best" row (:605). |
| 2 | `worker` | 446-484 | 288-327 | `pin_cpu`, `alloc_buf`, `k_write` (first touch). Per repetition: 1 warm-up `pass`, barrier, t0 = `now_s`, then repeat { `passes_per_check` times `pass`; t1 = `now_s` } until t1 - t0 reaches 0.5 s. Stores bytes and elapsed seconds. |
| 3 | `pin_cpu` | 108-117 | 107-116 | `sched_setaffinity` to one CPU. |
| 4 | `alloc_buf` | 119-134 | 118 onward | Buffer at a 2 MiB boundary, `MADV_HUGEPAGE`. |
| 5 | `now_s` | 56-61 | 55-60 | CLOCK_MONOTONIC as seconds (double). |
| 6 | `pass` | 418-444 | 260 onward | One pass: `k_read(t->a, n)`. In bw_old the returned sum goes to the sink (:264). |
| 7 | `k_read` | 184-211 (new read, load-only) | 138-148 (old read, 16 sums) | The kernel. |

- `passes_per_check` = 8 MiB / bytes, at least 1 (BENCH/bandwidth.c:452-454). At 8 MiB it is 1, as in the runner.
- Differences to the runner that matter for a reader: one repetition is one 0.5 s interval with a warm-up pass and two barrier waits before it, the store value changes per pass (`v + p`, used by write kernels only), and no per-window record array exists.

Proposed excerpts: BENCH/bandwidth.c:465-482 (the repetition loop of `worker`), BENCH/bandwidth.c:418-423 (`pass`, read case), K13/bandwidth.orig.c:138-148 (old `k_read`), BENCH/bandwidth.c:598-603 (the output row).

## (f) Real plan files, command lines and row legend

Step ZS, X11/sched11/s1/ZS/0000.plan (whole file, 4 lines):

```
# bwx8-plan v1
# step=ZS session=1 cpu=2 bytes=6291456 proc=0 kernel=asmread size=6291456 seed=2026111505 test=0
# trial cond rep prev pfx pred tgt nwin win_ms count bins
0 K=asmread|S=6291456|count=read 1 - - - asmread@6291456 20 300 read 0
```

Step ZN, X11/sched11/s1/ZN/0000.plan (whole file, 7 lines):

```
# bwx8-plan v1
# step=ZN session=1 cpu=2 bytes=32768 proc=0 rep_set=1 kernel=read_nop64 size=32768 seed=1612744531 test=0
# trial cond rep prev pfx pred tgt nwin win_ms count bins
0 K=read_nop64|S=32K 1 - read_nop64@32K:1200 - read_nop64@32K 4 300 closed 0
1 K=read_nop64|S=32K 2 - read_nop64@32K:1200 - read_nop64@32K 4 300 closed 0
2 K=read_nop64|S=32K 3 - read_nop64@32K:1200 - read_nop64@32K 4 300 closed 0
3 K=read_nop64|S=32K 4 - read_nop64@32K:1200 - read_nop64@32K 4 300 closed 0
```

A ZN plan of a proving kernel at 8 MiB: X11/sched11/s1/ZN/0012.plan (read_nop96 at 8 MiB on CPU 2, see the launch line R/bwx11-ZN-s1-20261115T092141Z/ZN.csv:1165).

Step S2, X8/sched/s1/S2/0000.plan lines 1-4:

```
# bwx8-plan v1
# step=S2 session=1 cpu=2 bytes=1048576 proc=0 rep_set=1 kernel=read size=1048576 seed=1926220671 test=0
# trial cond rep prev pfx pred tgt nwin win_ms count bins
0 K=read|S=1M 1 - read@1M:1200 - read@1M 4 300 closed 0
```

Legend of a trial line (11 fields, checked in `plan_trial`, bwx11.c:2247-2290):

| Field | Meaning |
|---|---|
| trial | trial number, from 0 |
| cond | name of the condition (text for the analysis) |
| rep | repeat number of this condition, 1 to 4 |
| prev | previous activity, KERNEL@SIZE:MS or "-" (1 window) |
| pfx | prefix, KERNEL@SIZE:MS or "-" (4 windows of MS / 4 each; 1200 gives 4 x 300 ms) |
| pred | predecessor, KERNEL@SIZE:MS or "-" (1 window) |
| tgt | target, KERNEL@SIZE |
| nwin | number of target windows |
| win_ms | length of one target window in ms |
| count | counters: closed, open, or read (read = one group read at every target window boundary) |
| bins | 1 = also record 10 ms bins inside the target windows |

So one S2 or ZN process = 4 trials x (4 prefix windows + 4 target windows) of 300 ms = 9.6 s of kernel work. One ZS process = 1 trial of 20 target windows of 300 ms = 6 s.

Real runner command lines (from the header lines of the result files):

- S2, R/bwx8-S2-s1-20261115T003207Z/S2.csv:1: `bwx8 --trial --cpus 2 --bytes 1048576 --plan sched/s1/S2/0000.plan`
- ZN, R/bwx11-ZN-s1-20261115T092141Z/ZN.csv:1165: `bwx11 --trial --cpus 2 --bytes 8388608 --plan sched11/s1/ZN/0012.plan`
- ZS, R/bwx11-ZS-s1-20261115T100610Z/ZS.csv:1: `bwx11 --trial --cpus 2 --bytes 6291456 --plan sched11/s1/ZS/0000.plan --pmu-type 11 --events cpu_cycles=0x11,l1d_cache_lmiss_rd=0x39,l2d_cache_refill=0x17,l2d_cache_wb=0x18,bus_access=0x19,l2d_cache_lmiss_rd=0x4009`
- H2, R/h2-s1-20261115T063514Z/env.txt (line "## command line of every process"): `<binary> --threads 1 --cpus <cpu> --bytes 8M --kernel read --reps 3 --min-ms 500`

The header line that the run script writes before each process (R/bwx11-ZS-s1-20261115T100610Z/ZS.csv:1):

```
-- step ZS session 1 idx 0 tag asmread-6291456-cpu2 waited_s 0 loadavg 0.72 0.93 0.98 1/1093 logins 0 utc 10:06:10 args --trial --cpus 2 --bytes 6291456 --plan sched11/s1/ZS/0000.plan --pmu-type 11 --events ...
```

Output rows of the runner (legend printed by `trial_worker`, bwx11.c:2054-2064; real rows from R/bwx11-ZS-s1-20261115T100610Z/ZS.csv:49, :51, :71, :92):

```
S,0,K=asmread|S=6291456|count=read,1,-,-,-,asmread@6291456,20,300,read,0,none,none
W,0,target,0,asmread,6291456,20459814912,31575871,331651063
C,0,0,300072480,300072480,299908396,839656786,112271970,239890291,239858578,959498118,180392
E,0,6000811328,5998072832,0,7,NA,3952,NA,read
```

| Row | Fields |
|---|---|
| M | name, value: settings and addresses of the process (cpu, bytes, check_bytes, events, plan.* pairs) |
| K | kernel, address of the function, address modulo 64 |
| S | trial, cond, rep, prev, pfx, pred, tgt, nwin, win_ms, count, bins, prev_cond, prev_tgt |
| P | trial, when (pre or post), kB_total, kB_huge, thp_fault_alloc, thp_fault_fallback, thp_collapse_alloc, pgmigrate_success |
| W | trial, phase, widx, kernel, pass_bytes, bytes, t_start_ns, t_end_ns |
| C | trial, widx, enabled_ns, running_ns, cputime_ns, then one count per event in the order of `--events` |
| E | trial, wall_ns, cpu_ns, nvcsw, nivcsw, gap_ns, max_boundary_gap_ns, sink_ok, count_state |
| X | trial, code, text: a failure or a mark. 0 X rows in all 41 folders (A/final8.txt block 1). |

Output of the original program (R/h2-s1-20261115T063514Z/H2.csv:1-7): one header line of run_h2.sh, then

```
kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps
read,1,8388608,0,33470545920,0.5000,66.94,66.94,66.94,66.94
```

## Notes for the page author (found while mapping; each is checked against A/final8.json)

1. Step ZN alone does not hold asmread. Its kernels are read_nop64, read_nop96, read_nop128 (X11/schedule11.py:64). The asmread 8 MiB levels in the ZN rule and in the supplementary gain come from step YF of the same session (binary bwx10, run by X10/run_bwx10.sh through X10/visit10.sh, plan example X10/sched10/s1/YF/0003.plan). Source: `asmread_source` in A/final8.json under families/ZN and supplementary/gain_from_two_rates, code A/final8.py:935-938 and :2513-2518. The 12 cells of the supplementary gain are oldread (from S2), read_nop96 and read_nop128 (from ZN), 2 CPUs x 2 sessions each. If the page shows the ZN test code, it must name YF as the source of the asmread rate. `k_asmread` of bwx10 has loop offset 20 as in bwx8 and bwx11 (X10/crb-build-1/offsets.tsv).
2. The 11 counted sizes of the ZS rule exclude 1 MiB and 8 MiB (`ZS_EXCLUDED`, A/final8.py:1817; DECISIONS line 367). The band was derived from the 1 MiB and 8 MiB numbers of session 1 (DECISIONS line 365), so those two sizes are printed and not counted. The one size outside is 32 MiB on CPU 2 and 6 MiB on CPU 41, in both sessions.
3. "Old read costs about 2.67 cycles per line at every size from 1 to 16 MiB" has exceptions in A/final8.json (ZS, rule, oldread). Session 1: 2.710 at 2 MiB on CPU 2, 2.737 at 2.5 MiB on CPU 41. Session 2: 2.707 (2 MiB), 2.817 (2.5 MiB), 2.716 (3 MiB) on CPU 2, and 2.801 (2.5 MiB), 2.707 (3 MiB) on CPU 41. The recorded old-read check holds at 8 of 9, 6 of 9, 8 of 9 and 7 of 9 sizes with r below 0.83 (cells CPU 2 session 1, CPU 2 session 2, CPU 41 session 1, CPU 41 session 2). At 1, 4, 5, 6, 8, 12 and 16 MiB the value is 2.669 to 2.679 in all four cells.
4. Numbers that I compared with A/final8.json and found equal: S2 gain at 1 MiB 27.01 to 27.03 %; S2 gain at 8 MiB 3.35 to 6.75 % (kernel read); P1 "equivalent" in 4 of 4 cells with largest |d| + limit 0.080 to 0.201 GB/s against the 0.30 margin; P2 medians -13.65 to -15.92 GB/s (read); new-loop share 100.1 to 100.3 %; ZS 1 of 11 outside in each of 4 cells; fitted lines 2.089 + 0.658 r, 2.083 + 0.667 r, 2.079 + 0.646 r, 2.074 + 0.663 r; asmread at 8 MiB r 0.820 to 0.827 and 2.505 to 2.596 cycles per line (ZS); ZN read_nop96 C 54.94 and read_nop128 C 42.89 GB/s, loss from 32 KiB to 8 MiB -0.08 to -0.00 GB/s (the 8 MiB median is not lower), "prediction holds" 4 of 4 each; supplementary gain 12 of 12 inside; H2 CPU 2 median gain 0.22 % and 0.17 % with 36 of 36 and 35 of 36 low repetitions, CPU 0 5.73 % and 5.71 %, verdicts cpu2 "supported", cpu0 "rejected", cpu41 "undecided".
5. The task text gives "2.50 to 2.67" cycles per line for the new loop at 8 MiB. Step ZS alone gives 2.505 to 2.596. The value 2.67 is the low-level value from the counter steps of rounds 2 and 4 (DECISIONS line 365), not a ZS cell median.
6. read_nop64 is in step ZN and does not follow the simple prediction (class "between 66 and 76", prediction fails in 3 of 4 cells). The conclusion uses only read_nop96 and read_nop128. The page should say that read_nop64 was run and where its result is (A/final8.txt block 7), or it shows only part of step ZN without saying so.
