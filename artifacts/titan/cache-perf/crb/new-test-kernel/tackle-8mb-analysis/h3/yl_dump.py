#!/usr/bin/env python3
"""yl_dump.py <YL.csv>: per process: window rates in window-index order (GB/s). For the one-window runs: the 10 ms bins as rates,
averaged over 10 bins (0.1 s), so that level switches can be seen."""
import sys
cur=None; out=[]
for line in open(sys.argv[1]):
    line=line.rstrip('\n')
    if line.startswith('-- step'):
        f=line.split(); cur={'tag':f[f.index('tag')+1],'W':[],'B':[],'cond':''}; out.append(cur)
    elif cur is None: continue
    elif line.startswith('S,'): cur['cond']=line.split(',')[2]
    elif line.startswith('W,'):
        p=line.split(','); cur['W'].append((int(p[6]),int(p[7]),int(p[8])))
    elif line.startswith('B,'):
        p=line.split(','); cur['B'].append((int(p[4]),int(p[5])))
for c in out:
    print(c['tag'], c['cond'])
    if c['B']:
        t0=c['W'][0][1]; pt,pb=t0,0; r=[]
        step=10
        for i in range(step-1,len(c['B']),step):
            t,b=c['B'][i]; r.append((b-pb)/(t-pt)); pt,pb=t,b
        for i in range(0,len(r),30): print('   %5.1fs '%(i*0.1)+' '.join('%4.1f'%x for x in r[i:i+30]))
    else:
        r=[b/(e-s) for b,s,e in c['W']]
        for i in range(0,len(r),30): print('   w%-4d '%i+' '.join('%4.1f'%x for x in r[i:i+30]))
