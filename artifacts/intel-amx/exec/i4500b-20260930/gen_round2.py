#!/usr/bin/env python3
"""Build VNNIed-K-in-place/issue4500/round2-4500.html: the plain-English report of issue #4500 round 2 with inline
SVG figures (who scores which keys, the life of a 16-token block, the per-pass trace series, the wall-clock lanes of
the block-completing pass, the result dumbbells on a percent axis, the latch release). Data: exec/results/i4500b-20260930
(summary.json, cells/*/perf-e0.json, traces/passes.json and traces/lanes14.json from traces_passes.py,
traces/analysis.json, smoke, tests), exec/results/i4500fix-20260928 (the 09-29 TTFT spread) and
exec/results/i4500c-20260930/perf. Light theme, ASCII only, no external resources. Reviewed by workflow
wf_c6c82f11-841 (plain English, facts, diagrams); its 84 confirmed findings are applied here.
Usage: gen_round2.py [OUT_HTML]"""
import glob, html, json, math, os, statistics, sys
RES = "/home/jhan/workspace/intel-AMX/exec/results/i4500b-20260930"
RES0 = "/home/jhan/workspace/intel-AMX/exec/results/i4500fix-20260928"
RESC = "/home/jhan/workspace/intel-AMX/exec/results/i4500c-20260930"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4500/round2-4500.html"
C = {"base": "#2a78d6", "fix": "#eb6834", "fixS1": "#1f9d55", "grey": "#6b7280", "line": "#d6d9de", "ink": "#1f2937", "soft": "#f3f5f8",
     "card": "#7c3aed", "cpu": "#b45309", "burst": "#dc2626"}
def esc(x): return html.escape(str(x))
def T(n): return {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78}.get(n, 2.0)
# ---------------- data ----------------
summary = json.load(open(os.path.join(RES, "summary.json")))
groups = {}
for key, reps in summary["cells"].items():
    model, tp, users, prompt, arm = key.split("__")
    g = groups.setdefault((model, int(tp), int(users), int(prompt)), {})
    tps = {int(r): v["tps"] for r, v in reps.items()}; ttft = {int(r): v["ttft"] for r, v in reps.items()}
    g[arm] = {"tps": tps, "ttft": ttft, "mean": statistics.mean(tps.values()), "n": len(tps), "sd": statistics.stdev(tps.values()) if len(tps) > 1 else 0.0,
              "min": min(tps.values()), "max": max(tps.values()), "ttft_mean": statistics.mean(ttft.values())}
def paired(g, a, b, metric):
    if a not in g or b not in g: return None
    common = sorted(set(g[a][metric]) & set(g[b][metric]))
    if len(common) < 2: return None
    d = [1000 / g[a][metric][r] - 1000 / g[b][metric][r] for r in common] if metric == "tps" else [g[a][metric][r] - g[b][metric][r] for r in common]
    m = statistics.mean(d); sd = statistics.stdev(d); t = m / (sd / math.sqrt(len(d))) if sd else float("inf")
    if metric == "tps": t = -t  # sign of the TPS change: positive = faster
    pct = 100 * (statistics.mean(g[a][metric][r] for r in common) / statistics.mean(g[b][metric][r] for r in common) - 1)
    return {"n": len(d), "mean": m, "sd": sd, "t": t, "pct": pct, "resolved": abs(t) >= T(len(d))}
def cell_label(model, tp, users, prompt):
    name = {"qwen3-4b": "qwen-3-4b", "llama-8b": "llama-3.1-8b"}.get(model, model)
    return f"{name} tp{tp}, {users} users per engine, prompt {prompt} ({'FPGA' if model.startswith('qwen') else 'CPU'} attention)"
passes = json.load(open(os.path.join(RES, "traces", "passes.json")))
lanes = json.load(open(os.path.join(RES, "traces", "lanes14.json")))
analysis = json.load(open(os.path.join(RES, "traces", "analysis.json")))
def ready_max_mean(arm, cell):
    tr = next(t for t in analysis if t["trace"].startswith(f"{arm}__{cell}"))
    vals = [p["spans"]["Attention Ready@worker"]["max_thread_us"] for p in tr["passes"] if p["dur_ms"] > 0 and "Attention Ready@worker" in p["spans"]]
    return statistics.mean(vals)
def pmean(arm, cell, k): return statistics.mean(r[k] for r in passes[f"{arm}__{cell}"])
def quiet_gap(arm, cell): return statistics.median(r["end_gap_us"] for i, r in enumerate(passes[f"{arm}__{cell}"]) if i not in (14, 30))
G2, G4, GL = groups[("qwen3-4b", 2, 2, 1024)], groups[("qwen3-4b", 4, 4, 1024)], groups[("llama-8b", 2, 8, 4096)]
def ttft_sd_0929():
    tt = {}
    for d in glob.glob(os.path.join(RES0, "cells", "*")):
        p = os.path.join(d, "perf-e0.json")
        if os.path.exists(p):
            cell, arm, rep = os.path.basename(d).rsplit("__", 2); tt.setdefault((cell, arm), {})[int(rep[3:])] = json.load(open(p))["ttft_mean_ms"]
    out = {}
    for cell in sorted({k[0] for k in tt}):
        a, b = tt[(cell, "fix")], tt[(cell, "base")]; common = sorted(set(a) & set(b))
        out[cell] = statistics.stdev([a[r] - b[r] for r in common])
    return out
SD0 = ttft_sd_0929()
def sd_today(g): return paired(g, "fixS1", "base", "ttft")["sd"]
# ---------------- SVG helpers ----------------
def svg_open(w, h, label): return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px;font-family:system-ui,sans-serif;font-size:13px;display:block" role="img" aria-label="{esc(label)}"><rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff"/><defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{C["ink"]}"/></marker></defs>'
def txt(x, y, s, anchor="start", fill=None, size=13, weight="normal"): return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill or C["ink"]}" font-size="{size}" font-weight="{weight}">{esc(s)}</text>'
def box(x, y, w, h, fill, stroke=None, r=4): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke or C["line"]}"/>'
def arrow(x1, y1, x2, y2, dash=False, head=True):
    dsh = 'stroke-dasharray="5 4"' if dash else ""
    mk = 'marker-end="url(#ah)"' if head else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C["ink"]}" stroke-width="1.6" {dsh} {mk}/>'
def figure(svg, caption): return f'<figure>{svg}<figcaption>{caption}</figcaption></figure>'
# Figure 1: who scores which keys
def diag_keys():
    W, H = 1100, 290
    o = [svg_open(W, H, "Which keys the card scores and which keys the CPU scores in one decode step under FPGA attention, when the DMA keeps up")]
    x0, x1, y = 60, 1040, 110; d_x = 820; p_x = 1000
    o.append(txt(x0, 32, "one user at decode step P (prompt 1024 plus generated tokens); the K cache holds one 256-byte row per token and KV head", size=12, fill=C["grey"]))
    o.append(f'<rect x="{x0}" y="{y}" width="{d_x - x0}" height="34" fill="#ede9fe" stroke="{C["line"]}"/>')
    o.append(f'<rect x="{d_x}" y="{y}" width="{p_x - d_x}" height="34" fill="#fef3c7" stroke="{C["line"]}"/>')
    o.append(f'<rect x="{p_x}" y="{y}" width="{x1 - p_x}" height="34" fill="#fee2e2" stroke="{C["line"]}"/>')
    o.append(txt(x0 + 6, y + 22, "keys 0 .. D: every GOF that the card already holds", size=12)); o.append(txt(d_x + 6, y + 22, "D+1 .. P-1", size=12)); o.append(txt(p_x + 4, y + 22, "P", size=12))
    o.append(txt(x0, y + 54, "position 0 (prompt start)", size=11, fill=C["grey"])); o.append(txt(d_x, y + 54, "D = last DMA-complete GOF", size=11, fill=C["grey"], anchor="middle")); o.append(txt(p_x + 20, y + 54, "P = this step's token", size=11, fill=C["grey"], anchor="middle"))
    o.append(f'<path d="M{x0} {y - 14} L{x0} {y - 26} L{d_x - 4} {y - 26} L{d_x - 4} {y - 14}" fill="none" stroke="{C["card"]}" stroke-width="2"/>')
    o.append(txt((x0 + d_x) / 2, y - 34, "the card scores these keys; the CPU reads no K-cache bytes for their pages", anchor="middle", fill=C["card"], weight="bold"))
    o.append(f'<path d="M{d_x + 2} {y + 72} L{d_x + 2} {y + 84} L{x1} {y + 84} L{x1} {y + 72}" fill="none" stroke="{C["cpu"]}" stroke-width="2"/>')
    o.append(txt(x1, y + 104, "the CPU scores only the tail: 1 to 4 keys when the DMA is at most one GOF behind", anchor="end", fill=C["cpu"], weight="bold"))
    o.append(txt(x1, y + 122, "(measured mean 2.5 keys per attention job at prompt 1024, so it is); a lagging DMA makes the tail longer", anchor="end", fill=C["cpu"], size=12))
    o.append(txt(x1, y + 140, "a GOF never crosses a 16-token block (16 = 4 x 4), so the tail then sits in the current block, row-major: 4 cache lines per key", anchor="end", fill=C["cpu"], size=12))
    o.append(txt(x0, H - 14, "Not in this picture: the 09-29 report's idea that positions 64..126 are scored every step. The engagement point (127) gates query positions and the card's first DMA prefix, never keys.", size=12, fill=C["grey"]))
    o.append("</svg>"); return "".join(o)
# Figure 2: the life of a block, fix vs policy (mechanism only)
def diag_block():
    W, H = 1100, 300
    o = [svg_open(W, H, "The life of one 16-token K block in decode: the fix converts it at the forward end, the policy leaves it row-major")]
    x0, y0, cw = 60, 60, 40
    o.append(txt(x0, 36, "decode steps (one token per user per step); the block receives one row-major row per step", size=12, fill=C["grey"]))
    for i in range(16):
        o.append(box(x0 + i * cw, y0, cw - 4, 26, "#dcfce7" if i < 15 else "#bbf7d0")); o.append(txt(x0 + i * cw + (cw - 4) / 2, y0 + 18, str(i + 1), anchor="middle", size=11))
    o.append(txt(x0 + 16 * cw + 8, y0 + 18, "row 16 saved: the block is complete", size=12))
    yb = 130
    o.append(arrow(x0 + 15 * cw + 18, y0 + 30, 330, yb - 6)); o.append(arrow(x0 + 15 * cw + 18, y0 + 30, 790, yb - 6))
    o.append(box(120, yb, 420, 130, "#fff7ed", C["fix"])); o.append(txt(130, yb + 20, "the 09-29 fix (f34b0fe2ec)", weight="bold", fill=C["fix"]))
    o.append(txt(130, yb + 44, "forward end of step 16, main thread: convert the block", size=12))
    o.append(txt(130, yb + 62, "in place to the VNNI layout, one block after the other,", size=12))
    o.append(txt(130, yb + 80, "for every layer and KV head (288 blocks per user)", size=12))
    o.append(txt(130, yb + 104, "the block is then VNNI: 64 cache lines per read of a row", size=12, fill=C["burst"]))
    o.append(box(580, yb, 460, 130, "#f0fdf4", C["fixS1"])); o.append(txt(590, yb + 20, "the policy (452b2052c9)", weight="bold", fill=C["fixS1"]))
    o.append(txt(590, yb + 44, "the operation is hardware-scored (cached_operation_uses_hw):", size=12))
    o.append(txt(590, yb + 62, "no row bit recorded, no block queued, no conversion", size=12))
    o.append(txt(590, yb + 80, "the block stays row-major for the life of the page", size=12))
    o.append(txt(590, yb + 104, "every read of a row stays 4 cache lines", size=12, fill=C["fixS1"]))
    o.append(txt(60, H - 14, "Both keep the whole-block prefill saves in the VNNI layout. The dense AMX kernel never runs in decode after the card has engaged at prompt 1024 (measured 0 dense-page visits).", size=12, fill=C["grey"]))
    o.append("</svg>"); return "".join(o)
# Figure 3: per-pass series (row 0 left out, per-arm length)
def diag_passes():
    W, H = 1100, 560
    o = [svg_open(W, H, "Decode pass duration per traced pass for base, fix and fixS1 at tp2 with 2 users and tp4 with 4 users: the fix rises at rows 14 and 30")]
    for k, (cell, title, ylo, yhi) in enumerate([("tp2__2u", "tp2, 2 users: pass duration, ms", 4.6, 6.2), ("tp4__4u", "tp4, 4 users: pass duration, ms", 5.4, 10.4)]):
        L, R, Tp, B = 70, 1040, 40 + k * 270, 40 + k * 270 + 200
        n = 38
        def x(i): return L + (i - 1) / (n - 2) * (R - L)
        def y(v): return B - (v - ylo) / (yhi - ylo) * (B - Tp)
        o.append(txt(L, Tp - 14, title, weight="bold"))
        for tv in [ylo + (yhi - ylo) * f for f in (0, 0.25, 0.5, 0.75, 1)]:
            o.append(f'<line x1="{L}" y1="{y(tv):.1f}" x2="{R}" y2="{y(tv):.1f}" stroke="{C["line"]}"/>'); o.append(txt(L - 8, y(tv) + 4, f"{tv:.1f}", anchor="end", size=11, fill=C["grey"]))
        for i in range(2, n, 4): o.append(txt(x(i), B + 16, str(i), anchor="middle", size=11, fill=C["grey"]))
        o.append(txt((L + R) / 2, B + 32, "trace row (row 0 = the 10th decode pass of a 40-token run, left out: 7 to 17 ms); a block completes at rows 14 and 30, 16 passes apart", anchor="middle", size=11, fill=C["grey"]))
        for arm in ("base", "fix", "fixS1"):
            rows = passes[f"{arm}__{cell}"]
            pts = " ".join(f"{x(i):.1f},{y(min(max(r['pass_ms'], ylo), yhi)):.1f}" for i, r in enumerate(rows) if 1 <= i < n)
            o.append(f'<polyline points="{pts}" fill="none" stroke="{C[arm]}" stroke-width="{2.4 if arm == "fixS1" else 1.8}"/>')
            for i, r in enumerate(rows):
                if 1 <= i < n and (r["pass_ms"] > yhi or r["pass_ms"] < ylo):
                    edge = yhi if r["pass_ms"] > yhi else ylo; d = 8 if r["pass_ms"] > yhi else -8
                    o.append(f'<polygon points="{x(i) - 5:.1f},{y(edge) + d:.1f} {x(i) + 5:.1f},{y(edge) + d:.1f} {x(i):.1f},{y(edge):.1f}" fill="none" stroke="{C[arm]}"/>')
        for i in (14, 30):
            v = passes[f"fix__{cell}"][i]["pass_ms"]
            o.append(f'<circle cx="{x(i):.1f}" cy="{y(min(v, yhi)):.1f}" r="6" fill="none" stroke="{C["burst"]}" stroke-width="2"/>')
        b = passes[f"fix__{cell}"]
        o.append(txt(x(14) + 10, y(min(b[14]["pass_ms"], yhi)) - 8, f"row 14: fix {b[14]['pass_ms']:.2f} ms, fixS1 {passes['fixS1__' + cell][14]['pass_ms']:.2f} ms, base {passes['base__' + cell][14]['pass_ms']:.2f} ms", size=11, fill=C["burst"]))
        lx = R - 330
        for j, arm in enumerate(("base", "fix", "fixS1")):
            o.append(f'<line x1="{lx + j * 110}" y1="{B - 10}" x2="{lx + j * 110 + 24}" y2="{B - 10}" stroke="{C[arm]}" stroke-width="3"/>'); o.append(txt(lx + j * 110 + 30, B - 6, arm, size=12))
    o.append("</svg>"); return "".join(o)
# Figure 3b: wall-clock lanes of pass 14 at tp4
def diag_lanes():
    W, H = 1100, 400
    cell = "tp4__4u"
    o = [svg_open(W, H, "Wall-clock lanes of decode pass 14 at tp4 with 4 users for base, fix and fixS1: the main thread's time after the workers' last span is the serial slice")]
    L, R = 130, 1040; tmax = 10.0
    def x(us): return L + (us / 1000) / tmax * (R - L)
    o.append(txt(L, 18, "wall-clock time inside the pass, ms (to scale; the three passes are aligned at their start)", size=12, fill=C["grey"]))
    o.append(txt(L, 34, "black = Save K, Save V, prepare, launch on main; dashed = staging drain, waiting for logits; blue band = at least one attention worker has a span", size=11, fill=C["grey"]))
    for t in range(0, 11, 1):
        o.append(f'<line x1="{x(t * 1000):.1f}" y1="42" x2="{x(t * 1000):.1f}" y2="{H - 30}" stroke="{C["line"]}"/>'); o.append(txt(x(t * 1000), H - 14, str(t), anchor="middle", size=11, fill=C["grey"]))
    for k, arm in enumerate(("base", "fix", "fixS1")):
        j = lanes[f"{arm}__{cell}"]; sp = j["spans"]; y0 = 44 + k * 116
        o.append(txt(L - 10, y0 + 16, arm, anchor="end", weight="bold", fill=C[arm]))
        wk = [s for s in sp if s["thread"] == "worker"]; busy = [False] * 520
        for s in wk:
            for b in range(int(s["t_us"] // 20), min(519, int((s["t_us"] + s["dur_us"]) // 20)) + 1): busy[b] = True
        o.append(txt(L - 10, y0 + 40, f"{j['n_workers']} attention workers", anchor="end", size=11, fill=C["grey"]))
        b = 0
        while b < 520:
            if busy[b]:
                e = b
                while e < 520 and busy[e]: e += 1
                o.append(f'<rect x="{x(b * 20):.1f}" y="{y0 + 30}" width="{max(1.0, x(e * 20) - x(b * 20)):.1f}" height="14" fill="#c7d2fe"/>'); b = e
            else: b += 1
        o.append(txt(L - 10, y0 + 64, "main thread", anchor="end", size=11, fill=C["grey"]))
        mn = [s for s in sp if s["thread"] == "main"]
        for s in mn:
            if s["name"] in ("Save K", "Save V", "prep_hw_attn", "launch_hw_attn", "Free scratchpads"):
                o.append(f'<rect x="{x(s["t_us"]):.1f}" y="{y0 + 54}" width="{max(0.8, x(s["t_us"] + s["dur_us"]) - x(s["t_us"])):.1f}" height="14" fill="{C["ink"]}"/>')
            elif s["name"] in ("wait_coop_gof", "gof_rodeo", "prepare_for_dma", "waiting_for_logits"):
                o.append(f'<rect x="{x(s["t_us"]):.1f}" y="{y0 + 54}" width="{max(0.8, x(s["t_us"] + s["dur_us"]) - x(s["t_us"])):.1f}" height="14" fill="none" stroke="{C["grey"]}" stroke-dasharray="3 2"/>')
        last_w = max(s["t_us"] + s["dur_us"] for s in wk); end = j["dur_ms"] * 1000
        o.append(f'<rect x="{x(last_w):.1f}" y="{y0 + 76}" width="{max(1.0, x(end) - x(last_w)):.1f}" height="10" fill="{C["burst"]}" opacity="0.85"/>')
        o.append(txt(x(end) - 4, y0 + 100, f"main alone after the last worker span: {(end - last_w) / 1000:.2f} ms of a {j['dur_ms']:.2f} ms pass", anchor="end", size=11, fill=C["burst"]))
        o.append(f'<line x1="{x(end):.1f}" y1="{y0 + 26}" x2="{x(end):.1f}" y2="{y0 + 90}" stroke="{C[arm]}" stroke-width="2"/>')
    o.append("</svg>"); return "".join(o)
# Figure 4/5: dumbbells on a percent axis
def diag_dumbbell(metric, title, unit):
    rows = sorted(groups); W, LEFT, RIGHT, RH, TOP = 1100, 480, 240, 92, 44; H = TOP + RH * len(rows) + 44
    o = [svg_open(W, H, title)]
    lo, hi = -12.0, 12.0
    def x(p): return LEFT + (p - lo) / (hi - lo) * (W - LEFT - RIGHT)
    for i, key in enumerate(rows):
        g = groups[key]; y = TOP + i * RH + RH / 2; base = g["base"]["mean" if metric == "tps" else "ttft_mean"]
        present = [(a, g[a]) for a in ("base", "fix", "fixS1") if a in g]
        vals = [g[a]["mean" if metric == "tps" else "ttft_mean"] for a, _ in present]
        pcts = [100 * (v / base - 1) for v in vals]
        o.append(f'<line x1="{LEFT}" y1="{y + 22}" x2="{W - RIGHT}" y2="{y + 22}" stroke="{C["line"]}"/>')
        for tick in (-12, -6, 0, 6, 12): o.append(txt(x(tick), y + 36, f"{tick:+d} %" if tick else "base", anchor="middle", size=11, fill=C["grey"]))
        o.append(f'<line x1="{x(0):.1f}" y1="{y - 12}" x2="{x(0):.1f}" y2="{y + 22}" stroke="{C["line"]}"/>')
        o.append(txt(LEFT - 12, y - 8, cell_label(*key), anchor="end", size=12))
        xs = [x(p) for p in pcts]
        o.append(f'<line x1="{min(xs):.1f}" y1="{y}" x2="{max(xs):.1f}" y2="{y}" stroke="#bbb" stroke-width="3"/>')
        for (a, v), xv in zip(present, xs): o.append(f'<circle cx="{xv:.1f}" cy="{y}" r="7" fill="{C[a]}"/>')
        for k, ((a, v), val) in enumerate(zip(present, vals)): o.append(txt(W - RIGHT + 16, y - 22 + 17 * k, f"{a} {val:.1f} {unit} (n = {v['n']})", fill=C[a], size=12))
        p = paired(g, "fixS1", "base", metric)
        if p: o.append(txt(LEFT - 12, y + 12, f"fixS1 vs base: {p['pct']:+.1f} % (paired t {p['t']:+.1f}, {'resolved' if p['resolved'] else 'not resolved'})", anchor="end", fill=C["fixS1"], size=12))
    lx = 40
    for a in ("base", "fix", "fixS1"): o.append(f'<circle cx="{lx + 6}" cy="{TOP - 28}" r="6" fill="{C[a]}"/>' + txt(lx + 16, TOP - 24, a, size=12)); lx += 80
    o.append(txt(lx + 10, TOP - 24, f"{title}; the axis is the change against base in percent, the same scale in every row", size=12, fill=C["grey"]))
    o.append("</svg>"); return "".join(o)
# Figure 6: latch release (mechanism only)
def diag_latch():
    W, H = 1100, 290
    o = [svg_open(W, H, "The K/V latch: the main thread counts it down twice per layer with a locked read-modify-write; the attention workers wait on its cache line inside a TSX transaction")]
    o.append(box(60, 110, 260, 70, C["soft"])); o.append(txt(190, 138, "main thread", anchor="middle", weight="bold")); o.append(txt(190, 160, "end of Save K, end of Save V", anchor="middle", size=12))
    o.append(box(440, 110, 230, 70, "#fef3c7")); o.append(txt(555, 138, "latch (one cache line)", anchor="middle", weight="bold")); o.append(txt(555, 160, "upstream_kvs_ready[slot]", anchor="middle", size=12))
    o.append(arrow(320, 145, 436, 145)); o.append(txt(378, 134, "count_down", anchor="middle", size=12)); o.append(txt(378, 196, "fetch_sub: one locked", anchor="middle", size=11, fill=C["grey"])); o.append(txt(378, 210, "read-modify-write", anchor="middle", size=11, fill=C["grey"]))
    for i in range(6):
        yy = 30 + i * 38
        o.append(box(820, yy, 220, 30, "#eef2ff")); o.append(txt(930, yy + 20, f"attention worker {i + 1 if i < 5 else '... 25'}", anchor="middle", size=12))
        o.append(arrow(816, yy + 15, 674, 118 + i * 10, dash=True, head=False))
    o.append(txt(700, 20, "wait(): xbegin, read the latch line, tpause loop, xend", size=12, fill=C["grey"]))
    o.append(txt(60, 232, "main's write aborts every waiting transaction at once; 25 workers at tp2 with 2 users, 50 at tp4 with 4 users", size=12, fill=C["grey"]))
    o.append(txt(60, 252, "the mwaitx namespace name is historical: on Intel the wait is a TSX transaction with tpause [src/system/mwaitx.cpp:104-106]", size=12, fill=C["grey"]))
    o.append(txt(60, 272, "the latch opens after the second count-down of the layer (kvs_needed = 2 per minibatch pair)", size=12, fill=C["grey"]))
    o.append("</svg>"); return "".join(o)
# ---------------- tables ----------------
def cells_table():
    h = ["<table><tr><th>cell</th><th>arm</th><th>n</th><th>TPS mean</th><th>sd</th><th>min / max</th><th>step ms</th><th>TTFT ms</th></tr>"]
    for key in sorted(groups):
        for a in ("base", "fix", "fixS1", "basekill", "fixS1kill"):
            if a not in groups[key]: continue
            v = groups[key][a]
            h.append(f"<tr><td>{esc(cell_label(*key))}</td><td>{a}</td><td>{v['n']}</td><td>{v['mean']:.2f}</td><td>{v['sd']:.2f}</td><td>{v['min']:.2f} / {v['max']:.2f}</td><td>{1000 / v['mean']:.3f}</td><td>{v['ttft_mean']:.0f}</td></tr>")
    return "\n".join(h) + "</table>"
def pairs_table(metric):
    unit = "a minus b, ms per step" if metric == "tps" else "a minus b, ms of TTFT"
    h = [f"<table><tr><th>cell</th><th>a</th><th>b</th><th>n</th><th>{unit}</th><th>change in %</th><th>paired t (positive = a is better)</th><th>resolved</th></tr>"]
    for key in sorted(groups):
        for a, b in (("fixS1", "base"), ("fix", "base"), ("fixS1", "fix"), ("basekill", "base"), ("fixS1kill", "fixS1")):
            p = paired(groups[key], a, b, metric)
            if p:
                tt = p["t"] if metric == "tps" else -p["t"]
                h.append(f"<tr><td>{esc(cell_label(*key))}</td><td>{a}</td><td>{b}</td><td>{p['n']}</td><td>{p['mean']:+.3f} (sd {p['sd']:.3f})</td><td>{p['pct']:+.2f}</td><td>{tt:+.2f}</td><td>{'yes' if p['resolved'] else 'no'}</td></tr>")
    return "\n".join(h) + "</table>"
def trace_table():
    h = ["<table><tr><th>arm, cell</th><th>complete decode passes</th><th>pass ms (mean)</th><th>Save K on main, us per pass</th><th>Save V on main, us per pass</th><th>end gap, quiet passes (median), us</th><th>end gap, rows 14 and 30, us</th><th>slowest worker's Ready time, us per pass</th></tr>"]
    for cell in ("tp2__2u", "tp4__4u"):
        for arm in ("base", "fix", "fixS1"):
            rows = passes[f"{arm}__{cell}"]
            h.append(f"<tr><td>{arm}, {cell.replace('__', ' ').replace('u', ' users')}</td><td>{len(rows)}</td><td>{pmean(arm, cell, 'pass_ms'):.3f}</td><td>{pmean(arm, cell, 'save_k_us'):.0f}</td><td>{pmean(arm, cell, 'save_v_us'):.0f}</td><td>{quiet_gap(arm, cell):.0f}</td><td>{rows[14]['end_gap_us']:.0f} / {rows[30]['end_gap_us']:.0f}</td><td>{ready_max_mean(arm, cell):.0f}</td></tr>")
    return "\n".join(h) + "</table>"
def pre(path, n=40):
    if not os.path.exists(path): return "<p>(not available)</p>"
    return "<pre>" + esc("\n".join(open(path, errors="replace").read().splitlines()[-n:])) + "</pre>"
def req_row(key):
    g = groups[key]; pt = paired(g, "fixS1", "base", "tps"); pf = paired(g, "fixS1", "base", "ttft")
    def w(p, sign, metric):
        tt = p["t"] if metric == "tps" else -p["t"]
        s = f"{p['pct']:+.2f} % (paired t {tt:+.1f}, n = {p['n']})"
        if not p["resolved"]: return s + ": not resolved, so not worse"
        return s + (": better" if p["pct"] * sign > 0 else ": worse")
    tw, fw = w(pt, +1, "tps"), w(pf, -1, "ttft")
    if fw.endswith(": worse"): verdict = f"TPS better. TTFT worse by {pf['mean']:+.0f} ms on {g['base']['ttft_mean'] / 1000:.1f} s, so the strict rule fails. jhan decides whether that size is acceptable."
    elif pt["resolved"] or pf["resolved"]: verdict = "met (one metric better, the other not worse)"
    else: verdict = "not worse on both, neither resolved"
    return f"<tr><td>{esc(cell_label(*key))}</td><td>{esc(tw)}</td><td>{esc(fw)}</td><td>{esc(verdict)}</td></tr>"
fix2, fix4 = passes["fix__tp2__2u"], passes["fix__tp4__4u"]
lane_tail = {arm: (lanes[f"{arm}__tp4__4u"]["dur_ms"] * 1000 - max(s["t_us"] + s["dur_us"] for s in lanes[f"{arm}__tp4__4u"]["spans"] if s["thread"] == "worker")) / 1000 for arm in ("base", "fix", "fixS1")}
P2, P4, PL = paired(G2, "fixS1", "base", "tps"), paired(G4, "fixS1", "base", "tps"), paired(GL, "fixS1", "base", "tps")
F2, F4, FL = paired(G2, "fixS1", "base", "ttft"), paired(G4, "fixS1", "base", "ttft"), paired(GL, "fixS1", "base", "ttft")
base4_sorted = sorted(G4["base"]["tps"].values())
page = f"""<title>Issue 4500 Round Two</title>
<style>
/* layout: one reading column, figures at full column width, tables scroll in their own box */
:root{{--bg:#fbfbf9;--fg:#1f2937;--muted:#6b7280;--line:#d6d9de;--soft:#f3f5f8;--accent:#1f9d55;color-scheme:light}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.5;margin:0;padding-block:24px;padding-inline:16px}}
main{{max-width:1060px;margin:0 auto}}
h1{{font-size:26px;line-height:1.25;text-wrap:balance;margin:0 0 12px}}h2{{font-size:20px;margin:36px 0 10px;text-wrap:balance}}h3{{font-size:16px;margin:22px 0 6px}}
p,li{{max-width:78ch}}
.short{{background:#eef6ff;border-left:4px solid #2a78d6;padding:10px 14px}}.note{{background:#fff8e6;border-left:4px solid #e0a800;padding:8px 12px}}
table{{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}}th,td{{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}}th{{background:var(--soft)}}
.tbl{{overflow-x:auto;max-width:100%}}pre{{background:var(--soft);padding:8px;overflow-x:auto;font-size:12px}}
figure{{margin:16px 0;overflow-x:auto;max-width:100%}}figure svg{{height:auto;min-width:700px}}figcaption{{font-size:13px;color:var(--muted);max-width:90ch;margin-top:6px}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;font-size:14px}}dt{{font-weight:600}}dd{{margin:0;max-width:78ch}}
@media (max-width:600px){{dl{{grid-template-columns:1fr}}}}
</style>
<main>
<h1>Issue #4500, round two: the VNNI K layout no longer loses on qwen-3-4b under FPGA attention</h1>
<p class="short"><b>Short version.</b> The qwen-3-4b decode loss that remained after the 09-29 fix came from a K-block conversion that the FPGA never uses. Commit 452b2052c9 stops that conversion when the FPGA scores the attention, and the policy build now matches canonical AMX on qwen-3-4b decode TPS ({P2['pct']:+.1f} % at tp2 with 2 users, {P4['pct']:+.1f} % at tp4 with 4 users, both inside the run-to-run spread) with TTFT {F4['pct']:.1f} % lower at tp4. llama-3.1-8b keeps its {PL['pct']:+.1f} % TPS gain, and its TTFT is {FL['mean']:.0f} ms ({FL['pct']:.2f} %) higher on 13.4 s, which jhan must judge.</p>
<p>Generated 2026-09-30 from exec/results/i4500b-20260930 and exec/results/i4500c-20260930 by exec/i4500b-20260930/gen_round2.py. Every number on this page is a measurement unless it is marked "est.".</p>

<h2>Words used here</h2>
<dl>
<dt>tron, runtron, rinzler</dt><dd>The inference program under test, its command-line tool, and the production server built from it.</dd>
<dt>K, V, KV cache, KV head</dt><dd>The key (K) and value (V) rows that attention keeps for every earlier token. The KV cache stores them. qwen-3-4b has 8 KV heads per layer, each with its own K and V rows of 256 bytes per token.</dd>
<dt>layer, KV slot, operation</dt><dd>One of the 36 transformer layers of qwen-3-4b, the K and V store of one layer, and one attention statement of the model (one per layer here).</dd>
<dt>AMX</dt><dd>Intel Advanced Matrix Extensions, the CPU's matrix (tile) instructions. The dense AMX kernel scores a dense page (all 64 keys of a page) with them.</dd>
<dt>VNNI K, the VNNI layout</dt><dd>VNNI = Vector Neural Network Instructions, the operand format the AMX kernel reads. The VNNI K layout of PR #4424 stores a 16-token block of one KV head as that operand: one 4-byte pair of each token in each of 64 cache lines.</dd>
<dt>row-major</dt><dd>One K row of a token as 256 contiguous bytes (4 cache lines of 64 bytes).</dd>
<dt>block, page, plane</dt><dd>16 tokens of one KV head (4 KiB), 64 tokens (4 blocks), and the K store of one page and KV head (16 KiB).</dd>
<dt>row bit, block bit, short run</dt><dd>One flag per row that says the row was saved singly into a block, one flag per block that says which layout the block holds (every reader checks it), and a save of fewer than 16 rows (the decode case).</dd>
<dt>canonical AMX, base</dt><dd>main 3faba6d0fd with the AMX kernels compiled into the package and row-major K. The arm every result is compared with.</dd>
<dt>the fix</dt><dd>The 09-29 change: a 16-token block stays row-major until its 16th row is saved, then the main thread converts it in place at the end of the forward pass. The rinzler package 98a5accb8b was built from 617cb8333f. The runtron binary of the traces and the smoke is f34b0fe2ec, three commits later (24 lines of self_attention.hpp reorder the dense-gate reads, the rest is tests).</dd>
<dt>the policy, fixS1</dt><dd>Commit 452b2052c9 (package 2fd11e32ca): the fix plus this round's change, described in section 4.</dd>
<dt>basekill, fixS1kill</dt><dd>The base and policy packages run with the kill switch on, at tp4 only.</dd>
<dt>kill switch</dt><dd>TRON_AMX_DISABLE=1. It turns off the AMX tile bracket (the per-section setup and release of the AMX tile registers), the Q packing (the copy of the query into AMX operand order) and the dense kernel. The K layout stays as built.</dd>
<dt>FPGA attention, CPU attention</dt><dd>Attention scored on the Positron card (an FPGA, field-programmable gate array), the default for the ingested qwen model, or on the CPU's attention worker threads (USE_HW_ATTN=0).</dd>
<dt>plugin</dt><dd>The model code tron runs. The qwen plugin is generated by the ingest tool. The llama plugin is hand-written and always uses CPU attention here.</dd>
<dt>GOF, DMA, staging</dt><dd>A group of four consecutive tokens whose K and V rows the CPU copies (stages) into a buffer that DMA (direct memory access) moves to the card. A GOF is "DMA-complete" once the card holds it for every layer.</dd>
<dt>the tail</dt><dd>The keys above the last DMA-complete GOF, which the CPU scores itself.</dd>
<dt>engagement point</dt><dd>hw_attn_engagement_point(), 127 by default: the first query position the card may score.</dd>
<dt>prefill, decode, pass</dt><dd>The forward passes over the prompt tokens (prefill, they set TTFT) and the one-token-per-user passes after them (decode, they set TPS). A pass is one forward pass.</dd>
<dt>main thread, attention workers, ready section</dt><dd>The thread that runs the model's statements (it saves K and V), the pool threads that score attention, and the part of a worker's attention job that scores pages the card does not cover.</dd>
<dt>dotter, qk_group</dt><dd>The two CPU routines that score keys. The dotter reads row-major rows (4 cache lines per key). qk_group reads a VNNI block (64 cache lines per block).</dd>
<dt>attention job, the PR 4596 counters</dt><dd>One user's query in one layer, and the attention path counters of PR #4596 (TRON_ATTN_STATS=1) that count visited pages and keys per path.</dd>
<dt>latch</dt><dd>A counter in one cache line that the attention workers wait on until the main thread counts it down (upstream_kvs_ready in the code).</dd>
<dt>Perfetto, span, trace</dt><dd>The tracing tool tron records into. A span is one timed region (Save K, Save V, ...). A trace is one file of spans from one runtron run.</dd>
<dt>perf, sample</dt><dd>The Linux sampling profiler. A sample is one interrupt that records which function a thread was in.</dd>
<dt>the nightly, delphi-3bda, our half</dt><dd>The CI performance run that systems_test executes every night on delphi-3bda (the shared Intel test machine). We use socket 1 of that machine and its four cards. The other half belongs to another user.</dd>
<dt>chain, gate, platformd</dt><dd>The script that runs the campaign steps in order, the time before which it waits, and the machine's service manager that starts and stops production serving.</dd>
<dt>fake device, VNNI build, row-major build</dt><dd>A software stand-in for the card that the unit tests run against, and the same source compiled with the VNNI K layout on or off (TRON_K_VNNI).</dd>
<dt>TPS, TTFT</dt><dd>Decode tokens per second per user (the nightly's client captures it between generated tokens 896 and 1024 of 1536, over 10 rounds), and time to first token in ms.</dd>
<dt>paired t, resolved</dt><dd>The mean of the per-repetition differences divided by its standard error. On this page the sign is turned so that a positive t means the first-named arm is better (faster TPS, lower TTFT). Resolved = the absolute t is at least the two-sided 95 % threshold (4.30 at n = 3, 3.18 at n = 4). Not resolved = the difference is inside the run-to-run spread.</dd>
<dt>tp2, tp4, users per engine</dt><dd>The model split over 2 or 4 cards, and the number of client streams one engine serves.</dd>
<dt>cell, arm, repetition</dt><dd>One test configuration (model, split, users, prompt length), one binary plus environment, one run of the cell with that arm.</dd>
<dt>bf16, memcpy</dt><dd>16-bit brain floating point, the type of the K rows, and one memory copy call.</dd>
</dl>

<h2>1. The requirement and the verdict</h2>
<p>jhan asked on 2026-09-30 that the VNNI K layout deliver better TPS and TTFT than canonical AMX on llama-8b tp2 and on qwen3-4b tp2 and tp4. If the layout is not better on both metrics, then one metric must be better and the other must not be worse.</p>
<div class="tbl"><table><tr><th>cell</th><th>TPS, policy vs canonical</th><th>TTFT, policy vs canonical</th><th>verdict</th></tr>
{req_row(("llama-8b", 2, 8, 4096))}{req_row(("qwen3-4b", 2, 2, 1024))}{req_row(("qwen3-4b", 4, 4, 1024))}</table></div>
<p>The cells are the nightly's own loads. Four repetitions per arm, arms interleaved, one engine on our half of delphi-3bda, the nightly's own client. Section 5 has the numbers.</p>

<h2>2. Where the remaining loss came from</h2>
<p>The 09-29 fix left qwen-3-4b at -2.3 % TPS (tp2) and -8.8 % (tp4) against canonical, both unresolved at 3 repetitions. A 25-agent code reading of the branch and of main (workflow wf_6861a5cc-c84), with every fact checked by two more agents, established the following.</p>
<h3>2.1 Under FPGA attention the CPU scores only the tail</h3>
{figure(diag_keys(), "Figure 1. One decode step of one user under FPGA attention, when the DMA keeps up. The card scores every key of the DMA-complete GOFs. The CPU's software loop visits those pages but jumps over their range without reading a K byte. The CPU scores only the tail. The tail is one to four keys and lies in the current 16-token block while the DMA is at most one GOF behind, which the measured mean of 2.5 keys per job says it is.")}
<p>The 09-29 report (issue4500/fix-4500.html) named the pages at positions 64 to 126 as a cost the CPU pays on every step. The code refutes that. The engagement point gates query positions and the card's first DMA prefix, never key positions [src/tron/models/ranged_mask.cpp:42-90; h/tron/scheduler/full.hpp:2761-2815].</p>
<p>The tail measured 2.5 keys per attention job at prompt 1024 (avx k_tokens 40,704 over 2,040 jobs and 8 KV heads) with the PR 4596 counters, on a PR 4596 build at 8 users per engine [exec/results/attnstats-20260925-fpga/exit-reports.txt:40]. The dense-page counters were 0 in decode and in all 8 prefill forwards, at 1 and at 8 users [same file, lines 16, 19, 38, 41]. The fix adds one more gate, so it can only visit fewer dense pages. So the VNNI layout brings the FPGA-attention decode nothing. It can only cost.</p>
<h3>2.2 What the fix build still did per step</h3>
{figure(diag_block(), "Figure 2. The life of one 16-token K block in decode. Left: the 09-29 fix converts the completed block at the forward end, one block after the other on the main thread, for every layer and KV head. Right: the policy leaves it row-major. Both keep the whole-block prefill saves in the VNNI layout.")}
<p>Three differences to canonical remained in the fix build per decode step, all on the main thread [h/tron/models/model.hpp:3080-3096, 2818-2825; kv_cache.hpp:1843-1866, lines of the fix tree f34b0fe2ec]:</p>
<ul>
<li>The forward-end conversion. Every 16th step per user, 36 layers x 8 KV heads = 288 blocks per user are converted one after the other, after the workers have joined. Each conversion reads and writes 8 KiB in the K store (16 rows x 512 bytes of panel) and uses an 8 KiB temporary copy on the thread's stack.</li>
<li>The staging gather. In the fix build the GOF fired at the block-completing step is staged before the conversion, so the routine step reads the block row-major. Only a block staged again after its conversion (a re-populate or a backfill) costs 64 cache lines per row.</li>
<li>Row bookkeeping in the K save: one atomic per row per layer, and four page lookups per token where canonical does one.</li>
</ul>
<p>One difference between the arms was found during the reading. main 3faba6d0fd carries PR #4191 (it skips whole card-covered pages in the software loop), and the PR branch does not. The rinzler packages of every arm contain main 3faba6d0fd. So the cells compare builds that both have PR #4191. The runtron traces of section 3 use main c7844ca2ce, the branch's merge base, as their canonical arm for the same reason.</p>

<h2>3. The trace evidence</h2>
{figure(diag_passes(), "Figure 3. Duration of each traced decode pass (runtron, prompt 1024, 40 generated tokens, tracing from run pass 10). The fix (orange) rises at rows 14 and 30, where a 16-token block completes and the forward end converts it. The policy (green) does not. Row 0 is left out: it is 7.2 to 7.3 ms at tp2 and 11.6 to 17.3 ms at tp4, the first traced pass of every run. A hollow triangle marks a value clipped to the axis. Tracing adds its own cost: 124.9 TPS untraced against 113.5 TPS traced at tp2 with 8 users on 09-19 [exec/results/issue4500-20260918/rt-results.txt], and it enlarges the VNNI-vs-canonical difference. So compare the three lines with each other, not with the cells.")}
{figure(diag_lanes(), f"Figure 3b. Wall-clock lanes of decode pass row 14 at tp4 with 4 users, to scale, one row per arm. The blue band is the time in which at least one attention worker has a span (scoring, waiting for the card, joining). The black ticks are the main thread's Save K, Save V, prepare and launch spans, 36 per pass. The red bar is the main thread alone after the last worker span: {lane_tail['base']:.2f} ms in base, {lane_tail['fix']:.2f} ms in the fix, {lane_tail['fixS1']:.2f} ms in the policy build. The fix build has no span for the conversion, so its red bar holds the staging drain (dashed, 0.62 ms), the conversion and the logits. Durations are to scale. The workers' internal interleaving is collapsed into the band.")}
<div class="tbl">{trace_table()}</div>
<p>The rise is the gap from the last Save V to the end of the pass. In the fix trace it goes from {quiet_gap('fix', 'tp2__2u'):.0f} us on quiet passes to {fix2[14]['end_gap_us']:.0f} and {fix2[30]['end_gap_us']:.0f} us at rows 14 and 30 at tp2 with 2 users. At tp4 with 4 users it goes from {quiet_gap('fix', 'tp4__4u'):.0f} us to {fix4[14]['end_gap_us']:.0f} and {fix4[30]['end_gap_us']:.0f} us [traces/passes.json]. The policy trace shows no rise. The Save K span stays {pmean('fixS1', 'tp2__2u', 'save_k_us') / pmean('base', 'tp2__2u', 'save_k_us'):.1f} times canonical's at tp2 and {pmean('fixS1', 'tp4__4u', 'save_k_us') / pmean('base', 'tp4__4u', 'save_k_us'):.1f} times at tp4 in both VNNI builds. Section 7 explains that.</p>
<p>traces/passes.json and traces/lanes14.json are written by exec/i4500b-20260930/traces_passes.py from the six traces. They keep only forward spans with a positive duration (37 per trace, 38 for the policy tp4 trace). traces/analysis.md from trace_analyze.py includes an unterminated final forward of 0 ms in its means, so its pass and Save K means are lower by one part in 38.</p>

<h2>4. What the policy commit changes</h2>
<h3>4.1 The rule</h3>
<p>cached_operation_uses_hw says, once per model, whether the hardware scores an attention operation. When it does, save_k records no row bits for the rows of a short run. It also queues no block for the forward-end conversion [h/tron/models/model.hpp:3094-3107 at 452b2052c9]. Such a block stays row-major for the life of the page. No bit is ever set for it, so a page copy does not convert it either.</p>
<h3>4.2 What else changed</h3>
<ul>
<li>The FPGA staging reads a row of a row-major block in place, without the scratch copy the fix made [h/tron/scheduler/full.hpp:2658; kv_cache.hpp:1996 k_row_if_row_major]. The copy into the DMA buffer stays, as in canonical.</li>
<li>k_forget_row clears the row bits of a row that is written again. In the plain decode case (a new row appended, no bit set at or above it) it now skips its two locked atomic updates per K store [kv_cache.hpp:2264].</li>
<li>convert_pending_k_blocks gets a Perfetto span (convert_k_blocks) with the queue length [model.hpp:2828].</li>
<li>Note [Row-major blocks under hardware attention] in kv_cache.hpp:719 carries the design. Seven older comments (three in kv_cache.hpp, three in model.hpp, one in self_attention.hpp) that described every completed block as queued were corrected.</li>
<li>t_llama_unit's save_k case gains two sections. With the saving operation flagged as hardware-scored, the rows are stored at the same bytes as before, and the short-run block stays row-major after convert_pending_k_blocks. With another operation flagged, the block still converts.</li>
</ul>
<p>Two adversarial review passes found no blocker (workflows wf_f9b3a62f-255 with 60 agents and wf_d9d0ea63-7ca with 18). Their wording and test findings are applied. A second commit that rewrote the row store was dropped. The review showed that the production K buffer is bf16, the same type as the incoming row. For that type the store was already one memcpy.</p>
<h3>4.3 The accepted limitation</h3>
<p class="note">The policy is static per operation. In some states the software still scores a range of a hardware-scored operation: query positions before the engagement point, a prompt shorter than 128 tokens, a model shard (the part of the KV cache one card holds) without HBM (high-bandwidth memory), or USE_HW_ATTN=N raising the engagement point. In those states the blocks that decode completed are scored by the row-major dotter, one key at a time. Under the 09-29 fix the AMX kernel could score a full page of them. Tokens are identical either way. Every reader takes the layout from the block bit. The nightly's cells do not reach these states.</p>

<h2>5. The measurements</h2>
{figure(diag_dumbbell("tps", "decode TPS per user, higher is better", "TPS"), "Figure 4. Decode TPS per cell and arm, mean over the repetitions, drawn as the change against base in percent on one common axis. The green annotation is the policy build against canonical.")}
{figure(diag_dumbbell("ttft", "time to first token, lower is better", "ms"), f"Figure 5. TTFT per cell and arm on the same percent axis. The sd of the paired TTFT differences is {sd_today(G2):.0f} ms at tp2, {sd_today(G4):.0f} ms at tp4 and {sd_today(GL):.0f} ms on llama today, against {SD0['qwen3-4b__tp2__2u__p1024']:.0f}, {SD0['qwen3-4b__tp4__4u__p1024']:.0f} and {SD0['llama-8b__tp2__8u__p4096']:.0f} ms on 09-29 (fix minus base, exec/results/i4500fix-20260928). So the tp2 pair is not resolved today.")}
<h3>5.1 Cells</h3>
<div class="tbl">{cells_table()}</div>
<h3>5.2 Paired differences, TPS</h3>
<div class="tbl">{pairs_table("tps")}</div>
<h3>5.3 Paired differences, TTFT</h3>
<div class="tbl">{pairs_table("ttft")}</div>
<p>The kill-switch arms at tp4 say whether the AMX tile bracket and the Q packing cost anything when no dense page is scored. Both differences are inside the tp4 spread. The tp4 cell had one slow canonical repetition ({G4['base']['min']:.0f} TPS against {base4_sorted[1]:.0f} to {G4['base']['max']:.0f} TPS for the other three, sd {G4['base']['sd']:.1f} TPS). Earlier days showed the same pattern: tp4 repetitions fall into a fast group and a slow group.</p>
<h3>5.4 Tokens and tests</h3>
<p>The smoke test is a short runtron run with one user, temperature 0 (always the top token), the pay-for-determinism option (repeatable output), 128 generated tokens, prompts of 1024 and 1000 tokens, under CPU and under FPGA attention. In all four cells the policy binary's tokens equal its own repeat run and equal the fix binary's tokens. Under FPGA attention the same K bytes reach the card. Under CPU attention the policy is off.</p>
{pre(os.path.join(RES, "smoke", "smoke.txt"), 12)}
<p>Unit tests at 452b2052c9 with the fake device: 5 of 5 test binaries pass in the VNNI build, and 3 of 3 pass in the row-major build.</p>
{pre(os.path.join(RES, "tests-fixS1.txt"))}{pre(os.path.join(RES, "tests-fixS1rm.txt"))}

<h2>6. Method</h2>
<ul>
<li>The chain (exec/i4500b-20260930/chain.sh, README there) runs the steps in order. It was launched at 05:28 UTC and waited until 13:00 UTC, after the nightly. Steps: builds and tests (10 min), the policy package (13 min), the smoke test, the traces, 40 rinzler cells (13:44 to 16:44 UTC), the row-major build tests. Production serving was stopped through platformd only when idle, and restored at the end.</li>
<li>Arms: base = /var/tmp/jhan/canon-ci-20260918/root; fix = /var/tmp/jhan/i4500fix-20260928/root (98a5accb8b, built from 617cb8333f); fixS1 = /var/tmp/jhan/i4500b-20260930/root (2fd11e32ca); basekill and fixS1kill = the same with TRON_AMX_DISABLE=1, at tp4 only.</li>
<li>Client: systems_test testlib/tps.py through st_perf2.py (sharegpt prompts of the given length, 1536 generated tokens, 10 rounds). Repetitions interleaved, odd ones forward and even ones reversed.</li>
<li>Traces: runtron with --trace-gen, categories model, scheduler and hwattention, run passes 10 and later of a 40-token run, read with the Perfetto trace processor (traces_passes.py).</li>
</ul>

<h2>7. The Save K gap, explained with the perf profiler</h2>
{figure(diag_latch(), "Figure 6. The K/V latch. The main thread counts it down twice per layer, at the end of Save K and at the end of Save V, with a locked read-modify-write. The second count-down opens it. The attention workers wait on its cache line inside a TSX transaction with tpause, so main's write aborts every waiting transaction at once. That write is where perf sees the main thread's extra time.")}
<p>The main thread's Save K span was 1.8 times canonical's at tp2 and 1.5 times at tp4 in both VNNI builds (section 3). Two runtron profiles attribute it: perf record, 6 s of decode each, 391 k samples over all threads, at tp2 with 2 users (exec/results/i4500c-20260930/perf). The reports were made for the work_queue thread (the thread that owns the Save K spans) with perf report --tid and --percent-limit 0.015. So every share below is a share of that thread's own samples, and a symbol absent from a list holds less than 0.015 % of them [perf/perf.done]. The chain's automatic reports had filtered on the process id, which is a different thread, and were discarded.</p>
<p>The K store symbol (save_k_impl) is 0.02 % of the thread's samples in canonical and 0.03 % in the policy build. The policy build's thread spends 0.91 % of its samples in latch_ref::count_down, the release of the K/V latch [h/tron/threading.hpp:109-135; model.hpp:3124, 3193]. The canonical thread has no count_down entry, so it spends less than 0.015 % there. The thread is on a core the whole time (24.5 G cycles in 6 s in perf-threads.txt). So 0.91 % of a 5.2 ms pass is about 47 us (est. from the sample share), the size of the Save K gap.</p>
<p>The workers wait on that latch inside a TSX transaction with tpause [src/system/mwaitx.cpp:104-106; h/tron/models/self_attention.hpp:784]. The policy build's slowest worker finishes its ready section sooner: {ready_max_mean('fixS1', 'tp2__2u'):.0f} us per pass against {ready_max_mean('base', 'tp2__2u'):.0f} us in canonical (mean over the complete decode passes of the tp2 traces, traces/analysis.json). Hypothesis: more workers are therefore already waiting on the line when main releases it, and the release pays for their aborted transactions. The measurement that would confirm it: per pass, count the workers whose Ready span ended before main's Save V end, from the trace timestamps. The remedy would be a threading change (a release that does not abort every waiter at once, or one latch line per worker). It costs about 0.9 % of a tp2 step. At 2 users the card job is launched late (after the CPU work of the pass), so main-thread time adds directly to the step time.</p>

<h2>8. Open items</h2>
<ul>
<li>llama-8b TTFT: +{FL['mean']:.0f} ms on 13.4 s, resolved at n = 4. The PR head showed +23 ms and the 09-29 fix +47 ms on 09-29. So the increase belongs to the VNNI prefill store of the hand-written llama plugin, not to this commit. Hypothesis: in that plugin the whole-block VNNI store (16 rows transposed in registers) runs on the main thread alone. Generated plugins spread it over the worker threads (the shared block save). Measurement that would confirm it: Save K spans of a llama prefill trace, canonical against the policy build.</li>
<li>The latch release (section 7): a threading change, measurable with the same perf recipe.</li>
<li>The static policy (section 4.3): a per-range or lazy conversion would recover the AMX kernel in the software-fallback states.</li>
<li>Rebase the branch onto main past PR #4191 before the PR update. The packages already contain it.</li>
<li>Tests: no unit test instantiates store_k_block with a bf16 K buffer (the production type), and the case "a row re-saved into an already converted block" is untested through store_k_block.</li>
<li>Not part of the PR: TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 (early card launch at 2 users) gave +7.7 % TPS on the 09-18 nightly package (no AMX kernels) and +11 % on the PR-head VNNI package at tp2 with 2 users on 09-19 (n = 2, rinzler cells) [exec/results/issue4500-20260918/m6]. A product default to discuss on its own.</li>
<li>The branch jhan-amx-vnniK-i4500 is local, PR #4424 is untouched, and issue #4500 has no comment. Push, PR text and the issue comment are jhan's decisions.</li>
</ul>

<h2>9. Where the data is</h2>
<p>Results: exec/results/i4500b-20260930 (summary.md and summary.json, cells/ with 40 folders, smoke/, traces/ with the six Perfetto traces, analysis.md, passes.json and lanes14.json, tests-fixS1*.txt, tests-fixS1rm.txt) and exec/results/i4500c-20260930/perf (perf reports and per-thread counters). Scripts: exec/i4500b-20260930 (chain.sh, campaign.sh, smoke.sh, traces.sh, summarize.py, trace_analyze.py, traces_passes.py, gen_report.py, gen_round2.py) and exec/i4500c-20260930 (perf.sh). Logs: exec/logs/i4500b-20260930*.log and i4500c-20260930*.log. Worktrees: VNNIed-K-in-place/tron-i4500 (branch head 452b2052c9) and ~/workspace/ai-runs/tron-i4500-deb (2fd11e32ca). The data page of this round's cells is issue4500/policy-4500.html.</p>
</main>"""
assert all(ord(ch) < 128 for ch in page), "non-ASCII in page"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write(page)
print("wrote", OUT, len(page), "bytes")
