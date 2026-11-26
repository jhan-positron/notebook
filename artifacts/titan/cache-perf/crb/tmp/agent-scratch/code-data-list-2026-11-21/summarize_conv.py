#!/usr/bin/env python3
"""Summarize the output of a check-until-clean workflow.

Usage: summarize_conv.py OUTPUT_JSON [--unresolved]
"""
import json, sys
top = json.load(open(sys.argv[1]))
res = top['result'] if 'result' in top else top
if isinstance(res, str):
    res = json.loads(res)
show_unres = '--unresolved' in sys.argv
nclean = 0
for t in res['targets']:
    line = []
    for r in t['rounds']:
        rr = r['result']
        if rr is None:
            line.append('r%d:NONE' % r['round'])
            continue
        kinds = {}
        for d in rr.get('defects', []):
            kinds[d['kind']] = kinds.get(d['kind'], 0) + 1
        line.append('r%d:%s%s' % (r['round'], ','.join('%s=%d' % kv for kv in sorted(kinds.items())) or 'none',
                                  '' if rr.get('checks_passed') else ' CHECKS-FAILED'))
    nclean += bool(t['clean'])
    print('%-22s %-5s clean=%-5s %s' % (t['name'], t['group'], t['clean'], ' | '.join(line)))
    if show_unres:
        last = t['rounds'][-1]['result'] if t['rounds'] else None
        for u in (last or {}).get('unresolved', []):
            print('     UNRESOLVED: ' + u)
print('targets %d, clean %d' % (len(res['targets']), nclean))
