#!/usr/bin/env python3
import json, collections
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
f=json.load(open(S+'/facts.json'))
print(list(f.keys()))
print({k:(type(v).__name__, len(v) if hasattr(v,'__len__') else v) for k,v in f.items()})
iv=f['intervals']
print(len(iv)); print(json.dumps(iv[0],indent=0)[:1500])
c=collections.Counter((r.get('dataset'),r.get('part'),r.get('role'),r.get('speed_MTps'),r.get('kernel'),r.get('binary')) for r in iv)
for k,v in sorted(c.items(), key=lambda x:str(x)): print(v,k)
m=f['meta']; print(list(m.keys()))
print(json.dumps(m.get('launches'),indent=0)[:3000])
