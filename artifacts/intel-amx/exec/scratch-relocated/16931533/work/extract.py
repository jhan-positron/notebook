#!/usr/bin/env python3
"""Parse every nightly log in ../logs into rows.csv / runs.json (both machines).
Reuses the row parser logic of ci-amx-persistence-20260928/analyze.py, relaxed:
incomplete rows are kept with usable=False instead of asserting."""
import csv, json, re, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
LOGS = HERE.parent / "logs"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
TS = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z")
FIELDS = ("n_users","n_rounds","stagger_delay","model","shared_prompt_length","prompt_length",
          "generate_length","start_capture","end_capture","sample_interval","continuous_usage","max_tokens")
def parse(path, machine, run_id):
    raw = path.read_bytes()
    lines = ANSI.sub("", raw.decode("utf-8","replace")).splitlines()
    rows=[]; row=None; package=None; dut=None; harness=None; status_notes=[]
    for i,line in enumerate(lines):
        m = re.search(r"Setting up tron \(([^)]+)\)", line)
        if m: package = m[1]
        m = re.search(r"DUT[:= ]+\s*([a-z]+-[0-9a-f]{4})", line)
        if m and not dut: dut = m[1]
        if re.search(r"\bn_users=\d+,", line):
            cfg={}
            for off, cl in enumerate(lines[i:i+18]):
                for f in FIELDS:
                    m = re.search(r"\b"+f+r"=('[^']*'|[^,]+),", cl)
                    if m:
                        v=m[1]
                        v = v.strip("'") if v.startswith("'") else (float(v) if "." in v else int(v))
                        cfg[f]=v
            if "model" in cfg and "prompt_length" in cfg:
                row={"config":cfg,"config_line":i+1,"start_time":(TS.search(line) or [None])[0],
                     "samples_tps":[],"samples_ttft_ms":[],"running_averages":[],"completed":False}
                rows.append(row)
        if row is None: continue
        m = re.search(r"Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)", line)
        if m:
            row["samples_ttft_ms"].append(int(m[1])); row["samples_tps"].append(float(m[2]))
        m = re.search(r"Running averages: TTFT=(\d+), TPS=([\d.]+)", line)
        if m: row["running_averages"].append({"ttft_ms":int(m[1]),"tps":float(m[2])})
        m = re.search(r"Perf test for (.+) completed in", line)
        if m and m[1]==row["config"]["model"]:
            row["completed"]=True; row["end_time"]=(TS.search(line) or [None])[0]; row=None
    for r in rows:
        n=len(r["samples_tps"]); exp=r["config"]["n_users"]*r["config"]["n_rounds"]
        r["n_samples"]=n; r["expected_samples"]=exp; r["usable"]=r["completed"] and n==exp
        if n:
            r["tps_mean"]=statistics.mean(r["samples_tps"]); r["tps_sd"]=statistics.pstdev(r["samples_tps"])
            r["tps_p05"]=sorted(r["samples_tps"])[max(0,int(round(0.05*n))-1)] if n>=20 else None
            r["tps_min"]=min(r["samples_tps"])
            r["ttft_mean_ms"]=statistics.mean(r["samples_ttft_ms"]); r["ttft_rounded_ms"]=round(r["ttft_mean_ms"])
            r["prefill_tps"]=r["config"]["prompt_length"]*1000/r["ttft_rounded_ms"] if r["ttft_rounded_ms"] else None
            if r["usable"] and r["running_averages"]:
                fa=r["running_averages"][-1]
                r["check_tps_gap"]=abs(r["tps_mean"]-fa["tps"]); r["check_ttft_gap_ms"]=abs(r["ttft_mean_ms"]-fa["ttft_ms"])
    first=[r["start_time"] for r in rows if r["start_time"]]
    return {"machine":machine,"run_id":run_id,"url":f"https://github.com/positron-ai/systems_test/actions/runs/{run_id}",
            "date":first[0][:10] if first else None,"package":package,"dut":dut,"log_bytes":len(raw),"rows":rows}
runs=[]
for p in sorted(LOGS.glob("*.log")):
    machine,run_id=p.stem.split("-"); runs.append(parse(p,machine,int(run_id)))
runs.sort(key=lambda r:(r["machine"],r["date"] or ""))
json.dump(runs,open(HERE/"runs.json","w"),indent=1)
cols=["machine","date","package","run_id","model","users","prompt_tokens","generated_tokens","n_samples","expected_samples",
      "usable","tps_mean","tps_sd","tps_p05","tps_min","ttft_mean_ms","ttft_rounded_ms","prefill_tps","check_tps_gap","check_ttft_gap_ms","source_url"]
with open(HERE/"rows.csv","w") as f:
    w=csv.DictWriter(f,fieldnames=cols,lineterminator="\n"); w.writeheader()
    for run in runs:
        for r in run["rows"]:
            if not r["n_samples"]: continue
            c=r["config"]
            w.writerow({"machine":run["machine"],"date":run["date"],"package":run["package"],"run_id":run["run_id"],
                "model":c["model"],"users":c["n_users"],"prompt_tokens":c["prompt_length"],"generated_tokens":c["generate_length"],
                **{k:r.get(k) for k in ("n_samples","expected_samples","usable","tps_mean","tps_sd","tps_p05","tps_min","ttft_mean_ms","ttft_rounded_ms","prefill_tps","check_tps_gap","check_ttft_gap_ms")},
                "source_url":run["url"]})
for run in runs:
    us=sum(r["usable"] for r in run["rows"])
    print(run["machine"],run["date"],run["package"],run["dut"],f"{us}/{len(run['rows'])} usable rows", f"{run['log_bytes']/1e6:.1f}MB")
