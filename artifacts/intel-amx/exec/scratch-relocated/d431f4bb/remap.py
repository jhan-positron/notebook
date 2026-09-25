import json, re, datetime, glob, os
R="/home/jhan/workspace/intel-AMX/exec/results/q4b-fpga-20260921"
J=R+"/hbm-journal-20260921.txt"
tags=["canon-pass1","fpgabase-cold-p4096","fpgabase-cold-p8192","fpgabase-pass1","fpgacanon-cold-p4096","fpgacanon-cold-p8192","fpgacanon-pass1"]
cells=[]
for t in tags:
    d=json.load(open(f"{R}/{t}/perf.json"))
    for r in d["raw"]:
        cells.append(dict(tag=t,prompt=r["prompt_length"],t_start=r["t_start"],t_end=r["t_end"],lose=0,eng=set(),bases=set(),exh=0))
cells.sort(key=lambda c:c["t_start"])
pat_lose=re.compile(r"^(\d{4}-\d\d-\d\d)T(\d\d:\d\d:\d\d)\+0000 \S+ rinzler\[(\d+)\]: \[(\d\d:\d\d:\d\d\.\d+)\|rz(\d)/4\|.*shard base tok_ix (\d+) on dev (\d+): .*(\d+) of (\d+) slots lose HW attention")
pat_exh=re.compile(r"^(\d{4}-\d\d-\d\d)T(\d\d:\d\d:\d\d)\+0000 \S+ rinzler\[(\d+)\]: \[(\d\d:\d\d:\d\d\.\d+)\|rz(\d)/4\|.*HBM bypass space exhausted")
n_lose=n_exh=0; inside=0; outside=0; first=None; last=None
outside_ts=[]
slots_forms=set()
avail=set()
for line in open(J):
    m=pat_lose.search(line)
    if m:
        n_lose+=1
        date,sec,pid,inner,rz,tok,dev,a,b=m.groups()
        slots_forms.add((a,b))
        ts=datetime.datetime.strptime(date+"T"+inner[:15],"%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=datetime.timezone.utc).timestamp()
        # handle date rollover: inner uses same date as prefix (both UTC)
        if first is None: first=(date,sec,inner)
        last=(date,sec,inner)
        hit=None
        for c in cells:
            if c["t_start"]<=ts<=c["t_end"]:
                hit=c;break
        if hit:
            inside+=1; hit["lose"]+=1; hit["eng"].add(rz); hit["bases"].add(int(tok))
        else:
            outside+=1; outside_ts.append(ts)
        continue
    m=pat_exh.search(line)
    if m:
        n_exh+=1
        mm=re.search(r"only (0x[0-9A-Fa-f]+) available",line); 
        if mm: avail.add(mm.group(1))
print("lose",n_lose,"exhausted",n_exh,"inside",inside,"outside",outside)
print("first",first,"last",last)
print("slot forms",slots_forms)
print("avail values",avail)
def iso(t): return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).strftime("%H:%M:%S")
for c in cells:
    print(f"{c['tag']:22s} p{c['prompt']:<5d} {iso(c['t_start'])}-{iso(c['t_end'])} lose={c['lose']:4d} eng={len(c['eng'])} bases={sorted(c['bases'])}")
# outside: which gaps
import collections
gaps=collections.Counter()
for ts in outside_ts:
    prev=[c for c in cells if c["t_end"]<ts]; nxt=[c for c in cells if c["t_start"]>ts]
    p=prev[-1] if prev else None; n=nxt[0] if nxt else None
    gaps[( (p["tag"],p["prompt"]) if p else None, (n["tag"],n["prompt"]) if n else None)]+=1
for k,v in sorted(gaps.items(), key=lambda kv: -kv[1]): print("gap",k,v)
# compare with JSON
Jm=json.load(open("/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/hbm-exhaustion-cells.json"))
for jc in Jm["cells"]:
    mc=[c for c in cells if c["tag"]==jc["tag"] and c["prompt"]==jc["prompt"]][0]
    ok = jc["lose"]==mc["lose"] and jc["engines"]==len(mc["eng"]) and jc["tok_bases"]==sorted(mc["bases"]) and abs(jc["t_start"]-mc["t_start"])<1e-3 and abs(jc["t_end"]-mc["t_end"])<1e-3
    if not ok: print("MISMATCH",jc["tag"],jc["prompt"],jc["lose"],mc["lose"],jc["engines"],len(mc["eng"]),jc["tok_bases"],sorted(mc["bases"]))
print("json vs remap check done")
