#!/usr/bin/env python3
"""Measure a printed brief PDF: pages, page size, fonts, content bottom of each page, caption lines, first-table cells.
Usage: pdf_report.py <pdf>"""
import sys, fitz
d = fitz.open(sys.argv[1])
MM = 25.4 / 72
print(sys.argv[1].split('/')[-1], '| pages:', len(d))
for i, p in enumerate(d):
    r = p.rect
    fonts = sorted({f[3] for f in p.get_fonts()})
    blocks = p.get_text('dict')['blocks']
    ys = []
    for b in blocks:
        ys.append(b['bbox'][3])
    for dr in p.get_drawings():
        ys.append(dr['rect'].y1)
    bottom = max(ys) if ys else 0
    top = min(b['bbox'][1] for b in blocks) if blocks else 0
    print(f' page {i + 1}: {r.width * MM:.1f} x {r.height * MM:.1f} mm; fonts {fonts}; content from {top * MM:.1f} mm to {bottom * MM:.1f} mm of {r.height * MM:.1f} mm; '
          f'free above the bottom margin (11 mm): {(r.height - bottom) * MM - 11:.1f} mm')
    first = p.get_text('text').strip().split('\n')[0:1]
    print('   first line:', first)
p = d[0]
words = p.get_text('words')  # x0, y0, x1, y1, word, block, line, word_no
def lines_of(start_word, end_word):
    """group the words between two marker words into visual lines by y"""
    seq = []; on = False
    for w in words:
        if not on and w[4] == start_word: on = True
        if on: seq.append(w)
        if on and w[4] == end_word and len(seq) > 3: break
    rows = {}
    for w in seq: rows.setdefault(round(w[1], 0), []).append(w)
    return [(' '.join(x[4] for x in sorted(v, key=lambda x: x[0])), min(x[0] for x in v), max(x[2] for x in v)) for k, v in sorted(rows.items())]
print(' caption lines on page 1:')
cap = [w for w in words if w[4] == 'Latency:']
if cap:
    y0 = cap[0][1]
    capw = [w for w in words if w[1] >= y0 - 1 and w[1] < y0 + 60 and w[3] - w[1] < 14]
    # stop at the heading "Findings"
    fy = min([w[1] for w in words if w[4] == 'Findings'] or [9999])
    capw = [w for w in capw if w[1] < fy - 2]
    rows = {}
    for w in capw: rows.setdefault(round(w[1], 0), []).append(w)
    for k, v in sorted(rows.items()):
        v = sorted(v, key=lambda x: x[0])
        print(f'   y {k * MM:.1f} mm, x {v[0][0] * MM:.1f} to {v[-1][2] * MM:.1f} mm: {" ".join(x[4] for x in v)[:150]}')
print(' first column of the first table (words left of 45 mm between the heading and the caption):')
hy = min([w[1] for w in words if w[4] == 'LEVEL' or w[4] == 'Level'] or [0])
cy = cap[0][1] if cap else 9999
col = [w for w in words if hy - 1 <= w[1] < cy - 1 and w[0] < 55 / MM]
rows = {}
for w in col: rows.setdefault(round(w[1], 0), []).append(w)
for k, v in sorted(rows.items()):
    v = sorted(v, key=lambda x: x[0])
    print(f'   y {k * MM:.1f} mm: {" ".join(x[4] for x in v)}')
print(' list items: number of text lines between "Findings" and the next heading:')
fy = min([w[1] for w in words if w[4] == 'Findings'] or [0]); wy = min([w[1] for w in words if w[4] == 'Where'] or [9999])
ly = sorted({round(w[1], 0) for w in words if fy + 5 < w[1] < wy - 2})
print('   ', len(ly), 'lines')
