import json, re, sys, statistics
R="/home/jhan/workspace/intel-AMX/exec/results/"
def runs(path):
    out=[];cur=None
    for i,line in enumerate(open(path,errors="replace"),1):
        m=re.match(r"### runtron tp=(\d) prompt=(\d+) arm=(\S+) rep=(\d+) attempt=(\d+) (.*)",line)
        if m:
            cur={"tp":int(m[1]),"prompt":int(m[2]),"arm":m[3],"rep":int(m[4]),"attempt":int(m[5]),"hdr":m[6].strip(),"line":i,"ttft":[],"ttft_lines":[],"hw":None,"ver":None,"status":"ok","tps":[]}
            out.append(cur);continue
        if cur is None: continue
        if line.startswith(("RUN-STOPPED","RUN-FAILED","RUN-GIVEN-UP")): cur["status"]=line.split()[0]
        m=re.search(r"Parsing the prompt took ([\d.]+) s",line)
        if m: cur["ttft"].append(float(m[1])); cur["ttft_lines"].append(i)
        m=re.search(r"HW attention (enabled|disabled)[^\n]*",line)
        if m: cur["hw"]=m[0][:120]
        m=re.search(r"Version: (\S+) hash: (\S+)",line)
        if m: cur["ver"]=m[1]
        m=re.search(r"at ([\d.]+) average tok/s",line)
        if m: cur["tps"].append(float(m[1]))
    return out
for camp in ["vnnik4-20260915"]:
    p=R+camp+"/rt-results.txt"
    rs=runs(p)
    print("=====",camp, "runs",len(rs))
    # unique arm -> (bin, tip, env, version)
    combos={}
    for r in rs:
        mb=re.search(r"bin=(\S+)",r["hdr"]); mt=re.search(r"tip=(\S+)",r["hdr"]); me=re.search(r"env=(.*?) len=",r["hdr"])
        combos.setdefault((r["arm"],mb[1] if mb else None,mt[1] if mt else None,me[1] if me else None,r["ver"]),0)
        combos[(r["arm"],mb[1] if mb else None,mt[1] if mt else None,me[1] if me else None,r["ver"])]+=1
    for k,v in sorted(combos.items()): print("  ARM",k,"runs",v)
    hw=set(r["hw"] for r in rs); print("  HW lines:",hw)
    st=set(r["status"] for r in rs); print("  statuses:",st)
    # per cell
    cells={}
    for r in rs:
        if r["status"]!="ok" or not r["tps"]: continue
        cells.setdefault((r["tp"],r["prompt"],r["arm"]),[]).append(r)
    for k in sorted(cells):
        reps=cells[k]
        vals=[max(r["ttft"]) for r in reps]
        spread=[ (max(r["ttft"])-min(r["ttft"]))*1000 for r in reps]
        dates=[re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)",r["hdr"])[1] for r in reps]
        m=statistics.mean(vals); sd=statistics.stdev(vals) if len(vals)>1 else 0.0
        print(f"  CELL tp{k[0]} p{k[1]} {k[2]:8s} n={len(reps)} ttft_ms={m*1000:.1f} sd_ms={sd*1000:.1f} reps_ms={[round(v*1000,1) for v in vals]} nreq={[len(r['ttft']) for r in reps]} within-run-spread_ms={[round(s,2) for s in spread]} tps={statistics.mean([statistics.mean(r['tps']) for r in reps]):.2f} hdr_lines={[r['line'] for r in reps]} ttft_lines={[r['ttft_lines'][0] for r in reps]}-{[r['ttft_lines'][-1] for r in reps]} dates={dates}")
