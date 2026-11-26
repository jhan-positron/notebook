#!/usr/bin/env python3
"""Section 2.3: the three hypotheses rewritten as short bullets (Jibin, 2026-11-08)."""
path = "/home/jhan/workspace/titan/cache-perf/asimov/gen_perf_core.py"
s = open(path).read()
a = s.find('<li>{hyp(" More reads in flight per cluster.")}')
b = s.find('<li><span class="gap">ruled out</span> <b>The build.</b>')
assert 0 < a < b
new = '''<li>{hyp(" More reads in flight per cluster.")}
<ul>
<li><b>The idea.</b> In run 3's snoop-filter-only mode every L2 miss goes straight to the mesh. In the full mode the L3 handles the miss first. The L3's miss handling may keep more read requests open at once (in flight: issued and not yet returned). With more requests in flight, a stream of independent reads waits less per line, wherever the lines come from: the L3, the SLC, OCM or DRAM.</li>
<li><b>Why only the reads moved.</b> A chain has one load in flight, so it gains nothing. A write is posted (the core does not wait for it), so it already overlaps. Every read stream of 48 KiB and above rose: one core, the pair, the OCM reads, the multi-core reads.</li>
<li><b>What else fits.</b> The refills per line are the same on both boots. The mesh requests are nearly the same. The chains of 1.5 MiB and above hold within 4 %. The one-core writes and the placement rows hold within 0.3 %, the multi-core writes of 2 MiB and above within 7 %. The eight-reader row shows a limit shared inside each cluster.</li>
<li><b>The test.</b> Count the read requests in flight at the DSU's mesh port during the same one-core read, once on an L3-on boot and once on an L3-off boot. This needs a mesh PMU event for requests in flight (to be checked in the CMN-S3 event list). No file on disk counts requests in flight.</li>
</ul></li>
<li>{hyp(" The prefetcher's requests are the ones that overlap more.")}
<ul>
<li><b>The idea.</b> The streams run on the hardware prefetcher. It issues the same number of requests per line on both boots ({e32['l2d_refill_l1dhwprf']:.2f} L2 refills caused by the L1 prefetcher per line on boot E, {c32['l2d_refill_l1dhwprf']:.2f} on boot C). The counters do not say how many of those requests it keeps open at once. The full L3 mode may let it keep more open.</li>
<li><b>What is known.</b> With the prefetchers off and the L3 off, boots B and D read {bd32[0]:.2f} and {bd32[1]:.2f} GB/s at 32 MiB. That is {64 / bd32[0]:.1f} ns per 64-byte line, about two lines per DRAM load of {lv(33554432, 'fresh')['ns_boot']['B']:.1f} ns. Without the prefetcher there is almost no overlap.</li>
<li><b>The test.</b> Run run 3's one-core read lines with the prefetchers off on an L3-on boot (boot F2's firmware; F2 ran run_cme.sh only). A rate near {bd32[0]:.1f} GB/s says the rise needs the prefetcher. A rate well above it says the L3 path overlaps demand misses on its own.</li>
</ul></li>
<li>{hyp(" A per-cluster limit, not a per-core one.")}
<ul>
<li><b>The idea.</b> The limit on reads in flight sits in the cluster (the DSU), not in the core. Two cores of one cluster then share it. Two cores of two clusters do not.</li>
<li><b>What fits.</b> Four readers on four clusters each read {per4[0] * 100:.1f} to {per4[1] * 100:.1f} % of one reader's rate: no sharing across clusters. Eight readers, two per cluster, get {rd8['agg'] / 4:.0f} GB/s est. per cluster, near one reader's rate: sharing inside the cluster.</li>
<li><b>The test.</b> Two readers on two clusters against two readers in one cluster, 16 MiB each, the same command otherwise. The nearest row on disk is the pair at 160 KiB ({M1[('read', 163840, 2)]['agg']:.1f} GB/s on F1 against {m3('read', 163840, 2):.1f} on run 3). It sits in the L2 and L3, not in DRAM, so it does not settle this.</li>
</ul></li>
'''
s = s[:a] + new + s[b:]
open(path, "w").write(s); print("patch_sec23e ok")
