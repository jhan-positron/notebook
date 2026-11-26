#!/usr/bin/env python3
# terms.py - candidate project terms used in the visible text outside the word list and the reference list, with a flag when no <dt> names them.
import re, html, collections
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
t=open(P,encoding='utf-8').read()
body=t[t.index('<body'):]
dl=re.search(r'<dl class="words">(.*?)</dl>',body,flags=re.S).group(1)
dts=[html.unescape(re.sub(r'<[^>]+>','',x)) for x in re.findall(r'<dt>(.*?)</dt>',dl,flags=re.S)]
dds=[html.unescape(re.sub(r'<[^>]+>','',x)) for x in re.findall(r'<dd>(.*?)</dd>',dl,flags=re.S)]
print(len(dts),'terms in the word list')
rest=body.replace(dl,'')
rest=rest[:rest.index('<ol class="refs">')]
rest=re.sub(r'<title>.*?</title>',' ',rest,flags=re.S)
rest=re.sub(r'<style.*?</style>',' ',rest,flags=re.S)
txt=html.unescape(re.sub(r'<[^>]+>',' ',rest))
toks=collections.Counter(re.findall(r"[A-Za-z_][A-Za-z0-9_\-./%]*",txt))
dtall=' '.join(dts).lower(); ddall=' '.join(dds).lower()
cand=[]
for w,n in toks.items():
    if re.search(r'\d|_',w) or (w.isupper() and len(w)>1) or re.search(r'[a-z][A-Z]',w):
        cand.append((w,n, w.lower() in dtall, w.lower() in ddall))
for w,n,a,b in sorted(cand,key=lambda x:(x[2],x[3],x[0].lower())):
    print(f'{w:28s} used {n:3d}  in dt:{a}  in dd:{b}')
