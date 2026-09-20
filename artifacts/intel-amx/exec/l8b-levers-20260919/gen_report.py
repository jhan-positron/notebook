#!/usr/bin/env python3
"""Report of the l8b-levers campaign (Saturday plan section 9): CI-test/status/Saturday-llama-3.1-8b.html.

Reads summary.json (analyze.py) and the pass records perf.json under the results directory, writes one light-theme
HTML page with inline SVG charts (pure ASCII output: the artifact publisher mangles non-ASCII bytes). Every number on
the page comes from those files; nothing is typed in by hand.
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

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/CI-test/status/Saturday-llama-3.1-8b.html"
GEN_TOKENS = 1536
WINDOW_MID = (896 + 1024) // 2   # generated tokens at the middle of the TPS window
USERS_PER_ENGINE = {4: 1, 8: 2, 16: 4, 32: 8}

# reference palette (dataviz skill, light mode; the page is single-theme light by jhan's rule)
C_BLUE, C_BLUE_LIGHT, C_ORANGE, C_AQUA = "#2a78d6", "#86b6ef", "#eb6834", "#1baf7a"
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
    """Split text into lines of at most `width` characters at spaces."""
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


def load():
    summary = json.load(open(os.path.join(RES, "summary.json")))
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
    outcome = open(os.path.join(RES, "outcome.txt")).read().strip() if os.path.isfile(os.path.join(RES, "outcome.txt")) else "outcome.txt missing (campaign still running or aborted before its end)"
    hist = open(os.path.join(RES, "status-history.log")).read().splitlines() if os.path.isfile(os.path.join(RES, "status-history.log")) else []
    prompt_check = None
    pc = os.path.join(RES, "prompt-check", "run1.json")
    if os.path.isfile(pc):
        prompt_check = json.load(open(pc))
    return summary, passes, checks, outcome, hist, prompt_check


def observed_overhead(summary):
    """Server-counted prompt tokens minus prompt_length, from the per-pass records (the plan assumed 31, data B)."""
    vals = []
    for n, e in summary["configs"].items():
        _, p = parse_name(n)
        for pv in e.get("per_pass", {}).values():
            if pv.get("prompt_tokens_mean"):
                vals.append(pv["prompt_tokens_mean"] - p)
    return (sum(vals) / len(vals)) if vals else None


def kv_tokens(n, overhead):
    u, p = parse_name(n)
    return USERS_PER_ENGINE[u] * (p + (overhead if overhead is not None else 31) + WINDOW_MID)


# ---------------------------------------------------------------- charts
def chart_dumbbell(summary, overhead):
    rows = [(n, e) for n, e in summary["configs"].items() if e.get("n_pairs")]
    rows.sort(key=lambda ne: kv_tokens(ne[0], overhead))
    if not rows:
        return "<p>No paired pass yet.</p>"
    W, left, right, rowh, top = 960, 300, 210, 46, 96
    Hh = top + rowh * len(rows) + 50
    xmax = max(max(e["base_tps_mean"], e["canon_tps_mean"]) for _, e in rows) * 1.05
    xmin = 0
    def X(v):
        return left + (v - xmin) / (xmax - xmin) * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="Decode TPS per config, nightly deb against canonical AMX deb" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(svg_text_lines(20, 22, ["Decode TPS per config: nightly deb (light dot) against canonical-AMX deb (dark dot)"], 15, C_INK, "600", 18))
    out.append(svg_text_lines(20, 44, wrap("Mean of 3 passes. Rows sorted by KV tokens per engine step. The label on each row is the gain of the AMX deb in percent; n.r. = not resolved by the pre-registered rule.", 130), 12, C_INK2, "400", 15))
    out.append(f'<circle cx="26" cy="{top - 18}" r="5" fill="{C_BLUE_LIGHT}"/><text x="36" y="{top - 14}" font-size="11" fill="{C_INK2}">nightly deb (no AMX code)</text>')
    out.append(f'<circle cx="216" cy="{top - 18}" r="5" fill="{C_BLUE}"/><text x="226" y="{top - 14}" font-size="11" fill="{C_INK2}">canonical-AMX deb</text>')
    # grid
    step = 20 if xmax > 100 else 10
    v = 0
    while v <= xmax:
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{Hh - 40}" stroke="{C_GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{Hh - 24}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{v}</text>')
        v += step
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 6}" font-size="11" fill="{C_MUTED}" text-anchor="middle">tokens per second per user (TPS), mean of the users of a config</text>')
    for i, (n, e) in enumerate(rows):
        y = top + rowh * i + rowh / 2
        b, c = e["base_tps_mean"], e["canon_tps_mean"]
        xb, xc = X(b), X(c)
        u, p = parse_name(n)
        out.append(f'<text x="{left - 12}" y="{y + 4}" font-size="12" fill="{C_INK}" text-anchor="end">{esc(label(n))}</text>')
        out.append(f'<text x="{left - 12}" y="{y + 17}" font-size="10" fill="{C_MUTED}" text-anchor="end">{kv_tokens(n, overhead) / 1000:.1f}K KV tokens per step</text>')
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


def chart_gain_vs_kv(summary, overhead):
    rows = [(n, e) for n, e in summary["configs"].items() if e.get("n_pairs")]
    if not rows:
        return ""
    W, Hh, left, right, top, bottom = 960, 470, 70, 40, 112, 60
    xs = [kv_tokens(n, overhead) / 1000 for n, _ in rows]
    gains = [e["gain_pct"] for _, e in rows] + [g for _, e in rows for g in e["gain_pct_per_pass"]]
    xmax = max(xs) * 1.12
    ymin, ymax = min(0, min(gains)) - 1.5, max(gains) + 2.5
    def X(v):
        return left + v / xmax * (W - left - right)
    def Y(v):
        return top + (ymax - v) / (ymax - ymin) * (Hh - top - bottom)
    ctx_prompts = sorted({parse_name(n)[1] for n, _ in rows if USERS_PER_ENGINE[parse_name(n)[0]] == 2 and parse_name(n)[1] != 1024})
    other = [n for n, _ in rows if parse_name(n)[1] != 1024 and USERS_PER_ENGINE[parse_name(n)[0]] != 2]
    other_txt = ", ".join(f"{USERS_PER_ENGINE[parse_name(n)[0]]} users x {parse_name(n)[1]}" for n in other) or "none"

    def group(n):
        u, p = parse_name(n)
        if p == 1024:
            return "users lever (prompt 1024, 2 to 8 users per engine)", C_BLUE
        if USERS_PER_ENGINE[u] == 2:
            return f"context lever (2 users per engine, prompt {ctx_prompts[0]} to {ctx_prompts[-1]})" if ctx_prompts else "context lever", C_ORANGE
        return f"other cells ({other_txt})", C_AQUA
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="AMX gain against KV tokens per engine step" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="20" y="22" font-size="15" font-weight="600" fill="{C_INK}">Gain of the AMX deb against the attention work of one decode step</text>')
    out.append(svg_text_lines(20, 42, wrap("Dot = mean gain over 3 passes; thin bar = lowest and highest single-pass gain; hollow dot = not resolved by the rule. x = users per engine x (prompt + measured server overhead + 960 generated tokens).", 130), 12, C_INK2, "400", 15))
    gy = math.floor(ymin)
    while gy <= ymax:
        if gy % 2 == 0:
            out.append(f'<line x1="{left}" y1="{Y(gy):.1f}" x2="{W - right}" y2="{Y(gy):.1f}" stroke="{C_GRID if gy else C_AXIS}" stroke-width="1"/>')
            out.append(f'<text x="{left - 8}" y="{Y(gy) + 4:.1f}" font-size="11" fill="{C_MUTED}" text-anchor="end">{gy:+d}</text>')
        gy += 1
    gx = 0
    while gx <= xmax:
        out.append(f'<text x="{X(gx):.1f}" y="{Hh - bottom + 18}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{gx}K</text>')
        gx += 4
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 8}" font-size="11" fill="{C_MUTED}" text-anchor="middle">KV tokens per engine step (thousands), at the middle of the TPS window</text>')
    out.append(f'<text transform="translate(16,{(top + Hh - bottom) / 2:.1f}) rotate(-90)" font-size="11" fill="{C_MUTED}" text-anchor="middle">gain of the AMX deb, percent of the nightly TPS</text>')
    seen = {}
    placed = []   # (x0, y0, x1, y1) boxes of point labels, to avoid collisions
    for n, e in sorted(rows, key=lambda ne: kv_tokens(ne[0], overhead)):
        x = X(kv_tokens(n, overhead) / 1000)
        g = e["gain_pct"]
        gname, col = group(n)
        seen[gname] = col
        lo, hi = min(e["gain_pct_per_pass"]), max(e["gain_pct_per_pass"])
        out.append(f'<line x1="{x:.1f}" y1="{Y(lo):.1f}" x2="{x:.1f}" y2="{Y(hi):.1f}" stroke="{col}" stroke-width="2" opacity="0.6"/>')
        fill = col if e["resolved"] else C_SURF
        title = f"{label(n)}: {g:+.2f} % (passes {', '.join(f'{v:+.1f}' for v in e['gain_pct_per_pass'])}), {kv_tokens(n, overhead) / 1000:.1f}K KV tokens per step"
        out.append(f'<circle cx="{x:.1f}" cy="{Y(g):.1f}" r="6" fill="{fill}" stroke="{col}" stroke-width="2"><title>{esc(title)}</title></circle>')
        u, p = parse_name(n)
        txt = f"{USERS_PER_ENGINE[u]}u x {p}"
        tw = 6 * len(txt)
        candidates = [(x + 9, Y(g) - 8), (x + 9, Y(g) + 16), (x - 9 - tw, Y(g) - 8), (x - 9 - tw, Y(g) + 16), (x + 9, Y(g) + 30)]
        for lx_, ly_ in candidates:
            box = (lx_, ly_ - 10, lx_ + tw, ly_ + 2)
            if not any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in placed):
                break
        placed.append(box)
        out.append(f'<text x="{lx_:.1f}" y="{ly_:.1f}" font-size="10" fill="{C_INK2}">{esc(txt)}</text>')
    ly = 72
    for gname, col in seen.items():
        out.append(f'<circle cx="26" cy="{ly - 4}" r="5" fill="{col}"/><text x="36" y="{ly}" font-size="11" fill="{C_INK2}">{esc(gname)}</text>')
        ly += 14
    out.append("</svg>")
    return "\n".join(out)


def chart_durations(summary):
    rows = [(n, e) for n, e in summary["configs"].items() if e.get("n_pairs") and e.get("wall_s_mean")]
    if not rows:
        return ""
    rows.sort(key=lambda ne: ne[1]["wall_s_mean"])
    W, left, right, rowh, top = 960, 300, 80, 26, 44
    Hh = top + rowh * len(rows) + 40
    xmax = max(e["wall_s_mean"] for _, e in rows) / 60 * 1.15
    def X(v):
        return left + v / xmax * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="Minutes per config" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="{left}" y="22" font-size="15" font-weight="600" fill="{C_INK}">Wall time of one config (10 rounds), mean over the passes, minutes</text>')
    for i, (n, e) in enumerate(rows):
        y = top + rowh * i
        m = e["wall_s_mean"] / 60
        out.append(f'<text x="{left - 10}" y="{y + 16}" font-size="12" fill="{C_INK}" text-anchor="end">{esc(label(n))}</text>')
        out.append(f'<rect x="{left}" y="{y + 4}" width="{X(m) - left:.1f}" height="16" rx="0" fill="{C_BLUE}"><title>{esc(label(n))}: {m:.1f} min</title></rect>')
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
    for n, e in sorted(summary["configs"].items(), key=lambda ne: kv_tokens(ne[0], overhead)):
        if not e.get("n_pairs"):
            rows.append([esc(label(n)), "0", "", "", "", "", "no pairs", "", "", "", ""])
            continue
        t = e["paired_t"]
        rows.append([esc(label(n)), str(e["n_pairs"]), fmt(e["base_tps_mean"]), fmt(e["canon_tps_mean"]),
                     f"<b>{sfmt(e['gain_pct'])}</b>", fmt(t, 2), ("yes, " + e["direction"]) if e["resolved"] else "no",
                     f"{fmt(e['base_ttft_ms_mean'], 0)} / {fmt(e['canon_ttft_ms_mean'], 0)}",
                     f"{fmt(e['base_min_tps'])} / {fmt(e['canon_min_tps'])}",
                     f"{fmt(e['base_p05_mean'])} / {fmt(e['canon_p05_mean'])}",
                     fmt((e['wall_s_mean'] or 0) / 60, 1)])
    return table(["config", "pairs", "nightly TPS", "AMX TPS", "gain %", "paired t", "resolved (|t| >= 4.303 and |gain| >= 1 %)",
                  "TTFT ms nightly / AMX", "slowest sample TPS nightly / AMX", "p05 TPS nightly / AMX", "min per config"], rows)


def per_pass_table(summary, overhead):
    rows = []
    for n, e in sorted(summary["configs"].items(), key=lambda ne: kv_tokens(ne[0], overhead)):
        if not e.get("n_pairs"):
            continue
        pp = e["per_pass"]
        cells = [esc(label(n))]
        for k in (1, 2, 3):
            b, c = pp.get(f"base-pass{k}"), pp.get(f"canon-pass{k}")
            cells.append(f"{fmt(b['tps_mean']) if b else 'n/a'} / {fmt(c['tps_mean']) if c else 'n/a'}" + (f" ({100 * (c['tps_mean'] / b['tps_mean'] - 1):+.1f} %)" if b and c else ""))
        rows.append(cells)
    return table(["config", "pass 1 nightly / AMX (gain)", "pass 2", "pass 3"], rows)


def quality_table(summary, overhead):
    rows = []
    for n, e in sorted(summary["configs"].items(), key=lambda ne: kv_tokens(ne[0], overhead)):
        if not e.get("n_pairs"):
            continue
        u, p = parse_name(n)
        expect = u * 10 // 4
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
        rows.append([esc(label(n)), str(expect), esc(", ".join(spreads)), esc(", ".join(e["uneven_spread_runs"]) or "none"),
                     esc(", ".join(e["caddy_health_event_runs"]) or "none"), str(e["anomalous_samples_total"]),
                     fmt(sum(pt) / len(pt), 0) if pt else "n/a", fmt(sum(ch) / len(ch), 1) if ch else "n/a",
                     (f"{max(amx_b) / 1e9:.1f}" if amx_b else "n/a") + " / " + (f"{min(amx_c) / 1e9:.1f}" if amx_c else "n/a")])
    return table(["config", "requests per engine expected", "requests per engine, each pass-run (engine 0/1/2/3)", "uneven-spread runs",
                  "runs with Caddy health events", "anomalous samples (all runs)", "prompt tokens counted by the server (mean)",
                  "prefix-cache hits % (mean)", "AMX-busy cycles, billions: nightly max / AMX min"], rows)


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
    summary, passes, checks, outcome, hist, prompt_check = load()
    overhead = observed_overhead(summary)
    v = summary["verdicts"]
    pair, triple = v["pair_16k"], v["triple_8k"]
    e_ref = summary["configs"].get("llama_3_1_8b_instruct_good_tp2_8u_p1024", {})
    e_t1 = summary["configs"].get("llama_3_1_8b_instruct_good_tp2_32u_p1024", {})
    n_complete = sum(1 for e in summary["configs"].values() if e.get("n_pairs") == 3)
    n_resolved = sum(1 for e in summary["configs"].values() if e.get("resolved"))
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    check_rows = []
    for tag, rec in checks.items():
        raw = rec.get("raw", [])
        r0 = raw[0] if raw else {}
        tps = r0.get("tpss") or []
        pt = r0.get("prompt_tokens") or []
        check_rows.append([esc(tag), str(r0.get("prompt_length", "?")), (f"{min(pt)} to {max(pt)}" if pt else "n/a"), str(len(tps)), fmt(sum(tps) / len(tps)) if tps else "n/a", fmt(min(tps)) if tps else "n/a",
                           fmt(sum(r0.get("ttfts_ms", [0])) / max(1, len(r0.get("ttfts_ms", [0]))), 0), fmt((r0.get("wall_seconds") or 0) / 60, 1),
                           esc(str(r0.get("engine_requests"))), (f"{(r0.get('amx_busy_cycles') or 0) / 1e9:.1f}"), esc(rec.get("stop") or "none")])
    short = []
    if e_t1.get("n_pairs") == 3 and e_ref.get("n_pairs") == 3:
        short.append(f"On the whole of delphi-3bda, with the nightly's own client and layout, the canonical-AMX deb changed llama-3.1-8b decode speed by {sfmt(e_ref['gain_pct'], 1)} % at today's nightly shape (2 users per engine, prompt 1024) and by {sfmt(e_t1['gain_pct'], 1)} % at the recommended shape (8 users per engine, prompt 1024), each over 3 interleaved passes.")
    else:
        short.append("The campaign did not complete all three passes for the reference cells; see the incomplete list.")
    short.append(f"Every cell in this report generates {GEN_TOKENS} tokens per request, the nightly's own generation length (perf.py generate_length), and measures TPS between generated tokens 896 and 1024. Only the prompt length and the user count vary between cells.")
    short.append(f"The pre-registered 16K pair says: {pair['verdict']}. The 8K triple says: {triple['verdict']}.")
    short.append(f"{n_complete} of {len(summary['configs'])} configs have all 3 passes on both arms and {n_resolved} are resolved by the rule |t| >= 4.303 and |gain| >= 1 %; the campaign outcome line reads: {outcome}.")
    words = [
        ("tron, rinzler, engine, tp2", "tron is the inference program under test; rinzler is its production server; one running rinzler is one engine; tp2 = two FPGA cards per engine. The nightly layout is 4 tp2 engines behind the Caddy proxy."),
        ("nightly deb, canonical-AMX deb (the two arms)", "The nightly deb is the package the nightly CI installed (tron 2026.09.18-3faba6d0, built without the AMX kernel). The canonical-AMX deb is the same source plus one CMake preset line (TRON_AMX_DISPATCH=ON), so its rinzler contains the AMX attention kernel of PR #3879. An arm is one installed package; a pass is one run of all configs on one arm."),
        ("AMX", "Intel Advanced Matrix Extensions, the CPU matrix instructions the kernel uses for attention. AMX-busy cycles come from the CPU counter EXE.AMX_BUSY read with perf stat for 20 s on the engine processes before each config: about 0 on the nightly deb, billions on the AMX deb."),
        ("CI harness, config, TPS, TTFT, slowest sample, p05", "The CI harness is the nightly's client code (systems_test scripts/perf.py). A config is one line of its table: model, number of users, prompt length. TPS = decode tokens per second per user, measured between generated tokens 896 and 1024 of every request, averaged over 10 rounds of all users. TTFT = time to first token in ms. Slowest sample = the lowest single-request TPS. p05 = the 5th percentile of the request TPS values."),
        ("users per engine, KV tokens per engine step, the two levers", "The harness's user count is spread by Caddy over the 4 engines, so 8 users = 2 users per engine. KV tokens per engine step = users per engine x context per user (prompt + tokens the server adds + generated tokens); it is the attention work of one decode step. The two ways to raise it are the two levers: more users per engine, or a longer prompt."),
        ("gain, paired t, resolved", "gain = AMX-deb mean TPS over nightly-deb mean TPS minus 1, in percent, over the 3 passes. Paired t = mean of the 3 per-pass TPS differences divided by their standard error (pass k of one arm pairs with pass k of the other). Resolved = |t| >= 4.303 (the 95 % two-sided limit of Student's t with 2 degrees of freedom) and |gain| >= 1 %."),
        ("16K pair, 8K triple", "Two pre-registered comparisons at equal attention work: the pair compares 2 users x prompt 7168 with 8 users x prompt 1024 (both about 16K KV tokens per step); the triple compares 1 user x 7168, 2 users x 3000 and 4 users x 1024 (about 8K). Verdict thresholds are 3 percentage points."),
        ("prompt truncation at 4096", "For llama-3.1-8b on this deployment the server keeps at most the first 4096 prompt tokens of a chat request. Cause (verified on the machine): the cached weights directory /opt/positron/weights_cache/cached/neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16/tokenizer.json contains a truncation block (direction Right, max_length 4096) that the stock Hugging Face file does not have, and tron's tokenizer wrapper never disables truncation, so the tokenizer itself drops everything after token 4096 before rinzler counts the prompt. Rinzler's own limits (max_prompt_tokens, max_total_tokens) are 131072 and are not the cause. The same weights directory serves llama-3.1-8b-instruct-good and -best. The 70b w4a16 weights (llama-3.1-70b-instruct-good) carry the same block with max_length 8192; the other 27 cached tokenizer files on the machine have none. Provenance (Hugging Face commit history, checked 2026-09-19): the block is Neural Magic's own, present in their upload from 2024-07-26 (their calibration code calls the tokenizer with truncation=True and max_length=max_seq_len, which the saved tokenizer.json then carries); they replaced tokenizer.json on 2024-09-30 (8b commit 1455f0f5f7, 70b commit 5ce1373819). Positron's weights store downloaded both models on 2024-09-10, 20 days before that fix (the 8b file is byte-identical to upstream revision 8ecfb5aa0d, sha256 4a49a5d5...), and never refreshed. The weights are not in any Positron GitHub repository: they live on the NFS store /opt/positron/weights/huggingface and are copied to each machine's /opt/positron/weights_cache by a cron script; tron's config/models.yaml only names the model id."),
        ("ShareGPT prompts, prefix cache", "The harness builds prompts from ShareGPT conversations. For prompts above 2048 tokens the campaign concatenates following conversations (one code change in the driver's checkout; the prompt-1024 prompts are unchanged). Same seeds are used in every config, so a longer prompt of a seed starts with the shorter prompt of the same seed sent minutes earlier; rinzler's prefix cache then serves that prefix when Caddy routes the request to the same engine. This affects TTFT and prefill, not the TPS window."),
    ]
    deviations = [
        "Two arms only, no kill-switch arm (jhan's decision in the plan).",
        "Prompt-7168 and prompt-8192 cells dropped before the first pass: the server truncates prompts above 4096 tokens (section 1), so these cells cannot be measured; the 16K pair is lost. The first launch (13:14 UTC, after the lease cleared) ran the check cell, was stopped at 13:35 UTC, restored the machine and was relaunched at 13:43 UTC with 7 configs and without a second check cell.",
        "The relaunched campaign waited for another session's issue4500 runtron work on the machine's second half (about 13:41 to 15:00 UTC) before taking the campaign flock; that session had taken the production engines down, so the first engine start of the campaign was its own serving-up.",
        "The driver timeout per pass was 5400 s instead of the plan's 'about 3600 s' (the plan's cell estimates left 16 min of margin; no long-prompt cell had ever been timed).",
        "The plan's '19:30 UTC' was applied as the campaign-start deadline; individual passes had their own start deadline (23:45 UTC) and every pass had to finish before 01:00 UTC.",
        "Engines were restarted after every package switch (serving-down, serving-up with a wait for platformd idle), because the legacy provisioning path never restarts a same-model engine (verified on the machine).",
        "The check cell was judged a prompt-length failure only on a timeout after the benchmark had started or on a request-level error; driver or provisioning faults were retried once and would have stopped the campaign.",
        "A failed pass was repeated once after an engine restart; a config counted as a systematic failure only after failing twice in one pass-run, and a later pass whose failures were all systematic was not repeated.",
        "Per-engine request counts were read from rinzler's FUSE stats (prompts_total), since the journal has no per-request line.",
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
    parts.append(f"<title>llama-8b AMX levers</title>\n<style>{css}</style>\n<main>")
    parts.append("<h1>AMX gain on llama-3.1-8b against users per engine and prompt length</h1>")
    parts.append(f'<p class="sub">Test T0 of the CI-AMX-test-shapes page. Whole delphi-3bda, nightly layout, CI harness, 2026-09-19. Generated {now} by exec/l8b-levers-20260919/gen_report.py from {esc(RES)}. Every number comes from the result files named in section 8.</p>')
    parts.append('<div class="short"><p><b>Short version.</b></p>' + "".join(f"<p>{esc(s)}</p>" for s in short) + "</div>")
    parts.append("<h2>Words used here</h2><dl>" + "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in words) + "</dl>")
    parts.append("<h2>1. What ran</h2>")
    parts.append("<ul>"
                 "<li>Machine: the whole of delphi-3bda (72-core Intel Granite Rapids, 8 FPGA cards), 4 tp2 engines provisioned by platformd behind Caddy on port 80, exactly the nightly layout. The nightly CI lease was free and Bill's marker taken for the whole campaign.</li>"
                 "<li>Client: the nightly's own perf code (systems_test scripts/perf.py) run from claude-agentsrv through the campaign driver (st_ci_perf.py), which records every request, the layout, the engine binary per pass and the AMX-busy probe. Talos (the CI results database) was replaced by a recording stub; nothing reached CI records.</li>"
                 f"<li>Arms: nightly deb against canonical-AMX deb, 3 passes each, interleaved (base, canon, base, canon, base, canon). Passes found: {esc(', '.join(summary['passes_found']))}.</li>"
                 f"<li>Configs per pass: {len(summary['configs'])} (llama-3.1-8b-instruct-good-tp2, 1536 generated tokens, TPS window 896 to 1024). Config file used: {esc(os.path.basename(open(os.path.join(RES, 'configs-used.txt')).read().strip()) if os.path.isfile(os.path.join(RES, 'configs-used.txt')) else 'unknown')}.</li>"
                 f"<li>Prompt source: ShareGPT with concatenation above one conversation's length; offline check of 1920 prompts: {('0 exceptions, deterministic, prompt-1024 identical to the previous code' if prompt_check and prompt_check.get('total_exceptions') == 0 and prompt_check.get('identity_1024_ok') else 'see prompt-check/')}.</li>"
                 f"<li>Tokens the server counted around the prompt (measured here, the plan assumed 31): {fmt(overhead, 1)}.</li>"
                 "</ul>")
    if check_rows:
        parts.append("<h3>The check cell before the first pass (32 users x the longest prompt, canonical-AMX deb)</h3>")
        parts.append(table(["cell", "prompt_length sent", "prompt tokens counted by the server", "requests", "TPS mean", "slowest sample", "TTFT ms", "minutes", "requests per engine", "AMX-busy cycles (billions)", "stop"], check_rows))
        parts.append('<p class="cap">The server counted 4096 prompt tokens for every 8192-token request of the check cell (the harness verified its prompts at 8192 tokens; rinzler\'s own limits max_prompt_tokens and max_total_tokens were 131072). So this deployment truncates chat prompts above 4096 tokens for llama-3.1-8b, and the prompt-7168 and prompt-8192 cells could not measure what the plan called them. They were dropped before the first pass (the plan\'s fallback for cells that cannot be measured), the campaign was stopped, restored and relaunched at 13:43 UTC with 7 configs. The 16K pair is therefore lost; the prompt-4096 cell is measured at 4096 server-side tokens (its 4127 tokens with the template were clipped by 31).</p>')
    parts.append("<h3>Identity of every pass-run</h3>")
    parts.append(identity_table(summary, passes))
    parts.append('<p class="cap">The binary check compares every engine process with the installed rinzler (sha256) after each provisioning; a pass stops if any engine still runs a deleted or foreign binary. AMX-busy cycles prove which kernel ran.</p>')
    parts.append("<h2>2. Results per config</h2>")
    parts.append('<div class="fig">' + chart_dumbbell(summary, overhead) + '<p class="cap">Figure 1. Each row is one config; the light dot is the nightly deb, the dark dot the canonical-AMX deb, both the mean TPS over 3 passes. The label is the AMX gain in percent. Hover a dot for the paired t.</p></div>')
    parts.append(results_table(summary, overhead))
    parts.append("<h3>Per pass</h3>" + per_pass_table(summary, overhead))
    if summary["incomplete"]:
        parts.append("<p>Incomplete configs (fewer than 3 paired passes; excluded from the verdicts): " + esc(", ".join(f"{label(i['name'])} ({i['n_pairs']} pairs)" for i in summary["incomplete"])) + ".</p>")
    parts.append("<h2>3. The two levers</h2>")
    parts.append('<div class="fig">' + chart_gain_vs_kv(summary, overhead) + '<p class="cap">Figure 2. The AMX gain against the attention work of one decode step. Blue = more users per engine at prompt 1024; orange = longer prompts at 2 users per engine; aqua = the other two cells.</p></div>')
    parts.append('<div class="verdict"><p><b>16K pair</b> (2 users x 7168 against 8 users x 1024): ' + esc(f"gains {sfmt(pair['gain_2u_p7168'], 2)} % and {sfmt(pair['gain_8u_p1024'], 2)} %, difference {sfmt(pair['diff_points'], 2)} points.") + f"</p><p>Verdict: {esc(pair['verdict'])}.</p></div>")
    parts.append('<div class="verdict"><p><b>8K triple</b> (1 user x 7168, 2 users x 3000, 4 users x 1024): ' + esc(f"gains {sfmt(triple['gain_1u_p7168'], 2)} %, {sfmt(triple['gain_2u_p3000'], 2)} %, {sfmt(triple['gain_4u_p1024'], 2)} %; 1-user cell had 10 requests per engine in every run: {triple['spread_1u_ok']}.") + f"</p><p>Verdict: {esc(triple['verdict'])}.</p></div>")
    parts.append('<div class="verdict"><p><b>Expected bands</b> (pre-registered): ' + esc(f"2 users x 1024 expected +0.2 to +1.2 %, measured {sfmt(v['expected_2u_p1024']['gain'], 2)} % (inside: {v['expected_2u_p1024']['inside']}); 8 users x 1024 (T1) expected 9.9 to 15.9 %, measured {sfmt(v['expected_8u_p1024_T1']['gain'], 2)} % (inside: {v['expected_8u_p1024_T1']['inside']}).") + "</p></div>")
    parts.append("<h2>4. Data quality</h2>")
    parts.append(quality_table(summary, overhead))
    parts.append('<p class="cap">Requests per engine come from rinzler\'s prompts_total counter read before and after each config; the expected value is users x 10 rounds / 4 engines. Caddy health events are health-checker lines in Caddy\'s journal during the config (an engine dropped from the pool moves users). Anomalous samples are harness samples above 1000 TPS (a client-side stall indicator). Prefix-cache hits are inflated for the longer-prompt cells by the same-seed prompts of earlier cells; the TPS window is not affected.</p>')
    parts.append('<div class="fig">' + chart_durations(summary) + '<p class="cap">Figure 3. Wall time of one config (10 rounds) including prompt generation and the harness\'s own waits; the AMX-busy probe and the layout snapshot are not included.</p></div>')
    parts.append("<h2>5. Decisions taken during the run (plan section 2a) and deviations from the plan text</h2><ul>" + "".join(f"<li>{esc(d)}</li>" for d in deviations) + "</ul>")
    parts.append("<h3>Campaign status lines</h3><pre style=\"font-size:12px;overflow-x:auto;background:#fcfcfb;border:1px solid #e1e0d9;padding:8px\">" + esc("\n".join(l for l in hist if "waiting: CI lease busy" not in l)) + "</pre>")
    parts.append("<h2>6. What this does and does not show</h2><ul>"
                 "<li>It shows the AMX deb's effect in the exact nightly setting for llama-3.1-8b at 10 shapes. It does not measure other models, and it does not measure PR #4424 (VNNI K), which is not in either package.</li>"
                 "<li>Both arms ran the same client code, prompts, layout and machine, alternating, so a common drift affects both passes of a pair; the paired t uses only within-pair differences.</li>"
                 "<li>TTFT and prefix-cache figures for prompts above 1024 are affected by warm prefixes (see the words list); decode TPS is not.</li>"
                 "</ul>")
    parts.append("<h2>7. Next steps (jhan decides)</h2><ul><li>Whether to file the 32-user prompt-1024 config in systems_test (the T1 reference values are the 8-users-per-engine row of section 2).</li><li>Whether a long-prompt shape is added, per the 16K pair verdict.</li><li>Feed these results into gen_ci_shapes.py as source H and re-rank the page's sections 4 and 5.</li></ul>")
    parts.append("<h2>8. Files</h2><ul>"
                 f"<li>Results: <code>{esc(RES)}</code> (per pass: perf.json, talos.json, driver.log, summary.txt; summary.json and summary.txt from analyze.py; preflight.txt; base-identity.txt; outcome.txt; status-history.log).</li>"
                 "<li>Scripts: <code>exec/l8b-levers-20260919/</code> (campaign.sh, launch.sh, dut.sh, st_ci_perf.py, configs.py, prompt_check.py, analyze.py, gen_report.py, review-findings.txt, review2-findings.txt).</li>"
                 "<li>Plan: <code>CI-test/status/Saturday-plan.md</code>; page under test: <code>PR3879/new-PRs/PR1/CI-AMX-test-shapes.html</code>.</li>"
                 "<li>Prompt-source change: <code>exec/l8b-levers-20260919/prompt.py.patch</code> applied to the driver's checkout ~/workspace/ai-runs/systems_test (uncommitted; the nightly's checkout is untouched).</li>"
                 "</ul></main>")
    page = "\n".join(parts)
    page = page.encode("ascii", "xmlcharrefreplace").decode("ascii")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(page)} bytes, ascii)")


if __name__ == "__main__":
    build()
