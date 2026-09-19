#!/usr/bin/env python3
"""Summary of the l8bload-20260918 cells: AMX gain on llama-3.1-8b per load level (users per engine).

Reads cells/<U>u__<arm>__rep<N>/{perf.json, meta.json, amx_busy.txt}. For every level U the on and
off arms are paired by repetition; the gain is the mean over repetitions of (on - off) / off, with a
paired t over the repetitions (t975 for n = 3 is 4.303, for n = 2 it is 12.71). Writes summary.json
next to the cells and prints summary.md to stdout.
Usage: summarize.py RESULTS_DIR
"""
import glob
import json
import math
import os
import re
import statistics
import sys

res = sys.argv[1]
cells = {}
for d in sorted(glob.glob(os.path.join(res, "cells", "*u__*__rep*"))):
    m = re.match(r"(\d+)u__(off|on)__rep(\d+)$", os.path.basename(d))
    if not m or not os.path.exists(os.path.join(d, "perf.json")):
        continue
    users, arm, rep = int(m.group(1)), m.group(2), int(m.group(3))
    p = json.load(open(os.path.join(d, "perf.json")))
    meta = json.load(open(os.path.join(d, "meta.json"))) if os.path.exists(os.path.join(d, "meta.json")) else {}
    anomaly = open(os.path.join(d, "ANOMALY")).read().strip() if os.path.exists(os.path.join(d, "ANOMALY")) else ""
    amx = None
    try:
        for line in open(os.path.join(d, "amx_busy.txt")):
            if "amx_busy" in line and line.split(",")[0].strip().isdigit():
                amx = int(line.split(",")[0])
    except FileNotFoundError:
        pass
    cells[(users, arm, rep)] = {"anomaly": anomaly, "tps": p["tps_mean"], "sd": p["tps_std_dev"], "min": p["min_tps"], "ttft": p["ttft_mean_ms"],
                                "per_engine": [e["tps_mean"] for e in p.get("per_engine", [])], "amx_busy": amx,
                                "minutes": p.get("minutes"), "machine": meta.get("machine", ""), "started": meta.get("started", "")}

levels = sorted({k[0] for k in cells})
out = {"model": "llama-3.1-8b-instruct-good-tp2", "layout": "2 engines on socket 1 (nightly instance-2/3 placement), one harness client per engine",
       "arms": {"off": "TRON_AMX_DISABLE=1", "on": "unset"}, "levels": {}}
T975 = {1: float("nan"), 2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}
lines = ["# l8bload-20260918: AMX gain on llama-3.1-8b against the load per engine", "",
         "Cells: 2 engines placed like the nightly's socket-1 engines, U users per engine each (CI harness, prompt 1024, generate 1536, 10 rounds, capture 896-1024). "
         "off = TRON_AMX_DISABLE=1, on = unset. TPS = tokens per second per user, pooled over both engines. Gain = mean over repetitions of (on - off) / off, paired by repetition.", "",
         "| users per engine | reps | off TPS | on TPS | gain | paired t | off TTFT ms | on TTFT ms | AMX-busy cycles off / on (20 s) |", "|---|---|---|---|---|---|---|---|---|"]
for u in levels:
    reps = sorted({k[2] for k in cells if k[0] == u and (u, "off", k[2]) in cells and (u, "on", k[2]) in cells
                   and not cells[(u, "off", k[2])]["anomaly"] and not cells[(u, "on", k[2])]["anomaly"]})
    if not reps:
        continue
    offs = [cells[(u, "off", r)] for r in reps]
    ons = [cells[(u, "on", r)] for r in reps]
    gains = [100.0 * (o["tps"] - f["tps"]) / f["tps"] for o, f in zip(ons, offs)]
    g = statistics.mean(gains)
    t = float("nan")
    if len(gains) >= 2:
        sd = statistics.stdev(gains)
        t = g / (sd / math.sqrt(len(gains))) if sd > 0 else float("inf")
    def mean(key, arr):
        vals = [a[key] for a in arr if a[key] is not None]
        return statistics.mean(vals) if vals else None
    lvl = {"reps": reps, "off_tps": mean("tps", offs), "on_tps": mean("tps", ons), "gain_pct": g, "gains_pct": gains, "paired_t": t,
           "t975": T975.get(len(gains)), "resolved": (len(gains) >= 2 and abs(t) >= T975.get(len(gains), float("inf"))),
           "off_ttft_ms": mean("ttft", offs), "on_ttft_ms": mean("ttft", ons),
           "off_amx_busy": mean("amx_busy", offs), "on_amx_busy": mean("amx_busy", ons),
           "off_per_engine": [f["per_engine"] for f in offs], "on_per_engine": [o["per_engine"] for o in ons],
           "off_min": [f["min"] for f in offs], "on_min": [o["min"] for o in ons]}
    out["levels"][str(u)] = lvl
    ab = lambda v: "n/a" if v is None else f"{v / 1e9:.1f} G"
    lines.append(f"| {u} | {len(reps)} | {lvl['off_tps']:.2f} | {lvl['on_tps']:.2f} | {g:+.1f} % | {t:+.1f} | {lvl['off_ttft_ms']:.0f} | {lvl['on_ttft_ms']:.0f} | {ab(lvl['off_amx_busy'])} / {ab(lvl['on_amx_busy'])} |")
lines += ["", "Per cell (started UTC, TPS mean +/- sd over all samples, slowest sample, per-engine means, TTFT, AMX-busy cycles, machine line at start):"]
for (u, arm, r), c in sorted(cells.items()):
    pe = " / ".join(f"{x:.1f}" for x in c["per_engine"])
    amx = "n/a" if c["amx_busy"] is None else f"{c['amx_busy']:,}"
    lines.append(f"- {u}u {arm} rep{r}{' EXCLUDED (' + c['anomaly'] + ')' if c['anomaly'] else ''} ({c['started']}): TPS {c['tps']:.2f} +/- {c['sd']:.2f} (min {c['min']:.1f}; engines {pe}), TTFT {c['ttft']} ms, amx_busy {amx}, {c['minutes'] and round(c['minutes'], 1)} min; {c['machine']}")
lines += ["", "Reference points (same kernel, same 28-CPU engine placement, CPU attention): runtron 2026-09-16, 8 users on one engine, 1536 generated tokens: 83.3 -> 97.5 TPS (+17 %); "
          "ci-mimic 2026-09-18, nightly layout 2 users per engine: 139.40 -> 140.53 TPS (+0.8 %, paired t 2.96 over 10 rounds)."]
json.dump(out, open(os.path.join(res, "summary.json"), "w"), indent=1)
print("\n".join(lines))
