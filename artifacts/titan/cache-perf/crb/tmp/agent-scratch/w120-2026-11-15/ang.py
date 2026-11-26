#!/usr/bin/env python3
"""ang.py FOLDER: per group of simultaneous processes: rate sum and per-thread range of each process, and start times."""
import sys,glob,os,re
fold=sys.argv[1]
groups=[re.match(r'launch (\S+)',l).group(1) for l in open(fold+'/launches.txt') if l.startswith('launch')]
for g in groups:
    out=f'{g:30}'; tot=0
    for f in sorted(glob.glob(f'{fold}/{g}.*.csv')):
        tag=os.path.basename(f).split('.')[-2]; r=[]; k=''; ts=[]
        for l in open(f):
            p=l.split(',')
            if p[0]=='T': r.append(float(p[6])/float(p[7])/1e9); k=p[3]; ts.append(float(p[9]))
        tot+=sum(r); out+=f' {tag}:{k:11} {sum(r):6.1f} ({min(r):.2f}-{max(r):.2f}) t0={min(ts):.1f}'
    print(out+f'  total {tot:6.1f}')
