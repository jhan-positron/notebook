#!/usr/bin/env python3
"""Compare script lines before/after with string literal contents and // comments blanked. Also compare tags outside scripts."""
import re
A = open("/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html", encoding="utf-8").read().split("\n")
B = open("/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html", encoding="utf-8").read().split("\n")
def blank(line):
    out = []; i = 0; n = len(line); strs = []
    while i < n:
        c = line[i]
        if c == "/" and i + 1 < n and line[i+1] == "/":
            out.append("//"); strs.append(("comment", line[i+2:])); break
        if c in "'\"`":
            j = i + 1; buf = []
            while j < n and line[j] != c:
                if line[j] == "\\": buf.append(line[j:j+2]); j += 2
                else: buf.append(line[j]); j += 1
            out.append(c + c); strs.append(("string", "".join(buf))); i = j + 1; continue
        out.append(c); i += 1
    return "".join(out), strs
s0 = next(i for i, s in enumerate(B) if s.startswith("<script>"))
print("script starts at line", s0 + 1)
bad = 0; nstr = 0; ncom = 0
for i in range(s0, len(B)):
    if A[i] == B[i]: continue
    ca, sa = blank(A[i]); cb, sb = blank(B[i])
    if ca != cb or len(sa) != len(sb):
        bad += 1; print("CODE DIFF at line", i + 1)
    else:
        for (ka, va), (kb, vb) in zip(sa, sb):
            if va != vb:
                if ka == "string": nstr += 1
                else: ncom += 1
                print(f"  line {i+1} {ka}: {va[:70]!r} -> {vb[:70]!r}")
print("code diffs:", bad, "changed strings:", nstr, "changed comments:", ncom)
# tags outside script
def tags(lines):
    t = "\n".join(lines[:s0])
    return re.findall(r"<(/?[a-zA-Z][a-zA-Z0-9]*)", t)
ta, tb = tags(A), tags(B)
print("tags before/after:", len(ta), len(tb), "same sequence:", ta == tb)
# attribute comparison outside script
def attrs(lines):
    t = "\n".join(lines[:s0])
    return re.findall(r'\s([a-zA-Z-]+)="([^"]*)"', t)
aa, ab = attrs(A), attrs(B)
print("attrs:", len(aa), len(ab))
for x, y in zip(aa, ab):
    if x != y: print("  attr changed:", x[0], "|", x[1][:80], "->", y[1][:80])
