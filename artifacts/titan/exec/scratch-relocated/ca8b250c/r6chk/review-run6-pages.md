# Review of the run 6 additions on the four pages (asimov-04, 2026-11-07)

46 findings confirmed by an independent re-check against the CSVs, READMEs and generator code; 1 refuted. Numbered as below. page_text is the page as it stands, source_says the primary source, suggested_text a proposed wording.

## [1] asimov-cme-perf.html | Short version | unsupported claim

**Page text:** The single-call form puts the CME L1 read rate at 109 to 132 GB/s, one 64-byte load per cycle, and the looped read's cost per call at 186 ns.

**Source says:** 186.2 ns is the bracket intercept of the F1 looped read fit [cme-bandwidth-l1-passes.csv of 011]. The bracket of a run 6 call carries the in-span stamp cost: cme-call reads 124.516 to 125.656 ns on F1 and F2 [cme-latency-*.csv of 011 and 012] against 42.516 to 43.922 ns on boot E [cme-latency-*.csv of 010], about 82 ns more per call. Run 3's 1 KiB read call, with no stamps, took 97 ns [cme-bandwidth-call-cost.csv of 004: 1024 B / 10.549 GB/s]. No run 6 row isolates the stamp cost.

**Suggested:** The single-call form puts the CME L1 read rate at 109 to 132 GB/s, one 64-byte load per cycle. The looped read's cost per call reads 186 ns by run 6's bracket, about 82 ns of which is the cost of run 6's in-span clock stamps (cme-call: 124.5 to 125.7 ns on F1 and F2 against 42.5 to 43.9 on boot E); net of the stamps the call costs about 100 ns (est.), near run 3's 97 ns for a 1 KiB read call.

**Verifier:** Confirmed, not refuted. Every number in the finding reproduces from the CSV rows. (1) The 186 ns is the bracket intercept of a least-squares line through the four F1 looped-read 'best' rows of results/membench-jibin-011/results/bootF1/cme-bandwidth-l1-passes.csv (4096 B at 18.783 GB/s = 218.1 ns per pass, 8192 at 33.045 = 247.9, 16384 at 53.021 = 309.0, 24576 at 65.849 = 373.2): a = 186.2 ns, rate 132.0 GB/s by the bracket, a = 103.9 ns in span. gen_run6.py line 189 computes it the same way (fit_line over t_pass = bytes / GB/s). (2) cme-call bracket rows: F1 (36 rows, cme-latency-*.csv of 011) 124.516 to 125.609 ns; F2 (36 rows, 012) 124.531 to 125.656 ns; boot E (63 rows, 010) 42.516 to 43.

## [2] asimov-cme-perf.html | Short version | unsupported claim

**Page text:** Settled by run 6. The L3-served load through the CME (32.8 to 33.9 ns, section 5.2), the demand-only OCM latency through the CME (47.9 to 52.1 ns per region, section 7), the bandwidth set with the L3 on (section 6), the cost per call (section 6.1) and the memory model's delay (section 2.2).

**Source says:** Section 6.1 itself says of the write 'What remains open is the size of the cost itself', and every run 6 per-call number includes the stamp cost, which no row isolates (cme-call 124.5 to 125.7 ns on F1 and F2 against 42.5 to 43.9 on boot E; the 1 KiB write's in-span 48.0 ns is above run 3's whole call of 39.1 ns [cme-bandwidth-call-cost.csv of 011 and 004]).

**Suggested:** Settled by run 6. The L3-served load through the CME (32.8 to 33.9 ns, section 5.2), the demand-only OCM latency through the CME (section 7), the bandwidth set with the L3 on (section 6) and the memory model's delay (section 2.2). Open: the cost per call net of run 6's clock stamps (section 6.1), why the CME's writes fall with the L3 on, and the two-core streaming rows (section 10).

**Verifier:** Not refuted. The Short version sentence (gen_perf_cme.py line 296) lists "the cost per call (section 6.1)" among the items settled by run 6 with no qualifier. The page's own section 10 (gen_perf_cme.py lines 422 and 427) narrows the settled item to "the cost per call of a read (section 6.1)" and lists "The cost of a write call" as open, and section 6.1's write paragraph ends "What remains open is the size of the cost itself, since the looped write gives no line to read it from." So the Short version states as settled what two other sections of the same page state as open. Every number the reviewer quoted recomputes: cme-call best rows read 124.516 to 125.609 ns on F1/F2 (reps up to 125.656) 

## [3] asimov-cme-perf.html | Short version | unsupported claim

**Page text:** and the demand-only OCM load through the CME costs 47.9 to 52.1 ns per region.

**Source says:** 47.91 to 52.11 ns are the bracket best rows of 64-load spans [cme-latency-ocm-region0..4.csv of 012]. Inside the span the same rows read 43.45 to 47.73 ns, so 4.4 to 4.5 ns per load (280 to 304 ns per call, F2 README, CME rows) is call cost outside the span, part of it run 6's stamps. Boot E's 29.0 to 37.7 ns in the same paragraph are bracket rows without stamps [cme-latency-ocm-region*.csv of 010].

**Suggested:** and the demand-only OCM load through the CME costs 47.9 to 52.1 ns per region by the bracket, 43.5 to 47.7 ns inside the streaming span; these 64-load rows carry 4.4 to 4.5 ns per load of call cost outside the span, part of it run 6's clock stamps, so they are not directly comparable to boot E's bracket values.

**Verifier:** Confirmed from the CSVs, the F2 README and the generator; the finding stands.

Numbers in the finding, recomputed:
- Bracket bests (column ns_per_load) of results/membench-jibin-012/results/bootF2/cme-latency-ocm-region0..4.csv: 48.859, 47.906, 48.813, 51.734, 52.109 ns. So the page's 47.9 to 52.1 ns is the bracket value, and gen_perf_cme.py line 291/296/405 prints F2_OCM_RNG from that column.
- In-span value (column ns_per_load_span) of the same best rows (cme-fresh2/7/5/7/2): 44.391, 43.453, 44.359, 47.266, 47.734 ns, so 43.5 to 47.7 ns. Bracket minus span is 4.44 to 4.47 ns per load, 64 loads per call, so 284 to 288 ns per call on the best rows. README line 141 gives 280.0 to 304.0 ns per

## [4] asimov-cme-perf.html | 2.2 Run 6: boots F1 and F2 | wording

**Page text:** The AP's DRAM is four Cadence AXI memory models, one per SMS lane, and every delay control on them is zero ... By Jesse's count of the RTL stages (an inference, not a measurement) about 20 ns of the DRAM leg is fixed pipeline between the mesh's SN bridges and the memory ... (0x70 in all nine BL31 readings and the two runtime ones)

**Source says:** AP, AXI, SMS, SN and BL31 appear here for the first time on the page and are not in 'Words used here' (grep of the page: one occurrence each; no 'application processor' or 'register transfer' anywhere). RTL is used in 'Words used here' and here without a definition.

**Suggested:** The AP's (the application processor's, the Arm cores' side of the chip) DRAM is four Cadence AXI (an Arm bus protocol) memory models, one per SMS lane (the four memory lanes that serve the AP), and every delay control on them is zero ... By Jesse's count of the RTL (the chip's hardware source) stages (an inference, not a measurement) about 20 ns of the DRAM leg is fixed pipeline between the mesh's SN bridges (the mesh's memory-side nodes) and the memory ... (0x70 in all nine readings by BL31, the TF-A runtime stage, and the two runtime ones)

**Verifier:** Confirmed, not refuted. I stripped the tags from /home/jhan/workspace/titan/cache-perf/asimov/asimov-cme-perf.html and searched the text with word-boundary regexes. AP (1 occurrence), AXI (1), SMS (1) and SN (1, "SN bridges") each appear only in the section 2.2 sentence "The memory model's delay, answered. The AP's DRAM is four Cadence AXI memory models, one per SMS lane ... between the mesh's SN bridges and the memory". BL31 appears twice (section 2.2 "0x70 in all nine BL31 readings" and section 10 open items), first in 2.2. None of the five has an entry in the "1. Words used here" section (the glossary spans the text between the second "Words used here" occurrence and "2. The run and the p

## [5] asimov-cme-perf.html | 2.2 Run 6: boots F1 and F2 | wording

**Page text:** F1 gives the core phases their L3-on bandwidth rows, which boot E did not run (asimov-c1nano-perf.html, sections 7, 9 and 10).

**Source says:** Boot E ran four core bandwidth files: bandwidth-l1-passes.csv, bandwidth-l1-asmpasses.csv, bandwidth-read-prefetch.csv, bandwidth-write-small.csv [results/membench-jibin-010/results/bootE/]. The core page's table 4.3 quotes boot E's 16 KiB read, 2 and 32 MiB reads and writes; the F1 README says 'E ran no copy or multi-core row'.

**Suggested:** F1 gives the core phases their L3-on bandwidth rows; boot E ran only the L1 rows, the read variants and the small writes, no copy, multi-core, writer-placement or OCM row (asimov-c1nano-perf.html, sections 7, 9 and 10).

**Verifier:** Confirmed, not refuted. The CME page sentence (asimov-cme-perf.html section 2.2, generated by gen_perf_cme.py line 329) says boot E did not run the core phases' L3-on bandwidth rows. Boot E's results folder holds five core bandwidth files, all listed in membench-jibin-010/SHA256SUMS: bandwidth-l1-passes.csv and bandwidth-l1-asmpasses.csv (one-core read and write at 4, 8, 16, 24 KiB, 56 rows each), bandwidth-read-prefetch.csv (one-core read and read variants at 2 and 32 MiB, 50 rows), bandwidth-write-small.csv and bandwidth-write-small-r2prog.csv (one-core write at 16, 48, 96, 256 KiB, 20 rows each). Boot E's log.txt lines 99-141 show the bandwidth command lines. The core page's own section 7

## [6] asimov-cme-perf.html | 4.3 One-core bandwidth, core against CME (caption) | unsupported claim

**Page text:** so at 16 and 48 KiB it reads below run 3's bracket while the in-span rate matches run 3 within 1 % (section 6.1).

**Source says:** True for the read cells only: in span 73.8 against run 3's 73.4 at 16 KiB and 104.6 against 104.9 at 48 KiB. Write in span 69.5 against 63.7 (+9 %) and 56.3 against 63.8 (-12 %); copy 139.5 against 126.5 (+10 %) and 112.1 against 126.4 (-11 %) [cme-bandwidth-dram-1core.csv of 011 and 004].

**Suggested:** so at 16 and 48 KiB the read cell reads below run 3's bracket while its in-span rate matches run 3 within 1 %; the write and copy in-span rates differ from run 3 by 9 to 12 % at those sizes (section 6.1).

**Verifier:** Confirmed from the primary CSVs. The caption sentence is on the page (asimov-cme-perf.html, section 4.3 caption) and comes from gen_perf_cme.py:185. The table's 16 and 48 KiB rows carry three CME kernels (read, write, copy), and the sentence says the in-span rate "matches run 3 within 1 %" for those sizes without naming a kernel. Recomputed best-rep span_GBps from results/membench-jibin-011/results/bootF1/cme-bandwidth-dram-1core.csv against best aggregate_GBps from results/membench-jibin-004/results/19700101T000000Z/cme-bandwidth-dram-1core.csv: read 16 KiB 73.808 vs 73.377 (+0.6 %), read 48 KiB 104.593 vs 104.865 (-0.3 %) - within 1 %; write 16 KiB 69.540 vs 63.731 (+9.1 %), write 48 KiB 5

## [7] asimov-cme-perf.html | 4.5 The four L1 forms and the cost per call (run 6), table row 'looped read', column 'F2: cost per pass (in span); rate' | unsupported claim

**Page text:** 182.1 (101.1); 128.9

**Source says:** F2's looped read fit has its largest residual at 6.6 ns, above 2 % of the smallest pass time (208.8 ns at 4 KiB, limit 4.2 ns), so by the page's own rule it is not a cost per call [cme-bandwidth-l1-passes.csv of 012; gen_run6.py prints 'looped read: a 182.1 ns ... resid 6.6 ns, no fit' for F2]. The rule column of the table covers F1 only.

**Suggested:** 182.1 (101.1); 128.9; rule not met (residual 6.6 ns of a 208.8 ns pass), so not a cost per call

**Verifier:** Confirmed from primary sources, not refuted. Recomputed the F2 looped-read fit from the best rows of results/membench-jibin-012/results/bootF2/cme-bandwidth-l1-passes.csv (cme-read, bracket aggregate_GBps 19.615, 32.473, 53.073, 66.110 at 4, 8, 16, 24 KiB; pass time = bytes / GB/s). Least squares (same formula as l1_reader.fit): intercept a = 182.1 ns, rate 128.9 GB/s, largest residual 6.60 ns (at 8 KiB; residuals -5.08, +6.60, -0.51, -1.02 ns). Smallest pass time 208.8 ns at 4 KiB, so the page's 2 % limit is 4.18 ns; 6.60 ns exceeds it, so by the page's own rule (caption of table 4.5: "the largest residual under 2 % of the smallest pass time") the F2 intercept is not a cost per call. The in

## [8] asimov-cme-perf.html | 4.5 The four L1 forms and the cost per call (run 6), caption (repeated under 6.1) | unsupported claim

**Page text:** The call-cost rows: a 1 KiB read call takes 186.1 ns (108.0 in span) against run 3's 97.2, a 1 KiB write call 124.1 ns (48.0 in span) against 39.1; writes of 2, 4 and 8 KiB per call 128.6, 149.8 and 182.1 ns per call (52.5, 73.5, 91.6 in span) [cme-bandwidth-call-cost.csv of 011].

**Source says:** The run 6 bracket includes the in-span stamp pair: cme-call 124.5 to 125.7 ns on F1 and F2 against 42.5 to 43.9 on boot E (about 82 ns per call) [cme-latency-*.csv of 011, 012, 010]. The in-span time still includes part of the pair: the 1 KiB write's 48.0 ns in span is above run 3's 39.1 ns for the whole call [cme-bandwidth-call-cost.csv of 004]. The caption states the run 3 values beside the run 6 values with no such note.

**Suggested:** The call-cost rows: a 1 KiB read call takes 186.1 ns (108.0 in span) against run 3's 97.2, a 1 KiB write call 124.1 ns (48.0 in span) against 39.1; writes of 2, 4 and 8 KiB per call 128.6, 149.8 and 182.1 ns per call (52.5, 73.5, 91.6 in span) [cme-bandwidth-call-cost.csv of 011]. Run 3's rows carried no in-span clock stamps: run 6's bracket includes about 82 ns of stamp cost per call (cme-call, section 6.1) and its in-span time still includes part of the stamp pair (the 1 KiB write's 48.0 ns in span is above run 3's 39.1 ns for the whole call). No run 6 row isolates the stamp cost.

**Verifier:** Confirmed from primary sources. Numbers in the caption are right (recomputed from results/membench-jibin-011/results/bootF1/cme-bandwidth-call-cost.csv and results/membench-jibin-004/results/19700101T000000Z/cme-bandwidth-call-cost.csv: read 1 KiB 186 ns / 108.0 in span vs run 3 97.2; write 1 KiB 124 / 48.0 vs 39.1; 2, 4, 8 KiB 128.4-128.9, 149.4-164.1 (best 149.4), 181.6 with 52.5, 73.5, 91.6 in span). cme-call brackets: F1 124.516-125.609, F2 124.531-125.656, boot E 42.516-43.922 ns, so about 82 ns per call of added cost on run 6 (cme-latency-*.csv of 011, 012, 010). The 011 README (lines 153, 155) states every run 6 kernel is its run 3 self plus 15 stamp instructions (2 ISB, 2 MRS CNTVCT_

## [9] asimov-cme-perf.html | 6.1 The cost per call, settled by the single-call form | wrong number

**Page text:** A read call costs about 186 ns, half of it the fold.

**Source says:** The fold's share is 186.2 - 134.2 = 52 ns, which is 28 % of 186 ns, not half [cme-bandwidth-l1-passes.csv and -nofold.csv of 011]. The 186 ns bracket intercept also includes about 82 ns of stamp cost (cme-call 124.5 to 125.7 ns on F1 and F2 against 42.5 to 43.9 on boot E).

**Suggested:** A read call costs about 186 ns by run 6's bracket: about 82 ns of it run 6's clock stamps, 52 ns the fold, and about 50 ns (est.) the rest of the call.

**Verifier:** Confirmed from primary sources. Recomputed l1_reader.fit on the best-rep bracket rates of results/membench-jibin-011/results/bootF1/cme-bandwidth-l1-passes.csv (cme-read 4/8/16/24 KiB: 18.783, 33.045, 53.021, 65.849 GB/s) gives intercept 186.2 ns; the same fit on cme-bandwidth-l1-nofold.csv (24.403, 42.129, 63.943, 76.151 GB/s) gives 134.2 ns. The fold's share is 186.2 - 134.2 = 52.0 ns = 28 % of 186 ns, not half. The page's own next sentences state the 52 ns and the 82 ns bracket-minus-span (186.2 - 103.9), so the bold lead sentence contradicts its own paragraph. The 82 ns is run 6's in-span stamp cost: cme-call-best rows read 124.5 to 125.6 ns on F1 and F2 (011/012 cme-latency-*.csv) again

## [10] asimov-cme-perf.html | 6.1 The cost per call, settled by the single-call form | unsupported claim

**Page text:** Bracket minus span is 82 ns per call: the save, SMSTART, SMSTOP, restore, call and return.

**Source says:** cme_kern.S lines 11 to 23: bracket minus span is 'the instrumented outside-span interval of the call: the register save, SMSTART, SMSTOP, the restore, the caller's call and return, and those eight instructions. It is not the switch alone.' On boot E the whole cme-call (the same items plus one DUP and LASTB) took 42.5 to 43.9 ns without stamps [cme-latency-*.csv of 010], so 82 ns cannot be those items alone.

**Suggested:** Bracket minus span is 82 ns per call: the save, SMSTART, SMSTOP, restore, call and return plus the second stamp's eight instructions [cme_kern.S]. On boot E the whole cme-call, without stamps, took 42.5 to 43.9 ns, so most of the 82 ns is the stamps' cost, not the switch.

**Verifier:** Confirmed, not refuted. The number is right but the attribution is not supported. (1) The 82 ns recomputes exactly: the looped read's bracket fit gives 186.2 ns per pass and the in-span fit 103.9 ns [results/membench-jibin-011/results/bootF1/cme-bandwidth-l1-passes.csv, best reps, fit per gen_run6.py line 185 to 191], difference 82.3 ns (per-size differences 83.2, 83.5, 84.0, 86.4 ns). (2) What sits in bracket minus span, from the kernel source: SM_ENTER holds the register save, SMSTART, then ISB + MRS CNTVCT (the first stamp); SM_LEAVE holds ISB + MRS CNTVCT (the second stamp) then adrp, add, ldr, str, sub, ldr, add, str (8 instructions) before SMSTOP and the restore [cme_kern.S lines 71 to

## [11] asimov-cme-perf.html | 6.1 The cost per call, settled by the single-call form | unsupported claim

**Page text:** The single-call read moves 109 to 132 GB/s from 4 to 48 KiB, 54 to 66 bytes per CME cycle, with a fitted cost per pass of 3.4 ns. ... the single-call read's 3.4 ns, so the call costs 183 ns.

**Source says:** The single-call read fit's largest residual is 5.9 ns, against a 2 % limit of 0.6 ns on the 31.1 ns smallest pass: table 4.5 marks it 'not met' [cme-bandwidth-l1-asmpasses.csv of 011]. The same caption rejects the looped write's intercept for failing the rule ('so its intercept is not a cost per call').

**Suggested:** The single-call read moves 109 to 132 GB/s from 4 to 48 KiB, 54 to 66 bytes per CME cycle. Its four points do not meet the 2 % rule (residual 5.9 ns of a 31.1 ns pass), so its 3.4 ns intercept is indicative only (est.). ... less the single-call read's intercept of about 3 ns (est.), so the call costs about 183 ns by the bracket (est.), about 100 ns net of the stamps (est.).

**Verifier:** Confirmed from primary sources, not refuted. Recomputed from results/membench-jibin-011/results/bootF1/cme-bandwidth-l1-asmpasses.csv (best rep per size, t_pass = total_bytes / (aggregate_GBps * 1e9) / passes, least squares as in l1_reader.fit): single-call read points 4/8/16/24 KiB = 31.11, 75.23, 136.38, 199.04 ns per pass; intercept 3.44 ns (bracket), 3.48 ns (span), rate 124.4 GB/s, largest residual 5.94 ns. Smallest pass 31.1 ns, so the 2 % limit is 0.62 ns; the residual is 19.1 % of the smallest pass. Table 4.5 prints exactly this ("3.4 (3.5)", "124.4 (125.7)", "5.9 ns, not met"), so the page's own table says the fit fails its own rule. F2 gives the same (3.38 ns, residual 5.45 ns, not

## [12] asimov-cme-perf.html | 6.1 The cost per call, settled by the single-call form | wrong number

**Page text:** The chain rows are one call per timed span of 8,192 to 524,288 loads, so this cost is under 10 ps per load there and the round trip reads 21.005 ns as before [table 4.1].

**Source says:** The OCM chain rows have 64 loads (one region) and 320 loads (all five, one line per page) per span: F1 region 0 best row 38.875 ns by the bracket against 34.359 in span (4.5 ns per load outside the span), all-five sparse 36.319 against 35.406 (0.9 ns per load) [cme-latency-ocm-region0.csv, cme-latency-ocm-all5.csv of 011; F2 README: 280.0 to 304.0 ns per call outside the span]. For the DRAM chains 82 ns / 8,192 loads = 10.0 ps, not under 10 ps.

**Suggested:** The DRAM chain rows are one call per timed span of 8,192 to 524,288 loads, so this cost is about 10 ps per load or less there, and the round trip reads 21.005 ns as before [table 4.1]. The sparse OCM rows have 64 loads (one region) or 320 loads (all five) per span, so their bracket time carries 4.4 to 4.5 ns and 0.9 ns per load outside the span [cme-latency-ocm-region0.csv, cme-latency-ocm-all5.csv of 011 and 012].

**Verifier:** Confirmed from the CSVs, READMEs and generator. (1) Scope: the page's own OCM chain rows are not "one call per timed span of 8,192 to 524,288 loads". The sparse per-region rows carry loads=64 per span and the sparse all-five row loads=320 [results/membench-jibin-011/results/bootF1/cme-latency-ocm-region0.csv, cme-latency-ocm-all5.csv; same in 012]. Bracket minus span there is 4.45 to 4.52 ns per load on every region row of F1 and F2 (F1 region 0 best row: 38.875 bracket vs 34.359 span; all-five sparse 36.319 vs 35.406, 0.91 ns per load), about 286 to 292 ns per span. README 011 line 189 says "4.5 ns per hop of each 64-hop pass outside the span"; README 012 line 141 says "280.0-304.0 ns per c

## [13] asimov-cme-perf.html | 6.1 The cost per call, settled by the single-call form (figure caption) | wrong number

**Page text:** Writes reach 52 to 54 GB/s in one call and 50 to 52 looped; the DSB ST write, which waits for every store before SMSTOP, reads 21 to 45.

**Source says:** The looped write's best reps are 26.980, 50.018, 52.211 and 52.251 GB/s at 4, 8, 16 and 24 KiB [cme-bandwidth-l1-passes.csv of 011, cme-write rows]; the figure's own 'write 4 KiB' bar is labelled 26.980 GB/s.

**Suggested:** Writes reach 52 to 54 GB/s in one call and 27 to 52 looped (27 at 4 KiB, 50 to 52 from 8 KiB); the DSB ST write, which waits for every store before SMSTOP, reads 21 to 45.

**Verifier:** Confirmed from primary sources. results/membench-jibin-011/results/bootF1/cme-bandwidth-l1-passes.csv, cme-write 'best' rows: 26.980 GB/s at 4 KiB, 50.018 at 8 KiB, 52.211 at 16 KiB, 52.251 at 24 KiB (aggregate_GBps, column 8). The caption text "50 to 52 looped" omits the 4 KiB point. The generator shows why: gen_perf_cme.py line 394 builds the looped write range from the 8192 and 24576 rows only (FORM1[('looped','write')]['rows'][8192] to [24576]), while the read range in the same sentence and the "4 to 24 KiB" scope cover 4096 to 24576, and the sentence does not say the write range starts at 8 KiB. The figure's own bar and the table 6.1 row ("looped write 27.0 (62.5) 50.0 (93.5) 52.2 (73.6

## [14] asimov-cme-perf.html | 6.1 The cost per call, settled by the single-call form | wording

**Page text:** A write call hides its cost behind its stores, and DSB ST brings it back. ... The two clock reads and the ISB that closes the span are inside the call.

**Source says:** 'hides its cost behind' and 'brings it back' are metaphors (plain-English rule 6). ISB appears here for the first and only time on the page with no definition (rule 1).

**Suggested:** A write call's cost overlaps with its stores, and DSB ST exposes it. ... The two clock reads and the ISB (an instruction barrier, which waits for the earlier instructions before the clock read) that closes the span are inside the call.

**Verifier:** Confirmed, not refuted. Primary source: /home/jhan/workspace/titan/cache-perf/asimov/asimov-cme-perf.html (tags stripped) and the template in gen_perf_cme.py lines 399-400. (1) The exact page text "A write call hides its cost behind its stores, and DSB ST brings it back." appears in section 6.1 as a bold list-item lead; "hides ... behind" and "brings it back" are figurative, so plain-English rule 6 applies. The page's own later sentence states the literal meaning ("stores are posted ... a barrier that waits for them exposes the time"), so the literal rewrite is available. (2) The acronym ISB occurs exactly once on the page (regex count = 1), in the sentence "The two clock reads and the ISB t

## [15] asimov-cme-perf.html | Table 4.1 caption (Latency by footprint, core against CME) | wrong number

**Page text:** On F1 and F2 the same call reads 124.5 to 125.7 ns by the bracket and 61.0 to 61.06 ns in span

**Source says:** cme-latency-*.csv of 011 (boot F1), the 36 cme-call reps: ns_per_load_span runs 61.000 to 61.250 (cme-latency-dram-small.csv of 011 among them). F2's 36 reps run 61.000 to 61.062. The generator takes the low end from F1 and the high end from F2 (C1['CALL_SPAN'][0] to C2['CALL_SPAN'][1]), so F1's 61.25 is dropped.

**Suggested:** On F1 and F2 the same call reads 124.5 to 125.7 ns by the bracket and 61.0 to 61.25 ns in span

**Verifier:** Confirmed from the CSVs. F1 (results/membench-jibin-011/results/bootF1/cme-latency-*.csv, 36 cme-call reps) has ns_per_load_span values {61.000, 61.062, 61.250}; the 61.250 is rep 0 of cme-latency-dram-small-l3.csv (row 'dram,0,cme-call,0,64,124.813,61.250'). F2 (membench-jibin-012/bootF2, 36 reps) has {61.000, 61.062}. The page sentence in the Table 4.1 caption of asimov-cme-perf.html reads '61.0 to 61.06 ns in span' because gen_perf_cme.py:164 formats C1['CALL_SPAN'][0] to C2['CALL_SPAN'][1], taking the high end from F2 only, so F1's 61.25 is dropped. The combined F1+F2 span range is 61.0 to 61.25 ns; the suggested text '61.0 to 61.25 ns in span' is correct. Minor correction to the reviewe

## [16] asimov-cme-perf.html | 7. OCM through the CME, second figure caption (run 3, boots B, E, F1, F2) | wrong number

**Page text:** With the prefetchers on (F1, E) the same rows read 37.3 to 39.2 ns because the CME's prefetcher fetches part of each load's line first.

**Source says:** cme-latency-ocm-region*.csv of 010 (boot E): the per-region bests are 37.156, 28.984, 35.969, 37.672, 37.109 ns, so boot E's range is 28.98 to 37.67 ns. F1 (011) reads 37.281 to 39.156. The range 37.3 to 39.2 is F1's low end to F1's high end; boot E's OCM1 row at 28.98 ns and its OCM2 row at 35.97 ns lie outside it. The 'part of each load's line' phrase is also wrong: F1 counts 0.41 to 0.47 prefetch refills per load, so the prefetcher fetches some of the loads' lines, not part of each line.

**Suggested:** With the prefetchers on the same rows read 37.3 to 39.2 ns on F1 and 29.0 to 37.7 ns on boot E, because the CME's prefetcher fetches some of the loads' lines before the chain reaches them (0.41 to 0.47 prefetch refills per load on F1).

**Verifier:** Confirmed from the CSVs and generator. Boot E (010/bootE cme-latency-ocm-region0..4.csv, cme-best rows): 37.156, 28.984, 35.969, 37.672, 37.109 ns, range 28.98 to 37.67 ns. F1 (011/bootF1 same files): 38.875, 37.281, 38.484, 39.156, 38.797 ns, range 37.28 to 39.16 ns. The caption text "With the prefetchers on (F1, E) the same rows read 37.3 to 39.2 ns" is generated by gen_perf_cme.py:405 as F1_OCM_RNG[0] to max(E_SP_RNG[1], F1_OCM_RNG[1]), so the lower bound is F1's minimum only and boot E's OCM1 (28.98 ns) and OCM2 (35.97 ns) rows lie outside the stated range: wrong number. F1 hwprf refills per load over the 7 fresh rows average 0.408 to 0.471 per region, so the prefetcher fetches some of t

## [17] asimov-cme-perf.html | 7. OCM through the CME, OCM bandwidth figure caption (boot F1) | wording

**Page text:** while the core's OCM reads fell to 1.21 to 1.36 times run 3's

**Source says:** bandwidth-ocm-region*.csv of 011: the core's best reads are 20.143, 20.042, 19.883, 20.086, 20.128 GB/s. bandwidth-ocm-region*.csv of 004: 16.219, 16.619, 16.320, 15.323, 14.817 GB/s. The ratios are 1.242, 1.206, 1.218, 1.311, 1.358: the core's OCM reads rose, they did not fall.

**Suggested:** while the core's own OCM reads rose 1.21 to 1.36 times run 3's

**Verifier:** Confirmed from primary sources. Core OCM region read 'best' rows: results/membench-jibin-011/results/bootF1/bandwidth-ocm-region{0..4}.csv give 20.143, 20.042, 19.883, 20.086, 20.128 GB/s; results/membench-jibin-004/results/19700101T000000Z/bandwidth-ocm-region{0..4}.csv give 16.219, 16.619, 16.320, 15.323, 14.817 GB/s. Ratios F1/run 3 = 1.242, 1.206, 1.218, 1.311, 1.358 (min 1.21, max 1.36 as the page prints). Every ratio is above 1.0, so the core's reads rose. The generator text in gen_perf_cme.py line 407 hard-codes the word 'fell' around OCMBW1['region'][r] / OCMBW['region'][r], where OCMBW1 = boot F1 (gen_run6.py line 120) and OCMBW = run 3 R4 folder (gen_run3.py lines 15 and 226). The 

## [18] asimov-cme-perf.html | 8. Mesh counters | unsupported claim

**Page text:** Boot A's split events count 0.36 to 0.45 prefetch refills per load of the one line per page chains on boot E (table 4.2), which fits, but no run has counted the mesh around a CME command with the split events on.

**Source says:** log.txt of 011 (boot F1), lines 88 to 94: 'cmn cme-ocm-region0-cpu2 latency --cme --cpu 2 --perf --mem ocm ...' through 'cmn cme-ocm-all5-dense-cpu2 ...'. The matching cme-latency-ocm-region*.csv of 011 carry the columns cme_l1d_refill_rd_per_load, cme_l1d_refill_hwprf_per_load, cme_l1d_refill_wr_per_load (events=cme on commit 0c190a1 is the split set), and cmn-counts.csv of 011 holds the labels cme-ocm-region0-cpu2 to cme-ocm-region4-cpu2, cme-ocm-all5-cpu2 and cme-ocm-all5-dense-cpu2. So boot F1 did count the mesh around CME commands with the split events on: those chains count 0.41 to 0.47 prefetch refills per load (pass mean) and put 0.91 to 1.09 times the core's requests on the region's node.

**Suggested:** Boot E's split events count 0.36 to 0.45 prefetch refills per load of the one line per page chains (table 4.2), which fits run 3's ratios. Boot F1 counted the mesh around the same CME chain commands with the split events on: the chains count 0.41 to 0.47 prefetch refills per load and put 0.91 to 1.09 times the core's requests on the region's node, and the CME's OCM read commands put 0.73 to 0.77 times the core's on the node of regions 1 to 4 [cmn-counts.csv and cme-latency-ocm-region*.csv of 011].

**Verifier:** Confirmed from primary sources. (1) results/membench-jibin-011/results/bootF1/log.txt lines 88 to 94 show boot F1 ran `cmn cme-ocm-region0-cpu2 ... latency --cme --cpu 2 --perf --mem ocm ...` through `cmn cme-ocm-all5-dense-cpu2`, i.e. the mesh counter wrapped the CME chain commands. (2) The header of cme-latency-ocm-region0.csv (and region1 to 4, all5, all5-dense) of 011 reads `events=cme` and carries the columns cme_l1d_refill_rd_per_load, cme_l1d_refill_hwprf_per_load, cme_l1d_refill_wr_per_load with non-zero values on the cme-fresh rows, which is the split set (demand read 0x3280 / hardware prefetch 0x32B2) the page defines in section 8. (3) cmn-counts.csv of 011 holds labels cme-ocm-reg

## [19] asimov-cme-perf.html | 8. Mesh counters | wording

**Page text:** The 8 MiB CME command with every line flushed first spread its 7,280,163 requests evenly over the five nodes, which fits the address hash.

**Source says:** cmn-counts.csv of 004 (run 3), label cme-dram-flushed-8M-cpu2: 1,461,104 + 1,460,635 + 1,454,701 + 1,452,658 + 1,451,065 = 7,280,163. cmn-counts.csv of 011 (boot F1), the same label: 7,061,170 (1,407,799 to 1,414,866 per node). The paragraph now covers both runs, and the sentence does not say which run the number belongs to.

**Suggested:** On run 3 the 8 MiB CME command with every line flushed first spread its 7,280,163 requests evenly over the five nodes (F1: 7,061,170, 1,407,799 to 1,414,866 per node), which fits the address hash.

**Verifier:** Confirmed from primary sources. results/membench-jibin-004/results/19700101T000000Z/cmn-counts.csv rows 456-460 (label cme-dram-flushed-8M-cpu2, hns_pocq_reqs_recvd_all, nodes 88/160/216/288/344) sum to 1,461,104 + 1,460,635 + 1,454,701 + 1,452,658 + 1,451,065 = 7,280,163, so the page number is run 3's. results/membench-jibin-011/results/bootF1/cmn-counts.csv rows 456-460, same label, read 1,413,946 + 1,410,993 + 1,407,799 + 1,413,566 + 1,414,866 = 7,061,170 (per node 1,407,799 to 1,414,866), so F1's count differs. The generator (gen_perf_cme.py:410) takes the number from g.FLUSH_SPREAD, the run 3 reader, with no run label. On the page (asimov-cme-perf.html line 167, section 8) the sentence 

## [20] asimov-cme-perf.html | 10. Open items, the hypothesis item (fixed cost per timed span) | unsupported claim

**Page text:** hypothesis A fixed cost of 0.1 to 0.3 us est. per timed span (CME wake-up from dynamic power-down, Jesse's run 3 README bounds) inflates the 64-load OCM passes: on boot E the one line per page medians run 3.6 to 12.7 ns above the bests (section 7). Run 6's in-span time does not separate the first pass from the later ones. A row that times the first and the later passes of one span separately would decide it.

**Source says:** cme-latency-ocm-region*.csv of 011 and 012: each of the 7 OCM passes (cme-fresh1 to cme-fresh7) is its own call and streaming span and prints its own ns_per_load_span, so run 6 does separate the passes. On F1 bracket minus span is 286 to 292 ns per call on every pass of every region (F2: 280 to 304), while the pass-to-pass spread, 3.1 to 8.7 ns per load (region 4: 38.797 to 47.531 ns), is carried in span (span spread 3.2 to 8.8 ns) and the first pass is not the slowest (region 1: pass 5 is best at 37.281, pass 3 slowest at 44.125). On F2, the prefetchers off, the spread is 0.16 to 0.66 ns per load. A fixed cost outside the span cannot produce the spread, and the spread goes away with the prefetcher off. Jesse's F1 README (CME rows) gives the same outside-span figure, 286 to 292 ns per call on the sparse OCM passes.

**Suggested:** hypothesis, narrowed by run 6 A fixed cost per timed span (CME wake-up from dynamic power-down, Jesse's run 3 README bounds it at 0.1 to 0.3 us est.) was the earlier reading of the OCM pass spread (on boot E the one line per page medians run 3.6 to 12.7 ns above the bests, section 7). Run 6 times every OCM pass in its own span: on F1 each pass spends 286 to 292 ns outside its span, the same on every pass of a region within 6 ns, while the pass-to-pass spread of 3.1 to 8.7 ns per load sits inside the span, and on F2 (the prefetchers off) the spread is 0.2 to 0.7 ns per load [cme-latency-ocm-region*.csv of 011 and 012]. So the spread is the prefetcher's, not a wake-up outside the span. Whether a wake-up sits in the span's first loads is still unmeasured; a row that times the first load of a span apart from the rest would decide it.

**Verifier:** Confirmed from the CSVs, the README and the generator. The page sentence "Run 6's in-span time does not separate the first pass from the later ones" (gen_perf_cme.py line 424, rendered in section 10) is wrong: in results/membench-jibin-011/results/bootF1/cme-latency-ocm-region{0..4}.csv and the same files of 012/bootF2, each of the 7 OCM passes (rows cme-fresh1 to cme-fresh7, 64 loads each) is its own call in its own streaming span and prints its own ns_per_load_span (column 6). Recomputed per pass, (ns_per_load - ns_per_load_span) x 64 loads gives the outside-span time per call: F1 286 to 292 ns on every pass of every region (region 0: 286-290, 1: 286-291, 2: 286-292, 3: 286-289, 4: 286-292

## [21] asimov-cme-perf.html | 10. Open items, the L3-state item | unsupported claim

**Page text:** No mesh counter has run around a CME command with the split refill events on.

**Source says:** log.txt of 011 lines 88 to 94 and cmn-counts.csv of 011: boot F1 ran cmncount around the seven CME OCM chain commands (cme-ocm-region0-cpu2 to cme-ocm-region4-cpu2, cme-ocm-all5-cpu2, cme-ocm-all5-dense-cpu2), each with --perf, and their CSV files (cme-latency-ocm-*.csv of 011) carry the split events cme_l1d_refill_rd, cme_l1d_refill_hwprf and cme_l1d_refill_wr. The item is settled by run 6 and should not be listed as open.

**Suggested:** Delete the sentence, or move it to the settled item: 'the mesh counted around CME chain commands with the split refill events on (boot F1, section 8)'.

**Verifier:** Confirmed from primary sources, not refuted. (1) results/membench-jibin-011/results/bootF1/log.txt, run_cme.sh phase F: seven commands 'cmn cme-ocm-region0-cpu2' .. 'cmn cme-ocm-region4-cpu2', 'cmn cme-ocm-all5-cpu2', 'cmn cme-ocm-all5-dense-cpu2' (and 'cmn cme-dram-flushed-8M-cpu2'), each 'latency --cme --cpu 2 --perf ...'. (2) results/bootF1/cmn-counts.csv of 011 holds mesh rows under those labels (e.g. cme-ocm-region0-cpu2, hns_pocq_reqs_recvd_all node 88 = 45,698; nodes 160/216/288/344 = 8,672/8,280/8,877/8,741; hns_mc_reqs_local_all 7,058; hns_cache_miss_all 8,583); 135 cme-* rows in all. (3) results/bootF1/cme-latency-ocm-region0.csv of 011 (header events=cme) has columns cme_l1d_refil

## [22] asimov-cme-perf.html | 10. Open items, the settled item | unsupported claim

**Page text:** settled By run 6: the bandwidth set with the L3 on (section 6), the cost per call of a read (section 6.1), the L3-served load through the CME (section 5.2), the demand-only OCM latency through the CME (section 7), the memory model's delay (section 2.2), and run 6's kernels' first run on Arm (cme_test, exit 0).

**Source says:** The 186 ns per pass that section 6.1 reads from the looped read's fit (cme-bandwidth-l1-passes.csv of 011) is by the bracket and includes run 6's two in-span stamps (ISB plus CNTVCT read): cme-call reads 124.5 to 125.7 ns on F1 and F2 against 42.5 to 43.9 on boot E, and the 1 KiB write call 124.1 ns against run 3's 39.1 (cme-bandwidth-call-cost.csv of 011 and 004), so about 82 to 95 ns of a one-call-per-span row is stamp cost, and the in-span time still holds part of the stamp pair (the 1 KiB write's span reads 48.0 ns where run 3 timed the whole call at 39.1). No run 6 row isolates the stamp cost, so the hardware cost of a read call is not settled: 186 ns less about 82 to 95 ns is about 91 to 104 ns, near run 3's 97.2.

**Suggested:** settled By run 6: the bandwidth set with the L3 on (section 6), the L3-served load through the CME (section 5.2), the demand-only OCM latency through the CME (section 7), the memory model's delay (section 2.2), and run 6's kernels' first run on Arm (cme_test, exit 0). Partly settled: the looped read's cost per pass, 186 ns by the bracket, of which about 82 to 95 ns is run 6's in-span stamps (cme-call reads 124.5 ns against boot E's 42.5), so the hardware cost of a read call is about 91 to 104 ns est. and no run 6 row isolates it (section 6.1).

**Verifier:** Confirmed from the primary sources. Section 10's "settled" item [gen_perf_cme.py:427] points at section 6.1, whose headline sentence is "A read call costs about 186 ns, half of it the fold" [gen_perf_cme.py:398], with the 186 taken from the looped read's bracket fit (cme-bandwidth-l1-passes.csv of 011) and from the 1 KiB call-cost row (results/membench-jibin-011/results/bootF1/cme-bandwidth-call-cost.csv: elapsed 0.000762 s / 4096 passes = 186.0 ns, span 108.0 ns). That bracket time includes run 6's two in-span stamps. Recomputed stamp cost from the rows: cme-call reads 42.52 to 43.92 ns in 63 reps on boot E (results/membench-jibin-010/results/bootE/cme-latency-*.csv, no stamps) and 124.52 t

## [23] asimov-cme-perf.html | Table 4.7 caption (also printed in section 5.2) | wording

**Page text:** a 23.4, h 6.7, s 13.9, o 20.4 ns est. (rms 0.02 ns)

**Source says:** The fit's numbers recompute from cme-latency-dram-small-l3.csv of 012 (15 reps, 96 to 384 KiB): a 23.36, h 6.67, s 13.86, o 20.39, root mean square of the residuals 0.019 ns. 'rms' is not defined anywhere on the page (its two occurrences are this caption and its copy), so the plain-English rule on metric names is broken.

**Suggested:** a 23.4, h 6.7, s 13.9, o 20.4 ns est. (rms, the root mean square of the fit's residuals, 0.02 ns)

**Verifier:** Confirmed. The fit recomputes from results/membench-jibin-012/results/bootF2/cme-latency-dram-small-l3.csv (15 cme-repeat rows, 96 to 384 KiB, same design matrix as gen_run6.py l3_fit): a 23.36, h 6.67, s 13.86, o 20.39, rms 0.019 ns, so every number in the caption is right. The wording defect stands: after stripping tags from asimov-cme-perf.html, the string "rms" appears only twice, in the Table 4.7 caption (gen_perf_cme.py line 212) and its copy in section 5.2. Neither "Words used here" (section 1) nor the section 3.1 inline glossary defines it. The definition "Root mean square of the residuals..." exists only in gen_perf.py line 282, which feeds the core page's word list, not the CME pag

## [24] asimov-cme-perf.html | 10. Open items, the L3-state item | wording

**Page text:** F2's BL31 hook read 0x70 on all nine power-ons

**Source says:** 'BL31' appears twice on the page (section 2.2 and here) and is defined in neither place nor in Words used here. Jesse's F2 README (The prefetchers; The L3) uses it for TF-A's runtime stage, whose hook in 0.35.0-pfoff.1 reads the registers at every power-on.

**Suggested:** F2's BL31 hook (BL31 is TF-A's runtime firmware stage; its hook reads the registers at every power-on) read 0x70 on all nine power-ons

**Verifier:** Confirmed. On /home/jhan/workspace/titan/cache-perf/asimov/asimov-cme-perf.html the string "BL31" occurs exactly twice: in section 2.2 ("0x70 in all nine BL31 readings and the two runtime ones") and in the section 10 open item ("F2's BL31 hook read 0x70 on all nine power-ons"). Neither place defines it. The "Words used here" section defines "SCP, TF-A" (Trusted Firmware-A, the boot firmware of the application cores) but has no BL31 entry, and "TF-A"/"Trusted Firmware" occur only in the glossary and in 2.2 without tying BL31 to TF-A. The F2 README (results/membench-jibin-012/README.md line 18) says "this boot's BL31 is TF-A 0.35.0-pfoff.1 ... The hook runs at EL3 at the end of every power-on 

## [25] asimov-cme-perf.html | 5.2 The L3-served load through the CME: boot F2 | wording

**Page text:** Footprint | F2 ns per load | minus the round-trip baseline | F2 inner refills (0x327D) | ... (the whole table 4.7, printed a second time after the figure)

**Source says:** gen_perf_cme.py prints {t6} under the 4.7 heading (line 357) and again inside section 5.2 (line 380), so the same 6-row table with the same caption appears twice on the page (the caption string 'F2 snoops (miss minus refill, derived)' occurs twice in the HTML). The 5.2 text already cites it as 'table 4.7'.

**Suggested:** Drop the second copy in section 5.2 and keep the reference '(table 4.7)' in the 'Two sources inside the cluster' paragraph.

**Verifier:** Confirmed. gen_perf_cme.py emits the same table string {t6} at line 357 (under the 4.7 heading) and at line 380 (inside section 5.2, after the f_l3 figure). In asimov-cme-perf.html the resulting <div class="tbl"> block is byte-identical in both places (1444 bytes; line 114 under id="t47", line 137 under id="l3cme"), and the caption 'F2 snoops (miss minus refill, derived)' occurs twice on the page. Section 5.2's 'Two sources inside the cluster' bullet already cites 'table 4.7', so the second copy is redundant. Severity: wording (duplicate table), not a wrong number.

## [26] asimov-c1nano-perf.html | Short version | unsupported claim

**Page text:** The bandwidth set of sections 4.4 to 4.6, 8 and 9 is run 3's, measured with the L3 holding no data.

**Source says:** Tables 4.4, 4.5 and 4.6 and section 9 of the same page now carry run 6 boot F1 columns (bandwidth-pair.csv, bandwidth-perdsu.csv, bandwidth-all8.csv, bandwidth-write-cpus*.csv, bandwidth-ocm-*.csv of 011, the L3 on) beside run 3's. The next Short version bullet says so itself.

**Suggested:** Tables 4.4 to 4.6 and section 9 give run 6 boot F1's values (the L3 on) beside run 3's (the L3 off). Section 8 is run 3's only.

**Verifier:** Confirmed. The sentence is fixed text in gen_perf_core.py line 320. On the generated page, table 4.4 (header "Boot F1 GB/s (L3 on, run 6) | Run 3 GB/s (L3 off) | F1 vs run 3", caption cites bandwidth-pair.csv, bandwidth-perdsu.csv, bandwidth-all8.csv of 011), table 4.5 (same F1 column, bandwidth-write-cpus*.csv of 011), table 4.6 and 4.6.1 (F1 read and write columns, bandwidth-ocm-*.csv of 011) and section 9 (64 mentions of boot F1 rows, e.g. "CPU 2+3 read 16 KiB: 116.407 GB/s run 3, 112.409 GB/s boot F1") all carry run 6 boot F1 values beside run 3's. Those CSVs exist in results/membench-jibin-011/results/bootF1. Section 8 has zero F1/011/run 6 mentions, so it alone is run 3's. The page's o

## [27] asimov-c1nano-perf.html | Short version | wrong number

**Page text:** every write row repeats run 3 within 6.4 % (sections 7 and 9)

**Source says:** bandwidth-pair.csv of 011 against 004: the two-thread write at 160 KiB reads 58.250 GB/s against 47.241 (+23.3 %), and at 48 KiB 61.943 against 59.070 (+4.9 %). The 6.4 % bound (gen_perf_core.py line 435) is computed over write rows of 2 MiB and above only (max +6.45 % on the eight-core 2 MiB write).

**Suggested:** every write row of 2 MiB and above repeats run 3 within 6.4 %, and the pair's 160 KiB write rises 23 % (sections 7 and 9)

**Verifier:** Confirmed from primary sources. The Short version of asimov-c1nano-perf.html reads "every write row repeats run 3 within 6.4 % (sections 7 and 9)". The placeholder (gen_perf_core.py line 325) takes the max over g.PAIR + g.PERDSU + g.ALL8 write rows with size >= 2097152 only, so the 16, 48 and 160 KiB pair writes are excluded from the bound. Recomputed from the best rows of bandwidth-pair.csv (results/membench-jibin-011/results/bootF1 against results/membench-jibin-004/results/19700101T000000Z): two-thread write at 160 KiB is 58.250 GB/s on F1 against 47.241 on run 3 (+23.30 %), at 48 KiB 61.943 against 59.070 (+4.86 %), at 16 KiB 60.755 against 61.153 (-0.65 %). The rows of 2 MiB and above: 

## [28] asimov-c1nano-perf.html | Short version | wording

**Page text:** four cores on four DSUs read 98.1 GB/s together (run 3 34.0) and eight cores 107.6 (run 3 66.7)

**Source says:** bandwidth-perdsu.csv and bandwidth-all8.csv of 011 and 004: 98.072 / 33.957 and 107.593 / 66.673 are the 16 MiB per-thread rows. The 2 MiB rows read 100.200 / 34.614 and 108.733 / 67.756, and section 9's caption quotes those. The Short version names no footprint, so the two sets of numbers look like a contradiction.

**Suggested:** four cores on four DSUs read 98.1 GB/s together at 16 MiB each (run 3 34.0) and eight cores 107.6 (run 3 66.7)

**Verifier:** Confirmed from the CSVs. Short version text: "four cores on four DSUs read 98.1 GB/s together (run 3 34.0) and eight cores 107.6 (run 3 66.7)". These are the 16 MiB-per-thread best rows: results/membench-jibin-011/results/bootF1/bandwidth-perdsu.csv read,4,16777216,best = 98.072; results/membench-jibin-004/results/19700101T000000Z/bandwidth-perdsu.csv read,4,16777216,best = 33.957; bandwidth-all8.csv read,8,16777216,best = 107.593 (011) and 66.673 (004). The 2 MiB-per-thread best rows in the same files read 100.200 / 34.614 (4 cores) and 108.733 / 67.756 (8 cores), and section 9's caption on the page quotes exactly those: "four cores on four DSUs read 100.2 GB/s together at 2 MiB each (2.89 

## [29] asimov-c1nano-perf.html | 9. Multi-core DRAM reads and writes, and writer placement (second figure caption) | wrong number

**Page text:** Every multi-core write row and every writer-placement row repeats run 3 within 6.4 % with the L3 on (the pair's 160 KiB write 1.23 times).

**Source says:** bandwidth-pair.csv of 011 against 004: the pair's 160 KiB write is +23.30 % and its 48 KiB write +4.86 %. The sentence states a 6.4 % bound for every row and then names a row outside it. gen_perf_core.py line 435 filters d['size'] >= 2097152.

**Suggested:** Every multi-core write row of 2 MiB and above and every writer-placement row repeats run 3 within 6.4 % with the L3 on. The pair's small writes move more: 1.05 times at 48 KiB and 1.23 times at 160 KiB.

**Verifier:** Confirmed from primary sources. Recomputed best-of-reps aggregate_GBps for every write row in bandwidth-pair.csv, bandwidth-perdsu.csv, bandwidth-all8.csv and bandwidth-write-cpus*.csv of results/membench-jibin-011/results/bootF1 against results/membench-jibin-004/results/19700101T000000Z: pair 16 KiB -0.65 %, pair 48 KiB +4.86 %, pair 160 KiB +23.30 % (58.250 vs 47.241 GB/s, 1.233 times), perdsu 2 MiB and 16 MiB 0.00 %, all8 2 MiB +6.45 %, all8 16 MiB +0.52 %, the six writer-placement rows within 0.03 %. The 6.4 % figure in gen_perf_core.py line 435 is max over g.PAIR + g.PERDSU + g.ALL8 write rows filtered with d['size'] >= 2097152, so it excludes the three pair rows (16, 48, 160 KiB), yet

## [30] asimov-c1nano-perf.html | 4.4 Multi-core DRAM bandwidth (note under the table, 'Where write loses instead') | unsupported claim

**Page text:** With the L3 on, one core reads 24.5 GB/s from DRAM (section 7). How the multi-core rows change with it is Insufficient data (not run).

**Source says:** The table above this note now holds the multi-core rows with the L3 on from bandwidth-pair.csv, bandwidth-perdsu.csv and bandwidth-all8.csv of 011: four readers 100.2 GB/s at 2 MiB (run 3 34.6), eight readers 108.7 (run 3 67.8), eight writers 165.2 (run 3 155.2).

**Suggested:** With the L3 on, one core reads 24.6 GB/s from DRAM (section 7). Run 6 boot F1 ran these rows with the L3 on: the four-DSU readers rise from 34.6 to 100.2 GB/s at 2 MiB, the eight readers from 67.8 to 108.7, and the write rows of 2 MiB and above stay within 6.4 % (the F1 column above).

**Verifier:** Confirmed from primary sources. The sentence comes from gen_perf_core.py line 215, a fixed string: "How the multi-core rows change with it is Insufficient data (not run)." The run 6 boot F1 CSVs hold those rows with the L3 on: results/membench-jibin-011/results/bootF1/bandwidth-perdsu.csv 'best' row dram,read,4,2097152 = 100.200 GB/s (run 3, results/membench-jibin-004 bandwidth-perdsu.csv = 34.614); bandwidth-all8.csv dram,read,8,2097152 best = 108.733 (run 3 67.756); dram,write,8,2097152 best = 165.154 (run 3 155.154, +6.45 %); the other write rows of 2 MiB and above change by +0.00 %, -0.00 % and +0.52 %. The table directly above the note on the page already prints these F1 values in its "

## [31] asimov-c1nano-perf.html | 4.6.1 One core, read and write by level (caption) | unsupported claim

**Page text:** Run 3's 256 KiB read row (10.2 GB/s) was not repeated with the L3 on. Boot E's 256 KiB chase counts 0.00 L3 read refills per load where run 3's counted 0.75, so on an L3-on boot that row would be served from the L3 (hypothesis: not measured).

**Source says:** bandwidth-dram-1core.csv of 011 (the L3 on): the 256 KiB read row reads 26.297 GB/s (best of reps 0 to 2), and the same table's 'Boot F1 read' column shows 26.3 on that row.

**Suggested:** Run 6 boot F1 repeated the 256 KiB read row with the L3 on: 26.3 GB/s against run 3's 10.2 [bandwidth-dram-1core.csv of 011]. Boot E's 256 KiB chase counts 0.00 L3 read refills per load where run 3's counted 0.75, so that row is read as an L3 row on the L3-on boots (a capacity reading: the bandwidth row carries no counters).

**Verifier:** Confirmed from primary sources. results/membench-jibin-011/results/bootF1/bandwidth-dram-1core.csv (sha256 matches the run's SHA256SUMS) holds dram,read,1,262144 reps at 26.122, 26.150, 26.297 GB/s with best 26.297, under a 262144-byte, 32-pass, 3-rep header, the same command line as run 3; the 011 README states the L3 of CPU 2's cluster was on (IMP_CLUSTERPWRSTAT_EL1 0x70, fcheck staging=PASS box=PASS) and run_asimov.sh was run 3's byte for byte. The same table on the page shows 26.3 in the 'Boot F1 read GB/s (L3 on, run 6)' column on the 256 KiB row. So the caption sentence 'Run 3's 256 KiB read row (10.2 GB/s) was not repeated with the L3 on' and the trailing '(hypothesis: not measured)' 

## [32] asimov-c1nano-perf.html | 12. Open items ('Why the L3 makes a read stream faster') | unsupported claim

**Page text:** Run 6 boot F1 repeats it (24.6 GB/s) and shows the same on every read stream that misses the L3: the one-core sweep from 48 KiB (1.56 to 2.69 times run 3), four readers on four DSUs (2.89 times), eight readers (1.61) and the one-pass OCM reads (1.21 to 1.36)

**Source says:** Table 4.3 of the same page labels the 48 KiB and 96 KiB one-core rows as L2 footprints and the 256 KiB row as 'L2 and L3' with the L3 on (the buffer is 128 KiB L2 and 256 KiB L3, read warm over 128, 64 and 32 passes). Those rows do not miss the L3. Only the 2 MiB and 32 MiB rows (2.69 and 2.68 times, bandwidth-dram-1core.csv of 011 and 004) are streams beyond the L3. Also, 1.61 is the eight readers' 16 MiB row (107.593 / 66.673) while section 9 quotes 1.60 for the 2 MiB row.

**Suggested:** Run 6 boot F1 repeats it (24.6 GB/s) and shows the same on every read stream beyond the L3: the one-core reads at 2 and 32 MiB (2.68 to 2.69 times run 3), four readers on four DSUs (2.89 times at 16 MiB), eight readers (1.61 at 16 MiB) and the one-pass OCM reads (1.21 to 1.36). The L2 and L3 footprints of the one-core sweep (48 KiB to 256 KiB) rise 1.56 to 2.59 times as well.

**Verifier:** Confirmed, not refuted. The generator (gen_perf_core.py line 450) builds the 1.56 to 2.69 range over every one-core read row with size >= 49152, so the range includes the 48 KiB (27.299/17.483 = 1.561), 96 KiB (26.877/12.057 = 2.229) and 256 KiB (26.297/10.164 = 2.587) rows beside the 2 MiB (25.044/9.311 = 2.690) and 32 MiB (24.575/9.172 = 2.679) rows [bandwidth-dram-1core.csv of 011 and 004]. The same page's table 4.3 (gen_perf.py line 169, capacity reading by size: L1 32 KiB, L2 128 KiB, L3 256 KiB per DSU; sysinfo lines 101-104 cited in the F1 README) labels the 48 KiB and 96 KiB L3-on rows "L2" and the 256 KiB row "L2 and L3", and its caption says these readings are hypotheses because no

## [33] asimov-c1nano-perf.html | 2.2 Run 6 boot F1 ('What F1 adds to this page') | wrong citation

**Page text:** the sparse and all-five OCM chains and the SLC chains from CPUs 4 and 6 (tables 4.2)

**Source says:** Table 4.2 holds no SLC chain. F1's SLC chains read 24.828 ns (CPU 4), 24.390 (CPU 6) and 26.202 (CPU 8) [latency-dram-slc-cpu<c>.csv of 011], and none of these values, nor the file name, appears anywhere on the page (0 matches in asimov-c1nano-perf.html).

**Suggested:** the sparse and all-five OCM chains from CPUs 4 and 6 (table 4.2). F1's 2 MiB SLC chains from CPUs 4, 6 and 8 (24.8, 24.4 and 26.2 ns [latency-dram-slc-cpu<c>.csv of 011]) are not on this page.

**Verifier:** Confirmed, not refuted. Primary sources checked: (1) The page sentence exists verbatim in asimov-c1nano-perf.html section 2.2 and is a literal string in gen_perf_core.py:356. (2) Table 4.2 ("4.2 OCM latency by region, from four CPUs", built from t2, t2b, t2c at gen_perf_core.py:154-200) holds only OCM region route rows, the all-five OCM chains and the distance grouping; the extracted section text (5,404 chars) contains the word "SLC" 0 times. Its F1 columns come only from latency-ocm-region<r>-cpu<c>.csv and latency-ocm-all5*-cpu<c>.csv of 011. (3) The F1 SLC chains exist: results/membench-jibin-011/results/bootF1/latency-dram-slc-cpu{4,6,8}.csv, 'best' rows read 24.828, 24.390 and 26.202 ns

## [34] asimov-c1nano-perf.html | 2.2 Run 6 boot F1 ('Controls and repeats') | wording

**Page text:** the L1, L2 and DRAM chains, the flushed row and the one-core writes hold within 1.9 % of run 3

**Source says:** latency-dram-small.csv, latency-dram-large.csv, latency-dram-flushed.csv and bandwidth-dram-1core.csv of 011 against 004: 4 to 128 KiB within 1.25 %, 6 to 32 MiB within 1.88 %, the flushed row 0.15 %, the one-core writes 1.6 %. But the 4 MiB fresh chain, which table 4.1 labels 'SLC and DRAM (mixed)' like the 6 and 8 MiB rows, reads 29.379 against 28.270 (+3.9 %), and the 512 KiB to 1 MiB chains read 0.757 to 0.963 times run 3's. The reader cannot tell which rows the 1.9 % covers (Jesse's F1 README groups them as 6 to 32 MiB: 0.981 to 1.001).

**Suggested:** the L1 and L2 chains (4 to 128 KiB) hold within 1.3 % of run 3, the DRAM chains from 6 to 32 MiB within 1.9 %, the flushed row within 0.2 % and the one-core writes within 1.6 %; the 4 MiB chain reads 3.9 % above run 3 and the 512 KiB to 1 MiB chains 4 to 24 % below it (the L3)

**Verifier:** Confirmed from primary sources. The page sentence is typed text in /home/jhan/workspace/titan/cache-perf/asimov/gen_perf_core.py line 355, not computed. It cites Jesse's F1 README (Core rows) and latency-dram-*.csv of 011. The README, line 10 and the Core rows table, qualifies the claim: "The L1 and L2 chases, the DRAM chases from 6 MiB, the flushed row, his controls, the one-core writes ... held within 1.9%", with the 6 to 32 MiB rows at 0.981 to 1.001 and the 1.5 to 4 MiB rows at 0.984 to 1.039. The page dropped "from 6 MiB". Recomputed from the best rows of results/membench-jibin-011/results/bootF1 against results/membench-jibin-004/results/19700101T000000Z: latency-dram-small.csv 4 to 12

## [35] asimov-c1nano-perf.html | 4.7 Home-node attribution of the 20 sparse per-region rows (caption) | wrong citation

**Page text:** Requests received per home node (hns_pocq_reqs_recvd_all) over the whole command [cmn-counts.csv of 004 and 002].

**Source says:** The table's 'Own node, boot F1 (L3 on, run 6)' and 'Own / others, F1' columns come from cmn-counts.csv of 011 (for example OCM0 chain, CPU 2: 47,417 on node 88, ratio 5.7), which the citation does not name.

**Suggested:** Requests received per home node (hns_pocq_reqs_recvd_all) over the whole command [cmn-counts.csv of 011, 004 and 002].

**Verifier:** Confirmed from primary sources. The page's table 4.7 (asimov-c1nano-perf.html, caption at offset ~77865) carries two run 6 columns, "Own node, boot F1 (L3 on, run 6)" and "Own / others, F1". The generator builds them from ATTR1 = K1["ATTR"] [gen_perf_core.py:44, :240], and K1's ATTR is computed from cmn_rows(R + "cmn-counts.csv") with R = results/membench-jibin-011/results/bootF1/ [gen_run6.py:24-25, :124-125]. Recomputed row OCM0 chain, CPU 2: 011's bootF1/cmn-counts.csv holds ocm-region0-cpu2,hns_pocq_reqs_recvd_all,88,47417 and the other four nodes 8355, 8255, 8416, 8209, giving 47417 / 8308.75 = 5.71, matching the page's 47,417 and 5.7. That row does not occur in 004's or 002's cmn-count

## [36] asimov-c1nano-perf.html | 4.2 OCM latency by region (caption of the first table) | unsupported claim

**Page text:** only 0.30 to 0.65 of their loads are read from the mesh, the rest are served by the L3, so these values are below the true OCM latency, as boot E's are.

**Source says:** latency-ocm-region<r>-cpu<c>.csv of 011 count 0xA2 (L3 read refills from outside the cluster) at 0.30 to 0.65 per load as the pass mean. These rows run with events=prefetch and carry no L3 hit event (0x81C6), so the counters say only that the other loads were filled inside the cluster; which level served them is an inference.

**Suggested:** only 0.30 to 0.65 of their loads are read from the mesh (0xA2 per load); the rest are filled inside the cluster, by the L3 on the page's reading (hypothesis: these rows count no L3 hit event), so these values are below the true OCM latency, as boot E's are.

**Verifier:** Confirmed, not refuted. The number is right: the per-row mean of l3d_refill_rd_per_load (0xA2) over the 7 fresh passes of the 20 files results/membench-jibin-011/results/bootF1/latency-ocm-region<r>-cpu<c>.csv spans 0.2991 to 0.6518, which rounds to the page's 0.30 to 0.65 (same recipe as gen_run6.py load_core, mean_e(ps, 'l3d_refill_rd')). The claim 'the rest are served by the L3' is not supported by a primary source: (1) every one of those files runs with events=prefetch and its header carries only l1d_refill, l2d_refill, l3d_refill_rd, l1d_refill_hwprf, l2d_refill_hwprf and l2d_refill_l1dhwprf; no L3 hit event (0x81C6) is counted, so no row says which level served the loads. (2) The same 

## [37] asimov-c1nano-perf.html | 2.2 Run 6 boot F1 | wording

**Page text:** the CME rows gain in-span timing and the single-call forms ... The AP's DRAM is four Cadence AXI memory models, one per SMS lane ... fixed pipeline between the mesh's SN bridges and the memory

**Source says:** The 'Words used here' list defines PMU, TRM, SOG, SCP, TF-A and the rest, but not CME (the C1-SME2 streaming unit), in-span timing, AP (the application processor), SMS (the DRAM subsystem lane name in Jesse's README), SN (the mesh's subordinate node, the SBSX bridge) or AXI (the Arm bus protocol of the memory model). Each appears here at first use without a definition (plain-English rule 1).

**Suggested:** the CME rows (the CME is the C1-SME2 streaming unit, one per DSU; its rows are on asimov-cme-perf.html) gain in-span timing (a second clock pair inside the streaming-mode span) and the single-call forms ... The AP's (application processor's) DRAM is four Cadence AXI (Arm bus protocol) memory models, one per SMS lane (SMS: the memory subsystem, four lanes) ... fixed pipeline between the mesh's SN bridges (the SBSX nodes that connect the mesh to memory) and the memory

**Verifier:** Confirmed from the page text (asimov-c1nano-perf.html, tags stripped). The "Words used here" list holds 19 entries (PMU/TRM/SOG, TLB, C1-Nano/DSU, L1/L2/L3, mesh/crosspoint, home node/SLC, OCM, node id, chase, repeated chase, sparse chain, best/pass/rep, refills per load, perf_cov, cmncount, SCP/TF-A, chip time, est., run/boot) and none of them is CME, AP, SMS, SN, AXI or in-span. A whole-page grep finds no "SME2", "streaming unit", "application processor", "subordinate", "memory subsystem" or "bus protocol" anywhere, so none of these terms is defined inline either. Occurrences: "CME" first appears inside the PMU entry of section 1 ("the counters of a core, of the CME or of the mesh"), then 

## [38] asimov-cme-perf-brief.html | 3. The numbers side by side, row 'Cost per call (the four L1 forms, 4 to 24 KiB)' | unsupported claim

**Page text:** read call about 183 ns, 52 of it the fold | boot F1 (run 6) | the looped read's line (ns per pass against bytes) gives 186 ns per pass, the single-call read's 3.4.

**Source says:** The 183 ns is the looped-read fit intercept (186.2 ns, cme-bandwidth-l1-passes.csv of 011, cme-read 4 to 24 KiB) minus the single-call intercept (3.4 ns, cme-bandwidth-l1-asmpasses.csv of 011). Every looped-form call on run 6 carries the in-span stamp pair: the cme-call rows of 011 read 124.5 to 125.6 ns per call against boot E's 42.5 to 43.9 (cme-latency-*.csv of 010), and the 1 KiB read call of cme-bandwidth-call-cost.csv of 011 reads 186.1 ns against run 3's 97.2 (004). So about 82 to 89 ns of the 183 ns is the clock reads, not the call. The full page (section 6.1) states this ('Bracket minus span is 82 ns per call'); the brief does not.

**Suggested:** read call about 183 ns by run 6's bracket, of which about 82 to 89 ns is run 6's own in-span clock reads (cme-call 124.5 to 125.6 ns against boot E's 42.5 to 43.9; the 1 KiB read call 186 ns against run 3's 97); 52 of it the fold. The call's cost without the clock reads is not measured by any run 6 row (about 95 to 100 ns est.).

**Verifier:** Confirmed from primary sources. Every number in the brief's row is right: the looped read's fit intercept is 186.2 ns per pass by the bracket (103.9 in span), the single-call read's 3.4 ns, the no-fold read's 134.2 ns, so 186.2 - 3.4 = 182.8 -> 183 and 186.2 - 134.2 = 52.0 [cme-bandwidth-l1-passes.csv, -asmpasses.csv, -nofold.csv of results/membench-jibin-011/results/bootF1, cme-read 4 to 24 KiB, best rep, fit as gen_run6.py load_cme FORM does]. The defect is the missing qualification. The looped form makes one call per pass and every run 6 call carries the in-span stamp pair (ISB + two CNTVCT reads); the single-call form carries one pair per 1024-pass rep, so the 183 ns difference holds one

## [39] asimov-cme-perf-brief.html | 4. What it means, bullet 'The L3 on costs the CME's writes' (the same words in the section 2 caption and in row 'Write bandwidth, 16 KiB to 32 MiB') | wrong number

**Page text:** On boots F1 and F2 alike the CME writes 53 GB/s to 256 KiB and 40 from 1 MiB, in span too

**Source says:** cme-bandwidth-dram-1core.csv of 011, cme-write best reps: by the bracket 52.42 / 51.64 / 52.42 / 52.34 / 52.53 GB/s at 16 / 48 / 96 / 160 / 256 KiB and 41.67 / 42.64 / 40.45 at 1 / 2 / 32 MiB; in span 69.54 / 56.27 / 54.83 / 53.81 / 53.48 at 16 to 256 KiB and 41.89 / 42.79 / 40.46 from 1 MiB. 012 (F2) reads the same within 1 GB/s (in span 69.05 and 56.09 at 16 and 48 KiB). In span the write is 70 and 56 GB/s at 16 and 48 KiB, not 53, and from 1 MiB the rate is 40 to 43, not 40.

**Suggested:** On boots F1 and F2 alike the CME writes 52 to 53 GB/s by the bracket from 16 KiB to 256 KiB (in span 53 to 55 from 96 KiB on, and 70 and 56 at 16 and 48 KiB) and 40 to 43 GB/s from 1 MiB, in span too

**Verifier:** Confirmed from the CSVs, not refuted. Source: results/membench-jibin-011/results/bootF1/cme-bandwidth-dram-1core.csv (F1) and results/membench-jibin-012/results/bootF2/cme-bandwidth-dram-1core.csv (F2), rows 'dram,cme-write,1,<bytes>,best' (aggregate_GBps = column 8, span_GBps = last column). F1 best reps by the bracket: 52.42 / 51.64 / 52.42 / 52.34 / 52.53 GB/s at 16 / 48 / 96 / 160 / 256 KiB and 41.67 / 42.64 / 40.45 at 1 / 2 / 32 MiB. F1 in span: 69.54 / 56.27 / 54.83 / 53.81 / 53.48 at 16 to 256 KiB and 41.89 / 42.79 / 40.46 from 1 MiB. F2 by the bracket: 52.15 / 51.49 / 52.41 / 52.28 / 52.51 and 41.34 / 39.54 / 40.36; F2 in span: 69.05 / 56.09 / 54.76 / 53.79 / 53.44 and 41.56 / 39.67 

## [40] asimov-cme-perf-brief.html | 4. What it means, bullet 'The L3 on costs the CME's writes' | wrong number

**Page text:** where run 3 wrote 62 at every footprint with the L3 off

**Source says:** cme-bandwidth-dram-1core.csv of 004, cme-write best reps: 63.73 / 63.82 / 63.82 / 63.78 / 63.87 / 63.87 / 63.87 GB/s at 16 KiB to 2 MiB and 61.97 at 32 MiB. The brief's own row 'Write bandwidth' says 'run 3 wrote 62 to 64'.

**Suggested:** where run 3 wrote 64 GB/s at 16 KiB to 2 MiB and 62 at 32 MiB with the L3 off

**Verifier:** Confirmed from primary sources. results/membench-jibin-004/results/19700101T000000Z/cme-bandwidth-dram-1core.csv, cme-write 'best' rows: 63.731 (16 KiB), 63.821 (48 KiB), 63.818 (96 KiB), 63.784 (160 KiB), 63.865 (256 KiB), 63.865 (1 MiB), 63.865 (2 MiB), 61.971 (32 MiB) GB/s. So run 3 wrote 64 (rounded) at seven of eight footprints and 62 only at 32 MiB, not '62 at every footprint'. The generator shows why: gen_brief.py line 257 formats b32m['write'] (the 32 MiB row alone, 61.97 -> '62') and pairs it with the words 'at every footprint'; gen_perf_cme.py line 389 has the same placeholder and wording on the full page. The brief's own 'Write bandwidth' row says 'run 3 wrote 62 to 64 with the L3

## [41] asimov-cme-perf-brief.html | 3. The numbers side by side, row 'L3-served load, 192 / 256 / 384 KiB chain, CME prefetcher off' | wrong number

**Page text:** one demand refill per load, 0.91 to 0.99 of it from inside the cluster.

**Source says:** cme-latency-dram-small.csv of 012: cme_l1d_refill_inner_per_load of the best rep is 1.000 / 0.997 / 0.958 at 192 / 256 / 384 KiB (the mean of the three reps is 0.986 / 0.934 / 0.909). The table's footnote says 'Best rep or best pass of each row', and the full page's table 4.7 quotes the best rep (0.96 to 1.00 at these sizes; 'From 96 to 384 KiB F2 counts 0.91 to 1.00 inner refills per load' in section 5.2). The brief's 0.91 to 0.99 is the rep mean, not the best rep, and does not appear on the full page.

**Suggested:** one demand refill per load, 0.96 to 1.00 of it from inside the cluster (best rep; the three reps' mean 0.91 to 0.99).

**Verifier:** Confirmed in substance, with two corrections to the reviewer's numbers.

What the primary sources say:
- gen_brief.py line 185 builds the brief's range from d["emean"]["cme_l1d_refill_inner"], the mean over the three reps, for the 192 / 256 / 384 KiB rows of CLV2 (gen_run6.py line 149: emean = mean over passes, e = best pass).
- results/membench-jibin-012/results/bootF2/cme-latency-dram-small.csv, column cme_l1d_refill_inner_per_load: reps at 192 KiB 0.9891 / 0.9851 / 0.9853 (mean 0.986), at 256 KiB 0.8918 / 0.9129 / 0.9970 (mean 0.934), at 384 KiB 0.9522 / 0.8906 / 0.8838 (mean 0.909). So "0.91 to 0.99" is the rep mean. The best rep (lowest ns: 33.910 / 32.779 / 33.014) carries 0.985 / 0.99

## [42] asimov-cme-perf-brief.html | 1. Latency, figure caption | unsupported claim

**Page text:** Boot F2 (run 6: the L3 on, the prefetchers off) repeats boot B to 64 KiB and reads 32.8 to 33.9 ns at 192 to 384 KiB, where the L3 serves it.

**Source says:** cme-latency-dram-small-l3.csv of 012, best rep: cme_l3d_hit_per_load 0.493 / 0.619 / 0.637 at 192 / 256 / 384 KiB with inner refills 1.000 / 0.997 / 0.958 per load. The L3-hit event accounts for half to two thirds of the loads; the brief's own row 3 and section 4 call the rest 'CPU 2's own cache (hypothesis)', and the full page (section 5.2) says 'served inside the cluster' with the split a hypothesis.

**Suggested:** Boot F2 (run 6: the L3 on, the prefetchers off) repeats boot B to 64 KiB and reads 32.8 to 33.9 ns at 192 to 384 KiB, where every load is served inside the cluster (0.49 to 0.64 per load by the exploratory L3-hit event; the rest is a hypothesis, section 4).

**Verifier:** Confirmed from primary sources. The caption's numbers come from cme-latency-dram-small.csv of 012 (best rows 33.910 / 32.779 / 33.014 ns at 192 / 256 / 384 KiB; gen_brief.py:183,244 take min and max of CLV2 repeat rows, so 32.8 to 33.9 is right). The claim "where the L3 serves it" is not supported as fact: cme-latency-dram-small-l3.csv of 012 (bootF2), best reps by ns, give cme_l3d_hit_per_load 0.4934 (192 KiB rep 2) / 0.6186 (256 KiB rep 2) / 0.6375 (384 KiB rep 0) with cme_l3d_miss_per_load 0.5066 / 0.3814 / 0.3625 and cme_l1d_refill_inner_per_load 0.9996 / 0.9965 / 0.9583. So the L3-hit event accounts for about half to two thirds of the loads, and the L3-miss event counts the rest as miss

## [43] asimov-cme-perf-brief.html | 3. The numbers side by side, row 'L1 hit, dependent load, 4 to 64 KiB, CME prefetcher off' | wording

**Page text:** L1 hit, dependent load, 4 to 64 KiB, CME prefetcher off | 2.0 ns (4 KiB) | 21.0 to 21.3 ns | boots B, F2

**Source says:** The core cell is gen_brief's c[(4096,'repeat')]['core'], boot E's 4 KiB core row (latency-dram-small.csv of 010, 2.002 ns), the same measurement the row above ('Dependent load, 4 KiB chain', 2.0 ns, boot E) already carries. The row's Source column says 'boots B, F2', but F2 ran no core rows (012 holds cme-*.csv only) and boot B's 4 KiB core row (latency-dram-small.csv of 006) reads 2.001 ns, which is not the number used.

**Suggested:** L1 hit, dependent load, 4 to 64 KiB, CME prefetcher off | 2.0 ns (4 KiB, boot B) | 21.0 to 21.3 ns | boots B, F2   (or leave the core cell empty with 'as the row above')

**Verifier:** Confirmed from the generator and CSVs. The core cell of the row 'L1 hit, dependent load, 4 to 64 KiB, CME prefetcher off' is c[(4096,'repeat')]['core'] [gen_brief.py:219]; CME_LEVELS sets core=_LV["E"][(size,kind)]["ns"] [gen_perf.py:231], i.e. boot E's core chase. Boot E (010) latency-dram-small.csv best row: dram,4096,best,-,-,2.002 -> printed 2.0 ns. Boot F2 (012/results/bootF2) contains only cme-*.csv, cmn-counts.csv, log.txt, all.txt: no core latency rows at all. Boot B (006/results/bootB) latency-dram-small.csv 4 KiB best row reads 2.001 ns, which the cell does not use. So the Source column 'boots B, F2' misattributes the core cell; the number itself is not wrong (both B and E round to

## [44] asimov-cme-perf-brief.html | Words used here (whole page) | wording

**Page text:** Words used here: CME, streaming mode; run, boot; bracket, in span; looped form, single-call form; round-trip baseline

**Source says:** Terms used on the brief with no definition at first use or in the list: OCM (first in 'run, boot': 'the OCM mapped with a 64 KiB hint'; the SRAM regions on the mesh), SLC (chart mark 'SLC 3.75 MiB', row '2 MiB chain walked once (SLC on the core)'), TLB (CME definition), crosspoints (row 'OCM, one region, 1 to 3 crosspoints'), DSB ST and 'posted stores' and 'the fold' (row 'Cost per call'), SOG, TRM and 'the LLVM model' (row 'CME pipeline widths'), GA13 Palladium (the opening line). The plain-English rule asks for every code name, acronym and metric to be defined at first use.

**Suggested:** Add to Words used here: 'OCM: the on-chip SRAM, five regions, each behind one home node of the mesh. SLC: the system level cache on the mesh, 3.75 MiB over five home nodes. Crosspoint: one switch of the CMN S3 mesh; the distance from the DSU to a region's home node is 1 or 3 crosspoints. Fold: the end-of-call sum of the read kernel's 16 running totals. DSB ST: the Arm barrier that waits for every earlier store. SOG, TRM: Arm's Software Optimization Guide and Technical Reference Manual. LLVM model: the public C1-Nano scheduling model in LLVM (refs/C1Nano-streaming-cme-instructions.s). GA13 Palladium: the emulator that runs the Asimov RTL.' and in the CME entry '(TLB, the translation buffer)'.

**Verifier:** Confirmed from the brief's own text (/home/jhan/workspace/titan/cache-perf/asimov/asimov-cme-perf-brief.html, tags stripped). The 'Words used here' list holds only four entries: 'CME, streaming mode', 'run, boot', 'bracket, in span; looped form, single-call form', and 'round-trip baseline'. Each term the reviewer named appears on the page with no definition at first use or in the list: OCM (first use in the 'run, boot' entry: 'C and D the OCM mapped with a 64 KiB hint'), SLC (chart mark 'SLC 3.75 MiB' in section 1, row '2 MiB chain walked once (SLC on the core)' in section 3), TLB (in the CME entry: 'its own 64 KiB L1 data cache, TLB and hardware prefetcher'), crosspoints (row 'OCM, one regi

## [45] asimov-c1nano-perf-brief.html | 3. What else the runs showed, run 6 bullet (class r6) | wording

**Page text:** The dependent chains do not move either (CPU 2's L3 rows repeat boot E within 0.2 ns).

**Source says:** The bullet's other sentences compare boot F1 with run 3 ('times run 3's rate', 'against 34.0', 'of run 3'). Against run 3 the 192 / 256 / 384 KiB chains did move: latency-dram-small.csv of 011 reads 7.825 / 9.509 / 10.986 ns against 004's 14.045 / 19.333 / 22.729 (0.48 to 0.56 times; Jesse's F1 README, Read first). Against boot E (010: 7.821 / 9.527 / 11.004) the difference is 0.004 to 0.018 ns, so 'within 0.2 ns' is true but ten times looser than the data; the 0.2 is literal text in gen_brief.py, not computed. The full page's section 12 makes the narrower claim 'The dependent chains beyond the L3 do not move either'.

**Suggested:** The dependent chains repeat boot E (CPU 2's 192 to 384 KiB rows within 0.02 ns of E), so against run 3 they keep boot E's change: 0.48 to 0.56 times at 192 to 384 KiB, and the other chains within 1.9 %.

**Verifier:** Confirmed from primary sources. (1) The "0.2" is literal text in gen_brief.py line 155 ("repeat boot E within 0.2 ns"), not a computed placeholder. (2) Recomputed from the 'best' rows of latency-dram-small.csv: boot F1 (results/membench-jibin-011/results/bootF1) reads 7.825 / 9.509 / 10.986 ns at 192 / 256 / 384 KiB; run 3 (results/membench-jibin-004/results/19700101T000000Z) reads 14.045 / 19.333 / 22.729 (F1 is 0.557 / 0.492 / 0.483 times run 3); boot E (results/membench-jibin-010/results/bootE) reads 7.821 / 9.527 / 11.004 (max |F1 - E| over all 12 sizes is 0.018 ns). The F1 README confirms these figures (line 10 and table row "A: chase 192, 256 and 384 KiB | 0.557, 0.492, 0.483"). (3) Th

## [46] asimov-c1nano-perf-brief.html | 4. Caveats, run 6 bullet (class r6) | wrong citation

**Page text:** Answered: the memory model has no configured delay (every delay control zero, a 3 ns native response); the rest of the DRAM leg is RTL pipeline by Jesse's stage count, an inference [Jesse's F1 README, The memory model behind the home node].

**Source says:** results/membench-jibin-011/README.md, 'The memory model behind the home node' and 'Read first': 'about 20 ns of the DRAM leg is fixed RTL pipeline by the box's count of its stages (an inference), and the rest is inside the CMN, which nothing in this tree configures' and 'The rest of his ~29 ns is inside the CMN ... this README does not determine its share.' The README does not say the whole rest of the leg is RTL pipeline; it splits it into about 20 ns of pipeline and an undetermined CMN share. The CME full page (section 2.2) states the README's split correctly.

**Suggested:** Answered: the memory model has no configured delay (every delay control zero, a 3 ns native response in the repo's Xcelium test). By Jesse's count of the RTL stages (an inference) about 20 ns of the DRAM leg is fixed pipeline between the mesh's SN bridges and the memory; the rest of the about 29 ns is inside the mesh, not configured anywhere in the tree and not determined [Jesse's F1 README, The memory model behind the home node].

**Verifier:** Confirmed from primary sources. The brief page bullet (gen_brief.py:164, rendered in asimov-c1nano-perf-brief.html section 4, class r6) reads: "the rest of the DRAM leg is RTL pipeline by Jesse's stage count, an inference". The README (results/membench-jibin-011/README.md) does not support attributing the whole rest to the stage count. Line 15 ("Read first"): "about 20 ns of the DRAM leg is fixed RTL pipeline by the box's count of its stages (an inference), and the rest is inside the CMN, which nothing in this tree configures". Line 250: the stage count gives 20.0-20.5 ns (ports 0-2) or 19.0-19.5 ns (port 3), "The rest of his ~29 ns is inside the CMN ... this README does not determine its sh

## Refuted (not defects)

- asimov-cme-perf.html | 8. Mesh counters: hypothesis The extra requests are the CME's refills above one per load (prefetches), seen at the home node. -- Refuted. The numbers the reviewer quotes are right (recomputed from cmn-counts.csv of 004 and 011: F1 CME OCM read on its own node / core = 1.26, 0.73, 0.77, 0.73, 0.75; F1 / run 3 for regions 1-4 = 0.467, 0.469, 0.464, 0.459; F1 chain-row cme_l1d_refill_hwprf_per_load pass means 0.41 to 0.47), but 