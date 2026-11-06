import os, re, glob, math, statistics, itertools, html
R = '/home/jhan/workspace/titan/cache-perf/asimov/results'
D = {'E': R+'/membench-jibin-010/results/bootE', 'C': R+'/membench-jibin-007/results/bootC',
     'A': R+'/membench-jibin-005/results/bootA', 'B': R+'/membench-jibin-006/results/bootB',
     'D': R+'/membench-jibin-008/results/bootD', 'R3': R+'/membench-jibin-004/results/19700101T000000Z'}
def rows(path):
    out = []; hdr = None
    for ln in open(path):
        ln = ln.strip()
        if not ln or ln.startswith('#'): continue
        f = ln.split(',')
        if f[0] == 'mem': hdr = f; continue
        out.append({k: f[i] for i, k in enumerate(hdr) if i < len(f)})
    return out
def lat_best(boot, fn, size=None):
    for r in rows(D[boot]+'/'+fn):
        if r['mode'] == 'best' and (size is None or int(r['size_bytes']) == size): return float(r['ns_per_load'])
def lat_passes(boot, fn, size=None):
    return [r for r in rows(D[boot]+'/'+fn) if r['mode'] != 'best' and (size is None or int(r['size_bytes']) == size)]
K=1024; M=K*K
def gm(xs): return math.exp(sum(math.log(x) for x in xs)/len(xs))
# 1. GM subsets
forms = {'sparse': ['latency-ocm-region%d-cpu%d.csv'%(i,c) for i in range(5) for c in (2,8)],
         'vary': ['latency-ocm-region%d-vary-cpu%d.csv'%(i,c) for i in range(5) for c in (2,8)],
         'dense': ['latency-ocm-region%d-dense-cpu%d.csv'%(i,c) for i in range(5) for c in (2,8)],
         'route': ['latency-ocm-region%d-route-cpu%d.csv'%(i,c) for i in range(5) for c in (2,4,6,8)],
         'all5s': ['latency-ocm-all5-cpu%d.csv'%c for c in (2,8)],
         'all5d': ['latency-ocm-all5-dense-cpu%d.csv'%c for c in (2,8)],
         'tlb': ['latency-ocm-region%d-tlb-cpu2.csv'%i for i in range(5)],
         'vtlb': ['latency-ocm-region%d-vary-tlb-cpu2.csv'%i for i in range(5)],
         'dtlb': ['latency-ocm-region%d-dense-tlb-cpu2.csv'%i for i in range(5)]}
def ratio(num, den, fns, med=False):
    xs=[]
    for fn in fns:
        if med:
            a=statistics.median(float(r['ns_per_load']) for r in lat_passes(num,fn)); b=statistics.median(float(r['ns_per_load']) for r in lat_passes(den,fn))
        else:
            a=lat_best(num,fn); b=lat_best(den,fn)
        xs.append(a/b)
    return gm(xs)
names=list(forms)
hits=[]
for n in range(1,len(names)+1):
    for sub in itertools.combinations(names,n):
        fns=sum((forms[s] for s in sub),[])
        for med in (False,True):
            ca=ratio('C','A',fns,med); db=ratio('D','B',fns,med)
            if abs(ca-0.977)<0.0015 and abs(db-0.985)<0.0015: hits.append((sub,med,round(ca,4),round(db,4)))
print('GM subsets matching 0.977/0.985:', hits[:10])
for s in ('sparse','vary','dense','route','all5s','all5d'):
    print(' ', s, 'best C/A', round(ratio('C','A',forms[s]),3), 'D/B', round(ratio('D','B',forms[s]),3), '| median C/A', round(ratio('C','A',forms[s],True),3), 'D/B', round(ratio('D','B',forms[s],True),3))
# cpu2-only sparse+vary+dense
fns=[f for s in ('sparse','vary','dense') for f in forms[s] if 'cpu2' in f]
print('  cpu2 sparse+vary+dense best C/A', round(ratio('C','A',fns),3), 'D/B', round(ratio('D','B',fns),3), 'median', round(ratio('C','A',fns,True),3), round(ratio('D','B',fns,True),3))
# 2. repeat rows
diffs=[]
for p in sorted(glob.glob(D['R3']+'/*latency-*.csv')):
    fn=os.path.basename(p); q=D['A']+'/'+fn
    if not os.path.exists(q): continue
    r3={int(r['size_bytes']):float(r['ns_per_load']) for r in rows(p) if r['mode'] in ('best','cme-best')}
    rb={int(r['size_bytes']):float(r['ns_per_load']) for r in rows(q) if r['mode'] in ('best','cme-best')}
    for s in r3:
        if s in rb: diffs.append((fn,s))
from collections import Counter
print('repeat files:', Counter(d[0] for d in diffs))
# 3. chart series
E=[(int(r['size_bytes']),float(r['ns_per_load'])) for r in rows(D['E']+'/latency-dram-small.csv') if r['mode']=='best']+[(int(r['size_bytes']),float(r['ns_per_load'])) for r in rows(D['E']+'/latency-dram-large.csv') if r['mode']=='best']
R3=[(int(r['size_bytes']),float(r['ns_per_load'])) for r in rows(D['R3']+'/latency-dram-small.csv') if r['mode']=='best']+[(int(r['size_bytes']),float(r['ns_per_load'])) for r in rows(D['R3']+'/latency-dram-large.csv') if r['mode']=='best']
t=open('/home/jhan/workspace/titan/cache-perf/asimov/asimov-c1nano-perf-brief.html').read()
titles=re.findall(r'<title>(.*?)</title>', t)
def lab(s):
    return ('%d KiB'%(s//K)) if s<M else (('%g MiB'%(s/M)))
bad=[]
for name,ser in (('boot E',E),('run 3',R3)):
    for s,v in ser:
        want=[x for x in titles if x.startswith(lab(s)+' ') and name in x]
        if not want or not any(('%.3f ns'%v) in x for x in want): bad.append((name,s,v,want))
print('chart series mismatches:', bad, 'n E', len(E), 'n R3', len(R3))
# 4. read fit variants: GB/s-space least squares via 1/G = a/bytes + 1/rate -> linear in 1/bytes
def bw_rows(boot, fn, kernel, size): return [r for r in rows(D[boot]+'/'+fn) if r['kernel']==kernel and int(r['bytes_per_thread'])==size and r['rep']!='best']
def bw_best(boot, fn, kernel, size):
    for r in rows(D[boot]+'/'+fn):
        if r['rep']=='best' and r['kernel']==kernel and int(r['bytes_per_thread'])==size: return float(r['aggregate_GBps'])
for kern in ('read','write'):
  for b in ('C','E'):
    for fn in ('bandwidth-l1-asmpasses.csv','bandwidth-l1-passes.csv'):
        sizes=(4*K,8*K,16*K,24*K)
        # variant A: all reps, t_pass vs bytes
        xs=[];ys=[]
        for s in sizes:
            for r in bw_rows(b,fn,kern,s): xs.append(s); ys.append(s/float(r['aggregate_GBps']))
        n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
        a=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); c=my-a*mx
        resA=max(abs((a*x+c)/y-1) for x,y in zip(xs,ys))*100
        # variant B: median reps
        xs=[];ys=[]
        for s in sizes:
            xs.append(s); ys.append(s/statistics.median(float(r['aggregate_GBps']) for r in bw_rows(b,fn,kern,s)))
        n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
        a=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); c=my-a*mx
        resB=max(abs((a*x+c)/y-1) for x,y in zip(xs,ys))*100
        # variant C: fit elapsed_s per pass using elapsed_s/passes with best rep
        print('fit variants', kern, b, fn, 'allreps maxres %.2f' % resA, 'median maxres %.2f' % resB, 'rate', round(1/a,2), 'c', round(c,2))
