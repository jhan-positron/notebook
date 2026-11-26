import re,sys,csv,collections,json,statistics as st
def parse(path):
    lines=open(path).read().split('\n'); out={}; y=None; start=None
    for i,l in enumerate(lines):
        m=re.match(r'^(\d)\s+\|(.*XP #.*)\|\s*$',l)
        if m: y=int(m.group(1)); continue
        m=re.match(r'^  (\d)  \|(.*)\|\s*$',l)
        if m and y is not None:
            port=int(m.group(1)); cells=[c.strip() for c in m.group(2).split('|')]
            d0=[c.strip() for c in lines[i+1].split('|')[1:-1]]; d1=[c.strip() for c in lines[i+2].split('|')[1:-1]]
            for x,c in enumerate(cells):
                if c: out[(x,y,port)]=(c,d0[x],d1[x],i+1)
    return out
import os
for f in ('results/map','results/map_1'):
    p=parse(f)
    rn=sorted((x,y) for (x,y,pt),v in p.items() if v[0].startswith('RN-F'))
    print(f,'ports',len(p),'RN-F ports',len(rn),'x',sorted(set(x for x,y in rn)),'y',sorted(set(y for x,y in rn)),'port idx',set(pt for (x,y,pt),v in p.items() if v[0].startswith('RN-F')),'types',collections.Counter(v[0] for v in p.values() if v[0].startswith('RN-F')))
    print('  RN-F dev ids nonblank:',[(k,v) for k,v in p.items() if v[0].startswith('RN-F') and (v[1] or v[2])][:5])
    hs=[(x,y) for (x,y,pt),v in p.items() if v[0]=='HN-S']; hn=[(x,y) for (x,y,pt),v in p.items() if v[0]=='HN-S' and not(v[1] or v[2])]
    print('  HN-S ports',len(hs),'without node',sorted(hn),'HN-S nodes',sum(bool(v[1])+bool(v[2]) for v in p.values() if v[0]=='HN-S'))
a=open('results/map').read(); b=open('results/map_1').read(); print('map==map_1 bytes',a==b)
if a!=b:
    import difflib
    d=[l for l in difflib.unified_diff(a.split('\n'),b.split('\n'),lineterm='',n=0)]; print(len(d)); print('\n'.join(d[:40]))
# margins
R='results/sudo-20261102T054936Z'
rows=[r for r in csv.DictReader(open(f'{R}/full/latency.csv')) if r['node_id_hex']!='mixed']
L=collections.defaultdict(dict)
for r in rows: L[int(r['core'])][(int(r['mesh']),int(r['x']),int(r['y']),int(r['dev']))]=float(r['ns_median'])
def fit(pts):
    n=len(pts); mx=sum(p[0] for p in pts)/n; my=sum(p[1] for p in pts)/n
    sxx=sum((p[0]-mx)**2 for p in pts); sxy=sum((p[0]-mx)*(p[1]-my) for p in pts); b=sxy/sxx; a=my-b*mx
    return a,b,(sum((v-(a+b*d))**2 for d,v in pts)/n)**.5
marg=[];om=[]
for core,d in sorted(L.items()):
    c=[]
    for m in (0,1):
        v={}
        for (mm,x,y,dv),val in d.items():
            if mm==m: v[(x,y)]=min(v.get((x,y),99),val)
        for cx in range(1,8):
            for cy in range(1,6):
                a_,b_,res=fit([(abs(x-cx)+abs(y-cy),val) for (x,y),val in v.items()])
                if b_>0: c.append((res,m,cx,cy))
    c.sort(); marg.append((c[1][0]/c[0][0],core,c[0],c[1]))
    best_other=min(x for x in c if x[1]!=c[0][1]); om.append(best_other[0]/c[0][0])
marg.sort()
print('cores',len(L),'slices per core',collections.Counter(len(d) for d in L.values()))
print('second/best rms ratio: min %.2f med %.2f max %.2f'%(marg[0][0],st.median(m[0] for m in marg),marg[-1][0]))
print('5 weakest',[(m[1],round(m[0],2),m[2][1:],round(m[2][0],3),m[3][1:],round(m[3][0],3)) for m in marg[:5]])
print('other-mesh best rms / best rms min %.2f'%min(om))
p=json.load(open(f'{R}/core-positions.json'))['pos']
r=[v['resid'] for v in p.values()]; print('resid med %.3f max %.3f; perhop med %.3f'%(st.median(r),max(r),st.median(v['per_hop'] for v in p.values())))
