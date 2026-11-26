import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
print("top keys before:", list(a.keys())); print("top keys after:", list(b.keys()))
ia=a["intervals"]; ib=b["intervals"]
print("n before", len(ia), "n after", len(ib))
ka=set(); kb=set()
for r in ia: ka|=set(r.keys())
for r in ib: kb|=set(r.keys())
print("fields removed:", sorted(ka-kb)); print("fields added:", sorted(kb-ka))
nd=0; kbd=0
from collections import Counter
c=Counter()
for i,(x,y) in enumerate(zip(ia,ib)):
    if set(x.keys())!=set(y.keys()):
        print("key set differs at", i, sorted(set(x)^set(y)))
    for k in sorted(set(x)|set(y)):
        if x.get(k,"<absent>")!=y.get(k,"<absent>"):
            c[k]+=1
            if k=="kernel_before":
                kbd+=1
                print("kernel_before diff:", i, x.get("proc_key"), x.get("file"), x.get("line"), repr(x.get(k)), "->", repr(y.get(k)))
            else:
                nd+=1
                if nd<40: print("DIFF", i, k, repr(x.get(k))[:200], "->", repr(y.get(k))[:200])
print("diff count by field:", dict(c))
# other top-level diffs
def walk(x,y,path,out):
    if type(x)!=type(y):
        out.append((path,"type",repr(x)[:120],repr(y)[:120])); return
    if isinstance(x,dict):
        for k in sorted(set(x)|set(y)):
            if k not in x: out.append((path+"/"+k,"added",None,repr(y[k])[:300]))
            elif k not in y: out.append((path+"/"+k,"removed",repr(x[k])[:300],None))
            else: walk(x[k],y[k],path+"/"+k,out)
    elif isinstance(x,list):
        if len(x)!=len(y): out.append((path,"len",len(x),len(y)))
        for i,(p,q) in enumerate(zip(x,y)): walk(p,q,path+"/%d"%i,out)
    else:
        if x!=y: out.append((path,"changed",repr(x)[:300],repr(y)[:300]))
out=[]
for k in sorted(set(a)|set(b)):
    if k=="intervals": continue
    if k not in a: out.append(("/"+k,"added",None,None)); continue
    if k not in b: out.append(("/"+k,"removed",None,None)); continue
    walk(a[k],b[k],"/"+k,out)
print("non-interval diffs:", len(out))
for o in out: print(o[0], o[1])
