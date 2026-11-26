import re, html, pickle, statistics, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
s = open('report-snapshot.html').read()
tables = re.findall(r'<table.*?</table>', s, flags=re.S)
print('tables', len(tables))
def cells(t):
    rows = []
    for tr in re.findall(r'<tr.*?</tr>', t, flags=re.S):
        cs = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.S)
        cs = [html.unescape(re.sub(r'<br\s*/?>', ' / ', c)) for c in cs]
        cs = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c)).strip() for c in cs]
        rows.append(cs)
    return rows
T = [cells(t) for t in tables]
for i, t in enumerate(T):
    cap = re.search(r'<caption[^>]*>(.*?)</caption>', tables[i], flags=re.S)
    print(i, len(t), 'rows', '| caption:', re.sub(r'<[^>]+>', '', cap.group(1))[:80] if cap else None, '| header:', t[0][:3])
pickle.dump(T, open('tables.pkl', 'wb'))
d = pickle.load(open('raw.pkl', 'rb'))
A, B, D = d['A'], d['B'], d['D']
med = statistics.median
def f2(x): return '%.2f' % x
def g(name, kernel, pos=None, rnd=None):
    return [i['total'] for i in D[name] if i['kernel'] == kernel and (pos is None or i['pos'] == pos) and (rnd is None or i['round'] == rnd)]
bad = 0
# ---- Table view of Figure 1
tv1 = [t for t in T if t and t[0] and t[0][0] == 'Row' and 'Drop' in t[0][-1]][0]
exp = {}
def bw(name, kn):
    o = g(name, 'oldread'); n = g(name, kn)
    od = {i['round']: i['total'] for i in D[name] if i['kernel'] == 'oldread'}
    nd = {i['round']: i['total'] for i in D[name] if i['kernel'] == kn}
    drops = [(1 - nd[r] / od[r]) * 100 for r in sorted(od)]
    return o, n, drops
keymap = [('L-1 ·', 'L-1', 'asmread'), ('F72d12', 'F72d12', 'asmread'), ('session 1 (T72L1)', 'T72L1', 'asmread'), ('session 2 (T72L2)', 'T72L2', 'asmread'), ('session 3 (T72L3)', 'T72L3', 'asmread'),
          ('T72C1', 'T72C1', 'read'), ('T72C2', 'T72C2', 'read'), ('T72C3', 'T72C3', 'read'), ('T72C4', 'T72C4', 'read'), ('T72I1', 'T72I1', 'asmread'), ('T72I2', 'T72I2', 'asmread')]
def dropstr(drops):
    lo, hi = '%.1f' % min(drops), '%.1f' % max(drops)
    return lo + ' %' if lo == hi else '%s %% to %s %%' % (lo, hi)
n_checked = 0
for row in tv1[1:]:
    if len(row) < 6: continue
    name = row[0]
    e = None
    for k, nm, kn in keymap:
        if k in name:
            o, n, drops = bw(nm, kn)
            e = [f2(med(o)), ', '.join(f2(x) for x in o), f2(med(n)), ', '.join(f2(x) for x in n), dropstr(drops)]
    m = re.match(r'(A-[12]), round (\d)', name)
    if m:
        o = B[(m.group(1), int(m.group(2)), 'bw_old')]; n = B[(m.group(1), int(m.group(2)), 'bw_new')]
        e = [f2(med(o)), ', '.join(f2(x) for x in o), f2(med(n)), ', '.join(f2(x) for x in n), dropstr([(1 - med(n) / med(o)) * 100])]
    m = re.match(r'Session (\d), round (\d)', name)
    if m:
        o = A[(int(m.group(1)), int(m.group(2)), 'bw_old')][0]; n = A[(int(m.group(1)), int(m.group(2)), 'bw_new')][0]
        e = [f2(med(o)), ', '.join(f2(x) for x in o), f2(med(n)), ', '.join(f2(x) for x in n), dropstr([(1 - med(n) / med(o)) * 100])]
    if e is None: print('NO KEY', row); bad += 1; continue
    n_checked += 1
    if row[1:6] != e: print('TV1 MISMATCH', name, row[1:6], e); bad += 1
print('table view fig1 rows checked', n_checked, 'bad', bad)
# ---- Table view of Figure 2
tv2 = [t for t in T if t and t[0] and t[0][0] == 'Row' and 'Memory speed' in t[0]][0]
fr = pickle.load(open('fig2rows.pkl', 'rb'))
print('table view fig2 rows:', len([r for r in tv2 if len(r) == 4]) - 1)
tot = 0
seq = [k for k in fr]
datarows = [r for r in tv2[1:] if len(r) == 4]
print(len(seq), len(datarows))
for k, r in zip(seq, datarows):
    vals = sorted(fr[k])
    es = ', '.join(f2(x) for x in vals)
    tot += len(vals)
    ok = (r[3] == es and int(r[2]) == len(vals))
    sp = '8000 MT/s' if (k[1].startswith('L-') or k[1].startswith('A-')) else '7200 MT/s'
    if r[1] != sp: ok = False
    print('  %-5s %-60s | %-70s %s' % (k[0], k[1][:60], r[0][:70], 'ok' if ok else 'MISMATCH ' + r[3] + ' vs ' + es))
    if not ok: bad += 1
print('total intervals in table view fig2', tot, 'bad', bad)
