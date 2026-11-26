#!/usr/bin/env python3
"""Compare a C1-Nano txt (pdftotext layout) against a pymupdf4llm md. Usage: nano_compare.py TXT MD"""
import sys, re, unicodedata
from collections import Counter
txtp, mdp = sys.argv[1], sys.argv[2]; N = 8; LIG = "ﬁﬂﬀﬃﬄ"
FOOT = re.compile(r"Copyright © 2023.2025 Arm Limited \(or its a\w+liates\)\. All rights reserved\.")
def norm(s):
    s = unicodedata.normalize("NFKC", s); s = FOOT.sub(" ", s)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S); s = re.sub(r"==> picture.*?<==", " ", s)
    s = re.sub(r"<br>", " ", s); s = s.lower(); s = re.sub(r"f+[il]?", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).split()
t = open(txtp, encoding="utf-8", errors="replace").read(); m = open(mdp, encoding="utf-8", errors="replace").read()
TW, MW = Counter(norm(t)), Counter(norm(m))
print(f"words: txt {sum(TW.values()):,}  md {sum(MW.values()):,}")
print(f"txt word occurrences absent from md: {sum((TW-MW).values()):,} ({sum((TW-MW).values())/sum(TW.values()):.2%}); md absent from txt: {sum((MW-TW).values()):,} ({sum((MW-TW).values())/sum(MW.values()):.2%})")
print("  top 10 txt-only:", (TW-MW).most_common(10))
mw = norm(m); MS = set(tuple(mw[i:i+N]) for i in range(len(mw)-N+1))
tw = norm(t); TS = set(tuple(tw[i:i+N]) for i in range(len(tw)-N+1))
print(f"8-gram coverage: txt->md {len(TS&MS)/len(TS):.1%}; md->txt {len(MS&TS)/len(MS):.1%}")
c = Counter(); w = Counter()
for page in t.split("\f"):
    for line in page.splitlines():
        s = line.strip()
        if re.search(r"\.{5,}", s): continue
        ws = norm(s)
        if len(ws) < 8: continue
        table = bool(re.search(r"\S {3,}\S", s)); lig = any(ch in s for ch in LIG); miss = tuple(ws[:8]) not in MS
        c[(table, lig, miss)] += 1; w[(table, lig, miss)] += len(ws)
for table in (False, True):
    for lig in (False, True):
        tot = c[(table,lig,False)] + c[(table,lig,True)]; mi = c[(table,lig,True)]
        print(f"{'table-layout' if table else 'prose      '} lines {'with   ' if lig else 'without'} ligature: {tot:6,}, first 8-gram missing {mi:5,} ({mi/max(tot,1):5.1%}), words in missing lines {w[(table,lig,True)]:6,}")
print(f"words in missing lines, all: {sum(v for k,v in w.items() if k[2]):,} ({sum(v for k,v in w.items() if k[2])/sum(TW.values()):.1%} of txt words)")
def cw(word, text): return len(re.findall(r"\b" + word + r"\b", text, re.I))
print("ligature spellings in md: " + ", ".join(f"{ok}={cw(ok, m)}/{bad}={cw(bad, m)}" for ok, bad in [("field","feld"),("offset","ofset"),("configured","confgured"),("identification","identifcation"),("affinity","afnity")]))
print(f"strikethrough fragments ~~x~~: {len(re.findall(r'~~[^~]*~~', m))}; picture placeholders: {m.count('==> picture')}; footer lines kept: {m.count('All rights reserved')}; 'available in all configurations': {len(re.findall(r'available in all con', m, re.I))} (txt {len(re.findall(r'available in all con', unicodedata.normalize('NFKC', t), re.I))})")
