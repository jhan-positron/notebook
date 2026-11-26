#!/usr/bin/env python3
"""Check TOC link text against headings, and quoted references against headings."""
import re, html, sys
P = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
L = open(P, encoding="utf-8").read().split("\n")
def strip(s): return html.unescape(re.sub(r"<[^>]+>", "", s))
heads = {}   # id -> (line, level, text)
for i, s in enumerate(L, 1):
    for m in re.finditer(r'<h([1-6])(?: id="([^"]*)")?>(.*?)</h\1>', s):
        heads[m.group(2) or f"noid{i}"] = (i, int(m.group(1)), strip(m.group(3)))
print("headings:", len(heads))
for k, v in heads.items(): print("  ", v[0], "h%d" % v[1], repr(v[2]), "#" + k)
# TOC
toc = []
for i, s in enumerate(L, 1):
    if 55 <= i <= 73:
        for m in re.finditer(r'<a href="#([^"]*)">(.*?)</a>', s):
            toc.append((i, m.group(1), strip(m.group(2))))
print("toc links:", len(toc))
bad = 0
seen = set()
for i, h, t in toc:
    seen.add(h)
    if h not in heads: print("  TOC target missing:", i, h); bad += 1
    elif heads[h][2] != t: print("  TOC text differs: line", i, repr(t), "vs heading line", heads[h][0], repr(heads[h][2])); bad += 1
print("toc mismatches:", bad)
for k, v in heads.items():
    if k not in seen and v[1] in (2, 3): print("  heading not in TOC:", v)
# ids duplicates
ids = re.findall(r'\bid="([^"]*)"', "\n".join(L))
dup = {x for x in ids if ids.count(x) > 1}
print("duplicate ids:", dup)
# all hrefs with # (outside toc)
for i, s in enumerate(L, 1):
    for m in re.finditer(r'href="#([^"]*)"', s):
        if m.group(1) not in ids: print("  dangling href line", i, m.group(1))
    if not (55 <= i <= 73):
        for m in re.finditer(r'<a\b[^>]*>', s): print("  link outside TOC, line", i, m.group(0)[:100])
