#!/usr/bin/env python3
"""Fixes that the check of 2026-11-12 confirmed in text written or rewritten by the rename and the buffer-size edit,
and three corrections of the open item. Usage: apply_report_fixes.py <report.html> [--write]"""
import sys
P = sys.argv[1]
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n = 0
def sub(k, old, new):
    global n
    assert L[k - 1].count(old) == 1, (k, L[k - 1].count(old), old[:70])
    assert "\n" not in new
    L[k - 1] = L[k - 1].replace(old, new); n += 1

# first use of the term, and the Short version (the reader must learn where the SLC sits)
sub(49, "the SLC (L3) and DRAM on the Phoenix", "the SLC (system level cache, L3) and DRAM on the Phoenix")
sub(52, "a 128 MiB SLC (system level cache, the shared cache that Linux lists as L3) at about 30 ns",
    "a 128 MiB SLC (system level cache, the shared cache in the on-chip mesh interconnect, which Linux lists as L3) at about 30 ns")
# the heading must say that the section describes the mesh
sub(60, ">Why older versions said \"mesh cache\"</a>", ">The mesh, and why older versions said \"mesh cache\"</a>")
sub(182, ">Why older versions said \"mesh cache\"</h3>", ">The mesh, and why older versions said \"mesh cache\"</h3>")
sub(179, "call it the mesh cache, and", "call it the \"mesh cache\", and")
sub(139, "[CMN S3 TRM, Table 1-9 page 31]", "[CMN S3 TRM, Table 1-9 pages 31 to 32]")
sub(297, "The SLC bars are lower bounds (see the scaling chart below).", "The SLC bar is a lower bound (see the scaling chart below).")
# word list: keep "there" next to the sentence on the place
sub(454, "It sits in the on-chip mesh interconnect (Arm CMN). Versions of this report before 2026-11-12 called it the \"mesh cache\". Mesh counters confirm",
    "Versions of this report before 2026-11-12 called it the \"mesh cache\". It sits in the on-chip mesh interconnect (Arm CMN). Mesh counters confirm")
# buffer size: the general sentence was wrong for the whole-chip tests, and a copy thread has two buffers
sub(457, "Each thread reads or writes its own buffer again and again [bench/bandwidth.c, line 4; column bytes_per_thread of the result files]. This report uses 8 MiB for the SLC tests and 1 GiB for the DRAM tests (caption of the first figure in \"Bandwidth per core\").</dd>",
    "Each thread reads or writes its own buffer again and again. A copy thread has two buffers of that size. It reads one and writes the other [bench/bandwidth.c, lines 4 to 6 and 301 to 306; column bytes_per_thread of the bandwidth result files, for example results/followup-20261030T194205Z/asm.csv]. The bandwidth tests with one, two or four threads use 8 MiB per thread for the SLC and 1 GiB per thread for DRAM [bench/run_crb.sh, lines 83 to 89; caption of the first figure in \"Bandwidth per core\"]. The whole-chip tests use 3 MiB per thread for the SLC and 256 MiB per thread for DRAM (caption of the first figure in \"Bandwidth of the whole chip\").</dd>")
# open item: three corrections
sub(421, "of two partner cores that write 8 MiB each, of one core that writes 1 GiB, and of two partner cores that write 1 GiB each.",
    "of two partner cores that write 8 MiB each with the asm loop, of one core that writes 1 GiB with the asm loop, and of two partner cores that write 1 GiB each.")
sub(421, "This report calls them the runs of hypothesis 2.", "This report calls these four kinds of run the runs of hypothesis 2.")
sub(118, "No run counted this share for two partner cores.", "No run counted this share with only two partner cores busy.")
sub(425, "No run counted the share for two partner cores.",
    "No run counted the share with only two partner cores busy. Two runs of 2026-11-02 counted it with four cores busy on two pairs (CPUs 0 to 3, asm loop). They gave 0.82 accesses to the SLC per line [case asmread-8M-4 in results/sudo-20261102T054936Z/writebw.csv and in results/sudo-20261102T040631Z/writebw.csv]. In those runs each pair read 62.9 to 63.7 GB/s at the loops, not 78 GB/s. So that count is from another load.")
sub(429, "No bus count exists for a copy run.",
    "No bus count exists for a copy run. The write runs of the loop compiled from C were not checked either. With that loop two partner cores write 75.6 GB/s at 8 MiB, and one core alone writes 44.8 GB/s at 8 MiB and at 1 GiB [results/20261030T193108Z/bandwidth.csv]. No bus count exists for that loop.")
assert len(L) == N0
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n} edits")
