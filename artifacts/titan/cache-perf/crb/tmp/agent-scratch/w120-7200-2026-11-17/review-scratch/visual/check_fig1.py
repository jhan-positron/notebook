# check_fig1.py - verify Figure 1 marks against their titles and against facts.json
import re, json, statistics, sys
import xml.etree.ElementTree as ET
V = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual'
src = open(V + '/svg-06.svg').read()
root = ET.fromstring(src)
def X(v): return 356.0 + v * 0.98
els = list(root)
print('top-level children', len(els))
from collections import Counter
print(Counter(e.tag for e in els))
bad = 0
# marks
rows = []
for e in els:
    if e.tag == 'g':
        t = e.find('title')
        if t is None:
            print('G WITHOUT TITLE', ET.tostring(e)[:200]); bad += 1; continue
        txt = t.text
        if e.get('class') == 'pt':
            m = re.search(r'Median ([\d.]+) GB/s\. Intervals: ([\d., ]+) GB/s', txt)
            med = float(m.group(1)); iv = [float(v) for v in m.group(2).split(',')]
            mk = [c for c in e.findall('circle') if c.get('class') == 'mk'][0]
            cx = float(mk.get('cx'))
            if abs(cx - X(med)) > 0.06: print('DOT POS MISMATCH', txt[:80], cx, X(med)); bad += 1
            if abs(statistics.median(iv) - med) > 0.006: print('MEDIAN MISMATCH', txt[:80]); bad += 1
            d = e.find('path').get('d')
            xs = [float(v) for v in re.findall(r'M([\d.]+) ', d)]
            lo, hi = min(xs), max(xs)
            if abs(lo - X(min(iv))) > 0.06 or abs(hi - X(max(iv))) > 0.06: print('WHISKER MISMATCH', txt[:80], lo, hi, X(min(iv)), X(max(iv))); bad += 1
            rows.append((txt, med, iv, mk.get('fill'), mk.get('stroke'), float(mk.get('cy'))))
        else:
            ln = e.find('line'); tx = e.find('text')
            rows.append((txt, None, tx.text, float(ln.get('x1')), float(ln.get('x2')), float(ln.get('y1')), float(tx.get('y'))))
print('marks', len(rows), 'bad', bad)
for r in rows:
    if r[1] is None:
        print(' LINE y=%.1f labely=%.1f x %.1f..%.1f  label=%s | %s' % (r[5], r[6], r[3], r[4], r[2], r[0][:150]))
    else:
        print(' DOT  y=%.1f med=%.2f fill=%s stroke=%s | %s' % (r[5], r[1], r[3], r[4], r[0][:110]))
