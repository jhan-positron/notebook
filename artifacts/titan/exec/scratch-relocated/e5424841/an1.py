import csv, sys, statistics as st, itertools
import numpy as np
f = sys.argv[1]
rows = [r for r in csv.reader(l for l in open(f) if not l.startswith('#'))]
hdr = rows[0]; rows = rows[1:]
H = {n:i for i,n in enumerate(hdr)}
nodes = [88,160,216,288,344]
npos = {88:(1,3),160:(2,4),216:(3,3),288:(4,4),344:(5,3)}
cpos = {0:(1,2),1:(1,2),2:(2,3),3:(2,3),4:(3,2),5:(3,2),6:(4,3),7:(4,3),8:(5,2),9:(5,2)}
cells = {}
for r in rows:
    if r[0]=='idle': continue
    cells.setdefault((r[0],int(r[1]),int(r[2])),[]).append(r)
def col(rs,name): return [float(r[H[name]]) for r in rs]
kinds = ['ocm-flush','slc','ocm-evict','dram-flush']
cpus = sorted({k[1] for k in cells})
print("passes per cell:", sorted({len(v) for v in cells.values()}), "cells:", len(cells))
print("perf_cov != 1:", sum(1 for r in rows if r[H['perf_cov']]!='1.0000'))
for k in kinds:
    print(f"\n== {k}: best (min of 7) ns | median ns | spread max-min")
    for c in cpus:
        b=[min(col(cells[(k,c,n)],'ns_per_load')) for n in nodes]
        m=[st.median(col(cells[(k,c,n)],'ns_per_load')) for n in nodes]
        s=[max(col(cells[(k,c,n)],'ns_per_load'))-min(col(cells[(k,c,n)],'ns_per_load')) for n in nodes]
        print(f"cpu{c} "+" ".join(f"{x:7.3f}" for x in b)+" | "+" ".join(f"{x:7.3f}" for x in m)+" | "+" ".join(f"{x:5.2f}" for x in s))
# fits (CPUs 2-9), best and median
def fit(k, cs, stat):
    A=[];y=[]
    for c in cs:
        for n in nodes:
            dx=abs(cpos[c][0]-npos[n][0]); dy=abs(cpos[c][1]-npos[n][1])
            A.append([1,dx,dy]); y.append(stat(col(cells[(k,c,n)],'ns_per_load')))
    A=np.array(A);y=np.array(y)
    co,_,_,_=np.linalg.lstsq(A,y,rcond=None)
    res=y-A@co
    return co, (res**2).mean()**.5, abs(res).max()
print("\n== fit ns = a + b*Xsteps + c*Ysteps")
for k in kinds:
    for nm,cs in (("cpus2-9",[c for c in cpus if c>=2]),("cpus2,4,6,8",[2,4,6,8]),("cpus3,5,7,9",[3,5,7,9])):
        for sn,sf in (("best",min),("median",st.median)):
            co,rms,mx=fit(k,cs,sf)
            print(f"{k:10s} {nm:12s} {sn:6s} a={co[0]:.3f} b={co[1]:.3f} c={co[2]:.3f} rms={rms:.3f} maxres={mx:.3f}")
# old fit vs new ocm-flush
print("\n== ocm-flush best minus old fit (20.75+1.99x+0.95y)")
for c in cpus:
    out=[]
    for n in nodes:
        dx=abs(cpos[c][0]-npos[n][0]); dy=abs(cpos[c][1]-npos[n][1])
        out.append(min(col(cells[('ocm-flush',c,n)],'ns_per_load'))-(20.75+1.99*dx+0.95*dy))
    print(f"cpu{c} "+" ".join(f"{x:+6.2f}" for x in out))
# slc vs ocm-evict vs ocm-flush
print("\n== slc minus ocm-evict (best) ; slc minus ocm-flush (best)")
d1=[];d2=[]
for c in cpus:
    a=[min(col(cells[('slc',c,n)],'ns_per_load'))-min(col(cells[('ocm-evict',c,n)],'ns_per_load')) for n in nodes]
    b=[min(col(cells[('slc',c,n)],'ns_per_load'))-min(col(cells[('ocm-flush',c,n)],'ns_per_load')) for n in nodes]
    if c>=2: d1+=a; d2+=b
    print(f"cpu{c} "+" ".join(f"{x:+6.3f}" for x in a)+" ; "+" ".join(f"{x:+6.3f}" for x in b))
print("cpus2-9 slc-evict mean %.3f min %.3f max %.3f rms %.3f"%(np.mean(d1),min(d1),max(d1),np.sqrt(np.mean(np.square(d1)))))
print("cpus2-9 slc-flush mean %.3f min %.3f max %.3f"%(np.mean(d2),min(d2),max(d2)))
print("\n== dram-flush minus slc (best)")
d3=[]
for c in cpus:
    a=[min(col(cells[('dram-flush',c,n)],'ns_per_load'))-min(col(cells[('slc',c,n)],'ns_per_load')) for n in nodes]
    if c>=2: d3+=a
    print(f"cpu{c} "+" ".join(f"{x:+7.3f}" for x in a))
print("cpus2-9 mean %.3f min %.3f max %.3f"%(np.mean(d3),min(d3),max(d3)))
# routing: req own - mean others; sums
print("\n== counters per load, range over cells of cpus 2-9 (median of 7 passes per cell)")
for k in kinds[1:]:
    own=[];oth=[];mc=[];cm=[];sn=[];l3=[];hw=[]
    for c in cpus:
        if c<2: continue
        for n in nodes:
            rs=cells[(k,c,n)]
            o=st.median(col(rs,'req_%d'%n)); ot=np.mean([st.median(col(rs,'req_%d'%m)) for m in nodes if m!=n])
            own.append(o-ot); oth.append(ot)
            mc.append(st.median(col(rs,'mc_reqs'))); cm.append(st.median(col(rs,'cache_miss'))); sn.append(st.median(col(rs,'snp_sent')))
            l3.append(st.median(col(rs,'l3d_refill_rd'))); hw.append(max(col(rs,'l1d_refill_hwprf')+col(rs,'l2d_refill_hwprf')))
    r=lambda v:f"{min(v):.4f}..{max(v):.4f}"
    print(f"{k:10s} own-others {r(own)} others {r(oth)} mc_reqs {r(mc)} cache_miss {r(cm)} snp_sent {r(sn)} l3d_refill_rd {r(l3)} hwprf max {max(hw):.4f}")
k='ocm-flush'
l3=[st.median(col(cells[(k,c,n)],'l3d_refill_rd')) for c in cpus if c>=2 for n in nodes]
print("ocm-flush l3d_refill_rd", min(l3), max(l3))
# worst-case per-pass check for slc: any pass with mc_reqs high
print("\n== slc passes with mc_reqs > 0.05:", sum(1 for (k,c,n),rs in cells.items() if k=='slc' for x in col(rs,'mc_reqs') if x>0.05), "of", sum(len(rs) for (k,c,n),rs in cells.items() if k=='slc'))
print("slc max mc_reqs any pass:", max(x for (k,c,n),rs in cells.items() if k=='slc' for x in col(rs,'mc_reqs')))
print("dram-flush min mc_reqs any pass:", min(x for (k,c,n),rs in cells.items() if k=='dram-flush' for x in col(rs,'mc_reqs')))
print("ocm-evict max mc_reqs any pass:", max(x for (k,c,n),rs in cells.items() if k=='ocm-evict' for x in col(rs,'mc_reqs')))
print("\n== idle rows")
for r in rows:
    if r[0]=='idle': print(",".join(r))
# cpu0 state
print("\n== cpu0: l3d_refill_rd median per kind/node; hwprf")
if 0 in cpus:
  for k in kinds:
    print(k, " ".join(f"{st.median(col(cells[(k,0,n)],'l3d_refill_rd')):.3f}" for n in nodes), "| l2hwprf", " ".join(f"{st.median(col(cells[(k,0,n)],'l2d_refill_hwprf')):.3f}" for n in nodes))
