#!/usr/bin/env python3
"""Record of the third pass of 2026-11-12: the findings of the check of the second pass
(check4) on the record, and what the third pass changed in the report and in the brief.
Edits before section 11 stay on their line, so the line numbers of sections 1 to 10 do
not move. Inside section 11 lines are added.
Usage: apply_record_p2.py <record.md> [--write]"""
import hashlib, sys

P = sys.argv[1]
CRB = "/home/jhan/workspace/titan/cache-perf/crb"
EVID = CRB + "/tmp/agent-scratch/apply-p1-p3-2026-11-12"
L = open(P, encoding="utf-8").read().split("\n")
assert L[-1] == ""
n_edits = 0
SHA_OLD_REPORT = "73117f7a580d7d936d022e2ce8811499db174fec0624aa49bea3a9b8e9801f2e"
SHA_OLD_BRIEF = "c49ea9a61e7a1c16028c8d885097579e65ac5c304e346829d8ca8b2a3aef9277"


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def differ(a, b):
    A = open(a, encoding="utf-8").read().split("\n"); B = open(b, encoding="utf-8").read().split("\n")
    assert len(A) == len(B), (a, len(A), len(B))
    return [i + 1 for i, (x, y) in enumerate(zip(A, B)) if x != y]


def find(prefix):
    hits = [i + 1 for i, l in enumerate(L) if l.startswith(prefix)]
    assert len(hits) == 1, (prefix, hits)
    return hits[0]


def find11(prefix):
    """the same inside section 11 (section 10.7 has rows with the same labels)"""
    hits = [i + 1 for i, l in enumerate(L) if l.startswith(prefix) and i + 1 > S11]
    assert len(hits) == 1, (prefix, hits)
    return hits[0]


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


def insert_after(n, new_lines):
    global n_edits
    L[n:n] = new_lines
    n_edits += 1


SHA_REPORT = sha(CRB + "/crb-memory-hierarchy.html")
SHA_BRIEF = sha(CRB + "/crb-memory-hierarchy-brief.html")
D_REPORT = differ(EVID + "/report.before.html", CRB + "/crb-memory-hierarchy.html")
D_PASS3 = differ(EVID + "/report.check4-state.html", CRB + "/crb-memory-hierarchy.html")
D_BRIEF = differ(EVID + "/brief.before.html", CRB + "/crb-memory-hierarchy-brief.html")
D_GEN = differ(EVID + "/make-brief.before.py", CRB + "/make-brief.py")
assert D_PASS3 == [49, 121, 213, 289, 429, 451] and len(D_REPORT) == 29, (D_PASS3, D_REPORT)
assert D_GEN == [166, 180, 181] and D_BRIEF == [25, 39, 40], (D_GEN, D_BRIEF)
assert differ(EVID + "/brief.check4-state.html", CRB + "/crb-memory-hierarchy-brief.html") == [40]
assert sha(EVID + "/report.check4-state.html") == SHA_OLD_REPORT and SHA_REPORT != SHA_OLD_REPORT

# ================= sections 1 to 10: edits in place =================
# ---- Short version (record-19): P1 to P3 are defined only in section 10.6
sub(7, "and the replacement texts P1 to P3 (section 11).",
    "and new texts for three older statements of the report (texts P1 to P3, section 11).")

# ---- section 1, files: the state after section 11
n = find("| `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html` |")
sub(n, f"The state after section 11 has the sha256 `{SHA_OLD_REPORT}` |", f"The state after section 11 has the sha256 `{SHA_REPORT}` |")

# ---- section 6 (record-10, record-11): not every row was closed with its proposed text, and F26 is applied for one line
n = find("These are outside the request. Each has a proposed correction.")
sub(n, "Section 11 then applied ten items in full (F2, F3, F4, F5, F14, F16, F30, F31, F32 and F33) and F15 for line 110. "
       "Their rows are marked \"applied\". All other items are still open.",
    "Section 11 then closed ten items (F2, F3, F4, F5, F14, F16, F30, F31, F32 and F33), F15 for line 110 and F26 for line 437. "
    "Their rows are marked \"applied\". The text in the report is not always the proposed text of the row. F4: the sentence was dropped "
    "with the old statement. F14 and F16: section 11.5 gives the new texts. F30: section 11.6 says what differs from the text of "
    "section 10.6. F33: section 11.4 gives the new text. All other items are still open.")
n = find("| F26 |")
sub(n, "| F26 |", "| F26 (applied for line 437, section 11.3. Line 63 and the other eight references are open) |")

# ================= section 11 =================
S11 = find("## 11. The author's three requests after section 10 (2026-11-12)")
assert S11 == 677, S11   # sections 1 to 10 did not move

# ---- the table of the files
n = find11("| `crb/crb-memory-hierarchy.html` | 978 lines, as before. 28 lines differ from the state of section 10:")
L[n - 1] = ("| `crb/crb-memory-hierarchy.html` | 978 lines, as before. " + f"{len(D_REPORT)} lines differ from the state of section 10: "
            + ", ".join(map(str, D_REPORT)) + f". sha256 `{SHA_REPORT}` |")
n_edits += 1
n = find11("| `crb/crb-memory-hierarchy-brief.html` | The brief, built again.")
sub(n, f"sha256 `{SHA_OLD_BRIEF}` |", f"sha256 `{SHA_BRIEF}` |")
n = find11("| `crb/tmp/agent-scratch/apply-p1-p3-2026-11-12/` | Scratch folder of this section [Ref38].")
sub(n, "copies of the state that the check of section 11.7 read (`report.check3-state.html`, `brief.check3-state.html`, "
       "`make-brief.check3-state.py`)",
    "copies of the state that the check of the first pass read (`report.check3-state.html`, `brief.check3-state.html`, "
    "`make-brief.check3-state.py`), copies of the state that the check of the second pass read (`report.check4-state.html`, "
    "`brief.check4-state.html`, `make-brief.check4-state.py`, `record.check4-state.md`)")

# ---- the passes (record-X1): the lines of the second pass were not named
n = find11("The edits were made in two passes.")
L[n - 1] = ("The edits were made in three passes. The first pass made 34 edits on 28 lines (`apply_report_p.py`). The check of the first pass "
            "read that state (section 11.7). The second pass made 37 edits on 15 of these lines (`apply_report_p_fixes.py`): 49, 52, 110, 118, "
            "121, 179, 206, 213, 266, 278, 289, 380, 437, 451 and 462. The check of the second pass read that state, which has the sha256 "
            f"`{SHA_OLD_REPORT}`. The third pass made 15 edits on 6 lines (`apply_report_p_fixes2.py`): 49, 121, 213, 289, 429 and 451. "
            "Line 429 is the only line that the first two passes had not changed. No checker read the third pass.")
n_edits += 1

# ---- the second session (record-X5): its draft changes more lines than it announced
n = find11("A second session of the author works on the report after this section.")
sub(n, "each on its physical line. The sha256 in the table",
    "each on its physical line. Its draft of 18:13 on 2026-11-12 changes more lines: 49, 232, 233, 253, 356, 440, 442, 488, 502 to 504, "
    "508, 779, 780 and 889. It does not change line 505. Line 49 is the sub-header, which this section changed too. The draft adds its "
    "own sentences at the end of that line. None of its other lines is a line of this section. The sha256 in the table")

# ---- words of this section (record-13)
n = find11("The author read the answers of section 10.5 and sent three requests.")
assert L[n] == "" and L[n + 1].startswith("The requests, in the author's words:")
insert_after(n + 1, [   # after the blank line that follows the paragraph
    "Words used in this section:",
    "",
    "- **First pass, second pass, third pass**: the three rounds of edits of this section. A check by checkers followed the first pass and "
    "the second pass (section 11.7).",
    "- **Latency fit, pair test**: the report's two timing tests for the shared port. The latency fit puts each CPU on the crosspoint that "
    "best matches its measured latency to every slice of the SLC. The pair test ran two readers with a buffer of 8 MiB each on chosen "
    "pairs of CPUs.",
    "- **Mesh map**: the map of the nodes and ports of each mesh, as the Linux mesh driver prints it. The copy is `crb/results/cmn-map.txt`.",
    "- **CAL2**: the two-device version of Arm's Component Aggregation Layer (CAL). A CAL lets several devices share one port of a crosspoint.",
    "- **Physical line**: one line of the report file, as a text editor counts it. One physical line can hold several paragraphs, tables "
    "and lists.",
    "",
])

# ---- 11.1: the entry of the third pass
n = find11("- The entry \"pair port\" (line 462) is now \"pair port, partner cores\".")
insert_after(n, [
    "- The third pass added one more entry on line 451: \"streaming write\". The term stands in report lines 268, 289, 324 and 974, and the "
    "list did not hold it. The entry says \"A write whose line is not allocated in L1 or L2.\" It gives the count of part 5 and names the "
    "section on one writer with its full heading.",
])

# ---- 11.2
n = find11("| Sub-header of the report | 49 |")
sub(n, "New sentences name the changes of this section |",
    "New sentences name the changes of this section. Since the third pass they also name the entry \"flit\", which was the first request |")
n = find11("- **Why it is lower than the measured ~80 GB/s.**")
sub(n, "For one core alone both places were measured in one run: 71 GB/s at the loop and 58.7 GB/s on the port.",
    "For one core alone both places were measured in one pair of runs (0.2 s and 2 s) of one counter set: 71 GB/s at the loop and "
    "58.7 GB/s on the port.")
n = find11("- **Limits of the estimate.**")
sub(n, "They say that the split of 83 % and 17 % was counted with one busy core and with the asm loop, that a share of 81 % (est.) gives "
       "62.9 to 63.7 GB/s, and that four of the five read rates are from the read loop compiled from C. They name the runs of two partner "
       "cores that were not converted: the write runs of the loop compiled from C and the copy runs. They say that the rates fit the "
       "estimate and do not prove it, and which two tests are missing.",
    "They give three limitations of the read row. The split of 83 % and 17 % was counted with one busy core and with the asm loop. A share "
    "of 81 % (est.) gives 62.9 to 63.7 GB/s at the port (est.). Four of the five read rates are from the read loop compiled from C. The "
    "lists also name the runs of two partner cores at 8 MiB or 1 GiB that were not converted. They are the write runs of the loop compiled "
    "from C, the copy runs of both loops and the read runs at 1 GiB. The lists say that the rates fit the estimate and do not prove it. They name the "
    "two tests that are missing.")
n = find11("Every rate and count of this text is in \"Open items\" of the report already")
L[n - 1] = ("Every measured rate and count that the first two passes wrote into this text was in \"Open items\" of the report already (lines "
            "418 to 435), with its source. The third pass added two kinds of run to the list of the runs that were not converted, at line 121 "
            "and at line 429. The first kind is the copy runs of the loop compiled from C. Their rates are new in the report: 77.9 GB/s at "
            "8 MiB and 72.4 GB/s at 1 GiB [Ref31]. The second kind is the read runs at 1 GiB. Their rates are in the table of line 380 "
            "(52.6 and 56.7 GB/s). Three derived values are new in the "
            "report. The first is \"about 13.5 GB/s\" for the part from the cores' own L2. It is the measured 77.5 to 78.5 GB/s minus the "
            "converted 64.1 to 64.9 GB/s (est.). The second is \"62.0 to 62.7 GB/s\" at the port for the writes at 8 MiB (est.). It is 81.41 "
            "and 82.34 GB/s at the loops times 1.524 bus writes per line, divided by 2 [Ref5][Ref10][Ref24]. The third is the share of this "
            "rate in 64 GB/s, \"0.97 to 0.98\" (est.). \"Open items\" gives the same comparison the other way round: 64 GB/s on the port "
            "allows 84 GB/s at the loops (line 426).")
n_edits += 1
# ---- record-2: the recommendation was in a chat answer, and section D1 had proposed another label
n = find11("What the label does not say.")
sub(n, "My recommendation in section 10.5 was to keep \"unknown\". The author decided for the number.",
    "In my chat answer of 2026-11-12 I recommended to keep \"unknown\". That recommendation is not in this record. Section D1 had proposed "
    "a label that starts with the word \"hypothesis\" and gives the same 64 GB/s. The author chose the label \"estimated 64 GB/s\".")

# ---- 11.3 (record-7, record-12, record-5, record-15, and the texts of the third pass)
n = find11("| P2 (reads at 8 MiB) | 214 |")
sub(n, "A bold lead sentence, a table of five rows", "A bold lead sentence, a paragraph that names the runs and the sources, a table of five rows")
n = find11("| P1 (1 GiB on a pair) | 380 |")
sub(n, "A bold lead sentence, a table of four rows", "A bold lead sentence, a paragraph that names the runs and the sources, a table of four rows")
n = find11("- **P2, line 214.**")
sub(n, "One sentence is reworded: \"With two busy pairs (CPUs 0 to 3) the four threads together read 0.82 to 0.83 of two times the rate of "
       "one pair.\" Its two rates are in the table.",
    "Three sentences are reworded. The first is \"With two busy pairs (CPUs 0 to 3) the four threads together read 0.82 to 0.83 of two "
    "times the rate of one pair.\" Its two rates are in the table. The second is the paragraph before the table: \"The rates in the table "
    "are for a buffer of 8 MiB for each thread. They were measured on 2026-10-30 with no other busy core\". It joins the second and the "
    "eighth sentence of P2. The third is \"The cause of the difference from the 66.9 to 67.5 GB/s of 2026-10-30 is not known.\" P2 said "
    "\"The cause of that difference is not known.\" Two sentences are new: \"What limits a pair was not measured.\" after the bold lead, "
    "and \"Each rate is the best repetition of its run.\"")
n = find11("- **P1, line 380.**")
sub(n, "One table row is new: \"Write, loop compiled from C: 44.8 GB/s alone, 63.2 GB/s for two partner cores, the second core adds "
       "18.4 GB/s (41 %)\".",
    "One table row is new. Its cells are \"Write, loop compiled from C\", \"44.8 GB/s\" (one core alone), \"63.2 GB/s\" (two partner cores "
    "together) and \"18.4 GB/s (41 %)\" (the second core adds).")
sub(n, "The item \"Withdrawn\" says that no run tested the earlier reason.",
    "\"All rates are from 2026-10-30.\" became \"The table is for a buffer of 1 GiB for each core. All its rates are from 2026-10-30.\" One "
    "list item is new: \"The percentage in the last column is the share of the rate of one core alone.\" The last two sentences of P1 "
    "became \"Earlier versions of this report said that DRAM latency limits each core first. No run tested it. That reason is withdrawn.\"")
n = find11("- **P3, line 289.**")
sub(n, "This text has the most changes. All of them come from the check of section 11.7.",
    "This text has the most changes. One was made in the first pass, before the first check: the rates by writer. The raw file holds the "
    "slowest and the fastest thread of each run, and P3 gave one value. All other changes come from the two checks of section 11.7.")
n = find11("  - The second sentence said \"so Arm's write-streaming behaviour is confirmed by measurement\".")
sub(n, "(table above). This report calls such writes streaming writes.\"", "(first table of this section). This report calls such writes "
                                                                           "streaming writes.\"")
n = find11("  - A new first item names the loop:")
L[n - 1] = ("  - A new first item names the loop: \"The rates in this list are from the asm write loop, except where a sentence names the loop "
            "compiled from C. With the write loop compiled from C one writer alone wrote 44.8 GB/s at 8 MiB and at 1 GiB (CPU 0, "
            "2026-10-30)\". The item gives the file of the main sweep as its source [Ref31].")
n_edits += 1
n = find11("  - The range 70.4 to 73.2 GB/s now names its runs:")
sub(n, "The item says that all rates of part 5 in the list are from the runs of 2 s.",
    "The item says that the other write rates of part 5 in the list are also from the runs of 2 s. It also says how a count per second of "
    "part 5 is made: the count of the 2 s run minus the count of the 0.2 s run, divided by the difference of the two counting times.")
n = find11("  - P3 said \"With a second busy port each writer falls from 71 to 61 GB/s.")
sub(n, "gives the rates by writer: between 60 and 61 GB/s for each of CPUs 2 and 4,", "gives the rates by writer: 60.15 to 61.34 GB/s for "
                                                                                      "each of CPUs 2 and 4,")
sub(n, "It adds \"No run measured CPU 4, 6 or 8 alone. So the fall is measured for CPU 2 only.\"",
    "It adds \"No run measured CPU 4, 6 or 8 writing alone. So the fall is measured for CPU 2 only.\"")
L[n - 1] += (" \"Four writers on four ports write 228 to 230 GB/s.\" became \"Four writers on four ports (CPUs 2, 4, 6 and 8) wrote 228 to "
             "230 GB/s.\"")
n = find11("  - Four sentences on the counters of these runs are new.")
sub(n, "With four busy ports that is 0.005 data stalls per line written.",
    "With four busy ports the home nodes of mesh 0 show 0.005 data stalls per line written.")
n = find11("  - The item on 1 GiB now names the asm loop for its three rates,")
insert_after(n, [
    "- **All three texts.** Eight sources in square brackets were added: two at line 214, four at line 289 and two at line 380.",
])
n = find11("The open item at line 437 listed the three old statements as current text.")
sub(n, "It quotes each old statement and names the section with the new text.",
    "It quotes each old statement and names the section with the new text. For the section on one writer it now quotes the full heading. "
    "That is one of the nine references of row F26.")

# ---- 11.4 (record-8): two of the rows are not places that section 10.6 named
n = find11("### 11.4 Places that section 10.6 named")
L[n - 1] = "### 11.4 Places that section 10.6 named, and two more rows of section 6"
n_edits += 1
n = find11("Section 10.6 listed the places that change with the three texts. They are changed.")
L[n - 1] = ("Section 10.6 listed the places that change with the three texts: line 437 (see section 11.3), rows F3, F33 and F2, and the brief "
            "(row F30). They are changed. Two more rows of section 6 were applied with them. Section 10.6 did not name them: row F15 for "
            "line 110 and row F31 at line 278.")
n_edits += 1

# ---- 11.5
n = find11("Changed because of the search. Each row is a sentence that section 10.6 did not name.")
sub(n, "The column \"Now\" gives the text after the check of section 11.7:", "The column \"Now\" gives the text after the third pass:")
n = find11("| 52 | \"each pair of neighbouring cores shares one path to the mesh of about 80 GB/s\"")
sub(n, "This is the first old statement in other words.", "This is the old statement that P2 replaces, in other words.")
n = find11("| 206 | \"cores 2k and 2k+1 running together share one 78 GB/s limit\"")
sub(n, "It ends with \"For these three pairs the pair test fits two cores on one port. It does not show what limits the pair.\" |",
    "Its new text ends with \"For these three pairs the pair test fits two cores on one port. It does not show what limits the pair.\" "
    "The older words \"Not read from hardware\" still close the cell |")
n = find11("| 213 | \"a port serving one busy core and one idle core gives the busy core its full 67 GB/s\"")
sub(n, "read 62.4 to 67.1 GB/s (seven runs). A core with a busy partner read 37.8 to 40.3 GB/s (five runs).\"",
    "read 62.4 to 67.1 GB/s (seven runs, best repetition of each). A core with a busy partner read 37.8 to 40.3 GB/s (five runs, best "
    "repetition of each).\"")
sub(n, "The rates by thread are from the best repetition of each run [Ref10][Ref31][Ref34] |",
    "The rates by thread stand in the row of the best repetition of each run [Ref34]. Over all 15 repetitions of the seven runs such a core "
    "read 61.3 to 67.1 GB/s. The second range holds for all 12 repetitions of its five runs |")
n = find11("| 266 | \"From the SLC and DRAM the two loops agree, so there the limit is outside the core.\"")
sub(n, "| A list with the read and write rates of both loops. It ends with \"These rates do not show where the limit of one core is.\" The "
       "older sentence on the mesh counters (81 % and 19 %) stands unchanged as the last item of that list |",
    "| A list with the items \"Reads from the SLC\", \"Reads from DRAM\" and \"Writes\". The text is not the proposed text of row F14. It "
    "gives 67.0 and 67.5 GB/s for the two read loops at 8 MiB. Row F14 gave 67.0 and 66.9 GB/s. Both asm rates are runs of 2026-10-30 on "
    "CPU 0 [Ref10][Ref34], and the chart above the text shows 67.5 GB/s. The two sentences of row F14 on one loop pass per cycle were not "
    "applied. One sentence is new: \"So its rate at 8 MiB can be the limit of the loop itself\". The new text ends with \"These rates do "
    "not show where the limit of one core is.\" The older sentence on the mesh counters (81 % and 19 %) stands unchanged as the last item "
    "of that list |")
# record-17: a list, and the two changes of the word list that came from the search
n = find11("The search also confirmed or sharpened texts that were planned anyway:")
L[n - 1:n] = [
    "The search also confirmed texts that were planned before it, or made them more exact:",
    "",
    "- the figure label for screen readers (line 77)",
    "- the two text lines of the Spec box (line 92)",
    "- the caption (line 97)",
    "- the paragraph at line 101",
    "- the row at line 118",
    "- the open item at line 437",
    "- the entry \"flit\" of the word list (line 451)",
    "",
    "Two changes of the word list were not planned. They come from the search: the entries for credit stall, data stall, back-pressure and "
    "write in flight (line 451) and the new text of the entry \"pair port\" (line 462).",
]
n_edits += 1
# record-9: the totals of the DRAM chart
n = find11("| Line 367 | The caption of the DRAM chart says")
sub(n, "With 16, 32 and 64 threads the totals agree within 1 % |",
    "With 16, 32 and 64 threads the read totals and the write totals agree within 1 %. The copy totals differ by 1.7 % at 16 threads and by "
    "1.1 % at 64 threads. With 96 and 120 threads the loops do not agree. Write at 96 threads gives 174.0 GB/s with the loop compiled from C "
    "and 149.5 GB/s with the asm loop. Read at 120 threads gives 368.3 and 307.6 GB/s [Ref31][Ref34] |")

# ---- 11.6: the brief after the third pass
n = find11("- **Line 40 of the brief (generator line 181).**")
sub(n, "\"What limits one writer at 8 MiB (70 to 73 GB/s) was not measured. Its lines are not allocated in L1 or L2 (0 refills, 0 "
       "write-backs).",
    "\"What limits one writer at 8 MiB (70 to 73 GB/s in runs of 0.5 s and 2 s) was not measured. Its lines are not allocated in L1 or L2 "
    "(0.000 refills for writes and at most 0.001 write-backs per line).")
n = find11("- **What differs from section 10.6 at line 40.**")
insert_after(n, [
    "- **Third pass, line 40.** The range 70 to 73 GB/s now names its runs: \"in runs of 0.5 s and 2 s\". The nine runs of 0.2 s of part 5 "
    "gave 68.9 to 70.7 GB/s. \"(0 refills, 0 write-backs)\" became \"(0.000 refills for writes and at most 0.001 write-backs per line)\". "
    "The counts are not zero. With one writer the core counted 10,263 L1 refills for writes and 1,318,307 L2 write-backs for 1.98 × 10^9 "
    "lines [Ref5]. The edit is in `apply_brief_p_fixes2.py` [Ref38].",
])
n = find11("- **Print.** The brief still prints on 2 A4 pages.")
sub(n, "The text of page 1 ends at 705 of 842 points (before this section: 642).",
    "The text of page 1 ends at 705 of 842 points (before this section: 642). A point is 1/72 inch, and an A4 page is 842 points high. The "
    "print was made again after the third pass, with the same result.")

# ---- 11.7
n = find11("| Structure of the report, by script (`structure_check.py`) |")
sub(n, "and the link to the font stylesheet |", "and the link to the font stylesheet. Run again after the third pass, with the same result |")
n = find11("| Figure geometry: `check_geometry.py crb/crb-memory-hierarchy.html 6` |")
sub(n, "keep 9.7 and 15.2 units to the sides of the box |", "keep 9.7 and 15.2 units to the sides of the box. Run again after the third pass |")
# record-1: the renders
n = find11("| Render with the local headless browser, with the network blocked [Ref35] |")
L[n - 1] = ("| Render with the local headless browser, with the network blocked [Ref35] | The report loads with no script error. All 19 figures "
            "that the script draws hold elements. The pair chart has 9 bars. After the third pass the changed sections were rendered again "
            "and viewed. That was at 19:17 on 2026-11-12, after the last write of the report at 19:16. The renders show nine parts. They "
            "are the page head with the Short version (lines 49 and 52), the first figure with its caption, the source table with the new "
            "text under it, and the section \"The SLC (L3) and the pair port\" (lines 178 to 215). They are also \"Bandwidth per core\" "
            "with the part on one writer, the paragraph at line 343, \"The pair finding\", \"Open items\" and \"Words used here\". "
            "These renders are in `render_final/` of the scratch folder. They are part "
            "pages without the page script, so they do not draw the figures that the script draws. The pair chart was rendered apart, from "
            "the page that the browser saved after the script ran (`render_final/pairchart.png`). The screenshots in `render/` are older. "
            "They show the state after the first pass (17:02) |")
n_edits += 1
n = find11("| Brief | Printed after the last edit:")
sub(n, "| Brief | Printed after the last edit:", "| Brief | Printed after the last edit of the third pass (`render_final/brief.final.pdf`):")
# record-3
n = find11("| Check of the first pass: four checkers")
sub(n, "No number of the new text was wrong.",
    "The checkers recomputed the rates and the counts of the new text from the raw files. All agreed, with one exception. Line 213 gave "
    "67 GB/s for a core with an idle partner, and its seven runs give 62.4 to 67.1 GB/s (major finding 3 in the next row). Several ranges "
    "did not name their runs: the rates of part 5 were the rates of the runs of 2 s only (section 11.3).")
# record-X1: the other lines that the first check changed
n = find11("| What the check changed besides |")
sub(n, "One more limit of the read row and the list", "One more limitation of the read row and the list")   # the report's word since the third pass
sub(n, "The brief (section 11.6) |",
    "The brief (section 11.6). The sub-header (line 49) now names the section and the table of the estimate, and it lists the other "
    "corrections of this section. Line 118 says \"The 32 B are from Arm's manual\" (before: \"The flit size is from Arm's manual\"). The "
    "sentence on the marked claims at line 179 (section 11.5). The values for 1 GiB in the cell of line 278 (section 11.4). Two words at "
    "line 380 (section 11.3). The loop and the read test at 1 GiB in the open item of line 437 (section 11.3). The definition of the data "
    "stall at line 451 no longer quotes the abbreviations \"HN-F\" and \"TXDAT\", and it names the \"data-send stall\" of the table of "
    "part 5 |")
n = find11("| Confirmed and not applied |")
sub(n, "Also not applied: the new item for the list \"Open\" of the brief (section 11.6) |",
    "Also not applied: the new item for the list \"Open\" of the brief (section 11.6). From the check of the second pass one optional part "
    "of a note is not applied. It proposed to call the limitation of the read row \"a third assumption\" at lines 121 and 422. The report "
    "says \"one more limitation\" and keeps \"two assumptions\" |")
# record-X3: the narrow window
n = find11("| Narrow window |")
L[n - 1] = ("| Narrow window | In a window of 390 px the page scrolls sideways by 80 px, as before this section (row F35). Two checkers of "
            "the first pass measured a page width of 470 px before this section and after the first pass. A checker of the second pass "
            "measured 470 px after the second pass. After the third pass I measured 470 px again with the same browser |")
n_edits += 1
# record-4: the check of the second pass, what it changed, and what no checker read
insert_after(n, [
    "| Check of the second pass: one checker on the fixes of the second pass (report, brief and generator) and one on section 11 of this "
    "record, each followed by a second checker that tried to refute every finding | Report and brief: 8 findings (3 minor, 5 notes). The "
    "second checker confirmed 7 and confirmed 1 in part, and it added 2 notes. No wrong number, no wrong source and no new contradiction "
    "was found. Record: 22 findings (2 major, 12 minor, 8 notes). The second checker confirmed 19 and confirmed 3 in part, and it added 5 "
    "findings (1 minor, 4 notes). No finding was rejected. The findings and the verdicts are in `check4_results.json` [Ref38] |",
    "| What the check of the second pass changed (the third pass) | Report, 15 edits on 6 lines. Line 49: the change note names the entry "
    "\"flit\" and the new entry \"streaming write\". Line 121: \"one pair of runs (0.2 s and 2 s)\" for the two counts of one core alone, "
    "\"one more limitation\", and the full list of the runs that were not converted. Line 213: \"best repetition of each\" for the two "
    "ranges by thread. Line 289: the scope of the two sentences that started with \"All rates\", the run and the source of the 44.8 GB/s, "
    "\"60.15 to 61.34 GB/s\", \"writing alone\", \"of mesh 0\" for the 0.005, and \"first table of this section\". Line 429: the same two "
    "kinds of run as line 121, so that the two lists agree. Line 451: the entry \"streaming write\". Brief: one edit on generator line 181 "
    "(section 11.6). Record: the two major findings were the row on the renders and the sentence on my recommendation. The row named a "
    "folder that held the screenshots of the first pass. The sentence named section 10.5, and the recommendation was in a chat answer. "
    "All 27 findings on the record are applied in this text |",
    "| After the third pass | The structure check, the geometry check, the page load, the renders and the print of the brief were run "
    "again on the final files (rows above). The script `recheck_third_pass.py` recomputes the numbers of the changed sentences from the "
    "raw files and compares them with the report. All its checks pass. Its output is `recheck_third_pass.out` [Ref38]. No checker read "
    "the third pass or the changes of this record that followed the check of the second pass |",
    "| Seen in the third pass and not changed | Unchanged line 316 says \"zero L1 and L2 refills for writes and zero write-backs\". The "
    "counts are 0.000 per line and at most 0.001 per line, and they are not zero (section 11.6). Unchanged line 428 says \"in that run\" "
    "for the pair of runs that gave the 58.7 GB/s. Both are older text |",
])
hits = [i + 1 for i, l in enumerate(L) if l.startswith("- The reviewer agent of the review loop has not read the changes of this section.")]
assert len(hits) == 2 and hits[0] < S11 < hits[1], hits   # the lists "Not done" of sections 10 and 11
n = hits[1]
insert_after(n, [
    "- No checker read the third pass (15 edits of the report and one edit of the generator) or the changes of this record that followed "
    "the check of the second pass. They were checked by the scripts and the renders of section 11.7 only.",
])

# ================= references =================
n = find("- [Ref5] ")
L[n - 1] = L[n - 1].rstrip() + (
    " Lines 628 and 637: the data stalls of the home nodes of mesh 0 in case w8M-c2c4, in the 0.2 s run and in the 2 s run. Lines 810 and "
    "819: the same counter in case w8M-c2c4c6c8. Lines 846 to 849 and 856 to 859: the credit-stall cycles of the four links in case "
    "w8M-c2c4c6c8. Line 652: the 2 s run of case w8M-c2c4 with the slowest and the fastest writer (60.15 and 61.34 GB/s). Line 797: the "
    "same for case w8M-c2c4c6c8 (55.49 and 58.80 GB/s). Lines 209 and 106: the slowest and the fastest 2 s run of case w8M-c2 (70.37 and "
    "71.34 GB/s). Lines 220 and 96: the slowest and the fastest 0.2 s run of that case (68.93 and 70.65 GB/s). Lines 201 and 212: the L1 "
    "refills for writes of case w8M-c2 (4,431 and 14,694). Lines 183 and 194: its L2 write-backs (182,122 and 1,500,429).")
n_edits += 1
n = find("- [Ref31] ")
L[n - 1] = L[n - 1].rstrip() + (
    " Lines 196 and 236: two partner cores that copy at 8 MiB and at 1 GiB, 77.87 and 72.39 GB/s. Line 121: the best repetition of the run "
    "of two readers at 8 MiB, with the slowest and the fastest thread (37.83 and 40.30 GB/s). Lines 316 and 326: write with 96 threads "
    "(174.02 GB/s) and read with 120 threads (368.25 GB/s), 256 MiB each.")
n_edits += 1
n = find("- [Ref34] ")
L[n - 1] = L[n - 1].rstrip() + (
    " The rates by thread stand in the row of the best repetition of each run. Two cores of different pairs: `pair.csv` lines 11, 17, 23, "
    "35, 41 and 53 (62.35 to 67.09 GB/s) and `asm.csv` line 306 (64.02 and 65.70 GB/s). Two partner cores: `pair.csv` lines 4, 28 and 46, "
    "`asm.csv` lines 71 and 72 (two repetitions with the best total), and line 121 of the file of [Ref31] (37.83 to 40.30 GB/s). `asm.csv` "
    "lines 274 and 285: asm write with 96 threads (149.45 GB/s) and asm read with 120 threads (307.60 GB/s), 256 MiB each.")
n_edits += 1
n = find("- [Ref38] ")
L[n - 1] = (
    "- [Ref38] `crb/tmp/agent-scratch/apply-p1-p3-2026-11-12/`, the scratch folder of section 11. `sweep_results.json`: the 72 findings of "
    "the search of section 11.5, by checker. `check3_results.json`: the findings and the verdicts of the check of the first pass. "
    "`check4_results.json`: the same for the check of the second pass (section 11.7). `apply_report_p.py` with `texts_p.py` and "
    "`apply_brief_p.py`: the edits of the first pass. `apply_report_p_fixes.py` and `apply_brief_p_fixes.py`: the edits of the second "
    "pass. `apply_report_p_fixes2.py` and `apply_brief_p_fixes2.py`: the edits of the third pass. `apply_record_p.py` and "
    "`apply_record_p2.py`: the edits of this record. `record_section11.final.md`: the text of section 11 as it was first written, before "
    "the check of the second pass. `sentences_p.py`: the comparison of the approved texts with the report lines. `structure_check.py`, "
    "`rates.py`, `render_parts.py` and `recheck_third_pass.py` with its output `recheck_third_pass.out`: the check scripts. `render/`: "
    "the screenshots of the state after the first pass, the print of the brief after the second pass (`brief.final.pdf`) and the report of "
    "that state after its script ran, saved as HTML (`report.final.dom.html`). `render_final/`: the same three kinds of file for the state "
    "after the third pass, with the pair chart (`pairchart.png`).")
n_edits += 1

assert find("## 11. The author's three requests after section 10 (2026-11-12)") == 677
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, record now {len(L) - 1} lines; "
      f"report sha256 {SHA_REPORT[:12]}, brief sha256 {SHA_BRIEF[:12]}")
