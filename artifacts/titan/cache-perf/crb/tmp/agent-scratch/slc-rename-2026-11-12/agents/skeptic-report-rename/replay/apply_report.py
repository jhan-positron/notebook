#!/usr/bin/env python3
"""Rename "mesh cache" to "SLC" / "SLC (L3)" in the report.
Every edit names its line and its old text. The old text must occur exactly once in that line.
No line is added or removed. Element ids and href values are not changed.
Usage: apply_report.py [--write]"""
import sys

P = "/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc/agents/skeptic-report-rename/replay/report.html"
L = open(P, encoding="utf-8").read().split("\n")
N0 = len(L)
n_edits = 0


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


# ---- sub-header and Short version
sub(49, "the mesh cache and DRAM on the Phoenix", "the SLC (L3) and DRAM on the Phoenix")
sub(49, "the explanation of the read loop compiled from C.</div>",
    "the explanation of the read loop compiled from C. Renamed on 2026-11-12: the cache in the mesh is now called SLC (system level cache, Arm's name). Linux lists it as L3. Earlier versions of this report said \"mesh cache\".</div>")
sub(52, "a 128 MiB mesh cache at about 30 ns", "a 128 MiB SLC (system level cache, the shared cache that Linux lists as L3) at about 30 ns")
sub(52, "67 GB/s from the mesh cache and 30 GB/s", "67 GB/s from the SLC and 30 GB/s")
sub(52, "at least 0.62 TB/s from the mesh cache and 533", "at least 0.62 TB/s from the SLC and 533")
sub(52, "under-report the mesh-cache latency", "under-report the SLC latency")

# ---- table of contents (link text only, the href values stay)
sub(60, ">The mesh cache and the pair port</a>", ">The SLC (L3) and the pair port</a>")
sub(60, ">Why \"mesh cache\"</a>", ">Why older versions said \"mesh cache\"</a>")
sub(60, ">Is the pair port how the mesh cache is reached?</a>", ">Is the pair port how the SLC is reached?</a>")
sub(62, ">Mesh-cache latency by core position</a>", ">SLC latency by core position</a>")
sub(64, ">Mesh cache: not saturated yet</a>", ">SLC: not saturated yet</a>")
sub(65, ">Why the mesh-cache row uses 40 threads, not 120</a>", ">Why the SLC row uses 40 threads, not 120</a>")

# ---- first figure, its caption and its source table
sub(77, "pair port, mesh cache, DRAM.", "pair port, SLC (L3), DRAM.")
sub(86, ">mesh cache 128 MiB *</text>", ">SLC (L3) 128 MiB *</text>")
sub(97, "Mesh-cache bandwidth is an estimated lower bound", "SLC bandwidth is an estimated lower bound")
sub(97, "of a 1.38 TB/s run to the mesh cache (the rest hit L2)", "of a 1.38 TB/s run to the SLC (the rest hit L2)")
sub(110, "read 78 GB/s from the mesh cache, two non-partners", "read 78 GB/s from the SLC, two non-partners")
sub(111, "<td>mesh cache 128 MiB, shared by 128 cores, 16-way</td>", "<td>SLC (L3) 128 MiB, shared by 128 cores, 16-way</td>")
sub(113, "(mesh cache plus L2 hits)", "(SLC plus L2 hits)")
sub(119, "<td>Spec row, mesh cache: unknown</td>", "<td>Spec row, SLC (L3): unknown</td>")

# ---- cache ways
sub(139, "The mesh cache's 16 ways match one of the two values Arm offers for the system level cache, 12 or 16",
    "The SLC's 16 ways match one of the two values Arm offers for it, 12 or 16")
sub(144, "<tr><td>mesh cache</td>", "<tr><td>SLC (L3)</td>")

# ---- section on the SLC and the pair port
sub(178, ">The mesh cache and the pair port</h2>", ">The SLC (L3) and the pair port</h2>")
sub(179, "is the mesh cache an L3 cache, why is it called the mesh cache, and is the pair port the way the mesh cache is reached.",
    "is the SLC an L3 cache, why did older versions of this report call it the mesh cache, and is the pair port the way the SLC is reached.")
sub(182, ">Why \"mesh cache\"</h3>", ">Why older versions said \"mesh cache\"</h3>")
sub(183, "This report calls it the mesh cache for that reason: an L2 miss travels across the mesh to the home node of its address, or to a local proxy of it.",
    "An L2 miss travels across the mesh to the home node of its address, or to a local proxy of it. Versions of this report before 2026-11-12 called the SLC the \"mesh cache\" for that reason. The report now uses Arm's name.")
sub(211, ">Is the pair port how the mesh cache is reached?</h3>", ">Is the pair port how the SLC is reached?</h3>")
sub(212, "so the mesh cache, the other cores' caches and DRAM are all behind it", "so the SLC, the other cores' caches and DRAM are all behind it")
sub(213, "each streaming its own buffer from the mesh cache, and added", "each streaming its own buffer from the SLC, and added")
sub(214, "1.6 to 1.7 times more mesh-cache bandwidth than", "1.6 to 1.7 times more SLC bandwidth than")

# ---- latency sections
sub(230, "The 29 to 30 ns \"mesh cache\" latency in the hierarchy figure", "The 29 to 30 ns SLC latency in the hierarchy figure")
sub(230, "(section \"Mesh-cache latency by core position\")", "(section \"SLC latency by core position\")")
sub(232, "while the loads were served at mesh latency", "while the loads were served at SLC latency")
sub(233, "That is why one buffer sees 64 MiB of mesh cache:", "That is why one buffer sees 64 MiB of SLC:")
sub(235, "hides most of the mesh-cache latency", "hides most of the SLC latency")
sub(245, "<tr><td>mesh cache, 128 MiB</td>", "<tr><td>SLC, 128 MiB</td>")
sub(245, "mesh counters: 1.03 mesh-cache accesses and", "mesh counters: 1.03 SLC accesses and")
sub(246, "<tr><td>mesh cache, corrected</td>", "<tr><td>SLC, corrected</td>")
sub(251, "<p>Mesh-cache misses for a single buffer", "<p>SLC misses for a single buffer")
sub(255, ">Mesh-cache latency by core position</h3>", ">SLC latency by core position</h3>")
sub(258, "one-thread mesh-cache read bandwidth per CPU", "one-thread SLC read bandwidth per CPU")
sub(259, "<b>Mesh-cache latency depends on where the core sits", "<b>SLC latency depends on where the core sits")

# ---- bandwidth of one core
sub(265, "L2 = 1 MiB, mesh cache = 8 MiB, DRAM = 1 GiB per thread", "L2 = 1 MiB, SLC = 8 MiB, DRAM = 1 GiB per thread")
sub(266, "From the mesh cache and DRAM the two loops agree", "From the SLC and DRAM the two loops agree")
sub(266, "81 % of lines coming from the mesh cache and 19 % from L2, so the mesh delivers about 54 GB/s",
    "81 % of lines coming from the SLC and 19 % from L2, so the SLC delivers about 54 GB/s")
sub(268, "the \"mesh write\" row is not a mesh-cache number", "the \"SLC write\" row is not an SLC number")
sub(268, "bypass allocation in the mesh cache and go on to memory", "bypass allocation in the SLC and go on to memory")
sub(268, "not a mesh-cache figure. The \"mesh read\" row is a mesh number:", "not an SLC figure. The \"SLC read\" row is an SLC number:")

# ---- bandwidth of the whole chip
sub(296, "Mesh cache uses 40 threads, one per pair", "SLC uses 40 threads, one per pair")
sub(296, "attribute to the mesh cache is shown, and mesh write and copy could not be attributed (write streams register as mesh misses)",
    "attribute to the SLC is shown, and SLC write and copy could not be attributed (write streams register as SLC misses)")
sub(297, "The mesh-cache bars are lower bounds", "The SLC bars are lower bounds")
sub(299, ">Mesh cache: not saturated yet</h3>", ">SLC: not saturated yet</h3>")
sub(302, "of which the mesh cache itself delivered about 0.62 TB/s", "of which the SLC itself delivered about 0.62 TB/s")
sub(302, "show 0.45 mesh accesses per line read", "show 0.45 SLC accesses per line read")
sub(302, "The mesh-served part was still rising with thread count", "The SLC-served part was still rising with thread count")
sub(302, "and do not isolate the mesh either", "and do not isolate the SLC either")
sub(307, "a 1 MiB slice of the mesh cache, and 5 DDR5-8000 channels", "a 1 MiB slice of the SLC, and 5 DDR5-8000 channels")
sub(316, "so the mesh cache does not keep the written lines", "so the SLC does not keep the written lines")
sub(320, "Mesh: 40 threads on CPUs 0, 2, 4, ... 78", "SLC: 40 threads on CPUs 0, 2, 4, ... 78")
sub(324, "Mesh: no number, because streaming writes are not kept in the mesh cache;", "SLC: no number, because streaming writes are not kept in the SLC;")
sub(330, "<tr><td>Read, 1 core, mesh</td>", "<tr><td>Read, 1 core, SLC</td>")
sub(333, "<tr><td>Write, 1 core, \"mesh\"</td>", "<tr><td>Write, 1 core, \"SLC\"</td>")
sub(336, "<tr><td>Read, whole chip, mesh</td>", "<tr><td>Read, whole chip, SLC</td>")
sub(342, ">Why the mesh-cache row uses 40 threads, not 120</h3>", ">Why the SLC row uses 40 threads, not 120</h3>")
sub(343, "<p>The mesh-cache test needs two things at once", "<p>The SLC test needs two things at once")
sub(343, "All buffers together must fit in the mesh cache, or", "All buffers together must fit in the SLC, or")
sub(343, "and the mesh-served part was still rising at 40", "and the SLC-served part was still rising at 40")

# ---- the pair finding and the result tables
sub(377, "(above L2, inside the mesh cache)", "(above L2, inside the SLC)")
sub(380, "1.6 to 1.7 times the mesh bandwidth of a pair", "1.6 to 1.7 times the SLC bandwidth of a pair")
sub(388, "<tr><td>mesh cache (8 MiB)</td>", "<tr><td>SLC (8 MiB)</td>")
sub(396, "<tr><td>mesh cache (lower bound)</td><td>≥ 620 mesh-served (1,385 total with L2 hits)</td>",
    "<tr><td>SLC (lower bound)</td><td>≥ 620 SLC-served (1,385 total with L2 hits)</td>")
sub(396, "99 % of its mesh accesses were misses", "99 % of its SLC accesses were misses")
sub(401, "mesh scaling <code>slc-20261030T194835Z</code>", "SLC scaling <code>slc-20261030T194835Z</code>")
sub(408, "<li>The mesh-cache latency and bandwidth rows", "<li>The SLC latency and bandwidth rows")

# ---- open items
sub(416, "Spec throughput of the pair port and the mesh cache.</b>", "Spec throughput of the pair port and the SLC.</b>")
sub(425, "0.83 accesses to the mesh cache per line, counted at the home nodes", "0.83 accesses to the SLC per line, counted at the home nodes")
sub(437, "\"For DRAM streams the port is not the limit\" (section \"Is the pair port how the mesh cache is reached?\")",
    "\"For DRAM streams the port is not the limit\" (section \"Is the pair port how the SLC is reached?\")")
sub(437, "on traffic beyond L2\" (section \"Is the pair port how the mesh cache is reached?\")",
    "on traffic beyond L2\" (section \"Is the pair port how the SLC is reached?\")")
sub(438, "<li><b>Mesh cache.</b>", "<li><b>SLC.</b>")

# ---- words used here
sub(454, "<dt>mesh cache (SLC)</dt><dd>The 128 MiB cache that Linux reports as \"L3\", shared by all 128 cores. It sits in the on-chip mesh interconnect (Arm CMN), and Arm calls it the system level cache (SLC). Mesh counters confirm",
    "<dt>SLC (L3)</dt><dd>The system level cache. That is Arm's name for the 128 MiB cache that all 128 cores share. Linux reports it as \"L3\". It sits in the on-chip mesh interconnect (Arm CMN). Versions of this report before 2026-11-12 called it the \"mesh cache\". Mesh counters confirm")
sub(454, "See \"The mesh cache and the pair port\" and", "See \"The SLC (L3) and the pair port\" and")
sub(455, "and already in the mesh cache are served", "and already in the SLC are served")
sub(465, "64 mesh-cache slices, and 5 DDR5 channels", "64 SLC slices, and 5 DDR5 channels")
sub(466, "holds a slice of the mesh cache. CAL =", "holds a slice of the SLC. CAL =")
sub(466, "See \"The mesh cache and the pair port\" above.", "See \"The SLC (L3) and the pair port\" above.")

# ---- labels drawn by script (string contents and two comments only)
sub(492, "'mesh cache 128 MiB'", "'SLC (L3) 128 MiB'")
sub(503, "'mesh cache: 30 ns (85 cycles)'", "'SLC: 30 ns (85 cycles)'")
sub(513, "['mesh read', 67.0, 67.5]", "['SLC read', 67.0, 67.5]")
sub(513, "['mesh write', 44.8, 73.2]", "['SLC write', 44.8, 73.2]")
sub(513, "['mesh copy', 50.0, 55.4]", "['SLC copy', 50.0, 55.4]")
sub(534, "['mesh read ≥', 0.62]", "['SLC read ≥', 0.62]")
sub(548, "// Mesh cache scaling", "// SLC scaling")
sub(730, "ns per load (mesh cache)'", "ns per load (SLC)'")
sub(731, "GB/s (mesh cache)'", "GB/s (SLC)'")
sub(851, "'Each holds one slice of the mesh cache.'", "'Each holds one slice of the SLC.'")
sub(908, "4 mesh slice, 5 DDR", "4 SLC slice, 5 DDR")
sub(909, "'pair port', 'mesh slice', 'DDR5'", "'pair port', 'SLC slice', 'DDR5'")
sub(959, "title: 'Mesh cache: 67 GB/s (8 MiB buffer)'", "title: 'SLC: 67 GB/s (8 MiB buffer)'")
sub(964, "title: '\"Mesh\": 73 GB/s (8 MiB buffer) goes to DRAM'", "title: '\"SLC\": 73 GB/s (8 MiB buffer) goes to DRAM'")
sub(969, "title: 'Mesh cache: ≥ 0.62 TB/s of 1.38, 40 threads'", "title: 'SLC: ≥ 0.62 TB/s of 1.38, 40 threads'")
sub(974, "title: 'Mesh cache: no number (writes are not kept)'", "title: 'SLC: no number (writes are not kept)'")

assert len(L) == N0
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, {N0} lines")
