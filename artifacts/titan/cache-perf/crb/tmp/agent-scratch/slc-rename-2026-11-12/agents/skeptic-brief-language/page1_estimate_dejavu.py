#!/usr/bin/env python3
"""Independent estimate of the printed height of page 1 of the brief (skeptic check).

Text widths come from FreeType through PIL (ImageFont.getlength at 1000 px, scaled down),
not from the first checker's fontTools code. No browser is used, so every number is an estimate.

Usage: page1_estimate.py <brief.html> [width_factor] [table_line_height]
"""
import re, sys, html
from PIL import ImageFont

FONTS = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/fonts'
F = {400: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 1000),
     600: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 1000)}
PXMM = 96 / 25.4
PAGE_W = (210 - 24) * PXMM
PAGE_H = (297 - 22) * PXMM
FACTOR = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
TABLE_LH = float(sys.argv[3]) if len(sys.argv) > 3 else 1.35


def tw(t, size, weight=400, ls=0.0):
    return F[weight].getlength(t) / 1000 * size * FACTOR + ls * len(t)


def words(t):
    return ' '.join(t.split()).split(' ')


def wrap(t, width, size, weight=400, ls=0.0):
    """greedy wrap, break at spaces only (a browser may also break after '-' or '/': fewer lines, so this is the high side)"""
    lines = []; cur = ''
    for w in words(t):
        trial = (cur + ' ' + w) if cur else w
        if cur and tw(trial, size, weight, ls) > width:
            lines.append(cur); cur = w
        else:
            cur = trial
    lines.append(cur)
    return lines


src = open(sys.argv[1], encoding='utf-8').read()
page1 = src.split('<div class="pb"></div>')[0]
body = page1.split('<main>')[1]


def text(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s))


h1 = text(re.search(r'<h1>(.*?)</h1>', body, re.S).group(1))
sub = text(re.search(r'<p class="sub">(.*?)</p>', body, re.S).group(1))
h2s = [text(x) for x in re.findall(r'<h2>(.*?)</h2>', body, re.S)]
rows = [[(k, text(c)) for k, c in re.findall(r'<(th|td)>(.*?)</(?:th|td)>', r, re.S)]
        for r in re.findall(r'<tr>(.*?)</tr>', body, re.S)]
cap = text(re.search(r'<p class="cap">(.*?)</p>', body, re.S).group(1))
lis = [(('take' in a), text(c)) for a, c in re.findall(r'<li([^>]*)>(.*?)</li>', body, re.S)]
vb = re.search(r'<svg viewBox="0 0 (\d+) (\d+)"', body)
svg_h = PAGE_W * int(vb.group(2)) / int(vb.group(1))

out = []
y = 0.0
# h1: margin 0 0 2
n = len(wrap(h1, PAGE_W, 17, 600)); h = n * 17 * 1.35; y += h; out.append(('h1', h, f'{n} line'))
# p.sub: margin 0 0 6 ; gap to h1 = max(2, 0) = 2
ls_ = wrap(sub, PAGE_W, 10.5); h = len(ls_) * 10.5 * 1.35; y += 2 + h
out.append(('sub', h, f'{len(ls_)} lines, last {tw(ls_[-1], 10.5):.0f} px of {PAGE_W:.0f}'))
# h2 #1: margin 10 0 4, border 1, padding-top 4 ; gap = max(6, 10) = 10
H2 = 1 + 4 + 12.5 * 1.35
y += 10 + H2; out.append(('h2', H2, h2s[0]))
# table: gap = 4 (h2 bottom margin)
ncol = len(rows[0])


def cell_style(k):
    return (9.5, 600, 0.02 * 9.5, True) if k == 'th' else (10.0, 400, 0.0, False)


mins = [0.0] * ncol; maxs = [0.0] * ncol
for r in rows:
    for j, (k, t) in enumerate(r):
        size, wgt, ls, up = cell_style(k)
        t2 = t.upper() if up else t
        mins[j] = max(mins[j], max(tw(w, size, wgt, ls) for w in words(t2)) + 12)
        maxs[j] = max(maxs[j], tw(' '.join(words(t2)), size, wgt, ls) + 12)
smin, smax = sum(mins), sum(maxs)
if PAGE_W >= smax:
    cols = [m * PAGE_W / smax for m in maxs]
elif PAGE_W <= smin:
    cols = mins[:]
else:
    k_ = (PAGE_W - smin) / (smax - smin)
    cols = [a + (b - a) * k_ for a, b in zip(mins, maxs)]
th_ = 0.0; detail = []
for r in rows:
    nl = []
    for j, (k, t) in enumerate(r):
        size, wgt, ls, up = cell_style(k)
        t2 = t.upper() if up else t
        nl.append(len(wrap(t2, cols[j] - 12, size, wgt, ls)) * size * TABLE_LH)
    rh = max(nl) + 4 + 1
    th_ += rh; detail.append(round(rh, 1))
y += 4 + th_; out.append(('table', th_, f'rows {detail}; col widths {[round(c) for c in cols]}; sum min {smin:.0f} max {smax:.0f}'))
# caption: margin 2 0 0
cl = wrap(cap, PAGE_W, 9.5); h = len(cl) * 9.5 * 1.35; y += 2 + h
out.append(('cap', h, f'{len(cl)} lines; widths {[round(tw(x, 9.5)) for x in cl]} of {PAGE_W:.0f}'))
# h2 #2: gap = max(0, 10) = 10
y += 10 + H2; out.append(('h2', H2, h2s[1]))
# ul: margin 2 0 4 ; gap to h2 = max(4, 2) = 4 ; li margin 1 0 (first and last collapse into the ul margins)
nlines = []
for take, t in lis:
    nlines.append(len(wrap(t, PAGE_W - 18, 10.5, 600 if take else 400)))
h = sum(nlines) * 10.5 * 1.35 + (len(lis) - 1) * 1
y += 4 + h; out.append(('ul', h, f'lines per item {nlines} = {sum(nlines)}'))
# h2 #3: gap = max(4, 10) = 10
y += 10 + H2; out.append(('h2', H2, h2s[2]))
# svg: gap 4
y += 4 + svg_h; out.append(('svg', svg_h, f'viewBox {vb.group(1)} x {vb.group(2)}'))

print(f'{sys.argv[1].split("/")[-1]}  factor {FACTOR}  table line-height {TABLE_LH}')
for k, h, info in out:
    print(f'  {k:6s} {h:7.1f} px  {info}')
print(f'  content {y:.1f} px = {y / PXMM:.1f} mm ; page area {PAGE_H:.1f} px = {PAGE_H / PXMM:.0f} mm ; free {PAGE_H - y:.1f} px = {(PAGE_H - y) / PXMM:.1f} mm')
