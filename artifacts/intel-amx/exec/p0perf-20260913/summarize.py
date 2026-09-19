#!/usr/bin/env python3
"""Summarize the p0perf-20260913 campaign: runtron cells (exec/results/p0perf-20260913/
rt-results.txt) and CI-config cells (cells/<model>__<arm>__rep<N>/perf.json, pooled over the
cell's engines by combine.py) into summary.json (next to the inputs) and a markdown table on
stdout. Fork of exec/p0perf-20260911/summarize.py; the CI cells now have three arms and the
nightly's per-engine load (tp2: 2 engines x 2 users, tp4: 1 engine x 4 users).

Definitions used here:
  runtron TPS  = the per-request decode rate runtron prints ("... at X average tok/s"),
                 averaged over the 8 requests of one run (they differ only in the 4th digit).
  runtron TTFT = "Parsing the prompt took S s": wall time of the batched prefill of the 8
                 prompts, i.e. the time until the first generated token of each request;
                 max over the 8 requests (they are equal to the millisecond).
  CI TPS       = perf.json tps_mean: per-user decode rate in the 896-1024 capture window,
                 averaged over every user sample of the cell (10 rounds x users), the way the
                 nightly's "Running averages" TPS pools its 8 users.
  CI TTFT      = perf.json ttft_mean_ms: time to the first streamed chunk, same averaging.
  arms         = off (AMX build, kill switch TRON_AMX_DISABLE=1, CPU attention), on (same binary,
                 CPU attention, switch unset), fpga (same binary, USE_HW_ATTN unset = the
                 nightly's current default: attention on the FPGA from query position 127 on,
                 positions 0-126 on the CPU; kill switch set so that CPU share runs on AVX as
                 main does). runtron cells: off, on only.
  on vs off    = on / off - 1 (the AMX gain in the CPU-attention path).
  on vs fpga   = on / fpga - 1 (the change the nightly would report after switching its qwen
                 engines from FPGA attention to CPU attention with AMX; TTFT: change of the time).
  nightly ref  = the nightly's own qwen numbers of 2026-09-11 (run 34559196745; main branch
                 package with FPGA attention, 4 tp2 / 2 tp4 engines): printed for orientation.
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
CI_ARMS = ["off", "on", "fpga"]
NIGHTLY_REF = os.path.join(os.path.dirname(RES.rstrip("/")), "p0perf-20260911", "ci-reference-20260911.json")


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
            users = int(re.search(r"users=(\d+)", r["header"]).group(1)) if re.search(r"users=(\d+)", r["header"]) else 8
            rows.append({"rep": r["rep"], "attempt": r["attempt"], "n_requests": len(r["tps"]),
                         "tps_per_user": statistics.mean(r["tps"]), "tps_aggregate": sum(r["tps"]),
                         "ttft_s": max(r["ttft"]) if r["ttft"] else None,
                         "prefill_tok_s_per_request": statistics.mean(r["prefill"]) if r["prefill"] else None,
                         "gen_tokens_min": min(r["gen"]), "gen_tokens_max": max(r["gen"]), "context": r.get("context"),
                         # early stop: one request hit a stop token before the sequence limit (lower count), or before its
                         # 2nd generated token (runtron prints no line, so fewer lines than users= in the header)
                         "early_stop": (min(r["gen"]) != max(r["gen"])) or (len(r["tps"]) != users),
                         "machine": r["header"]})
        runs[key] = rows
    return runs


def parse_ci(res):
    """-> {(tp, arm): [ {rep, tps_mean, tps_sd, min_tps, ttft_ms, minutes, status, machine, per_engine} ]}"""
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
        d = None
        if os.path.exists(pj):
            try:
                d = json.load(open(pj))
            except Exception as e:  # a truncated file must not hide the other cells
                row["status"] = f"{status} (bad perf.json: {e})"
        if d is not None:
            row.update({"tps_mean": d["tps_mean"], "tps_sd": d["tps_std_dev"], "min_tps": d["min_tps"], "ttft_ms": d["ttft_mean_ms"],
                        "minutes": d["minutes"], "n_users": d["n_users"], "n_engines": d.get("n_engines", 1),
                        "n_samples": len(d["tps_results"]), "prompt_tokens_mean": d.get("prompt_tokens_mean"),
                        "cache_hit_pct": d.get("cache_hit_pct"), "per_engine": d.get("per_engine", [])})
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


def valid(rows):  # runtron runs without an early stop; the mean is an 8-user number only for those
    return [r for r in rows if not r.get("early_stop")]


def paired(a_rows, b_rows, key):  # per-repetition b/a deltas in percent (matching rep numbers only)
    a = {r["rep"]: r[key] for r in a_rows if r.get(key) is not None}
    b = {r["rep"]: r[key] for r in b_rows if r.get(key) is not None}
    return {rep_: 100.0 * (b[rep_] / a[rep_] - 1) for rep_ in sorted(set(a) & set(b))}


def fmt_paired(pr):
    return ", ".join(f"{v:+.1f}%" for v in pr.values()) if pr else "n/a"


rt = parse_runtron(os.path.join(RES, "rt-results.txt"))
ci = parse_ci(RES)
nightly = {}
if os.path.exists(NIGHTLY_REF):
    try:
        ref = json.load(open(NIGHTLY_REF))
        for tp in (2, 4):
            rows = ref.get("perf", {}).get(MODELS[tp], [])
            if rows:
                nightly[tp] = {"tps": rows[-1]["tps"], "ttft_ms": rows[-1]["ttft_ms"], "run_id": ref.get("run_id")}
    except Exception as e:
        nightly = {"error": str(e)}
summary = {"runtron": {}, "ci": {}, "nightly_reference": nightly}
lines = []

# --- runtron: off / on ---
lines.append("## runtron (8 users on one process, prompt 1024, 256 generated)")
lines.append("")
lines.append("| tp | metric | AMX-off | AMX-on | on vs off (per rep) |")
lines.append("|---|---|---|---|---|")
for tp in (2, 4):
    off_all, on_all = rt.get((tp, "off"), []), rt.get((tp, "on"), [])
    off, on = valid(off_all), valid(on_all)
    m_off = agg(off, "tps_per_user"); m_on = agg(on, "tps_per_user")
    t_off = agg(off, "ttft_s"); t_on = agg(on, "ttft_s")
    pr = paired(off, on, "tps_per_user"); prt = paired(off, on, "ttft_s")
    summary["runtron"][f"tp{tp}"] = {"off": off_all, "on": on_all,
        "excluded_early_stop": [f"{r['rep']}:{arm}" for arm, rows in (("off", off_all), ("on", on_all)) for r in rows if r.get("early_stop")],
        "tps_per_user": {"off": m_off, "on": m_on, "boost_pct": pct(m_on[0], m_off[0]), "paired_pct": pr},
        "ttft_s": {"off": t_off, "on": t_on, "change_pct": pct(t_on[0], t_off[0]), "paired_pct": prt}}
    lines.append(f"| {tp} | decode TPS per user | {fmt_pm(*m_off)} | {fmt_pm(*m_on)} | {fmt(pct(m_on[0], m_off[0]), 1, '%')} ({fmt_paired(pr)}) |")
    lines.append(f"| {tp} | TTFT (prompt parse, s) | {fmt_pm(*t_off, nd=3)} | {fmt_pm(*t_on, nd=3)} | {fmt(pct(t_on[0], t_off[0]), 1, '%')} ({fmt_paired(prt)}) |")
lines.append("")

# --- CI-config: off / on / fpga ---
lines.append("## CI harness, the nightly's per-engine load (tp2: 2 engines x 2 users; tp4: 1 engine x 4 users; 10 rounds)")
lines.append("")
lines.append("| tp | metric | AMX-off | AMX-on | FPGA attention (nightly default) | on vs off (per rep) | on vs fpga (per rep) | off vs fpga | nightly 2026-09-11 |")
lines.append("|---|---|---|---|---|---|---|---|---|")
for tp in (2, 4):
    done = {arm: [r for r in ci.get((tp, arm), []) if r["status"] == "done"] for arm in CI_ARMS}
    m = {arm: agg(done[arm], "tps_mean") for arm in CI_ARMS}
    t = {arm: agg(done[arm], "ttft_ms") for arm in CI_ARMS}
    pr_on_off = paired(done["off"], done["on"], "tps_mean"); pr_on_fpga = paired(done["fpga"], done["on"], "tps_mean")
    prt_on_off = paired(done["off"], done["on"], "ttft_ms"); prt_on_fpga = paired(done["fpga"], done["on"], "ttft_ms")
    nref = nightly.get(tp, {})
    summary["ci"][f"tp{tp}"] = {arm: ci.get((tp, arm), []) for arm in CI_ARMS}
    summary["ci"][f"tp{tp}"].update({
        "tps_per_user": {arm: m[arm] for arm in CI_ARMS} | {"on_vs_off_pct": pct(m["on"][0], m["off"][0]), "on_vs_fpga_pct": pct(m["on"][0], m["fpga"][0]),
                                                         "off_vs_fpga_pct": pct(m["off"][0], m["fpga"][0]), "paired_on_vs_off": pr_on_off, "paired_on_vs_fpga": pr_on_fpga},
        "ttft_ms": {arm: t[arm] for arm in CI_ARMS} | {"on_vs_off_pct": pct(t["on"][0], t["off"][0]), "on_vs_fpga_pct": pct(t["on"][0], t["fpga"][0]),
                                                    "off_vs_fpga_pct": pct(t["off"][0], t["fpga"][0]), "paired_on_vs_off": prt_on_off, "paired_on_vs_fpga": prt_on_fpga},
        "nightly_reference": nref})
    lines.append(f"| {tp} | decode TPS per user | {fmt_pm(*m['off'])} | {fmt_pm(*m['on'])} | {fmt_pm(*m['fpga'])} | "
                 f"{fmt(pct(m['on'][0], m['off'][0]), 1, '%')} ({fmt_paired(pr_on_off)}) | {fmt(pct(m['on'][0], m['fpga'][0]), 1, '%')} ({fmt_paired(pr_on_fpga)}) | "
                 f"{fmt(pct(m['off'][0], m['fpga'][0]), 1, '%')} | {fmt(nref.get('tps'), 2) if nref else 'n/a'} |")
    lines.append(f"| {tp} | TTFT (ms) | {fmt_pm(*t['off'], nd=0)} | {fmt_pm(*t['on'], nd=0)} | {fmt_pm(*t['fpga'], nd=0)} | "
                 f"{fmt(pct(t['on'][0], t['off'][0]), 1, '%')} ({fmt_paired(prt_on_off)}) | {fmt(pct(t['on'][0], t['fpga'][0]), 1, '%')} ({fmt_paired(prt_on_fpga)}) | "
                 f"{fmt(pct(t['off'][0], t['fpga'][0]), 1, '%')} | {nref.get('ttft_ms', 'n/a') if nref else 'n/a'} |")
lines.append("")
lines.append("Per-run values (runtron: per-user TPS / TTFT s; CI: per-user TPS ± sd over all samples / TTFT ms, then each engine). "
             "Runtron runs marked EARLY-STOP (one user hit a stop token early, so part of the decode ran with fewer users) are excluded from the means and the paired deltas above:")
for tp in (2, 4):
    for arm in ("off", "on"):
        for r in rt.get((tp, arm), []):
            lines.append(f"- runtron tp{tp} {arm} rep{r['rep']}: TPS {r['tps_per_user']:.3f} (x{r['n_requests']} requests, aggregate {r['tps_aggregate']:.1f}), TTFT {fmt(r['ttft_s'], 3)} s, generated {r['gen_tokens_min']}-{r['gen_tokens_max']} tokens{' EARLY-STOP' if r['early_stop'] else ''}; {r['machine']}")
for tp in (2, 4):
    for arm in CI_ARMS:
        for r in ci.get((tp, arm), []):
            if "tps_mean" in r:
                eng = "; ".join(f"engine {i}: {e['n_users']} users TPS {e['tps_mean']:.2f} TTFT {e['ttft_mean_ms']} ms" for i, e in enumerate(r.get("per_engine", [])))
                lines.append(f"- CI tp{tp} {arm} rep{r['rep']}: TPS {r['tps_mean']:.2f} ± {r['tps_sd']:.2f} (min {r['min_tps']:.2f}, {r['n_samples']} samples, {r['n_users']} users on {r['n_engines']} engine(s)), TTFT {r['ttft_ms']} ms, {r['minutes']:.1f} min, status {r['status']}; {eng}; {r['machine']}")
            else:
                lines.append(f"- CI tp{tp} {arm} rep{r['rep']}: status {r['status']} (no perf.json)")
missing = [f"runtron tp{tp} {arm}" for tp in (2, 4) for arm in ("off", "on") if not rt.get((tp, arm))]
missing += [f"CI tp{tp} {arm}" for tp in (2, 4) for arm in CI_ARMS if not [r for r in ci.get((tp, arm), []) if r["status"] == "done"]]
if missing:
    lines.append("")
    lines.append("MISSING cells (no successful run): " + ", ".join(missing))
summary["missing"] = missing
json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=1, default=str)
print("\n".join(lines))
