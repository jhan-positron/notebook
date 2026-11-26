import csv,statistics as st
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/full/latency.csv'
own=[];oth=[]
for r in csv.DictReader(open(R)):
    if r['mesh']=='-1': continue
    c=int(r['core']); m=int(r['mesh']); v=float(r['ns_median'])
    (own if m==(0 if c<64 else 1) else oth).append(v)
for n,a in (('own',own),('other',oth)):
    print(n,len(a),min(a),max(a),round(st.mean(a),2),round(st.median(a),2))
