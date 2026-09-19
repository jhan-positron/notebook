#!/usr/bin/env python3
"""Generate VNNIed-K-in-place/status/Wednesday-morning-report.html for the PR #4424 open item
"128-dimension heads with kv_mul other than 4": the repeated qwen-3-30b-a3b cells
(exec/results/vnnik6-20260916/summary.json, smoke/smoke.txt, build-*.txt, rt-results.txt),
the traces (exec/results/vnnik6-trace-20260916/analysis.json) and three hand-written
fragments (exec/vnnik6-20260916/sections/{remedies,recommendation,notes}.html) for the code
analysis, the recommendation and the notes. Pure-ASCII HTML, light theme only, inline SVG
(small-multiple dot plots per cell for TPS and TTFT, a prompt-length trend of the decode step
delta, bars for the decode-step composition from the traces). Every block degrades to a
"pending" note when its input is missing, so the page can be generated while the campaign
still runs. Usage: gen_report.py [OUT_HTML]
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

EXEC = "/home/jhan/workspace/intel-AMX/exec"
C = f"{EXEC}/vnnik6-20260916"
RES = os.environ.get("VNNIK6_RES", f"{EXEC}/results/vnnik6-20260916")
TRES = os.environ.get("VNNIK6_TRES", f"{EXEC}/results/vnnik6-trace-20260916")
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/Wednesday-morning-report.html"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

ARMS = ["base", "headoff", "vnni"]
ARM_LABEL = {"base": "base (main c7844ca2ce, row-major K)",
             "headoff": "headoff (PR head, layout compiled off)",
             "vnni": "vnni (PR head, VNNI layout on)"}
ARM_SHORT = {"base": "base", "headoff": "headoff", "vnni": "vnni"}
# Colors: dataviz reference palette, light mode. Slot 1 blue and slot 2 orange for the two
# PR binaries; the control is a neutral gray so the eye lands on the PR binaries. Text and
# labels never take a series color.
ARM_COLOR = {"base": "#8a8987", "headoff": "#2a78d6", "vnni": "#eb6834"}
CELL_ORDER = [(2, 1024), (4, 1024), (2, 2048), (2, 8192), (4, 8192)]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


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
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    return f"{x:.{nd}f}"


def pending(what):
    return f'<p class="pending">Pending: {esc(what)} is not available yet. gen_report.py replaces this notice with the section content on its next run, once the file exists.</p>'


def cell_name(tp, prompt):
    return f"tp{tp}, prompt {prompt}"


# ---------------------------------------------------------------- data access
def cells_of(summary):
    d = {}
    for c in (summary or {}).get("cells", []):
        d[(c["tp"], c["prompt"], c["arm"])] = c
    return d


def paired_of(summary, tp, prompt, a, b):
    for p in (summary or {}).get("paired", []):
        if p["tp"] == tp and p["prompt"] == prompt and p["a"] == a and p["b"] == b:
            return p
    return None


def delta_of(summary, tp, prompt, a, b):
    for p in (summary or {}).get("deltas", []):
        if p["tp"] == tp and p["prompt"] == prompt and p["a"] == a and p["b"] == b:
            return p
    return None


# ---------------------------------------------------------------- figures
def dot_small_multiples(summary, metric, title, unit, nd, lower_better):
    """One mini panel per cell: the three arm means as 8-px dots on a local axis, the
    repetitions as faint 4-px dots, direct value labels, and the vnni-vs-base gap annotated."""
    cells = cells_of(summary)
    rows = [(tp, p) for (tp, p) in CELL_ORDER if any((tp, p, a) in cells for a in ARMS)]
    if not rows:
        return pending(f"summary.json ({metric})")
    W, LEFT, RIGHT, ROW_H, TOP = 1060, 150, 340, 72, 52
    H = TOP + ROW_H * len(rows) + 30
    key_mean = "tps_mean" if metric == "tps" else "ttft_mean"
    key_rep = "tps_per_user" if metric == "tps" else "ttft_s"
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(title)}">',
           f'<rect width="{W}" height="{H}" fill="{SURF}"/>',
           f'<text x="{LEFT}" y="22" fill="{INK}" font-size="15" font-weight="600">{esc(title)}</text>']
    # legend
    lx = LEFT
    for a in ARMS:
        out.append(f'<circle cx="{lx + 5}" cy="{TOP - 12}" r="5" fill="{ARM_COLOR[a]}"/>')
        out.append(f'<text x="{lx + 14}" y="{TOP - 8}" fill="{INK2}" font-size="12">{esc(ARM_SHORT[a])}</text>')
        lx += 14 + 7 * len(ARM_SHORT[a]) + 22
    out.append(f'<text x="{W - 10}" y="{TOP - 8}" fill="{INK2}" font-size="12" text-anchor="end">large dot = mean, small dots = repetitions; {esc("lower is better" if lower_better else "higher is better")}</text>')
    for i, (tp, p) in enumerate(rows):
        y = TOP + ROW_H * i + ROW_H / 2
        vals = {a: cells[(tp, p, a)] for a in ARMS if (tp, p, a) in cells}
        allv = [c[key_mean] for c in vals.values() if c[key_mean] is not None]
        allv += [r[key_rep] for c in vals.values() for r in c["reps"] if r[key_rep] is not None]
        if not allv:
            continue
        lo, hi = min(allv), max(allv)
        span = max(hi - lo, abs(hi) * 0.02, 1e-9)
        lo, hi = lo - span * 0.25, hi + span * 0.25
        x0, x1 = LEFT, W - RIGHT

        def X(v):
            return x0 + (v - lo) / (hi - lo) * (x1 - x0)

        out.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{LEFT - 10}" y="{y + 4}" fill="{INK}" font-size="13" text-anchor="end">{esc(cell_name(tp, p))}</text>')
        # axis ticks (3): lo, mid, hi rounded
        for tv in (lo + (hi - lo) * 0.05, (lo + hi) / 2, hi - (hi - lo) * 0.05):
            out.append(f'<text x="{X(tv):.1f}" y="{y + ROW_H / 2 - 6}" fill="{INK2}" font-size="10" text-anchor="middle">{fmt(tv, nd)}</text>')
        # gap line base -> vnni
        if REF in vals and "vnni" in vals and vals[REF][key_mean] and vals["vnni"][key_mean]:
            xb, xv = X(vals[REF][key_mean]), X(vals["vnni"][key_mean])
            out.append(f'<line x1="{xb:.1f}" y1="{y}" x2="{xv:.1f}" y2="{y}" stroke="{INK2}" stroke-width="2" stroke-linecap="round"/>')
            dv = vals["vnni"][key_mean] - vals[REF][key_mean]
            pct = 100 * dv / vals[REF][key_mean]
            if metric == "tps":
                gap_txt = f"vnni vs {REF} {pct:+.1f}% ({dv:+.2f} TPS)"
            else:
                gap_txt = f"vnni vs {REF} {pct:+.1f}% ({1000 * dv:+.0f} ms)"
            pr = paired_of(summary, tp, p, "vnni", REF)
            if pr and pr[metric if metric == "tps" else "ttft_s"] and pr[metric if metric == "tps" else "ttft_s"]["t"] is not None:
                gap_txt += f", t = {pr[metric if metric == 'tps' else 'ttft_s']['t']:+.1f}"
            out.append(f'<text x="{x1 + 12}" y="{y + 4}" fill="{INK}" font-size="12">{esc(gap_txt)}</text>')
        # repetitions (faint), then means
        for a in ARMS:
            c = vals.get(a)
            if not c:
                continue
            for r in c["reps"]:
                if r[key_rep] is None:
                    continue
                out.append(f'<circle cx="{X(r[key_rep]):.1f}" cy="{y}" r="4" fill="{ARM_COLOR[a]}" fill-opacity="0.35"><title>{esc(ARM_SHORT[a])} rep {r["rep"]}: {fmt(r[key_rep], nd)} {esc(unit)}</title></circle>')
        label_slots = []
        for a in ARMS:
            c = vals.get(a)
            if not c or c[key_mean] is None:
                continue
            xm = X(c[key_mean])
            out.append(f'<circle cx="{xm:.1f}" cy="{y}" r="7" fill="{ARM_COLOR[a]}" stroke="{SURF}" stroke-width="2"><title>{esc(ARM_LABEL[a])}: mean {fmt(c[key_mean], nd)} {esc(unit)}, sd {fmt(c["tps_sd" if metric == "tps" else "ttft_sd"], nd)}, n {c["n"]}</title></circle>')
            # stagger value labels upwards (two heights) to avoid collisions with each other and
            # with the axis ticks below the row
            ly = y - 13 if len([s for s in label_slots if abs(s - xm) < 48]) % 2 == 0 else y - 26
            label_slots.append(xm)
            out.append(f'<text x="{xm:.1f}" y="{ly}" fill="{INK}" font-size="11" text-anchor="middle">{fmt(c[key_mean], nd)}</text>')
    out.append(f'<text x="{W - RIGHT}" y="{H - 8}" fill="{INK2}" font-size="11" text-anchor="end">each row has its own axis ({esc(unit)}). The gray bar is the {REF}-to-vnni gap.</text>')
    out.append("</svg>")
    return "\n".join(out)


def trend_svg(summary):
    """Decode step time delta (vnni - base) in ms per generated token, per prompt length; one
    line per tp. A store cost is flat over prompt length; a reader cost grows with it."""
    cells = cells_of(summary)
    series = {}
    for tp in (2, 4):
        pts = []
        for p in (1024, 2048, 8192):
            b, v = cells.get((tp, p, REF)), cells.get((tp, p, "vnni"))
            if b and v and b["tps_mean"] and v["tps_mean"]:
                d = 1000 / v["tps_mean"] - 1000 / b["tps_mean"]
                pts.append((p, d, 1000 / b["tps_mean"]))
        if pts:
            series[tp] = pts
    if not series:
        return pending("summary.json (prompt 1024/2048/8192 cells)")
    W, H, L, R, T, B = 820, 320, 70, 190, 40, 60
    allx = sorted({p for s in series.values() for p, _, _ in s})
    ally = [d for s in series.values() for _, d, _ in s] + [0.0]
    ylo, yhi = min(ally), max(ally)
    pad = max((yhi - ylo) * 0.2, 0.2)
    ylo, yhi = ylo - pad, yhi + pad
    xs = {p: L + (i + 0.5) / len(allx) * (W - L - R) for i, p in enumerate(allx)}

    def Y(v):
        return T + (yhi - v) / (yhi - ylo) * (H - T - B)

    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="decode step delta by prompt length">',
           f'<rect width="{W}" height="{H}" fill="{SURF}"/>',
           f'<text x="{L}" y="22" fill="{INK}" font-size="15" font-weight="600">Decode step time, vnni minus {REF} (ms per generated token)</text>']
    for gv in (ylo + (yhi - ylo) * k / 4 for k in range(5)):
        out.append(f'<line x1="{L}" y1="{Y(gv):.1f}" x2="{W - R}" y2="{Y(gv):.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{Y(gv) + 4:.1f}" fill="{INK2}" font-size="11" text-anchor="end">{gv:+.2f}</text>')
    out.append(f'<line x1="{L}" y1="{Y(0):.1f}" x2="{W - R}" y2="{Y(0):.1f}" stroke="{INK2}" stroke-width="1"/>')
    for p, x in xs.items():
        out.append(f'<text x="{x:.1f}" y="{H - B + 18}" fill="{INK2}" font-size="12" text-anchor="middle">prompt {p}</text>')
    colors = {2: "#2a78d6", 4: "#eb6834"}
    for tp, pts in series.items():
        path = " ".join(f'{"M" if i == 0 else "L"}{xs[p]:.1f},{Y(d):.1f}' for i, (p, d, _) in enumerate(pts))
        out.append(f'<path d="{path}" fill="none" stroke="{colors[tp]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        for p, d, bstep in pts:
            out.append(f'<circle cx="{xs[p]:.1f}" cy="{Y(d):.1f}" r="5" fill="{colors[tp]}" stroke="{SURF}" stroke-width="2"><title>tp{tp} prompt {p}: {d:+.2f} ms per token ({100 * d / bstep:+.1f}% of the base step {bstep:.2f} ms)</title></circle>')
            ly = Y(d) - 8 if tp == 2 else Y(d) + 18
            out.append(f'<text x="{xs[p] + 9:.1f}" y="{ly:.1f}" fill="{INK}" font-size="11">{d:+.2f} ms ({100 * d / bstep:+.1f}%)</text>')
        lx, ly, _ = pts[-1]
        out.append(f'<text x="{xs[lx] + 9:.1f}" y="{Y(ly) + (30 if tp == 4 else -22):.1f}" fill="{INK2}" font-size="11">tp{tp}</text>')
    out.append(f'<text x="{L}" y="{H - 20}" fill="{INK2}" font-size="11">positive = the vnni binary needs more time per generated token, negative = less.</text>')
    out.append(f'<text x="{L}" y="{H - 6}" fill="{INK2}" font-size="11">a per-token cost (the store) is a flat offset over the prompt length. A per-page effect (the reader) grows with it.</text>')
    out.append("</svg>")
    return "\n".join(out)


def trace_rows(analysis):
    rows = {}
    for r in analysis or []:
        m = re.match(r"(\w+)-tp(\d)\.perfetto-trace", r["trace"])
        if m:
            rows[(m[1], int(m[2]))] = r
    return rows


def trace_bars(analysis, tp):
    """Decode step composition per arm for one tp: four small panels, each metric on its own
    axis (pass ms, attention ms per worker, Save K ms per step, kernels ms per main helper),
    bars for the arms with direct value labels."""
    rows = trace_rows(analysis)
    arms = [a for a in ARMS if (a, tp) in rows and rows[(a, tp)]["kinds"].get("decode")]
    if not arms:
        return pending(f"trace analysis (tp{tp})")
    metrics = [("pass_ms", "decode step (pass), ms"), ("attention_total_ms_per_worker", "attention, ms per worker"),
               ("save_k_ms", "Save K per step (main thread), ms"), ("helper_kernel_ms_per_helper", "kernels, ms per main helper")]
    W, H, T, B = 960, 300, 44, 64
    PW = W / len(metrics)
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="decode step composition tp{tp}">',
           f'<rect width="{W}" height="{H}" fill="{SURF}"/>',
           f'<text x="12" y="22" fill="{INK}" font-size="14" font-weight="600">Decode step composition from the traces, tp{tp}: mean over {rows[(arms[0], tp)]["kinds"]["decode"]["n_passes"]} traced decode steps, each panel on its own axis</text>']
    bw, gap = 34, 12
    for gi, (k, label) in enumerate(metrics):
        px0 = gi * PW + 52
        px1 = (gi + 1) * PW - 12
        vmax = max(rows[(a, tp)]["kinds"]["decode"][k] for a in arms) * 1.25 or 1

        def Y(v):
            return T + (1 - v / vmax) * (H - T - B)

        for kk in range(4):
            gv = vmax * kk / 3
            out.append(f'<line x1="{px0:.1f}" y1="{Y(gv):.1f}" x2="{px1:.1f}" y2="{Y(gv):.1f}" stroke="{GRID}" stroke-width="1"/>')
            out.append(f'<text x="{px0 - 5:.1f}" y="{Y(gv) + 4:.1f}" fill="{INK2}" font-size="10" text-anchor="end">{gv:.2f}</text>')
        total = len(arms) * bw + (len(arms) - 1) * gap
        gx = (px0 + px1) / 2 - total / 2
        for ai, a in enumerate(arms):
            v = rows[(a, tp)]["kinds"]["decode"][k]
            x = gx + ai * (bw + gap)
            y = Y(v)
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{max(0.0, Y(0) - y):.1f}" rx="4" ry="4" fill="{ARM_COLOR[a]}"><title>{esc(ARM_SHORT[a])}: {label} = {v:.3f} ms</title></rect>')
            out.append(f'<rect x="{x:.1f}" y="{Y(0) - 4:.1f}" width="{bw}" height="4" fill="{ARM_COLOR[a]}"/>')
            out.append(f'<text x="{x + bw / 2:.1f}" y="{y - 5:.1f}" fill="{INK}" font-size="11" text-anchor="middle">{v:.2f}</text>')
        out.append(f'<text x="{(px0 + px1) / 2:.1f}" y="{H - B + 18}" fill="{INK2}" font-size="11" text-anchor="middle">{esc(label)}</text>')
    lx = 52
    for a in arms:
        out.append(f'<rect x="{lx}" y="{H - 22}" width="10" height="10" rx="2" fill="{ARM_COLOR[a]}"/>')
        out.append(f'<text x="{lx + 14}" y="{H - 13}" fill="{INK2}" font-size="12">{esc(ARM_SHORT[a])}</text>')
        lx += 14 + 7 * len(ARM_SHORT[a]) + 22
    out.append(f'<text x="{W - 12}" y="{H - 13}" fill="{INK2}" font-size="11" text-anchor="end">one traced run per binary; the step-to-step spread of the pass is about 2 ms</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- tables
def cells_table(summary):
    cells = cells_of(summary)
    if not cells:
        return pending("summary.json")
    h = ['<table><thead><tr><th>cell</th><th>binary</th><th>n</th><th>TPS per user</th><th>sd</th><th>TTFT s</th><th>sd</th><th>early-stop runs</th><th>version in the log</th></tr></thead><tbody>']
    for tp, p in CELL_ORDER:
        for a in ARMS:
            c = cells.get((tp, p, a))
            if not c:
                continue
            h.append(f'<tr><td>{esc(cell_name(tp, p))}</td><td><span class="sw" style="background:{ARM_COLOR[a]}"></span>{esc(ARM_SHORT[a])}</td><td>{c["n"]}</td>'
                     f'<td>{fmt(c["tps_mean"], 2)}</td><td>{fmt(c["tps_sd"], 2)}</td><td>{fmt(c["ttft_mean"], 3)}</td><td>{fmt(c["ttft_sd"], 3)}</td>'
                     f'<td>{c["early_stop_runs"]}</td><td>{esc(",".join(c.get("versions", [])))}</td></tr>')
    h.append("</tbody></table>")
    h.append("<p>An early-stop run is a run in which the 8 requests did not all generate the same number of tokens (one request left the batch early, or fewer than 8 requests reported). Its per-user TPS is not comparable with the other runs. So it is left out of the TPS means and the paired deltas. Its TTFT is kept. The column early-stop runs counts such runs per cell.</p>")
    return "\n".join(h)


def paired_table(summary):
    if not summary or not summary.get("paired"):
        return pending("summary.json (paired deltas)")
    h = ['<table><thead><tr><th>cell</th><th>comparison</th><th>TPS delta %</th><th>paired TPS delta, mean (sd) n</th><th>t</th><th>TTFT delta ms</th><th>paired TTFT delta ms, mean (sd) n</th><th>t</th><th>reading</th></tr></thead><tbody>']
    for tp, p in CELL_ORDER:
        for a, b in (("vnni", "base"), ("headoff", "base"), ("vnni", "headoff")):
            pr = paired_of(summary, tp, p, a, b)
            d = delta_of(summary, tp, p, a, b)
            if not pr or not d:
                continue
            pt, pf = pr["tps"], pr["ttft_s"]
            reading = ""
            if pt and pt["t"] is not None and a == "vnni" and b == "base":
                reading = "loss confirmed (paired t below -2)" if pt["t"] < -2 else ("gain (paired t above 2)" if pt["t"] > 2 else "no difference resolved (|t| below 2)")
            if pt and pt["t"] is not None and a == "headoff" and b == "base":
                reading = "same as base within the run-to-run spread (|t| below 2)" if abs(pt["t"]) < 2 else "headoff differs from base (|t| above 2)"
            h.append(f'<tr><td>{esc(cell_name(tp, p))}</td><td>{a} vs {b}</td><td>{d["tps_delta_pct"]:+.1f}</td>'
                     f'<td>{(fmt(pt["mean"], 2) + " (" + fmt(pt["sd"], 2) + ") " + str(pt["n"])) if pt else "-"}</td><td>{fmt(pt["t"], 1) if pt and pt["t"] is not None else "-"}</td>'
                     f'<td>{d["ttft_delta_ms"]:+.0f}</td><td>{(fmt(1000 * pf["mean"], 0) + " (" + fmt(1000 * pf["sd"], 0) + ") " + str(pf["n"])) if pf else "-"}</td><td>{fmt(pf["t"], 1) if pf and pf["t"] is not None else "-"}</td><td>{esc(reading)}</td></tr>')
    h.append("</tbody></table>")
    return "\n".join(h)


def trace_table(analysis):
    rows = trace_rows(analysis)
    if not rows:
        return pending("trace analysis.json")
    h = ['<table><thead><tr><th>trace</th><th>kind</th><th>passes</th><th>pass ms</th><th>layers</th><th>Save K us per layer</th><th>Save K ns per row</th><th>Save K share %</th><th>attention ready ms per worker</th><th>attention pending ms per worker</th><th>join ms per worker</th><th>attention total ms per worker</th><th>kernels ms per main helper</th><th>workers busy in Save K</th></tr></thead><tbody>']
    for (a, tp) in sorted(rows, key=lambda k: (k[1], ARMS.index(k[0]) if k[0] in ARMS else 9)):
        r = rows[(a, tp)]
        for kind in ("prefill", "decode"):
            k = r["kinds"].get(kind)
            if not k:
                continue
            h.append(f'<tr><td><span class="sw" style="background:{ARM_COLOR.get(a, "#999")}"></span>{esc(a)} tp{tp}</td><td>{kind}</td><td>{k["n_passes"]}</td><td>{fmt(k["pass_ms"], 2)}</td><td>{fmt(k["n_layers"], 0)}</td>'
                     f'<td>{fmt(k["save_k_us_per_layer"], 1)}</td><td>{fmt(k["save_k_ns_per_row"], 0)}</td><td>{fmt(100 * k["save_k_share"], 2)}</td>'
                     f'<td>{fmt(k["attention_ready_ms_per_worker"], 3)}</td><td>{fmt(k["attention_pending_ms_per_worker"], 3)}</td><td>{fmt(k["attention_join_ms_per_worker"], 3)}</td>'
                     f'<td>{fmt(k["attention_total_ms_per_worker"], 3)}</td><td>{fmt(k["helper_kernel_ms_per_helper"], 3)}</td><td>{fmt(k["workers_busy_in_save_k"], 2)}</td></tr>')
    h.append("</tbody></table>")
    by_tp = {}
    for (a, tp), r in rows.items():
        by_tp.setdefault(tp, []).append((a, r["threads"]))
    lines = []
    for tp in sorted(by_tp):
        arms = by_tp[tp]
        counts = {(t["main"], t["attention_workers"], t["main_helpers"]) for _, t in arms}
        if len(counts) == 1:
            m, w, hh = next(iter(counts))
            lines.append(f"Every tp{tp} trace: main {m}, attention workers {w}, main helpers {hh}.")
        else:
            for a, t in sorted(arms, key=lambda kv: ARMS.index(kv[0]) if kv[0] in ARMS else 9):
                lines.append(f'{esc(a)} tp{tp}: main {t["main"]}, attention workers {t["attention_workers"]}, main helpers {t["main_helpers"]}.')
    h.append('<p class="small">Threads per trace.<br>' + "<br>".join(lines) + "</p>")
    return "\n".join(h)


def smoke_block():
    txt = read(f"{RES}/smoke/smoke.txt")
    if not txt:
        return pending("smoke/smoke.txt")
    cmp_lines = [l for l in txt.splitlines() if " vs " in l and ("identical" in l or "first difference" in l or "missing" in l)]
    runs = [l for l in txt.splitlines() if l.startswith("smoke ")]
    lead = ("Each line below compares the 128 generated token ids of two smoke runs, position by position. "
            "A token id is the integer number of one entry of the model vocabulary. Ids are labels: the gap between two ids has no meaning. "
            "'identical for 128 tokens (lengths 128 / 128)' means every id matches, and each run produced 128 ids. "
            "'first difference at generated token N of 128 (A vs B); agreeing prefix N tokens' means the two runs agree on the first N ids (positions 0 to N-1, the count starts at 0) and differ at position N: id A in the first-named run, id B in the second. "
            "'missing' means one of the two runs was not made. "
            "The bracket at the end of each line names what the pair controls for. It is not a source reference.")
    h = [f"<p>{esc(lead)}</p>", "<ul>"] + [f"<li>{esc(l)}</li>" for l in cmp_lines] + ["</ul>"]
    if runs:
        h.append('<details><summary>smoke run lines (version, TTFT, TPS of the 1-user runs)</summary><pre>' + esc("\n".join(runs)) + "</pre></details>")
    return "\n".join(h)


def builds_block():
    files = sorted(glob.glob(f"{RES}/build-*.txt"))
    vnnik5 = read(f"{EXEC}/results/vnnik5-20260916/build.txt")
    h = []
    if not files:
        h.append(pending("build-main0916.txt / build-headoff0916.txt"))
    for f in files:
        h.append(f"<pre>{esc(read(f).strip())}</pre>")
    if vnnik5:
        h.append("<p>The vnni binary is runtron.vnnik5, built 2026-09-16 00:09 UTC. Its build record below names the checked-out commit (the tip) d5b59b1101. The worktree was then moved to 65a1c41d72, a change to one test file. Only libversion.so was relinked. So the runtron file is byte-identical to the d5b59b1101 build (same sha256). Commit ff680c8020, the PR head, adds one JSON row of cost data on top of 65a1c41d72 and no C++.</p>")
        h.append(f"<pre>{esc(vnnik5.strip())}</pre>")
    hdr = [l for l in read(f"{RES}/rt-results.txt").splitlines() if l.startswith("#") or l.startswith("version ") or re.match(r"^[0-9a-f]{64} ", l)]
    if hdr:
        h.append("<details><summary>rt-results.txt header (binaries, placements, sha256, version strings)</summary><pre>" + esc("\n".join(hdr[:20])) + "</pre></details>")
    return "\n".join(h)


def machine_block():
    txt = read(f"{RES}/rt-results.txt")
    heads = [l for l in txt.splitlines() if l.startswith("### runtron")]
    if not heads:
        return pending("rt-results.txt")
    first, last = heads[0], heads[-1]
    t0 = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", first)
    t1 = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", last)
    loads = [float(m[1]) for l in heads for m in [re.search(r"load=([0-9.]+)", l)] if m]
    bills = [int(m[1]) for l in heads for m in [re.search(r"bill_procs=(\d+)", l)] if m]
    markers = {m[1] for l in heads for m in [re.search(r"marker=(\w+)", l)] if m}
    return (f"<p>{len(heads)} runs from {esc(t0[1] if t0 else '?')} to {esc(t1[1] if t1 else '?')}. 1-minute load average at run start (the number of runnable processes averaged over one minute, roughly the number of busy cores): min {fmt(min(loads), 1) if loads else '-'}, "
            f"median {fmt(statistics.median(loads), 1) if loads else '-'}, max {fmt(max(loads), 1) if loads else '-'} runnable processes. For comparison, one run of ours uses about 30 to 60 cores. "
            f"Processes of the other user of delphi-3bda (the colleague who holds the first half of the machine, see section 9) at run start: max {max(bills) if bills else '-'}. A value of 0 means the other user ran nothing when a run started. "
            f"Marker file /bill-has-instance-0,2 (its presence means the other user holds the first half of the machine, see section 9): {esc(', '.join(sorted(markers)) or '?')}.</p>")


BUILD_MARK = {"base": read(f"{RES}/build-main0916.done").strip(), "headoff": read(f"{RES}/build-headoff0916.done").strip()}


def build_failed(arm):
    m = BUILD_MARK.get(arm, "")
    return bool(m) and m != "ok"


# the reference binary of the comparison: base, or headoff when the base build failed
REF = "headoff" if build_failed("base") and not build_failed("headoff") else "base"


def short_version(summary, analysis):
    cells = cells_of(summary)
    b, v, ho = cells.get((2, 1024, REF)), cells.get((2, 1024, "vnni")), cells.get((2, 1024, "headoff"))
    pr = paired_of(summary, 2, 1024, "vnni", REF)
    prh = paired_of(summary, 2, 1024, "headoff", "base")
    if not (b and v):
        return "<p><b>Short version.</b> The campaign has not produced the tp2 prompt-1024 cell yet. This page regenerates itself from the result files. The sentences below fill in when the cell exists.</p>"
    if b["tps_mean"] is None or v["tps_mean"] is None:
        no_mean = ", ".join(a for a, c in ((REF, b), ("vnni", v)) if c["tps_mean"] is None)
        return f"<p><b>Short version.</b> Every repetition of the tp2 prompt-1024 cell of {esc(no_mean)} was an early-stop run (one request left the batch early). No TPS mean exists for that cell. Sections 4.3 and 4.4 list the runs.</p>"
    pct = 100 * (v["tps_mean"] / b["tps_mean"] - 1)
    tt = 1000 * (v["ttft_mean"] - b["ttft_mean"])
    t = pr["tps"]["t"] if pr and pr["tps"] and pr["tps"]["t"] is not None else None
    ref_name = "base (main)" if REF == "base" else "headoff (the PR head with the layout off)"
    n_txt = f"{pr['tps']['n']} paired repetitions" if pr and pr.get("tps") else f"{v['n']} repetitions"
    # The bolded Short version holds exactly three sentences (s1, s3, s4) in every branch. The
    # TTFT facts follow in a second, unbolded paragraph.
    if t is not None and t < -2:
        s1 = f"The {n_txt} at tp2 prompt 1024 confirm the decode loss of the VNNI layout for qwen-3-30b-a3b (kv_mul 8) against {ref_name}: {v['tps_mean']:.1f} against {b['tps_mean']:.1f} TPS per user ({pct:+.1f}%, paired t {t:+.1f})."
    elif t is not None and t > 2:
        s1 = f"The {n_txt} at tp2 prompt 1024 show the VNNI layout faster, not slower, for qwen-3-30b-a3b against {ref_name}: {v['tps_mean']:.1f} against {b['tps_mean']:.1f} TPS per user ({pct:+.1f}%, paired t {t:+.1f}), and the one-run loss of 2026-09-15 did not repeat."
    else:
        s1 = f"The {n_txt} at tp2 prompt 1024 do not resolve a decode difference for qwen-3-30b-a3b between the vnni binary and {ref_name}: {v['tps_mean']:.1f} against {b['tps_mean']:.1f} TPS per user ({pct:+.1f}%, paired t {t:+.1f})."
    tt_txt = f"{tt:+.0f} ms ({100 * (v['ttft_mean'] / b['ttft_mean'] - 1):+.1f}%, lower is better)"
    if REF == "headoff":
        s3 = f"The base binary was not built (marker: {BUILD_MARK['base']}, log exec/logs/vnnik6-build-main0916.log), and the comparison above is against the PR head with the layout off instead of the pre-registered vnni-vs-main rule of PLAN.md section 6."
    elif build_failed("headoff"):
        s3 = f"The headoff binary was not built (marker: {BUILD_MARK['headoff']}, log exec/logs/vnnik6-build-headoff0916.log), and the question whether a kv_mul gate gives main's numbers back stays open."
    elif ho and prh and prh["tps"] and prh["tps"]["t"] is not None and ho["tps_mean"] is not None:
        th = prh["tps"]["t"]
        same = abs(th) < 2
        speed = "main's speed" if same else "a speed different from main"
        verdict = "the same as base within the run-to-run spread" if same else "not the same as base"
        if t < -2:
            s3 = (f"The PR head with the layout compiled off runs at {speed} ({ho['tps_mean']:.1f} TPS per user, {verdict}, paired t {th:+.1f}), and a kv_mul gate would {'give' if same else 'not fully give'} main's numbers back for this model.")
        else:
            s3 = (f"The PR head with the layout compiled off runs at {speed} ({ho['tps_mean']:.1f} TPS per user, {verdict}, paired t {th:+.1f}), and no gate is needed based on these numbers.")
    else:
        s3 = "The headoff binary's cell is pending."
    # the other cells, in one sentence: the loss end first, then the gain end
    gains, losses = [], []
    for tp, p in ((2, 2048), (2, 8192), (4, 8192), (4, 1024)):
        q = paired_of(summary, tp, p, "vnni", REF)
        d = delta_of(summary, tp, p, "vnni", REF)
        if q and q.get("tps") and q["tps"]["t"] is not None and d:
            item = (d["tps_delta_pct"], f"{d['tps_delta_pct']:+.1f}% ({cell_name(tp, p)}, t {q['tps']['t']:+.1f})")
            if q["tps"]["t"] > 2:
                gains.append(item)
            elif q["tps"]["t"] < -2:
                losses.append(item)

    def join_and(items, one, many):
        txt = [s for _, s in sorted(items)]
        return (one if len(txt) == 1 else many) + (txt[0] if len(txt) == 1 else ", ".join(txt[:-1]) + " and " + txt[-1])

    s4 = ""
    if gains and losses:
        s4 = "In the other cells the decode effect ranges from " + join_and(losses, "a loss of ", "losses of ") + " to " + join_and(gains, "a gain of ", "gains of ") + "."
    elif gains:
        s4 = "In the other cells the decode effect is " + join_and(gains, "a gain of ", "gains of ") + "."
    elif losses:
        s4 = "In the other cells the decode effect is " + join_and(losses, "a loss of ", "losses of ") + "."
    # the TTFT paragraph: the every-cell claim is made only when the data hold it
    ttft_deltas = [delta_of(summary, tp, p, "vnni", REF) for tp, p in CELL_ORDER]
    ttft_deltas = [d for d in ttft_deltas if d and d.get("ttft_delta_ms") is not None]
    if ttft_deltas and all(d["ttft_delta_ms"] < 0 for d in ttft_deltas):
        s_ttft = f"TTFT is lower in every cell. At tp2 prompt 1024 it moves by {tt_txt}."
    else:
        s_ttft = f"TTFT at tp2 prompt 1024 moves by {tt_txt}."
    short = " ".join(esc(s) for s in (s1, s3, s4) if s)
    return f"<p><b>Short version.</b> {short}</p><p>{esc(s_ttft)}</p>"


def recommendation(summary, analysis):
    """Automatic recommendation from the decision rule (PLAN.md section 6), the prompt-length trend
    and the trace attribution. The hand-written fragment, when present, follows it."""
    cells = cells_of(summary)
    pr = paired_of(summary, 2, 1024, "vnni", REF)
    prh = paired_of(summary, 2, 1024, "headoff", "base")
    t = pr["tps"]["t"] if pr and pr.get("tps") and pr["tps"]["t"] is not None else None
    th = prh["tps"]["t"] if prh and prh.get("tps") and prh["tps"]["t"] is not None else None
    if t is None:
        return pending("the tp2 prompt-1024 paired result (the recommendation is derived from it)")
    out = []
    # attribution from the prompt-length trend (ms per generated token, vnni minus REF)
    dd = {}
    for p in (1024, 2048, 8192):
        b, v = cells.get((2, p, REF)), cells.get((2, p, "vnni"))
        if b and v and b["tps_mean"] and v["tps_mean"]:
            dd[p] = 1000 / v["tps_mean"] - 1000 / b["tps_mean"]
    trend = None
    if 1024 in dd and 8192 in dd:
        pts = sorted(dd.items())
        rising = all(pts[i + 1][1] > pts[i][1] for i in range(len(pts) - 1)) and (dd[8192] - dd[1024]) > 0.5
        if rising:
            trend = "rising"
        elif abs(dd[8192] - dd[1024]) <= 0.5:
            trend = "flat"
        else:
            trend = "mixed"
    # attribution from the traces (decode, tp2)
    rows = trace_rows(analysis)
    store_txt = ""
    if (REF, 2) in rows and ("vnni", 2) in rows and rows[(REF, 2)]["kinds"].get("decode") and rows[("vnni", 2)]["kinds"].get("decode"):
        kb, kv = rows[(REF, 2)]["kinds"]["decode"], rows[("vnni", 2)]["kinds"]["decode"]
        d_store = kv["save_k_ms"] - kb["save_k_ms"]
        d_attn = kv["attention_total_ms_per_worker"] - kb["attention_total_ms_per_worker"]
        d_pass = kv["pass_ms"] - kb["pass_ms"]
        store_txt = (f" In the tp2 traces the decode step of vnni is {d_pass:+.2f} ms against {REF} ({kv['pass_ms']:.2f} against {kb['pass_ms']:.2f} ms). There is one traced run per binary. So this difference is within the run-to-run spread. "
                     f"Inside the step, two effects have opposite signs. The Save K span on the main thread costs {d_store:+.3f} ms more per step ({kv['save_k_ms']:.3f} against {kb['save_k_ms']:.3f} ms, {kv['save_k_us_per_layer']:.1f} against {kb['save_k_us_per_layer']:.1f} us per layer). That is the per-token scatter store. "
                     f"The attention workers' time per worker moves by {d_attn:+.3f} ms per step ({kv['attention_total_ms_per_worker']:.3f} against {kb['attention_total_ms_per_worker']:.3f} ms). That is the reader against the dotter.")
        pb, pv = rows[(REF, 2)]["kinds"].get("prefill"), rows[("vnni", 2)]["kinds"].get("prefill")
        if pb and pv:
            store_txt += (f" In prefill (8 passes of 128 tokens x 8 users), the Save K span per layer falls from {pb['save_k_us_per_layer']:.1f} to {pv['save_k_us_per_layer']:.1f} us (the shared block save). "
                          f"The attention workers' time per worker per pass falls from {pb['attention_total_ms_per_worker']:.1f} to {pv['attention_total_ms_per_worker']:.1f} ms. "
                          f"The pass itself goes from {pb['pass_ms']:.1f} to {pv['pass_ms']:.1f} ms ({pv['pass_ms'] - pb['pass_ms']:+.1f} ms per pass, {8 * (pv['pass_ms'] - pb['pass_ms']):+.0f} ms over the 8 prefill passes). That is the TTFT gain.")
    if t < -2:
        out.append(f"The decode loss is confirmed by the pre-registered rule (paired t {t:+.1f} at tp2 prompt 1024, section 4.4).")
        if trend == "flat":
            out.append(f"The loss in ms per generated token is flat over the prompt length ({dd[1024]:+.2f} ms at prompt 1024, {dd[8192]:+.2f} ms at 8192). A flat cost is a per-token cost. That points at the decode K store, not at the reader.")
        elif trend == "rising":
            out.append(f"The loss in ms per generated token grows with the prompt length ({dd[1024]:+.2f} ms at prompt 1024, {dd[8192]:+.2f} ms at 8192). A cost that grows with the number of pages is a reader cost.")
        elif trend == "mixed":
            out.append(f"The loss in ms per generated token changes with the prompt length without a clean pattern ({', '.join(f'{d:+.2f} ms at {p}' for p, d in sorted(dd.items()))}). Both the store and the reader may contribute.")
        if store_txt:
            out.append(store_txt.strip())
        if th is not None and abs(th) < 2:
            out.append(f"The PR head with the layout compiled off runs at main's speed for this model (paired t {th:+.1f}). So remedy (a), a gate that keeps kv_mul 8 models on row-major K, gives main's numbers back for qwen-3-30b-a3b by construction.")
            out.append("Recommendation: apply remedy (a) before merging, as one of the two plumbing ways of section 6.2 (a kv_geometry field, or a template argument on the cache layout). The reader work of remedy (b) is not needed for this model once the gate is in. It stays an option for the partial pages of kv_mul 4 models.")
        elif th is not None:
            out.append(f"The PR head with the layout compiled off does not run at main's speed for this model (paired t {th:+.1f}). So a gate alone would not give main's numbers back, and the PR's row-major path itself needs a look before the gate decision.")
        else:
            out.append("Whether a gate gives main's numbers back is not established here (no headoff comparison).")
    elif t > 2:
        out.append(f"The VNNI layout is faster for this model at tp2 prompt 1024 (paired t {t:+.1f}, section 4.4). The one-run loss of 2026-09-15 did not repeat under interleaved repetitions against the exact merge base.")
        if store_txt:
            out.append(store_txt.strip())
        out.append("Recommendation: no gate change for kv_mul 8. Close the open item with these numbers, and keep the kv_mul 8 cell in the PR's measurement table.")
    else:
        out.append(f"The repetitions do not resolve a decode difference at tp2 prompt 1024 (paired t {t:+.1f}, section 4.4). The one-run -5.4% decode TPS per user of 2026-09-15 (34.3 against 36.3 TPS, section 2) did not repeat under interleaved repetitions against the exact merge base.")
        if store_txt:
            out.append(store_txt.strip())
            out.append("Recommendation: no gate change for kv_mul 8. Close the open item with these numbers. Write these five points into the PR:")
            pr_points = [
                "For a model without an AMX gain, the layout trades the per-token scatter store (the Save K numbers above) against a faster software reader.",
                "At prompt 1024 the two cancel in decode.",
                "At prompt 8192 the reader's gain dominates: the decode step falls by a fifth (section 5.3).",
                "The block save and the reader together lower TTFT at every prompt length, by 7% to 16%.",
                "The prompt-2048 cell is the one exception. It shows a resolved decode loss of 4.1%. Section 5.4 gives its traces and the open hypothesis.",
            ]
        else:
            out.append("Recommendation: no gate change for kv_mul 8 based on the decode numbers. Close the open item with these numbers.")
    other = []
    for tp, p in ((4, 1024), (2, 2048), (2, 8192), (4, 8192)):
        q = paired_of(summary, tp, p, "vnni", REF)
        if q and q.get("tps") and q["tps"]["t"] is not None:
            other.append(f"{cell_name(tp, p)}: {q['tps']['mean']:+.2f} TPS (t {q['tps']['t']:+.1f})")
    html_out = "<p>" + "</p><p>".join(esc(x) for x in out) + "</p>"
    if "pr_points" in locals():
        html_out += "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in pr_points) + "</ul>"
    if other:
        html_out += "<p>The other cells, vnni minus " + esc(REF) + " in TPS per user, with the paired t:</p><ul>" + "".join(f"<li>{esc(x)}</li>" for x in other) + "</ul>"
    return html_out


def trace_reading(analysis, prompt, n_prefill_passes):
    """One paragraph per extra trace set: decode step, attention per worker, Save K, prefill pass."""
    rows = trace_rows(analysis)
    if not ((REF, 2) in rows and ("vnni", 2) in rows):
        return pending(f"trace analysis at prompt {prompt}")
    kb, kv = rows[(REF, 2)]["kinds"].get("decode"), rows[("vnni", 2)]["kinds"].get("decode")
    pb, pv = rows[(REF, 2)]["kinds"].get("prefill"), rows[("vnni", 2)]["kinds"].get("prefill")
    if not (kb and kv and pb and pv):
        return pending(f"trace analysis at prompt {prompt} (decode or prefill passes missing)")
    d_pass, d_attn, d_store = kv["pass_ms"] - kb["pass_ms"], kv["attention_total_ms_per_worker"] - kb["attention_total_ms_per_worker"], kv["save_k_ms"] - kb["save_k_ms"]
    d_help = kv["helper_kernel_ms_per_helper"] - kb["helper_kernel_ms_per_helper"]
    out = [f"Decode step (mean over {kv['n_passes']} traced steps): {kb['pass_ms']:.2f} ms for {REF}, {kv['pass_ms']:.2f} ms for vnni ({d_pass:+.2f} ms per generated token).",
           f"The attention workers' time per worker per step: {kb['attention_total_ms_per_worker']:.2f} against {kv['attention_total_ms_per_worker']:.2f} ms ({d_attn:+.2f} ms, {100 * d_attn / kb['attention_total_ms_per_worker']:+.0f}%). That is the reader against the dotter.",
           f"The Save K span on the main thread per step: {kb['save_k_ms']:.3f} against {kv['save_k_ms']:.3f} ms ({d_store:+.3f} ms). That is the per-token scatter store.",
           f"The kernels on the main helpers per step: {kb['helper_kernel_ms_per_helper']:.2f} against {kv['helper_kernel_ms_per_helper']:.2f} ms ({d_help:+.2f} ms). The layout does not touch them, so this is the step-to-step spread.",
           f"Prefill pass ({n_prefill_passes} passes of 1024 token jobs): {pb['pass_ms']:.1f} against {pv['pass_ms']:.1f} ms ({pv['pass_ms'] - pb['pass_ms']:+.1f} ms per pass, {n_prefill_passes * (pv['pass_ms'] - pb['pass_ms']) / 1000:+.2f} s over the {n_prefill_passes} passes). Save K per layer falls from {pb['save_k_us_per_layer']:.1f} to {pv['save_k_us_per_layer']:.1f} us. The attention workers' time per worker per pass falls from {pb['attention_total_ms_per_worker']:.1f} to {pv['attention_total_ms_per_worker']:.1f} ms."]
    unexplained = d_pass - d_store
    if prompt == 2048:
        out.append(f"Reading: the reader is still faster per worker ({d_attn:+.2f} ms) and the store still costs {d_store:+.2f} ms on the main thread, yet the step is {d_pass:+.2f} ms slower. The two spans account for {d_store + d_attn:+.2f} ms of it. The rest ({unexplained - d_attn:+.2f} ms) is not in any measured span. Hypothesis, not measured: at this prompt length the attention phase ({kb['attention_total_ms_per_worker']:.1f} ms per worker) and the expert kernels ({kb['helper_kernel_ms_per_helper']:.1f} ms per helper) take about the same time, so the serial store on the main thread lands on the critical path while the workers' gain does not shorten it. The measurement that decides it: wall-clock lanes of one decode step (every thread's spans against time, the lanes.py recipe of the 2026-09-14 trace analysis).")
    elif prompt == 8192:
        out.append(f"Reading: at this prompt length attention takes most of the step ({kb['attention_total_ms_per_worker']:.1f} of {kb['pass_ms']:.1f} ms per worker for {REF}), so the reader's gain per worker ({d_attn:+.2f} ms) sets the step. The store ({d_store:+.2f} ms) is small against it. The traced step difference ({d_pass:+.2f} ms) matches the cells of section 4 (1000 / TPS: {1000 / cells_of(jload(f'{RES}/summary.json')).get((2, 8192, REF), {'tps_mean': float('nan')})['tps_mean']:.2f} against {1000 / cells_of(jload(f'{RES}/summary.json')).get((2, 8192, 'vnni'), {'tps_mean': float('nan')})['tps_mean']:.2f} ms per token).")
    return "<p>" + "</p><p>".join(esc(x) for x in out) + "</p>"


def oldbase_block():
    """The extra cell: the PR's old base binary (544ca05c7a) against main (c7844ca2ce), same cell."""
    sm = jload(f"{EXEC}/results/vnnik6-oldbase-20260916/summary.json")
    if not sm or not sm.get("cells"):
        return pending("the extra cell old base (544ca05c7a) vs main (exec/results/vnnik6-oldbase-20260916)")
    cells = {(c["arm"]): c for c in sm["cells"] if c["tp"] == 2 and c["prompt"] == 1024}
    pr = next((p for p in sm.get("paired", []) if p["a"] == "base" and p["b"] == "old"), None)
    h = ['<table><thead><tr><th>binary</th><th>commit</th><th>n</th><th>TPS per user</th><th>sd</th><th>TTFT s</th><th>sd</th></tr></thead><tbody>']
    for arm, label, commit in (("old", "old base = runtron.p0perf13", "544ca05c7a (PR #3879 head, the PR's base on 2026-09-15)"), ("base", "base = runtron.main0916", "c7844ca2ce (main, merge base of the PR)")):
        c = cells.get(arm)
        if c:
            h.append(f"<tr><td>{esc(label)}</td><td>{esc(commit)}</td><td>{c['n']}</td><td>{fmt(c['tps_mean'], 2)}</td><td>{fmt(c['tps_sd'], 2)}</td><td>{fmt(c['ttft_mean'], 3)}</td><td>{fmt(c['ttft_sd'], 3)}</td></tr>")
    h.append("</tbody></table>")
    if pr and pr.get("tps") and pr["tps"]["t"] is not None:
        pt, pf = pr["tps"], pr["ttft_s"]
        verdict = "main is slower than the old base for this model" if pt["t"] < -2 else ("main is faster than the old base" if pt["t"] > 2 else "no speed difference resolved between main and the old base")
        h.append(f"<p>Paired (main minus old base, tp2 prompt 1024): TPS {pt['mean']:+.2f} per user (sd {pt['sd']:.2f}, n {pt['n']}, t {pt['t']:+.1f}); TTFT {1000 * pf['mean']:+.0f} ms (sd {1000 * pf['sd']:.0f}, t {fmt(pf['t'], 1)}). Reading: {esc(verdict)}.</p>")
    return "\n".join(h)


def fragment(name):
    p = f"{C}/sections/{name}.html"
    t = read(p)
    return t if t.strip() else pending(f"sections/{name}.html (hand-written fragment)")


def main():
    summary = jload(f"{RES}/summary.json")
    analysis = jload(f"{TRES}/analysis.json")
    analysis8192 = jload(f"{EXEC}/results/vnnik6-trace8192-20260916/analysis.json")
    analysis2048 = jload(f"{EXEC}/results/vnnik6-trace2048-20260916/analysis.json")
    words = [
        ("tron, runtron", "tron = the inference program under test. runtron = its command-line tool that runs one model with synthetic prompts."),
        ("PR, PR head", "PR = a GitHub pull request, one proposed change to the tron repository. The PR head = the newest commit on the PR's branch. PR #4424 is the VNNI K change measured here (head ff680c8020). PR #3879 is the merged AMX attention kernel that #4424 builds on."),
        ("K, V, KV, KV head", "K = the key vector and V = the value vector that attention stores for every token in every layer. The KV cache is the memory that holds them. A KV head is one key/value head. Several query heads share it (see kv_mul). A K row is the 128 K values of one token for one KV head."),
        ("VNNI layout", "the pair-interleaved K layout of PR #4424: the two values of one dimension pair sit next to each other, and one 64-byte row holds that pair for 16 tokens. It is the right-hand (B) operand layout of the AMX tile multiply."),
        ("row-major K", "the layout of main (the main branch of the tron git repository, the branch PR #4424 merges into): one row of 128 values per token."),
        ("KV page, page", "a KV page = one 64-token block of the KV cache (kv_cache.hpp struct page, page_size 64). It holds the K and V rows of those tokens for one layer. \"page\" alone in this report means a KV page. page::k, page::set_k_row and similar names are the C++ members of that struct."),
        ("slot", "one persistent K/V storage unit of the cache, selected by a kv_slot_id and described by a kv_slot_spec (kv_cache.hpp:160-176). A row-major slot keeps K in the row-major layout. A VNNI slot keeps it in the VNNI layout."),
        ("bf16", "the 16-bit brain floating-point number format. K and V values are stored as bf16 in the cache."),
        ("AVX-512, gather, scatter", "AVX-512 = the CPU's 512-bit vector instruction set (Advanced Vector Extensions). Tron's software attention path, the dotter and the reader, is AVX-512 code. A gather is one AVX-512 load that collects 16 4-byte values from 16 addresses. A scatter is the matching store to 16 addresses."),
        ("TRON_AMX_DISPATCH, TRON_K_VNNI", "two CMake build options of tron, both OFF by default. TRON_AMX_DISPATCH compiles the AMX software-attention kernels and their dispatch [CMakeLists.txt:48]. TRON_K_VNNI stores the K cache of 128-dimension heads in the VNNI layout and requires TRON_AMX_DISPATCH [CMakeLists.txt:49; src/tron/CMakeLists.txt:209-213]."),
        ("attention workers, ready, pending, join", "the attention workers = the pool threads that run the software attention (the dotter or the reader) over the KV pages of a layer: 20 threads per tp2 process and 40 per tp4 process here (the Threads line under the trace table in section 5.2). The traces record their work as three sections. Pending = the work over the pages written in this pass. It starts after Save K and Save V of the layer. Ready = the work over pages written in earlier passes. Join = the per-KV-head step that adds the workers' partial results. 'attention total' in the trace tables = the three added."),
        ("minibatch, main helpers", "a minibatch = the group of a pass's tokens that the model runs through each layer together (generated plugins run one minibatch per pass). The main helpers = the pool threads that run the main thread's CPU kernels next to it. They are not the attention workers (defined above)."),
        ("worktree, sha256, libversion.so", "a worktree = a git working directory checked out at one commit. Each binary here was built from one. sha256 = the 64-hex-digit checksum of a file. Two files with the same sha256 are byte-identical. libversion.so = the small shared library of tron that holds the version string and git hash. It is relinked when the commit changes and no source changes. So a runtron binary can report a newer commit than the one its code was compiled from."),
        ("the nightly", "the systems_test CI (continuous integration) run that executes on delphi-3bda every night (start about 03:39 UTC). It holds the machine through a lease file. Nothing of ours runs while the lease is busy. systems_test is the repository of those CI tests."),
        ("AMX", "Intel Advanced Matrix Extensions, the tile-multiply instruction set. The AMX attention kernel of main (PR #3879) serves head size 128 with kv_mul 4 only."),
        ("head, query head, KV head, head size", "attention in each layer runs several independent heads. Each head works on a vector of head-size values (128 for this model). A query head computes the attention scores of one token against the stored tokens. A KV head holds the stored K and V rows that the query heads read (see the row K, V, KV, KV head above). Several query heads share one KV head (see kv_mul)."),
        ("kv_mul", "the number of query heads that share one KV head. qwen-3-30b-a3b has 32 query heads and 4 KV heads: kv_mul 8. The AMX kernel is not eligible for it. So all its attention runs on the software (AVX-512) path in every binary here."),
        ("gate, layout gate", "the compile-time condition that decides whether the K cache of a head size is stored in the VNNI layout: the variable template k_vnni::layout_on<head_size> (section 6.1). Today it is true for head size 128 when TRON_K_VNNI is defined. 'Gating the layout on kv_mul 4' (remedy (a)) means adding 'kv_mul is 4' to that condition. A kv_mul 8 model would then keep row-major K."),
        ("the dotter, the reader", "the dotter = the per-token AVX-512 dot-product loop of main's software attention (row-major K). The reader = k_vnni::qk_group, the AVX-512 routine of PR #4424 that scores the tokens of one page from the VNNI layout."),
        ("Save K", "the store of the K rows of one pass into the KV cache, once per layer, on the main thread (model.hpp save_k). In decode each token's row is one unit and the VNNI layout writes it with scatters into 64 cache lines."),
        ("TPS", "generated tokens per second per user in decode (runtron's \"average tok/s\" per request, averaged over the 8 requests of a run)."),
        ("TTFT", "time to first token: runtron's \"Parsing the prompt took\" time, taken as the maximum over the 8 prompts of a run. The 8 values of one run agree to the millisecond (they differ by less than 1 ms)."),
        ("cell, repetition", "a cell = one (tp, prompt length, binary) combination run with 8 users, 256 generated tokens. A repetition = one run of a cell. The binaries interleave inside each repetition (base, headoff, vnni, base, ...)."),
        ("paired delta, t", "for every repetition present in both binaries, the difference a minus b. The tables report the mean, the sample standard deviation (sd), n, and t = mean / (sd / sqrt(n)). |t| above 2 with 6 repetitions means the mean difference is more than twice its own uncertainty. The pairing removes slow drifts of the machine."),
        ("smoke, A/A", "smoke = a 1-user greedy run (temperature 0, deterministic reductions) of 128 tokens whose token ids are saved. A/A = the same binary run twice. Identical tokens are expected."),
        ("tp2, tp4", "the tensor-parallel width: how many FPGA cards the model is split over. FPGA = field-programmable gate array, the accelerator card that runs the model on delphi-3bda. tp2 uses tron --instance 2,4 (2 cards), tp4 --instance 1,2 (4 cards). Both are on our half of delphi-3bda (socket 1, cards 90/93/b9/bc)."),
        ("pass, decode step", "a pass = one scheduler forward() call. A prefill pass processes a chunk of the prompts; a decode step is one pass that generates one token for each of the 8 users."),
        ("token job", "one token processed in one pass (tron's trace argument n_token_jobs). In these runs a prefill pass carries 1024 token jobs and a decode step carries 8, one per user."),
        ("Perfetto trace", "tron's built-in trace recorder. The traced runs generate 32 tokens and record the passes 1 to 24 with the categories model and scheduler."),
        ("base, headoff, vnni", "the three binaries compared in this report. base = the main branch at commit c7844ca2ce (the merge base of PR #4424) built with TRON_AMX_DISPATCH=ON. headoff = the PR head ff680c8020 built with TRON_AMX_DISPATCH=ON and the layout option TRON_K_VNNI off. vnni = the PR head's code (65a1c41d72, runtron.vnnik5) built with TRON_K_VNNI=ON."),
    ]
    words_html = "<table><thead><tr><th>term</th><th>meaning</th></tr></thead><tbody>" + "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in words) + "</tbody></table>"
    item = ("128-dimension heads with kv_mul other than 4 (measure before merging). For qwen-3-30b-a3b (kv_mul 8) the VNNI layout is on. The AMX kernel is not eligible for that shape. So every page goes through the AVX-512 reader of the layout instead of the row-major dotter. The decode store also scatters into cold lines (64-byte cache lines not yet present in the CPU cache). One run showed -5.4% decode TPS (a loss: 34.3 vs 36.3 TPS/user) and -7% TTFT (a gain of 369 ms; lower TTFT is better) against base. If more repetitions confirm the decode loss, the layout gate k_vnni::layout_on<head_size> should also require the AMX shape (kv_mul 4), or the reader needs work for larger groups (more query heads per KV head).")
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VNNI K and kv_mul 8</title>
<style>
:root {{ color-scheme: light; --ink: {INK}; --ink2: {INK2}; --grid: {GRID}; --surf: {SURF}; --bg: #ffffff; --accent: #2a78d6; }}
body {{ margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--ink); font: 15px/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; max-width: 1100px; margin-left: auto; margin-right: auto; }}
h1 {{ font-size: 24px; margin: 0 0 6px; }} h2 {{ font-size: 19px; margin: 36px 0 8px; border-bottom: 1px solid var(--grid); padding-bottom: 4px; }} h3 {{ font-size: 16px; margin: 22px 0 6px; }}
p, li {{ max-width: 900px; }} .meta {{ color: var(--ink2); font-size: 13px; }}
table {{ border-collapse: collapse; margin: 10px 0 16px; font-size: 13px; }} th, td {{ border: 1px solid var(--grid); padding: 4px 8px; text-align: left; vertical-align: top; }} th {{ background: #f4f3f0; }}
td:nth-child(n+3):not(:last-child) {{ font-variant-numeric: tabular-nums; }}
pre {{ background: #f6f5f2; border: 1px solid var(--grid); padding: 8px 10px; font-size: 12px; overflow-x: auto; }}
.chart {{ max-width: 100%; height: auto; display: block; margin: 8px 0 4px; }}
.pending {{ color: #7a3b00; background: #fff4e5; border: 1px solid #f2c88f; padding: 6px 10px; display: inline-block; border-radius: 4px; }}
.sw {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }}
.small {{ font-size: 13px; color: var(--ink2); }} .quote {{ border-left: 3px solid var(--grid); padding: 4px 12px; color: var(--ink2); }}
details summary {{ cursor: pointer; color: var(--ink2); font-size: 13px; }}
</style></head><body>
<h1>VNNI K layout and a model with kv_mul 8: the repeated measurement</h1>
<p class="meta">Wednesday morning report, generated {esc(NOW)} from exec/results/vnnik6-20260916 and exec/results/vnnik6-trace-20260916 by exec/vnnik6-20260916/gen_report.py. Model ingested-qwen-3-30b-a3b-instruct-2507 (48 layers, 4 KV heads, 32 query heads, head size 128), 8 users, 256 generated tokens, CPU attention (USE_HW_ATTN=0), our half of delphi-3bda (the shared Positron test server: our half = CPU socket 1 and the cards 90/93/b9/bc, listed under tp2, tp4 in section 1).</p>
{short_version(summary, analysis)}

<h2>1. Words used here</h2>
{words_html}

<h2>2. The question</h2>
<p>PR #4424 (VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout) lists this open item:</p>
<p class="quote">{esc(item)}</p>
<p>Two remedies are named. Remedy (a) gates the layout on kv_mul 4. A kv_mul 8 model then keeps row-major K and the dotter. Remedy (b) makes the reader faster for larger groups.</p>
<p>The measurement here decides three things:</p>
<ul>
<li>whether the loss is real (repetitions with a paired test).</li>
<li>whether the PR's code with the layout off already equals main for this model. This is the binary headoff, and it is what remedy (a) would run.</li>
<li>whether the loss comes from the reader (a per-page cost that grows with the prompt length) or from the decode store (a per-token cost that does not).</li>
</ul>
<p>Decision rule, written before the runs (exec/vnnik6-20260916/PLAN.md section 6): the loss is confirmed when the paired t of vnni minus base at tp2 prompt 1024 is below -2 with 6 repetitions. headoff equals base when |t| is below 2.</p>

<h2>3. What was run</h2>
<h3>3.1 Binaries</h3>
<table><thead><tr><th>binary</th><th>commit</th><th>CMake options (preset cross-avx512, BUILD_INGEST_MODELS=ON)</th><th>K layout for this model</th></tr></thead><tbody>
<tr><td><span class="sw" style="background:{ARM_COLOR['base']}"></span>base = runtron.main0916</td><td>c7844ca2ce (origin/main at the rebase of the PR = its merge base)</td><td>TRON_AMX_DISPATCH=ON</td><td>row-major, the dotter</td></tr>
<tr><td><span class="sw" style="background:{ARM_COLOR['headoff']}"></span>headoff = runtron.headoff0916</td><td>ff680c8020 (PR #4424 head)</td><td>TRON_AMX_DISPATCH=ON, TRON_K_VNNI off</td><td>row-major, the dotter (the PR's code otherwise)</td></tr>
<tr><td><span class="sw" style="background:{ARM_COLOR['vnni']}"></span>vnni = runtron.vnnik5</td><td>65a1c41d72 (PR head minus the cost-data JSON commit; same C++)</td><td>TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON</td><td>VNNI layout, the AVX-512 reader on every page</td></tr>
</tbody></table>
<p>AMX-on / AMX-off runs (the same binary run with and without the AMX kernel) were not made. An AMX-off run sets the environment variable TRON_AMX_DISABLE=1, the runtime switch that turns the AMX kernel off for the whole run. The AMX kernel is not eligible for kv_mul 8. So that switch changes nothing for this model.</p>
{builds_block()}
<h3>3.2 Cells and machine</h3>
<table><thead><tr><th>order</th><th>cell</th><th>repetitions per binary</th><th>purpose</th></tr></thead><tbody>
<tr><td>1</td><td>smoke tp2 prompt 1024 (1 user, 128 tokens): base, base2, headoff, vnni, vnni2</td><td>1</td><td>token identity and A/A controls</td></tr>
<tr><td>2</td><td>tp2 prompt 1024</td><td>6</td><td>the reported cell</td></tr>
<tr><td>3</td><td>tp4 prompt 1024</td><td>4</td><td>the store's TTFT cost was most visible at tp4 in the earlier campaign on qwen3-4b (the model of PR #4424's earlier campaigns: 36 layers, 32 query heads, 8 KV heads, head size 128, kv_mul 4)</td></tr>
<tr><td>4</td><td>traces tp2 and tp4 prompt 1024 (32 tokens, passes 1-24)</td><td>1</td><td>attribution</td></tr>
<tr><td>5</td><td>tp2 prompt 2048</td><td>3</td><td>prompt-length trend</td></tr>
<tr><td>6</td><td>tp2 prompt 8192</td><td>3</td><td>prompt-length trend</td></tr>
<tr><td>7</td><td>tp4 prompt 8192</td><td>2</td><td>prompt-length trend at tp4</td></tr>
</tbody></table>
{machine_block()}

<h2>4. Results</h2>
<h3>4.1 Decode throughput (TPS per user)</h3>
{dot_small_multiples(summary, "tps", "Decode TPS per user, per cell", "TPS", 1, False)}
<h3>4.2 Time to first token (TTFT)</h3>
{dot_small_multiples(summary, "ttft", "TTFT in seconds, per cell", "s", 2, True)}
<h3>4.3 The numbers</h3>
{cells_table(summary)}
<h3>4.4 Paired deltas and the decision</h3>
{paired_table(summary)}
<h3>4.5 Smoke tokens</h3>
{smoke_block()}

<h2>5. Attribution: reader or store?</h2>
<h3>5.1 The prompt-length trend</h3>
<p>The decode step of one user takes 1000 / TPS milliseconds. The figure shows that time for vnni minus base. The reader scores every KV page of the context (the prompt plus the tokens generated so far) on every step. So its cost grows with the prompt length. The decode store (Save K in a decode step) writes one K row per token per layer whatever the context length. So its cost is flat over the prompt length.</p>
{trend_svg(summary)}
<h3>5.2 The traces</h3>
<p>One traced run per binary and tp (prompt 1024, 32 tokens). A section is one attention worker's work item over a set of KV pages, recorded as one trace span. Per pass the figures and the table give: the pass time, the attention workers' section time per worker, the Save K time on the main thread, and the kernel time per main helper. Each value is the mean over the traced passes of that kind (prefill or decode).</p>
{trace_bars(analysis, 2)}
{trace_bars(analysis, 4)}
<p>Columns of the trace tables (this one and those of sections 5.3 and 5.4):</p>
<ul>
<li>Save K share % = the Save K time of the pass as a percentage of the pass time.</li>
<li>attention ready = the workers' sections over the pages written in earlier passes, summed and divided by the attention-worker count.</li>
<li>attention pending = the workers' sections over the pages written in this pass, summed and divided by the worker count. A pending section starts after Save K and Save V of the layer.</li>
<li>join = the step that adds the workers' partial results of one KV head into one result, summed and divided by the worker count.</li>
<li>attention total = ready + pending + join, the workers' busy time per pass.</li>
<li>kernels ms per main helper = the per-token kernel spans on the main helper threads, summed and divided by the helper count.</li>
<li>workers busy in Save K = the fraction of attention workers (0 to 1) that had a section overlapping a Save K span, averaged over the Save K spans of the pass. 1.00 = every worker was busy while the store ran, 0 = the store ran with every worker idle.</li>
</ul>
{trace_table(analysis)}
<h3>5.3 The traces at prompt 8192 (tp2, base and vnni)</h3>
<p>These traces were run after the campaign. The prompt-2048 cells showed a decode loss. The prompt-1024 cells did not. The traces were run to find the cause of that difference. Same recipe, prompt 8192, passes 1-90: 64 prefill passes of 1024 token jobs each (64 x 1024 = the 8 prompts of 8192 tokens) and 26 decode steps.</p>
{trace_reading(analysis8192, 8192, 64)}
{trace_bars(analysis8192, 2)}
{trace_table(analysis8192)}
<h3>5.4 The traces at prompt 2048 (tp2, base and vnni)</h3>
<p>Run after the prompt-8192 traces. Same recipe, prompt 2048, passes 1-40: 16 prefill passes of 1024 token jobs each (16 x 1024 = the 8 prompts of 2048 tokens) and 24 decode steps.</p>
{trace_reading(analysis2048, 2048, 16)}
{trace_bars(analysis2048, 2)}
{trace_table(analysis2048)}

<h2>6. What each remedy takes (code analysis)</h2>
{fragment("remedies")}

<h2>7. Recommendation</h2>
{recommendation(summary, analysis)}
{fragment("recommendation") if read(f"{C}/sections/recommendation.html").strip() else ""}
<h3>7.3 Extra cell: the PR's old base against main</h3>
<p>Same cell (tp2, prompt 1024, 8 users), the two base binaries interleaved, run after the campaign. It tests the first hypothesis of section 7.1.</p>
{oldbase_block()}

<h2>8. Raw data for a reviewing agent</h2>
<ul>
<li>Plan and decision rule: exec/vnnik6-20260916/PLAN.md. Scripts: build.sh, chain.sh, campaign.sh, trace.sh, analyze.py, summarize.py, compare_tokens.py, gen_report.py in the same folder.</li>
<li>Runs: exec/results/vnnik6-20260916/rt-results.txt (one "### runtron ..." header per attempt with tp, prompt, arm, rep, binary, tip, machine line; then the Version, placement, TTFT and TPS lines of the run). Full logs: rt/tp&lt;N&gt;__p&lt;prompt&gt;__&lt;arm&gt;__rep&lt;k&gt;.log (the .attempt&lt;i&gt; files keep every attempt).</li>
<li>Derived numbers: summary.json and summary.md (python3 exec/vnnik6-20260916/summarize.py exec/results/vnnik6-20260916). TPS = mean of the 8 "average tok/s" values of a run; TTFT = max of the 8 "Parsing the prompt took" values; cell mean and sample sd over repetitions; paired deltas by repetition number.</li>
<li>Smoke: exec/results/vnnik6-20260916/smoke/&lt;arm&gt;.tokens and smoke.txt (compare_tokens.py output appended).</li>
<li>Builds: exec/results/vnnik6-20260916/build-main0916.txt, build-headoff0916.txt (tip, options, sha256, version string); exec/results/vnnik5-20260916/build.txt for the vnni binary; logs exec/logs/vnnik6-build-*.log.</li>
<li>Traces: exec/results/vnnik6-trace-20260916/&lt;arm&gt;-tp&lt;N&gt;.perfetto-trace, runs.txt, analysis.json, analysis.md (python3 exec/vnnik6-20260916/analyze.py exec/results/vnnik6-trace-20260916 4; the second argument is the KV-head count).</li>
<li>Campaign log and markers: exec/logs/vnnik6-chain.log, vnnik6-20260916.log, .status, .done; vnnik6-trace-20260916.log.</li>
<li>The one-run cell of 2026-09-15 that raised the item: exec/results/vnnik4-models-20260915/results.txt (cell=qwen30b, base 544ca05c7a vs dc950be5f2).</li>
</ul>

<h2>9. Notes and traps</h2>
{fragment("notes")}
</body></html>
"""
    if not all(ord(ch) < 128 for ch in page):
        bad = sorted({ch for ch in page if ord(ch) >= 128})
        raise SystemExit(f"non-ASCII characters in the page: {bad!r}")
    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
