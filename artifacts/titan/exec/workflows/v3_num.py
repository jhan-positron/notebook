import csv, sys, glob, os
R='/home/jhan/workspace/titan/cache-perf/asimov/results/'
B={'F1':R+'membench-jibin-011/results/bootF1/','F2':R+'membench-jibin-012/results/bootF2/'}
def rows(boot,f):
    out=[];hdr=None;lines=None
    for ln in open(B[boot]+f):
        ln=ln.strip()
        if not ln: continue
        if ln.startswith('#'):
            if 'lines=' in ln: lines=int(ln.split('lines=')[1].split()[0])
            continue
        p=ln.split(',')
        if p[0]=='mem': hdr=p; continue
        if p[3]=='-': continue
        d=dict(zip(hdr,p)); d['lines']=lines; out.append(d)
    return out
def best(rs):
    m=min(float(r['ns_per_load']) for r in rs)
    return [r for r in rs if float(r['ns_per_load'])==m][0]
from collections import OrderedDict
def bysize(rs,modes=None):
    g=OrderedDict()
    for r in rs:
        if r['mode'].startswith('cme-roundtrip') or r['mode'].startswith('cme-call'): continue
        g.setdefault(int(r['size_bytes']),[]).append(r)
    return g
base=21.005
print('== 4.7 / Table 19, F2 small')
g=bysize(rows('F2','cme-latency-dram-small.csv'))
allpl=[];n=0
for sz,rs in g.items():
    L=rs[0]['lines']; loads=int(rs[0]['loads'])
    pl=[float(r['cme_l1d_refill_inner_per_load'])*loads/L for r in rs]
    b=best(rs); inn=float(b['cme_l1d_refill_inner_per_load']); out=float(b['cme_l1d_refill_outer_per_load'])
    mb=float(b['ns_per_load'])-base
    print(sz//1024,'KiB lines',L,'loads',loads,'walks',loads/L,'inner %.4f io %.4f'%(inn,inn+out),'perline %.2f..%.2f'%(min(pl),max(pl)),'mb %.3f'%mb,'ns/ref %.1f'%(mb/(inn+out)) if inn+out else '', 'step %.4f'%(0.0001*loads/L), 'rd %s hw %s'%(b['cme_l1d_refill_rd_per_load'],b['cme_l1d_refill_hwprf_per_load']))
    if sz<=65536: allpl+=pl; n+=len(rs)
    # ns per refill uncertainty
    if sz in (4096,65536):
        t=inn+out; print('   ns/refill bounds', mb/(t+0.00005), mb/(t-0.00005), ' +-0.0005 ns time:', (mb+0.0005)/(t-0.00005)-mb/t)
print('4-64KiB rep rows',n,'perline %.2f..%.2f'%(min(allpl),max(allpl)))
print('== Table 62, F2 small-l3')
g=bysize(rows('F2','cme-latency-dram-small-l3.csv'))
for sz,rs in g.items():
    if sz<98304: 
        continue
    pr=[(float(r['cme_l3d_miss_per_load'])-float(r['cme_l3d_refill_per_load']))*sz/1024 for r in rs]
    print(sz//1024,' '.join('%.1f'%x for x in pr),'ns',rs[0]['ns_per_load'],rs[-1]['ns_per_load'],'hit',rs[0]['cme_l3d_hit_per_load'],rs[-1]['cme_l3d_hit_per_load'], 'falls' if pr[0]>pr[1]>pr[2] else 'NOTMONO')
# 4-64 KiB l3 events max of best reps
mx=0
for sz,rs in g.items():
    if sz<=65536:
        b=best(rs); mx=max(mx,*[float(b[k]) for k in ('cme_l3d_hit_per_load','cme_l3d_miss_per_load','cme_l3d_refill_per_load')])
print('max l3 event 4-64K best reps',mx)
for boot in ('F1','F2'):
    n=0;neq=0;maxd=0;mxhm=0;above=[]
    for f in ('cme-latency-dram-small-l3.csv','cme-latency-dram-large-l3.csv'):
        for sz,rs in bysize(rows(boot,f)).items():
            for r in rs:
                n+=1
                if '%.4f'%float(r['cme_l3d_refill_per_load'])!='%.4f'%float(r['cme_l1d_refill_outer_per_load']): neq+=1
                d=abs(float(r['cme_l3d_hit_per_load'])+float(r['cme_l3d_miss_per_load'])-float(r['cme_l1d_refill_inner_per_load'])-float(r['cme_l1d_refill_outer_per_load']))
                maxd=max(maxd,d)
            b=best(rs); hm=float(b['cme_l3d_hit_per_load'])+float(b['cme_l3d_miss_per_load']); mxhm=max(mxhm,hm)
            if hm>1: above.append(sz)
    print(boot,'l3 chain rep rows',n,'refill!=outer',neq,'max|hit+miss-in-out| %.5f'%maxd,'max hit+miss best %.4f'%mxhm,'above1 from',min(above)//1024 if above else None,'to',max(above)//1024 if above else None,len(above))
# F1 plain prefetch max best
mx=0
for f in ('cme-latency-dram-small.csv','cme-latency-dram-large.csv'):
    for sz,rs in bysize(rows('F1',f)).items():
        mx=max(mx,float(best(rs)['cme_l1d_refill_hwprf_per_load']))
print('F1 max prefetch best %.2f'%mx)
print('== 8.5 OCM F2')
tot=0
for i in range(5):
    rs=[r for r in rows('F2','cme-latency-ocm-region%d.csv'%i) if r['mode'].startswith('cme-fresh')]
    for r in rs:
        tot+=1; L=int(r['loads'])
        c=[float(r[k])*L for k in ('cme_l1d_refill_rd_per_load','cme_l1d_refill_outer_per_load','cme_l1d_refill_hwprf_per_load','cme_l1d_refill_inner_per_load')]
        if c!=[64,64,0,0] or L!=64: print('DIFF',i,r['mode'],L,c)
print('one-region passes',tot)
for f in ('cme-latency-ocm-all5.csv','cme-latency-ocm-all5-dense.csv'):
    rs=[r for r in rows('F2',f) if r['mode'].startswith('cme-fresh')]
    print(f,len(rs),set((r['loads'],r['cme_l1d_refill_rd_per_load'],r['cme_l1d_refill_outer_per_load'],r['cme_l1d_refill_inner_per_load'],r['cme_l1d_refill_hwprf_per_load']) for r in rs))
print('== 4.6 flushed F2')
for r in rows('F2','cme-latency-dram-flushed.csv'):
    if r['size_bytes']!='0': print(r['mode'],r['loads'],r['ns_per_load'],{k[8:]:v for k,v in r.items() if 'refill' in k})
print('== 3.1 1MiB 3MiB F2 large')
g=bysize(rows('F2','cme-latency-dram-large.csv'))
for sz in (1<<20,3<<20,8<<20,32<<20):
    b=best(g[sz]); print(sz>>20,b['ns_per_load'],b['loads'],{k[8:]:v for k,v in b.items() if 'refill' in k})
