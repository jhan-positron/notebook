# Facts sheet: why the whole-chip read rate fell with the new read kernel (2026-11-15)

This sheet is the source for the report. Every number was recomputed from raw files by an independent checker
agent (workflow wf_9d39bfdd-935); corrected values are used here. GB = 1e9 bytes. "64+56" = 64 threads on
CPUs 0-63 (mesh 0) + 56 threads on CPUs 64-119 (mesh 1), 256 MiB per thread, read from DRAM.

Paths: R = /home/jhan/workspace/titan/cache-perf/crb/results ; W = /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15
Runner: W/../bwx12-2026-11-15/bwx12.c (bwx11 + 26 kernels), binary sha256 cd58e564...546a on CRB ~/cache-perf/bwx12-20261115/bwx12.
Run scripts: W/r0.sh, rx.sh (plain runs), rg.sh (simultaneous processes), rc.sh, rc2.sh, rgc.sh (root counters via sudo perf stat -a).
Analysis scripts: W/an.py, anc.py, anc2.py, anc3.py, anc4.py, ang.py. Window test: W/robsize/.
All runs 2026-11-15 16:56 to 21:03 UTC, Sunday, no block announced in Slack #phoenix-crb, marker file absent,
no other logins. Load (env.txt and launches.txt of the 14 folders R/w120-*): the 1-minute load average at script start was 0.00 to 71.24,
and up to 109.60 at process launch, with 1 runnable task and 0 logged-in users at all 101 launches. High values follow the script's own
earlier 120-thread processes (hypothesis: decay of the load average; not checked further). The scripts wait until at most
2 tasks are runnable. Root: the user approved sudo perf stat (and temporary settings changes; none was made).

## The question
Original observation (R/kernels-20261113T181222Z/threads120.csv, benchmark bandwidth.c, whole-pass stop, 0.5 s):
- read: old C kernel 464.4-466.7 GB/s, new C kernel 279.7-304.1, asm kernel 271.1-305.9 (n=6 each).
- write: old 140.9-186.9 (median 144.6), new 123.5-147.8 (median 131.9).
- copy (read+written bytes): old 155.0-158.6, new 153.9-162.4. No drop.

## F1. Only read really dropped
- Copy: 64+56, common stop, 6 s (R/w120-R1-20261115T185140Z/p4copy.csv, n=2 intervals each): oldcopy 152.7-153.0,
  asmcopy 152.4-152.6, new C copy 152.7-153.4, copy_nop96 153.2-153.6, copy_nop192 153.3-153.4 GB/s.
- Write: 64+56, common stop, 8 s (p3write.csv, n=2 each): oldwrite 126.1-126.8, asmwrite 121.3-121.8,
  new C write 121.4-129.3, write_nop32/96/128/256 120.2-122.9. Padding does not change write.
- Earlier controlled runs (R/B10a-*, R/B10b-*, 64 processes, 64 intervals per cell), median total GB/s, old write vs new C write:
  whole-pass stop 0.5 s: 144.1 vs 118.6 (+21.5 %); whole-pass stop 15 s: 131.3 vs 117.4 (+11.9 %);
  common stop 0.5 s: 126.4 vs 122.0 (+3.7 %); common stop 15 s: 126.6 vs 122.8 (+3.1 %).
  So most of the write drop in the original run comes from the whole-pass stop rule of bandwidth.c; 3 to 4 % remains with a common stop.
  In the original file, at equal pass count (296 passes) old write is 144.2-145.6 and new write 143.6 and 147.8 GB/s.
- Writers on one mesh only (64+0): 455 GB/s for oldwrite, asmwrite, write_nop128, write_nop256 (p6w6400.csv). 32+32: 204-209 (p7w3232.csv).
  The write collapse with writers on both meshes is the same for old and new kernels; it is not explained here.

## F2. The read drop depends on how many cache lines the core's out-of-order window covers
Window test (W/robsize, one thread on CPU 2, method: two independent cache-missing loads separated by N filler units;
the N where time per iteration jumps from about 1 miss time to about 2 is the capacity): 684 nop; 159 vector-register writes
(NEON add, ldr q, or 2 per ldp q); 191 integer adds; and directly, with one loop body of each kernel as the unit (window depth in 64 B lines,
"last N that fits x lines per unit" to "first N that does not fit x lines per unit"). File W/robsize/results/rob-k1/k2/k3-*.csv.

Total at 64+56 (GB/s, min-max over all intervals; n = intervals; 12 processes, 177 intervals in total; R0, R0b, R1, R5, R6 folders) and window depth (lines):
| kernel | what the loop holds per iteration | window depth, lines | total GB/s | n | state |
| read_1pl | 4 ldr q, one per line (256 B) | 156-164 | 230.2-235.0 | 16 | slow |
| read_sparse (sp9) | 4 ldp + 9 nop (128 B) | 38-42 | 294.6-301.5 | 6 | slow |
| asmread (= new C read) | 8 ldp q (256 B) | 36-40 | 288.5-309.8 | 22 | slow |
| read_pf2048 | 8 ldp + 4 prfm 2048 B ahead | 36-40 | 290.5-306.8 | 11 | slow |
| read_nop32 | 8 ldp + 32 nop | 36-40 | 284.8-302.7 | 4 | slow |
| read_nop48 | 8 ldp + 48 nop | 32-36 | 305.4-307.2 | 2 | slow |
| read_dadd2 | 8 ldp + 2 vector adds | 32-36 | 290.1-296.4 | 2 | slow |
| read_sp24 | 4 ldp + 24 nop (128 B) | 32-34 | 280.9-283.2 | 2 | slow |
| read_nop56 | 8 ldp + 56 nop | 28-32 | 308.6-309.1 | 2 | slow |
| read_dadd4 | 8 ldp + 4 vector adds | 28-32 | 280.1-283.2 | 2 | slow |
| read_nop64 | 8 ldp + 64 nop | 28-32 | 325.5-333.9 | 13 | between |
| read_sp32 | 4 ldp + 32 nop (128 B) | 26-30 | 366.3-366.6 | 2 | between |
| read_nop72 | 8 ldp + 72 nop | 24-28 | 459.0-459.3 | 2 | fast |
| read_dadd8 | 8 ldp + 8 vector adds | 24-28 | 462.4-462.6 | 2 | fast |
| read_1pl_nop96 | 4 ldr q + 96 nop | 24-28 | 460.8-460.9 | 2 | fast |
| read_nop80 | 8 ldp + 80 nop | 24-28 | 459.7-459.8 | 2 | fast |
| read_sp40 | 4 ldp + 40 nop (128 B) | 22-24 | 466.8-466.9 | 2 | fast |
| read_nop88 | | 20-24 | 462.8-462.9 | 2 | fast |
| read_nop96 | | 20-24 | 465.5-470.6 | 16 | fast |
| read_sp48 | | 20-22 | 470.0-470.1 | 2 | fast |
| oldread (old C read) | 4 ldp + 8 vector adds (128 B) | 18-22 | 465.5-470.1 | 22 | fast |
| read_sp56 | | 18-20 | 473.6-473.7 | 2 | fast |
| read_dadd16 | 8 ldp + 16 vector adds that use the loaded data | 16-20 | 466.7-469.8 | 5 | fast |
| read_iadd16 | 8 ldp + 16 vector adds that do NOT use the loaded data | 16-20 | 469.2-469.7 | 2 | fast |
| read_nop112 | | 16-20 | 471.1-471.2 | 2 | fast |
| read_nop128 | | 16-20 | 473.8-476.4 | 9 | fast |
| read_nop160 | | 12-16 | 477.9-478.2 | 2 | fast |
| read_nop192 | | 12-16 | 479.6-479.8 | 2 | fast |
| read_nop256 | 8 ldp + 256 nop | 8-12 | 543.9-549.0 | 9 | fastest |
Also read_pf256 289.1-300.1 (n=4), read_pf512 302.3-303.9 (n=2), read_pf1024 311.8-315.8 (n=2): software prefetch does not restore the rate.
Reading: every variant with a window of 32 lines or more is slow (280-310 GB/s; 230-235 for 160 lines); every variant with 28 lines or
fewer... precisely: all variants whose measured range is at or below 24-28 are fast (459-480), the four variants measured at 26-32 (read_nop56, read_dadd4, read_nop64, read_sp32) are slow or between.
The old read loop is fast because its 8 vector adds per 128 B use up vector registers (the window holds 159 vector-register writes), not because the adds wait for data:
adds that do not use the loaded data (read_iadd16) give the same total as adds that do (read_dadd16).
Per-thread rates: slow state mesh 0 2.5-2.75 GB/s, mesh 1 2.25-2.45; fast state (459-480 group) mesh 0 4.27-5.45, mesh 1 2.51-2.78; read_nop256 mesh 0 4.99-5.22, mesh 1 3.84-3.97.
4 KiB pages instead of 2 MiB pages (R/w120-R5-*/nothp.csv, P rows show 0 kB on huge pages): same picture: oldread 466.0-468.5, asmread 298.0-300.3, read_nop64 325.9-326.1,
read_nop96 467.7-467.8, read_nop256 543.9-545.0, read_1pl 234.8-235.0, read_pf2048 297.6-302.5 (differences to the huge-page process -2.4 % to +0.2 %; one process per page size).
Other layouts (R/w120-R0b-*, one interval per cell; second process for 56+56 in R1 p5r5656.csv), total GB/s, oldread | asmread | read_nop96 | read_nop128:
56+56: 534.8 | 300.1 | 538.1 | 547.1 ; 48+48: 412.1 | 349.9 | 414.4 | 417.2 ; 64+44: 432.9 | 356.3 | 437.2 | 435.0 ; 64+32: 412.2 | 445.0 | 417.8 | 413.4 ;
64+0: 348.0 | 348.4 | 349.0 | 351.0 ; 0+56: 318.0 | 318.1 | 319.2 | 321.7 ; 32+32: 336.9 | 336.5 | 339.9 | 341.9.
So the padded loop follows the old read loop in every layout (within 2.3 %), including 64+32 where the load-only loop is 8 % faster, and the drop exists only with many threads on both meshes.

## F3. A thread's rate depends on the other threads' loop: the deeper window takes the larger share
Two processes at the same time, one per mesh (R/w120-R3-20261115T193922Z, 12 s, overlap 98.8-99.97 %), sum GB/s mesh 0 | mesh 1:
asmread | asmread: 175.7 | 127.2 (total 302.9) ; read_nop256 | read_nop256: 327.4 | 221.8 (549.1) ; read_nop96 | read_nop96: 318.9 | 150.7 (469.5) ;
asmread | read_nop256: 349.8 | 108.2 (457.9) ; read_nop256 | asmread: 137.3 | 251.3 (388.6) ; asmread | read_nop96: 331.9 | 116.2 (448.1) ;
read_nop96 | asmread: 149.5 | 154.3 (303.8) ; read_nop96 | read_nop256: 347.8 | 123.5 (471.3) ; read_nop256 | read_nop96: 238.1 | 254.2 (492.3).
Mesh 0 alone with asmread reads 348 GB/s. So with asmread on mesh 0 and a padded loop on mesh 1, mesh 0 reads as if it were alone and mesh 1 is squeezed to 108-116.
Mixed inside both meshes (even CPUs asmread, odd CPUs read_nop256): asmread threads 3.04-3.36 GB/s, read_nop256 threads 1.99-2.20, total 318.2. With read_nop96: 2.63-3.08 vs 2.06-2.40, total 306.3.
All read_nop256 in the same split: 548.3; all asmread: 300.3.

## F4. In the slow state nothing in the chip is congested and DRAM does no extra work
Latency probe (R/w120-R4-20261115T200016Z): one core per mesh (CPU 2, CPU 66) runs a pointer chase with one or two DRAM misses in flight while the other 118 cores stream.
Time per chase step, CPU 2 | CPU 66: idle machine 146.9 | 146.9 ns; all asmread (total 298 GB/s) 203.1 | 211.3; all read_nop256 238.0 | 246.9; all read_nop96 286.5 | 238.1;
asmread on mesh 0 + read_nop256 on mesh 1: 297.1 | 236.4; reverse: 212.9 | 223.5; all read_1pl 219.2 | 219.4; asmread on mesh 0 only: 278.0 | 165.5.
So one memory request takes less time in the slow state than in the fast states.
Estimated lines in flight per streaming core = lines per second per thread x probe time (est.; assumes a stream request takes as long as the probe's request):
slow or squeezed meshes 6.5-9.2 (asm/asm 8.4 and 7.9; squeezed read_nop256 7.0-7.6; read_nop96 mesh 1 9.2; read_1pl 6.5-7.1); fast meshes 14.9-25.3 (mesh 0 19.2-25.3; asmread on mesh 0 alone 23.4).
Mesh counters, root, per 64 B line read, 64+56, slow (asmread 299 GB/s) | fast (read_nop96 470) | fast (oldread 468) (R/w120-RC1-20261115T190208Z, no multiplexed row):
home-node request retries (hns_pocq_retry_all) 0.047 | 0.072 | 0.069 ; home-node queue occupancy (hns_qos_pocq_occupancy_all) 0.087 | 0.121 | 0.118 ;
memory-controller retries (hns_mc_retries_local_all) 0.0046 | 0.043 | 0.039 ; gateway data stalls (ccra_chidat_stalls) 0.21 | 0.73 | 0.73 ;
home-node busy level 3 (hns_cbusy11_all) 0.21 | 1.49 | 1.53 ; request-link stalls east (mxp_e_req_txflit_stall) 0.013 | 0.167 | 0.163 ; data-link stalls east 0.162 | 0.344 | 0.351.
Exception: north and south data-link stalls are higher in the slow state (north 0.119 | 0.069 | 0.073; south 0.027 | 0.020 | 0.025).
Memory ports, 24 ports (R/w120-RC2-20261115T192222Z), per line read: asmread 64+56 (307 GB/s) | read_nop96 (468) | read_nop256 (550) | asmread 64+0 (349):
read requests into the ports 1.004 | 1.002 | 1.076 | 0.997 ; request stalls 0.0005 | 0.018 | 0.030 | 0.000 ; write data into the ports 0.0004 | 0.0003 | 0.0003 | 0.0003 ; data flits out 1.992 | 1.996 | 1.995 | 1.995 (2 flits = 1 line).
So DRAM gets one read per line and no writes in both states; no read is wasted.
Where the data for a core comes from (R/w120-RC5-*, watchpoints at 4 core ports per mesh), per line: 1.0 flit pair... precisely 0.50+0.50 flits from the two memory-port columns of the own mesh and 1.00 flit from the gateway row, in every state (slow, fast, squeezed, alone). So half of the lines arrive directly from the own mesh's memory ports and half through the gateway from the other mesh, always.
Busy level on responses that reach the cores (R/w120-RC4-*, RC6-*): response messages with busy level 0: slow or squeezed meshes 82-93 %; fast meshes 4-26 %; three in-between cases 44-74 % (mesh 1 under read_nop96 or oldread at 64+56: 73-74 %; mesh 1 running asmread against read_nop256 on mesh 0: 44-46 %). Data that arrives through the gateway carries busy level 3 in 89-100 % of flits in every state, also with the other mesh idle.
So the squeezed cores do not receive a higher busy level than the fast cores.
Core counters per line are the same in slow and fast states: bus_access 2.08, L2 refills 1.000, L2 hardware-prefetch events 1.000, instructions as coded; cycles per line 66-77 (slow) vs 35-37 (fast, mesh 0). Core clock 2.8 GHz in all.

## F5. The drop needs a sequential stream: a load-only loop in scrambled order does not show it (added 21:05 UTC)
Runner bwx13 (bwx12 + rand_nop0, rand_nop96, rand_nop256; folder ../bwx13-2026-11-15, binary sha256 a2858df5...8dad). The rand kernels read the same bytes as asmread
(8 ldp q per 256 B block, every block once) but visit the 8192 blocks of each 2 MiB chunk in a scrambled order (block index (i*(2i+1)) mod 8192), then 0, 96 or 256 nop.
The window depth in lines is that of asmread, read_nop96, read_nop256 (same loads and padding, plus 5 integer instructions).
One thread, 256 MiB, CPU 2 (smoke test smoke13.txt; two runs of 0.5 s per loop used, both stop=common: one for the rate, one with counters; corrected 2026-11-15 after review, was "one run"): asmread 35.7 GB/s, rand_nop0 10.8, rand_nop96 8.4, rand_nop256 4.8 (per line, counter run: L2 refills 1.63-1.64 against 1.00, loads that miss all caches 0.41-0.42 against 0.00-0.06 (asmread 0.05, read_nop96 0.03, read_nop256 0.00: 252 events for 176 million lines; corrected, was "0.03-0.06"), L2 hardware-prefetch events 1.84-1.91 against 1.00).
The hardware prefetcher is therefore not idle in scrambled order; the rand kernels do not show the cores without prefetch. A second counter run with stop=pass gives for the rand kernels 1.44-1.51 L2 hardware-prefetch events and 0.58-0.60 loads that miss all caches per line.
64+56, two processes at the same time, 10 s, one interval per cell (R/w120-R7-20261115T205946Z), sum GB/s mesh 0 | mesh 1 (total):
rand_nop0 | rand_nop0: 268.8 | 220.8 (489.6) ; rand_nop96 | rand_nop96: 250.5 | 222.9 (473.5) ; rand_nop256 | rand_nop256: 204.3 | 178.3 (382.5) ;
rand_nop0 | rand_nop256: 264.2 | 158.1 (422.3) ; rand_nop256 | rand_nop0: 192.5 | 230.0 (422.6) ;
rand_nop0 | read_nop256: 182.8 | 278.8 (461.6) ; read_nop256 | rand_nop0: 307.2 | 158.4 (465.6) ;
asmread | rand_nop256: 282.9 | 134.2 (417.1) ; rand_nop256 | asmread: 127.5 | 266.5 (393.9) ;
controls in the same run: asmread | asmread: 166.3 | 131.5 (297.8) ; read_nop256 | read_nop256: 328.5 | 218.7 (547.2).
Mesh 0 alone: rand_nop0 342.8, rand_nop256 223.3.
Per thread, rand_nop256 | rand_nop256 at 64+56: 3.15-3.22 GB/s (one thread alone: 4.8 GB/s). Hypothesis, not tested: part of the fall to 382.5 is the core's own limit with 256 nop; a run of rand_nop256 with fewer threads per mesh would test it.
Reading:
- In scrambled order the deep window is the faster one: 489.6 (no padding) > 473.5 (96 nop) > 382.5 (256 nop). In sequential order it is the reverse: 297.8 < 465-471 < 547.
- The same loads with the same window read 489.6 GB/s in scrambled order and 297.8 GB/s in sequential order. So the deep window alone does not lower the total. In this run the drop appeared in sequential order and did not appear in the one scrambled order tested (one interval per cell; window depth of the rand kernels assumed, not measured).
- So the rule that lowers the lines in flight is in how the cores treat a sequential stream (hypothesis for the part inside the core: hardware prefetch and its request limit, see H-a below), not in the mesh, the gateways or DRAM. This narrows the open item; the exact core rule is still not established (the V3AE prefetch controls are not readable from Linux user space).

## What is established
1. Read is the only real drop. Its size at 64+56: about 300 vs about 468 GB/s (-36 %).
2. Cause in the benchmark: the load-only loop lets the core's window cover 36-40 lines; the old loop covered 18-22. Above about 30 lines the 120-thread total falls; below it stays. Vector adds are not needed.
3. Mechanism as far as measured: cores (or prefetchers) whose loop covers more lines take a larger share; a whole mesh then runs with about 8 lines in flight per core instead of about 20, although each request is served faster. Nothing is congested, DRAM does one read per line.
4. Remedy verified: padding the load-only loop (72 nop or more per 256 B) restores 459-480 GB/s; 256 nop gives 544-549 GB/s, 17 % above the old kernel.

## What is not established ("Insufficient data")
- Which rule inside the core lowers the number of lines in flight for a sequential stream in the slow state (F5 places it in the cores, not in the mesh). Candidates (hypotheses):
  H-a: the cores' request limit or prefetch aggressiveness is set dynamically. The Neoverse V2 manual documents a dynamic limit of outstanding requests from the L2 transaction queue driven by the busy level (IMP_CPUECTLR2_EL1 TXREQ_LIMIT_DYNAMIC) and adaptive prefetch modes (PF_MODE); whether V3AE has it and how firmware set it is not known. Against a simple form of H-a: squeezed cores receive lower busy levels.
  H-b: a prefetcher that adapts its distance to timeliness, combined with the in-order need for both halves of the lines (own-mesh half and other-mesh half).
  Measurement that would resolve it: read IMP_CPUECTLR_EL1 and IMP_CPUECTLR2_EL1 on CRB (needs a kernel module or firmware access), the V3AE manual's prefetch section, or a question to Arm support with the data of F3 and F4.
- Why the write total collapses with writers on both meshes (same for old and new kernels).
- The 3 to 4 % by which old write stays above new write under a common stop.

## Recommendation for the benchmark
- Keep the new load-only kernels for one-thread and cache-size measurements (they measure the load path without extra work).
- For whole-chip DRAM read numbers, state the loop: report the load-only loop and a window-limited loop (for example read_nop256: 544-549 GB/s at 64+56, 23 GB/s core-bound with one thread at 32 KiB). The old read loop's 465-470 GB/s is one point on this curve, not a chip constant.
- For write totals use a common stop time or a long interval; the whole-pass rule with 0.5 s moves old write by +14 % (144 vs 126 GB/s median).
- bench/bandwidth.c was not changed.
