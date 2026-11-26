import csv
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
own=[];oth=[];cores=set()
for r in csv.DictReader(open(R+'full/latency.csv')):
    m=int(r['mesh'])
    if m<0: continue
    c=int(r['core']); cores.add(c); cm=0 if c<64 else 1
    (own if m==cm else oth).append(float(r['ns_median']))
print(len(cores),min(own),max(own),min(oth),max(oth),len(own),len(oth))
n=list(csv.DictReader(open(R+'full/nodes.csv')))
print(set(r['lines'] for r in n), len(n))
