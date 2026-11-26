#!/usr/bin/env python3
"""List quoted strings in the body that look like references, and compare with headings / dt entries / bold item names."""
import re, html, sys
P = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
L = open(P, encoding="utf-8").read().split("\n")
def strip(s): return html.unescape(re.sub(r"<[^>]+>", "", s))
heads = []
for i, s in enumerate(L, 1):
    for m in re.finditer(r'<h([1-6])(?: id="([^"]*)")?>(.*?)</h\1>', s):
        heads.append((i, strip(m.group(3))))
dts = []
for i, s in enumerate(L, 1):
    for m in re.finditer(r'<dt>(.*?)</dt>', s):
        dts.append((i, strip(m.group(1))))
bolds = []
for i, s in enumerate(L, 1):
    for m in re.finditer(r'<li><b>(.*?)</b>', s):
        bolds.append((i, strip(m.group(1)).rstrip(".")))
    for m in re.finditer(r'<li>([A-Z][^<.]{3,60})\.', s):
        bolds.append((i, m.group(1)))
htext = {t for _, t in heads}
dparts = set()
for _, t in dts:
    dparts.add(t)
    for p in t.split(","): dparts.add(p.strip())
btext = {t for _, t in bolds}
end = next(i for i, s in enumerate(L, 1) if s.startswith("<script>"))
for i, s in enumerate(L[:end], 1):
    if i < 47 or (55 <= i <= 73): continue
    t = strip(s)
    # crude: find "..." pairs, allow nested heading quotes by also testing heading text directly
    for m in re.finditer(r'(\b[\w\']+\s+)?(\b[\w\']+\s+)?"([^"]{2,120})"', t):
        q = m.group(3); pre = ((m.group(1) or "") + (m.group(2) or "")).strip()
        kind = None
        if q in htext: kind = "HEADING-EXACT"
        elif any(h.startswith(q) for h in htext): kind = "heading-PREFIX of " + repr([h for h in htext if h.startswith(q)][0])
        elif q in dparts: kind = "dt-entry"
        elif q in btext: kind = "item-name"
        if kind or re.search(r'\b(section|sections|See|see|item|table|paragraph|in)\b$', pre):
            print(f"{i}: [{pre}] \"{q}\" -> {kind}")
