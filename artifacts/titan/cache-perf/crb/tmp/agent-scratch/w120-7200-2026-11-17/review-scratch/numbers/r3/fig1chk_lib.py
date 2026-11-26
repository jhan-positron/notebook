#!/usr/bin/env python3
"""Check Figure 1 (3 SVG variants) against raw data: tooltips, labels, dot x, whisker x, drop line ends, drop text."""
import re, sys, html, statistics
import data3 as d
from data3 import BW, sel, med, R
N = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/numbers/r3'

# ---- expected rows from raw
def bw_row(key, lo_kernel, lo_pos):
    ivs = BW[key]
    path = ivs[0]['path'].replace(R, 'R')
    o = sel(ivs, 'oldread'); l = sel(ivs, lo_kernel, lo_pos)
    o = sorted(o, key=lambda i: i['round']); l = sorted(l, key=lambda i: i['round'])
    drops = [(1 - b['total'] / a['total']) * 100 for a, b in zip(o, l)]
    return dict(path=path, old=[i['total'] for i in o], lo=[i['total'] for i in l], old_lines=[i['I_line'] for i in o],
                lo_lines=[i['I_line'] for i in l], drops=drops, npairs=len(drops))
def a_row(old, new):
    path = old['path'].replace(R, 'R')
    ov = [i['agg'] for i in old['iv']]; nv = [i['agg'] for i in new['iv']]
    return dict(path=path, old=ov, lo=nv, old_lines=[i['line'] for i in old['iv']], lo_lines=[i['line'] for i in new['iv']],
                drops=[(1 - med(nv) / med(ov)) * 100], npairs=1)
EXP = {
 'L-1': bw_row('L-1', 'asmread', 1), 'F72d12': bw_row('F72d12', 'asmread', 1),
 'Part L, session 1 (T72L1)': bw_row('T72L1', 'asmread', 1), 'Part L, session 2 (T72L2)': bw_row('T72L2', 'asmread', 1),
 'Part L, session 3 (T72L3)': bw_row('T72L3', 'asmread', 1),
 'Part C, T72C1 (cfwd)': bw_row('T72C1', 'read', 1), 'Part C, T72C2 (crev)': bw_row('T72C2', 'read', 1),
 'Part C, T72C3 (cfwd)': bw_row('T72C3', 'read', 1), 'Part C, T72C4 (crev)': bw_row('T72C4', 'read', 1),
 'Control I, T72I1': bw_row('T72I1', 'asmread', 1), 'Control I, T72I2': bw_row('T72I2', 'asmread', 1),
}
for r in (1, 2):
    EXP['A-1, round %d' % r] = a_row(d.aread(d.A1, 'bw_old', r), d.aread(d.A1, 'bw_new', r))
    EXP['A-2, round %d' % r] = a_row(d.a2read('bw_old', r), d.a2read('bw_new', r))
    for s in (1, 2, 3):
        EXP['Part A, session %d, round %d (T72A%d)' % (s, r, s)] = a_row(d.aread(d.A72[s], 'bw_old', r), d.aread(d.A72[s], 'bw_new', r))

def f2(x): return '%.2f' % x
def droptxt(dr):
    a, b = '%.1f' % min(dr), '%.1f' % max(dr)
    return a + ' %' if a == b else '%s %% to %s %%' % (a, b)

