import json
from collections import Counter
R="/home/jhan/workspace/titan/cache-perf/crb/results"
def load(p):
    d=json.load(open(p)); return d
b=load(R+"/uefisettings-20261117/questions.json"); x=load(R+"/fwtest-20261117/x1/post/questions.json"); r=load(R+"/fwtest-20261117/revert/questions.json")
print(type(b), list(b.keys())[:5] if isinstance(b,dict) else len(b))
def qs(d):
    q=d
    while isinstance(q,dict) and len(q)==1: q=list(q.values())[0]
    return q
B=qs(b); X=qs(x); Rv=qs(r)
print(len(B),len(X),len(Rv)); print(json.dumps(B[0])[:600])
def key(e):
    q=e.get("question",e)
    return json.dumps(q,sort_keys=True)
def ans(e):
    q=e.get("question",e); return q.get("answer")
for nm,L in (("base",B),("x1",X),("revert",Rv)):
    c=Counter(type(ans(e)).__name__+":"+("ValueUnavailable" if "navailable" in json.dumps(ans(e)) else "ok") for e in L)
    print(nm,len(L),c)
    for n in ("TXREQ Max","TXREQ Min","DIMM Frequency"):
        print("   ",n,[ans(e) for e in L if e.get("question",e).get("name")==n])
print("keys of an entry:",list(B[0].keys()), "question keys:", list(B[0].get("question",B[0]).keys()))
print("base==revert as multiset of whole entries:",Counter(json.dumps(e,sort_keys=True) for e in B)==Counter(json.dumps(e,sort_keys=True) for e in Rv))
print("base==revert same order:",[json.dumps(e,sort_keys=True) for e in B]==[json.dumps(e,sort_keys=True) for e in Rv])
cb=Counter(json.dumps(e,sort_keys=True) for e in B); cx=Counter(json.dumps(e,sort_keys=True) for e in X)
d1=cb-cx; d2=cx-cb
print("base - x1:",len(d1),[json.loads(k).get("question",json.loads(k)).get("name")+"="+str(json.loads(k).get("question",json.loads(k)).get("answer")) for k in d1])
print("x1 - base:",len(d2),[json.loads(k).get("question",json.loads(k)).get("name")+"="+str(json.loads(k).get("question",json.loads(k)).get("answer")) for k in d2])
# how answers that are unavailable look
print([json.dumps(ans(e)) for e in B[:5]])
