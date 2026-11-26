#!/usr/bin/env python3
# Round 2, claims lens: check the firmware settings claims of Table 5 against the two questions.json lists.
import json, collections
R='/home/jhan/workspace/titan/cache-perf/crb/results'
def load(p):
    d=json.load(open(p))
    return d
a=load(R+'/uefisettings-20261117/questions.json'); b=load(R+'/fwtest-20261117/revert/questions.json'); c=load(R+'/fwtest-20261117/x1/post/questions.json')
print(type(a), (list(a.keys())[:5] if isinstance(a,dict) else len(a)))
def entries(d):
    if isinstance(d,dict):
        for k in d:
            if isinstance(d[k],list): return d[k]
    return d
ea,eb,ec=entries(a),entries(b),entries(c)
print(len(ea),len(eb),len(ec)); print(json.dumps(ea[0])[:600])
def key(e): return json.dumps(e,sort_keys=True)
print('multiset equal a,b:', collections.Counter(map(key,ea))==collections.Counter(map(key,eb)), 'same order:', ea==eb)
print('multiset equal a,c:', collections.Counter(map(key,ea))==collections.Counter(map(key,ec)))
def ans(e):
    q=e.get('question',e); return q.get('answer')
for nm,E in (('8000 boot list',ea),('after revert',eb)):
    cnt=collections.Counter()
    for e in E:
        s=json.dumps(ans(e))
        if 'ValueUnavailable' in s: cnt['ValueUnavailable']+=1
        elif 'VStoreError' in s: cnt['VStoreError']+=1
        else: cnt['readable']+=1
    print(nm,dict(cnt))
    whole=collections.Counter()
    for e in E:
        s=json.dumps(e)
        whole['VU' if 'ValueUnavailable' in s else ('VS' if 'VStoreError' in s else 'ok')]+=1
    print('  by whole entry',dict(whole))
    for e in E:
        q=e.get('question',e)
        if q.get('name') in ('TXREQ Max','TXREQ Min','DIMM Frequency'): print('  ',q.get('name'),'=',q.get('answer'))
vs=[e for e in ea if 'VStoreError' in json.dumps(e)]
for e in vs: print(json.dumps(e)[:400])
