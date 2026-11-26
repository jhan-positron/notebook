#!/usr/bin/env python3
"""Record edits after the third internal check. Every old text must occur exactly once."""
import sys
P = "/home/jhan/tmp/update-crb-memory-hierarchy.md"
s = open(P, encoding="utf-8").read()
n_edits = 0

def rep(old, new):
    global s, n_edits
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new); n_edits += 1

def line_starting(prefix, new):
    global s, n_edits
    L = s.split("\n"); hits = [i for i, l in enumerate(L) if l.startswith(prefix)]
    assert len(hits) == 1, (len(hits), prefix)
    L[hits[0]] = new; s = "\n".join(L); n_edits += 1

def block(start, end, new):
    global s, n_edits
    assert s.count(start) == 1, (s.count(start), start[:60])
    i = s.index(start); j = s.index(end, i + len(start))
    s = s[:i] + new + s[j:]; n_edits += 1

# ------------------------------------------------------------ section 2 and Q1
rep("The cells at lines 113 (642 characters) and 104 (603 characters) are also long.",
    "The cells at lines 113 (690 characters) and 104 (603 characters) are also long.")
rep('"The counters were read in that one run. It used 40 threads of 3 MiB each [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv]. A separate series',
    '"The counters were read in that one run [results/uncore2-20261030T203752Z/cmn-asmread-3M-40T-even.csv]. It used 40 threads of 3 MiB each [bw-asmread-3M-40T-even.csv in the same folder]. A separate series')
rep("The mesh-served part (0.62 TB/s) was counted in one separate 40-thread run of the same day (20:37 UTC, total 1,384.8 GB/s).",
    "The mesh-served part (0.62 TB/s, est.) comes from the counters of one separate 40-thread run of the same day (20:37 UTC, total 1,384.8 GB/s). Each of the two counters ran for 49 % of that run, and perf scaled the counts.")
rep("If the run used the CPU list of the series (`0-118:2`), 8 of its 40 threads ran on mesh 1. The per-thread values of the run fit this. The slowest thread read 26.9 GB/s, the fastest 61.9 GB/s, and the average was 34.6 GB/s. 32 threads at the slowest value and 8 at the fastest would average 33.9 GB/s.",
    "If the run used the CPU list of the series (`0-118:2`, which is every second CPU from 0 to 118), its 40 threads ran on the even CPUs from 0 to 78. Then 8 of them ran on mesh 1 (CPUs 64 to 78). The slowest thread of the run read 26.9 GB/s, the fastest 61.9 GB/s, and the average was 34.6 GB/s. The run of 2026-11-02 has a recorded placement, with 32 threads on mesh 0 and 8 on mesh 1. Its fastest repetition gave nearly the same three values: 26.2, 61.6 and 34.3 GB/s. The three values do not show how many threads were fast.")

# ------------------------------------------------------------ Q4
rep("Size of the rename in the report after this update: 92 literal occurrences (86 before this update).",
    "Size of the rename in the report after this update: 93 literal occurrences (86 before this update).")

# ------------------------------------------------------------ D1
rep("The report calls them the tests of hypothesis 2. Hypothesis 1 can hold while a test leaves the port partly idle.",
    "The report calls them the runs of hypothesis 2. Hypothesis 1 can hold while a run leaves the port partly idle.")
rep("One more value of that share, the 0.81, is from a counter run of 2026-10-30 [Ref28]. Its file does not record the CPU. Most pair rates",
    "One more value of that share, the 0.81, is from a counter run of 2026-10-30 [Ref28]. Its file does not record the CPU. The loop read 67.1 GB/s in that run. It read 70.7 to 71.0 GB/s in the runs of the three counts of 0.83 [Ref5][Ref29]. On 2026-10-30 one asm reader alone read 66.9 GB/s in the file of the asm pair rate [Ref10]. Most pair rates")
rep("With 0.83, 64 GB/s on the port allows 77 GB/s. Measured 77.5 to 78.5 GB/s. Converted with 0.83, that is 64.1 to 64.9 GB/s on the port (est.), which is 1.00 to 1.01 flits per mesh cycle.",
    "With 0.83, 64 GB/s on the port allows 77 GB/s (est.). Measured 77.5 GB/s with the asm loop and 77.9 to 78.5 GB/s with the read loop compiled from C. Converted with 0.83, these rates are 64.1 to 64.9 GB/s on the port (est.), which is 1.00 to 1.01 flits per mesh cycle.")
line_starting("| Writers at 1 GiB |",
    "| Writers at 1 GiB | One writer 63.0 GB/s. Two partner writers together 63.2 GB/s. Four writers on two pairs 113 GB/s, which is 56.6 GB/s per pair | The first two rates: hypotheses 1 and 2 together, through the conversion (2.00 bus writes per line, measured on one writer alone). With the first assumption the rate of one writer through the port is 0.98 of 64 GB/s (est.). With both assumptions the rate of two partner writers through the port is 0.99 of 64 GB/s (est.). The run of four writers is not one of the runs of hypothesis 2. It has two busy pairs, and its rate per pair is 0.88 of 64 GB/s (est.). D2 uses this run | [Ref5][Ref10][Ref24] |")
rep("The manual gives no numbering for the field. The report assumes the numbering of the design parameter on TRM page 1678.",
    "The manual does not say which value of the field stands for which number of channels. The report assumes that the field counts the channels in the same way as the design parameter on TRM page 1678.")
rep("Write data goes the other way. For writes, the bus writes of both partner cores must be counted.",
    "Write data goes the other way. For writes, the bus writes of both partner cores must be counted. A reader also sends data the other way (1.653 bus writes per line for one reader). So the read test counts the bus writes of both cores too.")
rep("One count exists for one core of a writing pair: CPU 2 sent 1.52 bus writes per line that it wrote itself.",
    "One count exists for one core of a writing pair: CPU 2 sent 1.52 bus writes per line that it wrote itself. A count of more bus reads than port flits would have two readings. Either the first assumption is wrong, or a second data channel carries flits that the counter does not cover.")
rep("The measured ~80 GB/s in the box above (77.5 to 78.5 GB/s) is higher than 64 GB/s.",
    "The measured ~80 GB/s in the box above (77.5 GB/s with the asm loop, 77.9 to 78.5 GB/s with the read loop compiled from C) is higher than 64 GB/s.")
rep("A share of 0.81 would put all four pair rates below 64 GB/s (est.).",
    "A share of 0.81 would put all four pair rates of the read loops (77.5, 77.9, 78.3 and 78.5 GB/s) below 64 GB/s (est.).")

# ------------------------------------------------------------ D2
rep("At 1 GiB one writer sends 0.98 bus writes per mesh cycle [Ref5]. If hypothesis 1 of D1 and the first assumption of the conversion hold, that is 98 % of the capacity of the port (est.). Whether the port then limits the writer is hypothesis 2.",
    "At 1 GiB one writer sends 1.96 × 10^9 bus writes per second [Ref5]. At the mesh clock of 2.0 GHz that is 0.98 bus writes per mesh cycle (est.). If hypothesis 1 of D1 and the first assumption of the conversion hold, that is 98 % of the capacity of the port (est.). Whether the port then limits the writer is hypothesis 2.\n"
    "- \"For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2\" (line 214). The rates show that two partner readers share one limit of about 78 GB/s. That the full port is this limit is part of hypothesis 2. The 78 GB/s also counts the lines that the two cores take from their own L2.")

# ------------------------------------------------------------ section 5
rep("Line 132 holds three paragraphs on one source line.", "Line 132 holds five paragraphs on one source line.")
rep("Four of its items hold a nested list on one source line (lines 422, 425, 433 and 434)",
    "Six of its items hold a nested list on one source line (lines 422, 425, 433, 434, 435 and 437). Line 429 holds two items")
rep("The entry \"compiled loop, asm loop\" says what \"compiled\" means and what the three compiled loops are.",
    "Line 452 also holds a second entry, \"bus reads in part 5\". The entry \"compiled loop, asm loop\" says what \"compiled\" means and what the three compiled loops are.")

# ------------------------------------------------------------ section 6
rep("The 0.62 TB/s is what the mesh cache delivered in one run, so the cache can deliver at least that.\" Line 343, in place of the last sentence:",
    "The 0.62 TB/s is what the mesh cache delivered in one run (est.). Each counter ran for about half of that run, and the counts were scaled to the whole run. So the cache can deliver about 0.62 TB/s or more (est.).\" Line 343, in place of the last sentence:")
rep("The 0.62 TB/s is what the mesh cache delivered in this one run, so the cache can deliver at least that. A separate series",
    "The 0.62 TB/s is what the mesh cache delivered in this one run (est., from counters that ran for about half of the run). So the cache can deliver about 0.62 TB/s or more (est.). A separate series")
rep("| F21 | Lines 52, 86, 97, 113, 266, 302, 320, 330, 336, 343, 396, 959 and 969 |",
    "| F21 | Lines 52, 86, 97, 113, 266, 302, 320, 330, 336, 343, 396, 534, 959 and 969. Also lines 245 and 251 |")
rep("It gives 0.83, and the report has it at lines 232 and 268 [Ref29]. No count over the whole run exists for the 40-thread test |",
    "It gives 0.83, and the report has it at lines 232, 268, 308 and 312 [Ref29]. No count over the whole run exists for the 40-thread test. The first counter pass of the same day (`crb/results/uncore-20261030T203537Z/`) has the same property: 352 of its 354 counter rows ran for less than the whole run, most of them for 28 %. Report lines 245 and 251 give values of that pass with no \"est.\" |")

# ------------------------------------------------------------ section 7
rep("All 58 ids and all 38 links are unchanged.",
    "All 58 ids and all 38 href attributes (37 links in the page and the link to the font stylesheet) are unchanged.")
rep("1.5236 bus writes per line that it wrote itself. The nine 2 s runs",
    "1.5236 bus writes per line that it wrote itself. Each value per mesh cycle is the bus writes per second divided by 2.0 × 10^9 (est.). The runs that counted the bus writes did not count the mesh cycles. The nine 2 s runs")
rep("SOG pages 11, 12, 13, 14, 15, 19, 23, 24, 25, 26, 38, 52, 55.", "SOG pages 10, 11, 12, 13, 14, 15, 19, 23, 24, 25, 26, 38, 52, 55.")
rep("77.51 × 0.8121 = 62.94 GB/s and 78.45 × 0.8121 = 63.71 GB/s.", "77.51 × 0.81207 = 62.94 GB/s and 78.45 × 0.81207 = 63.71 GB/s.")
rep("78.45 / 77.34 = 1.01. 62.99 / 64 = 0.98", "64 / 0.8275 = 77.34 GB/s, and 78.45 / 77.34 = 1.01. 62.99 / 64 = 0.98")
rep("3.47 / 9.72 = 36 %. (32 × 26.86 + 8 × 61.90) / 40 = 33.9 GB/s |",
    "3.47 / 9.72 = 36 %. 3,553,584,520 bus writes in 1.8094 s = 1.96 × 10^9 per second, and 1.96 / 2.0 = 0.98. 1,782,823,128 bus writes in 1.8000 s = 0.99 × 10^9 per second, and 0.99 / 2.0 = 0.50 |")
rep("The 3 major findings: the share 0.81 was a scaled count and was given as a count; the write comparison of the capacity item used the conversion and did not say so; and the item on the older statements called them wrong for write streams independent of the hypotheses, although \"the port limits\" is hypothesis 2.",
    "The 3 findings that stayed major name these defects. First, the share 0.81 was a scaled count, and the text gave it as a count. Second, the write comparison of the capacity item used the conversion and did not say so. Third, the item on the older statements called them wrong for write streams and said that this does not depend on the hypotheses. But \"the port limits\" is hypothesis 2.")
rep("| Third internal check, on the text that changed after the second check | CHECK3_RESULT |",
    "| Third internal check, on the text that changed after the second check: three independent agents (numbers and logic, this record against the report and the sources, a reading as the reviewer with plain English). A second agent then tried to refute each minor finding | 43 findings: 0 major, 25 minor and 18 note. The second agents judged the 25 minor findings. They confirmed 24 and rejected 1, and they lowered 3 of the 24 to note. All 24 are applied. The main ones are these. First, the conversion item said that one failed comparison makes all converted numbers wrong. Second, the report called the four kinds of run \"the tests of hypothesis 2\" and also said that the test of hypothesis 2 was not run. Third, three values of bus writes per mesh cycle came from runs that did not count the mesh cycles. Fourth, the runs behind the shares 0.81 and 0.83 also differ in loop rate (67.1 against 70.7 to 71.0 GB/s). All 18 notes are applied too. The rejected finding asked that each sub-item can be read alone, and no change was made for it. The corrections of this third check were not read by another agent. I checked them by script: the numbers, the quotations of report text in this record, the report line numbers, and the HTML structure |")
rep("the long table cells and the nested lists in \"Open items\" (4 levels) were not rendered.",
    "the long table cells and the nested lists in \"Open items\" (4 levels) were not rendered. Line 452 of the report holds two entries of the word list on one source line, and line 132 holds five paragraphs. These were not rendered either.")

# ------------------------------------------------------------ section 8, first table
rep("A count mismatch tests the conversion, not the capacity. The threshold is removed",
    "A count mismatch tests the conversion. One kind of mismatch, more bus reads than port flits, can also mean a second data channel, and the text says so. The threshold is removed")

# ------------------------------------------------------------ section 8, second table
line_starting("| Capacity against saturation (CRB-R1) | Draft. Report line 433: \"Every line of a 1 GiB buffer leaves the core",
    "| Capacity against saturation (CRB-R1) | Round 1 and draft. Round 1: report line 425 (now 427) said \"so every line crosses the port as 2 flits\", and the D1 table of the record said \"Writers at 1 GiB, where every line crosses the port\". Draft: report line 433 said \"Every line of a 1 GiB buffer leaves the core, so this rate is the rate through the port\" | Line 427 names the first assumption and marks the step \"est.\". The row of D1 names both assumptions and marks its ratios \"est.\". The write comparison at line 433 names both assumptions of the conversion and the two counts that are missing |\n"
    "| Capacity against saturation (CRB-R1) | Draft. Report line 435: one failed comparison made \"the converted numbers in the items above\" wrong, and the text said that this result does not test hypothesis 1 | The item now says which comparison tests which assumption. It says that more bus reads than port flits can also mean a second data channel |\n"
    "| Capacity against saturation (CRB-R1) | Draft. Report lines 421, 423 and 427 called the four kinds of run \"the tests of hypothesis 2\". Line 431 said that the test of hypothesis 2 was not run | The runs are now called \"the runs of hypothesis 2\" |")
line_starting("| Runs kept apart (CRB-R3) | Round 1. Report line 423 (now 425) and record D1: pair rates of two loops in one range",
    "| Runs kept apart (CRB-R3) | Round 1. Report line 423 (now 425) and record D1: pair rates of two loops in one range, and the share 0.81 with only a pointer to another section | The item and D1 name the loop of each rate. They also name the counter and the source of each share |")
line_starting("| Runs kept apart (CRB-R3) | Round 1 and draft. Report lines 118, 425 and 433, record D1 and F15: the share 0.81 was given as a count.",
    "| Runs kept apart (CRB-R3) | Round 1 and draft. Report lines 118, 425 and 433, record D1 and F15: the share 0.81 was given as a count. Its counters ran for 49 or 50 % of the run, and perf scaled the counts. The run of the 0.81 also had another loop rate (67.1 GB/s) than the runs of the 0.83 (70.7 to 71.0 GB/s) | The share is 0.83 by three counters that ran for the whole run. The 0.81 is marked as a scaled count (est.), and the item gives the loop rate of each run. With 0.83 the converted pair rates are 64.1 to 64.9 GB/s on the port (est.). The earlier text said 63 to 65 GB/s |\n"
    "| Runs kept apart (CRB-R3) | Round 1 and draft. Report lines 424 and 430 (now 426 and 437) and, in the draft, line 434 gave bus writes \"per mesh cycle\" for runs that did not count the mesh cycles | The text gives the bus writes per second first. It marks the value per mesh cycle \"est.\" and names the mesh clock of 2.0 GHz |")
line_starting("| Source against claim (CRB-R4) | Draft. Report line 452: \"One transfer moved 32 B in part 5\"",
    "| Source against claim (CRB-R4) | Round 1 and draft. Round 1: report lines 424, 425 and 430 (now 426, 427 and 437) and record D1 and D2 said \"bus writes of 32 B\". The record's entry \"Bus write, bus read\" said \"one data transfer of 32 B\". Draft: report line 452 said \"One transfer moved 32 B in part 5\". All of them stated a part of the first assumption as a fact. The draft also left out Arm's sentence on snoops | Report lines 426, 427 and 437 and record D1 and D2 no longer say \"bus writes of 32 B\". Line 427 gives the 32 B under the first assumption and marks it \"est.\". Both word lists say that the text takes one transfer as 32 B. The entry at line 452 also says what Arm's list says and how many snoop flits the port counted |")
line_starting("| Source against claim (CRB-R4) | Draft. Report lines 428 and 433: \"The counter covers one data channel\"",
    "| Source against claim (CRB-R4) | Round 1 and draft. Round 1: the row \"One reader, counted at its port\" of record D1 said \"This counter covers one data channel\" and cited only the raw file. Draft: report line 428 said \"The counter covers one data channel\", and report line 433 gave the values of the register field. Neither had a source | Report line 428 and the row of D1 cite TRM pages 1678 to 1679. Line 433 says that the manual does not say which value of the field stands for which number of channels, and it names the assumption |\n"
    "| Source against claim (CRB-R4) | Draft. Report line 113: the sentence on 40 threads of 3 MiB cited the counter file, which holds neither value | Each of the two sentences cites the file that holds its fact |")

# ------------------------------------------------------------ section 8, other changes
line_starting("- Report lines 421, 423, 426 to 429, 431 and 435, wording.",
    "- Report lines 421, 423, 426 to 429 and 431: wording and added numbers. The four kinds of run of hypothesis 2 are named one by one and are called \"the runs of hypothesis 2\". The list items are called \"items\", not \"rows\". The \"first part\" of the conversion became the \"first assumption\". Line 423 gives the measured rates of these runs as 0.97 to 1.01 of the allowed rates (est.). It also gives the 0.88 of the run with two busy pairs. Line 426 gives both measured values of the pair write rate. It says that the bus writes of CPU 2 are half of the capacity of hypothesis 1 (est.). It adds that CPU 2 sent 1.52 bus writes per line that it wrote itself. Line 427 gives the ratios 0.98, 0.99 and 0.88 against 64 GB/s. Line 428 gives the loop rates of the 18 runs of case r8M-c2: 67.3 and 69.6 GB/s in the first two runs, and 70.8 to 71.2 GB/s in the 16 later runs [Ref5]. Line 429 adds the count on the four mesh links that is not explained. Line 431 says that first results exist for writes.\n"
    "- Report line 437: the heading changed from \"Older statements that need a correction\" to \"Older statements that the new rates put in doubt\". The item names one more older statement: \"For software, the pair port is a 78 GB/s limit per two cores on traffic beyond L2\" (D2).")
line_starting("- Plain English in the report.",
    "- Plain English in the report. The long sentence of line 420 is split. Line 132 holds five paragraphs. The items at lines 422, 425, 433, 434, 435 and 437 hold sub-items. The reading rules of line 423 moved to a new last item, \"How to read these items\", on line 429. The entry at line 452 is split into two entries. Each of these stays on its source line.")

# ------------------------------------------------------------ references
rep("Lines 433, 451, 470, 490, 510, 530, 551, 573 and 595: the loop rates of the nine 2 s runs of case w8M-c2c3.",
    "Lines 433, 451, 470, 490, 510, 530, 551, 573 and 595: the loop rates of the nine 2 s runs of case w8M-c2c3. Lines 970 and 979: the loop rates of the first two runs of case r8M-c2 (67.31 and 69.63 GB/s). The rows that start with `asmread,1,8388608,0,` from line 988 to line 1141: the loop rates of its 16 later runs (70.75 to 71.17 GB/s). Among them lines 1046 and 1056 are the runs with the port flits (70.79 and 70.98 GB/s), and lines 1086 and 1097 are the runs with the L2 refills (70.86 and 70.86 GB/s).")
rep("read runs with 40 and with 60 threads on CPU list `0-119` (lines 78 and 85; the 60-thread run is 180 MiB), and three read runs of 120 MiB with other buffer sizes (lines 92, 99 and 106).",
    "read runs with 40 and with 60 threads on CPU list `0-119` (lines 78 and 85), and three read runs of 120 MiB with other buffer sizes (lines 92, 99 and 106). The 60 buffers of the run at line 85 are 180 MiB together.")
rep("The 8 rows with CPUs 64 to 78 sum to 473.26, 474.29 and 481.74 GB/s.",
    "The 8 rows with CPUs 64 to 78 sum to 473.26, 474.29 and 481.74 GB/s. Line 5 of the same file: slowest, fastest and average thread of repetition 2 (26.23, 61.56 and 34.30 GB/s).")
rep("and `bw-asmread-8M-1T.csv` line 3: one asm reader at 8 MiB on 2026-10-30.",
    "and `bw-asmread-8M-1T.csv` line 3 (loop rate 67.07 GB/s): one asm reader at 8 MiB on 2026-10-30.")
rep("written by part 3 of `run_sudo.sh` (`bench/run_sudo.sh` lines 91 to 100) on 2026-11-02 from 05:49 UTC.",
    "written by part 3 of `run_sudo.sh` (`bench/run_sudo.sh` lines 91 to 103). The script run started on 2026-11-02 at 05:49 UTC, and part 3 ran from 05:54 to 06:02 UTC (`log.txt` of the same folder, line 2 and lines 208 to 211).")
rep("Lines 511 and 520: the bytes read in the 0.2 s run and in the 2 s run.",
    "Lines 511 and 520: the bytes read in the 0.2 s run and in the 2 s run, at 70.71 and 70.89 GB/s.")

if "--write" in sys.argv: open(P, "w", encoding="utf-8").write(s)
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits")
