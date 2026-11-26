#!/usr/bin/env python3
"""summarize_fs.py OUTPUT_JSON [--defects] [--unresolved] - summary of a false-statement-rounds workflow."""
import json, sys
res = json.load(open(sys.argv[1]))['result']
ns = 0
for t in res['targets']:
    if t.get('failed'):
        print('%-24s FAILED' % t['name']); continue
    rs = ['r%d %s:%s' % (r['round'], r['lens'][:3], 'NONE' if r['result'] is None else sum(d['kind'] == 'wrong' for d in r['result']['defects'])) for r in t['rounds']]
    ns += bool(t['settled'])
    print('%-24s settled=%-5s streak %d  %s' % (t['name'], t['settled'], t['streak'], '  '.join(rs)))
    for r in t['rounds']:
        if r['result'] is None: continue
        if '--defects' in sys.argv:
            for d in r['result']['defects']:
                print('    r%d %s [%s] %s | %s' % (r['round'], d['kind'], d['file'].split('/')[-1], d['lines'], d['evidence'][:260]))
                print('        BEFORE: %s' % d['before'][:260]); print('        AFTER : %s' % d['after'][:260])
        if '--unresolved' in sys.argv:
            for u in r['result'].get('unresolved', []):
                print('    r%d UNRESOLVED: %s' % (r['round'], u[:600]))
print('targets %d, settled %d' % (len(res['targets']), ns))
