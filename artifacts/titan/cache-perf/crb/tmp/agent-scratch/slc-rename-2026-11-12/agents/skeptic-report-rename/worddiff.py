#!/usr/bin/env python3
"""Print, for every changed line of the report, the changed segments with context."""
import difflib, sys
A = open("/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html", encoding="utf-8").read().split("\n")
B = open("/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html", encoding="utf-8").read().split("\n")
assert len(A) == len(B), (len(A), len(B))
lo = int(sys.argv[1]) if len(sys.argv) > 1 else 1
hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(A)
CTX = 60
nseg = 0
for i, (a, b) in enumerate(zip(A, B), 1):
    if a == b or not (lo <= i <= hi):
        continue
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        nseg += 1
        print(f"L{i} [{tag}]")
        print("   -", a[max(0, i1 - CTX):i1] + "[[" + a[i1:i2] + "]]" + a[i2:i2 + CTX])
        print("   +", b[max(0, j1 - CTX):j1] + "[[" + b[j1:j2] + "]]" + b[j2:j2 + CTX])
print("segments", nseg)
