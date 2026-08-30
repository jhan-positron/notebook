#!/usr/bin/env python3
"""Report for the 2026-08-25 perf round (canonical vs mirror-on, latest
jhan-amx-p0) against the Aug 19-21 reference runs of the same cells.

Inputs (all under exec/results/):
  perf-round-20260825/perf-round.txt   new: ### model= arm= ctx= users= rep=
  t4/t4-suite.txt                       qwen reference: arm=canonical-amx / mirror-amx
  t4/t4-shapes.txt                      llama reference (arena binary, mode=TRON_AMX_DISABLE=0 = mirror)
  ci-models/mixtral-ab.txt              mixtral reference: arm=canonical / mirror
Output: perf-round-20260825/perf-round.html (light theme) + a text table on stdout.
"""
import re, statistics, sys, html
from pathlib import Path

RES = Path.home() / "workspace/intel-AMX/exec/results"
NEW = RES / "perf-round-20260825/perf-round.txt"
OUT = RES / "perf-round-20260825/perf-round.html"

MODELS = {  # runtron name -> short label
    "ingested-qwen-3-4b-instruct-2507-tp2": "qwen-3-4b-tp2",
    "ingested-llama-3.1-8b-tp2": "llama-3.1-8b-tp2",
    "mixtral-8x7b-instruct-v0.1-tp2": "mixtral-8x7b-tp2",
}
CELLS = [  # (model label, ctx, users) in report order
    ("qwen-3-4b-tp2", 2048, 1), ("qwen-3-4b-tp2", 8192, 1),
    ("qwen-3-4b-tp2", 2048, 8), ("qwen-3-4b-tp2", 8192, 8),
    ("llama-3.1-8b-tp2", 8192, 1), ("llama-3.1-8b-tp2", 2048, 8),
    ("mixtral-8x7b-tp2", 2048, 8), ("mixtral-8x7b-tp2", 8192, 8),
]

def parse_blocks(path, header_to_key):
    """Like parse() but keeps per-rep means: {key: {'dec': [rep means], 'pre': [rep means], 'failed': n}}."""
    out = {}
    if not path.exists():
        return out
    key = None; d = []; p = []
    def flush():
        if key is None: return
        cell = out.setdefault(key, {"dec": [], "pre": [], "failed": 0})
        if d: cell["dec"].append(statistics.fmean(d))
        if p: cell["pre"].append(statistics.fmean(p))
    for line in path.read_text().splitlines():
        m = re.match(r"### (.*)", line)
        if m:
            flush()
            hdr = dict(kv.split("=", 1) for kv in m.group(1).split() if "=" in kv)
            key = header_to_key(hdr); d = []; p = []
            continue
        if key is None: continue
        m = re.search(r"Generating .* at ([0-9.]+) average tok/s", line)
        if m: d.append(float(m.group(1)))
        m = re.search(r"Parsing the prompt took .* at ([0-9.]+) tokens/s", line)
        if m: p.append(float(m.group(1)))
        if "RUN-FAILED" in line:
            out.setdefault(key, {"dec": [], "pre": [], "failed": 0})["failed"] += 1
    flush()
    return out

def k_new(h):
    if "model" not in h or "arm" not in h: return None
    return (MODELS.get(h["model"], h["model"]), int(h["ctx"]), int(h["users"]), h["arm"])
def k_qwen(h):
    arm = {"canonical-amx": "canon", "mirror-amx": "mirror"}.get(h.get("arm"))
    return ("qwen-3-4b-tp2", int(h["ctx"]), int(h["users"]), arm) if arm else None
def k_llama(h):
    if h.get("model") != "ingested-llama-3.1-8b-tp2": return None
    if h.get("mode") != "TRON_AMX_DISABLE=0": return None
    return ("llama-3.1-8b-tp2", int(h["ctx"]), int(h["users"]), "mirror")
def k_mix(h):
    arm = {"canonical": "canon", "mirror": "mirror"}.get(h.get("arm"))
    return ("mixtral-8x7b-tp2", int(h["ctx"]), int(h["users"]), arm) if arm else None

new = parse_blocks(NEW, k_new)
ref = {}
ref.update(parse_blocks(RES / "t4/t4-suite.txt", k_qwen))
ref.update(parse_blocks(RES / "t4/t4-shapes.txt", k_llama))
ref.update(parse_blocks(RES / "ci-models/mixtral-ab.txt", k_mix))

def mean(v): return statistics.fmean(v) if v else None
def fmt(x, nd=1): return "-" if x is None else f"{x:.{nd}f}"
def pct(a, b): return None if (a is None or b is None or b == 0) else 100.0 * (a - b) / b
def spread(v): return "" if len(v) < 2 else f" (n={len(v)}, {min(v):.1f}-{max(v):.1f})"

rows = []
for (model, ctx, users) in CELLS:
    r = {"cell": f"{model} {users}u/{ctx//1024}K", "model": model, "ctx": ctx, "users": users}
    for arm in ("canon", "mirror"):
        n = new.get((model, ctx, users, arm), {"dec": [], "pre": [], "failed": 0})
        f = ref.get((model, ctx, users, arm), {"dec": [], "pre": [], "failed": 0})
        r[arm] = {"dec": mean(n["dec"]), "dec_n": len(n["dec"]), "dec_all": n["dec"],
                  "pre": mean(n["pre"]), "pre_n": len(n["pre"]), "failed": n["failed"],
                  "ref_dec": mean(f["dec"]), "ref_dec_n": len(f["dec"]), "ref_pre": mean(f["pre"])}
    rows.append(r)

# ---- text table ----
print(f"{'cell':26} {'canon dec':>10} {'mirror dec':>11} {'mir/can':>8} | {'ref canon':>10} {'ref mirror':>11} | {'canon vs ref':>12} {'mirror vs ref':>13}")
for r in rows:
    c, m = r["canon"], r["mirror"]
    print(f"{r['cell']:26} {fmt(c['dec']):>10} {fmt(m['dec']):>11} {fmt(pct(m['dec'], c['dec'])):>7}% | "
          f"{fmt(c['ref_dec']):>10} {fmt(m['ref_dec']):>11} | {fmt(pct(c['dec'], c['ref_dec'])):>11}% {fmt(pct(m['dec'], m['ref_dec'])):>12}%")
print("\nprefill (tok/s):")
for r in rows:
    c, m = r["canon"], r["mirror"]
    print(f"{r['cell']:26} canon {fmt(c['pre']):>8} (ref {fmt(c['ref_pre'])})   mirror {fmt(m['pre']):>8} (ref {fmt(m['ref_pre'])})")
fails = sum(r[a]["failed"] for r in rows for a in ("canon", "mirror"))
reps = {r[a]["dec_n"] for r in rows for a in ("canon", "mirror")}
print(f"\nfailed runs: {fails}; reps per cell/arm: {sorted(reps)}")

# ---- HTML: dumbbell per cell, canonical (blue) vs mirror (orange), hollow = Aug reference ----
def dumbbell_svg(rows, metric, title, unit):
    # one panel per model group (own x-scale); rows within a panel share the scale
    groups = {}
    for r in rows: groups.setdefault(r["model"], []).append(r)
    W, left, right = 760, 190, 60
    plot_w = W - left - right
    y = 44; parts = []
    parts.append(f'<text x="12" y="18" font-size="13" font-weight="600" fill="#0b0b0b">{html.escape(title)}</text>')
    # legend
    parts.append(f'<circle cx="{left}" cy="30" r="5" fill="#2a78d6"/><text x="{left+10}" y="34" font-size="11" fill="#52514e">canonical (new)</text>')
    parts.append(f'<circle cx="{left+120}" cy="30" r="5" fill="#eb6834"/><text x="{left+130}" y="34" font-size="11" fill="#52514e">mirror-on (new)</text>')
    parts.append(f'<circle cx="{left+240}" cy="30" r="5" fill="none" stroke="#898781" stroke-width="1.6"/><text x="{left+250}" y="34" font-size="11" fill="#52514e">hollow = Aug 19-21 reference, same cell</text>')
    for model, grp in groups.items():
        vals = [v for r in grp for a in ("canon", "mirror") for v in (r[a][metric], r[a]["ref_" + metric]) if v is not None]
        if not vals: continue
        lo, hi = 0.0, max(vals) * 1.12
        sx = lambda v: left + (v - lo) / (hi - lo) * plot_w
        parts.append(f'<text x="12" y="{y+4}" font-size="11.5" font-weight="600" fill="#0b0b0b">{html.escape(model)}</text>')
        y += 14
        for r in grp:
            label = f"{r['users']}u/{r['ctx']//1024}K"
            parts.append(f'<text x="{left-10}" y="{y+4}" font-size="11" fill="#52514e" text-anchor="end">{label}</text>')
            parts.append(f'<line x1="{left}" y1="{y}" x2="{left+plot_w}" y2="{y}" stroke="#e1e0d9"/>')
            c, m = r["canon"][metric], r["mirror"][metric]
            if c is not None and m is not None:
                parts.append(f'<line x1="{sx(c):.1f}" y1="{y}" x2="{sx(m):.1f}" y2="{y}" stroke="#c3c2b7" stroke-width="2"/>')
            for arm, color in (("canon", "#2a78d6"), ("mirror", "#eb6834")):
                rv = r[arm]["ref_" + metric]
                if rv is not None:
                    parts.append(f'<circle cx="{sx(rv):.1f}" cy="{y}" r="5" fill="#fcfcfb" stroke="{color}" stroke-width="1.6"/>')
                v = r[arm][metric]
                if v is not None:
                    parts.append(f'<circle cx="{sx(v):.1f}" cy="{y}" r="5" fill="{color}" stroke="#fcfcfb" stroke-width="1.5"/>')
                    dy = -9 if arm == "canon" else 15
                    parts.append(f'<text x="{sx(v):.1f}" y="{y+dy}" font-size="10" fill="#0b0b0b" text-anchor="middle">{v:.1f}</text>')
            if c is not None and m is not None:
                d = pct(m, c)
                parts.append(f'<text x="{left+plot_w+8}" y="{y+4}" font-size="10.5" fill="#52514e">{d:+.1f}%</text>')
            y += 34
        parts.append(f'<text x="{left+plot_w}" y="{y-6}" font-size="9.5" fill="#898781" text-anchor="end">{unit}, axis from 0</text>')
        y += 10
    return f'<svg viewBox="0 0 {W} {y}" width="{W}" height="{y}" font-family="system-ui,sans-serif" role="img" aria-label="{html.escape(title)}">' + "".join(parts) + "</svg>"

table = ['<table><thead><tr><th>cell</th><th>canonical tok/s</th><th>mirror tok/s</th><th>mirror vs canonical</th><th>ref canonical</th><th>ref mirror</th><th>canonical vs ref</th><th>mirror vs ref</th><th>reps</th></tr></thead><tbody>']
for r in rows:
    c, m = r["canon"], r["mirror"]
    table.append("<tr>" + "".join(f"<td>{x}</td>" for x in [
        r["cell"], fmt(c["dec"]), fmt(m["dec"]), fmt(pct(m["dec"], c["dec"])) + "%",
        fmt(c["ref_dec"]), fmt(m["ref_dec"]), fmt(pct(c["dec"], c["ref_dec"])) + "%", fmt(pct(m["dec"], m["ref_dec"])) + "%",
        f"{c['dec_n']}/{m['dec_n']}"]) + "</tr>")
table.append("</tbody></table>")

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>AMX perf round 2026-08-25</title>
<style>
body{{background:#f9f9f7;color:#0b0b0b;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:980px;margin:24px auto;padding:0 24px;line-height:1.5}}
h1{{font-size:20px}} h2{{font-size:16px;margin-top:28px}}
.svgwrap{{background:#fcfcfb;border:1px solid #e1e0d9;border-radius:10px;padding:12px;overflow-x:auto}}
table{{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}} th,td{{border-bottom:1px solid #e1e0d9;padding:4px 10px;text-align:right}} th:first-child,td:first-child{{text-align:left}}
.take{{background:#f1f0ec;border-radius:8px;padding:10px 14px}} .cite{{font-size:11.5px;color:#898781;font-family:ui-monospace,monospace}}
</style></head><body>
<h1>AMX perf round on jhan-amx-p0 (2026-08-25, delphi-3bda)</h1>
<p>Two arms per model built from the latest branch: <b>canonical</b> (TRON_AMX_DISPATCH=ON, K_MIRROR=OFF) and
<b>mirror-on</b> (both ON), all-software attention (USE_HW_ATTN=0). Not a full A/B: no kill-switch or clean arm.
Hollow rings are the same cells from the Aug 19-21 campaigns (qwen: t4-suite.txt; llama: t4-shapes.txt, mirror arm only;
mixtral: mixtral-ab.txt), so filled-vs-hollow of the same color is "latest branch vs then".</p>
<h2>Decode (tok/s, per-user average; aggregate for 8 users)</h2>
<div class="svgwrap">{dumbbell_svg(rows, "dec", "Decode throughput: canonical vs mirror-on, with Aug reference", "tok/s")}</div>
<h2>Prefill (prompt tokens/s)</h2>
<div class="svgwrap">{dumbbell_svg(rows, "pre", "Prefill throughput: canonical vs mirror-on, with Aug reference", "tok/s")}</div>
<h2>Numbers</h2>
{''.join(table)}
<p class="cite">exec/results/perf-round-20260825/perf-round.txt; references exec/results/t4/t4-suite.txt, exec/results/t4/t4-shapes.txt, exec/results/ci-models/mixtral-ab.txt</p>
</body></html>"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(page)
print(f"\nwrote {OUT}")
