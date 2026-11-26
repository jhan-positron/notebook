import json
from collections import Counter,defaultdict
S="/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
b=json.load(open(S+"/facts.json"))
iv=b["intervals"]
print(list(iv[0].keys()))
print(json.dumps(iv[398],indent=0)[:1500])
c=Counter((r.get("dataset"),r.get("binary"),r.get("speed_MTps"),r.get("modules"),r.get("kernel")) for r in iv)
g=defaultdict(list)
for r in iv:
    if r.get("kernel")=="oldread": g[(r.get("dataset"),r.get("binary"),r.get("speed_MTps"),r.get("modules"),r.get("boot"))].append(r)
tot=0; mn=None
for k,v in sorted(g.items(),key=str):
    vals=[x["GBps"] for x in v]
    print(k,len(v),"%.2f to %.2f"%(min(vals),max(vals)), Counter(x.get("pos") for x in v))
    if k[2]==8000 and k[3]==12:
        tot+=len(v)
        m=min(v,key=lambda x:x["GBps"])
        if mn is None or m["GBps"]<mn["GBps"]: mn=m
print("oldread at 8000, 12 modules:",tot,"lowest",mn["GBps"],mn.get("dataset"),mn.get("proc_key"))
print(json.dumps(b["meta"]["fields"]["kernel_before"],indent=1))
for k in ("F72d12_boot","firmware_settings","hardware_error_records"):
    print("=====",k); print(json.dumps(b["meta"][k],indent=1)[:6000])
