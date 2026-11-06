import os, re, glob, math, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
def lat_best(boot, fn, size):
    for r in rows(D[boot]+'/'+fn):
        if r['mode'] == 'best' and int(r['size_bytes']) == size: return float(r['ns_per_load'])
def lat_passes(boot, fn, size=None):
    return [r for r in rows(D[boot]+'/'+fn) if r['mode'] != 'best' and (size is None or int(r['size_bytes']) == size)]
K=1024; M=K*K
# pair.csv
print('pair sizes', sorted(set(int(r['bytes_per_thread']) for r in rows(D['R3']+'/bandwidth-pair.csv'))))
print('pair write bests', [(int(r['bytes_per_thread'])//K, r['aggregate_GBps']) for r in rows(D['R3']+'/bandwidth-pair.csv') if r['rep']=='best' and r['kernel']=='write'])
print('ocm region reads R3', [ (i, [r['aggregate_GBps'] for r in rows(D['R3']+'/bandwidth-ocm-region%d.csv'%i) if r['rep']=='best']) for i in range(5)])
# C l3 file
for s in (192*K,256*K,384*K):
    ps = lat_passes('C','latency-dram-small-l3.csv',s); b=min(ps,key=lambda r: float(r['ns_per_load']))
    print('C l3.csv', s//K, b['ns_per_load'], 'l3hit', b['l3d_hit_rd_per_load'])
# TLB refills per pass (sparse region tlb cpu2), A, C, D
for b in ('A','C','D','E'):
    vals=[]
    for i in range(5):
        for r in lat_passes(b,'latency-ocm-region%d-tlb-cpu2.csv'%i):
            vals.append(round(float(r['l1d_tlb_refill_per_load'])*int(r['loads']),1))
    print('TLB refills per pass', b, 'min', min(vals), 'max', max(vals), 'n', len(vals))
    vals2=[]
    for i in range(5):
        for r in lat_passes(b,'latency-ocm-region%d-vary-tlb-cpu2.csv'%i):
            vals2.append(round(float(r['l1d_tlb_refill_per_load'])*int(r['loads']),1))
    print('   vary-tlb per pass', 'min', min(vals2), 'max', max(vals2))
    vals3=[]
    for i in range(5):
        for r in lat_passes(b,'latency-ocm-region%d-dense-tlb-cpu2.csv'%i):
            vals3.append(round(float(r['l1d_tlb_refill_per_load'])*int(r['loads']),1))
    print('   dense-tlb per pass', 'min', min(vals3), 'max', max(vals3))
# GM ratios of sparse rows C/A and D/B
def gm(xs): return math.exp(sum(math.log(x) for x in xs)/len(xs))
for num,den in (('C','A'),('D','B')):
    rs=[]; names=[]
    for i in range(5):
        for c in (2,8):
            for kind in ('','-vary','-dense','-route'):
                fn='latency-ocm-region%d%s-cpu%d.csv'%(i,kind,c)
                if kind=='-route':
                    for cc in (2,4,6,8):
                        fn2='latency-ocm-region%d-route-cpu%d.csv'%(i,cc)
                        if os.path.exists(D[num]+'/'+fn2) and os.path.exists(D[den]+'/'+fn2):
                            rs.append((kind,cc,lat_best(num,fn2,262144)/lat_best(den,fn2,262144)))
                    continue
                if os.path.exists(D[num]+'/'+fn) and os.path.exists(D[den]+'/'+fn):
                    rs.append((kind,c,lat_best(num,fn,262144)/lat_best(den,fn,262144)))
    for kind in ('','-vary','-dense','-route'):
        xs=[r[2] for r in rs if r[0]==kind]
        if xs: print('GM', num,'/',den, kind or 'sparse', round(gm(xs),3), 'n', len(xs))
    xs=[r[2] for r in rs if r[0] in ('','-vary')]; print('GM sparse+vary', num,'/',den, round(gm(xs),3))
    xs=[r[2] for r in rs if r[0] in ('',) and r[1]==2]; print('GM sparse cpu2', num,'/',den, round(gm(xs),3))
    xs=[r[2] for r in rs]; print('GM all', num,'/',den, round(gm(xs),3))
# Repeatability: boot X vs run 3, same file & size, latency files
def repeat(b):
    diffs=[]
    for p in sorted(glob.glob(D['R3']+'/latency-*.csv')):
        fn=os.path.basename(p); q=D[b]+'/'+fn
        if not os.path.exists(q): continue
        r3={int(r['size_bytes']):float(r['ns_per_load']) for r in rows(p) if r['mode']=='best'}
        rb={int(r['size_bytes']):float(r['ns_per_load']) for r in rows(q) if r['mode']=='best'}
        for s in r3:
            if s in rb: diffs.append((fn,s,(rb[s]/r3[s]-1)*100))
    n=len(diffs); a=[abs(d[2]) for d in diffs]
    print('repeat', b, 'n', n, 'within1', sum(x<=1 for x in a), 'within3', sum(x<=3 for x in a), 'within5', sum(x<=5 for x in a), 'largest', max(diffs,key=lambda d: abs(d[2])))
    return diffs
dA=repeat('A'); dE=repeat('E')
print('E L3 rows', [(d[0],d[1]//K,round(d[2],1)) for d in dE if d[0]=='latency-dram-small.csv' and d[1] in (192*K,256*K,384*K,512*K)])
print('E sorted 6 largest', sorted([(round(d[2],1),d[0],d[1]//K) for d in dE])[:8])
# also including cme files
def repeat_all(b):
    diffs=[]
    for p in sorted(glob.glob(D['R3']+'/*latency-*.csv')):
        fn=os.path.basename(p); q=D[b]+'/'+fn
        if not os.path.exists(q): continue
        r3={int(r['size_bytes']):float(r['ns_per_load']) for r in rows(p) if r['mode'] in ('best','cme-best')}
        rb={int(r['size_bytes']):float(r['ns_per_load']) for r in rows(q) if r['mode'] in ('best','cme-best')}
        for s in r3:
            if s in rb: diffs.append((fn,s,(rb[s]/r3[s]-1)*100))
    a=[abs(d[2]) for d in diffs]
    print('repeat incl cme', b, 'n', len(diffs), 'within1', sum(x<=1 for x in a), 'within5', sum(x<=5 for x in a))
repeat_all('A'); repeat_all('E')
# D walk rates
print('D tlb file walk', [r['dtlb_walk_per_load'] for r in lat_passes('D','latency-dram-tlb-cpu2.csv')], 'walk file', [r['dtlb_walk_per_load'] for r in lat_passes('D','latency-dram-walk-cpu2.csv')])
print('ratio', 0.4381/0.0033, 0.4371/0.0035)
# read fit residual alternatives
def bw_best(boot, fn, kernel, size):
    for r in rows(D[boot]+'/'+fn):
        if r['rep']=='best' and r['kernel']==kernel and int(r['bytes_per_thread'])==size: return float(r['aggregate_GBps'])
for b in ('C','E'):
    for fn in ('bandwidth-l1-asmpasses.csv','bandwidth-l1-passes.csv'):
        xs=[];ys=[]
        for s in (4*K,8*K,16*K,24*K):
            g=bw_best(b,fn,'read',s); xs.append(s); ys.append(s/g)
        n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
        a=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); c=my-a*mx
        res=[((a*x+c)/y-1)*100 for x,y in zip(xs,ys)]
        rms=math.sqrt(sum(r*r for r in res)/n)
        # fit with BW fixed to the marginal rate from 8->16? or to 64.1
        c2=statistics.mean(y-x/64.1 for x,y in zip(xs,ys)); res2=[((x/64.1+c2)/y-1)*100 for x,y in zip(xs,ys)]
        print('read fit', b, fn, 'res per point', [round(r,2) for r in res], 'rms', round(rms,2), '| BW fixed 64.1: c', round(c2,2), 'res', [round(r,2) for r in res2])
