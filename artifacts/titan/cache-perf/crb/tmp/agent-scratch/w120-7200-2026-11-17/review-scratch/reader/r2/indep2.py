#!/usr/bin/env python3
# indep2.py - reviewer's own computation of the headline values from facts.json (GBps field), not from make_report.py.
import json, collections, statistics as st
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
f=json.load(open(S+'/facts.json')); iv=f['intervals']
def sel(**kw):
    return [r for r in iv if all(r.get(k)==v for k,v in kw.items())]
def rng(rs): 
    v=[r['GBps'] for r in rs]; return (min(v),max(v),len(v),len(set(r['proc_key'] for r in rs)))
def show(name, rs): 
    lo,hi,n,p=rng(rs); print(f'{name}: {lo:.3f} to {hi:.3f}  n={n} intervals / {p} processes  median {st.median([r["GBps"] for r in rs]):.3f}')
# part C
C=sel(dataset='rerun-C')
for r in sorted(C,key=lambda r:(r['tag'],r['round'],r['pos'])):
    pass
byp=collections.defaultdict(list)
for r in C: byp[(r['tag'],r['round'])].append(r)
print('--- part C drops per process and round')
drops=collections.defaultdict(list)
for (tag,rd),rs in sorted(byp.items()):
    d={r['kernel']:r for r in rs}
    drop=(1-d['read']['GBps']/d['oldread']['GBps'])*100
    kb=d['read']['kernel_before']
    drops[kb].append(drop)
    print(tag,rd,'read',d['read']['GBps'],'pos',d['read']['pos'],'before:',kb,'| oldread',d['oldread']['GBps'],'pos',d['oldread']['pos'],'| asmread',d['asmread']['GBps'],'pos',d['asmread']['pos'],'before:',d['asmread']['kernel_before'],f'| drop {drop:.2f}')
for kb,v in drops.items(): print('read after',kb,f'{min(v):.2f} to {max(v):.2f}',len(v))
show('C oldread',sel(dataset='rerun-C',kernel='oldread'))
show('C oldread pos0',sel(dataset='rerun-C',kernel='oldread',pos=0))
# part L, control I, F72d12, L-1
for ds in ('rerun-L','control-I','F72d12','L-1'):
    rs=[r for r in iv if r['dataset']==ds]
    byp=collections.defaultdict(dict)
    for r in rs:
        if r['kernel'] in('oldread','asmread'): byp[(r['proc_key'],r['round'])][r['kernel']]=r
    dr=[(1-d['asmread']['GBps']/d['oldread']['GBps'])*100 for d in byp.values()]
    print(ds,f'drop {min(dr):.2f} to {max(dr):.2f} pairs {len(dr)}', 'pos old',set(d['oldread']['pos'] for d in byp.values()),'pos asm',set(d['asmread']['pos'] for d in byp.values()))
    show(' oldread',[r for r in rs if r['kernel']=='oldread']); show(' asmread',[r for r in rs if r['kernel']=='asmread'])
# pools
def pool(dss,kernel,**kw): return [r for r in iv if r['dataset'] in dss and r['kernel']==kernel and all(r.get(k)==v for k,v in kw.items())]
Lold=pool(('L-1','L-2','L-3','L-4'),'oldread'); Lasm=pool(('L-1','L-2','L-3','L-4'),'asmread')
show('pool L oldread',Lold); show('pool L asmread',Lasm)
print(' positions',collections.Counter((r['dataset'],r['kernel'],r['pos']) for r in Lold+Lasm))
Aold=pool(('A-1','A-2','A-3'),'read',binary='bw_old'); show('pool A bw_old read',Aold)
show('rerun A bw_old read',pool(('rerun-A',),'read',binary='bw_old'))
for rd in (1,2):
    show(f'8000 bw_new read round {rd}',pool(('A-1','A-2'),'read',binary='bw_new',round=rd))
    show(f'7200 s1 bw_new read round {rd}',pool(('rerun-A',),'read',binary='bw_new',round=rd,session=1))
    print('  passes 8000',sorted(r['passes'] for r in pool(('A-1','A-2'),'read',binary='bw_new',round=rd)),'7200 s1',sorted(r['passes'] for r in pool(('rerun-A',),'read',binary='bw_new',round=rd,session=1)))
# part A drops per session and round (process medians)
print('--- part A drops')
for ds in ('rerun-A','A-1','A-2'):
    for s in sorted(set(r['session'] for r in iv if r['dataset']==ds), key=str):
        for rd in (1,2):
            o=[r['GBps'] for r in iv if r['dataset']==ds and r['session']==s and r['round']==rd and r['kernel']=='read' and r['binary']=='bw_old']
            n=[r['GBps'] for r in iv if r['dataset']==ds and r['session']==s and r['round']==rd and r['kernel']=='read' and r['binary']=='bw_new']
            print(ds,s,rd,len(o),len(n),f'old med {st.median(o):.2f} new med {st.median(n):.2f} drop {(1-st.median(n)/st.median(o))*100:.2f}')
# distances
pl=[r['GBps'] for r in iv if r['dataset']=='rerun-L' and r['kernel']=='asmread']; po=[r['GBps'] for r in Lasm]; fd=[r['GBps'] for r in iv if r['dataset']=='F72d12' and r['kernel']=='asmread']; l1=[r['GBps'] for r in iv if r['dataset']=='L-1' and r['kernel']=='asmread']
print('partL-pool nearest',min(pl)-max(po),'medians',st.median(pl)-st.median(po),'farthest',max(pl)-min(po))
print('partL-F72 nearest',min(pl)-max(fd),'medians',st.median(pl)-st.median(fd),'farthest',max(pl)-min(fd))
print('F72 - L1 nearest',min(fd)-max(l1))
plo=[r['GBps'] for r in iv if r['dataset']=='rerun-L' and r['kernel']=='oldread']; poo=[r['GBps'] for r in Lold]
print('old: pool min - partL max',min(poo)-max(plo),'medians',st.median(poo)-st.median(plo), 'pct nearest',(min(poo)-max(plo))/min(poo)*100,'pct med',(st.median(poo)-st.median(plo))/st.median(poo)*100)
print('width pool A old %',(max(r['GBps'] for r in Aold)-min(r['GBps'] for r in Aold))/min(r['GBps'] for r in Aold)*100,'width pool L old %',(max(poo)-min(poo))/min(poo)*100)
print('pool asm without lowest',sorted(po)[1],max(po))
# loads at launch part A read processes
for s in (1,2,3):
    seen=[]
    for r in iv:
        if r['dataset']=='rerun-A' and r['session']==s and r['kernel']=='read' and r['interval']==0: seen.append((r['launch_utc'],r['binary'],r['round'],r['load1_at_launch']))
    print('A session',s,sorted(seen))
for ds in ('A-1','A-2','A-3','L-1','L-2','L-3','L-4','F72d12'):
    seen=sorted(set((r['launch_utc'],r['proc_key'].split('|')[-1],r['load1_at_launch']) for r in iv if r['dataset']==ds and ((r['kernel']=='read') or r['kernel'] in('oldread','asmread'))))
    print(ds,seen)
