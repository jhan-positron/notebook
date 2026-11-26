#!/usr/bin/env python3
import re, html
C="/home/jhan/workspace/titan/cache-perf/crb"
L=open(C+"/crb-memory-hierarchy.html",encoding="utf-8").read().split("\n")
heads={}
for i,l in enumerate(L,1):
    for m in re.finditer(r"<h([23])[^>]*>(.*?)</h\1>",l):
        heads[html.unescape(re.sub(r"<[^>]+>","",m.group(2)))]=i
print(len(heads),"headings")
for h,i in heads.items():
    if "part 5" in h or "root run" in h or "Latency" in h: print("  heading line",i,":",h)
body_end=475
res=[]
for i,l in enumerate(L[:body_end],1):
    if i in (55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72): continue  # contents list
    t=html.unescape(re.sub(r"<[^>]+>","",l))
    for m in re.finditer(r'"([^"]{6,120})"',t):
        q=m.group(1)
        exact=q in heads
        pref=[h for h in heads if h!=q and h.startswith(q)]
        if not exact and pref:
            res.append((i,q,pref))
for i,q,pref in res: print(f"line {i}: \"{q}\" is the first part of heading(s): {pref}")
print("lines:",sorted(set(i for i,_,_ in res)))
# contents entries vs headings
toc=[]
for i in range(55,73):
    for m in re.finditer(r'<a href="#([^"]+)">(.*?)</a>',L[i-1]):
        txt=html.unescape(re.sub(r"<[^>]+>","",m.group(2)))
        if txt not in heads: toc.append((i,txt,[h for h in heads if h.startswith(txt[:20])]))
print("contents entries that differ from their heading:",toc)
