import json
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
a=json.load(open(S+'/bak-before-vfix-r3/facts.json')); b=json.load(open(S+'/facts.json'))
print('top keys', list(a.keys()), list(b.keys()))
ia,ib=a['intervals'],b['intervals']
print('len', len(ia), len(ib))
print('lists equal', ia==ib)
nd=0
for i,(x,y) in enumerate(zip(ia,ib)):
    if x!=y:
        nd+=1
        if nd<=10:
            ks=set(x)|set(y)
            print(i,{k:(x.get(k),y.get(k)) for k in ks if x.get(k)!=y.get(k)})
print('records that differ', nd)
print('key sets equal', all(set(x)==set(y) for x,y in zip(ia,ib)))
# verdicts and meta diffs
def walk(p,x,y,out):
    if type(x)!=type(y): out.append((p,'type')); return
    if isinstance(x,dict):
        for k in sorted(set(x)|set(y)):
            if k not in x: out.append((p+'/'+k,'ADDED'))
            elif k not in y: out.append((p+'/'+k,'REMOVED'))
            else: walk(p+'/'+k,x[k],y[k],out)
    elif isinstance(x,list):
        if len(x)!=len(y): out.append((p,'len %d->%d'%(len(x),len(y))))
        for i,(u,v) in enumerate(zip(x,y)): walk(p+'[%d]'%i,u,v,out)
    else:
        if x!=y: out.append((p,(x,y)))
out=[]; walk('meta',a['meta'],b['meta'],out); walk('verdicts',a['verdicts'],b['verdicts'],out)
for o in out:
    s=repr(o)
    print(s[:700])
