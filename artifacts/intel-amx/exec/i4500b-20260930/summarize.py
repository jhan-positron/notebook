#!/usr/bin/env python3
"""Summarize the i4500b cells: per (model, tp, users, prompt, arm) the mean TPS (harness tps_mean of the cell's
perf.json), step ms = 1000/TPS, TTFT, AMX-busy cycles; paired deltas vs base, vs fix and vs fixS1 by repetition with paired t.
Fork of exec/i4500fix-20260928/summarize.py (arms base fix fixS1 basekill fixS1kill).
Usage: summarize.py RES_DIR   (writes RES_DIR/summary.json, prints markdown)"""
import glob, json, math, os, re, statistics, sys
from collections import defaultdict
RES = sys.argv[1]
cells = defaultdict(dict)
for d in sorted(glob.glob(os.path.join(RES, "cells", "*"))):
    m = re.match(r"([\w-]+?)__tp(\d)__(\d+)u__p(\d+)__([\w-]+)__rep(\d+)$", os.path.basename(d))
    if not m or not os.path.exists(os.path.join(d, "perf.json")) or open(os.path.join(d, "STATUS")).read().strip() != "done":
        continue
    p = json.load(open(os.path.join(d, "perf.json")))
    amx = None
    try:
        for line in open(os.path.join(d, "amx_busy.txt")):
            if "amx_busy" in line and not line.startswith("pid"):
                amx = int(line.split(",")[0]); break
    except Exception: pass
    key = (m[1], int(m[2]), int(m[3]), int(m[4]), m[5])
    cells[key][int(m[6])] = {"tps": p["tps_mean"], "sd": p["tps_std_dev"], "min": p["min_tps"], "ttft": p["ttft_mean_ms"],
                             "cache_hit_pct": p.get("cache_hit_pct"), "prompt_tokens_mean": p.get("prompt_tokens_mean"), "amx": amx}
print(f"cells parsed: {sum(len(v) for v in cells.values())} in {len(cells)} groups", file=sys.stderr)
def ms(xs): return (statistics.mean(xs), statistics.stdev(xs) if len(xs) > 1 else 0.0, len(xs))
lines = ["# i4500b: cells (rinzler + the nightly client on our half of delphi-3bda)", "",
         "| model | tp | users/engine | prompt | binary | n | TPS mean | TPS sd (reps) | step ms | TTFT ms | prompt tokens | cached % | AMX-busy cycles (20 s) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for k in sorted(cells):
    rs = cells[k]; m_, s_, n_ = ms([r["tps"] for r in rs.values()])
    pt = [r["prompt_tokens_mean"] for r in rs.values() if r["prompt_tokens_mean"] is not None]
    ch = [r["cache_hit_pct"] for r in rs.values() if r["cache_hit_pct"] is not None]
    lines.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {k[4]} | {n_} | {m_:.2f} | {s_:.2f} | {1000/m_:.3f} | "
                 f"{statistics.mean(r['ttft'] for r in rs.values()):.0f} | {statistics.mean(pt):.0f} | {statistics.mean(ch):.1f} | "
                 f"{'/'.join(str(r['amx']) for r in rs.values())} |" if pt and ch else
                 f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {k[4]} | {n_} | {m_:.2f} | {s_:.2f} | {1000/m_:.3f} | "
                 f"{statistics.mean(r['ttft'] for r in rs.values()):.0f} | - | - | {'/'.join(str(r['amx']) for r in rs.values())} |")
lines += ["", "## Paired (a minus b, per repetition; step ms = 1000/TPS; t thresholds 12.71 at n=2, 4.30 at n=3)", "",
          "| model | tp | users | prompt | a | b | n | delta ms/step | delta TPS % | paired t |", "|---|---|---|---|---|---|---|---|---|---|"]
pairs = []
for (model, tp, users, prompt) in sorted({k[:4] for k in cells}):
    arms = {k[4]: v for k, v in cells.items() if k[:4] == (model, tp, users, prompt)}
    wanted = {("fix", "base"), ("fixS1", "base"), ("fixS1", "fix"), ("basekill", "base"), ("fixS1kill", "fixS1"), ("fixS1kill", "base")}
    for ref in ("base", "fix", "fixS1"):
        if ref not in arms: continue
        for a in sorted(arms):
            if (a, ref) not in wanted: continue
            common = sorted(set(arms[a]) & set(arms[ref]))
            if not common: continue
            d = [1000/arms[a][r]["tps"] - 1000/arms[ref][r]["tps"] for r in common]
            pct = 100 * (statistics.mean(arms[a][r]["tps"] for r in common) / statistics.mean(arms[ref][r]["tps"] for r in common) - 1)
            md, sd, n = ms(d); t = md / (sd / math.sqrt(n)) if sd and n > 1 else None
            lines.append(f"| {model} | {tp} | {users} | {prompt} | {a} | {ref} | {n} | {md:+.3f} (sd {sd:.3f}) | {pct:+.2f} | {'-' if t is None else f'{t:+.2f}'} |")
            pairs.append({"model": model, "tp": tp, "users": users, "prompt": prompt, "a": a, "b": ref, "n": n, "delta_ms": md, "sd_ms": sd, "delta_tps_pct": pct, "t": t})
json.dump({"cells": {"__".join(map(str, k)): v for k, v in cells.items()}, "pairs": pairs}, open(os.path.join(RES, "summary.json"), "w"), indent=1)
print("\n".join(lines))
