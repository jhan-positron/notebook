#!/usr/bin/env python3
"""Summarize exec/results/issue4500-20260918/rt-results.txt into summary.json and a markdown table.

Words used here: TPS = runtron's per-request "average tok/s" (one line per user; the mean over users is
the run's TPS); step = 1000 / TPS in ms = the period of one batched decode step (every user of a run
reports the same ms/tok to 0.001 ms); TTFT = "Parsing the prompt took S s" (max over users); cell = one
(block, tp, users, tag, arm); rep = repetition; paired delta = per-rep difference a - b (same block, tp,
users, rep) of the step in ms, with mean, sample sd, n and t = mean / (sd / sqrt(n)); a run is EARLY-STOP
when its users generated unequal token counts or fewer TPS lines than users (its TPS is excluded).
Pairs: every arm vs base and vs headoff, and vnni2 / vnnikill / head30 vs vnni (head30 runs once, so its pair is one run
against the same-rep vnni run, judged by the 1 % rule alone). The m2 criterion D (late minus early) is computed at the end.
Usage: summarize.py RESULTS_DIR
"""
import json
import math
import os
import re
import statistics
import sys
from collections import defaultdict

RES = sys.argv[1]
HDR = re.compile(r"### rt block=(\S+) arm=(\S+) tp=(\d) users=(\d+) gen=(\d+) rep=(\d+) tag=(\S+) env=\[(.*?)\] cats=\[(.*?)\] bin=(\S+) model=(\S+) ts=(\S+)")


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
            cur = {"block": m[1], "arm": m[2], "tp": int(m[3]), "users": int(m[4]), "gen": int(m[5]), "rep": int(m[6]),
                   "tag": m[7], "env": m[8], "cats": m[9], "bin": m[10], "model": m[11], "ts": m[12],
                   "tps": [], "mstok": [], "ttft": [], "gen_counts": [], "failed": False, "stopped": False, "version": None, "hw": None}
            runs.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("RUN-FAILED"):
            cur["failed"] = True
        elif line.startswith("RUN-STOPPED"):
            cur["stopped"] = True
        m = re.search(r"Version: (\S+) hash: ([0-9a-f]+)", line)
        if m:
            cur["version"] = m[1]
        m = re.search(r"HW attention (enabled|disabled)", line)
        if m:
            cur["hw"] = m[1]
        m = re.search(r"Generating (\d+) response tokens .* at ([0-9.]+) average tok/s, or ([0-9.]+) ms/tok", line)
        if m:
            cur["gen_counts"].append(int(m[1])); cur["tps"].append(float(m[2])); cur["mstok"].append(float(m[3]))
        m = re.search(r"Parsing the prompt took ([0-9.]+) s", line)
        if m:
            cur["ttft"].append(float(m[1]))
    for r in runs:
        r["early_stop"] = bool(r["tps"]) and (len(set(r["gen_counts"])) > 1 or len(r["tps"]) != r["users"])
        ok = r["tps"] and not r["failed"] and not r["stopped"] and not r["early_stop"]
        r["tps_mean"] = statistics.mean(r["tps"]) if ok else None
        r["step_ms"] = 1000.0 / r["tps_mean"] if ok else None
        r["mstok_mean"] = statistics.mean(r["mstok"]) if ok else None
        r["ttft_max"] = max(r["ttft"]) if r["ttft"] else None
    return runs


def main():
    runs = parse(os.path.join(RES, "rt-results.txt"))
    cells = defaultdict(list)
    for r in runs:
        cells[(r["block"], r["tp"], r["users"], r["tag"], r["arm"])].append(r)
    summary = {"cells": [], "pairs": []}
    lines = ["# issue4500-20260918 runtron summary", "",
             "Words used here: TPS = tokens per second per user (mean over users of one run); step = 1000/TPS in ms; TTFT = max prompt time over users; sd = sample standard deviation over repetitions; paired t = mean of per-rep differences / (sd / sqrt(n)).", "",
             "## Cells", "", "| block | tp | users | tag | arm | n | TPS mean | TPS sd | step ms (1000/mean TPS) | ms/tok (mean of users) | TTFT s | version | HW attn | failed/stopped/early |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key in sorted(cells):
        rs = cells[key]
        tm, tsd, n = mean_sd([r["tps_mean"] for r in rs])
        sm, ssd, _ = mean_sd([r["step_ms"] for r in rs])
        ttm, _, _ = mean_sd([r["ttft_max"] for r in rs])
        bad = f"{sum(r['failed'] for r in rs)}/{sum(r['stopped'] for r in rs)}/{sum(r['early_stop'] for r in rs)}"
        ver = next((r["version"] for r in rs if r["version"]), "-")
        hw = next((r["hw"] for r in rs if r["hw"]), "-")
        mtm, _, _ = mean_sd([r["mstok_mean"] for r in rs])
        summary["cells"].append({"block": key[0], "tp": key[1], "users": key[2], "tag": key[3], "arm": key[4], "n": n,
                                 "tps_mean": tm, "tps_sd": tsd, "step_ms": sm, "step_sd": ssd, "mstok_mean": mtm, "ttft_s": ttm, "version": ver, "hw": hw,
                                 "reps": [{"rep": r["rep"], "tps": r["tps_mean"], "step_ms": r["step_ms"], "mstok": r["mstok_mean"], "ttft_s": r["ttft_max"], "env": r["env"], "ts": r["ts"],
                                           "failed": r["failed"], "stopped": r["stopped"], "early_stop": r["early_stop"]} for r in rs]})
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} | {key[4]} | {n} | {tm if tm is None else f'{tm:.2f}'} | {tsd if tsd is None else f'{tsd:.2f}'} | {sm if sm is None else f'{sm:.3f}'} | {mtm if mtm is None else f'{mtm:.3f}'} | {ttm if ttm is None else f'{ttm:.3f}'} | {ver} | {hw} | {bad} |")
    # paired comparisons: within (block, tp, users, tag): every arm vs base and vs headoff; within (block, tp, users, arm): tag vs tag
    lines += ["", "## Paired comparisons (a minus b, per repetition)", "",
              "| block | tp | users | a | b | n | step a ms | step b ms | delta ms/step | delta TPS % | delta us/layer (36) | paired t | TTFT delta ms |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def paired(ra, rb, label_a, label_b, block, tp, users):
        byrep_a = {r["rep"]: r for r in ra if r["step_ms"] is not None}
        byrep_b = {r["rep"]: r for r in rb if r["step_ms"] is not None}
        common = sorted(set(byrep_a) & set(byrep_b))
        if not common:
            return
        d = [byrep_a[k]["step_ms"] - byrep_b[k]["step_ms"] for k in common]
        dt = [byrep_a[k]["ttft_max"] - byrep_b[k]["ttft_max"] for k in common if byrep_a[k]["ttft_max"] and byrep_b[k]["ttft_max"]]
        md, sd, n = mean_sd(d)
        t = (md / (sd / math.sqrt(n))) if (sd and n > 1) else None
        sa = statistics.mean(byrep_a[k]["step_ms"] for k in common); sb = statistics.mean(byrep_b[k]["step_ms"] for k in common)
        ta = statistics.mean(byrep_a[k]["tps_mean"] for k in common); tb = statistics.mean(byrep_b[k]["tps_mean"] for k in common)
        pct = 100.0 * (ta / tb - 1.0)
        rec = {"block": block, "tp": tp, "users": users, "a": label_a, "b": label_b, "n": n, "step_a": sa, "step_b": sb,
               "delta_ms": md, "delta_sd": sd, "delta_tps_pct": pct, "delta_us_per_layer": md * 1000 / 36, "t": t,
               "ttft_delta_ms": (statistics.mean(dt) * 1000) if dt else None, "per_rep": d}
        summary["pairs"].append(rec)
        lines.append(f"| {block} | {tp} | {users} | {label_a} | {label_b} | {n} | {sa:.3f} | {sb:.3f} | {md:+.3f} (sd {sd:.3f}) | {pct:+.2f} | {md*1000/36:+.1f} | {'-' if t is None else f'{t:+.2f}'} | {'-' if not dt else f'{statistics.mean(dt)*1000:+.0f}'} |")

    groups = defaultdict(dict)
    for key, rs in cells.items():
        groups[key[:4]][key[4]] = rs
    for g in sorted(groups):
        arms = groups[g]
        for ref in ("base", "headoff", "vnni"):
            if ref in arms:
                for arm in sorted(arms):
                    if arm == ref or (ref == "headoff" and arm == "base") or (ref == "vnni" and arm in ("base", "headoff")):
                        continue
                    paired(arms[arm], arms[ref], f"{arm}/{g[3]}", f"{ref}/{g[3]}", g[0], g[1], g[2])
    # tag vs tag for the same arm (block m2: minb1 vs minb100)
    bytag = defaultdict(dict)
    for key, rs in cells.items():
        bytag[(key[0], key[1], key[2], key[4])][key[3]] = rs
    for g in sorted(bytag):
        tags = sorted(bytag[g])
        for i, ta in enumerate(tags):
            for tb in tags[i + 1:]:
                paired(bytag[g][ta], bytag[g][tb], f"{g[3]}/{ta}", f"{g[3]}/{tb}", g[0], g[1], g[2])
    # m2 criterion: D = d_late - d_early where d_x = per-rep (vnni - headoff) step in ms under tag minb100 (late) / minb1 (early);
    # t = mean(D) / (sd(D) / sqrt(n)) over reps present in all four cells. Positive D = the loss is larger under the late launch (H1).
    lines += ["", "## m2: launch-phase criterion D = (vnni - headoff)@late - (vnni - headoff)@early, per repetition", "",
              "| tp | users | n | d_early ms | d_late ms | D ms | sd | t (threshold 4.30 at n=3, 12.71 at n=2) |", "|---|---|---|---|---|---|---|---|"]
    m2 = defaultdict(dict)
    for key, rs in cells.items():
        if key[0] == "m2":
            m2[(key[1], key[2])][(key[3], key[4])] = {r["rep"]: r for r in rs if r["step_ms"] is not None}
    for (tp, users), d in sorted(m2.items()):
        try:
            reps = set(d[("minb1", "vnni")]) & set(d[("minb1", "headoff")]) & set(d[("minb100", "vnni")]) & set(d[("minb100", "headoff")])
        except KeyError:
            continue
        de = [d[("minb1", "vnni")][k]["step_ms"] - d[("minb1", "headoff")][k]["step_ms"] for k in sorted(reps)]
        dl = [d[("minb100", "vnni")][k]["step_ms"] - d[("minb100", "headoff")][k]["step_ms"] for k in sorted(reps)]
        D = [l - e for l, e in zip(dl, de)]
        md, sd, n = mean_sd(D)
        if n == 0:
            continue
        t = (md / (sd / math.sqrt(n))) if (sd and n > 1) else None
        summary.setdefault("m2_criterion", []).append({"tp": tp, "users": users, "n": n, "d_early": de, "d_late": dl, "D_mean": md, "D_sd": sd, "t": t})
        lines.append(f"| {tp} | {users} | {n} | {statistics.mean(de):+.3f} | {statistics.mean(dl):+.3f} | {md:+.3f} | {sd:.3f} | {'-' if t is None else f'{t:+.2f}'} |")
    json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=1)
    print("\n".join(lines))


main()
