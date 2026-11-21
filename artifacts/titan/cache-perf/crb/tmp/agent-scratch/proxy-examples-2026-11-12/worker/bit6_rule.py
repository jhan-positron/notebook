#!/usr/bin/env python3
"""Test the rule: the proxy crosspoint of a line, for a core of the other mesh, is the home
crosspoint of the line whose physical address differs in bit 6 only (lines 2k and 2k+1).
Home crosspoints come from full/homes.csv and full/nodes.csv. Proxy crosspoints come from the
latency fits of the cores of mesh 0 (proxy-positions.json, per_xp rows, reader mesh 0).
usage: bit6_rule.py <results dir> <proxy-positions.json>"""
import csv, json, sys, collections
R, P = sys.argv[1], sys.argv[2]
homes = [(int(r['mesh']), int(r['node_id_hex'], 16)) for r in csv.DictReader(open(R + '/full/homes.csv'))]
xyd = {(int(r['mesh']), int(r['node_id_hex'], 16)): (int(r['x']), int(r['y']), int(r['dev'])) for r in csv.DictReader(open(R + '/full/nodes.csv'))}
m10 = {tuple(r['home_xp']): tuple(r['best']) for r in json.load(open(P))['per_xp'] if r['kind'] == 'remote' and r['reader_mesh'] == 0}
assert len(m10) == 32
pairs = same_mesh = match = same_dev = 0
seen = collections.defaultdict(set)
for k in range(0, len(homes), 2):
    a, b = homes[k], homes[k + 1]
    pairs += 1
    if a[0] == b[0]:
        same_mesh += 1
        continue
    h0, h1 = (a, b) if a[0] == 0 else (b, a)          # h0: the line homed on mesh 0, h1: the line homed on mesh 1
    x0, x1 = xyd[h0], xyd[h1]
    match += m10[x1[:2]] == x0[:2]
    same_dev += x0[2] == x1[2]
    seen[x1[:2]].add(x0[:2])
print('aligned pairs (lines 2k, 2k+1):', pairs)
print('pairs with both homes on one mesh:', same_mesh)
print('pairs where the home crosspoint of the mesh 0 line is the fitted proxy crosspoint of the mesh 1 line:', match)
print('pairs where the two home nodes have the same device number:', same_dev)
print('home crosspoints on mesh 1 seen:', len(seen), '; each with one crosspoint on mesh 0:', all(len(v) == 1 for v in seen.values()))
