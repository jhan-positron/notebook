# Spec: update the four Asimov performance pages to the latest data (run 4 boot E)

Project dir: /home/jhan/workspace/titan/cache-perf/asimov (not a git repo). Scratchpad for temporary files:
/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/perf-update/
The previous versions of the four pages and of the two scripts are in that scratchpad's prev/ folder (read-only reference).

## 1. Goal

Rebuild these four pages so that they carry the latest measurements, keep their current section structure, and have
up-to-date open items:

- asimov-c1nano-perf.html  (the C1-Nano core: latency, bandwidth, OCM, mesh)
- asimov-c1nano-perf-brief.html  (its two-page brief)
- asimov-cme-perf.html  (the CME, the cluster's C1-SME2 unit)
- asimov-cme-perf-brief.html  (its two-page brief)

"Keep the structure" means: the same numbered sections with the same subjects, in the same order (headings may be
reworded where the subject's run changes, e.g. "run 3 against run 2" becomes "boot E against run 3"). Do not add or
remove top-level sections. Subsections may gain a row, a column or a figure series; none is removed.

## 2. Hard rules

- Every number on a page is read from the CSV files by the generator. No typed-in measurements. Platform facts quoted
  from Jesse's README files are cited as such. Reference values from asimov-bench stay as gen_run3.BENCH (cited).
- Do NOT edit gen_run3.py or gen_run4.py (another session owns them; gen_run4.py imports gen_run3's names as "run 3"
  data and slices gen_run3.WORDS_COMMON by index). Do not edit anything under results/. Do not run gen_run4.py or
  gen_run3.py as scripts (they overwrite other pages). Import them only.
- New module layout (gen_run3 must not import gen_run4; gen_run4 imports gen_run3, so the new code imports both):
    gen_perf.py        the data layer for the four pages + main() that writes all four pages
    gen_perf_core.py   core_page() -> HTML string for asimov-c1nano-perf.html
    gen_perf_cme.py    cme_page()  -> HTML string for asimov-cme-perf.html
    gen_brief.py       core_brief(), cme_brief() for the two briefs (rewrite of the existing file; keep its CSS,
                       page(), fig() and the two-A4-page limit)
  gen_perf.py's main imports each page module inside a try/except and writes what it can, printing which page
  failed and why, so the page modules can be built and tested in parallel. Run `python3 gen_perf.py` to regenerate.
- HTML: light theme only (single theme, white background), `<meta charset="utf-8">` in the head, ASCII only inside
  SVG text (no en dash, no arrows), `<title>` kept short. Keep gen_run3's CSS, page(), fig(), table(), chart helpers
  (line_chart, dumbbell, strip, bars_h, mesh_map, cme_path_fig) by importing them from gen_run3; add helpers in
  gen_perf.py if a new figure form is needed (gen_run4 has dotplot and stacked_h).
- Prose rules (the plain-english skill, in CLAUDE.md): define every term at first use, one claim per sentence, every
  number carries a unit and, where needed, a meaning clause, citations in brackets after the sentence, "Short version"
  of at most three sentences at the top, no idioms, bullets for multi-point paragraphs, short sentences, no semicolons
  joining clauses.
- Estimates are labelled "est." with units. Never an estimate where a measurement exists.
- A claim ties to a test row (file name in brackets) or to a source. A reading that the data does not prove is labelled
  `<span class="hyp">hypothesis</span>` with the measurement that would decide it. Where data is missing, write
  "Insufficient data" and name the measurement that would resolve it. gen_run4 has hyp(), ok(), no(), gap() helpers
  and the CSS classes .hyp .ok .gap exist in gen_run3's CSS.
- Do not quote boot D's 0.003 walks per hop as the effect of the 64 KiB hint: the TLB-set row and the walk row are two
  processes of one boot with different walk rates (D 0.003 vs 0.438 per hop); the cause is Insufficient data
  (asimov-c1nano-run4.html section 13.1).
- The OCM number to quote is the dense all-five chain from CPU 2 (latency-ocm-all5-dense-cpu2.csv). Sparse per-region
  rows read higher (TLB and prefetch costs) and on boot E they partly hit in the L3.
- Both briefs must still print on at most 2 A4 pages. Check with the headless shell:
    ~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-linux/headless_shell --headless --no-sandbox \
      --print-to-pdf=/tmp/claude-0/.../scratchpad/perf-update/x.pdf --no-pdf-header-footer file:///home/jhan/workspace/titan/cache-perf/asimov/asimov-c1nano-perf-brief.html
    then count pages: python3 -c "import re,sys;print(len(re.findall(rb'/Type\s*/Page[^s]', open(sys.argv[1],'rb').read())))" x.pdf
  (look for the binary under ~/.cache/ms-playwright/chromium_headless_shell-*/ if that path differs).

## 3. The data: what "latest" means

Runs and boots (all in results/membench-jibin-NNN/results/<dir>/, with README.md and dmesg.txt one level up):

| Name | Dir | Date | Commit | Firmware | Prefetchers | OCM pages | L3 of CPUs 2 to 9 |
|---|---|---|---|---|---|---|---|
| run 2 | 002/results/*/ | 2026-11-01 | ba834c0 (?) see gen_run3 | SCP 0.48.0, TF-A 0.35.0 | on | 4 KiB | off (snoop-filter only) |
| run 3 | 004/results/*/ | 2026-11-03 | see gen_run3 | SCP 0.48.0, TF-A 0.35.0 | on | 4 KiB | off |
| run 4 boot A | 005/results/bootA/ | 2026-11-04 | e8e4580 | SCP 0.48.0, TF-A 0.35.0 | on | 4 KiB | off |
| boot B | 006/results/bootB/ | 2026-11-04 | 7921962 | TF-A 0.35.0-pfoff | off | 4 KiB | off (reg 0x0) |
| boot C | 007/results/bootC/ | 2026-11-05 | b79dffa | as A | on | 64 KiB contiguous hint | off (reg 0x0) |
| boot D | 008/results/bootD/ | 2026-11-05 | ed6056a | as B | off | 64 KiB hint | off (reg 0x0) |
| boot E | 010/results/bootE/ | 2026-11-05 | b79dffa | SCP 0.48.0-nopcie-l3.1 (rebuilt, L3 staged on), TF-A 0.35.0 | on | 4 KiB | ON (IMP_CLUSTERPWRSTAT_EL1 0x70 on CPU 2's cluster) |

(Take the exact commit ids, firmware strings and dates from gen_run4.EX[x]["commit"], EX[x]["scp"], EX[x]["tfa"],
EX[x]["pwrstat"] and the README files; the table above is a guide, not a source.)

Decision: the "latest" number of every row is run 4 boot E's. Boot E is the newest boot and the first with the DSU L3
in use as a cache, which is the intended hardware configuration. The earlier runs had the L3 off because the stock SCP
stages the full-L3 mode for cluster 0 only (Jesse's boot B and E READMEs). The pages must say this plainly at the
top: the run 3 numbers (and run 2's) were measured with the L3 holding no data.

Beside boot E, the pages show:
- run 3 (the previous content of these pages) as the comparison column where boot E repeated the row;
- boot C (same commit as E, L3 off, prefetchers on, 64 KiB OCM hint) where a comparison isolates the L3
  (E/C ratios: 4 to 128 KiB 0.986 to 1.002; 192/256/384 KiB 0.55/0.48/0.49; 2 MiB 24.177 vs 24.053; 32 MiB 52.875 vs
  52.238; 8 MiB flushed 52.659 vs 52.657; sequential 8 MiB 2.492 vs 6.917 ns);
- boot A (L3 off, 4 KiB pages, prefetchers on: the configuration closest to run 3) where the OCM per-region rows need an
  L3-off reference; boots B and D (prefetchers off) where a sentence needs the demand-only reading.

Rows that run 4 did not repeat keep run 3's numbers, labelled in the table note and in the text as
"run 3 (the L3 off); not repeated with the L3 on". These are: the one-core bandwidth sweep by footprint
(bandwidth-dram-1core.csv), multi-core DRAM bandwidth (bandwidth-pair/perdsu/all8.csv), writer placement
(bandwidth-write-cpus*.csv), bandwidth-dram-spread.csv, OCM bandwidth (bandwidth-ocm-*.csv), every CME bandwidth row
(cme-bandwidth-*.csv incl. call cost and the 64-byte forms), the CPU 4 and CPU 6 OCM, SLC and control rows, and the
mesh-counter attribution rows (cmn-counts.csv labels other than route-*). Where a boot E row partly covers one of
these (the plain one-core read at 2 MiB and 32 MiB in bandwidth-read-prefetch.csv; the L1 rows at 4 to 24 KiB in
bandwidth-l1-passes.csv and bandwidth-l1-asmpasses.csv; the small write rows at 16 to 256 KiB in
bandwidth-write-small.csv), show the boot E value beside run 3's in that table.

New on boot E, to add to the existing sections (not new sections):
- the L3 hit set (latency-dram-small-l3.csv, 64 KiB to 512 KiB, with l3d_hit_rd per load: 0.4651 at 192 KiB, 0.7508
  at 256 KiB, 0.9236 at 384 KiB, 0.4118 at 512 KiB; gen_run4.E_L3) -> section 4.1 / 5;
- the sequential 8 MiB chain (latency-dram-seq.csv: 2.492 ns on E, 6.917 on C) -> section 4.1 / 5 as a row;
- the one-core read variants (bandwidth-read-prefetch.csv: plain 24.945 GB/s at 2 MiB and 24.546 at 32 MiB on E; C 9.294
  and 9.196; the PRFM variants read lower on E: pf4 20.196/20.353) -> section 4.3 / 7;
- the L1 bandwidth rows G8 (gen_run4.G8['E'] and ['C']: asm read 53.1/57.9/60.3/60.6 GB/s at 4/8/16/24 KiB on E;
  write fits 32.0 GB/s; read fits fail the 2 % residual rule so no single per-pass number for reads) -> section 4.3 / 7;
- the route rows under the crosspoint counters (20 cells, dense chain, CPUs 2/4/6/8 x OCM0..4; gen_run4.BT['E']['ROUTE'])
  -> section 4.2 / 6 / 10, with boot A's as the L3-off reference;
- the walk and TLB rows (latency-dram-tlb-cpu2.csv, latency-dram-walk-cpu2.csv, latency-ocm-*-tlb/-walk) -> one or two
  sentences in section 6 and the open items, under the walk-rate rule above.

Facts to state (verified against the CSVs on 2026-11-05; the generator must recompute them, never type them):
- Controls: 4 KiB chase 2.002 ns on every boot; cme-roundtrip 21.004 to 21.006 ns; every boot exit 0, no "# perf:" lines.
- Boot E L3: hits 0.4651/0.7508/0.9236 per load at 192/256/384 KiB; chases 7.811/9.489/10.906 ns (C: 14.101/19.690/22.669);
  an L3 hit costs about 10.6 to 11.0 ns est. (gen_run4.L3_HIT_EST, a derived number: label est. and say how it was derived).
- 2 MiB SLC chase E 24.177 vs C 24.053; 32 MiB E 52.875 vs C 52.238 (A 52.181, B 52.248, D 52.249); 16 MiB 51.167 vs
  50.686; 8 MiB flushed 52.659 vs 52.657. The +0.6 ns at 32 MiB on E is a hypothesis (translation walks); not settled.
- DRAM 52 ns reading: on boot B an address-order 8 MiB chain reads 52.762 ns and a random one 52.739 ns, so the memory
  model (emulator memory, not LPDDR5X) answers in a fixed time; 24 ns of it is the home-node hop (the 2 MiB SLC row),
  the rest (about 29 ns est.) the model's delay. Its configured delay is an open question to Jesse.
- One-core DRAM read: 9.2 GB/s with the L3 off (run 3, C) and 24.9/24.5 GB/s with it on (E); the mechanism inside the
  DSU is Insufficient data (the counters do not show it); the PRFM variants lower it on E.
- L1 read 58 GB/s on run 3 = 91 % of the 64 GB/s dual 128-bit path; G8 on C and E: asm form 60.2 to 60.6 GB/s at 16/24 KiB
  and the marginal 8 to 16 KiB rate 62.8 to 64.8 GB/s (the path's limit), so the shortfall is a per-pass cost;
  writes fit 32 GB/s with 24 to 26 ns (per-pass form) / 9 to 14 ns (asm form) per pass; E's 4 KiB per-pass read 40.9 vs
  C's 46.2 GB/s is unexplained (Insufficient data).
- OCM: dense all-five from CPU 2: E 26.082, A 26.009, C 24.959, B 25.576, D 24.959 ns (gen_run4.ALL5_DENSE_BEST); E's
  per-region rows count 0.42 to 0.63 L3 read refills per hop (A, C: 0.72 to 0.87), so part of their hops hit the L3 and
  they are not OCM latency alone. The 64 KiB hint lowers the per-region rows (C/D vs A/B, GM about 0.86 to 0.98 by pair,
  see gen_run4.RATIOS) and the L1 DTLB refills per pass fall from 21 to 559 (A) to 11 to 15 (C, D) (gen_run4.TLB_PASS).
  Prefetchers off (B): the 20 route cells fit distance within 0.09 ns rms, so most of the within-distance spread was the
  prefetchers' (gen_run4.BT['B']['FIT']['route']).
- CME on E: 4 KiB 21.371, 8 KiB 24.932 ns (boot C's values from gen_run4.BT['C']['CLV']); E/C ratios 8 KiB 1.019, 16 KiB 1.120,
  48 to 384 KiB 0.940 to 0.977; E outer refills 0.01/1.22 per load at 8/16 KiB vs C 3.28/6.50 (gen_run4.CME_INNER_SHARE,
  BT[x]['CLV'][..]['emean']['cme_l1d_refill_outer']); flushed 8 MiB E 62.053 vs C 62.556; sequential 8 MiB through the
  CME 21.417 ns on A, C and E (every refill a prefetch); boot B (CME prefetcher off): 21.02 to 21.26 ns from 4 to 64 KiB,
  37.16 at 96 KiB, so the climb from 8 KiB is the CME prefetcher's; through the CME no row gives an L3 hit number.
- CME OCM on E: sparse best 28.98 to 37.67 ns by region, all-five dense 43.28 ns, sparse all-five 34.62 (run 3: 35.5 to
  38.5 sparse, 44.7 dense).
- Repeat check boot E vs run 3 (gen_run4.BT['E']['REPEAT_SAME'], 70 rows with the same file and size): 24 within 1 %,
  39 within 3 %, 47 within 5 %; the largest changes are the L3 rows (192 to 512 KiB, -24.6 to -51.6 %) and OCM rows.
  Boot A vs run 3 (same configuration) is the repeatability pair: gen_run4.BT['A']['REPEAT_SAME'] / N_WITHIN.

## 4. Section-by-section mapping

### asimov-c1nano-perf.html (gen_perf_core.py), sections as in prev/asimov-c1nano-perf.html
Title: "Asimov C1-Nano Memory Performance" with the subtitle naming run 4 boot E (membench-jibin-010, 2026-11-05, the
L3 on) as the latest, run 3 (004) beside it, and the boots quoted. Short version: three sentences, the level map with
the L3 on (L1 2.0, L2 6.0, L3 hit about 11 ns est., SLC 24.2, DRAM 52.7 flushed), the one-core DRAM read 24.5 GB/s,
and that the bandwidth set below is run 3's with the L3 off.
1. Words used here: gen_run3.WORDS_COMMON plus the new terms (L3 hit set, sequential chain, route row, hint, boot),
   and the L3 entry reworded for the L3-on data (do not change gen_run3.WORDS_COMMON itself; build a new list).
2. The run and the platform: boot E's platform (README 010), the five boots in one small table (gen_run4.FIVE), chip
   time 3.250 s / 138 commands; 2.1 "What changed from run 3 to run 4 boot E": commit, SCP rebuild, L3 on, rows dropped
   (CPU 4/6, the bandwidth set), rows added (hit set, seq, read variants, G8, TLB/walk, route rows).
3. The hemisphere map: gen_run3.mesh_map; the L3 box now reads "L3 256 KiB per DSU (on, boot E)".
4. Summary tables:
   4.1 Latency by level, CPU 2: boot E against run 3 and boot C, with E's L3 hits per load where the hit set measured
       them (64 KiB to 512 KiB) and the refills; a level name column for the L3-on reading (write a level_name_e in
       gen_perf.py: 192 to 384 KiB = "L2 and L3 (mixed)" with the hit share in the row, do not reuse gen_run3.level_name's
       "held no data" wording for boot E rows). Add the sequential 8 MiB row.
   4.2 OCM latency by region: boot E route rows (20 cells, dense, under counters) with E's L3 refills per hop, boot A's
       route rows (L3 off) as the reference, run 3's sparse rows, distance, and the dense all-five rows for CPUs 2 and 8
       (E, A, C, run 3). Note that CPU 4 and 6 have route rows only on run 4.
   4.3 One-core bandwidth by footprint: run 3's sweep (read/write/copy) with boot E (and C) values beside it where they
       exist (G8 4 to 24 KiB read/write, 16 to 256 KiB write-small, 2 MiB and 32 MiB plain read); label the rest run 3.
   4.4, 4.5, 4.6, 4.6.1: run 3 only, each note saying so and that the L3 was off. 4.6.1 adds the E read at 2/32 MiB.
   4.7 Home-node attribution: run 3's 20 sparse rows (unchanged) plus a sentence that boot E's route rows count the
       crosspoint directions instead (X first in 20 of 20 cells on A; quote E's XFIRST_DSU/NODE from BT['E']).
   4.8 Every row that moved 1 % or more: boot E against run 3 (REPEAT_SAME sorted), and a line on boot A against run 3.
5. Latency by level: the chart gains boot E as the main series, run 3 (and boot C dashed) beside it; the takeaway names
   the L3 step; the hit-set rows as a second small chart or table.
6. OCM latency by region: dumbbell of E route vs A route (or E sparse vs run 3 sparse), the distance analysis from A/B,
   E's L3-hit caveat, the hint and prefetcher findings (B, C, D), the TLB sentence, the walk-rate rule.
7. One-core bandwidth by level: run 3 chart plus the E points; the G8 finding; the 24.5 GB/s DRAM read with the L3 on.
8. Multi-core DRAM writes and writer placement: run 3 unchanged, with the L3-off label and the open item.
9. OCM bandwidth: run 3 unchanged, labelled.
10. Mesh counters: run 3's attribution unchanged, plus boot E's route counters (directions, shares) in a short table.
11. Open items: rewrite (section 5 below).
12. Sources: 010, 007, 005, 006, 008, 004, 002 dirs and READMEs, gen_perf.py, gen_run3.py, gen_run4.py, the run 4 pages.

### asimov-cme-perf.html (gen_perf_cme.py), sections as in prev/asimov-cme-perf.html
Same scheme: boot E's CME rows (BT['E']['CLV'], COCM, CALL5, RT) as the latest, run 3 and boot C beside, boot B for the
prefetcher-off reading; the bandwidth sections (4.3, 4.4, 4.5, 6) stay run 3, labelled; 4.6 and 8 (mesh counters) stay
run 3 (boot E has no CME counter rows), labelled; 3.1 data-path figure says the L3 is on for boot E; 9 (against
asimov-bench) updated with E's numbers; 10 settled/open rewritten (section 5 below).

### The briefs (gen_brief.py)
Same sections as prev/. Core brief: level table with the L3 row measured (7.8 ns at 192 KiB with 47 % hits, 9.5 / 10.9 ns
at 256 / 384 KiB with 75 / 92 % hits, L3 hit about 11 ns est.), the bandwidth bars with run 3's rows labelled "(run 3,
L3 off)" and the E one-core read bar added, "What else the run showed" and "Caveats" rewritten to the current state.
CME brief: table and bullets from E, bandwidth rows run 3 labelled. Both at most 2 A4 pages when printed.

## 5. Open items (the content of core section 11, CME section 10, and the briefs' caveats)

Settled (cite the file or the run 4 page section):
- The L3 of CPUs 2 to 9 held no data on runs 1 to 3 and boots A to D (register 0x0, 0 hits); boot E's rebuilt SCP turns
  it on (0x70; 47/75/92 % hits at 192/256/384 KiB; 7.8/9.5/10.9 ns).
- The 52 ns DRAM chase is a fixed-delay memory model: 24 ns home-node hop plus about 29 ns est.; unchanged with the L3 on.
- One-core DRAM read 9.2 -> 24.5 GB/s with the L3 on; PRFM hints do not help (C) and lower it (E).
- L1 read 58 GB/s shortfall is per-pass cost (G8); writes fit the 32 GB/s path.
- OCM: the sparse rows' excess over dense = TLB refills + prefetch fills (A counts, B/C/D isolate); dense all-five is the
  number (26.1 ns on E); route spread mostly the prefetchers' (B fit 0.09 ns rms).
- The small write rows' per-pass cost is the program's (G5, boot A).
- CME: the climb from 8 KiB is the CME prefetcher's (B); L1 hop 21.0 to 21.3 ns; no CME L3 hit number exists.
Open (each with the measurement that would resolve it):
- The memory model's configured delay (asked of Jesse, unanswered).
- The bandwidth set (one-core sweep, multi-core, writer placement, OCM bandwidth, all CME bandwidth) has not run with
  the L3 on; those rows are run 3's.
- Boot E's 4 KiB per-pass L1 read 40.9 GB/s vs C's 46.2: Insufficient data.
- The walk rate differs 129x between two processes of one boot (D: 0.003 vs 0.438 per hop): Insufficient data.
- The G8 read fits fail the 2 % residual rule, so no single per-pass cost for reads.
- +0.6 ns at 32 MiB and +0.5 ns at 16 MiB on E vs C: hypothesis translation walks; a walk-counted 32 MiB row on E and C
  in one process would test it.
- The L3 state of the clusters of CPUs 4 to 9 on boot E was not read (the README says the reading covers CPU 2's cluster).
- The CPU 4 and 6 OCM, SLC and control rows have not run since run 3.
- CME: two cores of one DSU streaming at once; matmul operands in OCM; which level served a CME load (no CME event names
  it); the CME with the L3 on shows no L3 step because the prefetcher sets the time.

## 6. Verification (what the verify agents check; the build agents self-check the same)

1. `python3 gen_perf.py` runs clean and writes the four files. Each page has <meta charset="utf-8">, a light theme only
   (no prefers-color-scheme dark block), ASCII-only SVG text, and the section headings of prev/ in the same order.
2. Numbers: recompute at least 30 numbers per full page and 15 per brief directly from the CSV files with an
   independent python3 -I script (do not import the generators for the check) and compare to the page text: every
   number in the Short version, the first and last row of every table, every number in a figure caption, every number in
   the open items. Report each mismatch with file, row and both values.
3. Labels: every run 3 bandwidth number is labelled as run 3 with the L3 off; every estimate carries "est."; every
   hypothesis is labelled; no "held no data" sentence applies to boot E rows; D's 0.003 walks per hop is not quoted as the
   hint's effect; the OCM number quoted is the dense all-five row.
4. Plain English: the eight rules; report violations with the phrase and a fix.
5. Briefs: 2 A4 pages each (headless print).
6. gen_run3.py and gen_run4.py are unchanged (sha256 4f4109038fb89144... for gen_run3.py; compare with prev/).
