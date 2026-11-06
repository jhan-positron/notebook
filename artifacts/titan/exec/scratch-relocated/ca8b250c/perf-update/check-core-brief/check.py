import os, re, glob, math, statistics
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
        d = {}
        for i, k in enumerate(hdr):
            if i < len(f): d[k] = f[i]
        out.append(d)
    return out

def lat_best(boot, fn, size):
    for r in rows(D[boot]+'/'+fn):
        if r['mode'] == 'best' and int(r['size_bytes']) == size: return float(r['ns_per_load'])
def lat_passes(boot, fn, size=None):
    return [r for r in rows(D[boot]+'/'+fn) if r['mode'] != 'best' and (size is None or int(r['size_bytes']) == size)]
def bw_best(boot, fn, kernel, size, threads=None):
    for r in rows(D[boot]+'/'+fn):
        if r['rep'] == 'best' and r['kernel'] == kernel and int(r['bytes_per_thread']) == size and (threads is None or int(r['threads']) == threads):
            return float(r['aggregate_GBps'])
def bw_reps(boot, fn, kernel, size):
    return [r for r in rows(D[boot]+'/'+fn) if r['rep'] != 'best' and r['kernel'] == kernel and int(r['bytes_per_thread']) == size]

K = 1024; M = 1024*1024
print('== Short version / table')
print('L1 4K E', lat_best('E','latency-dram-small.csv',4*K), 'R3', lat_best('R3','latency-dram-small.csv',4*K))
print('L2 128K E', lat_best('E','latency-dram-small.csv',128*K), 'R3', lat_best('R3','latency-dram-small.csv',128*K))
for s in (192*K,256*K,384*K):
    print('small.csv', s//K, 'E', lat_best('E','latency-dram-small.csv',s), 'R3', lat_best('R3','latency-dram-small.csv',s), 'C', lat_best('C','latency-dram-small.csv',s))
# hit set
def l3row(boot, s):
    ps = lat_passes(boot,'latency-dram-small-l3.csv',s)
    b = min(ps, key=lambda r: float(r['ns_per_load']))
    return b
for s in (64*K,96*K,128*K,192*K,256*K,384*K,512*K):
    b = l3row('E', s)
    print('l3.csv E', s//K, 'best', b['ns_per_load'], 'l3hit', b['l3d_hit_rd_per_load'], 'l2hit', b['l2d_hit_rd_per_load'], 'l3refill', b['l3d_refill_rd_per_load'])
# L3 hit est: (ns - l2hit*t128 - l3refill*tC384) / l3hit
t128 = lat_best('E','latency-dram-small.csv',128*K); tC384 = lat_best('C','latency-dram-small.csv',384*K)
for s in (192*K,256*K,384*K):
    b = l3row('E', s)
    est = (float(b['ns_per_load']) - float(b['l2d_hit_rd_per_load'])*t128 - float(b['l3d_refill_rd_per_load'])*tC384)/float(b['l3d_hit_rd_per_load'])
    print('L3 hit est', s//K, round(est,3))
print('SLC 2M E', lat_best('E','latency-dram-large.csv',2*M), 'R3', lat_best('R3','latency-dram-large.csv',2*M), 'C', lat_best('C','latency-dram-large.csv',2*M))
print('32M E', lat_best('E','latency-dram-large.csv',32*M), 'R3', lat_best('R3','latency-dram-large.csv',32*M), 'C', lat_best('C','latency-dram-large.csv',32*M))
print('16M E', lat_best('E','latency-dram-large.csv',16*M), 'C', lat_best('C','latency-dram-large.csv',16*M))
print('flushed 8M E', lat_best('E','latency-dram-flushed.csv',8*M), 'R3', lat_best('R3','latency-dram-flushed.csv',8*M), 'C', lat_best('C','latency-dram-flushed.csv',8*M))
print('seq 8M E', lat_best('E','latency-dram-seq.csv',8*M), 'C', lat_best('C','latency-dram-seq.csv',8*M), 'B', lat_best('B','latency-dram-seq.csv',8*M))
for r in lat_passes('E','latency-dram-seq.csv'): print('  seq pass', r['mode'], r['ns_per_load'], 'l1 hwprf', r['l1d_refill_hwprf_per_load'])
print('B flushed 8M', lat_best('B','latency-dram-flushed.csv',8*M), 'B seq passes', [r['ns_per_load'] for r in lat_passes('B','latency-dram-seq.csv')], 'B flushed passes', [r['ns_per_load'] for r in lat_passes('B','latency-dram-flushed.csv')])
# OCM
for b in ('E','A','C','B','D','R3'):
    print('all5 dense cpu2', b, lat_best(b,'latency-ocm-all5-dense-cpu2.csv',1310720), 'cpu8', lat_best(b,'latency-ocm-all5-dense-cpu8.csv',1310720))
for c in (4,6): print('R3 all5 dense cpu', c, lat_best('R3','latency-ocm-all5-dense-cpu%d.csv'%c,1310720))
for r in lat_passes('E','latency-ocm-all5-dense-cpu2.csv'): print('  E all5 dense pass', r['mode'], r['ns_per_load'], 'l3refill', r['l3d_refill_rd_per_load'])
sp = {}
for b in ('E','R3','A','C'):
    v = [lat_best(b,'latency-ocm-region%d-cpu2.csv'%i,262144) for i in range(5)]
    sp[b] = v
    print('sparse cpu2', b, v, 'range', min(v), max(v))
    # l3 refill per hop pass means
    means = []
    for i in range(5):
        ps = lat_passes(b,'latency-ocm-region%d-cpu2.csv'%i,262144)
        means.append(statistics.mean(float(r['l3d_refill_rd_per_load']) for r in ps))
    print('   l3refill pass means', [round(m,3) for m in means])
# five boots all5 dense cpu2 range
print('five-boot all5 dense cpu2 range', min(lat_best(b,'latency-ocm-all5-dense-cpu2.csv',1310720) for b in 'EABCD'), max(lat_best(b,'latency-ocm-all5-dense-cpu2.csv',1310720) for b in 'EABCD'))
# L2 hit at 128K hit set
b = l3row('E',128*K); print('128K hit set l2hit', b['l2d_hit_rd_per_load'])

print('== Bandwidth')
print('R3 read 16K', bw_best('R3','bandwidth-dram-1core.csv','read',16*K), 'write 32M', bw_best('R3','bandwidth-dram-1core.csv','write',32*M), 'read 32M', bw_best('R3','bandwidth-dram-1core.csv','read',32*M), 'copy 32M', bw_best('R3','bandwidth-dram-1core.csv','copy',32*M))
wr = [r for r in rows(D['R3']+'/bandwidth-dram-1core.csv') if r['rep']=='best' and r['kernel']=='write']
print('R3 write all sizes', [(int(r['bytes_per_thread'])//K, r['aggregate_GBps']) for r in wr])
print('E asm read', [(s//K, bw_best('E','bandwidth-l1-asmpasses.csv','read',s)) for s in (4*K,8*K,16*K,24*K)])
print('C asm read', [(s//K, bw_best('C','bandwidth-l1-asmpasses.csv','read',s)) for s in (4*K,8*K,16*K,24*K)])
print('E passes read', [(s//K, bw_best('E','bandwidth-l1-passes.csv','read',s)) for s in (4*K,8*K,16*K,24*K)])
print('C passes read', [(s//K, bw_best('C','bandwidth-l1-passes.csv','read',s)) for s in (4*K,8*K,16*K,24*K)])
print('E read-prefetch', [(k, s//M, bw_best('E','bandwidth-read-prefetch.csv',k,s)) for s in (2*M,32*M) for k in ('read','read-pf4','read-pf8')])
print('C read-prefetch', [(k, s//M, bw_best('C','bandwidth-read-prefetch.csv',k,s)) for s in (2*M,32*M) for k in ('read','read-pf4','read-pf8')])
print('R3 pair write 16M', bw_best('R3','bandwidth-pair.csv','write',16*M), 'perdsu write 16M', bw_best('R3','bandwidth-perdsu.csv','write',16*M))
print('R3 all8 write 16M', bw_best('R3','bandwidth-all8.csv','write',16*M), 'read 16M', bw_best('R3','bandwidth-all8.csv','read',16*M), 'write 2M', bw_best('R3','bandwidth-all8.csv','write',2*M), 'read 2M', bw_best('R3','bandwidth-all8.csv','read',2*M))
print('R3 ocm region0 read', bw_best('R3','bandwidth-ocm-region0.csv','read',262144), 'regions', [bw_best('R3','bandwidth-ocm-region%d.csv'%i,'read',262144) for i in range(5)], '4core', bw_best('R3','bandwidth-ocm-4core.csv','read',262144), 'write', bw_best('R3','bandwidth-ocm-write.csv','write',1310720))
print('limits: 64.1?', 2*16*2.0, 'write', 16*2.0, 'asm 24K E / 64', bw_best('E','bandwidth-l1-asmpasses.csv','read',24*K)/64.0, 'R3 16K/64', bw_best('R3','bandwidth-dram-1core.csv','read',16*K)/64.0)
print('24.5/9.2 ratio', bw_best('E','bandwidth-read-prefetch.csv','read',32*M)/bw_best('R3','bandwidth-dram-1core.csv','read',32*M))
pf4C = bw_best('C','bandwidth-read-prefetch.csv','read-pf4',32*M); rC = bw_best('C','bandwidth-read-prefetch.csv','read',32*M)
print('C pf4 vs read 32M %', (pf4C/rC-1)*100, '2M', (bw_best('C','bandwidth-read-prefetch.csv','read-pf4',2*M)/bw_best('C','bandwidth-read-prefetch.csv','read',2*M)-1)*100)
# marginal rate 8->16K asm and passes
for b in ('C','E'):
    for fn in ('bandwidth-l1-asmpasses.csv','bandwidth-l1-passes.csv'):
        t8 = 8*K/bw_best(b,fn,'read',8*K); t16 = 16*K/bw_best(b,fn,'read',16*K)
        print('marginal 8->16K', b, fn, round(8*K/(t16-t8),2))
# write per-pass fit: t_pass(bytes) = bytes/BW + c; fit linear
for b in ('C','E'):
    for fn in ('bandwidth-l1-asmpasses.csv','bandwidth-l1-passes.csv'):
        for kern in ('write','read'):
            xs=[];ys=[]
            for s in (4*K,8*K,16*K,24*K):
                g = bw_best(b,fn,kern,s)
                if g is None: continue
                xs.append(s); ys.append(s/g)  # ns per pass (bytes / GB/s = ns)
            n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
            a=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); c=my-a*mx
            res=max(abs((a*x+c)/y-1) for x,y in zip(xs,ys))
            print('fit', b, fn, kern, 'BW', round(1/a,2), 'GB/s per-pass', round(c,2), 'ns maxres %', round(res*100,2))
