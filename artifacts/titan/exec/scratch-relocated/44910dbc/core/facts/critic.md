# Critic sheet (BINDING). It overrides every other sheet in `facts/`.

## Short version

- The critic recomputed 398 values from the raw CSV files with its own parser. Every measured row value
  in the eight sheets agrees. Seven statements differ from the files (section 1.2), and 23 corrections
  are binding (section 2).
- All six boots stay in scope, each for a narrow use. Boot F1 carries every result. Boot C is ruled IN
  for two uses that SPEC did not list, because without it two figures mix the L3 state with the
  prefetcher state.
- The page has 8 sections, 26 figures, 32 tables and about 15,300 words of prose (section 5).

Where this sheet and another sheet disagree, this sheet wins. Where this sheet and SPEC.md disagree on a
fact that a file proves (the OCM mapping of boots C and D), this sheet wins and says so.

Scripts (all `python3 -I`, in `SCR/scripts/`): `critic_lib.py` (own parser, own least squares),
`critic_latency.py` (88 checks), `critic_bw.py` (129), `critic_ocm.py` (65), `critic_scope.py` (63),
`critic_extra.py` (53). Each prints numbered lines `[NNN] tag value`.

---

## 1. Recomputation result

### 1.1 What was recomputed (all agree with the sheets to the printed digit)

| Group | Count | Script |
|---|---|---|
| Boot F1 footprint sweep: best ns, reps, spread, cycles, six counters, line numbers, 24 rows | 24 | critic_latency [001-024] |
| Count of rows with spread under 0.7 %, "L2 refills not accounted for" at 192, 256, 384 KiB, clock pooled 2.00025 over 79 rows | 5 | [025-029] |
| Background controls (5), 2 MiB row from CPUs 4, 6, 8 (3) | 8 | [030-037] |
| Boot E over boot F1, 12 + 11 rows, flushed row | 13 | [038-050] |
| Boot E hit-set rows (7), two counter identities, L3 estimate per rep (4 rows), sensitivity | 15 | [051-065] |
| Address-order chain on E, C, B, D with counters | 5 | [066-070] |
| Random chains B, D, C, R3 against F1; 32 KiB; 4 MiB by boot | 16 | [071-086] |
| Bracket overhead (39 commands, median 39 ns, max 59 ns), perf_cov (247 rows) | 2 | [087-088] |
| Boot F1 one-core bandwidth, 18 rows, steps, two write fits | 22 | critic_bw [001-022] |
| Boot E L1 forms, 16 rows, four fits with the 2 % rule, looped minus single-call | 24 | [023-046] |
| Read variants on E, B, C, D with per-line counters and ratios | 31 | [047-077] |
| Boot F1 over boot R3, one-core, 6 footprints | 6 | [078-083] |
| Multi-core rows (21), second-core gain (6), writer placement (7) | 34 | [084-117] |
| OCM bandwidth (8 rows), ratios to DRAM rows, counted 2 MiB read, stream over chain est. | 12 | [118-129] |
| OCM chains of F1 (every line, one line per page, 20 cells, void fit) | 13 | critic_ocm [002-014] |
| Route fits on B, D, E, one-slope fit, 120 port permutations, cells by steps, fit at mean steps | 20 | [015-034] |
| Page mapping D over B, L1 TLB refills per pass, dmesg `cont=` counts | 12 | [035-046] |
| Mesh counters of F1: controls, helper cost, own node, shares, sent on to memory, node sums | 17 | [047-063] |
| Flit directions on boots E and B | 2 | [064-065] |
| Checksums, command counts, failures on six boots; sysinfo and log lines; scope checks | 63 | critic_scope |
| Boot C L1 fits, boot C read variants, unaccounted L2 refills by boot, F1 over R3 multi-core | 53 | critic_extra |

### 1.2 Disagreements and the right value

| # | Where | Sheet says | Right value | Check |
|---|---|---|---|---|
| D1 | ocm_latency.md section 2 | the fifth cluster port at (1,2) has node id 144 | **80** (64 x 1 + 8 x 2) | critic_ocm [001] |
| D2 | platform.md section 2, summary item 1 | clock 2.003 cycles per ns | **2.000 cycles per ns** (pooled 2.00025 over 79 rows of at least 4,096 loads). 2.003 is 4.01 / 2.002, a rounding effect of a two-decimal column | critic_latency [029] |
| D3 | multicore.md short version and section 5 | "every DRAM command" puts 19.98 to 20.04 % on each node | **19.81 to 20.10 %** over the 10 DRAM-backed counted commands. 19.98 to 20.04 % holds for the 7 bandwidth commands only | critic_ocm [054-055] |
| D4 | open.md O6, platform.md | "boots A to D: at most 0.0157" | boots **B, C, D: at most 0.0156** per load. Boot A is out of scope | critic_extra [019-021] |
| D5 | open.md R17 against ocm_bw_mesh.md | own node is "4.50 to 6.05 times the next node" against "4.57 to 6.13 times the mean of the other four" | both are right. The page uses **own node over the mean of the other four: 4.57 to 6.13 (20 latency commands), 7.59 to 8.14 (5 read commands)** | [053] |
| D6 | multicore.md, open.md against ocm_bw_mesh.md | 3.27 against 2.98 requests "per timed line" on the 2 MiB read | 3.27 is the raw sum, 2.98 is net of the control. **Neither goes on the page** (see C12) | [058] |
| D7 | ocm_latency.md section 3 | all-five row against "the mean of the five per-region cells" on boot B: 23.881 and 26.075 ns | those means use the route files. The files without mesh counters give 23.923 and 26.287 ns. The page uses the **route files** and says so: +1.70 ns (CPU 2), +1.59 ns (CPU 8) | [031-032] |

No other value differs.

The JSON copies were scanned (top-level keys, spot values, and a search for known problem strings), not
read line by line. They are dumps of the same scripts as the `.md` sheets. Two warnings for the data
layer: `ocm_latency.json` and `open.json` hold boot A rows (folder 005), which are out of scope, and
`method.json` repeats the "2 MiB page" wording of SPEC. The data layer reads the CSV files, not these JSON
files.

---

## 2. Binding corrections

### 2.1 Wrong or unsupported statements

- **C1. OCM mapping of boots C and D.** SPEC.md and bandwidth.md section 4 say "2 MiB pages". All 115 map
  lines of each boot read `cont=64/64` (007 and 008 `dmesg.txt` lines 204 to 318). The page says:
  "4 KiB entries with the contiguous hint, one translation per 64 KiB". Never "2 MiB pages" for OCM.
- **C2. Ports of the clusters of CPUs 4 to 9.** ocm_latency.md calls them hypotheses. They are documented:
  operator's README of 004, line 36, gives (2,3), (3,2), (4,3), (5,2). The fit rank (1 of 120, rms
  0.095 against 1.085 ns) and the flit directions (20 of 20) are two measured checks, not the source.
- **C3. X steps and Y steps do not depend on the route.** Any shortest route has |dx| X steps and |dy| Y
  steps. So the fit needs only the coordinates. Do not write that the fit "assumes an X-first route".
- **C4. "Limit per cluster" is measured for writes only.** multicore.md states it for all three kernels.
  For read and copy, every row with two cores of one cluster at a DRAM footprint also has all eight
  cores running. The page says: measured for write (placement rows). For read and copy:
  "Insufficient data: two readers on CPUs 2 and 3 against CPUs 2 and 4 at 16 MiB".
- **C5. "No limit shared by the clusters" is too wide.** Right text: with one core per cluster, four cores
  scale 3.98 to 4.00 times, and 165.154 GB/s is the largest load applied, not a measured ceiling. With
  two writers per cluster the rate per cluster is 40.949 (one cluster busy), 42.916 and 42.092 (two
  busy), 38.241 GB/s (four busy, 16 MiB). That is unexplained and goes to the open table.
- **C6. Prefetcher comparisons must not mix two conditions.** Boot B differs from boots F1 and E in the
  prefetchers AND in the L3. Every figure that shows a prefetcher effect shows three boots: E (L3 on,
  prefetchers on), C (L3 holds no data, prefetchers on), B (L3 holds no data, prefetchers off). The
  prefetcher effect is C against B. The L3 effect is E against C. Affected: the address-order chain
  (latency.md figure 5, a two-boot dumbbell: replace) and the read variants (bandwidth.md figure 3).
  Numbers: address order 2.492 (E), 6.917 (C), 52.762 ns (B). So prefetchers on against off with the L3
  holding no data is 7.63 times, and the L3 step is 2.78 times. Plain 32 MiB read 24.546 (E), 9.196 (C),
  2.377 GB/s (B): 3.87 times and 2.67 times. "21.2 times" (B over E) may appear only with both
  differences named in the same sentence.
- **C7. 0xA2 does not count this stream's prefetch fills.** It reads 0.0001 per load on boot E's
  address-order chain and at most 0.0008 per line on boot C's plain read, where every line comes from
  outside the cluster. So "fewer than one L3 read refill per load" does NOT prove that a line was
  served inside the cluster. Consequences:
  - The page never states as fact that boot F1's one-line-per-page OCM rows are "partly served by the
    L3". Fact: each pass counts 1.00 to 3.28 L2 prefetch refills per load, 0.20 to 1.12 L3 read refills
    per load, and up to 0.48 L2 refills per load that neither count explains (at most 0.0156 on boots
    B, C, D). "Hypothesis: prefetch fills place chain members in the cluster before the chain reaches
    them. Test: the same rows on a boot with the L3 on and the prefetchers off, or with the hit set."
  - For 512 KiB to 1 MiB write "the rest is served inside the cluster", not "by the L3". The prefetch
    refill events read 0.0000 from 768 KiB up, so the caveat has no effect there. At 512 KiB the L2
    prefetch refills are 0.083 per load: say so.
- **C8. Causes that no counter proves.** Each of these is "Hypothesis:" with its test, or is left out:
  - 32 KiB: "the prefetcher's fills displace chain lines". Fact: 2.117 ns with 0.040 L1 refills per load
    (F1) against 2.031 ns with 0.009 (boot B). The four prefetchers-on boots (F1, E, C, R3) read 2.108 to 2.121 ns, both
    prefetchers-off boots 2.031 to 2.036 ns.
  - Address order: "the demand load finds its line already arriving" and "4 cycles + 1 cycle". Leave out.
  - Looped against single-call: "the register save explains the larger read difference". Hypothesis.
  - Software prefetch: "the hint takes a load slot". Hypothesis (the SOG gives PRFM a load pipeline).
  - Mesh: "as an address hash would do". Leave out. Fact: equal shares within 1.5 %.
  - Mesh: "a home node answers an OCM request from its own storage". Write: "consistent with". The two
    sums are exploratory events. Fact: they stay at the control level on 35 OCM commands (4,717 to
    13,105) and read 123,161 to 5,608,913 on the 10 DRAM-backed commands.
  - CPU order of the OCM row: write "consistent with distance". Boot F1 reads 1.45 to 1.63 ns above
    boot B's fit at each CPU's mean steps, so the offset is the same within 0.18 ns for the four CPUs.
  - 2 MiB row by cluster: CPU 8 is highest, as its 3.4 mean steps predict (+2.488 ns measured, +2.149
    from boot B's fit). CPU 6 reads 0.676 ns above CPU 2 at the same mean steps, and CPU 4 reads +1.114
    against +0.553. So distance stays a hypothesis for that row. The CPU 2 row comes from another
    command than the other three: say so.
- **C9. The L3-served load.** Lead with the direct row: boot E's 384 KiB row reads 10.906 to 11.147 ns
  with 0.915 to 0.924 L3 hits, 0.047 to 0.057 L2 hits and 0.020 to 0.032 refills from outside per load.
  Then the estimate: **10.6 to 11.0 ns est.** from the two rows where L3 hits are the majority of loads
  (256 KiB and 384 KiB: 10.62 to 10.96). State the sensitivity in one sentence: the 192 KiB row gives
  9.9 ns est. and the 512 KiB row 10.65 to 10.92 ns est. The least-squares fit is void (residual 4.2 %):
  never shown. The hit-set events are "exploratory, with three consistency checks" (two identities
  within 0.0003 per load; the L3 hit event reads 0.0000 in all 21 rows of each of boots B, C, D).
  Boot E's 512 KiB hit row is walked many times. Boot F1's 512 KiB row is walked once. Never compare them.
- **C10. "The L3 row" is a mixed row.** The 384 KiB row of boot F1 (10.986 ns) is "the 384 KiB chain".
  Its label on the headline figure: "L3 (384 KiB chain, 0.92 L3 hits per load counted on boot E)".
  The capacity marker reads "L2 + L3 sizes added = 384 KiB". Support in one sentence: 0.03 refills from
  outside per load at 384 KiB (best rep).
- **C11. "SLC" for the 1.5 to 3 MiB rows.** Write "served by the home nodes over the mesh (read as the
  SLC)". One sentence of caveat: no counter inside the timed interval separates an SLC hit from a
  memory-model fill. Two supports to state: the row is flat at 23.5 to 25.2 ns up to 3 MiB against
  52.658 ns for the DRAM-model row, and the OCM row (home-node storage) reads 25.4 to 27.7 ns from the
  same CPUs. "3.75 MiB est." always carries "est." and "(operator's README)".
- **C12. Mesh counts are whole-command counts.** No "requests per timed load" or "per timed line" on the
  page. Allowed: counts per command, own node over other nodes, shares per node, and "requests sent on
  to memory per line and pass of the whole command, net of the control, est." (1.02 for the 2 MiB read,
  1.02 to 1.07 for the six 16 MiB write commands). The pass count comes from the source, so it is "est.".
- **C13. The write rate.** "100.0 % of the documented store throughput at 32 MiB" needs two caveats in the
  same paragraph: it is the rate at which the store loop runs, and no write row waits for the lines to
  reach the memory model. The DRAM level is an emulator memory model (operator's README).
- **C14. Write intercepts are known to a few ns only.** Looped form: 25.12 ns (F1, 16 to 256 KiB), 25.70 ns
  (boot E, 4 to 24 KiB), 23.71 ns (boot C). Single-call form: 13.97 ns (E), 9.05 ns (C). The page quotes
  F1's fit and boot E's two fits, prints the intercepts with one decimal, and adds one sentence: "the
  same rows on boot C give 23.7 and 9.1 ns, so an intercept repeats to about 5 ns". Read fits are void
  on both boots (2.93 % and 2.14 % on E): no read intercept, no read slope, anywhere.
- **C15. Documented numbers are instruction throughput, not path width.** Verified in the SOG text: LDP
  Q-form throughput 1 (Table 2-13), STP Q-form throughput 1/2 (Table 2-14), at most two loads and one
  store per cycle, stores of more than 128 bits are multicycle (section 3.1), L1 hit 2 to 4 cycles and
  L2 hit 10 to 12 cycles (Table 3-2). The page writes "documented instruction throughput: 32 bytes per
  cycle for the read loop, 16 bytes per cycle for the write loop". Never "dual 128-bit". No TRM is in
  `refs/`. The copy ceiling of 21.33 bytes per cycle is not documented: leave it out.
- **C16. The shared vector unit is not the per-cluster limit.** The SOG says the two cores of a cluster
  share the vector unit (section 3.12). The pair scales 1.98 to 2.01 times at 16 KiB with the same
  instructions. One sentence in multicore 5.3.
- **C17. Stream over chain ("lines in flight est.")** restates a rate ratio. One wall-clock lanes figure
  only (latency 3.6). One paragraph in bandwidth 4.4 with the read rows of boot F1 only: 20.0 est. at
  32 MiB, 9.3 est. at 2 MiB. Stated assumption: a fetch of the stream lasts as long as one chain load.
  No write or copy value. No OCM value.
- **C18. Boot A never appears.** Remove it from every statement taken from open.md and ocm_latency.md.
- **C19. No history words from the sheets.** Not on the page: "codex round", "plan section 14", "run 7",
  "round three", "round four", "earlier boots", "old firmware", `bandwidth_r2`, `bandwidth_r3`.
  `run_l3.sh` is not an allowed input: write "a prepared command set (follow-up-run-plan.md)".
- **C20. Event status words.** "exploratory" for: the hit set (with its checks), 0x05 (L1 TLB refills),
  `hns_mc_reqs_local_all`, `hns_cache_miss_all`, the four flit events. "checked in two states" for
  0x81BC and 0x0111 (0.0000 on boots B and D, 0.9997 to 1.0000 per load on the address-order chain of
  E and C) and 0x81BD (0.11 to 0.26 per load at 192 to 384 KiB with prefetchers on, 0.0000 with them
  off). `hns_pocq_reqs_recvd_all` per node: "checked by the one-region commands (25 of 25)".
- **C21. Spread.** One definition for the whole page: (largest minus smallest) / best row, in percent.
  Best is the smallest for latency and the largest for bandwidth.
- **C22. Line numbers.** References cite the timed row that carries the best value (it has the counters
  and the per-thread columns), not the `best` row. The sheets mix both.
- **C23. Demand-only per-region rows** come from boot B's route files (20 cells, four CPUs), not from the
  files of CPUs 2 and 8 that open.md R11 lists.

### 2.2 Caveats that must stand next to the number (SPEC rule 5)

| Number | Caveat on the page, same paragraph or figure note |
|---|---|
| 52.658 ns, 52.212 ns, every bandwidth row of 2 MiB and more, every multi-core row | the DRAM level is an emulator memory model with zero configured delay, not silicon timing (operator's README) |
| any refill count near 1 per load | an aggregate count: it does not give each line's history, and refill counts include prefetch fills |
| any bandwidth number as cycles | "effective cycles per 64 bytes transferred", loop throughput |
| looped minus single-call, OCM against DRAM rate, any row minus a control | "the measured difference between two loops" |
| 64-load rows (one line per page, one region) | 39 ns of clock-read cost per pass is not subtracted: 0.61 ns per load est. Counters step by 1/64 |
| OCM read 0.79 and write 0.64 times the DRAM-backed rate | not like for like: the OCM rows flush first and the read rows run one pass. No DRAM-backed row with a flush exists on any boot |
| rows from CPUs 4 to 9 | the L3 register was read on CPU 2's cluster only (operator's README) |
| 20.752 ns intercept of boot B's fit | fitted value at zero steps. No cell has zero steps |
| "per step" of the fit | the cost of one more step of distance for the whole round trip, request and data |
| every boot B, C, D, R3 number | the boot's conditions in the same sentence or in the figure legend |

---

## 3. Data scope (ruled)

Check of boot F1's own files (critic_scope [026-052]): 57 core CSV files, the same names as boot R3.
Every latency header prints `events=prefetch`, `seq=0`, `sparse=0` or `1`. No file has a hit, TLB or walk
column. No per-region file has `sparse=0`. Every bandwidth header prints `asm_passes=0`. Kernels are
read, write, copy. No bandwidth block has counters. `cmn-counts.csv` has three home-node events only.
Boots E, B, C, D have no multi-thread block. No boot has a DRAM-backed bandwidth row with
`flush_before=1`, or a one-core DRAM row at 160 KiB, 1.25 MiB or 16 MiB. Boot F2 has no core CSV file.

| # | Row family | Boot | F1 lacks it because | Reader value | Ruling |
|---|---|---|---|---|---|
| S1 | hit set, `latency-dram-small-l3.csv`, 64 to 512 KiB | E | no `--events l3` command, no hit column | high: the only count of L3 hits | **IN** (latency 3.3) |
| S1b | the same file, L3 hits = 0.0000 | B, C, D | - | check of the event | **IN, one clause** in the event table |
| S2 | address-order chain `latency-dram-seq.csv` | E, C, B | no header with `seq=1` | high | **IN**, three boots (C6). Boot D: OUT (repeats B) |
| S3 | random chains with prefetchers off, `latency-dram-small/large/flushed.csv` | B | F1 has the rows, not the condition | medium: shows F1's chain loads are demand loads | **IN, one table**, footprints 4 to 128 KiB and 1.5 to 32 MiB plus the flushed row, all 18 rows shown. 192 KiB to 1 MiB left out with the reason (the L3 state differs). Boot D: OUT |
| S3b | boots B, D against C at 192 to 384 KiB (1.7 to 4.9 %) | B, C, D | - | low, a condition F1 never has | **OUT** |
| S4 | L1 forms, `bandwidth-l1-passes.csv`, `bandwidth-l1-asmpasses.csv` | E | one L1 footprint, looped form only | medium-high | **IN** (bandwidth 4.2). Boot C: one caveat sentence (C14) and one open row |
| S5 | read variants with per-line counters, `bandwidth-read-prefetch.csv` | E, C, B | no such kernel, no counters | high | **IN**, three boots (C6). Quote the plain rate from F1. Boot D: OUT (within 0.48 % of B) |
| S6 | `bandwidth-write-small*.csv` | E, B, C, D | F1 has the same footprints | none: compares two program builds | **OUT** |
| S7 | every line of one region under the mesh counters, `latency-ocm-regionR-route-cpuN.csv` | B | no every-line per-region row, prefetchers on | high: per-region OCM load and the step cost | **IN** (ocm 6.3), 20 cells, the fit |
| S7b | the same on boot D (fit void by one cell), on boot E (prefetch refills 0.16 to 0.65 per load, fit void) | D, E | - | - | D fit **OUT**. E: **one sentence** (why an L3-on, prefetchers-on boot cannot give the per-region number) |
| S7c | the same command without mesh counters, CPUs 2 and 8 | B | - | low | **OUT** |
| S8 | flit directions, `cmn-counts.csv` labels `route-ocmR-cpuN` | B | no crosspoint event | small: second check of the coordinates | **IN, one sentence** in ocm 6.3, boot B (the commands of the fit). Boot E's copy: OUT |
| S9 | page mapping: every line (route files, 20 cells), one line per page (10 cells), all five (2), TLB set | B, D | F1 maps 4 KiB entries only, no TLB set | medium | **IN, compact** (ocm 6.4). Boots C and A: OUT |
| S10 | one line per page at varied offsets | E, B, C, D | no `sparse=2` | none (reads as the fixed offset) | **OUT**. The term does not appear |
| S11 | TLB and walk rows of boot E, the 32 MiB chain on 4 KiB pages | E, C, D | no such set | none: 0x8188 never counts, 0x34 unexplained | **OUT** |
| S12 | boot F1's command set with the L3 holding no data | R3 | a boot cannot be its own control | high for one open item | **IN for open 8.1 only**: one-core read sweep, write and chain at 32 MiB, four and eight readers, OCM read, mesh requests of the 2 MiB read. State the setup differences (build, module, boards) |
| S12b | R3 one-line-per-page OCM rows (F1 over R3 = 0.834) | R3 | - | low: F1's own counters make the point (C7) | **OUT** |
| S13 | plain read with counters, L3 on against L3 holding no data, one build | E, C | no counters on F1 bandwidth rows | high for open 8.1 | **IN** (same rows as S5) |
| S14 | shared rows as a second sample (repeatability) | E | one boot gives no boot-to-boot variation | high | **IN, one figure and one table** in glance. Boot E never replaces a boot F1 number |
| S15 | boots 001, 002, 003, 005 (boot A) | - | - | none | **OUT** |

Use of each boot on the page: F1 everything. E: 3.3, 3.6, 4.2, 4.3, glance repeatability, open 8.1, one
sentence in 6.3. B: 3.6, 3.7, 4.3, 6.3, 6.4. C: 3.6, 4.3, open 8.1, one sentence in 4.2. D: 6.4 only.
R3: open 8.1 only. Boots B, C, D also appear in one clause of table TS4 (S1b).

---

## 4. Topics of open.md: resolved or open

| Topic | Ruling |
|---|---|
| R1, R2, R4, R5, R6, R8, R14, R15, R16, R18, R19 | resolved: state as fact in the section named in open.md |
| R3 | resolved: fact in 3.3 (supplementary, boot E) |
| R7 | resolved: fact in setup, repeated as the caveat of section 2.2 |
| R9 | resolved: the OCM row to quote (6.1) |
| R10 | resolved as a fact about counters only. "Partly served inside the cluster" is a hypothesis (C7) |
| R11 | resolved: fact in 6.3, from the route files (C23) |
| R12 | leave out, except boot B's one-line-per-page cells inside the page-mapping table |
| R13 | resolved: D over B only. No page size other than "64 KiB translations" |
| R17 | resolved: fact in mesh 7.1 with the ratio of D5 |
| X1 to X5 | leave out |
| O1 | **open**, own subsection 8.1. Add one measured fact that open.md did not draw out: the 48 KiB and 96 KiB reads fit the L2 on both boots and still differ 1.561 and 2.229 times (F1 over R3). So the gain does not need a line from outside the cluster |
| O2 | open, merged into 8.1 (E against C on the address-order chain, 2.78 times). The rows themselves are facts in 3.6 |
| O3 | open (read limit: per cluster or chip-wide) |
| O4, O5 | open, one row: what two cores of one cluster share. Sub-facts: 0.640, 0.671, 0.658; 2,3,8,9 is 1.9 % below 2,3,4,5; the rate per cluster with two writers is 40.9, 42.9, 42.1, 38.2 GB/s; pair read at 48 KiB scales 1.580 times |
| O6 | open (L3 state of the clusters of CPUs 4 to 9 not read). Evidence: 0.484, 0.469, 0.453 against at most 0.0156 on B, C, D |
| O7, O8 | open, one row: no line fits the L1 read rows, and the 4 KiB looped read is 40.910 GB/s on boot E against 46.180 on boot C |
| O9 | open, one row. The fact (which row to quote for the DRAM model) is in 3.4 |
| O10, O16 | open, one row: rows at a capacity edge repeat poorly (384 KiB first rep 12.004 ns; 768 KiB 20.023 against 22.072 ns and 4 MiB 29.379 against 28.321 ns on boots F1 and E). Boots F1 and E only |
| O11 | leave out (walk events are not used on the page) |
| O12 | open, one row |
| O13 | open, one row (no like-for-like DRAM row) |
| O14 | open, one row |
| O15 | open, one row, with the four-core row (node 288 is 15 to 21 % below the other three) |
| O17 | leave out (another program on another RTL revision) |
| from ocm_latency.md | two more open rows: an X step costs 1.994 ns and a Y step 0.952 ns; the all-five row reads 1.59 to 1.70 ns above the mean of boot B's five per-region rows |
| from ocm_bw_mesh.md | one more open row: the 2 MiB read sends about 1.0 request on to memory per line and pass est., although 2 MiB is under the 3.75 MiB est. SLC size |

Open table 8.2: 13 rows. "Not measured" 8.3: keep 10 rows of open.md section 5 (drop "CPUs 0, 1", "the
share of the DRAM-model latency inside the mesh" goes into the DRAM-model sentence of setup).

---

## 5. Page outline (final)

Budgets are words of prose, captions and notes. Table cells are extra: about 4,500 words in all. The page
total stays under 20,000 words of visible text. If the build is over, cut in this order: 7.2, 4.4, 3.7, 5.3.

Colours: boot F1 and boot E orange `#eb6834` (the legend names the boot). Boots B and D blue `#2a78d6`
(prefetchers off; where both appear, B is a filled dot and D a hollow one). Boot C and boot R3 aqua
`#1baf7a`. Kernels inside one boot F1 chart: read orange, write aqua, copy violet `#6250d6`. Red only in
figure L6. Reference lines and capacity markers grey.

**Short version** (150 words, at most three sentences) + **Fig H1**: horizontal bars from zero, boot F1,
CPU 2, ns per load: L1 2.002 (4 KiB), L2 6.014 (128 KiB), L3 10.986 (384 KiB chain), home nodes over the
mesh 23.714 (2 MiB), OCM 25.536 (every line, all five regions), DRAM model 52.658 (8 MiB, every line
flushed first). Value label on every bar, cycles in brackets. Note under it: the headline bandwidth
numbers (read 56.085 and 24.575 GB/s, write 31.997 GB/s, four cores 100.200 and 127.919 GB/s).

| Sec | Subsection | Words | Figure (form, series, annotation) | Table |
|---|---|---|---|---|
| 1 setup | 1.1 The chip under test | 300 | **S1** data-path diagram, left to right: core, L1 32 KiB, L2 128 KiB, L3 256 KiB (cluster), mesh port, home node (SLC slice 1 MiB, 4 of 16 ways = one OCM region), bridge, DRAM model. Grey size labels, no measured number | **TS1** platform facts (item, value, source) |
| | 1.2 The mesh | 200 | **S2** 6 x 6 mesh map: five home nodes (region, node id), four cluster ports (CPUs), fifth port grey. Step counts from CPU 2 and CPU 8 as small labels | - |
| | 1.3 The boots | 400 | **S3** boots matrix: 6 rows x 3 conditions (L3, prefetchers, OCM mapping), F1 row highlighted | **TS2** boots (folder, conditions, script, commands, failed, checksums, counter coverage). **TS3** rows taken from other boots (family, boot, section, why F1 has none) |
| | 1.4 The latency test | 350 | **S4** chain kinds and the timed interval: four small panels (walked many times, walked once, every line flushed first, address order) over one strip that marks what is inside the timed interval | - (bullets) |
| | 1.5 The bandwidth test | 250 | - | - (bullets: 256 bytes per iteration, passes, best rule, loop throughput, copy counts both directions) |
| | 1.6 Counters, clock, integrity | 300 | - | **TS4** events used (number, name, column, what it counts, status per C20) |
| 2 glance | Numbers to quote, repeatability | 500 | **G1** dot plot: boot E over boot F1, one dot per shared row (24 chain rows, 2 controls, 4 all-five OCM rows of CPUs 2 and 8, 2 plain reads, 2 looped 16 KiB rows = 34), x = ratio, grey band 0.98 to 1.02, labels on 768 KiB (1.102) and 4 MiB (0.964) | **TG1** numbers to quote (section 7 below). **TG2** repeatability: spread inside boot F1 by row group, and E over F1 by row group |
| 3 latency | 3.1 By footprint, CPU 2 | 450 | **L1** line chart, log2 x, 23 sizes, orange. Separate marker for the row with every line flushed first. Grey markers 32 KiB, 128 KiB, 384 KiB, 3.75 MiB est. Labels at 4 KiB, 128 KiB, 384 KiB, 2 MiB, 32 MiB. Rep range bar at 384, 512, 768 KiB | **TL1** 24 rows: footprint, kind, loads, best ns, cycles, spread, L1, L2, L3 read, L2 prefetch refills |
| | 3.2 Which level serves each footprint | 400 | **L2** three small multiples on the same x: L1 refills, L2 refills (thin second series: L2 prefetch refills), L3 read refills per load | **TL2** 7 bands: footprint, what the counters read, reading |
| | 3.3 What an L3-served load costs | 400 | **L3** stacked bars, boot E, 64 to 512 KiB: L2 hits, L3 hits, from outside, per load. ns per load on top. Annotation "384 KiB: 0.92 L3 hits, 10.9 ns" | **TL3** 7 rows + the estimate per row |
| | 3.4 The DRAM-model row | 200 | - (marker in L1) | - |
| | 3.5 The other clusters | 200 | **L4** dot plot, 4 rows (CPUs 2, 4, 6, 8), 2 MiB row, grey tick = boot B's fit at the CPU's mean steps plus CPU 2's offset | **TL4** background control and 2 MiB row per CPU |
| | 3.6 Address order and the prefetchers | 500 | **L5** dumbbell, 3 rows (boots E, C, B), two dots per row (address order, random with every line flushed first), log x, labels on all six dots, gaps annotated "21.1 x", "7.6 x", "1.00 x". **L6** wall-clock lanes (spec below) | **TL5** 3 boots: conditions, ns, cycles, L1 refills, L1 prefetch refills, L3 read refills |
| | 3.7 Random chains with the prefetchers off | 250 | - | **TL6** 18 rows: footprint, F1 ns, boot B ns, ratio. 32 KiB and 4 MiB called out |
| 4 bandwidth | 4.1 One core by footprint | 650 | **B1** line chart, log x, 6 sizes, read / write / copy, right scale bytes per cycle, grey lines at 64 and 32 GB/s (documented instruction throughput), capacity markers. Annotation "read: -51 % from 16 to 48 KiB, then -10 % to 32 MiB" | **TB1** 18 rows: GB/s, spread, bytes per cycle, effective cycles per 64 bytes, % of documented (read, write only) |
| | 4.2 Inside the L1: two forms (boot E) | 550 | **B2** dumbbell, two panels (read, write), rows 4, 8, 16, 24 KiB, hollow = looped, filled = single-call, grey line at the documented rate, gap labelled in ns per pass | **TB2** 16 rows. **TB3** fits: F1 write (looped), E write x 2 (valid), E read x 2 (VOID, no numbers shown except the residual) |
| | 4.3 The read stream and the prefetchers | 650 | **B3** dot plot at 32 MiB, rows = plain, prefetch 4 / 8 / 16 lines ahead, two streams. Three dots per row: E orange, C aqua, B blue. Annotations: "prefetchers: 3.87 x (C over B)", "hint: -17 to -26 % on E, x 2.1 to 2.7 on B" | **TB4** 10 rows (kernel x 2 footprints): GB/s and ratio to plain for E, C, B. **TB5** per-line counters at 32 MiB (L1 refills, L1 prefetch refills, L3 read refills) |
| | 4.4 Stream against chain | 250 | - | - |
| 5 multicore | 5.1 One core per cluster, all eight | 450 | **M1** dot plot, three small multiples (read, write, copy), rows 1 / 4 / 8 cores at 2 MiB, grey tick = threads x one-core rate, labels: GB/s and efficiency | **TM1** 12 rows |
| | 5.2 Writer placement | 400 | **M2** six bars (16 MiB write), each with a strip of four cluster boxes showing the writing cores. Annotations "one cluster: 0.64 x", "0.67 x", "0.66 x" | **TM2** 6 rows with per-thread range and requests sent on to memory |
| | 5.3 Two cores of one cluster, small footprints | 350 | - | **TM3** 9 rows. 160 KiB rows: "no one-core row at this footprint" |
| 6 ocm | 6.1 The OCM row to quote | 450 | **O1** dot plot, rows CPUs 2, 4, 6, 8: filled = every line, hollow = one line per page (all five regions), grey tick = boot B's fit at mean steps. Annotation "every line: 1.00 refill per level per load, 0 prefetch refills" | **TO1** 8 rows |
| | 6.2 One line per page: not an OCM latency | 400 | **O2** strip plot: 20 cells x 7 passes by CPU, median marked, grey line = that CPU's every-line row | **TO2** 20 cells: best, median, spread, L3 read refills, L2 prefetch refills, unaccounted L2 refills |
| | 6.3 Per region and per mesh step (boot B) | 600 | **O3** scatter, blue: x = X steps (0 to 4), y = ns, one fitted line per Y steps (0, 1, 2). Annotations "+1.99 ns per X step", "+0.95 ns per Y step", "rms 0.095 ns". Axis break marked if y does not start at zero | **TO3** 4 x 5 grid: steps, ns, residual. **TO4** fit, 2 % rule, the two checks of the coordinates |
| | 6.4 Page mapping (boots B and D) | 350 | **O4** dumbbell: 3 rows (every line one region, one line per page, every line all five), B filled blue, D hollow blue, gap = ratio. Small side bars: L1 TLB refills per pass 287 to 13 and 42 to 13 | **TO5** 4 rows |
| | 6.5 OCM bandwidth | 500 | **O5** dot plot, 7 rows (regions 0 to 4 read, all five read, all five write): best filled, other reps hollow. Grey lines at the DRAM-backed 2 MiB read and write, labelled "not flushed, 4 passes". "0.79 x", "0.64 x" | **TO6** 8 rows (with the four-core row) |
| 7 mesh | 7.1 Each command reached its own node | 400 | **N1** grid: 5 columns (nodes 88 to 344), rows = 5 one-region read commands + the 5 CPU 2 latency commands + control. Own node orange, others grey | **TN1** by command group: own node, other nodes, ratio, control |
| | 7.2 DRAM-backed commands | 300 | **N2** dot plot, log x: requests sent on to memory per command, rows = command groups (control, OCM chains, OCM read and write, 2 MiB chains, 2 MiB read, 16 MiB writes) | **TN2** 10 DRAM-backed commands: share per node |
| 8 open | 8.1 The read stream and the L3 state | 650 | **P1** dumbbell, F1 orange against R3 aqua: one-core read at 48 KiB, 96 KiB, 256 KiB, 2 MiB, 32 MiB; write 32 MiB; chain 32 MiB; four readers and eight readers per reader; OCM read. Ratio on each gap. Takeaway "only the read streams differ" | **TP1** those rows. **TP2** boots E and C: plain 32 MiB read, GB/s, cycles per line, L1 refills, L1 prefetch refills, L2 refills per line; address-order chain |
| | 8.2 Other open items | 900 | - | **TP3** 13 rows: observation with rows, why not explained, hypothesis, the measurement that would settle it |
| | 8.3 Not measured | 350 | **P2** grid: row families x four firmware states (L3 on or holding no data x prefetchers on or off); cell = boot name or "not measured" | **TP4** 10 rows |
| 9, 10 | Words used here, References | 700 + 1,500 | - | - |

Totals: prose 13,050 + 2,200 = 15,250 words. 26 figures. 32 tables.

**Figure L6, wall-clock lanes.** Time axis 0 to 110 ns, to scale. Lane 1 "boot B, prefetchers off: the
core's loads": two solid blocks of 52.76 ns, the first one red, label "one load = one fetch, 52.76 ns".
Lane 2 "boot E, prefetchers on: the core's loads": solid blocks of 2.49 ns back to back (drawn tiny).
Lane 3 "boot E: line fetches, est.": bars with dashed outline, 52.66 ns long, one starting every 2.49 ns,
about 21 overlapping. Caption, binding: "Durations to scale. The overlap is schematic. The length of a
fetch is assumed equal to the chain load with every line flushed first. Fetches in flight are an
estimate (52.66 / 2.49 = 21 est.). No counter counts them. With the L3 holding no data (boot C) the same
chain reads 6.92 ns per load."

---

## 6. Derived tables the data layer must provide

Every row carries `boot`, `file`, `line` (the timed row), `best_line`. All numbers are floats parsed
from the CSV. Rep time is `total_bytes / (aggregate_GBps x 1e9)`, never `elapsed_s`.

| Name | Rows | Keys |
|---|---|---|
| `boots` | 6 | name, folder, path, l3, prefetchers, ocm_mapping, script, commit, n_cmd, n_core, n_cme, n_failed, sha_ok, sha_total, cov_rows, cov_min, cov_max, pwrstat_lines, map_lines, map_cont |
| `clock` | 1 per boot | pooled, n_rows, min, max (rows of at least 4,096 loads) |
| `bracket` | 1 | n_cmd, min, median, max, max_file |
| `lat_sweep` | 24 (F1) | size, kind, loads, best_ns, reps, spread_pct, cycles, l1, l2, a2, l1pf, l2pf, l2byl1pf, unacc_l2 (per rep), a2_reps |
| `lat_bands` | 7 | from `lat_sweep`: size range, counter ranges |
| `lat_hit` | 7 (E) | size, best_ns, reps, l1, l2hit, l3hit, a2 (min, max over reps), identity residuals |
| `l3_est` | 4 | size, est per rep, inputs tL1, tL2, tOUT, l3 share |
| `lat_cluster` | 5 + 4 | cpu, control ns, cycles, l1; 2 MiB best, reps, a2, mean_steps_x, mean_steps_y, fit_pred |
| `lat_seq` | 3 (E, C, B) | conditions, best_ns, reps, cycles, l1, l2, a2, l1pf, l2byl1pf, random_ns, ratio |
| `lat_pfoff` | 18 | size, f1_ns, b_ns, ratio; plus l1 and l1pf of the 32 KiB row on both boots |
| `repeat` | 34 | row id, group, f1, e, ratio (24 chain rows, 2 controls, 4 OCM, 2 plain reads, 2 looped 16 KiB rows) |
| `spread_groups` | about 10 | group, n rows, min, max spread on F1 |
| `bw_1core` | 18 (F1) | kernel, size, passes, best, reps, spread_pct, bytes_per_cycle, eff_cycles_64, ns_pass, pct_doc |
| `bw_fit` | 5 + 2 | boot, form, kernel, intercept_ns, rate, residuals, max_res, limit, valid; boot C write fits for the caveat |
| `bw_l1` | 16 (E) | form, kernel, size, best, spread_pct, ns_pass, l1_refills_pass, diff_ns (looped minus single-call) |
| `bw_var` | 30 (E, C, B) | boot, kernel, size, best, spread_pct, ratio_plain, cyc_line, l1, l2, a2, l1pf, l2pf, l2byl1pf |
| `stream_chain` | 2 (F1) | size, chain_ns, ns_per_line, ratio_est |
| `mc_rows` | 21 | file, kernel, size, threads, cpus, agg, thr_min, thr_max, spread_pct, one_core (or None), scaling, efficiency, per_cluster |
| `mc_second_core` | 6 | kernel, size, gain_pct |
| `mc_writers` | 6 | cpus, clusters, agg, thr_min, thr_max, spread_pct, ratio_control, per_cluster, node counts, mc |
| `ocm_all5` | 8 (F1) | cpu, shape, loads, passes, best, spread_pct, l1, l2, a2, l2pf, mean_steps |
| `ocm_cells` | 20 (F1) | cpu, region, steps_x, steps_y, best, median, max, spread_pct, a2 range, l2pf range, unacc_l2 max |
| `ocm_route` | 20 (B) + 20 (D) | cpu, region, steps_x, steps_y, best, other pass, l1, l2, a2, pf_max, residual |
| `ocm_fit` | B, D, F1 cells, E | a, bx, cy, rms, max_res, pct_of_smallest, valid; one-slope fit of B; rank of the documented ports among 120; flit direction matches |
| `ocm_pagemap` | 4 | row group, n cells, min, max, geometric mean, n faster on D, mean diff; L1 TLB refills per pass (min, max, mean) on B and D |
| `ocm_bw` | 8 (F1) | file, kernel, threads, size, passes, reps, best, spread_pct, ns_per_64, ratio to the DRAM-backed 2 MiB row |
| `mesh_cmd` | 51 labels (F1) | label, group, node counts (5), own node, mean of others, ratio, mc, miss, child_ns, multiplexed |
| `mesh_ctrl` | 5 | label, node counts, mc, miss, child_ns, helper_ns |
| `mesh_share` | 10 | label, share per node, spread |
| `open_l3` | about 14 | row, f1, r3, ratio; mesh sum F1 and R3 |
| `open_ec` | 3 | plain read 2 MiB and 32 MiB, address-order chain: E, C values and counters |
| `not_measured` | grid | family, state, boot or None |
| `steps` | 4 x 5 | cpu, region, dx, dy |

`selftest()` must assert at least: every `best` row equals the min (latency) or max (bandwidth) of its
timed rows; perf_cov 1.0000 on all counted rows; checksums; boot B's fit reproduces 20.752, 1.994, 0.952
and passes the 2 % rule; boot D's fit fails it; both read fits of boot E fail it.

---

## 7. Numbers to quote (exact, with the timed row)

Paths: F1 = `results/membench-jibin-011/results/bootF1/`, E = `.../010/results/bootE/`, B = `006`,
C = `007`, D = `008`, R3 = `004/results/19700101T000000Z/`.

| # | Quantity | Value | Row |
|---|---|---|---|
| 1 | L1 chain load | 2.002 ns, 4.01 cycles | F1 `latency-dram-small.csv:5` |
| 2 | 128 KiB chain (L2) | 6.014 ns, 12.03 cycles, 0.986 L1 refills per load | F1 `:45` |
| 3 | 384 KiB chain (L3) | 10.986 ns, 21.98 cycles, reps 12.004, 11.054, 10.986 (spread 9.27 %) | F1 `:60-62` |
| 4 | L3 hits per load, 192 / 256 / 384 KiB | 0.465 to 0.471 / 0.751 to 0.771 / 0.915 to 0.924 | E `latency-dram-small-l3.csv:20-32` |
| 5 | L3-served load | 10.6 to 11.0 ns est. (192 KiB row: 9.9 ns est.) | derived, E, inputs 2.002, 6.003 est., 24.177 ns |
| 6 | 2 MiB chain, CPU 2 | 23.714 ns, 0.982 L3 read refills per load | F1 `latency-dram-large.csv:22` |
| 7 | 2 MiB chain, CPUs 4 / 6 / 8 | 24.828 / 24.390 / 26.202 ns | F1 `latency-dram-slc-cpu<c>.csv:5` |
| 8 | DRAM-model row | 52.658 ns, 105.32 cycles, both passes equal | F1 `latency-dram-flushed.csv:5-6` |
| 9 | 32 MiB and 8 MiB walked once | 52.212 ns and 44.485 ns | F1 `latency-dram-large.csv:45`, `:37` |
| 10 | Background control, CPUs 2 / 4 / 6 / 8 | 2.015 / 2.016 / 2.017 / 2.020 ns | F1 `latency-control-cpu<c>.csv:5` |
| 11 | Clock | 2.000 cycles per ns (pooled 2.00025, 79 rows, range 2.0000 to 2.0199) | F1 latency files |
| 12 | Rep spread, chains | under 0.7 % on 21 of 24 rows. 9.27 %, 2.79 %, 4.44 % at 384, 512, 768 KiB | F1 |
| 13 | Boot E over boot F1 | 0.9995 to 1.0019 (12 rows to 384 KiB), 1.0000 (flushed), 0.964 to 1.102 (11 walked-once rows) | E, F1 |
| 14 | Address-order 8 MiB chain | 2.492 ns (E), 6.917 ns (C), 52.762 ns (B). L1 prefetch refills 0.9997, 0.9999, 0.0000 per load | `latency-dram-seq.csv:5-6` |
| 15 | Random chain, boot B over boot F1 | 0.9965 to 1.0067 (4 to 128 KiB without 32 KiB), 0.9594 (32 KiB), 1.0007 to 1.0192 (1.5 to 32 MiB without 4 MiB), 0.9585 (4 MiB), 1.0015 (flushed) | B, F1 |
| 16 | One-core read | 56.085 GB/s at 16 KiB (28.04 bytes per cycle, 87.6 % of documented). 27.299 / 26.877 / 26.297 / 25.044 / 24.575 GB/s at 48 KiB / 96 KiB / 256 KiB / 2 MiB / 32 MiB (4.69 to 5.21 effective cycles per 64 bytes) | F1 `bandwidth-dram-1core.csv:6, 19, 35, 51, 66, 79` |
| 17 | One-core write | 30.608 GB/s at 16 KiB, 31.437 to 31.997 GB/s from 48 KiB to 32 MiB (4.000 effective cycles per 64 bytes at 32 MiB) | F1 `:9, 25, 40, 55, 70, 84` |
| 18 | One-core copy, both directions counted | 39.433 GB/s at 16 KiB, 31.438 GB/s at 32 MiB | F1 `:12, 87` |
| 19 | Documented | 32 bytes per cycle (64 GB/s) read loop, 16 bytes per cycle (32 GB/s) write loop, L1 hit 2 to 4 cycles, L2 hit 10 to 12 cycles | SOG Tables 2-13, 2-14, 3-2 |
| 20 | Write fit, boot F1, looped form | 25.1 ns per pass + bytes at 31.982 GB/s, largest residual 2.12 ns (limit 10.71 ns): valid | F1, 16 to 256 KiB |
| 21 | Write fits, boot E | looped 25.7 ns + bytes at 32.016 GB/s (0.28 %). Single-call 14.0 ns + bytes at 32.108 GB/s (0.73 %). Read fits void: 2.93 % and 2.14 % | E `bandwidth-l1-*.csv` |
| 22 | Looped minus single-call per pass | read 20.9 to 23.6 ns, write 12.0 to 14.7 ns | E |
| 23 | Best L1 rates, single-call form | read 60.586 GB/s (94.7 %), write 31.558 GB/s (98.6 %) at 24 KiB | E `bandwidth-l1-asmpasses.csv` |
| 24 | Plain 32 MiB read | 24.546 GB/s (E), 9.196 (C), 2.377 (B). L1 prefetch refills per line 0.9994, 0.9994, 0.0000 | `bandwidth-read-prefetch.csv:39-41` (best row 42) |
| 25 | Software prefetch 4 / 8 / 16 lines ahead, two streams, 32 MiB | E: -17.1 / -24.7 / -25.5 / -23.0 %. B: x 2.665 / 2.400 / 2.069 / 0.997 | E, B |
| 26 | Stream over chain, read | 20.0 est. at 32 MiB, 9.3 est. at 2 MiB | F1 |
| 27 | One core per cluster, 2 MiB | read 100.200, write 127.919, copy 125.331 GB/s (4.001, 4.000, 3.984 times) | F1 `bandwidth-perdsu.csv` |
| 28 | All eight cores, 2 MiB | read 108.733 (4.342 times), write 165.154 (5.164), copy 142.036 (4.515) GB/s | F1 `bandwidth-all8.csv` |
| 29 | Second core of each cluster adds | read +8.5 / +9.7 %, copy +13.3 / +12.5 %, write +29.1 / +19.5 % (2 / 16 MiB) | F1 |
| 30 | Writers, 16 MiB each | 63.985 (CPUs 2,4), 63.987 (2,8), 40.949 (2,3: 0.640), 127.965 (2,4,6,8), 85.833 (2,3,4,5: 0.671), 84.184 GB/s (2,3,8,9: 0.658) | F1 `bandwidth-write-cpus*.csv` |
| 31 | Pair at 16 KiB / 48 KiB | read 112.409 (2.004 times) / 43.135 (1.580). Write 60.755 (1.985) / 61.943 (1.970). Copy 79.106 (2.006) / 45.920 (1.338) | F1 `bandwidth-pair.csv` |
| 32 | OCM row | 25.536 / 25.932 / 25.445 / 27.702 ns on CPUs 2 / 4 / 6 / 8. Refills per load 1.0004 to 1.0007 (L1), 1.0003 to 1.0006 (L2), 1.0005 to 1.0012 (L3 read), prefetch 0.0000 | F1 `latency-ocm-all5-dense-cpu<c>.csv:5-6` |
| 33 | One line per page, boot F1 | 17.266 to 22.609 ns (20 cells, spread 19.9 to 59.7 %), 23.700 to 26.334 ns (all five) | F1 |
| 34 | Per-region rows, boot B | 21.697 to 29.804 ns over 20 cells | B `latency-ocm-region<r>-route-cpu<c>.csv` |
| 35 | Fit, boot B | 20.752 + 1.994 per X step + 0.952 per Y step, rms 0.095 ns, largest residual 0.173 ns (0.80 %). One slope: rms 0.643 ns | B |
| 36 | Page mapping, D over B | 0.996 (every line, 20 cells), 0.973 (one line per page, 10 of 10 lower), 0.976 and 0.980 (all five). L1 TLB refills per pass 163 to 599 against 12 to 15 | B, D |
| 37 | OCM bandwidth | read 19.883 to 20.143 GB/s per region (1.29 % apart), 19.822 all five, write 20.326, four cores 80.314 GB/s (1.002 times the sum) | F1 `bandwidth-ocm-*.csv` |
| 38 | OCM over DRAM-backed 2 MiB rate | read 0.791, write 0.636 (not like for like) | F1 |
| 39 | Mesh: control | 7,348 to 10,118 requests per node per command | F1 `cmn-counts.csv` |
| 40 | Mesh: own node | highest in 25 of 25. 4.57 to 6.13 and 7.59 to 8.14 times the mean of the other four | F1 |
| 41 | Mesh: DRAM-backed | 19.81 to 20.10 % per node (10 commands) | F1 |
| 42 | Mesh: sent on to memory | 4,717 to 13,105 (35 OCM commands), 6,732 to 11,014 (controls), 123,161 to 5,608,913 (DRAM-backed) | F1 |
| 43 | Integrity, boot F1 | 137 commands (67 core, 70 CME), 0 failed, 88 of 88 checksums, perf_cov 1.0000 on 247 core rows, 0 multiplexed mesh rows | F1 |
| 44 | Open 8.1 | one-core read F1 over R3: 1.561 / 2.229 / 2.587 / 2.690 / 2.679 at 48 KiB to 32 MiB. Write 1.000. Four readers 2.888 to 2.895. Eight readers 1.605 to 1.614. OCM read 1.206 to 1.358. Mesh requests of the 2 MiB read 0.975 | F1, R3 |

Typed facts with a [Ref] (operator's README or document): SLC 5 x 1 MiB with 4 of 16 ways as OCM,
3.75 MiB est.; port coordinates (004 README line 36); register meaning of 0x70 and 0x0; firmware
versions; chip time 3.803 s; the DRAM model (011 README lines 247, 354); the SOG rows of number 19.

---

## 8. Terms for "Words used here" (one sentence each)

- **boot**: one power-on of the emulated chip with one firmware set, which ran one script once.
- **boot F1**: the main boot; L3 on, prefetchers on, OCM mapped in 4 KiB entries.
- **boot E**: the same firmware state as boot F1, with another command set.
- **boot B**: prefetchers off, and the L3 of CPUs 2 to 9 holds no data.
- **boot C**: prefetchers on, the L3 holds no data, OCM mapped with 64 KiB translations.
- **boot D**: as boot B, with the OCM mapped with 64 KiB translations.
- **boot R3**: boot F1's command set on an older benchmark build, with the L3 holding no data.
- **C1-Nano**: the Arm core under test; the chip has ten, and the tests use CPUs 2 to 9.
- **cluster**: two cores that share one L2, one L3 and one mesh port.
- **L3 on / the L3 holds no data**: the cluster's L3 stores lines, or it only tracks which core has a line (snoop-filter-only mode), as the firmware sets it.
- **prefetcher**: the core's hardware data prefetchers; "prefetchers off" means the firmware set the disable bit.
- **mesh**: the 6 x 6 grid of crosspoints that joins the clusters, the home nodes and the memory.
- **step**: one move between neighbour crosspoints on the mesh, along X or along Y.
- **home node**: a mesh device that holds one slice of the SLC and one OCM region.
- **SLC**: the system-level cache, shared by all clusters and held by the five home nodes.
- **OCM**: on-chip memory, five regions of 256 KiB that live in the home nodes.
- **DRAM model**: the emulator's memory behind the home nodes; it has zero configured delay and is not silicon timing.
- **footprint**: the bytes of buffer that a row uses per thread.
- **latency test**: the program that walks a chain of pointers, one pointer per 64-byte line, each load's address being the previous load's data.
- **chain load**: elapsed time of a walk divided by its loads, in ns per load.
- **walked many times / walked once / every line flushed first / address order**: the four chain kinds (how often the chain is walked, whether its lines are removed from the caches first, and whether the order is random or ascending).
- **every line / one line per 4 KiB page**: the two OCM chain shapes (which lines of a region are chain members).
- **pass**: one walk over the chain or the buffer. **rep**: one timed measurement.
- **best row**: the smallest rep for latency, the largest for bandwidth.
- **spread**: (largest minus smallest) / best row, in percent.
- **bandwidth test**: the program that times whole passes of a fixed loop of 32-byte loads or stores over a buffer.
- **GB/s**: 1e9 bytes transferred per second of elapsed time; loop throughput.
- **effective cycles per 64 bytes transferred**: 128 divided by the rate in GB/s at 2.0 cycles per ns.
- **looped form / single-call form**: one kernel call per pass, or all passes of a rep in one call.
- **plain read / software prefetch N lines ahead / two streams**: the read loop alone, with one prefetch hint per line, or over the two halves of the buffer at once.
- **refill**: a line brought into a cache level; the counts include prefetch fills.
- **L3 read refill (0xA2)**: an L3 fill from outside the cluster caused by a read.
- **L2 refills not accounted for**: L2 refills minus the two prefetch refill counts minus the L3 read refills; a difference of counters.
- **hit set**: three events that count L2 hits, L3 accesses and L3 hits of demand reads (exploratory).
- **perf_cov**: the share of the timed interval during which the counters ran.
- **background control**: the 4 KiB chain on 4 KiB pages that runs per CPU under the mesh counters.
- **own node**: the home node of the region that a one-region command uses.
- **requests sent on to memory**: the home nodes' count of requests passed to the memory controller (exploratory).
- **operator's README**: the `README.md` that the emulator operator wrote into each results folder.
- **SOG**: Arm C1-Nano Core Software Optimization Guide, 109590_0001_04.
- **est.**: an estimate; its method stands next to it.
- **TLB**: the cache of address translations; "64 KiB translations" means one entry covers 64 KiB.

---

## 9. Wording decisions

- **L1 rows.** "L1 row" = the 4 KiB row of the footprint sweep (2.002 ns, the number to quote).
  "background control" = `latency-control-cpu<c>.csv` (2.015 to 2.020 ns). Never "baseline". A
  difference from either is "the measured difference between two loops".
- **Row groups, latency.** "footprint sweep" (4 KiB to 32 MiB on CPU 2). "the 384 KiB chain", "the 2 MiB
  chain". "DRAM-model row" = 8 MiB with every line flushed first. On chart labels write the kind in
  full: "8 MiB, every line flushed first".
- **Row groups, OCM.** "OCM row" = every line, all five regions. "one-line-per-page rows" (one region,
  all five regions). "per-region rows" = every line of one region (boot B).
- **Row groups, bandwidth.** "one-core sweep", "L1 forms", "read variants", "pair" (two cores of one
  cluster), "one core per cluster", "all eight cores", "writer placement rows", "OCM bandwidth rows".
- **Levels.** L1, L2, L3, "home nodes over the mesh (SLC)", OCM, "DRAM model". Never "DRAM latency"
  without "model".
- **L3 state.** "L3 on" and "the L3 holds no data". Table cells: "on", "no data". Never "L3 off".
- **Boots at first use in a section.** "boot E (the firmware state of boot F1, another command set)",
  "boot B (prefetchers off, the L3 holds no data)", "boot C (prefetchers on, the L3 holds no data)",
  "boot D (as boot B, OCM mapped with 64 KiB translations)", "boot R3 (boot F1's commands, the L3 holds
  no data, an older build)". After that the bare name.
- **Counters.** "L1 refills", "L2 refills", "L3 read refills", "L1 prefetch refills" (0x81BC), "L2
  prefetch refills" (0x81BD), "L2 refills by the L1 prefetcher" (0x0111), "L2 hits", "L3 hits". Event
  numbers appear in table TS4 and in References only.
- **Mesh.** "requests received", "requests sent on to memory", "own node", "other nodes". A mesh move is
  "a step".
- **Forbidden in prose** (besides SPEC rules 2 and 6): "L3 off", "dual 128-bit", "2 MiB pages" for OCM,
  "lines in flight" without "est.", "takes N cycles" for a bandwidth row, "served by the L3" for the
  one-line-per-page rows, "validated" for any event, boot A, and any verb form that tells a history
  ("was fixed", "turned out", "used to").
