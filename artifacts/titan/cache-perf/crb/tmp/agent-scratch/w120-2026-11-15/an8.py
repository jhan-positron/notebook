#!/usr/bin/env python3
"""an8.py FOLDER...: per csv, kernel, round and mesh: rate GB/s, responses per 64 B line, and share of busy level 0,1,2,3 (percent of all counted responses)."""
import sys,glob,os,collections
for fold in sys.argv[1:]:
    for path in sorted(glob.glob(fold+'/*.csv')):
        T=collections.OrderedDict(); C={}
        for l in open(path):
            p=l.rstrip('\n').split(',')
            if p[0]=='T': T.setdefault((p[1],p[2],p[3]),{})[int(p[5])]=(float(p[6]),float(p[7]))
            if p[0]=='C': C[(p[1],p[2],p[3],int(p[5]))]=[float(x) for x in p[6:]]
        for k,v in T.items():
            for name,lo,hi in (('half0',0,64),('half1',64,128)):
                cs=[c for c in v if lo<=c<hi and k+(c,) in C]
                if not cs: continue
                rate=sum(v[c][0]/v[c][1] for c in cs)/1e9
                lines=sum(v[c][0] for c in cs)/64
                s=[sum(C[k+(c,)][3+i] for c in cs) for i in range(4)]
                tot=sum(s)
                print(f'{os.path.basename(path):24} r{k[0]} {k[2]:12} {name} n={len(cs):3} {rate:6.1f} GB/s  resp/line {tot/lines:5.2f}  L0 {100*s[0]/tot:5.1f}%  L1 {100*s[1]/tot:5.1f}%  L2 {100*s[2]/tot:5.1f}%  L3 {100*s[3]/tot:5.1f}%  L3/line {s[3]/lines:5.2f}')
