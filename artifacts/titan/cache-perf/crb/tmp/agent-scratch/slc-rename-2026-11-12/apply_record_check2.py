#!/usr/bin/env python3
"""Record update after the second check of 2026-11-12.
Part 1: findings RC1 to RC30 and the skeptic's notes X-1 to X-3 about the record.
Part 2: the record follows the 13 report edits of apply_report_check2.py.
Every old text must occur exactly once in its line. New lines are inserted last, from the
bottom up, so the line numbers in this script are those of the record before this script.
Usage: apply_record_check2.py <sha256 of the final report> [--write]"""
import sys

P = "/home/jhan/tmp/update-crb-memory-hierarchy.md"
SHA = sys.argv[1]
assert len(SHA) == 64 and all(c in "0123456789abcdef" for c in SHA), SHA
L = open(P, encoding="utf-8").read().split("\n")
assert len(L) == 673 and L[-1] == "", len(L)
n_edits = 0
inserts = []  # (line number after which to insert, [new lines])


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


def whole(n, prefix, new):
    global n_edits
    assert L[n - 1].startswith(prefix), (n, L[n - 1][:80])
    assert "\n" not in new
    L[n - 1] = new
    n_edits += 1


def after(n, prefix, new_lines):
    assert L[n - 1].startswith(prefix), (n, L[n - 1][:80])
    inserts.append((n, new_lines))


SCRATCH = "crb/tmp/agent-scratch/slc-rename-2026-11-12/"

# ---------------------------------------------------------------- Words used here
# RC18
sub(40, "The report calls it the mesh cache.",
    "Until 2026-11-11 the report called it the mesh cache. Text of this record that was written before 2026-11-12 "
    "still uses that name in places. Since 2026-11-12 the report says SLC (section 10.1).")
# RC19
after(49, "- **est.**: estimate.", [
    "- **Review loop, reviewer agent**: the exchange between the writer of this record and a second agent, the reviewer agent. The reviewer wrote findings and the writer replied, both in the shared file of section 1. Sections 8 and 9 give the changes after its rounds 1 and 2.",
    "- **Brief, generator**: the brief is `crb/crb-memory-hierarchy-brief.html`, a results brief of two A4 pages. The script `crb/make-brief.py` builds it. This record calls that script the generator.",
    "- **Digest**: the sha256 of a file.",
    "- **Checker**: one of the agents of the checks of 2026-11-12 (section 10.7).",
    "- **Home node**: the mesh node that owns an address range and holds a slice of the SLC.",
    "- **Root run, final run**: a root run is a run of the script `bench/run_sudo.sh` with root rights on 2026-11-02. The final run is the one that started at 05:49 UTC, in `results/sudo-20261102T054936Z`. It is the last run with parts 1 to 4.",
    "- **Sweep, main sweep**: a sweep is one test repeated over a list of settings, for example over all cores. The main sweep is the run of `bench/run_crb.sh` on 2026-10-30, in `results/20261030T193108Z`.",
    "- **Hop**: one step from a crosspoint to a neighbouring crosspoint.",
    "- **Memory request**: one request from a home node to a memory controller, as the home-node events `hns_mc_reqs_local_all` and `hns_mc_reqs_remote_all` count it.",
    '- **Credit-stall cycle, data stall, back-pressure**: a sender needs one credit for each flit [Ref30]. A credit-stall cycle is one count of the link event that the TRM describes as "signaled when flit transmission is stalled and waiting on credits" (page 1679). A data stall is one time that a home node "has a pending TXDAT flit but no credits to upload" (TRM page 391). Back-pressure is the report\'s word for such waits.',
    "- **Write streaming, write-back, write in flight**: write streaming is the report's term for writes whose lines are not allocated in L1 or L2 (report line 289). A write-back is one count of the core events `l1d_cache_wb` and `l2d_cache_wb`. A write in flight is a write that the core has sent and that is not yet complete.",
    "- **Headless browser**: a web browser that runs with no window. It writes the page to an image file or a PDF file.",
    "- **cairosvg**: a Python library that draws an SVG figure into an image file.",
])

# ---------------------------------------------------------------- section 1
sub(55, "`REPORT_SHA256`", "`" + SHA + "`")

# ---------------------------------------------------------------- section 4, D3 (RC30)
sub(289, "to the Spec row.",
    'to the Spec row. Since 2026-11-12 the label is "3 loads / 2 stores of 16 B per cycle *" (section 10.2).')

# ---------------------------------------------------------------- section 6
# RC3, RC16
sub(352, "F22 to F34 were found by the check of 2026-11-12 (section 10.8).",
    "F22 to F33 were found by the checkers of 2026-11-12, and F34 by the browser render of the same day (section 10.7). "
    "F35 was found by the second check of that day.")
# RC30
sub(368, "Not checked against the new facts. The technique page repeats",
    "The check of 2026-11-12 read the brief for the rename and found F28 to F30. It did not compare the other numbers "
    "of the brief with the new facts. The technique page was not checked. It repeats")
# RC26
sub(377, "`results/followup-20261030T194205Z/dram.csv` line 75]",
    "`results/followup-20261030T194205Z/dram.csv` line 75]. The file `spread.csv` holds no CPU list, so the raw file "
    "does not show the spacing of the threads")
# RC22
sub(378, "A checker reports that the cells of that figure show 20.8 and 43.2 ns. I did not recompute those two cells",
    "The cells of that figure show 20.8 and 43.2 ns. The second check recomputed them. Each is the mean of the two "
    "slices of its crosspoint in the final run: (19.18 + 22.39) / 2 and (43.89 + 42.53) / 2 "
    "[`results/sudo-20261102T054936Z/full/latency.csv`]. The fit of the final run gives 2.86 ns per hop for CPU 0. "
    "The 19.0 ns and the 42 ns of the label fit the earlier run `results/sudo-20261102T040631Z`")
# RC23
sub(379, "A checker reports that 0.76 is the count of mesh 0 and that mesh 1 counted 0.38 more. I did not recompute the 0.38",
    "The 0.76 is the count of mesh 0 (0.759 per line, event `hns_mc_reqs_local_all`). Mesh 1 counted 0.376 more per "
    "line with the event `hns_mc_reqs_remote_all`. The sum is 1.14 [`results/sudo-20261102T054936Z/writebw.csv` "
    "lines 47, 56, 64 and 73, recomputed in the second check]. Report line 375 says that a proxy counts a request "
    "that its home also counts. So the sum is a count of events")
# RC21
sub(380, 'Line 265: "Buffer sizes: L1 = 32 KiB, L2 = 1 MiB, SLC = 8 MiB, DRAM = 1 GiB per thread. A copy thread has two buffers of that size." Line 385:',
    'Line 265, first sentence only: "Buffer sizes: L1 = 32 KiB, L2 = 1 MiB, SLC = 8 MiB, DRAM = 1 GiB per thread. '
    'A copy thread has two buffers of that size." The sentence "Copy counts bytes read plus bytes written." stays. Line 385:')
# RC24
sub(382, "I did not render that figure",
    "The second check rendered the final report with the headless browser and saw the same overlap. The band label "
    "starts at x = 696.7 with y = 34. The other label ends at x = 817.7 with y = 32.9 (units of the figure)")
# RC25
sub(384, "A checker reports a mean of 29.41 ns over the rows of the root run, which is 82 cycles. I did not recompute that mean",
    "The second check recomputed the mean of the final run. The column ns_median of "
    "`results/sudo-20261102T054936Z/full/latency.csv` has a mean of 29.41 ns over its 15,360 rows (the 120 rows "
    'marked "mixed" left out). That is 82 cycles')
# RC20, X-3
sub(389, 'A browser render shows the long texts of the column "Source" set flush right, which is hard to read.',
    'A browser render shows the long texts of the column "Source" aligned to the right edge. Such text is hard to read.')
sub(389, "(for example lines 102 to 121)",
    "(for example lines 102 to 121, and the two tables that section 10.2 added at lines 132 and 133)")
# RE13 of the report check: a new found item
after(389, "| F34 |", [
    "| F35 | Lines 183, 213, 461 and 467, in a narrow window | In a window of 390 px the whole page scrolls sideways by 80 px. Long path names in `code` elements cannot break. The widest are the paths at lines 213 and 183. The report before the changes of section 10 has the same overflow, with the same 46 elements past the right edge. At 1000 px nothing overflows. Two checkers of the second check measured this in the headless browser | A style rule that lets long `code` text break inside paragraphs, list items and captions. In a test copy the rule `overflow-wrap: anywhere` reduced the overflow from 80 px to 8 px. It also changed line breaks at 1000 px, so it needs the author's decision |",
])

# ---------------------------------------------------------------- section 10, intro and file table
# RC17
sub(498, "Its last entry names the digest `81bef21aae0ea4628c114234a2f40f6b0644f5d62fcb1d71b5a1bfa09e5ba864` of this record and the report with the sha256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3` (section 9).",
    "Its last entry carries the digest `81bef21aae0ea4628c114234a2f40f6b0644f5d62fcb1d71b5a1bfa09e5ba864` of this record and says that both submitted hashes match. The entry before it names the report with the sha256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3` (section 9).")
sub(502, "`REPORT_SHA256`", "`" + SHA + "`")
# X-1 of the record check
after(505, "| `crb/crb-memory-hierarchy-brief.html` |", [
    "| `" + SCRATCH + "` | Scratch folder of this section, a copy of the session scratch folder made at the end of the work. It holds the edit scripts (`apply_report.py`, `apply_report_bufsize.py`, `apply_report_fixes.py`, `apply_report_comments.py`, `apply_report_check2.py`, `apply_brief_generator.py`, `apply_brief_generator_nowrap.py`, `apply_record_10.py`, `apply_record_check2.py`), the draft answers (`draft_answers.md`), the renders (`render/`, `check2/final/` and `figure-after-slc-rename.png`), the results of the two checks (`check1_results.json` and `check2/check2_results.json`) and the folders of the checkers (`agents/` and `agents2/`). The browser profile folders were left out. The scripts in it name the session folder in their paths |",
])

# ---------------------------------------------------------------- 10.1
# RC4
whole(515, '- **Places with "SLC (L3)".**',
      '- **Places with "SLC (L3)".** The first figure and its screen-reader label (lines 86 and 77). Two rows of the source table (lines 111 and 119). The size table (line 144). The heading "The SLC (L3) and the pair port" and its contents entry (lines 178 and 60). The word list: the entry itself and two references to that heading (lines 454 and 466). One chart label (line 492). The sub-header (line 49) has the long form "SLC (system level cache, L3)".')
# follows report edit RE9
sub(516, 'Line 52: the Short version defines the SLC as "the shared cache in the on-chip mesh interconnect, which Linux lists as L3".',
    'Line 52: the Short version defines the SLC as "the shared cache that Linux lists as L3, located in the on-chip mesh interconnect".')
# RC5
sub(520, "The generator got 8 replacements. One sentence was added to the caption of the first table:",
    "The generator got 8 edits: 7 replacements of the name and one new sentence. The new sentence is in the caption of the first table:")
# RC20, RC30
sub(522, "`crb/perf-measurement-tech.html` (9 places), `crb/crb-cross-check-bill.html` (12), `crb/mesh0-or-mesh1.md` (11), `crb/plan-2026-11-02.md` (16), four review records in `crb/` (9 in total), `crb/crb-memory-hierarchy-edited.html` (40, an older copy of the report) and three files in `bench/` (5 in total).",
    "`crb/perf-measurement-tech.html` (9 places), `crb/crb-cross-check-bill.html` (12 places), `crb/mesh0-or-mesh1.md` (11 places), `crb/plan-2026-11-02.md` (16 places), four review records in `crb/` (9 places in total), `crb/crb-memory-hierarchy-edited.html` (40 places, an older copy of the report) and three files in `bench/` (5 places in total). The older copy also keeps the label \"3 loads + 2 stores\" in 2 places.")

# ---------------------------------------------------------------- 10.2
# RC1, with the count repeated after the corrections of the second check
whole(541, "- No statement and no number was changed.",
      '- No number was changed, and no statement was removed. The second check recounted the sentences with two scripts, and the count was repeated after the last corrections (`check2/final/sentences_final.py` in the scratch folder). The old text (report lines 131 to 133 before the change) was split at each full stop that ends a sentence. It has 57 sentences. 43 of them are in the new text word for word. Of the other 14, ten became list items, table cells or table rows. Four stayed sentences with a small change. The sentence on `k_read` now starts with "The read loop compiled from C is the function" and ends with the citation "[lines 138 to 148]". The label "Observation:" became the bold lead-in "Observation.". "The dispatch step handles at most 10 instructions per cycle." became "The dispatch step handles at most 10 of them per cycle." and now follows the sentence on MOPs. "The loop is below these too on average (est.)." became "The rates of the loop in the last two rows of the table are estimates (est.)."')
# RC6, and the new list item of report edit RE11
sub(542, 'and the sentence "The table below compares each limit with the average rate of the loop."',
    'and the sentence "The table below compares each limit with the average rate of the loop." Also new, as form: six bold lead-ins ("Source code.", "Machine code.", "Which build was read.", "The limits that were checked.", "Observation.", "The test that is missing.") and the head rows and row labels of the two tables. One item was added to the list "Which build was read" after the second check. It says that the listing of `k_asmread` shows the file of 2026-11-02, and that no copy of the asm source of 2026-10-30 was found [Ref37].')
sub(544, "One style rule for the listings was added at line 35.",
    "Two style rules for the listings were added at line 35, one for `pre` and one for `pre code`.")
after(544, "- Two style rules", [
    '- Side effect of the two new row labels at lines 112 and 113, found by the second check and not changed. The column head of that table is "Label in the figure". The figure still shows the short labels "30 ns (85 cycles)" and "≥0.62 TB/s whole chip". The caption of the figure calls the second value "SLC bandwidth", and the new row label says "SLC throughput". The two labels are the author\'s wording.',
])

# ---------------------------------------------------------------- 10.3
# RC12
sub(552, "for the whole-chip tests [Ref33].", "for the whole-chip tests [Ref33]. The 3 MiB is in the result files of [Ref11].")

# ---------------------------------------------------------------- 10.4
# RC7
sub(560, "With the write loop compiled from C one core writes 44.8 GB/s at 1 GiB. That is far below 64 GB/s [Ref31]",
    "With the write loop compiled from C one core writes 44.8 GB/s at 1 GiB, and two partner cores write 75.6 GB/s at 8 MiB [Ref31]. No bus count exists for that loop, so neither rate can be converted to the port. If every line of the 1 GiB run crosses the port once, 44.8 GB/s is 0.70 of 64 GB/s (est.)")
# RC7, RC28, and report edits RE1, RE2, X-1
whole(561, "| 425 and 118 |",
      '| 425 and 118 | "No run counted the share for two partner cores." (line 425) and "No run counted this share for two partner cores." (line 118) | "No run counted the share with only two partner cores busy." (line 425) and "No run counted this share with only two partner cores busy." (line 118). Line 425 adds the count of both complete sets of the root run with four busy cores on two pairs: 0.82 accesses to the SLC per line. In the runs that gave these counts the four cores together read 126.0 to 126.2 GB/s at the loops. That is 63.0 to 63.1 GB/s for one pair on average. The files do not record the rate of each pair. Line 425 also says that these runs have two busy pairs and are not runs of hypothesis 2 | [Ref32] |')
# report edit RE3
sub(562, "It also names the write runs of the loop compiled from C: 75.6 GB/s for two partner cores at 8 MiB, and 44.8 GB/s for one core at 8 MiB and at 1 GiB",
    "It also names the write runs of the loop compiled from C: 75.6 GB/s at 8 MiB and 63.2 GB/s at 1 GiB for two partner cores, and 44.8 GB/s for one core at 8 MiB and at 1 GiB")
# RC8, and the list of the report edits that followed the second check
whole(564, "Seven smaller corrections of text that this section wrote were also applied:",
      "Seven smaller corrections were also applied. Five are in text that this section wrote:")
after(564, "Seven smaller corrections were also applied.", [
    "",
    '- the first use of "SLC" at line 49',
    "- quotation marks at line 179",
    "- the heading at lines 182 and 60",
    "- the order of two sentences at line 454",
    '- the pronoun "them" at line 421',
    "",
    "Two are in older wording of sentences that the rename edited:",
    "",
    "- a citation at line 139 (pages 31 to 32)",
    '- one plural at line 297 ("The SLC bar is a lower bound")',
    "",
    "The second check of 2026-11-12 (section 10.7) led to 13 more edits of the report. They are on lines 49, 52, 131, 132, 425, 429 and 437:",
    "",
    '- Line 425, three edits. The rate of the runs with four busy cores is now that of the runs that gave the counts (the row for lines 425 and 118 above). Before, the sentence gave 62.9 to 63.7 GB/s for "each pair". That range is half of the totals of all ten 2 s runs of the case, and the files do not record the rate of each pair. "So that count is from another load." became "These runs have two busy pairs. They are not runs of hypothesis 2. So that count does not give the share for two partner cores alone.", because "load" means a read operation in the report. "Two runs of 2026-11-02" became "Both complete sets of the root run of 2026-11-02".',
    "- Line 429: the sentence on the write runs of the loop compiled from C now also gives 63.2 GB/s for two partner cores at 1 GiB [Ref31].",
    '- Line 437: the two write rates at 1 GiB now name the asm loop ("With the asm loop two partner cores together wrote 63.2 GB/s at 1 GiB", "One core alone wrote 63.0 GB/s with the same loop."). The sentences are older text. Since this section, line 429 gives 44.8 GB/s for one core with the other loop, and the two lines looked like a contradiction.',
    "- Line 52: the order of the clauses in the definition of the SLC (section 10.1).",
    '- Line 49, two edits. The long form "system level cache" now stands once. The sub-header now also names the other changes of 2026-11-12: the new sub-heading with its listings, the label "3 loads / 2 stores", and the three corrections in "Open items".',
    '- Lines 131 and 132, five edits in the new sub-section. "This loop is the C function" became "The read loop compiled from C is the function". The list "Which build was read" got its item on the asm loop (section 10.2). The first item of "How the loop is counted" now starts with the way of counting. The last row label of the limits table is now "Dispatch: operations for 3 groups of integer and branch pipelines (3 limits)". "For the last two rows of the table this holds on average (est.)." became "The rates of the loop in the last two rows of the table are estimates (est.).".',
])

# ---------------------------------------------------------------- 10.5
# RC10
sub(573, "The mesh manual names", "The TRM names")
sub(573, "A web search result says that PCIe 6.0 has a flit mode too [Ref36].",
    "It also names a 256 B flit format for connections to a PCIe controller [Ref3, page 27]. PCIe is Peripheral Component Interconnect Express, a standard for links to devices. A web search result says that PCIe 6.0 has a flit mode too [Ref36]. That page was not opened.")
# RC9
sub(578, "[Ref5][Ref24]. Three counters give 0.83 for the share of the lines that cross the port.",
    "[Ref5][Ref6][Ref24]. Three counters give 0.83 for the share of the lines that cross the port [Ref5][Ref24][Ref29].")
sub(579, "64.1 to 64.9 GB/s at the port (est.).",
    "64.1 to 64.9 GB/s at the port (est.) [Ref10][Ref31]. The share was counted on 2026-11-02 with the asm loop and one busy core. The pair rates are from 2026-10-30, and all but one of them are from the read loop compiled from C.")
# X-2 of the record check
sub(579, "No run counted the share with only two partner cores busy.",
    "A counter run of 2026-10-30 gave a share of 0.81 (est., from scaled counts) [Ref28]. With that share the pair rates are 62.9 to 63.7 GB/s at the port (est.). No run counted the share with only two partner cores busy.")
# RC9
sub(580, "- Where every line must cross the port, the pair rate at the loops is itself close to 64 GB/s. Two partner writers with 1 GiB each write 63.2 GB/s together [Ref10].",
    "- With a buffer of 1 GiB every line that a writer writes must leave the core. One asm writer alone sends 2.00 bus writes per 64 B line [Ref5][Ref24]. If one bus write is one data flit of 32 B, the rate at the loops is also the rate at the port (est.). Two partner writers with 1 GiB each write 63.2 GB/s together [Ref10]. No run counted the bus writes of two partner writers at 1 GiB.")
after(580, "- With a buffer of 1 GiB every line", [
    "- Writes at 8 MiB with the asm loop. Two partner writers write 81.4 to 82.3 GB/s together at the loops [Ref5][Ref10]. One writer alone sends 1.52 bus writes per line, not 2, for a reason that is not known [Ref24]. With that count the pair rate is 62.0 to 62.7 GB/s at the port (est.). In the pair run only CPU 2 was counted.",
])
sub(581, "That is 0.97 to 1.01 of 64 GB/s.", "That is 0.97 to 1.01 of 64 GB/s (est.).")
after(581, "- At the loops the pair rate differs", [
    "- One more pair test cannot be converted. With the write loop compiled from C two partner writers write 75.6 GB/s at 8 MiB [Ref31]. No bus count exists for that loop. So this rate was not checked against the hypothesis.",
])
# RC20
sub(582, "A rate close to 64 GB/s also fits a port with a higher maximum that something else holds near that rate.",
    "A rate close to 64 GB/s also fits a port with a higher maximum, if something else limits the rate to about 64 GB/s.")

# ---------------------------------------------------------------- 10.6
# RC27
sub(600, "Sources: [Ref10], [Ref31], [Ref5], [Ref29], [Ref34].",
    'Sources: [Ref10], [Ref31], [Ref5], [Ref29], [Ref34]. One sentence of P2 differs from the text that the first run checked: "with only two partner cores busy" follows the correction of section 10.4.')
# RC14
whole(606, "Sources: [Ref5], [Ref10], [Ref24].",
      "Sources: [Ref5], [Ref10], [Ref24]. In the raw file of [Ref5] the counts of case w8M-c2 are at lines 82 and 91 (data stalls of the home nodes of mesh 0), lines 98 to 101 and 108 to 111 (data flits on the four links) and lines 118 to 121 and 128 to 131 (credit-stall cycles on the four links).")
# RC13
sub(612, 'already reaches the rate of the pair (63.2 GB/s)."',
    'already reaches the rate of the pair (63.2 GB/s) [sudo-20261102T211150Z/writepath.csv, followup-20261030T194205Z/asm.csv]."')

# ---------------------------------------------------------------- 10.7
# RC15
sub(618, "59 ids (one new, none removed, none twice) and 39 link targets, all present.",
    "59 ids (one new, none removed, none twice). 39 href attributes: 38 links inside the page, whose targets are all present, and the link to the font stylesheet. One link is new.")
sub(618, "The style block has one new rule (line 35)", "The style block has two new rules, both on line 35")
# RC29
sub(622, "An unchanged copy of the generator rebuilt the old brief byte for byte, apart from the date.",
    "A copy of the old generator, changed only in its output path, rebuilt the old brief byte for byte, apart from the date. A copy of the new generator, changed in the same way, rebuilds the brief as it is now byte for byte (second check).")
# RC2
sub(623, "The first figure was also rendered with cairosvg and viewed.",
    'The first figure was rendered with cairosvg at 20:02 UTC and viewed. That was after the rename and before the label of the Core box changed, so that render shows "3 loads + 2 stores" (`figure-after-slc-rename.png` in the scratch folder of this section). The second check rendered the final figure again, with the headless browser and with cairosvg. Both renders show "3 loads / 2 stores" inside its box, and nothing overlaps (`agents2/record-section-10/fig-first.png` and `agents2/skeptic-record-section-10/figure-now-cairosvg.png` in the same folder).')
# RC16, RC20
sub(624, "Applied: every finding about text that this section wrote. Not applied: the findings about older text. They are items F22 to F34 of section 6.",
    'Applied: every finding about text that this section wrote, and two findings about older wording in sentences that the rename edited (the plural at report line 297 and the citation at line 139). Not applied: the other findings about older text. They are items F22 to F33 of section 6. F34 is not a finding of the checkers. It comes from the browser render of this section. Two notes with an optional change are neither applied nor listed: both name the words "mesh and pair port" in the sub-header at report line 49.')
sub(624, "are worked into sections 10.5 and 10.6", "are applied in the texts of sections 10.5 and 10.6")
# the second check and the state after it
after(625, "| What the first run changed in my own work |", [
    "| Check of 2026-11-12, second run: two checkers (the 26 report lines that changed after the state of the rename check, and the new text of this record), each followed by a second checker that tried to refute every finding | 45 findings: 2 major, 26 minor and 17 notes. The second checkers confirmed 35, confirmed 10 in part and rejected none. They added 7 findings of their own. Both major findings are about this record: the sentence count of section 10.2 and the scope of the cairosvg render. Applied to the report: 13 edits (section 10.4). Applied to this record: every finding about it. Not applied: the overflow in a narrow window, which is older text and now item F35, and the side effect of the author's two row labels (section 10.2) |",
    '| What the second run changed in my own work | The sentence count of section 10.2 said 60 and 47. A recount gives 57 and 44 for the state that the checkers read. The script of the first count was not kept. The row on the cairosvg render did not say that the render was older than the change of the Core label. A new sentence at report line 425 gave the range of all 2 s runs as the rate of the runs that gave the counts, and it named "each pair", which the files do not record. A new sentence at line 429 left out one of the four write rates of the loop compiled from C. The answer on 80 GB/s against 64 GB/s in section 10.5 left out the second share (0.81) and the conversion of the writes at 8 MiB |',
    "| Checks after the corrections of the second run | Structure of the report by script: 978 lines, 0 tag mismatches, 59 ids, 39 href attributes with all 38 targets inside the page present. Figure geometry: PASS. The three listings equal their sources. Render with the headless browser: no script error, and the 20 figures hold the same number of elements as before the corrections. The changed sub-section was rendered and viewed (`check2/final/part-section.2.png` and `part-section.3.png` in the scratch folder): no row of the limits table wraps. The numbers of the new sentences were compared with the raw rows (lines 601 and 610 of both files of [Ref32], line 232 of [Ref31]). No checker read these corrections |",
])
# Not done
sub(631, "The listings were not viewed in IBM Plex Mono.", "The listings were not viewed in IBM Plex Mono, the monospace font of the page.")
sub(633, "P1 to P3 and F1 to F34 are not applied.", "P1 to P3 and F1 to F35 are not applied.")
after(633, "- P1 to P3 and F1 to F35", [
    "- No checker read the corrections that followed the second check (13 edits of the report, and the edits of this record). They were checked by script and by one render (section 10.7).",
])

# ---------------------------------------------------------------- References
# RC11
sub(639, 'Page 2120, Table A-2: "Data_Width N Fixed to 256".',
    'Page 2120, Table A-2: "Data_Width N Fixed to 256". Pages cited in section 10.5 and in "Words used here". Page 12: CMN S3 is a "CHI interconnect". Page 17: the grid connects "CHI-compliant devices". Page 27: "programmable 256B flit support for PCIe controller/PHY connections". Page 51: "Each XP supports four CHI channels for transporting flits across the mesh". Page 250: "CXL IDE can be enabled for both 68B and 256B flit formats". Page 391: the home-node event that "Counts number of times HN-F has a pending TXDAT flit but no credits to upload". Page 621: "All 256B Flit mode-capable components shall set this bit to 1." Page 1679 also: "TX flit stall; signaled when flit transmission is stalled and waiting on credits".')
# follows report edit RE1
sub(668, "Lines 601 and 610: bytes of the 0.2 s run and of the 2 s run.",
    "Lines 601 and 610: bytes of the 0.2 s run and of the 2 s run, and the rate of the four readers together (126.04 and 126.00 GB/s in the first file, 126.13 and 126.23 GB/s in the second). These are the runs that gave the counts. The files hold no rate per thread or per pair for them, only the slowest, the fastest and the average thread.")
# RC29
sub(671, "with the page font IBM Plex Sans from", "with a copy of the page font IBM Plex Sans from")
# new reference for report edit RE11
after(672, "- [Ref36]", [
    "- [Ref37] `bench/README.md` lines 33 to 35, file time 2026-10-30 19:33 UTC: \"Each iteration moves 256 B with eight `ldp`/`stp` instructions on 16 B q registers, then one add, one compare and one branch.\" The source copy of the same minute [Ref22] holds no line with \"asm\", so it is older than the asm loops. `crb/results/followup-20261030T194205Z/asm.csv` line 7: 132.67 GB/s for one asm reader at 32 KiB, measured at 19:42 UTC. `bench/bandwidth.c` has the file time 2026-11-02 04:20 UTC and the sha256 that [Ref8] records for the source on CRB. A checker searched `~/workspace` and `~/tmp` and found no other copy of the source from 2026-10-30.",
])

# ---------------------------------------------------------------- apply the insertions, bottom up
for n, new_lines in sorted(inserts, key=lambda t: -t[0]):
    for s in new_lines:
        assert "\n" not in s
    L[n:n] = new_lines

text = "\n".join(L)
assert "REPORT_SHA256" not in text
assert text.endswith("\n")
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write(text)
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits in place, "
      f"{sum(len(x[1]) for x in inserts)} new lines, {len(L) - 1} lines")
