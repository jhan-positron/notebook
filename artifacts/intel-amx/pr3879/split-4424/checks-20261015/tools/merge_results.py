#!/usr/bin/env python3
"""Merge run 1 (comment findings only; its named-bool findings used the old rule) with run 2 (the two missing units'
comment findings, and every named-bool finding under the 2026-10-15 rule) into one result for build_comments.py."""
import json, sys
r1, r2, out = sys.argv[1:4]
R1 = json.load(open(r1)); R2 = json.load(open(r2))
units = {}
for u in R1['units']:
    u = dict(u); u['judged'] = [j for j in u['judged'] if j['f']['checker'] == 'B']
    units[(u['pr'], u['path'])] = u
for u in R2['units']:
    key = (u['pr'], u['path'])
    if key in units:
        units[key]['judged'] = [j for j in units[key]['judged'] if j['f']['checker'] == 'B'] + u['judged']
        units[key]['notes'] = units[key].get('notes', []) + u.get('notes', [])
    else:
        units[key] = u
merged = {'units': list(units.values()), 'dropped': R1.get('dropped', 0) + R2.get('dropped', 0)}
json.dump(merged, open(out, 'w'))
import collections
c = collections.Counter((u['pr'], j['f']['checker']) for u in merged['units'] for j in u['judged'])
print('merged judged counts:', sorted(c.items()))
