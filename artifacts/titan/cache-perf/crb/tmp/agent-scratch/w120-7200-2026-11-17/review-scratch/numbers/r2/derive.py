#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rawp import *

D, A, B = load_all()


def g(name, kernel, pos=None, rnd=None, prev='*'):
    return [e['total'] for e in D[name] if e['kernel'] == kernel and (pos is None or e['pos'] == pos)
            and (rnd is None or e['round'] == rnd) and (prev == '*' or e['prev'] == prev)]


def rng(v):
    return '%.2f to %.2f' % (min(v), max(v))


def pairs(name, lo_kernel):
    """drop per round: load-only kernel at pos 1 against oldread of the same round."""
    out = []
    for r in (0, 1):
        o = g(name, 'oldread', rnd=r)
        l = g(name, lo_kernel, rnd=r, pos=1)
        assert len(o) == 1 and len(l) == 1, (name, r, o, l)
        out.append((1 - l[0] / o[0]) * 100)
    return out


print('== Q1 drops per process (bwx)')
for name, k in (('L-1', 'asmread'), ('F72d12', 'asmread'), ('T72L1', 'asmread'), ('T72L2', 'asmread'), ('T72L3', 'asmread'),
                ('T72C1', 'read'), ('T72C2', 'read'), ('T72C3', 'read'), ('T72C4', 'read'), ('T72I1', 'asmread'), ('T72I2', 'asmread')):
    d = pairs(name, k)
    o = g(name, 'oldread'); l = g(name, k, pos=1)
    print(' %-7s drops %s -> %.1f to %.1f | old med %.2f [%s] | lo med %.2f [%s]' % (
        name, ['%.3f' % x for x in d], min(d), max(d), med(o), ', '.join('%.2f' % x for x in o), med(l), ', '.join('%.2f' % x for x in l)))
for grp, names, k in (('C after oldread', ('T72C1', 'T72C3'), 'read'), ('C after asmread', ('T72C2', 'T72C4'), 'read'),
                      ('part L', ('T72L1', 'T72L2', 'T72L3'), 'asmread'), ('control I', ('T72I1', 'T72I2'), 'asmread'),
                      ('F72d12', ('F72d12',), 'asmread'), ('L-1', ('L-1',), 'asmread')):
    d = sum([pairs(n, k) for n in names], [])
    o = sum([g(n, 'oldread') for n in names], [])
    l = sum([g(n, k, pos=1) for n in names], [])
    print(' GROUP %-16s n=%d drop %.3f to %.3f (%.1f to %.1f) old %s lo %s' % (grp, len(d), min(d), max(d), min(d), max(d), rng(o), rng(l)))

print('== Q1 part A')
for s in (1, 2, 3):
    for r in (1, 2):
        o = med([i['v'] for i in A[(s, r, 'bw_old')]['iv']]); n = med([i['v'] for i in A[(s, r, 'bw_new')]['iv']])
        print('  s%d r%d old med %.2f new med %.2f drop %.3f' % (s, r, o, n, (1 - n / o) * 100))
for row in ('A-1', 'A-2'):
    for r in (1, 2):
        o = med([i['v'] for i in B[(row, r, 'bw_old')]['iv']]); n = med([i['v'] for i in B[(row, r, 'bw_new')]['iv']])
        print('  %s r%d old med %.2f new med %.2f drop %.3f' % (row, r, o, n, (1 - n / o) * 100))

print('== Q2 pools')
LN = ('L-1', 'L-2a', 'L-2b', 'L-3', 'L-4a', 'L-4b', 'L-4c')
Lold = sum([g(n, 'oldread', pos=0) for n in LN], [])
Lasm = sum([g(n, 'asmread', pos=1) for n in LN], [])
print(' pool L old n=%d %s med %.4f width %.4f GB/s = %.3f %% of min / %.3f %% of med / %.3f %% of max' % (len(Lold), rng(Lold), med(Lold), max(Lold) - min(Lold), (max(Lold) - min(Lold)) / min(Lold) * 100, (max(Lold) - min(Lold)) / med(Lold) * 100, (max(Lold) - min(Lold)) / max(Lold) * 100))
print(' pool L asm n=%d %s med %.4f width %.4f' % (len(Lasm), rng(Lasm), med(Lasm), max(Lasm) - min(Lasm)))
L10 = sorted(Lasm)[1:]
print(' pool L asm without lowest n=%d %s' % (len(L10), rng(L10)))
PLold = sum([g(n, 'oldread') for n in ('T72L1', 'T72L2', 'T72L3')], [])
PLasm = sum([g(n, 'asmread') for n in ('T72L1', 'T72L2', 'T72L3')], [])
print(' part L old n=%d %s med %.4f ; asm n=%d %s med %.4f' % (len(PLold), rng(PLold), med(PLold), len(PLasm), rng(PLasm), med(PLasm)))
print(' part L old: nearest %.4f (%.3f %% of pool min) ; medians %.4f (%.3f %% of pool med, %.3f %% of partL med)' % (
    max(PLold) - min(Lold), (min(Lold) - max(PLold)) / min(Lold) * 100, med(Lold) - med(PLold), (med(Lold) - med(PLold)) / med(Lold) * 100, (med(Lold) - med(PLold)) / med(PLold) * 100))
print(' part L asm: nearest %.4f ; medians %.4f ; farthest %.4f ; vs pool10 nearest %.4f' % (min(PLasm) - max(Lasm), med(PLasm) - med(Lasm), max(PLasm) - min(Lasm), min(PLasm) - max(L10)))
Fold = g('F72d12', 'oldread'); Fasm = g('F72d12', 'asmread')
print(' F72d12 old %s asm %s med asm %.4f' % (rng(Fold), rng(Fasm), med(Fasm)))
print(' part L asm above F72d12: nearest %.4f medians %.4f farthest %.4f' % (min(PLasm) - max(Fasm), med(PLasm) - med(Fasm), max(PLasm) - min(Fasm)))
L1asm = g('L-1', 'asmread'); L1old = g('L-1', 'oldread')
print(' F72d12 asm above L-1: %.4f ; L-1 old %s asm %s' % (min(Fasm) - max(L1asm), rng(L1old), rng(L1asm)))
Iold = g('T72I1', 'oldread') + g('T72I2', 'oldread'); Iasm = g('T72I1', 'asmread') + g('T72I2', 'asmread')
print(' control I old %s asm %s ; asm above pool %.4f' % (rng(Iold), rng(Iasm), min(Iasm) - max(Lasm)))
CN = ('T72C1', 'T72C2', 'T72C3', 'T72C4')
Cold = sum([g(n, 'oldread') for n in CN], [])
Cold0 = sum([g(n, 'oldread', pos=0) for n in CN], [])
Cold2 = sum([g(n, 'oldread', pos=2) for n in CN], [])
print(' part C old n=%d %s ; pos0 n=%d %s ; pos2 n=%d %s' % (len(Cold), rng(Cold), len(Cold0), rng(Cold0), len(Cold2), rng(Cold2)))
Cro = sum([g(n, 'read', prev='oldread') for n in CN], []); Cra = sum([g(n, 'read', prev='asmread') for n in CN], [])
print(' part C read after oldread n=%d %s ; after asmread n=%d %s' % (len(Cro), rng(Cro), len(Cra), rng(Cra)))
Cao = sum([g(n, 'asmread', prev='oldread') for n in CN], [])
Car = sum([g(n, 'asmread', prev='read') for n in CN], [])
Caf = sum([g(n, 'asmread', prev=None) for n in CN], [])
print(' part C asm after oldread n=%d %s above pool %.4f ; after read n=%d %s ; first n=%d %s' % (len(Cao), rng(Cao), min(Cao) - max(Lasm), len(Car), sorted('%.2f' % x for x in Car), len(Caf), sorted('%.2f' % x for x in Caf)))
three = Fasm + PLasm + Iasm
print(' three visits asm %s span %.4f' % (rng(three), max(three) - min(three)))
six = Fold + PLold + Iold
print(' six rows old %s span %.4f' % (rng(six), max(six) - min(six)))
# overlap checks with L-1 alone
print('== overlap vs pool and vs L-1 alone')
rowsO = {'C old': Cold, 'L old': PLold, 'F old': Fold, 'I old': Iold}
rowsA = {'L asm': PLasm, 'C asm after old': Cao, 'F asm': Fasm, 'I asm': Iasm}
ov = lambda a, b: not (min(a) > max(b) or max(a) < min(b))
for k, v in rowsO.items():
    print('  %-16s pool %s  L-1 %s' % (k, ov(v, Lold), ov(v, L1old)))
for k, v in rowsA.items():
    print('  %-16s pool %s  L-1 %s' % (k, ov(v, Lasm), ov(v, L1asm)))

print('== part A Q2')
old72 = [i['v'] for k, p in A.items() if k[2] == 'bw_old' for i in p['iv']]
pool = [i['v'] for k, p in B.items() if k[2] == 'bw_old' for i in p['iv']]
print(' part A old n=%d %s med %.3f | pool n=%d %s med %.3f width %.2f = %.3f %% of min %.3f %% of med' % (len(old72), rng(old72), med(old72), len(pool), rng(pool), med(pool), max(pool) - min(pool), (max(pool) - min(pool)) / min(pool) * 100, (max(pool) - min(pool)) / med(pool) * 100))
for r in (1, 2):
    s1 = [i['v'] for i in A[(1, r, 'bw_new')]['iv']]
    b = [i['v'] for i in B[('A-1', r, 'bw_new')]['iv']] + [i['v'] for i in B[('A-2', r, 'bw_new')]['iv']]
    pc7 = sorted(set(int(i['passes']) for i in A[(1, r, 'bw_new')]['iv']))
    pc8 = sorted(set(int(i['passes']) for row in ('A-1', 'A-2') for i in B[(row, r, 'bw_new')]['iv']))
    print(' round %d s1 %s vs %s (n=%d) nearest %.2f passes 7200 %s 8000 %s' % (r, rng(s1), rng(b), len(b), min(s1) - max(b), pc7, pc8))
    for s in (2, 3):
        v = [i['v'] for i in A[(s, r, 'bw_new')]['iv']]
        print('    session %d: %s nearest %.2f' % (s, rng(v), min(v) - max(b)))
# count of intervals in fig 2
n_old = len(Lold) + len(Fold) + len(PLold) + len(Cold) + len(Iold) + len(pool) + len(old72)
n_lo = len(Lasm) + len(Fasm) + len(PLasm) + len(Cao) + len(Iasm) + len(Cro) + len(Cra) + len(Car) + len(Caf) + 12 + 18
print('fig2 intervals: old %d + load-only %d = %d' % (n_old, n_lo, n_old + n_lo))
