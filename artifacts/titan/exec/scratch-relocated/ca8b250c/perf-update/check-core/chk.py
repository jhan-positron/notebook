import csv, os, re, statistics as st, math
R = '/home/jhan/workspace/titan/cache-perf/asimov/results/'
D = {'E': R+'membench-jibin-010/results/bootE/', 'C': R+'membench-jibin-007/results/bootC/',
     'A': R+'membench-jibin-005/results/bootA/', 'B': R+'membench-jibin-006/results/bootB/',
     'D': R+'membench-jibin-008/results/bootD/', 'R3': R+'membench-jibin-004/results/19700101T000000Z/',
     'R2': R+'membench-jibin-002/results/19700101T000000Z/'}

def lat(boot, name):
    """returns dict: (size, mode) -> row dict list; 'best' rows keyed (size,'best') -> float"""
    out = {}
    hdr = None
    with open(D[boot]+name+'.csv') as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#'): continue
            parts=line.split(',')
            if parts[0]=='mem': hdr=parts; continue
            size=int(parts[1]); mode=parts[2]
            if mode in ('best','cme-best','cme-roundtrip-best'):
                out[(size,mode)] = float(parts[5]); continue
            row = {h: (float(v) if re.match(r'^-?[\d.]+(e-?\d+)?$', v) else v) for h,v in zip(hdr,parts)}
            out.setdefault((size,'rows'),[]).append(row)
    return out

def best(boot,name,size,mode='best'):
    return lat(boot,name)[(size,mode)]
def rows(boot,name,size):
    return lat(boot,name)[(size,'rows')]
def bestrow(boot,name,size,key='ns_per_load'):
    return min(rows(boot,name,size), key=lambda r:r['ns_per_load'])
def pmean(boot,name,size,col):
    return st.mean(r[col] for r in rows(boot,name,size))

def bw(boot,name):
    out={}
    hdr=None
    with open(D[boot]+name+'.csv') as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#'): continue
            parts=line.split(',')
            if parts[0]=='mem': hdr=parts; continue
            k=(parts[1], int(parts[3]))
            if parts[4]=='best':
                out[(k,'best')]=float(parts[7]); continue
            row={h:(float(v) if re.match(r'^-?[\d.]+(e-?\d+)?$', v) else v) for h,v in zip(hdr,parts)}
            out.setdefault((k,'rows'),[]).append(row)
    return out
def bwbest(boot,name,kernel,size):
    return bw(boot,name)[((kernel,size),'best')]
def bwrows(boot,name,kernel,size):
    return bw(boot,name)[((kernel,size),'rows')]

def cmn(boot):
    out={}
    with open(D[boot]+'cmn-counts.csv') as f:
        for r in csv.DictReader(f):
            out.setdefault(r['label'],[]).append(r)
    return out

checks=[]
def ck(label, page, val, tol=None, fmt=None):
    """page: the number as printed; val: computed. Match if rounding page's decimals of val equals page."""
    if isinstance(page,str): page=float(page)
    if tol is None:
        # decimals of page
        s=str(page); dec=len(s.split('.')[1]) if '.' in s else 0
        ok = abs(round(val,dec)-page) < 1e-9 or abs(val-page) <= 0.5*10**(-dec)+1e-9
    else:
        ok = abs(val-page)<=tol
    checks.append((label,page,val,ok))

KB=1024; MB=1024*1024
# ---------- Short version ----------
ck('SV L1 2.0 ns [E latency-dram-small 4K]', 2.0, best('E','latency-dram-small',4*KB))
ck('SV L2 6.0 ns [E 128K]', 6.0, best('E','latency-dram-small',128*KB))
ck('SV SLC 24.2 [E latency-dram-large 2M]', 24.2, best('E','latency-dram-large',2*MB))
ck('SV DRAM 52.7 flushed [E latency-dram-flushed 8M]', 52.7, best('E','latency-dram-flushed',8*MB))
ck('SV 24.5 GB/s [E bandwidth-read-prefetch read 32M]', 24.5, bwbest('E','bandwidth-read-prefetch','read',32*MB))
ck('SV 9.2 GB/s [C read 32M]', 9.2, bwbest('C','bandwidth-read-prefetch','read',32*MB))
# L3 hit est: (ns - l2hit*t128 - l3refill*tC384)/l3hit, for 256K and 384K rows of hit set
def l3est(size):
    r=bestrow('E','latency-dram-small-l3',size)
    t128=best('E','latency-dram-small-l3',128*KB)  # page says "128 KiB row's time (an L2 hit)" -- which file? try both
    tC384=best('C','latency-dram-small-l3',384*KB)
    return (r['ns_per_load'] - r['l2d_hit_rd_per_load']*t128 - r['l3d_refill_rd_per_load']*tC384)/r['l3d_hit_rd_per_load']
e256=l3est(256*KB); e384=l3est(384*KB)
print('L3 hit est 256/384 (hit-set 128K time, C hit-set 384K):', round(e256,3), round(e384,3))
# variant: 128K time from latency-dram-small and C 384 from latency-dram-small
def l3est2(size):
    r=bestrow('E','latency-dram-small-l3',size)
    t128=best('E','latency-dram-small',128*KB); tC384=best('C','latency-dram-small',384*KB)
    return (r['ns_per_load'] - r['l2d_hit_rd_per_load']*t128 - r['l3d_refill_rd_per_load']*tC384)/r['l3d_hit_rd_per_load']
print('variant 2:', round(l3est2(256*KB),3), round(l3est2(384*KB),3))
ck('SV L3 hit about 11 est (mean of 256/384 est)', 11, (e256+e384)/2, tol=0.6)
ck('sec5 L3 hit 10.8 est', 10.8, (e256+e384)/2, tol=0.1)
ck('sec5 256K gives 10.6', 10.6, e256, tol=0.1)
ck('sec5 384K gives 11.0', 11.0, e384, tol=0.1)
# L3 step bullet
for sz,pe,pc,ph in [(192,7.8,14.1,47),(256,9.5,19.7,75),(384,10.9,22.7,92)]:
    ck(f'L3 step E {sz}K ns', pe, best('E','latency-dram-small',sz*KB))
    ck(f'L3 step C {sz}K ns (hit-set? or small?)', pc, best('C','latency-dram-small-l3',sz*KB))
    ck(f'L3 step hits {sz}K %', ph, 100*bestrow('E','latency-dram-small-l3',sz*KB)['l3d_hit_rd_per_load'], tol=0.5)
# --- repeat set: every best row shared by E and R3 by file+size, core and cme, round trip set aside
import glob
def allbest(boot):
    out={}
    for p in sorted(glob.glob(D[boot]+'latency-*.csv')+glob.glob(D[boot]+'cme-latency-*.csv')):
        n=os.path.basename(p)[:-4]
        for (sz,mode),v in lat(boot,n).items():
            if mode in ('best','cme-best') and sz>0: out[(n,sz,mode)]=v
    return out
be=allbest('E'); b3=allbest('R3'); ba=allbest('A')
shared=sorted(set(be)&set(b3))
print('shared E/R3 rows:', len(shared)); print([k for k in shared if 'control' in k[0] or k[1]<8192])
diffs=sorted(((be[k]-b3[k])/b3[k]*100,k,b3[k],be[k]) for k in shared)
n1=sum(1 for d,*_ in diffs if abs(d)<1); n3=sum(1 for d,*_ in diffs if abs(d)<3); n5=sum(1 for d,*_ in diffs if abs(d)<5)
print('E vs R3 within 1/3/5:', n1,n3,n5, ' moved>=1%:', len(shared)-n1)
ck('SV repeat 70 rows', 70, len(shared), tol=0)
ck('SV 24 within 1%', 24, n1, tol=0); ck('4.8 39 within 3%',39,n3,tol=0); ck('SV 47 within 5%',47,n5,tol=0)
ck('4.8 46 of 70 moved', 46, len(shared)-n1, tol=0)
ck('SV -51.6% at 384K', -51.6, diffs[0][0]); print('largest E/R3:', diffs[0], diffs[-1])
sharedA=sorted(set(ba)&set(b3))
dA=sorted(((ba[k]-b3[k])/b3[k]*100,k) for k in sharedA)
a1=sum(1 for d,_ in dA if abs(d)<1); a3=sum(1 for d,_ in dA if abs(d)<3); a5=sum(1 for d,_ in dA if abs(d)<5)
print('A vs R3 shared', len(sharedA), 'within', a1,a3,a5, 'max', max(dA,key=lambda x:abs(x[0])))
ck('4.8 A vs R3 70 shared', 70, len(sharedA), tol=0); ck('A 52 within 1%',52,a1,tol=0); ck('A 58 within 3%',58,a3,tol=0); ck('A 59 within 5%',59,a5,tol=0)
ck('A largest +11.27 %', 11.27, max(dA,key=lambda x:abs(x[0]))[0])
# 4.8 table first and last rows
ck('4.8 first row R3 384K 22.729', 22.729, b3[('latency-dram-small',384*KB,'best')])
ck('4.8 first row E 384K 11.004', 11.004, be[('latency-dram-small',384*KB,'best')])
ck('4.8 first row -51.59', -51.59, diffs[0][0])
last=[x for x in diffs if abs(x[0])>=1]
last=sorted(last,key=lambda x:-abs(x[0]))[-1]
print('4.8 last row:', last)
ck('4.8 last row R3 128K 6.090', 6.090, last[2]); ck('4.8 last E 6.023', 6.023, last[3]); ck('4.8 last -1.10', -1.10, last[0])
# OCM bullet
ck('SV OCM E dense all5 26.08', 26.08, best('E','latency-ocm-all5-dense-cpu2',1310720))
ck('SV OCM R3 25.34', 25.34, best('R3','latency-ocm-all5-dense-cpu2',1310720))
ck('SV OCM A 26.01', 26.01, best('A','latency-ocm-all5-dense-cpu2',1310720))
ck('SV OCM C 24.96', 24.96, best('C','latency-ocm-all5-dense-cpu2',1310720))
ck('4.2 all5 E L3 refills 1.0008', 1.0008, bestrow('E','latency-ocm-all5-dense-cpu2',1310720)['l3d_refill_rd_per_load'])
# route rows
cells=[(2,0),(2,1),(2,2),(2,3),(2,4),(4,2),(4,0),(4,1),(4,3),(4,4),(6,2),(6,3),(6,4),(6,0),(6,1),(8,4),(8,2),(8,3),(8,0),(8,1)]
def route(boot,c,r): return lat(boot,f'latency-ocm-region{r}-route-cpu{c}')
rE={}; rA={}; rC={}; rB={}
for c,r in cells:
    for bt,dd in (('E',rE),('A',rA),('C',rC),('B',rB)):
        L=route(bt,c,r); rr=L[(262144,'rows')]
        dd[(c,r)]=dict(best=L[(262144,'best')], med=st.median(x['ns_per_load'] for x in rr),
                       l3=st.mean(x['l3d_refill_rd_per_load'] for x in rr), pf=st.mean(x['l2d_refill_hwprf_per_load'] for x in rr))
print('E route l3 range', min(v['l3'] for v in rE.values()), max(v['l3'] for v in rE.values()))
print('A route l3 range', min(v['l3'] for v in rA.values()), max(v['l3'] for v in rA.values()))
print('C route l3 range', min(v['l3'] for v in rC.values()), max(v['l3'] for v in rC.values()))
ck('SV route E L3 refills 0.41', 0.41, min(v['l3'] for v in rE.values())); ck('SV route 0.82', 0.82, max(v['l3'] for v in rE.values()))
ck('sec6 A 0.78', 0.78, min(v['l3'] for v in rA.values())); ck('sec6 A 0.94', 0.94, max(v['l3'] for v in rA.values()))
ck('sec6 C 0.79', 0.79, min(v['l3'] for v in rC.values())); ck('sec6 C 0.93', 0.93, max(v['l3'] for v in rC.values()))
# 4.2 first row CPU2 OCM0 and last row CPU8 OCM1
for (c,r),pv in [((2,0),dict(E=19.60,med=20.32,l3=0.791,pf=0.27,A=20.77,Al3=0.914,C=21.24,B=22.60,R3=22.97,R2=19.77,Ed=18.03)),
                 ((8,1),dict(E=23.19,med=24.95,l3=0.787,pf=0.19,A=27.11,Al3=0.921,C=23.47,B=28.54,R3=28.45,R2=24.48,Ed=16.80))]:
    ck(f'4.2 route E {c}-{r}',pv['E'],rE[(c,r)]['best']); ck(f'4.2 med {c}-{r}',pv['med'],rE[(c,r)]['med'])
    ck(f'4.2 E l3 {c}-{r}',pv['l3'],rE[(c,r)]['l3']); ck(f'4.2 E pf {c}-{r}',pv['pf'],rE[(c,r)]['pf'])
    ck(f'4.2 A {c}-{r}',pv['A'],rA[(c,r)]['best']); ck(f'4.2 A l3 {c}-{r}',pv['Al3'],rA[(c,r)]['l3'])
    ck(f'4.2 C {c}-{r}',pv['C'],rC[(c,r)]['best']); ck(f'4.2 B {c}-{r}',pv['B'],rB[(c,r)]['best'])
    ck(f'4.2 R3 sparse {c}-{r}',pv['R3'],best('R3',f'latency-ocm-region{r}-cpu{c}',262144))
    ck(f'4.2 R2 dense {c}-{r}',pv['R2'],best('R2',f'latency-ocm-region{r}-cpu{c}',262144))
    ck(f'4.2 E dense {c}-{r}',pv['Ed'],best('E',f'latency-ocm-region{r}-dense-cpu{c}',262144))
# all-five table rows
for c,pv in [(2,dict(E=26.082,l3=1.0008,Es=25.013,A=26.009,C=24.959,B=25.576,Dd=24.959,R3=25.340,R3s=25.869,R2=25.506)),
             (8,dict(E=27.648,l3=1.0009,Es=25.634,A=27.512,C=27.162,B=27.663,Dd=27.105,R3=27.539,R3s=28.216,R2=27.700))]:
    ck(f'4.2 all5 E dense cpu{c}',pv['E'],best('E',f'latency-ocm-all5-dense-cpu{c}',1310720))
    ck(f'4.2 all5 E l3 cpu{c}',pv['l3'],bestrow('E',f'latency-ocm-all5-dense-cpu{c}',1310720)['l3d_refill_rd_per_load'])
    ck(f'4.2 all5 E sparse cpu{c}',pv['Es'],best('E',f'latency-ocm-all5-cpu{c}',1310720))
    for bt,k in (('A','A'),('C','C'),('B','B'),('D','Dd'),('R3','R3')):
        ck(f'4.2 all5 {bt} dense cpu{c}',pv[k],best(bt,f'latency-ocm-all5-dense-cpu{c}',1310720))
    ck(f'4.2 all5 R3 sparse cpu{c}',pv['R3s'],best('R3',f'latency-ocm-all5-cpu{c}',1310720))
    ck(f'4.2 all5 R2 cpu{c}',pv['R2'],best('R2',f'latency-ocm-all5-cpu{c}',1310720))
for c,pv in [(4,(26.121,26.572,26.112)),(6,(25.306,26.466,25.365))]:
    ck(f'4.2 all5 R3 dense cpu{c}',pv[0],best('R3',f'latency-ocm-all5-dense-cpu{c}',1310720))
    ck(f'4.2 all5 R3 sparse cpu{c}',pv[1],best('R3',f'latency-ocm-all5-cpu{c}',1310720))
    ck(f'4.2 all5 R2 cpu{c}',pv[2],best('R2',f'latency-ocm-all5-cpu{c}',1310720))
# distance groups
xy={88:(1,3),160:(2,4),216:(3,3),288:(4,4),344:(5,3)}; node={0:88,1:160,2:216,3:288,4:344}; dsu={2:(2,3),4:(3,2),6:(4,3),8:(5,2)}
dist={(c,r): abs(dsu[c][0]-xy[node[r]][0])+abs(dsu[c][1]-xy[node[r]][1]) for c,r in cells}
for d,pv in [(1,dict(n=8,E=16.60,Elo=13.97,Ehi=19.60,A=20.25,Alo=18.77,Ahi=20.89,B=22.23,Blo=21.70,Bhi=22.89)),
             (5,dict(n=2,E=21.48,Elo=19.77,Ehi=23.19,A=26.74,Alo=26.37,Ahi=27.11,B=29.17,Blo=28.54,Bhi=29.80))]:
    cs=[k for k in cells if dist[k]==d]; ck(f'dist {d} cells',pv['n'],len(cs),tol=0)
    for bt,dd in (('E',rE),('A',rA),('B',rB)):
        vals=[dd[k]['best'] for k in cs]
        ck(f'dist {d} {bt} mean',pv[bt],st.mean(vals)); ck(f'dist {d} {bt} lo',pv[bt+'lo'],min(vals)); ck(f'dist {d} {bt} hi',pv[bt+'hi'],max(vals))
# sec 6 dumbbell E-A deltas range, 19 of 20 faster
dl=[rE[k]['best']-rA[k]['best'] for k in cells]
print('E-A deltas', round(min(dl),2), round(max(dl),2), 'faster', sum(1 for x in dl if x<0), 'below0.8', sum(1 for k in cells if rE[k]['l3']<0.8))
ck('sec6 E-A min -7.35',-7.35,min(dl)); ck('sec6 E-A max +0.24',0.24,max(dl)); ck('sec6 19 of 20 faster',19,sum(1 for x in dl if x<0),tol=0)
ck('sec6 19 of 20 below 0.8 refills',19,sum(1 for k in cells if rE[k]['l3']<0.8),tol=0)
# sec 6 sparse E vs R3 on 10 cells (CPU 2, 8); CPU2 sparse L3 refill pass means
ds=[]
for c in (2,8):
    for r in range(5):
        ds.append(best('E',f'latency-ocm-region{r}-cpu{c}',262144)-best('R3',f'latency-ocm-region{r}-cpu{c}',262144))
ck('sec6 sparse E-R3 min -6.70',-6.70,min(ds)); ck('sec6 sparse max +3.77',3.77,max(ds))
sp={bt:[pmean(bt,f'latency-ocm-region{r}-cpu2',262144,'l3d_refill_rd_per_load') for r in range(5)] for bt in ('E','A','C')}
print('CPU2 sparse l3 pass means', {k:[round(x,3) for x in v] for k,v in sp.items()})
ck('sec6 sparse E l3 0.33',0.33,min(sp['E'])); ck('sec6 sparse E 0.59',0.59,max(sp['E']))
ck('sec6 sparse A 0.74',0.74,min(sp['A'])); ck('A 0.77',0.77,max(sp['A'])); ck('C 0.70',0.70,min(sp['C'])); ck('C 0.83',0.83,max(sp['C']))
ck('sec6 "0.41 to 0.67 take no refill"', 0.41, 1-max(sp['E'])); ck('0.67',0.67,1-min(sp['E']))
# all-five sparse E: 25.01/25.63 and l3 0.95/0.80 -> which pass? best pass? 
for c,pl3 in ((2,0.95),(8,0.80)):
    br=bestrow('E',f'latency-ocm-all5-cpu{c}',1310720); pm=pmean('E',f'latency-ocm-all5-cpu{c}',1310720,'l3d_refill_rd_per_load')
    print(f'all5 sparse E cpu{c} best-pass l3 {br["l3d_refill_rd_per_load"]:.3f} pass-mean {pm:.3f} page {pl3}')
    ck(f'sec6 all5 sparse E cpu{c} l3 (best pass)',pl3,br['l3d_refill_rd_per_load'],tol=0.011)
# Bandwidth bullet
ck('SV 24.9 at 2M',24.9,bwbest('E','bandwidth-read-prefetch','read',2*MB))
asmE={s:bwbest('E','bandwidth-l1-asmpasses','read',s*KB) for s in (4,8,16,24)}
asmC={s:bwbest('C','bandwidth-l1-asmpasses','read',s*KB) for s in (4,8,16,24)}
ppE={s:bwbest('E','bandwidth-l1-passes','read',s*KB) for s in (4,8,16,24)}
ppC={s:bwbest('C','bandwidth-l1-passes','read',s*KB) for s in (4,8,16,24)}
print('asm read E',asmE,'C',asmC); print('pp read E',ppE,'C',ppC)
ck('SV asm 59.8 at 16K? (min of E/C 16,24)',59.8,min(asmE[16],asmE[24],asmC[16],asmC[24])); ck('SV 60.6',60.6,max(asmE[16],asmE[24],asmC[16],asmC[24]))
ck('SV 95 % of 64 (60.6/64.1)',95,100*max(asmE[16],asmE[24])/64.1,tol=0.6)
ck('SV 155 GB/s eight writers 2M',155,bwbest('R3','bandwidth-all8','write',2*MB))
ocm3={r:bwbest('R3',f'bandwidth-ocm-region{r}','read',262144) for r in range(5)}
ck('SV OCM read 14.8',14.8,min(ocm3.values())); ck('SV OCM 16.6',16.6,max(ocm3.values()))
# 4.3 table first row (16K) and last (32M)
r1=bw('R3','bandwidth-dram-1core')
ck('4.3 16K read 58.1',58.1,r1[(('read',16*KB),'best')]); ck('4.3 16K write 30.1',30.1,r1[(('write',16*KB),'best')]); ck('4.3 16K copy 39.7',39.7,r1[(('copy',16*KB),'best')])
ck('4.3 16K E read 56.00',56.00,ppE[16]); ck('4.3 16K C read 56.59',56.59,ppC[16]); ck('4.3 16K E write 30.68',30.68,bwbest('E','bandwidth-write-small','write',16*KB))
ck('4.3 32M read 9.2',9.2,r1[(('read',32*MB),'best')]); ck('4.3 32M write 32.0',32.0,r1[(('write',32*MB),'best')]); ck('4.3 32M copy 18.0',18.0,r1[(('copy',32*MB),'best')])
ck('4.3 32M E read 24.55',24.55,bwbest('E','bandwidth-read-prefetch','read',32*MB)); ck('4.3 32M C read 9.20',9.20,bwbest('C','bandwidth-read-prefetch','read',32*MB))
ck('4.3 2M E 24.95',24.95,bwbest('E','bandwidth-read-prefetch','read',2*MB)); ck('4.3 2M C 9.29',9.29,bwbest('C','bandwidth-read-prefetch','read',2*MB))
ck('4.3 256K E write 31.87',31.87,bwbest('E','bandwidth-write-small','write',256*KB))
# 4.3 prose: write rows 2M..32M 31.98 to 32.00; 16K pass 534 ns on E; G8 write fits (page: 23.7 C, 25.7 E per-pass; 9.1, 14.0 asm)
wv=[r1[(('write',s),'best')] for s in (2*MB,32*MB)]; print('R3 write 2M/32M',wv)
ck('4.3 16K pass 534 ns on E', 534, 16384/bwbest('E','bandwidth-write-small','write',16*KB)/1e9*1e9, tol=1)
def fit(boot,name,kernel):
    xs=[]; ys=[]
    for s in (4,8,16,24):
        b=bwbest(boot,name,kernel,s*KB); xs.append(s*KB); ys.append(s*KB/b)  # ns per pass (bytes/GBps = ns)
    n=len(xs); mx=st.mean(xs); my=st.mean(ys)
    bb=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); a=my-bb*mx
    res=[abs(a+bb*x-y)/y*100 for x,y in zip(xs,ys)]
    return a, 1/bb, max(res), res
for bt in ('C','E'):
    for nm in ('bandwidth-l1-passes','bandwidth-l1-asmpasses'):
        for kn in ('write','read'):
            a,rate,mr,res=fit(bt,nm,kn); print(f'fit {bt} {nm} {kn}: a={a:.1f} ns rate={rate:.1f} GB/s maxres={mr:.1f}% res={[round(x,1) for x in res]}')
# marginal 8->16K rate
for bt in ('C','E'):
    for nm in ('bandwidth-l1-passes','bandwidth-l1-asmpasses'):
        t8=8*KB/bwbest(bt,nm,'read',8*KB); t16=16*KB/bwbest(bt,nm,'read',16*KB); print(f'marginal {bt} {nm} read 8->16K: {8*KB/(t16-t8):.1f} GB/s')
ck('sec7 E 4K per-pass read 40.91',40.91,ppE[4]); ck('sec7 C 4K per-pass 46.18',46.18,ppC[4])
ratios=[]
for nm in ('bandwidth-l1-passes','bandwidth-l1-asmpasses'):
    for kn in ('read','write'):
        for s in (4,8,16,24):
            if nm=='bandwidth-l1-passes' and kn=='read' and s==4: continue
            ratios.append(bwbest('E',nm,kn,s*KB)/bwbest('C',nm,kn,s*KB))
ck('sec7 other 15 rows 0.972',0.972,min(ratios)); ck('1.013',1.013,max(ratios))
wr=[bwbest(bt,nm,'write',s*KB) for bt in ('C','E') for nm in ('bandwidth-l1-passes','bandwidth-l1-asmpasses') for s in (4,8,16,24)]
print('G8 write rows', sorted(round(x,2) for x in wr))
ck('sec7 writes fit 31.9',31.9,min(wr),tol=0.15); ck('32.1',32.1,max(wr),tol=0.15)
# L1 refills at most 0.0121 per line on every G8 row
mxref=0
for bt in ('C','E'):
    for nm in ('bandwidth-l1-passes','bandwidth-l1-asmpasses'):
        for kn in ('read','write'):
            for s in (4,8,16,24):
                for r in bwrows(bt,nm,kn,s*KB): mxref=max(mxref,r['l1d_refill_per_line'])
ck('sec7 L1 refills at most 0.0121',0.0121,mxref)
# sec 7 read variants: 2.68x at 2M, 2.67 at 32M; pf4 20.2/20.4 E; C pf4 9.65 at 2M
ck('sec7 2.68x 2M',2.68,bwbest('E','bandwidth-read-prefetch','read',2*MB)/bwbest('C','bandwidth-read-prefetch','read',2*MB))
ck('sec7 2.67x 32M',2.67,bwbest('E','bandwidth-read-prefetch','read',32*MB)/bwbest('C','bandwidth-read-prefetch','read',32*MB))
ck('sec7 E pf4 2M 20.2',20.2,bwbest('E','bandwidth-read-prefetch','read-pf4',2*MB)); ck('E pf4 32M 20.4',20.4,bwbest('E','bandwidth-read-prefetch','read-pf4',32*MB))
ck('sec7 C pf4 2M 9.65',9.65,bwbest('C','bandwidth-read-prefetch','read-pf4',2*MB))
print('variants E', {k[0]:v for k,v in bw('E','bandwidth-read-prefetch').items() if k[1]=='best'})
print('variants C', {k[0]:v for k,v in bw('C','bandwidth-read-prefetch').items() if k[1]=='best'})
# ---------- 4.1 first and last rows ----------
for bt,pv in (('E',2.002),('R3',2.002),('C',2.002)):
    ck(f'4.1 4K {bt}',pv,best(bt,'latency-dram-small',4*KB))
ck('4.1 8M flushed E 52.659',52.659,best('E','latency-dram-flushed',8*MB)); ck('R3 52.738',52.738,best('R3','latency-dram-flushed',8*MB)); ck('C 52.657',52.657,best('C','latency-dram-flushed',8*MB))
ck('4.1 seq E 2.492',2.492,best('E','latency-dram-seq',8*MB)); ck('seq C 6.917',6.917,best('C','latency-dram-seq',8*MB)); ck('seq E/C 0.360',0.360,2.492/6.917)
sr=bestrow('E','latency-dram-seq',8*MB); ck('4.1 seq L1 refills 1.00',1.00,sr['l1d_refill_per_load']); ck('seq L3 0.00',0.00,sr['l3d_refill_rd_per_load'])
fr=bestrow('E','latency-dram-flushed',8*MB); ck('4.1 flushed L3 1.00',1.00,fr['l3d_refill_rd_per_load'])
ck('4.1 flushed E vs R3 -0.15',-0.15,(52.659-52.738)/52.738*100); ck('E/C flushed 1.000',1.000,52.659/52.657)
# 4.1 L3 rows E vs run 3 pct
for sz,pv in ((192,-44.31),(256,-50.72),(384,-51.59),(512,-24.64)):
    f='latency-dram-small' if sz<512 else 'latency-dram-large'
    ck(f'4.1 {sz}K E vs R3 %',pv,(best('E',f,sz*KB)-best('R3',f,sz*KB))/best('R3',f,sz*KB)*100)
for sz,pv in ((192,0.465),(256,0.751),(384,0.924),(512,0.412)):
    ck(f'4.1 {sz}K hits col',pv,bestrow('E','latency-dram-small-l3',sz*KB)['l3d_hit_rd_per_load'])
ck('4.1 note 512K hit-set 18.481',18.481,best('E','latency-dram-small-l3',512*KB))
# hit-set table first (64K) and last (512K)
for sz,pv in ((64,dict(E=5.126,C=5.131,r=0.999,l2=0.8241,l3h=0.0001,l3r=0.0000,lo=0.0001,hi=0.0002,Ch=0.0000)),
              (512,dict(E=18.481,C=23.722,r=0.779,l2=0.0072,l3h=0.4118,l3r=0.5813,lo=0.4031,hi=0.4118,Ch=0.0000))):
    e=bestrow('E','latency-dram-small-l3',sz*KB); c=bestrow('C','latency-dram-small-l3',sz*KB)
    ck(f'hs {sz}K E',pv['E'],e['ns_per_load']); ck(f'hs {sz}K C',pv['C'],c['ns_per_load']); ck(f'hs {sz}K E/C',pv['r'],e['ns_per_load']/c['ns_per_load'])
    ck(f'hs {sz}K l2hit',pv['l2'],e['l2d_hit_rd_per_load']); ck(f'hs {sz}K l3hit',pv['l3h'],e['l3d_hit_rd_per_load']); ck(f'hs {sz}K l3ref',pv['l3r'],e['l3d_refill_rd_per_load'])
    hs=[r['l3d_hit_rd_per_load'] for r in rows('E','latency-dram-small-l3',sz*KB)]
    ck(f'hs {sz}K lo',pv['lo'],min(hs)); ck(f'hs {sz}K hi',pv['hi'],max(hs)); ck(f'hs {sz}K C hits',pv['Ch'],c['l3d_hit_rd_per_load'])
# L3 accesses = refills + hits within 0.0001 on every E row
mxd=0
for sz in (64,96,128,192,256,384,512):
    for r in rows('E','latency-dram-small-l3',sz*KB): mxd=max(mxd,abs(r['l3d_access_rd_per_load']-r['l3d_refill_rd_per_load']-r['l3d_hit_rd_per_load']))
print('max |access-refill-hit|', mxd); ck('hs note within 0.0001', 0.0001, mxd, tol=0.00005)
# five-boot table numbers (first/last rows and a few)
for bt,pv in (('A',19.470),('B',20.172),('C',19.228),('D',20.170),('E',9.527)): ck(f'five 256K {bt}',pv,best(bt,'latency-dram-small',256*KB))
for bt,pv in (('A',52.181),('B',52.248),('C',52.238),('D',52.249),('E',52.875)): ck(f'five 32M {bt}',pv,best(bt,'latency-dram-large',32*MB))
for bt,pv in (('A',24.091),('B',23.902),('C',24.053),('D',23.888),('E',24.177)): ck(f'five 2M {bt}',pv,best(bt,'latency-dram-large',2*MB))
for bt,pv in (('A',6.917),('B',52.762),('C',6.917),('D',52.763),('E',2.492)): ck(f'five seq {bt}',pv,best(bt,'latency-dram-seq',8*MB))
for bt,pv in (('B',2.377),('C',9.196),('D',2.377),('E',24.546)): ck(f'five read32M {bt}',pv,bwbest(bt,'bandwidth-read-prefetch','read',32*MB))
for bt,lo,hi in (('B',0,0),('C',0,0),('D',0,0),('E',0.7508,0.7712)):
    hs=[r['l3d_hit_rd_per_load'] for r in rows(bt,'latency-dram-small-l3',256*KB)]; ck(f'five hits256 {bt} lo',lo,min(hs)); ck(f'five hits256 {bt} hi',hi,max(hs))
# controls
ck('ctrl 4K E 2.002',2.002,best('E','latency-dram-small',4*KB))
allc=[best(bt,'latency-dram-small',4*KB) for bt in 'ABCDE']; print('4K on five boots',allc)
ck('ctrl five boots 2.001',2.001,min(allc)); ck('2.002',2.002,max(allc))
rt=[r['ns_per_load'] for bt in 'ABCDE' for r in lat(bt,'cme-latency-dram-small')[(0,'rows')] if r['mode']=='cme-roundtrip']
print('roundtrip range', min(rt), max(rt)); ck('rt 21.004',21.004,min(rt)); ck('rt 21.006',21.006,max(rt))
rt3=[r['ns_per_load'] for r in lat('R3','cme-latency-dram-small')[(0,'rows')] if r['mode']=='cme-roundtrip']; print('R3 rt',min(rt3),max(rt3))
ck('ctrl uncounted cpu2 2.014',2.014,best('E','latency-control-cpu2',4*KB)); ck('cpu8 2.018',2.018,best('E','latency-control-cpu8',4*KB))
# perf_cov 699 rows all 1.0000, no "# perf:"
n=0; bad=0; perfl=0
for p in glob.glob(D['E']+'*.csv'):
    hdr=None
    for line in open(p):
        if line.startswith('# perf'): perfl+=1
        if line.startswith('#'): continue
        parts=line.strip().split(',')
        if parts[0]=='mem': hdr=parts; continue
        if hdr and 'perf_cov' in hdr and len(parts)==len(hdr) and parts[-1] not in ('-',''):
            v=float(parts[-1]); n+=1
            if abs(v-1.0)>1e-9: bad+=1
print('perf_cov rows', n, 'bad', bad, 'perf lines', perfl); ck('699 counted rows',699,n,tol=0)
# sec 5 bullets
ck('sec5 192-384 ratio 0.49',0.49,min(best('E','latency-dram-small',s*KB)/best('C','latency-dram-small',s*KB) for s in (192,256,384)))
ck('sec5 0.55',0.55,max(best('E','latency-dram-small',s*KB)/best('C','latency-dram-small',s*KB) for s in (192,256,384)))
rr=[best('E','latency-dram-small',s*KB)/best('C','latency-dram-small',s*KB) for s in (4,8,16,24,32,48,64,96,128)]
ck('sec5 4-128K 0.986',0.986,min(rr)); ck('1.002',1.002,max(rr))
# run 3 and C within 3.2 % at every footprint
sm=[(s,best('R3','latency-dram-small',s*KB),best('C','latency-dram-small',s*KB)) for s in (4,8,16,24,32,48,64,96,128,192,256,384)]
lg=[(s,best('R3','latency-dram-large',s*KB),best('C','latency-dram-large',s*KB)) for s in (512,768,1024,1536,2048,3072,4096,6144,8192,16384,32768)]
mx=max(abs(a-b)/a*100 for s,a,b in sm+lg); print('R3 vs C max %', mx); ck('sec5 run3/C within 3.2 %',3.2,mx,tol=0.06)
ck('sec5 16M E-C 0.48',0.48,best('E','latency-dram-large',16*MB)-best('C','latency-dram-large',16*MB))
ck('sec5 32M E-C 0.64',0.64,best('E','latency-dram-large',32*MB)-best('C','latency-dram-large',32*MB))
ck('sec5 R3 32M 52.185',52.185,best('R3','latency-dram-large',32*MB))
ck('sec5 E 32M walk 0.51',0.51,bestrow('E','latency-dram-walk-cpu2',32*MB)['dtlb_walk_per_load'])
ck('sec5 B seq 52.762',52.762,best('B','latency-dram-seq',8*MB)); ck('B flushed 52.739',52.739,best('B','latency-dram-flushed',8*MB))
ck('sec5 model delay about 28 est (52.659-24.177)',28,best('E','latency-dram-flushed',8*MB)-best('E','latency-dram-large',2*MB),tol=0.6)
ck('sec5 seq E L1 prefetch 0.9997',0.9997,bestrow('E','latency-dram-seq',8*MB)['l1d_refill_hwprf_per_load']); ck('C 0.9999',0.9999,bestrow('C','latency-dram-seq',8*MB)['l1d_refill_hwprf_per_load'])
ck('sec5 A seq 6.917',6.917,best('A','latency-dram-seq',8*MB)); ck('D seq 52.763',52.763,best('D','latency-dram-seq',8*MB))
# sec 6: fit B route cells: t = a + bx*|dx| + by*|dy|
def fitxy(dd):
    import itertools
    X=[(1,abs(dsu[c][0]-xy[node[r]][0]),abs(dsu[c][1]-xy[node[r]][1])) for c,r in cells]; y=[dd[k]['best'] for k in cells]
    # normal equations 3x3
    n=3
    M=[[sum(X[i][a]*X[i][b] for i in range(len(X))) for b in range(n)] for a in range(n)]
    v=[sum(X[i][a]*y[i] for i in range(len(X))) for a in range(n)]
    # gaussian elimination
    for i in range(n):
        p=M[i][i]
        for j in range(i+1,n):
            f=M[j][i]/p
            for k in range(n): M[j][k]-=f*M[i][k]
            v[j]-=f*v[i]
    coef=[0]*n
    for i in range(n-1,-1,-1):
        coef[i]=(v[i]-sum(M[i][k]*coef[k] for k in range(i+1,n)))/M[i][i]
    res=[y[i]-sum(X[i][k]*coef[k] for k in range(n)) for i in range(len(X))]
    return coef, math.sqrt(sum(r*r for r in res)/len(res))
for bt,dd in (('B',rB),('A',rA),('C',rC),('E',rE)):
    coef,rms=fitxy(dd); print(f'fit {bt}: a={coef[0]:.2f} x={coef[1]:.2f} y={coef[2]:.2f} rms={rms:.2f}')
    if bt=='B':
        ck('sec6 B fit 0.09 rms',0.09,rms); ck('B a 20.75',20.75,coef[0]); ck('B x 1.99',1.99,coef[1]); ck('B y 0.95',0.95,coef[2])
    if bt=='A': ck('sec6 A rms 0.90',0.90,rms)
    if bt=='C': ck('sec6 C rms 0.80',0.80,rms)
    if bt=='E': ck('sec6 E rms 2.05',2.05,rms)
rD={}
for c,r in cells:
    L=route('D',c,r); rD[(c,r)]=dict(best=L[(262144,'best')])
coef,rms=fitxy(rD); print(f'fit D: x={coef[1]:.2f} y={coef[2]:.2f} rms={rms:.2f}'); ck('D x 2.00',2.00,coef[1]); ck('D y 0.98',0.98,coef[2]); ck('D rms 0.13',0.13,rms)
# hint GM ratios over 69 core OCM rows: D/B 0.985, C/A 0.977, C/D 0.861
def ocmrows(bt):
    out={}
    for p in sorted(glob.glob(D[bt]+'latency-ocm-*.csv')):
        n=os.path.basename(p)[:-4]
        for (sz,mode),v in lat(bt,n).items():
            if mode=='best': out[(n,sz)]=v
    return out
oc={bt:ocmrows(bt) for bt in 'ABCD'}
def gm(x,y):
    ks=sorted(set(oc[x])&set(oc[y])); return math.exp(st.mean(math.log(oc[x][k]/oc[y][k]) for k in ks)), len(ks)
for x,y,pv in (('D','B',0.985),('C','A',0.977),('C','D',0.861)):
    g,n=gm(x,y); print(f'GM {x}/{y} = {g:.4f} over {n} rows'); ck(f'sec6 GM {x}/{y}',pv,g); 
ck('sec6 69 rows',69,gm('D','B')[1],tol=0)
# TLB per pass: A 21 to 559, C/D 11 to 15, E 20 to 576 (latency-ocm-region<r>-<shape>-tlb-cpu2: l1d_tlb_refill per load * loads per pass)
def tlbpass(bt):
    vals=[]
    for p in sorted(glob.glob(D[bt]+'latency-ocm-region*-tlb-cpu2.csv')):
        n=os.path.basename(p)[:-4]
        for (sz,mode),rr in lat(bt,n).items():
            if mode=='rows':
                for r in rr: vals.append(r['l1d_tlb_refill_per_load']*r['loads'])
    return min(vals),max(vals),len(vals)
for bt,lo,hi in (('A',21,559),('C',11,15),('D',11,15),('E',20,576)):
    a,b,n=tlbpass(bt); print(f'TLB/pass {bt}: {a:.1f} to {b:.1f} over {n} passes'); ck(f'sec6 TLB {bt} lo',lo,a,tol=0.5); ck(f'sec6 TLB {bt} hi',hi,b,tol=0.5)
# sparse hop on E: 0.31 to 0.72 L1 DTLB refills, 0.56 to 1.62 walks (pass means) [latency-ocm-region<r>-tlb-cpu2.csv]
tl=[pmean('E',f'latency-ocm-region{r}-tlb-cpu2',262144,'l1d_tlb_refill_per_load') for r in range(5)]
wk=[pmean('E',f'latency-ocm-region{r}-tlb-cpu2',262144,'dtlb_walk_per_load') for r in range(5)]
print('E sparse tlb pass means',[round(x,3) for x in tl],'walks',[round(x,3) for x in wk])
ck('sec6 E sparse TLB 0.31',0.31,min(tl)); ck('0.72',0.72,max(tl)); ck('walks 0.56',0.56,min(wk)); ck('1.62',1.62,max(wk))
# gap sparse - dense mean on CPU2: A 4.0, B 1.8, C 2.8, D 1.2, E 2.8
for bt,pv in (('A',4.0),('B',1.8),('C',2.8),('D',1.2),('E',2.8)):
    g=st.mean(best(bt,f'latency-ocm-region{r}-cpu2',262144)-best(bt,f'latency-ocm-region{r}-dense-cpu2',262144) for r in range(5))
    print(f'gap {bt} {g:.2f}'); ck(f'sec6 gap {bt}',pv,g)
# walk rates: D tlb-set row 0.003 vs walk row 0.438; E 0.366 and 0.512
ck('D tlb-row walks 0.003',0.003,bestrow('D','latency-dram-tlb-cpu2',32*MB)['dtlb_walk_per_load'])
ck('D walk-row 0.438',0.438,bestrow('D','latency-dram-walk-cpu2',32*MB)['dtlb_walk_per_load'])
ck('E tlb-row 0.366',0.366,bestrow('E','latency-dram-tlb-cpu2',32*MB)['dtlb_walk_per_load']); ck('E walk-row 0.512',0.512,bestrow('E','latency-dram-walk-cpu2',32*MB)['dtlb_walk_per_load'])
ck('open 129x',129,0.438/0.003,tol=20)
# ---------- 4.4, 4.5, 4.6 first/last ----------
pr=bw('R3','bandwidth-pair'); pr2=bw('R2','bandwidth-pair')
ck('4.4 first R2 115.5',115.5,pr2[(('read',16*KB),'best')]); ck('4.4 first R3 116.4',116.4,pr[(('read',16*KB),'best')])
ck('4.4 first +0.77',0.77,(pr[(('read',16*KB),'best')]-pr2[(('read',16*KB),'best')])/pr2[(('read',16*KB),'best')]*100)
ck('4.4 first 2.00x',2.00,pr[(('read',16*KB),'best')]/r1[(('read',16*KB),'best')])
a8=bw('R3','bandwidth-all8'); a82=bw('R2','bandwidth-all8')
ck('4.4 last R2 128.2',128.2,a82[(('copy',16*MB),'best')]); ck('4.4 last R3 128.2',128.2,a8[(('copy',16*MB),'best')])
ck('4.4 last -0.05',-0.05,(a8[(('copy',16*MB),'best')]-a82[(('copy',16*MB),'best')])/a82[(('copy',16*MB),'best')]*100)
ck('4.4 last 7.14x',7.14,a8[(('copy',16*MB),'best')]/r1[(('copy',32*MB),'best')]); ck('89 %',89,a8[(('copy',16*MB),'best')]/r1[(('copy',32*MB),'best')]/8*100,tol=0.5)
ck('4.4 8 write 2M 155.2',155.2,a8[(('write',2*MB),'best')])
pd=bw('R3','bandwidth-perdsu')
w4=bwrows('R3','bandwidth-perdsu','write',2*MB); print('4 writers per-thread', [(r['per_thread_min_GBps'],r['per_thread_max_GBps']) for r in w4])
r4=bwrows('R3','bandwidth-perdsu','read',2*MB); print('4 readers per-thread', [(r['per_thread_min_GBps'],r['per_thread_max_GBps']) for r in r4])
r8=bwrows('R3','bandwidth-all8','read',2*MB); print('8 readers per-thread', [(r['per_thread_min_GBps'],r['per_thread_max_GBps']) for r in r8])
ck('4.4 prose one core 2M read 9.31',9.31,r1[(('read',2*MB),'best')]); 
ck('4.4 prose 2M chase CPUs 2,4,6,8 R3: 24.1',24.1,best('R3','latency-dram-large',2*MB))
for c,pv in ((4,24.6),(6,24.7),(8,26.1)): ck(f'4.4 prose 2M chase cpu{c}',pv,best('R3',f'latency-dram-slc-cpu{c}',2*MB))
wc=bw('R3','bandwidth-write-cpus2-3'); wc2=bw('R2','bandwidth-write-cpus2-3')
ck('4.5 first R2 40.9',40.9,wc2[(('write',16*MB),'best')]); ck('4.5 first R3 40.9',40.9,wc[(('write',16*MB),'best')])
ck('4.5 first +0.04',0.04,(wc[(('write',16*MB),'best')]-wc2[(('write',16*MB),'best')])/wc2[(('write',16*MB),'best')]*100)
pw=bwrows('R3','bandwidth-write-cpus2-3','write',16*MB); ck('4.5 per writer 20.5',20.5,min(r['per_thread_min_GBps'] for r in pw)); ck('21.7',21.7,max(r['per_thread_max_GBps'] for r in pw))
wl=bw('R3','bandwidth-write-cpus2-4-6-8'); wl2=bw('R2','bandwidth-write-cpus2-4-6-8')
ck('4.5 last R3 128.0',128.0,wl[(('write',16*MB),'best')]); ck('4.5 last R2 128.0',128.0,wl2[(('write',16*MB),'best')]); ck('4.5 last -0.01',-0.01,(wl[(('write',16*MB),'best')]-wl2[(('write',16*MB),'best')])/wl2[(('write',16*MB),'best')]*100)
o0=bwbest('R3','bandwidth-ocm-region0','read',262144); o02=bwbest('R2','bandwidth-ocm-region0','read',262144)
ck('4.6 first R3 16.2',16.2,o0); ck('4.6 first R2 16.4',16.4,o02); ck('4.6 first -1.07',-1.07,(o0-o02)/o02*100)
ow=bwbest('R3','bandwidth-ocm-write','write',1310720); ow2=bwbest('R2','bandwidth-ocm-write','write',1310720)
ck('4.6 last R3 20.3',20.3,ow); ck('4.6 last R2 20.4',20.4,ow2); ck('4.6 last -0.52',-0.52,(ow-ow2)/ow2*100)
ck('4.6 all5 16.0',16.0,bwbest('R3','bandwidth-ocm-all5','read',1310720)); ck('4.6 4core 66.5',66.5,bwbest('R3','bandwidth-ocm-4core','read',262144))
# 4.6.1 last row DRAM 32M: 9.2, 32.0, 24.5 - covered. 256K chase L3 refills E 0.00 vs R3 0.75
ck('4.6.1 E 256K L3 refills 0.00',0.00,bestrow('E','latency-dram-small',256*KB)['l3d_refill_rd_per_load'])
ck('4.6.1 R3 256K L3 refills 0.75',0.75,bestrow('R3','latency-dram-small',256*KB)['l3d_refill_rd_per_load'])
# 4.7 first and last rows: hns_pocq_reqs_recvd_all per node for sparse rows R3 (labels?) 
c3=cmn('R3'); c2=cmn('R2'); print('R3 labels', sorted(c3)[:50])

# ---------- 71st row: duplicates in R3 by (mode,size) ----------
for bt in ('R3',):
    for p in sorted(glob.glob(D[bt]+'latency-*.csv')+glob.glob(D[bt]+'cme-latency-*.csv')):
        n=os.path.basename(p)[:-4]; seen={}
        for line in open(p):
            if line.startswith('#') or line.startswith('mem,'): continue
            parts=line.split(','); k=(parts[2],parts[1])
            if parts[2].endswith('best'): seen[k]=seen.get(k,0)+1
        d=[k for k,v in seen.items() if v>1]
        if d: print('R3 dup best rows', n, d)
for p in sorted(glob.glob(D['E']+'latency-*.csv')+glob.glob(D['E']+'cme-latency-*.csv')):
    n=os.path.basename(p)[:-4]; seen={}
    for line in open(p):
        if line.startswith('#') or line.startswith('mem,'): continue
        parts=line.split(','); k=(parts[2],parts[1])
        if parts[2].endswith('best'): seen[k]=seen.get(k,0)+1
    d=[k for k,v in seen.items() if v>1]
    if d: print('E dup best rows', n, d)
print('R3 csv files', len(glob.glob(D['R3']+'*.csv')))
# GM C/D over the 69 rows common to all four
ks=set(oc['A'])&set(oc['B'])&set(oc['C'])&set(oc['D']); print('common 4-boot rows', len(ks))
g=math.exp(st.mean(math.log(oc['C'][k]/oc['D'][k]) for k in ks)); print('GM C/D over common', round(g,4))
ck('sec6 GM C/D over common rows 0.861',0.861,g)
# ---------- 4.7 table: own node / other four from cmn R3, R2 ----------
def reqs(cm,label):
    return {int(r['nodeid']):int(r['count']) for r in cm[label] if r['event']=='hns_pocq_reqs_recvd_all'}
for c,r,pv in ((2,0,(55374,9049,6.1,115433,0.48)),(8,4,(49134,9601,5.1,120209,0.41))):
    q3=reqs(c3,f'ocm-region{r}-cpu{c}'); q2=reqs(c2,f'ocm-region{r}-cpu{c}'); own=node[r]
    oth=st.mean(v for k,v in q3.items() if k!=own)
    ck(f'4.7 own R3 {c}-{r}',pv[0],q3[own],tol=0); ck(f'4.7 others {c}-{r}',pv[1],oth,tol=0.5); ck(f'4.7 ratio {c}-{r}',pv[2],q3[own]/oth); ck(f'4.7 own R2 {c}-{r}',pv[3],q2[own],tol=0); ck(f'4.7 R3/R2 {c}-{r}',pv[4],q3[own]/q2[own])
rat=[]; r32=[]; oth32=[]
for c in (2,4,6,8):
    for r in range(5):
        q3=reqs(c3,f'ocm-region{r}-cpu{c}'); q2=reqs(c2,f'ocm-region{r}-cpu{c}'); own=node[r]
        oth=st.mean(v for k,v in q3.items() if k!=own); rat.append(q3[own]/oth); r32.append(q3[own]/q2[own])
        oth32+= [q3[k]/q2[k] for k in q3 if k!=own]
ck('sec10 own/others 5.1',5.1,min(rat)); ck('6.2',6.2,max(rat)); ck('sec10 own R3/R2 0.40',0.40,min(r32)); ck('0.49',0.49,max(r32)); ck('sec10 others 0.91',0.91,min(oth32)); ck('1.04',1.04,max(oth32))
q=reqs(c3,'ocm-region1-cpu2'); ck('sec10 OCM1 node160 47,972',47972,q[160],tol=0); ck('sec10 8,692 avg',8692,st.mean(v for k,v in q.items() if k!=160),tol=0.5)
print('sec10 fig node counts', q)
# dense all-five controls repeat run 2 node for node within -2.3 to +1.4
dd=[]
for c in (2,4,6,8):
    q3=reqs(c3,f'ocm-all5-dense-cpu{c}'); q2=reqs(c2,f'ocm-all5-cpu{c}')
    dd+=[(q3[k]-q2[k])/q2[k]*100 for k in q3]
ck('sec10 all5 -2.3',-2.3,min(dd)); ck('+1.4',1.4,max(dd))
# control rows background 8,337 to 10,657; helper time diff 658,812; R2 622,374; counted command 44,824 longer
bg=[v for c in (2,4,6,8) for v in reqs(c3,f'control-cpu{c}').values()]; ck('sec10 bg 8,337',8337,min(bg),tol=0); ck('10,657',10657,max(bg),tol=0)
def elapsed(cm,label): return int([r for r in cm[label] if r['event']=='child_elapsed_ns'][0]['count'])
print('R3 control labels', [l for l in c3 if 'control' in l], 'R2', [l for l in c2 if 'control' in l])
for r in c3['control-nocount-cpu2']: print(r)
# section 10 route table first and last rows (E) + A
def flits(cm,label):
    out={}
    for r in cm[label]:
        m=re.match(r'mxp_([ewns])_dat_txflit_valid',r['event'])
        if m: out[(int(r['nodeid']),m.group(1))]=int(r['count'])
    return out
cE=cmn('E'); cA=cmn('A')
for c,r,dsuid,pv in ((2,0,152,dict(d=(21974,77769,8236,1172),n=(69766,3010,544,1557),dsh=71,nsh=93,Ad=75,An=89)),
                     (8,1,None,dict(d=(0,33992,1980,602),n=(37518,1188,0,9390),dsh=93,nsh=78,Ad=97,An=88))):
    f=flits(cE,f'route-ocm{r}-cpu{c}'); nid=node[r]; ids=sorted(set(k[0] for k in f)); did=[i for i in ids if i!=nid][0]
    dv=tuple(f[(did,x)] for x in 'ewns'); nv=tuple(f[(nid,x)] for x in 'ewns')
    print(f'route {c}-{r} dsu xp id {did}: {dv} node {nid}: {nv}')
    for i,x in enumerate('ewns'):
        ck(f'sec10 {c}-{r} dsu {x}',pv['d'][i],dv[i],tol=0); ck(f'sec10 {c}-{r} node {x}',pv['n'][i],nv[i],tol=0)
    ck(f'sec10 {c}-{r} dsu share',pv['dsh'],100*max(dv)/sum(dv),tol=0.5); ck(f'sec10 {c}-{r} node share',pv['nsh'],100*max(nv)/sum(nv),tol=0.5)
    fa=flits(cA,f'route-ocm{r}-cpu{c}'); dva=tuple(fa[(did,x)] for x in 'ewns'); nva=tuple(fa[(nid,x)] for x in 'ewns')
    ck(f'sec10 {c}-{r} A dsu share',pv['Ad'],100*max(dva)/sum(dva),tol=0.5); ck(f'sec10 {c}-{r} A node share',pv['An'],100*max(nva)/sum(nva),tol=0.5)
# X-first 20 of 20 and min share 61 %
xf_d=0; xf_n=0; minsh=100; xfa_d=0; xfa_n=0
for c,r in cells:
    for cm,acc in ((cE,'E'),(cA,'A')):
        f=flits(cm,f'route-ocm{r}-cpu{c}'); nid=node[r]; did=[i for i in set(k[0] for k in f) if i!=nid][0]
        dx=xy[nid][0]-dsu[c][0]; dy=xy[nid][1]-dsu[c][1]
        xd='e' if dx>0 else 'w'; xn='w' if dx>0 else 'e'
        if dx==0: xd='n' if dy>0 else 's'; xn='s' if dy>0 else 'n'
        md=max('ewns',key=lambda x:f[(did,x)]); mn=max('ewns',key=lambda x:f[(nid,x)])
        if acc=='E':
            xf_d+= md==xd; xf_n+= mn==xn
            minsh=min(minsh, 100*f[(did,md)]/sum(f[(did,x)] for x in 'ewns'), 100*f[(nid,mn)]/sum(f[(nid,x)] for x in 'ewns'))
        else: xfa_d+= md==xd; xfa_n+= mn==xn
print('E X-first dsu/node', xf_d, xf_n, 'A', xfa_d, xfa_n, 'min share', round(minsh,1))
ck('sec10 E xfirst dsu 20',20,xf_d,tol=0); ck('node 20',20,xf_n,tol=0); ck('A dsu 20',20,xfa_d,tol=0); ck('A node 20',20,xfa_n,tol=0); ck('sec10 min share 61 %',61,minsh,tol=0.5)
# ---------- five-boot table: hits lo/hi; 4.3 2 MiB pass 66 us; 4.3 write 31.98-32.00 ----------
ck('4.3 2 MiB pass 66 us',66,2*MB/bwbest('R3','bandwidth-dram-1core','write',2*MB)/1e3,tol=0.6)
ck('4.3 R3 write 2M..32M 31.98',31.98,min(wv)); ck('32.00',32.00,max(wv))
# write-small program per-pass: on A run3 prog minus run2 prog per pass 6.7 to 11.2 ns at 16..256K; E 16K -0.8, 48..256K 7.4 to 7.9
def perpass(bt,name,size): return size/bwbest(bt,name,'write',size)   # ns per pass
dA=[perpass('A','bandwidth-write-small',s)-perpass('A','bandwidth-write-small-r2prog',s) for s in (16*KB,48*KB,96*KB,256*KB)]
dE=[perpass('E','bandwidth-write-small',s)-perpass('E','bandwidth-write-small-r2prog',s) for s in (16*KB,48*KB,96*KB,256*KB)]
print('write-small prog delta per pass A', [round(x,2) for x in dA], 'E', [round(x,2) for x in dE])
ck('sec7 A prog 6.7',6.7,min(dA)); ck('11.2',11.2,max(dA)); ck('sec7 E 16K -0.8',-0.8,dE[0]); ck('E 7.4',7.4,min(dE[1:])); ck('7.9',7.9,max(dE[1:]))
d32=[perpass('R3','bandwidth-dram-1core',s)-perpass('R2','bandwidth-dram-1core',s) for s in (16*KB,48*KB,96*KB,256*KB)]
print('R3-R2 per pass', [round(x,2) for x in d32]); ck('sec7 across runs 7.7',7.7,min(d32)); ck('8.0',8.0,max(d32))
# section 3 map labels: CPU 2 route best per region on E: 19.6 18.6 19.3 18.0 20.9
for r,pv in enumerate((19.6,18.6,19.3,18.0,20.9)): ck(f'map OCM{r} label',pv,rE[(2,r)]['best'])
# ---------- summary ----------
bad=[c for c in checks if not c[3]]
print(f'\nCHECKS {len(checks)} mismatches {len(bad)}')
for c in bad: print('MISMATCH', c[0], 'page', c[1], 'csv', round(c[2],4))
