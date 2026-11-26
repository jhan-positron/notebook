#!/usr/bin/env python3
"""Per-cell wrap of the first table of the brief (estimate, PIL text widths). Usage: table_cells.py <brief.html>"""
import re, sys, html
from PIL import ImageFont
FONTS = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/fonts'
F = {400: ImageFont.truetype(f'{FONTS}/IBMPlexSans-400.ttf', 1000), 600: ImageFont.truetype(f'{FONTS}/IBMPlexSans-600.ttf', 1000)}
PAGE_W = (210 - 24) * 96 / 25.4
def tw(t, size, weight=400, ls=0.0): return F[weight].getlength(t) / 1000 * size + ls * len(t)
def words(t): return ' '.join(t.split()).split(' ')
def wrap(t, width, size, weight=400, ls=0.0):
    lines = []; cur = ''
    for w in words(t):
        trial = (cur + ' ' + w) if cur else w
        if cur and tw(trial, size, weight, ls) > width: lines.append(cur); cur = w
        else: cur = trial
    lines.append(cur); return lines
src = open(sys.argv[1], encoding='utf-8').read().split('<div class="pb"></div>')[0]
rows = [[(k, html.unescape(re.sub(r'<[^>]+>', '', c))) for k, c in re.findall(r'<(th|td)>(.*?)</(?:th|td)>', r, re.S)] for r in re.findall(r'<tr>(.*?)</tr>', src, re.S)]
def st(k): return (9.5, 600, 0.19, True) if k == 'th' else (10.0, 400, 0.0, False)
n = len(rows[0]); mins = [0.0] * n; maxs = [0.0] * n
for r in rows:
    for j, (k, t) in enumerate(r):
        s, w, ls, up = st(k); t2 = t.upper() if up else t
        mins[j] = max(mins[j], max(tw(x, s, w, ls) for x in words(t2)) + 12); maxs[j] = max(maxs[j], tw(' '.join(words(t2)), s, w, ls) + 12)
k_ = (PAGE_W - sum(mins)) / (sum(maxs) - sum(mins)); cols = [a + (b - a) * k_ for a, b in zip(mins, maxs)]
print('columns (px):', [round(c, 1) for c in cols], ' max-content:', [round(m, 1) for m in maxs])
for r in rows:
    for j, (k, t) in enumerate(r):
        s, w, ls, up = st(k); t2 = t.upper() if up else t
        l = wrap(t2, cols[j] - 12, s, w, ls)
        if len(l) > 1 or j == 0: print(f'  col {j + 1} inner {cols[j] - 12:.1f} px, needs {tw(" ".join(words(t2)), s, w, ls):.1f} px: {l}')
