#!/usr/bin/env python3
"""Summarize exec/results/vnnik6-20260916/rt-results.txt into summary.json (next to the
input) and a markdown table on stdout. Fork of exec/vnnik2-20260915/summarize.py for the
arms base / headoff / vnni, with paired per-repetition deltas added.

Definitions: TPS = runtron's per-request "average tok/s" averaged over the 8 requests of a
run; TTFT = "Parsing the prompt took S s" (max over the 8 requests); per cell (tp, prompt,
arm): mean and sample sd over the repetitions. Arms: base (main binary, row-major K),
headoff (PR head built with the layout off), vnni (PR head, VNNI layout on). Deltas a/b - 1
in percent for the pairs vnni vs base, headoff vs base, vnni vs headoff. Paired deltas: for
every repetition present in both arms, a - b (TPS) and a - b (TTFT s); mean, sample sd, n and
t = mean / (sd / sqrt(n)) (the repetitions interleave the arms, so the pairing removes slow
drifts of the machine). EARLY-STOP flags a run whose 8 requests generated unequal token
counts or fewer TPS lines than users.
Usage: summarize.py RESULTS_DIR
"""
import json
import math
import os
import re
import statistics
import sys

RES = sys.argv[1]
ARMS = os.environ.get("VNNIK6_ARMS", "base headoff vnni").split()
PAIRS = ([tuple(p.split(":")) for p in os.environ["VNNIK6_PAIRS"].split()] if os.environ.get("VNNIK6_PAIRS")
         else [("vnni", "base"), ("headoff", "base"), ("vnni", "headoff")])


def fnum(x, nd):
    return "-" if x is None else f"{x:.{nd}f}"


def mean_sd(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None, 0
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0), len(xs)


def parse(path):
    runs, cur = [], None
    for line in open(path, errors="replace"):
        line = line.rstrip("\n")
        m = re.match(r"### runtron tp=(\d) prompt=(\d+) arm=(\S+) rep=(\d+) attempt=(\d+)", line)
        if m:
            cur = {"tp": int(m[1]), "prompt": int(m[2]), "arm": m[3], "rep": int(m[4]), "attempt": int(m[5]),
                   "tps": [], "ttft": [], "gen": [], "failed": False, "stopped": False, "header": line,
                   "version": None}
            runs.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("RUN-FAILED"):
            cur["failed"] = True
        elif line.startswith("RUN-STOPPED") or line.startswith("RUN-GIVEN-UP"):
            cur["stopped"] = True
        m = re.search(r"Version: (\S+) hash: ([0-9a-f]+)", line)
        if m:
            cur["version"] = m[2][:10]
        m = re.search(r"Parsing the prompt took ([0-9.]+) s", line)
        if m:
            cur["ttft"].append(float(m[1]))
        m = re.search(r"Generating (\d+) response tokens with \d+ context took [0-9.]+ s at ([0-9.]+) average tok/s", line)
        if m:
            cur["gen"].append(int(m[1]))
            cur["tps"].append(float(m[2]))
    return runs


def paired(rs_a, rs_b, key):
    by_a = {r["rep"]: r[key] for r in rs_a if r[key] is not None}
    by_b = {r["rep"]: r[key] for r in rs_b if r[key] is not None}
    d = [by_a[k] - by_b[k] for k in sorted(set(by_a) & set(by_b))]
    if not d:
        return None
    m = statistics.mean(d)
    sd = statistics.stdev(d) if len(d) > 1 else 0.0
    t = (m / (sd / math.sqrt(len(d)))) if sd > 0 and len(d) > 1 else None
    return {"n": len(d), "mean": m, "sd": sd, "t": t, "deltas": d}


def main():
    runs = parse(os.path.join(RES, "rt-results.txt"))
    cells, seen, dups, early = {}, set(), [], []
    for r in runs:
        if r["failed"] or r["stopped"] or not r["tps"]:
            continue
        key = (r["tp"], r["prompt"], r["arm"], r["rep"])
        if key in seen:   # a second complete record of one repetition (hand resume): keep the first
            dups.append(r["header"])
            continue
        seen.add(key)
        r["early_stop"] = (len(r["tps"]) != 8) or (min(r["gen"]) != max(r["gen"]))
        # one request left the batch early: the others ran faster, so the TPS of the run is biased; TTFT is unaffected
        r["tps_per_user"] = None if r["early_stop"] else statistics.mean(r["tps"])
        r["ttft_s"] = max(r["ttft"]) if r["ttft"] else None
        if r["early_stop"]:
            early.append(f'{r["header"]} -> generated {sorted(r["gen"])} tokens over {len(r["tps"])} completion lines')
        cells.setdefault((r["tp"], r["prompt"], r["arm"]), []).append(r)
    out = {"cells": [], "deltas": [], "paired": []}
    lines = ["# vnnik6-20260916 summary (qwen-3-30b-a3b, kv_mul 8, 8 users)", "",
             "Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the 8 prompts).", ""]
    for tp in (2, 4):
        prompts = sorted({k[1] for k in cells if k[0] == tp})
        if not prompts:
            continue
        lines += [f"## tp{tp}", "", "| prompt | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | binary versions |", "|---|---|---|---|---|---|---|---|---|"]
        stats = {}
        for prompt in prompts:
            for arm in ARMS:
                rs = cells.get((tp, prompt, arm))
                if not rs:
                    continue
                tm, tsd, n = mean_sd([r["tps_per_user"] for r in rs])
                fm, fsd, _ = mean_sd([r["ttft_s"] for r in rs])
                es = sum(1 for r in rs if r["early_stop"])
                vers = sorted({r["version"] for r in rs if r["version"]})
                stats[(prompt, arm)] = (tm, fm)
                out["cells"].append({"tp": tp, "prompt": prompt, "arm": arm, "n": n, "tps_mean": tm, "tps_sd": tsd, "ttft_mean": fm, "ttft_sd": fsd,
                                     "early_stop_runs": es, "versions": vers,
                                     "reps": [{"rep": r["rep"], "tps_per_user": r["tps_per_user"], "ttft_s": r["ttft_s"], "early_stop": r["early_stop"]} for r in sorted(rs, key=lambda x: x["rep"])]})
                lines.append(f"| {prompt} | {arm} | {n} | {fnum(tm, 2)} | {fnum(tsd, 2)} | {fnum(fm, 3)} | {fnum(fsd, 3)} | {es} | {','.join(vers)} |")
        lines += ["", "| prompt | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |", "|---|---|---|---|---|---|---|"]
        for prompt in prompts:
            for a, b in PAIRS:
                if (prompt, a) in stats and (prompt, b) in stats:
                    ta, fa = stats[(prompt, a)]
                    tb, fb = stats[(prompt, b)]
                    if None in (ta, tb, fa, fb) or tb == 0 or fb == 0:
                        lines.append(f"| {prompt} | {a} vs {b} | - | - | - | (a cell has no complete run) | - |")
                        continue
                    dt, df = 100 * (ta / tb - 1), 100 * (fa / fb - 1)
                    pt = paired(cells[(tp, prompt, a)], cells[(tp, prompt, b)], "tps_per_user")
                    pf = paired(cells[(tp, prompt, a)], cells[(tp, prompt, b)], "ttft_s")
                    out["deltas"].append({"tp": tp, "prompt": prompt, "a": a, "b": b, "tps_delta_pct": dt, "ttft_delta_pct": df, "ttft_delta_ms": 1000 * (fa - fb)})
                    out["paired"].append({"tp": tp, "prompt": prompt, "a": a, "b": b, "tps": pt, "ttft_s": pf})
                    ptxt = f"{pt['mean']:+.2f} ({pt['sd']:.2f}, {pt['n']}, {pt['t']:+.1f})" if pt and pt["t"] is not None else (f"{pt['mean']:+.2f} (n={pt['n']})" if pt else "-")
                    ftxt = f"{1000*pf['mean']:+.0f} ({1000*pf['sd']:.0f}, {pf['n']}, {pf['t']:+.1f})" if pf and pf["t"] is not None else (f"{1000*pf['mean']:+.0f} (n={pf['n']})" if pf else "-")
                    lines.append(f"| {prompt} | {a} vs {b} | {dt:+.1f} | {df:+.1f} | {1000*(fa-fb):+.0f} | {ptxt} | {ftxt} |")
        lines.append("")
    bad = [r["header"] for r in runs if r["failed"] or r["stopped"]]
    lines += [f"Excluded attempts (failed or stopped): {len(bad)}"] + [f"- {h}" for h in bad] + [""]
    lines += [f"Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): {len(early)}"] + [f"- {h}" for h in early] + [""]
    lines += [f"Duplicate complete records of one repetition (second and later ignored): {len(dups)}"] + [f"- {h}" for h in dups] + [""]
    out["excluded"] = {"failed_or_stopped": bad, "early_stop": early, "duplicates": dups}
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
