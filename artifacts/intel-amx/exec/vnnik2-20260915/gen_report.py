#!/usr/bin/env python3
"""Generate VNNIed-K-in-place/status/store-remedies-report.html: the Perfetto measurement
of the "Save K" span (exec/results/vnnik-trace-20260914/analysis.json + *.lanes.json),
the two remedies (block store, helper striping) and their measurement
(exec/results/vnnik2-20260915/summary.json, smoke, build, tests; traces of the new arms in
exec/results/vnnik2-trace-20260915/analysis.json). Pure-ASCII HTML, light theme, inline
SVG: wall-clock lanes (durations to scale) for one prefill layer, dot plots per prompt for
TTFT and TPS, bars for the Save K span per arm. Every block degrades to "pending" when its
input is missing. Usage: gen_report.py [OUT_HTML]
"""
import datetime
import glob
import html
import json
import os
import re
import statistics
import sys

EXEC = "/home/jhan/workspace/intel-AMX/exec"
TRACE1 = f"{EXEC}/results/vnnik-trace-20260914"
TRACE2 = f"{EXEC}/results/vnnik2-trace-20260915"
RES2 = f"{EXEC}/results/vnnik2-20260915"
RES1 = f"{EXEC}/results/vnnik-20260914"
RES3 = f"{EXEC}/results/vnnik2-confirm-20260915"          # the review-fixed commit, confirmation cells
TRACE3 = f"{EXEC}/results/vnnik2-trace-confirm-20260915"
FIX_TIP = "10fc7c724c"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/store-remedies-report.html"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
NEW_TIP = "9928cb2849"

ARMS = ["base", "vnni", "vnni0", "a", "b", "ab"]
ARM_LABEL = {"base": "base (PR #3879, row-major K)", "vnni": "vnni (Monday binary, scatter store)",
             "vnni0": "vnni0 (new binary, both remedies off)", "a": "a (block store)",
             "b": "b (helper striping)", "ab": "a+b (both, the branch default)"}
# Validated categorical palette (dataviz reference, light theme); the two controls are
# gray shades so the eye lands on the remedies.
ARM_COLOR = {"base": "#8a8987", "vnni": "#52514e", "vnni0": "#2a78d6", "a": "#1baf7a", "b": "#eb6834", "ab": "#7a3fbf"}


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
    return "pending" if x is None else f"{x:.{nd}f}"


def pending(what):
    return f'<p class="pending">pending: {esc(what)}</p>'


# ---------------------------------------------------------------- trace section
def trace_table(analysis, kind, arms_order):
    if not analysis:
        return pending("trace analysis (analyze.py) not found")
    rows = []
    for r in analysis:
        a = r["kinds"].get(kind)
        if not a:
            continue
        name = r["trace"].replace(".perfetto-trace", "")
        rows.append((name, a, r["threads"]))
    rows.sort(key=lambda x: (arms_order.index(x[0].split("-")[0]) if x[0].split("-")[0] in arms_order else 99, x[0]))
    h = ['<table><tr><th>trace (arm-tp)</th><th>passes</th><th>pass ms</th><th>Save K us per layer</th><th>ns per K row</th>'
         '<th>Save K ms per pass</th><th>Save K share of the pass</th><th>Save V us per layer</th><th>attention workers with a span during Save K</th>'
         '<th>main helpers with a span during Save K</th></tr>']
    for name, a, thr in rows:
        h.append(f"<tr><td>{esc(name)}</td><td>{a['n_passes']}</td><td>{a['pass_ms']:.1f}</td><td><b>{a['save_k_us_per_layer']:.0f}</b></td>"
                 f"<td>{a['save_k_ns_per_row']:.0f}</td><td>{a['save_k_ms']:.1f}</td><td>{100*a['save_k_share']:.1f}%</td>"
                 f"<td>{a['save_v_us_per_layer']:.0f}</td><td>{100*a['workers_busy_in_save_k']:.0f}% of {thr['attention_workers']}</td>"
                 f"<td>{100*a['helpers_busy_in_save_k']:.0f}% of {thr['main_helpers']}</td></tr>")
    h.append("</table>")
    return "\n".join(h)


def lanes_svg(lanes, title, kind="prefill"):
    """Wall-clock lanes of one layer: main, helpers, attention workers; x = time to scale.
    kind = "prefill" (one 1024-token pass) or "decode" (one 8-token step)."""
    if not lanes or not lanes.get(kind):
        return pending("lanes data (lanes.py) not found")
    w = lanes[kind]
    t_lo, t_hi = w["window_us"]
    # x range: a little before Save K to the end of the layer's last join; the
    # decode window is one short layer, the prefill window a few ms
    lookback = 1300.0 if kind == "prefill" else 90.0
    spans = [s for s in w["spans"] if s["start_us"] + s["dur_us"] > -lookback]
    ends = [s["start_us"] + s["dur_us"] for s in spans if s["cls"] in ("attention", "main") and s["name"] in ("attention: join", "Attention Pending", "Save V", "Save K")]
    x0 = max(t_lo, -lookback)
    x1 = min(t_hi, (max(ends) if ends else 4000.0) + (150.0 if kind == "prefill" else 12.0))
    tick = 500.0 if kind == "prefill" else 50.0
    W, LEFT, RIGHT = 960, 150, 40
    px = lambda t: LEFT + (t - x0) / (x1 - x0) * (W - LEFT - RIGHT)
    # lanes: main, each helper (by name), each attention worker (by name). The
    # role comes from the spans of this window: the main-helper / attention
    # split is chosen per pass, so a pool thread can be a helper in this layer
    # and an attention worker in another pass.
    role = {}
    for sp in spans:
        if sp["name"] in ("Save K", "Save V"):
            role[sp["thread"]] = "main"
        elif sp["name"].startswith("Attention") or sp["name"] == "attention: join":
            role.setdefault(sp["thread"], "attention")
        elif sp["name"].startswith("kernel_"):
            role.setdefault(sp["thread"], "helper")
    for sp in spans:
        sp["cls"] = role.get(sp["thread"], sp["cls"])
    by = {}
    for s in spans:
        by.setdefault((s["cls"], s["thread"]), []).append(s)
    order = {"main": 0, "helper": 1, "attention": 2, "other": 3}
    keys = sorted(by.keys(), key=lambda k: (order[k[0]], k[1]))
    keys = [k for k in keys if k[0] != "other"]
    n_help = sum(1 for k in keys if k[0] == "helper")
    n_attn = sum(1 for k in keys if k[0] == "attention")
    ROWH = {"main": 28, "helper": 18, "attention": 10 if n_attn > 24 else 16}
    if kind == "prefill":
        GROUP = {"main": "main thread (traced spans only: Save K, Save V; its matmul launches and channel waits are not traced)",
                 "helper": f"main helpers ({n_help}): rope kernel, then idle until the attention output arrives",
                 "attention": f"attention workers ({n_attn}): Ready sections during Save K; Pending sections only after Save V"}
    else:
        GROUP = {"main": "main thread (traced spans only: Save K, Save V, Free scratchpads)",
                 "helper": f"main helpers ({n_help}): one token each in the per-token kernels, idle otherwise",
                 "attention": f"attention workers ({n_attn}): Ready sections start with Save K and outlast it; Pending follows each worker's own Ready work"}
    y = 84
    rows = []
    headers = []
    last_cls = None
    for k in keys:
        if k[0] != last_cls:
            y += 8
            headers.append((k[0], y + 11))
            y += 18
            last_cls = k[0]
        rows.append((k, y, ROWH[k[0]]))
        y += ROWH[k[0]] + (2 if k[0] == "attention" else 4) + (10 if (k[0] == "main" and kind == "decode") else 0)
    H = y + 52
    COLOR = {"Save K": "#d03b3b", "Save V": "#eb6834", "Attention Ready": "#2a78d6", "Attention Pending": "#eb6834",
             "attention: join": "#8a8987", "Free scratchpads": "#8a8987"}
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" aria-label="{esc(title)}" xmlns="http://www.w3.org/2000/svg" style="font-family:system-ui,sans-serif;">']
    out.append(f'<text x="10" y="16" font-size="14" font-weight="600" fill="#0b0b0b">{esc(title)}</text>')
    # time axis (ms)
    ax_y = H - 44
    out.append(f'<line x1="{LEFT}" y1="{ax_y}" x2="{W-RIGHT}" y2="{ax_y}" stroke="#52514e" stroke-width="1"/>')
    t = (int(x0 / tick) - 1) * tick
    while t <= x1:
        if t >= x0:
            out.append(f'<line x1="{px(t):.1f}" y1="{ax_y}" x2="{px(t):.1f}" y2="{ax_y+5}" stroke="#52514e"/>')
            lab = f"{t/1000:.1f}" if kind == "prefill" else f"{t:.0f}"
            out.append(f'<text x="{px(t):.1f}" y="{ax_y+18}" font-size="12" text-anchor="middle" fill="#52514e">{lab}</text>')
            out.append(f'<line x1="{px(t):.1f}" y1="82" x2="{px(t):.1f}" y2="{ax_y}" stroke="#e6e5e1" stroke-width="1"/>')
        t += tick
    unit = "ms" if kind == "prefill" else "us"
    out.append(f'<text x="{LEFT}" y="{ax_y+36}" font-size="12" fill="#52514e">wall-clock time, {unit}; 0 = the start of this layer\'s Save K; durations to scale, one traced layer</text>')
    for cls, hy in headers:
        out.append(f'<text x="6" y="{hy}" font-size="12" font-weight="600" fill="#0b0b0b">{esc(GROUP[cls])}</text>')
    for (cls, tname), yy, hh in rows:
        # lane background
        out.append(f'<rect x="{LEFT}" y="{yy}" width="{W-LEFT-RIGHT}" height="{hh}" fill="#f7f6f3"/>')
        if cls != "attention" or n_attn <= 24:
            out.append(f'<text x="{LEFT-6}" y="{yy+hh*0.74:.1f}" font-size="{11 if cls=="attention" else 12}" text-anchor="end" fill="#52514e">{esc(tname.strip())}</text>')
        ss = sorted(by[(cls, tname)], key=lambda s: s["start_us"])
        # idle (dashed) between consecutive spans of the lane; not for main, whose
        # untraced work between the two spans is not idleness
        for i in range(len(ss) - 1 if cls != "main" else 0):
            a_end = ss[i]["start_us"] + ss[i]["dur_us"]
            b_start = ss[i + 1]["start_us"]
            if b_start - a_end > 30 and a_end < x1 and b_start > x0:
                xa, xb = px(max(a_end, x0)), px(min(b_start, x1))
                out.append(f'<rect x="{xa:.1f}" y="{yy+1}" width="{max(0.5, xb-xa):.1f}" height="{hh-2}" fill="none" stroke="#a9a8a4" stroke-dasharray="3,3" stroke-width="1"/>')
        for s in ss:
            xs, xe = px(max(s["start_us"], x0)), px(min(s["start_us"] + s["dur_us"], x1))
            if xe <= xs:
                continue
            name = s["name"]
            col = COLOR.get(name, "#1baf7a" if name.startswith("kernel_") else "#8a8987")
            out.append(f'<rect x="{xs:.1f}" y="{yy+1}" width="{max(1.0, xe-xs):.1f}" height="{hh-2}" fill="{col}"><title>{esc(name)} {s["dur_us"]:.0f} us</title></rect>')
            if cls == "main" and name in ("Save K", "Save V"):
                lab = f'{name} {s["dur_us"]:.0f} us'
                # Save K is labelled to the left of its block and Save V to the
                # right of its block, on the lane's centre line: the two blocks
                # are adjacent and can be narrow, so labels above them collide.
                anchor = "end" if name == "Save K" else "start"
                lx = xs - 6 if name == "Save K" else xe + 6
                ly = yy + hh * 0.74
                out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="12" font-weight="600" text-anchor="{anchor}" fill="{col}">{esc(lab)}</text>')
    # legend
    lg = [[("Save K (serial, on the critical path)", "#d03b3b"), ("Save V", "#eb6834"), ("helper kernel (rope K and Q)", "#1baf7a")],
          [("Attention Ready (pages of earlier passes)", "#2a78d6"), ("Attention Pending (this pass's pages)", "#eb6834")],
          [("attention: join", "#8a8987"), ("idle (waiting)", None)]]
    for row_i, items in enumerate(lg):
        x, ly = 10, 26 + 17 * row_i
        for text, col in items:
            if col:
                out.append(f'<rect x="{x}" y="{ly}" width="11" height="11" fill="{col}"/>')
            else:
                out.append(f'<rect x="{x}" y="{ly}" width="11" height="11" fill="none" stroke="#a9a8a4" stroke-dasharray="3,3"/>')
            out.append(f'<text x="{x+16}" y="{ly+10}" font-size="12" fill="#52514e">{esc(text)}</text>')
            x += 16 + 6.6 * len(text) + 22
    out.append("</svg>")
    return f'<div class="fig">{"".join(out)}</div>'


# ---------------------------------------------------------------- results section
def dot_rows(summary, tp, metric, title, unit, arms, primary_pair, lower_better):
    """One row per prompt; one dot per arm; value labels on the compared arms; delta at right."""
    if not summary:
        return pending("summary.json of the vnnik2 campaign")
    cells = {(c["prompt"], c["arm"]): c for c in summary["cells"] if c["tp"] == tp}
    prompts = sorted({p for p, _ in cells})
    if not prompts:
        return pending(f"tp{tp} cells")
    W, LEFT, RIGHT, ROWH = 960, 110, 230, 84
    H = 40 + ROWH * len(prompts) + 24
    key = "tps_mean" if metric == "tps" else "ttft_mean"
    sdk = "tps_sd" if metric == "tps" else "ttft_sd"
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" xmlns="http://www.w3.org/2000/svg" style="font-family:system-ui,sans-serif;">',
           f'<text x="{LEFT}" y="16" font-size="13" font-weight="600" fill="#0b0b0b">{esc(title)}</text>']
    for i, prompt in enumerate(prompts):
        y = 40 + i * ROWH
        vals = {a: cells[(prompt, a)][key] for a in arms if (prompt, a) in cells and cells[(prompt, a)][key] is not None}
        if not vals:
            continue
        lo, hi = min(vals.values()), max(vals.values())
        span = (hi - lo) or (hi * 0.02 or 1.0)
        lo2, hi2 = lo - 0.25 * span, hi + 0.25 * span
        px = lambda v: LEFT + (v - lo2) / (hi2 - lo2) * (W - LEFT - RIGHT)
        out.append(f'<text x="8" y="{y+38}" font-size="13" fill="#0b0b0b">prompt {prompt}</text>')
        out.append(f'<line x1="{LEFT}" y1="{y+34}" x2="{W-RIGHT}" y2="{y+34}" stroke="#e6e5e1"/>')
        # dots, whiskers, then labels: a lone dot is labelled above itself; dots
        # closer than 56 px form a cluster whose labels are listed in a column
        # beside the cluster, on the side with more room, one line per arm
        order = sorted(vals.items(), key=lambda kv: kv[1])
        for a, v in order:
            c = cells[(prompt, a)]
            sd = c[sdk] or 0.0
            out.append(f'<line x1="{px(v-sd):.1f}" y1="{y+34}" x2="{px(v+sd):.1f}" y2="{y+34}" stroke="{ARM_COLOR[a]}" stroke-width="1"/>')
            out.append(f'<circle cx="{px(v):.1f}" cy="{y+34}" r="6" fill="{ARM_COLOR[a]}"><title>{esc(a)}: {v:.3f} {esc(unit)} (sd {sd:.3f}, n {c["n"]})</title></circle>')
        clusters = []
        for a, v in order:
            if clusters and px(v) - clusters[-1][-1][1] < 56:
                clusters[-1].append((a, px(v), v))
            else:
                clusters.append([(a, px(v), v)])
        for cl in clusters:
            if len(cl) == 1:
                a, x, v = cl[0]
                out.append(f'<text x="{x:.1f}" y="{y+22}" font-size="11" text-anchor="middle" fill="{ARM_COLOR[a]}">{esc(a)} {v:.2f}</text>')
                continue
            x_min, x_max = cl[0][1], cl[-1][1]
            right_room = (W - RIGHT) - x_max
            left_room = x_min - LEFT
            if right_room >= 92 or right_room >= left_room:
                lx, anchor = x_max + 12, "start"
            else:
                lx, anchor = x_min - 12, "end"
            n = len(cl)
            for k, (a, x, v) in enumerate(cl):
                # 13 px per line, centred on the axis; an odd count is shifted
                # by half a line so no label sits on the axis line itself
                ly = y + 34 + (k - (n - 1) / 2) * 13 + (6.5 if n % 2 == 1 else 0) + 4
                out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" text-anchor="{anchor}" fill="{ARM_COLOR[a]}">{esc(a)} {v:.2f}</text>')
        a1, a0 = primary_pair
        if a1 in vals and a0 in vals:
            d = 100 * (vals[a1] / vals[a0] - 1)
            good = (d < 0) if lower_better else (d > 0)
            col = "#0ca30c" if good else "#d03b3b"
            extra = f", {1000*(vals[a1]-vals[a0]):+.0f} ms" if metric == "ttft" else ""
            out.append(f'<text x="{W-RIGHT+12}" y="{y+38}" font-size="13" font-weight="600" fill="{col}">{esc(a1)} vs {esc(a0)} {d:+.1f}%{esc(extra)}</text>')
    out.append(f'<text x="{W-RIGHT}" y="{H-6}" font-size="11" text-anchor="end" fill="#52514e">dots = mean over repetitions, whiskers = one sd; each row has its own scale</text>')
    out.append("</svg>")
    return f'<div class="fig">{"".join(out)}</div>'


def legend_html(arms):
    return '<div class="legend">' + "".join(f'<span class="key"><span class="sw" style="background:{ARM_COLOR[a]};"></span>{esc(ARM_LABEL[a])}</span>' for a in arms) + "</div>"


def delta_table(summary, tp):
    if not summary:
        return ""
    ds = [d for d in summary["deltas"] if d["tp"] == tp]
    if not ds:
        return ""
    h = ['<table><tr><th>prompt</th><th>comparison</th><th>TTFT delta</th><th>TTFT delta ms</th><th>TPS delta</th><th>reading</th></tr>']
    reading = {("vnni0", "base"): "the old VNNI store against the AMX baseline (should repeat Monday's vnni vs base)",
               ("vnni0", "vnni"): "build drift check: the new binary with both remedies off against Monday's binary (same code path)",
               ("a", "vnni0"): "remedy (a): block store alone", ("b", "vnni0"): "remedy (b): helper striping alone",
               ("ab", "vnni0"): "remedies (a)+(b)", ("ab", "base"): "the branch with both remedies against the AMX baseline",
               ("a", "base"): "(a) against the AMX baseline", ("b", "base"): "(b) against the AMX baseline", ("vnni", "base"): "Monday's comparison, repeated today"}
    for d in ds:
        h.append(f"<tr><td>{d['prompt']}</td><td>{esc(d['a'])} vs {esc(d['b'])}</td><td>{d['ttft_delta_pct']:+.1f}%</td><td>{d['ttft_delta_ms']:+.0f}</td>"
                 f"<td>{d['tps_delta_pct']:+.1f}%</td><td>{esc(reading.get((d['a'], d['b']), ''))}</td></tr>")
    h.append("</table>")
    return "\n".join(h)


def cells_table(summary, tp):
    if not summary:
        return ""
    cs = [c for c in summary["cells"] if c["tp"] == tp]
    if not cs:
        return ""
    h = ['<table><tr><th>prompt</th><th>arm</th><th>n</th><th>TTFT s</th><th>sd</th><th>TPS per user</th><th>sd</th><th>early stops</th></tr>']
    for c in cs:
        h.append(f"<tr><td>{c['prompt']}</td><td>{esc(c['arm'])}</td><td>{c['n']}</td><td>{fmt(c['ttft_mean'],3)}</td><td>{fmt(c['ttft_sd'],3)}</td>"
                 f"<td>{fmt(c['tps_mean'],2)}</td><td>{fmt(c['tps_sd'],2)}</td><td>{c['early_stop_runs']}</td></tr>")
    h.append("</table>")
    return "\n".join(h)


def savek_bars(an1, an2, kind):
    """Save K us per layer per arm and tp, prefill or decode: base, vnni (first trace set) and vnni0/a/b/ab (second)."""
    vals = {}
    for an in (an1 or []), (an2 or []):
        for r in an:
            a = r["kinds"].get(kind)
            if not a:
                continue
            name = r["trace"].replace(".perfetto-trace", "")
            arm, tp = name.rsplit("-tp", 1)
            vals[(arm, int(tp))] = a
    if not vals:
        return pending("trace analyses")
    arms = [a for a in ARMS if any(k[0] == a for k in vals)]
    W, LEFT, RIGHT, ROWH = 960, 200, 270, 24
    groups = [2, 4]
    H = 40 + (len(arms) * ROWH + 30) * len(groups)
    mx = max(a["save_k_us_per_layer"] for a in vals.values())
    px = lambda v: LEFT + v / (mx * 1.12) * (W - LEFT - RIGHT)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" xmlns="http://www.w3.org/2000/svg" style="font-family:system-ui,sans-serif;">',
           f'<text x="{LEFT}" y="16" font-size="13" font-weight="600" fill="#0b0b0b">Save K span per layer, {esc(kind)} ({"1024 tokens, 8 KV heads" if kind=="prefill" else "8 tokens, 8 KV heads"}), us; shorter is better</text>']
    y = 36
    for tp in groups:
        out.append(f'<text x="8" y="{y+16}" font-size="13" font-weight="600" fill="#0b0b0b">tp{tp}</text>')
        for a in arms:
            v = vals.get((a, tp))
            if v is None:
                continue
            us = v["save_k_us_per_layer"]
            out.append(f'<text x="{LEFT-8}" y="{y+16}" font-size="12" text-anchor="end" fill="#52514e">{esc(ARM_LABEL.get(a, a).split(" (")[0])}</text>')
            out.append(f'<rect x="{LEFT}" y="{y+3}" width="{max(1.0, px(us)-LEFT):.1f}" height="{ROWH-6}" fill="{ARM_COLOR.get(a, "#8a8987")}"/>')
            base = vals.get(("base", tp))
            ref = vals.get(("vnni0", tp)) or vals.get(("vnni", tp))
            extra = ""
            if a not in ("base", "vnni", "vnni0") and ref:
                extra = f"  ({100*(us/ref['save_k_us_per_layer']-1):+.0f}% vs vnni0)"
            elif a in ("vnni", "vnni0") and base:
                extra = f"  ({us/base['save_k_us_per_layer']:.1f}x base)"
            out.append(f'<text x="{px(us)+6:.1f}" y="{y+16}" font-size="12" fill="#0b0b0b">{us:.0f} us, {v["save_k_ns_per_row"]:.0f} ns per row{esc(extra)}</text>')
            y += ROWH
        y += 30
    out.append("</svg>")
    return f'<div class="fig">{"".join(out)}</div>'


# ---------------------------------------------------------------- mechanism figures
TOKEN_HUES = ["#2a78d6", "#1baf7a", "#eb6834", "#7a3fbf"]  # 16 tokens, 4 hues cycling (the permutation is what matters)


STEP_HUES = ["#2a78d6", "#1baf7a", "#eb6834", "#7a3fbf"]  # the 4 dim steps of a K row
SVG_HEAD = 'xmlns="http://www.w3.org/2000/svg" style="font-family:system-ui,sans-serif;"'


def _grid_pattern(pid, cell):
    return (f'<pattern id="{pid}" width="{cell}" height="{cell}" patternUnits="userSpaceOnUse">'
            f'<rect width="{cell}" height="{cell}" fill="#f3f2ef"/><rect width="{cell-1}" height="{cell-1}" fill="#faf9f6"/></pattern>')


def fig_row_to_plane():
    """Figure 3.1a: one token's K row (64 dim pairs in 4 dim steps) and where each part lands in
    the page's VNNI plane: column t of the 4 panels of its token block, 4 bytes per line."""
    W, H = 960, 520
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" aria-label="One token\'s K row is 64 dim pairs in 4 dim steps; in the VNNI plane each dim step lands as column t of one panel of the token\'s block, so the row is spread over 64 cache lines, 4 bytes each" {SVG_HEAD}>',
         '<defs>', _grid_pattern("pg", 6), '<marker id="arrR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#52514e"/></marker></defs>']
    # left: the K row of token 21 (block 1, column 5), as 4 groups of 16 dim pairs
    o.append('<text x="10" y="20" font-size="13" font-weight="600" fill="#0b0b0b">One token\'s K row for one KV head</text>')
    o.append('<text x="10" y="38" font-size="11" fill="#52514e">128 bf16 values = 64 dim pairs of 4 bytes = 256 bytes, in 4 dim steps of 16 pairs</text>')
    cw = 11
    for st in range(4):
        y = 60 + st * 34
        o.append(f'<text x="10" y="{y+12}" font-size="11" fill="#0b0b0b">dim step s{st}</text>')
        o.append(f'<text x="10" y="{y+25}" font-size="10" fill="#52514e">dims {32*st}-{32*st+31}</text>')
        for k in range(16):
            o.append(f'<rect x="{100+k*cw}" y="{y}" width="{cw-1}" height="20" fill="{STEP_HUES[st]}"/>')
        o.append(f'<text x="{100+16*cw+6}" y="{y+14}" font-size="10" fill="#52514e">16 dim pairs = 64 B</text>')
    o.append('<text x="10" y="210" font-size="11" fill="#0b0b0b">Example: token 21 of the page</text>')
    o.append('<text x="10" y="226" font-size="11" fill="#0b0b0b">= token block c1 (tokens 16-31),</text>')
    o.append('<text x="10" y="242" font-size="11" fill="#0b0b0b">column t = 5 inside the block.</text>')
    o.append('<text x="10" y="270" font-size="11" fill="#52514e">Row-major store (the baseline):</text>')
    o.append('<text x="10" y="284" font-size="11" fill="#52514e">the 256 bytes are one contiguous</text>')
    o.append('<text x="10" y="298" font-size="11" fill="#52514e">run = 4 whole cache lines.</text>')
    o.append('<text x="10" y="320" font-size="11" fill="#52514e">VNNI store (this branch): the</text>')
    o.append('<text x="10" y="334" font-size="11" fill="#52514e">same 256 bytes go to 64 different</text>')
    o.append('<text x="10" y="348" font-size="11" fill="#52514e">lines, 4 bytes each (right).</text>')
    # right: the plane as 4 x 4 panels
    px0, py0, P, G = 470, 84, 88, 8
    o.append(f'<text x="{px0}" y="20" font-size="13" font-weight="600" fill="#0b0b0b">The KV head\'s VNNI plane for one page: 16 panels</text>')
    o.append(f'<text x="{px0}" y="38" font-size="11" fill="#52514e">64 tokens x 128 dims = 16 KiB; panel (s, c) = dim step s of token block c</text>')
    py0 = 84
    for c in range(4):
        o.append(f'<text x="{px0+c*(P+G)+P/2:.1f}" y="{py0-22}" font-size="10" text-anchor="middle" fill="#52514e">block c{c}</text>')
        o.append(f'<text x="{px0+c*(P+G)+P/2:.1f}" y="{py0-9}" font-size="10" text-anchor="middle" fill="#52514e">tokens {16*c}-{16*c+15}</text>')
    for st in range(4):
        o.append(f'<text x="{px0+4*(P+G)+2}" y="{py0+st*(P+G)+P/2+4:.1f}" font-size="10" fill="#52514e">dim step s{st}</text>')
        for c in range(4):
            x, y = px0 + c * (P + G), py0 + st * (P + G)
            o.append(f'<rect x="{x}" y="{y}" width="{P}" height="{P}" fill="url(#pg)" stroke="#a9a8a4" stroke-width="0.8"/>')
            if c == 1:
                o.append(f'<rect x="{x}" y="{y}" width="{P}" height="{P}" fill="none" stroke="#0b0b0b" stroke-width="1.5"/>')
                # column 5 of this panel: 16 cells of 4 B, one per line
                cx = x + 5 * (P / 16)
                for r in range(16):
                    o.append(f'<rect x="{cx:.1f}" y="{y + r*(P/16) + 0.5:.1f}" width="{P/16-0.8:.1f}" height="{P/16-1.3:.1f}" fill="{STEP_HUES[st]}"/>')
                # arrow from the row group of this dim step
                o.append(f'<path d="M {100+16*cw+130} {70+st*34+10} C 400 {70+st*34+10}, 420 {y+P/2}, {cx-3:.1f} {y+P/2:.1f}" fill="none" stroke="{STEP_HUES[st]}" stroke-width="1.4" marker-end="url(#arrR)"/>')
    o.append(f'<text x="10" y="{py0+4*(P+G)+18}" font-size="11" fill="#0b0b0b">Token 21\'s row lands in column 5 of the 4 panels of block c1 (black frames): 4 x 16 = 64 lines touched, 4 bytes in each.</text>')
    o.append(f'<text x="10" y="{py0+4*(P+G)+34}" font-size="11" fill="#0b0b0b">Why this layout: one panel is exactly one AMX tile (16 rows x 64 B); the QK kernel loads it as its K operand with no transpose.</text>')
    o.append('</svg>')
    return ('<figure><div class="fig">' + "".join(o) + '</div>'
            '<figcaption class="take">Figure 3.1a: where one token\'s K bytes go. Left: the row, 64 dim pairs in 4 dim steps (colours). Right: the KV head\'s VNNI plane for one page, 4 dim steps x 4 token blocks = 16 panels of 16 lines; '
            'each dim step of token 21 becomes column 5 of the panel (s, c1), one 4-byte cell in each of the panel\'s 16 lines. Storing one token therefore means writing 4 bytes into each of 64 lines; the baseline\'s row-major layout writes the same 256 bytes as 4 whole lines.</figcaption></figure>')


def fig_block_store_steps():
    """Figure 3.1b: filling one panel with 16 full-line stores (block store) against 16 scatters."""
    W, H = 960, 600
    cell = 11
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" aria-label="The block store fills a panel with 16 full-line stores: load one register per token, transpose the 16 by 16 dim pairs, store one register per line; the scatter writes one token\'s 16 dim pairs as 4 bytes into each of the 16 lines" {SVG_HEAD}>',
         '<defs><marker id="arrA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#52514e"/></marker></defs>']
    TOK = ["#2a78d6", "#1baf7a", "#eb6834", "#7a3fbf"]  # 16 tokens, 4 hues repeating: the permutation is what matters
    def grid(x0, y0, colour_of, title1, title2, below, line_rows=False):
        o.append(f'<text x="{x0}" y="{y0-30}" font-size="12" font-weight="600" fill="#0b0b0b">{esc(title1)}</text>')
        o.append(f'<text x="{x0}" y="{y0-16}" font-size="10" fill="#52514e">{esc(title2)}</text>')
        for r in range(16):
            for c in range(16):
                f = colour_of(r, c)
                o.append(f'<rect x="{x0+c*cell}" y="{y0+r*cell}" width="{cell-1}" height="{cell-1}" fill="{f or "#f3f2ef"}"/>')
            if line_rows:
                o.append(f'<rect x="{x0-1}" y="{y0+r*cell-1}" width="{16*cell+1}" height="{cell+1}" fill="none" stroke="#0b0b0b" stroke-width="0.8"/>')
        for k, t in enumerate(below):
            o.append(f'<text x="{x0}" y="{y0+16*cell+14+13*k}" font-size="10" fill="#52514e">{esc(t)}</text>')
        return x0 + 16 * cell
    # ---- after: block store, one dim step of one block (fills one panel)
    o.append('<text x="10" y="20" font-size="13" font-weight="600" fill="#0b0b0b">After: the block store fills one panel with 16 full-line stores (shown for dim step s0 of block c1; the same for s1..s3)</text>')
    gy = 74
    x1 = grid(40, gy, lambda r, c: TOK[r % 4], "1. load 16 registers", "one 64-byte load per token",
              ["row r_t = one register = one token:", "token 16+t's 16 dim pairs of step s0", "cell = one dim pair (4 B)"])
    o.append(f'<line x1="{x1+10}" y1="{gy+8*cell}" x2="{x1+70}" y2="{gy+8*cell}" stroke="#52514e" stroke-width="1.5" marker-end="url(#arrA)"/>')
    o.append(f'<text x="{x1+40}" y="{gy+8*cell-8}" font-size="11" text-anchor="middle" fill="#0b0b0b">transpose</text>')
    o.append(f'<text x="{x1+40}" y="{gy+8*cell+18}" font-size="10" text-anchor="middle" fill="#52514e">64 shuffles</text>')
    x2 = grid(x1+84, gy, lambda r, c: TOK[c % 4], "2. transpose in registers", "16 x 16 dim pairs, 64 shuffles",
              ["row q_dp = one register = one dim pair", "of all 16 tokens; lane (column) = token"])
    o.append(f'<line x1="{x2+10}" y1="{gy+8*cell}" x2="{x2+70}" y2="{gy+8*cell}" stroke="#52514e" stroke-width="1.5" marker-end="url(#arrA)"/>')
    o.append(f'<text x="{x2+40}" y="{gy+8*cell-8}" font-size="11" text-anchor="middle" fill="#0b0b0b">16 stores</text>')
    o.append(f'<text x="{x2+40}" y="{gy+8*cell+18}" font-size="10" text-anchor="middle" fill="#52514e">64 bytes each</text>')
    x3 = grid(x2+84, gy, lambda r, c: TOK[c % 4], "3. store q_dp to line dp", "panel (s0, c1) complete",
              ["row = one 64-byte line of the panel,", "written once, whole; column = token"], line_rows=True)
    o.append(f'<text x="{x3+14}" y="{gy+10}" font-size="11" fill="#0b0b0b">Per block of 16 tokens</text>')
    o.append(f'<text x="{x3+14}" y="{gy+24}" font-size="11" fill="#0b0b0b">and one KV head:</text>')
    o.append(f'<text x="{x3+14}" y="{gy+44}" font-size="11" font-weight="600" fill="#1baf7a">4 dim steps x 16 lines</text>')
    o.append(f'<text x="{x3+14}" y="{gy+58}" font-size="11" font-weight="600" fill="#1baf7a">= 64 full-line stores</text>')
    o.append(f'<text x="{x3+14}" y="{gy+72}" font-size="11" font-weight="600" fill="#1baf7a">(the block\'s 4 panels)</text>')
    o.append(f'<text x="{x3+14}" y="{gy+92}" font-size="11" fill="#52514e">plus 64 loads and</text>')
    o.append(f'<text x="{x3+14}" y="{gy+106}" font-size="11" fill="#52514e">4 x 64 shuffles.</text>')
    # ---- before: the scatter
    gy2 = gy + 16 * cell + 112
    o.append(f'<text x="10" y="{gy2-46}" font-size="13" font-weight="600" fill="#0b0b0b">Before: the per-token scatter, one token at a time (token 21 = column 5 of block c1, dim step s0)</text>')
    t = 5
    for r in range(16):
        for c in range(16):
            o.append(f'<rect x="{40+c*cell}" y="{gy2+r*cell}" width="{cell-1}" height="{cell-1}" fill="{TOK[t % 4] if r == t else "#f3f2ef"}"/>')
    o.append(f'<text x="40" y="{gy2-16}" font-size="10" fill="#52514e">one register: token 21, step s0 (64 B)</text>')
    o.append(f'<text x="40" y="{gy2+16*cell+14}" font-size="10" fill="#52514e">the other 15 tokens are not in registers</text>')
    o.append(f'<line x1="{x1+10}" y1="{gy2+8*cell}" x2="{x1+70}" y2="{gy2+8*cell}" stroke="#52514e" stroke-width="1.5" marker-end="url(#arrA)"/>')
    o.append(f'<text x="{x1+40}" y="{gy2+8*cell-8}" font-size="11" text-anchor="middle" fill="#0b0b0b">1 scatter</text>')
    o.append(f'<text x="{x1+40}" y="{gy2+8*cell+18}" font-size="10" text-anchor="middle" fill="#52514e">16 x 4 bytes</text>')
    xb = x1 + 84
    o.append(f'<text x="{xb}" y="{gy2-16}" font-size="10" fill="#52514e">panel (s0, c1): column 5, 4 B per line</text>')
    for r in range(16):
        for c in range(16):
            o.append(f'<rect x="{xb+c*cell}" y="{gy2+r*cell}" width="{cell-1}" height="{cell-1}" fill="{TOK[t % 4] if c == t else "#f3f2ef"}"/>')
        o.append(f'<rect x="{xb-1}" y="{gy2+r*cell-1}" width="{16*cell+1}" height="{cell+1}" fill="none" stroke="#a9a8a4" stroke-width="0.6" stroke-dasharray="2,2"/>')
    o.append(f'<text x="{xb}" y="{gy2+16*cell+14}" font-size="10" fill="#52514e">16 partial-line writes; the other 15</text>')
    o.append(f'<text x="{xb}" y="{gy2+16*cell+27}" font-size="10" fill="#52514e">tokens each do the same to these lines</text>')
    xr = xb + 16 * cell + 30
    o.append(f'<text x="{xr}" y="{gy2+10}" font-size="11" fill="#0b0b0b">Per block of 16 tokens and one KV head:</text>')
    o.append(f'<text x="{xr}" y="{gy2+30}" font-size="11" font-weight="600" fill="#d03b3b">16 tokens x 4 scatters = 64 scatters</text>')
    o.append(f'<text x="{xr}" y="{gy2+44}" font-size="11" font-weight="600" fill="#d03b3b">= 1024 writes of 4 bytes; every line</text>')
    o.append(f'<text x="{xr}" y="{gy2+58}" font-size="11" font-weight="600" fill="#d03b3b">of the 4 panels is touched 16 times</text>')
    o.append(f'<text x="{xr}" y="{gy2+82}" font-size="11" fill="#52514e">Measured: Save K per prefill layer</text>')
    o.append(f'<text x="{xr}" y="{gy2+96}" font-size="11" fill="#52514e">858 -&gt; 346 us (tp2) with the block</text>')
    o.append(f'<text x="{xr}" y="{gy2+110}" font-size="11" fill="#52514e">store; L1-resident microbenchmark</text>')
    o.append(f'<text x="{xr}" y="{gy2+124}" font-size="11" fill="#52514e">681 -&gt; 169 cycles per 16 tokens.</text>')
    o.append('</svg>')
    return ('<figure><div class="fig">' + "".join(o) + '</div>'
            '<figcaption class="take">Figure 3.1b: how a panel gets written. Top (block store): for one dim step, one 64-byte load per token puts token 16+t\'s 16 dim pairs into register r_t; the 16 x 16 transpose in registers turns them into q_dp = dim pair dp of all 16 tokens; '
            'storing q_dp to line dp writes the panel\'s 16 lines once each, whole. The four dim steps fill the block\'s 4 panels with 64 full-line stores. Bottom (scatter): one token\'s register is scattered as 4 bytes into each of the panel\'s 16 lines, and 16 tokens repeat this on the same lines. '
            'Colours mark tokens (four hues repeat); the transpose is visible as rows becoming columns.</figcaption></figure>')


def fig_partial_and_lone():
    """Figure 3.1c: a partial block (mask) and a lone token (decode keeps the scatter)."""
    W, H = 960, 330
    cell = 11
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" aria-label="A partial block uses the same 16 stores with a lane mask so only the present tokens\' columns are written; a token alone in its block would gain nothing from masked full-line stores and keeps the scatter" {SVG_HEAD}>']
    TOK = ["#2a78d6", "#1baf7a", "#eb6834", "#7a3fbf"]
    def panel(x0, y0, present, title, sub, below):
        o.append(f'<text x="{x0}" y="{y0-30}" font-size="12" font-weight="600" fill="#0b0b0b">{esc(title)}</text>')
        o.append(f'<text x="{x0}" y="{y0-16}" font-size="10" fill="#52514e">{esc(sub)}</text>')
        for r in range(16):
            for c in range(16):
                if c in present:
                    f = TOK[c % 4]
                else:
                    f = "#d9d8d4"  # bytes of other tokens: untouched
                o.append(f'<rect x="{x0+c*cell}" y="{y0+r*cell}" width="{cell-1}" height="{cell-1}" fill="{f}"/>')
            o.append(f'<rect x="{x0-1}" y="{y0+r*cell-1}" width="{16*cell+1}" height="{cell+1}" fill="none" stroke="#0b0b0b" stroke-width="0.8"/>')
        for k, t in enumerate(below):
            o.append(f'<text x="{x0}" y="{y0+16*cell+14+13*k}" font-size="10" fill="#52514e">{esc(t)}</text>')
    gy = 60
    panel(40, gy, set(range(10)), "Partial block: tokens 0-9 present",
          "a user's chunk ends 10 tokens into the block",
          ["same 16 full-line stores, each with a lane mask:", "only columns 0-9 are written (colour); the grey", "cells (other tokens' bytes) are left untouched"])
    panel(400, gy, {5}, "A token alone in its block (decode)",
          "one token per user per step",
          ["a masked store would still write 4 B per line:", "16 stores per panel, no better than the 1 scatter;", "so a lone token keeps scatter_row (4 scatters)"])
    xr = 720
    o.append(f'<text x="{xr}" y="{gy+10}" font-size="11" fill="#0b0b0b">Rule in save_k (store_k_block):</text>')
    o.append(f'<text x="{xr}" y="{gy+30}" font-size="11" fill="#0b0b0b">a run of 2 to 16 consecutive tokens</text>')
    o.append(f'<text x="{xr}" y="{gy+44}" font-size="11" fill="#0b0b0b">in the same block of the same page</text>')
    o.append(f'<text x="{xr}" y="{gy+58}" font-size="11" fill="#0b0b0b">-&gt; block store with the run\'s mask;</text>')
    o.append(f'<text x="{xr}" y="{gy+78}" font-size="11" fill="#0b0b0b">a run of 1 -&gt; scatter_row.</text>')
    o.append(f'<text x="{xr}" y="{gy+102}" font-size="11" fill="#52514e">Prefill passes here: 8 users x 128</text>')
    o.append(f'<text x="{xr}" y="{gy+116}" font-size="11" fill="#52514e">tokens = 64 whole blocks per pass,</text>')
    o.append(f'<text x="{xr}" y="{gy+130}" font-size="11" fill="#52514e">mask 0xffff, no partial block.</text>')
    o.append(f'<text x="{xr}" y="{gy+150}" font-size="11" fill="#52514e">Decode: 8 lone tokens per pass,</text>')
    o.append(f'<text x="{xr}" y="{gy+164}" font-size="11" fill="#52514e">all through the scatter: the decode</text>')
    o.append(f'<text x="{xr}" y="{gy+178}" font-size="11" fill="#52514e">Save K span is unchanged (2.3).</text>')
    o.append('</svg>')
    return ('<figure><div class="fig">' + "".join(o) + '</div>'
            '<figcaption class="take">Figure 3.1c: the two other cases. A partial block (left) uses the same 16 stores per panel with a lane mask, so only the present tokens\' 4-byte columns change; a token alone in its block (right, the decode case) would need 16 masked stores per panel for 4 bytes each, no better than one scatter, so it keeps the scatter.</figcaption></figure>')


def striping_svg(n_helpers=7, save_k_before_us=858, save_k_after_us=175):
    """(b) helper striping: the window protocol as who-does-what-when lanes, with the item list
    cut into page-block work units claimed from one counter."""
    W, H = 960, 560
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" aria-label="Helper striping: main cuts the pass\'s tokens into page-block units and opens a window; main and the idle helpers claim units from one counter and store them; main waits for every helper to finish, then marks the tokens complete" xmlns="http://www.w3.org/2000/svg" style="font-family:system-ui,sans-serif;">',
         '<defs><marker id="arrB" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#52514e"/></marker></defs>']
    THREAD = ["#d03b3b", "#2a78d6", "#1baf7a", "#eb6834", "#7a3fbf", "#c9a227", "#0ca3a3", "#8a8987"]
    # --- 1. the item list cut into units
    o.append('<text x="10" y="18" font-size="12" font-weight="600" fill="#0b0b0b">1. main cuts the pass\'s item list into work units: one unit = one 16-token page block</text>')
    ux, uy, uw, uh = 10, 30, 14, 20
    n_units = 64
    # who stores which unit: a plausible dynamic claim order (main first, then round-robin as threads arrive)
    claim = [(k % (n_helpers + 1)) for k in range(n_units)]
    for k in range(n_units):
        o.append(f'<rect x="{ux+k*uw}" y="{uy}" width="{uw-1}" height="{uh}" fill="{THREAD[claim[k]]}" opacity="0.85"/>')
        if k % 8 == 0:
            o.append(f'<line x1="{ux+k*uw-0.5}" y1="{uy-4}" x2="{ux+k*uw-0.5}" y2="{uy+uh+4}" stroke="#0b0b0b" stroke-width="1"/>')
            o.append(f'<text x="{ux+k*uw+4*uw}" y="{uy+uh+16}" font-size="10" text-anchor="middle" fill="#52514e">user {k//8+1}</text>')
    o.append(f'<line x1="{ux+n_units*uw-0.5}" y1="{uy-4}" x2="{ux+n_units*uw-0.5}" y2="{uy+uh+4}" stroke="#0b0b0b" stroke-width="1"/>')
    o.append(f'<text x="10" y="{uy+uh+34}" font-size="11" fill="#52514e">1024 items of one prefill pass (8 users x 128 tokens) = 64 units of 16 tokens; a unit ends where the page, the block or the KV flag changes.</text>')
    o.append(f'<text x="10" y="{uy+uh+48}" font-size="11" fill="#52514e">Colour = the thread that claimed the unit (main = red, helpers = the other colours): every page block has exactly one writer.</text>')
    # --- 2. lanes
    ly0 = uy + uh + 80
    o.append(f'<text x="10" y="{ly0-8}" font-size="12" font-weight="600" fill="#0b0b0b">2. the window, as who-does-what-when (schematic, not to scale)</text>')
    LEFT, RIGHT = 120, 30
    lanes = ["main"] + [f"helper {i}" for i in range(1, n_helpers + 1)]
    LH = 24
    def lane_y(i):
        return ly0 + 8 + i * (LH + 6)
    # x positions of the phases (fractions of the lane width)
    x = lambda f: LEFT + f * (W - LEFT - RIGHT)
    for i, name in enumerate(lanes):
        yy = lane_y(i)
        o.append(f'<rect x="{LEFT}" y="{yy}" width="{W-LEFT-RIGHT}" height="{LH}" fill="#f7f6f3"/>')
        o.append(f'<text x="{LEFT-8}" y="{yy+LH*0.7}" font-size="12" text-anchor="end" fill="#52514e">{esc(name)}</text>')
    def block(i, f0, f1, col, label, dashed=False, textcol="#fff"):
        yy = lane_y(i)
        if dashed:
            o.append(f'<rect x="{x(f0):.1f}" y="{yy+2}" width="{x(f1)-x(f0):.1f}" height="{LH-4}" fill="none" stroke="#a9a8a4" stroke-dasharray="3,3"/>')
            o.append(f'<text x="{(x(f0)+x(f1))/2:.1f}" y="{yy+LH*0.7}" font-size="10" text-anchor="middle" fill="#52514e">{esc(label)}</text>')
        else:
            o.append(f'<rect x="{x(f0):.1f}" y="{yy+2}" width="{x(f1)-x(f0):.1f}" height="{LH-4}" fill="{col}"/>')
            o.append(f'<text x="{(x(f0)+x(f1))/2:.1f}" y="{yy+LH*0.7}" font-size="10" text-anchor="middle" fill="{textcol}">{esc(label)}</text>')
    # main lane
    block(0, 0.00, 0.07, "#52514e", "wait K")
    block(0, 0.07, 0.14, "#d03b3b", "cut units")
    block(0, 0.14, 0.19, "#0b0b0b", "open")
    block(0, 0.19, 0.60, "#d03b3b", "claim + store units, like a helper (fetch_add on next_unit)")
    block(0, 0.60, 0.69, "", "wait fin == 7", dashed=True)
    block(0, 0.69, 0.85, "#d03b3b", "mark tokens complete")
    block(0, 0.85, 1.00, "#0b0b0b", "release attention")
    # helper lanes
    for i in range(1, n_helpers + 1):
        block(i, 0.00, 0.09, "#1baf7a", "rope kernel")
        block(i, 0.09, 0.19, "", "wait open", dashed=True)
        end = 0.60 - 0.02 * ((i * 3) % 4)  # helpers finish at slightly different times
        block(i, 0.19, end, THREAD[i], "claim + store units")
        block(i, end, end + 0.04, "#0b0b0b", "fin++")
        block(i, end + 0.04, 1.00, "", "idle until the attention output (as before)", dashed=True)
    # arrows: open -> helpers; finished -> main
    yo = lane_y(0) + LH
    # counter box right under the lanes; the two release annotations below it,
    # each at the foot of its dashed line
    cy = lane_y(n_helpers) + LH + 10
    o.append(f'<rect x="{x(0.23):.1f}" y="{cy}" width="{x(0.59)-x(0.23):.1f}" height="22" fill="#fff" stroke="#0b0b0b"/>')
    o.append(f'<text x="{x(0.41):.1f}" y="{cy+15}" font-size="10" text-anchor="middle" fill="#0b0b0b">next_unit: one atomic counter, one claim per unit</text>')
    ay = cy + 40
    o.append(f'<line x1="{x(0.165):.1f}" y1="{yo}" x2="{x(0.165):.1f}" y2="{ay}" stroke="#0b0b0b" stroke-width="1.2" stroke-dasharray="4,3"/>')
    o.append(f'<line x1="{x(0.645):.1f}" y1="{ay}" x2="{x(0.645):.1f}" y2="{yo}" stroke="#0b0b0b" stroke-width="1.2" stroke-dasharray="4,3" marker-end="url(#arrB)"/>')
    o.append(f'<text x="{x(0.165):.1f}" y="{ay+14}" font-size="10" text-anchor="middle" fill="#0b0b0b">open = opened++ (release):</text>')
    o.append(f'<text x="{x(0.165):.1f}" y="{ay+27}" font-size="10" text-anchor="middle" fill="#0b0b0b">the helpers\' W-th call may enter window W</text>')
    o.append(f'<text x="{x(0.645):.1f}" y="{ay+14}" font-size="10" text-anchor="middle" fill="#0b0b0b">fin++ = finished++ (release) by each helper;</text>')
    o.append(f'<text x="{x(0.645):.1f}" y="{ay+27}" font-size="10" text-anchor="middle" fill="#0b0b0b">main goes on when all 7 have finished</text>')
    cy = ay + 10
    # --- 3. before / after bars
    by = cy + 62
    o.append(f'<text x="10" y="{by}" font-size="12" font-weight="600" fill="#0b0b0b">3. the Save K span of one prefill layer, measured (tp2, 1024 tokens, 8 KV heads)</text>')
    bx0 = 240
    scale = (W - bx0 - 90) / max(save_k_before_us, 1)
    o.append(f'<text x="{bx0-8}" y="{by+26}" font-size="11" text-anchor="end" fill="#52514e">before: main alone</text>')
    o.append(f'<rect x="{bx0}" y="{by+12}" width="{save_k_before_us*scale:.1f}" height="18" fill="#d03b3b"/>')
    o.append(f'<text x="{bx0+save_k_before_us*scale+6:.1f}" y="{by+26}" font-size="11" fill="#0b0b0b">{save_k_before_us} us</text>')
    o.append(f'<text x="{bx0-8}" y="{by+54}" font-size="11" text-anchor="end" fill="#52514e">after: main + {n_helpers} helpers</text>')
    o.append(f'<rect x="{bx0}" y="{by+40}" width="{save_k_after_us*scale:.1f}" height="18" fill="#7a3fbf"/>')
    o.append(f'<text x="{bx0+save_k_after_us*scale+6:.1f}" y="{by+54}" font-size="11" fill="#0b0b0b">{save_k_after_us} us ({save_k_before_us/save_k_after_us:.1f}x shorter; the ideal with {n_helpers+1} threads is {save_k_before_us/(n_helpers+1):.0f} us, est.)</text>')
    o.append('</svg>')
    return ('<figure style="margin:8px 0 4px;"><div class="fig">' + "".join(o) + '</div>'
            '<figcaption class="take">Figure 3.2: helper striping. Main cuts the pass\'s items into page-block units, opens the window, and then behaves like a helper: every thread takes the next unit from one counter and stores it. '
            'A helper leaves the window when the counter is exhausted and increments finished; main returns only when all helpers have finished, so every unit is stored before the completion marks and the attention release. '
            'The lanes are schematic; the bars carry the measured span at tp2 (7 helpers): the gap to the ideal 8x is the join and the helpers\' arrival at the window.</figcaption></figure>')


def main():
    an1 = jload(f"{TRACE1}/analysis.json")
    an2 = jload(f"{TRACE2}/analysis.json")
    lanes = {n: jload(f"{TRACE1}/{n}.perfetto-trace.lanes.json") for n in ("base-tp2", "vnni-tp2", "base-tp4", "vnni-tp4")}
    summary = jload(f"{RES2}/summary.json")
    smoke = read(f"{RES2}/smoke/smoke.txt")
    build = read(f"{RES2}/build.txt")
    tests = read(f"{RES2}/tests.txt")
    status = read(f"{EXEC}/logs/vnnik2-20260915.status").strip()
    marker = read(f"{EXEC}/logs/vnnik2-20260915.done").strip() or "running"
    summary1 = jload(f"{RES1}/summary.json")

    def tr(arm, tp, kind, key):
        for r in (an1 or []) + (an2 or []):
            if r["trace"] == f"{arm}-tp{tp}.perfetto-trace" and kind in r["kinds"]:
                return r["kinds"][kind][key]
        return None

    # short version numbers
    sk = {(a, t): tr(a, t, "prefill", "save_k_us_per_layer") for a in ("base", "vnni", "vnni0", "a", "b", "ab") for t in (2, 4)}
    dk = {(a, t): tr(a, t, "decode", "save_k_us_per_layer") for a in ("base", "vnni") for t in (2, 4)}

    def d(summary, tp, prompt, a, b, key):
        if not summary:
            return None
        for x in summary["deltas"]:
            if x["tp"] == tp and x["prompt"] == prompt and x["a"] == a and x["b"] == b:
                return x[key]
        return None

    sh_pre = (100 * (tr("vnni", 2, "prefill", "save_k_share") or 0), 100 * (tr("base", 2, "prefill", "save_k_share") or 0),
              100 * (tr("vnni", 4, "prefill", "save_k_share") or 0), 100 * (tr("base", 4, "prefill", "save_k_share") or 0))
    diff_us = (sk[("vnni", 2)] or 0) - (sk[("base", 2)] or 0)
    # Short version: three sentences a newcomer can follow; the detail follows as
    # one claim per bullet (plain-english rules 2, 5, 7, 8).
    short = (f"<b>Short version.</b> In prefill the VNNI K store (Save K) takes {fmt(sk[('vnni',2)],0)} us per layer against {fmt(sk[('base',2)],0)} us for the baseline's row-major store, "
             f"and the layer's attention work waits for it, which makes this store the cause of the VNNI-K TTFT cost. "
             f"In decode the store is also slow ({fmt(dk[('vnni',2)],0)} us per layer against {fmt(dk[('base',2)],0)} us), but it overlaps the attention workers' work on the earlier pages and adds no time to a decode step. "
             f"Two remedies, a block store (16 tokens transposed in registers, whole cache lines written) and helper striping (the idle helper threads share the store), are built as switchable paths in one binary, and ")
    detail = [
        f"The Perfetto trace (the trace recorder built into tron) puts Save K at {fmt(sk[('vnni',2)],0)} us per layer at tp2 (the model split over two FPGA cards) and {fmt(sk[('vnni',4)],0)} us at tp4 (four cards). It is one thread's serial work, so the tensor-parallel width does not change it.",
        f"The baseline's row-major store (one contiguous 256-byte row per token) takes {fmt(sk[('base',2)],0)} us at tp2 and {fmt(sk[('base',4)],0)} us at tp4.",
        f"The store's share of a prefill pass rises 3x: from {sh_pre[1]:.1f}% to {sh_pre[0]:.1f}% at tp2, and from {sh_pre[3]:.1f}% to {sh_pre[2]:.1f}% at tp4.",
        "The pending attention sections (the work over the pages written in this pass) start only after Save K and Save V. So every microsecond of Save K moves the end of the layer (section 2.2).",
        f"The span difference is {diff_us:.0f} us per layer, or {8*36*diff_us/1000:.0f} ms over the 8 prefill passes of the 8 x 1024-token prompt set. At tp4 the measured TTFT increase was +171 ms, the same number. At tp2 the measured increase was +71 ms, so the transpose-free attention kernel (it reads the VNNI plane directly) offsets about {8*36*diff_us/1000-71:.0f} ms (est.).",
        f"In decode the store takes {fmt(dk[('vnni',2)],0)} us per layer against {fmt(dk[('base',2)],0)} us for base, about {100*(tr('vnni',2,'decode','save_k_share') or 0):.0f}% of a {fmt(tr('vnni',2,'decode','pass_ms'),1)} ms step ({fmt(36*(dk[('vnni',2)] or 0)/1000,1)} ms per step).",
        "The attention workers run their Ready sections (this step's query against the users' earlier pages) during Save K. Each worker's Pending section starts only after its own Ready work, about 110 us after Save K began. A shorter store would therefore not shorten the step (section 2.3).",
    ]
    if summary:
        parts = []
        for tp in (2, 4):
            for arm in ("a", "b", "ab"):
                dd = d(summary, tp, 1024, arm, "vnni0", "ttft_delta_pct")
                dm = d(summary, tp, 1024, arm, "vnni0", "ttft_delta_ms")
                if dd is not None:
                    parts.append(f"{arm} {dd:+.1f}% ({dm:+.0f} ms) at tp{tp}")
        vb = [d(summary, tp, 1024, "ab", "base", "ttft_delta_pct") for tp in (2, 4)]
        short += "their measurement is in section 4."
        detail.append(f"Commit {NEW_TIP} adds the block store and the helper striping, each with a runtime switch, so one binary provides the arms vnni0 (both off) / a / b / a+b. Against vnni0 the prompt-1024 TTFT changes by {'; '.join(parts) if parts else 'pending'}.")
        if all(v is not None for v in vb):
            detail.append(f"With both remedies the branch's TTFT at prompt 1024 is {fmt(vb[0])}% at tp2 and {fmt(vb[1])}% at tp4 against the AMX baseline (Monday: +2.2% and +7.8%). Decode TPS is unchanged.")
    else:
        short += "their measurement is running."
        phase = ("the tp2 cells are running" if "runtron tp2" in status else "the tp4 cells are running (tp2 done)" if "runtron tp4 prompt=1024" in status or "runtron tp4 prompt=2048" in status
                 else "the prompt-8192 cells are running (tp2 and tp4 done)" if "8192" in status else "the smoke or the traces are running" if "phase 2" in status else "it is waiting for the build" if "phase 1" in status else esc(status))
        detail.append(f"Commit {NEW_TIP} adds the block store and the helper striping, each with a runtime switch, so one binary provides the arms vnni0 (both off) / a / b / a+b. The measurement campaign is running: {phase}.")

    H = []
    H.append('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">')
    H.append('<title>VNNIed K store remedies</title>')
    H.append('''<style>
:root { --ink:#0b0b0b; --muted:#52514e; --line:#e6e5e1; --bg:#fcfcfb; --panel:#f3f2ef; --accent:#2a78d6; --warn:#d03b3b; --ok:#0ca30c; }
body { margin:0; padding:24px 16px 48px; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:1000px; margin:0 auto; }
h1 { font-size:26px; margin:0 0 6px; } h2 { font-size:20px; margin:30px 0 8px; border-bottom:1px solid var(--line); padding-bottom:4px; } h3 { font-size:16px; margin:18px 0 6px; } h4 { font-size:14px; margin:14px 0 4px; color:var(--muted); }
figure { margin:0; } figcaption { margin-top:4px; }
.sub { color:var(--muted); margin-bottom:16px; }
.short { background:var(--panel); border-left:4px solid var(--accent); padding:10px 14px; margin:14px 0; }
table { border-collapse:collapse; width:100%; margin:10px 0 14px; font-size:14px; } th, td { border:1px solid var(--line); padding:6px 8px; vertical-align:top; text-align:left; } th { background:var(--panel); }
td:nth-child(n+3) { font-variant-numeric: tabular-nums; }
code, pre { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px; } pre { background:var(--panel); border:1px solid var(--line); padding:10px 12px; overflow-x:auto; }
.fig { margin:6px 0 4px; border:1px solid var(--line); background:#fff; padding:8px; overflow-x:auto; }
.legend { display:flex; flex-wrap:wrap; gap:14px; font-size:13px; color:var(--muted); margin:10px 0 0; } .key { display:inline-flex; align-items:center; gap:6px; } .sw { display:inline-block; width:12px; height:12px; border-radius:2px; }
.pending { color:var(--muted); font-style:italic; } .warn { color:var(--warn); font-weight:600; } .ok { color:var(--ok); font-weight:600; }
.take { font-size:14px; color:var(--muted); margin:2px 0 12px; }
ul { margin:6px 0 10px 22px; } li { margin:3px 0; }
</style></head><body><main>''')
    H.append('<h1>VNNIed K in place: the K store, measured and shortened</h1>')
    H.append(f'<p class="sub">Generated {NOW}. Trace measurement: exec/results/vnnik-trace-20260914 (base and vnni binaries, 2026-09-14 22:2x UTC). Remedies: commit {NEW_TIP} on branch jhan-amx-vnniK; their campaign exec/results/vnnik2-20260915, status <b>{esc(marker)}</b> ({esc(status)}). Follows status/Monday-morning-report.html section 7.1.</p>')
    H.append(f'<div class="short"><p>{short}</p><p><b>The findings in more detail:</b></p><ul>' + "".join(f"<li>{x}</li>" for x in detail) + '</ul></div>')

    H.append('<h2>1. Words used here</h2><table><tr><th>Term</th><th>Meaning</th></tr>')
    for t, m in [("tron, runtron", "tron is the inference program under test; runtron is its command-line tool, which produced every number here."),
                 ("Perfetto, span", "Perfetto is the trace recorder built into tron; a span is one timed region of one thread in the trace (begin and end), named in the code with TRACE_EVENT."),
                 ("tp2, tp4", "The model split over two or four FPGA cards (tensor parallelism); the CPU attention runs on 28 (tp2) or 56 (tp4) application cores of one socket."),
                 ("AMX, AVX-512", "The Intel matrix (tile) and vector instruction sets of the Xeon 6 host delphi-3bda."),
                 ("VNNI layout", "The pair-interleaved K layout the AMX tile multiply needs as its right operand; the branch stores K in it. One token's 128 values sit in 64 different 64-byte lines (4 bytes each)."),
                 ("Save K, Save V", "The trace spans of the functions that copy the K and V vectors of the pass's tokens into the KV cache (model.hpp save_k_impl / save_v_impl), once per layer per pass, on the main thread."),
                 ("pass", "One forward() call of the scheduler. In these runs a prefill pass holds 128 tokens of each of the 8 users (1024 token jobs); a decode pass holds one token per user (8)."),
                 ("main thread, main helpers, attention workers", "The generated qwen plugin runs the forward pass on one main thread; a fixed set of main helpers runs the per-token kernels (norms, rope) in stripes; the remaining application-pool threads are attention workers. At tp2: 1 + 7 + 20 threads on 28 app cores; at tp4: 1 + 8 + 47 on 56."),
                 ("Attention Ready / Pending", "An attention worker's section over pages written in earlier passes (Ready) or over the pages written in this pass (Pending). Pending sections wait for Save K and Save V of the layer."),
                 ("arms", "base = the PR #3879 binary (row-major K); vnni = Monday's VNNI binary (per-token scatter store); vnni0 / a / b / ab = one new binary with the two remedies switched off / block store only / helper striping only / both (TRON_K_VNNI_BLOCK, TRON_K_VNNI_STRIPE)."),
                 ("TPS, TTFT", "TPS = generated tokens per second per user during decode (runtron's &quot;average tok/s&quot;, mean over the 8 users). TTFT = time to first token = runtron's &quot;Parsing the prompt took&quot; seconds, the batched prefill of the 8 prompts."),
                 ("prompt N", "Prompt length in tokens; every run then generates 256 tokens per user (the traced runs generate 32)."),
                 ("ns per K row", "Save K span divided by (tokens x KV heads) of the pass: the store time of one token's 128-value K vector for one KV head.")]:
        H.append(f"<tr><td>{esc(t)}</td><td>{m}</td></tr>")
    H.append("</table>")

    # ---- section 2: trace measurement
    H.append('<h2>2. The Save K span, traced (base and vnni, tp2 and tp4, prompt 1024)</h2>')
    H.append('<p>Recipe: the Monday campaign\'s placement and binaries, 8 users, prompt 1024, 32 generated tokens, <code>--trace-gen FILE --trace-passes 1-16</code> (the 8 prefill passes and 8 decode steps, in-process Perfetto backend) with <code>TRON_TRACE_CATEGORIES=&quot;-*,+model,+scheduler&quot;</code> (only the spans read here are recorded, so the trace overhead stays small: the traced prefill of 8 x 1024 tokens took 3.14 s (base) and 3.22 s (vnni) at tp2 against 3.151 and 3.221 s untraced on Monday). Script exec/vnnik-trace-20260914/trace.sh; analysis analyze.py; one layer\'s lanes lanes.py.</p>')
    H.append('<h3>2.1 Prefill: one number per layer, the same at tp2 and tp4</h3>')
    H.append(trace_table(an1, "prefill", ["base", "vnni"]))
    if sk[("vnni", 2)] and sk[("base", 2)]:
        H.append(f'<p>Reading. The VNNI store takes {sk[("vnni",2)]:.0f} us per layer at tp2 and {sk[("vnni",4)]:.0f} us at tp4: the same number, because it is one thread\'s serial work and the tensor-parallel width changes nothing about it. '
                 f'The row-major store takes {sk[("base",2)]:.0f} / {sk[("base",4)]:.0f} us. The difference, {sk[("vnni",2)]-sk[("base",2)]:.0f} us per layer, is {36*(sk[("vnni",2)]-sk[("base",2)])/1000:.1f} ms per prefill pass and {8*36*(sk[("vnni",2)]-sk[("base",2)])/1000:.0f} ms over the 8 passes of an 8 x 1024-token prefill. '
                 f'Monday\'s untraced TTFT difference was +71 ms at tp2 and +171 ms at tp4: at tp4 the store difference is the whole TTFT difference, at tp2 the transpose-free kernel recovers about 100 ms of it [status/Monday-morning-report.html section 7.1]. '
                 f'Per K row (one token, one KV head, 256 bytes) the scatter costs {tr("vnni",2,"prefill","save_k_ns_per_row"):.0f} ns against {tr("base",2,"prefill","save_k_ns_per_row"):.0f} ns: it writes 4 bytes into each of 64 cache lines where the row-major store writes 4 whole lines.</p>')
    H.append('<h3>2.2 Where the span sits: one prefill layer, all threads</h3>')
    H.append('<p>The lanes below are layer 10 of prefill pass 3 (the third 128-token chunk of every user, so each user already has 2 ready pages and gets 2 pending ones). Time 0 is the start of the layer\'s Save K. Solid blocks are recorded spans; dashed outlines are gaps between a thread\'s spans (waiting). Durations are to scale.</p>')
    for n, t in (("base-tp2", "base, tp2"), ("vnni-tp2", "vnni, tp2")):
        H.append(lanes_svg(lanes.get(n), f"{t}: prefill pass 3, layer 10"))
    H.append('<p class="take">What the figure shows: the main helpers finish the K/Q rope kernel just before Save K and then wait (their next kernel needs the attention output). The attention workers run their Ready sections during Save K, but the Pending sections start only after Save V ends, and they are the lanes that end last; the joins follow them. So every microsecond of Save K moves the end of the layer by the same amount, on both binaries; the vnni span is the wider red block.</p>')
    for n, t in (("base-tp4", "base, tp4"), ("vnni-tp4", "vnni, tp4")):
        H.append(lanes_svg(lanes.get(n), f"{t}: prefill pass 3, layer 10"))
    H.append('<p class="take">At tp4 the attention work per worker is smaller (47 workers instead of 20), so the same Save K span is a larger share of the layer; that is why the TTFT cost showed at tp4 first.</p>')
    H.append('<h3>2.3 Decode: the same slow store, hidden behind the attention workers</h3>')
    H.append(trace_table(an1, "decode", ["base", "vnni"]))
    if dk[("vnni", 2)]:
        H.append(f'<p>In decode (8 tokens per pass, one per user) the VNNI store takes {dk[("vnni",2)]:.0f} us per layer at tp2 and {dk[("vnni",4)]:.0f} us at tp4 against {dk[("base",2)]:.0f} / {dk[("base",4)]:.0f} us for base: 6x longer, and per row even worse than in prefill ({tr("vnni",2,"decode","save_k_ns_per_row"):.0f} / {tr("vnni",4,"decode","save_k_ns_per_row"):.0f} ns against {tr("vnni",2,"prefill","save_k_ns_per_row"):.0f} ns), because the 64 lines of a token\'s column are cold in decode and every 4-byte write pays a line fetch. Over 36 layers that is {36*dk[("vnni",2)]/1000:.2f} ms of a {tr("vnni",2,"decode","pass_ms"):.1f} ms decode step at tp2 ({100*tr("vnni",2,"decode","save_k_share"):.0f}% of the step; the Monday report\'s estimate of 0.16 ms per step was 6x too low).</p>')
        H.append('<p>Why it costs no decode time. The lanes below are layer 10 of a decode step, drawn like figure 2.2 (time in us). The attention workers start their Ready sections (this step\'s query against the users\' earlier pages: 16 pages x 8 KV heads spread over the workers) at the same instant Save K starts, and those sections last 100 to 180 us. Each worker\'s Pending section (the query against the page that receives the new token) begins only after that worker\'s own Ready work, about 110 us in, when Save K (25 us) and Save V have long ended. So the layer\'s end is set by the Ready work plus the join, and a shorter Save K would move nothing; the store is hidden, not free. With a shorter context (fewer Ready pages) or faster attention it would come out from behind the Ready sections.</p>')
    for n, t in (("vnni-tp2", "vnni, tp2"), ("base-tp2", "base, tp2")):
        H.append(lanes_svg(lanes.get(n), f"{t}: decode step 4, layer 10", "decode"))
    H.append('<p class="take">Compare the two main lanes: the vnni Save K is 6x the base one, and in both figures the Pending sections start about 110 us after Save K began, behind the Ready sections, so the layer ends at the same relative time. The remedies below do not change the decode store (one token per user per step: no 16-token run to transpose, no window to share).</p>')

    # ---- section 3: remedies
    H.append('<h2>3. The two remedies, built as switchable paths in one binary</h2>')
    H.append(f'<p>Commit {NEW_TIP} on jhan-amx-vnniK (7 files, +469 / -45 lines). Both remedies default on; each has a runtime switch (exactly &quot;0&quot; disables, like the AMX kill switch), so one binary gives the arms vnni0, a, b, ab and the arms interleave inside every repetition.</p>')
    H.append('<h3>3.1 (a) Block store: transpose 16 tokens in registers, write whole lines</h3>')
    H.append('<p>What it does. The pass\'s tokens arrive in position order, so runs of up to 16 consecutive tokens fall into one 16-token block of one page. For such a run save_k now loads the 16 rows (one 64-byte load per row per dim step), transposes the 16 x 16 matrix of 32-bit dim pairs in registers (64 shuffles), and writes each of the panel\'s 16 pair rows as one 64-byte store: 64 full-line stores per block and KV head instead of 64 scatters that write 4 bytes into each of 64 lines. A partial run uses a masked store of the present tokens\' lanes; a token alone in its block (decode) keeps the per-token scatter [h/tron/kernels/k_vnni.hpp store_block, transpose_16x16_epi32; h/tron/models/kv_cache.hpp set_k_block; h/tron/models/model.hpp store_k_block]. Switch: <code>TRON_K_VNNI_BLOCK=0</code>.</p>')
    H.append('<h4>3.1.1 How the block store moves the bytes</h4>')
    H.append('<p>Words used in the figures below:</p><table><tr><th>Term</th><th>Meaning</th></tr>'
             '<tr><td>K row</td><td>One token\'s K vector for one KV head: 128 bf16 values = 256 bytes.</td></tr>'
             '<tr><td>dim pair</td><td>Two neighbouring values of the row (dims 2k and 2k+1), 4 bytes; the AMX multiply consumes K in pairs, so the pair is the unit that moves. A row has 64 dim pairs.</td></tr>'
             '<tr><td>dim step</td><td>16 consecutive dim pairs (32 dims, 64 bytes of the row). A row has 4 dim steps, s0..s3.</td></tr>'
             '<tr><td>token block</td><td>16 consecutive tokens of a page (a page holds 64 tokens, so 4 blocks, c0..c3). Token i is column i % 16 of block i / 16.</td></tr>'
             '<tr><td>panel</td><td>The storage of one dim step of one token block: 16 rows (one per dim pair) x 16 columns (one per token) x 4 bytes = 16 lines of 64 bytes = 1 KiB. A panel is exactly one AMX tile, which is why the plane is laid out this way: the QK kernel loads a panel as its K operand with no transpose. One KV head\'s plane for a page is 4 x 4 = 16 panels.</td></tr>'
             '<tr><td>line</td><td>One 64-byte cache line = one row of a panel = one dim pair of 16 tokens. A store that writes a whole line at once is a full-line store; a store that writes 4 bytes of it is a partial-line write.</td></tr>'
             '<tr><td>register, lane</td><td>An AVX-512 register holds 64 bytes = 16 dim pairs; its 16 four-byte slots are its lanes. A masked store writes only the lanes whose mask bit is set.</td></tr>'
             '</table>')
    H.append(fig_row_to_plane())
    H.append(fig_block_store_steps())
    H.append(fig_partial_and_lone())
    H.append('<p>Checks. The unit test t/t_k_vnni_layout.cpp compares store_block against scatter_row bit for bit for every block and 38 present-masks (full, single lanes, halves, alternating, empty, random) and checks that absent tokens\' slots keep their poison; a standalone run of the same check on a delphi-3bda core passed 208 cases and measured, L1-resident, 169 cycles per 16 tokens for the block store against 681 for 16 scatters (a microbenchmark of the instruction cost only, not of the cold-line cost that dominates in the real store).</p>')
    H.append('<h4>3.1.2 The block store played step by step (separate page, added 2026-09-17)</h4>')
    H.append('<p>A separate page plays the block store of one token block, step by step, with mock values: <a href="block-store-animation.html">status/block-store-animation.html</a> (also published as an artifact: <a href="https://claude.ai/artifact/Mr7Vu2qJcA1uVdxP6kFiUh">claude.ai/artifact/Mr7Vu2qJcA1uVdxP6kFiUh</a>). It answers a reader\'s question about Figure 3.1a. The four dim steps of a K row are four consecutive 64-byte pieces of one contiguous 256-byte row, not four rows. Figure 3.1a stacked them only to fit the page width. Every cell on that page shows its two values, its dims, its token and its byte offsets. The 64 stores are numbered in their order on the plane: dim step s0 (panel lines 0-15) first, then s1, s2 and s3. An L1D and DRAM strip shows which lines are cold, fetched or dirty at each step, with the cache model stated apart from the measured facts. The positions come from running store_block itself on the mock rows [exec/block-store-animation/gt.cpp].</p>')
    H.append('<h3>3.2 (b) Striping: the idle main helpers share the store</h3>')
    H.append('<p>What it does. In the generated plugin the main helpers are idle while main runs save_k (figure 2.2). The code generator now emits, at the same statement position of the helpers\' schedule, a call to save_k_helper, and main\'s save_k receives the worker count. Main opens a window over the pass\'s token list, every thread claims 16-token blocks of it with an atomic counter and stores them, and main waits until every helper has left the window and every block is stored before it marks the tokens complete and releases the attention workers. Windows are counted on both sides, so a helper enters window N exactly when main opens window N; a pass with at most 16 tokens (decode) opens no window and nothing waits [ingest/src/TronCpp.hs runHelperStatement, submitAttentionOperation; h/tron/models/model.hpp Note [Striped K store], save_k_helper; h/tron/models/common.hpp batch::k_store_window]. Switch: <code>TRON_K_VNNI_STRIPE=0</code>. The handwritten plugins and the unit tests call save_k without a worker count and never stripe.</p>')
    H.append('<h4>3.2.1 The window, step by step</h4>')
    b_tp2 = tr("b", 2, "prefill", "save_k_us_per_layer") or 175
    v0_tp2 = tr("vnni0", 2, "prefill", "save_k_us_per_layer") or 858
    H.append(striping_svg(7, round(v0_tp2), round(b_tp2)))
    H.append('<p>Why it is safe for K and not for V. In the VNNI K plane a token owns 4 bytes of each line it touches and no other token writes those bytes, so threads storing different blocks never write the same bytes (a 16-token block owns whole lines). The V plane interleaves token pairs in one 32-bit lane, so two threads storing the two tokens of a pair would race; save_v stays serial [h/tron/kernels/k_vnni.hpp header comment; model.hpp save_v_impl comment].</p>')
    H.append('<p>Checks. The emitter test ingest/test/LoopyTronSpec.hs counts one save_k_helper call per KV-writing operation; the C++ unit tests (t_k_vnni_layout, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit) and the Haskell test suite run in the build phase below; the greedy smoke (section 5) must give identical tokens for vnni, vnni0, a, b and ab, because the store is data movement.</p>')

    # ---- section 4: results
    H.append('<h4>3.2.2 The window played claim by claim (separate page, added 2026-09-17)</h4>')
    H.append('<p>A separate page plays one window of the shared block save (the name the code gives this remedy at head) event by event: <a href="shared-save-animation.html">status/shared-save-animation.html</a> (also published as an artifact: <a href="https://claude.ai/artifact/9F8pqRrgZJjTbzQpFJg7eR">claude.ai/artifact/9F8pqRrgZJjTbzQpFJg7eR</a>). It lists the 64 work units of a prefill layer with their items, users, token positions, pages and blocks. It shows the counter values (opened, next_unit, finished, helper_windows) after every arrival, claim, unit completion and finished++. It draws the window as who-does-what-when lanes to scale and compares the simulated length with the measured Save K span (80 / 60 us for ab, 175 / 110 us for b). It also lays the k_store_window struct out on its cache lines with byte offsets, from a compiled replica of the struct [exec/shared-save-animation/window_layout.cpp]. The unit cut rule is reproduced in Python and checked against the unit test [exec/shared-save-animation/cut_units.py].</p>')
    H.append('<h2>4. Results: TTFT and TPS per arm (qwen3-4b, 8 users)</h2>')
    if not summary:
        H.append(pending(f"campaign cells (marker {marker}; {status})"))
    for tp in (2, 4):
        H.append(f'<h3>4.{1 if tp==2 else 2} tp{tp}</h3>')
        H.append(legend_html(ARMS))
        H.append(dot_rows(summary, tp, "ttft", f"TTFT (prefill s for 8 prompts), tp{tp}; lower is better", "s", ARMS, ("ab", "vnni0"), True))
        H.append(dot_rows(summary, tp, "tps", f"TPS per user (decode tokens/s), tp{tp}; higher is better", "tok/s", ARMS, ("ab", "vnni0"), False))
        H.append(delta_table(summary, tp))
        H.append(cells_table(summary, tp))
    H.append('<h3>4.3 The Save K span per arm (traces of the new arms, prompt 1024)</h3>')
    H.append(savek_bars(an1, an2, "prefill"))
    H.append(trace_table(an2, "prefill", ["vnni0", "a", "b", "ab"]) if an2 else pending("traces of the new arms (exec/results/vnnik2-trace-20260915)"))
    if an2:
        v0 = {tp: tr("vnni0", tp, "prefill", "save_k_us_per_layer") for tp in (2, 4)}
        H.append('<p>Reading. vnni0 reproduces Monday\'s binary ({:.0f} / {:.0f} us against {:.0f} / {:.0f} us at tp2 / tp4), so the new binary carries no drift. '
                 'The block store alone cuts the span to {:.0f} / {:.0f} us (the transposed full-line stores; 42-43 ns per row, still above the row-major store\'s 33 ns because a K row now lands in 4 panels 4 KiB apart instead of one contiguous 256-byte run). '
                 'Striping alone cuts it to {:.0f} / {:.0f} us: 4.9x with 7 helpers at tp2 and 7.9x with 8 helpers at tp4 (the ideal is 8x and 9x; the rest is the join and the helpers\' arrival). '
                 'Both together give {:.0f} / {:.0f} us: 3.4x / 4.7x shorter than the baseline\'s row-major store, 11x / 14x shorter than Monday\'s scatter. The decode span is unchanged in every arm (one token per user per step: no run to transpose, no window to share).</p>'.format(
                     v0[2], v0[4], sk[("vnni", 2)], sk[("vnni", 4)],
                     tr("a", 2, "prefill", "save_k_us_per_layer"), tr("a", 4, "prefill", "save_k_us_per_layer"),
                     tr("b", 2, "prefill", "save_k_us_per_layer"), tr("b", 4, "prefill", "save_k_us_per_layer"),
                     tr("ab", 2, "prefill", "save_k_us_per_layer"), tr("ab", 4, "prefill", "save_k_us_per_layer")))
    # ---- 4.4 confirmation round with the review-fixed commit
    summary3 = jload(f"{RES3}/summary.json")
    an3 = jload(f"{TRACE3}/analysis.json")
    smoke3 = read(f"{RES3}/smoke/smoke.txt")
    tests3 = read(f"{RES3}/tests.txt")
    H.append(f'<h3>4.4 Confirmation with the review-fixed commit {FIX_TIP}</h3>')
    H.append(f'<p>A 40-agent adversarial review of {NEW_TIP} confirmed 8 findings (none blocking); commit {FIX_TIP} answers them: the striped window hands out page-block work units instead of 16-item blocks (one writer per page block also when a user\'s chunk does not start at a multiple of 16 items), the join waits on one counter, the watchdog is time based, more than 128 workers turn striping off instead of aborting, a model-level test drives save_k alone and with two helper threads over runs that start mid-block, cross a block and a page boundary and contain jobs without KV work, and the emitter test checks the whole call text. The cells below repeat the prompt-1024 measurement with that commit (binary runtron.vnnik3).</p>')
    if summary3:
        for tp in (2, 4):
            H.append(legend_html(["base", "vnni0", "a", "b", "ab"]))
            H.append(dot_rows(summary3, tp, "ttft", f"TTFT (prefill s for 8 prompts), tp{tp}, commit {FIX_TIP}; lower is better", "s", ["base", "vnni0", "a", "b", "ab"], ("ab", "vnni0"), True))
            H.append(delta_table(summary3, tp))
            H.append(cells_table(summary3, tp))
    else:
        H.append(pending(f"confirmation cells ({read(EXEC + '/logs/vnnik2-confirm-20260915.status').strip() or 'not started'})"))
    if an3:
        H.append(trace_table(an3, "prefill", ["vnni0", "a", "b", "ab"]))
    H.append(f"<pre>{esc(tests3.strip()) if tests3 else 'pending: unit tests of ' + FIX_TIP}</pre>")
    cmp3 = [l for l in smoke3.splitlines() if " vs " in l or l.startswith("smoke token rows")]
    H.append(f"<pre>{esc(chr(10).join(cmp3)) if cmp3 else 'pending: smoke of ' + FIX_TIP}</pre>")

    # ---- section 5: smoke, build, tests
    H.append('<h2>5. Build, tests and the greedy-agreement smoke</h2>')
    H.append(f"<pre>{esc(build.strip()) if build else 'pending: build record'}</pre>")
    H.append(f"<pre>{esc(tests.strip()) if tests else 'pending: unit tests'}</pre>")
    cmp_lines = [l for l in smoke.splitlines() if " vs " in l or l.startswith("smoke token rows")]
    H.append(f"<pre>{esc(chr(10).join(cmp_lines)) if cmp_lines else 'pending: smoke comparison'}</pre>")
    H.append('<p>How to read it: ab vs ab2 is the A/A control (same binary, same recipe, run twice; must be identical). vnni vs vnni0 checks that the new binary with both remedies off reproduces Monday\'s binary. vnni0 vs a / b / ab must be identical for all 128 tokens: the remedies move the same bytes to the same places; a difference would be a defect.</p>')

    # ---- section 6: open items
    H.append('<h2>6. Open items</h2><ul>')
    H.append('<li>Decode store: the remedies do not touch it (one token per user per step: no 16-token run, no window). Measured at ' +
             (f"{dk[('vnni',2)]:.0f} / {dk[('vnni',4)]:.0f} us per layer (tp2 / tp4), {36*dk[('vnni',2)]/1000:.1f} ms of a {tr('vnni',2,'decode','pass_ms'):.1f} ms step, hidden behind the attention workers' Ready sections at prompt 1024 but present. " if dk[('vnni',2)] else "") +
             'Candidates: stripe the 8 decode tokens over the helpers one token each (a window with block size 1), or prefetch the 64 lines of the token\'s column; both unmeasured.</li>')
    H.append('<li>The remaining prefill span with both remedies (about 60-80 us per layer) is below the row-major store\'s 275 us; whether the residual is the block loop, the join, or the helpers\' arrival is not separated here (a per-block span would do it).</li>')
    H.append('<li>Model-level test of the striped window: the C++ unit tests exercise store_block and the grouping through the handwritten plugin path (n_workers 1), the emitter test counts the helper call, and the end-to-end greedy smoke checks the result; a fake-device test that drives save_k with n_workers greater than 1 does not exist yet.</li>')
    H.append('<li>Other plugins: every generated plugin with a KV-writing attention operation now emits the helper call; only qwen3-4b was run. The handwritten llama plugin keeps the serial store (n_workers 1) and gets the block store only.</li>')
    H.append('<li>Switch defaults: both remedies are on by default in the commit; the switches exist for this measurement and can be removed before a PR.</li>')
    H.append('</ul>')

    # ---- section 7: raw data
    H.append('<h2>7. Raw data for the reviewing agent</h2>')
    H.append('<table><tr><th>File</th><th>Content</th></tr>')
    for f, c in [("exec/results/vnnik-trace-20260914/{base,vnni}-tp{2,4}.perfetto-trace", "The four traces of section 2 (Perfetto protobuf, open with ui.perfetto.dev or the python TraceProcessor); *.log = the runtron output of each traced run; runs.txt = one header + the grepped lines per run."),
                 ("exec/results/vnnik-trace-20260914/analysis.json, analysis.md", "Output of exec/vnnik-trace-20260914/analyze.py: per trace and pass kind the Save K / Save V spans, shares, and the busy fractions of the worker classes during Save K; the docstring defines every column."),
                 ("exec/results/vnnik-trace-20260914/*.lanes.json", "Output of lanes.py: every span of one layer (pass 3, layer 10) and of one decode step on every thread, relative to the Save K start; the source of the lanes figures."),
                 ("exec/results/vnnik2-20260915/rt-results.txt, rt/", "The campaign's runtron runs: one header per run (arm, tp, prompt, binary, env, tip, machine line) and the grepped result lines; rt/ holds the complete output of every attempt."),
                 ("exec/results/vnnik2-20260915/summary.json, summary.md", "Output of exec/vnnik2-20260915/summarize.py: per cell mean and sd over repetitions, deltas per pair."),
                 ("exec/results/vnnik2-20260915/smoke/", "Greedy smoke: <arm>.tokens (one row of token ids), <arm>.log, smoke.txt with the comparison by compare_tokens.py."),
                 ("exec/results/vnnik2-20260915/build.txt, tests.txt, tests-*.out, cabal-test.out", "Build record (tip, cmake options, sha256 of the three binaries), unit test results, Haskell emitter test results."),
                 ("exec/results/vnnik2-trace-20260915/", "Traces of the new arms (vnni0, a, b, ab at tp2 and tp4) and their analysis.json."),
                 ("exec/vnnik2-20260915/campaign.sh, build.sh", "The campaign and the build script; their headers state every deliberate choice (arms, placement, guards)."),
                 ("VNNIed-K-in-place/tron-VNNIed-K", f"The branch worktree; commit {NEW_TIP} = the remedies.")]:
        H.append(f"<tr><td>{esc(f)}</td><td>{esc(c)}</td></tr>")
    H.append("</table>")
    H.append(f'<p>How to recompute: python3 exec/vnnik-trace-20260914/analyze.py; python3 exec/vnnik-trace-20260914/lanes.py TRACE 2 10; python3 exec/vnnik2-20260915/summarize.py exec/results/vnnik2-20260915; python3 exec/vnnik2-20260915/gen_report.py rewrites this page.</p>')
    H.append('</main></body></html>')
    page = "\n".join(H)
    bad = [c for c in set(page) if ord(c) > 126]
    assert not bad, f"non-ASCII characters in the page: {bad!r}"
    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
