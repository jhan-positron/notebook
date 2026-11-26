#!/usr/bin/env python3
import re, html
C="/home/jhan/workspace/titan/cache-perf/crb"; B="/home/jhan/workspace/titan/cache-perf/bench"
L=open(C+"/crb-memory-hierarchy.html",encoding="utf-8").read().split("\n")
pres=re.findall(r"<pre><code>(.*?)</code></pre>","\n".join(L[130:133]),flags=re.S)
print("pre blocks in lines 131-133:",len(pres), " whole file:",len(re.findall(r"<pre",open(C+"/crb-memory-hierarchy.html",encoding="utf-8").read())))
src=open(B+"/bandwidth.c",encoding="utf-8").read().split("\n")
probe=open(C+"/results/probe-20261111T210017Z.txt",encoding="utf-8").read().split("\n")
def dec(p): return html.unescape(p).split("\n")
a=dec(pres[0]); b=dec(pres[1]); c=dec(pres[2])
print("listing 1 == bandwidth.c 138-148:", a==src[137:148], len(a))
print("listing 2 == bandwidth.c 173-195:", b==src[172:195], len(b))
norm=lambda s: re.sub(r"\s+"," ",s).strip()
print("listing 3 == probe 44-59 (ws-normalised):", [norm(x) for x in c]==[norm(x) for x in probe[43:59]], len(c))
for i,(x,y) in enumerate(zip(c,probe[43:59])):
    if norm(x)!=norm(y): print("  diff",i,repr(x),repr(y))
print("probe 43:",repr(probe[42])); print("probe 44:",repr(probe[43])); print("probe 59:",repr(probe[58])); print("probe 60:",repr(probe[59]))
print("probe lines:",len(probe))
# count mnemonics in listing 3
import collections
mn=collections.Counter(norm(x).split(" ")[1] for x in c)
print(mn)
