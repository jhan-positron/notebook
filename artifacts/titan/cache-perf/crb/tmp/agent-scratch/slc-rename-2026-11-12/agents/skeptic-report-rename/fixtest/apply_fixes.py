#!/usr/bin/env python3
"""Apply the proposed fixes to a SCRATCH copy only, to test that each old text occurs exactly once in its line."""
import sys
P = sys.argv[1]
assert "/scratchpad/rename_slc/agents/skeptic-report-rename/" in P, "scratch copy only"
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n = 0
def sub(k, old, new):
    global n
    assert L[k - 1].count(old) == 1, (k, L[k - 1].count(old), old[:70])
    assert "\n" not in new
    L[k - 1] = L[k - 1].replace(old, new); n += 1
# RR1 + RR3
sub(457, 'Each thread reads or writes its own buffer again and again [bench/bandwidth.c, line 4; column bytes_per_thread of the result files]. This report uses 8 MiB for the SLC tests and 1 GiB for the DRAM tests (caption of the first figure in "Bandwidth per core").</dd>',
         'Each thread reads or writes its own buffer again and again. A copy thread has two buffers of that size. It reads one and writes the other [bench/bandwidth.c, lines 4 to 6 and 301 to 305; column bytes_per_thread of the result files]. The bandwidth tests with one, two or four threads use 8 MiB per thread for the SLC and 1 GiB per thread for DRAM (caption of the first figure in "Bandwidth per core"). The whole-chip numbers come from runs with 3 MiB per thread for the SLC and 256 MiB per thread for DRAM (caption of the first figure in "Bandwidth of the whole chip").</dd>')
# RR2
sub(296, "DRAM uses 32 to 60 threads, one per pair, 256 MiB each.",
         "DRAM uses 256 MiB per thread: 30 threads spread 4 cores apart for read, 16 threads spread 8 cores apart for write, and 48 threads, one per pair, for copy.")
# RR4
sub(421, "This report calls them the runs of hypothesis 2.", "This report calls these four kinds of run the runs of hypothesis 2.")
# RR5
sub(60,  '>Why older versions said "mesh cache"</a>', '>The mesh, and why older versions said "mesh cache"</a>')
sub(182, '>Why older versions said "mesh cache"</h3>', '>The mesh, and why older versions said "mesh cache"</h3>')
# RR6
sub(297, "The SLC bars are lower bounds (see the scaling chart below).", "The SLC bar is a lower bound (see the scaling chart below).")
# RR7
sub(63, "Where one writer's 73 GB/s limit sits (part 5)</a>", "Where one writer's 73 GB/s limit sits (part 5, 2026-11-02)</a>")
# RR8
sub(125, '(table "Per-core bandwidth" in Record)', '(table "Per-core bandwidth, GB/s (1 thread)" in "Record")')
for k in (183, 251, 259):
    sub(k, '(section "Latency from each core to each slice")', '(section "Latency from each core to each slice (root run)")')
sub(199, 'see "Latency from each core to each slice" below', 'see "Latency from each core to each slice (root run)" below')
sub(454, 'and "Latency from each core to each slice".', 'and "Latency from each core to each slice (root run)".')
for k in (316, 437):
    sub(k, '(section "Where one writer\'s 73 GB/s limit sits")', '(section "Where one writer\'s 73 GB/s limit sits (part 5, 2026-11-02)")')
sub(464, 'See "Cache ways" above.', 'See the section on cache ways above.')
# X-1
sub(52, "a 128 MiB SLC (system level cache, the shared cache that Linux lists as L3) at about 30 ns",
        "a 128 MiB SLC (system level cache, the shared cache in the on-chip mesh interconnect, which Linux lists as L3) at about 30 ns")
assert len(L) == N0
open(P, "w", encoding="utf-8").write("\n".join(L))
print("edits applied to scratch copy:", n, "lines:", N0 - 1)
