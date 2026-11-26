import re, os, sys
t=open(sys.argv[1],encoding='utf-8').read()
R="/home/jhan/workspace/titan/cache-perf/crb/results"
S="/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
refs=[]
for line in t.splitlines():
    m=re.match(r'- \[Ref(\d+)\] (\S+?)(?: \(([^)]*)\))?: (.*)$',line)
    if m:
        n=int(m.group(1)); p=m.group(2); note=m.group(3); desc=m.group(4)
        full=p.replace('R/',R+'/',1) if p.startswith('R/') else p.replace('S/',S+'/',1) if p.startswith('S/') else p
        refs.append((n,p,full,note,desc))
print(len(refs),'refs')
missing=0
for n,p,full,note,desc in refs:
    ex=os.path.exists(full)
    if not ex: missing+=1
    print(f"Ref{n}\t{'OK ' if ex else 'MISSING'}\t{os.path.getsize(full) if ex and os.path.isfile(full) else '-'}\t{p}\t{note or ''}")
print('missing',missing)
# cited in body
body=t.split('## References')[0]
cited=set(int(x) for x in re.findall(r'\[Ref(\d+)\]',body))
allc=set(int(x) for x in re.findall(r'\[Ref(\d+)\]',t.split('## References')[1].split('R = ')[0]))
print('cited in body before References heading:',len(cited),'cited in the References intro:',sorted(allc))
print('not cited anywhere:',[n for n,*_ in refs if n not in cited|allc])
order=[int(x) for x in re.findall(r'\[Ref(\d+)\]',t)]
first=[]
for x in order:
    if x not in first: first.append(x)
print('first-use order monotone:', first[:len(refs)]==sorted(first[:len(refs)]), first[:70])
