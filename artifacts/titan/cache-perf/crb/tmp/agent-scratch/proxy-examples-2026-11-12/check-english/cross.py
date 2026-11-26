import re,sys
rows=[];cpu=b=None
for l in open('results/followup2-20261031T073513Z/cross.csv'):
    m=re.search(r'cpu=(\d+)',l)
    if l.startswith('# latency') and m: cpu=int(m.group(1));continue
    m=re.search(r'build_cpu=(\d+)',l)
    if m: b=int(m.group(1));continue
    p=l.strip().split(',')
    if len(p)==4 and p[0].isdigit(): rows.append((b,cpu,int(p[0])>>20,p[1],float(p[3])))
for r in rows:
    if r[3]!='best': print(r)
# per-core 16 MiB
pc={};cpu=None
for l in open('results/followup3-20261102T031936Z/percore-latency-1.csv'):
    m=re.search(r'cpu=(\d+)',l)
    if l.startswith('# latency') and m: cpu=int(m.group(1));continue
    p=l.strip().split(',')
    if len(p)==4 and p[0].isdigit() and int(p[0])==16<<20: pc.setdefault(cpu,[]).append((p[1],float(p[3])))
for c in (3,64,67,119): print(c,pc.get(c))
for b,w,s,rep,v in rows:
    if s==16 and rep=='fresh2' and b//64!=w//64:
        for rp,x in pc[w]: print('pair',b,w,'second',v,'own',rp,x,'diff',round(v-x,2))
