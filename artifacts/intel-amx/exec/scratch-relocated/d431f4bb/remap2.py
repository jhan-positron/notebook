import json, re, datetime
R="/home/jhan/workspace/intel-AMX/exec/results/q4b-fpga-20260921"
J=R+"/hbm-journal-20260921.txt"
tags=["canon-pass1","fpgabase-cold-p4096","fpgabase-cold-p8192","fpgabase-pass1","fpgacanon-cold-p4096","fpgacanon-cold-p8192","fpgacanon-pass1"]
cells=[]
for t in tags:
    d=json.load(open(f"{R}/{t}/perf.json"))
    for r in d["raw"]:
        cells.append(dict(tag=t,prompt=r["prompt_length"],t_start=r["t_start"],t_end=r["t_end"],lose=0))
pat=re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\+0000 .*lose HW attention")
inside=outside=0
for line in open(J):
    m=pat.search(line)
    if not m: continue
    ts=datetime.datetime.strptime(m.group(1),"%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp()
    hit=[c for c in cells if c["t_start"]<=ts<=c["t_end"]]
    if hit: inside+=1; hit[0]["lose"]+=1
    else: outside+=1
print("prefix-second timestamps: inside",inside,"outside",outside)
for c in cells:
    if c["lose"]: print(c["tag"],c["prompt"],c["lose"])
