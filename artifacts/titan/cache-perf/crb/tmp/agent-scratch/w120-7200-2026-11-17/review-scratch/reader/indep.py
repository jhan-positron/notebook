#!/usr/bin/env python3
# Independent recomputation from the raw csv files (no use of facts.json or make_report.py).
import csv, statistics as st, sys
R='/home/jhan/workspace/titan/cache-perf/crb/results'
def bwx(path):
    """return dict (round,pos,kernel)->sum over T rows of bytes/elapsed in GB/s"""
    out={}
    for line in open(path):
        if line.startswith('T,'):
            p=line.rstrip('\n').split(',')
            k=(int(p[1]),int(p[2]),p[3])
            out[k]=out.get(k,0.0)+int(p[6])/float(p[7])/1e9
    return out
def k120(path, tagmode=False):
    """return list of (binary,kernel,round,load,utc,[agg...],[passes...])"""
    procs=[];cur=None
    for line in open(path):
        if line.startswith('-- '):
            w=line.split()
            if w[1]=='binary':
                d=dict(zip(w[1::2],w[2::2])); cur=dict(binary=d['binary'],kernel=d['kernel'],round=int(d['round']),load=d['load'],utc=d['utc'],iv=[],passes=[])
            else:
                # -- step A1 tag read_old-r1 binary bw_old ... loadavg x .. utc .. args ... --kernel read
                tag=w[w.index('tag')+1]; b=w[w.index('binary')+1]; la=w[w.index('loadavg')+1]; utc=w[w.index('utc')+1]; ker=w[w.index('--kernel')+1]; ms=w[w.index('--min-ms')+1]
                cur=dict(binary=b,kernel=ker,round=tag,load=la,utc=utc,iv=[],passes=[],ms=ms)
            procs.append(cur)
        elif cur is not None and line and line[0].isalpha() and not line.startswith('kernel,'):
            p=line.strip().split(',')
            if len(p)>=10 and p[1]=='120':
                try:
                    cur['iv'].append(float(p[6])); cur['passes'].append(int(p[4])//int(p[2]))
                except ValueError: pass
    return procs
f=lambda x:f'{x:.2f}'
print('== part C')
C={'T72C1':'w120-T72C1-20261117T221436Z/cfwd.csv','T72C3':'w120-T72C3-20261117T222054Z/cfwd.csv','T72C2':'w120-T72C2-20261117T221745Z/crev.csv','T72C4':'w120-T72C4-20261117T222136Z/crev.csv'}
cd={}
for t,p in C.items():
    d=bwx(f'{R}/{p}'); cd[t]=d
    for r in (0,1):
        o=[v for (rr,pos,k),v in d.items() if rr==r and k=='oldread'][0]
        rd=[v for (rr,pos,k),v in d.items() if rr==r and k=='read'][0]
        a=[v for (rr,pos,k),v in d.items() if rr==r and k=='asmread'][0]
        print(t,r,'old',f(o),'read',f(rd),'asm',f(a),'drop read %.2f'%((1-rd/o)*100),'drop asm %.2f'%((1-a/o)*100))
print('== part L / I / F / L-1')
L={'T72L1':'w120-T72L1-20261117T221329Z','T72L2':'w120-T72L2-20261117T221638Z','T72L3':'w120-T72L3-20261117T221947Z','T72I1':'w120-T72I1-20261117T222700Z','T72I2':'w120-T72I2-20261117T223227Z','F72d12':'w120-w120-F72d12-20261117T200231Z','L-1':'w120-R8-20261117T020549Z'}
ld={}
for t,p in L.items():
    d=bwx(f'{R}/{p}/a6456.csv'); ld[t]=d
    for r in (0,1):
        o=d[(r,0,'oldread')]; a=d[(r,1,'asmread')]
        print(t,r,'old',f(o),'asm',f(a),'drop %.2f'%((1-a/o)*100))
pool_files={'L-2a':'w120-R1-20261115T185140Z/p1nop.csv','L-2b':'w120-R1-20261115T185140Z/p2add.csv','L-3':'w120-R5-20261115T203152Z/thp.csv','L-4a':'w120-R6-20261115T203438Z/st1.csv','L-4b':'w120-R6-20261115T203438Z/st2.csv','L-4c':'w120-R6-20261115T203438Z/st3.csv'}
po=[ld['L-1'][(r,0,'oldread')] for r in (0,1)]; pa=[ld['L-1'][(r,1,'asmread')] for r in (0,1)]
for t,p in pool_files.items():
    d=bwx(f'{R}/{p}')
    o=[v for (rr,pos,k),v in sorted(d.items()) if pos==0 and k=='oldread']; a=[v for (rr,pos,k),v in sorted(d.items()) if pos==1 and k=='asmread']
    print(t,'old',[f(x) for x in o],'asm',[f(x) for x in a]); po+=o; pa+=a
print('pool old n',len(po),f(min(po)),f(max(po)),'median',f(st.median(po)),'width pct of lower end %.2f'%((max(po)-min(po))/min(po)*100))
print('pool asm n',len(pa),f(min(pa)),f(max(pa)),'median',f(st.median(pa)),'width',f(max(pa)-min(pa)))
pa2=sorted(pa)[1:]; print('pool asm without lowest',f(min(pa2)),f(max(pa2)),len(pa2))
Lo=[ld[t][(r,0,'oldread')] for t in ('T72L1','T72L2','T72L3') for r in (0,1)]; La=[ld[t][(r,1,'asmread')] for t in ('T72L1','T72L2','T72L3') for r in (0,1)]
print('part L old',f(min(Lo)),f(max(Lo)),'med',f(st.median(Lo)),' asm',f(min(La)),f(max(La)),'med',f(st.median(La)))
print('part L old vs pool: nearest',f(min(po)-max(Lo)),'%.2f %%'%((min(po)-max(Lo))/min(po)*100),'medians',f(st.median(po)-st.median(Lo)),'%.2f %%'%((st.median(po)-st.median(Lo))/st.median(po)*100))
print('part L asm vs pool: nearest',f(min(La)-max(pa)),'medians',f(st.median(La)-st.median(pa)),'farthest',f(max(La)-min(pa)))
Fa=[ld['F72d12'][(r,1,'asmread')] for r in (0,1)]; Fo=[ld['F72d12'][(r,0,'oldread')] for r in (0,1)]
print('part L asm vs F72d12: nearest',f(min(La)-max(Fa)),'medians',f(st.median(La)-st.median(Fa)),'farthest',f(max(La)-min(Fa)))
Ia=[ld[t][(r,1,'asmread')] for t in ('T72I1','T72I2') for r in (0,1)]; Io=[ld[t][(r,0,'oldread')] for t in ('T72I1','T72I2') for r in (0,1)]
print('control I asm',f(min(Ia)),f(max(Ia)),'above pool',f(min(Ia)-max(pa)),' old',f(min(Io)),f(max(Io)))
print('F72d12 above L-1 alone',f(min(Fa)-max(pa[:2])))
allold=Lo+Io+Fo; allasm=La+Ia+Fa
print('6 rows same line: old',f(min(allold)),f(max(allold)),f(max(allold)-min(allold)),' asm',f(min(allasm)),f(max(allasm)),f(max(allasm)-min(allasm)))
Co=[v for t in cd for (r,pos,k),v in cd[t].items() if k=='oldread']
print('part C old',f(min(Co)),f(max(Co)),len(Co))
ca=[cd[t][(1,0,'asmread')] for t in ('T72C2','T72C4')]; print('part C asm after oldread',[f(x) for x in ca],'above pool',f(min(ca)-max(pa)))
print('== part A')
import collections
for name,p in (('T72A1','k120-T72A1-20261117T221209Z/threads120.csv'),('T72A2','k120-T72A2-20261117T221518Z/threads120.csv'),('T72A3','k120-T72A3-20261117T221827Z/threads120.csv'),('A-1','kernels-20261113T181222Z/threads120.csv')):
    ps=[x for x in k120(f'{R}/{p}') if x['kernel']=='read']
    for r in (1,2):
        o=[x for x in ps if x['binary']=='bw_old' and x['round']==r][0]; n=[x for x in ps if x['binary']=='bw_new' and x['round']==r][0]
        print(name,'round',r,'old',o['iv'],'med',f(st.median(o['iv'])),'load',o['load'],o['utc'],'| new',n['iv'],n['passes'],'med',f(st.median(n['iv'])),'load',n['load'],n['utc'],'drop %.2f'%((1-st.median(n['iv'])/st.median(o['iv']))*100))
ps=k120(f'{R}/partA-20261113T205055Z/A1.csv')
for x in ps:
    if x['kernel']=='read': print('A-2',x['round'],x['binary'],x['iv'],x['passes'],'med',f(st.median(x['iv'])),'load',x['load'],x['utc'])
ps=k120(f'{R}/partA-20261113T205055Z/A3.csv')
a3=[]
for x in ps:
    if str(x['round']).startswith('onebuf-ms500'): print('A-3',x['round'],x['binary'],x['iv'],'load',x['load'],x['utc']); a3+=x['iv']
print('A-3 n',len(a3),min(a3),max(a3))
