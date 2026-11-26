#!/usr/bin/env python3
"""Record edits for the reviewer's finding CRB-R5 (round 2). Every old text must occur exactly once."""
import sys
P = "/home/jhan/tmp/update-crb-memory-hierarchy.md"
s = open(P, encoding="utf-8").read()
n_edits = 0

def rep(old, new):
    global s, n_edits
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new); n_edits += 1

# section 1: the digest of the report is filled in after the last edit
rep("978 lines. sha256 `a661b0040b4a1b26fae0638f7fed180eb2a353f49bdd330d8d5e965c81e0fbcf`", "978 lines. sha256 `REPORT_SHA256`")

# section 2: cell lengths
rep("Its longest cell grew from 231 to 706 characters (line 118). The cells at lines 113 (690 characters) and 104 (603 characters) are also long.",
    "Its longest cell grew from 231 to 832 characters (line 113). The cells at lines 118 (706 characters) and 104 (603 characters) are also long.")

# Q1, wording B: the quotation follows the report
rep('"The counters were read in that one run [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv]. It used 40 threads of 3 MiB each [bw-asmread-3M-40T-even.csv in the same folder]. A separate series',
    '"The counters were read in that one run. The value comes from two counters, one for each mesh. Each ran for 49 % of the run, and perf scaled its count to the whole run [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv]. The run used 40 threads of 3 MiB each [bw-asmread-3M-40T-even.csv in the same folder]. A separate series')

# section 5
rep("The phrase of Q1 is replaced by wording A, which names the separate series of runs | Follows from R1 to R8 and from Q1 | 97 |",
    "The phrase of Q1 is replaced by wording A, which names the separate series of runs. The caption marks the 0.62 TB/s as an estimate from scaled counts (section 9) | Follows from R1 to R8 and from Q1 | 97 |")
rep("It keeps the counter run and the series of runs apart, and it cites the file of each | Q1 | 113 |",
    "It keeps the counter run and the series of runs apart, and it cites the file of each. It marks the value as an estimate from scaled counts (section 9) | Q1 | 113 |")

# section 6
rep("54 GB/s from the mesh (line 266, run of 2026-10-30) and 71 GB/s",
    "54 GB/s from the mesh (line 266, run of 2026-10-30, est. from scaled counts, see F21) and 71 GB/s")
rep("| F21 | Lines 52, 86, 97, 113, 266, 302, 320, 330, 336, 343, 396, 534, 959 and 969. Also lines 245 and 251 |",
    "| F21 | Lines 52, 86, 266, 302, 320, 330, 336, 343, 396, 534, 959 and 969. Also lines 245 and 251 |")
rep("Report lines 245 and 251 give values of that pass with no \"est.\" | Mark the values of these lines \"est.\" and add at line 113: \"Each counter ran for about half of this run, and perf (the Linux counter tool) scaled the counts to the whole run.\" At lines 266, 330 and 959",
    "Report lines 245 and 251 give values of that pass with no \"est.\". Lines 97 and 113 held the 0.62 TB/s in the same way. They are corrected (section 9) | Mark the values of these lines \"est.\", as lines 97 and 113 now do. At lines 266, 330 and 959")

# section 7
rep("are unchanged. Checked again after the changes of section 8. The open item",
    "are unchanged. Checked again after the changes of sections 8 and 9. The open item")
rep("all listed in sections 2 and 5. Still 19 after the changes of section 8. Against the round-1 state",
    "all listed in sections 2 and 5. Still 19 after the changes of sections 8 and 9. Against the report of round 2 the diff has 2 hunks, lines 97 and 113 (section 9). Against the round-1 state")
rep("| External review, round 1 of the review loop (reviewer agent, 2026-11-12 00:41 UTC) | 4 findings, CRB-R1 to CRB-R4. All 4 are accepted and applied. Section 8 lists them |",
    "| External review, round 1 of the review loop (reviewer agent, 2026-11-12 00:41 UTC) | 4 findings, CRB-R1 to CRB-R4. All 4 are accepted and applied. Section 8 lists them |\n"
    "| External review, round 2 of the review loop (reviewer agent, 2026-11-12 04:24 UTC) | The reviewer's entry says that CRB-R1 to CRB-R4 are resolved. It holds 1 new finding, CRB-R5. It is accepted and applied. Section 9 lists it. The same entry confirms the two submitted hashes, the hunk counts (9 and 19) and the counts of `port_counts.py` |")

# new section 9, before the references
rep("## References\n", r'''## 9. Changes after the external review, round 2

The reviewer's entry of 2026-11-12 at 04:24 UTC says that CRB-R1 to CRB-R4 are resolved. It holds one new finding. It is accepted. No benchmark was needed.

| Finding | What the reviewer asked | What changed | Where |
|---|---|---|---|
| CRB-R5 | This change revised the caption and the source row of the first figure. Both still gave the 0.62 TB/s with no "est.", and F21 listed both as text outside this change. Mark the value and its reading as a lower bound as estimated in both places. Say that each cache-access counter ran for about half of the run and that perf scaled its count. Do not list the two places as uncorrected in F21 | The caption now says "an estimated lower bound" and "0.62 TB/s (est.)". It adds: "Each of these counters ran for about half of that run, and perf (the Linux counter tool) scaled its count to the whole run." The source row now starts with "From the mesh counters (est.)" and says "An estimated lower bound". It adds: "The value comes from two counters, one for each mesh. Each ran for 49 % of the run, and perf scaled its count to the whole run." F21 no longer lists lines 97 and 113 | Report lines 97 and 113. Record: wording B of Q1, section 2 (cell lengths), C3 and C7 of section 5, F10 and F21 of section 6, section 7 |

How it was checked:

- The two counters are lines 3 and 7 of the counter file of that run. Column 5 of both lines is 49.00 [Ref11].
- The mechanical checks of section 7 were run again after the change. The geometry check prints PASS. The HTML has 0 tag mismatches. The diff has 19 hunks against the backup, 9 against the round-1 report and 2 against the report of round 2 (lines 97 and 113).
- A script confirmed that wording B of Q1 is in report line 113 word for word.
- I searched the text that this change wrote or revised for other values of the scaled counts. Report lines 425 and 433 and this record already mark each such value "est.". One place had no label: F10 of this record named the 54 GB/s of report line 266. It now says that the value is from scaled counts.

Not changed:

- The label "≥0.62 TB/s whole chip" in the figure (line 86), and the first cell of the source row (line 113), which repeats that label. The caption and the second cell of the row now carry the qualification. Line 86 stays in F21.
- The other lines of F21. The reviewer's finding leaves them deferred.

## References
''')

if "--write" in sys.argv: open(P, "w", encoding="utf-8").write(s)
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits")
