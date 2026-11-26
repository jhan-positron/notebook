#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rawp import *

D, A, B = load_all()
f2 = lambda x: '%.2f' % x
f4 = lambda x: '%.4f' % x


def rng(v):
    return '%.2f to %.2f' % (min(v), max(v))


print('=== bwx intervals (kernels oldread/read/asmread)')
for name, ivs in D.items():
    for e in ivs:
        if e['kernel'] not in ('oldread', 'read', 'asmread'):
            continue
        print(' %-7s r%d p%d %-8s prev=%-8s total %.4f Iagg %.2f diff %.4f n=%d ok=%s Iline %d T %d-%d ts %.3f te %.3f %s' % (
            name, e['round'], e['pos'], e['kernel'], e['prev'], e['total'], e['Iagg'], e['total'] - e['Iagg'], e['n'], e['ok'],
            e['Iline'], e['Tlines'][0], e['Tlines'][-1], min(e['ts']), max(e['te']), os.path.basename(e['file'])))

print('max |total - Iagg| over the intervals used:', max(abs(e['total'] - e['Iagg']) for ivs in D.values() for e in ivs if e['kernel'] in ('oldread', 'read', 'asmread')))

print('=== part A 7200')
for k in sorted(A):
    p = A[k]
    v = [i['v'] for i in p['iv']]
    print(' s%d r%d %-6s load %6.2f utc %s hline %d vals %s med %.2f passes %s lines %s' % (k[0], k[1], k[2], p['load'], p['utc'], p['hline'], v, med(v), [i['passes'] for i in p['iv']], [i['line'] for i in p['iv']]))
print('=== part A 8000')
for k in sorted(B):
    p = B[k]
    v = [i['v'] for i in p['iv']]
    print(' %s r%d %-6s tag %s load %6.2f utc %s hline %d vals %s med %.2f passes %s lines %s' % (k[0], k[1], k[2], p['tag'], p['load'], p['utc'], p['hline'], v, med(v), [i['passes'] for i in p['iv']], [i['line'] for i in p['iv']]))
