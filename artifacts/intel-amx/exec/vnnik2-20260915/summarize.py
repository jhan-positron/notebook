#!/usr/bin/env python3
"""Summarize exec/results/vnnik2-20260915/rt-results.txt into summary.json (next to the
input) and a markdown table on stdout.

Definitions: TPS = runtron's per-request "average tok/s" averaged over the 8 requests of a
run; TTFT = "Parsing the prompt took S s" (max over the 8 requests); then mean and sd over
the repetitions of a cell (tp, prompt, arm). Arms: base (PR #3879 binary, row-major K),
vnni (Monday's VNNI binary), vnni0 (new binary, both switches off = the old store), a
(block store), b (helper striping), ab (both). Deltas a/b - 1 in percent: each arm against
base, and each new arm against vnni0 (the same binary, old store). EARLY-STOP flags a run
whose requests generated unequal token counts or fewer TPS lines than users.
Usage: summarize.py RESULTS_DIR
"""
import json
import os
import re
import statistics
import sys

RES = sys.argv[1]
ARMS = ["base", "vnni", "vnni0", "a", "b", "ab"]
PAIRS = [("vnni", "base"), ("vnni0", "base"), ("a", "base"), ("b", "base"), ("ab", "base"),
         ("vnni0", "vnni"), ("a", "vnni0"), ("b", "vnni0"), ("ab", "vnni0")]


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
                   "tps": [], "ttft": [], "gen": [], "failed": False, "stopped": False, "header": line}
            runs.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("RUN-FAILED"):
            cur["failed"] = True
        elif line.startswith("RUN-STOPPED") or line.startswith("RUN-GIVEN-UP"):
            cur["stopped"] = True
        m = re.search(r"Parsing the prompt took ([0-9.]+) s", line)
        if m:
            cur["ttft"].append(float(m[1]))
        m = re.search(r"Generating (\d+) response tokens with \d+ context took [0-9.]+ s at ([0-9.]+) average tok/s", line)
        if m:
            cur["gen"].append(int(m[1]))
            cur["tps"].append(float(m[2]))
    return runs


def main():
    runs = parse(os.path.join(RES, "rt-results.txt"))
    cells = {}
    for r in runs:
        if r["failed"] or r["stopped"] or not r["tps"]:
            continue
        r["tps_per_user"] = statistics.mean(r["tps"])
        r["ttft_s"] = max(r["ttft"]) if r["ttft"] else None
        r["early_stop"] = (len(r["tps"]) != 8) or (min(r["gen"]) != max(r["gen"]))
        cells.setdefault((r["tp"], r["prompt"], r["arm"]), []).append(r)
    out = {"cells": [], "deltas": []}
    lines = ["# vnnik2-20260915 summary", "", "Per cell: mean over repetitions (sd), n = repetitions. TPS = decode tok/s per user; TTFT = prefill s (8 prompts).", ""]
    for tp in (2, 4):
        prompts = sorted({k[1] for k in cells if k[0] == tp})
        if not prompts:
            continue
        lines += [f"## tp{tp}", "", "| prompt | arm | n | TPS/user | sd | TTFT s | sd | early-stop runs |", "|---|---|---|---|---|---|---|---|"]
        stats = {}
        for prompt in prompts:
            for arm in ARMS:
                rs = cells.get((tp, prompt, arm))
                if not rs:
                    continue
                tm, tsd, n = mean_sd([r["tps_per_user"] for r in rs])
                fm, fsd, _ = mean_sd([r["ttft_s"] for r in rs])
                es = sum(1 for r in rs if r["early_stop"])
                stats[(prompt, arm)] = (tm, fm)
                out["cells"].append({"tp": tp, "prompt": prompt, "arm": arm, "n": n, "tps_mean": tm, "tps_sd": tsd, "ttft_mean": fm, "ttft_sd": fsd,
                                     "early_stop_runs": es, "reps": [{"rep": r["rep"], "tps_per_user": r["tps_per_user"], "ttft_s": r["ttft_s"]} for r in rs]})
                lines.append(f"| {prompt} | {arm} | {n} | {tm:.2f} | {tsd:.2f} | {fm:.3f} | {fsd:.3f} | {es} |")
        lines += ["", "| prompt | comparison | TPS delta % | TTFT delta % (time; negative = faster) | TTFT delta ms |", "|---|---|---|---|---|"]
        for prompt in prompts:
            for a, b in PAIRS:
                if (prompt, a) in stats and (prompt, b) in stats:
                    ta, fa = stats[(prompt, a)]
                    tb, fb = stats[(prompt, b)]
                    dt, df = 100 * (ta / tb - 1), 100 * (fa / fb - 1)
                    out["deltas"].append({"tp": tp, "prompt": prompt, "a": a, "b": b, "tps_delta_pct": dt, "ttft_delta_pct": df, "ttft_delta_ms": 1000 * (fa - fb)})
                    lines.append(f"| {prompt} | {a} vs {b} | {dt:+.1f} | {df:+.1f} | {1000*(fa-fb):+.0f} |")
        lines.append("")
    bad = [r["header"] for r in runs if r["failed"] or r["stopped"]]
    lines += [f"Excluded attempts (failed or stopped): {len(bad)}"] + [f"- {h}" for h in bad] + [""]
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
