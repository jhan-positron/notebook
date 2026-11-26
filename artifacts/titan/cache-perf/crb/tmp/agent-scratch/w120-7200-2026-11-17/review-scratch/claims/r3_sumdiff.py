#!/usr/bin/env python3
# Round 3, lens claims: "This sum differs from the rate printed in the interval row by at most 0.02 GB/s" (bwx12 rows of the page).
import json, os, collections
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
R='/home/jhan/workspace/titan/cache-perf/crb/results'
d=json.load(open(S+'/facts.json')); iv=d['intervals']
used=[r for r in iv if r['binary']=='bwx12' and r['dataset'] in('rerun-L','rerun-C','control-I','F72d12','L-1','L-2','L-3','L-4') and r['kernel'] in('oldread','asmread','read')]
used=[r for r in used if not (r['dataset'] in('L-1','L-2','L-3','L-4') and not ((r['kernel']=='oldread' and r['pos']==0) or (r['kernel']=='asmread' and r['pos']==1)))]
cache={}
worst=(0,None); allw=[]
for r in used:
    p=r['folder'].replace('R/',R+'/')+'/'+r['file']
    if p not in cache: cache[p]=open(p).read().split('\n')
    L=cache[p]; i=r['line']-1
    assert L[i].startswith('I,'), (p,r['line'],L[i][:40])
    agg=float(L[i].split(',')[8]); s=0.0; n=0
    for l in L[i+1:i+1+400]:
        if l.startswith('T,'):
            f=l.split(','); s+=int(f[6])/float(f[7])/1e9; n+=1
        elif l.startswith('I,'): break
    assert n==120,(p,n)
    dd=abs(s-agg); allw.append((dd,r['dataset'],r['tag'],r['kernel'],r['round'],round(s,4),agg, r['GBps']))
    if abs(round(s,3)-r['GBps'])>0.0011: print('facts mismatch',r['dataset'],s,r['GBps'])
allw.sort(reverse=True)
print(len(used),'intervals; largest |sum - I row|:'); 
for w in allw[:6]: print(w)
