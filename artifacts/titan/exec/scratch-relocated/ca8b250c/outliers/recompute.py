import re, glob, statistics
R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
def rows(path):
    out=[]; header=''; meta={}
    for n,line in enumerate(open(path),1):
        line=line.rstrip('\n')
        if line.startswith('# latency:'): meta=dict(re.findall(r"(\w+)=(\S+)",line)); continue
        if line.startswith('mem,'): header=line.split(','); continue
        if line.startswith('#') or not line: continue
        f=line.split(',')
        if f[3]=='-': continue
        d=dict(zip(header,f)); d['_line']=n; d['_file']=path
        for k in header[5:]:
            d[k]=None if d[k]=='-' else float(d[k])
        d['size_bytes']=int(d['size_bytes']); out.append(d)
    return out
# 1. run 3: timed CME load rows with zero inner
timed=0; zero=[]
for f in sorted(glob.glob(R+'membench-jibin-004/results/19700101T000000Z/cme-latency-*.csv')):
    for d in rows(f):
        if 'roundtrip' in d['mode'] or 'call' in d['mode']: continue
        timed+=1
        assert d['cme_l1d_refill_outer_per_load']>0
        if d['cme_l1d_refill_inner_per_load']==0.0: zero.append((f.split('/')[-1],d['_line'],d['mode'],d['size_bytes']))
print('run3 timed CME load rows',timed,'zero inner',len(zero))
for z in zero: print('  ',z)
# sparse OCM passes: outer refills per load in run 3
ou=[]
for r in range(5):
    for d in rows(R+f'membench-jibin-004/results/19700101T000000Z/cme-latency-ocm-region{r}.csv'):
        if 'fresh' in d['mode']: ou.append(d['cme_l1d_refill_outer_per_load'])
for d in rows(R+'membench-jibin-004/results/19700101T000000Z/cme-latency-ocm-all5.csv'):
    if 'fresh' in d['mode']: ou.append(d['cme_l1d_refill_outer_per_load'])
print('run3 sparse OCM passes outer per load: min %.4f max %.4f n=%d'%(min(ou),max(ou),len(ou)))
# 2. boots A, C, E: cme-latency-dram-small.csv inner/outer at sizes; best rep and mean
def small(boot, run):
    p=R+f'membench-jibin-{run}/results/boot{boot}/cme-latency-dram-small.csv'
    by={}
    for d in rows(p): by.setdefault(d['size_bytes'],[]).append(d)
    return by,p
for boot,run in (('A','005'),('C','007'),('E','010')):
    by,p=small(boot,run); print('--- boot',boot,p.split('results/')[-1])
    for s in (8192,16384,32768,49152,65536):
        ps=by[s]; bp=min(ps,key=lambda d:float(d['ns_per_load']))
        mi=statistics.mean(d['cme_l1d_refill_inner_per_load'] for d in ps); mo=statistics.mean(d['cme_l1d_refill_outer_per_load'] for d in ps)
        print(f"  {s//1024:3d} KiB best rep line {bp['_line']} ns {bp['ns_per_load']} inner {bp['cme_l1d_refill_inner_per_load']:.3f} outer {bp['cme_l1d_refill_outer_per_load']:.3f} sum {bp['cme_l1d_refill_inner_per_load']+bp['cme_l1d_refill_outer_per_load']:.1f} | mean inner {mi:.2f} outer {mo:.2f} share {100*mi/(mi+mo):.1f} %  (reps inner: {[d['cme_l1d_refill_inner_per_load'] for d in ps]})")
# 3. F2 small-l3
p=R+'membench-jibin-012/results/bootF2/cme-latency-dram-small-l3.csv'; by={}
for d in rows(p): by.setdefault(d['size_bytes'],[]).append(d)
print('--- F2',p.split('results/')[-1])
for s in (65536,98304,131072,196608,262144,393216):
    ps=by[s]; bp=min(ps,key=lambda d:float(d['ns_per_load']))
    print(f"  {s//1024:3d} KiB best rep line {bp['_line']} ns {bp['ns_per_load']} span {bp['ns_per_load_span']} inner {bp['cme_l1d_refill_inner_per_load']:.3f} outer {bp['cme_l1d_refill_outer_per_load']:.3f} hit {bp['cme_l3d_hit_per_load']:.3f} miss {bp['cme_l3d_miss_per_load']:.3f} refill {bp['cme_l3d_refill_per_load']:.3f} miss-refill {bp['cme_l3d_miss_per_load']-bp['cme_l3d_refill_per_load']:.3f}  reps miss-refill {[round(d['cme_l3d_miss_per_load']-d['cme_l3d_refill_per_load'],3) for d in ps]}")
# least squares check over F2 reps 96-384 KiB
import numpy as np
X=[];y=[]
for s in (98304,131072,196608,262144,393216):
    for d in by[s]:
        X.append([1,d['cme_l3d_hit_per_load'],d['cme_l3d_miss_per_load']-d['cme_l3d_refill_per_load'],d['cme_l1d_refill_outer_per_load']]); y.append(d['ns_per_load_span'])
X=np.array(X);y=np.array(y); c,res,rk,sv=np.linalg.lstsq(X,y,rcond=None)
print('lstsq (span ns) a h s o =',np.round(c,1),'rms',round(float(np.sqrt(np.mean((X@c-y)**2))),3),'n',len(y))
y2=np.array([float(d['ns_per_load']) for s in (98304,131072,196608,262144,393216) for d in by[s]]); c2=np.linalg.lstsq(X,y2,rcond=None)[0]
print('lstsq (ns_per_load) =',np.round(c2,1))
