#!/usr/bin/env python3
"""For each changed report line: compare the multiset of numbers before and after."""
import re
from collections import Counter
A = open("/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html", encoding="utf-8").read().split("\n")
B = open("/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html", encoding="utf-8").read().split("\n")
num = re.compile(r"\d+(?:[.,]\d+)*")
for i, (a, b) in enumerate(zip(A, B), 1):
    if a == b: continue
    ca, cb = Counter(num.findall(a)), Counter(num.findall(b))
    if ca != cb:
        print(i, "removed:", dict(ca - cb), "added:", dict(cb - ca))
