#!/usr/bin/env python3
# sumdiff.py - largest difference between the sum of the 120 thread rows and the rate printed in the interval row, over the bwx12 intervals the page uses.
import json
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
R='/home/jhan/workspace/titan/cache-perf/crb/results'
f=json.load(open(S+'/facts.json')); iv=f['intervals']
cache={}
def lines(p):
    if p not in cache: cache[p]=open(p).read().split('\n')
    return cache[p]
worst=(0,None); n=0
for r in iv:
    if r['dataset'] not in ('rerun-L','rerun-C','control-I','F72d12','L-1','L-2','L-3','L-4'): continue
    if r['kernel'] not in ('oldread','asmread','read'): continue
    L=lines(r['folder'].replace('R/',R+'/',1)+'/'+r['file']); i=r['line']-1
    q=L[i].split(','); assert q[0]=='I' and q[3]==r['kernel'],(L[i][:60],r['kernel'])
    printed=float(q[8]); s=0;k=0
    for x in L[i+1:]:
        if not x.startswith('T,'): break
        t=x.split(','); s+=int(t[6])/float(t[7]); k+=1
    assert k==120
    d=abs(s/1e9-printed); n+=1
    if d>worst[0]: worst=(d,(r['dataset'],r['kernel'],r['line'],printed,round(s/1e9,4)))
print(n,'intervals; largest difference %.4f GB/s'%worst[0],worst[1])
