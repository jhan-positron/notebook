#!/usr/bin/env python3
"""Summarize the vnnik-20260914 campaign (exec/results/vnnik-20260914/rt-results.txt) into
summary.json (next to the input) and a markdown table on stdout.

Definitions used here:
  TPS  = the per-request decode rate runtron prints ("... at X average tok/s"), averaged
         over the 8 requests of one run; then mean and sd over the repetitions of a cell.
  TTFT = "Parsing the prompt took S s": wall time of the batched prefill of the 8 prompts,
         i.e. the time until the first generated token of each request; max over the 8
         requests of a run (they are equal to the millisecond); then mean and sd.
  arms = off (base binary, kill switch), base (base binary, AMX on), vnni (VNNI binary,
         AMX on), vnnioff (VNNI binary, kill switch).
  deltas = vnni vs base (the design), base vs off (the known AMX gain), vnnioff vs off
         (the software path change alone), vnni vs off (total over AVX). TPS delta =
         a/b - 1; TTFT delta = a/b - 1 of the time (negative = faster).
  EARLY-STOP = a request generated fewer tokens than the other requests of the run (a stop
         token; runtron prints 253 for a full -l 256 request: response size minus one minus
         padding), or the run has fewer "average tok/s" lines than users; its TPS is kept
         but the run is flagged, because the other users then run with less load.
Usage: summarize.py RESULTS_DIR
"""
import json
import os
import re
import statistics
import sys

RES = sys.argv[1]
ARMS = ["off", "base", "vnni", "vnnioff"]
PAIRS = [("vnni", "base"), ("base", "off"), ("vnnioff", "off"), ("vnni", "off"), ("vnni", "vnnioff")]


def mean_sd(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None, 0
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0), len(xs)


def parse(path):
    runs = []
    cur = None
    for line in open(path, errors="replace"):
        m = re.match(r"### runtron tp=(\d) prompt=(\d+) arm=(\w+) rep=(\d+) attempt=(\d+) (.*)", line)
        if m:
            hdr = m.group(6).strip()
            mt = re.search(r"\btip=(\S+)", hdr)
            mu = re.search(r"\busers=(\d+)", hdr)
            cur = {"tp": int(m.group(1)), "prompt": int(m.group(2)), "arm": m.group(3), "rep": int(m.group(4)),
                   "attempt": int(m.group(5)), "header": hdr, "tps": [], "gen": [], "ttft": [],
                   "prefill_tok_s": [], "status": "ok", "context": None, "placement": None, "cpus": None,
                   "tip": mt.group(1) if mt else None, "users": int(mu.group(1)) if mu else 8}
            runs.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("RUN-STOPPED"):
            cur["status"] = "stopped"
        elif line.startswith("RUN-FAILED"):
            cur["status"] = "failed"
        elif line.startswith("RUN-GIVEN-UP"):
            cur["status"] = "given-up"
        m = re.search(r"Configured instance[^\n]*", line)
        if m:
            cur["placement"] = m.group(0).strip()[:160]
        m = re.search(r"App CPU list[^\n]*", line)
        if m:
            cur["cpus"] = m.group(0).strip()[:200]
        m = re.search(r"Parsing the prompt took ([\d.]+) s at ([\d.]+) tokens/s", line)
        if m:
            cur["ttft"].append(float(m.group(1)))
            cur["prefill_tok_s"].append(float(m.group(2)))
        m = re.search(r"Generating (\d+) response tokens with (\d+) context took ([\d.]+) s at ([\d.]+) average tok/s", line)
        if m:
            cur["tps"].append(float(m.group(4)))
            cur["gen"].append(int(m.group(1)))
            cur["context"] = int(m.group(2))
    return runs


runs = parse(os.path.join(RES, "rt-results.txt"))
# the last complete attempt of each (tp, prompt, arm, rep) wins
by_key = {}
for r in runs:
    if r["status"] == "ok" and r["tps"]:
        by_key[(r["tp"], r["prompt"], r["arm"], r["rep"])] = r
rows = {}
for (tp, prompt, arm, rep), r in by_key.items():
    rows.setdefault((tp, prompt, arm), []).append({
        "rep": rep, "attempt": r["attempt"], "tps_per_user": statistics.mean(r["tps"]),
        "tps_aggregate": sum(r["tps"]), "ttft_s": max(r["ttft"]) if r["ttft"] else None,
        "prefill_tok_s": statistics.mean(r["prefill_tok_s"]) if r["prefill_tok_s"] else None,
        "generated": r["gen"], "early_stop": (min(r["gen"]) != max(r["gen"])) or (len(r["tps"]) != r["users"]),
        "context": r["context"], "tip": r["tip"],
        "header": r["header"], "placement": r["placement"], "cpus": r["cpus"]})

cells = {}
for key, reps in sorted(rows.items()):
    reps.sort(key=lambda x: x["rep"])
    tps_m, tps_sd, n = mean_sd([x["tps_per_user"] for x in reps])
    ttft_m, ttft_sd, _ = mean_sd([x["ttft_s"] for x in reps])
    cells["tp%d p%d %s" % key] = {"tp": key[0], "prompt": key[1], "arm": key[2], "n": n, "tps_mean": tps_m, "tps_sd": tps_sd,
                                  "ttft_mean_s": ttft_m, "ttft_sd_s": ttft_sd,
                                  "early_stop_runs": sum(1 for x in reps if x["early_stop"]),
                                  "tips": sorted({x["tip"] for x in reps if x["tip"]}), "reps": reps}


def cell(tp, prompt, arm):
    return cells.get("tp%d p%d %s" % (tp, prompt, arm))


deltas = {}
for tp in (2, 4):
    for prompt in sorted({k[1] for k in rows}):
        for a, b in PAIRS:
            ca, cb = cell(tp, prompt, a), cell(tp, prompt, b)
            if not ca or not cb or ca["tps_mean"] is None or cb["tps_mean"] is None:
                continue
            d = {"tps_pct": 100 * (ca["tps_mean"] / cb["tps_mean"] - 1)}
            if ca["ttft_mean_s"] and cb["ttft_mean_s"]:
                d["ttft_pct"] = 100 * (ca["ttft_mean_s"] / cb["ttft_mean_s"] - 1)
            deltas["tp%d p%d %s vs %s" % (tp, prompt, a, b)] = d

failed = [{"tp": r["tp"], "prompt": r["prompt"], "arm": r["arm"], "rep": r["rep"], "attempt": r["attempt"], "status": r["status"]}
          for r in runs if r["status"] != "ok"]
out = {"cells": cells, "deltas": deltas, "failed_or_stopped_attempts": failed,
       "definitions": __doc__}
json.dump(out, open(os.path.join(RES, "summary.json"), "w"), indent=1)

print("# vnnik-20260914 summary\n")
print("Per cell: mean over repetitions (sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (8 prompts).\n")
for tp in (2, 4):
    prompts = sorted({k[1] for k in rows if k[0] == tp})
    if not prompts:
        continue
    print(f"## tp{tp}\n")
    print("| prompt | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs |")
    print("|---|---|---|---|---|---|---|---|")
    for prompt in prompts:
        for arm in ARMS:
            c = cell(tp, prompt, arm)
            if not c:
                continue
            print(f"| {prompt} | {arm} | {c['n']} | {c['tps_mean']:.2f} | {c['tps_sd']:.2f} | "
                  f"{c['ttft_mean_s']:.3f} | {c['ttft_sd_s']:.3f} | {c['early_stop_runs']} |")
    print()
    print("| prompt | comparison | TPS delta % | TTFT delta % (time; negative = faster) |")
    print("|---|---|---|---|")
    for prompt in prompts:
        for a, b in PAIRS:
            d = deltas.get("tp%d p%d %s vs %s" % (tp, prompt, a, b))
            if d:
                print(f"| {prompt} | {a} vs {b} | {d['tps_pct']:+.1f} | {d.get('ttft_pct', float('nan')):+.1f} |")
    print()
if failed:
    print("## failed or stopped attempts\n")
    for f in failed:
        print(f"- tp{f['tp']} p{f['prompt']} {f['arm']} rep{f['rep']} attempt{f['attempt']}: {f['status']}")
