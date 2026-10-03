#!/usr/bin/env python3
"""Build VNNIed-K-in-place/issue4500/round2-4500.html: the plain-English report of issue #4500 round 2 with inline
SVG diagrams (who scores which keys, the life of a 16-token block, the per-pass trace series, the result dumbbells,
the latch release). Data: exec/results/i4500b-20260930 (summary.json, traces/passes.json, traces/analysis.md, smoke,
tests) and exec/results/i4500c-20260930/perf. Light theme, ASCII only, no external resources.
Usage: gen_round2.py [OUT_HTML]"""
import html, json, math, os, statistics, sys
RES = "/home/jhan/workspace/intel-AMX/exec/results/i4500b-20260930"
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
    pct = 100 * (statistics.mean(g[a][metric][r] for r in common) / statistics.mean(g[b][metric][r] for r in common) - 1)
    return {"n": len(d), "mean": m, "sd": sd, "t": t, "pct": pct, "resolved": abs(t) >= T(len(d))}
def cell_label(model, tp, users, prompt):
    name = {"qwen3-4b": "qwen-3-4b", "llama-8b": "llama-3.1-8b"}.get(model, model)
    return f"{name} tp{tp}, {users} users per engine, prompt {prompt} ({'FPGA' if model.startswith('qwen') else 'CPU'} attention)"
passes = json.load(open(os.path.join(RES, "traces", "passes.json")))
def pmean(arm, cell, k): return statistics.mean(r[k] for r in passes[f"{arm}__{cell}"])
G2, G4, GL = groups[("qwen3-4b", 2, 2, 1024)], groups[("qwen3-4b", 4, 4, 1024)], groups[("llama-8b", 2, 8, 4096)]
def pv(g, a, b, m, unit=""):
    p = paired(g, a, b, m)
    return "n/a" if not p else f"{p['pct']:+.1f} % (paired t {p['t']:+.1f}, n = {p['n']}, {'resolved' if p['resolved'] else 'not resolved'})"
# ---------------- SVG helpers ----------------
def svg_open(w, h, label): return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px;font-family:system-ui,sans-serif;font-size:13px;display:block" role="img" aria-label="{esc(label)}"><rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff"/><defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{C["ink"]}"/></marker><marker id="ahr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{C["burst"]}"/></marker></defs>'
def txt(x, y, s, anchor="start", fill=None, size=13, weight="normal"): return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill or C["ink"]}" font-size="{size}" font-weight="{weight}">{esc(s)}</text>'
def box(x, y, w, h, fill, stroke=None, r=4): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke or C["line"]}"/>'
def arrow(x1, y1, x2, y2, red=False, dash=False):
    dsh = 'stroke-dasharray="5 4"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C["burst"] if red else C["ink"]}" stroke-width="1.6" {dsh} marker-end="url(#{"ahr" if red else "ah"})"/>'
def figure(svg, caption): return f'<figure>{svg}<figcaption>{caption}</figcaption></figure>'
# Diagram A: who scores which keys
def diag_keys():
    W, H = 1100, 300
    o = [svg_open(W, H, "Which keys the card scores and which keys the CPU scores in one decode step under FPGA attention")]
    x0, x1, y = 60, 1040, 120
    # sequence bar
    o.append(box(x0, y, x1 - x0, 34, C["soft"]))
    d_x = 820; p_x = 1000
    o.append(f'<rect x="{x0}" y="{y}" width="{d_x - x0}" height="34" fill="#ede9fe" stroke="{C["line"]}"/>')
    o.append(f'<rect x="{d_x}" y="{y}" width="{p_x - d_x}" height="34" fill="#fef3c7" stroke="{C["line"]}"/>')
    o.append(f'<rect x="{p_x}" y="{y}" width="{x1 - p_x}" height="34" fill="#fee2e2" stroke="{C["line"]}"/>')
    o.append(txt(x0 + 6, y + 22, "keys 0 .. D: every GOF (group of four tokens) that the card already holds", size=12))
    o.append(txt(d_x + 6, y + 22, "D+1 .. P-1", size=12)); o.append(txt(p_x + 4, y + 22, "P", size=12))
    o.append(txt(x0, y + 56, "position 0 (prompt start)", size=11, fill=C["grey"])); o.append(txt(d_x, y + 56, "D = last DMA-complete GOF", size=11, fill=C["grey"], anchor="middle")); o.append(txt(p_x + 20, y + 56, "P = this step's token", size=11, fill=C["grey"], anchor="middle"))
    # brackets
    o.append(f'<path d="M{x0} {y - 14} L{x0} {y - 26} L{d_x - 4} {y - 26} L{d_x - 4} {y - 14}" fill="none" stroke="{C["card"]}" stroke-width="2"/>')
    o.append(txt((x0 + d_x) / 2, y - 34, "the card scores these keys (attention on the FPGA); the CPU reads 0 K bytes for their pages", anchor="middle", fill=C["card"], weight="bold"))
    o.append(f'<path d="M{d_x + 2} {y + 44 + 30} L{d_x + 2} {y + 44 + 42} L{x1} {y + 44 + 42} L{x1} {y + 44 + 30}" fill="none" stroke="{C["cpu"]}" stroke-width="2"/>')
    o.append(txt(x1, y + 44 + 60, "the CPU scores only the tail: 1 to 4 keys (measured mean 2.5 per job at prompt 1024)", anchor="end", fill=C["cpu"], weight="bold"))
    o.append(txt(x1, y + 44 + 78, "the tail lies in the current 16-token block, which the fix keeps row-major: 4 cache lines per key", anchor="end", fill=C["cpu"], size=12))
    # note on page and blocks
    o.append(txt(x0, 32, "One sequence at decode step P (prompt 1024 + generated tokens); the K cache is one row of 256 bytes per token and KV head", size=12, fill=C["grey"]))
    o.append(txt(x0, H - 22, "Not in this picture: the earlier 'positions 64..126 scored every step' idea. The engagement point (127) gates query positions and the card's first DMA prefix, never keys.", size=12, fill=C["grey"]))
    o.append("</svg>"); return "".join(o)
# Diagram B: the life of a block, fix vs policy
def diag_block():
    W, H = 1100, 420
    o = [svg_open(W, H, "The life of one 16-token K block in decode: the fix converts it at the forward end, the policy leaves it row-major")]
    # top: 16 steps
    x0, y0, cw = 60, 70, 40
    o.append(txt(x0, 40, "decode steps (one token per user per step); the block gathers one row per step", size=12, fill=C["grey"]))
    for i in range(16):
        o.append(box(x0 + i * cw, y0, cw - 4, 26, "#dcfce7" if i < 15 else "#bbf7d0"))
        o.append(txt(x0 + i * cw + (cw - 4) / 2, y0 + 18, str(i + 1), anchor="middle", size=11))
    o.append(txt(x0 + 16 * cw + 8, y0 + 18, "row 16 saved: the block is complete", size=12))
    # two branches
    yb = 150
    o.append(arrow(x0 + 15 * cw + 18, y0 + 30, 330, yb - 6)); o.append(arrow(x0 + 15 * cw + 18, y0 + 30, 790, yb - 6))
    o.append(box(120, yb, 420, 240, "#fff7ed", C["fix"])); o.append(txt(130, yb + 20, "the 09-29 fix (f34b0fe2ec)", weight="bold", fill=C["fix"]))
    o.append(txt(130, yb + 44, "at the forward end of step 16, on the main thread:", size=12))
    o.append(txt(130, yb + 62, "convert the block to the VNNI layout (transpose in place)", size=12))
    o.append(txt(130, yb + 80, "8 KiB of plane traffic + 8 KiB stack per block and KV head", size=12))
    o.append(txt(130, yb + 98, "36 layers x 8 KV heads = 288 blocks per user, in series", size=12))
    o.append(txt(130, yb + 122, "measured in the traces (every 16th pass):", size=12, fill=C["burst"]))
    o.append(txt(130, yb + 140, "+0.7 ms per burst at tp2 with 2 users (of a 5.3 ms pass)", size=12, fill=C["burst"]))
    o.append(txt(130, yb + 158, "+2.5 ms per burst at tp4 with 4 users (of a 7.9 ms pass)", size=12, fill=C["burst"]))
    o.append(txt(130, yb + 186, "readers afterwards: card staging = 64-line gather per row,", size=12))
    o.append(txt(130, yb + 204, "CPU tail = VNNI reader qk_group (64 lines per block)", size=12))
    o.append(txt(130, yb + 228, "who benefits: nobody, the card never reads the VNNI layout", size=12, fill=C["grey"]));
    o.append(box(580, yb, 460, 240, "#f0fdf4", C["fixS1"])); o.append(txt(590, yb + 20, "the policy (452b2052c9)", weight="bold", fill=C["fixS1"]))
    o.append(txt(590, yb + 44, "the operation is scored by the hardware attention", size=12))
    o.append(txt(590, yb + 62, "(cached_operation_uses_hw, decided once per model), so:", size=12))
    o.append(txt(590, yb + 80, "no row bits recorded, no block queued, no conversion", size=12))
    o.append(txt(590, yb + 98, "the block stays row-major: 4 whole cache lines per row", size=12))
    o.append(txt(590, yb + 122, "readers: card staging = the row in place (no copy),", size=12))
    o.append(txt(590, yb + 140, "CPU tail = row-major dotter (4 lines per key)", size=12))
    o.append(txt(590, yb + 164, "unchanged: whole-block prefill saves are VNNI at once,", size=12))
    o.append(txt(590, yb + 182, "so the AMX prefill path and its TTFT gain stay", size=12))
    o.append(txt(590, yb + 206, "accepted cost: a software-scored range under a hardware", size=12, fill=C["grey"]))
    o.append(txt(590, yb + 224, "operation uses the dotter, not the AMX kernel (see 4.3)", size=12, fill=C["grey"]))
    o.append(txt(130, yb + 246 - 0, "", size=12))
    o.append(txt(60, H - 12, "The dense AMX kernel never runs in steady FPGA decode at prompt 1024 (measured 0 dense-page visits with the PR 4596 counters).", size=12, fill=C["grey"]))
    o.append("</svg>"); return "".join(o)
# Diagram C: per-pass series, two small multiples
def diag_passes():
    W, H = 1100, 560
    o = [svg_open(W, H, "Decode pass duration per pass for base, fix and fixS1 at tp2 with 2 users and tp4 with 4 users: the fix spikes every 16th pass")]
    for k, (cell, title, ylo, yhi) in enumerate([("tp2__2u", "tp2, 2 users: pass duration, ms", 4.6, 6.2), ("tp4__4u", "tp4, 4 users: pass duration, ms", 5.4, 10.4)]):
        L, R, Tp, B = 70, 1040, 40 + k * 270, 40 + k * 270 + 200
        n = 37
        def x(i): return L + i / (n - 1) * (R - L)
        def y(v): return B - (v - ylo) / (yhi - ylo) * (B - Tp)
        o.append(txt(L, Tp - 14, title, weight="bold"))
        for tv in [ylo + (yhi - ylo) * f for f in (0, 0.25, 0.5, 0.75, 1)]:
            o.append(f'<line x1="{L}" y1="{y(tv):.1f}" x2="{R}" y2="{y(tv):.1f}" stroke="{C["line"]}"/>'); o.append(txt(L - 8, y(tv) + 4, f"{tv:.1f}", anchor="end", size=11, fill=C["grey"]))
        for i in range(0, n, 4): o.append(txt(x(i), B + 16, str(i), anchor="middle", size=11, fill=C["grey"]))
        o.append(txt((L + R) / 2, B + 32, "decode pass index (passes 10 and later of a 40-token run; a block completes at passes 14 and 30)", anchor="middle", size=11, fill=C["grey"]))
        for arm in ("base", "fix", "fixS1"):
            rows = passes[f"{arm}__{cell}"][:n]
            pts = " ".join(f"{x(i):.1f},{y(min(max(r['pass_ms'], ylo), yhi)):.1f}" for i, r in enumerate(rows))
            o.append(f'<polyline points="{pts}" fill="none" stroke="{C[arm]}" stroke-width="{2.4 if arm == "fixS1" else 1.8}"/>')
        for i in (14, 30):
            v = passes[f"fix__{cell}"][i]["pass_ms"]
            o.append(f'<circle cx="{x(i):.1f}" cy="{y(min(v, yhi)):.1f}" r="6" fill="none" stroke="{C["burst"]}" stroke-width="2"/>')
        b = passes[f"fix__{cell}"]
        o.append(txt(x(14) + 10, y(min(b[14]["pass_ms"], yhi)) - 8, f"conversion burst: fix {b[14]['pass_ms']:.2f} ms, fixS1 {passes['fixS1__' + cell][14]['pass_ms']:.2f} ms", size=11, fill=C["burst"]))
        lx = R - 330
        for j, arm in enumerate(("base", "fix", "fixS1")):
            o.append(f'<line x1="{lx + j * 110}" y1="{B - 10}" x2="{lx + j * 110 + 24}" y2="{B - 10}" stroke="{C[arm]}" stroke-width="3"/>'); o.append(txt(lx + j * 110 + 30, B - 6, arm, size=12))
    o.append("</svg>"); return "".join(o)
# Diagram D: dumbbells
def diag_dumbbell(metric, title, unit):
    rows = sorted(groups); W, LEFT, RIGHT, RH, TOP = 1100, 480, 240, 92, 44; H = TOP + RH * len(rows) + 40
    o = [svg_open(W, H, title)]
    for i, key in enumerate(rows):
        g = groups[key]; y = TOP + i * RH + RH / 2
        present = [(a, g[a]) for a in ("base", "fix", "fixS1") if a in g]
        vals = [g[a]["mean" if metric == "tps" else "ttft_mean"] for a, _ in present]
        lo, hi = min(vals), max(vals); span = max(hi - lo, 0.02 * hi); lo -= span * 0.6; hi += span * 0.6
        def x(v): return LEFT + (v - lo) / (hi - lo) * (W - LEFT - RIGHT)
        o.append(f'<line x1="{LEFT}" y1="{y + 22}" x2="{W - RIGHT}" y2="{y + 22}" stroke="{C["line"]}"/>')
        for tick in (lo + (hi - lo) * f for f in (0.0, 0.5, 1.0)): o.append(txt(x(tick), y + 36, f"{tick:.0f}", anchor="middle", size=11, fill=C["grey"]))
        o.append(txt(LEFT - 12, y - 8, cell_label(*key), anchor="end", size=12))
        xs = [x(v) for v in vals]
        o.append(f'<line x1="{min(xs):.1f}" y1="{y}" x2="{max(xs):.1f}" y2="{y}" stroke="#bbb" stroke-width="3"/>')
        for (a, v), xv in zip(present, xs): o.append(f'<circle cx="{xv:.1f}" cy="{y}" r="7" fill="{C[a]}"/>')
        for k, ((a, v), val) in enumerate(zip(present, vals)): o.append(txt(W - RIGHT + 16, y - 22 + 17 * k, f"{a} {val:.1f} {unit} (n = {v['n']})", fill=C[a], size=12))
        p = paired(g, "fixS1", "base", metric)
        if p: o.append(txt(LEFT - 12, y + 12, f"fixS1 vs base: {p['pct']:+.1f} % (paired t {p['t']:+.1f}, {'resolved' if p['resolved'] else 'not resolved'})", anchor="end", fill=C["fixS1"], size=12))
    lx = 40
    for a in ("base", "fix", "fixS1"): o.append(f'<circle cx="{lx + 6}" cy="{TOP - 28}" r="6" fill="{C[a]}"/>' + txt(lx + 16, TOP - 24, a, size=12)); lx += 80
    o.append(txt(lx + 10, TOP - 24, f"{title}; each row has its own axis", size=12, fill=C["grey"]))
    o.append("</svg>"); return "".join(o)
# Diagram E: latch release
def diag_latch():
    W, H = 1100, 370
    o = [svg_open(W, H, "The K/V latch: the main thread releases it once per layer, the attention workers wait on it with mwaitx; more parked workers make the release slower")]
    o.append(box(60, 110, 240, 70, C["soft"])); o.append(txt(180, 138, "main thread", anchor="middle", weight="bold")); o.append(txt(180, 160, "end of Save K / Save V", anchor="middle", size=12))
    o.append(box(440, 110, 220, 70, "#fef3c7")); o.append(txt(550, 138, "latch (one cache line)", anchor="middle", weight="bold")); o.append(txt(550, 160, "upstream_kvs_ready[slot]", anchor="middle", size=12))
    o.append(arrow(300, 145, 436, 145)); o.append(txt(368, 136, "count_down", anchor="middle", size=12)); o.append(txt(368, 165, "one atomic write", anchor="middle", size=11, fill=C["grey"]))
    for i in range(6):
        yy = 30 + i * 38
        o.append(box(820, yy, 220, 30, "#eef2ff")); o.append(txt(930, yy + 20, f"attention worker {i + 1 if i < 5 else '... 20+'}", anchor="middle", size=12))
        o.append(arrow(816, yy + 15, 664, 145, dash=True))
    o.append(txt(700, 20, "wait() = mwaitx on the latch line", size=12, fill=C["grey"]))
    o.append(txt(60, 290, "measured (perf, 6 s of decode, runtron tp2 with 2 users): the policy build's main thread spends 0.91 % of its own samples in count_down;", size=12))
    o.append(txt(60, 308, "the canonical build's main thread spends less than 0.015 % there. 0.91 % of a 5.2 ms pass is about 47 us, the size of the Save K gap.", size=12))
    o.append(txt(60, 332, "why more waiters: the policy build's workers finish their ready sections sooner (141 vs 171 us per worker and pass), so more of them are parked when main releases.", size=12, fill=C["grey"]))
    o.append(txt(60, 354, "the K store itself is not the gap: its symbols are about 0.03 % of the main thread's samples in both builds.", size=12, fill=C["grey"]))
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
    h = [f"<table><tr><th>cell</th><th>a</th><th>b</th><th>n</th><th>{unit}</th><th>%</th><th>paired t</th><th>resolved</th></tr>"]
    for key in sorted(groups):
        for a, b in (("fixS1", "base"), ("fix", "base"), ("fixS1", "fix"), ("basekill", "base"), ("fixS1kill", "fixS1")):
            p = paired(groups[key], a, b, metric)
            if p: h.append(f"<tr><td>{esc(cell_label(*key))}</td><td>{a}</td><td>{b}</td><td>{p['n']}</td><td>{p['mean']:+.3f} (sd {p['sd']:.3f})</td><td>{p['pct']:+.2f}</td><td>{p['t']:+.2f}</td><td>{'yes' if p['resolved'] else 'no'}</td></tr>")
    return "\n".join(h) + "</table>"
def trace_table():
    h = ["<table><tr><th>arm, cell</th><th>decode passes</th><th>pass ms (mean)</th><th>Save K on main, us per pass</th><th>Save V on main, us per pass</th><th>largest end gap, us</th></tr>"]
    for cell in ("tp2__2u", "tp4__4u"):
        for arm in ("base", "fix", "fixS1"):
            rows = passes[f"{arm}__{cell}"]
            h.append(f"<tr><td>{arm}, {cell.replace('__', ' ').replace('u', ' users')}</td><td>{len(rows)}</td><td>{pmean(arm, cell, 'pass_ms'):.3f}</td><td>{pmean(arm, cell, 'save_k_us'):.0f}</td><td>{pmean(arm, cell, 'save_v_us'):.0f}</td><td>{max(r['end_gap_us'] for r in rows):.0f}</td></tr>")
    return "\n".join(h) + "</table>"
def pre(path, n=40):
    if not os.path.exists(path): return "<p>(not available)</p>"
    return "<pre>" + esc("\n".join(open(path, errors="replace").read().splitlines()[-n:])) + "</pre>"
def req_row(key):
    g = groups[key]; pt = paired(g, "fixS1", "base", "tps"); pf = paired(g, "fixS1", "base", "ttft")
    def w(p, sign):
        s = f"{p['pct']:+.2f} % (paired t {p['t']:+.1f}, n = {p['n']})"
        if not p["resolved"]: return s + ": not resolved, so not worse"
        return s + (": better" if p["pct"] * sign > 0 else ": worse")
    tw, fw = w(pt, +1), w(pf, -1)
    if "worse" in fw and ": not" not in fw: verdict = f"TPS better; TTFT worse by {pf['mean']:+.0f} ms on {g['base']['ttft_mean'] / 1000:.1f} s: the strict reading fails, the size is jhan's call"
    elif pt["resolved"] or pf["resolved"]: verdict = "met (one better, the other not worse)"
    else: verdict = "not worse on both, neither resolved"
    return f"<tr><td>{esc(cell_label(*key))}</td><td>{esc(tw)}</td><td>{esc(fw)}</td><td>{esc(verdict)}</td></tr>"
perf_done = os.path.exists(os.path.join(RESC, "perf", "perf.done"))
page = f"""<title>Issue 4500 Round Two</title>
<style>
/* layout: one reading column, figures at full column width, tables scroll in their own box */
:root{{--bg:#fbfbf9;--fg:#1f2937;--muted:#6b7280;--line:#d6d9de;--soft:#f3f5f8;--accent:#1f9d55;--warn:#b45309;color-scheme:light}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.5;margin:0;padding-block:24px;padding-inline:16px}}
main{{max-width:1060px;margin:0 auto}}
h1{{font-size:26px;line-height:1.25;text-wrap:balance;margin:0 0 12px}}h2{{font-size:20px;margin:36px 0 10px;text-wrap:balance}}h3{{font-size:16px;margin:22px 0 6px}}
p,li{{max-width:78ch}}
.short{{background:#eef6ff;border-left:4px solid #2a78d6;padding:10px 14px}}.note{{background:#fff8e6;border-left:4px solid #e0a800;padding:8px 12px}}
table{{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}}th,td{{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}}th{{background:var(--soft)}}
.tbl{{overflow-x:auto;max-width:100%}}pre{{background:var(--soft);padding:8px;overflow-x:auto;font-size:12px}}
figure{{margin:16px 0;overflow-x:auto;max-width:100%}}figure svg{{height:auto}}figcaption{{font-size:13px;color:var(--muted);max-width:90ch;margin-top:6px}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;font-size:14px}}dt{{font-weight:600}}dd{{margin:0;max-width:78ch}}
@media (max-width:600px){{dl{{grid-template-columns:1fr}}}}
</style>
<main>
<h1>Issue #4500, round two: the VNNI K layout no longer loses on qwen-3-4b under FPGA attention</h1>
<p class="short"><b>Short version.</b> The qwen-3-4b decode loss that remained after the 09-29 fix came from a conversion the FPGA never benefits from: at the end of every 16th decode step the main thread rewrote every completed K block of every layer and KV head into the AMX layout. Commit 452b2052c9 stops that conversion for KV slots the FPGA scores, and the policy build now measures {pv(G2, 'fixS1', 'base', 'tps')} TPS at tp2 with 2 users and {pv(G4, 'fixS1', 'base', 'tps')} at tp4 with 4 users against the canonical AMX build, with TTFT {pv(G4, 'fixS1', 'base', 'ttft')} at tp4. llama-3.1-8b keeps its {pv(GL, 'fixS1', 'base', 'tps')} TPS gain, with a 46 ms (0.34 %) TTFT increase on a 13.4 s TTFT that is resolved and is jhan's call.</p>
<p>Generated 2026-09-30 from exec/results/i4500b-20260930 and exec/results/i4500c-20260930 by exec/i4500b-20260930/gen_round2.py. Every number on this page is a measurement unless it is marked "est.".</p>

<h2>Words used here</h2>
<dl>
<dt>tron, runtron, rinzler</dt><dd>The inference program under test, its command-line tool, and the production server built from it.</dd>
<dt>AMX</dt><dd>Intel Advanced Matrix Extensions, the CPU's matrix (tile) instructions. The AMX attention kernel scores a dense page (all 64 keys of a page) with them.</dd>
<dt>VNNI K, the VNNI layout</dt><dd>The K cache layout of PR #4424: a 16-token block of one KV head is stored as the AMX operand (one 4-byte pair of a token in each of 64 cache lines) instead of one 256-byte row per token.</dd>
<dt>row-major</dt><dd>One K row of a token as 256 contiguous bytes (4 cache lines of 64 bytes).</dd>
<dt>canonical AMX, base</dt><dd>main 3faba6d0fd with the AMX kernels compiled into the package and row-major K. The arm every result is compared with.</dd>
<dt>the fix</dt><dd>The 09-29 change (f34b0fe2ec, package 98a5accb8b): a 16-token block stays row-major until its 16th row is saved, then the main thread converts it in place at the end of the forward pass.</dd>
<dt>the policy, fixS1</dt><dd>Commit 452b2052c9 (package 2fd11e32ca): the fix plus this round's change, described in section 4.</dd>
<dt>FPGA attention, CPU attention</dt><dd>Attention scored on the Positron card (the default for the ingested qwen model) or on the CPU's attention worker threads (USE_HW_ATTN=0, the mode of the hand-written llama plugin).</dd>
<dt>GOF, DMA, staging</dt><dd>A group of four consecutive tokens whose K and V rows the CPU copies (stages) into a buffer that DMA (direct memory access) moves to the card. A GOF is "DMA-complete" once the card holds it for every layer.</dd>
<dt>the tail</dt><dd>The keys above the last DMA-complete GOF, which the CPU scores itself.</dd>
<dt>engagement point</dt><dd>hw_attn_engagement_point(), 127 by default: the first query position the card may score.</dd>
<dt>KV slot, KV head, layer</dt><dd>One K and V store of the cache (one per layer here), one of the 8 key/value heads of qwen-3-4b, and one of its 36 transformer layers.</dd>
<dt>decode step, pass, forward</dt><dd>One forward pass that produces one token per user.</dd>
<dt>main thread, attention workers</dt><dd>The thread that runs the model's statements (it saves K and V), and the pool threads that score attention.</dd>
<dt>kill switch</dt><dd>TRON_AMX_DISABLE=1: the AMX tile bracket, the Q packing and the dense kernel are off; the K layout stays.</dd>
<dt>TPS, TTFT</dt><dd>Decode tokens per second per user (the nightly's client captures it between generated tokens 896 and 1024 of 1536, over 10 rounds), and time to first token in ms.</dd>
<dt>paired t, resolved</dt><dd>The mean of the per-repetition differences divided by its standard error. Resolved = the absolute t is at least the two-sided 95 % threshold (4.30 at n = 3, 3.18 at n = 4). Not resolved = the difference is inside the run-to-run spread.</dd>
<dt>tp2, tp4, users per engine</dt><dd>The model split over 2 or 4 cards, and the number of client streams one engine serves.</dd>
<dt>cell, arm, repetition</dt><dd>One test configuration (model, split, users, prompt length), one binary plus environment, one run of the cell with that arm.</dd>
</dl>

<h2>1. The requirement and the verdict</h2>
<p>jhan asked on 2026-09-30 that the VNNI K layout deliver better TPS and TTFT than canonical AMX on llama-8b tp2 and on qwen3-4b tp2 and tp4. Failing both, one metric must be better and the other not worse.</p>
<div class="tbl"><table><tr><th>cell</th><th>TPS, policy vs canonical</th><th>TTFT, policy vs canonical</th><th>verdict</th></tr>
{req_row(("llama-8b", 2, 8, 4096))}{req_row(("qwen3-4b", 2, 2, 1024))}{req_row(("qwen3-4b", 4, 4, 1024))}</table></div>
<p>The cells are the nightly's own loads. Four repetitions per arm, arms interleaved, one engine on our half of delphi-3bda, the nightly's own client. Section 5 has the numbers.</p>

<h2>2. Where the remaining loss came from</h2>
<p>The 09-29 fix left qwen-3-4b at -2.3 % TPS (tp2) and -8.8 % (tp4) against canonical, both unresolved at 3 repetitions. A 25-agent code reading of the branch and of main, with every fact checked by two more agents, established the following.</p>
<h3>2.1 Under FPGA attention the CPU scores only the tail</h3>
{figure(diag_keys(), "Figure 1. One decode step of one user under FPGA attention. The card scores every key of the DMA-complete GOFs. The CPU's software loop visits those pages but jumps over their range without reading a K byte. The CPU scores only the tail, one to four keys, which lie in the current 16-token block.")}
<p>The earlier report named the pages at positions 64 to 126 as a cost the CPU pays on every step. The code refutes that. The engagement point gates query positions and the card's first DMA prefix, never key positions [src/tron/models/ranged_mask.cpp:42-90; h/tron/scheduler/full.hpp:2761-2815]. The tail measured 2.5 keys per job on average at prompt 1024 with the PR 4596 counters [exec/results/attnstats-20260925-fpga/exit-reports.txt:37-42].</p>
<p>The dense AMX kernel never ran in steady FPGA decode at prompt 1024, and ran 0 times in that prompt's prefill [same file, lines 15-20 and 37-42]. So the VNNI layout brings the FPGA-attention decode nothing. It can only cost.</p>
<h3>2.2 What the fix build still did per step</h3>
{figure(diag_block(), "Figure 2. The life of one 16-token K block in decode. Left: the 09-29 fix converts the completed block at the forward end, in series on the main thread, for every layer and KV head. Right: the policy leaves it row-major. Both keep the whole-block prefill saves in the VNNI layout.")}
<p>Three differences to canonical remained in the fix build per decode step, all on the main thread [h/tron/models/model.hpp:3080-3096, 2818-2825; kv_cache.hpp:1843-1866]:</p>
<ul>
<li>The forward-end conversion: every 16th step per user, 36 layers x 8 KV heads = 288 blocks per user, 8 KiB of plane traffic plus an 8 KiB stack round trip each, in series after the workers have joined.</li>
<li>The staging gather: whenever a converted block is copied to the card again, each row costs 64 cache lines instead of 4.</li>
<li>Row bookkeeping in the K save: one atomic per row per layer, and four page lookups per token where canonical does one.</li>
</ul>
<p>One trap was found on the way. main 3faba6d0fd carries PR #4191 (it skips whole card-covered pages in the software loop), and the PR branch does not. The rinzler packages of every arm contain main 3faba6d0fd, so the cells compare like with like. The runtron traces of section 6 use main c7844ca2ce, the branch's merge base, as their canonical arm for the same reason.</p>

<h2>3. The trace evidence</h2>
{figure(diag_passes(), "Figure 3. Duration of each decode pass in the runtron traces (prompt 1024, 40 generated tokens, decode passes 10 and later). The fix (orange) spikes at passes 14 and 30, where a 16-token block completes and the forward end converts it. The policy (green) does not. Tracing itself costs about 9 % of a step, so compare the three lines with each other, not with the cells.")}
<div class="tbl">{trace_table()}</div>
<p>The burst is the gap from the last Save V to the end of the pass. In the fix trace it rises from about 450 us to 1130 us at tp2 with 2 users, and from about 1000 us to 3800 us at tp4 with 4 users, at passes 14 and 30 [traces/passes.json]. The policy trace shows no such rise. The Save K span stays about twice canonical's in both VNNI builds; section 7 explains that.</p>

<h2>4. What the policy commit changes</h2>
<h3>4.1 The rule</h3>
<p>When the hardware attention scores an operation's K (cached_operation_uses_hw, decided once per model from the model's configuration), save_k records no row bits for the rows a short run stores and queues no block for the forward-end conversion [h/tron/models/model.hpp:3080-3096]. Such a block stays row-major for the life of the page. No bit is ever set for it, so a page copy does not convert it either.</p>
<h3>4.2 What else changed</h3>
<ul>
<li>The FPGA staging reads a row of a row-major block in place instead of copying it into a scratch buffer [h/tron/scheduler/full.hpp:2648-2662; kv_cache.hpp k_row_if_row_major].</li>
<li>k_forget_row skips its two locked read-modify-writes per storage slot when no bit at or above the offset is set, the plain decode append [kv_cache.hpp k_forget_row].</li>
<li>convert_pending_k_blocks gets a Perfetto span (convert_k_blocks) with the queue length.</li>
<li>Note [Row-major blocks under hardware attention] in kv_cache.hpp carries the design, and six older comments that described every completed block as queued were corrected.</li>
<li>t_llama_unit's save_k case gains two sections: with the saving operation flagged as hardware-scored, the rows land the same way and the short-run block stays row-major after convert_pending_k_blocks; with another operation flagged, the block still converts.</li>
</ul>
<p>Two adversarial review passes (60 and 18 agents) found no blocker. Their wording and test findings are applied. A second commit that rewrote the row store was dropped: the review showed the production K buffer is bf16, so the store was already one memcpy.</p>
<h3>4.3 The accepted limitation</h3>
<p class="note">The policy is static per operation. A range that the software scores although the operation is a hardware one (before the engagement point, a prompt shorter than 128 tokens, a shard without HBM memory, USE_HW_ATTN=N raising the engagement point) scores the blocks decode completed with the row-major dotter, where the 09-29 fix let the AMX kernel score a page of them. Tokens are identical either way, because every reader takes the layout from the block bit. The nightly's cells do not reach these states.</p>

<h2>5. The measurements</h2>
{figure(diag_dumbbell("tps", "decode TPS per user, higher is better", "TPS"), "Figure 4. Decode TPS per cell and arm, mean over the repetitions. The green annotation is the policy build against canonical.")}
{figure(diag_dumbbell("ttft", "time to first token, lower is better", "ms"), "Figure 5. TTFT per cell and arm. The TTFT spread today (16 to 32 ms between paired runs) is larger than on 09-29 (2 to 7 ms), so the tp2 pair is not resolved.")}
<h3>5.1 Cells</h3>
<div class="tbl">{cells_table()}</div>
<h3>5.2 Paired differences, TPS</h3>
<div class="tbl">{pairs_table("tps")}</div>
<h3>5.3 Paired differences, TTFT</h3>
<div class="tbl">{pairs_table("ttft")}</div>
<p>The kill-switch arms at tp4 say whether the per-section AMX tile bracket and Q packing cost anything when no dense page is scored. Both differences are inside the tp4 spread. The tp4 cell had one slow canonical repetition (sd 13.5 TPS), the bimodal state seen on earlier days.</p>
<h3>5.4 Tokens and tests</h3>
<p>Greedy runtron smoke (one user, temperature 0, pay-for-determinism, 128 tokens, prompts 1024 and 1000, CPU and FPGA attention): the policy binary's tokens equal its own repeat run and equal the fix binary's in all four cells. Under FPGA attention the same K bytes reach the card; under CPU attention the policy is off.</p>
{pre(os.path.join(RES, "smoke", "smoke.txt"), 12)}
<p>Unit tests with the fake device at 452b2052c9: 5 of 5 binaries pass in the VNNI build and 3 of 3 in the row-major build.</p>
{pre(os.path.join(RES, "tests-fixS1.txt"))}{pre(os.path.join(RES, "tests-fixS1rm.txt"))}

<h2>6. Method</h2>
<ul>
<li>Chain exec/i4500b-20260930 (README there), launched 05:28 UTC with a 13:00 UTC gate, ran after the nightly: builds and tests (10 min), the policy package (13 min), the smoke, the traces, 40 rinzler cells (13:44 to 16:44 UTC), the row-major build tests. Production serving was taken down through platformd only when idle and brought back at the end.</li>
<li>Arms: base = /var/tmp/jhan/canon-ci-20260918/root; fix = /var/tmp/jhan/i4500fix-20260928/root (98a5accb8b); fixS1 = /var/tmp/jhan/i4500b-20260930/root (2fd11e32ca); basekill and fixS1kill = the same with TRON_AMX_DISABLE=1, at tp4 only.</li>
<li>Client: systems_test testlib/tps.py through st_perf2.py (sharegpt prompts of the given length, 1536 generated tokens, 10 rounds). Repetitions interleaved, odd ones forward and even ones reversed.</li>
<li>Traces: runtron with --trace-gen, categories model, scheduler and hwattention, passes 10 and later of a 40-token run, analysed with the Perfetto trace processor (traces/passes.json).</li>
</ul>

<h2>7. The Save K gap, explained by perf</h2>
{figure(diag_latch(), "Figure 6. The K/V latch. The main thread releases it once per layer at the end of Save K and Save V; the attention workers wait on it with mwaitx. The policy build's workers arrive sooner, so more of them are parked on the line when main writes it, and the write is what perf sees.")}
<p>The main thread's Save K span was about twice canonical's in both VNNI builds (section 3). Two runtron profiles (perf record, 6 s of decode each, 391 k samples, exec/results/i4500c-20260930/perf) attribute it. The K store symbols are about 0.03 % of the model thread's samples in both builds. The policy build's model thread spends 0.91 % of its own samples in latch_ref::count_down, the release of the K/V latch [h/tron/threading.hpp:109-135; model.hpp:3124, 3193]. The canonical build's model thread spends less than 0.015 % there. perf report was run with a thread filter, so these shares are of that thread's own samples. 0.91 % of a 5.2 ms pass is about 47 us (est. from the sample share), the size of the Save K gap.</p>
<p>The workers wait on that latch with mwaitx [h/tron/models/self_attention.hpp:784]. The policy build's workers reach the wait sooner: their ready sections take 141 us per worker and pass against 171 us in canonical, in the traces of section 3 [traces/analysis.md]. So the release finds more cores parked on the line. This is a property of the many-waiter latch, not of the K store, and a remedy (a release that does not wake every core at once, or one latch line per worker) belongs to the threading code. It costs about 0.9 % of a tp2 step and is on the main thread's serial path under the late launch at 2 users.</p>

<h2>8. Open items</h2>
<ul>
<li>llama-8b TTFT: +46 ms on 13.4 s, resolved at n = 4. The PR head showed +23 ms and the 09-29 fix +47 ms on 09-29, so it is a property of the VNNI prefill store in the hand-written llama plugin, not of this commit. Candidate: the whole-block VNNI store (16 rows transposed in registers) runs on the main thread alone there, without the shared block save of generated plugins. Measure: Save K spans of a llama prefill trace, canonical against the policy build.</li>
<li>The latch release (section 7): a threading change, measurable with the same perf recipe.</li>
<li>The static policy (section 4.3): a per-range or lazy conversion would recover the AMX kernel in the software-fallback states.</li>
<li>Rebase the branch onto main past PR #4191 before the PR update. The packages already contain it.</li>
<li>Tests: no unit test instantiates store_k_block with a bf16 K buffer (the production type), and the "row re-saved into a converted block" arm is untested through store_k_block.</li>
<li>Not part of the PR: TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 (early card launch at 2 users) gave +7.7 % TPS on canonical and +11 % on the VNNI build at tp2 on 09-19. A product default to discuss on its own.</li>
<li>The branch jhan-amx-vnniK-i4500 is local, PR #4424 is untouched, and issue #4500 has no comment. Push, PR text and the issue comment are jhan's decisions.</li>
</ul>

<h2>9. Where the data is</h2>
<p>Results: exec/results/i4500b-20260930 (summary.md and summary.json, cells/ with 40 folders, smoke/, traces/ with the six Perfetto traces, analysis.md and passes.json, tests-fixS1*.txt, tests-fixS1rm.txt) and exec/results/i4500c-20260930/perf (perf reports and per-thread counters). Scripts: exec/i4500b-20260930 (chain.sh, campaign.sh, smoke.sh, traces.sh, summarize.py, trace_analyze.py, gen_report.py, gen_round2.py) and exec/i4500c-20260930 (perf.sh). Logs: exec/logs/i4500b-20260930*.log and i4500c-20260930*.log. Worktrees: VNNIed-K-in-place/tron-i4500 (branch head 452b2052c9) and ~/workspace/ai-runs/tron-i4500-deb (2fd11e32ca). The 09-29 data page of this round's cells is issue4500/policy-4500.html.</p>
</main>"""
assert all(ord(ch) < 128 for ch in page), "non-ASCII in page"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write(page)
print("wrote", OUT, len(page), "bytes")
