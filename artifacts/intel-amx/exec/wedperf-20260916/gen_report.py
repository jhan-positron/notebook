#!/usr/bin/env python3
"""Generate VNNIed-K-in-place/status/Wednesday-perf-test.html: the nightly CI's perf models, base
(main just before PR #3879) vs target (PR #4424 head), from exec/results/wedperf-20260916/
(summary.json by summarize.py, smoke/compare.txt, build-*.txt, rt-results.txt), the campaign log,
the per-model code-path facts (exec/wedperf-20260916/model-facts.json, written from the review
workflow) and the nightly's own reference numbers (exec/results/more-testing-r1/
ci-reference-20260904.json, orientation only). Pure-ASCII HTML, light theme only, inline SVG
(delta bars per cell; dumbbell small multiples per cell with the repetitions as faint dots).
Every block degrades to a "pending" note when its input is missing, so the page can be generated
while the campaign still runs. Usage: gen_report.py [OUT_HTML]
"""
import datetime
import html
import json
import math
import os
import re
import sys

EXEC = "/home/jhan/workspace/intel-AMX/exec"
C = f"{EXEC}/wedperf-20260916"
RES = os.environ.get("WEDPERF_RES", f"{EXEC}/results/wedperf-20260916")
LOG = os.environ.get("WEDPERF_LOG", f"{EXEC}/logs/wedperf-20260916.log")
FACTS = os.environ.get("WEDPERF_FACTS", f"{C}/model-facts.json")
RES_C = os.environ.get("WEDPERF_RES_C", f"{EXEC}/results/wedperf-gen1536-20260916")   # block C: 1536 generated tokens
RES_D = os.environ.get("WEDPERF_RES_D", f"{EXEC}/results/wedperf-attr-20260916")      # block D: base / mid / target attribution
RES_E = os.environ.get("WEDPERF_RES_E", f"{EXEC}/results/wedperf-attr2-20260916")     # block E: base / p3879 / mid / target on gpt-oss
CIREF = f"{EXEC}/results/more-testing-r1/ci-reference-20260904.json"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/Wednesday-perf-test.html"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

ARMS = ["base", "target"]
ARM_LABEL = {"base": "base (main eb2de0265a, before PR #3879, no AMX code)", "p3879": "p3879 (3fd5edaa66, the PR #3879 merge commit, AMX dispatch, no VNNI)", "mid": "mid (main c7844ca2ce, after PR #3879 and PR #4400, AMX dispatch, no VNNI)", "target": "target (PR #4424 head ff680c8020, AMX dispatch + VNNI K layout)"}
# dataviz reference palette, light mode: the control is neutral gray, the PR binary is slot 1 blue;
# the delta bars use the diverging pair blue (improvement) / red (regression) with a legend
ARM_COLOR = {"base": "#8a8987", "p3879": "#1baf7a", "mid": "#eb6834", "target": "#2a78d6"}
C_GAIN, C_LOSS, C_FLAT = "#2a78d6", "#e34948", "#c3c2b7"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
# cell order = the order of scripts/perf.py configs
CELL_ORDER = ["l3b-tp2-32u", "l8b-tp2-8u", "l70b-tp2-8u", "l70b-tp2-4u", "l70b-tp4-4u", "mixtral-tp2-8u", "q25-32b-tp2-8u",
              "q3-4b-tp2-8u", "q3-4b-tp4-8u", "g2-9b-tp2-8u", "gptoss-tp4-8u", "g4-31b-tp2-8u"]
CELL_MODEL = {"l3b-tp2-32u": ("llama-3.2-3b-instruct-fast-tp2", 2, 32), "l8b-tp2-8u": ("llama-3.1-8b-instruct-good-tp2", 2, 8),
              "l70b-tp2-8u": ("llama-3.3-70b-instruct-good-tp2", 2, 8), "l70b-tp2-4u": ("llama-3.3-70b-instruct-good-tp2", 2, 4),
              "l70b-tp4-4u": ("llama-3.3-70b-instruct-good-tp4", 4, 4), "mixtral-tp2-8u": ("mixtral-8x7b-instruct-v0.1-tp2", 2, 8),
              "q25-32b-tp2-8u": ("qwen-2.5-32b-it-fast-tp2", 2, 8), "q3-4b-tp2-8u": ("ingested-qwen-3-4b-instruct-2507-tp2", 2, 8),
              "q3-4b-tp4-8u": ("ingested-qwen-3-4b-instruct-2507-tp4", 4, 8), "g2-9b-tp2-8u": ("gemma-2-9b-it-fast-tp2", 2, 8),
              "gptoss-tp4-8u": ("ingested-gpt-oss-120b-tp4", 4, 8), "g4-31b-tp2-8u": ("ingested-gemma-4-31b-it-tp2", 2, 8)}
CELL_NICE = {"l3b-tp2-32u": "llama-3.2-3b fast, tp2, 32 users", "l8b-tp2-8u": "llama-3.1-8b good, tp2, 8 users",
             "l70b-tp2-8u": "llama-3.3-70b good, tp2, 8 users", "l70b-tp2-4u": "llama-3.3-70b good, tp2, 4 users",
             "l70b-tp4-4u": "llama-3.3-70b good, tp4, 4 users", "mixtral-tp2-8u": "mixtral-8x7b, tp2, 8 users",
             "q25-32b-tp2-8u": "qwen-2.5-32b fast, tp2, 8 users", "q3-4b-tp2-8u": "qwen-3-4b (ingested), tp2, 8 users",
             "q3-4b-tp4-8u": "qwen-3-4b (ingested), tp4, 8 users", "g2-9b-tp2-8u": "gemma-2-9b fast, tp2, 8 users",
             "gptoss-tp4-8u": "gpt-oss-120b (ingested), tp4, 8 users", "g4-31b-tp2-8u": "gemma-4-31b (ingested), tp2, 8 users"}
T_RESOLVED = 2.0
PCT_FLOOR = 1.0   # percent; a resolved change must also be at least this large


def esc(s):
    return html.escape(str(s), quote=True)


def jload(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def read(path):
    try:
        with open(path, errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def fmt(x, nd=1):
    if x is None:
        return "-"
    return f"{x:.{nd}f}"


def pending(what):
    return f'<p class="pending">pending: waiting for {esc(what)}</p>'


def cells_of(summary):
    return {(c["cell"], c["attn"], c["arm"]): c for c in (summary or {}).get("cells", [])}


def paired_of(summary, cell, attn, a="target", b="base"):
    for p in (summary or {}).get("paired", []):
        if p["cell"] == cell and p["attn"] == attn and p.get("a", "target") == a and p.get("b", "base") == b:
            return p
    return None


def delta_of(summary, cell, attn, a="target", b="base"):
    for d in (summary or {}).get("deltas", []):
        if d["cell"] == cell and d["attn"] == attn and d.get("a", "target") == a and d.get("b", "base") == b:
            return d
    return None


ATTR_D = (("base", "mid", "target"), (("mid", "base", "base -> mid: main's own change (PR #3879 + PR #4400)"), ("target", "mid", "mid -> target: PR #4424"), ("target", "base", "base -> target")), "block D results (exec/results/wedperf-attr-20260916/summary.json)")
ATTR_E = (("base", "p3879", "mid", "target"), (("p3879", "base", "base -> p3879: PR #3879 alone"), ("mid", "p3879", "p3879 -> mid: PR #4400 alone"), ("target", "mid", "mid -> target: PR #4424"), ("target", "base", "base -> target")), "block E results (exec/results/wedperf-attr2-20260916/summary.json)")


def attribution_table(summary_d, spec=ATTR_D):
    """Attribution blocks: several binaries per cell and the steps between them, each with the paired t.
    spec = (arms, ((a, b, column label), ...), pending text)."""
    arms, step_specs, pend = spec
    if not summary_d or not summary_d.get("cells"):
        return pending(pend)
    cells = cells_of(summary_d)
    rows = [(c, attn) for attn in ("cpu", "fpga") for c in CELL_ORDER if any((c, attn, a) in cells for a in arms)]
    out = ["<table><thead><tr><th>cell</th><th>attention</th><th>metric</th>" + "".join(f"<th>{esc(a)}</th>" for a in arms) + "".join(f"<th>{esc(lab)}</th>" for _, _, lab in step_specs) + "</tr></thead><tbody>"]
    for cell, attn in rows:
        for metric, key, nd, unit, pk, lower in (("TPS per user", "tps_mean", 2, "", "tps", False), ("TTFT s", "ttft_mean", 3, "", "ttft_s", True)):
            vals = [cells.get((cell, attn, a)) for a in arms]
            cols = [fmt(v[key], nd) + (f" (n {v['n']})" if v else "") if v else "-" for v in vals]
            steps = []
            for a, b, _ in step_specs:
                d = delta_of(summary_d, cell, attn, a, b)
                p = paired_of(summary_d, cell, attn, a, b)
                if not d:
                    steps.append("-")
                    continue
                pct = d["tps_delta_pct"] if metric.startswith("TPS") else d["ttft_delta_pct"]
                s = f"{pct:+.1f}%"
                if not metric.startswith("TPS"):
                    s += f" ({d['ttft_delta_ms']:+.0f} ms)"
                cls, txt = verdict(p, pk, lower, pct_of(d, "tps" if metric.startswith("TPS") else "ttft"))
                s += f", {txt}"
                steps.append(f'<span class="v-{cls}">{esc(s)}</span>')
            out.append(f"<tr><td>{esc(nice(cell))}</td><td>{esc(attn.upper() if attn == 'fpga' else 'CPU')}</td><td>{esc(metric)}</td>" + "".join(f"<td>{esc(c)}</td>" for c in cols) + "".join(f"<td>{s}</td>" for s in steps) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def cells_present(summary, attn):
    cells = cells_of(summary)
    seen = [k for k in CELL_ORDER if any((k, attn, a) in cells for a in ARMS)]
    extra = sorted({c["cell"] for c in (summary or {}).get("cells", []) if c["attn"] == attn and c["cell"] not in CELL_ORDER})
    return seen + extra


def nice(cell):
    return CELL_NICE.get(cell, cell)


def verdict(pr, metric, lower_better, pct=None):
    """(class, text) from the paired dict of one metric. Resolved = |t| >= 2 AND |change| >= 1%
    (the percent change of the means, when given): with 2 or 3 repetitions two nearly equal runs
    give a large t for a change too small to matter, so the size floor keeps those out."""
    if not pr or not pr.get(metric):
        return "none", "no paired repetition"
    p = pr[metric]
    if p["n"] < 2 or p["t"] is None:
        return "single", f"n = {p['n']}, no t"
    better = (p["mean"] < 0) if lower_better else (p["mean"] > 0)
    if abs(p["t"]) < T_RESOLVED:
        return "flat", f"not resolved (t = {p['t']:+.1f}, n = {p['n']})"
    if pct is not None and abs(pct) < PCT_FLOOR:
        return "flat", f"below the 1% floor (t = {p['t']:+.1f}, n = {p['n']})"
    return ("gain" if better else "loss"), f"{'gain' if better else 'loss'} (t = {p['t']:+.1f}, n = {p['n']})"


def pct_of(d, metric):
    return None if not d else (d["tps_delta_pct"] if metric == "tps" else d["ttft_delta_pct"])


def delta_bars(summary, attn, metric, title):
    """Horizontal bars: target vs base in percent per cell; value label at the bar end, t next
    to it; blue = improvement, red = regression, gray = not resolved (|t| < 2 or a change below 1%)."""
    rows = cells_present(summary, attn)
    lower_better = metric == "ttft"
    key_pct = "tps_delta_pct" if metric == "tps" else "ttft_delta_pct"
    pkey = "tps" if metric == "tps" else "ttft_s"
    data = []
    for cell in rows:
        d = delta_of(summary, cell, attn)
        if not d:
            continue
        pr = paired_of(summary, cell, attn)
        cls, txt = verdict(pr, pkey, lower_better, d[key_pct])
        data.append((cell, d[key_pct], cls, pr[pkey] if pr and pr.get(pkey) else None, d.get("ttft_delta_ms")))
    if not data:
        return pending(f"summary.json ({attn}, {metric})")
    W, LEFT, RIGHT, ROW_H, TOP = 1060, 305, 300, 30, 56
    H = TOP + ROW_H * len(data) + 44
    vals = [v for _, v, _, _, _ in data]
    lim = max(5.0, max(abs(v) for v in vals) * 1.15)
    x0, x1 = LEFT, W - RIGHT
    xm = (x0 + x1) / 2

    def X(v):
        return xm + v / lim * (x1 - x0) / 2

    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(title)}">',
           f'<rect width="{W}" height="{H}" fill="{SURF}"/>',
           f'<text x="{LEFT}" y="22" fill="{INK}" font-size="15" font-weight="600">{esc(title)}</text>']
    # legend
    lx = LEFT
    for col, lab in ((C_GAIN, "gain (resolved, better)"), (C_LOSS, "loss (resolved, worse)"), (C_FLAT, "not resolved / below the 1% floor")):
        out.append(f'<rect x="{lx}" y="{TOP - 20}" width="12" height="12" rx="2" fill="{col}"/>')
        out.append(f'<text x="{lx + 17}" y="{TOP - 10}" fill="{INK2}" font-size="12">{esc(lab)}</text>')
        lx += 17 + 6.6 * len(lab) + 22
    # gridlines at round percents
    step = 5 if lim <= 30 else (10 if lim <= 60 else 25)
    v = -step * int(lim // step)
    while v <= lim + 1e-9:
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{TOP - 2}" x2="{x:.1f}" y2="{TOP + ROW_H * len(data)}" stroke="{GRID if v != 0 else MUTED}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{TOP + ROW_H * len(data) + 16}" fill="{MUTED}" font-size="11" text-anchor="middle">{v:+d}%</text>')
        v += step
    for i, (cell, pct, cls, p, dms) in enumerate(data):
        y = TOP + ROW_H * i + ROW_H / 2
        col = C_GAIN if cls == "gain" else (C_LOSS if cls == "loss" else C_FLAT)
        xa, xb = sorted((X(0), X(pct)))
        bw = max(xb - xa, 1.5)
        out.append(f'<text x="{LEFT - 12}" y="{y + 4}" fill="{INK}" font-size="13" text-anchor="end">{esc(nice(cell))}</text>')
        out.append(f'<rect x="{xa:.1f}" y="{y - 9}" width="{bw:.1f}" height="18" rx="3" fill="{col}"><title>{esc(nice(cell))}: {pct:+.1f}%</title></rect>')
        lab = f"{pct:+.1f}%"
        if metric == "ttft" and dms is not None:
            lab += f" ({dms:+.0f} ms)"
        if p and p.get("t") is not None:
            lab += f", t = {p['t']:+.1f}, n = {p['n']}"
        elif p:
            lab += f", n = {p['n']}"
        # the label sits at the bar's far end; when it would leave the plot it moves to the other
        # side of the zero line (so it never runs into the row names or off the right edge)
        tw = 6.6 * len(lab)
        if pct >= 0:
            if xb + 8 + tw <= W - 6:
                out.append(f'<text x="{xb + 8:.1f}" y="{y + 4}" fill="{INK}" font-size="12">{esc(lab)}</text>')
            else:
                out.append(f'<text x="{xa - 8:.1f}" y="{y + 4}" fill="{INK}" font-size="12" text-anchor="end">{esc(lab)}</text>')
        else:
            if xa - 8 - tw >= LEFT + 4:
                out.append(f'<text x="{xa - 8:.1f}" y="{y + 4}" fill="{INK}" font-size="12" text-anchor="end">{esc(lab)}</text>')
            else:
                out.append(f'<text x="{xb + 8:.1f}" y="{y + 4}" fill="{INK}" font-size="12">{esc(lab)}</text>')
    better = "lower TTFT is better: bars to the left are improvements" if lower_better else "higher TPS is better: bars to the right are improvements"
    out.append(f'<text x="{W - 10}" y="{H - 8}" fill="{INK2}" font-size="11" text-anchor="end">{esc(better)}. resolved = |t| >= 2 and a change of at least 1%; t = paired mean / (sd / sqrt(n)) over the repetitions</text>'.replace("; t =", ". t ="))
    out.append("</svg>")
    return "\n".join(out)


def dumbbell(summary, attn, metric, title, unit, nd, lower_better):
    """One row per cell, each with its own axis: base and target means as 7-px dots joined by a
    gray bar, the repetitions as faint 4-px dots, direct value labels, the gap annotated."""
    cells = cells_of(summary)
    rows = cells_present(summary, attn)
    if not rows:
        return pending(f"summary.json ({attn}, {metric})")
    W, LEFT, RIGHT, ROW_H, TOP = 1060, 305, 330, 64, 52
    H = TOP + ROW_H * len(rows) + 30
    key_mean = "tps_mean" if metric == "tps" else "ttft_mean"
    key_sd = "tps_sd" if metric == "tps" else "ttft_sd"
    key_rep = "tps_per_user" if metric == "tps" else "ttft_s"
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(title)}">',
           f'<rect width="{W}" height="{H}" fill="{SURF}"/>',
           f'<text x="{LEFT}" y="22" fill="{INK}" font-size="15" font-weight="600">{esc(title)}</text>']
    lx = LEFT
    for a in ARMS:
        out.append(f'<circle cx="{lx + 5}" cy="{TOP - 12}" r="5" fill="{ARM_COLOR[a]}"/>')
        out.append(f'<text x="{lx + 14}" y="{TOP - 8}" fill="{INK2}" font-size="12">{esc(a)}</text>')
        lx += 14 + 7 * len(a) + 22
    out.append(f'<text x="{W - 10}" y="{TOP - 8}" fill="{INK2}" font-size="12" text-anchor="end">large dot = mean, small dots = repetitions. {esc("Lower is better" if lower_better else "Higher is better")}</text>')
    for i, cell in enumerate(rows):
        y = TOP + ROW_H * i + ROW_H / 2
        vals = {a: cells[(cell, attn, a)] for a in ARMS if (cell, attn, a) in cells}
        allv = [c[key_mean] for c in vals.values() if c[key_mean] is not None]
        allv += [r[key_rep] for c in vals.values() for r in c["reps"] if r[key_rep] is not None]
        out.append(f'<text x="{LEFT - 12}" y="{y + 4}" fill="{INK}" font-size="13" text-anchor="end">{esc(nice(cell))}</text>')
        if not allv:
            out.append(f'<text x="{LEFT}" y="{y + 4}" fill="{INK2}" font-size="12">no complete run</text>')
            continue
        lo, hi = min(allv), max(allv)
        span = max(hi - lo, abs(hi) * 0.02, 1e-9)
        lo, hi = lo - span * 0.25, hi + span * 0.25
        x0, x1 = LEFT, W - RIGHT

        def X(v):
            return x0 + (v - lo) / (hi - lo) * (x1 - x0)

        out.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{GRID}" stroke-width="1"/>')
        for tv in (lo + (hi - lo) * 0.05, (lo + hi) / 2, hi - (hi - lo) * 0.05):
            out.append(f'<text x="{X(tv):.1f}" y="{y + ROW_H / 2 - 6}" fill="{MUTED}" font-size="10" text-anchor="middle">{fmt(tv, nd)}</text>')
        if all(a in vals and vals[a][key_mean] is not None for a in ARMS):
            xb, xt = X(vals["base"][key_mean]), X(vals["target"][key_mean])
            out.append(f'<line x1="{xb:.1f}" y1="{y}" x2="{xt:.1f}" y2="{y}" stroke="{INK2}" stroke-width="2" stroke-linecap="round"/>')
            dv = vals["target"][key_mean] - vals["base"][key_mean]
            pct = 100 * dv / vals["base"][key_mean]
            gap = f"target vs base {pct:+.1f}% ({dv:+.2f} TPS)" if metric == "tps" else f"target vs base {pct:+.1f}% ({1000 * dv:+.0f} ms)"
            pr = paired_of(summary, cell, attn)
            pk = "tps" if metric == "tps" else "ttft_s"
            if pr and pr.get(pk) and pr[pk]["t"] is not None:
                gap += f", t = {pr[pk]['t']:+.1f}"
            out.append(f'<text x="{x1 + 12}" y="{y + 4}" fill="{INK}" font-size="12">{esc(gap)}</text>')
        for a in ARMS:
            c = vals.get(a)
            if not c:
                continue
            for r in c["reps"]:
                if r[key_rep] is None:
                    continue
                out.append(f'<circle cx="{X(r[key_rep]):.1f}" cy="{y}" r="4" fill="{ARM_COLOR[a]}" fill-opacity="0.35"><title>{esc(a)} rep {r["rep"]}: {fmt(r[key_rep], nd)} {esc(unit)}</title></circle>')
        slots = []
        for a in ARMS:
            c = vals.get(a)
            if not c or c[key_mean] is None:
                continue
            xmn = X(c[key_mean])
            out.append(f'<circle cx="{xmn:.1f}" cy="{y}" r="7" fill="{ARM_COLOR[a]}" stroke="{SURF}" stroke-width="2"><title>{esc(ARM_LABEL[a])}: mean {fmt(c[key_mean], nd)} {esc(unit)}, sd {fmt(c[key_sd], nd)}, n {c["n"]}</title></circle>')
            ly = y - 13 if len([s for s in slots if abs(s - xmn) < 48]) % 2 == 0 else y - 26
            slots.append(xmn)
            out.append(f'<text x="{xmn:.1f}" y="{ly}" fill="{INK}" font-size="11" text-anchor="middle">{fmt(c[key_mean], nd)}</text>')
    out.append(f'<text x="{W - RIGHT}" y="{H - 8}" fill="{INK2}" font-size="11" text-anchor="end">each row has its own axis ({esc(unit)}). The gray bar is the base-to-target gap.</text>')
    out.append("</svg>")
    return "\n".join(out)


def cells_table(summary, attn):
    cells = cells_of(summary)
    rows = cells_present(summary, attn)
    if not rows:
        return pending(f"summary.json ({attn})")
    out = ["<table><thead><tr><th>cell</th><th>model (runtron model name)</th><th>tp</th><th>users</th><th>binary</th><th>n</th><th>TPS per user</th><th>sd</th><th>TTFT s</th><th>sd</th><th>early-stop runs</th><th>runtron commit</th></tr></thead><tbody>"]
    for cell in rows:
        first = True
        for a in ARMS:
            c = cells.get((cell, attn, a))
            if not c:
                continue
            head = f'<td rowspan="{sum(1 for b in ARMS if (cell, attn, b) in cells)}">{esc(nice(cell))}</td><td rowspan="{sum(1 for b in ARMS if (cell, attn, b) in cells)}">{esc(c["model"])}</td><td rowspan="{sum(1 for b in ARMS if (cell, attn, b) in cells)}">{c["tp"]}</td><td rowspan="{sum(1 for b in ARMS if (cell, attn, b) in cells)}">{c["users"]}</td>' if first else ""
            first = False
            out.append(f'<tr>{head}<td><span class="sw" style="background:{ARM_COLOR[a]}"></span>{esc(a)}</td><td>{c["n"]}</td><td>{fmt(c["tps_mean"], 2)}</td><td>{fmt(c["tps_sd"], 2)}</td><td>{fmt(c["ttft_mean"], 3)}</td><td>{fmt(c["ttft_sd"], 3)}</td><td>{c["early_stop_runs"]}</td><td>{esc(",".join(c["versions"]))}</td></tr>')
    out.append("</tbody></table>")
    return "\n".join(out)


def paired_table(summary, attn):
    rows = cells_present(summary, attn)
    if not rows:
        return pending(f"summary.json ({attn})")
    out = ["<table><thead><tr><th>cell</th><th>TPS: target vs base</th><th>paired TPS delta, mean (sd, n, t)</th><th>reading</th><th>TTFT: target vs base</th><th>paired TTFT delta ms, mean (sd, n, t)</th><th>reading</th></tr></thead><tbody>"]
    for cell in rows:
        d = delta_of(summary, cell, attn)
        pr = paired_of(summary, cell, attn)
        if not d:
            out.append(f'<tr><td>{esc(nice(cell))}</td><td colspan="6">a binary has no complete run in this cell</td></tr>')
            continue
        pt = pr["tps"] if pr and pr.get("tps") else None
        pf = pr["ttft_s"] if pr and pr.get("ttft_s") else None
        ptxt = f"{pt['mean']:+.2f} ({pt['sd']:.2f}, {pt['n']}, {pt['t']:+.1f})" if pt and pt["t"] is not None else (f"{pt['mean']:+.2f} (n = {pt['n']})" if pt else "-")
        ftxt = f"{1000 * pf['mean']:+.0f} ({1000 * pf['sd']:.0f}, {pf['n']}, {pf['t']:+.1f})" if pf and pf["t"] is not None else (f"{1000 * pf['mean']:+.0f} (n = {pf['n']})" if pf else "-")
        ct, tt = verdict(pr, "tps", False, d["tps_delta_pct"])
        cf, tf = verdict(pr, "ttft_s", True, d["ttft_delta_pct"])
        out.append(f'<tr><td>{esc(nice(cell))}</td><td>{d["tps_delta_pct"]:+.1f}%</td><td>{esc(ptxt)}</td><td class="v-{ct}">{esc(tt)}</td><td>{d["ttft_delta_pct"]:+.1f}% ({d["ttft_delta_ms"]:+.0f} ms)</td><td>{esc(ftxt)}</td><td class="v-{cf}">{esc(tf)}</td></tr>')
    out.append("</tbody></table>")
    return "\n".join(out)


def smoke_block():
    cmp_txt = read(f"{RES}/smoke/compare.txt")
    if not cmp_txt.strip():
        return pending("smoke/compare.txt")
    lines = [l for l in cmp_txt.splitlines() if l and not l.startswith("#")]
    out = ["<table><thead><tr><th>cell</th><th>base vs target, 128 greedy tokens</th></tr></thead><tbody>"]
    for l in lines:
        m = re.match(r"(\S+) (\S+): (.*)", l)
        if m:
            txt = m[3]
            mm = re.match(r"first difference at generated token (\d+) of (\d+) \((-?\d+) vs (-?\d+)\); agreeing prefix \d+ tokens", txt)
            if mm:
                txt = f"first difference at generated token {int(mm[1]) + 1} of {mm[2]} (counting from 1): token id {mm[3]} (base) vs {mm[4]} (target). The first {mm[1]} tokens agree."
            mm = re.match(r"identical for (\d+) tokens \(lengths (\d+) / (\d+)\)", txt)
            if mm:
                txt = f"identical for all {mm[1]} tokens (both runs produced {mm[2]} tokens)" if mm[2] == mm[3] else f"identical for the first {mm[1]} tokens (base produced {mm[2]}, target {mm[3]})"
            out.append(f"<tr><td>{esc(nice(m[1]).rsplit(',', 1)[0])} ({esc('CPU' if m[2] == 'cpu' else 'FPGA')} attention, 1 user)</td><td>{esc(txt)}</td></tr>")
    out.append("</tbody></table>")
    fails = [l for l in read(f"{RES}/smoke/smoke.txt").splitlines() if l.startswith("SMOKE-")]
    if fails:
        out.append("<p>Smoke problems:</p><ul>" + "".join(f"<li>{esc(f)}</li>" for f in fails) + "</ul>")
    return "\n".join(out)


def builds_block():
    out = []
    for suffix, arm in (("pre3879", "base"), ("pr4424", "target")):
        t = read(f"{RES}/build-{suffix}.txt")
        if not t.strip():
            out.append(pending(f"build-{suffix}.txt"))
            continue
        out.append(f"<p><b>{esc(arm)} = runtron.{esc(suffix)}</b></p><pre>{esc(t.strip())}</pre>")
    return "\n".join(out)


def facts_table(facts):
    if not facts:
        return pending("model-facts.json (the per-model code-path facts)")
    out = ["<table><thead><tr><th>model</th><th>layers</th><th>query heads / KV heads (kv_mul)</th><th>head size</th><th>KV cache type</th><th>AMX kernel eligible</th><th>VNNI K layout</th><th>attention when USE_HW_ATTN is unset</th><th>what changes from base to target</th></tr></thead><tbody>"]
    for f in facts:
        out.append(f'<tr><td>{esc(f.get("slug"))}</td><td>{esc(f.get("n_layers"))}</td><td>{esc(f.get("n_query_heads"))} / {esc(f.get("n_kv_heads"))} ({esc(f.get("kv_mul"))})</td><td>{esc(f.get("head_size"))}</td><td>{esc(f.get("kv_cache_dtype"))}</td>'
                   f'<td>{"yes" if f.get("amx_kernel_eligible") else "no"}: {esc(f.get("amx_reason"))}</td><td>{"on" if f.get("vnni_layout_on") else "off"}: {esc(f.get("vnni_reason"))}</td>'
                   f'<td>{esc(f.get("default_attention_when_USE_HW_ATTN_unset"))}</td><td>{esc(f.get("what_changes_base_to_target"))}</td></tr>')
    out.append("</tbody></table>")
    unc = [(f.get("slug"), f.get("uncertainties")) for f in facts if f.get("uncertainties")]
    if unc:
        out.append("<p class=\"small\">Facts marked uncertain by the research agents (the code-reading agents that wrote exec/wedperf-20260916/model-facts.json):</p><ul>" + "".join(f"<li>{esc(s)}: {esc(u)}</li>" for s, u in unc) + "</ul>")
    return "\n".join(out)


def ciref_table(ciref):
    perf = (ciref or {}).get("perf") or {}
    if not perf:
        return pending("ci-reference-20260904.json")
    out = ["<table><thead><tr><th>nightly perf config (model, users)</th><th>nightly TPS per user (2026-09-04 run)</th><th>nightly TTFT ms</th><th>here: base TPS (CPU attention)</th><th>here: target TPS</th></tr></thead><tbody>"]
    return_rows = []
    return_rows.append("")
    return "\n".join(out[:0]) if False else None


def orientation_table(summary, ciref):
    perf = (ciref or {}).get("perf") or {}
    if not perf:
        return pending("ci-reference-20260904.json")
    cells = cells_of(summary)
    out = ["<table><thead><tr><th>cell</th><th>nightly TPS per user (GitHub Actions run 33833914529, 2026-09-04)</th><th>nightly TTFT ms</th><th>here, base, CPU attention: TPS / TTFT s</th><th>here, target: TPS / TTFT s</th></tr></thead><tbody>"]
    for cell in CELL_ORDER:
        model, tp, users = CELL_MODEL[cell]
        entries = perf.get(model) or []
        # the 70b tp2 config appears twice in perf.py (8 then 4 users); the reference file lists them in that order
        idx = 0 if cell != "l70b-tp2-4u" else 1
        e = entries[idx] if len(entries) > idx else None
        b, t = cells.get((cell, "cpu", "base")), cells.get((cell, "cpu", "target"))
        bt = f'{fmt(b["tps_mean"], 1)} / {fmt(b["ttft_mean"], 2)}' if b else "-"
        tt = f'{fmt(t["tps_mean"], 1)} / {fmt(t["ttft_mean"], 2)}' if t else "-"
        out.append(f'<tr><td>{esc(nice(cell))}</td><td>{esc(e["tps"]) if e else "not in the 2026-09-04 nightly run"}</td><td>{esc(e["ttft_ms"]) if e else "-"}</td><td>{esc(bt)}</td><td>{esc(tt)}</td></tr>')
    out.append("</tbody></table>")
    return "\n".join(out)


def gen_compare_table(summary, summary_c):
    """TPS delta of target vs base at 256 and at 1536 generated tokens, per cell (CPU attention)."""
    if not summary_c or not summary_c.get("cells"):
        return pending("block C results (exec/results/wedperf-gen1536-20260916/summary.json)")
    rows = [c for c in CELL_ORDER if delta_of(summary, c, "cpu") or delta_of(summary_c, c, "cpu")]
    out = ["<table><thead><tr><th>cell</th><th>256 generated tokens: TPS delta % (t, n)</th><th>1536 generated tokens: TPS delta % (t, n)</th><th>base TPS 256 -> 1536</th><th>target TPS 256 -> 1536</th></tr></thead><tbody>"]
    ca, cc = cells_of(summary), cells_of(summary_c)
    for cell in rows:
        da, dc = delta_of(summary, cell, "cpu"), delta_of(summary_c, cell, "cpu")
        pa, pc = paired_of(summary, cell, "cpu"), paired_of(summary_c, cell, "cpu")

        def cell_txt(d, p):
            if not d:
                return "-"
            s = f"{d['tps_delta_pct']:+.1f}%"
            if p and p.get("tps") and p["tps"]["t"] is not None:
                s += f" (t = {p['tps']['t']:+.1f}, n = {p['tps']['n']})"
            elif p and p.get("tps"):
                s += f" (n = {p['tps']['n']})"
            return s

        def abs_txt(arm):
            a, c = ca.get((cell, "cpu", arm)), cc.get((cell, "cpu", arm))
            return f"{fmt(a['tps_mean'] if a else None, 1)} -> {fmt(c['tps_mean'] if c else None, 1)}"
        out.append(f"<tr><td>{esc(nice(cell))}</td><td>{esc(cell_txt(da, pa))}</td><td>{esc(cell_txt(dc, pc))}</td><td>{esc(abs_txt('base'))}</td><td>{esc(abs_txt('target'))}</td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def machine_block():
    log = read(LOG)
    hdr = [l for l in read(f"{RES}/rt-results.txt").splitlines() if l.startswith("#") or l.startswith("version") or re.match(r"^[0-9a-f]{64} ", l)]
    parts = []
    if hdr:
        parts.append("<pre>" + esc("\n".join(hdr[:40])) + "</pre>")
    else:
        parts.append(pending("rt-results.txt header"))
    ev = [l for l in log.splitlines() if re.search(r"campaign started|campaign finished|repetition \d+ done|smokes done|STATUS waiting|kill_ours|WATCH-STOP|takeover|deadline|skip ", l)]
    if ev:
        parts.append("<p>The first start of the main campaign (17:50 UTC) was stopped on purpose at 18:09 UTC, during the gpt-oss-120b target smoke, to apply the script fixes from the pre-launch review: the --dont-stop flag on the throughput runs, the fixed-instant deadline with a validated DEADLINE_HHMM, and the removal of a partial token file after a stopped smoke. Its log line reads Terminated and its marker aborted. The second start (18:10 UTC) reused the 19 finished smokes, reran the gpt-oss-120b pair (attempt 2) and ran every block to the end. So rt-results.txt holds 24 smoke records for 22 smoke runs.</p>")
        parts.append("<p>Campaign events (from the campaign log exec/logs/wedperf-20260916.log):</p><pre>" + esc("\n".join(ev[:60])) + "</pre>")
    else:
        parts.append(pending("exec/logs/wedperf-20260916.log"))
    return "\n".join(parts)


def step_text(summary_x, cell, attn, a, b, metric):
    """one step of an attribution block: 'label: +x.x% (verdict)' or None when the pair is missing."""
    d = delta_of(summary_x, cell, attn, a, b)
    pr = paired_of(summary_x, cell, attn, a, b)
    if not d:
        return None
    if metric == "tps":
        pct = d["tps_delta_pct"]
        cls, txt = verdict(pr, "tps", False, pct)
        return f"{pct:+.1f}% ({txt})", cls
    pct = d["ttft_delta_pct"]
    cls, txt = verdict(pr, "ttft_s", True, pct)
    return f"{d['ttft_delta_ms']:+.0f} ms = {pct:+.1f}% ({txt})", cls


STEP_LABELS = {("mid", "base"): "main's own change (PR #3879 + PR #4400)", ("target", "mid"): "PR #4424",
               ("p3879", "base"): "PR #3879 alone", ("mid", "p3879"): "PR #4400 alone", ("target", "base"): "base to target as a whole"}


def attribution_items(summary_x, steps):
    """bullets: for every (cell, attn, metric) with any resolved step, the steps and their verdicts."""
    items = []
    if not summary_x or not summary_x.get("cells"):
        return items
    cells = cells_of(summary_x)
    keys = []
    for c in summary_x["cells"]:
        k = (c["cell"], c["attn"])
        if k not in keys:
            keys.append(k)
    for cell, attn in keys:
        for metric, name in (("tps", "TPS"), ("ttft", "TTFT")):
            parts, any_resolved = [], False
            for a, b in tuple(steps) + (("target", "base"),):
                r = step_text(summary_x, cell, attn, a, b, metric)
                if not r:
                    continue
                parts.append(f"{STEP_LABELS[(a, b)]}: {r[0]}")
                any_resolved = any_resolved or r[1] in ("gain", "loss")
            if parts and any_resolved:
                items.append(f"{nice(cell)}, {'CPU' if attn == 'cpu' else 'FPGA'} attention, {name}: " + ". ".join(parts) + ".")
    return items


def reading(summary, facts, summary_c=None, summary_d=None, summary_e=None):
    """Auto-text: one bullet per cell class, with the code path from the facts; then blocks C, D, E."""
    if not summary or not summary.get("cells"):
        return pending("summary.json")
    fmap = {f["slug"]: f for f in (facts or [])}
    groups = {"gain": [], "loss": [], "flat": [], "single": [], "none": []}
    ttft = {"gain": [], "loss": [], "flat": [], "single": [], "none": []}
    for cell in cells_present(summary, "cpu"):
        pr = paired_of(summary, cell, "cpu")
        d = delta_of(summary, cell, "cpu")
        if not d:
            continue
        ct, _ = verdict(pr, "tps", False, d["tps_delta_pct"])
        cf, _ = verdict(pr, "ttft_s", True, d["ttft_delta_pct"])
        model = CELL_MODEL.get(cell, ("", 0, 0))[0]
        slug = re.sub(r"-tp[24]$", "", model)
        f = fmap.get(slug)
        path = ""
        if f:
            path = " (AMX kernel" if f.get("amx_kernel_eligible") else (" (VNNI layout + AVX-512 VNNI reader, no AMX kernel" if f.get("vnni_layout_on") else " (neither the AMX kernel nor the VNNI layout")
            path += ")"
        groups[ct].append(f"{nice(cell)}: {d['tps_delta_pct']:+.1f}%{path}")
        ttft[cf].append(f"{nice(cell)}: {d['ttft_delta_pct']:+.1f}% ({d['ttft_delta_ms']:+.0f} ms)")
    out = ["<h3>Decode throughput (TPS), CPU attention, 256 generated tokens (block A)</h3><ul>"]
    for k, lab in (("gain", "Resolved gains (paired t >= 2 and at least 1%)"), ("loss", "Resolved losses (paired t <= -2 and at least 1%)"), ("flat", "Not resolved or below the 1% floor (|t| < 2, or a change under 1%)"), ("single", "Single repetition only")):
        if groups[k]:
            out.append(f"<li><b>{lab}:</b><ul>" + "".join(f"<li>{esc(x)}</li>" for x in groups[k]) + "</ul></li>")
    out.append("</ul><h3>Time to first token (TTFT), CPU attention, 256 generated tokens (block A)</h3><ul>")
    for k, lab in (("gain", "Resolved gains, lower TTFT (paired t <= -2 and at least 1%)"), ("loss", "Resolved losses, higher TTFT (paired t >= 2 and at least 1%)"), ("flat", "Not resolved or below the 1% floor (|t| < 2, or a change under 1%)"), ("single", "Single repetition only")):
        if ttft[k]:
            out.append(f"<li><b>{lab}:</b><ul>" + "".join(f"<li>{esc(x)}</li>" for x in ttft[k]) + "</ul></li>")
    out.append("</ul>")
    fp = cells_present(summary, "fpga")
    if fp:
        out.append("<h3>USE_HW_ATTN unset (block B): FPGA attention for qwen-3-4b and gpt-oss-120b (the nightly's default for them), CPU attention again for gemma-4-31b</h3><ul>")
        for cell in fp:
            d = delta_of(summary, cell, "fpga")
            pr = paired_of(summary, cell, "fpga")
            if not d:
                continue
            ct, tt = verdict(pr, "tps", False, d["tps_delta_pct"])
            cf, tf = verdict(pr, "ttft_s", True, d["ttft_delta_pct"])
            out.append(f"<li>{esc(nice(cell))}: TPS {d['tps_delta_pct']:+.1f}% ({esc(tt)}). TTFT {d['ttft_delta_pct']:+.1f}%, {d['ttft_delta_ms']:+.0f} ms ({esc(tf)}).</li>")
        out.append("</ul>")
    if summary_c and summary_c.get("cells"):
        out.append("<h3>1536 generated tokens (block C, CPU attention, the nightly's generation length)</h3><ul>")
        for cell in cells_present(summary_c, "cpu"):
            dc, pc = delta_of(summary_c, cell, "cpu"), paired_of(summary_c, cell, "cpu")
            da = delta_of(summary, cell, "cpu")
            if not dc:
                continue
            ct, tt = verdict(pc, "tps", False, dc["tps_delta_pct"])
            cf, tf = verdict(pc, "ttft_s", True, dc["ttft_delta_pct"])
            if ct in ("gain", "loss") or cf in ("gain", "loss"):
                at256 = f" (at 256 tokens {da['tps_delta_pct']:+.1f}%)" if da else ""
                out.append(f"<li>{esc(nice(cell))}: TPS {dc['tps_delta_pct']:+.1f}%{esc(at256)} ({esc(tt)}). TTFT {dc['ttft_delta_pct']:+.1f}%, {dc['ttft_delta_ms']:+.0f} ms ({esc(tf)}).</li>")
        out.append("<li>Every other cell: not resolved or below the 1% floor at 1536 tokens (section 4b).</li></ul>")
    items_d = attribution_items(summary_d, (("mid", "base"), ("target", "mid")))
    if items_d:
        nd = sorted({c["n"] for c in summary_d["cells"]})
        out.append(f"<h3>Attribution (block D, n = {'-'.join(str(x) for x in (nd[0], nd[-1])) if len(nd) > 1 else nd[0]} per binary): main's own change (PR #3879 + PR #4400) vs PR #4424</h3><p>One item per cell and metric where any step, or the base-to-target change as a whole, is resolved. Every step is listed with its verdict.</p><ul>" + "".join(f"<li>{esc(x)}</li>" for x in items_d) + "</ul>")
    items_e = attribution_items(summary_e, (("p3879", "base"), ("mid", "p3879"), ("target", "mid")))
    if items_e:
        out.append("<h3>Attribution of gpt-oss-120b (block E, n = 2 per binary): PR #3879 vs PR #4400 vs PR #4424</h3><ul>" + "".join(f"<li>{esc(x)}</li>" for x in items_e) + "</ul>")
        # the FPGA-attention TPS of gpt-oss-120b differs in sign between the blocks: say so with the numbers
        seen = []
        for name, summ in (("block B", summary), ("block D", summary_d), ("block E", summary_e)):
            r = step_text(summ, "gptoss-tp4-8u", "fpga", "target", "base", "tps") if summ else None
            pr = paired_of(summ, "gptoss-tp4-8u", "fpga", "target", "base") if summ else None
            if r:
                seen.append(f"{name}: {r[0]}")
        if len(seen) > 1:
            need = ""
            prd = paired_of(summary_d, "gptoss-tp4-8u", "fpga", "target", "base") if summary_d else None
            if prd and prd.get("tps") and prd["tps"]["mean"] and prd["tps"]["sd"]:
                n_need = math.ceil((2 * prd["tps"]["sd"] / abs(prd["tps"]["mean"])) ** 2)
                need = f" Block D's {prd['tps']['n']} paired repetitions did not resolve it (paired mean {prd['tps']['mean']:+.2f} TPS, sd {prd['tps']['sd']:.2f}). At that spread about {n_need} paired repetitions would be needed for |t| of 2, or a trace of one decode step instead."
            out.append("<p><b>Conflicting samples:</b> the FPGA-attention decode speed of gpt-oss-120b tp4, target vs base (PR #3879 + PR #4400 + PR #4424 together), differs by block:</p><ul>" + "".join(f"<li>{esc(s)}</li>" for s in seen) + f"</ul><p>The sign differs between blocks at these repetition counts. So the size and even the direction of the base-to-target change on this cell are not decided by this campaign.{esc(need)}</p>")
        # the facts table says PR #4424 changes nothing on gpt-oss's CPU path (head size 64); a resolved PR #4424 step there contradicts it
        for attn in ("cpu", "fpga"):
            r = step_text(summary_e, "gptoss-tp4-8u", attn, "target", "mid", "tps")
            if r and r[1] == "loss":
                out.append(f"<p><b>Hypothesis, not a measurement:</b> section 2.3 says PR #4424 changes no attention code for gpt-oss-120b (head size 64: neither the AMX kernel nor the VNNI layout applies). Yet the PR #4424 step of block E shows a TPS loss with {'CPU' if attn == 'cpu' else 'FPGA'} attention: {esc(r[0])}. PR #4424 also changes the generated code of every ingested model. The K save now runs a sharing check between the main thread and its helper threads (save_k_helper and the k_store_window join in model.hpp). For a row-major head that check returns at once. It still runs once per layer and per pass. Whether that check costs the measured time, or the two repetitions are noise, is not decided here. The measurement that decides it: 6 or more repetitions of this cell, or a trace with Perfetto (the timeline tracing tool built into tron: it records how long each function ran) of one decode step with and without PR #4424.</p>")
                break
    return "\n".join(out)


def who_moved(summary_d, summary_e, cell, attn, metric, lower_better):
    """name of the change that carries the resolved loss (or gain) of a cell, from the attribution blocks."""
    names = []
    for summ, steps in ((summary_e, (("p3879", "base", "PR #3879"), ("mid", "p3879", "PR #4400"), ("target", "mid", "PR #4424"))),
                        (summary_d, (("mid", "base", "main's own change (PR #3879 or PR #4400)"), ("target", "mid", "PR #4424")))):
        if not summ:
            continue
        found = []
        for a, b, name in steps:
            d = delta_of(summ, cell, attn, a, b)
            pr = paired_of(summ, cell, attn, a, b)
            if not d:
                continue
            pct = d["tps_delta_pct"] if metric == "tps" else d["ttft_delta_pct"]
            cls, _ = verdict(pr, "tps" if metric == "tps" else "ttft_s", lower_better, pct)
            if cls == "loss":
                found.append(name)
        if found:
            return found
    return names


def short_version(summary, marker, summary_c=None, summary_d=None, summary_e=None):
    if not summary or not summary.get("cells"):
        return '<div class="short"><b>Short version.</b> ' + esc(f"The campaign has not produced complete runs yet (marker: {marker or 'none'}).") + "</div>"
    cpu = cells_present(summary, "cpu")
    ds = [(c, delta_of(summary, c, "cpu"), paired_of(summary, c, "cpu")) for c in cpu]
    ds = [(c, d, p) for c, d, p in ds if d]
    if not ds:
        return '<div class="short"><b>Short version.</b> No cell has both binaries yet.</div>'
    gains = [(c, d) for c, d, p in ds if verdict(p, "tps", False, d["tps_delta_pct"])[0] == "gain"]
    losses = [(c, d) for c, d, p in ds if verdict(p, "tps", False, d["tps_delta_pct"])[0] == "loss"]
    tl = [(c, d) for c, d, p in ds if verdict(p, "ttft_s", True, d["ttft_delta_pct"])[0] == "loss"]

    def lab(c):
        return nice(c).rsplit(",", 1)[0].replace(",", "")

    s1 = (f"We compared two builds of runtron (the command-line tool of tron, the inference program under test) on the 12 model configurations of the nightly perf test: "
          f"base = main just before the AMX kernel PR #3879 merged (no AMX code), target = the PR #4424 head (AMX kernel plus VNNI K layout).")
    s2 = (f"With CPU attention, target's decode speed (TPS, generated tokens per second per user) is higher by a resolved margin (paired |t| of 2 or more and a change of at least 1%) in {len(gains)} of {len(ds)} cells"
          + " and lower in " + (f"{len(losses)} (" + ", ".join(f"{lab(c)} {d['tps_delta_pct']:+.1f}%" for c, d in losses) + ")" if losses else "none"))
    if summary_c and summary_c.get("cells"):
        cg = []
        for c in cells_present(summary_c, "cpu"):
            dc, pc = delta_of(summary_c, c, "cpu"), paired_of(summary_c, c, "cpu")
            if dc and verdict(pc, "tps", False, dc["tps_delta_pct"])[0] == "gain":
                cg.append((c, dc))
        cg.sort(key=lambda x: -x[1]["tps_delta_pct"])
        if cg:
            s2 += ", and at the nightly's generation length (1536 tokens) the largest gains are " + ", ".join(f"{lab(c)} {d['tps_delta_pct']:+.1f}%" for c, d in cg[:3])
    s2 += "."
    ttft_bad = ", ".join(f"{lab(c)} TTFT (time to first token) {d['ttft_delta_ms']:+.0f} ms = {d['ttft_delta_pct']:+.1f}%" for c, d in tl)
    fp = cells_present(summary, "fpga")
    fbad = []
    for c in fp:
        d, p = delta_of(summary, c, "fpga"), paired_of(summary, c, "fpga")
        # block D repeats the ingested FPGA cells with more repetitions: prefer the larger paired n
        dd, pdd = (delta_of(summary_d, c, "fpga"), paired_of(summary_d, c, "fpga")) if summary_d else (None, None)
        if dd and pdd and pdd.get("tps") and (not p or not p.get("tps") or pdd["tps"]["n"] > p["tps"]["n"]):
            d, p = dd, pdd
        if not d:
            continue
        ct = verdict(p, "tps", False, d["tps_delta_pct"])[0]
        cf = verdict(p, "ttft_s", True, d["ttft_delta_pct"])[0]
        if ct == "loss" or cf == "loss":
            parts = []
            if ct == "loss":
                parts.append(f"TPS {d['tps_delta_pct']:+.1f}%")
            if cf == "loss":
                parts.append(f"TTFT {d['ttft_delta_ms']:+.0f} ms = {d['ttft_delta_pct']:+.1f}%")
            fbad.append(f"{lab(c)} " + " and ".join(parts))
    s3 = "The costs: " if (tl or fbad) else "No resolved regression appeared"
    if tl:
        s3 += f"with CPU attention {ttft_bad}"
    if fbad:
        s3 += ("; " if tl else "") + "with FPGA attention (the nightly's default for qwen-3-4b and gpt-oss-120b, each cell taken from the block with the most repetitions) " + ", ".join(fbad)
    if summary_e and any("gpt-oss" in x for x in [ttft_bad]):
        shares = []
        for a, b, name in (("p3879", "base", "PR #3879"), ("mid", "p3879", "PR #4400"), ("target", "mid", "PR #4424")):
            ms = []
            for attn, an in (("cpu", "CPU"), ("fpga", "FPGA")):
                d = delta_of(summary_e, "gptoss-tp4-8u", attn, a, b)
                pr = paired_of(summary_e, "gptoss-tp4-8u", attn, a, b)
                if d and verdict(pr, "ttft_s", True, d["ttft_delta_pct"])[0] == "loss":
                    ms.append(f"{d['ttft_delta_ms']:+.0f} ms with {an} attention")
            if ms:
                shares.append(f"{name} ({', '.join(ms)})")
        if shares:
            s3 += ", and the attribution runs (blocks D and E) assign that TTFT increase to " + " and ".join(shares) + ("" if any("PR #4424" in x for x in shares) else ", and PR #4424 adds none")
    s3 += "."
    s3 = s3.replace("; with FPGA", ", and with FPGA")
    return f'<div class="short"><b>Short version.</b> {esc(s1)} {esc(s2)} {esc(s3)}</div>'


def main():
    summary = jload(f"{RES}/summary.json")
    summary_c = jload(f"{RES_C}/summary.json")
    summary_d = jload(f"{RES_D}/summary.json")
    summary_e = jload(f"{RES_E}/summary.json")
    facts_doc = jload(FACTS)
    facts = (facts_doc or {}).get("model_facts") if isinstance(facts_doc, dict) else facts_doc
    ciref = jload(CIREF)
    marker = read(f"{EXEC}/logs/wedperf-20260916.done").strip()
    n_rt = (summary or {}).get("n_rt_records", 0)
    n_cpu = sum(c["n"] for c in (summary or {}).get("cells", []) if c["attn"] == "cpu")
    n_fpga = sum(c["n"] for c in (summary or {}).get("cells", []) if c["attn"] == "fpga")
    n_smoke = read(f"{RES}/rt-results.txt").count("### runtron kind=smoke")
    words = [
        ("tron, runtron", "tron = the inference program under test. runtron = its command-line tool that runs one model with synthetic prompts and prints per-user timing lines."),
        ("the nightly, System CI", "the systems_test CI (continuous integration) run that executes on delphi-3bda every night. Its perf test (scripts/perf.py) runs 12 model configurations. This report uses those 12."),
        ("PR, PR head, main", "PR = a GitHub pull request. main = the main branch of the tron repository. PR #3879 = the AMX attention kernel, merged into main on 2026-09-15 22:19 UTC. PR #4424 = the VNNI K layout (defined below) on top of it, not merged. Its head (newest commit) is ff680c8020."),
        ("base, target", "the two binaries compared. base = runtron built from main at eb2de0265a, the commit just before PR #3879 merged (no AMX code at all). target = runtron built from the PR #4424 head with the CMake build options TRON_AMX_DISPATCH=ON (compiles the AMX kernel in) and TRON_K_VNNI=ON (compiles the VNNI K layout in). So target minus base = the effect of PR #3879, PR #4400 (an ingest-pipeline change merged between them, see section 4c) and PR #4424 together."),
        ("AMX", "Intel Advanced Matrix Extensions, the tile-multiply instruction set of the CPU. The AMX attention kernel of PR #3879 serves heads of size 128 with 4 query heads per KV head and a bf16 (bfloat16, a 16-bit floating-point number format) KV cache, on the CPU attention path."),
        ("VNNI K layout", "VNNI = Vector Neural Network Instructions, an instruction group of AVX-512 (Intel Advanced Vector Extensions 512, the 512-bit vector instruction set of the same CPUs). The name is used here for the pair-interleaved data layout those instructions read: the two values of one dimension pair of a token lie next to each other, and one 64-byte row holds that pair for 16 consecutive tokens. PR #4424 stores the K cache of 128-dimension heads in that layout. The AMX tile multiply reads that layout directly. Models that cannot use the AMX kernel read it with an AVX-512 routine (the reader)."),
        ("K, V, KV cache, KV head, kv_mul", "K = key vector, V = value vector that attention stores for every token in every layer (one of the model's repeated transformer blocks). The KV cache holds them. A KV head is one key/value head. kv_mul = the number of query heads that share one KV head."),
        ("CPU attention, FPGA attention", "where the attention over the KV cache runs. CPU attention = on the host cores (environment variable USE_HW_ATTN=0): the only path PR #3879 and PR #4424 change. FPGA attention = on the FPGA (field-programmable gate array) accelerator cards (USE_HW_ATTN unset): the nightly's default for ingested models (model plugins produced by the ingest pipeline, with names that start with ingested-). Hand-written plugins run CPU attention by default [h/tron/models/hw_attn_config.hpp:12]."),
        ("tp2, tp4", "the tensor-parallel width: how many FPGA cards the model is split over. Here tp2 = runtron --instance 2,4 (slice 2 of 4 equal slices of the machine's cards: cards 90 and 93), tp4 = --instance 1,2 (slice 1 of 2: cards 90, 93, b9, bc): our half of delphi-3bda (CPU socket 1)."),
        ("fast, good", "variant names of the hand-written models in config/models.yaml: different weight files (quantization) of the same architecture. The names are the nightly's."),
        ("TPS", "generated tokens per second per user in decode (the phase that produces the answer one token per step, after the prompt has been read). Measured as runtron's \"average tok/s\" per request, averaged over the users of a run."),
        ("TTFT", "time to first token: runtron's \"Parsing the prompt took\" time, the maximum over the users of a run. Lower is better."),
        ("cell, repetition", "a cell = one (model configuration, attention mode) with its CI user count, prompt 1024 tokens, 256 generated tokens (1536 generated tokens in block C, the repeat described in section 4b). A repetition = one run of a cell with one binary. The binaries interleave inside each repetition (base, target, base, target, ...)."),
        ("paired delta, t", "for every repetition present in both binaries, target minus base. The tables report the mean, the sample standard deviation (sd), n (the number of paired repetitions), and t = mean / (sd / sqrt(n)). A change is called resolved here when |t| is 2 or more and the change of the means is at least 1%. The size floor matters because two nearly equal repetitions give a large t for a change too small to matter. With 2 or 3 repetitions this is a coarse rule, not a significance test. The pairing removes slow drifts of the machine. The result tables and the chart legends use four verdict words. gain = a resolved change in the better direction (higher TPS or lower TTFT). loss = a resolved change in the worse direction. not resolved = |t| under 2. below the 1% floor = |t| of 2 or more but a change of the means under 1%."),
        ("block", "one pass of the campaign: a set of cells run with a set of binaries in one attention mode and one generation length. Block A = section 3, block B = section 4, block C = section 4b, block D = section 4c, block E = section 4d."),
        ("engagement point", "with FPGA attention the accelerator scores a request's tokens from position 127 on. Positions 0 to 126 of every request are scored by the CPU attention code, so the AMX kernel and the VNNI reader still run for that first slice [h/tron/models/hw_attn_config.hpp]."),
        ("early-stop run", "a run in which one user's request ended early (a stop token) or fewer TPS lines than users were printed. The other users then run faster. So the TPS of that run is excluded. Its TTFT is kept."),
        ("smoke", "a 1-user greedy run of 128 tokens (temperature 0 = always the highest-scoring token, deterministic reductions = sums in a fixed order so that two runs give identical tokens) whose token ids are saved and compared between the binaries."),
        ("our half", "delphi-3bda is shared by halves: the first four cards and CPU socket 0 are Bill's, the second four cards and socket 1 are ours. Every run here is on our half."),
    ]
    words_html = "<table><thead><tr><th>term</th><th>meaning</th></tr></thead><tbody>" + "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in words) + "</tbody></table>"
    cells_rows = "".join(f'<tr><td>{esc(nice(k))}</td><td>{esc(CELL_MODEL[k][0])}</td><td>{CELL_MODEL[k][1]}</td><td>{CELL_MODEL[k][2]}</td><td>{"CPU (its default). FPGA attention is not available for its shape, so its block B runs also used CPU attention." if k == "g4-31b-tp2-8u" else ("CPU + FPGA (FPGA is its default)" if CELL_MODEL[k][0].startswith("ingested-") else "CPU (its default)")}</td></tr>' for k in CELL_ORDER)
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wednesday perf test</title>
<meta name="description" content="The nightly CI's 12 perf models: main before PR #3879 vs the PR #4424 head, on our half of delphi-3bda.">
<style>
:root {{ color-scheme: light; --ink: {INK}; --ink2: {INK2}; --grid: {GRID}; --surf: {SURF}; --bg: #ffffff; --accent: #2a78d6; }}
body {{ margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; max-width: 1100px; margin-left: auto; margin-right: auto; }}
h1 {{ font-size: 24px; margin: 0 0 6px; }} h2 {{ font-size: 19px; margin: 36px 0 8px; border-bottom: 1px solid var(--grid); padding-bottom: 4px; }} h3 {{ font-size: 16px; margin: 22px 0 6px; }}
p, li {{ max-width: 900px; }} .meta {{ color: var(--ink2); font-size: 13px; }}
.short {{ background: #f4f3f0; border-left: 4px solid var(--accent); padding: 10px 14px; margin: 14px 0 6px; max-width: 900px; }}
table {{ border-collapse: collapse; margin: 10px 0 16px; font-size: 13px; }} th, td {{ border: 1px solid var(--grid); padding: 4px 8px; text-align: left; vertical-align: top; }} th {{ background: #f4f3f0; }}
td:nth-child(n+3):not(:last-child) {{ font-variant-numeric: tabular-nums; }}
pre {{ background: #f6f5f2; border: 1px solid var(--grid); padding: 8px 10px; font-size: 12px; overflow-x: auto; }}
.chart {{ max-width: 100%; height: auto; display: block; margin: 8px 0 4px; }}
.pending {{ color: #7a3b00; background: #fff4e5; border: 1px solid #f2c88f; padding: 6px 10px; display: inline-block; border-radius: 4px; }}
.sw {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }}
.small {{ font-size: 13px; color: var(--ink2); }}
.v-gain {{ color: #006300; }} .v-loss {{ color: #b3261e; }} .v-flat, .v-single, .v-none {{ color: var(--ink2); }}
</style></head><body>
<h1>Wednesday perf test: the nightly CI's models, main before PR #3879 vs the PR #4424 head</h1>
<p class="meta">Generated {esc(NOW)} from exec/results/wedperf-20260916 by exec/wedperf-20260916/gen_report.py. {n_rt} perf-run records read from rt-results.txt, the raw results file of blocks A and B (one record per run: {n_cpu} with USE_HW_ATTN=0, {n_fpga} with USE_HW_ATTN unset), plus {n_smoke} smoke records (section 5). Blocks C, D and E are read from their own results folders (section 10). Campaign end marker (the .done file that the campaign script writes when every run has finished): {esc(marker or "not written yet, the campaign is still running")}. Machine: our half of delphi-3bda. Prompt 1024 tokens, 256 generated tokens, the nightly's user count per model.</p>
{short_version(summary, marker, summary_c, summary_d, summary_e)}

<h2>1. Words used here</h2>
{words_html}

<h2>2. What was compared</h2>
<h3>2.1 The two binaries</h3>
<table><thead><tr><th>binary</th><th>commit</th><th>CMake options (preset cross-avx512, BUILD_INGEST_MODELS=ON, BUILD_PRODUCTION_MODELS=ON)</th><th>attention code on the CPU path</th></tr></thead><tbody>
<tr><td><span class="sw" style="background:{ARM_COLOR['base']}"></span>base = runtron.pre3879</td><td>eb2de0265a (main, parent 1 of the PR #3879 merge commit 3fd5edaa66, 2026-09-15 22:04 UTC)</td><td>none of the AMX options exist at this commit</td><td>the AVX-512 dotter (the dot-product routine that scores one query against the keys of a page) over row-major K (main before AMX)</td></tr>
<tr><td><span class="sw" style="background:{ARM_COLOR['target']}"></span>target = runtron.pr4424</td><td>ff680c8020 (PR #4424 head, 18 commits on top of main c7844ca2ce. c7844ca2ce = eb2de0265a + the merges of PR #3879 and PR #4400, an ingest-pipeline change described in section 4c)</td><td>TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON</td><td>the AMX QK/PV kernel (QK = the query-key score multiply, PV = the probability-times-value multiply) where the model shape is eligible. The VNNI K layout for every 128-dimension head. The AVX-512 VNNI reader where the kernel is not eligible.</td></tr>
</tbody></table>
<p>The runtime kill switch TRON_AMX_DISABLE (an environment variable that turns the AMX kernel off) is unset in both binaries. BUILD_PRODUCTION_MODELS=ON (the CMake option that compiles the models tagged production) was set for both builds. llama-3.3-70b-instruct-good carries only the production tag in config/models.yaml. A default build leaves it out.</p>
{builds_block()}
<h3>2.2 The cells</h3>
<p>The 12 configurations of the nightly's perf test (systems_test scripts/perf.py at 6b20db0, 2026-09-15), each at its nightly user count. Every cell here runs prompt 1024 tokens and 256 generated tokens (1536 in block C, section 4b). The nightly differs in three ways:</p>
<ul>
<li>it generates 1536 tokens per request (845 in the llama-3.2-3b cell).</li>
<li>it uses sharegpt prompts (prompts taken from the ShareGPT set of real chat logs) of 1024 tokens [systems_test scripts/perf.py, prompt_length].</li>
<li>its llama-3.2-3b cell gives all 32 users a shared 800-token prefix plus 200 prompt tokens each.</li>
</ul>
<table><thead><tr><th>cell</th><th>runtron model slug (the model name as given on the runtron command line)</th><th>tp</th><th>users</th><th>attention modes run</th></tr></thead><tbody>{cells_rows}</tbody></table>
<p>Block A runs every cell with CPU attention (USE_HW_ATTN=0), the path both PRs change. Block B repeats the four ingested cells with USE_HW_ATTN unset. For qwen-3-4b and gpt-oss-120b that is FPGA attention, their default in the nightly. For gemma-4-31b FPGA attention is not available (head size 256 dimensions and 16 KV heads, a shape the FPGA attention path does not support), so its block B runs used CPU attention again [runtron log line "HW-attention not available for this model"]. With FPGA attention the AMX kernel runs only for the positions below the engagement point (the first 127 tokens of a request). For every other position only the K save into the VNNI layout differs between the binaries. The hand-written plugins run CPU attention by default, so block A already is their nightly mode.</p>
<h3>2.3 Which code path each model takes</h3>
{facts_table(facts)}

<h2>3. Results, CPU attention (block A)</h2>
<h3>3.1 Decode throughput: target vs base in percent</h3>
{delta_bars(summary, "cpu", "tps", "Decode TPS per user, target vs base, CPU attention")}
<h3>3.2 Time to first token: target vs base in percent</h3>
{delta_bars(summary, "cpu", "ttft", "TTFT, target vs base, CPU attention (negative = faster)")}
<h3>3.3 Decode throughput, absolute values</h3>
{dumbbell(summary, "cpu", "tps", "Decode TPS per user, per cell (CPU attention)", "TPS", 1, False)}
<h3>3.4 Time to first token, absolute values</h3>
{dumbbell(summary, "cpu", "ttft", "TTFT in seconds, per cell (CPU attention)", "s", 2, True)}
<h3>3.5 The numbers</h3>
{cells_table(summary, "cpu")}
<h3>3.6 Paired deltas</h3>
{paired_table(summary, "cpu")}

<h2>4. Results, FPGA attention (block B, the ingested models in their nightly mode)</h2>
{delta_bars(summary, "fpga", "tps", "Decode TPS per user, target vs base, FPGA attention")}
{delta_bars(summary, "fpga", "ttft", "TTFT, target vs base, FPGA attention (negative = faster)")}
{cells_table(summary, "fpga")}
{paired_table(summary, "fpga")}

<h2>4b. Results, 1536 generated tokens (block C, the nightly's generation length)</h2>
<p>The nightly generates 1536 tokens per request in 11 of the 12 cells (845 in the llama-3.2-3b cell). It measures TPS over generated tokens 896 to 1024 (2 to 333 in the llama-3.2-3b cell) [systems_test scripts/perf.py, start_capture / end_capture]. So its TPS measurement covers contexts (prompt plus tokens generated so far) of about 1900 to 2050 tokens (about 1000 to 1330 in the llama-3.2-3b cell). Block A's 256-token cells average the decode over contexts 1024 to 1280. At the longer context, attention is a larger share of one decode step (the work to generate one token). So a change to attention shows more there. Block C repeats the 12 cells with 1536 generated tokens (CPU attention, 2 repetitions). Here runtron's TPS is the average over all 1536 tokens (contexts 1024 to 2560).</p>
{delta_bars(summary_c, "cpu", "tps", "Decode TPS per user, target vs base, CPU attention, 1536 generated tokens")}
{delta_bars(summary_c, "cpu", "ttft", "TTFT, target vs base, CPU attention, 1536 generated tokens (negative = faster)")}
<h3>256 vs 1536 generated tokens</h3>
{gen_compare_table(summary, summary_c)}
{cells_table(summary_c, "cpu")}
{paired_table(summary_c, "cpu")}

<h2>4c. Attribution: which PR moved a cell (block D)</h2>
<p>Block D separates the changes between base and target.</p>
<ul>
<li>The target differs from the base by three changes: PR #3879 (the AMX attention kernel), PR #4400, and PR #4424 (the VNNI K layout). PR #4400 is a change to the ingest compiler, the program that generates the C++ code of every ingested model. Its title is "preserve cpu scratch ownership". It changes the generated code of the ingested models.</li>
<li>Block D adds a third binary, mid = runtron.main0916. It is built from main c7844ca2ce, the commit PR #4424 is based on. It has PR #3879 and PR #4400 but not PR #4424 (TRON_AMX_DISPATCH=ON, no VNNI layout).</li>
<li>The step base to mid is main's own change. The step mid to target is PR #4424 alone.</li>
<li>Cells run with CPU attention: llama-3.1-8b, qwen-3-4b tp2, gemma-2-9b and gpt-oss-120b tp4. These are four of the six cells with a resolved base-to-target change in block A. llama-3.2-3b and qwen-3-4b tp4 were left out for lack of time. Cells run with FPGA attention: qwen-3-4b tp2, qwen-3-4b tp4 and gpt-oss-120b tp4. Every cell ran 256 generated tokens. The four CPU-attention cells ran 2 repetitions. The three FPGA-attention cells ran 6 repetitions (repetitions 3 to 6 were added by a second launch after block E, exec/wedperf-20260916/launch-attr-more.sh with REPS_B=6). The three binaries interleave inside each repetition.</li>
</ul>
{attribution_table(summary_d)}
<h3>4d. gpt-oss-120b: PR #3879 or PR #4400 (block E)</h3>
<ul>
<li>Main's own change between base and mid is two merges: PR #3879 (the AMX kernel, merge commit 3fd5edaa66) and PR #4400 (a change to the ingest compiler, the program that generates the C++ code of every ingested model, merge commit c7844ca2ce).</li>
<li>Block E adds a fourth binary, p3879 = runtron.p3879. It is built from 3fd5edaa66 with the same options as mid (TRON_AMX_DISPATCH=ON, no VNNI layout).</li>
<li>The step base to p3879 is PR #3879 alone. The step p3879 to mid is PR #4400 alone.</li>
<li>Cell: gpt-oss-120b tp4 in both attention modes, 2 repetitions, the four binaries interleaved.</li>
</ul>
{attribution_table(summary_e, ATTR_E)}

<h2>5. Smoke tokens</h2>
<p>One user, 128 greedy tokens, CPU attention, both binaries. Models on the AMX kernel path or the VNNI reader path may produce different tokens. The AMX kernel and the AVX-512 dotter (main's dot-product routine over the K cache) never give bit-identical results. The VNNI reader sums the products in another order, and its rounding therefore differs too. A model with head size 64 (gpt-oss-120b) takes neither path. Its tokens must be identical.</p>
{smoke_block()}

<h2>6. Reading</h2>
{reading(summary, facts, summary_c, summary_d, summary_e)}

<h2>7. What this means for the nightly</h2>
<ul>
<li>The nightly installs tron from a Debian package (.deb, installed with apt). The GitHub Actions workflow publish-deb.yml builds that package every day from the CMake preset deb plus two flags.</li>
<li>Neither the preset nor the flags set TRON_AMX_DISPATCH (the option that compiles the AMX kernel) or TRON_K_VNNI (the option that turns on the VNNI K layout). Both options default to OFF [GNUmakefile:466-468; CMakePresets.json, configure preset deb; CMakeLists.txt:48-49; verified at ff680c8020].</li>
<li>So the package carries neither the AMX kernel nor the VNNI K layout. The nightly's numbers will not change when PR #4424 merges.</li>
<li>For the same reason the merge of PR #3879 on 2026-09-15 should not have changed them. This report did not compare the nightly's numbers before and after that merge. The two nightly runs of 2026-09-16 (GitHub Actions runs 35050734153 and 35052594106) ended with the GitHub Actions conclusion "failure", so there is no after-merge number to compare.</li>
<li>Only the older CMake-based CI workflow (cmake-single-platform.yml) compiles both options ON, and that build never becomes a package [.github/workflows/cmake-single-platform.yml:330-335; README.ci.md:518-556].</li>
</ul>
<p>If the package build is changed to compile both options, the cells here predict the direction of the change per model.</p>
<ul>
<li>The hand-written plugins (llama, mixtral, qwen-2.5, gemma-2) run CPU attention in the nightly. Blocks A and C apply to them. Block C (1536 generated tokens) is the closer match to the nightly's capture window (the range of generated tokens over which it measures TPS, section 4b).</li>
<li>qwen-3-4b and gpt-oss-120b run FPGA attention there. Block B and the FPGA rows of blocks D and E apply to them. gemma-4-31b has no FPGA attention, so block A is its nightly mode (no resolved change).</li>
</ul>
<p>The size of the change in the nightly's own per-user TPS is not predicted by these runtron numbers. runtron runs one engine (one tron process serving the model). The nightly runs 2 to 4 engines per model (section 8 shows why the scales differ).</p>

<h2>8. Orientation: the nightly's own numbers</h2>
<p>The nightly measures the same models with rinzler (the production server) behind a proxy, 2 to 4 engines per model, FPGA attention for the ingested models, sharegpt prompts and 1536 generated tokens (845 in the llama-3.2-3b cell). Its per-user TPS is therefore not comparable with the runtron numbers here. The nightly spreads the same 8 users over 2 to 4 engines. Each engine then serves 2 to 4 users. runtron serves all users of a cell with one engine [PR3879/new-PRs/PR1/Sunday-CI-layout-results.html, Words used here, row "CI, the nightly, CI harness, nightly layout"]. The table is for orientation only.</p>
{orientation_table(summary, ciref)}

<h2>9. Machine, placement and timeline</h2>
<p>The first header lines of rt-results.txt (the raw results file, section 10) list: the campaign settings, the cell list, the runtron placement flags for tp2 and tp4 (cards, cores, the NUMA node = the CPU socket whose memory the process uses, NUMA = non-uniform memory access, and hugepages = Linux large memory pages), the two binaries with their sha256 checksums and versions, and one line per run (kind, cell, binary, commit, start time).</p>
{machine_block()}

<h2>10. Raw data</h2>
<ul>
<li>exec/results/wedperf-20260916/rt-results.txt: one header line per run (kind, cell, model, tp, users, attn, binary, commit, machine load) followed by runtron's own output lines: Version, placement, HW attention (hardware attention: whether the FPGA attention path is on), and the per-user "Parsing the prompt took" and "average tok/s" lines.</li>
<li>exec/results/wedperf-20260916/rt/&lt;cell&gt;__&lt;attn&gt;__&lt;arm&gt;__rep&lt;n&gt;.log: the full runtron output of every complete run (files with the suffix .attemptN keep every attempt, including the failed ones).</li>
<li>exec/results/wedperf-20260916/smoke/: token files and logs of the smokes, compare.txt.</li>
<li>exec/results/wedperf-20260916/summary.json, summary.md: the aggregation by exec/wedperf-20260916/summarize.py.</li>
<li>exec/results/wedperf-gen1536-20260916/: the same layout for block C (1536 generated tokens). Scripts: campaign-gen.sh, launcher launch-gen1536.sh.</li>
<li>exec/results/wedperf-attr-20260916/: the same layout for block D (three binaries). Scripts: campaign-attr.sh, launcher launch-attr.sh. Its summary.json carries three pairs: mid vs base, target vs mid, target vs base.</li>
<li>exec/results/wedperf-attr2-20260916/: block E (four binaries on gpt-oss-120b; campaign-attr2.sh, launcher launch-attr2.sh, build-p3879.txt for the extra binary).</li>
<li>exec/results/wedperf-20260916/build-pre3879.txt, build-pr4424.txt: commit, CMake line, sha256 and version of each binary.</li>
<li>exec/logs/wedperf-20260916.log: the campaign log (start, per-repetition progress, aborts).</li>
<li>exec/wedperf-20260916/: build.sh, build-chain.sh, campaign.sh, summarize.py, compare_tokens.py, gen_report.py, model-facts.json.</li>
</ul>
</body></html>
"""
    assert all(ord(ch) < 128 for ch in page), "non-ASCII character in the page"
    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
