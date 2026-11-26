#!/usr/bin/env python3
"""For each run of a journal: print the sentences that propose a per-target define, with the test they name."""
import json, re, sys
labels={};results={}
for line in open(sys.argv[1]):
    d=json.loads(line)
    if d.get("type")=="started": labels[d["agentId"]]=d["label"]
    elif d.get("type")=="result": results[d["agentId"]]=d.get("result")
DEF=re.compile(r"\bDEFINES\b|(?i:target_compile_definitions|per-target define|own (compile )?definition|passes? (the|its own) defin\w+|t_page_share_counters)")
only=sys.argv[2] if len(sys.argv)>2 else ""
for aid,res in sorted(results.items(), key=lambda kv: labels[kv[0]]):
    lab=labels[aid]
    if only and only not in lab: continue
    hits=[]
    for i,f in enumerate(res["findings"]):
        pc=str(f.get("proposed_change",""))
        for s in re.split(r"(?<=[.!?])\s+", pc):
            if DEF.search(s): hits.append((i+1,f["severity"],f.get("file","")[-40:],s.strip()[:330]))
    print(f"\n== {lab}: {len(res['findings'])} findings, {len(hits)} sentences that name a per-target define in a proposed change")
    for h in hits[:5]: print(f"   #{h[0]} [{h[1]}] {h[2]} :: {h[3]}")
