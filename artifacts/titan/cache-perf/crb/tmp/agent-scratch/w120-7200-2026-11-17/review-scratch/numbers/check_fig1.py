import re, sys, os, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lookup import value_at
v = open('fig1.svg.txt').read()
X0, K = 356.0, 0.98
bad = 0
def r2(x): return '%.2f' % x
# groups
groups = re.findall(r'<g( class="pt")?>\n(.*?)</g>(\n<text[^>]*>([^<]*)</text>)?', v, flags=re.S)
print('groups', len(groups))
rows = {}
for cls, body, _, lab in groups:
    t = re.search(r'<title>(.*?)</title>', body, flags=re.S).group(1)
    row = t.split(' (')[0]
    src = re.search(r'Source: R/(\S+) lines? ([\d, ]+)\.', t)
    f = src.group(1); lines = [int(x) for x in src.group(2).split(',')]
    if cls:
        med = float(re.search(r'Median ([\d.]+) GB/s', t).group(1))
        ivs = [float(x) for x in re.search(r'Intervals: ([\d., ]+) GB/s', t).group(1).split(',')]
        n = int(re.search(r'n = (\d+) intervals', t).group(1))
        raw = [value_at(f, l) for l in lines]
        rv = [x['v'] for x in raw]
        rmed = statistics.median(rv)
        kern = re.search(r'\): (\S+ ?\S*) \(', t).group(1)
        ok = True
        if len(rv) != n or len(ivs) != n: ok = False; print('N MISMATCH', t)
        for a, b in zip(ivs, rv):
            if r2(b) != r2(a): ok = False; print('INTERVAL MISMATCH', row, a, b)
        if r2(rmed) != r2(med): ok = False; print('MEDIAN MISMATCH', row, med, rmed)
        # kernel check
        kk = set(x['kernel'] for x in raw)
        cx = float(re.search(r'<circle class="mk" cx="([\d.]+)"', body).group(1))
        ex = X0 + K * rmed
        if abs(cx - ex) > 0.06: ok = False; print('CX MISMATCH', row, cx, ex)
        w = re.search(r'<path d="M([\d.]+) [\d.]+V[\d.]+M([\d.]+) ', body)
        wl, wh = float(w.group(1)), float(w.group(2))
        if abs(wl - (X0 + K*min(rv))) > 0.06 or abs(wh - (X0 + K*max(rv))) > 0.06: ok = False; print('WHISKER MISMATCH', row, wl, wh, X0+K*min(rv), X0+K*max(rv))
        if lab is None or lab.strip() != r2(rmed): ok = False; print('LABEL MISMATCH', row, lab, r2(rmed))
        fill = re.search(r'<circle class="mk"[^>]*fill="([^"]+)"(?: stroke="([^"]+)")?', body)
        rows.setdefault(row, {})[kern] = dict(f=f, lines=lines, raw=raw, med=rmed, fill=fill.groups(), ok=ok, kk=kk)
        if not ok: bad += 1
    else:
        m = re.search(r'lies ([\d.]+) %(?: to ([\d.]+) %)? below', t)
        lo = m.group(1); hi = m.group(2) or lo
        npairs = int(re.search(r'n = (\d+) pairs?', t).group(1))
        lab2 = re.search(r'<text[^>]*>([^<]*)</text>', body).group(1)
        x1, x2 = re.search(r'<line x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)"', body).groups()
        rows.setdefault(row, {})['drop'] = dict(lo=lo, hi=hi, n=npairs, label=lab2, f=f, lines=lines, x1=float(x1), x2=float(x2), title=t)
print('rows', len(rows))
allpairs = 0
for row, d in rows.items():
    ks = [k for k in d if k != 'drop']
    old = [k for k in ks if 'old' in k][0]; new = [k for k in ks if k != old][0]
    o = d[old]; nw = d[new]; dr = d['drop']
    if 'median' in dr['title'] and 'medians of the two processes' in dr['title']:
        drops = [(1 - nw['med'] / o['med']) * 100]
    else:
        # pair by round
        ob = {x['round']: x['v'] for x in o['raw']}; nb = {x['round']: x['v'] for x in nw['raw']}
        drops = [(1 - nb[r] / ob[r]) * 100 for r in sorted(ob)]
        # check adjacency
        for x in nw['raw']:
            pass
    lo, hi = '%.1f' % min(drops), '%.1f' % max(drops)
    st = 'ok'
    if (lo, hi) != (dr['lo'], dr['hi']) or dr['n'] != len(drops): st = 'DROP MISMATCH'; bad += 1
    exp_label = ('%s %%' % lo) if lo == hi else ('%s %% to %s %%' % (lo, hi))
    if dr['label'] != exp_label: st += ' LABEL MISMATCH'; bad += 1
    if abs(dr['x1'] - (356 + .98 * nw['med'])) > 0.06 or abs(dr['x2'] - (356 + .98 * o['med'])) > 0.06: st += ' LINE MISMATCH'; bad += 1
    if sorted(dr['lines']) != sorted(o['lines'] + nw['lines']): st += ' SRC LINES MISMATCH'; bad += 1
    allpairs += len(drops)
    print('%-45s old %s %s med %.2f fill %s | new %s %s med %.2f fill %s | drops %s page %s-%s n=%d  %s' % (row, old, sorted(o['kk']), o['med'], o['fill'], new, sorted(nw['kk']), nw['med'], nw['fill'], ['%.3f' % x for x in drops], dr['lo'], dr['hi'], dr['n'], st))
print('bad', bad, 'pairs total', allpairs)
