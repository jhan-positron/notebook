#!/usr/bin/env python3
"""anc.py FOLDER [mode]: mesh counters per 64 B line read (all threads), per mesh 'm0/m1'. mode=cyc gives counts per mesh cycle instead."""
import sys,glob,os,re,collections
fold=sys.argv[1]; mode=sys.argv[2] if len(sys.argv)>2 else 'line'
tags=[]; rate={}
for l in open(fold+'/launches.txt'):
    m=re.match(r'launch (\S+)',l)
    if m: tags.append(m.group(1))
for t in tags:
    for l in open(f'{fold}/{t}.csv'):
        if l.startswith('I,'): rate[t]=float(l.split(',')[-1])
val=collections.OrderedDict(); warn=set()
for t in tags:
    for f in sorted(glob.glob(f'{fold}/{t}.s*.perf')):
        cyc={}
        rows=[l.strip().split(',') for l in open(f) if l.strip() and not l.startswith('#')]
        for p in rows:
            m=re.match(r'arm_cmn_(\d)/(.*)/',p[2]); mesh=int(m.group(1)); ev=m.group(2)
            if p[0].startswith('<'): continue
            c=float(p[0]); sec=float(p[3])/1e9
            if float(p[4])<99.9: warn.add((t,ev,p[4]))
            if ev=='dtc_cycles': cyc[mesh]=c; continue
            lines=rate[t]*1e9*sec/64
            v=c/lines if mode=='line' else c/cyc[mesh]
            val.setdefault(ev,{}).setdefault(t,{})[mesh]=v
print('rate GB/s:',' '.join(f'{t}={rate[t]:.0f}' for t in tags))
print(f'{"event":34}'+''.join(f'{t[:13]:>15}' for t in tags))
for ev,d in val.items():
    print(f'{ev:34}'+''.join((f'{d[t][0]:7.3f}/{d[t][1]:<7.3f}' if t in d and len(d[t])==2 else f'{"-":>15}') for t in tags))
if warn: print('MULTIPLEXED:',sorted(warn)[:10],len(warn))
