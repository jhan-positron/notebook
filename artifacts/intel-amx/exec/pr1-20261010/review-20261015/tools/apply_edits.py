#!/usr/bin/env python3
"""Apply whole-line edits (from the workflow result) to the worktree. usage: apply_edits.py result.json items.json worktree [--dry]"""
import json, sys, collections
res, items_p, W = sys.argv[1:4]; dry = '--dry' in sys.argv
R = json.load(open(res)); items = {x['id']: x for x in json.load(open(items_p))['items']}
by = collections.defaultdict(list); problems = []
for r in R['results']:
    it = items[r['id']]
    if not r['applicable']: problems.append((r['id'], 'not applicable: ' + r['note'])); continue
    for k, e in enumerate(r['edits']):
        by[it['path']].append((r['id'], k, e['old_text'].rstrip('\n'), e['new_text'].rstrip('\n'), r['note']))
report = []
for path, edits in by.items():
    lines = open(f'{W}/{path}').read().split('\n')
    spans = []
    for (fid, k, old, new, note) in edits:
        ol = old.split('\n'); n = len(ol)
        hits = [i for i in range(len(lines) - n + 1) if lines[i:i + n] == ol]
        if len(hits) != 1:
            problems.append((fid, f'edit {k}: old_text occurs {len(hits)} times in {path}')); continue
        spans.append((hits[0], hits[0] + n, fid, k, new))
    spans.sort()
    for a, b in zip(spans, spans[1:]):
        if b[0] < a[1]: problems.append((b[2], f'overlaps {a[2]} in {path} (lines {a[0]+1}-{a[1]} vs {b[0]+1}-{b[1]})'))
    if any(p for p in problems if p[1].startswith('overlaps')): continue
    for (s, e, fid, k, new) in sorted(spans, reverse=True):
        nl = new.split('\n') if new != '' else []
        lines[s:e] = nl
        report.append((path, fid, k, s + 1, e - s, len(nl)))
    if not dry: open(f'{W}/{path}', 'w').write('\n'.join(lines))
for p in problems: print('PROBLEM', *p)
print(f'applied {len(report)} edits in {len(by)} files; problems {len(problems)}; dry={dry}')
json.dump(dict(report=report, problems=problems), open(res + '.apply.json', 'w'), indent=1)
