#!/usr/bin/env python3
# Round 3, lens claims: the note "Other runner binary" under Table 2.
import json, collections
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
d=json.load(open(S+'/facts.json')); iv=d['intervals']
B=[r for r in iv if r['dataset'] in('B7a','B7b','C3a','C3b')]
print('n all',len(B),'procs',len({r['proc_key'] for r in B}))
c=collections.Counter((r['kernel'],r['pos'],r['kernel_before']) for r in B)
for k,v in sorted(c.items(),key=str): print(v,k)
lo=[r for r in B if r['kernel'] in('read','asmread')]
print('load-only n',len(lo),'procs',len({r['proc_key'] for r in lo}), 'min',min(r['GBps'] for r in lo),'max',max(r['GBps'] for r in lo))
for k in('read','asmread'):
    print(k,'max',max(r['GBps'] for r in lo if r['kernel']==k), 'min', min(r['GBps'] for r in lo if r['kernel']==k))
grp=collections.defaultdict(list)
for r in lo: grp[(r['kernel'],r['kernel_before'])].append(r)
for k,v in grp.items(): print(k,len(v),len({r['proc_key'] for r in v}),min(r['GBps'] for r in v),max(r['GBps'] for r in v))
C=[r for r in iv if r['dataset']=='rerun-C']
cg=collections.defaultdict(list)
for r in C:
    if r['kernel'] in('read','asmread'): cg[(r['kernel'],r['kernel_before'])].append(r['GBps'])
for k,v in cg.items():
    print('partC',k,min(v),max(v), 'bwx max', max((r['GBps'] for r in grp.get(k,[])),default=None), 'dist', (min(v)-max(r['GBps'] for r in grp[k])) if k in grp else None)
R=[r for r in iv if r['dataset'] in('B5a-rev','B5b-rev')]
for r in sorted(R,key=lambda r:(r['dataset'],r['tag'],r['pos'])): print(r['dataset'],r['tag'],r['pos'],r['kernel'],r['kernel_before'],r['GBps'],r['folder'],r['file'],r['line'],r['launch_utc'])
Fw=[r for r in iv if r['dataset'] in('B5a','B5b')]
for r in sorted(Fw,key=lambda r:(r['dataset'],r['tag'],r['pos'])): print(r['dataset'],r['tag'],r['pos'],r['kernel'],r['kernel_before'],r['GBps'])
print(sorted({(r['dataset'],r['folder']) for r in iv if r['binary']=='bwx'}))
