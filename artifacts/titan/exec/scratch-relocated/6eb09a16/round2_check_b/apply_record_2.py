#!/usr/bin/env python3
"""Record edits after the second internal check, part 2: sections 7 and 8 and the references.
Every old text must occur exactly once."""
import sys
P = "/home/jhan/tmp/update-crb-memory-hierarchy.md"
s = open(P, encoding="utf-8").read()
n_edits = 0

def rep(old, new):
    global s, n_edits
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new); n_edits += 1

def block(start, end, new):
    global s, n_edits
    assert s.count(start) == 1, (s.count(start), start[:60])
    i = s.index(start); j = s.index(end, i + len(start))
    s = s[:i] + new + s[j:]; n_edits += 1

def line_starting(prefix, new):
    """Replace the one whole line that starts with prefix."""
    global s, n_edits
    L = s.split("\n"); hits = [i for i, l in enumerate(L) if l.startswith(prefix)]
    assert len(hits) == 1, (len(hits), prefix)
    L[hits[0]] = new; s = "\n".join(L); n_edits += 1   # new may hold a second line (a new reference)

# ---------------------------------------------------------------- section 7
rep("All 58 ids and all 38 links are unchanged. Checked again after the changes of section 8 |",
    "All 58 ids and all 38 links are unchanged. Checked again after the changes of section 8. The open item now nests lists 4 levels deep. The backup had 1 level |")
rep("all listed in sections 2 and 5. Still 19 after the changes of section 8 |",
    "all listed in sections 2 and 5. Still 19 after the changes of section 8. Against the round-1 state of the report the diff has 9 hunks: lines 97, 113, 118, 125, 131 to 133, 420 to 423, 425 to 429, 431 to 437 and 452. Section 8 names each of them |")
rep("CPU 2 with its partner also writing: 0.495 bus writes per mesh cycle and 1.5236 bus writes per own line. The nine long runs of one case differ by 0.0 to 2.2 % in loop rate |",
    "CPU 2 with its partner also writing: 0.495 bus writes per mesh cycle and 1.5236 bus writes per line that it wrote itself. The nine 2 s runs of one case differ by 0.0 to 2.2 % in loop rate. Every counter row of part 5 ran for 100 % of its run (598 rows, column 5 of the raw file) |\n"
    "| Share of the lines of one reader at 8 MiB that cross the port, recomputed from the raw rows | Port flits: 1.6530 per line, which is 0.8265 of the lines [Ref5]. L2 refills: 0.8264 per line [Ref5]. Accesses to the mesh cache in part 3: 1,650,550,050 for 1,994,522,624 lines, which is 0.8275 per line, with both counters at 100 % of the run [Ref29]. Scaled count of 2026-10-30: 850,985,083 for 1,047,920,640 lines, which is 0.8121 per line, with the counters at 49 % of the run [Ref28] |")
rep("SOG pages 11, 12, 13, 14, 15, 19, 23, 24, 25, 26, 38, 52, 55. TRM pages 54, 280, 386, 1016, 1656, 2120.",
    "SOG pages 11, 12, 13, 14, 15, 19, 23, 24, 25, 26, 38, 52, 55. TRM pages 54, 101 to 102, 280, 386, 671 to 672, 1016, 1656, 1678 to 1679, 2120.")
rep("| Web sources of Q4 and D9 |",
    "| Firmware image of Q2 [Ref17] | Read again as bytes on 2026-11-12: the two values, the text \"PhoenixCfg1\", the names before and after INTPLL_MAIN, and the 46 offsets of the 8-byte value 2,000,000,000 |\n| Web sources of Q4 and D9 |")
rep("20 / 5.37 = 3.7 per cycle. 4 / 5.37 = 0.75 per cycle.",
    "20 / 5.37 = 3.7 per cycle. 4 / 5.37 = 0.745 and 4 / 5.34 = 0.749, so at most 0.75 per cycle.")
rep("64 / 0.83 = 77 GB/s and 64 / 0.81 = 79 GB/s. 77.5 × 0.81 = 62.8 GB/s and 78.5 × 0.83 = 65.2 GB/s. 64 × 2 / 1.524 = 84 GB/s. 62.99 / 64 = 0.98 and 63.18 / 64 = 0.99. 113.24 / 2 = 56.6 GB/s. 1,348.80 − 898.80 = 450.00 GB/s. 3.47 / 9.72 = 36 % |",
    "64 / 0.8265 = 77.4 GB/s and 64 / 0.8121 = 78.8 GB/s. 77.51 × 0.8264 = 64.05 GB/s and 78.45 × 0.8275 = 64.92 GB/s. 77.51 × 0.8121 = 62.94 GB/s and 78.45 × 0.8121 = 63.71 GB/s. 64.05 / 64 = 1.00 and 64.92 / 64 = 1.01 flits per mesh cycle. 64.05 GB/s / 32 B = 2.00 × 10^9 and 64.92 GB/s / 32 B = 2.03 × 10^9 bus reads per second. 62.94 / 32 = 1.97 × 10^9 and 63.71 / 32 = 1.99 × 10^9. 78.45 × 0.81 = 63.5 GB/s. 1 − 0.8265 = 17 %. 64 × 2 / 1.5241 = 83.98 GB/s. 81.41 / 83.98 = 0.97 and 82.34 / 83.98 = 0.98. 78.45 / 77.34 = 1.01. 62.99 / 64 = 0.98 and 63.18 / 64 = 0.99. 113.24 / 2 = 56.6 GB/s, and 56.6 / 64 = 0.88. 63.18 − 62.99 = 0.19 GB/s, which is 0.3 % of 62.99. 1,348.80 − 898.80 = 450.00 GB/s. 3.47 / 9.72 = 36 %. (32 × 26.86 + 8 × 61.90) / 40 = 33.9 GB/s |")
rep("All 47 are applied. Of the 30 notes, 26 are applied and 2 in part. Not applied: a second counter (stall cycles) for the saturation test, a sentence on the placement of the threads in report line 113 (report line 344 has it), a quotation from the CHI specification about links with resource planes, and the split of three long list items of the open item |",
    "All 47 are applied. Of the 30 notes, 26 are applied, 2 are applied in part and 2 are not applied. The 2 notes that are not applied: a second counter (stall cycles) for the saturation test, and a sentence on the placement of the threads in report line 113 (report line 344 has it). The open part of one other note is not applied either: a quotation from the CHI specification about resource planes (a flow-control feature of CHI links). The open part of the last note, the split of three long list items, was applied after the second check |")
rep("| Second internal check, after the findings of the first check were applied | CHECK2_RESULT |",
    "| Second internal check, after the findings of the first check were applied: four independent agents (data and logic of the report, claims of this record, a reading as the reviewer, plain English). A second agent then tried to refute each major and minor finding | 78 findings: 5 major, 55 minor and 18 note. The second agents judged the 60 major and minor findings. They confirmed 59 and rejected 1. They kept 3 as major, lowered 2 from major to minor and 7 from minor to note. Several findings name the same defect. The 3 major findings: the share 0.81 was a scaled count and was given as a count; the write comparison of the capacity item used the conversion and did not say so; and the item on the older statements called them wrong for write streams independent of the hypotheses, although \"the port limits\" is hypothesis 2. All 59 confirmed findings are applied. I checked the evidence of each against the raw files or the cited pages before I applied it. Of the 18 notes, 16 are applied and 2 in part. The open parts: the caption at report line 97 keeps wording A, and the 60-thread run in the file of the series is named in [Ref11] and not in the report |\n"
    "| Third internal check, on the text that changed after the second check | CHECK3_RESULT |")
rep("The charts that the page draws by script, the long table cells and the nested list in \"Open items\" were not rendered.",
    "The charts that the page draws by script, the long table cells and the nested lists in \"Open items\" (4 levels) were not rendered.")

# ---------------------------------------------------------------- section 8
block("## 8. Changes after the external review, round 1\n", "## References\n", r'''## 8. Changes after the external review, round 1

The reviewer agent of the review loop read the report and this record. It wrote four findings on 2026-11-12 at 00:41 UTC. All four are accepted. No benchmark was needed for any of them.

| Finding | What the reviewer asked | What changed | Where |
|---|---|---|---|
| CRB-R1 | Keep the capacity of the port apart from the question whether a test fills it. Remove the rejection threshold of 0.95 flits per mesh cycle or justify it | The open item now holds two hypotheses (capacity, saturation) and the conversion with its two assumptions. Each has its own missing test. A low rate no longer rejects the capacity. A count mismatch tests the conversion, not the capacity. The threshold is removed, and the text says why none is set | Report lines 118 and 420 to 437. Record D1 and D2 |
| CRB-R2 | Do not present an observed loop rate as an established limit. Limit "No other limit in Arm's guide is reached" to the limits that were checked | The sentence is replaced by the list of the limits that were checked, and the paragraph ends with "The cause of the remaining gap is not established". In this record, one loop pass per cycle is an observed rate. A bound from Arm's guide, a hypothesis and its test are labelled as such. Q7 no longer says that the "Words used here" entry states a limit. The proposed text of F14 states no cause | Report lines 132 and 133. Record Q7 and F14, Ref2, Ref16 |
| CRB-R3 | Do not assign the increase of 450 GB/s of 2026-10-30 to the threads on mesh 1, because only the run of 2026-11-02 recorded each thread | Q1 keeps the totals of the series of 2026-10-30 apart from the totals per mesh of other runs. The attribution is labelled as an interpretation | Record Q1, Ref11 |
| CRB-R4 | The row "Other vendors of CMN-based chips" claims an interconnect that the NVIDIA page does not support | The row is now "Other Arm server CPUs" and compares the words only. A note says what each page states about its interconnect | Record Q4, Ref13, Ref20 |

Two internal checks then read the corrected texts (section 7). They found more places with the same four kinds of defect. The table lists them by kind. "Round 1" marks a defect that was in the text that the reviewer read. "Draft" marks a defect that was only in a corrected version of this round, which the reviewer did not see.

| Kind | Place | Correction |
|---|---|---|
| Capacity against saturation (CRB-R1) | Round 1. Report line 118: "the hypothesis does not conflict with the measured ~80 GB/s (est.)" | The converted rate on the port is 64 to 65 GB/s (est.), at or just above 64 GB/s. The text says that the estimate cannot decide |
| Capacity against saturation (CRB-R1) | Round 1. Report line 430 (now 437): "If the hypothesis holds, "The single-writer limit is inside the core" also does not hold at 1 GiB" | The step from 98 % of the capacity to "the port limits the writer" now needs hypothesis 2 |
| Capacity against saturation (CRB-R1) | Round 1. Report line 430 (now 437) and record D2: the two older statements "are wrong for write streams", and this "does not depend on the hypothesis" | The measured rates show that two partner writers share one limit at 1 GiB. That the full port is this limit is now part of hypothesis 2 |
| Capacity against saturation (CRB-R1) | Draft. Report lines 433 to 435: the test for the capacity and the test for the conversion read one result in two ways | For reads, more bus reads than mesh cycles cannot separate a wrong hypothesis 1 from a wrong first assumption. The text says so. Tests for writes are added |
| Capacity against saturation (CRB-R1) | Draft. Report line 433: "Every line of a 1 GiB buffer leaves the core, so this rate is the rate through the port" | The write comparison now names both assumptions of the conversion and the two counts that are missing |
| Observed rate against limit (CRB-R2) | Round 1. Report line 132: "The vector adds explain only part of the gap". The dispatch limits: round 1 named three of the eight, and a draft named four | The first sentence states a bound. All eight dispatch limits are named and compared |
| Observed rate against limit (CRB-R2) | Round 1 and draft. Report line 132: operations "enter the pipelines". This read as a conflict with "Each pipeline accepts one operation per cycle" (line 123) | The text now says that these are limits of dispatch, the step before the pipelines |
| Runs kept apart (CRB-R3) | Round 1. Report lines 97 and 113: the 1.38 TB/s counter run and the series of runs with 8 to 40 threads read as one test | Both texts now name the separate series of runs. Line 113 cites the file of each |
| Runs kept apart (CRB-R3) | Round 1. Report line 423 (now 425) and record D1: pair rates of two loops in one range, and the share 0.81 with only a pointer to another section | The item names the loop of each rate and the counter and the file of each share |
| Runs kept apart (CRB-R3) | Round 1 and draft. Report lines 118, 425 and 433, record D1 and F15: the share 0.81 was given as a count. Its counters ran for 49 or 50 % of the run, and perf scaled the counts | The share is 0.83 by three counters that ran for the whole run. The 0.81 is marked as a scaled count (est.). With 0.83 the converted pair rates are 64.1 to 64.9 GB/s on the port (est.). The earlier text said 63 to 65 GB/s |
| Runs kept apart (CRB-R3) | Draft. Record Q1: "8 of the 40 threads" stated for the counter run, whose files hold no CPU list. Also: "These sums differ from 450 GB/s, because they are from another run" | The placement of the counter run is now a condition ("If the run used the CPU list of the series"). The sums and the 450 GB/s are named as two different quantities |
| Runs kept apart (CRB-R3) | Draft. Report line 422: "three separate runs" for three counts that come from six runs | "Each of these three counts is from its own pair of runs" |
| Source against claim (CRB-R4) | Round 1. Record Q2: "2,000,000,000 Hz next to the PLL name INTPLL_MAIN" | The value and the name are 73.5 MiB apart. The row now says that it is consistent with 2.0 GHz and does not establish it |
| Source against claim (CRB-R4) | Round 1. Record D7 and D9: statements about CRB and about Arm's highest values with no source | D7 cites the inspection record and the module inventory. D9 adds the values of Arm's product brief and says which values the report gives |
| Source against claim (CRB-R4) | Round 1. Report line 131 and record Q7: "the same package on both days", with no record for the build day | Both texts name the two days that have a record (2026-10-30 and 2026-11-11) |
| Source against claim (CRB-R4) | Draft. Report line 452: "One transfer moved 32 B in part 5" stated the first assumption as a fact. Arm's sentence on snoops was left out | The entry says what Arm's list says, what the report assumes, and how many snoop flits the port counted |
| Source against claim (CRB-R4) | Draft. Report lines 428 and 433: "the counter covers one data channel" and the values of the register field, both with no source | Line 428 cites TRM pages 1678 to 1679. Line 433 says that the manual gives no numbering for the field, and it names the assumption |
| Source against claim (CRB-R4) | Draft. Record Q4, note: "a future product" | The note quotes the page |

Other changes of this round:

- Evidence for the conversion from the existing raw files: the new script `port_counts.py` [Ref24], Arm's description of the bus events [Ref26], the count of part 3 [Ref29], report line 422 and the new "Words used here" entry at report line 452.
- The three vendor pages and Arm's product brief were downloaded and read as text. The earlier reading came through a tool that summarises pages.
- Report line 125: "confirms the second mix" became "is a measured case of the second mix". Q5 of this record already used these words.
- Report line 131: the sentence on the source copy of 2026-10-30 now names `k_write` and `k_copy` next to `k_read` [Ref22]. Its conclusion now covers the three loops compiled from C. Line 133 uses the instruction counts of the write and copy loops.
- Report line 133: the sentence on the write and copy loops is now two sentences. It says "A general limit", gives the instructions per pass (4 and 5) and names the buffer sizes (32 KiB and 1 MiB).
- Report lines 421, 423, 426 to 429, 431 and 435, wording. The runs of hypothesis 2 are named one by one and are called "the tests of hypothesis 2". The list items are called "items", not "rows". The "first part" of the conversion became the "first assumption". Line 426 gives both measured values of the pair write rate. Line 429 adds the count on the four mesh links that is not explained. Line 431 says that first results exist for writes.
- Plain English in the report. The long sentence of line 420 is split. Line 132 holds three paragraphs. The items at lines 422, 425, 433 and 434 hold sub-items. Each of these stays on one source line.
- Between round 1 and this round the report grew from 970 to 978 lines. Lines after 420 moved down by up to 8 lines. The line numbers in this record are updated.
- Section 6 has one new item, F21: older text of the report gives values from scaled counts with no "est.".
- This record also changed outside the places named in this section: the Short version and the new section "The three corrections", "Words used here", sections 1, 2, 5, 6 and 7, and the references. These edits are not listed one by one.

''')

# ---------------------------------------------------------------- references
line_starting("- [Ref2] ", r'''- [Ref2] `crb/refs/arm-neoverse-v3ae-r0p2-software-optimization-guide-110075.pdf`. Page 11: instructions are "decoded into internal Macro-OPerations (MOPs)", and "A MOP can be split into two Micro-OPerations (µOPs)". This record calls a µOP an operation. Page 11 also: "Once dispatched, µOPs wait for their operands and issue out-of-order to one of 21 issue pipelines. Each issue pipeline can accept one µOP per cycle." Pages 12 and 13: Figure 2-1 and Table 2-1. Page 14, Table 3-1: the symbols V0 and V1 stand for the pipelines FP/ASIMD 0 and FP/ASIMD 1. Page 14 also: "Exec Latency is defined as the minimum latency seen by an operation dependent on an instruction in the described group." Page 15, Table 3-3: integer ADD ("ALU, basic"), latency 1 cycle. Page 19, Table 3-7: LDR, latency 4 cycles, 3 per cycle. Pages 23 to 25, Tables 3-13 and 3-14. Page 23: LDP of two q registers with an immediate offset, latency 6 cycles, 3/2 per cycle, load pipelines. The table gives no count of µOPs. Page 26, Table 3-15: vector ADD, latency 2 cycles, 2 per cycle. Page 38, Table 3-23: WHILELO, latency 2 cycles, 2 per cycle. Page 52, Table 3-28: ST1D with a scalar + scalar address, latency 2 cycles, 2 per cycle. Page 55, section 4.1 "Dispatch constraints": "Dispatch of µOPs from the in-order portion to the out-of-order portion of the microarchitecture includes several constraints.", "The dispatch stage can process up to 10 MOPs per cycle and dispatch up to 20 µOPs per cycle", "Up to 4 µOPs utilizing the S or B pipelines", "Up to 4 µOPs utilizing the M pipelines", "Up to 2 µOPs utilizing the M0 pipelines", "Up to 2 µOPs utilizing the V0 pipeline", "Up to 2 µOPs utilizing the V1 pipeline", "Up to 6 µOPs utilizing the L pipelines".''')
rep("Page 1016: field data_ram_latency. Page 1656: field dat_vc_num_p. Page 2120, Table A-2:",
    '''Page 1016: field data_ram_latency. Page 1656: field dat_vc_num_p, "Number of replicated channels on DAT VC at this port", with no table of values. Page 1678: the port event DAT, "DAT channel when POR_DAT_VC_NUM_PARAM = 1 ; DAT Sub-channel 1: when POR_DAT_VC_NUM_PARAM > 1", and the port event DAT2, "DAT Sub-channel 2: Applicable when POR_DAT_VC_NUM_PARAM > 1". Page 1679: "TX flit valid; signaled when a flit is successfully transmitted". Page 2120, Table A-2:''')
rep("Lines 1092 and 1103: L2 refills of case r8M-c2. Event names such as",
    "Lines 1092 and 1103: L2 refills of case r8M-c2. Lines 1050 and 1060: snoop flits to the port in case r8M-c2. Lines 433, 451, 470, 490, 510, 530, 551, 573 and 595: the loop rates of the nine 2 s runs of case w8M-c2c3. Every counter row of the file ran for 100.00 % of its run (column 5). Event names such as")
rep("`crb/results/followup-20261030T194205Z/asm.csv` lines 11, 15, 67, 74, 102, 109, 144, 165, 169, 184, 188, 199 and `pair.csv`",
    "`crb/results/followup-20261030T194205Z/asm.csv` lines 11, 15, 67, 74, 102, 109, 144, 165, 169, 184, 188, 199, lines 166 to 168 and 181 to 183 (the three repetitions of one writer and of two partner writers at 1 GiB) and `pair.csv`")
rep("and lines 27 and 34 (slowest, fastest and average thread of the best repetition with 32 and with 40 threads).",
    "and lines 27 and 34 (slowest, fastest and average thread of the best repetition with 32 and with 40 threads). The same file holds other runs that are not part of this series: write and copy runs, read runs with 40 and with 60 threads on CPU list `0-119` (lines 78 and 85; the 60-thread run is 180 MiB), and three read runs of 120 MiB with other buffer sizes (lines 92, 99 and 106).")
rep("with 6,247,492,962 accesses to the mesh cache on mesh 0 (line 3) and 3,471,244,819 on mesh 1 (line 7). `bw-asmread-3M-40T-even.csv` in the same folder: the total of that run, 1,384.77 GB/s in one repetition of 1.0 s.",
    "with 6,247,492,962 accesses to the mesh cache on mesh 0 (line 3) and 3,471,244,819 on mesh 1 (line 7). Both are scaled counts (est.): each of the two counters ran for 49 % of the run (column 5). `bw-asmread-3M-40T-even.csv` in the same folder: the total of that run, 1,384.77 GB/s in one repetition of 1.0 s, and its slowest, fastest and average thread (26.86, 61.90 and 34.62 GB/s, line 3). Neither file of this run holds a CPU list.")
rep("0x4e80428 (text PhoenixCfg1) and 0x4fbf12 (text INTPLL_MAIN).",
    "0x4e80428 (text PhoenixCfg1) and 0x4fbf12 (text INTPLL_MAIN). The names before INTPLL_MAIN are DBGSYSPLL, APSYSPLL, LCPPLL, DDRPLL0 to DDRPLL5 and 70 names from CPU_PLL0_MAIN to CPU_PLL34_FALLBK. The names after it are INTPLL_FALLBK, CCSM_MESH, MESH_THERMAL_MANAGEMENT and MESH_DVFS. The 8-byte value 2,000,000,000 occurs at 46 offsets of the image.")
rep("173 to 195 (`k_asmread`) and 197 to 215 (`k_asmwrite`,", "173 to 195 (`k_asmread`) and 197 to 218 (`k_asmwrite`,")
rep("file `tools/perf/pmu-events/arch/arm64/arm/neoverse-v3/bus.json` (descriptions of BUS_ACCESS, BUS_ACCESS_RD and BUS_ACCESS_WR) and file",
    '''file `tools/perf/pmu-events/arch/arm64/arm/neoverse-v3/bus.json` (descriptions of BUS_ACCESS, BUS_ACCESS_RD, BUS_ACCESS_WR and BUS_CYCLES). BUS_ACCESS: "Counts memory transactions issued by the CPU to the external bus, including snoop requests and snoop responses. Each beat of data is counted individually." BUS_CYCLES: "Since that interface is driven at the same clock speed as the CPU, this event is a duplicate of CPU_CYCLES." Also file''')
line_starting("- [Ref28] ", "- [Ref28] `crb/results/uncore2-20261030T203752Z/cmn-asmread-8M-1T.csv` lines 3 and 7 and `bw-asmread-8M-1T.csv` line 3: one asm reader at 8 MiB on 2026-10-30. Each counter of this file ran for 49 or 50 % of the run (column 5 of each row), and perf scaled the counts to the whole run. The scaled counts of the two meshes sum to 850,985,083 accesses to the mesh cache. The loop read 1,047,920,640 lines. That is 0.81 accesses per line (est.). The file does not record the CPU. All 8 counter files of this folder have every counter at 49 or 50 %.\n"
    "- [Ref29] `crb/results/sudo-20261102T054936Z/writebw.csv`, written by part 3 of `run_sudo.sh` (`bench/run_sudo.sh` lines 91 to 100) on 2026-11-02 from 05:49 UTC. Case asmread-8M-1 is one asm reader at 8 MiB with the CPU list `0-119`, which puts the thread on CPU 0. Lines 511 and 520: the bytes read in the 0.2 s run and in the 2 s run. Lines 515 and 524: the accesses to the mesh cache on mesh 0, both counters at 100.00 % of the run. The 2 s run minus the 0.2 s run gives 1,650,550,050 accesses for 1,994,522,624 lines, which is 0.83 per line.")

if "--write" in sys.argv: open(P, "w", encoding="utf-8").write(s)
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits")
