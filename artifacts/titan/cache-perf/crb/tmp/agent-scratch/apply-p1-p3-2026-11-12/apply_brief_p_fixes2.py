#!/usr/bin/env python3
"""Third pass of the step of 2026-11-12, the brief (check4, finding fixes-7).
  - line 181: the range 70 to 73 GB/s covers the runs of 0.5 s and of 2 s only (the runs of 0.2 s gave 68.9 to 70.7 GB/s)
  - line 181: "0 refills, 0 write-backs" had no unit, and the counts are not zero. The report says "0.000 refills for
    writes per line and at most 0.001 write-backs per line" (line 289)
Usage: apply_brief_p_fixes2.py <make-brief.py> [--write]"""
import sys
P = sys.argv[1]
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n = 0


def sub(k, old, new):
    global n
    assert L[k - 1].count(old) == 1, (k, L[k - 1].count(old), old[:70])
    assert "\n" not in new and "{" not in new and "}" not in new   # the line is part of an f-string
    L[k - 1] = L[k - 1].replace(old, new); n += 1


sub(181, "What limits one writer at 8 MiB (70 to 73 GB/s) was not measured. Its lines are not allocated in L1 or L2 (0 refills, 0 write-backs).",
    "What limits one writer at 8 MiB (70 to 73 GB/s in runs of 0.5 s and 2 s) was not measured. Its lines are not allocated in L1 or L2 "
    "(0.000 refills for writes and at most 0.001 write-backs per line).")
assert len(L) == N0
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n} edits")
