#!/usr/bin/env python3
"""Independent recomputation from the raw csv files (not from facts.json, not from the generator)."""
import os,re,statistics as st,glob
R="/home/jhan/workspace/titan/cache-perf/crb/results"
def bwx(path):
    """return list of (round,pos,kernel,rate_from_T_rows,printed)"""
    out=[];cur=None
    for ln in open(path):
        p=ln.rstrip('\n').split(',')
        if p[0]=='I':
            cur=[int(p[1]),int(p[2]),p[3],0.0,float(p[8]),0]; out.append(cur)
        elif p[0]=='T' and cur is not None and int(p[1])==cur[0] and int(p[2])==cur[1]:
            cur[3]+=float(p[6])/float(p[7])/1e9; cur[5]+=1
    for c in out: assert c[5]==120,(path,c)
    return out
def r2(x): 
    from decimal import Decimal,ROUND_HALF_UP
    return float(Decimal(repr(x)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
def rng(v): return f"{min(v):.2f} to {max(v):.2f}"
def med(v): return st.median(v)
F={}
for tag,pat in [('L1','w120-T72L1-*/a6456.csv'),('L2','w120-T72L2-*/a6456.csv'),('L3','w120-T72L3-*/a6456.csv'),
                ('C1','w120-T72C1-*/cfwd.csv'),('C2','w120-T72C2-*/crev.csv'),('C3','w120-T72C3-*/cfwd.csv'),('C4','w120-T72C4-*/crev.csv'),
                ('I1','w120-T72I1-*/a6456.csv'),('I2','w120-T72I2-*/a6456.csv'),('F','w120-w120-F72d12-*/a6456.csv'),
                ('B1','w120-R8-20261117T020549Z/a6456.csv'),('B2a','w120-R1-20261115T185140Z/p1nop.csv'),('B2b','w120-R1-20261115T185140Z/p2add.csv'),
                ('B3','w120-R5-20261115T203152Z/thp.csv'),('B4a','w120-R6-20261115T203438Z/st1.csv'),('B4b','w120-R6-20261115T203438Z/st2.csv'),('B4c','w120-R6-20261115T203438Z/st3.csv')]:
    g=glob.glob(R+'/'+pat); assert len(g)==1,(pat,g); F[tag]=bwx(g[0])
def get(tag,kernel,pos=None):
    return [r[3] for r in F[tag] if r[2]==kernel and (pos is None or r[1]==pos)]
def drops(tag,new,old,):
    out=[]
    for rd in sorted(set(r[0] for r in F[tag])):
        n=[r[3] for r in F[tag] if r[0]==rd and r[2]==new]; o=[r[3] for r in F[tag] if r[0]==rd and r[2]==old]
        assert len(n)==1 and len(o)==1
        out.append((1-n[0]/o[0])*100)
    return out
print("== part L")
for t in ('L1','L2','L3','I1','I2','F','B1'):
    o=get(t,'oldread',0); a=get(t,'asmread',1); d=drops(t,'asmread','oldread')
    print(t,'old',[f"{x:.2f}" for x in o],'med',f"{med(o):.2f}",'asm',[f"{x:.2f}" for x in a],'med',f"{med(a):.2f}",'drop',[f"{x:.2f}" for x in d])
Lo=sum((get(t,'oldread',0) for t in ('L1','L2','L3')),[]); La=sum((get(t,'asmread',1) for t in ('L1','L2','L3')),[])
Io=sum((get(t,'oldread',0) for t in ('I1','I2')),[]); Ia=sum((get(t,'asmread',1) for t in ('I1','I2')),[])
Fo=get('F','oldread',0); Fa=get('F','asmread',1)
Po=sum((get(t,'oldread',0) for t in ('B1','B2a','B2b','B3','B4a','B4b','B4c')),[]); Pa=sum((get(t,'asmread',1) for t in ('B1','B2a','B2b','B3','B4a','B4b','B4c')),[])
print('part L old',rng(Lo),len(Lo),'asm',rng(La),len(La)); print('ctrl I old',rng(Io),'asm',rng(Ia)); print('F old',rng(Fo),'asm',rng(Fa))
print('pool old',rng(Po),len(Po),'asm',rng(Pa),len(Pa))
print('part L old below pool nearest',f"{min(Po)-max(Lo):.3f}",'pct of lower end',f"{(min(Po)-max(Lo))/min(Po)*100:.2f}",'medians',f"{med(Po)-med(Lo):.3f}",'pct',f"{(med(Po)-med(Lo))/med(Po)*100:.2f}", 'med L',f"{med(Lo):.2f}",'med pool',f"{med(Po):.2f}")
print('part L asm above pool nearest',f"{min(La)-max(Pa):.3f}",'medians',f"{med(La)-med(Pa):.3f}",'farthest',f"{max(La)-min(Pa):.3f}")
print('part L asm above F nearest',f"{min(La)-max(Fa):.3f}",'medians',f"{med(La)-med(Fa):.3f}",'farthest',f"{max(La)-min(Fa):.3f}")
print('ctrl I above pool',f"{min(Ia)-max(Pa):.3f}",'F above L-1',f"{min(Fa)-max(get('B1','asmread',1)):.3f}", 'pool width asm',f"{max(Pa)-min(Pa):.3f}", 'pool width old pct',f"{(max(Po)-min(Po))/min(Po)*100:.2f}")
Pa2=sorted(Pa)[1:]; print('pool without lowest',rng(Pa2),len(Pa2),'part L above',f"{min(La)-max(Pa2):.3f}")
print('same line 7200: old span',rng(Lo+Io+Fo),f"{max(Lo+Io+Fo)-min(Lo+Io+Fo):.3f}",'asm span',rng(La+Ia+Fa),f"{max(La+Ia+Fa)-min(La+Ia+Fa):.3f}")
print('F in part L distance old?', )
print("== part C")
for t in ('C1','C2','C3','C4'):
    print(t,[(r[0],r[1],r[2],f"{r[3]:.2f}") for r in F[t]], 'drop read',[f"{x:.2f}" for x in drops(t,'read','oldread')])
ro=get('C1','read')+get('C3','read'); ra=get('C2','read')+get('C4','read')
print('read after oldread',rng(ro),'read after asmread',rng(ra))
print('old cfwd',rng(get('C1','oldread')+get('C3','oldread')),'old crev',rng(get('C2','oldread')+get('C4','oldread')), 'all old', rng(sum((get(t,'oldread') for t in ('C1','C2','C3','C4')),[])))
d_ao=drops('C1','read','oldread')+drops('C3','read','oldread'); d_aa=drops('C2','read','oldread')+drops('C4','read','oldread')
print('drops after old',f"{min(d_ao):.2f} {max(d_ao):.2f}",'after asm',f"{min(d_aa):.2f} {max(d_aa):.2f}")
a_after_old=[r[3] for t in ('C2','C4') for r in F[t] if r[2]=='asmread' and r[0]==1]
print('asmread after oldread (crev r1)',rng(a_after_old),'above pool',f"{min(a_after_old)-max(Pa):.3f}")
print('asmread after read (cfwd)',rng(get('C1','asmread')+get('C3','asmread')),'first interval',rng([r[3] for t in ('C2','C4') for r in F[t] if r[2]=='asmread' and r[0]==0]))
print('part C old vs pool: overlap', not(max(sum((get(t,'oldread') for t in ('C1','C2','C3','C4')),[]))<min(Po)))
# part A
def partA(path, style='ra'):
    procs=[];cur=None
    for i,ln in enumerate(open(path),1):
        if ln.startswith('-- '):
            cur={'hdr':ln.strip(),'line':i,'iv':[]}; procs.append(cur)
        elif cur is not None and ln[0].isdigit() or (cur is not None and ln.startswith('120')):
            pass
    return procs
import csv
def parseA(path):
    procs=[];cur=None;header=None
    for i,ln in enumerate(open(path),1):
        s=ln.rstrip('\n')
        if s.startswith('-- '):
            cur={'hdr':s,'line':i,'iv':[]}; procs.append(cur); continue
        if s.startswith('kernel,') or 'aggregate_GBps' in s: header=s.split(','); continue
        p=s.split(',')
        if cur is not None and header and len(p)==len(header) and p[0] in ('read','write','copy','asmread','asmwrite','asmcopy') and 'aggregate_GBps' in header:
            row=dict(zip(header,p)); cur['iv'].append(row)
    return procs
pa=parseA(glob.glob(R+'/k120-T72A1-*/threads120.csv')[0])
print(pa[0]['hdr'], pa[0]['iv'][:1])
