## 11. The author's three requests after section 10 (2026-11-12)

The author read the answers of section 10.5 and sent three requests. This section lists what changed after them. The reviewer agent has not read these changes.

The requests, in the author's words:

1. "Add flit to Words used here if not done yet."
2. "Change "unknown" of pair port to "estimated 64 GB/s" in spec box, and explain it at `Where each number in the figure comes from`"
3. "`Full replacement texts P1 to P3 are now in section 10.6 of the record (lines 624 to 650). They are not applied`: please apply"

| File | State after this section |
|---|---|
| `crb/crb-memory-hierarchy.html` | 978 lines, as before. @@NREPORT@@ lines differ from the state of section 10: @@LINESREPORT@@. sha256 `@@SHAREPORT@@` |
| `crb/make-brief.py` | The script that builds the brief. 3 lines differ from the state of section 10: 166, 180 and 181 |
| `crb/crb-memory-hierarchy-brief.html` | The brief, built again. 3 lines differ from the state of section 10: the date at line 25 and the two findings at lines 39 and 40. sha256 `@@SHABRIEF@@` |
| `crb/tmp/agent-scratch/apply-p1-p3-2026-11-12/` | Scratch folder of this section [Ref38]. It holds copies of the four files before this section (`report.before.html`, `brief.before.html`, `make-brief.before.py`, `record.before.md`), copies of the state that the check of section 11.7 read (`report.check3-state.html`, `brief.check3-state.html`, `make-brief.check3-state.py`), the edit scripts, the check scripts, the renders and the results of the search and of the checks |

No line was added to the report or removed from it. So the report line numbers of sections 1 to 10 still fit.

The edits were made in two passes. The first pass made 34 edits on 28 lines (`apply_report_p.py`). The check of section 11.7 read that state. The second pass made 37 edits on 15 of these lines (`apply_report_p_fixes.py`). It changed no other line.

A second session of the author works on the report after this section. It announced edits at report lines 232, 233, 253, 505 and 889 and in the page script near line 778, each on its physical line. The sha256 in the table is the state after the last write of this section and before those edits. Line 505 holds the label of row F27.

The work was done on 2026-11-12 in the author's time zone. The clock in UTC already showed 2026-11-13. The brief stamps its date in UTC, and its line 25 now says so: "Brief generated 2026-11-13 (UTC)".

### 11.1 "flit" in "Words used here"

- The report already had the entry "flit, data flit, data channel" (line 451). It did not say what the word stands for.
- The entry now says that "flit" is short for "flow control unit". It quotes the definition of Arm's CHI specification [Ref30]. It names CHI (Coherent Hub Interface) as the protocol of the mesh ports and links.
- Three entries are new on the same line: "credit stall, data stall", "back-pressure" and "write in flight". The text of P3 uses these terms, and the list did not hold them. The sources are page 518 of the CHI specification and TRM pages 1679 and 391 [Ref30][Ref3]. They were read again for this section.
- The entry "pair port" (line 462) is now "pair port, partner cores". It says that the two cores of one pair are called partner cores. It also says that the shared port is inferred from two timing tests and from the port count of the mesh map, and that it was not read from hardware or from documentation. Before, the entry called the shared path "Measured".

### 11.2 The Spec box of the pair port: "estimated 64 GB/s"

The author decided D1. The box now shows a number, and the number is marked as an estimate.

| Place | Line | Change |
|---|---|---|
| Spec box of the pair port in the first figure | 92 | "unknown" became two text lines: "estimated" and "64 GB/s". The box keeps its position and size |
| Label of the figure for screen readers | 77 | "for core and DRAM only" became "for core and DRAM, and an estimate of 64 GB/s for the pair port" |
| Caption of the figure | 97 | Four new sentences say what "estimated 64 GB/s" is and why the measured ~80 GB/s above it is higher. "unknown" now "means that this row gives no number" (before: "no number yet") |
| Paragraph before the source table | 101 | After "The Spec row holds derived numbers only." two new sentences say that the 64 GB/s is an estimate and that one of its three factors is a hypothesis |
| Row "Spec row, pair port" of the source table | 118 | The label is "Spec row, pair port: estimated 64 GB/s". The cell gives the calculation, the source of each factor, and a pointer to the text under the table |
| New text under the source table | 121 | Three paragraphs (two of them with a bold lead), three small tables and three lists (see below). The text stands on the physical line that held only the end of the source table |
| Open item "Spec throughput of the pair port and the SLC" | 416 | "says "unknown" for both" became "says "estimated 64 GB/s" for the pair port and "unknown" for the SLC. The 64 GB/s is hypothesis 1 below. It is not confirmed." |
| Sub-header of the report | 49 | New sentences name the changes of this section |

What the new text under the table says (line 121):

- **The estimate.** A table gives the three factors: 32 B of data in one data flit (Arm document), the mesh clock of 2.0 GHz (measured), and at most one data flit in one direction in one mesh cycle (hypothesis 1, not confirmed). The product is 64 GB/s in one direction (est.).
- **Why it is lower than the measured ~80 GB/s.** A table gives the two places of counting for two partner cores that read 8 MiB each: 77.5 to 78.5 GB/s at the loops (measured), about 13.5 GB/s from the cores' own L2 (est.) and 64.1 to 64.9 GB/s through the port (est.). For one core alone both places were measured in one run: 71 GB/s at the loop and 58.7 GB/s on the port.
- **Three kinds of run that can be converted to the port.** A table gives the rate at the loops, the rate at the port (est.) and its share of 64 GB/s (est.) for reads at 8 MiB, writes at 8 MiB with the asm loop and writes at 1 GiB with the asm loop. The shares are 0.97 to 1.01 (est.).
- **Limits of the estimate.** The lists name the runs behind each rate and the assumptions of the conversion. They say that the split of 83 % and 17 % was counted with one busy core and with the asm loop, that a share of 81 % (est.) gives 62.9 to 63.7 GB/s, and that four of the five read rates are from the read loop compiled from C. They name the runs of two partner cores that were not converted: the write runs of the loop compiled from C and the copy runs. They say that the rates fit the estimate and do not prove it, and which two tests are missing.

Every rate and count of this text is in "Open items" of the report already (lines 418 to 435), with its source. One number is new: "about 13.5 GB/s" for the part from the cores' own L2. It is the measured 77.5 to 78.5 GB/s minus the converted 64.1 to 64.9 GB/s (est.).

What the label does not say. The 64 GB/s is the capacity of hypothesis 1. It is not a measured maximum. The report says so in the caption, in the row of the table and in the new text. My recommendation in section 10.5 was to keep "unknown". The author decided for the number.

The figure now shows a measured value (~80 GB/s) above a lower Spec value (64 GB/s) in one column. The caption (line 97) explains the difference in two sentences, and line 121 explains it in full.

### 11.3 P1 to P3 in the report

The three texts of section 10.6 are now in the report. Each stands at the place that section 10.6 names.

| Text | Report line | Section of the report | Form in the report |
|---|---|---|---|
| P2 (reads at 8 MiB) | 214 | "Is the pair port how the SLC is reached?" | A bold lead sentence, a table of five rows (the kinds of run with their read rates) and a list of six items |
| P3 (one writer) | 289 | "Where one writer's 73 GB/s limit sits (part 5, 2026-11-02)" | A bold lead sentence and a list of eight items. Seven items start with a lead in bold |
| P1 (1 GiB on a pair) | 380 | "The pair finding" | A bold lead sentence, a table of four rows (reads and writes with each loop) and a list of five items |

The author's comment of section 10.2 asked for a better format of a long paragraph. I used the same form here: tables for the rates, and lists for the statements. The approved texts were one paragraph each.

The three texts have 81 sentences. 47 stand word for word in the report. The other 34 are now table cells or lead sentences, or they have a change that this section lists. The script `sentences_p.py` in the scratch folder prints them [Ref38].

What differs from the approved texts, apart from the form:

- **P2, line 214.** The bold lead joins the first and the seventh sentence of P2: "For software: with a buffer of 8 MiB for each thread, two threads on two pairs read 1.6 to 1.7 times as much as two threads on one pair." The table names the number of runs of each row. P2 gave "five runs" and "seven runs". The other counts are from the same files: three runs for one thread alone, five and two for the two kinds of different pairs, and two for four threads [Ref10][Ref31][Ref34]. One sentence is reworded: "With two busy pairs (CPUs 0 to 3) the four threads together read 0.82 to 0.83 of two times the rate of one pair." Its two rates are in the table.
- **P1, line 380.** One table row is new: "Write, loop compiled from C: 44.8 GB/s alone, 63.2 GB/s for two partner cores, the second core adds 18.4 GB/s (41 %)". P1 gave the two rates and not the difference. 63.19 minus 44.78 GB/s is 18.41 GB/s, which is 41 % of 44.78 GB/s [Ref31]. Two words were changed for the rule against idioms. "Two heavy threads" became "Two threads". "are not held to the rate of one reader" became "are not limited to the rate of one reader". The item "Withdrawn" says that no run tested the earlier reason.
- **P3, line 289.** This text has the most changes. All of them come from the check of section 11.7.
  - The second sentence said "so Arm's write-streaming behaviour is confirmed by measurement". No Arm document that the report cites describes write streaming for this core. The sentence is now "Part 5 counted 0.000 refills for writes per line and at most 0.001 write-backs per line (table above). This report calls such writes streaming writes."
  - A new first item names the loop: "All rates in this list are from the asm write loop. With the write loop compiled from C one writer alone writes 44.8 GB/s at 8 MiB and at 1 GiB."
  - The range 70.4 to 73.2 GB/s now names its runs: 73.2 GB/s on CPU 0 on 2026-10-30 (best of three repetitions of 0.5 s), and 70.4 to 71.3 GB/s on CPU 2 in the nine runs of 2 s of part 5. The nine runs of 0.2 s gave 68.9 to 70.7 GB/s. The item says that all rates of part 5 in the list are from the runs of 2 s.
  - "Other runs sent more through the same parts." became "Other runs sent more data through the same port or through the same mesh."
  - The pair rate 81.4 to 82.3 GB/s was the range of two pairs. It is now "the pair wrote 81.4 to 82.1 GB/s" for CPUs 2 and 3, and "82.3 GB/s on 2026-10-30" for CPUs 0 and 1. The item on the conversion adds "CPUs 0 and 1 were not counted either."
  - "The runs do not rule out a limit that depends on the shared path." became "The runs do not exclude a limit in the path that writers share outside the core."
  - P3 said "With a second busy port each writer falls from 71 to 61 GB/s. With four busy ports each writer falls to 57 GB/s." The report now names the CPUs and gives the rates by writer: between 60 and 61 GB/s for each of CPUs 2 and 4, and 57 GB/s on average (55 to 59 GB/s by writer) for CPUs 2, 4, 6 and 8. It adds "No run measured CPU 4, 6 or 8 alone. So the fall is measured for CPU 2 only." In the nine runs of 2 s the threads wrote 60.15 to 61.34 GB/s with two ports and 55.49 to 58.80 GB/s with four ports [Ref5].
  - Four sentences on the counters of these runs are new. The home nodes of mesh 0 show 1.7 × 10^6 data stalls per second with two busy ports and 2.0 × 10^7 per second with four busy ports. The links out of the crosspoint of CPU 2 show 7 × 10^5 credit-stall cycles per second with four busy ports. With four busy ports that is 0.005 data stalls per line written. Each value is the 2 s run minus the 0.2 s run of its case: 3,116,815 data stalls in 1.8000 s (case w8M-c2c4), 35,180,359 data stalls in 1.8001 s and 1,252,463 credit-stall cycles (case w8M-c2c4c6c8) [Ref5].
  - The item on 1 GiB now names the asm loop for its three rates, and it adds the rates of the loop compiled from C (44.8 GB/s alone, 63.2 GB/s for the pair).

The open item at line 437 listed the three old statements as current text. It is now the item "Three older statements were replaced on 2026-11-12". It quotes each old statement and names the section with the new text. Its last entry says what is still open: what limits a pair, whether the pair port limits reads at 1 GiB, and what limits one writer at 8 MiB. It names the tests: the missing tests of the item above it, the per-core asm write sweep, and a read run at 1 GiB with two cores of different pairs on one mesh.

### 11.4 Places that section 10.6 named

Section 10.6 listed the places that change with the three texts. They are changed.

| Row of section 6 | Report line | Change |
|---|---|---|
| F3 | 110, 213, 377 | "134 GB/s" for two cores of different pairs is now "125 to 134 GB/s". Line 213 also gives the rates of CPUs 0 and 2 (126.6 GB/s with the read loop compiled from C, 129.7 GB/s with the asm loop). It says that only cores on different meshes reached 134 GB/s |
| F15, for line 110 only | 110 | The cell no longer says "from the SLC". It says that the 78 GB/s counts every byte that the loops read, and that one core alone takes 17 % of its lines from its own L2 |
| F33 | 343 | "two partner cores share one port and together get no more than one" became "At 8 MiB two partner cores together read only 1.15 to 1.17 times as much as one core alone: 77.5 to 78.5 GB/s against 66.9 to 67.5 GB/s". The pointer now names the section "Is the pair port how the SLC is reached?", which holds both rates |
| F2 | 379 | The caption of the pair chart says "Read loop compiled from C" (before: "asm read") |
| F31 | 278 | "1.8 × 10^9 flits per second" became "1.85 × 10^9". The cell now also gives the values for 1 GiB in brackets, 3 × 10^4 credit-stall cycles and 2.14 × 10^9 flits per second, as the note above the table promises |
| F4, F5, F32 | 214, 289, 380 | These rows named defects inside the three old statements. P1 to P3 replace the statements |
| F30 | Brief lines 39 and 40 | See section 11.6 |

### 11.5 Other places, found by a search

Before the edits four checkers searched the report, the brief and the generator. Three of them read one range of report lines each (47 to 216, 217 to 381, 382 to 978). The fourth searched all files for phrases and numbers of the old statements. Their task was to find every other sentence that still states one of the replaced statements, relies on one, or would read oddly next to the new texts.

They returned 72 findings at 43 places: 29 report lines, the two generator lines, and 12 places in four other files. The four checkers overlap, so one place can have several findings. The findings are in `sweep_results.json` in the scratch folder [Ref38].

Changed because of the search. Each row is a sentence that section 10.6 did not name. The column "Now" gives the text after the check of section 11.7:

| Line | Before | Now | Reason |
|---|---|---|---|
| 52 | "each pair of neighbouring cores shares one path to the mesh of about 80 GB/s" | "with a buffer of 8 MiB each, the two cores of a pair (cores 2k and 2k+1, three pairs tested) together read only about 78 GB/s, against 125 to 134 GB/s for two cores of different pairs" | The Short version gave about 80 GB/s as a property of a shared path. This is the first old statement in other words. The Short version keeps its three sentences |
| 110 | "The mechanism (two cores on one crosspoint port, Arm's CAL2) is from the CMN S3 manual and the map's port count." | "That two cores sit on one crosspoint port is inferred from two timing tests and from the map's port count ... Arm's manual describes the block that allows it (CAL2). It was not read from hardware. What limits the pair was not measured. That the full port is the limit is hypothesis 2 in "Open items"." | The cell named the shared port as the mechanism of the 78 GB/s |
| 179 | "and the one claim that neither confirms is marked" | "The CAL2 and the two hypotheses on the pair port are marked as an inference or as hypotheses." | The section now names more than one claim that is not confirmed |
| 206 | "cores 2k and 2k+1 running together share one 78 GB/s limit" | The cell names the latency fit of all 120 measured CPUs and the pair test on three pairs (CPUs 0 and 1, 2 and 3, 4 and 5), with the rates 77.5 to 78.5 GB/s and 125 to 134 GB/s. It ends with "For these three pairs the pair test fits two cores on one port. It does not show what limits the pair." | The cell gave "one 78 GB/s limit" as a fact, and for every pair |
| 213 | "each streaming its own buffer from the SLC, and added their bandwidths" | "Each core read its own buffer of 8 MiB, which does not fit in its L2. The rates of the two cores were added." | The rates include lines from the cores' own L2 |
| 213 | "a port serving one busy core and one idle core gives the busy core its full 67 GB/s" | "With one more busy core on another pair, a core with an idle partner read 62.4 to 67.1 GB/s (seven runs). A core with a busy partner read 37.8 to 40.3 GB/s (five runs)." | The old sentence gave 67 GB/s as a rate of the port. The rates by thread are from the best repetition of each run [Ref10][Ref31][Ref34] |
| 213 | "What is measured is that CRB's cores are limited in pairs." | "What is measured is that the two cores of a pair slow each other on the three pairs that were tested (CPUs 0 to 5)." The paragraph is now three paragraphs | The pair test ran on three pairs |
| 266 | "From the SLC and DRAM the two loops agree, so there the limit is outside the core." | A list with the read and write rates of both loops. It ends with "These rates do not show where the limit of one core is." The older sentence on the mesh counters (81 % and 19 %) stands unchanged as the last item of that list | The sentence gave a place for the limit. Line 289 now says that it was not measured. The write loops also do not agree. This is row F14 |
| 275 | "every line leaves the core as a write; the 8 MiB bus count below 2 is unexplained" | "At 1 GiB the core sends 2.00 bus writes per line. At 8 MiB it sends 1.52, for a reason that is not known" | The text under the table converts the pair rate with the 1.52. If every line left the core, the pair would send 82 GB/s through one port. This is row F16 |
| 276 | "the stall counter does not see the wait" | "The stall counter shows 0.000 stall cycles per line" | "The wait" took the hypothesis of the old paragraph as a fact |
| 278 | "no back-pressure at the first hop" | "almost no back-pressure on these four links" | The count is not zero. "The first hop" could also mean the step from the port to the crosspoint, which no counter covers |
| 377 | "The same two cores with 1 MiB each (inside L2) get 134 GB/s, so the L2 is private and the shared part is the path to the mesh." | "CPUs 0 and 1, the two cores of one pair, get 134 GB/s together with 1 MiB each (inside L2). So the L2 is private, and what the two partner cores share lies beyond L2. What it is was not measured. Hypothesis 2 in "Open items" says that it is the full pair port." | The sentence named the shared part as a fact |
| 379 | "Pairs are CPUs (0,1), (2,3), (4,5); the others mix pairs." | The same two statements as two sentences, and "CPUs 64 and 119 are on mesh 1. All other CPUs of the chart are on mesh 0." | The two bars at 134 GB/s are the runs with one core on the other mesh |
| 425 | Four rates of two partner readers, and "all four measured rates" | A fifth run is named: 78.1 GB/s for CPUs 0 and 1 in the main sweep. "all five measured rates" | The new texts count five runs |
| 587 | The pair chart drew seven runs | Two more rows: CPUs 0,3 with 124.8 GB/s and CPUs 4,6 with 132.4 GB/s. The chart now holds all nine runs of `pair.csv` at 8 MiB | The text gives 125 to 134 GB/s, and the lowest bar was 126.6 GB/s |

The search also confirmed or sharpened texts that were planned anyway: the figure label for screen readers (line 77), the two text lines of the Spec box (line 92), the caption (line 97), the paragraph at line 101, the row at line 118, the open item at line 437 and the entries of the word list (lines 451 and 462).

Found by the search and not changed:

| Place | What the search found | Why it is not changed |
|---|---|---|
| Line 52 | "One core reads at most ... 67 GB/s from the SLC". Line 214 now gives 69.6 to 71.2 GB/s for one thread in the root runs. This is row F10 | Older text. The contradiction is older than this section (lines 259 and 428 have the higher rates). The proposed text of row F10 stands |
| Line 85 | The Measured box of the pair port says "~80 GB/s" and "per 2 cores" above the new "estimated 64 GB/s". Two checkers proposed "2 cores read" for the third label line | The author named the Spec box only. The caption (line 97) and the new text (line 121) explain the two numbers. A geometry check of the proposal passed |
| Lines 266, 330 and 959 | "81 %" and "19 %" for one reader at 8 MiB. The new texts give 83 % and 17 %. These are rows F15 and F21 | Older text. The 81 % is the scaled count of 2026-10-30 (est.), and line 121 names it as the older count. The rate next to it (67 GB/s) is from the same day. The 83 % was counted on 2026-11-02 at 70.7 to 71.0 GB/s. A change must keep the two runs apart, and it needs the author's decision on row F21 |
| Line 408 | "The SLC latency and bandwidth rows carry a few percent of L2 hits". For one reader at 8 MiB the share is 17 %. This is row F15 | Older text, same reason |
| Line 269 | The heading "Where one writer's 73 GB/s limit sits" now stands over "was not measured" | The heading can be read as a question. Three other places quote it |
| Line 333 | The row "Write, 1 core, "SLC"" gives 73 GB/s on a path through the pair port | Older text. The 73 GB/s is the rate at the loop. Line 289 gives the conversion |
| Line 367 | The caption of the DRAM chart says "asm loop gives the same numbers from DRAM". With one thread the two loops differ (line 380). With 16, 32 and 64 threads the totals agree within 1 % | Older text, and not one of the replaced statements |
| `crb/perf-measurement-tech.html` lines 137, 187, 196, 270, 746 and 780 | The page repeats the old statements on the pair port and on DRAM | Other file. See F13 |
| `crb/plan-2026-11-02.md` lines 12 and 205 | The plan of 2026-11-02 holds the old statements as its questions and results | Other file, a record of that day |
| `crb/crb-cross-check-bill.html` line 180 | One sentence on the pair port | Other file |
| `crb/crb-memory-hierarchy-edited.html` lines 48, 131 and 134 | An older copy of the report | Other file |

### 11.6 The brief

The generator has three changed lines, and the brief was built again with `python3 -B crb/make-brief.py crb/results/sudo-20261102T054936Z`.

- **Line 39 of the brief (generator line 180).** "Pair port: cores 2k and 2k+1 share one crosspoint port (inferred from two timing tests and the mesh map, not read from hardware). Two partner cores together read 78 GB/s with a buffer of 8 MiB each. That rate counts the lines from their own L2 too. Two cores of different pairs read 125 to 134 GB/s. What limits a pair was not measured." Two parts are not in the text of section 10.6: the clause in brackets and the last sentence. The report now marks the shared port as an inference, and the text of section 10.6 did not say that the cause was not measured.
- **Line 40 of the brief (generator line 181).** "What limits one writer at 8 MiB (70 to 73 GB/s) was not measured. Its lines are not allocated in L1 or L2 (0 refills, 0 write-backs). The mesh links out of its crosspoint waited for the receiver in about 0.001 % of the cycles of the mesh clock (2.0 GHz). With the partner core on the same port the pair writes 82 GB/s. Four writers on four ports write 229 GB/s. Hypothesis, not tested: the core keeps only a fixed number of writes unfinished at a time. The test is the write loop run on every core in turn. It was not run. At 1 GiB one writer alone (63.0 GB/s) already reaches the rate of the pair (63.2 GB/s) [sudo-20261102T211150Z/writepath.csv, followup-20261030T194205Z/asm.csv]."
- **What differs from section 10.6 at line 40.** The text of section 10.6 gave "2 × 10^4 credit-stall cycles per second against 1.85 × 10^9 data flits per second" and "the writes that the core keeps in flight". The brief has no word list, so these terms would stand there with no definition. The brief now gives the share of the cycles of the mesh clock in which the links waited: 37,976 credit-stall cycles on the four links in 3,599,908,867 mesh cycles, which is 0.001 % [Ref5]. It also names the test of the hypothesis. The report keeps the two counts (line 289) and defines the terms (line 451).
- **Line 25 of the brief (generator line 166).** "Brief generated 2026-11-13 (UTC)". The words "(UTC)" are new. The script always stamped the date in UTC.
- **Print.** The brief still prints on 2 A4 pages. The text of page 1 ends at 705 of 842 points (before this section: 642). Page 2 starts with "DRAM write bandwidth against writer placement", as before [Ref35].
- **Not changed.** A checker proposed a fourth item for the list "Open" of the brief, on the pair and on the writer. The list never held all open items of the report, and the two findings now say "was not measured" themselves.

### 11.7 Checks of this section

| Check | Result |
|---|---|
| Structure of the report, by script (`structure_check.py`) | 978 lines before and after. 0 tag mismatches. 59 ids, none twice, the same as before this section. 39 href attributes: 38 links inside the page, whose targets are all present, and the link to the font stylesheet |
| Figure geometry: `check_geometry.py crb/crb-memory-hierarchy.html 6` | PASS. The two text lines of the Spec box of the pair port keep 9.7 and 15.2 units to the sides of the box |
| Render with the local headless browser, with the network blocked [Ref35] | The report loads with no script error. All 19 figures that the script draws hold elements. The pair chart has 9 bars. The changed sections were rendered and viewed after the last edit of each: the first figure with its caption, the source table with the new text under it, "Is the pair port how the SLC is reached?", "Bandwidth per core" with the part on one writer, "The pair finding" with its chart, "Open items" and "Words used here". The renders are in `render/` of the scratch folder |
| Brief | Printed after the last edit: 2 pages, and page 2 starts at the page break. 3 lines differ from the brief before this section (25, 39, 40) |
| Search before the edits (section 11.5) | 72 findings at 43 places |
| Check of the first pass: four checkers (numbers of the read statements, numbers of the write statements and of the brief, claims, language and render), each followed by a second checker that tried to refute every finding | 39 findings: 6 major, 16 minor and 17 notes. The second checkers confirmed 32, confirmed 6 in part and rejected 1. They added 15 findings of their own: 9 minor and 6 notes. No number of the new text was wrong. The findings and the verdicts are in `check3_results.json` [Ref38] |
| The major findings | Three defects, and four checkers reported the first one. (1) The table of line 121 converted the write rate of two partner cores at 1 GiB with a bus count of the asm loop, and its source sentence also named the run of the loop compiled from C. Line 429 says that no bus count exists for that loop. The row and the sentence now name the asm loop only. (2) Line 121 said "No run counted both cores of a pair." Counters at the home nodes and on the links did count runs with both cores busy. The sentence is now "No run counted the bus accesses of both cores of a pair." (3) Line 213 said that a core with an idle partner reads the full 67 GB/s. In the seven runs with two cores of different pairs such a core read 62.4 to 67.1 GB/s |
| What the check changed besides | The loop and the runs behind each rate of line 289 (section 11.3). The scope of the pair test: three pairs, at lines 52, 206 and 213. One basis for the inference of the shared port at lines 110 and 462. "Data that one data flit holds" in place of "Size of one data flit", because 32 B is the data field and not the whole flit. One more limit of the read row and the list of the runs that were not converted (line 121). The long paragraphs of lines 213 and 266 as paragraphs and a list. A word-list entry with shorter terms, so that the list keeps its column width. The brief (section 11.6) |
| Rejected | One finding: "64.1 to 64.9 GB/s" should be "64.1 to 64.8". The three counters of the share give 64.06 to 64.92 GB/s, so the value stands |
| Confirmed and not applied | The third sentence of the Short version has 62 words and four statements (line 52). A checker proposed a list of two items. The rule for a Short version allows three sentences, so the two rules conflict. This is the author's decision. Also not applied: the new item for the list "Open" of the brief (section 11.6) |
| Narrow window | In a window of 390 px the page scrolls sideways by 80 px, as before this section (row F35). Two checkers measured a page width of 470 px before and after |

Not done:

- The reviewer agent of the review loop has not read the changes of this section.
- No benchmark ran, and no login to CRB was made.
- The page was not viewed in a normal browser with its web fonts.
- The items of section 6 that are not marked "applied" are still open. They wait for the author's decision.
- The other files that repeat the old statements were not changed (section 11.5).
