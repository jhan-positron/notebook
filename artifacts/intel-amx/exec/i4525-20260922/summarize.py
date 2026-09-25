#!/usr/bin/env python3
"""Summarize exec/results/wedperf-20260916/rt-results.txt (or a sibling campaign dir) into summary.json (next to the
input) and a markdown table on stdout. Fork of exec/vnnik6-20260916/summarize.py for cells
keyed by (cell key, attention mode) and the two arms base / target.

Definitions: TPS = runtron's per-request "average tok/s" averaged over the requests of a run
(one per user); TTFT = "Parsing the prompt took S s" (max over the users); per cell (key,
attn, arm): mean and sample sd over the repetitions. Arms: base (main before PR #3879),
target (PR #4424 head, AMX dispatch + VNNI K layout). Delta target/base - 1 in percent.
Paired deltas: for every repetition present in both arms, target - base (TPS) and target -
base (TTFT s); mean, sample sd, n and t = mean / (sd / sqrt(n)) (the repetitions interleave
the arms, so the pairing removes slow drifts of the machine). EARLY-STOP flags a run whose
requests generated unequal token counts or fewer TPS lines than users; its TPS is excluded,
its TTFT kept. Only kind=rt records are summarized (smokes are compared by compare_tokens.py).
Usage: summarize.py RESULTS_DIR
"""
import json
import math
import os
import re
import statistics
import sys

RES = sys.argv[1]
ARMS = os.environ.get("WEDPERF_ARMS", "base head baseoff headoff").split()   # i4525: base = main binary, head = branch binary, headoff = head with TRON_AMX_DISABLE=1
# comparison pairs a:b (a vs b); the default is the two-binary campaign; block D uses "mid:base target:mid target:base"
PAIRS = ([tuple(p.split(":")) for p in os.environ["WEDPERF_PAIRS"].split()] if os.environ.get("WEDPERF_PAIRS") else [("head", "base"), ("headoff", "baseoff")])
HDR = re.compile(r"### runtron kind=(\S+) cell=(\S+) model=(\S+) tp=(\d) users=(\d+) attn=(\S+) prompt=(\d+) len=(\d+) arm=(\S+)(?: armenv=\[[^\]]*\])? rep=(\d+) attempt=(\d+)")   # i4525: optional armenv=[...] field


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
        m = HDR.match(line)
        if m:
            cur = {"kind": m[1], "cell": m[2], "model": m[3], "tp": int(m[4]), "users": int(m[5]), "attn": m[6],
                   "prompt": int(m[7]), "len": int(m[8]), "arm": m[9], "rep": int(m[10]), "attempt": int(m[11]),
                   "tps": [], "ttft": [], "gen": [], "failed": False, "stopped": False, "header": line,
                   "version": None, "hw_attn": None, "hbm_lose": None, "hbm_exh": None, "started": (re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line) or [None, None])[1]}
            runs.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("RUN-FAILED"):
            cur["failed"] = True
        elif line.startswith("RUN-STOPPED") or line.startswith("RUN-GIVEN-UP"):
            cur["stopped"] = True
        m = re.match(r"HBM-EXHAUSTION lose=(\d+) exhausted=(\d+)", line)
        if m:
            cur["hbm_lose"], cur["hbm_exh"] = int(m[1]), int(m[2])
        m = re.search(r"Version: (\S+) hash: ([0-9a-f]+)", line)
        if m:
            cur["version"] = m[2][:10]
        m = re.search(r"HW attention[^\n]*", line)
        if m and cur["hw_attn"] is None:
            cur["hw_attn"] = m[0][:120]
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
    cells, seen, dups, early, order = {}, set(), [], [], []
    for r in runs:
        if r["kind"] != "rt" or r["failed"] or r["stopped"] or not r["tps"]:
            continue
        key = (r["cell"], r["attn"], r["arm"], r["rep"])
        if key in seen:   # a second complete record of one repetition (hand resume): keep the first
            dups.append(r["header"])
            continue
        seen.add(key)
        r["early_stop"] = (len(r["tps"]) != r["users"]) or (min(r["gen"]) != max(r["gen"]))
        # one request left the batch early: the others ran faster, so the TPS of the run is biased; TTFT is unaffected
        r["tps_per_user"] = None if r["early_stop"] else statistics.mean(r["tps"])
        r["ttft_s"] = max(r["ttft"]) if r["ttft"] else None
        if r["early_stop"]:
            early.append(f'{r["header"]} -> generated {sorted(r["gen"])} tokens over {len(r["tps"])} completion lines')
        ck = (r["cell"], r["attn"])
        if ck not in order:
            order.append(ck)
        cells.setdefault((r["cell"], r["attn"], r["arm"]), []).append(r)
    out = {"cells": [], "deltas": [], "paired": []}
    lines = ["# i4525-20260922 summary (issue #4525 typed KV-cache tensors: base = main binary, head = branch binary, baseoff/headoff = the same binaries with TRON_AMX_DISABLE=1; attn = cpu or fpga)", "",
             "Per cell: mean over repetitions (sample sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (max over the users).", "",
             "| cell | attn | model | tp | users | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs | HBM-exhaustion warnings per run (mean) | binary versions |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    stats = {}
    for cell, attn in order:
        for arm in ARMS:
            rs = cells.get((cell, attn, arm))
            if not rs:
                continue
            tm, tsd, n = mean_sd([r["tps_per_user"] for r in rs])
            fm, fsd, _ = mean_sd([r["ttft_s"] for r in rs])
            es = sum(1 for r in rs if r["early_stop"])
            vers = sorted({r["version"] for r in rs if r["version"]})
            hw = sorted({r["hw_attn"] for r in rs if r["hw_attn"]})
            stats[(cell, attn, arm)] = (tm, fm)
            r0 = rs[0]
            hl = [r["hbm_lose"] for r in rs if r["hbm_lose"] is not None]
            hbm = statistics.mean(hl) if hl else None
            out["cells"].append({"cell": cell, "attn": attn, "model": r0["model"], "tp": r0["tp"], "users": r0["users"], "prompt": r0["prompt"], "arm": arm, "n": n,
                                 "tps_mean": tm, "tps_sd": tsd, "ttft_mean": fm, "ttft_sd": fsd, "early_stop_runs": es, "versions": vers, "hw_attn_lines": hw,
                                 "hbm_lose_mean": hbm, "hbm_lose_per_rep": hl,
                                 "reps": [{"rep": r["rep"], "tps_per_user": r["tps_per_user"], "ttft_s": r["ttft_s"], "early_stop": r["early_stop"],
                                           "started": r["started"], "n_tps_lines": len(r["tps"]), "gen_tokens": sorted(set(r["gen"]))} for r in sorted(rs, key=lambda x: x["rep"])]})
            lines.append(f"| {cell} | {attn} | {r0['model']} | {r0['tp']} | {r0['users']} | {arm} | {n} | {fnum(tm, 2)} | {fnum(tsd, 2)} | {fnum(fm, 3)} | {fnum(fsd, 3)} | {es} | {fnum(hbm, 1)} | {','.join(vers)} |")
    lines += ["", "| cell | attn | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms | paired TPS delta mean (sd, n, t) | paired TTFT delta ms mean (sd, n, t) |", "|---|---|---|---|---|---|---|---|"]
    for cell, attn in order:
        for A, B in PAIRS:
            if (cell, attn, A) in stats and (cell, attn, B) in stats:
                ta, fa = stats[(cell, attn, A)]
                tb, fb = stats[(cell, attn, B)]
                if None in (ta, tb, fa, fb) or tb == 0 or fb == 0:
                    lines.append(f"| {cell} | {attn} | {A} vs {B} | - | - | - | (a cell has no complete run) | - |")
                    continue
                dt, df = 100 * (ta / tb - 1), 100 * (fa / fb - 1)
                pt = paired(cells[(cell, attn, A)], cells[(cell, attn, B)], "tps_per_user")
                pf = paired(cells[(cell, attn, A)], cells[(cell, attn, B)], "ttft_s")
                out["deltas"].append({"cell": cell, "attn": attn, "a": A, "b": B, "tps_delta_pct": dt, "ttft_delta_pct": df, "ttft_delta_ms": 1000 * (fa - fb)})
                out["paired"].append({"cell": cell, "attn": attn, "a": A, "b": B, "tps": pt, "ttft_s": pf})
                ptxt = f"{pt['mean']:+.2f} ({pt['sd']:.2f}, {pt['n']}, {pt['t']:+.1f})" if pt and pt["t"] is not None else (f"{pt['mean']:+.2f} (n={pt['n']})" if pt else "-")
                ftxt = f"{1000*pf['mean']:+.0f} ({1000*pf['sd']:.0f}, {pf['n']}, {pf['t']:+.1f})" if pf and pf["t"] is not None else (f"{1000*pf['mean']:+.0f} (n={pf['n']})" if pf else "-")
                lines.append(f"| {cell} | {attn} | {A} vs {B} | {dt:+.1f} | {df:+.1f} | {1000*(fa-fb):+.0f} | {ptxt} | {ftxt} |")
    bad = [r["header"] for r in runs if r["kind"] == "rt" and (r["failed"] or r["stopped"])]
    smoke_bad = [r["header"] for r in runs if r["kind"] == "smoke" and (r["failed"] or r["stopped"])]
    lines += ["", f"Excluded rt attempts (failed or stopped): {len(bad)}"] + [f"- {h}" for h in bad] + [""]
    lines += [f"Failed or stopped smoke attempts: {len(smoke_bad)}"] + [f"- {h}" for h in smoke_bad] + [""]
    lines += [f"Early-stop runs (TPS excluded from the means and the paired deltas, TTFT kept): {len(early)}"] + [f"- {h}" for h in early] + [""]
    lines += [f"Duplicate complete records of one repetition (second and later ignored): {len(dups)}"] + [f"- {h}" for h in dups] + [""]
    out["excluded"] = {"failed_or_stopped": bad, "smoke_failed_or_stopped": smoke_bad, "early_stop": early, "duplicates": dups}
    out["n_rt_records"] = sum(1 for r in runs if r["kind"] == "rt")
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
