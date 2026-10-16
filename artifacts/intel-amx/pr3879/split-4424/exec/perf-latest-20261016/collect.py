#!/usr/bin/env python3
"""Collect the latest PR-vs-main performance records into one JSON file.

Sources (all under exec/results/):
  pr4424ci-20261009  PR 4424 deb vs the nightly deb of main (be0d5565b3), the harness's 14 cells + sw8k
  m4737-E-cpu        PR 4424 at 9d5c7a389b vs main be0d5565b3, runtron, qwen3-4b CPU attention
  pr4ci-20261012     PR 4901 deb (ea94e95a4e) vs the deb of main 72308ec90c, 3 harness cells
  pr4-E-cpu          PR 4901 ea94e95a4e vs main 72308ec90c, runtron, qwen3-4b CPU attention
  pr4-E-fpga         same, FPGA attention
  pr4off-E-cpu       same binaries with TRON_AMX_DISABLE=1 on both arms
"""
import json, re, sys
from pathlib import Path

R = Path("/home/jhan/workspace/intel-AMX/exec/results")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("data.json")

def md_rows(text, header_must_contain):
    """Yield the cells of every data row of the first table whose header contains the phrase."""
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("|") and header_must_contain in l:
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                yield [c.strip() for c in lines[j].strip().strip("|").split("|")]
                j += 1
            return

num = lambda s: float(s.replace(",", "").split(" ")[0])

def harness(name):
    text = (R / name / "summary.md").read_text()
    out = []
    for section, phrase in (("fpga", "### Full passes"), ("sw8k", "### Extra cell")):
        if phrase not in text:
            continue
        part = text.split(phrase, 1)[1]
        for c in md_rows(part, "base TPS mean"):
            if c[0].startswith("sw8k cell"):
                continue
            m = re.match(r"([+-][\d.]+) ms \(([+-][\d.]+) %\) t=([+-][\d.]+)", c[8])
            out.append(dict(
                cell=c[0], attn=("fpga" if section == "fpga" else "sw"),
                base_tps=num(c[1]), target_tps=num(c[2]),
                base_sd=float(re.search(r"\(([\d.]+)\)", c[1]).group(1)),
                target_sd=float(re.search(r"\(([\d.]+)\)", c[2]).group(1)),
                tps_delta_pct=num(c[3]), tps_t=num(c[4].split(" ")[0]),
                tps_resolved=(c[5] == "YES"),
                base_ttft_ms=num(c[6]), target_ttft_ms=num(c[7]),
                ttft_delta_ms=float(m.group(1)), ttft_delta_pct=float(m.group(2)),
                ttft_t=float(m.group(3)), ttft_resolved=(c[9] == "YES"),
            ))
    return out

def runtron(name, pairs):
    """pairs: list of (new_arm, base_arm, label). Band = 2 x max(sd), floor 0.4 TPS / 0.15 s."""
    text = (R / name / "summary.md").read_text()
    arms = {}
    for c in md_rows(text, "TPS/user"):
        arms[(c[0], c[1], c[5])] = dict(tps=float(c[7]), tps_sd=float(c[8]), ttft=float(c[9]), ttft_sd=float(c[10]), n=int(c[6]), commit=c[13])
    comps = {}
    for c in md_rows(text, "comparison"):
        comps[(c[0], c[1], c[2])] = c
    out = []
    for (cell, attn, arm), a in arms.items():
        for new_arm, base_arm, label in pairs:
            if arm != new_arm or (cell, attn, base_arm) not in arms:
                continue
            b = arms[(cell, attn, base_arm)]
            comp = comps[(cell, attn, f"{new_arm} vs {base_arm}")]
            band_tps = max(2 * max(a["tps_sd"], b["tps_sd"]), 0.4)
            band_ttft = max(2 * max(a["ttft_sd"], b["ttft_sd"]), 0.15)
            d_tps = a["tps"] - b["tps"]
            d_ttft = a["ttft"] - b["ttft"]
            out.append(dict(
                cell=cell, attn=attn, pair=label,
                base_tps=b["tps"], target_tps=a["tps"], base_sd=b["tps_sd"], target_sd=a["tps_sd"],
                tps_delta_pct=float(comp[3]), tps_delta=round(d_tps, 2), band_tps=round(band_tps, 2),
                tps_resolved=abs(d_tps) > band_tps,
                base_ttft_ms=round(b["ttft"] * 1000), target_ttft_ms=round(a["ttft"] * 1000),
                ttft_delta_ms=float(comp[5]), ttft_delta_pct=float(comp[4]),
                band_ttft_ms=round(band_ttft * 1000), ttft_resolved=abs(d_ttft) > band_ttft,
                n=a["n"], base_commit=b["commit"], target_commit=a["commit"],
            ))
    return out

data = {
    "pr4424": {
        "harness": harness("pr4424ci-20261009"),
        "runtron_cpu": runtron("m4737-E-cpu", [("new", "base", "PR 4424 vs main")]),
    },
    "pr4901": {
        "harness": harness("pr4ci-20261012"),
        "runtron_cpu": runtron("pr4-E-cpu", [("new", "base", "PR 4901 vs main")]),
        "runtron_fpga": runtron("pr4-E-fpga", [("new", "base", "PR 4901 vs main")]),
        "runtron_off": runtron("pr4off-E-cpu", [("newoff", "baseoff", "PR 4901 vs main, AMX off on both")]),
    },
}
OUT.write_text(json.dumps(data, indent=1))
for k, v in data.items():
    for kk, rows in v.items():
        print(k, kk, len(rows), "rows")
        for r in rows:
            print("   ", r["cell"], r["attn"], r["tps_delta_pct"], "res" if r["tps_resolved"] else "noise", "| ttft", r["ttft_delta_ms"], "res" if r["ttft_resolved"] else "noise")
