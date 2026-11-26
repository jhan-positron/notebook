#!/usr/bin/env python3
"""prior_append.py CONV_OUTPUT... - append the defects of the check-until-clean rounds to prior/<target>.json."""
import json, sys
for path in sys.argv[1:]:
    top = json.load(open(path))
    res = top.get('result', top)
    for t in res['targets']:
        p = 'prior/%s.json' % t['name']
        cur = json.load(open(p))
        have = {d['round'] for d in cur['defects']}
        n = 0
        for r in t['rounds']:
            if r['result'] is None or r['round'] in have:
                continue
            for d in r['result']['defects']:
                cur['defects'].append(dict(round=r['round'], **d))
                n += 1
        json.dump(cur, open(p, 'w'), indent=1)
        print(t['name'], 'added', n, 'total', len(cur['defects']))
