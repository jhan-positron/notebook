#!/usr/bin/env python3
"""Check Figure 1 (3 SVG variants) against raw data: tooltips, labels, dot x, whisker x, drop line ends, drop text."""
import re, sys, html, statistics
import data3 as d
from data3 import BW, sel, med, R
N = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/numbers/r3'

# ---- expected rows from raw
def bw_row(key, lo_kernel, lo_pos):
    ivs = BW[key]
    path = ivs[0]['path'].replace(R, 'R')
    o = sel(ivs, 'oldread'); l = sel(ivs, lo_kernel, lo_pos)
    o = sorted(o, key=lambda i: i['round']); l = sorted(l, key=lambda i: i['round'])
    drops = [(1 - b['total'] / a['total']) * 100 for a, b in zip(o, l)]
    return dict(path=path, old=[i['total'] for i in o], lo=[i['total'] for i in l], old_lines=[i['I_line'] for i in o],
                lo_lines=[i['I_line'] for i in l], drops=drops, npairs=len(drops))
def a_row(old, new):
    path = old['path'].replace(R, 'R')
    ov = [i['agg'] for i in old['iv']]; nv = [i['agg'] for i in new['iv']]
    return dict(path=path, old=ov, lo=nv, old_lines=[i['line'] for i in old['iv']], lo_lines=[i['line'] for i in new['iv']],
                drops=[(1 - med(nv) / med(ov)) * 100], npairs=1)
EXP = {
 'L-1': bw_row('L-1', 'asmread', 1), 'F72d12': bw_row('F72d12', 'asmread', 1),
 'Part L, session 1 (T72L1)': bw_row('T72L1', 'asmread', 1), 'Part L, session 2 (T72L2)': bw_row('T72L2', 'asmread', 1),
 'Part L, session 3 (T72L3)': bw_row('T72L3', 'asmread', 1),
 'Part C, T72C1 (cfwd)': bw_row('T72C1', 'read', 1), 'Part C, T72C2 (crev)': bw_row('T72C2', 'read', 1),
 'Part C, T72C3 (cfwd)': bw_row('T72C3', 'read', 1), 'Part C, T72C4 (crev)': bw_row('T72C4', 'read', 1),
 'Control I, T72I1': bw_row('T72I1', 'asmread', 1), 'Control I, T72I2': bw_row('T72I2', 'asmread', 1),
}
for r in (1, 2):
    EXP['A-1, round %d' % r] = a_row(d.aread(d.A1, 'bw_old', r), d.aread(d.A1, 'bw_new', r))
    EXP['A-2, round %d' % r] = a_row(d.a2read('bw_old', r), d.a2read('bw_new', r))
    for s in (1, 2, 3):
        EXP['Part A, session %d, round %d (T72A%d)' % (s, r, s)] = a_row(d.aread(d.A72[s], 'bw_old', r), d.aread(d.A72[s], 'bw_new', r))

def f2(x): return '%.2f' % x
def droptxt(dr):
    a, b = '%.1f' % min(dr), '%.1f' % max(dr)
    return a + ' %' if a == b else '%s %% to %s %%' % (a, b)

bad = 0
def chk(cond, msg):
    global bad
    if not cond:
        bad += 1; print('  MISMATCH:', msg)

for fn in sys.argv[1:]:
    s = open(N + '/' + fn).read()
    # axis: tick texts
    ticks = {}
    for m in re.finditer(r'<text x="([\d.]+)" y="[\d.]+" font-size="12" fill="#52514e" text-anchor="middle"[^>]*>(\d+)</text>', s):
        ticks[int(m.group(2))] = float(m.group(1))
    v0 = ticks[0]; k = (ticks[max(ticks)] - v0) / max(ticks)
    print(fn, 'ticks', sorted(ticks.items()), 'scale px per GB/s %.4f' % k)
    for t in sorted(ticks): chk(abs(ticks[t] - (v0 + k * t)) < 0.06, 'tick %d not linear' % t)
    X = lambda v: v0 + k * v
    seen = set()
    # split into groups
    groups = re.findall(r'<g( class="pt")?>(.*?)</g>((?:\s*<text[^>]*>[^<]*</text>)?)', s, flags=re.S)
    npt = ndrop = 0
    for cls, body, after in groups:
        tm = re.search(r'<title>(.*?)</title>', body, flags=re.S)
        if not tm: continue
        title = html.unescape(tm.group(1))
        key = [kk for kk in EXP if title.startswith(kk + ' ·') or title.startswith(kk + ',')]
        chk(len(key) == 1, 'no unique row for title ' + title[:80])
        if len(key) != 1: continue
        e = EXP[key[0]]
        if not cls:
            ndrop += 1
            # drop group
            exp = droptxt(e['drops'])
            chk((': ' + exp + ' (') in title, '%s: drop tooltip, expected %s; title %s' % (key[0], exp, title[:200]))
            chk(('n = %d pair' % e['npairs']) in title, '%s drop n' % key[0])
            lm = re.search(r'<line x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)"', body)
            x1, x2 = float(lm.group(1)), float(lm.group(2))
            chk(abs(x1 - X(med(e['lo']))) < 0.06 and abs(x2 - X(med(e['old']))) < 0.06, '%s drop line ends %s %s exp %.2f %.2f' % (key[0], x1, x2, X(med(e['lo'])), X(med(e['old']))))
            txt = re.search(r'<text[^>]*>([^<]*)</text>', body).group(1)
            chk(html.unescape(txt) == exp, '%s drop text "%s" exp "%s"' % (key[0], txt, exp))
            lines = sorted(e['old_lines'] + e['lo_lines'])
            chk(e['path'] in title, '%s drop source path' % key[0])
            chk(', '.join(str(x) for x in lines) in title, '%s drop source lines exp %s; title %s' % (key[0], lines, title[-200:]))
            seen.add((key[0], 'drop'))
        else:
            npt += 1
            which = 'old' if '(old read kernel)' in title else 'lo'
            vals = e[which]; lines = e[which + '_lines']
            chk(('Median %s GB/s' % f2(med(vals))) in title, '%s %s median tooltip exp %s: %s' % (key[0], which, f2(med(vals)), title[:260]))
            chk(('Intervals: %s GB/s' % ', '.join(f2(v) for v in vals)) in title, '%s %s intervals tooltip exp %s: %s' % (key[0], which, [f2(v) for v in vals], title[:300]))
            chk(('n = %d intervals / 1 process' % len(vals)) in title, '%s %s n' % (key[0], which))
            chk(e['path'] in title, '%s %s source path: %s' % (key[0], which, title[-200:]))
            chk(('lines ' + ', '.join(str(x) for x in lines)) in title, '%s %s source lines exp %s: %s' % (key[0], which, lines, title[-200:]))
            cxs = set(float(x) for x in re.findall(r'<circle[^>]*cx="([\d.]+)"', body))
            chk(len(cxs) == 1 and abs(list(cxs)[0] - X(med(vals))) < 0.06, '%s %s dot cx %s exp %.2f' % (key[0], which, cxs, X(med(vals))))
            pm = re.search(r'<path d="M([\d.]+) [\d.]+V[\d.]+M([\d.]+) [\d.]+V[\d.]+M([\d.]+) [\d.]+H([\d.]+)"', body)
            chk(pm is not None, '%s %s no whisker' % (key[0], which))
            if pm:
                a, b, c, dd = map(float, pm.groups())
                chk(abs(a - X(min(vals))) < 0.06 and abs(b - X(max(vals))) < 0.06 and abs(c - a) < 0.01 and abs(dd - b) < 0.01, '%s %s whisker %s %s exp %.2f %.2f' % (key[0], which, a, b, X(min(vals)), X(max(vals))))
            lab = re.search(r'<text[^>]*>([^<]*)</text>', after)
            chk(lab is not None and lab.group(1) == f2(med(vals)), '%s %s direct label %s exp %s' % (key[0], which, lab.group(1) if lab else None, f2(med(vals))))
            # marker fill convention: hollow for 8000
            is8000 = key[0].startswith('L-1') or key[0].startswith('A-1') or key[0].startswith('A-2')
            hollow = 'class="mk ho"' in body
            chk(hollow == is8000, '%s %s hollow=%s' % (key[0], which, hollow))
            col = '#2a78d6' if which == 'old' else '#eb6834'
            mk = re.search(r'<circle class="mk[^>]*>', body).group(0)
            chk(col in mk, '%s %s colour %s' % (key[0], which, mk))
            seen.add((key[0], which))
    print('  point groups', npt, 'drop groups', ndrop, 'rows seen', len(set(x[0] for x in seen)), 'of', len(EXP))
    for kk in EXP:
        for w in ('drop', 'old', 'lo'):
            chk((kk, w) in seen, 'missing %s %s' % (kk, w))
print('TOTAL MISMATCHES', bad)
