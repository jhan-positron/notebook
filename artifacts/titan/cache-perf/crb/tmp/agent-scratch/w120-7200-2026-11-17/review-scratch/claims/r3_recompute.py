#!/usr/bin/env python3
# Round 3, lens claims: recompute the values behind the prose claims of the report from facts.json.
import json, statistics as st, collections
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
d=json.load(open(S+'/facts.json'))
iv=d['intervals']
def sel(**kw):
    out=[]
    for r in iv:
        ok=True
        for k,v in kw.items():
            if callable(v):
                if not v(r.get(k)): ok=False;break
            elif r.get(k)!=v: ok=False;break
        if ok: out.append(r)
    return out
def rng(rs): 
    g=[r['GBps'] for r in rs]; return (min(g),max(g),len(g),len({r['proc_key'] for r in rs}))
def show(name,rs): 
    lo,hi,n,p=rng(rs); print(f'{name}: {lo:.3f} to {hi:.3f}  n={n} iv / {p} proc  median {st.median([r["GBps"] for r in rs]):.3f}')
    return lo,hi
# part L
Lold=sel(dataset='rerun-L',kernel='oldread'); Lasm=sel(dataset='rerun-L',kernel='asmread')
show('partL oldread',Lold); show('partL asmread',Lasm)
pool=[r for r in iv if r['dataset'] in('L-1','L-2','L-3','L-4')]
Pold=[r for r in pool if r['kernel']=='oldread' and r['pos']==0]; Pasm=[r for r in pool if r['kernel']=='asmread' and r['pos']==1]
print('pool positions', collections.Counter((r['dataset'],r['kernel'],r['pos']) for r in pool))
show('pool oldread pos0',Pold); show('pool asmread pos1',Pasm)
F=sel(dataset='F72d12'); Fold=[r for r in F if r['kernel']=='oldread']; Fasm=[r for r in F if r['kernel']=='asmread']
show('F72 old',Fold); show('F72 asm',Fasm)
I=sel(dataset='control-I'); Iold=[r for r in I if r['kernel']=='oldread']; Iasm=[r for r in I if r['kernel']=='asmread']
show('I old',Iold); show('I asm',Iasm)
g=lambda rs:[r['GBps'] for r in rs]
print('partL old nearest', min(g(Pold))-max(g(Lold)), 'median diff', st.median(g(Pold))-st.median(g(Lold)), 'pct', (min(g(Pold))-max(g(Lold)))/min(g(Pold))*100, (st.median(g(Pold))-st.median(g(Lold)))/st.median(g(Pold))*100)
print('partL asm nearest', min(g(Lasm))-max(g(Pasm)), 'medians', st.median(g(Lasm))-st.median(g(Pasm)), 'farthest', max(g(Lasm))-min(g(Pasm)))
print('partL asm vs F72 nearest', min(g(Lasm))-max(g(Fasm)), 'medians', st.median(g(Lasm))-st.median(g(Fasm)), 'farthest', max(g(Lasm))-min(g(Fasm)))
print('I asm nearest vs pool', min(g(Iasm))-max(g(Pasm)))
print('F72 asm vs L-1', min(g(Fasm))-max(g([r for r in Pasm if r['dataset']=='L-1'])))
print('pool asm width', max(g(Pasm))-min(g(Pasm)))
print('pool old width %', (max(g(Pold))-min(g(Pold)))/min(g(Pold))*100)
# 6 rows of same line
six_old=g(Lold)+g(Iold)+g(Fold); six_asm=g(Lasm)+g(Iasm)+g(Fasm)
print('six rows old', min(six_old),max(six_old),max(six_old)-min(six_old),'asm',min(six_asm),max(six_asm),max(six_asm)-min(six_asm))
# pool without lowest
P2=sorted(g(Pasm))[1:]; print('pool w/o lowest', P2[0],P2[-1],len(P2), 'partL above by', min(g(Lasm))-P2[-1])
# part C groups
C=sel(dataset='rerun-C')
print(collections.Counter((r['tag'],r['kernel'],r['pos'],r['round'],r['kernel_before']) for r in C))
def grp(k,kb): return [r for r in C if r['kernel']==k and (kb(r) if callable(kb) else r['kernel_before']==kb)]
for r in sorted(C,key=lambda r:(r['tag'],r['round'],r['pos'])): print(r['tag'],r['session'],r['round'],r['pos'],r['kernel'],r['kernel_before'],r['GBps'],r['load1_at_launch'],r['launch_utc'])
# part A
A=sel(dataset='rerun-A',kernel='read')
for r in sorted(A,key=lambda r:(r['tag'],r['round'],r['binary'],r['interval'])): print(r['tag'],r['session'],r['round'],r['binary'],r['interval'],r['GBps'],r['passes'],r['load1_at_launch'],r['launch_utc'],r['line'])
for ds in ('A-1','A-2','A-3'):
    for r in sorted(sel(dataset=ds,kernel='read'),key=lambda r:(r['round'] or 0,r['binary'],r['interval'])): print(ds,r['tag'],r['round'],r['binary'],r['interval'],r['GBps'],r['passes'],r['load1_at_launch'],r['launch_utc'],r['line'])
