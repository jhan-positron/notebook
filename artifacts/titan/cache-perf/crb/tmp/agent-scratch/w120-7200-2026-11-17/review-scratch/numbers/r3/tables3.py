#!/usr/bin/env python3
"""Parse the HTML tables and compare number cells with values from raw (round-3 reviewer)."""
import re, html, json
import data3 as d
from data3 import BW, sel, med
from fig1chk_lib import EXP, droptxt, f2
N = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/numbers/r3'
t = open(N + '/page.html').read()
t = re.sub(r'<svg\b.*?</svg>', '', t, flags=re.S)
tables = re.findall(r'<table\b.*?</table>', t, flags=re.S)
def cells(tb):
    rows = []
    for tr in re.findall(r'<tr\b.*?</tr>', tb, flags=re.S):
        cs = re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', tr, flags=re.S)
        cs = [re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', c))).strip() for c in cs]
        rows.append(cs)
    return rows
T = [cells(tb) for tb in tables]
json.dump(T, open(N + '/tables.json', 'w'), indent=1)
for i, tb in enumerate(T): print(i, len(tb), 'rows; header:', tb[0][:3])
bad = 0
def chk(c, msg):
    global bad
    if not c: bad += 1; print('MISMATCH:', msg)
# ---- table view of Figure 1 (find the table whose header starts with 'Row' and has 'Drop')
tv1 = [tb for tb in T if tb[0] and tb[0][0] == 'Row' and 'Drop' in tb[0]][0]
n = 0
for row in tv1[1:]:
    if len(row) < 6: continue
    key = [k for k in EXP if row[0].startswith(k + ' ') or row[0].startswith(k + ' ·') or row[0] == k]
    chk(len(key) == 1, 'fig1 table row key: %s -> %s' % (row[0][:60], key))
    if len(key) != 1: continue
    e = EXP[key[0]]; n += 1
    exp = [f2(med(e['old'])), ', '.join(f2(v) for v in e['old']), f2(med(e['lo'])), ', '.join(f2(v) for v in e['lo']), droptxt(e['drops'])]
    chk(row[1:6] == exp, 'fig1 table %s: page %s raw %s' % (key[0], row[1:6], exp))
print('fig1 table rows checked', n)
print('TOTAL MISMATCHES', bad)
