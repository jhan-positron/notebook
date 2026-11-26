import sys, glob, re, os
sys.path.insert(0, "/home/jhan/workspace/titan/cache-perf/asimov")
from gen_run3 import lat_rows
R="/home/jhan/workspace/titan/cache-perf/asimov/results"
def show(pat, label):
    print("=====", label)
    for p in sorted(glob.glob(pat)):
        rows=[d for d in lat_rows(p) if d["rep"]!="-"]
        for d in rows:
            print(os.path.basename(p), d["size"], d["mode"], d["rep"], d["ns"], "c1",d.get("c1"),"c2",d.get("c2"),"c3",d.get("c3"), {k:v for k,v in d.items() if k.startswith("c") and k not in("c1","c2","c3","cyc","cov","cme")})
show(R+"/membench-jibin-002/results/*/latency-ocm-region*-cpu*.csv","run2 region rows")
show(R+"/membench-jibin-002/results/*/latency-ocm-all5-cpu2.csv","run2 all5 cpu2")
show(R+"/membench-jibin-004/results/*/latency-ocm-region*-cpu*.csv","run3 sparse region rows")
show(R+"/membench-jibin-004/results/*/latency-ocm-all5*-cpu2.csv","run3 all5 cpu2")
