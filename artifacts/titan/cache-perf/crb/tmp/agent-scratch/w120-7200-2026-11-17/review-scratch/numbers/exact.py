"""Exact (Fraction) recomputation of the bwx totals, medians, distances and drops; flags values near a rounding boundary."""
from fractions import Fraction as F
from decimal import Decimal, ROUND_HALF_UP
import os
R = '/home/jhan/workspace/titan/cache-perf/crb/results'
def totals(path):
    out = {}
    for line in open(path):
        if line.startswith('T,'):
            p = line.rstrip('\n').split(',')
            k = (int(p[1]), int(p[2]), p[3])
            out[k] = out.get(k, F(0)) + F(p[6]) / F(p[7]) / F(10**9)
    return out
def r(x, nd=2):
    q = Decimal(1).scaleb(-nd)
    return str((Decimal(x.numerator) / Decimal(x.denominator)).quantize(q, rounding=ROUND_HALF_UP))
def margin(x, nd=2):
    s = x * 10**nd
    frac = s - (s.numerator // s.denominator)
    return float(abs(frac - F(1, 2)))  # distance to the .5 boundary, in units of the last digit
files = {'T72L1':'w120-T72L1-20261117T221329Z/a6456.csv','T72L2':'w120-T72L2-20261117T221638Z/a6456.csv','T72L3':'w120-T72L3-20261117T221947Z/a6456.csv',
 'T72C1':'w120-T72C1-20261117T221436Z/cfwd.csv','T72C2':'w120-T72C2-20261117T221745Z/crev.csv','T72C3':'w120-T72C3-20261117T222054Z/cfwd.csv','T72C4':'w120-T72C4-20261117T222136Z/crev.csv',
 'T72I1':'w120-T72I1-20261117T222700Z/a6456.csv','T72I2':'w120-T72I2-20261117T223227Z/a6456.csv','F72d12':'w120-w120-F72d12-20261117T200231Z/a6456.csv','L-1':'w120-R8-20261117T020549Z/a6456.csv',
 'L-2a':'w120-R1-20261115T185140Z/p1nop.csv','L-2b':'w120-R1-20261115T185140Z/p2add.csv','L-3':'w120-R5-20261115T203152Z/thp.csv','L-4a':'w120-R6-20261115T203438Z/st1.csv','L-4b':'w120-R6-20261115T203438Z/st2.csv','L-4c':'w120-R6-20261115T203438Z/st3.csv'}
T = {n: totals(os.path.join(R, f)) for n, f in files.items()}
def g(n, kern, pos=None, rnd=None):
    return [v for (rd, ps, k), v in sorted(T[n].items()) if k == kern and (pos is None or ps == pos) and (rnd is None or rd == rnd)]
def med(v):
    v = sorted(v); n = len(v)
    return v[n//2] if n % 2 else (v[n//2-1] + v[n//2]) / 2
warn = []
def show(label, x, nd=2):
    m = margin(x, nd)
    flag = '  <-- near boundary' if m < 0.02 else ''
    print('%-58s %s  (exact %.6f, margin %.3f)%s' % (label, r(x, nd), float(x), m, flag))
names = ['L-1','F72d12','T72L1','T72L2','T72L3','T72C1','T72C2','T72C3','T72C4','T72I1','T72I2']
for n in names:
    kn = 'read' if n.startswith('T72C') else 'asmread'
    posn = 1
    o = g(n, 'oldread'); nw = g(n, kn, pos=1)
    for i, x in enumerate(o): show('%s oldread iv%d' % (n, i), x)
    for i, x in enumerate(nw): show('%s %s iv%d' % (n, kn, i), x)
    show('%s oldread median' % n, med(o)); show('%s %s median' % (n, kn), med(nw))
    od = {rd: v for (rd, ps, k), v in T[n].items() if k == 'oldread'}
    nd_ = {rd: v for (rd, ps, k), v in T[n].items() if k == kn and ps == 1}
    for rd in sorted(od): show('%s drop round %d %%' % (n, rd), (1 - nd_[rd] / od[rd]) * 100, 1)
Lold = sum([g(n, 'oldread', pos=0) for n in ('L-1','L-2a','L-2b','L-3','L-4a','L-4b','L-4c')], [])
Lasm = sum([g(n, 'asmread', pos=1) for n in ('L-1','L-2a','L-2b','L-3','L-4a','L-4b','L-4c')], [])
PLold = sum([g(n, 'oldread') for n in ('T72L1','T72L2','T72L3')], []); PLasm = sum([g(n, 'asmread') for n in ('T72L1','T72L2','T72L3')], [])
Fold = g('F72d12','oldread'); Fasm = g('F72d12','asmread'); Iold = g('T72I1','oldread')+g('T72I2','oldread'); Iasm = g('T72I1','asmread')+g('T72I2','asmread')
Cao = g('T72C2','asmread',rnd=1)+g('T72C4','asmread',rnd=1)
for x in sorted(Lold): show('pool old', x)
for x in sorted(Lasm): show('pool asm', x)
for n in ('T72C1','T72C3'):
    for x in g(n,'asmread'): show(n+' asmread after read', x)
for n in ('T72C2','T72C4'):
    for x in g(n,'asmread'): show(n+' asmread', x)
show('pool old width %', (max(Lold)-min(Lold))/min(Lold)*100, 1)
show('L old nearest', min(Lold)-max(PLold)); show('L old nearest %', (min(Lold)-max(PLold))/min(Lold)*100, 1)
show('L old medians', med(Lold)-med(PLold)); show('L old medians %', (med(Lold)-med(PLold))/med(Lold)*100, 1)
show('L asm nearest', min(PLasm)-max(Lasm)); show('L asm medians', med(PLasm)-med(Lasm)); show('L asm farthest', max(PLasm)-min(Lasm))
show('L asm above F nearest', min(PLasm)-max(Fasm)); show('L asm above F medians', med(PLasm)-med(Fasm)); show('L asm above F farthest', max(PLasm)-min(Fasm))
show('F asm above L-1', min(Fasm)-max(g('L-1','asmread'))); show('pool asm width', max(Lasm)-min(Lasm))
show('control I asm above pool', min(Iasm)-max(Lasm)); show('part C asm-after-old above pool', min(Cao)-max(Lasm))
show('six rows old span', max(Fold+PLold+Iold)-min(Fold+PLold+Iold)); show('three visits span', max(Fasm+PLasm+Iasm)-min(Fasm+PLasm+Iasm))
# part A (values are 2-decimal in the csv)
A = {('s1',1):([467.83,467.92,465.38],[330.59,330.09,333.25]),('s1',2):([461.71,461.33,459.90],[327.60,332.82,326.68]),('s2',1):([468.21,468.62,467.85],[322.67,325.26,324.42]),('s2',2):([467.52,467.55,465.89],[330.32,328.62,328.96]),('s3',1):([474.15,469.73,469.37],[315.55,320.46,320.89]),('s3',2):([465.61,465.55,466.63],[336.41,331.45,332.96]),
 ('A-1',1):([465.22,465.14,465.73],[285.06,279.66,280.27]),('A-1',2):([465.78,466.65,464.42],[304.05,299.58,294.02]),('A-2',1):([465.91,464.66,465.47],[288.94,293.39,297.34]),('A-2',2):([467.06,465.74,466.13],[311.51,311.67,316.31])}
for k,(o,n) in A.items():
    o=[F(str(x)) for x in o]; n=[F(str(x)) for x in n]
    show('part A %s r%d drop %%' % k, (1-med(n)/med(o))*100, 1)
show('pool A width %', (F('469.03')-F('463.58'))/F('463.58')*100, 1)
