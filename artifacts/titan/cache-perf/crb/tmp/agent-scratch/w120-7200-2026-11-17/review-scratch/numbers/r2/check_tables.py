#!/usr/bin/env python3
"""Check the two 'table view' tables (Figure 1 rows, Figure 2 intervals) against the raw files."""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rawp import *

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, 'tables.json')))
D, A, B = load_all()
bad = 0


def err(*a):
    global bad
    bad += 1
    print('MISMATCH', *a)


def g(name, kernel, pos=None, rnd=None, prev='*'):
    return [e['total'] for e in D[name] if e['kernel'] == kernel and (pos is None or e['pos'] == pos)
            and (rnd is None or e['round'] == rnd) and (prev == '*' or e['prev'] == prev)]


f2 = lambda v: ', '.join('%.2f' % x for x in v)


def droptxt(d):
    a, b = '%.1f' % min(d), '%.1f' % max(d)
    return a + ' %' if a == b else '%s %% to %s %%' % (a, b)


# ---- table view of Figure 1
exp = []
for name, k in (('L-1', 'asmread'), ('F72d12', 'asmread'), ('T72L1', 'asmread'), ('T72L2', 'asmread'), ('T72L3', 'asmread'),
                ('T72C1', 'read'), ('T72C2', 'read'), ('T72C3', 'read'), ('T72C4', 'read'), ('T72I1', 'asmread'), ('T72I2', 'asmread')):
    o = [g(name, 'oldread', rnd=r)[0] for r in (0, 1)]
    l = [g(name, k, rnd=r, pos=1)[0] for r in (0, 1)]
    d = [(1 - b / a) * 100 for a, b in zip(o, l)]
    exp.append((name, '%.2f' % med(o), f2(o), '%.2f' % med(l), f2(l), droptxt(d)))
for row, r in (('A-1', 1), ('A-1', 2), ('A-2', 1), ('A-2', 2)):
    o = [i['v'] for i in B[(row, r, 'bw_old')]['iv']]; l = [i['v'] for i in B[(row, r, 'bw_new')]['iv']]
    exp.append(('%s, round %d' % (row, r), '%.2f' % med(o), f2(o), '%.2f' % med(l), f2(l), droptxt([(1 - med(l) / med(o)) * 100])))
for s in (1, 2, 3):
    for r in (1, 2):
        o = [i['v'] for i in A[(s, r, 'bw_old')]['iv']]; l = [i['v'] for i in A[(s, r, 'bw_new')]['iv']]
        exp.append(('Session %d, round %d' % (s, r), '%.2f' % med(o), f2(o), '%.2f' % med(l), f2(l), droptxt([(1 - med(l) / med(o)) * 100])))
rows = [r for r in T[1]['rows'][1:] if len(r) == 6]
print('fig1 table rows', len(rows), 'expected', len(exp))
for r, e in zip(rows, exp):
    key = e[0]
    if key not in r[0]:
        err('row name', r[0], key)
    if tuple(r[1:]) != e[1:]:
        err(r[0], r[1:], e[1:])
    else:
        print('  ok', r[0][:40], r[1:])

# ---- table view of Figure 2
LN2 = {'L-1 (6 s)': ('L-1',), 'L-2 (4 s)': ('L-2a', 'L-2b'), 'L-3 (4 s)': ('L-3',), 'L-4 (4 s)': ('L-4a', 'L-4b', 'L-4c')}
CN = ('T72C1', 'T72C2', 'T72C3', 'T72C4')
sect = None
n_total = 0
for r in T[5]['rows'][1:]:
    if len(r) == 1:
        sect = r[0]
        print(' --', sect)
        continue
    name, n, vals = r
    old = sect.startswith('Old read kernel')
    k8 = '8000 MT/s' in sect
    v = None
    first = name.split(' 1')[0] if False else name
    if 'bwx12' in sect:
        if name in LN2:
            v = sum([g(x, 'oldread' if old else 'asmread', pos=0 if old else 1) for x in LN2[name]], [])
        elif name.startswith('F72d12'):
            v = g('F72d12', 'oldread' if old else 'asmread')
        elif name.startswith('Part L'):
            v = sum([g(x, 'oldread' if old else 'asmread') for x in ('T72L1', 'T72L2', 'T72L3')], [])
        elif name.startswith('Control I'):
            v = sum([g(x, 'oldread' if old else 'asmread') for x in ('T72I1', 'T72I2')], [])
        elif name.startswith('Part C (4 processes)'):
            v = sum([g(x, 'oldread') for x in CN], [])
        elif name.startswith('Part C (crev, round 1)'):
            v = sum([g(x, 'asmread', prev='oldread') for x in CN], [])
        elif name.startswith('Part C, read new read kernel, after oldread'):
            v = sum([g(x, 'read', prev='oldread') for x in CN], [])
        elif name.startswith('Part C, read new read kernel, after asmread'):
            v = sum([g(x, 'read', prev='asmread') for x in CN], [])
        elif name.startswith('Part C, asmread after read'):
            v = sum([g(x, 'asmread', prev='read') for x in CN], [])
        elif name.startswith('Part C, asmread first interval'):
            v = sum([g(x, 'asmread', prev=None) for x in CN], [])
    else:
        rnd = [int(x) for x in re.findall(r'round (\d)', sect)]
        b = 'bw_old' if old else 'bw_new'
        if name[:3] in ('A-1', 'A-2', 'A-3'):
            v = [i['v'] for k, p in B.items() if k[0] == name[:3] and k[2] == b and (not rnd or k[1] == rnd[0]) for i in p['iv']]
        else:
            s = int(re.search(r'Session (\d)', name).group(1))
            v = [i['v'] for k, p in A.items() if k[0] == s and k[2] == b and (not rnd or k[1] == rnd[0]) for i in p['iv']]
    if v is None:
        err('unknown row', sect, name)
        continue
    want = ', '.join('%.2f' % x for x in sorted(v))
    n_total += len(v)
    if int(n) != len(v) or vals != want:
        err(sect, name, n, vals, '| raw', len(v), want)
    else:
        print('   ok %-70s %s %s' % (name[:70], n, vals[:60]))
print('fig2 table intervals', n_total)
print('MISMATCHES', bad)
