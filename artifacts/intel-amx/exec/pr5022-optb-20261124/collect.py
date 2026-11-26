#!/usr/bin/env python3
"""pr5022-optb-20261124: collect the results of the A/B test into summary.json and print a text table.

Words: tron = the inference program; runtron = its command-line tool. Arm a = the head of PR 5022 unchanged,
arm b = the same commit with the option B declaration of s_pages. A cell is one model with one setting.

Per throughput run (file rt/<cell>-8u-p1024__<arm>__rep<n>.log) it reads:
  - decode speed: the mean over the 8 users of runtron's "average tok/s" lines (tokens per second per user),
  - prefill time: the slowest user's "Parsing the prompt took" value in seconds,
  - the attention path counts of the exit report (TRON_ATTN_STATS=1): K tokens scored by AMX and by AVX.
The load line of each run comes from rt-results.txt (written by run-one.sh before the run starts).

Decision rule (the rule of exec/glimext-20261018/gen_report.py): the difference is the mean of the paired
differences b - a per repetition. The band is twice the larger standard deviation of the two arms.
"within the band" means |difference| <= band.

Usage: python3 collect.py [results folder]
"""
import json
import re
import statistics
import sys
from pathlib import Path

RES = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/pr5022-optb-20261124")
RUN_RE = re.compile(r"^(?P<cell>.+)-8u-p(?P<prompt>\d+)__(?P<arm>[ab])__rep(?P<rep>\d+)$")


def parse_run(path):
    tps, prefill, ttft, amx, avx = [], [], [], {}, {}
    version = None
    for line in path.read_text(errors="replace").splitlines():
        m = re.search(r"Generating (\d+) response tokens with (\d+) context took ([\d.]+) s at ([\d.]+) average tok/s", line)
        if m:
            tps.append(float(m.group(4)))
            continue
        m = re.search(r"Parsing the prompt took ([\d.eE+-]+) s at", line)
        if m:
            prefill.append(float(m.group(1)))
            continue
        m = re.search(r"saw ([\d.]+) s TTFT and ([\d.]+) s TTLT", line)
        if m:
            ttft.append(float(m.group(1)))
            continue
        m = re.search(r"Version: (\S+) hash: (\S+)", line)
        if m and version is None:
            version = m.group(1)
            continue
        m = re.match(r"\[attn-stats\] (\S+)/\S+ totals: (\{.*\})", line)
        if m:
            try:
                d = json.loads(m.group(2))
            except json.JSONDecodeError:
                continue
            amx[m.group(1)] = d.get("ready_amx_k_tokens", 0) + d.get("pending_amx_k_tokens", 0)
            avx[m.group(1)] = d.get("ready_avx_k_tokens", 0) + d.get("pending_avx_k_tokens", 0)
    if not tps:
        return None
    a, v = sum(amx.values()), sum(avx.values())
    return {
        "users": len(tps),
        "tps_user": statistics.fmean(tps),
        "prefill_s": max(prefill) if prefill else None,
        "ttft_s": max(ttft) if ttft else None,
        "amx_k_tokens": a,
        "avx_k_tokens": v,
        "amx_share_pct": (100.0 * a / (a + v)) if (a + v) else None,
        "version": version,
    }


def load_lines():
    out, run = {}, None
    f = RES / "rt-results.txt"
    if not f.exists():
        return out
    for line in f.read_text(errors="replace").splitlines():
        m = re.match(r"### run=(\S+) .* (\d{4}-\d\d-\d\dT[\d:]+Z)$", line)
        if m:
            run = m.group(1)
            out[run] = {"start": m.group(2)}
            continue
        if run and line.startswith("load: "):
            for k, v in re.findall(r"(\w+)=(\[[^\]]*\]|[\d. %]+?)(?= \w+=|$)", line[6:]):
                out[run][k] = v.strip()
    return out


def sd(xs):
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def main():
    loads = load_lines()
    runs = {}
    for p in sorted((RES / "rt").glob("*.log")):
        m = RUN_RE.match(p.stem)
        if not m:
            continue
        r = parse_run(p)
        if r is None:
            continue
        r.update(loads.get(p.stem, {}))
        runs.setdefault(m.group("cell"), {}).setdefault(m.group("arm"), {})[int(m.group("rep"))] = r
    cells = {}
    for cell, arms in runs.items():
        c = {"runs": arms, "metrics": {}}
        for metric in ("tps_user", "prefill_s"):
            a = {rep: r[metric] for rep, r in arms.get("a", {}).items() if r[metric] is not None}
            b = {rep: r[metric] for rep, r in arms.get("b", {}).items() if r[metric] is not None}
            reps = sorted(set(a) & set(b))
            if not reps:
                continue
            av, bv = [a[r] for r in reps], [b[r] for r in reps]
            deltas = [b[r] - a[r] for r in reps]
            band = 2 * max(sd(av), sd(bv))
            mean_a, mean_b, d = statistics.fmean(av), statistics.fmean(bv), statistics.fmean(deltas)
            c["metrics"][metric] = {
                "reps": reps, "a": av, "b": bv, "mean_a": mean_a, "mean_b": mean_b, "sd_a": sd(av), "sd_b": sd(bv),
                "deltas": deltas, "delta": d, "delta_pct": 100.0 * d / mean_a, "band": band,
                "verdict": "within the band" if abs(d) <= band else "outside the band",
            }
        cells[cell] = c
    out = {"cells": cells}
    for name in ("identity.txt", "tests.txt", "build-a.txt", "build-b.txt", "chain.done"):
        f = RES / name
        out[name] = f.read_text(errors="replace") if f.exists() else None
    (RES / "summary.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    for cell, c in cells.items():
        print(f"== {cell}")
        for arm in ("a", "b"):
            for rep, r in sorted(c["runs"].get(arm, {}).items()):
                pf = "n/a" if r["prefill_s"] is None else f"{r['prefill_s']:.3f}"
                sh = "n/a" if r["amx_share_pct"] is None else f"{r['amx_share_pct']:.1f}%"
                print(f"  arm {arm} rep {rep}: {r['tps_user']:.3f} tok/s per user, prefill {pf} s, AMX share {sh}, "
                      f"users {r['users']}, start {r.get('start')}, socket0 {r.get('socket0_busy')}, "
                      f"socket1 {r.get('socket1_busy')}, our cores {r.get('our_app_cores_busy')}")
        for metric, m in c["metrics"].items():
            print(f"  {metric}: a {m['mean_a']:.3f} (sd {m['sd_a']:.3f}), b {m['mean_b']:.3f} (sd {m['sd_b']:.3f}), "
                  f"b - a = {m['delta']:+.3f} ({m['delta_pct']:+.2f}%), band {m['band']:.3f}: {m['verdict']}")


main()
