#!/usr/bin/env python3
"""Check that given strings occur exactly once in the given line of the after-file, and whether the before-file has them too."""
A = open("/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html", encoding="utf-8").read().split("\n")
B = open("/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html", encoding="utf-8").read().split("\n")
checks = [
 (63,  "Where one writer's 73 GB/s limit sits (part 5)</a>"),
 (269, "Where one writer's 73 GB/s limit sits (part 5, 2026-11-02)</h3>"),
 (125, '(table "Per-core bandwidth" in Record)'),
 (183, '(section "Latency from each core to each slice")'),
 (199, 'see "Latency from each core to each slice" below'),
 (251, '(section "Latency from each core to each slice")'),
 (259, '(section "Latency from each core to each slice")'),
 (454, 'and "Latency from each core to each slice".'),
 (316, '(section "Where one writer\'s 73 GB/s limit sits")'),
 (437, '(section "Where one writer\'s 73 GB/s limit sits")'),
 (464, 'See "Cache ways" above.'),
 (192, 'See "Latency from each core to each slice (root run)" below.'),
 (297, "The SLC bars are lower bounds (see the scaling chart below)."),
 (296, "DRAM uses 32 to 60 threads, one per pair, 256 MiB each."),
 (421, "This report calls them the runs of hypothesis 2."),
 (457, 'Each thread reads or writes its own buffer again and again [bench/bandwidth.c, line 4; column bytes_per_thread of the result files]. This report uses 8 MiB for the SLC tests and 1 GiB for the DRAM tests (caption of the first figure in "Bandwidth per core").</dd>'),
 (60,  '>Why older versions said "mesh cache"</a>'),
 (182, '>Why older versions said "mesh cache"</h3>'),
 (52,  "a 128 MiB SLC (system level cache, the shared cache that Linux lists as L3) at about 30 ns"),
 (49,  "Explanation sections (pipelines, cache ways, mesh and pair port) added 2026-11-01"),
 (889, "'mesh: 64 slices of 1 MiB'"),
 (139, "[CMN S3 TRM, Table 1-9 page 31]"),
 (265, "Footprints: L1 = 32 KiB, L2 = 1 MiB, SLC = 8 MiB, DRAM = 1 GiB per thread. Copy counts bytes read plus bytes written."),
 (385, "<th>Level (footprint)</th>"),
 (179, "why did older versions of this report call it the mesh cache"),
]
for n, s in checks:
    print(f"line {n}: after x{B[n-1].count(s)}  before x{A[n-1].count(s)}  | {s[:90]}")
