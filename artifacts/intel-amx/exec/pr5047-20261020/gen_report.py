#!/usr/bin/env python3
"""pr5047-20261020 report: results.md (stdout) and results.json (in the results dir) from the campaign's files.

Reads: rt-results.txt (the perf cells; parsed with exec/glimmer-20261016/gen_compare.parse_results), rt/<run>.log (the
[attn-stats] exit reports; gen_compare.parse_stats), smoke/<key>/smoke.txt (token identity), tests.txt, build-*.txt,
hetero-*.txt.

Arms: base = PR 5047 base (PR 4956 head a5697f86d3) with TRON_K_VNNI OFF, head = PR 5047 head ade89a9d9c OFF, basev = base
ON, headv = head ON. Pairs: head vs base, headv vs basev (same option, commit differs = the PR's effect).
Perf decision rule: per cell the decode TPS per user (mean over the users' "average tok/s" lines of a run) and the prefill
time (the slowest user's "Parsing the prompt took") are averaged over the repetitions per arm. Paired delta = head - base
per repetition (the arms of one cell run back to back; the order alternates per repetition); band = twice the larger of
the two arms' sample standard deviations, never smaller than 0.4 TPS or 0.15 s. A cell "holds" (no degradation) when the
paired mean TPS delta is >= -band and the paired mean prefill delta is <= +band_prefill; it is a "gain" when the TPS delta
is > +band with the prefill delta inside its band; with fewer than 2 repetitions in an arm there is no band ("insufficient
reps"). The t statistic over the paired deltas is reported next to it.
Usage: gen_report.py RESULTS_DIR
"""
import glob
import json
import math
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "glimmer-20261016"))
from gen_compare import parse_results, parse_stats  # noqa: E402

RES = sys.argv[1]
ARMS = ["base", "head", "basev", "headv", "baseoff", "headoff"]
PAIRS = [("head", "base"), ("headv", "basev"), ("headoff", "baseoff")]
NAMES = {"base": "base (PR 4956 head a5697f86d3, option OFF)", "head": "head (PR 5047 ade89a9d9c, option OFF)",
         "basev": "basev (PR 4956 head, option ON)", "headv": "headv (PR 5047 head, option ON)",
         "baseoff": "baseoff (base, option OFF, kill switch TRON_AMX_DISABLE=1)", "headoff": "headoff (head, option OFF, kill switch)"}
MIN_BAND_TPS = 0.4
MIN_BAND_PREFILL = 0.15


def mean_sd(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None, 0
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0), len(xs)


def fnum(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


def pct(a, b):
    return None if a is None or not b else 100.0 * a / b


def runs_by_cell(runs):
    cells = {}
    for r in runs:
        if r["kind"] != "rt" or r["failed"] or r["stopped"] or not r["tps"]:
            continue
        r["early_stop"] = len(r["tps"]) != r["users"]
        r["tps_user"] = None if r["early_stop"] else statistics.mean(r["tps"])
        r["prefill_s"] = max(r["ttft"]) if r["ttft"] else None
        key = (r["cell"], r["attn"])
        cells.setdefault(key, {}).setdefault(r["arm"], {})
        if r["rep"] not in cells[key][r["arm"]]:
            cells[key][r["arm"]][r["rep"]] = r
    return cells


def amx_share(log):
    st = parse_stats(log)
    amx = avx = fpga = 0
    for cls in st["classes"].values():
        for (_ix, a, v, f) in (cls.get("layers") or []):
            amx += a; avx += v; fpga += f
    tot = amx + avx + fpga
    return {"amx_k": amx, "avx_k": avx, "fpga_k": fpga, "amx_pct": pct(amx, tot), "fpga_pct": pct(fpga, tot), "avx_pct": pct(avx, tot),
            "model": st["model"], "hw_line": st["hw_line"], "has_report": bool(st["classes"])}


def stat(d):
    if not d:
        return None
    m = statistics.mean(d); sd = statistics.stdev(d) if len(d) > 1 else 0.0
    t = (m / (sd / math.sqrt(len(d)))) if sd > 0 and len(d) > 1 else None
    return {"n": len(d), "mean": m, "sd": sd, "t": t, "deltas": d}


def perf_section(out, lines):
    path = os.path.join(RES, "rt-results.txt")
    if not os.path.exists(path):
        lines.append("No rt-results.txt: the perf campaign (step D) has not run."); return
    cells = runs_by_cell(parse_results(path))
    lines += ["| cell | attention | arm | reps | decode TPS per user (sd) | prefill s (sd) | K tokens by path (mean over reps) | early-stop runs |", "|---|---|---|---|---|---|---|---|"]
    verdict_rows = []
    for (cell, attn), arms in cells.items():
        row = {"cell": cell, "attn": attn, "arms": {}, "pairs": {}}
        for arm in ARMS:
            rs = arms.get(arm, {})
            tm, tsd, n = mean_sd([r["tps_user"] for r in rs.values()])
            pm, psd, _ = mean_sd([r["prefill_s"] for r in rs.values()])
            shares = [amx_share(os.path.join(RES, "rt", f"{cell}__{attn}__{arm}__rep{rep}.log")) for rep in sorted(rs)]
            amx_pcts = [s["amx_pct"] for s in shares if s["amx_pct"] is not None]
            fpga_pcts = [s["fpga_pct"] for s in shares if s["fpga_pct"] is not None]
            avx_pcts = [s["avx_pct"] for s in shares if s["avx_pct"] is not None]
            es = sum(1 for r in rs.values() if r["early_stop"])
            row["arms"][arm] = {"n": n, "tps_mean": tm, "tps_sd": tsd, "prefill_mean": pm, "prefill_sd": psd,
                                "amx_pct_mean": statistics.mean(amx_pcts) if amx_pcts else None, "fpga_pct_mean": statistics.mean(fpga_pcts) if fpga_pcts else None,
                                "avx_pct_mean": statistics.mean(avx_pcts) if avx_pcts else None,
                                "early_stop_runs": es, "reps": {rep: {"tps_user": r["tps_user"], "prefill_s": r["prefill_s"], "started": r["started"]} for rep, r in sorted(rs.items())},
                                "versions": sorted({r["version"] for r in rs.values() if r["version"]}), "hbm_lose": [r["hbm_lose"] for r in rs.values()]}
            if n:
                a = row["arms"][arm]
                lines.append(f"| {cell} | {attn} | {arm} | {n} | {fnum(tm)} ({fnum(tsd)}) | {fnum(pm, 3)} ({fnum(psd, 3)}) | AMX {fnum(a['amx_pct_mean'], 1)} %, AVX {fnum(a['avx_pct_mean'], 1)} %, FPGA {fnum(a['fpga_pct_mean'], 1)} % | {es} |")
        for (pa, pb) in PAIRS:
            a, b = row["arms"].get(pa), row["arms"].get(pb)
            if not (a and b and a["n"] and b["n"]):
                continue
            common = sorted(set(a["reps"]) & set(b["reps"]))
            dt = [a["reps"][k]["tps_user"] - b["reps"][k]["tps_user"] for k in common if a["reps"][k]["tps_user"] is not None and b["reps"][k]["tps_user"] is not None]
            dp = [a["reps"][k]["prefill_s"] - b["reps"][k]["prefill_s"] for k in common if a["reps"][k]["prefill_s"] is not None and b["reps"][k]["prefill_s"] is not None]
            st, sp = stat(dt), stat(dp)
            band_t = max(2 * max(a["tps_sd"] or 0, b["tps_sd"] or 0), MIN_BAND_TPS)
            band_p = max(2 * max(a["prefill_sd"] or 0, b["prefill_sd"] or 0), MIN_BAND_PREFILL)
            tps_ok = st is not None and st["mean"] >= -band_t
            pre_ok = sp is not None and sp["mean"] <= band_p
            if st is None:
                v = "no data"
            elif st["n"] < 2 or a["n"] < 2 or b["n"] < 2:
                v = "insufficient reps (n < 2, no band)"
            elif sp is None:
                v = "no prefill data"
            elif st["mean"] > band_t and pre_ok:
                v = "gain"
            elif tps_ok and pre_ok:
                v = "holds"
            else:
                v = "DEGRADATION beyond the band"
            row["pairs"][f"{pa}:{pb}"] = {"tps": st, "prefill": sp, "band_tps": band_t, "band_prefill": band_p, "tps_pct": pct(st["mean"] if st else None, b["tps_mean"]),
                                          "prefill_pct": pct(sp["mean"] if sp else None, b["prefill_mean"]), "verdict": v}
        if row["pairs"]:
            verdict_rows.append(row)
        out["perf"].append(row)
    lines += ["", "Paired deltas per cell (band = twice the larger arm sd, at least 0.4 TPS / 0.15 s; verdict per the decision rule in the header):", "",
              "| cell | attention | pair | TPS delta (mean over paired reps) | TPS delta % | TPS band | t | prefill delta s | prefill delta % | prefill band s | verdict |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in verdict_rows:
        for pk, p in row["pairs"].items():
            st, sp = p["tps"], p["prefill"]
            lines.append(f"| {row['cell']} | {row['attn']} | {pk} | {fnum(st['mean'] if st else None)} (n {st['n'] if st else 0}) | {fnum(p['tps_pct'], 1)} % | {fnum(p['band_tps'])} | {fnum(st['t'] if st else None, 1)} | {fnum(sp['mean'] if sp else None, 3)} | {fnum(p['prefill_pct'], 1)} % | {fnum(p['band_prefill'], 3)} | {p['verdict']} |")


def identity_section(out, lines):
    dirs = sorted(glob.glob(os.path.join(RES, "smoke", "*")))
    if not dirs:
        lines.append("No smoke/ results: the identity step (step I) has not run."); return
    lines += ["| cell | verdict | pair | result | role |", "|---|---|---|---|---|"]
    for d in dirs:
        key = os.path.basename(d)
        txt = open(os.path.join(d, "smoke.txt"), errors="replace").read() if os.path.exists(os.path.join(d, "smoke.txt")) else ""
        done = open(os.path.join(d, "smoke.done")).read().strip() if os.path.exists(os.path.join(d, "smoke.done")) else "missing"
        verdict_ix = [i for i, l in enumerate(txt.splitlines()) if l.startswith("SMOKE-VERDICT")]
        start = verdict_ix[-2] + 1 if len(verdict_ix) >= 2 else 0
        block = txt.splitlines()[start:]
        last = {}
        for line in block:
            m = re.match(r"^([a-z0-9]+) vs ([a-z0-9]+): (.*?)(?: \[(must match|informational)\])?$", line)
            if m:
                last[(m[1], m[2])] = {"a": m[1], "b": m[2], "result": m[3], "role": m[4] or "-"}
        fails = [l for l in block if l.startswith(("SMOKE-FAILED", "SMOKE-STOPPED")) or re.match(r"^[a-z0-9]+: (no token row|\d+ tokens, expected \d+)$", l) or re.match(r"^[a-z0-9]+ vs [a-z0-9]+: missing$", l)]
        out["identity"].append({"cell": key, "verdict": done, "pairs": list(last.values()), "failed_lines": fails})
        for p in last.values():
            lines.append(f"| {key} | {done} | {p['a']} vs {p['b']} | {p['result']} | {p['role']} |")
        if not last:
            lines.append(f"| {key} | {done} | - | no pair lines | - |")


def small_file(name, n=14):
    p = os.path.join(RES, name)
    if not os.path.exists(p):
        return [f"({name} missing)"]
    return [l.rstrip() for l in open(p, errors="replace").read().splitlines()[:n]]


def main():
    tags = ("b47b", "b47h", "b47bv", "b47hv")
    out = {"perf": [], "identity": [], "tests": small_file("tests.txt", 12), "builds": {t: small_file(f"build-{t}.txt", 14) for t in tags},
           "hetero": {t: small_file(f"hetero-{t}.txt", 6) for t in tags}}
    lines = ["# pr5047-20261020 results: PR 5047 (Ben's refactor of the PR 4956 K-layout code) with and without the change, on llama-3.1-8b, qwen3-4b and gpt-oss-120b", "",
             "Words used here: base = runtron built from PR 5047's base (= PR 4956 head a5697f86d3), head = runtron built from the PR 5047 head (ade89a9d9c); the option = the CMake option TRON_K_VNNI (OFF in every preset); basev / headv = the same commits with the option ON; all four built with the same recipe on delphi-3bda (plain shell, clang 19, preset native, BUILD_INGEST_MODELS=ON, TRON_AMX_DISPATCH=ON); K tokens by path = the exit report of TRON_ATTN_STATS=1 (K tokens scored by the AMX kernel / the AVX software path / the FPGA); attention cpu = USE_HW_ATTN=0, fpga = the model default.", "",
             "## 1. Builds and tests", ""]
    for t in tags:
        lines += [f"build {t}:"] + ["    " + l for l in out["builds"][t] if l.startswith(("tag", "tip", "compiler", "checks", "version", "t_heterogeneous"))]
    lines += ["", "tests (head builds):"] + ["    " + l for l in out["tests"]] + [""]
    lines += ["## 2. Token identity (1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens)", ""]
    identity_section(out, lines)
    lines += ["", "## 3. Throughput, head vs base (8 users, 256 generated tokens, --dont-stop)", ""]
    perf_section(out, lines)
    json.dump(out, open(os.path.join(RES, "results.json"), "w"), indent=1, default=str)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
