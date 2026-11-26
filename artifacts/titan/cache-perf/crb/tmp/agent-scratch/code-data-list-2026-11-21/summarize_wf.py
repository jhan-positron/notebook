#!/usr/bin/env python3
"""summarize_wf.py OUTPUT_FILE - print a summary of one workflow result (units, defect counts, open points)."""
import json, re, sys
top = json.load(open(sys.argv[1]))
for l in top.get('logs', []):
    print('log:', l)
obj = top.get('result') or top.get('output') or top
if isinstance(obj, str):
    obj = json.loads(obj)
if 'units' not in obj:
    sys.exit('keys: %s' % list(top.keys()))
def rounds(vs, label):
    for n, v in enumerate(vs or [], 1):
        if not v:
            print('   %s check %d: NO RESULT' % (label, n)); continue
        k = {}
        for d in v['defects']:
            k[d['kind']] = k.get(d['kind'], 0) + 1
        print('   %s check %d: %d items, defects %s, verdict %s, checks_passed %s' % (label, n, v['items_checked'], k or '{}', v['verdict'], v['checks_passed']))
        for u in v.get('unresolved') or []:
            print('      UNRESOLVED: ' + u[:700])
def ann(a, label):
    if not a:
        print('   %s: NO RESULT' % label); return
    print('   %s: checks_passed %s, %d files' % (label, a['checks_passed'], len(a['files_written'])))
    for q in a.get('open_questions') or []:
        print('      OPEN: ' + q[:700])
print('group', obj['group'])
for u in obj['units']:
    print('==', u['id'], u.get('type'), 'FAILED' if u.get('failed') else '')
    if u.get('failed'):
        continue
    if u['type'] == 'big':
        ann(u['overview'], 'overview')
        for c in u['chunks']:
            if not c:
                print('   chunk: NO RESULT'); continue
            ann(c['annotate'], 'chunk %d' % c['chunk']); rounds(c['verify'], 'chunk %d' % c['chunk'])
        rounds(u['overview_verify'], 'overview')
    else:
        ann(u['annotate'], 'writer'); rounds(u['verify'], 'unit')
