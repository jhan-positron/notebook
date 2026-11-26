import json, sys, os
D="/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-GDN/be74f0ef-9ecd-4d0b-b01e-43155cd9bc79/subagents/workflows/"+sys.argv[1]
out=sys.argv[2]; os.makedirs(out, exist_ok=True)
labels={}
for line in open(D+"/journal.jsonl"):
    j=json.loads(line)
    if j.get('type')=='started': labels[j['agentId']]=j.get('label','?')
    if j.get('type')=='result':
        r=j.get('result')
        if isinstance(r,str):
            try: r=json.loads(r)
            except Exception: pass
        lab=labels.get(j.get('agentId'),'?').replace(':','_')
        json.dump(r,open(f"{out}/{lab}.json","w"),indent=1)
        with open(f"{out}/{lab}.txt","w") as f:
            def w(k,v): f.write(f"\n## {k}\n{v}\n")
            if isinstance(r,dict):
                for k,v in r.items():
                    if k=='components':
                        for c in v:
                            f.write(f"\n=== COMPONENT: {c['name']}  [{c['verdict']}]  target: {c['target']}\n")
                            for kk in ('idea','algorithm','amx_mapping','numerics','cost_estimate','expected_kernel_speedup','code_changes','risks'):
                                f.write(f"--- {kk}: {c[kk]}\n")
                    elif isinstance(v,list):
                        f.write(f"\n## {k}\n")
                        for x in v: f.write("  - "+(json.dumps(x) if not isinstance(x,str) else x)+"\n")
                    else: w(k,v)
            else: f.write(str(r))
        print(lab, os.path.getsize(f"{out}/{lab}.txt"))
