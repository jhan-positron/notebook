#!/usr/bin/env python3
"""Report of the q4b-swattn campaign (qwen3-4b Saturday plan section 9): CI-test/status/Saturday-qwen3-4b.html.

Copied 2026-09-19 from exec/l8b-levers-20260919/gen_report.py and rewritten for one model (qwen3-4b tp2), one load
(2 users per engine) and the prompt-length lever. Reads summary.json (analyze.py), the pass records perf.json and the
check-cell records under the results directory, writes one light-theme HTML page with inline SVG charts (pure ASCII
output: the artifact publisher mangles non-ASCII bytes). Every campaign number on the page comes from those files. The
context numbers of other campaigns (the nightly's FPGA-attention level, the p0perf-20260913 band, the llama curve,
the runtron data F) are named with their source next to the value.
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

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/q4b-swattn-20260919"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/CI-test/status/Saturday-qwen3-4b.html"
L8B_SUMMARY = "/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/summary.json"
GEN_TOKENS = 1536
WINDOW_MID = (896 + 1024) // 2   # generated tokens at the middle of the TPS window
USERS_PER_ENGINE = 2
BAND = (5.4, 11.4)
# context values from other campaigns, each with its source (plan sections "Two corrections" and 11)
CTX_NIGHTLY_FPGA = (186.13, 186.25, "canon-ci 2026-09-18: nightly deb / canonical deb, qwen3-4b tp2, FPGA attention, CI harness, whole machine (PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html)")
CTX_P0PERF = (140.61, 152.46, "p0perf-20260913: CI layout tp2, 2 users per engine, USE_HW_ATTN=0, kill switch / AMX on, same binary, our half (PR3879/new-PRs/PR1/Sunday-CI-layout-results.html)")
DATA_F = [  # (prompt, gain %, users on one engine, label) runtron qwen3-4b canonical vs clean, exec/canon-ci-20260918/gen_ci_shapes.py f_p2048 f_p8192 fc1_p2048 fc1_p8192
    (2048, 19.0, 8, "runtron, 8 users"), (8192, 17.5, 8, "runtron, 8 users"), (2048, 3.8, 1, "runtron, 1 user"), (8192, 15.2, 1, "runtron, 1 user")]
L8B_FALLBACK = {1024: 0.21, 2048: 1.55, 3000: 7.30, 4096: 8.19}   # status/Saturday-llama-3.1-8b.html, 2 users per engine

C_BLUE, C_BLUE_LIGHT, C_ORANGE, C_AQUA, C_GREY = "#2a78d6", "#86b6ef", "#eb6834", "#1baf7a", "#9a9891"
C_INK, C_INK2, C_MUTED, C_GRID, C_AXIS, C_SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"


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


def plen(n):
    return int(re.search(r"_p(\d+)$", n).group(1))


def label(n):
    return f"prompt {plen(n)}"


def load():
    sp = os.path.join(RES, "summary.json")
    summary = json.load(open(sp)) if os.path.isfile(sp) else {"passes_found": [], "configs": {}, "incomplete": [], "verdicts": {}}
    passes = {}
    for path in sorted(glob.glob(os.path.join(RES, "*-pass[0-9]", "perf.json"))):
        tag = os.path.basename(os.path.dirname(path))
        try:
            passes[tag] = json.load(open(path))
        except Exception:
            pass
    checks = {}
    for d in sorted(glob.glob(os.path.join(RES, "check-*"))):
        p = os.path.join(d, "perf.json")
        if os.path.isfile(p) and "check-mode" not in d:
            try:
                checks[os.path.basename(d)] = json.load(open(p))
            except Exception:
                pass
    outcome = open(os.path.join(RES, "outcome.txt")).read().strip() if os.path.isfile(os.path.join(RES, "outcome.txt")) else "outcome.txt missing (the passes have not run yet, or the campaign is still running)"
    outcome_check = open(os.path.join(RES, "outcome-check.txt")).read().strip() if os.path.isfile(os.path.join(RES, "outcome-check.txt")) else None
    hist = open(os.path.join(RES, "status-history.log")).read().splitlines() if os.path.isfile(os.path.join(RES, "status-history.log")) else []
    prompt_check = None
    pc = os.path.join(RES, "prompt-check", "run1.json")
    if os.path.isfile(pc):
        prompt_check = json.load(open(pc))
    l8b = dict(L8B_FALLBACK)
    l8b_src = "status/Saturday-llama-3.1-8b.html (typed fallback values)"
    if os.path.isfile(L8B_SUMMARY):
        try:
            ls = json.load(open(L8B_SUMMARY))["configs"]
            got = {plen(n): e["gain_pct"] for n, e in ls.items() if "_8u_p" in n and e.get("n_pairs") == 3}
            if got:
                l8b, l8b_src = got, "exec/results/l8b-levers-20260919/summary.json (2 users per engine cells)"
        except Exception:
            pass
    return summary, passes, checks, outcome, outcome_check, hist, prompt_check, l8b, l8b_src


def observed_overhead(summary):
    vals = []
    for n, e in summary["configs"].items():
        for pv in e.get("per_pass", {}).values():
            if pv.get("prompt_tokens_mean"):
                vals.append(pv["prompt_tokens_mean"] - plen(n))
    return (sum(vals) / len(vals)) if vals else None


def kv_tokens(n, overhead, e=None):
    """2 x (prompt + measured server overhead + 960): the cell's own overhead when analyze.py measured it, else the campaign mean, else 0."""
    ov = e.get("overhead_tokens_mean") if e else None
    if ov is None:
        ov = overhead if overhead is not None else 0
    return USERS_PER_ENGINE * (plen(n) + ov + WINDOW_MID)


# ---------------------------------------------------------------- charts
def chart_dumbbell(summary, overhead):
    rows = [(n, e) for n, e in summary["configs"].items() if e.get("n_pairs")]
    rows.sort(key=lambda ne: plen(ne[0]))
    if not rows:
        return "<p>No paired pass yet (the passes run in the Sunday window).</p>"
    W, left, right, rowh, top = 960, 250, 230, 46, 96
    Hh = top + rowh * len(rows) + 50
    xmax = max(max(e["base_tps_mean"], e["canon_tps_mean"]) for _, e in rows) * 1.05
    def X(v):
        return left + v / xmax * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="Decode TPS per prompt length, nightly deb against canonical AMX deb, software attention on both" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(svg_text_lines(20, 22, ["Decode TPS per prompt length: nightly deb (light dot) against canonical-AMX deb (dark dot), software attention on both"], 15, C_INK, "600", 18))
    out.append(svg_text_lines(20, 44, wrap("qwen3-4b tp2, 2 users per engine, 1536 generated tokens per request. Mean of 3 passes. The label on each row is the gain of the AMX deb in percent; n.r. = not resolved by the pre-registered rule.", 130), 12, C_INK2, "400", 15))
    out.append(f'<circle cx="26" cy="{top - 18}" r="5" fill="{C_BLUE_LIGHT}"/><text x="36" y="{top - 14}" font-size="11" fill="{C_INK2}">nightly deb (no AMX code), AVX attention</text>')
    out.append(f'<circle cx="286" cy="{top - 18}" r="5" fill="{C_BLUE}"/><text x="296" y="{top - 14}" font-size="11" fill="{C_INK2}">canonical-AMX deb, AMX attention</text>')
    step = 20 if xmax > 100 else 10
    v = 0
    while v <= xmax:
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{Hh - 40}" stroke="{C_GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{Hh - 24}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{v}</text>')
        v += step
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 6}" font-size="11" fill="{C_MUTED}" text-anchor="middle">tokens per second per user (TPS), mean of the 8 users of a cell</text>')
    for i, (n, e) in enumerate(rows):
        y = top + rowh * i + rowh / 2
        b, c = e["base_tps_mean"], e["canon_tps_mean"]
        xb, xc = X(b), X(c)
        out.append(f'<text x="{left - 12}" y="{y + 4}" font-size="12" fill="{C_INK}" text-anchor="end">{esc(label(n))}</text>')
        out.append(f'<text x="{left - 12}" y="{y + 17}" font-size="10" fill="{C_MUTED}" text-anchor="end">{kv_tokens(n, overhead, e) / 1000:.1f}K KV tokens per step</text>')
        out.append(f'<line x1="{xb:.1f}" y1="{y:.1f}" x2="{xc:.1f}" y2="{y:.1f}" stroke="{C_BLUE_LIGHT}" stroke-width="3"/>')
        title = f"{label(n)}: nightly {b:.2f} TPS, canonical AMX {c:.2f} TPS, gain {e['gain_pct']:+.2f} %, paired t {fmt(e['paired_t'])}, {'resolved' if e['resolved'] else 'not resolved'}"
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


def chart_gain_vs_prompt(summary, l8b, l8b_src):
    rows = [(n, e) for n, e in summary["configs"].items() if e.get("n_pairs")]
    rows.sort(key=lambda ne: plen(ne[0]))
    W, Hh, left, right, top, bottom = 960, 520, 70, 40, 128, 60
    pts_q = [(plen(n), e["gain_pct"], e) for n, e in rows]
    gains = [g for _, g, _ in pts_q] + [v for _, _, e in pts_q for v in e["gain_pct_per_pass"]] + list(l8b.values()) + [g for _, g, _, _ in DATA_F]
    xmax = 8192 * 1.06
    ymin, ymax = min(0, min(gains)) - 1.5, max(gains) + 2.5
    def X(p):
        return left + p / xmax * (W - left - right)
    def Y(v):
        return top + (ymax - v) / (ymax - ymin) * (Hh - top - bottom)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="AMX gain against prompt length" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="20" y="22" font-size="15" font-weight="600" fill="{C_INK}">Gain of the AMX deb against prompt length, qwen3-4b tp2 at 2 users per engine (this campaign) with two context curves</text>')
    out.append(svg_text_lines(20, 42, wrap("Blue dot = mean gain over 3 passes (thin bar = lowest and highest single-pass gain; hollow = not resolved). Orange = llama-3.1-8b at the same load from the campaign of 2026-09-19 (" + l8b_src + "). Grey = runtron single-engine measurements of qwen3-4b (data F), 8 users and 1 user, context only: different client and layout.", 135), 12, C_INK2, "400", 15))
    gy = math.floor(ymin)
    while gy <= ymax:
        if gy % 2 == 0:
            out.append(f'<line x1="{left}" y1="{Y(gy):.1f}" x2="{W - right}" y2="{Y(gy):.1f}" stroke="{C_GRID if gy else C_AXIS}" stroke-width="1"/>')
            out.append(f'<text x="{left - 8}" y="{Y(gy) + 4:.1f}" font-size="11" fill="{C_MUTED}" text-anchor="end">{gy:+d}</text>')
        gy += 1
    for gx in (1024, 2048, 3000, 4096, 5120, 6144, 7168, 8192):
        out.append(f'<line x1="{X(gx):.1f}" y1="{Y(ymax):.1f}" x2="{X(gx):.1f}" y2="{Y(ymin):.1f}" stroke="{C_GRID}" stroke-width="1" stroke-dasharray="2 4"/>')
        out.append(f'<text x="{X(gx):.1f}" y="{Hh - bottom + 18}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{gx}</text>')
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 8}" font-size="11" fill="{C_MUTED}" text-anchor="middle">prompt length (tokens sent by the harness); every request also generates {GEN_TOKENS} tokens</text>')
    out.append(f'<text transform="translate(16,{(top + Hh - bottom) / 2:.1f}) rotate(-90)" font-size="11" fill="{C_MUTED}" text-anchor="middle">gain of the AMX deb, percent of the nightly-deb TPS</text>')
    # band at 1024 and the +10 % crossing line
    out.append(f'<rect x="{X(1024) - 14:.1f}" y="{Y(BAND[1]):.1f}" width="28" height="{Y(BAND[0]) - Y(BAND[1]):.1f}" fill="{C_AQUA}" opacity="0.18"><title>pre-registered band at prompt 1024: +5.4 to +11.4 %</title></rect>')
    out.append(f'<line x1="{left}" y1="{Y(10):.1f}" x2="{W - right}" y2="{Y(10):.1f}" stroke="{C_AQUA}" stroke-width="1" stroke-dasharray="6 4"/>')
    out.append(f'<text x="{W - right - 4}" y="{Y(10) - 5:.1f}" font-size="10" fill="{C_AQUA}" text-anchor="end">+10 % (crossing rule)</text>')
    # data F (grey)
    for p, g, u, lab in DATA_F:
        out.append(f'<circle cx="{X(p):.1f}" cy="{Y(g):.1f}" r="5" fill="{C_GREY}" opacity="0.8"><title>{esc(lab)}: prompt {p}, {g:+.1f} % (data F, one engine, runtron)</title></circle>')
        dy = -8 if u == 8 else 14
        out.append(f'<text x="{X(p) + 8:.1f}" y="{Y(g) + dy:.1f}" font-size="10" fill="{C_GREY}">{esc(lab.split(", ")[1])} {g:+.1f}</text>')
    for (u, grp) in ((8, [d for d in DATA_F if d[2] == 8]), (1, [d for d in DATA_F if d[2] == 1])):
        grp.sort()
        out.append(f'<polyline points="{" ".join(f"{X(p):.1f},{Y(g):.1f}" for p, g, _, _ in grp)}" fill="none" stroke="{C_GREY}" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.8"/>')
    # llama curve (orange)
    lp = sorted(l8b.items())
    out.append(f'<polyline points="{" ".join(f"{X(p):.1f},{Y(g):.1f}" for p, g in lp)}" fill="none" stroke="{C_ORANGE}" stroke-width="2"/>')
    for p, g in lp:
        out.append(f'<circle cx="{X(p):.1f}" cy="{Y(g):.1f}" r="5" fill="{C_ORANGE}"><title>llama-3.1-8b, 2 users per engine, prompt {p}: {g:+.2f} %</title></circle>')
        out.append(f'<text x="{X(p):.1f}" y="{Y(g) + 18:.1f}" font-size="10" fill="{C_ORANGE}" text-anchor="middle">{g:+.1f}</text>')
    # this campaign (blue)
    if pts_q:
        out.append(f'<polyline points="{" ".join(f"{X(p):.1f},{Y(g):.1f}" for p, g, _ in pts_q)}" fill="none" stroke="{C_BLUE}" stroke-width="2.5"/>')
        for p, g, e in pts_q:
            lo, hi = min(e["gain_pct_per_pass"]), max(e["gain_pct_per_pass"])
            out.append(f'<line x1="{X(p):.1f}" y1="{Y(lo):.1f}" x2="{X(p):.1f}" y2="{Y(hi):.1f}" stroke="{C_BLUE}" stroke-width="2" opacity="0.6"/>')
            fill = C_BLUE if e["resolved"] else C_SURF
            title = f"qwen3-4b prompt {p}: {g:+.2f} % (passes {', '.join(f'{v:+.1f}' for v in e['gain_pct_per_pass'])}), paired t {fmt(e['paired_t'])}, {'resolved' if e['resolved'] else 'not resolved'}"
            out.append(f'<circle cx="{X(p):.1f}" cy="{Y(g):.1f}" r="6.5" fill="{fill}" stroke="{C_BLUE}" stroke-width="2"><title>{esc(title)}</title></circle>')
            out.append(f'<text x="{X(p):.1f}" y="{Y(g) - 11:.1f}" font-size="11" font-weight="600" fill="{C_INK}" text-anchor="middle">{g:+.1f}{"" if e["resolved"] else " n.r."}</text>')
    else:
        out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{(top + Hh - bottom) / 2:.1f}" font-size="13" fill="{C_MUTED}" text-anchor="middle">this campaign: no paired pass yet</text>')
    ly = 96
    for col, txt in ((C_BLUE, "qwen3-4b tp2, 2 users per engine, CI harness, whole machine (this campaign)"), (C_ORANGE, "llama-3.1-8b tp2, 2 users per engine, same harness and machine (2026-09-19)"), (C_GREY, "qwen3-4b, runtron on one engine, data F (context only)")):
        out.append(f'<circle cx="26" cy="{ly - 4}" r="5" fill="{col}"/><text x="36" y="{ly}" font-size="11" fill="{C_INK2}">{esc(txt)}</text>')
        ly += 14
    out.append("</svg>")
    return "\n".join(out)


def chart_level(summary):
    e_ref = summary["configs"].get("ingested_qwen_3_4b_instruct_2507_tp2_8u_p1024", {})
    bars = [("nightly (FPGA attention), nightly deb", CTX_NIGHTLY_FPGA[0], C_GREY, CTX_NIGHTLY_FPGA[2]),
            ("nightly (FPGA attention), canonical deb", CTX_NIGHTLY_FPGA[1], C_GREY, CTX_NIGHTLY_FPGA[2]),
            ("software attention, no AMX (p0perf-20260913)", CTX_P0PERF[0], C_GREY, CTX_P0PERF[2]),
            ("software attention, AMX on (p0perf-20260913)", CTX_P0PERF[1], C_GREY, CTX_P0PERF[2])]
    if e_ref.get("n_pairs"):
        bars.append(("software attention, nightly deb (this campaign, prompt 1024)", e_ref["base_tps_mean"], C_BLUE_LIGHT, "mean of 3 passes"))
        bars.append(("software attention, canonical-AMX deb (this campaign, prompt 1024)", e_ref["canon_tps_mean"], C_BLUE, "mean of 3 passes"))
    W, left, right, rowh, top = 960, 400, 90, 28, 58
    Hh = top + rowh * len(bars) + 40
    xmax = max(v for _, v, _, _ in bars) * 1.12
    def X(v):
        return left + v / xmax * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="TPS level: FPGA attention against software attention" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="20" y="22" font-size="15" font-weight="600" fill="{C_INK}">Why the TPS level here is far below the nightly: FPGA attention against software attention</text>')
    out.append(f'<text x="20" y="40" font-size="12" fill="{C_INK2}">qwen3-4b tp2, prompt 1024, 2 users per engine; grey = other campaigns, blue = this campaign</text>')
    for i, (lab, v, col, src) in enumerate(bars):
        y = top + rowh * i
        out.append(f'<text x="{left - 10}" y="{y + 16}" font-size="12" fill="{C_INK}" text-anchor="end">{esc(lab)}</text>')
        out.append(f'<rect x="{left}" y="{y + 4}" width="{X(v) - left:.1f}" height="18" fill="{col}"><title>{esc(lab)}: {v:.2f} TPS ({esc(src)})</title></rect>')
        out.append(f'<text x="{X(v) + 8:.1f}" y="{y + 17}" font-size="11" fill="{C_INK2}">{v:.1f} TPS</text>')
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 8}" font-size="11" fill="{C_MUTED}" text-anchor="middle">tokens per second per user; grey bars are other campaigns\' measurements (sources in the hover text and in section 4)</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_durations(summary):
    rows = [(n, e) for n, e in summary["configs"].items() if e.get("n_pairs") and e.get("wall_s_mean")]
    if not rows:
        return ""
    rows.sort(key=lambda ne: plen(ne[0]))
    W, left, right, rowh, top = 960, 200, 80, 26, 44
    Hh = top + rowh * len(rows) + 40
    xmax = max(e["wall_s_mean"] for _, e in rows) / 60 * 1.15
    def X(v):
        return left + v / xmax * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="Minutes per cell" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="{left}" y="22" font-size="15" font-weight="600" fill="{C_INK}">Wall time of one cell (10 rounds of 8 users), mean over the passes, minutes</text>')
    for i, (n, e) in enumerate(rows):
        y = top + rowh * i
        m = e["wall_s_mean"] / 60
        out.append(f'<text x="{left - 10}" y="{y + 16}" font-size="12" fill="{C_INK}" text-anchor="end">{esc(label(n))}</text>')
        out.append(f'<rect x="{left}" y="{y + 4}" width="{X(m) - left:.1f}" height="16" fill="{C_BLUE}"><title>{esc(label(n))}: {m:.1f} min</title></rect>')
        out.append(f'<text x="{X(m) + 8:.1f}" y="{y + 16}" font-size="11" fill="{C_INK2}">{m:.1f} min</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- tables
def table(headers, rows, cls="num"):
    h = "".join(f"<th>{esc(x)}</th>" for x in headers)
    b = "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>\n{b}\n</tbody></table></div>'


def results_table(summary, overhead):
    rows = []
    for n, e in sorted(summary["configs"].items(), key=lambda ne: plen(ne[0])):
        if not e.get("n_pairs"):
            rows.append([esc(label(n)), "", "0", "", "", "", "", "no pairs", "", "", "", ""])
            continue
        t = e["paired_t"]
        rows.append([esc(label(n)), f"{kv_tokens(n, overhead, e) / 1000:.1f}K", str(e["n_pairs"]), fmt(e["base_tps_mean"]), fmt(e["canon_tps_mean"]),
                     f"<b>{sfmt(e['gain_pct'])}</b>", fmt(t, 2), ("yes, " + e["direction"]) if e["resolved"] else ("incomplete (fewer than 3 pairs)" if e["n_pairs"] < 3 else "no"),
                     f"{fmt(e['base_ttft_ms_mean'], 0)} / {fmt(e['canon_ttft_ms_mean'], 0)}",
                     f"{fmt(e['base_min_tps'])} / {fmt(e['canon_min_tps'])}",
                     f"{fmt(e['base_p05_mean'])} / {fmt(e['canon_p05_mean'])}",
                     fmt((e['wall_s_mean'] or 0) / 60, 1)])
    return table(["cell", "KV tokens per engine step", "pairs", "nightly-deb TPS", "AMX-deb TPS", "gain %", "paired t", "resolved (|t| >= 4.303 and |gain| >= 1 %)",
                  "TTFT ms nightly / AMX", "slowest sample TPS nightly / AMX", "p05 TPS nightly / AMX", "min per cell"], rows)


def per_pass_table(summary):
    rows = []
    for n, e in sorted(summary["configs"].items(), key=lambda ne: plen(ne[0])):
        if not e.get("n_pairs"):
            continue
        pp = e["per_pass"]
        cells = [esc(label(n))]
        for k in (1, 2, 3):
            b, c = pp.get(f"base-pass{k}"), pp.get(f"canon-pass{k}")
            cells.append(f"{fmt(b['tps_mean']) if b else 'n/a'} / {fmt(c['tps_mean']) if c else 'n/a'}" + (f" ({100 * (c['tps_mean'] / b['tps_mean'] - 1):+.1f} %)" if b and c else ""))
        rows.append(cells)
    return table(["cell", "pass 1 nightly / AMX (gain)", "pass 2", "pass 3"], rows)


def quality_table(summary):
    rows = []
    for n, e in sorted(summary["configs"].items(), key=lambda ne: plen(ne[0])):
        if not e.get("n_pairs"):
            continue
        pp = e["per_pass"]
        spreads = []
        for tag, v in pp.items():
            r = v.get("engine_requests") or {}
            spreads.append("/".join(str(r.get(str(i), r.get(i, "?"))) for i in range(4)))
        pt = [v.get("prompt_tokens_mean") for v in pp.values() if v.get("prompt_tokens_mean")]
        ch = [v.get("cache_hit_pct") for v in pp.values() if v.get("cache_hit_pct") is not None]
        amx = e.get("amx_busy_cycles") or {}
        amx_b = [v for k, v in amx.items() if k.startswith("base") and v is not None]
        amx_c = [v for k, v in amx.items() if k.startswith("canon") and v is not None]
        hw = e.get("hwattn_ok_runs") or {}
        rows.append([esc(label(n)), "20", esc(", ".join(spreads)), esc(", ".join(e["uneven_spread_runs"]) or "none"),
                     esc(", ".join(e["caddy_health_event_runs"]) or "none"), str(e["anomalous_samples_total"]),
                     fmt(sum(pt) / len(pt), 0) if pt else "n/a", sfmt(e.get("overhead_tokens_mean"), 0), fmt(sum(ch) / len(ch), 1) if ch else "n/a",
                     (f"{max(amx_b) / 1e9:.1f}" if amx_b else "n/a") + " / " + (f"{min(amx_c) / 1e9:.1f}" if amx_c else "n/a"),
                     ("all yes" if hw and all(v is True for v in hw.values()) else esc(str(hw)))])
    return table(["cell", "requests per engine expected", "requests per engine, each pass-run (engine 0/1/2/3)", "uneven-spread runs",
                  "runs with Caddy health events", "anomalous samples (all runs)", "prompt tokens counted by the server (mean)", "server overhead vs prompt_length (tokens)",
                  "prefix-cache hits % (mean)", "AMX-busy cycles, billions: nightly max / AMX min", "USE_HW_ATTN=0 on every engine (per run)"], rows)


def identity_table(passes):
    rows = []
    for tag, rec in sorted(passes.items(), key=lambda kv: (int(kv[0].split("pass")[1]), kv[0].split("-")[0])):
        ver = (rec.get("versions") or {}).get("Tron (package)", "?")
        sha = (rec.get("installed_sha_env") or "?")[:16]
        probes = [p.get("amx_busy_cycles") for p in rec.get("amx_probes", []) if p.get("amx_busy_cycles") is not None]
        bad = [b for b in rec.get("binary_checks", []) if b.get("bad")]
        hw = rec.get("hwattn_checks", [])
        hw_txt = f"{sum(1 for h in hw if h.get('ok'))} of {len(hw)} ok" if hw else "n/a"
        ncfg = sum(1 for r in rec.get("results", []) if r.get("tps_results")) or sum(1 for r in rec.get("raw", []) if r.get("tpss"))
        rows.append([esc(tag), esc(ver), esc(sha), str(len(rec.get("binary_checks", []))), str(len(bad)), hw_txt,
                     f"{min(probes) / 1e9:.1f} to {max(probes) / 1e9:.1f}" if probes else "n/a", str(ncfg),
                     esc(rec.get("started", "?")), esc(rec.get("finished", "?")), fmt(rec.get("perf_minutes"), 0), esc(rec.get("stop") or "none")])
    return table(["pass-run", "tron package (posadm info)", "rinzler sha256 (first 16)", "binary checks", "checks with a bad pid", "USE_HW_ATTN=0 checks",
                  "AMX-busy cycles per probe, billions (min to max)", "cells with results", "started", "finished", "minutes", "stop"], rows)


def check_table(checks):
    rows = []
    for tag, rec in checks.items():
        raw = rec.get("raw", [])
        r0 = raw[0] if raw else {}
        tps = r0.get("tpss") or []
        pt = r0.get("prompt_tokens") or []
        fl = r0.get("fuse_limits") or {}
        fl_txt = ", ".join(f"{i}: {v.get('max_prompt_tokens')} / {v.get('max_total_tokens')}" for i, v in sorted(fl.items(), key=lambda kv: str(kv[0]))) or "n/a"
        rows.append([esc(tag), str(r0.get("prompt_length", "?")), (f"{min(pt)} to {max(pt)}" if pt else "n/a"), str(len(tps)), fmt(sum(tps) / len(tps)) if tps else "n/a", fmt(min(tps)) if tps else "n/a",
                     fmt(sum(r0.get("ttfts_ms", [0])) / max(1, len(r0.get("ttfts_ms", [0]))), 0), fmt((r0.get("wall_seconds") or 0) / 60, 1),
                     esc(str(r0.get("engine_requests"))), (f"{(r0.get('amx_busy_cycles') or 0) / 1e9:.1f}"), esc(str(r0.get("hwattn_ok"))), esc(fl_txt), esc(rec.get("stop") or "none")])
    return table(["cell", "prompt_length sent", "prompt tokens counted by the server", "requests", "TPS mean", "slowest sample", "TTFT ms", "minutes", "requests per engine",
                  "AMX-busy cycles (billions)", "USE_HW_ATTN=0 on every engine", "FUSE max_prompt_tokens / max_total_tokens per engine", "stop"], rows)


# ---------------------------------------------------------------- page
def build():
    summary, passes, checks, outcome, outcome_check, hist, prompt_check, l8b, l8b_src = load()
    overhead = observed_overhead(summary)
    v = summary.get("verdicts", {})
    band, curve, crossing = v.get("band_p1024", {}), v.get("curve", {}), v.get("crossing", {})
    e_ref = summary["configs"].get("ingested_qwen_3_4b_instruct_2507_tp2_8u_p1024", {})
    complete = [e for e in summary["configs"].values() if e.get("n_pairs") == 3]
    n_resolved = sum(1 for e in summary["configs"].values() if e.get("resolved"))
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    short = []
    band_word = "inside" if band.get("inside") is True else ("outside" if band.get("inside") is False else "undecided")
    curve_word = (curve.get("verdict") or "undecided").split(":")[0]
    cross_p = crossing.get("prompt_length")
    if complete:
        gains = sorted((plen(n), e["gain_pct"]) for n, e in summary["configs"].items() if e.get("n_pairs") == 3)
        short.append(f"With software (CPU) attention forced on both arms, the canonical-AMX deb changed qwen3-4b tp2 decode speed by {sfmt(e_ref.get('gain_pct'), 1)} % at the nightly's own shape (prompt 1024, 2 users per engine) and by {sfmt(gains[-1][1], 1)} % at prompt {gains[-1][0]}, each over 3 interleaved passes on the whole of delphi-3bda with the nightly's own client and layout.")
        short.append(f"The pre-registered verdicts (section 3) read: band at prompt 1024 {band_word}, curve {curve_word}, crossing " + (f"at prompt {cross_p}" if cross_p else "not reached") + f", with {len(complete)} of {len(summary['configs'])} cells complete and {n_resolved} resolved.")
    else:
        short.append("The six passes have not produced 3 paired passes yet, so this page shows the check cell and the campaign state for the comparison of the nightly deb (no AMX code) with the canonical-AMX deb on qwen3-4b tp2, software attention forced on both arms (USE_HW_ATTN=0), prompt 1024 to 8192 at 2 users per engine.")
        short.append(f"Campaign state: {outcome}.")
    short.append(f"Every TPS here is far below the nightly's own qwen3-4b number (about {CTX_NIGHTLY_FPGA[0]:.0f} TPS with FPGA attention) because both arms run software attention, which is where the AMX kernel works (section 4), and every request generates {GEN_TOKENS} tokens, the nightly's generation length, with only the prompt length varying between cells.")
    words = [
        ("tron, rinzler, engine, tp2", "tron is the inference program under test; rinzler is its production server; one running rinzler is one engine; tp2 = two FPGA cards per engine. The nightly layout is 4 tp2 engines behind the Caddy proxy on port 80."),
        ("qwen3-4b, GPTQ, bf16", "The ingested model ingested-qwen-3-4b-instruct-2507-tp2 (Qwen/Qwen3-4B-Instruct-2507): 36 layers, 8 KV heads of 128 values, 144 KiB of KV cache per token in bf16. GPTQ = a 4-bit weight quantization format; bf16 = the 16-bit floating-point format the KV cache is stored in."),
        ("KV, KV head, KV cache", "KV = key and value, the two per-token vectors attention stores for every layer; a KV head is one set of them (8 per layer for this model); the KV cache is their store for a request's context. KV tokens per engine step = users per engine x context per user, the attention work of one decode step."),
        ("platformd, posadm, Caddy, FUSE", "platformd is the machine's service manager that starts the rinzler engines from its saved configuration; posadm is its command-line client; Caddy is the reverse proxy on port 80 that spreads requests over the engines; FUSE is the file system each rinzler exposes under /var/run/rinzler/N/ with its counters (prompts_total = requests admitted) and its configuration limits (max_prompt_tokens, max_total_tokens, both in tokens)."),
        ("nightly deb, canonical-AMX deb (the two arms)", "The nightly deb is the package the nightly CI installed on 2026-09-18 (tron 2026.09.18-3faba6d0, built without the AMX kernel). The canonical-AMX deb is the same source plus one CMake preset line (TRON_AMX_DISPATCH=ON), so its rinzler contains the AMX attention kernel of PR #3879 in its canonical form (no K mirror, no VNNI K). An arm is one installed package; a pass is one run of all cells on one arm."),
        ("AMX, AVX", "Intel Advanced Matrix Extensions and Advanced Vector Extensions, two CPU instruction sets. The nightly deb computes attention with AVX; the canonical-AMX deb with AMX. AMX-busy cycles come from the CPU counter EXE.AMX_BUSY read with perf stat for 20 s on the engine processes before each cell: about 0 on the nightly deb, billions on the AMX deb."),
        ("software attention, hardware attention, USE_HW_ATTN", "Software attention = attention computed on the CPU (AVX or AMX); hardware attention = attention computed on the FPGA. USE_HW_ATTN is the environment variable that selects it: unset = hardware attention for ingested models such as qwen3-4b from query position 127 on; USE_HW_ATTN=0 = software attention for every model. The campaign sets USE_HW_ATTN=0 for every engine through /opt/positron/user/config.env (the rinzler unit reads that file last, at engine start), verifies it in every engine's /proc/PID/environ after every start, and clears the file before production comes back up."),
        ("CI harness, cell, TPS, TTFT, slowest sample, p05", "The CI harness is the nightly's client code (systems_test scripts/perf.py). A cell is one line of its config table: model, number of users, prompt length. TPS = decode tokens per second per user, measured between generated tokens 896 and 1024 of every request, averaged over 10 rounds of all 8 users. TTFT = time to first token in ms. Slowest sample = the lowest single-request TPS. p05 = the 5th percentile of the request TPS values."),
        ("prompt length, generated tokens, users per engine", "prompt length = the tokens the harness sends (its own count); every request then generates 1536 tokens. The harness's 8 users are spread by Caddy over the 4 engines, so 2 users per engine. The KV-tokens column of the tables is 2 x (prompt + the cell's measured server overhead + 960 generated tokens at the middle of the TPS window)."),
        ("server overhead", "Prompt tokens counted by the server minus the harness's prompt_length. The harness counts with llama header strings and drops the first token of every part (the qwen tokenizer has no BOS token, so a real token is dropped and each part loses its first few characters, exactly as in the nightly); the server applies the qwen chat template. The difference is measured per cell and used in the KV arithmetic."),
        ("gain, paired t, resolved", "gain = AMX-deb mean TPS over nightly-deb mean TPS minus 1, in percent, over the 3 passes. Paired t = mean of the 3 per-pass TPS differences divided by their standard error (pass k of one arm pairs with pass k of the other). Resolved = |t| >= 4.303 (the 95 % two-sided limit of Student's t with 2 degrees of freedom) and |gain| >= 1 %."),
        ("band, curve, crossing (plan section 7)", "band: the gain at prompt 1024 against +5.4 to +11.4 % (the p0perf-20260913 measurement of this exact load, +8.4 %, plus or minus 3 points). curve: in prompt-length order, every resolved cell must gain at least the previous resolved cell's gain minus 2 points. crossing: the shortest prompt length whose gain is resolved and at least +10 %."),
        ("ShareGPT prompts, prefix cache", "The harness builds prompts from ShareGPT conversations; above one conversation's length the campaign's driver checkout concatenates following conversations (one code change, prompt-1024 prompts unchanged). Same seeds in every cell, so a longer prompt of a seed starts with the shorter prompt of the same seed sent minutes earlier; rinzler's prefix cache then serves that prefix when Caddy routes the request to the same engine. This affects TTFT and prefill, not the TPS window."),
    ]
    starts = [l for l in hist if "campaign start (" in l]
    deviations = [
        "Two launches instead of one (plan section 2): the executing agent started at 21:09 UTC on 2026-09-19, past the 20:30 UTC deadline for a full Saturday run, so the check cell (8 users x prompt 8192, canonical deb) was run on Saturday night in a check-only mode and the six passes in the Sunday window. The restore-target rule of plan section 1 applies to the Sunday run: the base arm stays the 2026-09-18 nightly deb, the package found installed at preflight is reinstalled at the end. The status lines below record what each run did.",
        "The check cell's prompt-token rule is a band around prompt_length (its bounds are in the 'campaign start' status line, PT_BAND) instead of the plan's [8192, 8400]: the qwen chat template counts fewer tokens than the harness's llama-header counting (measured offline on the campaign's prompts before launch), so the server counts slightly fewer tokens than prompt_length; the rule exists to catch a silent truncation (as with llama-3.1-8b at 4096), which shows as a count far below prompt_length. The check also requires AMX-busy of at least 10 billion cycles on the canonical deb and rinzler's FUSE limits above the cell's need (plan section 6).",
        "The offline prompt check's 'first part is the system line' assertion was relaxed to 'a suffix of the system line' for the qwen tokenizer (the harness drops the first token of every part; see server overhead in the words list). Nothing in the harness or its prompts was changed for this.",
        "The driver timeout per pass and the check timeout are recorded in the 'campaign start' status line of each run (DRIVER_TIMEOUT, CHECK_TIMEOUT); the plan's values were 3600 s and 1200 s." + (" Recorded: " + "; ".join(esc(x.split("(", 1)[1].rstrip(")")) for x in starts) if starts else ""),
        "Rules in force (from the reviewed llama-campaign driver): engines are restarted after every package switch (serving-down, serving-up with a wait for platformd idle), because the legacy provisioning path never restarts a same-model engine; USE_HW_ATTN=0 is verified after every start and after every provisioning; a failed pass is repeated once after an engine restart; a cell counts as a systematic failure only after failing twice in one pass-run; the CI lease is re-checked before every pass, every provisioning and every cell.",
        "Per-engine request counts were read from rinzler's FUSE stats (prompts_total), since the journal has no per-request line.",
        "No dead-man switch for config.env exists on the machine (a transient systemd timer was designed but its creation was refused by the agent's permission classifier as unauthorized persistence): if the client host had died mid-run, USE_HW_ATTN=0 would have stayed in config.env until cleared by hand. The status lines show whether the restore's hwattn-clear ran.",
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
    parts.append(f"<title>qwen3-4b AMX prompt sweep</title>\n<style>{css}</style>\n<main>")
    parts.append("<h1>AMX gain on qwen3-4b tp2 against prompt length, software attention on both arms</h1>")
    parts.append(f'<p class="sub">Whole delphi-3bda, nightly layout (4 tp2 engines behind Caddy), CI harness, 2 users per engine, USE_HW_ATTN=0 on both arms. Plan: CI-test/status/qwen3-4b-Saturday-plan.md. Generated {now} by exec/q4b-swattn-20260919/gen_report.py from {esc(RES)}. Every campaign number comes from the result files named in section 8; context numbers from other campaigns carry their source.</p>')
    parts.append('<div class="short"><p><b>Short version.</b></p>' + "".join(f"<p>{esc(s)}</p>" for s in short) + "</div>")
    parts.append("<h2>Words used here</h2><dl>" + "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in words) + "</dl>")
    parts.append("<h2>1. What ran</h2>")
    cfg_used = os.path.basename(open(os.path.join(RES, 'configs-used.txt')).read().strip()) if os.path.isfile(os.path.join(RES, 'configs-used.txt')) else 'unknown'
    pc_txt = "see prompt-check/"
    if prompt_check:
        pc_txt = f"{prompt_check.get('total_exceptions')} exceptions over {sum(c.get('n_ok', 0) for c in prompt_check.get('cells', {}).values())} prompts, stored lists unchanged {prompt_check.get('stored_lists_unchanged')}, prompt-1024 identical to the previous code {prompt_check.get('identity_1024_ok')}"
    parts.append("<ul>"
                 "<li>Machine: the whole of delphi-3bda (Intel Granite Rapids, 8 FPGA cards), 4 tp2 engines provisioned by platformd behind Caddy on port 80, exactly the nightly layout. The nightly CI lease was free and Bill's marker taken for the run.</li>"
                 "<li>Client: the nightly's own perf code (systems_test scripts/perf.py) run from claude-agentsrv through the campaign driver (st_ci_perf.py), which records every request, the layout, the engine binary and environment per pass and the AMX-busy probe. Talos (the CI results database) was replaced by a recording stub; nothing reached CI records.</li>"
                 f"<li>Arms: nightly deb against canonical-AMX deb, both with USE_HW_ATTN=0, 3 passes each, interleaved (base, canon, base, canon, base, canon). Passes found: {esc(', '.join(summary['passes_found']) or 'none yet')}.</li>"
                 f"<li>Cells per pass: {len(summary['configs']) or 'n/a'} (ingested-qwen-3-4b-instruct-2507-tp2, 8 users = 2 per engine, {GEN_TOKENS} generated tokens, TPS window 896 to 1024). Config file used: {esc(cfg_used)}.</li>"
                 f"<li>Prompt source: ShareGPT with concatenation above one conversation's length; offline check with the qwen tokenizer: {esc(pc_txt)}.</li>"
                 f"<li>Tokens the server counted around the prompt (server overhead, measured here): {fmt(overhead, 1)}.</li>"
                 + (f"<li>Check-only run outcome: {esc(outcome_check)}.</li>" if outcome_check else "") +
                 "</ul>")
    if checks:
        parts.append("<h3>The check cell before the first pass (8 users x the longest prompt, canonical-AMX deb, software attention)</h3>")
        parts.append(check_table(checks))
        parts.append('<p class="cap">The check cell decides whether the longest prompt is measurable: rc 0, every engine with USE_HW_ATTN=0, server-counted prompt tokens within 400 of prompt_length (no silent truncation), AMX-busy above 10 billion cycles, FUSE limits above 9800. Its duration is the upper bound for the pass-time estimate.</p>')
    if passes:
        parts.append("<h3>Identity of every pass-run</h3>")
        parts.append(identity_table(passes))
        parts.append('<p class="cap">The binary check compares every engine process with the installed rinzler (sha256) after each provisioning; the USE_HW_ATTN=0 check reads every engine\'s environment; a pass stops if any engine runs a deleted or foreign binary or lacks the key. AMX-busy cycles prove which kernel ran.</p>')
    parts.append("<h2>2. Results per prompt length</h2>")
    parts.append('<div class="fig">' + chart_dumbbell(summary, overhead) + '<p class="cap">Figure 1. Each row is one prompt length; the light dot is the nightly deb (AVX attention), the dark dot the canonical-AMX deb (AMX attention), both the mean TPS over 3 passes. The label is the AMX gain in percent. Hover a dot for the paired t.</p></div>')
    parts.append(results_table(summary, overhead))
    if any(e.get("n_pairs") for e in summary["configs"].values()):
        parts.append("<h3>Per pass</h3>" + per_pass_table(summary))
    if summary.get("incomplete"):
        parts.append("<p>Incomplete cells (fewer than 3 paired passes; excluded from the verdicts): " + esc(", ".join(f"{label(i['name'])} ({i['n_pairs']} pairs)" for i in summary["incomplete"])) + ".</p>")
    parts.append("<h2>3. Gain against prompt length, with the llama curve</h2>")
    parts.append('<div class="fig">' + chart_gain_vs_prompt(summary, l8b, l8b_src) + '<p class="cap">Figure 2. Blue: this campaign. Orange: llama-3.1-8b at the same load, same harness and machine, one day earlier (its 7168 and 8192 cells were lost to a tokenizer truncation at 4096). Grey: qwen3-4b runtron measurements on one engine (data F), a different client and layout, drawn as context only. The aqua band marks the pre-registered band at prompt 1024; the dashed aqua line is the +10 % crossing rule.</p></div>')
    parts.append('<div class="verdict"><p><b>Band at prompt 1024</b> (pre-registered +5.4 to +11.4 %, from p0perf-20260913: 140.61 to 152.46 TPS, +8.4 %): ' + esc(f"measured {sfmt(band.get('gain'), 2)} %, {band_word}.") + f"</p><p>Verdict: {esc(band.get('verdict', 'n/a'))}.</p></div>")
    parts.append('<div class="verdict"><p><b>Curve</b> (monotone within 2 points over the resolved cells, in prompt-length order): ' + esc(f"resolved cells {', '.join(f'{p}: {g:+.2f} %' for p, g in curve.get('resolved_cells', []))}; unresolved: {curve.get('unresolved_cells', [])}.") + f"</p><p>Verdict: {esc(curve.get('verdict', 'n/a'))}.</p></div>")
    parts.append('<div class="verdict"><p><b>Crossing</b> (shortest prompt length with a resolved gain of at least +10 %): ' + esc(f"prompt {cross_p}" if cross_p else "none reached") + f".</p><p>Verdict: {esc(crossing.get('verdict', 'n/a'))}. No recommendation is made here (plan section 7); the CI-AMX-test-shapes page carries the decision.</p></div>")
    parts.append("<h2>4. Why the TPS level is far below the nightly's number</h2>")
    parts.append('<div class="fig">' + chart_level(summary) + '<p class="cap">Figure 3. The nightly runs qwen3-4b tp2 with FPGA attention (grey, top two bars: canon-ci 2026-09-18). With USE_HW_ATTN=0 the same load ran at about 141 TPS without AMX and 152 TPS with AMX on our half of the machine (grey, p0perf-20260913). This campaign forces software attention on both arms, so its level (blue, when the passes exist) is comparable to the lower grey pair, not to the nightly. The point of the setup: with FPGA attention the AMX kernel touches only the CPU share of attention (positions 0 to 126) and the nightly number moves +0.1 %; software attention is where the kernel runs.</p></div>')
    parts.append("<p>Sources: " + esc(CTX_NIGHTLY_FPGA[2]) + "; " + esc(CTX_P0PERF[2]) + ".</p>")
    parts.append("<h2>5. Data quality</h2>")
    parts.append(quality_table(summary))
    parts.append('<p class="cap">Requests per engine come from rinzler\'s prompts_total counter read before and after each cell; the expected value is 8 users x 10 rounds / 4 engines = 20. Caddy health events are health-checker lines in Caddy\'s journal during the cell. Anomalous samples are harness samples above 1000 TPS (a client-side stall indicator). Prefix-cache hits are inflated for the longer-prompt cells by the same-seed prompts of earlier cells; the TPS window is not affected. The server overhead column is the measured difference between the server\'s prompt token count and prompt_length.</p>')
    dur = chart_durations(summary)
    if dur:
        parts.append('<div class="fig">' + dur + '<p class="cap">Figure 4. Wall time of one cell (10 rounds) including prompt generation and the harness\'s own waits; the AMX-busy probe and the layout snapshot are not included.</p></div>')
    parts.append("<h2>6. Decisions taken during the run (plan section 2a) and deviations from the plan text</h2><ul>" + "".join(f"<li>{esc(d)}</li>" for d in deviations) + "</ul>")
    parts.append("<h3>Campaign status lines</h3><pre style=\"font-size:12px;overflow-x:auto;background:#fcfcfb;border:1px solid #e1e0d9;padding:8px\">" + esc("\n".join(l for l in hist if "waiting: CI lease busy" not in l and "waiting: NOT_BEFORE" not in l)) + "</pre>")
    parts.append("<h2>7. What this does and does not show</h2><ul>"
                 "<li>It shows the AMX kernel's own effect on qwen3-4b tp2 decode speed against prompt length, in the nightly's layout and load, when attention runs on the CPU. It does not show what the nightly would measure: the nightly runs this model with FPGA attention, where the kernel touches only positions 0 to 126.</li>"
                 "<li>Both arms ran the same client code, prompts, layout, machine and attention mode, alternating, so a common drift affects both passes of a pair; the paired t uses only within-pair differences.</li>"
                 "<li>TTFT and prefix-cache figures for prompts above 1024 are affected by warm prefixes (see the words list); decode TPS is not.</li>"
                 "<li>PR #4424 (VNNI K) is in neither package.</li>"
                 "</ul>")
    parts.append("<h2>8. Files</h2><ul>"
                 f"<li>Results: <code>{esc(RES)}</code> (per pass: perf.json, talos.json, driver.log, summary.txt; check-8u-p8192/ the check cell; prompt-check/ the offline check; summary.json and summary.txt from analyze.py; preflight.txt; base-identity.txt; outcome.txt; status-history.log).</li>"
                 "<li>Scripts: <code>exec/q4b-swattn-20260919/</code> (campaign.sh, launch.sh, dut.sh, st_ci_perf.py, configs.py, prompt_check.py, analyze.py, gen_report.py; .orig/ holds the llama-campaign files they were copied from).</li>"
                 "<li>Plan: <code>CI-test/status/qwen3-4b-Saturday-plan.md</code>; precedent campaign and report: <code>exec/l8b-levers-20260919/</code>, <code>CI-test/status/Saturday-llama-3.1-8b.html</code>.</li>"
                 "<li>Prompt-source change: <code>exec/q4b-swattn-20260919/prompt.py.patch</code> applied to the driver's checkout ~/workspace/ai-runs/systems_test (uncommitted; the nightly's checkout is untouched).</li>"
                 "</ul></main>")
    page = "\n".join(parts)
    page = page.encode("ascii", "xmlcharrefreplace").decode("ascii")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(page)} bytes, ascii)")


if __name__ == "__main__":
    build()
