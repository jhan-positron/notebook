#!/usr/bin/env python3
"""List every occurrence of 'mesh' (any case) in the report with context."""
import re, sys
P = "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
L = open(P, encoding="utf-8").read().split("\n")
lo = int(sys.argv[1]); hi = int(sys.argv[2]); ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 45
n = 0
for i, s in enumerate(L, 1):
    for m in re.finditer(r"mesh", s, re.I):
        n += 1
        if lo <= i <= hi:
            a, b = m.start(), m.end()
            print(f"{i}: …{s[max(0,a-ctx):a]}[{s[a:b]}]{s[b:b+ctx]}…")
print("total occurrences in file:", n)
