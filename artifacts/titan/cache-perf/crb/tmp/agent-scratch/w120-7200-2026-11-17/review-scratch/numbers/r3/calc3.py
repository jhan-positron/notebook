#!/usr/bin/env python3
import data3 as d, statistics
from data3 import BW, sel, med
def r2(x): return '%.2f' % x
def rng(v): return '%s to %s' % (r2(min(v)), r2(max(v)))
def tot(ivs): return [i['total'] for i in ivs]

print('### Q1 pairs')
def pairs_L(k):
    out = []
    for rnd in (0, 1):
        o = sel(BW[k], 'oldread', 0, rnd)[0]['total']; a = sel(BW[k], 'asmread', 1, rnd)[0]['total']
        out.append((o, a, (1 - a / o) * 100))
    return out
def pairs_C(k):
    out = []
    for rnd in (0, 1):
        o = sel(BW[k], 'oldread', None, rnd)[0]['total']; a = sel(BW[k], 'read', 1, rnd)[0]['total']
        out.append((o, a, (1 - a / o) * 100))
    return out
for k in ('L-1', 'F72d12', 'T72L1', 'T72L2', 'T72L3', 'T72I1', 'T72I2'):
    p = pairs_L(k)
    print(k, 'old', [r2(x[0]) for x in p], 'med', r2(med([x[0] for x in p])), 'asm', [r2(x[1]) for x in p], 'med', r2(med([x[1] for x in p])), 'drop', ['%.3f' % x[2] for x in p])
for k in ('T72C1', 'T72C2', 'T72C3', 'T72C4'):
    p = pairs_C(k)
    print(k, 'old', [r2(x[0]) for x in p], 'med', r2(med([x[0] for x in p])), 'read', [r2(x[1]) for x in p], 'med', r2(med([x[1] for x in p])), 'drop', ['%.3f' % x[2] for x in p])
def grp(keys, fn):
    ps = [x for k in keys for x in fn(k)]
    return ps
for name, keys, fn in (('C fwd', ('T72C1', 'T72C3'), pairs_C), ('C rev', ('T72C2', 'T72C4'), pairs_C), ('L', ('T72L1', 'T72L2', 'T72L3'), pairs_L), ('I', ('T72I1', 'T72I2'), pairs_L), ('F', ('F72d12',), pairs_L), ('L-1', ('L-1',), pairs_L)):
    ps = grp(keys, fn)
    print(name, 'drop %.3f to %.3f' % (min(x[2] for x in ps), max(x[2] for x in ps)), 'old', rng([x[0] for x in ps]), 'lo', rng([x[1] for x in ps]), 'npairs', len(ps))

print('### part A')
def Amed(procs_get, s=None):
    pass
rowsA = []
for s in (1, 2, 3):
    for r in (1, 2):
        o = d.aread(d.A72[s], 'bw_old', r); n = d.aread(d.A72[s], 'bw_new', r)
        ov = [i['agg'] for i in o['iv']]; nv = [i['agg'] for i in n['iv']]
        rowsA.append((s, r, med(ov), med(nv), (1 - med(nv) / med(ov)) * 100, ov, nv))
        print('s%d r%d old med %s new med %s drop %.3f' % (s, r, r2(med(ov)), r2(med(nv)), (1 - med(nv) / med(ov)) * 100), ov, nv)
print('A72 drop %.3f to %.3f' % (min(x[4] for x in rowsA), max(x[4] for x in rowsA)), 'old medians', rng([x[2] for x in rowsA]), 'new medians r1', rng([x[3] for x in rowsA if x[1] == 1]), 'r2', rng([x[3] for x in rowsA if x[1] == 2]))
rows8 = []
for nm, get in (('A-1', lambda b, r: d.aread(d.A1, b, r)), ('A-2', d.a2read)):
    for r in (1, 2):
        o = get('bw_old', r); n = get('bw_new', r)
        ov = [i['agg'] for i in o['iv']]; nv = [i['agg'] for i in n['iv']]
        rows8.append((nm, r, med(ov), med(nv), (1 - med(nv) / med(ov)) * 100))
        print(nm, 'r%d old med %s new med %s drop %.3f' % (r, r2(med(ov)), r2(med(nv)), (1 - med(nv) / med(ov)) * 100), ov, nv, o['utc'], n['utc'])
print('A8000 drop %.3f to %.3f' % (min(x[4] for x in rows8), max(x[4] for x in rows8)), 'old medians', rng([x[2] for x in rows8]), 'new medians r1', rng([x[3] for x in rows8 if x[1] == 1]), 'r2', rng([x[3] for x in rows8 if x[1] == 2]))

print('### Q2 old read')
A72old = [i['agg'] for s in (1, 2, 3) for r in (1, 2) for i in d.aread(d.A72[s], 'bw_old', r)['iv']]
A8old = [i['agg'] for r in (1, 2) for i in d.aread(d.A1, 'bw_old', r)['iv']] + [i['agg'] for r in (1, 2) for i in d.a2read('bw_old', r)['iv']] + [i['agg'] for n in (1, 2, 3) for i in d.a3(n)['iv']]
print('A72 old', rng(A72old), len(A72old), 'width %.2f' % (max(A72old) - min(A72old)), '| A8 old', rng(A8old), len(A8old), 'width %.2f' % (max(A8old) - min(A8old)), 'pct of low %.3f pct of med %.3f pct of high %.3f' % ((max(A8old) - min(A8old)) / min(A8old) * 100, (max(A8old) - min(A8old)) / med(A8old) * 100, (max(A8old) - min(A8old)) / max(A8old) * 100))
print(' below', sorted(x for x in A72old if x < min(A8old)), 'above', sorted(x for x in A72old if x > max(A8old)))
LP = ('L-1', 'L-2a', 'L-2b', 'L-3', 'L-4a', 'L-4b', 'L-4c')
L8old = [i['total'] for k in LP for i in sel(BW[k], 'oldread', 0)]
L8asm = [i['total'] for k in LP for i in sel(BW[k], 'asmread', 1)]
print('L8 old', rng(L8old), len(L8old), 'med %.3f' % med(L8old), 'width %.3f' % (max(L8old) - min(L8old)), 'pct low %.3f med %.3f' % ((max(L8old) - min(L8old)) / min(L8old) * 100, (max(L8old) - min(L8old)) / med(L8old) * 100))
print('L8 asm', rng(L8asm), len(L8asm), 'med %.3f' % med(L8asm), 'width %.3f' % (max(L8asm) - min(L8asm)))
Lold = [i['total'] for k in ('T72L1', 'T72L2', 'T72L3') for i in sel(BW[k], 'oldread', 0)]
Lasm = [i['total'] for k in ('T72L1', 'T72L2', 'T72L3') for i in sel(BW[k], 'asmread', 1)]
print('L old', rng(Lold), 'med %.3f' % med(Lold), 'nearest %.3f' % (min(L8old) - max(Lold)), 'pct %.3f' % ((min(L8old) - max(Lold)) / min(L8old) * 100), 'med diff %.3f' % (med(L8old) - med(Lold)), 'pct %.3f' % ((med(L8old) - med(Lold)) / med(L8old) * 100))
print('L asm', rng(Lasm), 'med %.3f' % med(Lasm), 'nearest %.3f' % (min(Lasm) - max(L8asm)), 'med diff %.3f' % (med(Lasm) - med(L8asm)), 'farthest %.3f' % (max(Lasm) - min(L8asm)))
Cold = [i['total'] for k in ('T72C1', 'T72C2', 'T72C3', 'T72C4') for i in sel(BW[k], 'oldread')]
print('C old', rng(Cold), len(Cold), 'pos0', rng([i['total'] for k in ('T72C1', 'T72C3') for i in sel(BW[k], 'oldread', 0)]), 'pos2', rng([i['total'] for k in ('T72C2', 'T72C4') for i in sel(BW[k], 'oldread', 2)]))
Fold = tot(sel(BW['F72d12'], 'oldread', 0)); Fasm = tot(sel(BW['F72d12'], 'asmread', 1))
Iold = [i['total'] for k in ('T72I1', 'T72I2') for i in sel(BW[k], 'oldread', 0)]
Iasm = [i['total'] for k in ('T72I1', 'T72I2') for i in sel(BW[k], 'asmread', 1)]
print('F old', rng(Fold), 'asm', rng(Fasm), '| I old', rng(Iold), 'asm', rng(Iasm))
print('F asm vs L-1 asm: %.3f' % (min(Fasm) - max(tot(sel(BW['L-1'], 'asmread', 1)))), 'L-1 asm', rng(tot(sel(BW['L-1'], 'asmread', 1))))
print('I asm nearest above pool %.3f' % (min(Iasm) - max(L8asm)))
print('L asm above F: nearest %.3f med %.3f farthest %.3f' % (min(Lasm) - max(Fasm), med(Lasm) - med(Fasm), max(Lasm) - min(Fasm)))
allv = Fasm + Lasm + Iasm
print('three visits asm span', rng(allv), '%.3f' % (max(allv) - min(allv)))
allo = Fold + Lold + Iold
print('three visits old span', rng(allo), '%.3f' % (max(allo) - min(allo)))
# pool without the lowest
L8asm2 = sorted(L8asm)[1:]
print('pool w/o lowest', rng(L8asm2), len(L8asm2), 'nearest to L %.3f' % (min(Lasm) - max(L8asm2)))
print('### Part A new read s1 vs 8000 per round')
for r in (1, 2):
    n72 = [i['agg'] for i in d.aread(d.A72[1], 'bw_new', r)['iv']]
    n8 = [i['agg'] for i in d.aread(d.A1, 'bw_new', r)['iv']] + [i['agg'] for i in d.a2read('bw_new', r)['iv']]
    print('r%d' % r, rng(n72), 'vs', rng(n8), 'nearest %.3f' % (min(n72) - max(n8)))
print('### Part C groups')
rd_after_old = [i['total'] for k in ('T72C1', 'T72C3') for i in sel(BW[k], 'read', 1)]
rd_after_asm = [i['total'] for k in ('T72C2', 'T72C4') for i in sel(BW[k], 'read', 1)]
asm_after_read = [i['total'] for k in ('T72C1', 'T72C3') for i in sel(BW[k], 'asmread', 2)]
asm_first = [i['total'] for k in ('T72C2', 'T72C4') for i in sel(BW[k], 'asmread', 0, 0)]
asm_after_old = [i['total'] for k in ('T72C2', 'T72C4') for i in sel(BW[k], 'asmread', 0, 1)]
for nm, v in (('read after old', rd_after_old), ('read after asm', rd_after_asm), ('asm after read', asm_after_read), ('asm first', asm_first), ('asm after old', asm_after_old)):
    print(nm, sorted(round(x, 2) for x in v), rng(v))
print('asm after old nearest above pool %.3f' % (min(asm_after_old) - max(L8asm)))
print('### sorted lists')
for k in ('L-1',): pass
def sl(v): return ', '.join(r2(x) for x in sorted(v))
print('L-1 old', sl(tot(sel(BW['L-1'], 'oldread', 0))), '| asm', sl(tot(sel(BW['L-1'], 'asmread', 1))))
print('L-2 old', sl([i['total'] for k in ('L-2a', 'L-2b') for i in sel(BW[k], 'oldread', 0)]), '| asm', sl([i['total'] for k in ('L-2a', 'L-2b') for i in sel(BW[k], 'asmread', 1)]))
print('L-3 old', sl(tot(sel(BW['L-3'], 'oldread', 0))), '| asm', sl(tot(sel(BW['L-3'], 'asmread', 1))))
print('L-4 old', sl([i['total'] for k in ('L-4a', 'L-4b', 'L-4c') for i in sel(BW[k], 'oldread', 0)]), '| asm', sl([i['total'] for k in ('L-4a', 'L-4b', 'L-4c') for i in sel(BW[k], 'asmread', 1)]))
print('F old', sl(Fold), '| asm', sl(Fasm)); print('L old', sl(Lold), '| asm', sl(Lasm)); print('C old', sl(Cold)); print('I old', sl(Iold), '| asm', sl(Iasm))
print('A-1 old', sl([i['agg'] for r in (1, 2) for i in d.aread(d.A1, 'bw_old', r)['iv']]))
print('A-2 old', sl([i['agg'] for r in (1, 2) for i in d.a2read('bw_old', r)['iv']]))
print('A-3 old', sl([i['agg'] for n in (1, 2, 3) for i in d.a3(n)['iv']]))
for s in (1, 2, 3):
    print('S%d old' % s, sl([i['agg'] for r in (1, 2) for i in d.aread(d.A72[s], 'bw_old', r)['iv']]), '| new r1', sl([i['agg'] for i in d.aread(d.A72[s], 'bw_new', 1)['iv']]), '| new r2', sl([i['agg'] for i in d.aread(d.A72[s], 'bw_new', 2)['iv']]))
# I_agg vs sum max diff
mx = max(abs(i['total'] - i['I_agg']) for k in BW for i in BW[k] if i['kernel'] in ('oldread', 'asmread', 'read'))
print('max |sum - I_agg| over used bwx12 intervals: %.4f' % mx)
# count intervals in figure 2
n_old = len(L8old) + len(Fold) + len(Lold) + len(Cold) + len(Iold) + len(A8old) + len(A72old)
n_lo = len(L8asm) + len(Fasm) + len(Lasm) + len(asm_after_old) + len(Iasm) + len(rd_after_old) + len(rd_after_asm) + len(asm_after_read) + len(asm_first) + 12 + 18
print('fig2 n old', n_old, 'lo', n_lo, 'total', n_old + n_lo)
