#!/usr/bin/env python3
"""an.py FOLDER [file...]: per interval of each csv: total and per-mesh rate (GB/s), per-thread range, and each counter per 64 B line per mesh."""
import sys,glob,os,collections
fold=sys.argv[1]; files=sys.argv[2:] or sorted(os.path.basename(x) for x in glob.glob(fold+'/*.csv'))
for f in files:
    T=collections.OrderedDict(); C={}; ev=None; copyk=False
    for l in open(os.path.join(fold,f)):
        p=l.rstrip('\n').split(',')
        if l.startswith('#') and 'C,round' in l:
            h=l.strip('# \n').split(';')[0].split(','); ev=h[9:]
        if p[0]=='T': T.setdefault((p[1],p[2],p[3]),{})[int(p[5])]=(float(p[6]),float(p[7]))
        if p[0]=='C': C[(p[1],p[2],p[3],int(p[5]))]=[float(x) for x in p[6:]]
    print('==',f,'events per line (mesh0 | mesh1):',ev)
    for k,v in T.items():
        div=2 if 'copy' in k[2] else 1
        out=f'{k[0]} {k[1]:>2} {k[2]:14}'
        tot=0; parts=[]
        for lo,hi in ((0,64),(64,128)):
            cs=[c for c in v if lo<=c<hi]
            if not cs: parts.append('      -                 '); continue
            r=[v[c][0]/v[c][1]/1e9 for c in cs]; tot+=sum(r)
            parts.append(f'{sum(r):6.1f} ({min(r):.2f}-{max(r):.2f})')
        out+=f' tot {tot:6.1f} m0 {parts[0]} m1 {parts[1]}'
        if ev:
            for lo,hi in ((0,64),(64,128)):
                cs=[c for c in v if lo<=c<hi and k+(c,) in C]
                if not cs: continue
                lines=sum(v[c][0] for c in cs)/64/div
                s=[sum(C[k+(c,)][i] for c in cs) for i in range(3+len(ev))]
                out+=' |'+' '.join(f'{s[3+i]/lines:7.3f}' for i in range(len(ev)))
                if s[1]<0.999*s[0]: out+=f' RUN{s[1]/s[0]:.2f}'
        print(out)
