## 10. Changes after the review loop (2026-11-12)

The review loop ended on 2026-11-12 at 04:30 UTC. Its last entry names the digest `81bef21aae0ea4628c114234a2f40f6b0644f5d62fcb1d71b5a1bfa09e5ba864` of this record and the report with the sha256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3` (section 9). After that the author decided two open points and sent five comments on the report. This section lists what changed since then. The reviewer agent has not read these changes.

| File | State after this section |
|---|---|
| `crb/crb-memory-hierarchy.html` | 978 lines, as before. 93 lines differ from the reviewed state. sha256 `REPORT_SHA256` |
| `crb/tmp/crb-memory-hierarchy.before-slc-rename.html` | Copy of the reviewed state of the report |
| `crb/make-brief.py` | The script that builds the brief. 10 lines differ from its copy `crb/tmp/make-brief.before-slc-rename.py` |
| `crb/crb-memory-hierarchy-brief.html` | The brief, built again with `python3 crb/make-brief.py crb/results/sudo-20261102T054936Z`. 11 lines differ from its copy `crb/tmp/crb-memory-hierarchy-brief.before-slc-rename.html` |

No line was added to the report or removed from it. So the report line numbers in sections 1 to 9 still fit.

### 10.1 The name "SLC" replaces "mesh cache"

The author confirmed the recommendation of Q4 and asked for the same change in the brief.

- **Rule.** "SLC (L3)" stands where the term is introduced and in main labels. "SLC" stands elsewhere. The word "mesh" stays where it means the interconnect, for example in "mesh counters", "mesh clock" and "own mesh".
- **Report.** 101 replacements on 77 lines. They include the places where the bare word "mesh" named the cache level, for example the chart rows "mesh read", "mesh write" and "mesh copy". These rows are now "SLC read", "SLC write" and "SLC copy".
- **Places with "SLC (L3)".** The sub-header (line 49), the first figure and its screen-reader label (lines 86 and 77), two rows of the source table (lines 111 and 119), the size table (line 144), the heading "The SLC (L3) and the pair port" and its contents entry (lines 178 and 60), the word list (line 454) and one chart label (line 492).
- **Sentences that were rewritten.** Line 49: the change log names the new term. Line 52: the Short version defines the SLC as "the shared cache in the on-chip mesh interconnect, which Linux lists as L3". Line 139. Line 179. Line 183: it says that versions before 2026-11-12 used the old name, and why. Line 454: the entry of the word list.
- **Heading.** The heading 'Why "mesh cache"' is now 'The mesh, and why older versions said "mesh cache"' (lines 182 and 60). The section under it describes the mesh.
- **Old name kept on purpose.** Six lines name the old term as a history note: lines 49, 60, 179, 182, 183 and 454.
- **Not changed.** The element ids and the link targets still contain "mesh-cache". No other file links to them. The identifiers in the page script are not changed.
- **Brief.** The generator got 8 replacements. One sentence was added to the caption of the first table: "SLC: Arm's system level cache, in the mesh. Linux lists it as L3." The label of the table row is now "SLC (L3), 128 slices of 1 MiB, 16-way".
- **Side effect in the brief, corrected.** The shorter label made the first column of that table narrower. A print with the local browser then broke two labels at a hyphen ("4-" and "way", "DDR5-" and "8000"). Four labels now keep their short parts on one line (generator lines 171 to 174). A new print has 2 pages and no such break [Ref35].
- **Other files.** These still say "mesh cache", and they were not changed: `crb/perf-measurement-tech.html` (9 places), `crb/crb-cross-check-bill.html` (12), `crb/mesh0-or-mesh1.md` (11), `crb/plan-2026-11-02.md` (16), four review records in `crb/` (9 in total), `crb/crb-memory-hierarchy-edited.html` (40, an older copy of the report) and three files in `bench/` (5 in total).

### 10.2 The author's comments of 2026-11-12 on the report

| Comment | Change | Lines |
|---|---|---|
| Source table: "The cycle number is derived: ns × 2.8 GHz." becomes "Cycles derived" | Done. The cell now ends with "Cycles derived." | 107 |
| Source table: the label "30 ns (85 cycles)" becomes "SLC latency avg: 30 ns (85 cycles)" | Done | 112 |
| Source table: the label "≥0.62 TB/s whole chip" becomes "SLC throughput ≥0.62 TB/s whole chip" | Done | 113 |
| Every "3 loads + 2 stores" becomes "3 loads / 2 stores" | Done in all six places: the Core box of the first figure, the row label of the source table, a reference to that row, the section heading, its contents entry and one sentence. The mixes "3 loads + 1 store" and "2 loads + 2 stores" keep the plus sign, because each names the operations of one cycle. This decides D6 | 82, 105, 116, 122, 58, 124 |
| The long paragraph on the read loop compiled from C: a better format, and a listing of the C code | Done. The list below gives the details | 131 to 133, 58, 35 |

The passage on the read loop compiled from C:

- It has its own sub-heading now: "The read loop compiled from C: 1.5 loads per cycle". The heading has the new id `the-read-loop-compiled-from-c` and a new contents entry at line 58.
- Three listings were added. The first is the C function `k_read` [Ref21]. The second is the function `k_asmread` with the hand-written loop [Ref21]. The third is the 16 machine instructions of the compiled loop, which are lines 44 to 59 of the saved output from CRB [Ref8].
- The script that wrote the passage copied the listings from these files. A check after the edit found each listing equal to its source.
- The limits that were checked are now one table. Its columns are "Limit in Arm's guide", "Allowed per cycle" and "This loop, average per cycle".
- The two hypotheses are a list. The predictions of the missing test are a small table.
- No statement and no number was changed. A script compared the sentences. Of the 60 sentences of the old text, 47 are in the new text word for word. The other 13 became list items, table cells or table rows.
- New sentences: a lead of four sentences under the sub-heading, two sentences that introduce `k_asmread`, the line "How the loop is counted:", and the sentence "The table below compares each limit with the average rate of the loop."
- The three source lines 131 to 133 are still three lines. A listing keeps its line breaks as the character reference `&#10;`.
- One style rule for the listings was added at line 35.

### 10.3 What "at 1 GiB" means

The author asked what "1 GiB" means in "Two partner cores together wrote 63.2 GB/s at 1 GiB".

- It is the size of the buffer of each thread. Each thread reads or writes its own buffer again and again [Ref33].
- The report now says so in three places: line 421 (the first place in "Open items" that uses the sizes), line 437 (the sentence that the author quoted) and line 457 (word list, entry "GB/s, TB/s").
- Line 457 also says that a copy thread has two buffers of that size. It names the sizes of the tests: 8 MiB and 1 GiB per thread for the bandwidth tests with one, two or four threads, and 3 MiB and 256 MiB per thread for the whole-chip tests [Ref33].

### 10.4 Corrections in "Open items" that the check found

The check of 2026-11-12 (section 10.7) found three places in the open item of this update that said more than the data show. They are corrected.

| Line | Before | Now | Evidence |
|---|---|---|---|
| 421 | The runs of hypothesis 2 included "two partner cores that write 8 MiB each" and "one core that writes 1 GiB" | Both are limited to the asm loop | With the write loop compiled from C one core writes 44.8 GB/s at 1 GiB. That is far below 64 GB/s [Ref31] |
| 425 and 118 | "No run counted the share for two partner cores." | "No run counted the share with only two partner cores busy." Line 425 adds the count of two runs with four busy cores on two pairs: 0.82 accesses to the SLC per line. In those runs each pair read 62.9 to 63.7 GB/s at the loops | [Ref32] |
| 429 | The list of runs that were not checked against the hypotheses named the copy runs only | It also names the write runs of the loop compiled from C: 75.6 GB/s for two partner cores at 8 MiB, and 44.8 GB/s for one core at 8 MiB and at 1 GiB | [Ref31] |

Seven smaller corrections of text that this section wrote were also applied: the first use of "SLC" at line 49, a citation at line 139 (pages 31 to 32), quotation marks at line 179, the heading at lines 182 and 60, one plural at line 297 ("The SLC bar is a lower bound"), the order of two sentences at line 454, and the pronoun "them" at line 421.

### 10.5 Answers to the author's questions of 2026-11-12

**What is a "flit"? Is it a known term?**

- Yes. "Flit" is short for "flow control unit". It is the smallest unit that the flow control of a network link handles.
- Arm's CHI specification defines it: "FLow control unIT (Flit) is the smallest flow control unit. A packet can be made up of one or more flits." and "A flit is the basic unit of transfer in the Link layer." [Ref30]. CHI (Coherent Hub Interface) is the protocol of CRB's mesh [Ref3, pages 12, 17 and 51].
- In CRB's mesh one data flit carries 32 B of data. So a 64 B line needs two data flits [Ref3, page 2120].
- The term is also used outside CHI. The mesh manual names flit formats of 68 B and 256 B for CXL (Compute Express Link) links [Ref3, pages 250 and 621]. A web search result says that PCIe 6.0 has a flit mode too [Ref36].

**"We measured 80 GB/s, but the hypothesis is 64 GB/s."**

- The two numbers are counted at two different places. The 80 GB/s (78 rounded) is every byte that the two loops read. The 64 GB/s is a calculation for the bytes that cross the shared port in one direction: one data flit of 32 B in each mesh cycle, at a mesh clock of 2.0 GHz.
- With a buffer of 8 MiB a part of the lines never crosses the port. The core's own L2 serves them. For one core alone this was measured: the loop read 71 GB/s while its port carried 58.7 GB/s toward the core [Ref5][Ref24]. Three counters give 0.83 for the share of the lines that cross the port.
- If two partner cores have the same share, 77.5 to 78.5 GB/s at the loops is 64.1 to 64.9 GB/s at the port (est.). No run counted the share with only two partner cores busy.
- Where every line must cross the port, the pair rate at the loops is itself close to 64 GB/s. Two partner writers with 1 GiB each write 63.2 GB/s together [Ref10]. With the loop compiled from C one writer alone writes 44.8 GB/s, and two partner writers reach the same 63.2 GB/s together [Ref31].
- At the loops the pair rate differs from test to test: 63 GB/s (writes at 1 GiB), 78 GB/s (reads at 8 MiB) and 82 GB/s (writes at 8 MiB with the asm loop). Converted to the port, the three are 62.0 to 64.9 GB/s (est.). That is 0.97 to 1.01 of 64 GB/s.
- So the rates fit the hypothesis. They do not prove it. A rate close to 64 GB/s also fits a port with a higher maximum that something else holds near that rate. The number of data channels at the port was not read from CRB. "Open items" in the report names the tests.

**Where are F1 to F21?** They are in section 6 of this record. They are not in the report. Entry 6 of the contents list of the report is "Latency".

### 10.6 Replacement texts for the older statements (proposed, not applied)

The author asked what the new statements would be. For the cause of each limit there is no definitive statement. The measured part can be stated definitively. Each text below gives the measured rates first and names the hypotheses as not confirmed. Two checkers compared every number with the raw files (section 10.7). None of the three texts is in the report.

**P1. For the second sentence of report line 380 ("For DRAM traffic the port is not the limit") and the last sentence of line 214 ("For DRAM streams the port is not the limit").**

> With a buffer of 1 GiB for each core, reads and writes behave differently on a pair. All rates are from 2026-10-30. The pair is CPUs 0 and 1. Reads. One core alone reads 28.2 GB/s with the read loop compiled from C and 30.5 GB/s with the asm loop. Two partner cores together read 52.6 GB/s with the compiled loop and 56.7 GB/s with the asm loop. So the second reader on the pair adds 24.5 GB/s or 26.2 GB/s. That is 87 % or 86 % of the rate of one core alone. So two partner readers are not held to the rate of one reader. Two cores on different meshes (CPUs 0 and 64) together read 54.9 GB/s with the compiled loop. That is 2.3 GB/s (4 %) more than the partner pair. CPUs 0 and 64 share neither a pair port nor a mesh. No run has two cores of different pairs on one mesh at 1 GiB. So the cause of this difference was not measured. Whether the pair port limits DRAM reads was not measured. Writes. One core alone writes 63.0 GB/s with the asm loop and 44.8 GB/s with the compiled loop. Two partner cores together write 63.2 GB/s with each loop. So the second asm writer adds 0.2 GB/s (0.3 %). Four writers on two pairs (CPUs 0 to 3) write 113 GB/s. So a second pair adds 50 GB/s. So two partner writers share one limit of about 63 GB/s. What this limit is was not measured. Hypothesis 2 of "Open items" says that the full pair port is this limit. Hypothesis 1 says that the port passes at most 64 GB/s in each direction. Neither is confirmed. The earlier reason, that DRAM latency limits each core first, is withdrawn. No run tested it.

The full text would go to line 380. At line 214 the last sentence would become: "With a buffer of 1 GiB for each core, reads and writes behave differently on a pair (section "The pair finding")." Sources: [Ref10], [Ref31], [Ref34].

**P2. For sentences 1 to 3 of report line 214 ("For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2").**

> For software. The rates below are for a buffer of 8 MiB for each thread, measured on 2026-10-30. Two threads on partner cores together read 77.5 to 78.5 GB/s (five runs on the pairs of CPUs 0 to 5, four with the read loop compiled from C and one with the asm loop). One thread alone read 66.9 to 67.5 GB/s on CPU 0. Two threads on cores of different pairs together read 125 to 134 GB/s (seven runs, best repetition of each). That is 125 to 132 GB/s on mesh 0 and 134 GB/s on two meshes. So two threads on two pairs read 1.6 to 1.7 times as much as two threads on one pair. These rates were measured with no other busy core. With two busy pairs (CPUs 0 to 3) four threads together read 127.6 GB/s with the asm loop and 129.1 GB/s with the compiled loop. That is 0.82 to 0.83 of two times the rate of one pair. In the root runs of 2026-11-02 one thread alone read 69.6 to 71.2 GB/s (CPUs 0 and 2, runs of 2 s). The cause of that difference is not known. All these rates count the bytes that the loops read. They include the lines that a core takes from its own L2. For one core alone that is 0.17 of the lines. No run counted it with only two partner cores busy. What limits the pair was not measured. Hypothesis 2 of "Open items" says that the full pair port is this limit. Hypothesis 1 says that the port passes at most 64 GB/s in each direction. The 78 GB/s and the 64 GB/s are counted at two different places. If 0.83 of the lines cross the port, as counted for one core alone, 77.5 to 78.5 GB/s at the loops is about 64 to 65 GB/s at the port (est.).

The first sentence of line 380 would become: "Two heavy threads on two pairs read 1.6 to 1.7 times as much as two threads on one pair (buffer of 8 MiB for each thread)." The old sentence "about 28 B per core cycle" is dropped. The port belongs to the mesh, and the mesh clock is 2.0 GHz, not 2.8 GHz. Sources: [Ref10], [Ref31], [Ref5], [Ref29], [Ref34].

**P3. For the whole paragraph of report line 289 ("The single-writer limit is inside the core").**

> What limits one writer at 8 MiB was not measured. The lines are not allocated in L1 or L2 (zero refills for writes, zero write-backs), so Arm's write-streaming behaviour is confirmed by measurement. One writer alone writes 70.4 to 73.2 GB/s with a buffer of 8 MiB (CPUs 0 and 2, runs of 2026-10-30 and 2026-11-02). With one writer the counters show almost no back-pressure. The links out of the crosspoint show 2 × 10^4 credit-stall cycles per second against 1.85 × 10^9 data flits per second. The home nodes of mesh 0 show 1 × 10^4 data stalls per second. Other runs sent more through the same parts. CPU 2 sent 1.68 × 10^9 bus writes per second at 8 MiB and 1.96 × 10^9 per second at 1 GiB. With the partner core also writing, the pair writes 81.4 to 82.3 GB/s. Four writers on four ports write 228 to 230 GB/s. These rates count the bytes that the loops wrote. At 8 MiB a line needs 1.52 bus writes, not 2, for a reason that is not known. So 82 GB/s at the loops is about 62 to 63 GB/s at the port (est.). This estimate uses the count of CPU 2. CPU 3 was not counted. The runs do not rule out a limit that depends on the shared path. With a second busy port each writer falls from 71 to 61 GB/s. With four busy ports each writer falls to 57 GB/s. No counter of part 5 covers the write data from the port to the crosspoint. Hypothesis, not tested: the core keeps at most a fixed number of writes in flight. Then the rate of one writer is that number divided by the round-trip time to the home node. The test is a per-core asm write sweep, like the per-core read sweep. It was not run. At 1 GiB the comparison with the partner gives another result. One writer alone writes 63.0 GB/s (CPU 0, 2026-10-30) and 62.9 GB/s (CPU 2, part 5). Two partner writers together write 63.2 GB/s (CPUs 0 and 1, 2026-10-30). So one writer alone already reaches the rate of the pair. What limits the pair was not measured. Hypothesis 2 of "Open items" says that the full pair port is this limit. One count fits it. The 1.96 × 10^9 bus writes per second of CPU 2 are 0.98 bus writes per mesh cycle at the mesh clock of 2.0 GHz (est.). If one bus write is one data flit at the port, that is 98 % of the capacity of hypothesis 1 (est.).

Sources: [Ref5], [Ref10], [Ref24].

If these texts are applied, other places change with them:

- Report line 437 lists the three old statements as current text and says "These sections are unchanged for now." It would then say that the sections were changed.
- Report lines 110, 213 and 377 give 134 GB/s for two cores of different pairs (F3), line 343 repeats the pair statement (F33), and line 379 names the wrong loop (F2).
- The brief repeats two of the statements at its lines 39 and 40 (F30). Proposed texts for the generator, line 180: "Pair port: cores 2k and 2k+1 share one crosspoint port. Two partner cores together read 78 GB/s with a buffer of 8 MiB each. That rate counts the lines from their own L2 too. Two cores of different pairs read 125 to 134 GB/s." Line 181: "What limits one writer at 8 MiB (70 to 73 GB/s) was not measured. The lines are not allocated in L1 or L2 (0 refills, 0 write-backs). The links out of its crosspoint show 2 × 10^4 credit-stall cycles per second against 1.85 × 10^9 data flits per second. With the partner core on the same port the pair writes 82 GB/s. Four writers on four ports write 229 GB/s. Hypothesis, not tested: a limit on the writes that the core keeps in flight. At 1 GiB one writer alone (63.0 GB/s) already reaches the rate of the pair (63.2 GB/s)."

### 10.7 Checks of this section

| Check | Result |
|---|---|
| Structure of the report, by script | 978 lines before and after. 0 tag mismatches. 59 ids (one new, none removed, none twice) and 39 link targets, all present. The two script blocks changed only inside 14 text strings and 2 comments, all by the rename. The style block has one new rule (line 35) |
| Figure geometry: `check_geometry.py crb/crb-memory-hierarchy.html 6` | PASS |
| Old names left in the report | "3 loads + 2 stores": 0 places. "mesh cache" outside ids and link targets: the 6 history notes of section 10.1 |
| Listings | Each of the three listings equals its source: `bench/bandwidth.c` lines 138 to 148 and 173 to 195, and lines 44 to 59 of the saved output from CRB (white space normalised for the third) |
| Brief | An unchanged copy of the generator rebuilt the old brief byte for byte, apart from the date. After the edits the brief differs from the old one in 11 lines: the date, the four label rows of the first table, its caption, three findings, one screen-reader label and one figure caption |
| Render with the local headless browser, with the network blocked [Ref35] | The report loads with no script error, and all 19 figures that the script draws hold elements. The changed section was rendered and viewed: the source table, the new sub-heading, the three listings, the limits table and the test table. The brief was printed: 2 pages, and page 2 starts at the page break. The first figure was also rendered with cairosvg and viewed. The browser had no copy of the page's monospace font, so the listings were viewed in the fallback font DejaVu Sans Mono |
| Check of 2026-11-12, first run: four checkers (rename in the report, brief and language, facts of the answers, replacement texts), each followed by a second checker that tried to refute every finding | 73 findings: 12 major, 36 minor and 25 notes. The second checkers confirmed 60, confirmed 13 in part and rejected none. They added 22 findings of their own. Applied: every finding about text that this section wrote. Not applied: the findings about older text. They are items F22 to F34 of section 6. The findings about the draft answers and the draft replacement texts are worked into sections 10.5 and 10.6 |
| What the first run changed in my own work | Three statements of the open item said more than the data show (section 10.4). The first draft of P1 to P3 called the limit of one writer "by elimination ... in the core" and gave the pair rate with no conversion to the port. Both are corrected in section 10.6. One new sentence at line 457 was wrong for the whole-chip tests and is corrected |

Not done:

- The reviewer agent of the review loop has not read the changes of this section.
- No benchmark ran, and no login to CRB was made.
- The page was not viewed in a normal browser with its web fonts. The listings were not viewed in IBM Plex Mono.
- The other files that still say "mesh cache" were not changed (section 10.1).
- P1 to P3 and F1 to F34 are not applied. They wait for the author's decision.
