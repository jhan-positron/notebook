#!/usr/bin/env python3
"""Build the HTML report for the p0perf-20260913 campaign.

Inputs (all under RESULTS_DIR = exec/results/p0perf-20260913 unless noted):
  summary.json            written by summarize.py (runtron + CI-config cells, means, deltas, paired deltas,
                          the nightly's 2026-09-11 reference numbers)
  rt-results.txt          runtron result lines (placement header lines; per-request parse times)
  build.txt               tip, cmake line, sha256 of the two binaries, version line
  cells/*/meta.json       per CI cell: engines (key, port, placement, launcher cores, users), env, client cores
  platformd-instance-1.env.txt   the production unit file as pasted by jhan (placement and environment source)
  exec/logs/p0perf-20260913.log   campaign passes (start / finish lines), the idle-serving stop
Output: the HTML page given as the second argument (light theme, inline SVG, no libraries).
Usage: gen_report.py RESULTS_DIR OUT_HTML
Version 2 (2026-09-13): after the 132-agent verification of version 1 (two recomputations of 385 and 470
numbers matched; 59 wording, claim, record and figure findings applied).
"""
import datetime
import glob
import html
import json
import math
import os
import re
import statistics
import sys

RES, OUT = sys.argv[1], sys.argv[2]
EXEC = os.path.dirname(os.path.dirname(os.path.abspath(RES.rstrip('/'))))
LOG = os.path.join(EXEC, "logs", "p0perf-20260913.log")
S = json.load(open(os.path.join(RES, "summary.json")))
BUILD = open(os.path.join(RES, "build.txt")).read().splitlines() if os.path.exists(os.path.join(RES, "build.txt")) else []
RT_TXT = open(os.path.join(RES, "rt-results.txt"), errors="replace").read().splitlines() if os.path.exists(os.path.join(RES, "rt-results.txt")) else []
RT_HDR = [l for l in RT_TXT if l.startswith("#")]
LOGL = open(LOG, errors="replace").read().splitlines() if os.path.exists(LOG) else []
ENVFILE = os.path.join(RES, "platformd-instance-1.env.txt")
METAS = {}
for p in sorted(glob.glob(os.path.join(RES, "cells", "*__*__rep*", "meta.json"))):
    try:
        d = json.load(open(p)); METAS[(d.get("tp"), d.get("arm"))] = d
    except Exception:
        pass

# Colours: off = neutral gray, on = blue, fpga = orange (a colour-blind-safe trio); text in ink tokens.
C_OFF, C_ON, C_FPGA = "#6b6a66", "#2a78d6", "#d9822b"
INK, INK2, MUTED, GRID, AXIS, SURF, GOOD, BAD = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb", "#006300", "#d03b3b"
ARM_NAME = {"off": "AMX-off", "on": "AMX-on", "fpga": "FPGA attention"}
ARM_COL = {"off": C_OFF, "on": C_ON, "fpga": C_FPGA}
CI_ARMS = ["off", "on", "fpga"]
FID_BAND = 5.0   # percent; a threshold chosen while writing this generator (during the runtron phase, before the CI cells ran), not a measured noise figure
# Friday's cells (2026-09-11, head 47f6f2dceb, one engine, 8 users): PR3879/new-PRs/PR1/Friday-morning-CI-results.html
FRI = {"rt": {2: {"off": (71.07, 3934, 5), "on": (79.53, 3128, 6)}, 4: {"off": (95.15, 2458, 6), "on": (101.63, 2188, 6)}},
       "ci": {2: {"off": (48.81, 3052, 2), "on": (55.61, 2460, 2)}, 4: {"off": (72.76, 1738, 2), "on": (82.38, 1578, 2)}}}
# the 2026-09-08 one-engine users sweep: exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u{1,2,4,8}/perf.json
SWEEP = {1: 189.31, 2: 159.26, 4: 121.80, 8: 78.50}
# the nightly's per-user tp2 samples of 2026-09-11 (exec/results/p0perf-20260911/ci-run-34559196745.log, lines 2031-2130, 80 "Done (TTFT=.., X / 170.00 TPS)" lines)
NIGHTLY_TP2 = {"fast_n": 42, "fast_mean": 193.4, "slow_n": 38, "slow_mean": 176.6, "gap_pct": 9.5, "per_round": "4:4, 2:6, 6:2, 6:2, 4:4, 4:4, 4:4, 6:2, 4:4, 2:6"}
NIGHTLY_META = {"run": 34559196745, "package": "2026.09.11-632c6181", "client_host": "system-ci-runner", "log": "exec/results/p0perf-20260911/ci-run-34559196745.log",
                "tp2_lines": "2003-2130", "tp4_lines": "2162-2291", "workflow": 'System CI (Rinzler 72-core Intel system OCI version)'}


def esc(x):
    return html.escape(str(x), quote=True)


def f(x, nd=1, unit=""):
    return "n/a" if x is None else f"{x:.{nd}f}{unit}"


def pm(triple, nd=1, unit=""):
    if not triple or triple[0] is None:
        return "n/a"
    m, sd, n = triple
    return f"{m:.{nd}f}{unit} ± {sd:.{nd}f} (n={n})" if n > 1 else f"{m:.{nd}f}{unit} (n=1)"


def ms(tr):  # seconds triple [mean, sd, n] -> milliseconds triple
    return None if (not tr or tr[0] is None) else [tr[0] * 1000, tr[1] * 1000, tr[2]]


def signed(x, nd=1):
    return "n/a" if x is None else f"{x:+.{nd}f}%"


def pct(a, b):
    return None if (a is None or b in (None, 0)) else 100.0 * (a / b - 1)


def ratio(a, b):
    return None if (a is None or b in (None, 0)) else a / b


def nice_ticks(hi, n=6):
    if hi <= 0:
        return [0, 1]
    raw = hi / (n - 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    t, out = 0, []
    while t <= hi + 1e-9:
        out.append(round(t, 6)); t += step
    return out


def valid(rows):
    return [r for r in rows if not r.get("early_stop")]


def spread_pct(vals):
    vals = [v for v in vals if v is not None]
    return None if len(vals) < 2 or min(vals) <= 0 else 100.0 * (max(vals) / min(vals) - 1)


def resolve_threshold(tr_a, tr_b):
    """Percent of the baseline mean (a) that a difference of means must exceed to count as resolved:
    twice the combined standard error of the two cell means, 2*sqrt(sd_a^2/n_a + sd_b^2/n_b)."""
    if not tr_a or not tr_b or tr_a[0] in (None, 0) or tr_b[0] is None or tr_a[2] < 2 or tr_b[2] < 2:
        return None
    se = math.sqrt(tr_a[1] ** 2 / tr_a[2] + tr_b[1] ** 2 / tr_b[2])
    return 100.0 * 2 * se / tr_a[0]


def verdict(p, better, thr):
    """(word, colour). better = 'higher' | 'lower'. thr = resolution threshold in percent (None: unknown)."""
    if p is None:
        return ("n/a", MUTED)
    if thr is not None and abs(p) <= thr:
        return (f"not resolved (±{thr:.1f}%)", MUTED)
    good = (p > 0) if better == "higher" else (p < 0)
    return ("better" if good else "worse", GOOD if good else BAD)


# ---------- data views ----------
def rt_rows(tp, arm):
    return S["runtron"].get(f"tp{tp}", {}).get(arm, [])


def ci_rows(tp, arm, done_only=True):
    rows = S["ci"].get(f"tp{tp}", {}).get(arm, [])
    return [r for r in rows if r.get("status") == "done"] if done_only else rows


def rt_agg(tp, metric, arm):   # metric tps_per_user | ttft_s -> [mean, sd, n] or None
    return S["runtron"].get(f"tp{tp}", {}).get(metric, {}).get(arm)


def ci_agg(tp, metric, arm):   # metric tps_per_user | ttft_ms
    return S["ci"].get(f"tp{tp}", {}).get(metric, {}).get(arm)


def mean_of(tr):
    return None if (not tr or tr[0] is None) else tr[0]


def nightly(tp):
    return S.get("nightly_reference", {}).get(str(tp)) or S.get("nightly_reference", {}).get(tp) or {}


def rt_pct(tp, metric):
    d = S["runtron"].get(f"tp{tp}", {}).get(metric, {})
    return d.get("boost_pct") if metric == "tps_per_user" else d.get("change_pct")


def ci_pct(tp, metric, which):   # which = on_vs_off | on_vs_fpga | off_vs_fpga
    return S["ci"].get(f"tp{tp}", {}).get(metric, {}).get(f"{which}_pct")


def ci_paired(tp, metric, which):
    return S["ci"].get(f"tp{tp}", {}).get(metric, {}).get(f"paired_{which}", {}) or {}


def rt_paired(tp, metric):
    return S["runtron"].get(f"tp{tp}", {}).get(metric, {}).get("paired_pct", {}) or {}


def rng(pairs):   # "-20.4% to -20.8%" from a paired dict
    v = list(pairs.values())
    return "n/a" if not v else (f"{min(v):+.1f}% to {max(v):+.1f}%" if len(v) > 1 else f"{v[0]:+.1f}%")


# ---------- figure ----------
def dumbbell(rows, title, unit, nd, legend, mark_legend=None):
    """rows: [{label, sub, points: [{name, short, color, mean, sd, n, reps, hollow}], annot: [(text, colour)], marks: [(value, label)]}]
    Means are big dots (hollow ring = runtron in Figures 3 and 4); one strip of small dots per arm below the means;
    marks are hollow diamonds on the row line."""
    W, L, R, ROW, TOP, BOT = 980, 330, 210, 84, 92, 44
    H = TOP + ROW * len(rows) + BOT
    vals = [v for r in rows for p in r["points"] for v in ([p["mean"]] + p["reps"]) if v is not None] + [m[0] for r in rows for m in r.get("marks", []) if m[0] is not None]
    hi = max(vals) * 1.2 if vals else 1   # head-room for the label of the rightmost point
    ticks = nice_ticks(max(vals) * 1.05 if vals else 1)
    hi = max(hi, ticks[-1])
    def X(v): return L + (W - L - R) * v / hi
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;min-width:760px;display:block;background:{SURF}" role="img" aria-label="{esc(title)}">']
    o.append(f'<text x="{L}" y="22" font-size="15" font-weight="600" fill="{INK}">{esc(title)}</text>')
    for t in ticks:
        x = X(t)
        o.append(f'<line x1="{x:.1f}" y1="{TOP - 8}" x2="{x:.1f}" y2="{H - BOT + 6}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{x:.1f}" y="{H - BOT + 22}" font-size="11" fill="{MUTED}" text-anchor="middle" font-variant-numeric="tabular-nums">{t:g}</text>')
    o.append(f'<text x="{X(hi / 2):.1f}" y="{H - 8}" font-size="11" fill="{INK2}" text-anchor="middle">{esc(unit)}</text>')
    o.append(f'<line x1="{L}" y1="{TOP - 8}" x2="{L}" y2="{H - BOT + 6}" stroke="{AXIS}" stroke-width="1"/>')
    for i, r in enumerate(rows):
        y = TOP + ROW * i + ROW / 2 - 10
        o.append(f'<text x="{L - 14}" y="{y - 3}" font-size="13" font-weight="600" fill="{INK}" text-anchor="end">{esc(r["label"])}</text>')
        o.append(f'<text x="{L - 14}" y="{y + 13}" font-size="11" fill="{MUTED}" text-anchor="end">{esc(r["sub"])}</text>')
        pts = [p for p in r["points"] if p["mean"] is not None]
        if not pts:
            o.append(f'<text x="{L + 12}" y="{y + 4}" font-size="12" fill="{MUTED}">no data</text>')
            continue
        xs = [X(p["mean"]) for p in pts]
        if len(pts) > 1:
            o.append(f'<line x1="{min(xs):.1f}" y1="{y}" x2="{max(xs):.1f}" y2="{y}" stroke="{AXIS}" stroke-width="2" stroke-linecap="round"/>')
        for j, p in enumerate(pts):   # one strip of single repetitions per arm, so two arms' strips never mix
            cy = y + 14 + 6 * j
            for v in p["reps"]:
                o.append(f'<circle cx="{X(v):.1f}" cy="{cy:.1f}" r="3" fill="{p["color"]}" fill-opacity="0.65"><title>{esc(p["name"])}, one repetition: {v:.{nd}f} {esc(unit)}</title></circle>')
        for mv, ml in r.get("marks", []):
            if mv is None:
                continue
            mx = X(mv)
            o.append(f'<path d="M {mx:.1f} {y - 9} L {mx + 7:.1f} {y} L {mx:.1f} {y + 9} L {mx - 7:.1f} {y} Z" fill="{SURF}" stroke="{C_FPGA}" stroke-width="2"><title>{esc(ml)}: {mv:.{nd}f} {esc(unit)}</title></path>')
        for p, cx in zip(pts, xs):
            if p.get("hollow"):
                o.append(f'<circle cx="{cx:.1f}" cy="{y}" r="8" fill="{SURF}"/><circle cx="{cx:.1f}" cy="{y}" r="6" fill="{SURF}" stroke="{p["color"]}" stroke-width="2.5"><title>{esc(p["name"])}: mean {p["mean"]:.{nd}f} {esc(unit)}, sd {f(p["sd"], nd)}, n={p["n"]}</title></circle>')
            else:
                o.append(f'<circle cx="{cx:.1f}" cy="{y}" r="8" fill="{SURF}"/><circle cx="{cx:.1f}" cy="{y}" r="6" fill="{p["color"]}"><title>{esc(p["name"])}: mean {p["mean"]:.{nd}f} {esc(unit)}, sd {f(p["sd"], nd)}, n={p["n"]}</title></circle>')
        order = sorted(zip(xs, pts), key=lambda t: t[0])
        below = y + 14 + 6 * len(pts) + 12
        for k, (cx, p) in enumerate(order):
            if len(order) <= 2:
                yy, anchor, dx = ((y - 12), "middle", 0) if k == 0 else (below, "middle", 0)
            elif k == 0:
                yy, anchor, dx = (y - 12), "end", -2
            elif k == len(order) - 1:
                yy, anchor, dx = (y - 12), "start", 2
            else:
                yy, anchor, dx = below, "middle", 0
            o.append(f'<text x="{cx + dx:.1f}" y="{yy:.1f}" font-size="12" fill="{INK}" text-anchor="{anchor}" font-variant-numeric="tabular-nums">{esc(p["short"])} {p["mean"]:.{nd}f}</text>')
        for k, (text, col) in enumerate(r.get("annot", [])):
            o.append(f'<text x="{W - R + 12}" y="{y - 10 + 15 * k}" font-size="{13 if k == 0 else 10.5}" font-weight="{600 if k == 0 else 400}" fill="{col}" font-variant-numeric="tabular-nums">{esc(text)}</text>')
    lx, ly = L + 8, 46
    for name, col, kind in legend:
        width = 13 + 6.3 * len(name) + 24
        if lx + width > W - 8 and lx > L + 8:   # wrap the legend to a second line
            lx, ly = L + 8, ly + 16
        if kind == "hollow":
            o.append(f'<circle cx="{lx}" cy="{ly}" r="6" fill="{SURF}" stroke="{col}" stroke-width="2.5"/>')
        elif kind == "mark":
            o.append(f'<path d="M {lx} {ly - 7} L {lx + 6} {ly} L {lx} {ly + 7} L {lx - 6} {ly} Z" fill="{SURF}" stroke="{col}" stroke-width="2"/>')
        elif kind == "rep":
            o.append(f'<circle cx="{lx - 5}" cy="{ly}" r="3" fill="{C_OFF}" fill-opacity="0.65"/><circle cx="{lx + 1}" cy="{ly}" r="3" fill="{C_ON}" fill-opacity="0.65"/><circle cx="{lx + 7}" cy="{ly}" r="3" fill="{C_FPGA}" fill-opacity="0.65"/>')
        else:
            o.append(f'<circle cx="{lx}" cy="{ly}" r="6" fill="{col}"/>')
        o.append(f'<text x="{lx + 13}" y="{ly + 4}" font-size="11.5" fill="{INK2}">{esc(name)}</text>')
        lx += width
    o.append('</svg>')
    return "\n".join(o)


def point(name, short, color, tr, reps, hollow=False):
    tr = tr or [None, None, 0]
    return {"name": name, "short": short, "color": color, "mean": tr[0], "sd": tr[1], "n": tr[2], "reps": [v for v in reps if v is not None], "hollow": hollow}


LEG3 = [("AMX-off (kill switch)", C_OFF, "dot"), ("AMX-on", C_ON, "dot"), ("FPGA attention", C_FPGA, "dot"), ("single repetitions, arm colour", INK2, "rep")]
LEG3M = LEG3 + [("nightly 2026-09-11", C_FPGA, "mark")]
LEG2 = [("AMX-off (kill switch)", C_OFF, "dot"), ("AMX-on", C_ON, "dot"), ("single repetitions", INK2, "rep")]


def annot_change(label, p, better, thr):
    word, col = verdict(p, better, thr)
    return (f"{label} {signed(p)}" + (f" ({word})" if word.startswith("not") else ""), col)


def rows_tps_rt():
    rows = []
    for tp in (2, 4):
        a_off, a_on = rt_agg(tp, "tps_per_user", "off"), rt_agg(tp, "tps_per_user", "on")
        rows.append({"label": f"runtron · tp{tp}", "sub": "8 users, one process · 256-token limit",
                     "points": [point("AMX-off", "off", C_OFF, a_off, [r["tps_per_user"] for r in valid(rt_rows(tp, "off"))]),
                                point("AMX-on", "on", C_ON, a_on, [r["tps_per_user"] for r in valid(rt_rows(tp, "on"))])],
                     "annot": [annot_change("on vs off", rt_pct(tp, "tps_per_user"), "higher", resolve_threshold(a_off, a_on))]})
    return rows


def rows_tps_ci():
    rows = []
    for tp in (2, 4):
        a = {arm: ci_agg(tp, "tps_per_user", arm) for arm in CI_ARMS}
        rows.append({"label": f"CI harness · tp{tp}", "sub": ("2 engines × 2 users" if tp == 2 else "1 engine × 4 users") + " · 10 rounds",
                     "points": [point(ARM_NAME[arm], arm, ARM_COL[arm], a[arm], [r["tps_mean"] for r in ci_rows(tp, arm)]) for arm in CI_ARMS],
                     "marks": [(nightly(tp).get("tps"), "nightly 2026-09-11")],
                     "annot": [annot_change("on vs off", ci_pct(tp, "tps_per_user", "on_vs_off"), "higher", resolve_threshold(a["off"], a["on"])),
                               annot_change("on vs fpga", ci_pct(tp, "tps_per_user", "on_vs_fpga"), "higher", resolve_threshold(a["fpga"], a["on"])),
                               (f"nightly 2026-09-11: {f(nightly(tp).get('tps'), 1)}", MUTED)]})
    return rows


def rows_ttft_rt():
    rows = []
    for tp in (2, 4):
        a_off, a_on = ms(rt_agg(tp, "ttft_s", "off")), ms(rt_agg(tp, "ttft_s", "on"))
        rows.append({"label": f"runtron · tp{tp}", "sub": "batched prefill of 8 prompts",
                     "points": [point("AMX-off", "off", C_OFF, a_off, [r["ttft_s"] * 1000 for r in valid(rt_rows(tp, "off")) if r.get("ttft_s") is not None]),
                                point("AMX-on", "on", C_ON, a_on, [r["ttft_s"] * 1000 for r in valid(rt_rows(tp, "on")) if r.get("ttft_s") is not None])],
                     "annot": [annot_change("on vs off", rt_pct(tp, "ttft_s"), "lower", resolve_threshold(a_off, a_on))]})
    return rows


def rows_ttft_ci():
    rows = []
    for tp in (2, 4):
        t = {arm: ci_agg(tp, "ttft_ms", arm) for arm in CI_ARMS}
        rows.append({"label": f"CI harness · tp{tp}", "sub": "per request, users 0.1 s apart",
                     "points": [point(ARM_NAME[arm], arm, ARM_COL[arm], t[arm], [r["ttft_ms"] for r in ci_rows(tp, arm)]) for arm in CI_ARMS],
                     "annot": [annot_change("on vs off", ci_pct(tp, "ttft_ms", "on_vs_off"), "lower", resolve_threshold(t["off"], t["on"])),
                               annot_change("on vs fpga", ci_pct(tp, "ttft_ms", "on_vs_fpga"), "lower", resolve_threshold(t["fpga"], t["on"])),
                               (f"nightly 2026-09-11: {nightly(tp).get('ttft_ms', 'n/a')} ms", MUTED)]})
    return rows


def rows_predict(metric):
    """runtron (hollow ring) against the CI harness (filled dot), both in the arm's colour."""
    rows = []
    for tp in (2, 4):
        for arm in ("off", "on"):
            if metric == "tps":
                a_rt, a_ci = rt_agg(tp, "tps_per_user", arm), ci_agg(tp, "tps_per_user", arm)
                reps_rt = [r["tps_per_user"] for r in valid(rt_rows(tp, arm))]; reps_ci = [r["tps_mean"] for r in ci_rows(tp, arm)]
            else:
                a_rt, a_ci = ms(rt_agg(tp, "ttft_s", arm)), ci_agg(tp, "ttft_ms", arm)
                reps_rt = [r["ttft_s"] * 1000 for r in valid(rt_rows(tp, arm)) if r.get("ttft_s") is not None]; reps_ci = [r["ttft_ms"] for r in ci_rows(tp, arm)]
            rr = ratio(mean_of(a_ci), mean_of(a_rt))
            rows.append({"label": f"tp{tp} · {ARM_NAME[arm]}", "sub": "runtron (ring) and CI harness (dot)",
                         "points": [point("runtron", "runtron", ARM_COL[arm], a_rt, reps_rt, hollow=True), point("CI harness", "CI", ARM_COL[arm], a_ci, reps_ci)],
                         "annot": [(f"CI / runtron = {f(rr, 2)}×", INK)]})
    return rows


LEGP = [("runtron (ring, arm colour)", INK2, "hollow"), ("CI harness, nightly layout (dot)", INK2, "dot"), ("single repetitions", INK2, "rep")]

# ---------- facts computed from the raw files ----------
passes = []
for l in LOGL:
    m = re.match(r"=== p0perf-20260913 campaign started (\S+) pid \d+ TIP=\S+ RT_REPS=(\d+) CI_REPS=(\d+)", l)
    if m:
        passes.append({"start": m.group(1), "end": None, "status": "running", "rt": int(m.group(2)), "ci": int(m.group(3))})
    m = re.match(r"=== campaign finished (\S+): (.*) ===", l)
    if m and passes:
        passes[-1]["end"] = m.group(1); passes[-1]["status"] = m.group(2)
idle_stop = next((l[:20] for l in LOGL if "stopping idle rinzler serving" in l), None)


def hm(ts):
    return ts[11:19] + "Z" if ts and len(ts) >= 19 else (ts or "running")


if passes:
    p0 = passes[0]
    pass_txt = (f"One campaign pass on 2026-09-13, {hm(p0['start'])} to {hm(p0['end'])} UTC, finished {p0['status']}; {p0['rt']} runtron repetitions and {p0['ci']} CI-benchmark repetitions per cell."
                if len(passes) == 1 else "Campaign in %d passes on 2026-09-13 UTC: " % len(passes) + "; ".join(f"{hm(p['start'])} to {hm(p['end'])} ({p['status']})" for p in passes) + ".")
else:
    pass_txt = "Campaign log not found."

rt_runs, cur = [], None
for l in RT_TXT:
    m = re.match(r"### runtron tp=(\d) arm=(\w+) rep=(\d+) attempt=(\d+)", l)
    if m:
        cur = {"tp": int(m.group(1)), "arm": m.group(2), "rep": int(m.group(3)), "parse": [], "gen": 0}; rt_runs.append(cur); continue
    if cur is None:
        continue
    m = re.search(r"Parsing the prompt took ([\d.]+) s", l)
    if m: cur["parse"].append(float(m.group(1)))
    if "average tok/s" in l: cur["gen"] += 1
rt_runs = [r for r in rt_runs if r["gen"] > 0]
parse_spreads = [(max(r["parse"]) - min(r["parse"])) * 1000 for r in rt_runs if r["parse"]]
max_parse_spread = max(parse_spreads) if parse_spreads else None
worst = max(rt_runs, key=lambda r: (max(r["parse"]) - min(r["parse"])) if r["parse"] else 0) if rt_runs else None
ex_runs = [(tp, arm, r) for tp in (2, 4) for arm in ("off", "on") for r in rt_rows(tp, arm) if r.get("early_stop")]

eng_gap = []
for arm in CI_ARMS:
    for r in ci_rows(2, arm):
        pe = r.get("per_engine") or []
        if len(pe) == 2 and pe[0].get("tps_mean") and pe[1].get("tps_mean"):
            eng_gap.append((arm, r["rep"], pe[0]["tps_mean"], pe[1]["tps_mean"], 100.0 * (max(pe[0]["tps_mean"], pe[1]["tps_mean"]) / min(pe[0]["tps_mean"], pe[1]["tps_mean"]) - 1)))

ci_prompt = [r.get("prompt_tokens_mean") for tp in (2, 4) for arm in CI_ARMS for r in ci_rows(tp, arm) if r.get("prompt_tokens_mean")]
ci_cache = [r.get("cache_hit_pct") for tp in (2, 4) for arm in CI_ARMS for r in ci_rows(tp, arm) if r.get("cache_hit_pct") is not None]
ci_prompt_txt = (f"the server counted {statistics.mean(ci_prompt):.0f} prompt tokens per request on average, with a prefix-cache hit rate of {statistics.mean(ci_cache):.1f}%"
                 if ci_prompt else "the server's own prompt-token count was not recorded")


def build_field(prefix):
    return next((l for l in BUILD if l.startswith(prefix)), "")


tip = build_field("tip ").replace("tip ", "", 1) or "(build.txt missing)"
tip10 = tip.split(" ")[0][:10]
shas = [l for l in BUILD if re.match(r"^[0-9a-f]{64} ", l)]
version = next((l for l in BUILD if re.match(r"^\d{4}\.\d{2}\.\d{2}-", l)), "")
m = re.search(r"built (\S+) in (\d+) s", build_field("cmake"))
build_end, build_secs = (m.group(1), int(m.group(2))) if m else ("", 0)
place2 = next((l.split(":", 1)[1].strip() for l in RT_HDR if l.startswith("# placement tp2")), "(see rt-results.txt)")
place4 = next((l.split(":", 1)[1].strip() for l in RT_HDR if l.startswith("# placement tp4")), "(see rt-results.txt)")
envfile_lines = open(ENVFILE).read().splitlines() if os.path.exists(ENVFILE) else []
env_cli = next((l for l in envfile_lines if l.startswith("RZ_CLI_ARGS=")), "")
env_aff = next((l for l in envfile_lines if l.startswith("CPUAFFINITY=")), "")
place4_match = ("--instance 1,2" in env_cli) and all(tok in env_cli for tok in place4.split()) if env_cli else False

ctx_rows = []
for tp in (2, 4):
    for arm in ("off", "on"):
        for r in rt_rows(tp, arm):
            ctx_rows.append((f"runtron tp{tp} {arm} rep{r['rep']}" + (" (excluded, early stop)" if r.get("early_stop") else ""), r.get("machine", "")))
    for arm in CI_ARMS:
        for r in ci_rows(tp, arm, done_only=False):
            ctx_rows.append((f"CI tp{tp} {arm} rep{r['rep']} ({r.get('status')})", r.get("machine", "")))
n_ctx = len(ctx_rows)
n_b0 = sum(1 for _, l in ctx_rows if "bill_procs=0 bill_cpu_pct=0" in l)
n_hp = sum(1 for _, l in ctx_rows if "hugepages_free=512" in l)


def load1(line):
    m = re.search(r"load=([\d.]+)", line); return float(m.group(1)) if m else None


loads = [load1(l) for _, l in ctx_rows if load1(l) is not None]
first_load = load1(rt_rows(2, "off")[0].get("machine", "")) if rt_rows(2, "off") else None

# headline numbers
p_rt = {tp: rt_pct(tp, "tps_per_user") for tp in (2, 4)}
t_rt = {tp: rt_pct(tp, "ttft_s") for tp in (2, 4)}
p_ci = {tp: ci_pct(tp, "tps_per_user", "on_vs_off") for tp in (2, 4)}
t_ci = {tp: ci_pct(tp, "ttft_ms", "on_vs_off") for tp in (2, 4)}
p_sw = {tp: ci_pct(tp, "tps_per_user", "on_vs_fpga") for tp in (2, 4)}
t_sw = {tp: ci_pct(tp, "ttft_ms", "on_vs_fpga") for tp in (2, 4)}
fid = {tp: pct(mean_of(ci_agg(tp, "tps_per_user", "fpga")), nightly(tp).get("tps")) for tp in (2, 4)}
fid_t = {tp: pct(mean_of(ci_agg(tp, "ttft_ms", "fpga")), nightly(tp).get("ttft_ms")) for tp in (2, 4)}
fid_reps = {tp: [pct(r["tps_mean"], nightly(tp).get("tps")) for r in ci_rows(tp, "fpga")] for tp in (2, 4)}
rat = {(tp, arm): ratio(mean_of(ci_agg(tp, "tps_per_user", arm)), mean_of(rt_agg(tp, "tps_per_user", arm))) for tp in (2, 4) for arm in ("off", "on")}
rat_t = {(tp, arm): ratio(mean_of(ci_agg(tp, "ttft_ms", arm)), mean_of(ms(rt_agg(tp, "ttft_s", arm)))) for tp in (2, 4) for arm in ("off", "on")}
all_pairs = []
for tp in (2, 4):
    for v in rt_paired(tp, "tps_per_user").values(): all_pairs.append(v > 0)
    for v in rt_paired(tp, "ttft_s").values(): all_pairs.append(v < 0)
    for v in ci_paired(tp, "tps_per_user", "on_vs_off").values(): all_pairs.append(v > 0)
    for v in ci_paired(tp, "ttft_ms", "on_vs_off").values(): all_pairs.append(v < 0)
n_pairs, n_good = len(all_pairs), sum(1 for x in all_pairs if x)
tp2_onoff = list(ci_paired(2, "tps_per_user", "on_vs_off").values())
tp2_onoff_spread = (max(tp2_onoff) - min(tp2_onoff)) if len(tp2_onoff) > 1 else None
thr = {("ci", tp, "tps", w): resolve_threshold(ci_agg(tp, "tps_per_user", b), ci_agg(tp, "tps_per_user", "on")) for tp in (2, 4) for w, b in (("on_vs_off", "off"), ("on_vs_fpga", "fpga"))}
thr.update({("ci", tp, "ttft", w): resolve_threshold(ci_agg(tp, "ttft_ms", b), ci_agg(tp, "ttft_ms", "on")) for tp in (2, 4) for w, b in (("on_vs_off", "off"), ("on_vs_fpga", "fpga"))})
thr.update({("rt", tp, "tps"): resolve_threshold(rt_agg(tp, "tps_per_user", "off"), rt_agg(tp, "tps_per_user", "on")) for tp in (2, 4)})
thr.update({("rt", tp, "ttft"): resolve_threshold(rt_agg(tp, "ttft_s", "off"), rt_agg(tp, "ttft_s", "on")) for tp in (2, 4)})


def fid_sentences():
    ours = f"{f(mean_of(ci_agg(2, 'tps_per_user', 'fpga')), 1)} (tp2) and {f(mean_of(ci_agg(4, 'tps_per_user', 'fpga')), 1)} (tp4) tokens per second per user"
    theirs = f"the nightly's own {f(nightly(2).get('tps'), 1)} and {f(nightly(4).get('tps'), 1)} of 2026-09-11 ({signed(fid.get(2))} / {signed(fid.get(4))})"
    vals = {tp: fid[tp] for tp in (2, 4) if fid[tp] is not None}
    if not vals:
        return f"The FPGA-attention arm gives {ours}; there is no nightly value to compare with."
    ttft = (f"It does not reproduce the nightly's time to first token: {f(mean_of(ci_agg(2, 'ttft_ms', 'fpga')), 0)} and {f(mean_of(ci_agg(4, 'ttft_ms', 'fpga')), 0)} ms here against the nightly's "
            f"{nightly(2).get('ttft_ms', 'n/a')} and {nightly(4).get('ttft_ms', 'n/a')} ms ({signed(fid_t.get(2))} / {signed(fid_t.get(4))}), so the TTFT prediction above is less certain than the TPS prediction (see How to read).")
    if all(abs(v) <= FID_BAND for v in vals.values()):
        return (f"Our set-up (the same users per engine, placement and environment as the nightly) reproduces the nightly's decode rate: the FPGA-attention arm gives {ours} against {theirs}, "
                f"within the ±{FID_BAND:.0f}% threshold we chose for this check, so the TPS prediction above compares two arms of one binary in a set-up that behaves like the nightly's. {ttft}")
    off = ", ".join(f"tp{tp}" for tp, v in vals.items() if abs(v) > FID_BAND)
    return (f"Our set-up does NOT fully reproduce the nightly's decode rate: the FPGA-attention arm gives {ours} against {theirs}; the gap at {off} exceeds the ±{FID_BAND:.0f}% threshold we chose for this check, "
            f"and it adds to the uncertainty of the TPS prediction above (see How to read). {ttft}")


# ---------- HTML ----------
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
CSS = """
:root { color-scheme: light; }
body { background:#f9f9f7; color:#0b0b0b; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size:15px; line-height:1.5; margin:0; padding-block:24px 48px; padding-inline:16px; }
main { max-width: 980px; margin: 0 auto; }
h1 { font-size: 24px; margin: 0 0 4px; } h2 { font-size: 18px; margin: 32px 0 8px; } h3 { font-size: 15px; margin: 20px 0 6px; }
.sub { color:#52514e; font-size: 13.5px; margin-bottom: 18px; }
.short { background:#fcfcfb; border:1px solid #e1e0d9; border-radius:8px; padding:14px 18px; }
table { border-collapse: collapse; font-size: 13.5px; } .tw { overflow-x:auto; }
th, td { border-bottom: 1px solid #e1e0d9; padding: 5px 10px; text-align: left; vertical-align: top; } th { color:#52514e; font-weight:600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.fig { background:#fcfcfb; border:1px solid #e1e0d9; border-radius:8px; padding:10px 12px 6px; margin: 10px 0; overflow-x:auto; }
.take { font-size: 13.5px; color:#52514e; margin: 4px 0 0 4px; }
code { font-size: 12.5px; background:#f0efec; padding:1px 4px; border-radius:3px; }
dl { margin:0; } dt { font-weight:600; margin-top:6px; } dd { margin: 0; color:#52514e; }
ul.inner { margin: 4px 0 0 0; }
.warn { border-left: 4px solid #eda100; padding-left: 12px; }
"""
H = [f"<title>Sunday CI-layout results</title>\n<style>{CSS}</style>\n<main>"]
H.append('<h1>AMX performance check with the nightly CI\'s own engine and user layout (2026-09-13)</h1>')
H.append(f'<div class="sub">CI = continuous integration, the automated nightly test run of the tron inference program (GitHub Actions workflow "{esc(NIGHTLY_META["workflow"])}", called "System CI" below; its client runs on another host, its server is delphi-3bda, the shared test machine). '
         f'This page repeats Friday\'s (2026-09-11) tests: runtron and the CI benchmark, qwen-3-4b tp2 and tp4, prompt 1024, AMX-off against AMX-on. New today: the CI benchmark is laid out as the nightly runs it (the same number of users per server process, the CPU-core and card assignment of the production server processes, the same environment variables), plus a third setting with the nightly\'s current attention on the FPGA cards. '
         f'Branch jhan-amx-p0, commit {esc(tip10)}, our half of delphi-3bda. {esc(pass_txt)} Page generated {now}.</div>')

# ---- Short version ----
sv = (f"<p><b>Short version.</b> If the nightly CI (the automated test run every night against delphi-3bda) switched its qwen-3-4b engines (one engine = one server process serving the model) from attention on the FPGA cards to attention on the CPU with AMX (Intel's matrix instructions, the code under test here), "
      f"the per-user decode rate it reports would change by {signed(p_sw[2])} at tp2 (the model spread over 2 cards; the three repetitions gave {rng(ci_paired(2, 'tps_per_user', 'on_vs_fpga'))}) and {signed(p_sw[4])} at tp4 (4 cards; repetitions {rng(ci_paired(4, 'tps_per_user', 'on_vs_fpga'))}). "
      f"Its time to first token would change by {signed(t_sw[2])} (tp2) and {signed(t_sw[4])} (tp4). "
      f"Inside CPU attention, AMX gains {signed(p_ci[2])} / {signed(p_ci[4])} in decode rate over the existing AVX code in the CI benchmark (tp2 / tp4) and {signed(p_rt[2])} / {signed(p_rt[4])} in runtron (tron's command-line tool, 8 users on one process).</p>"
      f"<p><b>Basis of the prediction.</b> {fid_sentences()} The nightly reference is one run (GitHub Actions run {NIGHTLY_META['run']}); its night-to-night spread is Insufficient data (the CI results database would give it).</p>")
H.append(f'<div class="short">{sv}</div>')
if ex_runs:
    parts = [f"tp{tp} {arm} repetition {r['rep']}: shortest answer {r['gen_tokens_min']} tokens, longest {r['gen_tokens_max']}, {r['n_requests']} of 8 requests reported" for tp, arm, r in ex_runs]
    H.append(f"<p><b>Excluded run{'s' if len(ex_runs) > 1 else ''}.</b> {len(ex_runs)} runtron run{'s are' if len(ex_runs) > 1 else ' is'} excluded from the means and the per-repetition deltas: {esc('; '.join(parts))}. A stop token (the model's end-of-answer marker) ended one user's answer early, so part of that decode ran with fewer than 8 users.</p>")
missing = S.get("missing", [])
if missing:
    H.append(f'<p class="warn"><b>Incomplete:</b> no successful run for {esc(", ".join(missing))}. See the status and log files under exec/logs/.</p>')

# ---- Words used here ----
n_rt_txt = ", ".join(f"tp{tp} {arm} n={len(valid(rt_rows(tp, arm)))}" for tp in (2, 4) for arm in ("off", "on"))
n_ci_txt = ", ".join(f"tp{tp} {arm} n={len(ci_rows(tp, arm))}" for tp in (2, 4) for arm in CI_ARMS)
H.append(f"""<h2>Words used here</h2>
<dl>
<dt>tron, runtron, rinzler, engine</dt><dd>tron is the inference program under test (it serves large language models on this hardware). runtron is its command-line tool: one process loads the model, sends 8 synthetic prompts at once and generates a fixed number of tokens for each. rinzler is the production HTTP server built from the same source. One running rinzler process serving one model is an engine.</dd>
<dt>CI, the nightly, CI harness, nightly layout</dt><dd>CI = continuous integration, the automated build-and-test system. "The nightly" = the GitHub Actions workflow System CI that runs every night against delphi-3bda. One of its phases is a throughput benchmark (repository positron-ai/systems_test, file testlib/tps.py); that code, run by us, is the CI harness. The nightly sends its 8 benchmark users (n_users=8 in the job log of run {NIGHTLY_META['run']}) through platformd's Caddy reverse proxy (platformd = the production process manager; Caddy = the web server that forwards each request to one engine) to every engine of the model: 4 engines for a tp2 model, 2 for tp4 (log lines "All 4 inference engines are running" and "All 4 Caddy upstreams are healthy" before the tp2 test, "All 2 ..." before the tp4 test). How the proxy spread the 8 users is not logged. We take 2 users per tp2 engine and 4 per tp4 engine, the even spread: the 80 per-user tp2 values of that run fall into two speed groups ({NIGHTLY_TP2['fast_n']} values near {NIGHTLY_TP2['fast_mean']} and {NIGHTLY_TP2['slow_n']} near {NIGHTLY_TP2['slow_mean']} tokens per second), and the fast:slow count per round was {NIGHTLY_TP2['per_round']}, always even, which fits pairs of users sharing an engine; single rounds may still have put 3 users on one engine and 1 on another. "Nightly layout" here = that average load on our half of the machine: tp2 = 2 engines (cards 90/93 and b9/bc) with a 2-user client each, run at the same time; tp4 = 1 engine with a 4-user client.</dd>
<dt>AMX, AVX, kernel</dt><dd>AMX = Intel Advanced Matrix Extensions, CPU instructions that multiply small matrices in one step; the branch uses them for the attention step of the model. AVX = Intel Advanced Vector Extensions, the older CPU vector instructions the existing attention code uses. A kernel is one small compute routine.</dd>
<dt>arm: AMX-off, AMX-on, FPGA attention; kill switch</dt><dd>An arm is one setting of the two environment variables that choose the attention path, applied to the same binary; the page compares the three settings below with each other, and the FPGA-attention setting with the nightly. All arms run the binary built from the branch head with the AMX code compiled in (cmake option TRON_AMX_DISPATCH=ON). AMX-off = CPU attention (USE_HW_ATTN=0) with the AMX code turned off at run time by the environment variable TRON_AMX_DISABLE=1 (called the kill switch below), so attention takes the existing AVX path. AMX-on = CPU attention with the kill switch unset. FPGA attention = USE_HW_ATTN unset, the nightly's current setting for the ingested qwen model: attention runs on the FPGA cards from query position 127 on, positions 0 to 126 of every sequence stay on the CPU, and the kill switch is set so that CPU share runs on AVX as the nightly's main-branch package (which has no AMX code) runs it. runtron cells have the arms AMX-off and AMX-on only.</dd>
<dt>on vs off, on vs fpga, off vs fpga</dt><dd>on vs off = AMX-on mean divided by AMX-off mean, minus one: the gain of the AMX kernels inside the CPU-attention path. on vs fpga = AMX-on divided by FPGA attention, minus one: the change the nightly would report after its qwen engines are switched from FPGA attention to CPU attention with AMX. off vs fpga = AMX-off divided by FPGA attention, minus one: the existing AVX attention against FPGA attention, without any AMX. For TTFT all three are changes of the time, so negative is better.</dd>
<dt>fidelity check</dt><dd>The test that our set-up behaves like the nightly's: the FPGA-attention arm's decode rate (the same attention setting as the nightly) divided by the nightly's own decode rate of 2026-09-11. A gap of at most {FID_BAND:.0f}% counts as a pass; the {FID_BAND:.0f}% is a threshold chosen while writing this page (before the CI cells ran), not a measured noise figure. TTFT is compared but not part of the pass criterion (see How to read).</dd>
<dt>tp2, tp4, FPGA</dt><dd>tp = tensor parallelism, the number of FPGA cards one model instance spans (2 or 4). FPGA = field-programmable gate array, the accelerator cards of this machine (8 per machine). On our half tp2 engines use cards 90:00.0+93:00.0 and b9:00.0+bc:00.0; the tp4 engine uses all four, all attached to CPU socket 1.</dd>
<dt>delphi-3bda, our half, Bill, socket, hugepages</dt><dd>delphi-3bda is the shared test machine: 2 CPU sockets (72 cores each, 288 hardware threads in total) and 8 FPGA cards. Since 2026-09-06 it is split between two people: Bill (a colleague) uses socket 0 and cards 10/13/38/3b; we use socket 1 and cards 90/93/b9/bc ("our half"). Hugepages are 1 GiB memory pages reserved at boot for tron; the machine has 512, and "hugepages_free=512" in a machine line means none were in use when the run started.</dd>
<dt>ingested, prefill, decode, speculative decoding, FUSE</dt><dd>"Ingested" marks a model converted into tron's own format (the model name carries the prefix). Prefill = processing the prompt tokens before the first answer token; decode = generating the answer one token at a time. Speculative decoding = tron guessing several tokens ahead and then checking them; it is off in the nightly and here. FUSE = a file system served by a user program; rinzler mounts one per engine for its token files.</dd>
<dt>TPS (runtron)</dt><dd>tokens per second per user during decode, as runtron prints it per request, averaged over the 8 requests of one run (the 8 values agree within 0.01 because the 8 users run in one batch).</dd>
<dt>TTFT (runtron)</dt><dd>time to first token: the largest of the 8 "Parsing the prompt took S s" values of one run, that is the wait until the last of the 8 users has its first token (the 8 prompts are prefilled together). In all {len(rt_runs)} runs the 8 values agree within {f(max_parse_spread, 1)} ms{(' (largest spread ' + f(max_parse_spread, 2) + ' ms, tp' + str(worst['tp']) + ' ' + worst['arm'] + ' repetition ' + str(worst['rep']) + ')') if worst else ''}. Figures and tables use milliseconds.</dd>
<dt>TPS and TTFT (CI harness), capture window, pooled</dt><dd>Each harness client sends, per user, 10 rounds of a chat prompt cut to 1024 tokens from real conversations (the sharegpt set, a public set of chat transcripts; {esc(ci_prompt_txt)}) and reads 1536 generated tokens. TPS = tokens per second per user measured in the capture window, generated tokens 896 to 1024 of each answer, averaged over every user and round of the cell. For tp2 the 20 samples of each of the two engines are put into one list of 40 before averaging ("pooled"); the nightly pools its 8 users the same way. TTFT = milliseconds until the first piece of the streamed HTTP answer arrives, same averaging. The nightly's TTFT also contains the proxy hop and the network to its client host; ours does not.</dd>
<dt>cell, repetition, per repetition, n, sd</dt><dd>A cell is one combination of test, tp and arm. A repetition is one complete run of a cell. "Per repetition" columns pair the runs that carry the same repetition number (for example AMX-on repetition 1 divided by AMX-off repetition 1, minus one); the two runs of a pair started 45 to 72 s apart for runtron and 2.5 to 4 minutes apart for the CI harness. n = the number of repetitions that enter a cell's mean (runtron: {n_rt_txt}; CI harness: {n_ci_txt}). sd = the sample standard deviation over those repetitions (divides by n-1; roughly the typical distance of one repetition from the cell mean); with n=3 or 6 the sd itself is imprecise, so read it as an order of magnitude. In the Exact numbers table it is written after ±. In the Every run table, "sd over N samples" is the population standard deviation (divides by N, the numpy convention combine.py uses) of the N per-user per-round TPS samples inside that one run, and "slowest sample" is the smallest of them.</dd>
<dt>resolved, not resolved</dt><dd>A change between two cell means counts as resolved when it exceeds twice the combined standard error of the two means, 2 × sqrt(sd₁²/n₁ + sd₂²/n₂), expressed as a percent of the baseline mean. The figures print that threshold next to a change that does not exceed it and colour it gray; resolved changes are green (better) or red (worse).</dd>
<dt>placement, SYSTEM_CONFIG</dt><dd>Placement = the machine resources one tron process gets: --instance k,n = the k-th of n equal shares of the machine from tron's resource map; --devices = the FPGA cards; --app-cores = CPU cores for the application threads; --dev-cores = cores for the device driver threads; --numa = the memory node (socket); --nr_hugepages = the number of 1 GiB hugepages. SYSTEM_CONFIG is an environment variable the login shell exports with a default placement; tron applies it after the command line, so every run here removes it (env -u) and passes the placement explicitly.</dd>
</dl>""")

# ---- What was run ----
H.append("""<h2>What was run</h2>
<div class="tw"><table>
<tr><th>#</th><th>test</th><th>model</th><th>arm</th><th>engines × users</th><th>prompt</th><th>generated</th><th>repetitions</th></tr>""")
i = 0
for tp in (2, 4):
    for arm in ("off", "on"):
        i += 1
        runs = rt_rows(tp, arm); n_ex = len([r for r in runs if r.get("early_stop")])
        H.append(f"<tr><td>{i}</td><td>runtron</td><td>ingested-qwen-3-4b-instruct-2507-tp{tp}</td><td>{ARM_NAME[arm]}</td><td>1 process × 8 users</td><td>1024 synthetic tokens</td><td>256-token limit (253 generated)</td><td>{len(runs)} done{f', {n_ex} excluded (early stop)' if n_ex else ''}</td></tr>")
for tp in (2, 4):
    for arm in CI_ARMS:
        i += 1
        allr = ci_rows(tp, arm, done_only=False); n_done = len(ci_rows(tp, arm)); n_other = len(allr) - n_done
        cell = f"{n_done} done" + (f", {n_other} not done ({', '.join(r.get('status', '?') for r in allr if r.get('status') != 'done')})" if n_other else "")
        H.append(f"<tr><td>{i}</td><td>CI harness</td><td>ingested-qwen-3-4b-instruct-2507-tp{tp}</td><td>{ARM_NAME[arm]}</td><td>{'2 engines × 2 users' if tp == 2 else '1 engine × 4 users'}</td><td>1024 (harness setting)</td><td>1536 per round, 10 rounds</td><td>{cell}</td></tr>")
H.append("</table></div>")
H.append("<p class='take'>Inside each repetition the arms run in the same order (runtron: tp2 off, tp2 on, tp4 off, tp4 on; CI harness: off, on, fpga per tp), so a slow change of the machine over the campaign lands on every arm alike. The two tp2 engines of a CI cell are started together and their two clients run at the same time.</p>")

# ---- Results ----
colour_note = "Colours of the right column: green = better, red = worse, gray = not resolved (the change is within twice the combined standard error of the two means; that threshold is printed). The gray reference line gives the nightly's own value and is not a change."
H.append('<h2>Results</h2><h3>Figure 1: decode throughput per user (higher is better)</h3><div class="fig">')
H.append(dumbbell(rows_tps_rt() + rows_tps_ci(), "decode TPS per user, by arm", "tokens per second per user", 1, LEG3M))
fid_txt = " ".join(f"tp{tp}: our FPGA-attention arm {f(mean_of(ci_agg(tp, 'tps_per_user', 'fpga')), 1)} TPS per user against the nightly's {f(nightly(tp).get('tps'), 1)} ({signed(fid[tp])})." for tp in (2, 4) if nightly(tp))
H.append(f'<div class="take">Reading: big dots are arm means; the small dots below them are the single repetitions, one strip per arm in the arm\'s colour. The hollow diamond on the CI rows marks the nightly\'s own value of 2026-09-11 for the same model (GitHub Actions run {NIGHTLY_META["run"]}, tron package {NIGHTLY_META["package"]}, FPGA attention, 4 or 2 engines behind the proxy, client on host {NIGHTLY_META["client_host"]}; job log {NIGHTLY_META["log"]}, tp2 block lines {NIGHTLY_META["tp2_lines"]}, tp4 block lines {NIGHTLY_META["tp4_lines"]}). Fidelity check: {esc(fid_txt)} {colour_note}</div></div>')
H.append('<h3>Figure 2: time to first token (lower is better)</h3><div class="fig">')
H.append(dumbbell(rows_ttft_rt(), "time to first token, runtron (batched prefill of 8 prompts)", "milliseconds", 0, LEG2))
H.append(dumbbell(rows_ttft_ci(), "time to first token, CI harness (per request)", "milliseconds", 0, LEG3))
H.append(f'<div class="take">The two panels have their own axes. runtron TTFT is the batched prefill of 8 prompts of 1024 tokens (time until the last user has its first token); CI TTFT is each user\'s wait for the first streamed chunk. The nightly\'s TTFT (gray line) also contains its proxy hop and network path; compare arms within a row, and see How to read for the gap between our FPGA-attention arm and the nightly. {colour_note}</div></div>')
H.append('<h3>Figure 3: decode throughput, runtron against the CI harness for the same arm</h3><div class="fig">')
H.append(dumbbell(rows_predict("tps"), "decode TPS per user: runtron (ring) against the CI harness (dot)", "tokens per second per user", 1, LEGP))
rat_txt = "; ".join(f"tp{tp} {ARM_NAME[arm]}: CI / runtron = {f(rat[(tp, arm)], 2)}" for tp in (2, 4) for arm in ("off", "on"))
H.append(f'<div class="take">Both marks of a row share the arm\'s colour; the ring is runtron (8 users on one process), the dot the CI harness in the nightly layout (2 or 4 users per engine). Ratios: {esc(rat_txt)}. Hypothesis: after the switch to CPU attention with AMX, the nightly\'s qwen decode rate should be about these CI / runtron factors times runtron\'s 8-user rate at the same commit ({f(rat[(2, "on")], 2)} at tp2, {f(rat[(4, "on")], 2)} at tp4, the AMX-on rows), corrected by the fidelity gap ({signed(fid[2])} / {signed(fid[4])}); the first nightly that runs qwen with CPU attention and the AMX build settles it. Two things make the factor differ from 1: the CI harness puts 2 or 4 users on an engine where runtron puts 8 (the 2026-09-08 users sweep in Context shows fewer users per engine means a higher per-user rate), and the two tools time different things (Words used here). This page does not separate the two contributions.</div></div>')
H.append('<h3>Figure 4: time to first token, runtron against the CI harness for the same arm</h3><div class="fig">')
H.append(dumbbell(rows_predict("ttft"), "time to first token: runtron (ring) against the CI harness (dot)", "milliseconds", 0, LEGP))
rat_t_txt = "; ".join(f"tp{tp} {ARM_NAME[arm]}: {f(rat_t[(tp, arm)], 2)}" for tp in (2, 4) for arm in ("off", "on"))
H.append(f'<div class="take">Ratios CI / runtron: {esc(rat_t_txt)}. These TTFT ratios do not transfer to the nightly: they divide a per-request mean (CI) by the largest of 8 batched prefill times (runtron), two different waits, and our CI-harness TTFT is {signed(fid_t[2])} (tp2) and {signed(fid_t[4])} (tp4) away from the nightly\'s own TTFT (see How to read).</div></div>')

# ---- Exact numbers ----
def prs(p):
    return ", ".join(f"rep{k}: {v:+.1f}%" for k, v in (p or {}).items()) or "n/a"

H.append('<h3>Exact numbers</h3><p class="take">Means and sd are over the repetitions (sample standard deviation). TTFT in milliseconds. The "per repetition" columns pair the runs of the same repetition number (Words used here). A runtron run marked <b>early stop</b> is listed but excluded from the means.</p><div class="tw"><table><tr><th>test</th><th>metric</th><th class="num">AMX-off</th><th class="num">AMX-on</th><th class="num">FPGA attention</th><th class="num">on vs off</th><th>on vs off per repetition</th><th class="num">on vs fpga</th><th>on vs fpga per repetition</th><th class="num">off vs fpga</th></tr>')
for tp in (2, 4):
    a_off, a_on = rt_agg(tp, "tps_per_user", "off"), rt_agg(tp, "tps_per_user", "on")
    t_off, t_on = ms(rt_agg(tp, "ttft_s", "off")), ms(rt_agg(tp, "ttft_s", "on"))
    H.append(f"<tr><td>runtron tp{tp}</td><td>TPS per user</td><td class='num'>{pm(a_off, 2)}</td><td class='num'>{pm(a_on, 2)}</td><td class='num'>–</td><td class='num'>{signed(p_rt[tp])}</td><td>{esc(prs(rt_paired(tp, 'tps_per_user')))}</td><td class='num'>–</td><td>–</td><td class='num'>–</td></tr>")
    H.append(f"<tr><td>runtron tp{tp}</td><td>TTFT ms (batched prefill)</td><td class='num'>{pm(t_off, 0)}</td><td class='num'>{pm(t_on, 0)}</td><td class='num'>–</td><td class='num'>{signed(t_rt[tp])}</td><td>{esc(prs(rt_paired(tp, 'ttft_s')))}</td><td class='num'>–</td><td>–</td><td class='num'>–</td></tr>")
for tp in (2, 4):
    a = {arm: ci_agg(tp, "tps_per_user", arm) for arm in CI_ARMS}; t = {arm: ci_agg(tp, "ttft_ms", arm) for arm in CI_ARMS}
    H.append(f"<tr><td>CI harness tp{tp}</td><td>TPS per user</td><td class='num'>{pm(a['off'], 2)}</td><td class='num'>{pm(a['on'], 2)}</td><td class='num'>{pm(a['fpga'], 2)}</td><td class='num'>{signed(p_ci[tp])}</td><td>{esc(prs(ci_paired(tp, 'tps_per_user', 'on_vs_off')))}</td><td class='num'>{signed(p_sw[tp])}</td><td>{esc(prs(ci_paired(tp, 'tps_per_user', 'on_vs_fpga')))}</td><td class='num'>{signed(ci_pct(tp, 'tps_per_user', 'off_vs_fpga'))}</td></tr>")
    H.append(f"<tr><td>CI harness tp{tp}</td><td>TTFT ms</td><td class='num'>{pm(t['off'], 0)}</td><td class='num'>{pm(t['on'], 0)}</td><td class='num'>{pm(t['fpga'], 0)}</td><td class='num'>{signed(t_ci[tp])}</td><td>{esc(prs(ci_paired(tp, 'ttft_ms', 'on_vs_off')))}</td><td class='num'>{signed(t_sw[tp])}</td><td>{esc(prs(ci_paired(tp, 'ttft_ms', 'on_vs_fpga')))}</td><td class='num'>{signed(ci_pct(tp, 'ttft_ms', 'off_vs_fpga'))}</td></tr>")
H.append("</table></div>")
thr_txt = "; ".join(f"CI tp{tp} TPS on vs off ±{f(thr[('ci', tp, 'tps', 'on_vs_off')], 1)}%, on vs fpga ±{f(thr[('ci', tp, 'tps', 'on_vs_fpga')], 1)}%; TTFT on vs off ±{f(thr[('ci', tp, 'ttft', 'on_vs_off')], 1)}%, on vs fpga ±{f(thr[('ci', tp, 'ttft', 'on_vs_fpga')], 1)}%" for tp in (2, 4))
thr_rt = "; ".join(f"runtron tp{tp} TPS ±{f(thr[('rt', tp, 'tps')], 1)}%, TTFT ±{f(thr[('rt', tp, 'ttft')], 1)}%" for tp in (2, 4))
H.append(f"<p class='take'>Resolution thresholds (twice the combined standard error of the two means, as a percent of the baseline; a change inside the threshold is 'not resolved'): {esc(thr_rt)}; {esc(thr_txt)}.</p>")

# per-run table with per-engine values
H.append('<h3>Every run</h3><div class="tw"><table><tr><th>run</th><th class="num">TPS per user</th><th class="num">TTFT ms</th><th>per engine (users: TPS, TTFT ms)</th><th>notes (sd over the per-user per-round samples of the run, population sd; slowest = lowest single sample; minutes = client wall time)</th></tr>')
for tp in (2, 4):
    for arm in ("off", "on"):
        for r in rt_rows(tp, arm):
            note = ("EARLY STOP (%d-%d tokens), excluded" % (r["gen_tokens_min"], r["gen_tokens_max"])) if r.get("early_stop") else f"{r['n_requests']} requests, {r['gen_tokens_max']} tokens each"
            H.append(f"<tr><td>runtron tp{tp} {ARM_NAME[arm]} rep{r['rep']}</td><td class='num'>{r['tps_per_user']:.2f}</td><td class='num'>{f(r['ttft_s'] * 1000 if r.get('ttft_s') is not None else None, 0)}</td><td>–</td><td>{esc(note)}</td></tr>")
for tp in (2, 4):
    for arm in CI_ARMS:
        for r in ci_rows(tp, arm, done_only=False):
            if "tps_mean" not in r:
                H.append(f"<tr><td>CI tp{tp} {ARM_NAME[arm]} rep{r['rep']}</td><td class='num'>n/a</td><td class='num'>n/a</td><td>–</td><td>status {esc(r.get('status'))}</td></tr>"); continue
            pe = "; ".join(f"engine {k} ({e['n_users']} users): {e['tps_mean']:.2f}, {e['ttft_mean_ms']}" for k, e in enumerate(r.get("per_engine") or []))
            H.append(f"<tr><td>CI tp{tp} {ARM_NAME[arm]} rep{r['rep']}</td><td class='num'>{r['tps_mean']:.2f}</td><td class='num'>{r['ttft_ms']}</td><td>{esc(pe)}</td><td>sd over {r['n_samples']} samples ({r['n_users']} users × 10 rounds) {r['tps_sd']:.2f} TPS, slowest sample {r['min_tps']:.1f} TPS; client ran {r['minutes']:.1f} min; status {esc(r['status'])}</td></tr>")
H.append("</table></div>")
if eng_gap:
    g = max(eng_gap, key=lambda x: x[4])
    H.append(f"<p class='take'><b>The two tp2 engines.</b> Inside each tp2 CI cell the two engines (cards 90/93 and b9/bc, both on socket 1) serve 2 users each at the same time. Their per-user TPS differed by {min(x[4] for x in eng_gap):.1f}% to {max(x[4] for x in eng_gap):.1f}% (largest: {ARM_NAME[g[0]]} repetition {g[1]}, {g[2]:.1f} against {g[3]:.1f} TPS). "
             f"The nightly's per-user tp2 samples of 2026-09-11 (80 values, job log lines 2031-2130) fall into two groups: {NIGHTLY_TP2['slow_n']} values near {NIGHTLY_TP2['slow_mean']} and {NIGHTLY_TP2['fast_n']} values near {NIGHTLY_TP2['fast_mean']} TPS, {NIGHTLY_TP2['gap_pct']}% apart; our two socket-1 engines both sit at the faster level. "
             f"Hypothesis: the two groups are two engine speeds, and the slower engines are the nightly's socket-0 engines, which our half cannot reproduce; this would also account for part of the {signed(fid[2])} of the fidelity check. The measurement that would settle it: the nightly's per-user samples matched to the engine (port) that served each request, or a run of the same layout on socket 0.</p>")

# ---- Context ----
H.append(f"""<h2>Context</h2>
<h3>Friday's cells (2026-09-11, one engine, all 8 users on it) against today's nightly layout</h3>
<div class="tw"><table><tr><th>test</th><th>layout</th><th class="num">AMX-off TPS</th><th class="num">AMX-on TPS</th><th class="num">on vs off</th><th class="num">AMX-off TTFT ms</th><th class="num">AMX-on TTFT ms</th><th class="num">on vs off</th><th>n (off / on)</th></tr>""")
for tp in (2, 4):
    fr = FRI["ci"][tp]; fo, fn = fr["off"], fr["on"]
    H.append(f"<tr><td>CI harness tp{tp}, Friday (commit 47f6f2dceb)</td><td>1 engine × 8 users</td><td class='num'>{fo[0]:.2f}</td><td class='num'>{fn[0]:.2f}</td><td class='num'>{signed(pct(fn[0], fo[0]))}</td><td class='num'>{fo[1]}</td><td class='num'>{fn[1]}</td><td class='num'>{signed(pct(fn[1], fo[1]))}</td><td>{fo[2]} / {fn[2]}</td></tr>")
    ao, an = ci_agg(tp, "tps_per_user", "off"), ci_agg(tp, "tps_per_user", "on")
    H.append(f"<tr><td>CI harness tp{tp}, today (commit {esc(tip10)})</td><td>{'2 engines × 2 users' if tp == 2 else '1 engine × 4 users'}</td><td class='num'>{f(mean_of(ao), 2)}</td><td class='num'>{f(mean_of(an), 2)}</td><td class='num'>{signed(p_ci[tp])}</td><td class='num'>{f(mean_of(ci_agg(tp, 'ttft_ms', 'off')), 0)}</td><td class='num'>{f(mean_of(ci_agg(tp, 'ttft_ms', 'on')), 0)}</td><td class='num'>{signed(t_ci[tp])}</td><td>{ao[2] if ao else 0} / {an[2] if an else 0}</td></tr>")
for tp in (2, 4):
    fr = FRI["rt"][tp]; fo, fn = fr["off"], fr["on"]
    H.append(f"<tr><td>runtron tp{tp}, Friday</td><td>1 process × 8 users</td><td class='num'>{fo[0]:.2f}</td><td class='num'>{fn[0]:.2f}</td><td class='num'>{signed(pct(fn[0], fo[0]))}</td><td class='num'>{fo[1]}</td><td class='num'>{fn[1]}</td><td class='num'>{signed(pct(fn[1], fo[1]))}</td><td>{fo[2]} / {fn[2]}{' (one tp2 AMX-off run excluded, early stop)' if tp == 2 else ''}</td></tr>")
    ao, an = rt_agg(tp, "tps_per_user", "off"), rt_agg(tp, "tps_per_user", "on")
    H.append(f"<tr><td>runtron tp{tp}, today</td><td>1 process × 8 users</td><td class='num'>{f(mean_of(ao), 2)}</td><td class='num'>{f(mean_of(an), 2)}</td><td class='num'>{signed(p_rt[tp])}</td><td class='num'>{f(mean_of(ms(rt_agg(tp, 'ttft_s', 'off'))), 0)}</td><td class='num'>{f(mean_of(ms(rt_agg(tp, 'ttft_s', 'on'))), 0)}</td><td class='num'>{signed(t_rt[tp])}</td><td>{ao[2] if ao else 0} / {an[2] if an else 0}</td></tr>")
H.append("</table></div>")
on4 = mean_of(ci_agg(4, "tps_per_user", "on"))
H.append(f"<p class='take'>Friday's page: PR3879/new-PRs/PR1/Friday-morning-CI-results.html. The AMX gain measured by the CI harness is smaller in the nightly layout than on Friday: {signed(p_ci[2])} / {signed(p_ci[4])} today (2 or 4 users per engine, commit {esc(tip10)}) against {signed(pct(FRI['ci'][2]['on'][0], FRI['ci'][2]['off'][0]))} / {signed(pct(FRI['ci'][4]['on'][0], FRI['ci'][4]['off'][0]))} on Friday (8 users on one engine, commit 47f6f2dceb). Insufficient data to say why: the two campaigns differ in users per engine and in commit; a run of both user counts at one commit would separate them.</p>")
H.append(f"<p class='take'>The one-engine users sweep of 2026-09-08 (same harness, qwen tp4, CPU attention, AMX-on, the canonical build of commit 60d66d9c04, that is the AMX kernels without any extra copy of the attention cache; placement --instance 0,2 on socket 0, the other half of the machine; exec/results/g1-20260908) gave {SWEEP[1]:.1f} TPS per user at 1 user, {SWEEP[2]:.1f} at 2, {SWEEP[4]:.1f} at 4 and {SWEEP[8]:.1f} at 8. Fewer users per engine means a higher per-user rate, which is why the nightly layout's numbers sit far above Friday's 8-users-on-one-engine numbers. Today's socket-1 AMX-on cell at 4 users ({f(on4, 1)}) is {signed(pct(on4, SWEEP[4]))} from the sweep's 4-user value ({SWEEP[4]:.1f}), a different commit and socket.</p>")

# ---- How to read ----
sp_txt = "; ".join(f"CI tp{tp} {ARM_NAME[a]} {f(spread_pct([r['tps_mean'] for r in ci_rows(tp, a)]), 1, '%')}" for tp in (2, 4) for a in CI_ARMS)
sp_rt = "; ".join(f"runtron tp{tp} {ARM_NAME[a]} {f(spread_pct([r['tps_per_user'] for r in valid(rt_rows(tp, a))]), 1, '%')}" for tp in (2, 4) for a in ('off', 'on'))
fid4 = ", ".join(signed(v) for v in fid_reps[4]) if fid_reps[4] else "n/a"
fid2 = ", ".join(signed(v) for v in fid_reps[2]) if fid_reps[2] else "n/a"
load_txt = f"the 1-minute load average (the number of runnable threads; the machine has 288 hardware threads) fell from {f(first_load, 0)} at the first runtron run, 2.5 minutes after the {build_secs}-second build ended, to {f(min(loads), 0)} to {f(sorted(loads)[len(loads) // 2], 0)} for the later runs" if loads and first_load is not None else "the machine lines give the load at every start"
H.append(f"""<h2>How to read these numbers</h2>
<ul>
<li><b>Same binary, three environments.</b> Every arm runs the binary built from the branch head. The arms differ only in two environment variables (USE_HW_ATTN, TRON_AMX_DISABLE). The FPGA-attention arm is our substitute for the nightly's main-branch package. It matches the nightly in placement (tp4 copied from the production unit file, tp2 derived from it), users per engine, speculative decoding off (TRON_USE_SPECULATION=0 here; the nightly's job exports SYSTEM_CI_SPECULATION=0), FUSE settings and log level. Differences that remain (from the campaign design; none removable on our binaries):
<ul class="inner">
<li>the build: our branch commit {esc(tip10)} against the main-branch package {NIGHTLY_META['package']};</li>
<li>the proxy hop: our clients talk to each engine directly, the nightly's requests pass through Caddy;</li>
<li>the client host: ours runs on delphi-3bda itself, pinned to cores no engine uses (87-95 and 231-239), the nightly's on host {NIGHTLY_META['client_host']};</li>
<li>the arrival pattern: each of our clients starts its users 0.1 s apart (tp2: 0 and 0.1 s per engine; tp4: 0 to 0.3 s), the nightly starts 8 users over 0.7 s through one proxy;</li>
<li>the spread of users over engines: assumed even (2 or 4 per engine) from the nightly's per-user values, not read from the proxy;</li>
<li>the prompts: each client picks conversation number (round × users + user) from the sharegpt set, so both tp2 clients send the same 20 conversations (one copy to each engine) and the tp4 client 40, where the nightly's one 8-user client sends 80 different ones; all are cut to 1024 tokens and the decode length is fixed at 1536;</li>
<li>the two tp2 clients are not round-synchronized: the slower engine's last rounds run after the other engine has finished and sits idle; the nightly's one client starts every round for all 8 users together;</li>
<li>the second socket: the nightly's engines on socket 0 run at the same time as its socket-1 engines; our half has no socket-0 engines.</li>
</ul></li>
<li><b>What the fidelity check can and cannot show.</b> We count our set-up as reproducing the nightly when the FPGA-attention arm's mean decode rate is within ±{FID_BAND:.0f}% of the nightly's value of 2026-09-11; the threshold is a choice made while writing this page, not a measured noise figure, and the reference is one nightly run. Measured: tp2 repetitions {fid2}; tp4 repetitions {fid4} (the tp4 mean {signed(fid[4])} is inside the threshold, two of three repetitions are outside it). A pass means our set-up measures decode rate the way the nightly does, so on vs fpga predicts the nightly's change with one binary on both sides; the remaining gap adds to the error of the prediction. The nightly's TTFT is NOT reproduced: our FPGA-attention arm gives {f(mean_of(ci_agg(2, 'ttft_ms', 'fpga')), 0)} ms (tp2) and {f(mean_of(ci_agg(4, 'ttft_ms', 'fpga')), 0)} ms (tp4) against the nightly's {nightly(2).get('ttft_ms', 'n/a')} and {nightly(4).get('ttft_ms', 'n/a')} ms ({signed(fid_t[2])} / {signed(fid_t[4])}), although the nightly's value contains an extra proxy hop. Hypothesis: the nightly's 8 users arrive 0.1 s apart across 4 (or 2) engines, so the users that share one engine arrive about 0.4 s apart and are prefilled one after the other, while our 2 or 4 users of one engine arrive 0.1 s apart and are prefilled together, which lengthens the wait of every user; the measurement that would settle it is one CI-harness cell per engine with the stagger set to 0.4 s. Until then the TTFT prediction (on vs fpga) is less certain than the TPS prediction.</li>
<li><b>Run order.</b> Inside every repetition the arms run in the same order (runtron: off, on; CI harness: off, on, fpga), never reversed, and every run starts a fresh process. A drift that changes between repetitions (the machine speeding up or slowing down over the campaign) would show as per-repetition deltas that differ from one another (Exact numbers table). An effect of the position inside a repetition that repeats identically every time cannot be separated from the arm effect in these data; one repetition in reversed order would settle it (Insufficient data). Evidence against a large position effect: the tp2 CI on-vs-off deltas agree within {f(tp2_onoff_spread, 1)} points across the three repetitions spread over 40 minutes, while {load_txt}.</li>
<li><b>Spread and resolution.</b> Spread = the largest value of one arm's repetitions divided by the smallest, minus one. Decode TPS: {esc(sp_rt)}; {esc(sp_txt)}. The tp2 CI cells repeat within 0.6%; the tp4 cells and the runtron tp4 cells spread by 5 to 8%, so their changes carry the wider thresholds printed under the Exact numbers table. {n_good} of the {n_pairs} per-repetition on-vs-off comparisons (runtron and CI, TPS and TTFT) favour AMX-on.</li>
<li><b>The other half of the machine.</b> Bill's socket-0 work can run at the same time as our cells; the machine line at the start of every run (Provenance) shows his process count and CPU so that a disturbed cell can be identified. Memory and cards are per socket.</li>
</ul>""")

# ---- Provenance ----
H.append("<h2>Provenance</h2><dl>")
H.append(f"<dt>Source</dt><dd>branch jhan-amx-p0, commit {esc(tip)}</dd>")
H.append(f"<dt>Build</dt><dd>{esc(build_field('cmake'))}<br>{'<br>'.join(esc(s) for s in shas)}<br>{esc(version)}</dd>")
m2 = METAS.get((2, "on")) or METAS.get((2, "off")) or METAS.get((2, "fpga"))
m4 = METAS.get((4, "on")) or METAS.get((4, "off")) or METAS.get((4, "fpga"))
H.append(f"<dt>Placement tp2, runtron and CI engine 0 (key 2a, --instance 2,4, port 13100, launcher cores 73,217)</dt><dd><code>{esc(place2)}</code></dd>")
if m2:
    for e in m2.get("engines", []):
        if e.get("index") == 1:
            H.append(f"<dt>Placement tp2, CI engine 1 (key {esc(e.get('key'))}, port {e.get('port')}, launcher cores {esc(e.get('launcher_cores'))}, {e.get('users')} users)</dt><dd><code>{esc(e.get('placement'))}</code></dd>")
aff4 = (m4 or {}).get("engines", [{}])[0].get("launcher_cores", "73,217,74,218") if m4 else "73,217,74,218"
H.append(f"<dt>Placement tp4, runtron and CI engine (--instance 1,2, port 13100, launcher cores {esc(aff4)})</dt><dd><code>{esc(place4)}</code>. "
         + (f"This is the same string as the RZ_CLI_ARGS line (without the --model, --port and --hugepage_file words) of the production unit file /etc/rinzler/instance-1.env as read on delphi-3bda at 06:11 UTC on 2026-09-13 and pasted into the session; the paste is archived as exec/results/p0perf-20260913/platformd-instance-1.env.txt, and its CPUAFFINITY line ({esc(env_aff)}) is the launcher core set used here. Match checked by this generator: {'yes' if place4_match else 'NO'}." if env_cli else "The production unit file was not archived; the match rests on the rz.sh header note.") + "</dd>")
H.append("<dt>Derived placements</dt><dd>The two tp2 engine placements and their launcher cores are the two halves of the tp4 lists (cards 90/93 with cores 223-224,96-101,120-125,225-226,102-107,126-131, dev cores 75,76, launcher cores 73,217; cards b9/bc with the remaining cores, dev cores 77,78, launcher cores 74,218). The production unit files for a tp2 model were not read. Engine 0's placement is the same tp2 placement Friday's runs used (Friday's page, Provenance); tron logged 'Configured instance 2,4 using resource map' and 'Configured instance 3,4 using resource map' for the two engines (cells/*tp2*/proof.txt).</dd>")
env_txt = (f"<code>env -u SYSTEM_CONFIG</code> on every tron process. rinzler engines get the production environment (<code>TRON_USE_SPECULATION=0 RZ_FUSE_MOUNT_PRESCOPED=1 RZ_ENABLE_SAVE_TOKENS=1</code>, a FUSE mount path per port, launcher cores per engine via taskset) plus the arm: off = <code>USE_HW_ATTN=0 TRON_AMX_DISABLE=1</code>, on = <code>USE_HW_ATTN=0</code>, fpga = <code>TRON_AMX_DISABLE=1</code> with USE_HW_ATTN unset. "
           f"Log level: <code>TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug</code> (the login environment's values). The production tp4 unit file (archived paste, see above) sets neither variable, and tron's default when TRON_LOG_LEVEL is unset is debug (src/system/spdlog.cpp), so the production tp4 engine logs at the same level; the tp2 unit files were not read.")
H.append(f"<dt>Environment</dt><dd>{env_txt}</dd>")
H.append(f"<dt>Harness clients</dt><dd>systems_test 470aca1 testlib/tps.py through exec/more-testing-r1/st_perf.py --users 2 (tp2, one client per engine, both at the same time) or --users 4 (tp4), pinned with taskset to cores {esc((m2 or m4 or {}).get('client_cores', '87-95,231-239'))} (socket-1 cores no engine uses), each talking to its engine directly at http://delphi-3bda:1310x/v1; the CI results database is replaced by a stub that writes nothing. Per-engine results are pooled by exec/p0perf-20260913/combine.py. The nightly's job ran systems_test commit efb2d985; its testlib/tps.py is identical to 470aca1's.</dd>")
H.append("<dt>runtron command</dt><dd><code>runtron.p0perf13 stream-generate-text -m &lt;model&gt; &lt;placement&gt; --hugepage_file /dev/hugepages/amx-p0perf13 -o --prompt-length 1024 -l 256 -u 8</code></dd>")
H.append(f"<dt>Machine</dt><dd>delphi-3bda, our half (socket 1, cards 90/93/b9/bc). The production rinzler engines the nightly had left running were idle (no request lines in their journal, no non-idle statistics, no remote connections for 10 minutes) and were stopped at {esc(idle_stop or 'n/a')} UTC by the standing rule that stops idle production engines after 10 minutes without client requests; they were not restarted. Free 1 GiB hugepages afterwards: 512 of 512. Machine line at the start of every run: load average over 1, 5 and 15 minutes (the number of runnable threads; the machine has 288 hardware threads), free hugepages, Bill's process count and his summed CPU percent:</dd>")
H.append("</dl><div class='tw'><table><tr><th>run</th><th>machine line at start</th></tr>")
for name, line in ctx_rows:
    H.append(f"<tr><td>{esc(name)}</td><td><code>{esc(line)}</code></td></tr>")
H.append("</table></div>")
H.append(f"<p class='take'>bill_procs=0 and bill_cpu_pct=0 in {n_b0} of {n_ctx} lines; hugepages_free=512 in {n_hp} of {n_ctx} lines. The first runtron line (load {f(first_load, 0)}) follows the {build_secs}-second build on our cores that ended {build_end[11:19] if build_end else '?'} UTC.</p>")
H.append(f"""<h2>Raw data</h2>
<ul>
<li>exec/results/p0perf-20260913/rt-results.txt (runtron result lines per run), rt/*.log (full runtron output per run)</li>
<li>exec/results/p0perf-20260913/cells/&lt;model&gt;__&lt;arm&gt;__rep&lt;N&gt;/ (perf.json pooled, perf-e&lt;k&gt;.json and perf-e&lt;k&gt;.log per engine, rinzler-e&lt;k&gt;.log, meta.json, proof.txt, STATUS)</li>
<li>exec/results/p0perf-20260913/summary.json, summary.md (exec/p0perf-20260913/summarize.py); build.txt; platformd-instance-1.env.txt (the production unit file as pasted)</li>
<li>the nightly's reference numbers: exec/results/p0perf-20260911/ci-reference-20260911.json and its job log {NIGHTLY_META['log']} (run {NIGHTLY_META['run']})</li>
<li>campaign: exec/p0perf-20260913/campaign.sh, rz.sh, launch.sh, combine.py; log exec/logs/p0perf-20260913.log; this page: exec/p0perf-20260913/gen_report.py</li>
</ul>
</main>""")
open(OUT, "w").write("\n".join(H))
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
