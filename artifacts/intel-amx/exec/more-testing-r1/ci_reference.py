#!/usr/bin/env python3
"""Extract the nightly System CI reference numbers from a downloaded GitHub
Actions log (gh run view <id> --log) into JSON, so the status report cites
measured CI values instead of hand-copied ones.

Usage: ci_reference.py <run-log> <run-id> <out.json>
"""
import json, re, sys

log_path, run_id, out_path = sys.argv[1:4]
lines = [re.sub(r'^\S+ ', '', re.sub(r'^[^\t]*\t[^\t]*\t', '', l.rstrip('\n')), count=1) for l in open(log_path, errors='replace')]
ref = {"run_id": int(run_id), "workflow": "System CI (Rinzler 72-core Intel system OCI version)",
       "dut": "delphi-3bda", "tron_package": None, "mmlu_coverage_pct": None,
       "functional": [], "perf": {}, "mmlu": {}, "soak": {}}

for l in lines:
    m = re.search(r'MMLU_COVERAGE: (\d+)', l)
    if m and ref["mmlu_coverage_pct"] is None: ref["mmlu_coverage_pct"] = int(m.group(1))
    m = re.search(r"Provisioning models via legacy posadm path: (\[.*\])", l)
    if m: last_prov = m.group(1)
    m = re.search(r'=+ (\d+) passed(?:, (\d+) skipped)?(?:, (\d+) failed)? in ([\d.]+)s', l)
    if m and len(ref["functional"]) < 2:
        ref["functional"].append({"models": last_prov, "passed": int(m.group(1)),
                                  "skipped": int(m.group(2) or 0), "failed": int(m.group(3) or 0),
                                  "seconds": float(m.group(4))})

# perf: last "Running averages" before each "Perf test for X completed"
last_avg = None
for l in lines:
    m = re.search(r'Running averages: TTFT=(\d+), TPS=([\d.]+)', l)
    if m: last_avg = (int(m.group(1)), float(m.group(2)))
    m = re.search(r'Perf test for (\S+) completed in ([\d.]+)mins', l)
    if m and last_avg:
        ref["perf"].setdefault(m.group(1), []).append({"ttft_ms": last_avg[0], "tps": last_avg[1], "minutes": float(m.group(2))})
        last_avg = None

# mmlu: "MMLU test for X completed" followed by the markdown table rows
cur = None
hdr = None
for i, l in enumerate(lines):
    m = re.search(r'MMLU test for (\S+) completed in ([\d.]+)mins', l)
    if m: cur = m.group(1); ref["mmlu"][cur] = {"minutes": float(m.group(2))}; continue
    if cur and l.startswith('| overall |'):
        hdr = [h.strip() for h in l.strip('|').split('|')]
    elif cur and hdr and re.match(r'^\| [\d.]+ \|', l):
        vals = [float(v) for v in l.strip('|').split('|')]
        ref["mmlu"][cur]["scores_pct"] = dict(zip(hdr, vals)); cur = None; hdr = None
    m = re.search(r'Completion tokens: min (\d+), average (\d+), max (\d+), total (\d+)', l)
    if m and cur: ref["mmlu"][cur]["completion_tokens"] = {"min": int(m.group(1)), "avg": int(m.group(2)), "max": int(m.group(3)), "total": int(m.group(4))}

# soak: last block
blk = None
for i, l in enumerate(lines):
    if l.startswith('-- Duration:'): blk = i
if blk is not None:
    seg = lines[blk:blk+80]
    ref["soak"]["duration"] = seg[0].split('Duration:')[1].strip(' -')
    cur = None
    for l in seg:
        m = re.search(r'Errors: (\d+)', l)
        if m: ref["soak"]["errors"] = int(m.group(1))
        m = re.search(r'Used Memory: ([\d.]+) GiB \(Growth: (-?[\d.]+) GiB\)', l)
        if m: ref["soak"]["used_memory_gib"] = float(m.group(1)); ref["soak"]["growth_gib"] = float(m.group(2))
        m = re.search(r'^\s*Model: (\S+)', l)
        if m: cur = m.group(1); ref["soak"].setdefault("models", {})[cur] = {}
        if cur:
            m = re.search(r'Requests \(sent/succeeded/failed\): (\d+)/(\d+)/(\d+)', l)
            if m: ref["soak"]["models"][cur].update(sent=int(m.group(1)), succeeded=int(m.group(2)), failed=int(m.group(3)))
            m = re.search(r'Avg TTFT: ([\d.]+)s', l)
            if m: ref["soak"]["models"][cur]["avg_ttft_s"] = float(m.group(1))
            m = re.search(r'Total token generation\s*: ([\d.]+) tok/s', l)
            if m: ref["soak"]["models"][cur]["total_gen_tok_s"] = float(m.group(1))
            m = re.search(r'Per-user token generation: ([\d.]+) tok/s', l)
            if m: ref["soak"]["models"][cur]["per_user_gen_tok_s"] = float(m.group(1))
for l in lines:
    m = re.search(r'Auto-detected model names: (\S+)', l)
    if m: ref["soak"]["model_list"] = m.group(1).split(',')
json.dump(ref, open(out_path, 'w'), indent=1)
print(json.dumps({k: (v if k in ('run_id','mmlu_coverage_pct','functional','soak') else {m: (x if k=='perf' else x.get('scores_pct',{}).get('overall')) for m, x in v.items()}) for k, v in ref.items() if k not in ('workflow','dut','tron_package')}, indent=1)[:3000])
