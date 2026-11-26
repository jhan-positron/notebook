#!/usr/bin/env python3
"""check-figdata: compare fig.js with the data. Read-only on inputs."""
import json, csv, re, math, collections
B='/home/jhan/workspace/titan/cache-perf/crb/'
R=B+'results/sudo-20261102T054936Z/'
W=B+'tmp/agent-scratch/proxy-examples-2026-11-12/'
js=open(W+'worker/fig.js').read()
M10=json.loads(re.search(r'M10 = (\{.*?\})', js).group(1))
print('M10 entries', len(M10), 'distinct values', len(set(M10.values())))
pf=json.load(open(W+'proxyfit/proxy-positions.json'))
# (1a) against proxy-positions.json
bad=0
for r in pf['per_xp']:
    if r['reader_mesh']==0 and r['kind']=='remote':
        k='%d,%d'%tuple(r['home_xp']); v='%d,%d'%tuple(r['best'])
        if M10.get(k)!=v or r['ambiguous']: bad+=1; print('MISMATCH/AMB',k,M10.get(k),v,r['ambiguous'])
n=sum(1 for r in pf['per_xp'] if r['reader_mesh']==0 and r['kind']=='remote')
print('(1a) per_xp reader 0 remote rows',n,'mismatch',bad)
# (1b) independent recompute
pos={int(k):v for k,v in json.load(open(R+'core-positions.json'))['pos'].items()}
nodes=list(csv.DictReader(open(R+'full/nodes.csv')))
xp={(int(r['mesh']),r['node_id_hex']):(int(r['x']),int(r['y'])) for r in nodes}
slicexp=sorted({(int(r['x']),int(r['y'])) for r in nodes if r['mesh']=='0'})
allxp=[(x,y) for x in range(1,8) for y in range(1,6)]
print('crosspoints without slice m0', [p for p in allxp if p not in slicexp], 'm1', [p for p in allxp if p not in {(int(r['x']),int(r['y'])) for r in nodes if r['mesh']=='1'}])
lat=collections.defaultdict(dict)  # (mesh,node) -> core -> ns
for r in csv.DictReader(open(R+'full/latency.csv')):
    if r['mesh']=='-1': continue
    lat[(int(r['mesh']),r['node_id_hex'])][int(r['core'])]=float(r['ns_median'])
def fit(series, cores, cands):
    res=[]
    for c in cands:
        xs=[abs(pos[k]['x']-c[0])+abs(pos[k]['y']-c[1]) for k in cores]; ys=[series[k] for k in cores]
        n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
        sxx=sum((x-mx)**2 for x in xs); sxy=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
        if sxx==0: continue
        b=sxy/sxx; a=my-b*mx
        if b<=0: continue
        rms=math.sqrt(sum((a+b*x-y)**2 for x,y in zip(xs,ys))/n)
        res.append((rms,c,a,b))
    res.sort(); return res
def table(reader, cands):
    cores=[k for k in pos if pos[k]['mesh']==reader]
    home=1-reader; out={}
    hx=collections.defaultdict(list)
    for (m,nid),p in xp.items():
        if m==home: hx[p].append(nid)
    for p,nids in sorted(hx.items()):
        ser={k:min(lat[(home,n)][k] for n in nids) for k in cores}
        f=fit(ser,cores,cands)
        ties=[c for rms,c,a,b in f if rms-f[0][0]<0.3]
        # second method without the line fit: the candidate whose distance ranks the latency best (Spearman)
        out[p]=(f[0][1],ties,f[0][0],f[1][0])
    return out,len(cores)
t0,n0=table(0,slicexp)
bad=0
for p,(best,ties,rms,rms2) in t0.items():
    k='%d,%d'%p; v='%d,%d'%best
    if M10.get(k)!=v or len(ties)>1: bad+=1; print('RECOMPUTE MISMATCH',k,M10.get(k),v,ties)
print('(1b) recompute, slice crosspoints as candidates: reader cores',n0,'homes',len(t0),'mismatch or tie',bad,'min gap to runner-up %.3f'%min(r2-r for _,_,r,r2 in t0.values()))
t0b,_=table(0,allxp)
print('(1b) recompute, all 35 crosspoints as candidates: mismatch', sum(1 for p,(b,t,_,_) in t0b.items() if M10['%d,%d'%p]!='%d,%d'%b), [ (p,b) for p,(b,t,_,_) in t0b.items() if M10['%d,%d'%p]!='%d,%d'%b])
# per-node (dev 0 and dev 1 apart)
cores0=[k for k in pos if pos[k]['mesh']==0]; bad=0
for (m,nid),p in sorted(xp.items()):
    if m!=1: continue
    f=fit(lat[(1,nid)],cores0,slicexp)
    if '%d,%d'%f[0][1]!=M10['%d,%d'%p]: bad+=1; print('per-node mismatch',nid,p,f[0][1])
print('(1b) per-node fits (64 nodes of mesh 1) that disagree with M10:',bad)
# method 3, no fit: crosspoint of the cores with the lowest latency (mean of cores per crosspoint)
bad=0
for p in sorted(t0):
    nids=[n for (m,n),q in xp.items() if m==1 and q==p]
    by=collections.defaultdict(list)
    for k in cores0: by[(pos[k]['x'],pos[k]['y'])].append(min(lat[(1,n)][k] for n in nids))
    best=min(by,key=lambda c:sum(by[c])/len(by[c]))
    if '%d,%d'%best!=M10['%d,%d'%p]: bad+=1; print('  lowest-latency core crosspoint differs: home',p,'M10',M10['%d,%d'%p],'lowest at',best,'(no core at the M10 crosspoint)' if tuple(map(int,M10['%d,%d'%p].split(','))) not in by else '')
print('(1b) method without fit: disagreements',bad)
# reverse direction vs M01
M01={v:k for k,v in M10.items()}
t1,n1=table(1,slicexp)
same=intie=0
for p,(best,ties,_,_) in t1.items():
    want=tuple(map(int,M01['%d,%d'%p].split(',')))
    if best==want and len(ties)==1: same+=1
    elif want in ties: intie+=1
    else: print('REVERSE CONTRADICTS',p,want,best,ties)
print('reverse (reader mesh 1, %d cores): unique and equal to M01 %d, M01 in tie set %d'%(n1,same,intie))
print('panel 4: home (2,5) mesh 0, reader mesh 1 ->',t1[(2,5)][:2], 'M01[2,5]=',M01['2,5'])
# (2) panels
print('\n(2) panels')
for c in (0,64): print(' CPU',c,{k:pos[c][k] for k in('mesh','x','y','inferred')})
homes={}
want={0:'A',1:'B',3*32768:'C'}
for r in csv.DictReader(open(R+'full/homes.csv')):
    if int(r['line']) in want: homes[want[int(r['line'])]]=(int(r['mesh']),r['node_id_hex'])
ch=list(csv.DictReader(open(R+'full/chunks.csv')))
print(' chunk0',ch[0]['virt_hex'],ch[0]['pfn_hex'],' chunk3',ch[3]['virt_hex'],ch[3]['pfn_hex'])
nd={(int(r['mesh']),r['node_id_hex']):r for r in nodes}
for L,(m,nid) in sorted(homes.items()):
    r=nd[(m,nid)]; print(' line',L,'mesh',m,nid,'xp',(r['x'],r['y']),'dev',r['dev'])
def L(core,m,nid): return lat[(m,nid)][core]
def other(m,nid):
    p=xp[(m,nid)]; return [n for (mm,n),q in xp.items() if mm==m and q==p and n!=nid][0]
for title,core,ln in (('1',0,'A'),('2',0,'B'),('3',0,'C'),('4',64,'A')):
    m,nid=homes[ln]; o=other(m,nid)
    print(' panel',title,'CPU',core,'line',ln,'node',nid,'dev',nd[(m,nid)]['dev'],'ns_median %.2f'%L(core,m,nid),'| other node of the crosspoint',o,'%.2f'%L(core,m,o))
def hops(c,p): return abs(pos[c]['x']-p[0])+abs(pos[c]['y']-p[1])
print(' hops CPU0->(2,5)',hops(0,(2,5)),' CPU0->(1,3)',hops(0,(1,3)),' CPU64->(5,2)',hops(64,(5,2)))
# local slice latency at the proxy crosspoint, for reference
for core,m,p in ((0,0,(2,5)),(0,0,(1,3)),(64,1,(5,2))):
    print(' local slices at',p,'mesh',m,'from CPU',core,[(n,lat[(mm,n)][core]) for (mm,n),q in sorted(xp.items()) if mm==m and q==p])
# is (1,3) the proxy closest to CPU 0 among all? and other cores at the same crosspoint as CPU 0 / 64
print(' cores at crosspoint of CPU0:',[k for k in pos if (pos[k]['mesh'],pos[k]['x'],pos[k]['y'])==(0,1,2)],' of CPU64:',[k for k in pos if (pos[k]['mesh'],pos[k]['x'],pos[k]['y'])==(pos[64]['mesh'],pos[64]['x'],pos[64]['y'])])
# (3) drawing logic for proxymap
print('\n(3) proxymap')
print(' mesh 0 cells undefined (drawn "no slice"):',[ '%d,%d'%p for p in allxp if '%d,%d'%p not in M01],' mesh 1:',[ '%d,%d'%p for p in allxp if '%d,%d'%p not in M10])
print(' M01[2,5]=',M01['2,5'],' M10[5,2]=',M10['5,2'])
print(' text colour white when col>4; shade lightness per column:',[(c,round(93-(c-1)*8.5,1)) for c in range(1,8)])
