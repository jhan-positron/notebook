# check_fig2.py - verify Figure 2 marks (both panels) against their titles
import re, sys
import xml.etree.ElementTree as ET
from collections import Counter
V = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual'
tot = 0
for name, x0, v0, x1, v1 in (('svg-12.svg', 218.9, 460, 450.0, 476), ('svg-13.svg', None, None, None, None)):
    root = ET.fromstring(open(V + '/' + name).read())
    els = list(root)
    # derive scale from tick labels
    ticks = [(float(e.get('x')), float(e.text)) for e in els if e.tag == 'text' and re.fullmatch(r'\d{3}', e.text or '') and e.get('text-anchor') == 'middle']
    ticks = sorted(set(ticks))
    (xa, va), (xb, vb) = ticks[0], ticks[-1]
    k = (xb - xa) / (vb - va)
    X = lambda v: xa + (v - va) * k
    print('==', name, 'ticks', ticks, 'px per GB/s %.3f' % k, 'axis start value at x=190: %.2f' % (va + (190 - xa) / k))
    print(Counter(e.tag for e in els))
    bad = 0; ndots = 0
    cur_text = []
    for e in els:
        if e.tag == 'text':
            cur_text.append((float(e.get('y')), e.text))
        if e.tag != 'g':
            continue
        t = e.find('title')
        if t is None:
            print('NO TITLE', ET.tostring(e)[:150]); bad += 1; continue
        txt = t.text
        if e.get('class') == 'pt':
            ndots += 1
            m = re.search(r': ([\d.]+) GB/s\. Row', txt)
            if not m:
                print('TITLE WITHOUT VALUE', txt[:160]); bad += 1; continue
            v = float(m.group(1))
            mk = [c for c in e.findall('circle') if c.get('class') == 'mk'][0]
            cx = float(mk.get('cx'))
            if abs(cx - X(v)) > 0.08:
                print('POS MISMATCH', v, cx, X(v), txt[:100]); bad += 1
            hollow = mk.get('fill') == '#fcfcfb'
            col = mk.get('stroke') if hollow else mk.get('fill')
            if 'n =' not in txt or 'Source:' not in txt:
                print('TITLE WITHOUT n OR SOURCE', txt[:160]); bad += 1
            # speed from source folder name
            src = txt.split('Source:')[1]
            is7200 = ('T72' in src) or ('F72d12' in src)
            if hollow == is7200:
                print('HOLLOW/FILLED MISMATCH', hollow, src); bad += 1
            want = '#2a78d6' if name == 'svg-12.svg' else '#eb6834'
            if col != want:
                print('COLOUR MISMATCH', col, txt[:80]); bad += 1
        else:
            r = e.find('rect')
            m = re.search(r'([\d.]+) to ([\d.]+) GB/s', txt)
            lo, hi = float(m.group(1)), float(m.group(2))
            bx = float(r.get('x')); bw = float(r.get('width'))
            ok = abs(bx - X(lo)) < 0.08 and abs(bx + bw - X(hi)) < 0.08
            print(' BAND %s y=%s h=%s x=%.1f..%.1f expect %.1f..%.1f | %s' % ('ok ' if ok else 'BAD', r.get('y'), r.get('height'), bx, bx + bw, X(lo), X(hi), txt[:140]))
            if not ok: bad += 1
    print(' dots', ndots, 'bad', bad)
    tot += ndots
print('total dots', tot)
