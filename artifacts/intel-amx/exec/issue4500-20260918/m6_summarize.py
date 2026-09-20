#!/usr/bin/env python3
"""Summarize the m6 cells: per (tp, users, arm) mean TPS (harness tps_mean of the cell's perf.json), step ms = 1000/TPS,
TTFT, AMX-busy cycles; paired deltas vs base and vs target by repetition with paired t. Usage: m6_summarize.py RES_DIR"""
import glob, json, math, os, re, statistics, sys
from collections import defaultdict
RES = sys.argv[1]
cells = defaultdict(dict)
for d in sorted(glob.glob(os.path.join(RES, "cells", "*"))):
    m = re.match(r"tp(\d)__(\d+)u__(\w+)__rep(\d+)$", os.path.basename(d))
    if not m or not os.path.exists(os.path.join(d, "perf.json")) or open(os.path.join(d, "STATUS")).read().strip() != "done":
        continue
    p = json.load(open(os.path.join(d, "perf.json")))
    amx = None
    try:
        for line in open(os.path.join(d, "amx_busy.txt")):
            if "amx_busy" in line and not line.startswith("pid"):
                amx = int(line.split(",")[0]); break
    except Exception: pass
    cells[(int(m[1]), int(m[2]), m[3])][int(m[4])] = {"tps": p["tps_mean"], "sd": p["tps_std_dev"], "min": p["min_tps"], "ttft": p["ttft_mean_ms"], "amx": amx}
def ms(xs): return (statistics.mean(xs), statistics.stdev(xs) if len(xs) > 1 else 0.0, len(xs))
lines = ["# issue4500 block m6: CI-layout cells (rinzler + the nightly client on our half)", "",
         "| tp | users/engine | arm | n | TPS mean | TPS sd (reps) | step ms | TTFT ms | AMX-busy cycles (20 s) |", "|---|---|---|---|---|---|---|---|---|"]
for k in sorted(cells):
    rs = cells[k]; m_, s_, n_ = ms([r["tps"] for r in rs.values()])
    lines.append(f"| {k[0]} | {k[1]} | {k[2]} | {n_} | {m_:.2f} | {s_:.2f} | {1000/m_:.3f} | {statistics.mean(r['ttft'] for r in rs.values()):.0f} | {'/'.join(str(r['amx']) for r in rs.values())} |")
lines += ["", "## Paired (a minus b, per repetition; step ms = 1000/TPS)", "", "| tp | users | a | b | n | delta ms/step | delta TPS % | paired t (12.71 at n=2, 4.30 at n=3) |", "|---|---|---|---|---|---|---|---|"]
for (tp, users) in sorted({(k[0], k[1]) for k in cells}):
    arms = {k[2]: v for k, v in cells.items() if k[0] == tp and k[1] == users}
    for ref in ("base", "target"):
        if ref not in arms: continue
        for a in sorted(arms):
            if a == ref or (ref == "target" and a == "base"): continue
            common = sorted(set(arms[a]) & set(arms[ref]))
            if not common: continue
            d = [1000/arms[a][r]["tps"] - 1000/arms[ref][r]["tps"] for r in common]
            pct = 100 * (statistics.mean(arms[a][r]["tps"] for r in common) / statistics.mean(arms[ref][r]["tps"] for r in common) - 1)
            md, sd, n = ms(d); t = md / (sd / math.sqrt(n)) if sd and n > 1 else None
            lines.append(f"| {tp} | {users} | {a} | {ref} | {n} | {md:+.3f} (sd {sd:.3f}) | {pct:+.2f} | {'-' if t is None else f'{t:+.2f}'} |")
json.dump({f"tp{k[0]}__{k[1]}u__{k[2]}": v for k, v in cells.items()}, open(os.path.join(RES, "summary.json"), "w"), indent=1)
print("\n".join(lines))
