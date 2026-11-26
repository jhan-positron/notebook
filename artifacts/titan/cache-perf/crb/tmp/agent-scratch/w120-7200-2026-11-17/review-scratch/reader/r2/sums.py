#!/usr/bin/env python3
# sums.py - sum of the 120 thread rows (bytes / elapsed) for the four intervals behind the two differences 39.38 and 1.73 GB/s.
import json
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
R='/home/jhan/workspace/titan/cache-perf/crb/results'
f=json.load(open(S+'/facts.json')); iv=f['intervals']
def rate(r):
    p=r['folder'].replace('R/',R+'/',1)+'/'+r['file']
    L=open(p).read().split('\n')
    i=r['line']-1
    assert L[i].startswith('I,'),L[i][:40]
    s=0;n=0
    for x in L[i+1:]:
        if not x.startswith('T,'): break
        q=x.split(','); s+=int(q[6])/float(q[7]); n+=1
    assert n==120,n
    return s/1e9
def pick(ds,kernel,fn):
    rs=[r for r in iv if r['dataset'] in ds and r['kernel']==kernel]
    v=[(rate(r),r['GBps'],r['folder'],r['line']) for r in rs]
    return fn(v)
a=pick(('rerun-L',),'asmread',max); b=pick(('L-1','L-2','L-3','L-4'),'asmread',min)
c=pick(('F72d12',),'asmread',min); d=pick(('L-1',),'asmread',max)
for n,x in (('part L highest asmread',a),('pool lowest asmread',b),('F72d12 lowest asmread',c),('L-1 highest asmread',d)): print(n,'%.4f'%x[0],x[1:])
print('farthest ends: %.4f (rounded operands %.2f)'%(a[0]-b[0], round(a[0],2)-round(b[0],2)))
print('F72d12 above L-1: %.4f (rounded operands %.2f)'%(c[0]-d[0], round(c[0],2)-round(d[0],2)))
