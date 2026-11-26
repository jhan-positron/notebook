#!/usr/bin/env python3
# skeleton.py - print the block structure of the page (no svg content, no table cells) to see what is prose.
import re,sys
from html.parser import HTMLParser
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
src=open(P,encoding='utf-8').read()
class H(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.depth=0; s.skip=0; s.buf=[]; s.stack=[]
    def handle_starttag(s,tag,attrs):
        if tag in('br','meta','link','img','input','hr','col'): return
        a=dict(attrs)
        if s.skip: s.skip+=1; s.stack.append(tag); return
        if tag in('svg','style','table'):
            print('  '*len(s.stack)+f'<{tag} class={a.get("class")} id={a.get("id")}> ...'); s.skip=1; s.stack.append(tag); return
        if tag in('div','section','figure','figcaption','details','summary','ul','ol','p','h1','h2','h3','main','header','li','dl','dt','dd','body','footer','nav','aside'):
            print('  '*len(s.stack)+f'<{tag} class={a.get("class")} id={a.get("id")}>')
        s.stack.append(tag)
    def handle_endtag(s,tag):
        if tag in('br','meta','link','img','input','hr','col'): return
        if s.skip: s.skip-=1
        if s.stack: s.stack.pop()
    def handle_data(s,d):
        if s.skip: return
        d=d.strip()
        if d and s.stack and s.stack[-1] not in('style','script','title'):
            print('  '*len(s.stack)+'"'+d[:70]+('...' if len(d)>70 else '')+'"')
H().feed(src)
