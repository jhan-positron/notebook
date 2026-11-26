import re, os
S='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'; R='/home/jhan/workspace/titan/cache-perf/crb/results'
t=open(S+'/FACTS.md').read()
body,sec7=t.split('\n## 7. Files\n')
defs={}
for m in re.finditer(r'^- \[Ref(\d+)\] (.*)$',sec7,re.M):
    defs[int(m[1])]=m[2]
cited=set(int(x) for x in re.findall(r'\[Ref(\d+)\]',body))
print('defined',len(defs),'cited in body',len(cited))
print('cited but not defined',sorted(cited-set(defs)))
print('defined but not cited',sorted(set(defs)-cited))
print('numbering continuous', sorted(defs)==list(range(1,max(defs)+1)))
miss=[]
for n,d in sorted(defs.items()):
    m=re.match(r'`([^`]+)`',d)
    if not m: print('  no path: Ref%d %s'%(n,d[:90])); continue
    p=m[1].replace('R/',R+'/',1) if m[1].startswith('R/') else (m[1].replace('S/',S+'/',1) if m[1].startswith('S/') else m[1])
    if not os.path.isfile(p): miss.append((n,p))
print('missing files',miss)
