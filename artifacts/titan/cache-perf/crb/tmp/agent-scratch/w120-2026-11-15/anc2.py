#!/usr/bin/env python3
"""anc2.py FOLDER: memory-port (SN-F) flit counts per 64 B line read, and the memory-controller PMU event scan."""
import sys,glob,re,collections
fold=sys.argv[1]
tags=[re.match(r'launch (\S+)',l).group(1) for l in open(fold+'/launches.txt') if l.startswith('launch')]
rate={}
for t in tags:
    for l in open(f'{fold}/{t}.csv'):
        if l.startswith('I,'): rate[t]=float(l.split(',')[-1])
def rows(f):
    for l in open(f):
        if l.startswith('#') or not l.strip(): continue
        a=l.strip().rsplit(',',4); h=a[0].split(',',2)
        yield [h[0],h[1],h[2],a[1],a[2]]
print('rate',rate)
print('== SN ports: per line read; sum over 12 ports of mesh0 / mesh1; then per-port min-max of mesh 0 (per line)')
for s in ('snreq','snwdat','snrdat','snmesh','snrsp'):
    for t in tags:
        acc=collections.defaultdict(lambda:[0,0]); per=collections.defaultdict(list); mux=0
        for p in rows(f'{fold}/{t}.{s}.perf'):
            m=re.match(r'arm_cmn_(\d)/(\w+)',p[2]); 
            if m.group(2)=='dtc_cycles': continue
            ch=re.search(r'wp_chn_sel=(\d)',p[2]); ev=m.group(2)+(('_ch'+ch.group(1)) if ch else '')
            if p[0].startswith('<'): acc[ev+'_NS'][int(m.group(1))]+=1; continue
            lines=rate[t]*1e9*float(p[3])/1e9/64
            acc[ev][int(m.group(1))]+=float(p[0])/lines; 
            if m.group(1)=='0': per[ev].append(float(p[0])/lines)
            if float(p[4])<99.9: mux+=1
        print(f'{s:7}{t:12}'+'  '.join(f'{e}={v[0]:.4f}/{v[1]:.4f} [{min(per[e]):.3f}-{max(per[e]):.3f}]' if per[e] else f'{e}={v}' for e,v in acc.items())+(f' MUX{mux}' if mux else ''))
print('== MC PMU scan: event k: sum over 48 instances per line read; nonzero instances')
for k in range(40):
    out=f'ev{k:2}'; anyv=False
    for t in tags:
        tot=0; nz=0; ns=0
        for p in rows(f'{fold}/{t}.mc{k:02d}.perf'):
            if 'cspmu' not in p[2]: continue
            if p[0].startswith('<'): ns+=1; continue
            c=float(p[0]); tot+=c/(rate[t]*1e9*float(p[3])/1e9/64); nz+=c>0
        out+=f'  {t}: {tot:10.4f} nz{nz} ns{ns}'; anyv|=tot>0
    if anyv: print(out)
