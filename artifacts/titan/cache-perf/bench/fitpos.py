#!/usr/bin/env python3
"""fitpos.py - infer each core's crosspoint from homelat's latency matrix.
For each core and each candidate core-port crosspoint (every crosspoint with an RN-F port in the
map: rows 1 to 5, columns 1 to 7, including the three without slices), fit
  latency(slice) = intercept + slope * manhattan(candidate, slice)
over the 64 slices of each mesh (the smaller of the two slice medians per crosspoint), slope > 0,
and keep the candidate and mesh with the smallest root-mean-square error. The result is an
inferred position. Usage: fitpos.py <results dir with full/latency.csv> -> core-positions.json"""
import csv, json, sys, statistics as st, collections
R = sys.argv[1]
CANDIDATES = [(x, y) for y in range(1, 6) for x in range(1, 8)]
rows = [r for r in csv.DictReader(open(f'{R}/full/latency.csv')) if r['node_id_hex'] != 'mixed']
L = collections.defaultdict(dict)
for r in rows:
    L[int(r['core'])][(int(r['mesh']), int(r['x']), int(r['y']), int(r['dev']))] = float(r['ns_median'])
def fit(pts):
    n = len(pts); mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts); sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    b = sxy / sxx; a = my - b * mx
    return a, b, (sum((v - (a + b * d)) ** 2 for d, v in pts) / n) ** 0.5
pos = {}
for core, d in L.items():
    best = None
    for m in (0, 1):
        v = {}
        for (mm, x, y, dv), val in d.items():
            if mm == m: v[(x, y)] = min(v.get((x, y), 99), val)
        for (cx, cy) in CANDIDATES:
            pts = [(abs(x - cx) + abs(y - cy), val) for (x, y), val in v.items()]
            a, b, res = fit(pts)
            if b <= 0: continue
            if best is None or res < best[0]: best = (res, m, cx, cy, a, b, min(v.values()))
    res, m, cx, cy, a, b, near = best
    pos[core] = dict(mesh=m, x=cx, y=cy, nearest=near, per_hop=b, intercept=a, resid=res, inferred=True)
far = [max(val for k, val in d.items() if k[0] == pos[c]['mesh']) for c, d in L.items()]
json.dump(dict(method=__doc__, candidates=CANDIDATES, pos={str(c): p for c, p in pos.items()}, far=far), open(f'{R}/core-positions.json', 'w'), indent=1)
print('cores', len(pos), 'mesh disagrees with 0-63 split:', [c for c, p in pos.items() if (c < 64) != (p['mesh'] == 0)])
print('pairs on one crosspoint:', sum(1 for c in range(0, 120, 2) if c + 1 in pos and (pos[c]['mesh'], pos[c]['x'], pos[c]['y']) == (pos[c + 1]['mesh'], pos[c + 1]['x'], pos[c + 1]['y'])), 'of 60')
cnt = collections.Counter((p['mesh'], p['x'], p['y']) for p in pos.values())
print('crosspoints used', len(cnt), 'max cores per crosspoint', max(cnt.values()))
for c in (34, 35, 98, 99): print(' core', c, (pos[c]['x'], pos[c]['y']), 'resid %.3f' % pos[c]['resid'])
print('per hop ns min/med/max: %.2f %.2f %.2f; resid med/max: %.2f %.2f' % (min(p['per_hop'] for p in pos.values()), st.median(p['per_hop'] for p in pos.values()), max(p['per_hop'] for p in pos.values()), st.median(p['resid'] for p in pos.values()), max(p['resid'] for p in pos.values())))
