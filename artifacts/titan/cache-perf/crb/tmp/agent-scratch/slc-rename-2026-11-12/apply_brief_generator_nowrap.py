#!/usr/bin/env python3
"""Keep short compounds of the level labels on one line (4-way, 8-way, 1 MiB, 16-way, DDR5-8000).
The rename made the first column narrower, and two labels then broke at a hyphen in print. Usage: [--write]"""
import sys
P = "/home/jhan/workspace/titan/cache-perf/crb/make-brief.py"
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n = 0
NW = '<span style="white-space:nowrap">'
def sub(k, old, new):
    global n
    assert L[k - 1].count(old) == 1, (k, L[k - 1].count(old), old[:70])
    L[k - 1] = L[k - 1].replace(old, new); n += 1
sub(171, "<td>L1 data, private, 4-way</td>", f"<td>L1 data, private, {NW}4-way</span></td>")
sub(172, "<td>L2, private, 8-way</td>", f"<td>L2, private, {NW}8-way</span></td>")
sub(173, "<td>SLC (L3), 128 slices of 1 MiB, 16-way</td>", f"<td>SLC (L3), 128 slices of {NW}1 MiB</span>, {NW}16-way</span></td>")
sub(174, "<td>DRAM, 10 ch DDR5-8000</td>", f"<td>DRAM, 10 ch {NW}DDR5-8000</span></td>")
assert len(L) == N0
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n} edits")
