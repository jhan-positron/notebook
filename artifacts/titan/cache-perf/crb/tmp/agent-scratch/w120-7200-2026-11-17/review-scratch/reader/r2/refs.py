#!/usr/bin/env python3
# refs.py - list every reference of the page, check that the path exists, and print the cited lines.
import re, os, sys, html
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
R='/home/jhan/workspace/titan/cache-perf/crb/results'
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
t=open(P,encoding='utf-8').read()
i=t.index('id="refs"') if 'id="refs"' in t else t.rindex('References')
tail=t[i:]
items=re.findall(r'<li[^>]*>(.*?)</li>',tail,flags=re.S)
n=0;bad=0
for it in items:
    txt=html.unescape(re.sub(r'<[^>]+>','',it)).strip()
    m=re.match(r'\[Ref(\d+)\]\s*(\S+)(.*)',txt,flags=re.S)
    if not m: print('??',txt[:80]); continue
    n+=1
    num,path,rest=m.group(1),m.group(2),m.group(3)
    path=path.rstrip(':')
    full=path.replace('R/',R+'/',1) if path.startswith('R/') else path.replace('S/',S+'/',1) if path.startswith('S/') else path
    ex=os.path.exists(full)
    if not ex: bad+=1
    print(f'[Ref{num}] {"OK " if ex else "MISSING"} {full} || {rest.strip()[:150]}')
print('references:',n,'missing:',bad)
# body citations
body=t[:i]
cited=sorted(set(int(x) for x in re.findall(r'\[Ref(\d+)\]',html.unescape(re.sub(r'<[^>]+>','',body)))))
print('cited in body:',len(cited),'not cited:',[k for k in range(1,n+1) if k not in cited])
