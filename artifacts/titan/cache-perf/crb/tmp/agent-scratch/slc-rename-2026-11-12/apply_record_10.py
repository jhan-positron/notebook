#!/usr/bin/env python3
"""Record of the changes of 2026-11-12 after the review loop: section 10, new found items F22 to F34,
updated rows of section 6, and new references. Every old text must occur exactly once.
Usage: apply_record_10.py [--write]"""
import sys

P = "/home/jhan/tmp/update-crb-memory-hierarchy.md"
s = open(P, encoding="utf-8").read()
n_edits = 0


def rep(old, new):
    global s, n_edits
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)
    n_edits += 1


# ---- Short version, third sentence
rep('The term "mesh cache" is not an Arm term, and the report still uses it (see Q4).',
    'After the review loop the author\'s decisions and comments of 2026-11-12 were applied, among them Arm\'s name "SLC" in place of "mesh cache" (section 10).')

# ---- section 1: state of the files
rep("| The report after this update. 978 lines. sha256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3` |",
    "| The report. 978 lines. The reviewed state of sections 2 to 9 has the sha256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3`. The state after section 10 has the sha256 `REPORT_SHA256` |")
rep("No other project file was changed. The directory has no git history. The backup file is the only record of the old state.",
    "No other project file was changed in the work of sections 2 to 9. Section 10 also changed the brief and its generator, and it lists its own backup files. The directory has no git history. The backup files are the only record of the older states.")

# ---- Q4: the rename is done
rep("Not done. The request asked only for an investigation of the term. I will do it when you confirm the term.",
    "This was not done in the update of 2026-11-11, because the request asked only for an investigation of the term. It was done on 2026-11-12 after the author confirmed the term (section 10.1).")

# ---- D6: decided
rep('An exact label would be "3 loads or 2 stores of 16 B per cycle".',
    'An exact label would be "3 loads or 2 stores of 16 B per cycle". Decided by the author on 2026-11-12: the label is now "3 loads / 2 stores" in all six places (section 10.2).')

# ---- section 6: intro and rows that quote text which the rename changed
rep('These are outside the request. Each has a proposed correction. Say "apply" with the ids.',
    'These are outside the request. Each has a proposed correction. Say "apply" with the ids. F1 to F21 are from the update of 2026-11-11. F22 to F34 were found by the check of 2026-11-12 (section 10.8). The rows quote the report with the name "SLC", as the report has it since 2026-11-12. The rename of 2026-11-12 edited report lines that hold nine of the older items (F1, F3, F4, F5, F10, F14, F15, F20 and F21). It replaced only the name there, and these items are still open.')
rep('"The mesh-served part was still rising" was not measured. The mesh-served part was counted in one run at 40 threads.',
    '"The SLC-served part was still rising" was not measured. The SLC-served part was counted in one run at 40 threads.')
rep("The 0.62 TB/s is what the mesh cache delivered in one run (est.). Each counter ran for about half of that run",
    "The 0.62 TB/s is what the SLC delivered in one run (est.). Each counter ran for about half of that run")
rep("The 0.62 TB/s is what the mesh cache delivered in this one run (est., from counters that ran for about half of the run).",
    "The 0.62 TB/s is what the SLC delivered in this one run (est., from counters that ran for about half of the run).")
rep('| F8 | Line 107 | "The cycle number is derived: ns × 2.8 GHz." The perf counter also measured 4.0000 cycles per L1 load |',
    '| F8 | Line 107 | "Cycles derived." (the author\'s wording of 2026-11-12, before that "The cycle number is derived: ns × 2.8 GHz."). The perf counter also measured 4.0000 cycles per L1 load |')
rep("Three values for one reader at the mesh cache: 67 GB/s (line 52), 54 GB/s from the mesh (line 266,",
    "Three values for one reader at the SLC: 67 GB/s (line 52), 54 GB/s from the SLC (line 266,")
rep('| F14 | Line 266 | "From the mesh cache and DRAM the two loops agree, so there the limit is outside the core."',
    '| F14 | Line 266 | "From the SLC and DRAM the two loops agree, so there the limit is outside the core."')
rep('| "From the mesh cache the two read loops give the same rate (67.0 and 66.9 GB/s).',
    '| "From the SLC the two read loops give the same rate (67.0 and 66.9 GB/s).')
rep('The share of L2 hits at the mesh-cache footprint has three values: none (line 110, "read 78 GB/s from the mesh cache"),',
    'The share of L2 hits at the SLC footprint has three values: none (line 110, "read 78 GB/s from the SLC"),')
rep('Line 110: "two partner cores together read 78 GB/s at the mesh-cache footprint"',
    'Line 110: "two partner cores together read 78 GB/s at the SLC footprint"')

# ---- section 6: new rows after F21 (the row ends with "Not run |")
F_NEW = "\n".join([
    '| F22 | Line 296, caption of the whole-chip chart | "DRAM uses 32 to 60 threads, one per pair, 256 MiB each." This fits the copy bar only (48 threads, one per pair). The read bar is from 30 threads, and the write bar is from 16 threads [`results/followup2-20261031T073513Z/spread.csv` lines 20 and 5, `results/followup-20261030T194205Z/dram.csv` line 75]. Line 397 has the right values | "DRAM uses 256 MiB per thread: 30 threads spread 4 cores apart for read, 16 threads spread 8 cores apart for write, and 48 threads, one per pair, for copy." |',
    '| F23 | Lines 230, 259 and 778 | "2.6 ns" for one crosspoint hop. The table at line 227 gives a median of 2.67 ns. The file of the final run gives 2.668 ns [`results/sudo-20261102T054936Z/core-positions.json`], and the brief says 2.7 ns. The figure label at line 778 gives 19.0 ns, 2.6 ns and 42 ns. A checker reports that the cells of that figure show 20.8 and 43.2 ns. I did not recompute those two cells | Lines 230 and 259: "2.7 ns". Line 778: take its three numbers from the final run |',
    '| F24 | Lines 268, 316 and 964 | Memory requests per line of one writer at 8 MiB. Line 268 says 0.76. Lines 316 and 964 say "about 1". A checker reports that 0.76 is the count of mesh 0 and that mesh 1 counted 0.38 more. I did not recompute the 0.38 | Give one value and name its mesh at lines 316 and 964, for example "0.76 memory requests per line on mesh 0" |',
    '| F25 | Lines 265 and 385 | "Footprints: ... per thread" and "Level (footprint)". The sizes are buffer sizes. A copy thread has two buffers of that size, so its footprint is two times the value [Ref33] | Line 265: "Buffer sizes: L1 = 32 KiB, L2 = 1 MiB, SLC = 8 MiB, DRAM = 1 GiB per thread. A copy thread has two buffers of that size." Line 385: "Level (buffer size)" |',
    '| F26 | Line 63, and references at lines 125, 183, 199, 251, 259, 316, 437, 454 and 464 | The contents entry says "(part 5)", and its heading at line 269 says "(part 5, 2026-11-02)". The nine references quote only the first part of a heading. Each short form fits one heading only, so none is ambiguous | Use the full heading text |',
    '| F27 | Latency figure, script lines 492 and 505 | Two labels are drawn over each other: the band label "DRAM" and the label "DRAM: 148 ns (415 cycles)". A checker saw this in a browser render of the report before and after the rename. I did not render that figure | Move one of the two labels |',
    '| F28 | Brief line 46, `crb/make-brief.py` lines 47 and 48 | The values per thread are from repetition 0 (869 GB/s on one mesh, 25 to 30 GB/s each, 58 to 60 GB/s each on the other mesh). The total is from the best repetition (1372 GB/s). The parts of repetition 0 add up to 1342 GB/s [`results/followup3-20261102T031936Z/perthread-asmread-3M-40.csv`] | Take all values from repetition 2: 890 GB/s on one mesh (26 to 30 GB/s each), 59 to 62 GB/s each on the other mesh, 1372 GB/s total |',
    '| F29 | Brief line 32, `crb/make-brief.py` line 173 | "29 avg (85)". 29 ns is 81 cycles at 2.8 GHz. The report gives 30 ns and 85 cycles. A checker reports a mean of 29.41 ns over the rows of the root run, which is 82 cycles. I did not recompute that mean | Make the two numbers agree: "29 avg (82)" or "30 avg (85)" |',
    '| F30 | Brief line 40, `crb/make-brief.py` line 181 | "the same port carries 82 GB/s with the partner core, 229 GB/s with 4 writers". The four writers ran on four ports (CPUs 2, 4, 6 and 8, report line 287). The line also repeats "inside the core" with no limit to 8 MiB | The text for the brief under P3 in section 10.6 |',
    '| F31 | Line 278 | "1.8 × 10^9 flits per second". The raw counts give 1.85 × 10^9 [Ref5, lines 98 to 101 and 108 to 111: 3,338,638,175 data flits in 1.7999 s] | "1.85 × 10^9 flits per second" |',
    '| F32 | Line 289 | "the number of write transactions the core\'s L2 interface keeps outstanding, times the round trip to the home node, sets the rate" and "the limit is latency times in-flight count". The relation is the other way round. With a fixed number of writes in flight, a longer round trip gives a lower rate. So the rate is the number in flight divided by the round-trip time | P3 in section 10.6 holds the corrected wording |',
    '| F33 | Line 343 | "two partner cores share one port and together get no more than one". At 8 MiB two partner cores together read 1.15 to 1.17 times as much as one core alone (77.5 to 78.5 GB/s against 66.9 to 67.5 GB/s). That the port is the limit is hypothesis 2 | "one thread per pair. At 8 MiB two partner cores together read only 1.15 to 1.17 times as much as one core alone (section "The pair finding")." |',
    '| F34 | Style rule at line 32, tables with text columns (for example lines 102 to 121) | One rule aligns every table cell but the first to the right. A browser render shows the long texts of the column "Source" set flush right, which is hard to read. The rule is older than this update | Add a class for tables with text columns that aligns their cells to the left |',
])
rep("A new counter run of the 40-thread test with fewer events at a time would give counts over the whole run. Not run |\n",
    "A new counter run of the 40-thread test with fewer events at a time would give counts over the whole run. Not run |\n" + F_NEW + "\n")

# ---- section 10 and new references
SEC10 = open(sys.argv[1], encoding="utf-8").read()
REFS = open(sys.argv[2], encoding="utf-8").read()
rep("## References\n", SEC10.rstrip("\n") + "\n\n## References\n")
assert s.endswith("\n")
s = s + REFS.rstrip("\n") + "\n"

if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write(s)
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, {s.count(chr(10))} lines")
