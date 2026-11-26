#!/usr/bin/env python3
# wordcount.py - reviewer's own word count of the prose, by block type.
import re
from html.parser import HTMLParser
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
src=open(P,encoding='utf-8').read()
class H(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.stack=[]; s.out=[]
    def handle_starttag(s,tag,attrs):
        if tag in('br','meta','link','img','input','hr','col'): return
        a=dict(attrs); s.stack.append((tag,a.get('class') or '',a.get('id') or ''))
    def handle_endtag(s,tag):
        if tag in('br','meta','link','img','input','hr','col'): return
        while s.stack and s.stack[-1][0]!=tag: s.stack.pop()
        if s.stack: s.stack.pop()
    def handle_data(s,d):
        if not d.strip(): return
        tags=[t for t,_,_ in s.stack]; cls=' '.join(c for _,c,_ in s.stack)
        if 'style' in tags or 'script' in tags or 'head' in tags and 'body' not in tags: return
        if 'svg' in tags: k='svg'
        elif 'table' in tags: k='table'
        elif 'dl' in tags or ('summary' in tags): k='wordlist/summary'
        elif 'figcaption' in tags or 'caption' in tags or 'cap' in cls.split(): k='caption'
        elif 'legend' in cls.split(): k='legend'
        elif 'refs' in cls or any(i=='refs' for _,_,i in s.stack): k='refs'
        elif any(t in('h1','h2','h3') for t in tags): k='heading'
        else: k='prose:'+'/'.join(f'{t}.{c}' if c else t for t,c,_ in s.stack[2:])
        s.out.append((k,d))
h=H(); h.feed(src)
import collections
agg=collections.OrderedDict()
for k,d in h.out:
    d2=re.sub(r'\[Ref\d+\]','',d)
    n=len([w for w in re.findall(r"\S+",d2) if re.search(r"[A-Za-z0-9]",w)])
    agg[k]=agg.get(k,0)+n
tot=0
for k,n in agg.items():
    print(f'{n:6d}  {k}')
    if k.startswith('prose:'): tot+=n
print('prose total',tot)
