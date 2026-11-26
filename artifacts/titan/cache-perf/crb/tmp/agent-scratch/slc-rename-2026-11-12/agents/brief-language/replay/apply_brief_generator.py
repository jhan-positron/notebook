#!/usr/bin/env python3
"""Rename "mesh cache" to "SLC" in make-brief.py, the generator of the brief. Usage: apply_brief_generator.py [--write]"""
import sys
P = "/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc/agents/brief-language/replay/make-brief.py"
L = open(P, encoding="utf-8").read().split("\n")
N0 = len(L); n = 0
def sub(k, old, new):
    global n
    assert L[k - 1].count(old) == 1, (k, L[k - 1].count(old), old[:70])
    assert "\n" not in new
    L[k - 1] = L[k - 1].replace(old, new); n += 1
sub(129, 'aria-label="Per-core mesh-cache latency"', 'aria-label="Per-core SLC latency"')
sub(173, "<tr><td>Mesh cache (SLC), 128 slices of 1 MiB, 16-way</td>", "<tr><td>SLC (L3), 128 slices of 1 MiB, 16-way</td>")
sub(176, "Cycles at 2.8 GHz.</p>", "Cycles at 2.8 GHz. SLC: Arm's system level cache, in the mesh. Linux lists it as L3.</p>")
sub(180, "read 78 GB/s from the mesh cache; two non-partners", "read 78 GB/s from the SLC; two non-partners")
sub(185, "<li>Streaming writes largely bypass the mesh cache:", "<li>Streaming writes largely bypass the SLC:")
sub(185, 'The 73 GB/s "mesh write" is mostly the DRAM write path.', 'The 73 GB/s "SLC write" is mostly the DRAM write path.')
sub(187, "<li>Concurrent reads from the mesh cache:", "<li>Concurrent reads from the SLC:")
sub(197, "Average mesh-cache latency by core:", "Average SLC latency by core:")
assert len(L) == N0
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n} edits")
