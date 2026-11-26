#!/usr/bin/env python3
"""Nano txt vs md, ligature-tolerant (fi/fl/ff/ffi/ffl -> f on both sides), per-page copyright footer removed."""
import sys, re, unicodedata, os
from collections import Counter
root = sys.argv[1]; N = 8
FOOT = re.compile(r"Copyright © 2023.2025 Arm Limited \(or its a\w+liates\)\. All rights reserved\.")

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = FOOT.sub(" ", s)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"==> picture.*?<==", " ", s)
    s = re.sub(r"<br>", " ", s)
    s = s.lower()
    s = re.sub(r"ff?[il]?", "f", s)          # ligature-tolerant: field/feld -> feld, offset/ofset -> ofset
    return re.sub(r"[^a-z0-9]+", " ", s).split()
def shingles(w): return set(tuple(w[i:i+N]) for i in range(len(w)-N+1))

traw = open(os.path.join(root,"arm-txt","c1-nano-trm.txt"),encoding="utf-8",errors="replace").read()
mraw = open(os.path.join(root,"ARM","md","Arm-C1-Nano-TRM-r0p2.md"),encoding="utf-8",errors="replace").read()
tp = traw.split("\f")
pat = re.compile(r"Page \*\*(\d+)\*\* of \*\*914\*\*")
mp = {}; pos = 0
for m in pat.finditer(mraw):
    n = int(m.group(1)); mp[n] = mp.get(n,"") + mraw[pos:m.start()]; pos = m.end()
mp[915] = mraw[pos:]

TW, MW = Counter(norm(traw)), Counter(norm(mraw))
print(f"whole-doc bag of words (ligature-tolerant, footer removed):")
print(f"  txt occurrences absent from md: {sum((TW-MW).values()):,} of {sum(TW.values()):,} ({sum((TW-MW).values())/sum(TW.values()):.2%})")
print(f"  md  occurrences absent from txt: {sum((MW-TW).values()):,} of {sum(MW.values()):,} ({sum((MW-TW).values())/sum(MW.values()):.2%})")
print("  top 20 txt-only words:", (TW-MW).most_common(20))
print("  top 20 md-only words :", (MW-TW).most_common(20))

TS, MS = shingles(norm(traw)), shingles(norm(mraw))
print(f"\n8-gram coverage (ligature-tolerant): txt->md {len(TS&MS)/len(TS):.1%} of {len(TS):,}; md->txt {len(MS&TS)/len(MS):.1%} of {len(MS):,}")

rows=[]; tot=miss=0
for n in range(1,915):
    tw = Counter(norm(tp[n-1])); mw = Counter(norm(mp.get(n,"")))
    m = sum((tw-mw).values()); rows.append((n,sum(tw.values()),sum(mw.values()),m)); tot+=sum(tw.values()); miss+=m
print(f"\nper-page summed: txt words not on same md page {miss:,} of {tot:,} ({miss/tot:.2%})")
b=Counter()
for n,t,mm,m in rows:
    if t==0: continue
    f=m/t; b["0-2%" if f<.02 else "2-5%" if f<.05 else "5-10%" if f<.1 else "10-25%" if f<.25 else "25-50%" if f<.5 else ">=50%"]+=1
print("  pages by fraction of txt words missing on md page:", dict(sorted(b.items())))
print("  worst 12 pages (page, txt words, md words, missing):")
for r in sorted(rows,key=lambda r:-r[3])[:12]: print("   ",r)

print("\nsample single-column prose lines (>=8 words) whose first 8-gram is nowhere in md:")
shown=0; tot2=miss2=0
for n,page in enumerate(tp,1):
    for line in page.splitlines():
        s=line.strip()
        if re.search(r"\S {3,}\S",s) or re.search(r"\.{5,}",s): continue
        w=norm(s)
        if len(w)<8: continue
        tot2+=1
        if tuple(w[:8]) not in MS:
            miss2+=1
            if shown<40 and n not in (248,623): print(f"  p{n}: {s[:120]}"); shown+=1
print(f"  prose lines {tot2:,}; missing {miss2:,} ({miss2/tot2:.2%})")
