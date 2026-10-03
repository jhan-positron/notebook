#!/usr/bin/env python3
"""Build VNNIed-K-in-place/issue4500/fix-results.html from the i4500fix-20260928 results: the cells (summary.json),
the smoke token rows (smoke/smoke.txt), the unit-test results (tests-fix.txt, tests-fixrm.txt) and the deb manifest.
Light theme, ASCII only, inline SVG dumbbell chart (one row per cell, one dot per binary, gap fix vs vnni annotated).
Usage: gen_report.py [RES_DIR] [OUT_HTML]"""
import glob, html, json, os, re, sys
RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/i4500fix-20260928"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4500/fix-results.html"
ARMS = [("base", "canonical AMX (row-major K)", "#2a78d6"), ("vnni", "PR 4424 (VNNI K, the loss)", "#eb6834"),
        ("fix", "PR 4424 + fix", "#1f9d55"), ("nightly", "installed nightly", "#8a8a8a")]
def esc(x): return html.escape(str(x))
summary = json.load(open(os.path.join(RES, "summary.json"))) if os.path.exists(os.path.join(RES, "summary.json")) else {"cells": {}, "pairs": []}
cells, pairs = summary["cells"], summary["pairs"]
groups = {}
for key, reps in cells.items():
    model, tp, users, prompt, arm = key.split("__")
    g = groups.setdefault((model, int(tp), int(users), int(prompt)), {})
    tps = [r["tps"] for r in reps.values()]
    g[arm] = {"mean": sum(tps) / len(tps), "n": len(tps), "min": min(tps), "max": max(tps),
              "ttft": sum(r["ttft"] for r in reps.values()) / len(reps), "amx": [r.get("amx") for r in reps.values()]}
def pair(model, tp, users, prompt, a, b):
    for p in pairs:
        if (p["model"], p["tp"], p["users"], p["prompt"], p["a"], p["b"]) == (model, tp, users, prompt, a, b): return p
    return None
def cell_label(model, tp, users, prompt):
    name = {"qwen3-4b": "qwen-3-4b", "llama-8b": "llama-3.1-8b"}.get(model, model)
    attn = "FPGA attention" if model.startswith("qwen") else "CPU attention"
    return f"{name} tp{tp}, {users} users per engine, prompt {prompt} ({attn})"
# ---- dumbbell chart ----
def chart():
    rows = sorted(groups)
    if not rows: return "<p>No cells yet.</p>"
    W, LEFT, RIGHT, RH, TOP = 1240, 500, 250, 84, 44  # RIGHT holds the value column
    H = TOP + RH * len(rows) + 50
    allv = [v["mean"] for g in groups.values() for v in g.values()]
    lo, hi = min(allv), max(allv); span = max(hi - lo, 1.0); lo -= span * 0.12; hi += span * 0.12
    def x(v): return LEFT + (v - lo) / (hi - lo) * (W - LEFT - RIGHT)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font-family:system-ui,sans-serif;font-size:13px">']
    out.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    step = 10 if span > 40 else 5 if span > 15 else 2
    t = int(lo // step) * step
    while t <= hi:
        if t >= lo:
            out.append(f'<line x1="{x(t):.1f}" y1="{TOP - 8}" x2="{x(t):.1f}" y2="{H - 40}" stroke="#e8e8e8"/>')
            out.append(f'<text x="{x(t):.1f}" y="{H - 22}" text-anchor="middle" fill="#666">{t}</text>')
        t += step
    out.append(f'<text x="{(LEFT + W - RIGHT) / 2:.0f}" y="{H - 6}" text-anchor="middle" fill="#444">decode TPS per user (higher is better)</text>')
    for i, key in enumerate(rows):
        g = groups[key]; y = TOP + i * RH + RH / 2
        out.append(f'<text x="{LEFT - 12}" y="{y - 6}" text-anchor="end" fill="#222">{esc(cell_label(*key))}</text>')
        present = [(a, g[a]) for a, _, _ in ARMS if a in g]
        if present:
            xs = [x(v["mean"]) for _, v in present]
            out.append(f'<line x1="{min(xs):.1f}" y1="{y:.1f}" x2="{max(xs):.1f}" y2="{y:.1f}" stroke="#bbb" stroke-width="3"/>')
        # Dots, and the values as a column at the right (dots may sit within a
        # few pixels of each other, so labels next to the dots would overlap).
        for a, v in present:
            col = next(c for aa, _, c in ARMS if aa == a)
            out.append(f'<circle cx="{x(v["mean"]):.1f}" cy="{y:.1f}" r="7" fill="{col}"/>')
        for k, (a, v) in enumerate(present):
            col = next(c for aa, _, c in ARMS if aa == a)
            out.append(f'<text x="{W - RIGHT + 16}" y="{y - 27 + 18 * k:.0f}" fill="{col}">{a} {v["mean"]:.1f}</text>')
        p = pair(key[0], key[1], key[2], key[3], "fix", "vnni")
        if p:
            tt = "n.r." if p["t"] is None or abs(p["t"]) < (12.71 if p["n"] == 2 else 4.30 if p["n"] == 3 else 2.78) else "resolved"
            out.append(f'<text x="{LEFT - 12}" y="{y + 14}" text-anchor="end" fill="#1f9d55">fix vs PR 4424: {p["delta_tps_pct"]:+.1f} % TPS ({p["delta_ms"]:+.3f} ms per step, paired t {p["t"]:+.1f}, {tt})</text>' if p["t"] is not None else
                       f'<text x="{LEFT - 12}" y="{y + 14}" text-anchor="end" fill="#1f9d55">fix vs PR 4424: {p["delta_tps_pct"]:+.1f} % TPS (n = {p["n"]})</text>')
    lx = 40
    for a, label, col in ARMS:
        out.append(f'<circle cx="{lx + 6}" cy="{TOP - 28}" r="6" fill="{col}"/><text x="{lx + 16}" y="{TOP - 24}" fill="#333">{a} = {esc(label)}</text>')
        lx += 300
    out.append("</svg>")
    return "\n".join(out)
# ---- tables ----
def cells_table():
    h = ["<table><tr><th>cell</th><th>binary</th><th>n</th><th>TPS mean</th><th>min / max over reps</th><th>TTFT ms</th><th>AMX-busy cycles per rep (20 s)</th></tr>"]
    for key in sorted(groups):
        g = groups[key]
        for a, label, _ in ARMS:
            if a not in g: continue
            v = g[a]
            h.append(f"<tr><td>{esc(cell_label(*key))}</td><td>{a} = {esc(label)}</td><td>{v['n']}</td><td>{v['mean']:.2f}</td><td>{v['min']:.2f} / {v['max']:.2f}</td><td>{v['ttft']:.0f}</td><td>{esc('/'.join(str(x) for x in v['amx']))}</td></tr>")
    h.append("</table>")
    return "\n".join(h)
def pairs_table():
    h = ["<table><tr><th>cell</th><th>a</th><th>b</th><th>n</th><th>a minus b, ms per step</th><th>TPS %</th><th>paired t</th></tr>"]
    for p in pairs:
        t_text = "-" if p["t"] is None else f"{p['t']:+.2f}"
        h.append(f"<tr><td>{esc(cell_label(p['model'], p['tp'], p['users'], p['prompt']))}</td><td>{p['a']}</td><td>{p['b']}</td><td>{p['n']}</td><td>{p['delta_ms']:+.3f} (sd {p['sd_ms']:.3f})</td><td>{p['delta_tps_pct']:+.2f}</td><td>{t_text}</td></tr>")
    h.append("</table>")
    return "\n".join(h)
def pre(path, n=60):
    if not os.path.exists(path): return "<p>(not available yet)</p>"
    lines = open(path, errors="replace").read().splitlines()[-n:]
    return "<pre>" + esc("\n".join(lines)) + "</pre>"
manifest = json.load(open(os.path.join(RES, "manifest.json"))) if os.path.exists(os.path.join(RES, "manifest.json")) else {}
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Issue 4500 fix results</title>
<style>:root{{color-scheme:light}}body{{background:#fff;color:#222;font-family:system-ui,sans-serif;max-width:1040px;margin:24px auto;padding:0 16px;line-height:1.45}}
table{{border-collapse:collapse;font-size:14px}}th,td{{border:1px solid #ddd;padding:4px 8px;text-align:left}}th{{background:#f4f4f4}}pre{{background:#f6f6f6;padding:8px;overflow-x:auto;font-size:12px}}h2{{margin-top:32px}}.short{{background:#eef6ff;padding:10px 14px;border-left:4px solid #2a78d6}}</style></head><body>
<h1>Issue #4500 fix: row-major tail block for the VNNI K layout, measured</h1>
<p class="short"><b>Short version.</b> The fix recovers little of the issue 4500 loss. qwen-3-4b with FPGA attention: PR 4424 loses 3.8 % TPS at tp2 (2 users per engine) and 11.8 % at tp4 (4 users) against the canonical AMX build; with the fix the losses are 2.3 % and 8.8 %, and the fix-vs-PR differences (+1.5 % and +3.4 %) are not resolved at 3 repetitions. llama-3.1-8b with CPU attention (tp2, 8 users per engine, prompt 4096) is unchanged by the fix (-0.4 %, not resolved; both builds +8.5 to +8.9 % over the canonical build). Token rows of the fix equal its own repeat run in every smoke; under FPGA attention they also equal the PR head's.</p>
<p><b>What this says about the root cause.</b> The row-major tail block removes the three 64-line accesses of decode that the root-cause page named (the main-thread scatter store, the workers' tail read, the staging gather), and the smoke shows the new code path is active (the CPU-attention token rows of the fix differ from the PR head's from token 52 and 6 on, as the tail-block scores now take the row-major dotter's fp32 add order). Yet most of the loss stays. So the exposed cost of the VNNI layout in FPGA decode is not, or not mainly, the per-token access pattern of the incomplete block. Candidates that the fix does not touch: the AVX-512 reader k_vnni::qk_group on the engagement-prefix page (positions 64..126 are scored by the CPU on every step, in converted blocks), the per-step AMX path work that the kill switch removed at tp4 in the 09-19 campaign (+6.8 % TPS), and the forward-end conversions (est. 0.05 ms per step at 2 users, not measured). The m2 launch-phase result of 09-19 (+0.58 ms per step more loss with the late launch) still stands as the strongest lever: TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 gave +6.2 % over the shipped package on the tp2 cell.</p>
<p><b>Repetition 2 of the tp4 cell</b> is the known bimodal state of that cell (fix 127.0 and PR 118.4 TPS against 148 to 154 in the other repetitions; the canonical and nightly builds did not show it); the tp4 means and the paired t carry that spread.</p>
<p><b>Nightly reference.</b> The installed nightly package (main of 2026-09-28, canonical AMX) is 12.9 % faster than the 09-18 canonical build at tp4 and equal at tp2 and on llama; the tp4 gain of main since 09-23 is a separate open item (memory: ci-amx-row-20260923). All four binaries were measured in the same session, interleaved.</p>
<p><b>Unit tests.</b> The chain's builds ran 5 test binaries with the fake device: two failed in the VNNI build and one in the row-major build. Causes: the new EAGLE-view layout test built its book without the x storage an EAGLE slot needs (test setup); the apply-and-join test scores a page of a book with no active KV slot under a window that excludes every token, and the new software loop read the page's layout state before the token loop (a reader defect: the state is now fetched at the first relevant token, commit f34b0fe2ec, no effect on the measured decode paths). A third rerun exposed a data-dependent tolerance miss on one weighted-V element (scores matched the reference to 1e-5, one v_star element was 0.016 off on 0.25, the same with the AMX kernels off): the VNNI build's unconverted rows live at other plane bytes than the row-major build's rows, so the two builds scored different random K instances; the test now stores the row-major rows first, both builds score one instance, and every test passes in both builds at f34b0fe2ec (section 5, rerun). The miss on the other instance is consistent with the bf16 truncation of the softmax weights in scaled_v (issue #4600) on a large V value; not proven.</p>
<p>Words used here: tron = the inference program under test; rinzler = the production server; runtron = tron's command-line tool; TPS = decode tokens per second per user, captured by the nightly's own client between generated tokens 896 and 1024 of 1536 (10 rounds); step ms = 1000 / TPS; paired t = the mean of the per-repetition differences divided by its standard error (thresholds 12.71 at n = 2, 4.30 at n = 3; "n.r." = not resolved); VNNI K = the K cache layout of PR 4424; the fix = commit 78582b7ba3 (row-major 16-token tail block, converted in place at the forward end); AMX-busy = cycles of the EXE.AMX_BUSY counter on the engine during 20 s of the benchmark (0 = no AMX kernel ran).</p>
<h2>1. The chart</h2>
{chart()}
<p>Every dot is the mean over the repetitions; the cell table gives min and max. Durations of the harness runs are in the cells' perf-e0.log files.</p>
<h2>2. Cells</h2>
{cells_table()}
<h2>3. Paired differences</h2>
{pairs_table()}
<h2>4. Token smoke (runtron, one user, temperature 0)</h2>
<p>fix vs fix2 must be identical (the A/A control). fix vs vnni may differ at a bf16 tie: the tail-block scores of the fix take the row-major dotter's fp32 add order, the PR head's take qk_group's.</p>
{pre(os.path.join(RES, "smoke", "smoke.txt"), 80)}
<h2>5. Unit tests (fake device, our half of delphi-3bda)</h2>
<p>VNNI build (TRON_K_VNNI on), chain run:</p>{pre(os.path.join(RES, "tests-fix.txt"))}
<p>Row-major build (TRON_K_VNNI off), chain run:</p>{pre(os.path.join(RES, "tests-fixrm.txt"))}
<p>Rerun after the test fixes (VNNI build, then row-major):</p>{pre(os.path.join(RES, "tests-retest.txt"))}{pre(os.path.join(RES, "tests-retestrm.txt"))}
<h2>6. Binaries</h2>
<pre>{esc(json.dumps(manifest, indent=1))}</pre>
<p>base = /var/tmp/jhan/canon-ci-20260918 (main 3faba6d0fd + AMX in the deb preset); vnni = /var/tmp/jhan/ci-mimic-20260918 (main 3faba6d0fd + PR 4424 head 30c4ac82cb); fix = the same plus commits 78e2da7511, 78582b7ba3 and 617cb8333f (the measured package 98a5accb8b); the branch head after the test fixes is f34b0fe2ec; nightly = /opt/positron/bin/rinzler at campaign start (results/nightly.sha).</p>
<h2>7. Chain log tail</h2>
{pre('/home/jhan/workspace/intel-AMX/exec/logs/i4500fix-20260928-chain.log', 40)}
</body></html>"""
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write(page)
print("wrote", OUT, "cells:", len(cells), "pairs:", len(pairs))
