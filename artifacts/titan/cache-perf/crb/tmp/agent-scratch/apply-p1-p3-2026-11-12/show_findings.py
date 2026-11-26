#!/usr/bin/env python3
"""Print the findings of one agent of a workflow from its journal.
Usage: show_findings.py <journal.jsonl> <label substring> [max chars per field]"""
import json, sys
jr, want = sys.argv[1], sys.argv[2]
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 700
started = {}
for line in open(jr):
    try: j = json.loads(line)
    except Exception: continue
    if j.get("type") == "started": started[j.get("agentId")] = j.get("label")
    if j.get("type") != "result": continue
    label = started.get(j.get("agentId"), "?")
    if want not in label: continue
    r = j.get("result")
    if isinstance(r, str):
        try: r = json.loads(r)
        except Exception: pass
    print("AGENT", label)
    if not isinstance(r, dict): print(str(r)[:4000]); continue
    for k in ("lines_read", "checked", "notes"):
        if r.get(k): print(f"{k}: {str(r[k])[:1800]}")
    for f in r.get("findings", []) + r.get("extra_findings", []):
        head = " ".join(f"{k}={f[k]}" for k in ("id", "line", "severity", "conflicts_with") if k in f)
        print(f"\n--- {head} | {str(f.get('file', '')).split('/')[-1]}")
        for k in ("quote", "why", "problem", "proposed_text", "evidence"):
            if f.get(k): print(f"{k.upper()}: {str(f[k])[:cap]}")
    for v in r.get("verdicts", []):
        print(f"\n=== {v['id']}: {v['verdict']}\nREASON: {v['reason'][:cap]}")
        if v.get("corrected_text"): print("CORRECTED:", v["corrected_text"][:cap])
