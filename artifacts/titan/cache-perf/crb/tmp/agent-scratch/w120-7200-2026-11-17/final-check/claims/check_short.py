#!/usr/bin/env python3
"""Recompute the numbers of the Short version and its detail bullets from the raw files."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import R, bwx, parta, med, rng

def sel(ivs, kernel, pos=None):
    return [i for i in ivs if i['kernel'] == kernel and (pos is None or i['pos'] == pos)]

def fmt(v):
    return '%.2f to %.2f' % (min(v), max(v))

# ---------- part C ----------
C = {'T72C1': 'w120-T72C1-20261117T221436Z/cfwd.csv', 'T72C2': 'w120-T72C2-20261117T221745Z/crev.csv',
     'T72C3': 'w120-T72C3-20261117T222054Z/cfwd.csv', 'T72C4': 'w120-T72C4-20261117T222136Z/crev.csv'}
print('== part C: read against oldread of the same process and round')
drops = {}
cold = []
c_asm_after_old = []
asm_pairs = []
for tag, f in C.items():
    ivs = bwx(os.path.join(R, f))
    assert len(ivs) == 6, len(ivs)
    for rnd in (0, 1):
        o = [i for i in ivs if i['round'] == rnd and i['kernel'] == 'oldread'][0]
        r = [i for i in ivs if i['round'] == rnd and i['kernel'] == 'read'][0]
        a = [i for i in ivs if i['round'] == rnd and i['kernel'] == 'asmread'][0]
        d = (1 - r['total'] / o['total']) * 100
        da = (1 - a['total'] / o['total']) * 100
        drops.setdefault('cfwd' if 'cfwd' in f else 'crev', []).append(d)
        asm_pairs.append(da)
        cold.append(o['total'])
        print('  %s round %d: oldread %.3f (pos %d) read %.3f (pos %d) asmread %.3f (pos %d)  read drop %.3f %%  asmread drop %.3f %%  n=%d/%d/%d flags=%d'
              % (tag, rnd, o['total'], o['pos'], r['total'], r['pos'], a['total'], a['pos'], d, da, o['n'], r['n'], a['n'], o['flags'] + r['flags'] + a['flags']))
        if 'crev' in f and rnd == 1:
            c_asm_after_old.append(a['total'])
for k, v in drops.items():
    print('  %s: read drop %.2f to %.2f %% (%d pairs)' % (k, min(v), max(v), len(v)))
allv = drops['cfwd'] + drops['crev']
print('  all 8 pairs: %.2f to %.2f %%' % (min(allv), max(allv)))
print('  8 asmread pairs: %.2f to %.2f %%, all positive: %s' % (min(asm_pairs), max(asm_pairs), all(x > 0 for x in asm_pairs)))
print('  oldread part C: %s (n=%d) median %.2f' % (fmt(cold), len(cold), med(cold)))
print('  asmread after oldread (crev round 1): %s' % fmt(c_asm_after_old))

# ---------- part L and the pool ----------
def lrow(f):
    ivs = bwx(os.path.join(R, f))
    o = [i for i in ivs if i['kernel'] == 'oldread' and i['pos'] == 0]
    a = [i for i in ivs if i['kernel'] == 'asmread' and i['pos'] == 1]
    return o, a

L72 = ['w120-T72L1-20261117T221329Z/a6456.csv', 'w120-T72L2-20261117T221638Z/a6456.csv', 'w120-T72L3-20261117T221947Z/a6456.csv']
POOL = {'L-1': ['w120-R8-20261117T020549Z/a6456.csv'],
        'L-2': ['w120-R1-20261115T185140Z/p1nop.csv', 'w120-R1-20261115T185140Z/p2add.csv'],
        'L-3': ['w120-R5-20261115T203152Z/thp.csv'],
        'L-4': ['w120-R6-20261115T203438Z/st1.csv', 'w120-R6-20261115T203438Z/st2.csv', 'w120-R6-20261115T203438Z/st3.csv']}
lo, la, ldrop = [], [], []
for f in L72:
    o, a = lrow(f)
    lo += [i['total'] for i in o]
    la += [i['total'] for i in a]
    for x, y in zip(o, a):
        assert x['round'] == y['round']
        ldrop.append((1 - y['total'] / x['total']) * 100)
po, pa = [], []
nproc = 0
for row, fs in POOL.items():
    ro, ra = [], []
    for f in fs:
        o, a = lrow(f)
        nproc += 1
        ro += [i['total'] for i in o]
        ra += [i['total'] for i in a]
        print('   %s %s: seq=%s rounds=%s min_ms=%s oldread@0 %s asmread@1 %s' % (row, f.split('/')[-1], o[0]['hdr'].get('seq', '')[:40], o[0]['hdr'].get('rounds'), o[0]['hdr'].get('min_ms'), ['%.2f' % i['total'] for i in o], ['%.2f' % i['total'] for i in a]))
    po += ro
    pa += ra
print('== part L')
print('  7200 oldread: %s n=%d median %.3f' % (fmt(lo), len(lo), med(lo)))
print('  7200 asmread: %s n=%d median %.3f' % (fmt(la), len(la), med(la)))
print('  drop asmread below oldread: %.2f to %.2f %% (%d pairs)' % (min(ldrop), max(ldrop), len(ldrop)))
print('  pool oldread: %s n=%d / %d processes, median %.3f' % (fmt(po), len(po), nproc, med(po)))
print('  pool asmread: %s n=%d, median %.3f' % (fmt(pa), len(pa), med(pa)))
ne = min(po) - max(lo)
md = med(po) - med(lo)
fe = max(po) - min(lo)
print('  oldread: nearest ends %.3f GB/s = %.3f %% of the lower end of the 8000 range (%.2f)' % (ne, ne / min(po) * 100, min(po)))
print('  oldread: medians %.3f GB/s = %.3f %% of the 8000 median (%.2f); %.3f %% of the 7200 median' % (md, md / med(po) * 100, med(po), md / med(lo) * 100))
print('  oldread: farthest ends %.3f GB/s = %.3f %% of the lower end' % (fe, fe / min(po) * 100))
print('  oldread: nearest ends as %% of the upper end of 7200 (%.2f): %.3f' % (max(lo), ne / max(lo) * 100))
print('  width of the 8000 oldread range: %.2f %% of its lower end' % ((max(po) - min(po)) / min(po) * 100))
print('  asmread: part L above pool by %.3f (nearest ends)' % (min(la) - max(pa)))
print('  asmread part C after oldread above pool by %.3f' % (min(c_asm_after_old) - max(pa)))
print('  part C oldread against pool: overlap %s' % (min(cold) <= max(po) and min(po) <= max(cold)))

# F72d12, control I, X2d12
for name, fs in (('F72d12', ['w120-w120-F72d12-20261117T200231Z/a6456.csv']),
                 ('control I', ['w120-T72I1-20261117T222700Z/a6456.csv', 'w120-T72I2-20261117T223227Z/a6456.csv']),
                 ('X2d12', ['w120-X2d12-20261117T040922Z/a6456.csv'])):
    o, a = [], []
    for f in fs:
        x, y = lrow(f)
        o += [i['total'] for i in x]
        a += [i['total'] for i in y]
    print('== %s: oldread %s (n=%d) asmread %s (n=%d)' % (name, fmt(o), len(o), fmt(a), len(a)))
    if name == 'F72d12':
        print('   asmread inside pool: %s; part L above F72d12 by %.3f (nearest ends)' % (min(pa) <= min(a) and max(a) <= max(pa), min(la) - max(a)))
    if name == 'X2d12':
        x_o, x_a = o, a

# pool with X2d12
po2, pa2 = po + x_o, pa + x_a
print('== pool L-1 to L-4 with X2d12: oldread %s, asmread %s' % (fmt(po2), fmt(pa2)))

# ---------- part A ----------
print('== part A')
A72 = ['k120-T72A1-20261117T221209Z/threads120.csv', 'k120-T72A2-20261117T221518Z/threads120.csv', 'k120-T72A3-20261117T221827Z/threads120.csv']
aold = []
sess = {}
for s, f in enumerate(A72, 1):
    ps = parta(os.path.join(R, f))
    assert len(ps) == 24, len(ps)
    for p in ps:
        if p['kernel'] == 'read':
            v = [i['rate'] for i in p['iv']]
            assert len(v) == 3
            sess[(s, p['binary'], p['round'])] = p
            if p['binary'] == 'bw_old':
                aold += v
print('  7200 bw_old read: %s n=%d median %.3f' % (fmt(aold), len(aold), med(aold)))
adrops = []
for s in (1, 2, 3):
    for r in ('1', '2'):
        o = med([i['rate'] for i in sess[(s, 'bw_old', r)]['iv']])
        n = med([i['rate'] for i in sess[(s, 'bw_new', r)]['iv']])
        adrops.append((1 - n / o) * 100)
        print('   session %d round %s: old median %.2f new median %.2f drop %.2f %%  new intervals %s passes %s' % (s, r, o, n, (1 - n / o) * 100, [i['rate'] for i in sess[(s, 'bw_new', r)]['iv']], [i['passes'] for i in sess[(s, 'bw_new', r)]['iv']]))
print('  part A drops: %.2f to %.2f %%' % (min(adrops), max(adrops)))
a1 = parta(os.path.join(R, 'kernels-20261113T181222Z/threads120.csv'))
a2 = parta(os.path.join(R, 'partA-20261113T205055Z/A1.csv'))
a3 = [p for p in parta(os.path.join(R, 'partA-20261113T205055Z/A3.csv')) if p['tag'] and p['tag'].startswith('onebuf-ms500-')]
def rd(ps, binary, kernel='read'):
    return [p for p in ps if p['binary'] == binary and (p['kernel'] == kernel or (p['kernel'] is None and kernel in p['header'].split('--kernel ')[1].split()[0:1]))]
old8 = []
for name, ps in (('A-1', a1), ('A-2', a2), ('A-3', a3)):
    q = rd(ps, 'bw_old')
    v = [i['rate'] for p in q for i in p['iv']]
    old8 += v
    print('  %s bw_old read: %s n=%d / %d processes, median %.3f' % (name, fmt(v), len(v), len(q), med(v)))
print('  pool A-1 to A-3: %s n=%d, median %.3f; width %.2f %% of lower end' % (fmt(old8), len(old8), med(old8), (max(old8) - min(old8)) / min(old8) * 100))
print('  part A overlap with pool: %s; intervals below %d, above %d' % (min(aold) <= max(old8) and min(old8) <= max(aold), sum(x < min(old8) for x in aold), sum(x > max(old8) for x in aold)))
# load-only, session 1 against same round
for name, ps in (('A-1', a1), ('A-2', a2)):
    for p in rd(ps, 'bw_new'):
        print('   %s bw_new read: header line %d round/tag %s/%s load %s: %s passes %s' % (name, p['line'], p['round'], p['tag'], p['load'], [i['rate'] for i in p['iv']], [i['passes'] for i in p['iv']]))
for r, tags in (('1', ('1', 'read_new-r1')), ('2', ('2', 'read_new-r2'))):
    v8 = []
    for ps in (a1, a2):
        for p in rd(ps, 'bw_new'):
            if p['round'] == tags[0] or p['tag'] == tags[1]:
                v8 += [i['rate'] for i in p['iv']]
    v7 = [i['rate'] for i in sess[(1, 'bw_new', r)]['iv']]
    print('  round %s: session 1 %s against 8000 %s (n=%d): above by %.2f to %.2f' % (r, fmt(v7), fmt(v8), len(v8), min(v7) - max(v8), max(v7) - max(v8)))
