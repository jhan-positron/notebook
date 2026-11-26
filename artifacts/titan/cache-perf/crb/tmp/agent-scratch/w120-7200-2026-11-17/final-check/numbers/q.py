import json, collections, sys
R = '/home/jhan/workspace/titan/cache-perf/crb/results'
a = json.load(open(R + '/uefisettings-20261117/questions.json'))
b = json.load(open(R + '/fwtest-20261117/revert/questions.json'))
def flat(x):
    # find list of question dicts
    out = []
    def walk(o):
        if isinstance(o, dict):
            if 'name' in o and 'answer' in o:
                out.append(o)
            else:
                for v in o.values():
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(x)
    return out
print(type(a), (list(a.keys())[:5] if isinstance(a, dict) else len(a)))
fa, fb = flat(a), flat(b)
print('entries', len(fa), len(fb))
print('keys of one', fa[0].keys() if fa else None)
def key(q):
    return json.dumps(q, sort_keys=True)
ca = collections.Counter(key(q) for q in fa); cb = collections.Counter(key(q) for q in fb)
print('multiset equal:', ca == cb, ' same order:', [key(q) for q in fa] == [key(q) for q in fb])
ans = collections.Counter()
for q in fa:
    s = json.dumps(q['answer'])
    if 'Unavailable' in s: ans['ValueUnavailable'] += 1
    elif 'VStoreError' in s or 'Error' in s: ans[s[:60]] += 1
    else: ans['readable'] += 1
print(ans)
ansb = collections.Counter()
for q in fb:
    s = json.dumps(q['answer'])
    if 'Unavailable' in s: ansb['ValueUnavailable'] += 1
    elif 'VStoreError' in s or 'Error' in s: ansb[s[:60]] += 1
    else: ansb['readable'] += 1
print(ansb)
for q in fa:
    if q.get('name') in ('DIMM Frequency', 'TXREQ Min', 'TXREQ Max'):
        print('8000 boot list:', q['name'], q['answer'])
for q in fb:
    if q.get('name') in ('DIMM Frequency', 'TXREQ Min', 'TXREQ Max'):
        print('revert list:', q['name'], q['answer'])
