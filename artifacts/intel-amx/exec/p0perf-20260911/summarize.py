#!/usr/bin/env python3
"""Summarize the p0perf-20260911 campaign: runtron cells (exec/results/p0perf-20260911/
rt-results.txt) and CI-harness cells (cells/<model>__<arm>__rep<N>/perf.json) into
summary.json (next to the inputs) and a markdown table on stdout.

Definitions used here:
  runtron TPS  = the per-request decode rate runtron prints ("... at X average tok/s"),
                 averaged over the 8 requests of one run (they differ only in the 4th digit).
  runtron TTFT = "Parsing the prompt took S s": wall time of the batched prefill of the 8
                 prompts, i.e. the time until the first generated token of each request;
                 max over the 8 requests (they are equal to the millisecond).
  CI TPS       = perf.json tps_mean: per-user decode rate in the 896-1024 capture window,
                 averaged over 8 users x 10 rounds (the nightly's "Running averages" TPS).
  CI TTFT      = perf.json ttft_mean_ms: time to the first streamed chunk, same averaging.
  boost        = on / off - 1 of the per-cell means (TPS: higher is better; TTFT: lower is
                 better, so the TTFT row reports the change of the time).
Usage: summarize.py RESULTS_DIR
"""
import glob
import json
import os
import re
import statistics
import sys

RES = sys.argv[1]
MODELS = {2: "ingested-qwen-3-4b-instruct-2507-tp2", 4: "ingested-qwen-3-4b-instruct-2507-tp4"}


def mean_sd(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None, 0
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0), len(xs)


def parse_runtron(path):
    """-> {(tp, arm): [ {rep, attempt, tps_per_user, tps_aggregate, ttft_s, prefill_tok_s, machine, status} ]}"""
    out = {}
    if not os.path.exists(path):
        return out
    cur = None
    for line in open(path, errors="replace"):
        m = re.match(r"### runtron tp=(\d) arm=(\w+) rep=(\d+) attempt=(\d+) (.*)", line)
        if m:
            cur = {"tp": int(m.group(1)), "arm": m.group(2), "rep": int(m.group(3)), "attempt": int(m.group(4)),
                   "header": m.group(5).strip(), "tps": [], "gen": [], "ttft": [], "prefill": [], "status": "ok"}
            out.setdefault((cur["tp"], cur["arm"]), []).append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("RUN-STOPPED"):
            cur["status"] = "stopped"
        elif line.startswith("RUN-FAILED"):
            cur["status"] = "failed"
        elif line.startswith("RUN-GIVEN-UP"):
            cur["status"] = "given-up"
        m = re.search(r"Parsing the prompt took ([\d.]+) s at ([\d.]+) tokens/s", line)
        if m:
            cur["ttft"].append(float(m.group(1))); cur["prefill"].append(float(m.group(2)))
        m = re.search(r"Generating (\d+) response tokens with (\d+) context took ([\d.]+) s at ([\d.]+) average tok/s", line)
        if m:
            cur["tps"].append(float(m.group(4))); cur["gen"].append(int(m.group(1))); cur["context"] = int(m.group(2))
    runs = {}
    for key, lst in out.items():
        rows = []
        for r in lst:
            if r["status"] != "ok" or not r["tps"]:
                continue   # stopped/failed attempts carry no numbers; the retried attempt does
            rows.append({"rep": r["rep"], "attempt": r["attempt"], "n_requests": len(r["tps"]),
                         "tps_per_user": statistics.mean(r["tps"]), "tps_aggregate": sum(r["tps"]),
                         "ttft_s": max(r["ttft"]) if r["ttft"] else None,
                         "prefill_tok_s_per_request": statistics.mean(r["prefill"]) if r["prefill"] else None,
                         "gen_tokens_min": min(r["gen"]), "gen_tokens_max": max(r["gen"]), "context": r.get("context"),
                         # early stop: one request hit a stop token before the sequence limit (lower count), or before its
                         # 2nd generated token (runtron prints no line, so fewer lines than users= in the header)
                         "early_stop": (min(r["gen"]) != max(r["gen"])) or (len(r["tps"]) != int((re.search(r"users=(\d+)", r["header"]).group(1)) if re.search(r"users=(\d+)", r["header"]) else 8)),
                         "machine": r["header"]})
        runs[key] = rows
    return runs


def parse_ci(res):
    """-> {(tp, arm): [ {rep, tps_mean, tps_sd, min_tps, ttft_ms, minutes, status, machine} ]}"""
    out = {}
    for cell in sorted(glob.glob(os.path.join(res, "cells", "*__*__rep*"))):
        name = os.path.basename(cell)
        m = re.match(r"(.+)__(\w+)__rep(\d+)$", name)
        if not m:
            continue
        model, arm, rep = m.group(1), m.group(2), int(m.group(3))
        tp = int(model.rsplit("tp", 1)[1])
        status = open(os.path.join(cell, "STATUS")).read().strip() if os.path.exists(os.path.join(cell, "STATUS")) else "missing"
        meta = json.load(open(os.path.join(cell, "meta.json"))) if os.path.exists(os.path.join(cell, "meta.json")) else {}
        row = {"rep": rep, "status": status, "machine": meta.get("machine", ""), "started": meta.get("started")}
        pj = os.path.join(cell, "perf.json")
        if os.path.exists(pj):
            try:
                d = json.load(open(pj))
            except Exception as e:  # a truncated file must not hide the other cells
                row["status"] = f"{status} (bad perf.json: {e})"; d = None
        if os.path.exists(pj) and d is not None:
            row.update({"tps_mean": d["tps_mean"], "tps_sd": d["tps_std_dev"], "min_tps": d["min_tps"], "ttft_ms": d["ttft_mean_ms"],
                        "minutes": d["minutes"], "n_users": d["n_users"], "n_samples": len(d["tps_results"]),
                        "prompt_tokens_mean": d.get("prompt_tokens_mean"), "cache_hit_pct": d.get("cache_hit_pct")})
        out.setdefault((tp, arm), []).append(row)
    return out


def agg(rows, key):
    return mean_sd([r.get(key) for r in rows])


def pct(a, b):
    return None if (a is None or b in (None, 0)) else 100.0 * (a / b - 1)


def fmt(x, nd=2, unit=""):
    return "n/a" if x is None else f"{x:.{nd}f}{unit}"


def fmt_pm(m, sd, n, nd=2, unit=""):
    if m is None:
        return "n/a"
    return f"{m:.{nd}f}{unit} ± {sd:.{nd}f} (n={n})" if n > 1 else f"{m:.{nd}f}{unit} (n=1)"


rt = parse_runtron(os.path.join(RES, "rt-results.txt"))
ci = parse_ci(RES)
summary = {"runtron": {}, "ci": {}}
lines = []
lines.append("| test | tp | metric | AMX-off | AMX-on | on vs off |")
lines.append("|---|---|---|---|---|---|")
def valid(rows):  # runs without an early stop; the mean is an 8-user number only for those
    return [r for r in rows if not r.get("early_stop")]


def paired(off_rows, on_rows, key):  # per-repetition on/off deltas in percent, valid runs only
    o = {r["rep"]: r[key] for r in valid(off_rows) if r.get(key) is not None}
    n = {r["rep"]: r[key] for r in valid(on_rows) if r.get(key) is not None}
    return {rep_: 100.0 * (n[rep_] / o[rep_] - 1) for rep_ in sorted(set(o) & set(n))}


for tp in (2, 4):
    off_all, on_all = rt.get((tp, "off"), []), rt.get((tp, "on"), [])
    off, on = valid(off_all), valid(on_all)
    m_off = agg(off, "tps_per_user"); m_on = agg(on, "tps_per_user")
    t_off = agg(off, "ttft_s"); t_on = agg(on, "ttft_s")
    summary["runtron"][f"tp{tp}"] = {"off": off_all, "on": on_all, "excluded_early_stop": [f"{r['rep']}:{arm}" for arm, rows in (("off", off_all), ("on", on_all)) for r in rows if r.get("early_stop")],
        "tps_per_user": {"off": m_off, "on": m_on, "boost_pct": pct(m_on[0], m_off[0]), "paired_pct": paired(off_all, on_all, "tps_per_user")},
        "ttft_s": {"off": t_off, "on": t_on, "change_pct": pct(t_on[0], t_off[0]), "paired_pct": paired(off_all, on_all, "ttft_s")}}
    pr = paired(off_all, on_all, "tps_per_user")
    lines.append(f"| runtron | {tp} | decode TPS per user | {fmt_pm(*m_off)} | {fmt_pm(*m_on)} | {fmt(pct(m_on[0], m_off[0]), 1, '%')} (per rep: {', '.join(f'{v:+.1f}%' for v in pr.values())}) |")
    lines.append(f"| runtron | {tp} | TTFT (prompt parse, s) | {fmt_pm(*t_off, nd=3)} | {fmt_pm(*t_on, nd=3)} | {fmt(pct(t_on[0], t_off[0]), 1, '%')} |")
for tp in (2, 4):
    off = [r for r in ci.get((tp, "off"), []) if r["status"] == "done"]
    on = [r for r in ci.get((tp, "on"), []) if r["status"] == "done"]
    m_off = agg(off, "tps_mean"); m_on = agg(on, "tps_mean")
    t_off = agg(off, "ttft_ms"); t_on = agg(on, "ttft_ms")
    pr = paired(off, on, "tps_mean")
    summary["ci"][f"tp{tp}"] = {"off": ci.get((tp, "off"), []), "on": ci.get((tp, "on"), []),
        "tps_per_user": {"off": m_off, "on": m_on, "boost_pct": pct(m_on[0], m_off[0]), "paired_pct": pr},
        "ttft_ms": {"off": t_off, "on": t_on, "change_pct": pct(t_on[0], t_off[0]), "paired_pct": paired(off, on, "ttft_ms")}}
    lines.append(f"| CI harness | {tp} | decode TPS per user | {fmt_pm(*m_off)} | {fmt_pm(*m_on)} | {fmt(pct(m_on[0], m_off[0]), 1, '%')} (per rep: {', '.join(f'{v:+.1f}%' for v in pr.values())}) |")
    lines.append(f"| CI harness | {tp} | TTFT (ms) | {fmt_pm(*t_off, nd=0)} | {fmt_pm(*t_on, nd=0)} | {fmt(pct(t_on[0], t_off[0]), 1, '%')} |")
lines.append("")
lines.append("Per-run values (runtron: per-user TPS / TTFT s; CI: per-user TPS ± sd over 80 samples / TTFT ms). Runtron runs marked EARLY-STOP (one user hit a stop token early, so part of the decode ran with fewer users) are excluded from the means and the paired deltas above:")
for tp in (2, 4):
    for arm in ("off", "on"):
        for r in rt.get((tp, arm), []):
            lines.append(f"- runtron tp{tp} {arm} rep{r['rep']}: TPS {r['tps_per_user']:.3f} (x{r['n_requests']} requests, aggregate {r['tps_aggregate']:.1f}), TTFT {fmt(r['ttft_s'], 3)} s, generated {r['gen_tokens_min']}-{r['gen_tokens_max']} tokens{' EARLY-STOP' if r['early_stop'] else ''}; {r['machine']}")
for tp in (2, 4):
    for arm in ("off", "on"):
        for r in ci.get((tp, arm), []):
            if "tps_mean" in r:
                lines.append(f"- CI tp{tp} {arm} rep{r['rep']}: TPS {r['tps_mean']:.2f} ± {r['tps_sd']:.2f} (min {r['min_tps']:.2f}, {r['n_samples']} samples), TTFT {r['ttft_ms']} ms, {r['minutes']:.1f} min, status {r['status']}; {r['machine']}")
            else:
                lines.append(f"- CI tp{tp} {arm} rep{r['rep']}: status {r['status']} (no perf.json)")
missing = [f"runtron tp{tp} {arm}" for tp in (2, 4) for arm in ("off", "on") if not rt.get((tp, arm))]
missing += [f"CI tp{tp} {arm}" for tp in (2, 4) for arm in ("off", "on") if not [r for r in ci.get((tp, arm), []) if r["status"] == "done"]]
if missing:
    lines.append("")
    lines.append("MISSING cells (no successful run): " + ", ".join(missing))
summary["missing"] = missing
json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=1, default=str)
print("\n".join(lines))
