#!/usr/bin/env python3
"""anc3.py FOLDER: mixed-kernel groups with mesh counters. Prints counts in millions per second, per mesh 'm0/m1'.
Line rates (M lines/s) per mesh come from the T rows of the two processes."""
import sys,glob,os,re,collections
fold=sys.argv[1]
groups=[re.match(r'launch (\S+)',l).group(1) for l in open(fold+'/launches.txt') if l.startswith('launch')]
def rows(f):
    for l in open(f):
        if l.startswith('#') or not l.strip(): continue
        a=l.strip().rsplit(',',4); h=a[0].split(',',2)
        yield [h[0],h[1],h[2],a[1],a[2]]
val=collections.OrderedDict(); rate={}
for g in groups:
    rate[g]={}
    for f in glob.glob(f'{fold}/{g}.m?.csv'):
        m=int(os.path.basename(f).split('.')[-2][1]); s=0
        for l in open(f):
            p=l.split(',')
            if p[0]=='T': s+=float(p[6])/float(p[7])
        rate[g][m]=s
    for f in sorted(glob.glob(f'{fold}/{g}.*.perf')):
        sn=os.path.basename(f).split('.')[-2]
        for p in rows(f):
            m=re.match(r'arm_cmn_(\d)/(\w+)',p[2]); mesh=int(m.group(1)); ev=m.group(2)
            if ev=='dtc_cycles' or p[0].startswith('<'): continue
            if 'nodeid' in p[2]: ev='SN_'+ev
            d=val.setdefault(ev,{}).setdefault(g,{0:0.0,1:0.0}); d[mesh]+=float(p[0])/(float(p[3])/1e9)/1e6
            if float(p[4])<99.9: d['mux']=1
sh=lambda g:g.replace('read_','').replace('asmread','asm')
print(f'{"M per second":30}'+''.join(f'{sh(g):>18}' for g in groups))
print(f'{"GB/s m0/m1":30}'+''.join(f'{rate[g][0]/1e9:9.0f}/{rate[g][1]/1e9:<8.0f}' for g in groups))
print(f'{"Mlines/s m0/m1":30}'+''.join(f'{rate[g][0]/64e6:9.2f}/{rate[g][1]/64e6:<8.2f}' for g in groups))
for ev,d in val.items():
    print(f'{ev:30}'+''.join((f'{d[g][0]:9.2f}/{d[g][1]:<8.2f}'+('' if 'mux' not in d[g] else '*') if g in d else f'{"-":>18}') for g in groups))
