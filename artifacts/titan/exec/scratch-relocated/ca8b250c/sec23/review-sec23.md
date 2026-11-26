# Review of core page section 2.3 (boot F1 against run 3), 2026-11-07, asimov-04

Short version. A 108-agent workflow (six finders, three refuters per finding) checked every number and claim in section 2.3 against the 004 and 011 folders, the READMEs and the rest of the page. 33 findings survived, 1 was refuted. The ratio table itself is right in every one of the 112 rows that were recomputed; the defects are in the prose around it (captions and Short version that contradict the table, one 'quoted' table that carries the author's verdicts, two wrong facts).

Spot-checked by asimov-04 from the raw files: 68.1 % run 3 OCM spread, no one-core 16 MiB row on F1, ToC/heading mismatch, section 9 wording, 2 MiB read is a bandwidth command.

## 1. [wrong] The sparse OCM rows spread up to 60 % between passes inside one boot
- Stated: up to 60 %
- Found: Run 3's largest within-row spread is 68.1 % (latency-ocm-region1-cpu2.csv, 7 passes, 21.359 to 35.906 ns); F1's largest is 59.7 % (latency-ocm-region0-cpu6.csv, 19.328 to 30.875 ns). The 011 README's table states '68.1%; 59.7%' for this group. So 'up to 60 %' holds for F1 only; across both boots the figure is 68 %.
- Evidence: Recomputed with python3 -I as (max - min) / min of ns_per_load over the non-best rows of every latency-ocm-region<r>-cpu<c>.csv under /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-004/results/19700101T000000Z/ and /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/results/bootF1/; /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md line 102.

## 2. [wrong] every write, every control and every chain beyond the L3 repeated run 3 (figure caption under the dot plot)
- Stated: every write repeated run 3
- Found: The pair writes at 48 and 160 KiB are 1.049 and 1.233 times run 3 (F1 61.943 and 58.250 GB/s against 59.070 and 47.241), and the all-eight-core write at 2 MiB is 1.064 times (165.154 against 155.154). The section's own table marks both groups 'faster on F1'. Only the one-core writes (1.000 to 1.003), the one-core-per-cluster writes (1.000) and the six placement rows (1.000 to 1.0003) repeated run 3.
- Evidence: bandwidth-pair.csv and bandwidth-all8.csv of 011 and 004; max aggregate_GBps over the rep rows per kernel and size, F1 over run 3 (script /tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/sec23/verify/bw.py)

## 3. [wrong] boots B and D read 2.38 and 2.38 GB/s at 32 MiB, one line per DRAM latency
- Stated: 2.38 GB/s is one 64 B line per DRAM latency
- Found: 2.377 GB/s is one 64 B line every 26.9 ns (64 / 2.377e9 s). Boot B's own DRAM chain latency is 52.248 ns (32 MiB fresh chain), 52.739 ns (flushed 8 MiB chain) and 52.762 ns (sequential 8 MiB chain, prefetchers off), so the stream moved about two lines per DRAM latency, not one. The 2.38 and 2.38 values themselves are right (B 2.377, D 2.377 GB/s, best of three reps, each rep 2.377). This phrase sits in the second hypothesis paragraph, outside the four paragraphs of this dimension, but it is attached to the B/D numbers the task listed.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-006/results/bootB/bandwidth-read-prefetch.csv and /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-008/results/bootD/bandwidth-read-prefetch.csv (read, 33554432, best 2.377); /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-006/results/bootB/latency-dram-large.csv (32 MiB best 52.248 ns), latency-dram-flushed.csv (52.739 ns), latency-dram-seq.csv (52.762 ns); 64 B / 2.377 GB/s = 26.9 ns computed by hand

## 4. [wrong] boots B and D read 2.38 and 2.38 GB/s at 32 MiB, one line per DRAM latency
- Stated: 2.38 GB/s equals one 64-byte line per DRAM latency
- Found: One 64-byte line per 52.7 ns (the flushed chain's DRAM time per load, section 5 and section 8) is 64 / 52.7e-9 = 1.21 GB/s. 2.38 GB/s is 2.38e9 x 52.7e-9 / 64 = 1.96 lines per DRAM latency, about two lines in flight, not one.
- Evidence: sec23.txt line 71; the 52.7 ns figure is the page's own (section 8: 'One DRAM read takes about 53 ns', flushed 8 MiB chain 52.659 ns of 010; section 2.2 quotes 52.762 ns on boot B). Arithmetic done by hand: 64 B / 52.7 ns = 1.21 GB/s.

## 5. [wrong] The sparse OCM rows spread up to 60 % between passes inside one boot (setup table) and (up to 60 % between passes of one row) (partly: page placement)
- Stated: largest pass spread of a sparse OCM row is 60 %
- Found: Over the 7 fresh passes of each of the 20 sparse rows, (max - min) / min is up to 68.1 % on run 3 (latency-ocm-region1-cpu2.csv) and up to 59.7 % on F1. 'Up to 60 %' holds for F1 only; run 3's largest spread is 68 %. The section cites no file for this number and the generator hard-codes it.
- Evidence: python3 -I over results/membench-jibin-004/results/19700101T000000Z/latency-ocm-region[0-4]-cpu[2468].csv and results/membench-jibin-011/results/bootF1/latency-ocm-region[0-4]-cpu[2468].csv: ns_per_load of the fresh1..fresh7 rows, spread = (max - min) / min per file, maxima 68.1 % (004) and 59.7 % (011). Jesse's F1 README line 146 gives the spread in ns only (5.2 to 14.5 ns on round three). sec_f1_vs_run3.py lines 79 and 103 hard-code '60 %'.

## 6. [misleading] Every cell is quoted from Jesse's two README files; nothing in this table is measured by this page.
- Stated: Every cell of the 10-row table is a quotation from the 011 or 004 README.
- Found: The first three columns are quotations (every fact checked against the READMEs, log.txt, sysinfo.txt and the CSVs). The fourth column, 'Can it move a core row?', is the author's judgment in 8 of 10 rows. Cells that no README states: 'run-to-run noise only (section 4.8, boot A against run 3)'; 'Yes: the one platform change'; 'No' (TF-A row); 'The pass and worker changes could move an L1-sized row by a few percent'; 'the PMU has 21 counters, so nothing is multiplexed' (the 'so' is the author's); 'OCM rows only, through page placement'; 'No: cme_test finished before any row' (the 'No' verdict); 'No: they ran after phases A to E' (the 'No' verdict). Only 'No (perf_cov 1.0000 on every row)' and the coverage caveat in the SCP row ('The register reading covers CPU 2's cluster only; clusters of CPUs 4 to 9 rest on the SCP's staging lines') are README statements (011 README, Read first bullet 2; Core rows, 'perf_cov 1.0000 in all 481 counted rows').
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md lines 8, 13, 78-91, 147 (the README says of the 16 KiB rows 'These files do not show why', and of moves between boots 'a move is a difference between these two boots, not by itself an effect of the L3 or of any other one thing that differs'); /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-004/README.md lines 18, 32, 39. Compared cell by cell by reading both READMEs.

## 7. [misleading] every write, every control and every chain beyond the L3 repeated run 3 (figure caption) and "the dependent chains beyond the L3 (within 4 %) ... repeated run 3" (Short version)
- Stated: Every chain beyond the L3 repeated run 3, within 4 %.
- Found: The fresh chains at 512 KiB, 768 KiB and 1 MiB (two to four times the 256 KiB L3) read 17.464, 20.023 and 22.823 ns on F1 against 23.084, 23.633 and 23.706 ns on run 3: ratios 1.32, 1.18 and 1.04. The section's own table lists this group as "Fresh chains 512 KiB to 1 MiB | 3 | 1.04 to 1.32 | faster on F1". The "within 4 %" figure (max deviation 3.77 %) holds only for the chains from 1.5 MiB on, as the "ruled out" bullet states ("the chains from 1.5 MiB on within 3.8 %").
- Evidence: latency-dram-large.csv of membench-jibin-011/results/bootF1 and membench-jibin-004/results/19700101T000000Z, lowest ns_per_load per size (equal to each file's best row), ratio run3/F1 computed with python3 -I; Jesse's F1 README line 141 gives the same three rows as 0.757, 0.847 and 0.963 times. The 512 KiB F1 passes count 0.54 to 0.56 0xA2 refills per load, so the L3 still serves part of this chain; the caption's "beyond the L3" reads as 'larger than the L3', which these rows are.

## 8. [misleading] the writes from 48 KiB on within 0.3 % (ruled out: Boards or run-to-run noise)
- Stated: writes from 48 KiB on within 0.3 %
- Found: True for the one-core writes only (max deviation 0.29 %, at 48 KiB). The pair writes at 48 and 160 KiB deviate 4.9 % and 23.3 %, the all-eight 2 MiB write 6.4 %. The generator computes this number from the one-core write group (wr1) but the sentence does not say 'one-core', so a reader takes it as all writes from 48 KiB on.
- Evidence: bandwidth-dram-1core.csv, bandwidth-pair.csv, bandwidth-all8.csv of 011 and 004; same recomputation as above

## 9. [misleading] the dependent chains beyond the L3 (within 4 %) ... repeated run 3 (Short version); every write, every control and every chain beyond the L3 repeated run 3 (figure caption); Fits: ... chains beyond th
- Stated: every dependent chain beyond the L3 is within 4 % of run 3
- Found: The section's own table lists chains beyond the L3's 256 KiB that moved more than 4 %: 'Fresh chains 512 KiB to 1 MiB' 1.04 to 1.32 (faster on F1), 'OCM, one line per page, per region' 1.05 to 1.44, 'OCM, one line per page, all five regions' 1.07 to 1.09. Only the chains from 1.5 MiB on hold within 3.8 %, which is what the 'ruled out: boards or noise' item says ('the chains from 1.5 MiB on within 3.8 %').
- Evidence: /tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/sec23/sec23.txt lines 3, 25, 29, 34, 35, 69, 77; section 2.2 of asimov-c1nano-perf.html calls the 512 KiB to 1 MiB rows 'the L3' (0.76 to 0.96 times), and table 4.1 labels 768 KiB and 1 MiB 'SLC (mesh cache)' with 0.84 and 0.91 L3 read refills per load. A reader who takes 'beyond the L3' as 'larger than 256 KiB' draws the wrong conclusion. Fix: say 'the chains from 1.5 MiB on (within 4 %)' and name the OCM chains and the 512 KiB to 1 MiB chains as moved.

## 10. [misleading] Every stream of independent reads got faster (1.2 to 2.9 times) (Short version); Every stream of independent reads got faster on F1, by 1.56 to 2.69 times for one core (figure caption)
- Stated: every independent read stream is faster on F1; one-core reads by 1.56 to 2.69 times
- Found: The table's 'One core, 16 KiB: read, write, copy' group is 0.96 to 1.02 and the 'ruled out: the build' item gives the 16 KiB one-core read at 0.965 and the pair's 16 KiB read at 0.966, both read streams that did not get faster. The one-core OCM reads (also one core) are 1.21 to 1.36, outside the caption's 'by 1.56 to 2.69 times for one core'.
- Evidence: sec23.txt lines 3, 25, 38, 42, 45, 75; Jesse's F1 README line 147 (16 KiB read 0.965, pair read 0.966). Fix: 'every read stream beyond the L1' and 'by 1.56 to 2.69 times for the one-core DRAM-address sweep, 1.21 to 1.36 for the one-core OCM reads'.

## 11. [misleading] a stream of independent reads overlaps more of its DRAM time (hypothesis 1)
- Stated: the read-stream rise is overlap of DRAM time
- Found: The rows that rose include reads that the page itself places outside DRAM: the one-core 2 MiB read (table 4.3 capacity reading 'SLC'), the 48 KiB, 96 KiB and 256 KiB one-core reads (L2 and L3 footprints, 1.56 to 2.59 times), the pair's 48 and 160 KiB reads (1.28 to 1.59) and the OCM reads (home nodes, 1.21 to 1.36). The hypothesis as worded explains only the DRAM rows; the 'Fits' list does not mention the L2, SLC and OCM rows it has to explain.
- Evidence: sec23.txt lines 39, 42, 43, 46, 69; asimov-c1nano-perf.html table 4.3 (2 MiB row 'SLC', 48 to 96 KiB 'L2') and section 12 open item ('the L2 and L3 footprints of the one-core sweep (48 to 256 KiB) rise 1.56 to 2.59 times as well'). Fix: 'overlaps more of its time behind the L1 (L2, L3, SLC, OCM or DRAM)' and list those rows under 'has to explain'.

## 12. [unsupported] run-to-run noise only (section 4.8, boot A against run 3)
- Stated: The board and date difference can move a core row by run-to-run noise only.
- Found: Neither README says this. The 011 README's own caveat (line 91) says boots with the L3 out of use 'also differ by more than these spreads in some rows (the 4 MiB chase's bests span 28.161-29.838 ns over rounds two and three and boots A to D), so a move is a difference between these two boots, not by itself an effect of the L3 or of any other one thing that differs'. The section 4.8 cross-reference exists (gen_perf_core.py line 489, 'Every row that moved 1 % or more between run 3 and boot E', which also carries the boot A against run 3 pair, gen_perf.py line 89), so the pointer is valid, but the cell is the page's inference, not a README quotation.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md line 91; /home/jhan/workspace/titan/cache-perf/asimov/gen_perf_core.py lines 215, 437, 489; /home/jhan/workspace/titan/cache-perf/asimov/gen_perf.py line 89.

## 13. [unsupported] OCM rows only, through page placement
- Stated: The /dev/ocm module difference can move only OCM rows, and only through page placement.
- Found: Neither README states this. The 011 README says the module 'maps OCM as round three's did, in single 4 KiB entries' and that 'every command is its own process on each boot, so its buffers need not sit on the same physical pages; round three's OCM placements are unknown (no map lines)'. It does not say which rows the module can move or that placement is the only path. The cell is a reasonable deduction from those two statements, not a quotation.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md lines 83 and 87, and OCM mappings (lines 255-262).

## 14. [minor] Yes: the one platform change.
- Stated: The SCP firmware is the only platform change between run 3 and boot F1.
- Found: The 011 README's Platform facts name two platform components that differ from round three: 'round three's apart from the SCP, the /dev/ocm module, his programs and the init'. The section's own Short version says 'the one platform change that matters'; the table cell drops 'that matters'. The /dev/ocm module row of the same table lists the second platform difference.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md line 341 (Platform facts, first paragraph) and lines 82-83.

## 15. [minor] the PMU has 21 counters, so nothing is multiplexed
- Stated: The 21-counter PMU is why no event was multiplexed.
- Found: The 011 README states the count ('armv9_c1_nano, 21 counters (20 plus the cycle counter; dmesg.txt line 189)') and separately that 'perf_cov' is 1.0000 in all 481 counted rows and no '# perf:' line exists; it does not draw the 'so'. The 004 README says 'none was multiplexed' only of the mesh PMU. The conclusion is true by the data (I counted 481 data rows with perf_cov on F1 and 411 on run 3, every one 1.0000), but the causal clause is the author's.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md lines 13 and 349; /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-004/README.md lines 22, 39, 40. perf_cov recomputed with python3 -I over every CSV with a perf_cov column in both results folders (the one non-1.0000 hit on each boot is the repeated header line of latency-control-cpu2.csv, not a data row).

## 16. [minor] The table lists every difference between the two boots that Jesse's README names
- Stated: The table is complete with respect to the 011 README's list of differences.
- Found: Three differences the 011 README names are not in the table: (1) every bandwidth file's comment line gains 'asm_passes=0 dsb_st=0 no_fold=0' (line 85, under 'What his rows print'); (2) the box patch's two 'clusterpwrstat' comment lines in run_cme.sh (lines 12 and 'The run'), so run_cme.sh is not byte for byte run 3's, though the table does not claim it is; (3) the initial ramdisk's size and the two boot-memory lines that follow from it, by which F1's sysinfo.txt differs from round three's and F1's init ran 7.9 ms later (lines 47 and 341). None of the three touches a core row, so the omission changes no conclusion.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md lines 12, 47, 85, 341 and 'The run' (box patch bullet).

## 17. [minor] TF-A, kernel, OS image, device tree, huge pages, CPU layout | ... | the same files byte for byte (kernel Image sha256 equal)
- Stated: The device tree is the same file byte for byte on both boots.
- Found: The 011 README says 'the base device tree' is the same; the 004 README notes that the device tree of a snapshot differs 'only in where the initial ramdisk ends', and the 011 README says F1's sysinfo differs from round three's in the initial ramdisk's size. So the loaded device tree likely differs in the ramdisk end address; only the base device tree is stated to be identical. The kernel Image sha256 (e298e0e0...) is stated equal in both snapshots, and Linux 6.18.36, 256 huge pages and CPUs 2-9 isolated are confirmed on both boots.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md lines 89 and 341; /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-004/README.md line 27; sysinfo.txt line 4 (kernel), lines 6 (isolcpus=2-9) and 109 (HugePages_Total 256) in both results folders.

## 18. [minor] CPU 3 was online and idle during cme_test and went offline after the sysinfo step on both boots
- Stated: Read literally, CPU 3 was online during cme_test on both boots.
- Found: cme_test ran on F1 only (run 3's init started run_all.sh directly). What holds on both boots is that CPU 3 went offline after the sysinfo step (log.txt line 4, 'cpu3 online=0', on both). The 011 README says 'with CPU 3 online and idle (his run_asimov.sh takes it offline after its sysinfo step)' of F1's cme_test. The sentence's 'on both boots' should attach only to the offline step.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md line 35; /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/results/bootF1/log.txt line 4; /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-004/results/19700101T000000Z/log.txt line 4.

## 19. [minor] F1's log.txt equals run 3's except for the 39 lines run_cme.sh adds, by diff
- Stated: 39 lines, all added by run_cme.sh
- Found: 39 lines added, 0 removed (my diff with cache-mem-perf-<commit>, the results folder, [uptime N.NN] and the ISO date stamps normalised). 37 of the 39 are run_cme.sh command lines ('+ .../bandwidth --cme ...' and the two '--events cme-l3' latency lines). The other 2 are comment lines '# box clusterpwrstat before cme-l3: 0x70' and '# box clusterpwrstat after cme-l3: 0x70', which the box's wrapper writes, not run_cme.sh.
- Evidence: Normalised diff of /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-004/results/19700101T000000Z/log.txt (120 lines) against /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/results/bootF1/log.txt (159 lines): single hunk '110a111,149', 39 '>' lines. Jesse's F1 README line 12 says the box added the two clusterpwrstat comment lines, and line 153 says run_cme.sh 'inserts 37 new ones ... (log.txt lines 111-149, the box's two lines among them)'.

## 20. [minor] F1's core latency commands lived longer: the four counted 4 KiB controls 1.31 to 1.42 times run 3's lifetime, the 20 sparse OCM rows 1.24 to 1.60 times, while the counted 2 MiB read lived 0.648 times
- Stated: The 2 MiB read is listed in the same sentence as the core latency commands, as the contrasting case
- Found: The ratios are right (controls 1.3103 to 1.4230, sparse rows 1.2360 to 1.5982, dram-read-2M-cpu2 1391056/2147182 = 0.6479). But dram-read-2M-cpu2 is a bandwidth command (log.txt line 56: 'cmn dram-read-2M-cpu2 .../bandwidth --threads 1 --cpus 2 --bytes 2M --kernel read --passes 4 --reps 1'), not a latency command. Every counted core latency command did live longer on F1 (ratios 1.010 to 1.598, including ocm-all5 1.17 to 1.21, dense 1.03 to 1.04, dram-slc-2M 1.01 to 1.02). The other counted core bandwidth commands lived 0.916 to 1.027 times, so 0.648 is the one outlier among them.
- Evidence: child_elapsed_ns rows of cmn-counts.csv in membench-jibin-011/results/bootF1/ and membench-jibin-004/results/19700101T000000Z/, ratio F1/run 3 computed per label with my own script (/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/verify23/cmn.py). The F1 README line 149 separates 'core latency commands' (1.010 to 1.598) from 'counted core bandwidth commands' (0.648 to 1.027).

## 21. [minor] So the L3 did not take these reads off the mesh: the same lines were fetched, by the same number of requests, in less time
- Stated: the same number of requests
- Found: 0.975 times: 427,991 requests over the five home nodes on F1 against 438,961 on run 3, 10,970 fewer (2.5 %); per node 0.972 to 0.977. hns_mc_reqs_local_all is 0.967 times and hns_cache_miss_all 0.969 times. The 0.975 figure printed in the sentence before is correct; 'the same number' rounds a 2.5 % drop to zero. The conclusion (the L3 did not take the reads off the mesh) still holds, since a 2.5 % drop in requests cannot explain a 2.69 times faster read.
- Evidence: Sum of hns_pocq_reqs_recvd_all over node ids 88, 160, 216, 288, 344 for label dram-read-2M-cpu2 in both cmn-counts.csv files (the five home nodes of the file: exactly five node ids appear, matching 'five home nodes'). Computed with my own script (/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/verify23/cmn.py).

## 22. [minor] Every stream of independent reads got faster on F1, by 1.56 to 2.69 times for one core (figure caption) and 'Every stream of independent reads got faster (1.2 to 2.9 times)' (Short version)
- Stated: every independent read stream faster, one core 1.56 to 2.69
- Found: The 16 KiB read streams did not get faster: one core 0.965 (56.085 against 58.127 GB/s), pair 0.966 (112.409 against 116.407). The 1.56 to 2.69 range is the 48 KiB to 32 MiB one-core rows only. The table handles the 16 KiB rows as their own 'unchanged' groups, so the caption's 'every' overstates by two rows that sit in the L1.
- Evidence: bandwidth-dram-1core.csv and bandwidth-pair.csv of 011 and 004; max aggregate_GBps over reps

## 23. [minor] Four readers on four clusters each keep 100 to 100 % of F1's one-core rate at 16 MiB (24.5 to 24.6 GB/s against 24.6)
- Stated: one-core rate at 16 MiB = 24.6 GB/s
- Found: There is no 16 MiB one-core row; the 24.6 GB/s is the one-core 32 MiB read (24.575 GB/s, generator uses ONE1[33554432]). The per-thread range of the four-reader 16 MiB best rep is 24.518 to 24.610 GB/s, so the 100 to 100 % and the GB/s figures are right; only the size label of the one-core reference is off (adjacent to my dimension, reported because it rests on the same CSV).
- Evidence: bandwidth-perdsu.csv rep 0 of read,4,16777216 (per_thread_min 24.518, per_thread_max 24.610) and bandwidth-dram-1core.csv read,1,33554432 best 24.575, both in 011

## 24. [minor] Four readers on four clusters each keep 100 to 100 % of F1's one-core rate at 16 MiB (24.5 to 24.6 GB/s against 24.6)
- Stated: a one-core rate of 24.6 GB/s at 16 MiB
- Found: No one-core 16 MiB row exists on boot F1 (grep of 'threads=1 bytes_per_thread=16777216' over results/membench-jibin-011/results/bootF1/*.csv finds no file). The 24.6 is the 32 MiB one-core read best, 24.575 GB/s; the nearest smaller one-core row is 2 MiB at 25.044 GB/s. The four-reader figures are right: best rep (98.072 GB/s aggregate) per-thread min 24.518, max 24.610 GB/s; 24.518/24.575 = 99.8 %, 24.610/24.575 = 100.1 %.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/results/bootF1/bandwidth-dram-1core.csv (best rows: read 2 MiB 25.044, read 32 MiB 24.575); /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/results/bootF1/bandwidth-perdsu.csv (16 MiB read block, rep 0 = best); the generator divides by ONE1[33554432]['read'] in sec_f1_vs_run3.py

## 25. [minor] OCM is Normal write-back memory, so the L3 may hold its lines [latency-ocm-region<r>-cpu<c>.csv of 011 and 004]
- Stated: OCM is Normal write-back memory, cited to the latency CSV files
- Found: The fact is on disk but not in the cited files. Run 3's README says /dev/ocm 'maps a region as Normal write-back in 4 KiB pages' (line 37), and F1's README says every OCM mapping has prot=0x68000000000fc3 '(Normal write-back memory, inner shareable, user read-write, never executable)' (line 260). The CSV files carry no memory-type field.
- Evidence: /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-004/README.md:37; /home/jhan/workspace/titan/cache-perf/asimov/results/membench-jibin-011/README.md:260; grep -i 'write-back' over the two READMEs, sysinfo.txt and log.txt of 011 and 004

## 26. [minor] The counters show the same number of refills per line and the same number of mesh requests per command (Short version)
- Stated: F1 against run 3 counters show equal refills per line
- Found: The refills-per-line evidence in the section is boot E against boot C (bandwidth-read-prefetch.csv of 010 and 007), not F1 against run 3 (run 3's bandwidth rows carry no core counters, F1 README line 144). Only the mesh-request count (0.975 times) is F1 against run 3. For the L3-sized chains and the sparse OCM rows the section itself reports fewer 0xA2 refills per load on F1 (0.46 to 0.94 falling to 0.00 to 0.03; 0.71 falling to 0.42).
- Evidence: sec23.txt lines 3, 59, 61, 63; sec_f1_vs_run3.py line 58 (RV[...]['e']['E'] and ['C']). Fix: 'For the read streams, boots E and C show the same refills per line and F1 puts the same number of requests on the home nodes as run 3'.

## 27. [minor] Four readers on four clusters each keep 100 to 100 % of F1's one-core rate at 16 MiB (24.5 to 24.6 GB/s against 24.6)
- Stated: 100 to 100 %; F1's one-core rate at 16 MiB
- Found: 24.5 / 24.6 = 99.6 % and 24.6 / 24.6 = 100 %, printed with .0f as '100 to 100 %'. There is no one-core 16 MiB row: the 24.6 GB/s is the one-core 32 MiB row (ONE1[33554432]), which table 4.4 says it substitutes 'where no one-core row has that size (160 KiB, 16 MiB)'. Section 9 states the same rows as '98 % or more of F1's one-core rate'.
- Evidence: sec_f1_vs_run3.py line 60 (per4 uses ONE1[33554432]['read']); sec23.txt line 65; page table 4.4 note; section 9 caption. Fix: 'keep 99.6 to 100 % of F1's one-core 32 MiB rate'.

## 28. [minor] the chains from 1.5 MiB on within 3.8 % (ruled out: boards or noise) against section 2.2's 'the 4 MiB chain reads 3.9 % above run 3'
- Stated: 3.8 % (2.3) and 3.9 % (2.2) for the same row
- Found: Both are the 4 MiB fresh chain: run 3 ns / F1 ns = 0.962 (2.3's convention, 3.8 % below 1) and F1 ns / run 3 ns = 1.039 (2.2's convention, 3.9 % above 1). Not wrong, but two conventions for one row on one page.
- Evidence: sec23.txt lines 30, 77; asimov-c1nano-perf.html section 2.2 ('the 4 MiB chain reads 3.9 % above run 3'); sec_f1_vs_run3.py line 102 (max(abs(x - 1) for x in ch)). Fix: use one convention or state both ('3.9 % more time per load').

## 29. [minor] Eight readers, two per cluster, read 107.6 GB/s together, 13.4 each, so two readers in one cluster share about 27 GB/s est. per cluster (2.3) against section 9's 'eight readers share a ceiling of abou
- Stated: a per-cluster limit of 27 GB/s (2.3, labelled hypothesis) and a shared ceiling of 109 GB/s (section 9)
- Found: The two sections give two readings of the same row (bandwidth-all8.csv of 011): a per-cluster limit (4 x 27 = 108) and one shared ceiling (109). The data cannot separate them, and neither section cross-references the other. Section 2.3 labels its reading a hypothesis with a test; section 9 states its reading as fact.
- Evidence: sec23.txt lines 65, 73; asimov-c1nano-perf.html section 9 caption. Fix: section 9 should point to the hypothesis and test in 2.3, or 2.3 should name section 9's reading as the alternative.

## 30. [minor] Table of contents entry '2.3 Boot F1 against run 3: what differed, what moved, the hypotheses' against the heading '2.3 Boot F1 against run 3: what differed, what moved, and the hypotheses'
- Stated: two spellings of the section title
- Found: The TOC link text (asimov-c1nano-perf.html line 46, href="#f1vs3") lacks the 'and' that the h3 has.
- Evidence: grep -n 'href="#f1vs3"' asimov-c1nano-perf.html; sec_f1_vs_run3.py line 66.

## 31. [minor] Undefined terms at first use: 'the box' (the box's wrapper), 'RT throttling off', 'Normal write-back memory', 'pass and worker differ', 'sha256 equal', 'Jesse's README'
- Stated: terms used without a definition in the section or earlier on the page
- Found: 'the box' first appears on the page at section 2 ('the box's two reads') and in 2.3 as 'the box's wrapper' with no definition (it is emuMemBenchBox, Jesse's run automation). 'RT throttling' (the kernel's cap on real-time CPU time), 'Normal write-back memory' (the Arm memory type that caches may hold), 'pass' and 'worker' (functions of the bandwidth program), 'sha256' (a file hash) and 'Jesse' (the person who runs the emulator box) are not defined anywhere on the page (checked by search of the page text: no 'box (', 'Jesse (', 'emuMemBenchBox').
- Evidence: sec23.txt lines 5, 10, 11, 12, 16, 63; page text search over asimov-c1nano-perf.html (Words used here, section 1, defines PMU, TLB, DSU, SLC, home node, SCP, TF-A, perf_cov, 0xA2, snoop-filter-only, est., sparse, but none of these six). Plain-English rule 1.

## 32. [minor] Idioms and metaphors: 'rest on the SCP's staging lines', 'every process draws its own pages', 'the L3 did not take these reads off the mesh', 'F1's core latency commands lived longer ... run 3's lifet
- Stated: figurative wording
- Found: Each has a literal form: 'are known only from the SCP's staging log lines', 'every process gets its own physical pages', 'the L3 did not remove these reads from the mesh', 'ran longer ... run 3's run time'. 'lived' and 'lifetime' are quoted from the README's wording but are still metaphors for a command's elapsed time.
- Evidence: sec23.txt lines 9, 15, 21, 61, 79. Plain-English rule 6.

## 33. [minor] Short version, third sentence: 'The counters show the same number of refills per line and the same number of mesh requests per command, so the reads overlap more of their time rather than skipping the
- Stated: one sentence
- Found: Three claims in one sentence (what the counters show; the inference joined by 'so'; the status joined by 'and'). The Short version has three sentences, within the limit, but this one breaks rule 2 (one claim per sentence). The second sentence of the Short version likewise carries two claims ('got faster ... while ... repeated run 3').
- Evidence: sec23.txt line 3. Plain-English rules 2 and 8. Fix: 'The counters show the same refills per line and the same mesh requests per command. So the reads overlap more of their time rather than skipping the mesh. The mechanism is a hypothesis with a test, not a measurement.'

## Refuted (not a defect)
- The pass and worker changes could move an L1-sized row by a few percent (the 16 KiB rows below).: The 011 README does not make this attribution. It says 'Round three's README tied its own 16 KiB write shift to its rebuilt bandwidth, and pass differs again between the two builds; boot E against boot C, on one build, moved one L1 row too (the 4 KiB per-pass read, 0.886; boot E's README). These fil