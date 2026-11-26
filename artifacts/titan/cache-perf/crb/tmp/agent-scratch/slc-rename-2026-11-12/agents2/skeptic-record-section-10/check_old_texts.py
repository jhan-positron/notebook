#!/usr/bin/env python3
"""Read-only: check that each 'old text' of my proposed fixes occurs exactly once in its record line."""
R = "/home/jhan/tmp/update-crb-memory-hierarchy.md"
L = open(R, encoding="utf-8").read().split("\n")
pairs = [
    ("RC1", 541, "A script compared the sentences. Of the 60 sentences of the old text, 47 are in the new text word for word. The other 13 became list items, table cells or table rows."),
    ("RC2", 623, "The first figure was also rendered with cairosvg and viewed."),
    ("RC3", 352, "(section 10.8)"),
    ("RC4", 515, "- **Places with \"SLC (L3)\".** The sub-header (line 49), the first figure and its screen-reader label (lines 86 and 77), two rows of the source table (lines 111 and 119), the size table (line 144), the heading \"The SLC (L3) and the pair port\" and its contents entry (lines 178 and 60), the word list (line 454) and one chart label (line 492)."),
    ("RC5", 520, "The generator got 8 replacements. One sentence was added to the caption of the first table:"),
    ("RC6a", 542, "and the sentence \"The table below compares each limit with the average rate of the loop.\""),
    ("RC6b", 544, "One style rule for the listings was added at line 35."),
    ("RC7a", 560, "With the write loop compiled from C one core writes 44.8 GB/s at 1 GiB. That is far below 64 GB/s [Ref31]"),
    ("RC7b", 561, "\"No run counted the share for two partner cores.\""),
    ("RC7c", 561, "\"No run counted the share with only two partner cores busy.\" Line 425 adds"),
    ("RC8", 564, "Seven smaller corrections of text that this section wrote were also applied: the first use of \"SLC\" at line 49, a citation at line 139 (pages 31 to 32), quotation marks at line 179, the heading at lines 182 and 60, one plural at line 297 (\"The SLC bar is a lower bound\"), the order of two sentences at line 454, and the pronoun \"them\" at line 421."),
    ("RC9a", 578, "[Ref5][Ref24]. Three counters give 0.83 for the share of the lines that cross the port."),
    ("RC9b", 579, "64.1 to 64.9 GB/s at the port (est.). No run counted"),
    ("RC9c", 580, "- Where every line must cross the port, the pair rate at the loops is itself close to 64 GB/s. Two partner writers with 1 GiB each write 63.2 GB/s together [Ref10]."),
    ("RC9d", 581, "That is 0.97 to 1.01 of 64 GB/s."),
    ("RC10a", 573, "The mesh manual names"),
    ("RC10b", 573, "A web search result says that PCIe 6.0 has a flit mode too [Ref36]."),
    ("RC11", 639, "Page 2120, Table A-2: \"Data_Width N Fixed to 256\"."),
    ("RC12", 552, "for the whole-chip tests [Ref33]."),
    ("RC13", 612, "already reaches the rate of the pair (63.2 GB/s).\""),
    ("RC14", 606, "Sources: [Ref5], [Ref10], [Ref24]."),
    ("RC15a", 618, "59 ids (one new, none removed, none twice) and 39 link targets, all present."),
    ("RC15b", 618, "The style block has one new rule (line 35)"),
    ("RC16a", 624, "Applied: every finding about text that this section wrote. Not applied: the findings about older text. They are items F22 to F34 of section 6."),
    ("RC16b", 352, "F22 to F34 were found by the check of 2026-11-12"),
    ("RC17", 498, "Its last entry names the digest `81bef21aae0ea4628c114234a2f40f6b0644f5d62fcb1d71b5a1bfa09e5ba864` of this record and the report with the sha256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3` (section 9)."),
    ("RC18", 40, "The report calls it the mesh cache."),
    ("RC19", 49, "- **est.**: estimate."),
    ("RC19b", 631, "The listings were not viewed in IBM Plex Mono."),
    ("RC20a", 624, "are worked into sections 10.5 and 10.6"),
    ("RC20b", 389, "A browser render shows the long texts of the column \"Source\" set flush right, which is hard to read."),
    ("RC20c", 582, "A rate close to 64 GB/s also fits a port with a higher maximum that something else holds near that rate."),
    ("RC20d", 522, "`crb/perf-measurement-tech.html` (9 places), `crb/crb-cross-check-bill.html` (12), `crb/mesh0-or-mesh1.md` (11), `crb/plan-2026-11-02.md` (16), four review records in `crb/` (9 in total), `crb/crb-memory-hierarchy-edited.html` (40, an older copy of the report) and three files in `bench/` (5 in total)."),
    ("RC21", 380, "Line 265: \"Buffer sizes: L1 = 32 KiB, L2 = 1 MiB, SLC = 8 MiB, DRAM = 1 GiB per thread. A copy thread has two buffers of that size.\" Line 385:"),
    ("RC22", 378, "A checker reports that the cells of that figure show 20.8 and 43.2 ns. I did not recompute those two cells"),
    ("RC23", 379, "A checker reports that 0.76 is the count of mesh 0 and that mesh 1 counted 0.38 more. I did not recompute the 0.38"),
    ("RC24", 382, "I did not render that figure"),
    ("RC25", 384, "A checker reports a mean of 29.41 ns over the rows of the root run, which is 82 cycles. I did not recompute that mean"),
    ("RC26", 377, "`results/followup-20261030T194205Z/dram.csv` line 75]"),
    ("RC28", 561, "In those runs each pair read 62.9 to 63.7 GB/s at the loops"),
    ("RC29a", 622, "An unchanged copy of the generator rebuilt the old brief byte for byte, apart from the date."),
    ("RC29b", 671, "with the page font IBM Plex Sans from"),
    ("RC30a", 289, "to the Spec row."),
    ("RC30b", 368, "Not checked against the new facts. The technique page repeats"),
    ("RC30c", 522, "(40, an older copy of the report)"),
    ("X1", 505, "| `crb/crb-memory-hierarchy-brief.html` | The brief, built again"),
    ("X2", 579, "No run counted the share with only two partner cores busy."),
    ("X3", 389, "(for example lines 102 to 121)"),
    ("RC27", 600, "Sources: [Ref10], [Ref31], [Ref5], [Ref29], [Ref34]."),
]
bad = 0
for tag, n, old in pairs:
    c = L[n - 1].count(old)
    if c != 1:
        bad += 1
    print("%-6s line %3d count %d %s" % (tag, n, c, "" if c == 1 else "<-- NOT EXACTLY ONCE"))
print("problems:", bad)
