#!/usr/bin/env python3
# Round 2, claims lens: every text unit (p, li, td, th, figcaption, dd, dt, title, text, summary, aria-label) that names
# control I or F72d12 must carry the label; asmread rows of part L / control I must say "in place of".
import re, html
src=open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html',encoding='utf-8').read()
src=re.sub(r'<style\b.*?</style>','',src,flags=re.S)
units=[]
for tag in ('p','li','td','th','figcaption','dd','dt','title','summary','h1','h2','h3','caption','tr'):
    for m in re.finditer(r'<%s\b[^>]*>(.*?)</%s>'%(tag,tag),src,flags=re.S):
        t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',m.group(1)))).strip()
        if t: units.append((tag,t))
for m in re.finditer(r'aria-label="([^"]*)"',src): units.append(('aria',html.unescape(m.group(1))))
# svg text: group consecutive <text> of a row is hard; treat <g> groups
for m in re.finditer(r'<g\b[^>]*>(.*?)</g>',src,flags=re.S):
    t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',m.group(1)))).strip()
    if t: units.append(('g',t))
seen=set()
for tag,t in units:
    if tag in('tr','g'): continue
    if re.search(r'[Cc]ontrol I\b',t) and 'added after the first numbers were seen' not in t and 'added after the first' not in t:
        k=('CI',t[:200])
        if k not in seen: seen.add(k); print('CI-NOLABEL [%s] %s'%(tag,t[:300])); print()
    if 'F72d12' in t and 'not part of the rerun' not in t and 'earlier run of the same boot' not in t:
        k=('F',t[:200])
        if k not in seen: seen.add(k); print('F72-NOLABEL [%s] %s'%(tag,t[:300])); print()
