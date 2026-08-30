#!/usr/bin/env python3
"""Report for the 2026-08-30 perf round (regression check for the commits
bbb55ae5f..HEAD on jhan-amx-p0).

Inputs (under exec/results/):
  perf-round-20260830/perf-round.txt  new: ### model= arm= ctx= users= rep=
  perf-round-20260825/perf-round.txt  reference: same cells, same protocol,
                                      at bbb55ae5f (the pre-change head)
gpt-oss-120b has no Aug-25 reference; its baseline is the within-round
"disable" arm (canon binary, TRON_AMX_DISABLE=1).

Output: perf-round-20260830/perf-round.html (light theme), a text table on
stdout, and perf-round-20260830/pr-summary.md (draft table for the PR
comment).
"""
import re, statistics, html
from pathlib import Path

RES = Path.home() / "workspace/intel-AMX/exec/results"
NEW = RES / "perf-round-20260830/perf-round.txt"
REF = RES / "perf-round-20260825/perf-round.txt"
OUT = RES / "perf-round-20260830/perf-round.html"
MD = RES / "perf-round-20260830/pr-summary.md"

MODELS = {  # runtron name -> short label
    "ingested-qwen-3-4b-instruct-2507-tp2": "qwen-3-4b-tp2",
    "ingested-llama-3.1-8b-tp2": "llama-3.1-8b-tp2",
    "mixtral-8x7b-instruct-v0.1-tp2": "mixtral-8x7b-tp2",
    "ingested-gpt-oss-120b-tp2": "gpt-oss-120b-tp2",
}
BOOSTED = [  # (model label, ctx, users), Aug-25 order; arms canon/mirror
    ("qwen-3-4b-tp2", 2048, 1), ("qwen-3-4b-tp2", 8192, 1),
    ("qwen-3-4b-tp2", 2048, 8), ("qwen-3-4b-tp2", 8192, 8),
    ("llama-3.1-8b-tp2", 8192, 1), ("llama-3.1-8b-tp2", 2048, 8),
    ("mixtral-8x7b-tp2", 2048, 8), ("mixtral-8x7b-tp2", 8192, 8),
]
INELIGIBLE = [  # arms canon/mirror/disable, baseline = disable
    ("gpt-oss-120b-tp2", 2048, 1), ("gpt-oss-120b-tp2", 8192, 1),
    ("gpt-oss-120b-tp2", 2048, 8), ("gpt-oss-120b-tp2", 8192, 8),
]


def parse_blocks(path):
    """{(label, ctx, users, arm): {'dec': [per-rep means], 'pre': [...], 'failed': n}}"""
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
            key = None; d = []; p = []
            if "model" in hdr and "arm" in hdr and hdr.get("rep") != "0":
                key = (MODELS.get(hdr["model"], hdr["model"]),
                       int(hdr["ctx"]), int(hdr["users"]), hdr["arm"])
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


new = parse_blocks(NEW)
ref = parse_blocks(REF)

def mean(v): return statistics.fmean(v) if v else None
def fmt(x, nd=1): return "-" if x is None else f"{x:.{nd}f}"
def pct(a, b): return None if (a is None or b is None or b == 0) else 100.0 * (a - b) / b
def fpct(x): return "-" if x is None else f"{x:+.1f}%"
def cellname(model, ctx, users): return f"{model} {users}u/{ctx//1024}K"
def get(src, model, ctx, users, arm):
    c = src.get((model, ctx, users, arm), {"dec": [], "pre": [], "failed": 0})
    return {"dec": mean(c["dec"]), "dec_all": c["dec"], "pre": mean(c["pre"]),
            "pre_all": c["pre"], "n": len(c["dec"]), "failed": c["failed"]}

# ---- boosted models: new vs Aug-25 reference, per arm ----
brows = []
for (model, ctx, users) in BOOSTED:
    r = {"cell": cellname(model, ctx, users), "model": model, "ctx": ctx, "users": users}
    for arm in ("canon", "mirror"):
        r[arm] = get(new, model, ctx, users, arm)
        r[arm]["ref_dec"] = get(ref, model, ctx, users, arm)["dec"]
        r[arm]["ref_pre"] = get(ref, model, ctx, users, arm)["pre"]
    brows.append(r)

# ---- gpt-oss-120b: arms vs within-round disable baseline ----
irows = []
for (model, ctx, users) in INELIGIBLE:
    r = {"cell": cellname(model, ctx, users), "model": model, "ctx": ctx, "users": users}
    for arm in ("canon", "mirror", "disable"):
        r[arm] = get(new, model, ctx, users, arm)
    irows.append(r)

# ---- text tables ----
print("AMX-boosted models: decode tok/s, new (head at run time) vs Aug-25 reference (bbb55ae5f)")
print(f"{'cell':26} {'canon':>8} {'ref':>8} {'delta':>7} | {'mirror':>8} {'ref':>8} {'delta':>7} | {'mir/can':>8}")
for r in brows:
    c, m = r["canon"], r["mirror"]
    print(f"{r['cell']:26} {fmt(c['dec']):>8} {fmt(c['ref_dec']):>8} {fpct(pct(c['dec'], c['ref_dec'])):>7} | "
          f"{fmt(m['dec']):>8} {fmt(m['ref_dec']):>8} {fpct(pct(m['dec'], m['ref_dec'])):>7} | "
          f"{fpct(pct(m['dec'], c['dec'])):>8}")
print("\nAMX-boosted models: prefill tok/s, new vs Aug-25 reference")
for r in brows:
    c, m = r["canon"], r["mirror"]
    print(f"{r['cell']:26} canon {fmt(c['pre']):>8} (ref {fmt(c['ref_pre'])}, {fpct(pct(c['pre'], c['ref_pre']))})   "
          f"mirror {fmt(m['pre']):>8} (ref {fmt(m['ref_pre'])}, {fpct(pct(m['pre'], m['ref_pre']))})")
print("\ngpt-oss-120b (AMX-ineligible): decode tok/s, arms vs kill-switch baseline (disable)")
print(f"{'cell':26} {'disable':>8} {'canon':>8} {'delta':>7} {'mirror':>8} {'delta':>7}")
for r in irows:
    d, c, m = r["disable"], r["canon"], r["mirror"]
    print(f"{r['cell']:26} {fmt(d['dec']):>8} {fmt(c['dec']):>8} {fpct(pct(c['dec'], d['dec'])):>7} "
          f"{fmt(m['dec']):>8} {fpct(pct(m['dec'], d['dec'])):>7}")
print("\ngpt-oss-120b prefill tok/s, arms vs disable")
for r in irows:
    d, c, m = r["disable"], r["canon"], r["mirror"]
    print(f"{r['cell']:26} disable {fmt(d['pre']):>8}  canon {fmt(c['pre']):>8} ({fpct(pct(c['pre'], d['pre']))})  "
          f"mirror {fmt(m['pre']):>8} ({fpct(pct(m['pre'], d['pre']))})")

fails = sum(r[a]["failed"] for r in brows for a in ("canon", "mirror")) + \
        sum(r[a]["failed"] for r in irows for a in ("canon", "mirror", "disable"))
reps = sorted({r[a]["n"] for r in brows for a in ("canon", "mirror")} |
              {r[a]["n"] for r in irows for a in ("canon", "mirror", "disable")})
print(f"\nfailed runs: {fails}; reps per cell/arm: {reps}")

def spread(vals):
    return "" if len(vals) < 2 else f"{min(vals):.1f}-{max(vals):.1f}"

# ---- HTML ----
def dumbbell_svg(rows, metric, title, unit, arms):
    groups = {}
    for r in rows: groups.setdefault(r["model"], []).append(r)
    W, left, right = 760, 190, 66
    plot_w = W - left - right
    y = 44; parts = []
    colors = {"canon": "#2a78d6", "mirror": "#eb6834", "disable": "#52514e"}
    names = {"canon": "canonical", "mirror": "mirror-on", "disable": "kill switch"}
    parts.append(f'<text x="12" y="18" font-size="13" font-weight="600" fill="#0b0b0b">{html.escape(title)}</text>')
    x = left
    for a in arms:
        parts.append(f'<circle cx="{x}" cy="30" r="5" fill="{colors[a]}"/><text x="{x+10}" y="34" font-size="11" fill="#52514e">{names[a]} (new)</text>')
        x += 130
    parts.append(f'<circle cx="{x}" cy="30" r="5" fill="none" stroke="#898781" stroke-width="1.6"/><text x="{x+10}" y="34" font-size="11" fill="#52514e">hollow = Aug-25 reference</text>')
    for model, grp in groups.items():
        vals = [v for r in grp for a in arms
                for v in (r[a][metric], r[a].get("ref_" + metric)) if v is not None]
        if not vals: continue
        lo, hi = 0.0, max(vals) * 1.12
        sx = lambda v: left + (v - lo) / (hi - lo) * plot_w
        parts.append(f'<text x="12" y="{y+4}" font-size="11.5" font-weight="600" fill="#0b0b0b">{html.escape(model)}</text>')
        y += 14
        for r in grp:
            label = f"{r['users']}u/{r['ctx']//1024}K"
            parts.append(f'<text x="{left-10}" y="{y+4}" font-size="11" fill="#52514e" text-anchor="end">{label}</text>')
            parts.append(f'<line x1="{left}" y1="{y}" x2="{left+plot_w}" y2="{y}" stroke="#e1e0d9"/>')
            pair = [r[a][metric] for a in arms if r[a][metric] is not None]
            if len(pair) >= 2:
                parts.append(f'<line x1="{sx(min(pair)):.1f}" y1="{y}" x2="{sx(max(pair)):.1f}" y2="{y}" stroke="#c3c2b7" stroke-width="2"/>')
            for i, a in enumerate(arms):
                rv = r[a].get("ref_" + metric)
                if rv is not None:
                    parts.append(f'<circle cx="{sx(rv):.1f}" cy="{y}" r="5" fill="#fcfcfb" stroke="{colors[a]}" stroke-width="1.6"/>')
                v = r[a][metric]
                if v is not None:
                    parts.append(f'<circle cx="{sx(v):.1f}" cy="{y}" r="5" fill="{colors[a]}" stroke="#fcfcfb" stroke-width="1.5"/>')
                    dy = (-9, 15, -9)[i] if len(arms) == 3 else (-9 if a == "canon" else 15)
                    parts.append(f'<text x="{sx(v):.1f}" y="{y+dy}" font-size="10" fill="#0b0b0b" text-anchor="middle">{v:.1f}</text>')
            y += 34
        parts.append(f'<text x="{left+plot_w}" y="{y-6}" font-size="9.5" fill="#898781" text-anchor="end">{unit}, axis from 0</text>')
        y += 10
    return f'<svg viewBox="0 0 {W} {y}" width="{W}" height="{y}" font-family="system-ui,sans-serif" role="img" aria-label="{html.escape(title)}">' + "".join(parts) + "</svg>"

btable = ['<table><thead><tr><th>cell</th><th>canonical tok/s</th><th>Aug-25 ref</th><th>delta</th><th>mirror tok/s</th><th>Aug-25 ref</th><th>delta</th><th>mirror vs canonical</th><th>reps</th></tr></thead><tbody>']
for r in brows:
    c, m = r["canon"], r["mirror"]
    btable.append("<tr>" + "".join(f"<td>{x}</td>" for x in [
        r["cell"], fmt(c["dec"]), fmt(c["ref_dec"]), fpct(pct(c["dec"], c["ref_dec"])),
        fmt(m["dec"]), fmt(m["ref_dec"]), fpct(pct(m["dec"], m["ref_dec"])),
        fpct(pct(m["dec"], c["dec"])), f"{c['n']}/{m['n']}"]) + "</tr>")
btable.append("</tbody></table>")

itable = ['<table><thead><tr><th>cell</th><th>kill switch tok/s</th><th>canonical tok/s</th><th>delta</th><th>mirror tok/s</th><th>delta</th><th>reps</th></tr></thead><tbody>']
for r in irows:
    d, c, m = r["disable"], r["canon"], r["mirror"]
    itable.append("<tr>" + "".join(f"<td>{x}</td>" for x in [
        r["cell"], fmt(d["dec"]), fmt(c["dec"]), fpct(pct(c["dec"], d["dec"])),
        fmt(m["dec"]), fpct(pct(m["dec"], d["dec"])), f"{d['n']}/{c['n']}/{m['n']}"]) + "</tr>")
itable.append("</tbody></table>")

page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>AMX perf round 2026-08-30</title>
<style>
body{{background:#f9f9f7;color:#0b0b0b;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:980px;margin:24px auto;padding:0 24px;line-height:1.5}}
h1{{font-size:20px}} h2{{font-size:16px;margin-top:28px}}
.svgwrap{{background:#fcfcfb;border:1px solid #e1e0d9;border-radius:10px;padding:12px;overflow-x:auto}}
table{{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}} th,td{{border-bottom:1px solid #e1e0d9;padding:4px 10px;text-align:right}} th:first-child,td:first-child{{text-align:left}}
.take{{background:#f1f0ec;border-radius:8px;padding:10px 14px}} .cite{{font-size:11.5px;color:#898781;font-family:ui-monospace,monospace}}
</style></head><body>
<h1>AMX perf round on jhan-amx-p0 (2026-08-30, delphi-3bda)</h1>
<p>Regression check for the commits since the 2026-08-25 round (reference head bbb55ae5f).
Arms per AMX-boosted model: <b>canonical</b> (TRON_AMX_DISPATCH=ON, K_MIRROR=OFF) and
<b>mirror-on</b> (both ON), all-software attention (USE_HW_ATTN=0). Hollow rings are the
same cells from the Aug-25 round, so filled-vs-hollow of the same color is "after the
recent commits vs before". gpt-oss-120b (AMX-ineligible geometry, 64 query heads /
8 KV heads / head size 64) has no Aug-25 reference; its baseline is the within-round
<b>kill switch</b> arm (canonical binary run with TRON_AMX_DISABLE=1).</p>
<h2>AMX-boosted models: decode (tok/s, per-user average; aggregate for 8 users)</h2>
<div class="svgwrap">{dumbbell_svg(brows, "dec", "Decode throughput: new vs Aug-25 reference", "tok/s", ["canon", "mirror"])}</div>
<h2>AMX-boosted models: prefill (prompt tokens/s)</h2>
<div class="svgwrap">{dumbbell_svg(brows, "pre", "Prefill throughput: new vs Aug-25 reference", "tok/s", ["canon", "mirror"])}</div>
<h2>gpt-oss-120b (AMX-ineligible): decode, arms vs kill switch</h2>
<div class="svgwrap">{dumbbell_svg(irows, "dec", "Decode throughput: canonical / mirror / kill switch (same round)", "tok/s", ["canon", "mirror", "disable"])}</div>
<h2>Numbers: AMX-boosted models (decode)</h2>
{''.join(btable)}
<h2>Numbers: gpt-oss-120b (decode)</h2>
{''.join(itable)}
<p class="cite">exec/results/perf-round-20260830/perf-round.txt; reference exec/results/perf-round-20260825/perf-round.txt</p>
</body></html>"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(page)
print(f"\nwrote {OUT}")

# ---- markdown draft for the PR comment ----
md = ["### Decode throughput (tok/s), this round vs the 2026-08-25 round at bbb55ae5f",
      "",
      "| cell | canonical | ref | delta | mirror | ref | delta |",
      "|---|---|---|---|---|---|---|"]
for r in brows:
    c, m = r["canon"], r["mirror"]
    md.append(f"| {r['cell']} | {fmt(c['dec'])} | {fmt(c['ref_dec'])} | {fpct(pct(c['dec'], c['ref_dec']))} "
              f"| {fmt(m['dec'])} | {fmt(m['ref_dec'])} | {fpct(pct(m['dec'], m['ref_dec']))} |")
md += ["", "### gpt-oss-120b (AMX-ineligible), arms vs kill switch (TRON_AMX_DISABLE=1), same round",
       "",
       "| cell | kill switch | canonical | delta | mirror | delta |",
       "|---|---|---|---|---|---|"]
for r in irows:
    d, c, m = r["disable"], r["canon"], r["mirror"]
    md.append(f"| {r['cell']} | {fmt(d['dec'])} | {fmt(c['dec'])} | {fpct(pct(c['dec'], d['dec']))} "
              f"| {fmt(m['dec'])} | {fpct(pct(m['dec'], d['dec']))} |")
MD.write_text("\n".join(md) + "\n")
print(f"wrote {MD}")
