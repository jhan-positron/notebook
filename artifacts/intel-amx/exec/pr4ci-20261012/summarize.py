#!/usr/bin/env python3
"""Summary of campaign W of PR-4 (pr4ci-20261012): base (the deb of main at 72308ec90c, jhan-pr4ci-base) against target
(the PR-4 deb, jhan-pr4ci-target) per config, over passes and rounds, with memory; prints markdown to stdout and writes
summary.json next to the results. Forked 2026-10-12 from exec/pr4424ci-20261009/summarize.py (the default results
folder, the title strings, and the "Runs found" line's tron version key changed; the statistics are the same).

usage: summarize.py [--res DIR] [--nightly-log RUN.log] [--nightly-date YYYY-MM-DD] [--json OUT.json]
  DIR default: exec/results/pr4ci-20261012. Every DIR/<tag>/perf.json is read; the tag names the arm and the kind:
  <arm>-pass<k> = a full pass (FPGA attention; the cells of the configs file the campaign gave the driver, three in
  this fork's scope), <arm>-sw8k-pass<k> = the extra qwen3-4b prompt-8192 cell with software attention (not run in
  this fork's scope: the sw8k table then reads "sw8k cell: not run"). Repeated-run directories (<tag>-failed1) are ignored.

Statistics (the same as exec/canon-ci-20260918/gen_report.py, copied here, not imported):
  * a cell is (model, users, prompt_length); its per-pass data are the 10 rounds (the harness runs n_rounds=10, each
    round = one request per user); the round mean of TPS (per-user tokens per second, averaged over the users of the
    round) and of TTFT (ms) are the paired units;
  * pass pairing: base pass k is paired with target pass k (pass1 with pass1, pass2 with pass2); the paired-by-round
    differences of every pass pair are POOLED (n = 10 x number of complete pass pairs), and t = mean / (sd / sqrt(n));
  * "base TPS mean (sd over passes)" = mean over the arm's passes of the pass mean, with the sd of those pass means;
  * resolved = |t| >= 2.26 AND |delta| >= 1 % (for TTFT also |delta| >= 1 ms). 2.26 is the two-sided 5 % t for 9
    degrees of freedom (one pass pair); with two pass pairs (18 df) the 5 % point is 2.10, so 2.26 is conservative;
  * memory: per cell and arm the mean over passes of the sum over engines of VmHWM (peak resident set, MiB) and of
    VmRSS from the memsnap taken right after the benchmark (driver raw record mem_after_benchmark); delta = target - base.
  * fidelity (optional): with --nightly-log a nightly's own numbers (gh run view --log) are parsed by
    nightly_to_arm.py (copied from exec/ci-mimic-20260918) and printed against our base arm per cell.
"""
import argparse
import glob
import json
import math
import os
import re
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES_DEFAULT = "/home/jhan/workspace/intel-AMX/exec/results/pr4ci-20261012"
T_FLAG = 2.26
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201,
        12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042, 40: 2.021}


def t975(df):
    if df <= 0:
        return float("nan")
    if df in T975:
        return T975[df]
    for k in sorted(T975):
        if df < k:
            return T975[k]
    return 1.96


def paired(a, b):
    """paired difference b - a over rounds: mean, sd, t, n, ci95 (absolute units); None below 2 pairs."""
    n = min(len(a), len(b))
    if n < 2:
        return None
    d = [b[i] - a[i] for i in range(n)]
    m = statistics.mean(d)
    sd = statistics.stdev(d)
    se = sd / math.sqrt(n)
    t = (m / se) if se > 0 else (float("inf") if m != 0 else 0.0)
    return {"mean": m, "sd": sd, "t": t, "n": n, "ci": t975(n - 1) * se}


def cell_of(model, users, plen):
    return f"{model}@{users}u-p{plen}"


def rounds_of(raw):
    """Per-round lists of TPS and TTFT from a driver raw record (flat lists in round order; a round = n_users values)."""
    tps, ttft, n = raw.get("tpss") or [], raw.get("ttfts_ms") or [], int(raw.get("n_users") or 0)
    if n and tps and len(tps) % n == 0:
        rt = [tps[i:i + n] for i in range(0, len(tps), n)]
        rf = [ttft[i:i + n] for i in range(0, len(ttft), n)] if len(ttft) == len(tps) else []
        return rt, rf
    return ([tps] if tps else []), ([ttft] if ttft else [])


def mem_of(snap):
    """(sum VmHWM MiB, sum VmRSS MiB, sum HugetlbPages MiB, host MemAvailable MiB, n pids) of a memsnap, or None."""
    if not snap or snap.get("error") or snap.get("n_pids") in (None, 0):
        return None
    mi = snap.get("meminfo") or {}
    return {"hwm_mib": snap.get("sum_VmHWM_kB", 0) / 1024.0, "rss_mib": snap.get("sum_VmRSS_kB", 0) / 1024.0,
            "hugetlb_mib": snap.get("sum_HugetlbPages_kB", 0) / 1024.0, "mem_available_mib": mi.get("MemAvailable_kB", 0) / 1024.0,
            "n_pids": snap.get("n_pids"), "unreadable": len(snap.get("unreadable_pids") or [])}


def load_runs(res):
    """{(arm, kind, k): {cell: entry}} from every <arm>-pass<k>/perf.json and <arm>-sw8k-pass<k>/perf.json."""
    runs = {}
    for path in sorted(glob.glob(os.path.join(res, "*", "perf.json"))):
        tag = os.path.basename(os.path.dirname(path))
        m = re.match(r"^(base|target)-(sw8k-)?pass(\d+)$", tag)
        if not m:
            continue
        arm, kind, k = m.group(1), ("sw8k" if m.group(2) else "full"), int(m.group(3))
        try:
            rec = json.load(open(path))
        except Exception as exc:  # noqa: BLE001
            print(f"note: {path} not readable ({exc}); skipped", file=sys.stderr)
            continue
        cells = {}
        for raw in rec.get("raw") or []:
            try:
                cell = raw.get("cell") or cell_of(raw["model"], raw["n_users"], raw["prompt_length"])
            except KeyError:
                continue
            rt, rf = rounds_of(raw)
            cells[cell] = {"tag": tag, "model": raw.get("model"), "users": raw.get("n_users"), "prompt_length": raw.get("prompt_length"),
                           "round_tps": [statistics.mean(r) for r in rt if r], "round_ttft": [statistics.mean(r) for r in rf if r],
                           "tps_all": [x for r in rt for x in r], "ttft_all": [x for r in rf for x in r],
                           "mem_bench": mem_of(raw.get("mem_after_benchmark")), "mem_prov": mem_of(raw.get("mem_after_provision")),
                           "wall_s": raw.get("wall_seconds"), "anomalous": raw.get("anomalous_samples"), "amx_busy": raw.get("amx_busy_cycles"),
                           "hwattn_ok": raw.get("hwattn_ok"), "hwattn_unset_ok": raw.get("hwattn_unset_ok"), "binary_check_ok": raw.get("binary_check_ok"),
                           "engine_requests": raw.get("engine_requests"), "order": len(cells)}
        runs[(arm, kind, k)] = {"cells": cells, "rec": {"started": rec.get("started"), "finished": rec.get("finished"), "stop": rec.get("stop"),
                                                       "versions": (rec.get("versions") or {}).get("Tron (package)"), "perf_minutes": rec.get("perf_minutes"),
                                                       "installed_sha": rec.get("installed_sha_env")}}
    return runs


def fmt(x, nd=2):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:,.{nd}f}"


def signed(x, nd=1, unit=" %"):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+.{nd}f}{unit}"


def tstr(pr):
    if not pr:
        return "n/a"
    return "inf" if math.isinf(pr["t"]) else f"{pr['t']:+.2f}"


def summarize_kind(runs, kind):
    """Per cell: base/target pass means, pooled paired t, TTFT, memory. Returns (rows, cells order)."""
    ks = sorted({k for (a, kd, k) in runs if kd == kind})
    cells = []
    for key in sorted(runs, key=lambda x: (x[2], x[0])):
        if key[1] != kind:
            continue
        for cell, e in sorted(runs[key]["cells"].items(), key=lambda kv: kv[1]["order"]):
            if cell not in cells:
                cells.append(cell)
    rows = []
    for cell in cells:
        row = {"cell": cell, "kind": kind}
        per_arm = {}
        for arm in ("base", "target"):
            passes = {k: runs[(arm, kind, k)]["cells"].get(cell) for k in ks if (arm, kind, k) in runs}
            passes = {k: v for k, v in passes.items() if v and v["round_tps"]}
            pm = [statistics.mean(v["round_tps"]) for v in passes.values()]
            fm = [statistics.mean(v["round_ttft"]) for v in passes.values() if v["round_ttft"]]
            mem = [v["mem_bench"] for v in passes.values() if v["mem_bench"]]
            per_arm[arm] = {"passes": sorted(passes), "pass_tps": pm, "tps_mean": statistics.mean(pm) if pm else None,
                            "tps_sd_passes": statistics.stdev(pm) if len(pm) > 1 else (0.0 if pm else None),
                            "pass_ttft": fm, "ttft_mean": statistics.mean(fm) if fm else None,
                            "hwm_mib": statistics.mean([m["hwm_mib"] for m in mem]) if mem else None,
                            "rss_mib": statistics.mean([m["rss_mib"] for m in mem]) if mem else None,
                            "hugetlb_mib": statistics.mean([m["hugetlb_mib"] for m in mem]) if mem else None,
                            "mem_pids": sorted({m["n_pids"] for m in mem}) if mem else None,
                            "min_tps": min([min(v["tps_all"]) for v in passes.values()]) if passes else None,
                            "n_requests": sum(len(v["tps_all"]) for v in passes.values()),
                            "anomalous": sum((v["anomalous"] or 0) for v in passes.values()),
                            "amx_busy": [v["amx_busy"] for v in passes.values() if v["amx_busy"] is not None],
                            "checks_ok": all((v["binary_check_ok"] is not False) and (v["hwattn_ok"] is not False or kind == "full")
                                             and (v["hwattn_unset_ok"] is not False or kind == "sw8k") for v in passes.values()),
                            "_passes": passes}
        b, t = per_arm["base"], per_arm["target"]
        # pooled paired-by-round differences over the pass pairs (k present in both arms)
        pairs = sorted(set(b["passes"]) & set(t["passes"]))
        dtps_a, dtps_b, dttft_a, dttft_b = [], [], [], []
        for k in pairs:
            vb, vt = b["_passes"][k], t["_passes"][k]
            n = min(len(vb["round_tps"]), len(vt["round_tps"]))
            dtps_a += vb["round_tps"][:n]
            dtps_b += vt["round_tps"][:n]
            n2 = min(len(vb["round_ttft"]), len(vt["round_ttft"]))
            dttft_a += vb["round_ttft"][:n2]
            dttft_b += vt["round_ttft"][:n2]
        pr = paired(dtps_a, dtps_b)
        prf = paired(dttft_a, dttft_b)
        delta_pct = ((t["tps_mean"] - b["tps_mean"]) / b["tps_mean"] * 100.0) if (b["tps_mean"] and t["tps_mean"] is not None) else None
        ttft_delta_ms = (t["ttft_mean"] - b["ttft_mean"]) if (b["ttft_mean"] is not None and t["ttft_mean"] is not None) else None
        ttft_delta_pct = (ttft_delta_ms / b["ttft_mean"] * 100.0) if (ttft_delta_ms is not None and b["ttft_mean"]) else None
        resolved = (pr is not None and delta_pct is not None and abs(pr["t"]) >= T_FLAG and abs(delta_pct) >= 1.0)
        ttft_resolved = (prf is not None and ttft_delta_ms is not None and ttft_delta_pct is not None and abs(prf["t"]) >= T_FLAG
                         and abs(ttft_delta_pct) >= 1.0 and abs(ttft_delta_ms) >= 1.0)
        hwm_delta = (t["hwm_mib"] - b["hwm_mib"]) if (b["hwm_mib"] is not None and t["hwm_mib"] is not None) else None
        rss_delta = (t["rss_mib"] - b["rss_mib"]) if (b["rss_mib"] is not None and t["rss_mib"] is not None) else None
        row.update({"base": {k: v for k, v in b.items() if not k.startswith("_")}, "target": {k: v for k, v in t.items() if not k.startswith("_")},
                    "pass_pairs": pairs, "delta_pct": delta_pct, "paired_tps": pr, "resolved": resolved,
                    "ttft_delta_ms": ttft_delta_ms, "ttft_delta_pct": ttft_delta_pct, "paired_ttft": prf, "ttft_resolved": ttft_resolved,
                    "hwm_delta_mib": hwm_delta, "hwm_delta_pct": (hwm_delta / b["hwm_mib"] * 100.0) if (hwm_delta is not None and b["hwm_mib"]) else None,
                    "rss_delta_mib": rss_delta})
        rows.append(row)
    return rows


def table(rows, title):
    out = [f"### {title}", "",
           "| cell | base TPS mean (sd over passes) | target TPS | delta % | paired t (n rounds) | resolved | base TTFT ms | target TTFT ms | delta ms (%) | TTFT resolved | base VmHWM sum MiB | target VmHWM sum MiB | delta MiB (%) | base RSS sum MiB | target RSS sum MiB | delta MiB |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        b, t, pr, prf = r["base"], r["target"], r["paired_tps"], r["paired_ttft"]
        out.append("| " + " | ".join([
            r["cell"],
            f"{fmt(b['tps_mean'])} ({fmt(b['tps_sd_passes'])}) n={len(b['passes'])}",
            f"{fmt(t['tps_mean'])} ({fmt(t['tps_sd_passes'])}) n={len(t['passes'])}",
            signed(r["delta_pct"]),
            f"{tstr(pr)} ({pr['n']})" if pr else "n/a",
            "YES" if r["resolved"] else ("no" if pr else "n/t"),
            fmt(b["ttft_mean"], 0), fmt(t["ttft_mean"], 0),
            f"{signed(r['ttft_delta_ms'], 0, ' ms')} ({signed(r['ttft_delta_pct'])}) t={tstr(prf)}",
            "YES" if r["ttft_resolved"] else ("no" if prf else "n/t"),
            fmt(b["hwm_mib"], 0), fmt(t["hwm_mib"], 0),
            f"{signed(r['hwm_delta_mib'], 0, ' MiB')} ({signed(r['hwm_delta_pct'])})",
            fmt(b["rss_mib"], 0), fmt(t["rss_mib"], 0), signed(r["rss_delta_mib"], 0, " MiB"),
        ]) + " |")
    out.append("")
    return out


def nightly_fidelity(res, log_path, date, runs):
    """Our base arm against the nightly's own numbers per cell (nightly_to_arm.py on the run log)."""
    conv = os.path.join(HERE, "nightly_to_arm.py")
    if not os.path.exists(conv):
        conv = "/home/jhan/workspace/intel-AMX/exec/ci-mimic-20260918/nightly_to_arm.py"
    out_json = os.path.join(res, "nightly-arm.json")
    cmd = [sys.executable, conv, log_path, out_json, "--label", "nightly"] + (["--date", date] if date else [])
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return [f"### Fidelity against the nightly: nightly_to_arm.py failed", "", "```", p.stdout[-800:], p.stderr[-800:], "```", ""]
    night = json.load(open(out_json))
    by = {}
    for r in night.get("results") or []:
        c = r["context"]
        by[(c["model"], int(c["nominal_users"]))] = r
    out = [f"### Fidelity: our base arm (full passes) against the nightly's own perf numbers ({night.get('tron_version')})", "",
           "| cell | nightly TPS mean | our base TPS mean | delta % | nightly TTFT ms | our base TTFT ms |", "|---|---|---|---|---|---|"]
    rows = summarize_kind(runs, "full")
    for r in rows:
        m = re.match(r"^(.*)@(\d+)u-p(\d+)$", r["cell"])
        n = by.get((m.group(1), int(m.group(2)))) if m else None
        b = r["base"]
        if not n or b["tps_mean"] is None:
            out.append(f"| {r['cell']} | n/a | {fmt(b['tps_mean'])} | n/a | n/a | {fmt(b['ttft_mean'], 0)} |")
            continue
        d = (b["tps_mean"] - n["tps_mean"]) / n["tps_mean"] * 100.0 if n["tps_mean"] else None
        out.append(f"| {r['cell']} | {fmt(n['tps_mean'])} | {fmt(b['tps_mean'])} | {signed(d)} | {fmt(n['ttft_mean'], 0)} | {fmt(b['ttft_mean'], 0)} |")
    out.append("")
    out.append("The nightly's llama-8b 32u row shares the model name with the 8u row; nightly_to_arm.py keys by (model, users), so both resolve.")
    out.append("")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default=RES_DEFAULT)
    ap.add_argument("--nightly-log", default=None)
    ap.add_argument("--nightly-date", default=None)
    ap.add_argument("--json", default=None, help="summary.json path (default DIR/summary.json)")
    a = ap.parse_args()
    runs = load_runs(a.res)
    if not runs:
        print(f"no <arm>-pass<k>/perf.json or <arm>-sw8k-pass<k>/perf.json under {a.res}")
        return 1
    full = summarize_kind(runs, "full")
    sw8k = summarize_kind(runs, "sw8k")
    out = ["## pr4ci-20261012 summary: base (the deb of main at 72308ec90c, jhan-pr4ci-base) against target (the PR-4 deb, jhan-pr4ci-target)", ""]
    out.append("Runs found: " + ", ".join(f"{a_}-{'sw8k-' if kd == 'sw8k' else ''}pass{k} ({len(v['cells'])} cells, {v['rec'].get('perf_minutes')} min, tron {v['rec'].get('versions')})"
                                         for (a_, kd, k), v in sorted(runs.items(), key=lambda x: (x[0][2], x[0][1], x[0][0]))))
    out.append("")
    out.append(f"Resolution rule: resolved = |paired t| >= {T_FLAG} AND |delta| >= 1 % (TTFT also |delta| >= 1 ms). The paired t pools the "
               "paired-by-round differences (target - base, round means) of every complete pass pair (pass1 with pass1, pass2 with pass2; "
               "n = 10 rounds per pair). Memory = mean over passes of the sum over engine pids of VmHWM (peak resident set) and VmRSS "
               "read right after the benchmark (MiB; 1 GiB hugepages are NOT in these sums, they are in HugetlbPages). n/t = not testable (no complete pass pair).")
    out.append("")
    out += table(full, "Full passes (FPGA attention as shipped; the cells of the configs file given to the driver)")
    if sw8k:
        out += table(sw8k, "Extra cell: qwen3-4b tp2, 8 users, prompt 8192, software attention (USE_HW_ATTN=0)")
    else:
        out += ["### Extra cell: qwen3-4b tp2, 8 users, prompt 8192, software attention (USE_HW_ATTN=0)", "", "sw8k cell: not run", ""]
    stops = [(f"{a_}-{'sw8k-' if kd == 'sw8k' else ''}pass{k}", v["rec"]["stop"]) for (a_, kd, k), v in runs.items() if v["rec"].get("stop")]
    if stops:
        out.append("Driver stops: " + "; ".join(f"{t}: {s}" for t, s in stops))
        out.append("")
    checks_bad = [r["cell"] + "/" + arm for rows_ in (full, sw8k) for r in rows_ for arm in ("base", "target") if r[arm]["passes"] and not r[arm]["checks_ok"]]
    out.append("Per-provisioning checks (installed binary mapped by every engine, USE_HW_ATTN state): " + ("all ok" if not checks_bad else "FAILED for " + ", ".join(checks_bad)))
    out.append("")
    if a.nightly_log:
        out += nightly_fidelity(a.res, a.nightly_log, a.nightly_date, runs)
    print("\n".join(out))
    js = a.json or os.path.join(a.res, "summary.json")
    with open(js, "w") as f:
        json.dump({"res": a.res, "t_flag": T_FLAG, "rule": "resolved = |t| >= 2.26 and |delta| >= 1 % (TTFT also >= 1 ms); t pooled over pass pairs",
                   "runs": {f"{a_}-{kd}-pass{k}": v["rec"] for (a_, kd, k), v in runs.items()}, "full": full, "sw8k": sw8k}, f, indent=1, default=str)
    print(f"summary.json written: {js}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
