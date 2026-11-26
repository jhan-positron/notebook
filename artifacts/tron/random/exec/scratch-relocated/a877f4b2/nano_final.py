#!/usr/bin/env python3
"""Nano txt vs md. Normalization deletes every 'f+[il]?' run on both sides so that
field / feld / eld, offset / ofset / oset, configured / confgured / congured all compare equal.
Page markers matched with or without spaces. Per-page copyright footer removed."""
import sys, re, unicodedata, os
from collections import Counter
root = sys.argv[1]; N = 8
FOOT = re.compile(r"Copyright © 2023.2025 Arm Limited \(or its a\w+liates\)\. All rights reserved\.")
LIG = "ﬁﬂﬀﬃﬄ"
def norm(s):
    s = unicodedata.normalize("NFKC", s); s = FOOT.sub(" ", s)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S); s = re.sub(r"==> picture.*?<==", " ", s)
    s = re.sub(r"<br>", " ", s); s = s.lower()
    s = re.sub(r"f+[il]?", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).split()
def sh(w): return set(tuple(w[i:i+N]) for i in range(len(w)-N+1))
traw = open(os.path.join(root,"arm-txt","c1-nano-trm.txt"),encoding="utf-8",errors="replace").read()
mraw = open(os.path.join(root,"ARM","md","Arm-C1-Nano-TRM-r0p2.md"),encoding="utf-8",errors="replace").read()
tp = traw.split("\f")
pat = re.compile(r"Page\s*\*\*(\d+)\*\*\s*of\s*\*\*914\*\*"); mp = {}; pos = 0
for m in pat.finditer(mraw):
    n = int(m.group(1)); mp[n] = mp.get(n,"") + mraw[pos:m.start()]; pos = m.end()
print("md page markers found:", len(mp), " missing page numbers:", [n for n in range(2,915) if n not in mp])
TW, MW = Counter(norm(traw)), Counter(norm(mraw))
tm, mm = sum((TW-MW).values()), sum((MW-TW).values())
print(f"whole-doc bag of words: txt occurrences absent from md {tm:,} of {sum(TW.values()):,} ({tm/sum(TW.values()):.2%}); md absent from txt {mm:,} of {sum(MW.values()):,} ({mm/sum(MW.values()):.2%})")
print("  top 15 txt-only:", (TW-MW).most_common(15)); print("  top 15 md-only :", (MW-TW).most_common(15))
TS, MS = sh(norm(traw)), sh(norm(mraw))
print(f"8-gram coverage: txt->md {len(TS&MS)/len(TS):.1%} of {len(TS):,}; md->txt {len(MS&TS)/len(MS):.1%} of {len(MS):,}")
rows=[]
for n in range(1,915):
    tw=Counter(norm(tp[n-1])); mw=Counter(norm(mp.get(n,""))); rows.append((n,sum(tw.values()),sum(mw.values()),sum((tw-mw).values())))
b=Counter()
for n,t,m,x in rows:
    if t: f=x/t; b["0-2%" if f<.02 else "2-5%" if f<.05 else "5-10%" if f<.1 else "10-25%" if f<.25 else "25-50%" if f<.5 else ">=50%"]+=1
print("pages by fraction of txt words missing from md page:", dict(sorted(b.items())))
print("worst 10 pages (page, txt words, md words, missing):"); [print("  ",r) for r in sorted(rows,key=lambda r:-r[3])[:10]]
# prose lines: ligature vs non-ligature
stats=Counter(); samples=[]
for n,page in enumerate(tp,1):
    for line in page.splitlines():
        s=line.strip()
        if re.search(r"\S {3,}\S",s) or re.search(r"\.{5,}",s): continue
        w=norm(s)
        if len(w)<8: continue
        lig = any(c in s for c in LIG)
        miss = tuple(w[:8]) not in MS
        stats[(lig,miss)]+=1
        if miss and len(samples)<40: samples.append(f"  p{n}: {s[:120]}")
for lig in (False,True):
    t=stats[(lig,False)]+stats[(lig,True)]
    print(f"prose lines {'WITH' if lig else 'without'} ligature glyph: {t:,}; first 8-gram missing from md: {stats[(lig,True)]:,} ({stats[(lig,True)]/max(t,1):.2%})")
print("sample missing prose lines:"); print("\n".join(samples))
