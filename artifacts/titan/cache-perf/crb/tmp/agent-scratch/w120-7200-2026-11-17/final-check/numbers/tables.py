import sys, os, re, statistics, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *
src = open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html').read()
tables = re.findall(r'<table.*?</table>', src, re.S)
print('tables', len(tables))
def cells(tr):
    return [html.unescape(re.sub(r'<[^>]+>', ' ', c)).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
def rows(t):
    return [cells(tr) for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)]
def bw(path): return parse_bwx(R + '/' + path)[0]
def k(p, kern, **kw):
    return [iv['rate'] for iv in p['iv'] if iv['kernel'] == kern and all(iv[a] == b for a, b in kw.items())]
f2 = lambda v: '%.2f' % v
FILES = {'L-1': 'w120-R8-20261117T020549Z/a6456.csv', 'F72d12': 'w120-w120-F72d12-20261117T200231Z/a6456.csv',
 'T72L1': 'w120-T72L1-20261117T221329Z/a6456.csv', 'T72L2': 'w120-T72L2-20261117T221638Z/a6456.csv', 'T72L3': 'w120-T72L3-20261117T221947Z/a6456.csv',
 'T72C1': 'w120-T72C1-20261117T221436Z/cfwd.csv', 'T72C2': 'w120-T72C2-20261117T221745Z/crev.csv', 'T72C3': 'w120-T72C3-20261117T222054Z/cfwd.csv', 'T72C4': 'w120-T72C4-20261117T222136Z/crev.csv',
 'T72I1': 'w120-T72I1-20261117T222700Z/a6456.csv', 'T72I2': 'w120-T72I2-20261117T223227Z/a6456.csv'}
AF = {'A-1': 'kernels-20261113T181222Z/threads120.csv', 'A-2': 'partA-20261113T205055Z/A1.csv', 'T72A1': 'k120-T72A1-20261117T221209Z/threads120.csv', 'T72A2': 'k120-T72A2-20261117T221518Z/threads120.csv', 'T72A3': 'k120-T72A3-20261117T221827Z/threads120.csv'}
nbad = 0
def bad(m):
    global nbad; nbad += 1; print('  !!', m)
for ti, t in enumerate(tables):
    rs = rows(t)
    head = rs[0] if rs else []
    print('table %d: %d rows, header %s' % (ti, len(rs), [h[:25] for h in head]))
    if head and head[0] == 'Row' and 'Drop' in head[-1]:
        n = 0
        for r in rs[1:]:
            if len(r) != 6: continue
            name = r[0]
            key = next((x for x in list(FILES) + list(AF) if (x in name)), None)
            if key in FILES:
                p = bw(FILES[key]); lo_k = 'read' if 'Part C' in name else 'asmread'
                o = k(p, 'oldread'); l = k(p, lo_k)
                if 'Part C' in name:
                    pass
                drops = []
                for rnd in (0, 1):
                    oo = k(p, 'oldread', round=rnd)[0]; ll = k(p, lo_k, round=rnd)[0]; drops.append((1 - ll / oo) * 100)
            else:
                rnd = int(re.search(r'round (\d)', name)[1])
                ps = parse_bandwidth(R + '/' + AF[key])
                o = [iv['agg'] for p in ps if p['binary'] == 'bw_old' and p['kernel'] == 'read' and p['round'] == rnd for iv in p['iv']]
                l = [iv['agg'] for p in ps if p['binary'] == 'bw_new' and p['kernel'] == 'read' and p['round'] == rnd for iv in p['iv']]
                drops = [(1 - statistics.median(l) / statistics.median(o)) * 100]
            exp = [f2(statistics.median(o)), ', '.join(f2(x) for x in o), f2(statistics.median(l)), ', '.join(f2(x) for x in l)]
            d1, d2 = '%.1f' % min(drops), '%.1f' % max(drops)
            exp.append('%s %%' % d1 if d1 == d2 else '%s %% to %s %%' % (d1, d2))
            if r[1:] != exp: bad('row "%s": page %s vs raw %s' % (name[:40], r[1:], exp))
            n += 1
        print('   checked %d rows of the Figure 1 table view' % n)
    if head and head[0] == 'Row' and 'sorted' in head[-1]:
        n = 0; tot = 0
        for r in rs[1:]:
            if len(r) != 3: continue
            vals = [x.strip() for x in r[2].split(',')]
            if int(r[1]) != len(vals): bad('row %s: n %s vs %d values' % (r[0][:30], r[1], len(vals)))
            if vals != sorted(vals, key=float): bad('row %s not sorted' % r[0][:30])
            tot += len(vals); n += 1
        print('   %d rows, %d intervals in the Figure 2 table view' % (n, tot))
print('bad', nbad)
