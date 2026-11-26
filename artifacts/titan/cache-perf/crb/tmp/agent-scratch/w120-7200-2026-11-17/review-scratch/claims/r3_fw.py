#!/usr/bin/env python3
# Round 3, lens claims: compare the two firmware settings lists named by the page (Ref57, Ref58).
import json, collections
R='/home/jhan/workspace/titan/cache-perf/crb/results'
a=json.load(open(R+'/uefisettings-20261117/questions.json'))
b=json.load(open(R+'/fwtest-20261117/revert/questions.json'))
print(type(a), list(a.keys())[:5] if isinstance(a,dict) else len(a))
def items(x):
    if isinstance(x,dict):
        for k in x:
            if isinstance(x[k],list): return x[k]
    return x
ia, ib = items(a), items(b)
print(len(ia), len(ib))
print(json.dumps(ia[0])[:600])
def key(e): return json.dumps(e, sort_keys=True)
ca=collections.Counter(key(e) for e in ia); cb=collections.Counter(key(e) for e in ib)
print('equal as multisets:', ca==cb, 'same order:', ia==ib)
def val(e):
    q=e.get('question',e)
    return q.get('answer')
vals=collections.Counter()
for e in ia:
    s=json.dumps(e)
    if 'ValueUnavailable' in s: vals['ValueUnavailable']+=1
    elif 'VStoreError' in s: vals['VStoreError']+=1
    else: vals['readable']+=1
print(vals)
for e in ia:
    s=json.dumps(e)
    if 'TXREQ' in s or 'DIMM Frequency' in s: print('8000 boot:', s[:400])
for e in ib:
    s=json.dumps(e)
    if 'TXREQ' in s or 'DIMM Frequency' in s: print('after revert:', s[:400])
