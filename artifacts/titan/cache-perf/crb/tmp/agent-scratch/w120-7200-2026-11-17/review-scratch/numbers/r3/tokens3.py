#!/usr/bin/env python3
"""Sweep: every decimal number token in the page text (outside SVG) must be in the set of values computed from raw.
Unknown tokens are printed with context for manual review."""
import re, statistics
import data3 as d
from data3 import BW, sel, med
N = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/numbers/r3'
known = {}
def add(v, why, nd=2):
    known.setdefault(('%.' + str(nd) + 'f') % v, set()).add(why)
# all interval values
for k, ivs in BW.items():
    for i in ivs:
        if i['kernel'] in ('oldread', 'asmread', 'read'):
            add(i['total'], 'iv %s r%d p%d %s' % (k, i['round'], i['pos'], i['kernel']))
            add(i['I_agg'], 'I_agg %s' % k)
allA = []
for nm, procs in (('A72-1', d.A72[1]), ('A72-2', d.A72[2]), ('A72-3', d.A72[3]), ('A-1', d.A1), ('A-2', d.A2), ('A-3', d.A3)):
    for p in procs:
        if p['kernel'] == 'read':
            for i in p['iv']: add(i['agg'], 'iv %s %s' % (nm, p['binary']))
            add(med([i['agg'] for i in p['iv']]), 'median %s' % nm)
        add(float(p['load']), 'load %s' % nm)
for k in BW:
    for kern in ('oldread', 'asmread', 'read'):
        v = [i['total'] for i in sel(BW[k], kern)]
        if v: add(med(v), 'median %s %s' % (k, kern))
print(len(known), 'known tokens from intervals/medians/loads')
text = open(N + '/text.txt').read()
toks = [(m.group(0), m.start()) for m in re.finditer(r'(?<![\w.:/-])\d+\.\d+(?![\w:-]|\.\d)', text)]
unk = {}
for t, pos in toks:
    if t not in known:
        unk.setdefault(t, []).append(text[max(0, pos - 70):pos + 40].replace('\n', ' / '))
print(len(toks), 'decimal tokens;', len(unk), 'distinct not in interval/median/load set')
for t in sorted(unk, key=lambda x: float(x)):
    print('%-8s x%d  %s' % (t, len(unk[t]), unk[t][0]))
