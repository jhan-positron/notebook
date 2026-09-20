#!/usr/bin/env python3
"""Build 2026-08-12-07-3bda-pfgate-step0.html from the pfgate campaign outputs."""

import csv
import json
import statistics as st

BASE = "/home/jhan/workspace/perf-fluctuation/deep-dive-3bda"
ROOT = open(f"{BASE}/CURRENT_CAMPAIGN_PFGATE").read().strip()
OUT = f"{BASE}/2026-08-12-07-3bda-pfgate-step0.html"

# palette (dataviz reference instance, light mode)
C_BLUE = "#2a78d6"    # TX driver family
C_ORANGE = "#eb6834"  # listener / logits family
C_AQUA = "#1baf7a"    # coordinator prep family
C_VIOLET = "#4a3aa7"  # worker kernels family
C_GRAY = "#8a8984"    # RX loop
C_RED = "#e34948"     # stall annotation only
INK = "#0b0b0b"
INK2 = "#52514e"

FAM = {}
for n in ("legacy tx_launch", "tx submitting activation DMA request", "matmul enqueue",
          "Prepare hardware matmul job", "Launch hardware matmul job", "legacy hw_prepare"):
    FAM[n] = C_BLUE
for n in ("notify_listener", "fill_logits_buffer", "waiting_for_logits", "prepare streams",
          "setup_logits", "partition_listeners"):
    FAM[n] = C_ORANGE
for n in ("rx collecting results",):
    FAM[n] = C_GRAY

LANE_ORDER = ["24/?-work_queue", "25/0-worker", "3/0-TX-10", "4/0-TX-13", "5/0-TX-38",
              "6/0-TX-3b", "147/0-RX-10", "148/0-RX-13", "149/0-RX-38", "150/0-RX-3b"]
LANE_LABEL = {"24/?-work_queue": "work_queue (coordinator)", "25/0-worker": "pool worker 25 (logits job)",
              "3/0-TX-10": "TX card 10", "4/0-TX-13": "TX card 13", "5/0-TX-38": "TX card 38",
              "6/0-TX-3b": "TX card 3b", "147/0-RX-10": "RX card 10", "148/0-RX-13": "RX card 13",
              "149/0-RX-38": "RX card 38", "150/0-RX-3b": "RX card 3b"}


def fam_color(name, thr):
    if name in FAM:
        return FAM[name]
    if name.startswith("kernel_"):
        return C_VIOLET
    if "work_queue" in thr:
        return C_AQUA
    if "worker" in thr:
        return C_VIOLET
    return C_AQUA


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lanes_svg(lane_json, title, seg_marks, big_labels, scale=0.5):
    d = json.load(open(lane_json))
    ext = d["extent_us"]
    lx = 178                      # left gutter for lane labels
    w = lx + int(ext * scale) + 96
    pitch, rh, top = 27, 16, 66
    h = top + pitch * len(LANE_ORDER) + 56
    s = [f'<svg viewBox="0 0 {w} {h}" width="{w}" font-family="system-ui,sans-serif">']
    s.append(f'<text x="{lx}" y="16" font-size="13" font-weight="700" fill="{INK}">{esc(title)}</text>')
    # axis
    ay = top - 12
    s.append(f'<line x1="{lx}" y1="{ay}" x2="{lx + ext*scale:.0f}" y2="{ay}" stroke="#c9c8c2" stroke-width="1"/>')
    t = 0
    while t <= ext:
        x = lx + t * scale
        s.append(f'<line x1="{x:.0f}" y1="{ay-3}" x2="{x:.0f}" y2="{ay+3}" stroke="#c9c8c2"/>')
        s.append(f'<text x="{x:.0f}" y="{ay-7}" font-size="10" fill="{INK2}" text-anchor="middle">{t}</text>')
        t += 200
    s.append(f'<text x="{lx + ext*scale + 8:.0f}" y="{ay+4}" font-size="10" fill="{INK2}">&#181;s</text>')
    # segment braces A1'/B'/C'
    segy = top - 2
    for (a, b, name) in seg_marks:
        xa, xb = lx + a * scale, lx + b * scale
        s.append(f'<line x1="{xa:.0f}" y1="{segy}" x2="{xb:.0f}" y2="{segy}" stroke="{INK2}" stroke-width="1"/>')
        s.append(f'<line x1="{xa:.0f}" y1="{segy-3}" x2="{xa:.0f}" y2="{segy+3}" stroke="{INK2}"/>')
        s.append(f'<line x1="{xb:.0f}" y1="{segy-3}" x2="{xb:.0f}" y2="{segy+3}" stroke="{INK2}"/>')
        s.append(f'<text x="{(xa+xb)/2:.0f}" y="{segy+11}" font-size="10" fill="{INK2}" text-anchor="middle">{esc(name)}</text>')

    # all-idle regions (no span of any kind open anywhere): red hatched
    ivs = []
    for thr, spans in d["lanes"].items():
        for sp in spans:
            if sp["kind"] == "instant":
                continue
            ivs.append((sp["off_us"], sp["off_us"] + sp["dur_us"]))
    ivs.sort()
    merged = []
    for a, b in ivs:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    y0, y1 = top + 8, top + pitch * len(LANE_ORDER)
    for i in range(len(merged) - 1):
        g0, g1 = merged[i][1], merged[i + 1][0]
        if g1 - g0 < 40:  # only draw notable gaps
            continue
        xa, xb = lx + g0 * scale, lx + g1 * scale
        s.append(f'<rect x="{xa:.0f}" y="{y0}" width="{xb-xa:.0f}" height="{y1-y0}" fill="{C_RED}" fill-opacity="0.13"/>')
        s.append(f'<text x="{(xa+xb)/2:.0f}" y="{y0-4}" font-size="10" font-weight="700" fill="{C_RED}" text-anchor="middle">{g1-g0:.0f}&#181;s idle</text>')

    # lanes
    for li, lane in enumerate(LANE_ORDER):
        y = top + 8 + li * pitch
        s.append(f'<text x="{lx-8}" y="{y+12}" font-size="11" fill="{INK}" text-anchor="end">{esc(LANE_LABEL[lane])}</text>')
        s.append(f'<line x1="{lx}" y1="{y+rh+3}" x2="{lx+ext*scale:.0f}" y2="{y+rh+3}" stroke="#eeede8" stroke-width="1"/>')
        for sp in d["lanes"].get(lane, []):
            x = lx + sp["off_us"] * scale
            wd = max(sp["dur_us"] * scale, 1.2)
            c = fam_color(sp["name"], lane)
            if sp["kind"] == "instant":
                s.append(f'<path d="M {x:.1f} {y-2} l 3.5 -6 l -7 0 z" fill="{C_BLUE}"><title>data ready @{sp["off_us"]}&#181;s</title></path>')
            elif sp["kind"] == "wait":
                s.append(f'<rect x="{x:.1f}" y="{y}" width="{wd:.1f}" height="{rh}" rx="2" fill="{c}" fill-opacity="0.22" stroke="{c}" stroke-width="1" stroke-dasharray="4 3"><title>{esc(sp["name"])} @{sp["off_us"]}+{sp["dur_us"]}&#181;s (wait)</title></rect>')
            else:
                s.append(f'<rect x="{x:.1f}" y="{y}" width="{wd:.1f}" height="{rh}" rx="2" fill="{c}" fill-opacity="0.85"><title>{esc(sp["name"])} @{sp["off_us"]}+{sp["dur_us"]}&#181;s</title></rect>')
    # big labels: (off_us, lane_index, text, color)
    for (off, li, text, col) in big_labels:
        x = lx + off * scale
        y = top + 8 + li * pitch
        s.append(f'<text x="{x:.0f}" y="{y-3}" font-size="10.5" font-weight="700" fill="{col}">{esc(text)}</text>')
    s.append('</svg>')
    return "\n".join(s)


def hist_svg():
    out = ['<svg viewBox="0 0 980 240" width="980" font-family="system-ui,sans-serif">']
    for pi, (d, tag, col) in enumerate((("draw_18", "fastest draw 18 — 185.3 tok/s", C_BLUE),
                                        ("draw_11", "slowest draw 11 — 170.5 tok/s", C_BLUE))):
        rows = list(csv.DictReader(open(f"{BASE}/analysis/out/{d}/{d}.gaps.csv")))
        spans = [float(r["span_us"]) for r in rows]
        bins = [0] * 16
        for v in spans:
            bins[min(15, int(v // 200))] += 1
        n = len(spans)
        x0 = 60 + pi * 490
        out.append(f'<text x="{x0}" y="18" font-size="12.5" font-weight="700" fill="{INK}">{tag}</text>')
        peak = max(bins) / n
        for i, b in enumerate(bins):
            frac = b / n
            bh = 0 if frac == 0 else max(frac / peak * 150, 1.5)
            x = x0 + i * 26
            out.append(f'<rect x="{x}" y="{190-bh:.1f}" width="22" height="{bh:.1f}" rx="3" fill="{col}" fill-opacity="0.85"><title>{i*200}-{(i+1)*200}&#181;s: {b} windows ({100*frac:.1f}%)</title></rect>')
            if frac == peak or (frac > 0.1 and i > 4):
                out.append(f'<text x="{x+11}" y="{184-bh:.0f}" font-size="10" fill="{INK2}" text-anchor="middle">{100*frac:.0f}%</text>')
        for i in range(0, 17, 4):
            out.append(f'<text x="{x0+i*26}" y="206" font-size="10" fill="{INK2}" text-anchor="middle">{i*200}</text>')
        out.append(f'<text x="{x0+210}" y="224" font-size="10.5" fill="{INK2}" text-anchor="middle">inter-fwd-pass window duration (&#181;s), 200&#181;s bins, % of windows</text>')
    out.append('</svg>')
    return "\n".join(out)


def dumbbell_svg(rows):
    # rows: (label, fast, slow, corr)
    W, lx, rx = 980, 300, 60
    xmax = 1300.0
    ph = 34
    H = 60 + ph * len(rows) + 30
    sc = (W - lx - rx) / xmax
    s = [f'<svg viewBox="0 0 {W} {H}" width="{W}" font-family="system-ui,sans-serif">']
    for t in range(0, 1400, 200):
        x = lx + t * sc
        s.append(f'<line x1="{x:.0f}" y1="40" x2="{x:.0f}" y2="{H-34}" stroke="#eeede8"/>')
        s.append(f'<text x="{x:.0f}" y="30" font-size="10" fill="{INK2}" text-anchor="middle">{t}</text>')
    s.append(f'<text x="{lx + 1300*sc + 6:.0f}" y="30" font-size="10" fill="{INK2}">&#181;s/step</text>')
    LIGHT, DARK = "#93bbe8", "#1e5da8"
    for i, (label, f, sl, corr) in enumerate(rows):
        y = 60 + i * ph
        xf, xs = lx + f * sc, lx + sl * sc
        s.append(f'<text x="{lx-10}" y="{y+4}" font-size="11.5" fill="{INK}" text-anchor="end">{esc(label)}</text>')
        s.append(f'<line x1="{xf:.0f}" y1="{y}" x2="{xs:.0f}" y2="{y}" stroke="#b9b8b2" stroke-width="2"/>')
        s.append(f'<circle cx="{xf:.0f}" cy="{y}" r="6" fill="{LIGHT}" stroke="#fff" stroke-width="1.5"/>')
        s.append(f'<circle cx="{xs:.0f}" cy="{y}" r="6" fill="{DARK}" stroke="#fff" stroke-width="1.5"/>')
        s.append(f'<text x="{xf:.0f}" y="{y-11}" font-size="10.5" fill="{INK2}" text-anchor="middle">{f:.0f}</text>')
        s.append(f'<text x="{xs:.0f}" y="{y-11}" font-size="10.5" fill="{INK2}" text-anchor="middle">{sl:.0f}</text>')
        s.append(f'<text x="{max(xf,xs)+14:.0f}" y="{y+4}" font-size="10.5" font-weight="700" fill="{C_RED}">+{sl-f:.0f}</text>')
        s.append(f'<text x="{W-4}" y="{y+4}" font-size="10.5" fill="{INK2}" text-anchor="end">corr {corr}</text>')
    y = 60 + len(rows) * ph
    s.append(f'<circle cx="{lx}" cy="{y}" r="6" fill="{LIGHT}" stroke="#fff" stroke-width="1.5"/><text x="{lx+10}" y="{y+4}" font-size="11" fill="{INK2}">fast4 mean</text>')
    s.append(f'<circle cx="{lx+110}" cy="{y}" r="6" fill="{DARK}" stroke="#fff" stroke-width="1.5"/><text x="{lx+120}" y="{y+4}" font-size="11" fill="{INK2}">slow4 mean</text>')
    s.append('</svg>')
    return "\n".join(s)


def mixture_table():
    # pooled fast4/slow4 window-mode profile
    pool = {"fast4": ["draw_10", "draw_12", "draw_20", "draw_18"],
            "slow4": ["draw_11", "draw_16", "draw_09", "draw_13"]}
    keys = ["us:compute_forward_args", "us:fill_logits_buffer", "us:construct_minibatches",
            "us:Prepare hardware matmul job", "us:legacy tx_launch", "us:notify_listener"]
    res = {}
    for cls, ds in pool.items():
        fastw, stallw, tot = [], [], 0
        for d in ds:
            for r in csv.DictReader(open(f"{BASE}/analysis/out/{d}/{d}.windows.csv")):
                tot += 1
                v = float(r["dur_us"])
                (fastw if v < 800 else stallw if v > 1500 else []).append(r)
        res[cls] = (fastw, stallw, tot)
    def med(rows, k):
        return st.median(float(r[k]) for r in rows)
    lines = ["<table><thead><tr><th>span (median &#181;s per window)</th>"
             "<th>fast4 draws:<br>quick windows</th><th>fast4:<br>stalled windows</th>"
             "<th>slow4 draws:<br>quick windows</th><th>slow4:<br>stalled windows</th></tr></thead><tbody>"]
    for k in keys:
        f_f, f_s = med(res['fast4'][0], k), med(res['fast4'][1], k)
        s_f, s_s = med(res['slow4'][0], k), med(res['slow4'][1], k)
        lines.append(f"<tr><td>{esc(k[3:])}</td><td>{f_f:.0f}</td><td>{f_s:.0f}</td><td>{s_f:.0f}</td><td>{s_s:.0f}</td></tr>")
    fa, sa = res["fast4"], res["slow4"]
    lines.append(f"<tr class='hl'><td>share of windows in each mode</td>"
                 f"<td>{100*len(fa[0])/fa[2]:.0f}%</td><td>{100*len(fa[1])/fa[2]:.0f}%</td>"
                 f"<td>{100*len(sa[0])/sa[2]:.0f}%</td><td>{100*len(sa[1])/sa[2]:.0f}%</td></tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines), res


def per_draw_table():
    tps = {r["draw"]: float(r["generate_tok_s"]) for r in csv.DictReader(open(f"{ROOT}/results.csv")) if r["status"] == "ok"}
    lines = ["<table><thead><tr><th>draw</th><th>decode tok/s</th><th>windows</th>"
             "<th>window mean &#181;s</th><th>median</th><th>p90</th><th>% windows &gt; 1500 &#181;s</th></tr></thead><tbody>"]
    for d in sorted(tps, key=lambda x: -tps[x]):
        rows = list(csv.DictReader(open(f"{BASE}/analysis/out/{d}/{d}.gaps.csv")))
        spans = sorted(float(r["span_us"]) for r in rows)
        stall = 100 * sum(1 for v in spans if v > 1500) / len(spans)
        lines.append(f"<tr><td>{d}</td><td>{tps[d]:.2f}</td><td>{len(spans)}</td>"
                     f"<td>{st.mean(spans):.0f}</td><td>{spans[len(spans)//2]:.0f}</td>"
                     f"<td>{spans[int(0.9*len(spans))]:.0f}</td><td>{stall:.1f}%</td></tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


attr = json.load(open(f"{BASE}/analysis/out/attribution.json"))
agg = json.load(open(f"{BASE}/analysis/out/aggregate.json"))

fast_lanes = lanes_svg(
    f"{BASE}/analysis/out/lane-fast-d18w2557.json",
    "FAST window — draw_18 (185.3 tok/s, fastest), window 2557 of 3830: 560 µs, 240 slices",
    [(0, 119, "A1′ 119"), (119, 423, "B′ 304"), (423, 560, "C′ 137")],
    [(120, 1, "fill_logits_buffer 293µs", C_ORANGE),
     (123, 0, "waiting_for_logits 179µs", C_ORANGE),
     (447, 0, "compute_forward_args 43µs", C_AQUA)])
slow_lanes = lanes_svg(
    f"{BASE}/analysis/out/lane-slow-d11w2524.json",
    "SLOW window — draw_11 (170.5 tok/s), window 2524 of 3746: 1930 µs, 240 slices — same structure, every station stretched",
    [(0, 362, "A1′ 362"), (362, 1029, "B′ 667"), (1029, 1930, "C′ 901")],
    [(362, 1, "fill_logits_buffer 667µs (×2.2)", C_ORANGE),
     (365, 0, "waiting_for_logits 199µs (flat)", C_ORANGE),
     (1289, 0, "compute_forward_args 186µs (quick-window median 35µs)", C_RED),
     (109, 2, "wcls chunk pause ≈200µs →", C_RED)])

mix_html, mix_res = mixture_table()
hist = hist_svg()
dumb = dumbbell_svg([
    ("inter-fwd-pass window (total)", 804.9, 1206.6, "−0.956"),
    ("A1′ window start → listener job start", 236.1, 383.0, "−0.761"),
    ("B′ listener job (stream wait + consume)", 385.5, 567.9, "−0.858"),
    ("C′ listener end → next step first dispatch", 184.5, 258.6, "−0.769"),
    ("host work spans (union coverage)", 296.6, 459.1, "−0.845"),
    ("wait spans (union coverage)", 438.3, 628.0, "−0.844"),
    ("all-idle (no span on any thread)", 70.0, 119.4, "−0.776"),
])
pdraw = per_draw_table()

span_rows = []
for k, v in agg["spans"].items():
    if k in ("forward args", "other"):
        continue
    span_rows.append((k, v["fast4_us"], v["slow4_us"], v["delta_us"], v["corr_vs_tps"]))
span_rows.sort(key=lambda r: -abs(r[3]))
span_tbl = ["<table><thead><tr><th>span (mean &#181;s per window, per draw)</th><th>fast4</th><th>slow4</th><th>&#916;</th><th>corr vs TPS</th></tr></thead><tbody>"]
for k, f, s, dl, c in span_rows:
    hl = " class='hl'" if abs(dl) > 100 else ""
    span_tbl.append(f"<tr{hl}><td>{esc(k)}</td><td>{f}</td><td>{s}</td><td>{dl:+.1f}</td><td>{c}</td></tr>")
span_tbl.append("</tbody></table>")
span_tbl = "\n".join(span_tbl)

l1 = attr["level1"]
l2 = attr["level2"]

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3bda pfgate step 0 — perfetto-gated inter-fwd-pass capture</title>
<style>
 body {{ background:#fcfcfb; color:{INK}; font-family: system-ui, -apple-system, sans-serif;
        margin: 24px auto; max-width: 1160px; padding: 0 20px; line-height:1.45; }}
 h1 {{ font-size: 22px; margin-bottom:2px }} h2 {{ font-size:17px; margin-top:34px; border-bottom:1px solid #e4e3dd; padding-bottom:4px }}
 .sub {{ color:{INK2}; font-size:13px; }}
 table {{ border-collapse: collapse; font-size: 13px; margin: 10px 0; }}
 th, td {{ border: 1px solid #e4e3dd; padding: 4px 10px; text-align: right; }}
 th {{ background:#f4f3ee; font-weight:600 }} td:first-child, th:first-child {{ text-align:left }}
 tr.hl td {{ background:#fdf6ec; font-weight:600 }}
 .figwrap {{ overflow-x:auto; border:1px solid #eeede8; border-radius:8px; padding:12px; margin:12px 0; background:#fff }}
 .take {{ font-size:13.5px; color:{INK}; background:#f4f8f4; border-left:4px solid {C_AQUA}; padding:8px 12px; margin:8px 0 }}
 .warn {{ background:#fffbe8; border:1px solid #eedfa0; border-radius:8px; padding:10px 14px; margin:10px 0; font-size:13.5px }}
 .warn b {{ color:#8a6d00 }}
 .cap {{ font-size:12px; color:{INK2}; margin-top:4px }}
 .glos td {{ text-align:left; font-size:12.5px }}
 code {{ background:#f4f3ee; padding:1px 4px; border-radius:4px; font-size:12px }}
 .legend span {{ display:inline-block; margin-right:18px; font-size:12px; color:{INK2} }}
 .swatch {{ display:inline-block; width:14px; height:10px; border-radius:2px; margin-right:4px; vertical-align:baseline }}
</style></head><body>

<h1>Where the per-launch decode loss lives: a thread-complete view of the inter-fwd-pass window</h1>
<div class="sub">perf-fluctuation deep dive &#183; delphi-3bda &#183; drill-down series, gated-perfetto step 0 &#183; 2026-08-12 12:03&#8211;12:28 UTC campaign
(<code>pfgate-tp4-20260812T120255Z</code>, 20/20 draws ok + smoke)</div>

<h2>What was measured</h2>
<p>Every tron trace event was put behind a runtime gate that is open <b>only inside the inter-fwd-pass window during decode</b>:
it opens when the last layer&#8217;s attention finishes (layer 35 barrier) and closes when the next step&#8217;s first attention
job starts (layer 0 entry). One capture therefore contains ~3700&#8211;3890 dense event clusters (&#8220;windows&#8221;, one per generated
token that fits the 25&#8201;s capture) separated by silent forward passes, on <b>all threads</b>: the work_queue coordinator,
the pool worker that runs the logits job, and the TX/RX driver threads of all four cards. Mike&#8217;s
<code>&#8220;data ready&#8221;</code> instant marker (activations ready at each hardware launch, on the TX thread) rides inside the window.</p>
<div class="take"><b>Numerics unchanged, workload unperturbed:</b> all 21 runs (smoke + 20 draws) produced bit-identical token
sequences (sha256 <code>66af1d58&#8230;93c4</code>, the qwen-tp4 reference), decode TPS stayed in the bare band
(170.5&#8211;185.3, campaign CV 2.60%, worst-vs-best gap 8.0% &#8212; the launch lottery rolled normally).</div>

<h2>Headline: the whole difference is one window per token, and slow launches simply stall it more often</h2>
<table>
<thead><tr><th>LEVEL 1 &#8212; whole decode step (from TPS)</th><th>fast4 &#181;s</th><th>slow4 &#181;s</th><th>&#916; &#181;s</th><th>share of &#916;T</th><th>corr vs TPS</th></tr></thead>
<tbody>
<tr><td>whole step (1e6 / TPS)</td><td>{l1['step_us']['fast4']}</td><td>{l1['step_us']['slow4']}</td><td>+{l1['step_us']['delta']}</td><td>100%</td><td>&#8212;</td></tr>
<tr class="hl"><td>inter-fwd-pass window (measured, mean over ~3800 windows/draw)</td><td>{l1['window_us']['fast4']}</td><td>{l1['window_us']['slow4']}</td><td>+{l1['window_us']['delta']}</td><td>{l1['window_us']['share_of_dT_pct']}%</td><td>{l1['corr_window_vs_tps']}</td></tr>
<tr><td>forward pass remainder (derived: step &#8722; window)</td><td>{l1['remainder_derived_us']['fast4']}</td><td>{l1['remainder_derived_us']['slow4']}</td><td>+{l1['remainder_derived_us']['delta']}</td><td>{l1['remainder_derived_us']['share_of_dT_pct']}%</td><td>&#8212;</td></tr>
</tbody></table>
<p class="cap">fast4 / slow4 = means over the 4 fastest (draws 18, 20, 12, 10) / 4 slowest (draws 11, 16, 09, 13) of the 20 draws.
corr = Pearson correlation coefficient between the per-draw mean and that draw&#8217;s decode TPS, computed across all 20 draws;
&#8722;1 means &#8220;longer exactly when the launch is slower&#8221;, 0 means no relationship. The remainder row is derived, so its share
is the complement by construction; the honest reconciliation figure is the measured window&#8217;s 96.7%.</p>

<table>
<thead><tr><th>LEVEL 2 &#8212; inside the window (union coverage across all threads)</th><th>fast4 &#181;s</th><th>slow4 &#181;s</th><th>&#916; &#181;s</th><th>share of level 1</th><th>corr vs TPS</th></tr></thead>
<tbody>
<tr><td>named host <b>work</b> spans (coordinator prep, kernels, driver dispatch)</td><td>{l2['host work spans (union)']['fast4_us']}</td><td>{l2['host work spans (union)']['slow4_us']}</td><td>+{l2['host work spans (union)']['delta_us']}</td><td>{l2['host work spans (union)']['share_of_level1_pct']}%</td><td>{l2['host work spans (union)']['corr_vs_tps']}</td></tr>
<tr class="hl"><td>named <b>wait</b> spans (logits stream wait/consume, act-ready waits, RX loops)</td><td>{l2['wait spans (union, incl. B fill/stream)']['fast4_us']}</td><td>{l2['wait spans (union, incl. B fill/stream)']['slow4_us']}</td><td>+{l2['wait spans (union, incl. B fill/stream)']['delta_us']}</td><td>{l2['wait spans (union, incl. B fill/stream)']['share_of_level1_pct']}%</td><td>{l2['wait spans (union, incl. B fill/stream)']['corr_vs_tps']}</td></tr>
<tr><td><b>all-idle</b>: no span open on any thread</td><td>{l2['all-idle (no span on any thread)']['fast4_us']}</td><td>{l2['all-idle (no span on any thread)']['slow4_us']}</td><td>+{l2['all-idle (no span on any thread)']['delta_us']}</td><td>{l2['all-idle (no span on any thread)']['share_of_level1_pct']}%</td><td>{l2['all-idle (no span on any thread)']['corr_vs_tps']}</td></tr>
<tr><td>residual (children vs window total)</td><td colspan="2"></td><td>{attr['level2_residual_us']}</td><td>0.0%</td><td>&#8212;</td></tr>
</tbody></table>

<h2>The two windows, thread by thread, to scale</h2>
<div class="legend">
<span><span class="swatch" style="background:{C_AQUA}"></span>coordinator prep (work_queue)</span>
<span><span class="swatch" style="background:{C_ORANGE}"></span>logits listener job</span>
<span><span class="swatch" style="background:{C_VIOLET}"></span>worker kernels (layer-35 tail + lm-head norm)</span>
<span><span class="swatch" style="background:{C_BLUE}"></span>TX driver (dispatch)</span>
<span><span class="swatch" style="background:{C_GRAY}"></span>RX loop</span>
<span>&#9650; data ready instant</span>
<span>solid = working &#183; dashed = waiting (even if spinning) &#183; <b style="color:{C_RED}">red = all-idle region / stall callout</b></span>
</div>
<div class="figwrap">{fast_lanes}</div>
<div class="figwrap">{slow_lanes}</div>
<p class="cap">Durations to scale (0.5&#8201;px/&#181;s, identical scale in both figures); both windows contain the same ~240 slices.
Simplifications: RX &#8220;collecting results&#8221; loop spans persist across the whole step and are truncated at the window edge;
spans whose end event fell outside the gate are drawn to their last visible point; the two idle stretches shown in red are
where <b>no</b> tron thread had any span open. A1&#8242; = window start &#8594; listener job start; B&#8242; = listener job
(logits stream wait + consume + callback); C&#8242; = listener end &#8594; next step&#8217;s first dispatch.</p>
<div class="take">Reading the slow window left to right: the lm-head (wcls) dispatch burst itself pauses ~200&#181;s between
chunk completions (card-side); the logits stream wait/consume doubles to 667&#181;s; after the callback there is a 239&#181;s
stretch where <i>nothing</i> runs; then the next-step preparation executes <b>&#215;3&#8211;5 slower than the same code in quick
windows</b> (compute_forward_args 43&#8594;186&#181;s in the two windows shown; pooled medians 35&#8594;117&#181;s) with another idle stretch before the first dispatch. Every station
stretches together &#8212; including pure host compute that never touches the cards.</div>

<h2>Windows are two populations; the lottery sets the mixture</h2>
<div class="figwrap">{hist}</div>
<p class="cap">Per-window duration distributions, fastest vs slowest draw. The fast draw concentrates 58% of windows in the
400&#8211;600&#181;s mode; in the slow draw that mode keeps only 16% and the mass moves into a broad stalled population.</p>
{mix_html}
<p class="cap">Medians per window mode, pooled over fast4 / slow4 draws. &#8220;Quick&#8221; = window &lt; 800&#181;s,
&#8220;stalled&#8221; = &gt; 1500&#181;s (middle windows omitted). Read: a stalled window in a <i>fast</i> launch looks the same as
a stalled window in a <i>slow</i> launch &#8212; the launch changes only how often they happen.</p>

<h2>Per-segment record (dumbbell) and full span table</h2>
<div class="figwrap">{dumb}</div>
<p class="cap">Union coverages overlap across threads, so work + wait + idle sums to the window total; A1&#8242;+B&#8242;+C&#8242;
partitions the same total by pipeline position.</p>
{span_tbl}
<p class="cap">Mean total &#181;s per window of each named span, per draw, then averaged over fast4/slow4. Spans with dropped
end events repaired where possible (fill_logits_buffer &#8776; notify_listener &#8722; 12&#181;s in the ~11% of windows where the
fill end fell outside the gate). <code>legacy tx_launch</code> sums over 4 TX threads and includes activation-ready waits;
<code>rx collecting results</code> is the flat capped RX loop.</p>

<h2>Cross-validation against the TSC-probe view (kvprobe7)</h2>
<table>
<thead><tr><th>segment</th><th colspan="3">this capture (perfetto, 20 draws)</th><th colspan="3">kvprobe7 (TSC stamps, 16 draws)</th></tr></thead>
<tbody>
<tr><th></th><th>fast4 &#181;s</th><th>slow4 &#181;s</th><th>corr</th><th>fast4 &#181;s</th><th>slow4 &#181;s</th><th>corr</th></tr>
<tr><td>A1&#8242; window start &#8594; listener job start (kvprobe7 A1)</td><td>236</td><td>383</td><td>&#8722;0.76</td><td>184</td><td>252</td><td>&#8722;0.61</td></tr>
<tr class="hl"><td>B&#8242; listener job: stream wait + consume (+ callback) (kvprobe7 B + C.cb)</td><td>386</td><td>568</td><td>&#8722;0.86</td><td>358</td><td>484</td><td>&#8722;0.79</td></tr>
<tr><td>C&#8242; listener end &#8594; next step first dispatch (kvprobe7 C.rest)</td><td>185</td><td>259</td><td>&#8722;0.77</td><td>156</td><td>195</td><td>&#8722;0.69</td></tr>
</tbody></table>
<p><b>Agreements.</b> Same ordering (B largest, A1 second, C third), same signs, comparable magnitudes (kvprobe7 cycles
converted at 2.7&#8201;GHz), and the same heavy-tail texture (fastest draw: A1&#8242; median 121 / p90 594; slowest: B&#8242;
median 672 / p90 908, C&#8242; median 144 / p90 700). <b>Disagreements to note.</b> (1) This capture attributes
<b>96.7%</b> of the step difference to the inter-fwd-pass window vs kvprobe7&#8217;s 68.3% &#8212; the perfetto window additionally
contains the layer-35 post-attention MLP and the full dispatch tail, the campaigns&#8217; spreads differ, and the TSC accounting
carried a 10.1% reconciliation residual; the derived forward-pass remainder here is flat (+13.6&#181;s), so the earlier
&#8220;in-attention +17%&#8221; share does not replicate in this view. (2) Absolute segment values run larger here for the same
reason (wider window edges). The new information perfetto adds: the co-stretch of <i>pure host compute</i> inside stalled
windows, and the small true all-idle share (12.3%).</p>

<h2>Measured answers to the runbook&#8217;s &#167;5.4 question</h2>
<p><i>&#8220;In slow windows, where does the wall time between the wcls dispatch and data-ready / fill completion sit &#8212;
in a named span on some thread (which?), or in unattributed gaps?&#8221;</i></p>
<ul>
<li><b>Mostly in named spans, split between waiting and slowed-down work.</b> Of the +402&#181;s/step fast4&#8594;slow4 window
growth: 47.2% named wait spans (the logits stream wait inside <code>fill_logits_buffer</code> is the single largest,
+181&#181;s, corr &#8722;0.86; TX <code>act_ready</code>/slot waits +381&#181;s summed over 4 TX threads), 40.4% named host
<b>work</b> spans that simply run slower (e.g. <code>compute_forward_args</code>, host-only, &#215;3.3&#8211;4.7 in stalled
windows; <code>construct_minibatches</code> &#215;12), and only 12.3% true all-idle.</li>
<li><b>The lm-head input chain also stretches:</b> window start &#8594; last wcls <code>data ready</code> goes 247&#8594;396&#181;s
(corr &#8722;0.77), with visible ~200&#181;s pauses between chunk completions in stalled windows (card/DMA side of the stream).</li>
<li><b>The stall is a window-wide state, not one component:</b> every station (card stream, TX waits, host prep) stretches
together in a stalled window while <code>waiting_for_logits</code> stays fixed (~185&#8594;194&#181;s, corr &#8722;0.27) and whole-package
core frequency is flat across draws (turbostat Bzy_MHz 3751&#8211;3778, 5&#8201;s cadence &#8212; too coarse for per-window transients).</li>
<li><b>All-idle gaps concentrate at two seams:</b> after the listener callback ends (before the coordinator&#8217;s next
get_work) and between attention-plan assembly and the first hardware dispatch of the next step.</li>
</ul>

<h2>Per-draw record</h2>
{pdraw}
<p class="cap">Windows below 4096 because the 25&#8201;s capture clips the decode tail (trace spans 20.5&#8211;22.2&#8201;s of decode);
window counts match the per-trace <code>forward</code> slice counts, so no windows were missed by the gate mid-run.</p>

<h2>Next collection targets</h2>
<div class="warn"><b>1 &#183; Per-window CPU-speed transient (prime suspect for the co-stretch).</b> Pure host compute runs
&#215;3&#8211;5 slower inside stalled windows while 5&#8201;s turbostat shows nothing. Stamp aperf/mperf (or cycles + ref-cycles)
around the window on the coordinator and listener threads to test &#8220;cores ramp down during the near-idle inter-fwd-pass
and wake slowly &#8212; more often in slow launches&#8221;.</div>
<div class="warn"><b>2 &#183; Stall inter-arrival forensics (cheap, data already on disk).</b> Within each draw, test whether
stalled windows are periodic (external poller?), bursty, or memoryless; compare the rate constant against the launch TPS.
Every per-window duration for all 20 draws is already in <code>analysis/out/draw_*/draw_*.gaps.csv</code>.</div>
<div class="warn"><b>3 &#183; Card-side chunk pauses.</b> The wcls burst shows ~200&#181;s pauses between chunk completions in
stalled windows. Scope the existing per-block stream-arrival stamp idea (step-4 target from the TSC series) to stalled
windows only, or pull card telemetry for the same windows.</div>
<div class="warn"><b>4 &#183; Chunk-size A/B under wall-clock.</b> The harness&#8217;s TRON_MAX_LOGITS_CHUNK_SIZE arm is present
but was disabled this run; re-enable on alternating draws to test whether smaller logits chunks shrink B&#8242; in stalled windows.</div>
<div class="warn"><b>5 &#183; Replicate the mixture finding on delphi-3c51</b> (Bill&#8217;s machine, same shared /scratch
tooling): does its narrower spread (CV 0.85%) come with a lower stalled-window rate, same stall profile?</div>

<h2>Glossary and traceability</h2>
<table class="glos">
<tr><td><b>inter-fwd-pass window</b></td><td>the once-per-token end-of-step path: last layer&#8217;s attention ends &#8594; lm-head (wcls) matmul &#8594; streamed logits consumed &#8594; token picked &#8594; next step&#8217;s first dispatch. &#8220;Window&#8221; on this page always means one such occurrence, recovered as a dense cluster of trace events separated by &gt;1.5&#8201;ms silences.</td></tr>
<tr><td><b>draw / launch lottery</b></td><td>one benchmark process start; the same binary and input lands at a per-launch decode speed that persists for the whole run.</td></tr>
<tr><td><b>wcls / lm-head</b></td><td>the final vocabulary-projection matmul (151k vocabulary) whose streamed output are the logits.</td></tr>
<tr><td><b>gate</b></td><td>an atomic flag checked inside tron&#8217;s perfetto emission macros; trace events are dropped at the source while it is closed. Open/close sites: layer-35 attention barrier / layer-0 attention entry (decode batches only), defensive close on parse batches.</td></tr>
<tr><td><b>corr</b></td><td>Pearson correlation coefficient of a per-draw quantity vs the draw&#8217;s decode TPS across the 20 draws; &#8722;1 = longer exactly when slower.</td></tr>
<tr><td><b>span / instant</b></td><td>a named begin/end interval (span) or single timestamped marker (instant) emitted by tron&#8217;s TRACE_EVENT macros on the thread that executes it.</td></tr>
</table>
<p class="cap">
Campaign: <code>/scratch/jhan/perf-fluctuation/pfgate-3bda/pfgate-tp4-20260812T120255Z</code> (per-draw command, environment,
bitfile, power.tsv captured by the harness) &#183; binary <code>install-pfgate/bin/runtron</code>
sha256 <code>0200e818&#8230;9148</code> = trunk 12804a812 + 34-line window-gate patch (worktree <code>tron-pfgate</code> on alpha)
&#183; model ingested-qwen-3-4b-instruct-2507-tp4, USE_HW_ATTN=0, seed 2954953865, prompt 1024 / gen 4096 / ssp 256,
-u 1 -i 1 --slice-of 2 --slice-start 0 (harness identity.env&#8217;s USERS=4 line is stale template metadata; the actual run is
-u 1) &#183; kernel 6.8.0-124-generic (unchanged all campaign) &#183; bitfile Release Code 01.05.08.00 / 06-16-2026 (all draws)
&#183; perfetto categories scheduler, model, driver, sys; 25&#8201;s captures, 2&#8201;GB ring buffer; traces 57&#8211;62&#8201;MB/draw
&#183; analysis scripts: <code>deep-dive-3bda/analysis/{{pfgate_windows,window_gaps,aggregate_draws,attribution,lane_extract,build_report}}.py</code>;
machine restored and verified serving the trio at 12:28 UTC.
Known artifacts: fill_logits_buffer end events fall outside the gate in ~11% of windows (repaired from its notify_listener
wrapper); unmatched END events can extend a still-open slice to a later stray END (window extents therefore computed from
&lt;2.5&#8201;ms spans only); slices between capture start and decode start are absent because parse batches keep the gate closed.
</p>
</body></html>
"""
open(OUT, "w").write(html)
print(f"wrote {OUT}: {len(html)} bytes")
