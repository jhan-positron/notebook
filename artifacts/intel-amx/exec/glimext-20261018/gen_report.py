#!/usr/bin/env python3
"""glimext-20261018 report: results.md (stdout) and results.json (in the results dir) from the campaign's files.

Reads: rt-results.txt (the perf cells; parsed with exec/glimmer-20261016/gen_compare.parse_results), rt/<run>.log (the
[attn-stats] exit reports; gen_compare.parse_stats), smoke/<key>/smoke.txt (token identity), margin/margin.txt (the near-tie
probe), tests.txt, build-*.txt, preservation.txt.

Perf decision rule (the one PR #5015's body uses, with the repetitions of this campaign): per cell the decode TPS per user
(mean over the users' "average tok/s" lines of a run) and the prefill time (the slowest user's "Parsing the prompt took")
are averaged over the repetitions per arm. Paired delta = head - base per repetition (the arms of one cell run back to back;
the order alternates per repetition); band = twice the larger of the two arms' sample standard deviations. A cell "holds"
(no degradation) when the paired mean TPS delta is >= -band and the paired mean prefill delta is <= +band_prefill; it is a
"gain" when the TPS delta is > +band with the prefill delta inside its band; with fewer than 2 repetitions in an arm there is no band ("insufficient reps"). The t statistic over the paired deltas is reported next to it.
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
ARMS = ["base", "head"]
PAIR = ("head", "base")
NAMES = {"base": "base (main 6198824246, without PR #5015)", "head": "head (PR #5015 5061623a34)"}


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
        if r["rep"] not in cells[key][r["arm"]]:   # the first complete record of a repetition
            cells[key][r["arm"]][r["rep"]] = r
    return cells


def amx_share(log):
    """K tokens scored by AMX / AVX / FPGA over all classes of one run's exit report, and the busy ms per job (decode class)."""
    st = parse_stats(log)
    amx = avx = fpga = 0
    for cls in st["classes"].values():
        for (_ix, a, v, f) in (cls.get("layers") or []):
            amx += a; avx += v; fpga += f
    tot = amx + avx + fpga
    return {"amx_k": amx, "avx_k": avx, "fpga_k": fpga, "amx_pct": pct(amx, tot), "fpga_pct": pct(fpga, tot), "avx_pct": pct(avx, tot),
            "model": st["model"], "hw_line": st["hw_line"], "has_report": bool(st["classes"])}


def perf_section(out, lines):
    path = os.path.join(RES, "rt-results.txt")
    if not os.path.exists(path):
        lines.append("No rt-results.txt: the perf campaign (step D) has not run."); return
    cells = runs_by_cell(parse_results(path))
    lines += ["| cell | attention | arm | reps | decode TPS per user (sd) | prefill s (sd) | AMX share of K tokens (mean over reps) | early-stop runs |", "|---|---|---|---|---|---|---|---|"]
    verdict_rows = []
    for (cell, attn), arms in cells.items():
        row = {"cell": cell, "attn": attn, "arms": {}}
        for arm in ARMS:
            rs = arms.get(arm, {})
            tm, tsd, n = mean_sd([r["tps_user"] for r in rs.values()])
            pm, psd, _ = mean_sd([r["prefill_s"] for r in rs.values()])
            shares = [amx_share(os.path.join(RES, "rt", f"{cell}__{attn}__{arm}__rep{rep}.log")) for rep in sorted(rs)]
            amx_pcts = [s["amx_pct"] for s in shares if s["amx_pct"] is not None]
            fpga_pcts = [s["fpga_pct"] for s in shares if s["fpga_pct"] is not None]
            es = sum(1 for r in rs.values() if r["early_stop"])
            row["arms"][arm] = {"n": n, "tps_mean": tm, "tps_sd": tsd, "prefill_mean": pm, "prefill_sd": psd,
                                "amx_pct_mean": statistics.mean(amx_pcts) if amx_pcts else None, "fpga_pct_mean": statistics.mean(fpga_pcts) if fpga_pcts else None,
                                "early_stop_runs": es, "reps": {rep: {"tps_user": r["tps_user"], "prefill_s": r["prefill_s"], "started": r["started"]} for rep, r in sorted(rs.items())},
                                "versions": sorted({r["version"] for r in rs.values() if r["version"]}), "hbm_lose": [r["hbm_lose"] for r in rs.values()]}
            if n:
                lines.append(f"| {cell} | {attn} | {arm} | {n} | {fnum(tm)} ({fnum(tsd)}) | {fnum(pm, 3)} ({fnum(psd, 3)}) | AMX {fnum(row['arms'][arm]['amx_pct_mean'], 1)} %, FPGA {fnum(row['arms'][arm]['fpga_pct_mean'], 1)} % | {es} |")
        a, b = row["arms"].get(PAIR[0]), row["arms"].get(PAIR[1])
        if a and b and a["n"] and b["n"]:
            common = sorted(set(a["reps"]) & set(b["reps"]))
            dt = [a["reps"][k]["tps_user"] - b["reps"][k]["tps_user"] for k in common if a["reps"][k]["tps_user"] is not None and b["reps"][k]["tps_user"] is not None]
            dp = [a["reps"][k]["prefill_s"] - b["reps"][k]["prefill_s"] for k in common if a["reps"][k]["prefill_s"] is not None and b["reps"][k]["prefill_s"] is not None]
            def stat(d):
                if not d:
                    return None
                m = statistics.mean(d); sd = statistics.stdev(d) if len(d) > 1 else 0.0
                t = (m / (sd / math.sqrt(len(d)))) if sd > 0 and len(d) > 1 else None
                return {"n": len(d), "mean": m, "sd": sd, "t": t, "deltas": d}
            st, sp = stat(dt), stat(dp)
            band_t = 2 * max(a["tps_sd"] or 0, b["tps_sd"] or 0)
            band_p = 2 * max(a["prefill_sd"] or 0, b["prefill_sd"] or 0)
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
            row["pair"] = {"tps": st, "prefill": sp, "band_tps": band_t, "band_prefill": band_p, "tps_pct": pct(st["mean"] if st else None, b["tps_mean"]),
                           "prefill_pct": pct(sp["mean"] if sp else None, b["prefill_mean"]), "verdict": v}
            verdict_rows.append(row)
        out["perf"].append(row)
    lines += ["", f"Paired head minus base per cell ({PAIR[0]} vs {PAIR[1]}; band = twice the larger arm sd; verdict per the decision rule in the header):", "",
              "| cell | attention | TPS delta (mean over paired reps) | TPS delta % | TPS band | t | prefill delta s | prefill delta % | prefill band s | verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
    for row in verdict_rows:
        p = row["pair"]; st, sp = p["tps"], p["prefill"]
        lines.append(f"| {row['cell']} | {row['attn']} | {fnum(st['mean'] if st else None)} (n {st['n'] if st else 0}) | {fnum(p['tps_pct'], 1)} % | {fnum(p['band_tps'])} | {fnum(st['t'] if st else None, 1)} | {fnum(sp['mean'] if sp else None, 3)} | {fnum(p['prefill_pct'], 1)} % | {fnum(p['band_prefill'], 3)} | {p['verdict']} |")


def identity_section(out, lines):
    dirs = sorted(glob.glob(os.path.join(RES, "smoke", "*")))
    if not dirs:
        lines.append("No smoke/ results: the identity step (step I) has not run."); return
    lines += ["| cell | verdict | pair | result | role |", "|---|---|---|---|---|"]
    for d in dirs:
        key = os.path.basename(d)
        txt = open(os.path.join(d, "smoke.txt"), errors="replace").read() if os.path.exists(os.path.join(d, "smoke.txt")) else ""
        done = open(os.path.join(d, "smoke.done")).read().strip() if os.path.exists(os.path.join(d, "smoke.done")) else "missing"
        pairs = []
        for line in txt.splitlines():
            m = re.match(r"^([a-z0-9]+) vs ([a-z0-9]+): (.*?)(?: \[(must match|informational)\])?$", line)
            if m:
                pairs.append({"a": m[1], "b": m[2], "result": m[3], "role": m[4] or "-"})
        # the LAST block of pair lines (smoke.txt is appended to across reruns): keep the last occurrence per pair
        last = {}
        for p in pairs:
            last[(p["a"], p["b"])] = p
        # only the last block (after the second-to-last SMOKE-VERDICT line): smoke.txt is appended to across reruns
        verdict_ix = [i for i, l in enumerate(txt.splitlines()) if l.startswith("SMOKE-VERDICT")]
        start = verdict_ix[-2] + 1 if len(verdict_ix) >= 2 else 0
        block = txt.splitlines()[start:]
        fails = [l for l in block if l.startswith(("SMOKE-FAILED", "SMOKE-STOPPED")) or re.match(r"^[a-z0-9]+: (no token row|\d+ tokens, expected \d+)$", l) or re.match(r"^[a-z0-9]+ vs [a-z0-9]+: missing$", l)]
        out["identity"].append({"cell": key, "verdict": done, "pairs": list(last.values()), "failed_lines": fails})
        for p in last.values():
            lines.append(f"| {key} | {done} | {p['a']} vs {p['b']} | {p['result']} | {p['role']} |")
        if not last:
            lines.append(f"| {key} | {done} | - | no pair lines | - |")


def margin_section(out, lines):
    p = os.path.join(RES, "margin", "margin.txt")
    if not os.path.exists(p):
        lines.append("No margin/margin.txt: the near-tie probe (step E) did not run (skipped when head and base were identical, or not reached)."); return
    txt = open(p, errors="replace").read().splitlines()
    keep = [l for l in txt if l.startswith(("MARGIN", "MARKED", "run ", "baseF.tokens", "headF.tokens", "RUN-"))]
    out["margin"] = keep
    lines += ["```"] + keep[-8:] + ["```"]
    sj = os.path.join(RES, "margin", "steps-base-vs-head.json")
    if os.path.exists(sj):
        s = json.load(open(sj)).get("summary", {})
        m = s.get("marked_step") or {}
        out["margin_summary"] = {k: v for k, v in s.items() if k != "marked_step"}
        out["margin_marked"] = m
        if m:
            lines += ["", f"At the marked step the base arm's top-1 minus top-2 margin is {m['margin_off']:.5f} logit units ({m['margin_off_ulps']} bf16 ulps of the top-1 logit {m['off_top1_logit']:.4f}); the head arm moves that pair by {m['delta_pair']:.5f}. "
                          f"Over all steps: {len(s.get('flip_steps') or [])} flips (argmax differs, at steps {s.get('flip_steps')}), first flip at step {s.get('first_flip')}, median |pair delta| on non-flip steps {s.get('nonflip_median_abs_delta_pair')}, max TVD {s.get('max_tvd')}."]


def small_file(name, n=12):
    p = os.path.join(RES, name)
    if not os.path.exists(p):
        return [f"({name} missing)"]
    return [l.rstrip() for l in open(p, errors="replace").read().splitlines()[:n]]


def main():
    out = {"perf": [], "identity": [], "margin": None, "tests": small_file("tests.txt", 8), "builds": {t: small_file(f"build-{t}.txt", 12) for t in ("g16b", "g16h")},
           "preservation": [l for l in small_file("preservation.txt", 40) if re.match(r"^(pack_q|qk_row|weights_times)", l)]}
    lines = ["# glimext-20261018 results: PR #5015 (AMX attention kernels for kv_mul 16) with and without the change, on llama-3.1-8b, qwen3-4b, gpt-oss-120b and Muse Glimmer 30B", "",
             "Words used here: base = runtron built from the PR's merge base (main 6198824246), head = runtron built from the PR head (5061623a34), both with the same recipe on delphi-3bda (plain shell, clang 19, preset native, BUILD_INGEST_MODELS=ON, TRON_AMX_DISPATCH=ON); headoff = head with the kill switch TRON_AMX_DISABLE=1; AMX share = K (key) tokens scored by the AMX kernel over all K tokens of the run's exit report (TRON_ATTN_STATS=1); attention cpu = USE_HW_ATTN=0, fpga = the model default.", "",
             "## 1. Builds and tests", ""]
    for t in ("g16b", "g16h"):
        lines += [f"build {t}:"] + ["    " + l for l in out["builds"][t] if l.startswith(("tip", "compiler", "checks", "version"))]
    lines += ["", "tests (head build):"] + ["    " + l for l in out["tests"]] + ["", "preservation (base plain kernels vs head <4> instantiations, same compiler):"] + ["    " + l for l in out["preservation"]] + [""]
    lines += ["## 2. Token identity (1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens)", ""]
    identity_section(out, lines)
    lines += ["", "## 3. Throughput, base vs head (8 users, 256 generated tokens, --dont-stop)", ""]
    perf_section(out, lines)
    lines += ["", "## 4. Near-tie margin at the first Glimmer divergence (teacher-forced logits, CPU attention)", ""]
    margin_section(out, lines)
    json.dump(out, open(os.path.join(RES, "results.json"), "w"), indent=1, default=str)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
