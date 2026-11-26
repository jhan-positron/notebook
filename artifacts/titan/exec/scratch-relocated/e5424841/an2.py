import sys, csv, collections, itertools, statistics as st
import numpy as np
base='/home/jhan/workspace/titan/cache-perf/asimov/results/'
def homes(p):
    L=open(p).read().split('\n'); print(L[0]); s=''.join(x for x in L[1:] if not x.startswith('#')); return s
def sel(pa, shut=0, n=5):
    a = pa>>6            # Addr[51:6], 46 bits
    a = (a>>shut)<<shut if shut else a
    h = (a & 0xfff) ^ ((a>>12)&0xfff) ^ ((a>>24)&0xfff) ^ ((a>>36)&0x3ff)
    top=0
    for k in range(6):   # bit 11-k of mix = h[11-k]^h[k]
        top |= (((h>>(11-k))^(h>>k))&1) << (5-k)
    mix=(top<<6)|(h&0x3f)
    return (mix*n)>>12
for name,p in (("014 boot1",base+'membench-jibin-014/results/bootM1/map-homes.txt'),("013 rehearsal",base+'membench-jibin-013/results/bootM0/map-rehearsal-homes.txt')):
    s=homes(p); pa0=0xc004800<<12
    print(name,"chars",len(s),collections.Counter(s).most_common())
    for shut in (0,):
        m=collections.Counter(); bad=0
        for i,ch in enumerate(s):
            if ch in '01234': m[(sel(pa0+64*i,shut),int(ch))]+=1
        print(" shut",shut,"(formula select, measured index): count"); 
        for k in sorted(m): print("   ",k,m[k])
        # consistent permutation?
        best={}
        for (f,h),c in m.items():
            if c>best.get(f,(0,0))[1]: best[f]=(h,c)
        tot=sum(m.values()); agree=sum(c for (f,h),c in m.items() if best[f][0]==h)
        print("  mapping",{f:best[f][0] for f in sorted(best)},"agree",agree,"of",tot)
        # what about the non-digit lines
        nd=[(i,ch,sel(pa0+64*i)) for i,ch in enumerate(s) if ch not in '01234']
        print("  non-digit lines:",len(nd), collections.Counter(ch for _,ch,_ in nd))
# SN-position fit for dram-flush
f=base+'membench-jibin-014/results/bootM1/latency-map.csv'
rows=[r for r in csv.reader(l for l in open(f) if not l.startswith('#'))]; H={n:i for i,n in enumerate(rows[0])}
nodes=[88,160,216,288,344]
npos={88:(1,3),160:(2,4),216:(3,3),288:(4,4),344:(5,3)}
cpos={2:(2,3),3:(2,3),4:(3,2),5:(3,2),6:(4,3),7:(4,3),8:(5,2),9:(5,2)}
def best(kind):
    d=collections.defaultdict(list)
    for r in rows[1:]:
        if r[0]==kind and int(r[1])>=2: d[(int(r[1]),int(r[2]))].append(float(r[H['ns_per_load']]))
    return {k:min(v) for k,v in d.items()}
D=best('dram-flush'); S=best('slc')
def tryfit(model, y, label):
    res=[]
    for sx in range(0,7):
        for sy in range(0,7):
            A=[];Y=[]
            for (c,n),v in y.items():
                cx,cy=cpos[c];hx,hy=npos[n]
                if model=='tri':   X=abs(cx-hx)+abs(hx-sx)+abs(sx-cx); Yy=abs(cy-hy)+abs(hy-sy)+abs(sy-cy)
                elif model=='via': X=2*(abs(cx-hx)+abs(hx-sx)); Yy=2*(abs(cy-hy)+abs(hy-sy))
                A.append([1,X,Yy]);Y.append(v)
            A=np.array(A,float);Y=np.array(Y)
            if np.linalg.matrix_rank(A)<3: continue
            co=np.linalg.lstsq(A,Y,rcond=None)[0]; r=Y-A@co
            res.append(((r**2).mean()**.5,abs(r).max(),sx,sy,co))
    res.sort(key=lambda t:t[0])
    print(label,model)
    for rms,mx,sx,sy,co in res[:6]: print(f"   SN=({sx},{sy}) a={co[0]:.3f} perXcross={co[1]:.3f} perYcross={co[2]:.3f} rms={rms:.3f} max={mx:.3f}")
tryfit('tri',D,'dram-flush'); tryfit('via',D,'dram-flush')
# OCM-style fit in per-crossing units for comparison: slc round trip = 2 crossings per step
A=[];Y=[]
for (c,n),v in S.items():
    cx,cy=cpos[c];hx,hy=npos[n]; A.append([1,2*abs(cx-hx),2*abs(cy-hy)]);Y.append(v)
co=np.linalg.lstsq(np.array(A,float),np.array(Y),rcond=None)[0]; print("slc per crossing: a=%.3f X=%.3f Y=%.3f"%tuple(co))
# extra = dram-flush - slc
E={k:D[k]-S[k] for k in D}
print("dram-flush minus slc by cpu(row) node(col):")
for c in sorted(cpos): print("  cpu%d "%c+" ".join("%6.2f"%E[(c,n)] for n in nodes))
