#!/usr/bin/env python3
"""Rows of the older runner bwx (note under Table 2, Table 6): recompute from the raw csv files."""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import R, bwx, med

FILES = {'B7a': 'B7-20261113T232859Z/B7.csv', 'B7b': 'B7-20261114T024352Z/B7.csv',
         'C3a': 'C3-20261114T022708Z/C3.csv', 'C3b': 'C3-20261114T054116Z/C3.csv',
         'B5a': 'B5-20261114T011723Z/B5.csv', 'B5b': 'B5-20261114T043213Z/B5.csv'}

def tag(i):
    m = re.search(r' tag (\S+)', i['proc'] or '')
    return m.group(1) if m else None

def info(i):
    p = i['proc']
    return (re.search(r'loadavg (\S+)', p).group(1), re.search(r'utc (\S+)', p).group(1))

allc = []
for name in ('B7a', 'B7b', 'C3a', 'C3b'):
    ivs = [i for i in bwx(os.path.join(R, FILES[name])) if tag(i) and tag(i).startswith('common-6000-')]
    procs = sorted(set(i['proc'] for i in ivs))
    counts = sorted(set(i['hdr'].get('count') for i in ivs))
    starts = [re.search(r'--start (\S+)', p).group(1) for p in procs]
    seqs = sorted(set(i['hdr'].get('seq') for i in ivs))
    print('%s: %d processes, %d intervals, count=%s, start offset %d / common %d, seq %s, bad n=%d flags=%d' % (
        name, len(procs), len(ivs), counts, starts.count('offset'), starts.count('common'), seqs,
        sum(i['n'] != 120 or i['n0'] != 64 or i['n1'] != 56 for i in ivs), sum(i['flags'] for i in ivs)))
    for i in ivs:
        i['row'] = name
    allc += ivs
procs = sorted(set((i['row'], i['proc']) for i in allc))
print('all: %d processes, %d intervals' % (len(procs), len(allc)))
loads = [float(re.search(r'loadavg (\S+)', p).group(1)) for _, p in procs]
print('load at launch: %.2f to %.2f' % (min(loads), max(loads)))
t = sorted((r, re.search(r'utc (\S+)', p).group(1)) for r, p in procs)
print('launch times per row:', {r: (min(x for rr, x in t if rr == r), max(x for rr, x in t if rr == r)) for r in ('B7a', 'B7b', 'C3a', 'C3b')})
lo = [i for i in allc if i['kernel'] in ('read', 'asmread')]
print('load-only intervals (read, asmread): %d; max read %.2f, max asmread %.2f; min %.2f' % (
    len(lo), max(i['total'] for i in lo if i['kernel'] == 'read'), max(i['total'] for i in lo if i['kernel'] == 'asmread'), min(i['total'] for i in lo)))
for k, pos in (('oldread', 0), ('read', 1), ('asmread', 2), ('asmread2', 3), ('asmread2', 4), ('asmread', 5), ('read', 6), ('oldread', 7)):
    v = [i['total'] for i in allc if i['kernel'] == k and i['pos'] == pos]
    print('  pos %d %-8s n=%d  %.2f to %.2f  median %.2f' % (pos, k, len(v), min(v), max(v), med(v)))

print('--- b5-rev and b5-fwd, every file that holds such a tag')
for name, f in FILES.items():
    ivs = [i for i in bwx(os.path.join(R, f)) if tag(i) and tag(i).startswith('b5-')]
    for p in sorted(set(i['proc'] for i in ivs), key=lambda s: re.search(r'utc (\S+)', s).group(1)):
        q = [i for i in ivs if i['proc'] == p]
        r = [(i['pos'], '%.2f' % i['total'], i['line']) for i in q if i['kernel'] == 'read']
        a = [(i['pos'], '%.2f' % i['total'], i['line']) for i in q if i['kernel'] == 'asmread']
        o = [(i['pos'], '%.2f' % i['total']) for i in q if i['kernel'] == 'oldread']
        print('  %s %s load %s utc %s count=%s: read %s asmread %s oldread %s' % (name, tag(q[0]), info(q[0])[0], info(q[0])[1], q[0]['hdr'].get('count'), r, a, o))
