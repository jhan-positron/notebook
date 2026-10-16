#!/usr/bin/env python3
"""spans_compare.py <dir> <prompt> <arm>...: side-by-side span statistics from trace_spans.py reports.

Reads <dir>/spans-<arm>-p<prompt>.txt for every arm and prints, per span name, n / mean us / sum ms per arm,
then the decode forwards (forwards whose Save K count equals the layer count, 36 here): count, mean and
median duration, and the mean Save K sum per decode forward. Decode forward = one generation step.
"""
import re
import statistics
import sys

d, prompt, arms = sys.argv[1], sys.argv[2], sys.argv[3:]
LAYERS = 36
rows = {}
dec = {}
for arm in arms:
    txt = open(f'{d}/spans-{arm}-p{prompt}.txt').read().splitlines()
    for ln in txt:
        m = re.match(r'^(\S.*?)\s+n=\s*(\d+) mean=\s*([\d.]+) us min=\s*([\d.]+) us max=\s*([\d.]+) us sum=\s*([\d.]+) ms', ln)
        if m:
            rows.setdefault(m.group(1).strip(), {})[arm] = (int(m.group(2)), float(m.group(3)), float(m.group(6)))
        m = re.match(r'^forward ts=\d+ dur=([\d.]+) us\s+Save K n=(\d+) sum=([\d.]+) us', ln)
        if m and int(m.group(2)) == LAYERS:
            dec.setdefault(arm, []).append((float(m.group(1)), float(m.group(3))))
print(f'prompt {prompt}: ' + ' | '.join(arms))
print('| span | ' + ' | '.join(f'{a} n / mean us / sum ms' for a in arms) + ' |')
print('|---|' + '---|' * len(arms))
for name, per in rows.items():
    print(f'| {name} | ' + ' | '.join((f'{per[a][0]} / {per[a][1]:.1f} / {per[a][2]:.1f}' if a in per else 'none') for a in arms) + ' |')
print()
print('| decode forwards | ' + ' | '.join(arms) + ' |')
print('|---|' + '---|' * len(arms))
for label, f in [('count', lambda v: f'{len(v)}'),
                 ('forward mean ms', lambda v: f'{statistics.mean(x[0] for x in v) / 1000:.3f}'),
                 ('forward median ms', lambda v: f'{statistics.median(x[0] for x in v) / 1000:.3f}'),
                 ('forward min ms', lambda v: f'{min(x[0] for x in v) / 1000:.3f}'),
                 ('Save K sum per forward, mean us', lambda v: f'{statistics.mean(x[1] for x in v):.1f}')]:
    print(f'| {label} | ' + ' | '.join(f(dec[a]) if a in dec else 'none' for a in arms) + ' |')
