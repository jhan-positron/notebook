#!/usr/bin/env python3
# tablewords.py - words per table of the page, and whether the table sits in a folded <details>.
import re, html
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
t=open(P,encoding='utf-8').read()
body=t[t.index('<body'):]
pos=0
for m in re.finditer(r'<table.*?</table>',body,flags=re.S):
    before=body[:m.start()]
    cap=re.findall(r'<p class="tcap">(.*?)</p>|<summary>(.*?)</summary>',before,flags=re.S)[-1]
    cap=html.unescape(re.sub(r'<[^>]+>','',cap[0] or cap[1]))[:70]
    txt=html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'<span class="ref">.*?</span>',' ',m.group(0))))
    n=len([w for w in txt.split() if re.search(r'[A-Za-z0-9]',w)])
    rows=len(re.findall(r'<tr',m.group(0)))
    folded = before.count('<details')>before.count('</details>')
    cells=[html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'<span class="ref">.*?</span>',' ',c))) for c in re.findall(r'<td[^>]*>(.*?)</td>',m.group(0),flags=re.S)]
    longest=max(cells,key=lambda c:len(c.split()))
    print(f'{n:5d} words, {rows:3d} rows, folded={folded}, longest cell {len(longest.split())} words | {cap}')
