import re
S="/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
L=open(S+"/FACTS.md").read().split("\n")
tre=re.compile(r"(?<![\dT:\-])(\d{1,2}:\d{2}(?::\d{2})?)(?![\d:])")
dre=re.compile(r"20\d\d-\d\d-\d\d")
out=[]
for n,l in enumerate(L,1):
    if l.startswith("|"):
        units=[c for c in l.split("|")]
    else:
        # split sentences on ". " followed by capital or end
        units=re.split(r"(?<=[\.\:])\s+(?=[A-Z\"`\(\[])",l)
    for u in units:
        ts=tre.findall(u)
        if not ts: continue
        # ignore things like "64+56", ratios; keep only times
        hasdate=bool(dre.search(u))
        if not hasdate:
            out.append((n,ts,u.strip()[:230]))
print(len(out))
for n,ts,u in out: print(n,ts,"::",u)
