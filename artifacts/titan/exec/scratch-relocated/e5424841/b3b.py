import sys; sys.path.insert(0,'/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/e5424841-ab73-4e33-aa57-48b09daa261f/scratchpad')
from b3 import *
def M1(k,c,n):  # boot1 fit for ocm-evict
    dx,dy=steps(c,n); return 20.61+2.00*dx+1.00*dy
for b in (2,3):
  o=B[b]
  for k in KINDS:
    X=[];y=[]
    for c in C29:
        for n in NODES:
            for r in o.cells[(k,c,n)]:
                f=float(r[o.H['l3d_refill_rd']]); X.append([1-f,f,f*sum(steps(c,n)[i]*w for i,w in enumerate((2,1)))]); y.append(float(r[o.H['ns_per_load']]))
    X=np.array(X);y=np.array(y)
    if np.linalg.matrix_rank(X)<3: print(b,k,'rank deficient'); continue
    co=np.linalg.lstsq(X,y,rcond=None)[0]; res=y-X@co
    print('boot',b,k,'ns = %.2f*(1-f) + f*(%.2f + %.2f*(2X+Y))  rms %.2f n=%d  corr(ns,f)=%.2f'%(*co,(res**2).mean()**.5,len(y),np.corrcoef(y,X[:,1])[0,1]))
  # f by rep
  for k in KINDS:
    print('  ',k,'l3d_refill_rd mean by rep',' '.join('%.2f'%np.mean([o.col(k,c,n,'l3d_refill_rd')[r] for c in C29 for n in NODES]) for r in range(7)),
          '| ns by rep',' '.join('%.2f'%np.mean([o.col(k,c,n,'ns_per_load')[r] for c in C29 for n in NODES]) for r in range(7)))
  for k in ('ocm-evict','slc'):
    print('  ',k,'cell-median f:')
    for c in [2,4,6,8,3,5,7,9]: print('     cpu',c,' '.join('%.2f'%o.med(k,c,n,'l3d_refill_rd') for n in NODES),'| l2hwprf',' '.join('%.2f'%o.med(k,c,n,'l2d_refill_hwprf') for n in NODES))
# three-leg on each boot
def tri(c,n,m):
    (cx,cy),(hx,hy)=CPOS[c],NPOS[n]; return (abs(cx-hx)+abs(hx-m[0])+abs(m[0]-cx),abs(cy-hy)+abs(hy-m[1])+abs(m[1]-cy))
for b in (1,2,3):
    o=B[b]; y=np.array([o.best('dram-flush',c,n) for c in C29 for n in NODES]); out=[]
    for mx in range(6):
        for my in range(6):
            A=np.array([[1,*tri(c,n,(mx,my))] for c in C29 for n in NODES],float)
            if np.linalg.matrix_rank(A)<3: continue
            co=np.linalg.lstsq(A,y,rcond=None)[0]; r=y-A@co; out.append(((r**2).mean()**.5,(mx,my),co))
    out.sort(key=lambda t:t[0]); print('boot',b,'tri best',[(round(a,3),m,np.round(co,3)) for a,m,co in out[:3]])
# partner agreement, slc-evict per boot, mc_reqs cell medians
for b in (1,2,3):
    o=B[b]
    for k in KINDS:
        d=[o.best(k,c,n)-o.best(k,c+1,n) for c in (2,4,6,8) for n in NODES]
        print('boot',b,k,'partner diff even-odd mean %+.2f max|%.2f|'%(np.mean(d),max(map(abs,d))), 'mc_reqs cell med range %.4f..%.4f'%(min(o.med(k,c,n,'mc_reqs') for c in C29 for n in NODES),max(o.med(k,c,n,'mc_reqs') for c in C29 for n in NODES)) if k!='ocm-flush' else '')
    d=[o.best('slc',c,n)-o.best('ocm-evict',c,n) for c in C29 for n in NODES]; print('  slc-evict mean %+.3f range %+.2f..%+.2f'%(np.mean(d),min(d),max(d)))
    hw=[(sum(1 for r in o.rows if r[0]!='idle' and (r[1]=='0')==z and (float(r[o.H['l1d_refill_hwprf']])>0 or float(r[o.H['l2d_refill_hwprf']])>0))) for z in (True,False)]; print('  hwprf rows cpu0, cpu2-9:',hw)
    print('  idle rows:'); 
    for r in o.rows:
        if r[0]=='idle': print('    ',','.join(r)[:200]); break
# boot2 ocm-flush: quantization
o=B[2]; print(sorted(set(round(o.med('ocm-flush',c,n),2) for c in C29 for n in NODES)))
o=B[1]; print(sorted(set(round(o.med('ocm-flush',c,n),2) for c in C29 for n in NODES)))
# dram-flush boot2-boot1 by cell
d=[B[2].best('dram-flush',c,n)-B[1].best('dram-flush',c,n) for c in C29 for n in NODES]; print('dram b2-b1',np.round(d,2))
# boot 3 l2 hwprf by kind and cpu parity
o=B[3]
for k in KINDS:
    for par in (0,1):
        cs=[c for c in C29 if c%2==par]
        print('boot3',k,'parity',par,'ns best mean %.2f med mean %.2f l3rd %.2f l2hwprf %.2f'%(np.mean([o.best(k,c,n) for c in cs for n in NODES]),np.mean([o.med(k,c,n) for c in cs for n in NODES]),np.mean([o.med(k,c,n,'l3d_refill_rd') for c in cs for n in NODES]),np.mean([o.med(k,c,n,'l2d_refill_hwprf') for c in cs for n in NODES])))
