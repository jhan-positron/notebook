#!/usr/bin/env python3
"""prior_defects.py OUTPUT_FILE... - write prior/<target>.json: the defects that the check rounds of a workflow fixed."""
import json, sys
for path in sys.argv[1:]:
    top = json.load(open(path))
    obj = top.get('result', top)
    for u in obj['units']:
        if u.get('failed'):
            continue
        targets = []
        if u['type'] == 'big':
            for c in u['chunks']:
                targets.append(('%s.c%02d' % (u['id'], c['chunk']), c['verify']))
            targets.append((u['id'] + '.overview', u['overview_verify']))
        else:
            targets.append((u['id'], u['verify']))
        for name, rounds in targets:
            out, last = [], None
            for n, v in enumerate(rounds or [], 1):
                if not v:
                    continue
                last = dict(round=n, wrong=sum(d['kind'] == 'wrong' for d in v['defects']), missing=sum(d['kind'] == 'missing' for d in v['defects']))
                for d in v['defects']:
                    out.append(dict(round=n, **d))
            json.dump(dict(target=name, group=obj['group'], defects=out), open('prior/%s.json' % name, 'w'), indent=1)
            print(obj['group'], name, 'rounds', len(rounds or []), 'last', last, 'dry' if last and last['wrong'] == 0 and last['missing'] <= 1 else 'NOT DRY')
