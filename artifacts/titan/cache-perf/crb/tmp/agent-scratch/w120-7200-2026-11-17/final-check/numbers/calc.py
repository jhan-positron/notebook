#!/usr/bin/env python3
import sys, os, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *

def bw(path):
    ps = parse_bwx(R + path)
    assert len(ps) == 1
    return ps[0]

def get(p, kernel, pos=None, rnd=None):
    return [iv for iv in p['iv'] if iv['kernel'] == kernel and (pos is None or iv['pos'] == pos) and (rnd is None or iv['round'] == rnd)]

def rng(v):
    return '%.2f to %.2f (n=%d, med %.3f, width %.3f)' % (min(v), max(v), len(v), statistics.median(v), max(v) - min(v))

L = {k: bw(f) for k, f in [('T72L1', '/w120-T72L1-20261117T221329Z/a6456.csv'), ('T72L2', '/w120-T72L2-20261117T221638Z/a6456.csv'), ('T72L3', '/w120-T72L3-20261117T221947Z/a6456.csv')]}
C = {k: bw(f) for k, f in [('T72C1', '/w120-T72C1-20261117T221436Z/cfwd.csv'), ('T72C2', '/w120-T72C2-20261117T221745Z/crev.csv'), ('T72C3', '/w120-T72C3-20261117T222054Z/cfwd.csv'), ('T72C4', '/w120-T72C4-20261117T222136Z/crev.csv')]}
I = {k: bw(f) for k, f in [('T72I1', '/w120-T72I1-20261117T222700Z/a6456.csv'), ('T72I2', '/w120-T72I2-20261117T223227Z/a6456.csv')]}
F = bw('/w120-w120-F72d12-20261117T200231Z/a6456.csv')
L1 = bw('/w120-R8-20261117T020549Z/a6456.csv')
POOL = {'L-1': [L1], 'L-2': [bw('/w120-R1-20261115T185140Z/p1nop.csv'), bw('/w120-R1-20261115T185140Z/p2add.csv')],
        'L-3': [bw('/w120-R5-20261115T203152Z/thp.csv')],
        'L-4': [bw('/w120-R6-20261115T203438Z/st%d.csv' % i) for i in (1, 2, 3)]}
X2 = bw('/w120-X2d12-20261117T040922Z/a6456.csv')
D10 = {'X1d10': bw('/w120-X1d10-20261117T034916Z/a6456.csv'), 'X1d10b': bw('/w120-X1d10b-20261117T040407Z/a6456.csv'), 'BASEd10': bw('/w120-BASEd10-20261117T041738Z/a6456.csv')}

def pairs(p, lo_kernel, lo_pos=None):
    out = []
    for rnd in sorted({iv['round'] for iv in p['iv']}):
        o = get(p, 'oldread', rnd=rnd); l = get(p, lo_kernel, pos=lo_pos, rnd=rnd)
        assert len(o) == 1 and len(l) == 1, (len(o), len(l))
        out.append((o[0]['rate'], l[0]['rate'], (1 - l[0]['rate'] / o[0]['rate']) * 100))
    return out

print('##### PART C drops (read vs oldread)')
alld = []
for k in ('T72C1', 'T72C3', 'T72C2', 'T72C4'):
    pr = pairs(C[k], 'read')
    alld += [x[2] for x in pr]
    print(k, C[k]['meta']['seq'], ['old %.2f read %.2f drop %.3f' % x for x in pr], 'median old %.3f read %.3f' % (statistics.median([x[0] for x in pr]), statistics.median([x[1] for x in pr])))
print(' all 8: %.3f to %.3f' % (min(alld), max(alld)))
for grp in (('T72C1', 'T72C3'), ('T72C2', 'T72C4')):
    pr = [x for k in grp for x in pairs(C[k], 'read')]
    print(grp, 'drop %.3f to %.3f' % (min(x[2] for x in pr), max(x[2] for x in pr)), 'old', rng([x[0] for x in pr]), 'read', rng([x[1] for x in pr]))
print('##### PART C asmread pairs')
for k in C:
    pr = pairs(C[k], 'asmread')
    print(k, ['old %.2f asm %.2f drop %.3f' % x for x in pr])
print('part C oldread all', rng([iv['rate'] for k in C for iv in get(C[k], 'oldread')]))
print('part C oldread pos0', rng([iv['rate'] for k in C for iv in get(C[k], 'oldread', pos=0)]))
print('part C oldread pos2', rng([iv['rate'] for k in C for iv in get(C[k], 'oldread', pos=2)]))
print('part C asmread after read (cfwd pos2)', rng([iv['rate'] for k in ('T72C1', 'T72C3') for iv in get(C[k], 'asmread')]), sorted('%.2f' % iv['rate'] for k in ('T72C1', 'T72C3') for iv in get(C[k], 'asmread')))
print('part C asmread first (crev rd0 pos0)', sorted('%.2f' % iv['rate'] for k in ('T72C2', 'T72C4') for iv in get(C[k], 'asmread', rnd=0)))
print('part C asmread after oldread (crev rd1 pos0)', sorted('%.2f' % iv['rate'] for k in ('T72C2', 'T72C4') for iv in get(C[k], 'asmread', rnd=1)))

print('##### PART L')
for k in L:
    pr = pairs(L[k], 'asmread')
    print(k, ['old %.2f asm %.2f drop %.3f' % x for x in pr], 'median old %.3f asm %.3f' % (statistics.median([x[0] for x in pr]), statistics.median([x[1] for x in pr])))
Lold = [iv['rate'] for k in L for iv in get(L[k], 'oldread')]
Lasm = [iv['rate'] for k in L for iv in get(L[k], 'asmread')]
print('L old', rng(Lold), sorted('%.2f' % x for x in Lold)); print('L asm', rng(Lasm), sorted('%.2f' % x for x in Lasm))
pr = [x for k in L for x in pairs(L[k], 'asmread')]
print('L drops %.3f to %.3f' % (min(x[2] for x in pr), max(x[2] for x in pr)))
print('##### Control I')
for k in I:
    pr = pairs(I[k], 'asmread')
    print(k, ['old %.2f asm %.2f drop %.3f' % x for x in pr], 'median old %.3f asm %.3f' % (statistics.median([x[0] for x in pr]), statistics.median([x[1] for x in pr])))
Iold = [iv['rate'] for k in I for iv in get(I[k], 'oldread')]
Iasm = [iv['rate'] for k in I for iv in get(I[k], 'asmread')]
print('I old', rng(Iold), sorted('%.2f' % x for x in Iold)); print('I asm', rng(Iasm), sorted('%.2f' % x for x in Iasm))
print('##### F72d12')
pr = pairs(F, 'asmread'); print(['old %.2f asm %.2f drop %.3f' % x for x in pr])
Fold = [iv['rate'] for iv in get(F, 'oldread')]; Fasm = [iv['rate'] for iv in get(F, 'asmread')]
print('F old', rng(Fold)); print('F asm', rng(Fasm))
print('##### L-1')
pr = pairs(L1, 'asmread'); print(['old %.2f asm %.2f drop %.3f' % x for x in pr])
print('##### pool L-1..L-4')
Pold, Pasm = [], []
for row, ps in POOL.items():
    o = [iv['rate'] for p in ps for iv in get(p, 'oldread', pos=0)]
    a = [iv['rate'] for p in ps for iv in get(p, 'asmread', pos=1)]
    print(row, 'old', sorted('%.2f' % x for x in o), 'asm', sorted('%.2f' % x for x in a), 'nproc', len(ps))
    Pold += o; Pasm += a
print('pool old', rng(Pold)); print('pool asm', rng(Pasm))
L1old = [iv['rate'] for iv in get(L1, 'oldread')]; L1asm = [iv['rate'] for iv in get(L1, 'asmread')]

def cmp(name, a, b):
    """a = 7200 values, b = 8000 values"""
    ov = not (min(a) > max(b) or max(a) < min(b))
    if ov:
        d = 0
    elif min(a) > max(b):
        d = min(a) - max(b)
    else:
        d = -(min(b) - max(a))
    far = (max(a) - min(b)) if statistics.median(a) > statistics.median(b) else -(max(b) - min(a))
    print('  CMP %-34s 7200 %.2f-%.2f n=%d | 8000 %.2f-%.2f n=%d | overlap %s | nearest %+.4f | medians %+.4f | farthest %+.4f | width8000 %.3f = %.3f%% of low end, %.3f%% of high' % (
        name, min(a), max(a), len(a), min(b), max(b), len(b), ov, d, statistics.median(a) - statistics.median(b), far, max(b) - min(b), (max(b) - min(b)) / min(b) * 100, (max(b) - min(b)) / max(b) * 100))
    return ov, d

print('##### Table 2 old read')
Cold = [iv['rate'] for k in C for iv in get(C[k], 'oldread')]
cmp('C old vs pool', Cold, Pold)
cmp('C old pos0 vs pool', [iv['rate'] for k in C for iv in get(C[k], 'oldread', pos=0)], Pold)
cmp('L old vs pool', Lold, Pold)
print('   L nearest %% of low end of 8000: %.3f ; medians %% of 8000 median: %.3f' % ((min(Pold) - max(Lold)) / min(Pold) * 100, (statistics.median(Pold) - statistics.median(Lold)) / statistics.median(Pold) * 100))
cmp('F old vs pool', Fold, Pold)
cmp('I old vs pool', Iold, Pold)
print('##### Table 2 load-only')
cmp('L asm vs pool', Lasm, Pasm)
Casm_after_old = [iv['rate'] for k in ('T72C2', 'T72C4') for iv in get(C[k], 'asmread', rnd=1)]
cmp('C asm after oldread vs pool', Casm_after_old, Pasm)
cmp('F asm vs pool', Fasm, Pasm)
cmp('I asm vs pool', Iasm, Pasm)
print('L-1 alone:')
for nm, a, b in [('C old', Cold, L1old), ('L old', Lold, L1old), ('F old', Fold, L1old), ('I old', Iold, L1old), ('L asm', Lasm, L1asm), ('C asm aft old', Casm_after_old, L1asm), ('F asm', Fasm, L1asm), ('I asm', Iasm, L1asm)]:
    cmp(nm + ' vs L-1', a, b)
print('pool + X2d12:')
X2old = [iv['rate'] for iv in get(X2, 'oldread')]; X2asm = [iv['rate'] for iv in get(X2, 'asmread')]
print(' X2 old', rng(X2old), 'asm', rng(X2asm))
for nm, a, b in [('C old', Cold, Pold + X2old), ('L old', Lold, Pold + X2old), ('F old', Fold, Pold + X2old), ('I old', Iold, Pold + X2old), ('L asm', Lasm, Pasm + X2asm), ('C asm aft old', Casm_after_old, Pasm + X2asm), ('F asm', Fasm, Pasm + X2asm), ('I asm', Iasm, Pasm + X2asm)]:
    cmp(nm + ' vs pool+X2', a, b)
print('##### Table 4')
cmp('L asm vs pool', Lasm, Pasm)
cmp('L asm vs F', Lasm, Fasm)
print('##### 3 visits')
allasm = Lasm + Iasm + Fasm; allold = Lold + Iold + Fold
print(' asm', rng(allasm), ' old', rng(allold))
cmp('I asm vs F asm', Iasm, Fasm); cmp('L asm vs I asm', Lasm, Iasm)
print('##### pool without lowest')
P2 = sorted(Pasm)[1:]
print(rng(P2)); cmp('L asm vs pool-minus-lowest', Lasm, P2)
print('##### 10-module boots')
for k, p in D10.items():
    o = [iv['rate'] for iv in get(p, 'oldread')]; a = [iv['rate'] for iv in get(p, 'asmread')]
    print(k, 'old', ['%.2f' % x for x in o], 'asm', ['%.2f' % x for x in a], 'asm median %.3f' % statistics.median(a))
o10 = [iv['rate'] for p in D10.values() for iv in get(p, 'oldread')]
print(' old 3 boots', rng(o10), 'width %% low %.3f high %.3f' % ((max(o10) - min(o10)) / min(o10) * 100, (max(o10) - min(o10)) / max(o10) * 100))
m1 = statistics.median([iv['rate'] for iv in get(D10['X1d10'], 'asmread')]); m2 = statistics.median([iv['rate'] for iv in get(D10['X1d10b'], 'asmread')])
print(' X1d10 vs X1d10b asm medians %.3f %.3f : %.3f %% of lower' % (m1, m2, (m2 - m1) / m1 * 100))
m3 = statistics.median([iv['rate'] for iv in get(D10['BASEd10'], 'asmread')])
print(' BASEd10 median %.3f ; vs X1d10 %.3f%% ; vs X1d10b %.3f%%' % (m3, (m3 - m1) / m1 * 100, (m2 - m3) / m3 * 100))
print('##### max |sum - I_agg| over used bwx12 intervals')
mx = 0
for p in list(L.values()) + list(C.values()) + list(I.values()) + [F, L1, X2] + [q for ps in POOL.values() for q in ps] + list(D10.values()):
    for iv in p['iv']:
        if iv['kernel'] in ('oldread', 'asmread', 'read'):
            mx = max(mx, abs(iv['rate'] - iv['I_agg']))
print(' %.4f' % mx)
