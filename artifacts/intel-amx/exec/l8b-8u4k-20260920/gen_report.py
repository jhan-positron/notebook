#!/usr/bin/env python3
"""Report of the l8b-8u4k campaign (plan CI-test/status/llama-3.1-8b-8u-4k-plan.md, section 9):
CI-test/status/llama-3.1-8b-8u-4k.html.

Copied from exec/l8b-levers-20260919/gen_report.py (the Saturday report) and adapted to one cell plus the three Saturday
reference cells that analyze.py copies into summary.json["reference"] (never retyped). Reads summary.json (analyze.py) and
the pass records perf.json under the results directory, writes one light-theme HTML page with inline SVG charts (pure
ASCII output: the artifact publisher mangles non-ASCII bytes). Every number on the page comes from those files.
usage: gen_report.py [RESULTS_DIR] [OUT_HTML]
"""
import glob
import html
import json
import math
import os
import re
import sys
import time

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/l8b-8u4k-20260920"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/CI-test/status/llama-3.1-8b-8u-4k.html"
CELL = "llama_3_1_8b_instruct_good_tp2_32u_p4096"
GEN_TOKENS = 1536
WINDOW_MID = (896 + 1024) // 2   # generated tokens at the middle of the TPS window
USERS_PER_ENGINE = {4: 1, 8: 2, 16: 4, 32: 8}
SAT_OVERHEAD = 34   # tokens the server counted around a prompt below 4096 on Saturday (measured; the 4096 cells are clipped to 4096)

# reference palette (dataviz skill, light mode; the page is single-theme light by jhan's rule)
C_BLUE, C_BLUE_LIGHT, C_ORANGE, C_AQUA = "#2a78d6", "#86b6ef", "#eb6834", "#1baf7a"
C_INK, C_INK2, C_MUTED, C_GRID, C_AXIS, C_SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
C_BAND = "#fbe9df"


def esc(x):
    return html.escape(str(x), quote=True)


def fmt(x, nd=2, unit=""):
    if x is None:
        return "n/a"
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return "inf" if x > 0 else "-inf"
    return f"{x:.{nd}f}{unit}"


def sfmt(x, nd=2):
    return "n/a" if x is None else f"{x:+.{nd}f}"


def wrap(text, width=105):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def svg_text_lines(x, y, lines, size, fill, weight="400", lh=15):
    return "\n".join(f'<text x="{x}" y="{y + i * lh}" font-size="{size}" font-weight="{weight}" fill="{fill}">{esc(l)}</text>' for i, l in enumerate(lines))


def parse_name(n):
    u = int(re.search(r"_(\d+)u_", n).group(1))
    p = int(re.search(r"_p(\d+)$", n).group(1))
    return u, p


def label(n):
    u, p = parse_name(n)
    return f"{USERS_PER_ENGINE[u]} user{'s' if USERS_PER_ENGINE[u] > 1 else ''} per engine, prompt {p}"


def kv_tokens(n, overhead):
    u, p = parse_name(n)
    ovh = 0 if p >= 4096 else (overhead if overhead is not None else SAT_OVERHEAD)   # prompts of 4096 are clipped to 4096 by the tokenizer
    return USERS_PER_ENGINE[u] * (p + ovh + WINDOW_MID)


def load():
    summary = json.load(open(os.path.join(RES, "summary.json")))
    passes = {}
    for path in sorted(glob.glob(os.path.join(RES, "*-pass[0-9]", "perf.json"))):
        tag = os.path.basename(os.path.dirname(path))
        try:
            passes[tag] = json.load(open(path))
        except Exception:
            pass
    outcome = open(os.path.join(RES, "outcome.txt")).read().strip() if os.path.isfile(os.path.join(RES, "outcome.txt")) else "outcome.txt missing (campaign still running or aborted before its end)"
    hist = open(os.path.join(RES, "status-history.log")).read().splitlines() if os.path.isfile(os.path.join(RES, "status-history.log")) else []
    prompt_check = None
    pc = os.path.join(RES, "prompt-check", "run1.json")
    if os.path.isfile(pc):
        prompt_check = json.load(open(pc))
    compare = open(os.path.join(RES, "prompt-check", "compare.log")).read() if os.path.isfile(os.path.join(RES, "prompt-check", "compare.log")) else ""
    base_identity = open(os.path.join(RES, "base-identity.txt")).read().split() if os.path.isfile(os.path.join(RES, "base-identity.txt")) else []
    return summary, passes, outcome, hist, prompt_check, compare, base_identity


def observed_overhead(summary):
    """Server-counted prompt tokens minus prompt_length for the cell (expected 0 here: the tokenizer clips at 4096)."""
    vals = []
    for n, e in summary["configs"].items():
        _, p = parse_name(n)
        for pv in e.get("per_pass", {}).values():
            if pv.get("prompt_tokens_mean"):
                vals.append(pv["prompt_tokens_mean"] - p)
    return (sum(vals) / len(vals)) if vals else None


def rows_all(summary):
    """[(name, entry, is_reference)] for the cell (if paired) and the three reference cells."""
    out = []
    e = summary["configs"].get(CELL)
    if e and e.get("n_pairs"):
        out.append((CELL, e, False))
    for n, r in summary.get("reference", {}).get("cells", {}).items():
        out.append((n, r, True))
    return out


# ---------------------------------------------------------------- charts
def chart_dumbbell(summary):
    rows = rows_all(summary)
    rows.sort(key=lambda t: kv_tokens(t[0], SAT_OVERHEAD))
    if not rows:
        return "<p>No paired pass yet.</p>"
    W, left, right, rowh, top = 960, 330, 210, 50, 100
    Hh = top + rowh * len(rows) + 50
    xmax = max(max(e["base_tps_mean"], e["canon_tps_mean"]) for _, e, _ in rows) * 1.06
    def X(v):
        return left + v / xmax * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="Decode TPS: nightly deb against canonical AMX deb, the new cell and the Saturday reference cells" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(svg_text_lines(20, 22, ["Decode TPS per cell: nightly deb (light dot) against canonical-AMX deb (dark dot)"], 15, C_INK, "600", 18))
    out.append(svg_text_lines(20, 44, wrap("Mean of 3 passes. Rows sorted by KV tokens per engine step. The label on each row is the gain of the AMX deb in percent; n.r. = not resolved by the pre-registered rule. Rows marked Saturday are the 2026-09-19 reference cells (same arms, driver and layout).", 130), 12, C_INK2, "400", 15))
    out.append(f'<circle cx="26" cy="{top - 16}" r="5" fill="{C_BLUE_LIGHT}"/><text x="36" y="{top - 12}" font-size="11" fill="{C_INK2}">nightly deb (no AMX code)</text>')
    out.append(f'<circle cx="216" cy="{top - 16}" r="5" fill="{C_BLUE}"/><text x="226" y="{top - 12}" font-size="11" fill="{C_INK2}">canonical-AMX deb</text>')
    step = 20 if xmax > 100 else 10
    v = 0
    while v <= xmax:
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{Hh - 40}" stroke="{C_GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{Hh - 24}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{v}</text>')
        v += step
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 6}" font-size="11" fill="{C_MUTED}" text-anchor="middle">tokens per second per user (TPS), mean of the users of a cell</text>')
    for i, (n, e, is_ref) in enumerate(rows):
        y = top + rowh * i + rowh / 2
        b, c = e["base_tps_mean"], e["canon_tps_mean"]
        xb, xc = X(b), X(c)
        lab = label(n) + (" (Saturday)" if is_ref else " (this run)")
        out.append(f'<text x="{left - 12}" y="{y + 4}" font-size="12" font-weight="{"400" if is_ref else "600"}" fill="{C_INK}" text-anchor="end">{esc(lab)}</text>')
        out.append(f'<text x="{left - 12}" y="{y + 17}" font-size="10" fill="{C_MUTED}" text-anchor="end">{kv_tokens(n, SAT_OVERHEAD) / 1000:.1f}K KV tokens per step</text>')
        out.append(f'<line x1="{xb:.1f}" y1="{y:.1f}" x2="{xc:.1f}" y2="{y:.1f}" stroke="{C_BLUE_LIGHT}" stroke-width="3"/>')
        title = f"{lab}: nightly {b:.2f} TPS, canonical AMX {c:.2f} TPS, gain {e['gain_pct']:+.2f} %, paired t {fmt(e['paired_t'])}, {'resolved' if e['resolved'] else 'not resolved'}"
        out.append(f'<circle cx="{xb:.1f}" cy="{y:.1f}" r="7" fill="{C_BLUE_LIGHT}" stroke="{C_SURF}" stroke-width="2"><title>{esc(title)}</title></circle>')
        out.append(f'<circle cx="{xc:.1f}" cy="{y:.1f}" r="7" fill="{C_BLUE}" stroke="{C_SURF}" stroke-width="2"><title>{esc(title)}</title></circle>')
        gain = f"{e['gain_pct']:+.1f} %" + ("" if e["resolved"] else " n.r.")
        if abs(xc - xb) < 44:
            out.append(f'<text x="{max(xb, xc) + 12:.1f}" y="{y + 4}" font-size="12" fill="{C_INK}">{b:.1f} to {c:.1f}, {gain}</text>')
        else:
            lo, hi = (xb, xc) if xb < xc else (xc, xb)
            lo_v, hi_v = (b, c) if xb < xc else (c, b)
            out.append(f'<text x="{lo - 11:.1f}" y="{y + 4}" font-size="11" fill="{C_INK2}" text-anchor="end">{lo_v:.1f}</text>')
            out.append(f'<text x="{hi + 11:.1f}" y="{y + 4}" font-size="11" fill="{C_INK2}">{hi_v:.1f}</text>')
            out.append(f'<text x="{(lo + hi) / 2:.1f}" y="{y - 10}" font-size="12" font-weight="600" fill="{C_INK}" text-anchor="middle">{gain}</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_per_pass(summary):
    e = summary["configs"].get(CELL, {})
    pp = e.get("per_pass", {})
    ks = [k for k in (1, 2, 3) if f"base-pass{k}" in pp or f"canon-pass{k}" in pp]
    if not ks:
        return ""
    W, left, right, rowh, top = 960, 200, 210, 40, 70
    Hh = top + rowh * len(ks) + 50
    vals = [pp[t]["tps_mean"] for t in pp]
    xmin, xmax = min(vals) * 0.9, max(vals) * 1.06
    def X(v):
        return left + (v - xmin) / (xmax - xmin) * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="TPS per pass of the cell" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(svg_text_lines(20, 22, [f"{label(CELL)}: TPS per pass (pass k of one arm pairs with pass k of the other)"], 15, C_INK, "600", 18))
    out.append(f'<circle cx="26" cy="{top - 16}" r="5" fill="{C_BLUE_LIGHT}"/><text x="36" y="{top - 12}" font-size="11" fill="{C_INK2}">nightly deb</text>')
    out.append(f'<circle cx="136" cy="{top - 16}" r="5" fill="{C_BLUE}"/><text x="146" y="{top - 12}" font-size="11" fill="{C_INK2}">canonical-AMX deb</text>')
    step = 2 if (xmax - xmin) < 20 else 5
    v = math.ceil(xmin / step) * step
    while v <= xmax:
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{Hh - 40}" stroke="{C_GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{Hh - 24}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{v}</text>')
        v += step
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 6}" font-size="11" fill="{C_MUTED}" text-anchor="middle">TPS (axis does not start at zero)</text>')
    for i, k in enumerate(ks):
        y = top + rowh * i + rowh / 2
        b, c = pp.get(f"base-pass{k}"), pp.get(f"canon-pass{k}")
        out.append(f'<text x="{left - 12}" y="{y + 4}" font-size="12" fill="{C_INK}" text-anchor="end">pass {k}</text>')
        if b and c:
            xb, xc = X(b["tps_mean"]), X(c["tps_mean"])
            out.append(f'<line x1="{xb:.1f}" y1="{y:.1f}" x2="{xc:.1f}" y2="{y:.1f}" stroke="{C_BLUE_LIGHT}" stroke-width="3"/>')
            g = 100 * (c["tps_mean"] / b["tps_mean"] - 1)
            out.append(f'<text x="{(xb + xc) / 2:.1f}" y="{y - 10}" font-size="12" font-weight="600" fill="{C_INK}" text-anchor="middle">{g:+.1f} %</text>')
        for rec, col, anchor, dx in ((b, C_BLUE_LIGHT, "end", -11), (c, C_BLUE, "start", 11)):
            if rec:
                x = X(rec["tps_mean"])
                tt = f"pass {k}: {rec['tps_mean']:.2f} TPS"
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{col}" stroke="{C_SURF}" stroke-width="2"><title>{esc(tt)}</title></circle>')
                out.append(f'<text x="{x + dx:.1f}" y="{y + 4}" font-size="11" fill="{C_INK2}" text-anchor="{anchor}">{rec["tps_mean"]:.2f}</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_gain_vs_prompt(summary):
    """Gain against prompt length: the 8-users-per-engine series (Saturday 1024 and 2048, this run 4096) and the
    2-users-per-engine series (Saturday 1024 to 4096) for scale; the pre-registered band at 4096."""
    ref = summary.get("reference", {})
    s8 = dict(ref.get("series_8u", {}))
    e = summary["configs"].get(CELL)
    if e and e.get("n_pairs"):
        s8[CELL] = e
    s2 = ref.get("series_2u", {})
    band = summary["verdicts"].get("cell", {}).get("band_pct", [11.0, 21.0])
    pts = [(parse_name(n)[1], r, "8u") for n, r in s8.items()] + [(parse_name(n)[1], r, "2u") for n, r in s2.items()]
    if not pts:
        return ""
    W, Hh, left, right, top, bottom = 960, 500, 70, 60, 118, 60
    xmax = 4096 * 1.15
    gains = [r["gain_pct"] for _, r, _ in pts] + [g for _, r, _ in pts for g in (r.get("gain_pct_per_pass") or [])] + list(band)
    ymin, ymax = min(0, min(gains)) - 1.5, max(gains) + 2.5
    def X(v):
        return left + v / xmax * (W - left - right)
    def Y(v):
        return top + (ymax - v) / (ymax - ymin) * (Hh - top - bottom)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="AMX gain against prompt length at 8 and 2 users per engine" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="20" y="22" font-size="15" font-weight="600" fill="{C_INK}">Gain of the AMX deb against prompt length, at 8 users per engine (blue) and 2 users per engine (orange)</text>')
    out.append(svg_text_lines(20, 42, wrap("Dot = mean gain over 3 passes; thin bar = lowest and highest single-pass gain; hollow dot = not resolved. Blue at 1024 and 2048 and all orange points are Saturday measurements; the large blue point at 4096 is this run; the shaded box is its pre-registered band.", 150), 12, C_INK2, "400", 15))
    out.append(f'<rect x="{X(4096) - 28:.1f}" y="{Y(band[1]):.1f}" width="56" height="{Y(band[0]) - Y(band[1]):.1f}" fill="{C_BAND}" stroke="{C_ORANGE}" stroke-width="1" stroke-dasharray="3,3"/>')
    out.append(f'<text x="{X(4096):.1f}" y="{Y(band[0]) + 14:.1f}" font-size="10" fill="{C_INK2}" text-anchor="middle">expected {band[0]:+.0f} to {band[1]:+.0f} %</text>')
    gy = math.floor(ymin)
    while gy <= ymax:
        if gy % 2 == 0:
            out.append(f'<line x1="{left}" y1="{Y(gy):.1f}" x2="{W - right}" y2="{Y(gy):.1f}" stroke="{C_GRID if gy else C_AXIS}" stroke-width="1"/>')
            out.append(f'<text x="{left - 8}" y="{Y(gy) + 4:.1f}" font-size="11" fill="{C_MUTED}" text-anchor="end">{gy:+d}</text>')
        gy += 1
    for gx in (0, 1024, 2048, 3000, 4096):
        out.append(f'<text x="{X(gx):.1f}" y="{Hh - bottom + 18}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{gx}</text>')
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 8}" font-size="11" fill="{C_MUTED}" text-anchor="middle">prompt length in tokens (every request also generates {GEN_TOKENS} tokens; TPS measured at generated tokens 896 to 1024)</text>')
    out.append(f'<text transform="translate(16,{(top + Hh - bottom) / 2:.1f}) rotate(-90)" font-size="11" fill="{C_MUTED}" text-anchor="middle">gain of the AMX deb, percent of the nightly TPS</text>')
    for series, col in (("8u", C_BLUE), ("2u", C_ORANGE)):
        sp = sorted([(p, r) for p, r, s_ in pts if s_ == series], key=lambda t: t[0])
        if len(sp) > 1:
            path = " ".join(f"{'M' if i == 0 else 'L'}{X(p):.1f},{Y(r['gain_pct']):.1f}" for i, (p, r) in enumerate(sp))
            out.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="1.5" opacity="0.5"/>')
        for p, r in sp:
            x, g = X(p), r["gain_pct"]
            gp = r.get("gain_pct_per_pass") or []
            if gp:
                out.append(f'<line x1="{x:.1f}" y1="{Y(min(gp)):.1f}" x2="{x:.1f}" y2="{Y(max(gp)):.1f}" stroke="{col}" stroke-width="2" opacity="0.6"/>')
            fill = col if r.get("resolved") else C_SURF
            this_run = (series == "8u" and p == 4096)
            title = f"{'8' if series == '8u' else '2'} users per engine, prompt {p}: {g:+.2f} % (passes {', '.join(f'{v:+.1f}' for v in gp)}){' (this run)' if this_run else ' (Saturday)'}"
            out.append(f'<circle cx="{x:.1f}" cy="{Y(g):.1f}" r="{8 if this_run else 6}" fill="{fill}" stroke="{col}" stroke-width="2"><title>{esc(title)}</title></circle>')
            dy = -12 if series == "8u" else 20
            out.append(f'<text x="{x:.1f}" y="{Y(g) + dy:.1f}" font-size="11" font-weight="{"600" if this_run else "400"}" fill="{C_INK}" text-anchor="middle">{g:+.1f} %{" (this run)" if this_run else ""}</text>')
    out.append(f'<circle cx="26" cy="{top - 30}" r="5" fill="{C_BLUE}"/><text x="36" y="{top - 26}" font-size="11" fill="{C_INK2}">8 users per engine (32 users in total)</text>')
    out.append(f'<circle cx="296" cy="{top - 30}" r="5" fill="{C_ORANGE}"/><text x="306" y="{top - 26}" font-size="11" fill="{C_INK2}">2 users per engine (8 users in total), Saturday, for scale</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- tables
def table(headers, rows, cls="num"):
    h = "".join(f"<th>{esc(x)}</th>" for x in headers)
    b = "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>\n{b}\n</tbody></table></div>'


def results_table(summary):
    rows = []
    e = summary["configs"].get(CELL)
    if not e or not e.get("n_pairs"):
        rows.append([esc(label(CELL)) + " (this run)", "0", "", "", "", "", "no pairs", "", "", "", ""])
    for n, e, is_ref in sorted(rows_all(summary), key=lambda t: kv_tokens(t[0], SAT_OVERHEAD)):
        t = e["paired_t"]
        rows.append([esc(label(n)) + (" (Saturday)" if is_ref else " (this run)"), str(e["n_pairs"]), fmt(e["base_tps_mean"]), fmt(e["canon_tps_mean"]),
                     f"<b>{sfmt(e['gain_pct'])}</b>", fmt(t, 2), ("yes, " + str(e.get("direction"))) if e["resolved"] else "no",
                     f"{fmt(e['base_ttft_ms_mean'], 0)} / {fmt(e['canon_ttft_ms_mean'], 0)}",
                     f"{fmt(e['base_min_tps'])} / {fmt(e['canon_min_tps'])}",
                     f"{fmt(e['base_p05_mean'])} / {fmt(e['canon_p05_mean'])}",
                     fmt((e['wall_s_mean'] or 0) / 60, 1)])
    return table(["cell", "pairs", "nightly TPS", "AMX TPS", "gain %", "paired t", "resolved (|t| >= 4.303 and |gain| >= 1 %)",
                  "TTFT ms nightly / AMX", "slowest sample TPS nightly / AMX", "p05 TPS nightly / AMX", "min per cell"], rows)


def per_pass_table(summary, passes):
    e = summary["configs"].get(CELL, {})
    pp = e.get("per_pass", {})
    rows = []
    for k in (1, 2, 3):
        for arm in ("base", "canon"):
            tag = f"{arm}-pass{k}"
            v = pp.get(tag)
            if not v:
                continue
            r = v.get("engine_requests") or {}
            spread = "/".join(str(r.get(str(i), r.get(i, "?"))) for i in range(4))
            rec = passes.get(tag, {})
            psi = [s.get("client_cpu_psi") for s in rec.get("snapshots", []) if s.get("client_cpu_psi")]
            load = [s.get("client_load") for s in rec.get("snapshots", []) if s.get("client_load")]
            psi_txt = esc(psi[-1].split()[1] if psi and len(psi[-1].split()) > 1 else "n/a")   # "some avg10=x avg60=y ..." -> avg10=x
            load_txt = fmt(max(l[0] for l in load), 1) if load else "n/a"
            rows.append([esc(tag), "nightly deb" if arm == "base" else "canonical-AMX deb", fmt(v["tps_mean"]), fmt(v["tps_sd"]), fmt(v["min"]), fmt(v["p05"]), fmt(v["ttft_ms"], 0),
                         fmt(v.get("prompt_tokens_mean"), 0), fmt(v.get("cache_hit_pct"), 1), spread, str(v.get("anomalous_samples")),
                         (f"{v['amx_busy_cycles'] / 1e9:.1f}" if v.get("amx_busy_cycles") is not None else "n/a"),
                         fmt((v.get("wall_s") or 0) / 60, 1), esc(v.get("started", "?")), psi_txt, load_txt])
    return table(["pass-run", "arm", "TPS mean", "TPS sd", "slowest sample", "p05", "TTFT ms", "prompt tokens counted by the server (mean)",
                  "prefix-cache hits %", "requests per engine 0/1/2/3 (expected 80 each)", "anomalous samples", "AMX-busy cycles (billions)",
                  "minutes for the cell", "cell started (UTC)", "client CPU pressure (avg10, last snapshot)", "client load (max, 32 CPUs)"], rows)


def identity_table(summary, passes):
    rows = []
    for tag, rec in sorted(passes.items(), key=lambda kv: (int(kv[0].split("pass")[1]), kv[0].split("-")[0])):
        ver = (rec.get("versions") or {}).get("Tron (package)", "?")
        sha = (rec.get("installed_sha_env") or "?")[:16]
        probes = [p.get("amx_busy_cycles") for p in rec.get("amx_probes", []) if p.get("amx_busy_cycles") is not None]
        bad = [b for b in rec.get("binary_checks", []) if b.get("bad")]
        ncfg = sum(1 for r in rec.get("results", []) if r.get("tps_results")) or sum(1 for r in rec.get("raw", []) if r.get("tpss"))
        rows.append([esc(tag), esc(ver), esc(sha), str(len(rec.get("binary_checks", []))), str(len(bad)),
                     f"{min(probes) / 1e9:.1f} to {max(probes) / 1e9:.1f}" if probes else "n/a", str(ncfg),
                     esc(rec.get("started", "?")), esc(rec.get("finished", "?")), fmt(rec.get("perf_minutes"), 0), esc(rec.get("stop") or "none")])
    return table(["pass-run", "tron package (posadm info)", "rinzler sha256 (first 16)", "binary checks", "checks with a bad pid",
                  "AMX-busy cycles per probe, billions (min to max)", "configs with results", "started", "finished", "minutes", "stop"], rows)


# ---------------------------------------------------------------- page
def build():
    summary, passes, outcome, hist, prompt_check, compare, base_identity = load()
    overhead = observed_overhead(summary)
    v = summary["verdicts"]
    cell = v.get("cell", {})
    ag = v.get("against_2048", {})
    e = summary["configs"].get(CELL, {})
    ref = summary.get("reference", {}).get("cells", {})
    r2048 = ref.get("llama_3_1_8b_instruct_good_tp2_32u_p2048", {})
    r1024 = ref.get("llama_3_1_8b_instruct_good_tp2_32u_p1024", {})
    r2u4096 = ref.get("llama_3_1_8b_instruct_good_tp2_8u_p4096", {})
    band = cell.get("band_pct", [11.0, 21.0])
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    n_pairs = e.get("n_pairs", 0)
    short = []
    if n_pairs:
        short.append(f"On the whole of delphi-3bda, with the nightly's own client and layout, the canonical-AMX deb changed llama-3.1-8b decode speed by {sfmt(e['gain_pct'], 1)} % at 8 users per engine and prompt 4096 ({fmt(e['base_tps_mean'])} to {fmt(e['canon_tps_mean'])} TPS, {n_pairs} interleaved pass pairs, paired t {fmt(e['paired_t'], 1)}, {'resolved' if e['resolved'] else 'not resolved'}).")
        short.append(f"The pre-registered band was {sfmt(band[0], 0)} to {sfmt(band[1], 0)} %, the result is {'inside' if cell.get('inside_band') else 'outside'} it, and the Saturday cells at the same load gave {sfmt(r1024.get('gain_pct'), 1)} % at prompt 1024 and {sfmt(r2048.get('gain_pct'), 1)} % at prompt 2048.")
        short.append(f"Reading per the plan: {cell.get('reading')}.")
    else:
        short.append("The campaign has no paired pass yet for the cell; the numbers below are partial.")
        short.append(f"The campaign outcome line reads: {outcome}.")
    words = [
        ("tron, rinzler, engine, tp2", "tron is the inference program under test; rinzler is its production server; one running rinzler is one engine; tp2 = two FPGA cards per engine (FPGA = field-programmable gate array, the accelerator card that runs the dense part of the model). The nightly layout is 4 tp2 engines behind the Caddy proxy."),
        ("nightly deb, canonical-AMX deb (the two arms)", "The nightly deb is the package the nightly CI installed (tron 2026.09.18-3faba6d0, built without the AMX kernel). The canonical-AMX deb is the same source plus one CMake preset line (TRON_AMX_DISPATCH=ON), so its rinzler contains the AMX attention kernel of PR #3879 and nothing of PR #4424. An arm is one installed package; a pass is one run of the cell on one arm."),
        ("AMX", "Intel Advanced Matrix Extensions, the CPU matrix instructions the kernel uses for attention. AMX-busy cycles come from the CPU counter EXE.AMX_BUSY read with perf stat for 20 s on the engine processes before the cell: about 0 on the nightly deb, billions on the AMX deb."),
        ("CI harness, cell, TPS, TTFT, slowest sample, p05", "The CI harness is the nightly's client code (systems_test scripts/perf.py). A cell is one benchmark run of one config (model, number of users, prompt length) on one arm. TPS = decode tokens per second per user, measured between generated tokens 896 and 1024 of every request, averaged over 10 rounds of all users. TTFT = time to first token in ms. Slowest sample = the lowest single-request TPS. p05 = the 5th percentile of the request TPS values."),
        ("users per engine, KV tokens per engine step", "The harness's user count is spread by Caddy over the 4 engines, so 32 users = 8 users per engine. KV tokens per engine step = users per engine x context per user (prompt + tokens the server adds + generated tokens at the middle of the TPS window); it is the attention work of one decode step."),
        ("gain, paired t, resolved", "gain = AMX-deb mean TPS over nightly-deb mean TPS minus 1, in percent, over the 3 passes. Paired t = mean of the 3 per-pass TPS differences divided by their standard error (pass k of one arm pairs with pass k of the other). Resolved = |t| >= 4.303 (the 95 % two-sided limit of Student's t with 2 degrees of freedom) and |gain| >= 1 %."),
        ("pre-registered band", f"The plan (section 7) expected a gain of {sfmt(band[0], 0)} to {sfmt(band[1], 0)} % before the run, from the Saturday series (8 users per engine: +10.8 % at 1024, +14.0 % at 2048) and the kernel's per-unit speed ratio of about 1.26 (ceiling near +21 %)."),
        ("prompt truncation at 4096", "For llama-3.1-8b on this deployment the server keeps at most the first 4096 prompt tokens of a chat request (the deployed tokenizer.json carries a truncation block; found on Saturday, documented in the Saturday report). The harness sends a 4096-token conversation, the server adds about 34 tokens of system line and chat template, then keeps the first 4096. The last tokens of the request are dropped and the server counts exactly 4096 prompt tokens. Decode speed is measured either way; the Saturday 2-users-per-engine cell at 4096 ran under the same property."),
        ("Saturday reference cells", "The three cells of the 2026-09-19 campaign (CI-test/status/Saturday-llama-3.1-8b.html) shown next to this run: 8 users per engine at prompt 1024 and 2048, and 2 users per engine at prompt 4096. Same arms, same driver, same layout; their numbers are read from that campaign's summary.json, not retyped."),
    ]
    deviations = [
        "One cell, no check cell before the first pass (plan section 6): the Saturday check cell (32 users, 4096 server-side prompt tokens, canon) and the Saturday 2-users prompt-4096 cell had shown the shape works on both the server and the client side.",
        "Driver timeout per pass 2400 s (plan section 4); campaign start deadline 22:00 UTC, last pass start 00:20 UTC, hard end 01:00 UTC (plan section 2).",
        "Engines restarted after every package switch (serving-down, serving-up with a wait for platformd idle), as on Saturday.",
        "Per-engine request counts read from rinzler's FUSE stats (prompts_total); the AMX-busy probe ran before every cell.",
        "The offline prompt check ran for prompt 4096 only (seeds 0 to 319, two runs compared); the prompt-source change of Saturday is unchanged (md5 of testlib/prompt.py equal to prompt.py.after).",
    ]
    css = """
    body{background:#f9f9f7;color:#0b0b0b;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.5;margin:0;padding-block:24px;padding-inline:16px}
    main{max-width:1040px;margin:0 auto}
    h1{font-size:26px;line-height:1.2;margin:0 0 6px;text-wrap:balance}
    h2{font-size:19px;margin:36px 0 10px;border-bottom:1px solid #e1e0d9;padding-bottom:4px}
    h3{font-size:16px;margin:22px 0 6px}
    p,li{max-width:78ch}
    .sub{color:#52514e;font-size:13px;margin:0 0 18px}
    .short{background:#fcfcfb;border:1px solid #e1e0d9;border-left:4px solid #2a78d6;padding:12px 16px;margin:16px 0}
    .short p{margin:6px 0}
    .fig{background:#fcfcfb;border:1px solid #e1e0d9;padding:12px;margin:14px 0;overflow-x:auto}
    .cap{color:#52514e;font-size:13px;margin:6px 0 0}
    .tw{overflow-x:auto;margin:10px 0}
    table{border-collapse:collapse;font-size:13px;min-width:600px}
    th,td{border-bottom:1px solid #e1e0d9;padding:5px 8px;text-align:left;vertical-align:top}
    th{background:#f0efec;font-weight:600;color:#52514e}
    table.num td:not(:first-child){font-variant-numeric:tabular-nums;white-space:nowrap}
    dt{font-weight:600;margin-top:10px}
    dd{margin:2px 0 0 0;color:#0b0b0b}
    code{font-size:13px;background:#f0efec;padding:1px 4px}
    .verdict{background:#fcfcfb;border:1px solid #e1e0d9;padding:10px 14px;margin:10px 0}
    """
    parts = []
    parts.append(f"<title>llama-8b AMX 8u 4k</title>\n<style>{css}</style>\n<main>")
    parts.append("<h1>AMX gain on llama-3.1-8b at 8 users per engine and prompt 4096</h1>")
    parts.append(f'<p class="sub">Nightly deb against canonical-AMX deb, CI harness, nightly layout, whole delphi-3bda, 2026-09-20. Plan: CI-test/status/llama-3.1-8b-8u-4k-plan.md. Generated {now} by exec/l8b-8u4k-20260920/gen_report.py from {esc(RES)}. Every number comes from the result files named in section 7.</p>')
    parts.append('<div class="short"><p><b>Short version.</b></p>' + "".join(f"<p>{esc(s)}</p>" for s in short) + "</div>")
    parts.append("<h2>Words used here</h2><dl>" + "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in words) + "</dl>")
    parts.append("<h2>1. What ran</h2>")
    parts.append("<ul>"
                 "<li>Machine: the whole of delphi-3bda (72-core Intel Granite Rapids, 8 FPGA cards), 4 tp2 engines provisioned by platformd behind Caddy on port 80, exactly the nightly layout. The nightly CI lease was free and Bill's marker taken for the whole campaign.</li>"
                 "<li>Client: the nightly's own perf code (systems_test scripts/perf.py) run from claude-agentsrv through the campaign driver (st_ci_perf.py), which records every request, the layout, the engine binary per pass and the AMX-busy probe. Talos (the CI results database) was replaced by a recording stub; nothing reached CI records.</li>"
                 f"<li>Arms: nightly deb {esc(base_identity[0] if base_identity else '2026.09.18-3faba6d0')} against the canonical-AMX deb tron_2026.09.18-0594dc54-jhan-ci-canon, 3 passes each, interleaved (base, canon, base, canon, base, canon). Passes found: {esc(', '.join(summary['passes_found']))}.</li>"
                 f"<li>Cell: llama-3.1-8b-instruct-good-tp2, 32 users (8 per engine), prompt length 4096, {GEN_TOKENS} generated tokens, TPS window 896 to 1024, 10 rounds = 320 requests per cell.</li>"
                 f"<li>Prompt source: ShareGPT with concatenation of following conversations; offline check of 320 prompts at 4096: {('0 exceptions' if prompt_check and prompt_check.get('total_exceptions') == 0 else 'see prompt-check/')}, {'deterministic across two runs' if 'DETERMINISTIC' in compare else 'determinism not checked'}.</li>"
                 f"<li>Prompt tokens counted by the server minus the prompt length sent (measured here): {fmt(overhead, 1)} (0 = clipped at 4096, see the words list).</li>"
                 "</ul>")
    parts.append("<h3>Identity of every pass-run</h3>")
    parts.append(identity_table(summary, passes))
    parts.append('<p class="cap">The binary check compares every engine process with the installed rinzler (sha256) after each provisioning; a pass stops if any engine still runs a deleted or foreign binary. AMX-busy cycles prove which kernel ran.</p>')
    parts.append("<h2>2. Result</h2>")
    parts.append('<div class="fig">' + chart_dumbbell(summary) + '<p class="cap">Figure 1. Each row is one cell; the light dot is the nightly deb, the dark dot the canonical-AMX deb, both the mean TPS over 3 passes. The label is the AMX gain in percent. The bold row is this run; the others are the Saturday reference cells. Hover a dot for the paired t.</p></div>')
    parts.append(results_table(summary))
    parts.append('<div class="verdict"><p><b>Verdict of the pre-registered rule</b> (plan section 7): ' + esc(f"{n_pairs} paired passes, gain {sfmt(e.get('gain_pct'), 2)} %, paired t {fmt(e.get('paired_t'), 2)} against the limit {fmt(e.get('t_limit_95'), 3)}, resolved: {e.get('resolved')}, direction: {e.get('direction')}.") + f"</p><p>Band {sfmt(band[0], 0)} to {sfmt(band[1], 0)} %: inside = {esc(cell.get('inside_band'))}. Reading: {esc(cell.get('reading'))}</p>"
                 + f"<p>Against the Saturday 2048 cell at the same load: {sfmt(ag.get('gain_8u_p2048_saturday'), 2)} % at 2048, {sfmt(ag.get('gain_8u_p4096'), 2)} % at 4096, difference {sfmt(ag.get('diff_points'), 2)} points.</p></div>")
    if n_pairs:
        cg = cell.get("candidate_goal_values_clean") or {}
        parts.append('<div class="verdict"><p><b>Candidate goal values for a CI threshold at this shape</b> (the clean arm, as the Saturday run recorded them for the 32-user prompt-1024 shape): ' + esc(f"mean TPS {fmt(cg.get('tps_mean'))}, slowest sample {fmt(cg.get('slowest_sample_tps'))} TPS, p05 {fmt(cg.get('p05_tps_mean'))} TPS (means over the 3 clean passes; slowest sample = the lowest of all clean requests).") + " No threshold exists for this shape today.</p></div>")
    parts.append("<h3>Per pass</h3>")
    parts.append('<div class="fig">' + chart_per_pass(summary) + '<p class="cap">Figure 2. TPS of each pass; the label is the gain of that pair. The paired t uses these three differences.</p></div>')
    parts.append(per_pass_table(summary, passes))
    parts.append('<p class="cap">Requests per engine come from rinzler\'s prompts_total counter read before and after the cell; 32 users x 10 rounds / 4 engines = 80 expected per engine. Anomalous samples are harness samples above 1000 TPS (a client-side stall indicator). Client CPU pressure is the avg10 value of /proc/pressure/cpu on the client host at the last snapshot of the pass (the 2026-09-18 run with a saturated client showed 93 to 99 %).</p>')
    parts.append("<h2>3. Gain against prompt length at 8 users per engine</h2>")
    parts.append('<div class="fig">' + chart_gain_vs_prompt(summary) + '<p class="cap">Figure 3. Blue: 8 users per engine (Saturday at 1024 and 2048, this run at 4096). Orange: 2 users per engine, Saturday, for scale. Thin bars: lowest and highest single-pass gain. The shaded box at 4096 is the band the plan expected for this run.</p></div>')
    parts.append("<ul>"
                 f"<li>8 users per engine: {sfmt(r1024.get('gain_pct'), 1)} % at prompt 1024 (Saturday), {sfmt(r2048.get('gain_pct'), 1)} % at 2048 (Saturday), {sfmt(e.get('gain_pct'), 1)} % at 4096 (this run).</li>"
                 f"<li>2 users per engine at prompt 4096 (Saturday): {sfmt(r2u4096.get('gain_pct'), 1)} %; the same prompt length at 4x the users per engine gives {sfmt(e.get('gain_pct'), 1)} %.</li>"
                 f"<li>TTFT at this cell: {fmt(e.get('base_ttft_ms_mean'), 0)} ms on the nightly deb, {fmt(e.get('canon_ttft_ms_mean'), 0)} ms on the AMX deb (Saturday at 2048: {fmt(r2048.get('base_ttft_ms_mean'), 0)} / {fmt(r2048.get('canon_ttft_ms_mean'), 0)} ms). TTFT includes the prefill of a 4096-token prompt for 8 users per engine and the client's own waits.</li>"
                 "</ul>")
    parts.append("<h2>4. Decisions taken during the run (plan section 2a) and deviations from the plan text</h2><ul>" + "".join(f"<li>{esc(d)}</li>" for d in deviations) + "</ul>")
    parts.append(f"<p>Campaign outcome line: {esc(outcome)}.</p>")
    parts.append("<h3>Campaign status lines</h3><pre style=\"font-size:12px;overflow-x:auto;background:#fcfcfb;border:1px solid #e1e0d9;padding:8px\">" + esc("\n".join(l for l in hist if "waiting: CI lease busy" not in l)) + "</pre>")
    parts.append("<h2>5. What this does and does not show</h2><ul>"
                 "<li>It shows the AMX deb's effect in the exact nightly setting for llama-3.1-8b at one shape: 8 users per engine and prompt 4096. It does not measure other models or shapes, and it does not measure PR #4424 (VNNI K), which is not in either package.</li>"
                 "<li>Both arms ran the same client code, prompts, layout and machine, alternating, so a common drift affects both passes of a pair; the paired t uses only within-pair differences.</li>"
                 "<li>The Saturday reference rows were measured one day earlier with the same packages and driver; they are shown for scale and were not re-run.</li>"
                 "<li>Prompts of 4096 tokens are clipped by the deployed tokenizer (the words list); the cell measures decode at exactly 4096 server-side prompt tokens, comparable with the Saturday 2-users cell at 4096.</li>"
                 "</ul>")
    parts.append("<h2>6. Next steps (jhan decides)</h2><ul><li>Whether the 32-user prompt-4096 shape is proposed to the CI team as a long-prompt shape at the recommended load (the candidate goal values are in section 2).</li><li>Feed this cell into gen_ci_shapes.py as source I (exec/l8b-8u4k-20260920/i_registry.py) and re-render the CI-AMX-test-shapes page.</li><li>Notebook preservation of this page.</li></ul>")
    parts.append("<h2>7. Files</h2><ul>"
                 f"<li>Results: <code>{esc(RES)}</code> (per pass: perf.json, talos.json, driver.log, summary.txt; summary.json and summary.txt from analyze.py; preflight.txt; base-identity.txt; outcome.txt; status-history.log; prompt-check/run1.json, run2.json, compare.log; check-mode/).</li>"
                 "<li>Scripts: <code>exec/l8b-8u4k-20260920/</code> (campaign.sh, launch.sh, dut.sh, st_ci_perf.py, configs.py, prompt_check.py, analyze.py, gen_report.py, i_registry.py), copied from exec/l8b-levers-20260919/ with the changes of plan section 4.</li>"
                 "<li>Plan: <code>CI-test/status/llama-3.1-8b-8u-4k-plan.md</code>; Saturday report: <code>CI-test/status/Saturday-llama-3.1-8b.html</code>; Saturday results: <code>exec/results/l8b-levers-20260919/summary.json</code>.</li>"
                 "</ul></main>")
    page = "\n".join(parts)
    page = page.encode("ascii", "xmlcharrefreplace").decode("ascii")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(page)} bytes, ascii)")


if __name__ == "__main__":
    build()
