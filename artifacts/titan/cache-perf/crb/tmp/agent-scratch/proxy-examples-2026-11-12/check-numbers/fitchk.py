#!/usr/bin/env python3
# Independent recompute of the proxy statements of sec232.html from latency.csv, nodes.csv, core-positions.json.
import csv, json, collections, statistics as st, itertools
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z'
cp=json.load(open(R+'/core-positions.json'))['pos']
pos={int(c):(p['mesh'],p['x'],p['y']) for c,p in cp.items()}
print('cores with a position',len(pos),'cpu range',min(pos),max(pos),'missing below 128:',[c for c in range(128) if c not in pos])
print('CPU 0',pos[0],'CPU 64',pos[64],'mesh by cpu<64:',all((m==0)==(c<64) for c,(m,x,y) in pos.items()))
print('mesh0 column 7 CPUs',sorted(c for c,(m,x,y) in pos.items() if m==0 and x==7),' mesh1 column 7 CPUs',sorted(c for c,(m,x,y) in pos.items() if m==1 and x==7))
print('mesh0 column 6 CPUs',sorted(c for c,(m,x,y) in pos.items() if m==0 and x==6),' mesh1 column 6 CPUs',sorted(c for c,(m,x,y) in pos.items() if m==1 and x==6))
nodes=[(int(r['mesh']),r['node_id_hex'],int(r['x']),int(r['y']),int(r['dev'])) for r in csv.DictReader(open(R+'/full/nodes.csv'))]
XP=sorted({(x,y) for m,n,x,y,d in nodes if m==0}); print('home crosspoints per mesh',len(XP),'grid x',sorted({x for x,y in XP}),'y',sorted({y for x,y in XP}),'missing of 7x5:',sorted(set(itertools.product(range(1,8),range(1,6)))-set(XP)))
lat=collections.defaultdict(dict); rows=0; cores=set(); meta=set()
for r in csv.DictReader(open(R+'/full/latency.csv')):
    cores.add(int(r['core']))
    if r['node_id_hex']=='mixed': continue
    lat[(int(r['mesh']),r['node_id_hex'])][int(r['core'])]=float(r['ns_median']); rows+=1; meta.add((r['lines'],sum(1 for k in r if k.startswith('ns_rep'))))
print('latency rows',rows,'cores',len(cores),min(cores),max(cores),'(lines, reps):',meta)
for lab,c,k in (('CPU0 line A',0,(0,'0x128')),('CPU0 line B',0,(1,'0x290')),('CPU0 line C',0,(1,'0x390')),('CPU64 line A',64,(0,'0x128')),('CPU64 line B',64,(1,'0x290'))):
    print(lab,k,lat[k][c])
rd={m:collections.defaultdict(list) for m in (0,1)}
for c,(m,x,y) in pos.items(): rd[m][(x,y)].append(c)
def fit(pts):
    n=len(pts); mx=sum(p[0] for p in pts)/n; my=sum(p[1] for p in pts)/n
    sxx=sum((p[0]-mx)**2 for p in pts); sxy=sum((p[0]-mx)*(p[1]-my) for p in pts)
    if sxx==0: return None
    b=sxy/sxx; a=my-b*mx
    return (sum((v-(a+b*d))**2 for d,v in pts)/n)**.5,a,b
def best(points):  # points: list of ((x,y), ns)
    out=[]
    for c in XP:
        f=fit([(abs(x-c[0])+abs(y-c[1]),v) for (x,y),v in points])
        if f and f[2]>0: out.append((f[0],c,f[1],f[2]))
    out.sort(); ties=[o[1] for o in out if o[0]-out[0][0]<1e-9]
    return out[0],ties
def summ(tag,res):
    print('%-44s n=%d npts=%s RMS med %.3f worst %.3f | slope med %.3f | intercept med %.3f | tied %d'%(tag,len(res),sorted({r[2] for r in res}),st.median(r[0][0] for r in res),max(r[0][0] for r in res),st.median(r[0][3] for r in res),st.median(r[0][2] for r in res),sum(len(r[1])>1 for r in res)))
maps={}
for A in (0,1):
    for kind in ('local','remote'):
        hm=A if kind=='local' else 1-A
        # variant 1: per node, one point per reader crosspoint (min of its cores)  [proxyfit per_node]
        res=[]
        for m,n,x,y,d in nodes:
            if m!=hm: continue
            pts=[(xp,min(lat[(m,n)][c] for c in cs)) for xp,cs in rd[A].items()]
            b,t=best(pts); res.append((b,t,len(pts),(x,y)))
        summ('reader %d %s per node, 1 pt per reader XP'%(A,kind),res)
        if kind=='local': print('     true XP = unique best:',sum(r[0][1]==r[3] and len(r[1])==1 for r in res),' RMS at the TRUE XP: med %.3f worst %.3f'%(lambda l:(st.median(l),max(l)))([fit([(abs(xp[0]-x)+abs(xp[1]-y),min(lat[(m,n)][c] for c in cs)) for xp,cs in rd[A].items()])[0] for m,n,x,y,d in nodes if m==hm]))
        # variant 2: per node, one point per core
        res=[]
        for m,n,x,y,d in nodes:
            if m!=hm: continue
            pts=[(pos[c][1:],v) for c,v in lat[(m,n)].items() if pos[c][0]==A]
            b,t=best(pts); res.append((b,t,len(pts),(x,y)))
        summ('reader %d %s per node, 1 pt per core'%(A,kind),res)
        # variant 3: per crosspoint (min of 2 devs), one point per reader XP [proxyfit per_xp]
        res=[]
        for xp0 in XP:
            ks=[(m,n) for m,n,x,y,d in nodes if m==hm and (x,y)==xp0]
            pts=[(xp,min(lat[k][c] for k in ks for c in cs)) for xp,cs in rd[A].items()]
            b,t=best(pts); res.append((b,t,len(pts),xp0))
        summ('reader %d %s per XP, 1 pt per reader XP'%(A,kind),res)
        if kind=='remote': maps[A]={r[3]:(r[0][1],r[1]) for r in res}
        # variant 4: per crosspoint, one point per core (min of the 2 devs per core) [refute A]
        res=[]
        for xp0 in XP:
            ks=[(m,n) for m,n,x,y,d in nodes if m==hm and (x,y)==xp0]
            pts=[(pos[c][1:],min(lat[k][c] for k in ks)) for c in pos if pos[c][0]==A]
            b,t=best(pts); res.append((b,t,len(pts),xp0))
        summ('reader %d %s per XP, 1 pt per core'%(A,kind),res)
M0={h:p for h,(p,t) in maps[0].items()}   # home XP on mesh 1 -> proxy XP on mesh 0
print('reader 0: distinct proxies',len(set(M0.values())),'ties',sum(len(t)>1 for p,t in maps[0].values()))
inv={p:h for h,p in M0.items()}           # mesh-0 XP -> partner on mesh 1
un=[h for h,(p,t) in maps[1].items() if len(t)==1]
print('reader 1: unique fits',len(un),'of 32; of those equal to the inverse of reader 0:',sum(maps[1][h][0]==inv[h] for h in un))
tied=[h for h in maps[1] if len(maps[1][h][1])>1]
print('reader 1 tied:',len(tied),'inverse inside tie set:',sum(inv[h] in maps[1][h][1] for h in tied),'tie sets:',sorted((h,sorted(maps[1][h][1])) for h in tied))
print('tie sets all {(6,y),(7,y)}:',all(sorted(maps[1][h][1])[0][0]==6 and sorted(maps[1][h][1])[1][0]==7 and len(maps[1][h][1])==2 for h in tied))
print('example: M0[(5,2)] =',M0[(5,2)],' reader1 home (2,5) ->',maps[1][(2,5)],' M0[(7,2)] =',M0[(7,2)])
# best mirror / rotation / shift rule: (x,y)->(sx*x+ax, sy*y+ay), optionally transposed; all 8 symmetries of the grid plus any offsets
bestr=[]
for tr in (0,1):
  for sx in (1,-1):
    for sy in (1,-1):
      for ax in range(-12,13):
        for ay in range(-12,13):
          k=sum(((sx*(h[1] if tr else h[0])+ax, sy*(h[0] if tr else h[1])+ay)==p) for h,p in M0.items())
          bestr.append((k,tr,sx,ax,sy,ay))
bestr.sort(reverse=True); print('best rules for M0 (matches,transpose,sx,ax,sy,ay):',bestr[:4])
pure={'mirror x (8-x,y)':lambda x,y:(8-x,y),'mirror y (x,6-y)':lambda x,y:(x,6-y),'rot180':lambda x,y:(8-x,6-y),'identity':lambda x,y:(x,y)}
for nme,f in pure.items(): print('  ',nme,sum(f(*h)==p for h,p in M0.items()),'of 32')
# Evidence 1: position-free. latency vector over the 64 cores of mesh 0 of a remote home XP (mesh 1) against the local XP at the fitted proxy
def vec(m,xp0,A,mode):
    ks=[(mm,n) for mm,n,x,y,d in nodes if mm==m and (x,y)==xp0]
    cs=sorted(c for c in pos if pos[c][0]==A)
    return [ (min if mode=='min' else (lambda l:sum(l)/len(l)))([lat[k][c] for k in ks]) for c in cs]
for A in (0,1):
  for mode in ('min','mean'):
    raw=[];mr=[];closest=0;closest_mr=0
    for h in XP:
        r=vec(1-A,h,A,mode)
        def d(p,rm):
            l=vec(A,p,A,mode); off=(sum(r)-sum(l))/len(r) if rm else 0
            return (sum((a-b-off)**2 for a,b in zip(r,l))/len(r))**.5
        target=maps[A][h][1]
        dd=sorted((d(p,False),p) for p in XP); dm=sorted((d(p,True),p) for p in XP)
        closest+=dd[0][1] in target; closest_mr+=dm[0][1] in target
        raw.append(dd[0][0]); mr.append(dm[0][0])
    print('reader %d (%s of the 2 nodes): closest local XP in fit tie set raw %d/32, mean-removed %d/32; RMS diff raw med %.3f max %.3f; mean-removed med %.3f max %.3f; n cores %d'%(A,mode,closest,closest_mr,st.median(raw),max(raw),st.median(mr),max(mr),len(r)))
# per node (not per XP): remote node vs each local node, raw
for A in (0,1):
    cs=sorted(c for c in pos if pos[c][0]==A); mx=[]
    for m,n,x,y,d in nodes:
        if m==A: continue
        best_=min(((sum((lat[(m,n)][c]-lat[(A,n2)][c])**2 for c in cs)/len(cs))**.5,(x2,y2)) for m2,n2,x2,y2,d2 in nodes if m2==A)
        mx.append(best_[0])
    print('reader %d per node raw RMS to closest local node: med %.3f max %.3f'%(A,st.median(mx),max(mx)))
