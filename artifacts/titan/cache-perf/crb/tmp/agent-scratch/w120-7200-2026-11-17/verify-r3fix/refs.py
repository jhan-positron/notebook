import re,os
S="/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
R="/home/jhan/workspace/titan/cache-perf/crb/results"
L=open(S+"/FACTS.md").read().split("\n")
# find section 7 start
s7=[i for i,l in enumerate(L) if l.startswith("## 7")][0]
print("section 7 starts at line",s7+1,L[s7])
defs={}
for i,l in enumerate(L[s7:],s7+1):
    m=re.match(r"- \[Ref(\d+)\] (.*)",l)
    if m:
        n=int(m.group(1)); assert n not in defs,("dup",n); defs[n]=(i,m.group(2))
print("defined:",len(defs),"min",min(defs),"max",max(defs),"missing numbers:",[n for n in range(1,max(defs)+1) if n not in defs])
cited={}
for i,l in enumerate(L[:s7],1):
    for m in re.finditer(r"\[Ref(\d+)\]",l):
        cited.setdefault(int(m.group(1)),[]).append(i)
print("cited not defined:",[n for n in cited if n not in defs])
print("defined not cited in sections 0-6:",[n for n in sorted(defs) if n not in cited])
miss=[]
for n,(i,t) in sorted(defs.items()):
    m=re.match(r"`([^`]+)`",t)
    if not m:
        if n>=135: print("  no path:",n,t[:100])
        continue
    p=m.group(1)
    if p.startswith("R/"): p=R+p[1:]
    elif p.startswith("S/"): p=S+p[1:]
    if not os.path.exists(p): miss.append((n,p))
print("files missing:",miss)
for n in list(range(150,164))+[19,20,23,67,69,70,71,73,75,77,78,80,82,84,86,87,88,90,92,93,95,97,98,99,101,119,120,121,135,136,137,139,140,141,31,35,39,43,47,51,55,59,63,123,125,127,129,7,8,10,22,25,27,29]:
    print(n,"cited at",cited.get(n,[])[:12],"|",defs[n][1][:150])
