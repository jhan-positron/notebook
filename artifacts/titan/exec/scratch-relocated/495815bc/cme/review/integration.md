# Integration of asimov-cme-perf.html

## Short version

The page builds with 0 lint errors and 0 lint warnings, the data selftest passes (190 checks), and two builds give the same bytes.
The shared requests of the five fixer reports that reached me are applied, and the page text and all screenshot slices were checked once for consistency and layout.
The fixer reports of `callcost` (all but its first finding), `ocm` and `open` were cut off in the task text, so their shared requests were handled only where the build notes or the page text showed them.

## Final counts

| Item | Value |
|---|---|
| Page height at 1100 px width | 118,563 px (66 slices of 1,800 px) |
| Figures | 55 (64 SVG elements) |
| Tables | 67 |
| References | 62, all used, every named file exists on disk |
| Terms in "Words used here" | 107, every one used outside the glossary |
| Hypothesis blocks / Insufficient-data blocks | 41 / 42 |
| Size | 1,314,504 bytes |
| sha256 prefix | 9e1c444fc140 |
| Lint | 0 errors, 0 warnings |
| Tables or figures wider than the column | 0 (probe of shoot_full.py) |
| Two builds | byte-identical (`cmp`) |

## What changed in the shared modules

`refs.py`
- `cme_kern.S`: header comment is lines 1 to 67. The four load instructions of the read loop are lines 174 to 177 (the fixer wrote 173 to 176, the file says 174 to 177).
- `sysinfo.txt` of boot F1: new sentence for the processor entries (lines 10 to 91, 10 entries), computed from the file.
- `dmesg.txt`: "The N mapping lines between line A and line B" (the lines are not contiguous).
- `latency.c`: one timed rep is lines 201 to 222 (function `timed_walk`). "timed walk" is now "timed rep".
- `common.h`: new sentence for lines 462 to 495 (counter read, start, stop).
- `run_cme.sh`: "No CSV file states the size of the CME L1. The operator's README of boot F1 gives it."
- Arm guide: "load and store instructions have a bandwidth of two", "2 load or store instructions per cycle", "no limit in vectors or in bytes".
- LLVM model: load pipe (line 84), store pipe (line 85), prefetch pipe (line 86), and line 361 with lines 2885 to 2890 (a 4-vector load holds the load pipe for 2 cycles). Verified in `refs/AArch64SchedC1Nano.td`.

`words.py`
- New entries: call-cost rows, command lifetime, control row (one general wording), correlation coefficient, CSV, excess, free intercept, idle control, in flight, intercept, level subtracted, load pipe and store pipe, repeat difference, residual, write refill (event 0x3281).
- Reworded: B/cycle (2.00 cycles per ns and the measured range from `D.clock`), cme-call row (no "back to back"), L3-event rows (no run history), walked many times (load count from the CSV header), every line flushed first ("timed rep"), demand-only (was "demand-only row", which the page never writes).
- Removed: SOG and TRM (the page writes both names in full). Aliases: pipe, Pearson correlation, demand-only row.

`viz.py`
- Box kind `accent` is an ink outline of 1.5 px on a grey fill. No diagram uses the boot F2 blue.
- The legend swatch of a dashed line series is dashed.
- No "axis starts at" note when the axis range holds 0.
- Sub labels of row charts are 11 px (were 10.5 px).

`shell.py`
- A table column whose header starts with "Footprint" is left-aligned when the alignment is automatic.

`data.py`
- `D.g1` row `dram-32m` is named "Outside the cluster". The OCM row condition reads "all five regions, chain over every line, every line flushed first".
- `CLOCK_MIN_LOADS` and `D.clock['min_loads']` (8,192). `sec_callcost.py` reads it.
- `D.limits['doc']`: `read_load_instructions_per_iter`, `vectors_per_load`, `llvm_ld4_release_cycles`, corrected note.
- Row labels without "back to back".

`API.md`: the notes for the points above.

## What changed in the section modules (consistency only)

- One wording for the documented limit: "2 load or store instructions per cycle" (`sec_setup.py` Table 1, `sec_bandwidth.py` 6.1).
- Section 6.1 hypothesis block now agrees with section 3.3: the LLVM model gives 2 vectors per cycle (est.), one vector per cycle is not the limit, the 4 KiB rows are above it. The two sections contradicted each other before.
- Section 3.4 hypothesis test: the L3-event rows do not carry the prefetch refill counter, so the test asks for more reps with that counter.
- Section 4.4: "repeat spread" is now "repeat difference".
- "back to back" replaced by "that follow each other" in sections 7 and 9, in the heading of 7.6 and in the chart labels.
- Section 8: "control row" for the mesh background count is now "idle control". "Pearson correlation" is now "correlation coefficient", with the same meaning clause as section 5.
- Section 9: "DRAM-backed" is now "on the DRAM model". "us" is now "microseconds". "timed walk" is now "timed pass" (also in 5.6). Figure 51 prints 2.00 cycles per ns.
- Table 47: the cme-call value is the range 124.5 to 125.6 ns, as in Table 13 and Table 46.
- Section 2.6: the block on the two mesh sums now cites the one-line descriptions of the project README, as section 8.9 does.
- Reference of the address-order file names line 15 (the best row) as well.

## Layout defects found in the screenshots and fixed

- Figure 2: the caption says that the CME and its cache have a dark outline. Only the CME box had it. The CME L1 box now has it too.
- Table 9: range cells are set on two lines, so the first column no longer wraps to five lines.
- Figure 23: the annotation overlapped the dashed line. It now sits above the line.
- Footprint columns were right-aligned in some tables and left-aligned in others. They are left-aligned now where the alignment is automatic.

## Checks done

- `python3 -m cme_page.data`: selftest OK, 190 checks.
- `python3 gen_cme_perf.py`: no unmapped reference key, no unmapped term.
- Visible text read once, sections 1 to 10 (dump: `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/integ/page.txt`).
- Script `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/scripts/integ_check.py`: 0 unused glossary terms, 0 unused references, 0 reference files missing, 0 semicolons, 0 history words, 0 forbidden words, no folder name outside the References, figure numbers 1 to 55 and table numbers 1 to 67 all named, no typed figure or table number in a module.
- Every cross-reference resolves (the build raises otherwise).
- Screenshots: all slices of the build before the last four fixes were looked at, except the slice with references 29 to 61. After the fixes the set was retaken (66 slices, `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/shots/full-00.png` to `full-65.png`), and slices 03, 10, 22, 26, 64 and 65 were looked at again. The other slices of the final set were not looked at a second time.
- Copy of the modules before integration: `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/review/integ-backup/`.

## Unresolved

1. The fixer reports of `callcost`, `ocm` and `open` were cut off in the task text. Their shared requests and doubts are not known to me. No content of those sections was dropped.
2. Sections 3.3 and 6.1 depart from the wording of critic G2 ("one vector load per cycle, the one-load-pipe limit of the LLVM model"). The `.td` file gives 2 cycles for a load of 4 vectors, which is 2 vectors per cycle. The page owner should confirm.
3. Viz options that were asked for and not built: a median tick and a hollow marker in the dumbbell (Figure 6), a colour per row or a range mark (Figures 8, 9 and 31), a dashed horizontal line, a reference line over some bars only, a lighter line segment where no row exists. The captions state what the figures cannot show.
4. `D.repeatability` has no entry for the 8 KiB and 16 KiB write repeats. `sec_glance.py` computes them and checks its values against the data layer.
5. Line numbers stand in some table cells of the body (Table 1, Table 2, Table 4, Table 8, Table 66). A strict reading of the citation rule puts them in the References only.
6. Possible duplicates that stay: Figure 52 (9.8) shares its three 32 MiB rows with Figure 32 (6.6), and its other five rows are nowhere else. Table 13 (3.5) is a short form of rows of Tables 46 and 47 (7.8) and Table 67 (9.13). Sections 3.5 and 9.13 point to the owners. Section 7.8 has no pointer back to 3.5.
7. Wording left as it is: past tense "ran" for what the boots did, "the sweep" in section 9 without a definition, "above 2.0 cycles per bracket ns" with one decimal in section 2.7.
8. Section 6 prints two decimals in Tables 29 to 35 and three in Tables 32, 36 and 37. The page-wide rule is the owner's decision.
9. The single-section test scripts `try_*.py` still fail, since they do not install `refs.py`. They were not changed.
10. The module asserts of `sec_glance.py` and `sec_bandwidth.py` stop the build when the data changes. That is intended.

## Final fixes

### Short version

The four final checkers gave 34 findings: 29 are fixed in full or in part, 5 parts are rejected with a reason, and the page length finding is not resolved (the page is 1,791 px longer than before, not shorter).
The page builds with 0 lint errors and 0 lint warnings, the data selftest passes (190 checks), and two builds give the same bytes.
Every number that this pass added was recomputed from the raw files of boot F1 and boot F2 with a separate parser (`python3 -I`), and no file that SPEC hard rule 1 forbids was opened.

### Words used here

- Fix pass: this step, the last edit of the page after the four final checks.
- No-drop rule: the fix rule "no content dropped except duplicates turned into cross-references".
- Figure and table numbers below are the numbers of the final page. A number of the checked page is given as "was N".

### Final counts

| Item | Value |
|---|---|
| Page height at 1100 px width | 120,354 px (67 slices of 1,800 px). Before this pass: 118,563 px |
| Figures | 56 (66 SVG elements). Before: 55 |
| Tables | 68. Before: 67 |
| References | 62, numbered by first use in reading order, all cited |
| Terms in "Words used here" | 115, every one used outside the glossary. Before: 107 |
| Hypothesis blocks / Insufficient-data blocks | 39 / 44. Before: 41 / 42 |
| Visible words | 60,930. Before: 59,354 |
| Size | 1,325,560 bytes |
| sha256 prefix | 4a2c195c5f2c |
| Lint | 0 errors, 0 warnings |
| Tables or figures wider than the column | 0 (probe of shoot_full.py) |
| Two builds | byte-identical (`cmp`) |
| Data selftest | OK, 190 checks |

### Fixed

Checker numbers-B (1 finding)

- Table 41, 0.01 ns: the three times of a row come from two columns of the file, so they can differ by 0.01 ns. The table note says so. The tooltip of Figure 37 lists the three times and no longer writes them as a sum.

Checker rules (11 findings)

1. Line numbers in the body: removed from the cells of Tables 1, 2, 4 and 8 and of the address-order table of section 9.12. Each cell keeps its [RefN]. The reference entries of the two command logs now also hold the lines with the count of failed commands. All other line numbers were in the reference entries already. The visible body text holds no line number (script check).
2. Figure 2, SLC label: see "Rejected". The label is set on its own line as "3.75 MiB est. in all", so "est." cannot be separated from the value.
3. "about 299 ns" (section 9.4) and "about 14 ns" (section 9.10): replaced by computed values (the gap of 292 to 302 ns, and 14.4 ns as the median of the higher reps minus the median of the lower reps).
4. `sec_l3.py`, "1.0000 per load": the value is computed from the rep rows that the sentence names.
5. Typed counts: "the three reps", "all three footprints", "the five groups" and "the three footprints" are computed. "Every row is above the baseline" is chosen by a condition. "Every row except the looped ..." is guarded by an assert.
6. "in-span": replaced by "span time" in the lanes legend of section 7.1 and in the table of section 7.9.
7. Pass and rep in section 8: one paragraph at the top of section 8 says that a timed rep of an OCM latency row is one pass, and that the section calls it a pass.
8. Short version, sentence 3: it now gives the read and write rates of boot F2 (110.8 to 132.4 GB/s and 51.6 to 53.4 GB/s).
9. Lead with a chart: in sections 7.1, 7.2, 7.6, 6.5 and 6.7 the figure follows the lead bullets, and the explanation follows the figure.
10. Reference numbers: `S.render()` renumbers every [RefN] by first use in reading order (Short version, then the sections). Script check: the first uses read 1, 2, 3 ... 62, and 617 links plus 62 entries make all 679 marks.
11. Glossary: new entry "ADD, CMP, SUBS, B.LO, B.NE".

Checker reader (22 findings)

1. Short version and baseline: sentence 2 says that a test load takes 21.0 ns for the round trip, plus 0.010 to 0.235 ns from the CME L1, plus 50.7 ns from the DRAM model. The takeaway and the tooltips of Figure 1 give the time above the baseline.
2. Terms before their definition: the Short version defines Asimov and boot. The note under Figure 1 defines cluster, OCM and the three chain kinds of the row labels. The glossary has new entries Asimov and boot.
3. "Test plan" against "run plan": section 7.8 and two reference texts said "test plan" for `follow-up-run-plan.md`. They say "run plan". The glossary has both plans.
4. The 186 ns conflict: section 7.2 says that the intercept is the fixed time of one looped read call on boot F1, fold and stamps included, and not the cost of a call in general (a call with one register step takes 124.5 to 125.6 ns). The two tables of section 7.9 use the same wording and point to each other.
5. "est." on fitted values: every fit intercept and fitted rate carries "est." (sections 7.1 to 7.3, the fit table headers and note, the chart label, section 7.9, Table 13, sections 9.2 and 9.5).
6. Section 4.4: "The intended difference between the two boots is one firmware setting", followed by the two other known differences and a link to section 2.2.
7. Section 9.2: the hypothesis gives 2.38 to 2.49 cycles per store for the single-call rows from 4 KiB to 256 KiB, bracket time, both boots (computed).
8. L3 hit share: section 9.6 has a new table (miss minus refill per load times the footprint, per rep), new observation bullets, a second Hypothesis block with its test, and one more line under "What would settle it". The product reads 96.5 to 98.2 KiB in the last rep at 128 KiB to 384 KiB and 81.2 KiB at 96 KiB. Section 4.3 has an "Insufficient data" bullet with links. Checked against the raw file with `chk_new.py`.
9. Copy rows (section 6.3): two meaning sentences (the written half equals the write kernel within 0.2 GB/s at 16 KiB and 48 KiB, the read half is 0.48 to 0.61 times the read kernel from 96 KiB to 2 MiB, 0.56 times on boot F1 and 0.97 times on boot F2 at 32 MiB), one Insufficient-data block, and one new row in the table of smaller items (section 9.10). Checked against the raw files with `chk_new.py`.
10. Step counts of the project README: line 40 of `README.md` names notes of the operator as the source. Section 8.1 says so and has an Insufficient-data block. Section 8.3 says that the two groups are an observation by region and that mesh steps are one hypothesis. The reference entry names line 40.
11. Sign of a difference: partly fixed. The gap of the OCM figure (Figure 43) is boot F1 minus boot F2, as in Figures 1, 7 and 15. Section 2.2 states the rule in a note. See "Unresolved" for section 6.
12. Order of section 5: "What the three events are" is section 5.1 and the scatter is section 5.2. The key points use the hit share, as section 5.2 does.
13. Section 7.6: split into 7.6 (a call alone in its bracket) and 7.7 (the CME cycle counter gap). Section 7.7 has a new to-scale lanes diagram of the four nested intervals (Figure 40). The last two columns of Table 44 are named "window minus bracket" and "bracket minus CME-counted time". The three Hypothesis blocks, which section 9.4 repeated, are one cross-reference each, and the 4,065 ns arithmetic stands in section 9.4 only. The one test that section 9.4 did not have was added there. Figure 40 was checked against the raw files with `chk_fig40.py`.
14. Table of fits (Table 25): partly fixed. The rows stand in two groups with a heading each, and the note says that the letter only names a fit. See "Rejected" for the cut.
15. Page length: partly fixed, see "Unresolved". Cut: the table under Figure 2 (now a cross-reference to section 3.1), the list "How the bandwidth test produces a row" of section 6 (now a pointer to sections 2.4 and 2.5 with three reading points), and the three repeated Hypothesis blocks of section 7.6.
16. Long captions: Figures 1, 2, 4, 27, 34, 36 and 39 have a short caption above the chart. Files, references and simplifications stand in a small note under the takeaway (`S.fig(..., note=...)`).
17. Undefined words: glossary entries for best rep, thread barrier and command. "Plain ratio" is replaced by "the ratio with the round-trip baseline left in".
18. Cycles: Table 9 and the two full latency tables (Tables 20 and 21) have a column "above the baseline, cycles" (ns times the measured 2.00 cycles per ns).
19. Figure 19 (was 20): redrawn. Two boxes in the middle hold the two equalities, and each counter has one arrow to the equality that it enters. No label crosses an arrow.
20. Figure 2: the gaps between the boxes are wider, so the three "miss" labels and the tag "document not on disk" touch no border.
21. Empty chart areas and narrow columns: Figure 22 starts at 20 ns and Figure 54 (was 53) at 70 ns, both said in the caption and on the axis. Table 12 names its files A, B and C in the note, so its first two columns do not wrap to four lines. The axis of Figure 6 starts on a tick.
22. Figure 42 (was 41): each route is drawn on the mesh links as a dark stroke, with the step number at each link.

### Rejected, with reasons

- Rules 2 (Figure 2 label without "est."): the label did carry "est.". The text was wrapped, and "est. in all" stood on the second line of the box. The line break is fixed (see above).
- Reader 1, second x axis on Figure 1: one axis per chart is a rule of the SPEC. The takeaway, the tooltips and the new column of Table 9 give the time above the baseline.
- Reader 14, cut seven of the ten fits: the no-drop rule. The seven rows are not duplicates.
- Reader 15 (a), merge Figure 7 into Figure 1: the SPEC outline asks for the headline figure in the Short version and for the same figure "in full" in section 3.
- Reader 15 (b), one "do not quote" table: the SPEC outline places such a list in section 3 and in section 7. The three lists point to each other, and section 7.9 has the two pointers that it lacked.
- Reader 15 (d), cut Figures 22 and 24: Figure 22 is the lead chart of section 5.4 (SPEC rule 8). Figures 24 and 25 show the same rows against two different axes, which is not a duplicate.
- Reader 15 (f), (g), (h): five of the eight rows of Figure 53 are in no other figure, Table 12 holds the bandwidth repeats that Tables 27 and 28 do not hold, and the bullets on the idle control are five different facts. The no-drop rule applies.
- Reader 22, crop of the mesh map: the map keeps the 6 x 6 grid that the text names. The empty rows are drawn lower, as before.

### Unresolved

1. Page length. The page is 120,354 px high and has 60,930 words. That is 1,791 px and 1,576 words more than the checked page. The cuts of this pass are smaller than what the other fixes added (one figure, one table, eight glossary terms, the open item on the L3 hit share, three table columns).
2. Hypothesis blocks that stand in a result section and again in section 9 (sections 4.4, 4.5, 4.7, 5.6, 6.2, 7.8 and 8.3). Only section 7.6 was reduced to a cross-reference. The others need a block-by-block comparison of their tests before one copy can go, and this pass did not make it.
3. Section 6 keeps boot F1 in the first columns and the ratio "F2 / F1" (Tables 29 to 37 and Table 63). Each header names its direction. A change to "F1 / F2" touches every table and about thirty sentences of sections 6 and 9.8.
4. Captions: only the seven longest have the short form. The other 49 figures keep their caption as it was.
5. Screenshots: all 67 slices were retaken on the final build. I looked at slices 0, 4, 6, 10, 14, 25, 36, 38, 42, 43, 46, 47 and 59 in full and at crops of slices 13, 22 and 62. Slices 6, 43 and 46 were seen on the layout of the last build. After the other slices were seen, only text changed (sections 2.4, 7.3, 7.7, the start of section 8, and 9.6), and the page height stayed 120,354 px. The other 51 slices were not looked at in this pass.
6. Of the earlier "Unresolved" list above: item 5 (line numbers in table cells) is resolved, and item 6 is resolved for the missing pointer of section 7.9. Items 1 to 4 and 7 to 10 are as they were.

### What changed in the shared modules

- `shell.py`: `S.fig()` takes `note=`. `S.render()` renumbers the references by reading order and sorts a run of [RefN] links. New CSS class `fnote`.
- `words.py`: new terms ADD, CMP, SUBS, B.LO, B.NE, Asimov, best rep, boot, command, run plan, test plan, thread barrier.
- `refs.py`: the two command-log entries (lines of the failed-command counts) and the project README entry (line 40).
- `API.md`: the two notes for `S.fig` and `S.ref`.
- `data.py`, `viz.py` and `gen_cme_perf.py` are unchanged.

### Files of this pass

- Edit scripts and checks: `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/scripts/finalfix/` (`p_*.py` edits, `chk_fig40.py` and `chk_new.py` raw-file checks, `crop.py`).
- Modules before this pass: `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/review/final-backup/`.
- Page before this pass, text dumps and crops: `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/review/final/`.
- Screenshots of the final build: `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/shots/full-00.png` to `full-66.png`.
