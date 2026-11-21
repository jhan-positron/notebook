#!/usr/bin/env python3
"""Fixes from the second check of 2026-11-12 (findings RE1 to RE9, RE11, RE14, and the
skeptic's notes X-1 and X-2 for the report). Every edit stays on its physical line, so the
report keeps 978 lines. Every old text must occur exactly once in its line.
Usage: apply_report_check2.py [--write]"""
import sys

P = "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
L = open(P, encoding="utf-8").read().split("\n")
n_lines = len(L)
n_edits = 0


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


# ---- line 49, sub-header
# X-2: the long form stands once in this line already
sub(49, "is now called SLC (system level cache, Arm's name).", "is now called SLC (Arm's name).")
# RE14: name the other changes of 2026-11-12
sub(49, 'Earlier versions of this report said "mesh cache".</div>',
    'Earlier versions of this report said "mesh cache". Also changed on 2026-11-12: the passage on the read loop '
    'compiled from C now has its own heading and three code listings. The label of the core\'s load and store '
    'pipelines now reads "3 loads / 2 stores". Three statements in "Open items" were corrected: the runs of '
    'hypothesis 2, the share counted with four busy cores, and the write runs of the loop compiled from C.</div>')

# ---- line 52, Short version (RE9): the clause on Linux must attach to the cache
sub(52, "a 128 MiB SLC (system level cache, the shared cache in the on-chip mesh interconnect, which Linux lists as L3) at about 30 ns",
    "a 128 MiB SLC (system level cache: the shared cache that Linux lists as L3, located in the on-chip mesh interconnect) at about 30 ns")

# ---- line 131
# RE8: "This loop" lost its noun after the new lead paragraph
sub(131, "<p><b>Source code.</b> This loop is the C function <code>k_read</code>",
    "<p><b>Source code.</b> The read loop compiled from C is the function <code>k_read</code>")
# RE11: which day the listing of k_asmread is from
sub(131, "<li>So the three loops compiled from C were very probably the same.</li></ul>",
    "<li>So the three loops compiled from C were very probably the same.</li>"
    "<li>The 132.7 GB/s of the asm loop is from 2026-10-30 too. No copy of the asm source of that day was found. "
    "The listing above shows the file of 2026-11-02. A note of 2026-10-30 describes the loop as the listing shows it: "
    "eight LDP q instructions, one add, one compare and one branch for each 256 B [bench/README.md, lines 33 to 35].</li></ul>")

# ---- line 132
# RE7: the first list item starts with a way of counting
sub(132, "<li>The dispatch step handles at most 10 instructions per cycle. The guide counts instructions after decoding and calls them MOPs (macro-operations).</li>",
    "<li>The guide counts instructions after decoding and calls them MOPs (macro-operations). The dispatch step handles at most 10 of them per cycle.</li>")
# RE6: the row names what is counted
sub(132, "<td>Dispatch: three groups of integer and branch pipelines (3 limits)</td>",
    "<td>Dispatch: operations for 3 groups of integer and branch pipelines (3 limits)</td>")
# RE5: "on average" is true for every row; the last two rows are estimates
sub(132, "For the last two rows of the table this holds on average (est.).",
    "The rates of the loop in the last two rows of the table are estimates (est.).")

# ---- line 425, open item, reads at 8 MiB
# X-1: the report calls the two result folders the two sets of the root run
sub(425, "Two runs of 2026-11-02 counted it with four cores busy on two pairs (CPUs 0 to 3, asm loop).",
    "Both complete sets of the root run of 2026-11-02 counted it with four cores busy on two pairs (CPUs 0 to 3, asm loop).")
# RE1: the rates of the runs that gave the counts, and what the files record
sub(425, "In those runs each pair read 62.9 to 63.7 GB/s at the loops, not 78 GB/s.",
    "In the runs that gave these counts the four cores together read 126.0 to 126.2 GB/s at the loops. "
    "That is 63.0 to 63.1 GB/s for one pair on average, not 78 GB/s.")
# RE2: "load" means a read operation in this report
sub(425, "So that count is from another load.",
    "These runs have two busy pairs. They are not runs of hypothesis 2. So that count does not give the share for two partner cores alone.")

# ---- line 429 (RE3): the fourth write rate of the loop compiled from C
sub(429, "With that loop two partner cores write 75.6 GB/s at 8 MiB, and one core alone writes 44.8 GB/s at 8 MiB and at 1 GiB [results/20261030T193108Z/bandwidth.csv].",
    "With that loop two partner cores write 75.6 GB/s at 8 MiB and 63.2 GB/s at 1 GiB, and one core alone writes 44.8 GB/s at 8 MiB and at 1 GiB [results/20261030T193108Z/bandwidth.csv].")

# ---- line 437 (RE4): name the loop, because line 429 now gives the other loop's rate
sub(437, "Two partner cores together wrote 63.2 GB/s at 1 GiB (each core wrote its own buffer of 1 GiB). One core alone wrote 63.0 GB/s.",
    "With the asm loop two partner cores together wrote 63.2 GB/s at 1 GiB (each core wrote its own buffer of 1 GiB). One core alone wrote 63.0 GB/s with the same loop.")

# the file ends with a newline, so the split gives 978 lines and one empty string
assert len(L) == n_lines == 979 and L[-1] == "", len(L)
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, {len(L) - 1} lines")
