"""Merge the tighten workflow's output into polished.json, after checking that no number changed."""
import json, re, sys, collections
D = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/outliers'
raw = open(sys.argv[1]).read()
m = re.search(r'\{', raw); obj, _ = json.JSONDecoder().raw_decode(raw[m.start():])
if 'result' in obj and 'tightened' not in obj: obj = obj['result']
T = {t['id']: t for t in obj['tightened']}
P = json.load(open(D + '/polished.json'))
NUM = re.compile(r'\d[\d,]*\.?\d*')
def nums(p):
    txt = ' '.join([p['one_line'], p['open']] + p['looked_wrong'] + p['why_wrong'] + p['showed'] + [t['name'] + ' ' + t['run'] + ' ' + t['measures'] for t in p['tests']])
    return collections.Counter(NUM.findall(txt))
merged = 0; skipped = []; stats = collections.Counter()
for p in P['polished']:
    t = T.get(p['id'])
    if not t: skipped.append((p['id'], 'no tightened entry')); continue
    a, b = nums(p), nums(t)
    lost = a - b; added = b - a
    if lost or added:
        skipped.append((p['id'], f'numbers lost {dict(lost)} added {dict(added)}')); continue
    for f in ('one_line', 'looked_wrong', 'why_wrong', 'showed', 'open', 'tests'): p[f] = t[f]
    merged += 1
    for f in ('looked_wrong', 'why_wrong', 'showed'):
        for bl in p[f]:
            stats['bullets'] += 1
            if ';' in bl: stats['semicolon'] += 1
            if len(bl.split()) > 45: stats['over45'] += 1
json.dump(P, open(D + '/polished.json', 'w'), indent=1)
print('merged', merged, 'skipped', len(skipped), dict(stats))
for s in skipped: print(' -', s[0], s[1][:300])
