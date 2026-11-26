#!/usr/bin/env python3
"""Read-only check of the record: every [RefN] that is used is defined, and Ref30 to Ref36 are used.
Also scans the new lines of the record for semicolons outside code spans."""
import re

R = "/home/jhan/tmp/update-crb-memory-hierarchy.md"
L = open(R, encoding="utf-8").read().split("\n")
defs = {}
for i, l in enumerate(L, 1):
    m = re.match(r"- \[Ref(\d+)\]", l)
    if m:
        defs[int(m.group(1))] = i
used = {}
for i, l in enumerate(L, 1):
    body = l[l.find("]") + 1:] if re.match(r"- \[Ref(\d+)\]", l) else l
    for m in re.finditer(r"\[Ref(\d+)[\],]", body):
        used.setdefault(int(m.group(1)), []).append(i)
print("defined:", sorted(defs))
print("used but not defined:", sorted(set(used) - set(defs)))
print("defined but not used:", sorted(set(defs) - set(used)))
for k in range(30, 37):
    print("Ref%d used at" % k, used.get(k))
new = set([7, 55, 63, 185, 301, 352, 356, 363, 365, 369, 370] + list(range(377, 390)) + list(range(496, 635)) + list(range(666, 673)))
print("semicolons in new lines, outside code spans:")
for i in sorted(new):
    s = re.sub(r"`[^`]*`", "", L[i - 1])
    if ";" in s:
        print("  ", i, [s[max(0, m.start() - 50):m.start() + 30] for m in re.finditer(";", s)][:3])
print("done")
