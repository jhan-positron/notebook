#!/usr/bin/env python3
# Independent recompute of the page's numbers from facts.json (reviewer, claims lens).
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
    g=[r['GBps'] for r in rs]; return (min(g),max(g),st.median(g),len(g),len(set(r['proc_key'] for r in rs)))
def show(name,rs): 
    lo,hi,med,n,p=rng(rs); print(f'{name}: {lo:.2f} to {hi:.2f} med {med:.3f} n={n} proc={p}')
    return lo,hi,med
print('--- part L')
L_old=sel(dataset='rerun-L',kernel='oldread'); L_asm=sel(dataset='rerun-L',kernel='asmread')
print(collections.Counter((r['pos'],r['kernel']) for r in sel(dataset='rerun-L')))
lo_Lo,hi_Lo,med_Lo=show('L oldread',L_old); lo_La,hi_La,med_La=show('L asmread',L_asm)
def pairs(ds,kold,knew,filt=lambda r:True):
    out=[]
    for a in [r for r in iv if r['dataset']==ds and r['kernel']==knew and filt(r)]:
        b=[r for r in iv if r['dataset']==ds and r['kernel']==kold and r['proc_key']==a['proc_key'] and r['round']==a['round']]
        assert len(b)==1,(a,b)
        out.append((a['tag'],a['round'],b[0]['GBps'],a['GBps'],(1-a['GBps']/b[0]['GBps'])*100))
    return out
for ds in ['rerun-L','control-I','F72d12','L-1']:
    p=pairs(ds,'oldread','asmread',lambda r:r['pos']==1)
    print(ds,[(t,rd,f'{o:.2f}',f'{n:.2f}',f'{dr:.2f}') for t,rd,o,n,dr in p]); print('  drop',min(x[4] for x in p),max(x[4] for x in p))
print('--- part C')
C=sel(dataset='rerun-C')
for r in C: print(r['tag'],r['round'],r['pos'],r['kernel'],r['kernel_before'],r['GBps'],r['session'],r['launch_utc'],r['load1_at_launch'])
p=pairs('rerun-C','oldread','read')
for g in ['oldread','asmread']:
    pp=[x for x in p if any(r['tag']==x[0] and r['round']==x[1] and r['kernel']=='read' and g in str(r['kernel_before']) for r in C)]
    print('read after',g,[(x[0],x[1],round(x[4],2)) for x in pp], 'old',min(x[2] for x in pp),max(x[2] for x in pp),'new',min(x[3] for x in pp),max(x[3] for x in pp))
show('C oldread',sel(dataset='rerun-C',kernel='oldread'))
print('--- part A')
for s in (1,2,3):
    for rd in (1,2):
        o=sel(dataset='rerun-A',session=s,round=rd,kernel='read',binary='bw_old'); n=sel(dataset='rerun-A',session=s,round=rd,kernel='read',binary='bw_new')
        mo=st.median(r['GBps'] for r in o); mn=st.median(r['GBps'] for r in n)
        print(s,rd,mo,mn,round((1-mn/mo)*100,2),[r['GBps'] for r in o],[r['GBps'] for r in n],[r['passes'] for r in n],[r['load1_at_launch'] for r in o+n],[r['launch_utc'] for r in o+n])
show('A bw_old read',sel(dataset='rerun-A',kernel='read',binary='bw_old'))
for dsn in ['A-1','A-2','A-3']:
    for b in ['bw_old','bw_new']:
        for rd in (1,2,3):
            x=sel(dataset=dsn,kernel='read',binary=b,round=rd)
            if x: print(dsn,b,rd,[r['GBps'] for r in x],[r['passes'] for r in x],st.median(r['GBps'] for r in x),x[0]['launch_utc'],x[0]['load1_at_launch'],x[0]['tag'])
poolA=[r for r in iv if r['dataset'] in('A-1','A-2','A-3') and r['kernel']=='read' and r['binary']=='bw_old']
show('pool A old',poolA)
lo,hi,med=show('pool A old',poolA); print('width %',(hi-lo)/lo*100)
poolLo=[r for r in iv if r['dataset'] in('L-1','L-2','L-3','L-4') and r['kernel']=='oldread' and r['pos']==0]
poolLa=[r for r in iv if r['dataset'] in('L-1','L-2','L-3','L-4') and r['kernel']=='asmread' and r['pos']==1]
plo,phi,pmed=show('pool L old',poolLo); print('width %',(phi-plo)/plo*100)
alo,ahi,amed=show('pool L asm',poolLa); print('width',ahi-alo)
print('L old nearest',plo-hi_Lo,(plo-hi_Lo)/plo*100,'med',pmed-med_Lo,(pmed-med_Lo)/pmed*100)
print('L asm nearest',lo_La-ahi,'med',med_La-amed,'far',hi_La-alo)
F=sel(dataset='F72d12',kernel='asmread',pos=1); Fo=sel(dataset='F72d12',kernel='oldread',pos=0)
flo,fhi,fmed=show('F asm',F); show('F old',Fo)
I=sel(dataset='control-I',kernel='asmread',pos=1); Io=sel(dataset='control-I',kernel='oldread',pos=0)
ilo,ihi,imed=show('I asm',I); show('I old',Io)
print('L vs F nearest',lo_La-fhi,'med',med_La-fmed,'far',hi_La-flo)
print('I vs pool',ilo-ahi)
L1=sel(dataset='L-1',kernel='asmread',pos=1); l1lo,l1hi,_=show('L-1 asm',L1); print('F above L-1',flo-l1hi)
p2=[r for r in poolLa if r['GBps']>alo+0.001]; show('pool w/o lowest',p2)
for dsn in ['L-1','L-2','L-3','L-4']:
    show(dsn+' old',[r for r in poolLo if r['dataset']==dsn]); show(dsn+' asm',[r for r in poolLa if r['dataset']==dsn])
    print('   ',sorted(set((r['tag'],r['launch_utc'],r['load1_at_launch']) for r in poolLo if r['dataset']==dsn)))
# part C asmread groups
for kb in sorted(set(str(r['kernel_before']) for r in C if r['kernel']=='asmread')):
    show('C asmread before='+kb,[r for r in C if r['kernel']=='asmread' and str(r['kernel_before'])==kb])
x=[r for r in C if r['kernel']=='asmread' and 'oldread' in str(r['kernel_before'])]
print('C asm after old vs pool',min(r['GBps'] for r in x)-ahi)
# old-kernel span of 6 rows of same line
six=[r for r in iv if r['dataset'] in('rerun-L','control-I','F72d12') and r['kernel']=='oldread' and r['pos']==0]
show('six rows old',six)
six=[r for r in iv if r['dataset'] in('rerun-L','control-I','F72d12') and r['kernel']=='asmread' and r['pos']==1]
show('six rows asm',six)
