#!/usr/bin/env python3
"""Say in three places of the report that "at 8 MiB" / "at 1 GiB" is the buffer size of each thread. Usage: [--write]"""
import sys
P = "/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc/agents/report-rename/replay/report.html"
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n = 0
def sub(k, old, new):
    global n
    assert L[k - 1].count(old) == 1, (k, L[k - 1].count(old), old[:70])
    assert "\n" not in new
    L[k - 1] = L[k - 1].replace(old, new); n += 1
sub(421, "and of two partner cores that write 1 GiB each. This report calls them",
    "and of two partner cores that write 1 GiB each. A size such as 8 MiB or 1 GiB is the size of the buffer of each core. Each core reads or writes its own buffer again and again. This report calls them")
sub(437, "Two partner cores together wrote 63.2 GB/s at 1 GiB. One core alone wrote 63.0 GB/s.",
    "Two partner cores together wrote 63.2 GB/s at 1 GiB (each core wrote its own buffer of 1 GiB). One core alone wrote 63.0 GB/s.")
sub(457, "Cache and buffer sizes use KiB, MiB, GiB (powers of 1024).</dd>",
    "Cache and buffer sizes use KiB, MiB, GiB (powers of 1024). \"At 8 MiB\" or \"at 1 GiB\" gives the size of the buffer of each thread. Each thread reads or writes its own buffer again and again [bench/bandwidth.c, line 4; column bytes_per_thread of the result files]. This report uses 8 MiB for the SLC tests and 1 GiB for the DRAM tests (caption of the first figure in \"Bandwidth per core\").</dd>")
assert len(L) == N0
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n} edits")
