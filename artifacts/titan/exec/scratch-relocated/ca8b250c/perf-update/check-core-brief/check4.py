import os, math, statistics
R = '/home/jhan/workspace/titan/cache-perf/asimov/results'
D = {'E': R+'/membench-jibin-010/results/bootE', 'C': R+'/membench-jibin-007/results/bootC',
     'A': R+'/membench-jibin-005/results/bootA', 'B': R+'/membench-jibin-006/results/bootB',
     'D': R+'/membench-jibin-008/results/bootD'}
def rows(path):
    out = []; hdr = None
    for ln in open(path):
        ln = ln.strip()
        if not ln or ln.startswith('#'): continue
        f = ln.split(',')
        if f[0] == 'mem': hdr = f; continue
        out.append({k: f[i] for i, k in enumerate(hdr) if i < len(f)})
    return out
K=1024
# mesh constants (platform facts from sysinfo mesh map, copied from the generator's constants, not imported)
NODES = {88: (1, 3, 0), 160: (2, 4, 1), 216: (3, 3, 2), 288: (4, 4, 3), 344: (5, 3, 4)}
DSUS = {1: (2, 3), 2: (3, 2), 3: (4, 3), 4: (5, 2)}
CPU_DSU = {2: 1, 4: 2, 6: 3, 8: 4}
NODE_OF_REGION = {r: n for n, (x, y, r) in NODES.items()}
def fit3(cells):
    # least squares ns = a + bx*|dx| + by*|dy|
    import itertools
    n=len(cells)
    X=[[1,c[0],c[1]] for c in cells]; y=[c[2] for c in cells]
    # normal equations
    XtX=[[sum(X[k][i]*X[k][j] for k in range(n)) for j in range(3)] for i in range(3)]
    Xty=[sum(X[k][i]*y[k] for k in range(n)) for i in range(3)]
    # solve 3x3
    def solve(A,b):
        A=[r[:] for r in A]; b=b[:]
        for i in range(3):
            p=max(range(i,3),key=lambda r: abs(A[r][i])); A[i],A[p]=A[p],A[i]; b[i],b[p]=b[p],b[i]
            for r in range(i+1,3):
                f=A[r][i]/A[i][i]
                for c in range(i,3): A[r][c]-=f*A[i][c]
                b[r]-=f*b[i]
        x=[0]*3
        for i in (2,1,0):
            x[i]=(b[i]-sum(A[i][c]*x[c] for c in range(i+1,3)))/A[i][i]
        return x
    a,bx,by=solve(XtX,Xty)
    rms=math.sqrt(sum((a+bx*c[0]+by*c[1]-c[2])**2 for c in cells)/n)
    return a,bx,by,rms
for boot in ('B','D','A','C','E'):
    for stat in ('best','median'):
        cells=[]
        for c in (2,4,6,8):
            for r in range(5):
                ps=[float(x['ns_per_load']) for x in rows(D[boot]+'/latency-ocm-region%d-route-cpu%d.csv'%(r,c)) if x['mode']!='best']
                v=min(ps) if stat=='best' else statistics.median(ps)
                dx=abs(DSUS[CPU_DSU[c]][0]-NODES[NODE_OF_REGION[r]][0]); dy=abs(DSUS[CPU_DSU[c]][1]-NODES[NODE_OF_REGION[r]][1])
                cells.append((dx,dy,v))
        a,bx,by,rms=fit3(cells)
        print('route fit', boot, stat, 'a %.2f bx %.2f by %.2f rms %.2f'%(a,bx,by,rms))
# G8 residual relative to the smallest pass time
def bw_best(boot, fn, kernel, size):
    for r in rows(D[boot]+'/'+fn):
        if r['rep']=='best' and r['kernel']==kernel and int(r['bytes_per_thread'])==size: return float(r['aggregate_GBps'])
for kern in ('read','write'):
  res_all=[]
  for b in ('C','E'):
    for fn in ('bandwidth-l1-asmpasses.csv','bandwidth-l1-passes.csv'):
        xs=[];ys=[]
        for s in (4*K,8*K,16*K,24*K):
            g=bw_best(b,fn,kern,s); xs.append(s); ys.append(s/g)
        n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
        a=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); c=my-a*mx
        res=max(abs(a*x+c-y) for x,y in zip(xs,ys))/min(ys)*100
        res_all.append(res)
        print('G8 fit', kern, b, fn, 'rate %.1f fixed %.1f ns  largest residual / smallest pass time %.1f %%'%(1/a,c,res))
  print('  ', kern, 'residual range %.1f to %.1f'%(min(res_all),max(res_all)))
