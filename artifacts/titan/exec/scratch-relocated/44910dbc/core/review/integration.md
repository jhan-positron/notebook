# Integration of asimov-c1nano-perf (build in scratch only)

## Short version

- The whole page builds to `build/page.html` with 0 lint errors, 0 lint warnings and no unmapped reference or term note. Two builds give the same bytes, and the data selftest passes (418 checks).
- The page had 25,880 visible words (generator count). It now has 19,999. To get there, the four subsections of the critic's cut order (7.2, 4.4, 3.7, 5.3) were removed, and the References were made compact.
- `asimov-c1nano-perf.html` in the project folder was never written (still dated 2026-11-08 22:11, 333,062 bytes).

## Counts (final build)

| Item | Value |
|---|---|
| Visible words, generator count | 19,999 (limit: about 20,000) |
| Visible words, every table cell and SVG label counted on its own | 24,209 |
| of these: prose, captions, notes, Words used here | 12,329 |
| of these: table cells | 6,352 |
| of these: SVG text | 2,735 |
| of these: References | 2,613 |
| of these: Contents | 180 |
| Figures | 25 (limit 32) |
| Tables | 29 (limit 40) |
| References | 116, every [RefN] resolves, every entry is cited |
| Terms in "Words used here" | 68 |
| Bytes | 525,017 |
| Pixel height at 1100 px wide | 47,305 px (19 slices of 2,600 px) |
| Words per section (generator count) | setup 2,655, glance 1,038, latency 2,633, bandwidth 2,178, multicore 1,226, ocm 3,095, mesh 530, open 2,561 |

The generator joins text nodes without a separator, so adjacent table cells count as one word. The second row of the table counts each cell.

## Checks done

- (a) `python3 -m c1nano_page.data`: selftest OK. Two builds: identical bytes.
- (b) Order: Short version, Contents, sections 1 to 8, Words used here (9), References (10).
- (f) Every `S.term` name is in `words.py`. Every [RefN] has an entry.
- (h) `<meta charset="utf-8">` right after `<title>`, light theme only, no external resource, no non-ASCII character anywhere, tags balanced.
- (g) All 19 slices of `shots/integ/` were looked at once. After that only small text edits, the reference-label CSS fix and the removal of one table row were made. Slices 17 and 18 were looked at again.

## Changes

### Word count (25,880 to 19,999)

1. `refs.py`: a result file lists its cited line numbers only, in the short form "5-7, 10". The text per cited line stays for READMEs, sources and documents, unless the entry text already describes those lines. Dropped: line counts of files, the `log.txt` command lines of each CSV, the first and last file name of a group, section pointers of the READMEs that carried no fact. References went from 5,593 to about 2,290 words (generator count).
2. Cut per the critic's cut order: subsections 7.2 (with figure N2 and table TN2), 4.4, 3.7 (with table TL6), 5.3 (with table TM3). `ids.py` and `IDS.md` are updated. The modules before this cut are saved in `review/precut/`.
   - Kept from 7.2, as two bullets in 7.1: the equal shares per node (19.81 to 20.10 %) and the ranges of requests sent on to memory.
   - Kept from 5.3, as one paragraph in 5.2: the shared vector unit is not the limit (the pair scales 1.98 to 2.01 times at 16 KiB).
3. Repetition removed, with a cross-reference to the home section: test descriptions in 3.1, 4.1, 5.1, 7.1 (home: section 1), spread numbers in 3.1 (home: 2.2), the fit numbers and coordinate checks in 6.3 prose (home: table TO4), the mapping-line counts in 6.4 (home: 1.3), the hit-set checks in 3.3 (home: table TS4), per-variant hint numbers in 4.3 (home: figure B3 and table TB4), open-item rows 2, 5, 6, 8, 9, 11, 12, 13 (home: their sections), the integrity bullets of 1.6 (home: table TS2), the "Key points" block of section 5.
4. Tables shortened: TS1 (5 rows fewer), TS2 (2 rows fewer), TS3 (2 rows fewer), TG2 (boot E over boot F1 part removed, figure G1 carries it; the pair row removed), TP4 (4 rows fewer, two of them are rows of TP3).
5. Insufficient-data blocks that repeated an open-item row were folded into a sentence (1.1, 6.3) or shortened (4.1, 5.1, 6.5).

### Names and consistency

- "DRAM level" and "emulator memory model" are now "DRAM model ... an emulator memory" everywhere in prose.
- Open item 9 used the 2 MiB and 32 MiB rows (17.1 to 26.1 %, 1.88 to 2.66 times). Section 4.3 uses the 32 MiB rows. Item 9 now uses the 32 MiB rows too (17.1 to 25.5 %, 2.07 to 2.66 times).
- New entries in `words.py`: aggregate rate, scaling, efficiency, kernel, L1 prefetch refills, DRAM-model row, OCM row, crosspoint, flit. The SOG entry is now a full sentence.
- `refs.py`: canonical entry `folder:F2` for the key `folder-012-core-files`. The SOG entry names Table 2-6 (the prefetch hint is listed with the load instructions).
- Figure P1 note: the reference marks no longer stand alone after a full stop.

### Layout

- `shell.py`: the label of a three-digit reference ([Ref100] and up) broke over two lines. The label column is now 66 px wide and does not wrap.

## Open problems

1. The word count is 19,999 only by the generator's count. With each table cell counted it is 24,209. Prose, captions and notes are within the critic's budget. Table cells (6,352 against 4,500 est.) and References (2,613 against 1,500) are over the critic's estimates.
2. Three sections are over their SPEC budget: setup 2,655 (2,500), glance 1,038 (1,000), open 2,561 (2,500).
3. Content lost with the cut order: the boot B against boot F1 table of random chains with the 32 KiB and 4 MiB rows (critic number 15), the stream over chain estimate (number 26), the pair rows at 48 and 160 KiB (number 31, the 48 KiB read scaling remains in open item 2), the per-command share table of the DRAM-backed commands.
4. Figure P2 still counts 15 row families. Some families of boots B and D (the footprint sweep with the prefetchers off) are no longer shown on the page.
5. Cited-line descriptions for result files are gone from the References. The sentence that carries the mark says what the rows are.
6. Small layout points left as they are: the footprint column of table TL2 and the boot column of table TS3 wrap to two lines, the annotation of figure B1 sits close to the L1 marker, figure L3 uses orange, aqua and grey for parts of boot E, not for boots.
7. Slices 0 to 16 were not looked at again after the last small text edits.

## Verification round

### Short version

- All fixer changes are integrated, and `build/page.html` builds with 0 lint errors, 0 lint warnings, no unmapped note, selftest OK (418 checks) and two identical builds (sha256 `48d9c6ca1b45de258672e22e131d67eb47844bfea33ace8c540d6755ed63bc4a`).
- FAIL-LOUD: the page has 22,586 visible words (generator count). The limit of SPEC rule 9 is about 20,000. The fix round added about 2,900 words of caveats, definitions and conditions, and this integration removed 390 of them.
- `asimov-c1nano-perf.html` in the project folder was never written (sha256 `84b13d61...`, dated 2026-11-08 22:11, 333,062 bytes).

### Counts

| Item | Value |
|---|---|
| Visible words, generator count | 22,586 (was 22,976 at the start of this integration, 19,999 before the fix round) |
| Words per section | Short version and Contents 534, setup 2,954, glance 1,253, latency 2,982, bandwidth 2,410, multicore 1,576, ocm 3,268, mesh 723, open 2,891, Words used here 1,369, References 2,346 |
| Figures | 25 (limit 32) |
| Tables | 29 (limit 40) |
| References | 116, every one cited |
| Terms | 82 |
| Bytes | 554,076 |
| Pixel height at 1100 px | 49,763 px (21 slices of 2,400 px in `shots/verify/`) |

### Findings

- The eight fixer reports list 114 finding items (bandwidth 4, shared 62, glance 4, latency 15, multicore 3, mesh 11, open 9, ocm 6). Several items are the same defect seen by two reviewers.
- Accepted: all but one. The fixers had applied most of them. The integrator applied the ones reported as "needed elsewhere":
  - 1.5: "Each command of the one-core sweep runs 3 reps". The DRAM sentence names the DRAM model with the page's wording.
  - 1.4: bullets 1 and 3 now agree with Figure 5 (random order except in the kind "address order", a rep holds one walk or several walks).
  - 6.1: the cycle range that covered best reps only is removed, the prefetch refill bound prints 0.00005, "within 0.18 ns" is computed from the two printed ends, the boot E ratio is a second sample and no longer a "reason to quote".
  - 6.2: the takeaway counts 123 of 140 reps below the every-line row, the caption explains the grey tick, the note carries the L3 register caveat, and the conditions of boots B, C, D are stated.
  - 6.3: the X over Y ratio is computed (2.10 times), the sentence on the busiest data direction is split, the caption of Figure 20 says that the 20 marks stand at 7 distances.
  - 6.5: the takeaway and the bullet give the read and write rates with their passes per rep and no ratio. The rep spread stands next to each rate.
  - 8.2 row 3: "OCM reps". Row 12 points to section 6.1.
  - Figure 3: the legend swatch of a cluster port is a white box with a border (`viz.py`, new legend shape `outline`).
- Rejected: 1. "The boot E random-order value in Table 11 duplicates a boot F1 measurement." Each address-order row is compared with the random-order row of its own boot, and Table 3 has a row that says so.
- Not done, optional in the reports: the region in `max_label` of `data.py` (sec_glance has its own helper), the label rule of the leftmost dot in `viz.dot_rows`, the legend swatch of a tinted kind inside `V.grid` (sec_mesh replaces the swatch itself), the direction of the boot F1 over boot B ratio in 6.1.

### Cuts made (390 words)

- Short version note, Table 1 (one row), notes of Figure 4 and Table 2, intro sentence of section 1, integrity bullet of 1.6.
- 3.1 (pointer paragraph), 3.3 (hit-set checks are in Table 4), 3.4, 3.6 (one bullet and one sentence that Figure 11 and Table 4 carry).
- 4.1, 4.2, 4.3 (sentences that repeat a takeaway or a table), 5.1 (one bullet merged), 5.2.
- 6.3 (route bullet, home is 1.2; back reference paragraph), 6.5 (Insufficient-data box folded into one sentence, home is Table 28 row 8).
- 7.1 (Insufficient-data box folded into the hypothesis), Table 28 rows 2, 3, 7, 9, 13, Table 29 (one row that Table 3 covers), Table 27 note.
- Copies of the modules before this integration: `review/preverify/`. Edit scripts: `scripts/verify/e_*.py`.

### Checks

- Build twice: identical bytes. Selftest OK. 0 non-ASCII characters, `<meta charset="utf-8">` right after `<title>`, no external resource.
- Forbidden words in the page text: 0 for hop, chase, earlier, previously, no longer, L3 off, dual 128, sparse, asm form, was read, boot A. "dense" appears in file names of the References only.
- All 21 slices were looked at. Two defects were fixed after that (Figure 3 legend, Figure 20 caption), and both places were looked at again.
- Spot check with an own parser (`scripts/verify/spot40.py`, `python3 -I`): 56 values across all sections recomputed from the raw CSV files, 56 agree with the page text. The script prints 53 found: the 3 others are the last cells of Table 11, which the text dump prints without the trailing separator, and they were confirmed by a search.

### Remaining known limits

1. Word count 22,586 against about 20,000. The critic's cut order (7.2, 4.4, 3.7, 5.3) is used up. Candidates for a further cut, with their size: section 6.4 with Figure 21 and Table 23 (about 430 words), the line descriptions of the 12 long README and source entries in the References (about 650 words if halved), Table 28 cells (1,500 words against a critic budget of 900 for 8.2), the sub-entries of the Contents (about 150 words), Table 6 (about 230 words).
2. Sections over their SPEC budget: setup 2,954 (2,500), glance 1,253 (1,000), open 2,891 (2,500).
3. Figure 20 still draws overlapping marks. The caption now says so and points to Table 21.
4. Figure 21 draws three of the four row groups of Table 23.
5. "lives" and "life of a command" remain in 7.1 (the critic's own wording).
6. `API.md` does not yet list the legend shape `outline`.
7. Content lost with the earlier cut order is unchanged (see "Open problems" above).
