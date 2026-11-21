#!/usr/bin/env python3
"""Third pass of the step of 2026-11-12: the fixes after the last check (check4: one checker
on the fixes of the second pass and one on the record, each followed by a second checker).
Every edit stays on its physical line, so the report keeps 978 lines. Each edit names the
finding that it answers. The texts are the proposed or corrected texts of the findings,
except where a comment says what differs.
sub(): the old text must occur exactly once in its line.
Usage: apply_report_p_fixes2.py <report.html> [--write]"""
import sys

P = sys.argv[1]
L = open(P, encoding="utf-8").read().split("\n")
assert len(L) == 979 and L[-1] == "", len(L)
n_edits = 0
ASM = "results/followup-20261030T194205Z/asm.csv"
BW = "results/20261030T193108Z/bandwidth.csv"
HEAD_WRITER = "Where one writer's 73 GB/s limit sits (part 5, 2026-11-02)"


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


# ---- line 49 (fixes-8): the change note did not name the entry "flit", which was the author's first request.
# "streaming write" is added to the list of new entries, because this pass adds that entry (fixes-5).
sub(49, '"Words used here" has new entries for credit stall, data stall, back-pressure, write in flight and partner cores.</div>',
    '"Words used here" has new entries for credit stall, data stall, back-pressure, write in flight, streaming write and partner cores. '
    'Its entry "flit" now gives the long form of the word and Arm\'s definition.</div>')

# ---- line 121 (record-20): the 58.7 GB/s is the 2 s run minus the 0.2 s run of one counter set, as line 422 says
sub(121, "For one core alone the two places of counting were measured in one run.",
    "For one core alone the two places of counting were measured in one pair of runs (0.2 s and 2 s).")
# ---- line 121 (fixes-4): "limit" is a maximum of a rate in the rest of the report
sub(121, "The read row has one more limit.", "The read row has one more limitation.")
# ---- line 121 (fixes-3, corrected text of the second checker): the list of the runs that were not converted was not complete
sub(121, "Other runs with two partner cores were not converted. No bus count exists for them. They are the write runs of the loop compiled "
         f"from C (75.6 GB/s at 8 MiB and 63.2 GB/s at 1 GiB) [{BW}] and the copy runs of the asm loop (80.9 GB/s at 8 MiB and 72.5 GB/s at "
         f"1 GiB, counted as bytes read plus bytes written) [{ASM}]. So these runs were not compared with the estimate.",
    "Other runs with two partner cores at 8 MiB or 1 GiB were not converted. No bus count exists for them. So these runs were not compared "
    f"with the estimate. The write runs of the loop compiled from C gave 75.6 GB/s at 8 MiB and 63.2 GB/s at 1 GiB [{BW}]. The copy runs of "
    f"the asm loop gave 80.9 GB/s at 8 MiB and 72.5 GB/s at 1 GiB [{ASM}]. The copy runs of the loop compiled from C gave 77.9 GB/s at 8 MiB "
    f"and 72.4 GB/s at 1 GiB [{BW}]. A copy rate counts bytes read plus bytes written. The read runs at 1 GiB gave 52.6 GB/s with the loop "
    'compiled from C and 56.7 GB/s with the asm loop (table in "The pair finding").')

# ---- line 213 (fixes-X1): the two ranges belong to the best repetition of each run, as P2 said
sub(213, "62.4 to 67.1 GB/s (seven runs).", "62.4 to 67.1 GB/s (seven runs, best repetition of each).")
sub(213, "37.8 to 40.3 GB/s (five runs).", "37.8 to 40.3 GB/s (five runs, best repetition of each).")

# ---- line 289 (fixes-5): the nearest table above the paragraph is the placement table, which holds no refills
sub(289, "at most 0.001 write-backs per line (table above).", "at most 0.001 write-backs per line (first table of this section).")
# ---- line 289 (fixes-1, fixes-X2): the list holds three rates of the loop compiled from C, and this rate had no run and no source
sub(289, "All rates in this list are from the asm write loop. With the write loop compiled from C one writer alone writes 44.8 GB/s at 8 MiB "
         "and at 1 GiB.",
    "The rates in this list are from the asm write loop, except where a sentence names the loop compiled from C. With the write loop "
    f"compiled from C one writer alone wrote 44.8 GB/s at 8 MiB and at 1 GiB (CPU 0, 2026-10-30) [{BW}].")
# ---- line 289 (fixes-1): the counts per second are differences of two runs, and one rate of the item is from the runs of 0.2 s
sub(289, "All rates of part 5 in this list are from the runs of 2 s. The nine runs of 0.2 s of one writer gave 68.9 to 70.7 GB/s.",
    "The nine runs of 0.2 s of one writer gave 68.9 to 70.7 GB/s. The other write rates of part 5 in this list are also from the runs of "
    "2 s. Each count per second of part 5 is the count of the 2 s run minus the count of the 0.2 s run, divided by the difference of the "
    "two counting times.")
# ---- line 289 (fixes-6): the faster writer is above 61.0 GB/s in 7 of the 9 runs
sub(289, "each of the two writers writes between 60 and 61 GB/s.", "each of the two writers writes 60.15 to 61.34 GB/s.")
# ---- line 289 (fixes-2): the per-core read sweep did run CPUs 4, 6 and 8 alone
sub(289, "No run measured CPU 4, 6 or 8 alone.", "No run measured CPU 4, 6 or 8 writing alone.")
# ---- line 289 (fixes-6): the 0.005 is the count of mesh 0 (0.0054 per line), and the colon joined two statements
sub(289, "These counts stay small: with four busy ports the home nodes show 0.005 data stalls per line written.",
    "These counts stay small. With four busy ports the home nodes of mesh 0 show 0.005 data stalls per line written.")

# ---- line 429 (remark in the verdict of fixes-3): "Open items" lists the same runs as line 121. Without this edit the two lists differ.
sub(429, "counted as bytes read plus bytes written [asm.csv]. No bus count exists for a copy run.",
    "counted as bytes read plus bytes written [asm.csv]. With the loop compiled from C the copy runs of two partner cores gave 77.9 GB/s "
    f"at 8 MiB and 72.4 GB/s at 1 GiB [{BW}]. No bus count exists for a copy run.")
sub(429, "No bus count exists for that loop. Also not explained:",
    "No bus count exists for that loop. The read runs of two partner cores at 1 GiB were not checked either. They gave 52.6 GB/s with the "
    'loop compiled from C and 56.7 GB/s with the asm loop (table in "The pair finding"). No bus count exists for a read at 1 GiB. '
    "Also not explained:")

# ---- line 451 (fixes-5): the term stands in lines 268, 289, 324 and 974 and had no entry. The pointer quotes the full heading
# (the proposed text had the short form, which is the defect of row F26 of the record).
sub(451, "<dt>write in flight</dt><dd>A write that the core has sent and that is not yet complete.</dd>",
    "<dt>write in flight</dt><dd>A write that the core has sent and that is not yet complete.</dd><dt>streaming write</dt><dd>A write "
    "whose line is not allocated in L1 or L2. Part 5 counted 0.000 refills for writes per line with the asm write loop. The counts are in "
    f'section "{HEAD_WRITER}".</dd>')

assert len(L) == 979 and L[-1] == "", len(L)
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, {len(L) - 1} lines")
