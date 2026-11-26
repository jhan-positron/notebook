#!/usr/bin/env python3
"""Section 2.3 group names: add the initiating CPU(s) of every row group, from log.txt of 011 (phases A to E; run 3's lines are the same)."""
path = "/home/jhan/workspace/titan/cache-perf/asimov/gen_perf_core.py"
s = open(path).read()
i, j = s.find("def sec_f1_vs_run3"), s.find("def level_cell")
sec = s[i:j]
REN = {
    "Chains 4 to 128 KiB (L1, L2): read": "Chains 4 to 128 KiB (L1, L2), CPU 2: read",
    "Chains 192 to 384 KiB (the L3's sizes): read": "Chains 192 to 384 KiB (the L3's sizes), CPU 2: read",
    "Fresh chains 512 KiB to 1 MiB: read": "Fresh chains 512 KiB to 1 MiB, CPU 2: read",
    "Fresh chains 1.5 to 4 MiB (the SLC): read": "Fresh chains 1.5 to 4 MiB (the SLC), CPU 2: read",
    "Fresh chains 6 to 32 MiB (DRAM): read": "Fresh chains 6 to 32 MiB (DRAM), CPU 2: read",
    "Flushed 8 MiB chain: read": "Flushed 8 MiB chain, CPU 2: read",
    "OCM, one line per page, per region, CPUs 2 to 8: read (20 rows)": "OCM, one line per page, per region, CPUs 2, 4, 6, 8: read (20 rows)",
    "OCM, one line per page, all five regions, CPUs 2 to 8: read": "OCM, one line per page, all five regions, CPUs 2, 4, 6, 8: read",
    "OCM, every line, all five regions, CPUs 2 to 8: read": "OCM, every line, all five regions, CPUs 2, 4, 6, 8: read",
    "One core, 16 KiB: read, write, copy": "One core, 16 KiB, CPU 2: read, write, copy",
    "One core read, 48 KiB to 32 MiB": "One core, 48 KiB to 32 MiB, CPU 2: read",
    "One core write, 48 KiB to 32 MiB": "One core, 48 KiB to 32 MiB, CPU 2: write",
    "One core copy, 48 KiB to 32 MiB": "One core, 48 KiB to 32 MiB, CPU 2: copy",
    "OCM read, one core, per region and all five": "OCM, one core, per region and all five, CPU 2: read",
    "OCM read, four cores": "OCM, four cores, regions 1 to 4, CPUs 2, 4, 6, 8: read",
    "OCM write, one core": "OCM, one core, all five regions, CPU 2: write",
    "Pair (CPUs 2, 3), 16 KiB: read, write, copy": "Pair, 16 KiB, CPUs 2, 3: read, write, copy",
    "Pair, 48 and 160 KiB: read": "Pair, 48 and 160 KiB, CPUs 2, 3: read",
    "Pair, 48 and 160 KiB: write": "Pair, 48 and 160 KiB, CPUs 2, 3: write",
    "Pair, 48 and 160 KiB: copy": "Pair, 48 and 160 KiB, CPUs 2, 3: copy",
    "One core per cluster, 2 and 16 MiB: read": "One core per cluster, 2 and 16 MiB, CPUs 2, 4, 6, 8: read",
    "One core per cluster, 2 and 16 MiB: write": "One core per cluster, 2 and 16 MiB, CPUs 2, 4, 6, 8: write",
    "One core per cluster, 2 and 16 MiB: copy": "One core per cluster, 2 and 16 MiB, CPUs 2, 4, 6, 8: copy",
    "All eight cores, 2 and 16 MiB: read": "All eight cores, 2 and 16 MiB, CPUs 2 to 9: read",
    "All eight cores, 2 and 16 MiB: write": "All eight cores, 2 and 16 MiB, CPUs 2 to 9: write",
    "All eight cores, 2 and 16 MiB: copy": "All eight cores, 2 and 16 MiB, CPUs 2 to 9: copy",
    "Writer placement, six rows: write": "Writer placement, six CPU sets from CPUs 2 to 9: write",
}
# longest keys first so a short key never matches inside a long one
for old in sorted(REN, key=len, reverse=True):
    assert old in sec, old; sec = sec.replace(old, REN[old])
for new in REN.values(): assert new in sec, new
old_w = 'unit="ratio", xlim=(0.5, 3.0), rh=19, L=430)'; assert sec.count(old_w) == 1
sec = sec.replace(old_w, 'unit="ratio", xlim=(0.5, 3.0), rh=19, L=470)')
old_b = "the writer-placement rows are writes.</li>"; assert sec.count(old_b) == 1
sec = sec.replace(old_b, "the writer-placement rows are writes. Each name also carries the initiating CPU or CPUs, from the command lines (the --cpu or --cpus option; both boots ran the same lines): the 16 KiB and larger bandwidth rows and the chains run on CPU 2, the controls and the OCM chains on CPUs 2, 4, 6 and 8 (one core per cluster), the SLC chains on CPUs 4, 6 and 8, the pair on CPUs 2 and 3, the per-cluster rows on CPUs 2, 4, 6 and 8, the eight-core rows on CPUs 2 to 9, and the six placement sets are CPUs 2,4; 2,8; 2,3; 2,4,6,8; 2,3,4,5; 2,3,8,9 [log.txt of 011, phases A to E].</li>")
s = s[:i] + sec + s[j:]
open(path, "w").write(s); print("patch_sec23c ok")
