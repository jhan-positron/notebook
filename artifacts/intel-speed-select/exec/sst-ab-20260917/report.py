#!/usr/bin/env python3
"""Build the HTML report for sst-ab-20260917 from results/<name>/summary.json (written by summarize.py)
and the fixed part-1 facts. Usage: report.py <results dir> <out.html>

Design (single-theme light, per the user's rule): one axis per chart; the arm comparison is indexed to the
boot arm = 100 so all four models share one scale; the frequency chart shows the measured app-core MHz per
arm; absolute numbers live in the tables next to the charts. Colors: the documented reference palette slots
1-3 (blue = shipped policy, orange = shipped + cores 72-78; the boot baseline in a neutral grey, the emphasis
pattern), slots validated all-pairs in the skill's palette.md; every dot is also direct-labeled and every value is in a table.
"""
import sys, json, os, html, math, datetime, statistics as st

RES = sys.argv[1]; OUT = sys.argv[2]
S = json.load(open(os.path.join(RES, "summary.json")))
cells = S["cells"]; pairs = S["pairs"]; models = S.get("models", {}); runs = S.get("runs", [])
ORDER = [c for c in ["l8b", "q3-4b", "mixtral", "q25-32b"] if c in cells] + [c for c in cells if c not in ["l8b", "q3-4b", "mixtral", "q25-32b"]]
ARMS = ["boot", "tuned", "tunedplus"]
ARM_LABEL = {"boot": "boot default (no tune-up)", "tuned": "shipped policy (today)", "tunedplus": "shipped + cores 72-78"}
COL = {"boot": "var(--neutral)", "tuned": "var(--s1)", "tunedplus": "var(--s2)"}   # baseline in a neutral grey (emphasis pattern), the two policies in validated slots 1 and 2
NICE = {"l8b": "llama-3.1-8b tp2", "q3-4b": "qwen-3-4b tp2", "mixtral": "mixtral-8x7b tp2", "q25-32b": "qwen-2.5-32b tp2"}

def f(x, nd=1, sign=False):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "n/a"
    return (f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}")
def esc(s): return html.escape(str(s))

# ---- run-level facts ----
versions = sorted({r["version"] for r in runs if r.get("version")})
hw = {c: sorted({r["hw_attn"] for r in runs if r["cell"] == c and r.get("hw_attn")}) for c in ORDER}
n_runs = len(runs)
t0 = min((r["mtime"] for r in runs), default=None); t1 = max((r["mtime"] for r in runs), default=None)
def utc(ts): return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if ts else "n/a"

# ---- chart 1: TPS indexed to boot = 100, one row per model, three dots ----
def idx(c, a):
    b = cells[c].get("boot"); r = cells[c].get(a)
    if not b or not r: return None
    return 100 * r["tps_mean"] / b["tps_mean"]
rows = []
for c in ORDER:
    rows.append({"cell": c, "vals": {a: idx(c, a) for a in ARMS}, "abs": {a: (cells[c][a]["tps_mean"] if a in cells[c] else None) for a in ARMS},
                 "pair_tuned": pairs.get(c, {}).get("tuned_vs_boot"), "pair_plus": pairs.get(c, {}).get("tunedplus_vs_boot"), "pair_pp": pairs.get(c, {}).get("tunedplus_vs_tuned")})
allv = [v for r in rows for v in r["vals"].values() if v is not None]
xmin = math.floor((min(allv + [100]) - 2) / 2) * 2 if allv else 96
xmax = math.ceil((max(allv + [100]) + 2) / 2) * 2 if allv else 110
W, LEFT, RIGHT, ROWH, TOP = 760, 170, 40, 58, 36
H = TOP + ROWH * len(rows) + 44
def X(v): return LEFT + (v - xmin) / (xmax - xmin) * (W - LEFT - RIGHT)
svg1 = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Decode throughput per model, indexed to the boot default arm = 100">']
step = 2 if xmax - xmin <= 24 else 5
for v in range(xmin, xmax + 1, step):
    x = X(v); svg1.append(f'<line x1="{x:.1f}" y1="{TOP-8}" x2="{x:.1f}" y2="{H-40}" class="grid"/><text x="{x:.1f}" y="{H-22}" class="tick" text-anchor="middle">{v}</text>')
svg1.append(f'<text x="{(LEFT + W - RIGHT)/2:.0f}" y="{H-6}" class="axis" text-anchor="middle">decode tokens/s per user, in % of the boot-default arm (boot = 100)</text>')
svg1.append(f'<line x1="{X(100):.1f}" y1="{TOP-14}" x2="{X(100):.1f}" y2="{H-40}" class="ref"/>')
for i, r in enumerate(rows):
    y = TOP + i * ROWH + ROWH / 2
    vals = {a: v for a, v in r["vals"].items() if v is not None}
    if len(vals) >= 2:
        lo, hi = min(vals.values()), max(vals.values())
        svg1.append(f'<line x1="{X(lo):.1f}" y1="{y:.1f}" x2="{X(hi):.1f}" y2="{y:.1f}" class="bar"/>')
    svg1.append(f'<text x="{LEFT-12}" y="{y+4:.1f}" class="rowlab" text-anchor="end">{esc(NICE.get(r["cell"], r["cell"]))}</text>')
    for a in ("boot", "tunedplus", "tuned"):   # the shipped-policy dot is drawn last so it stays visible where the two policies coincide
        v = vals.get(a)
        if v is None: continue
        svg1.append(f'<circle cx="{X(v):.1f}" cy="{y:.1f}" r="7" fill="{COL[a]}" class="dot"><title>{esc(ARM_LABEL[a])}: {f(r["abs"][a], 2)} tok/s per user = {f(v)} % of boot</title></circle>')
    # direct labels: the paired gain of each policy over boot; the shipped label above its dot, the extended label
    # below the row when the two dots are closer than 60 px (they coincide for every model here); boot absolute below its dot
    close = ("tuned" in vals and "tunedplus" in vals and abs(X(vals["tuned"]) - X(vals["tunedplus"])) < 60)
    for a, dy in (("tuned", -13), ("tunedplus", 22 if close else -13)):
        v = vals.get(a); p = r["pair_tuned"] if a == "tuned" else r["pair_plus"]
        if v is None or not p: continue
        lab = f'{p["tps_delta_mean"]:+.1f} %'
        svg1.append(f'<text x="{X(v):.1f}" y="{y+dy:.1f}" class="dlab{" muted" if a == "tunedplus" else ""}" text-anchor="middle">{lab}</text>')
    if "boot" in vals:
        svg1.append(f'<text x="{X(vals["boot"]):.1f}" y="{y+22:.1f}" class="dlab muted" text-anchor="middle">{f(r["abs"]["boot"], 1)} tok/s</text>')
svg1.append('</svg>')

# ---- chart 2: measured app-core frequency per arm (proof the arm took effect) ----
fr = []
for c in ORDER:
    fr.append({"cell": c, "mhz": {a: (cells[c][a].get("app_mhz_mean") if a in cells[c] else None) for a in ARMS}, "fast": {a: (cells[c][a].get("fast_cpus_mean") if a in cells[c] else None) for a in ARMS}})
allm = [v for r in fr for v in r["mhz"].values() if v]
fmin, fmax = 2500, 4300
def FX(v): return LEFT + (v - fmin) / (fmax - fmin) * (W - LEFT - RIGHT)
H2 = TOP + ROWH * len(fr) + 44
svg2 = [f'<svg viewBox="0 0 {W} {H2}" width="100%" role="img" aria-label="Measured mean frequency of the 28 tron app cpus per arm">']
for v in range(fmin, fmax + 1, 300):
    x = FX(v); svg2.append(f'<line x1="{x:.1f}" y1="{TOP-8}" x2="{x:.1f}" y2="{H2-40}" class="grid"/><text x="{x:.1f}" y="{H2-22}" class="tick" text-anchor="middle">{v}</text>')
svg2.append(f'<text x="{(LEFT + W - RIGHT)/2:.0f}" y="{H2-6}" class="axis" text-anchor="middle">mean busy frequency of the 28 app cpus during the run, MHz (turbostat, 5-s samples)</text>')
svg2.append(f'<line x1="{FX(2700):.1f}" y1="{TOP-14}" x2="{FX(2700):.1f}" y2="{H2-40}" class="ref"/><text x="{FX(2700)+4:.1f}" y="{TOP-4}" class="tick">2700 = CLOS3 cap</text>')
for i, r in enumerate(fr):
    y = TOP + i * ROWH + ROWH / 2
    vals = {a: v for a, v in r["mhz"].items() if v}
    if len(vals) >= 2: svg2.append(f'<line x1="{FX(min(vals.values())):.1f}" y1="{y:.1f}" x2="{FX(max(vals.values())):.1f}" y2="{y:.1f}" class="bar"/>')
    svg2.append(f'<text x="{LEFT-12}" y="{y+4:.1f}" class="rowlab" text-anchor="end">{esc(NICE.get(r["cell"], r["cell"]))}</text>')
    for a in ("boot", "tunedplus", "tuned"):
        v = vals.get(a)
        if v is None: continue
        svg2.append(f'<circle cx="{FX(v):.1f}" cy="{y:.1f}" r="7" fill="{COL[a]}" class="dot"><title>{esc(ARM_LABEL[a])}: {v:.0f} MHz, {f(r["fast"][a], 1)} of 28 app cpus above the cap</title></circle>')
    if "boot" in vals: svg2.append(f'<text x="{FX(vals["boot"]):.1f}" y="{y+22:.1f}" class="dlab muted" text-anchor="middle">{vals["boot"]:.0f}</text>')
    if "tuned" in vals: svg2.append(f'<text x="{FX(vals["tuned"]):.1f}" y="{y-13:.1f}" class="dlab" text-anchor="middle">{vals["tuned"]:.0f}</text>')
svg2.append('</svg>')

legend = '<div class="legend">' + ''.join(f'<span><i style="background:{COL[a]}"></i>{esc(ARM_LABEL[a])}</span>' for a in ARMS) + '</div>'

# ---- tables ----
def cell_table():
    h = ['<table><thead><tr><th>model</th><th>arm</th><th>n</th><th>TPS/user tok/s</th><th>sd</th><th>CV %</th><th>TTFT s</th><th>prefill tok/s/user</th><th>app MHz</th><th>fast cpus /28</th><th>dev MHz</th><th>pkg1 W</th><th>attention</th></tr></thead><tbody>']
    for c in ORDER:
        for a in ARMS:
            r = cells[c].get(a)
            if not r: continue
            h.append(f'<tr><td>{esc(NICE.get(c, c))}</td><td><i class="sw" style="background:{COL[a]}"></i>{esc(ARM_LABEL[a])}</td><td>{r["n"]}</td><td>{f(r["tps_mean"],2)}</td><td>{f(r["tps_sd"],2)}</td><td>{f(r["tps_cv_pct"],2)}</td><td>{f(r.get("ttft_mean"),3)}</td><td>{f(r.get("prefill_tps_mean"),1)}</td><td>{f(r.get("app_mhz_mean"),0)}</td><td>{f(r.get("fast_cpus_mean"),1)}</td><td>{f(r.get("dev_mhz_mean"),0)}</td><td>{f(r.get("pkg1_w_mean"),1)}</td><td>{esc(r.get("hw_attn") or "n/a")}</td></tr>')
    h.append('</tbody></table>'); return ''.join(h)
def pair_table():
    h = ['<table><thead><tr><th>model</th><th>comparison (B vs A)</th><th>pairs</th><th>TPS delta % mean +/- 95% CI</th><th>sd</th><th>t</th><th>TTFT delta % (negative = faster)</th><th>pkg1 W delta</th><th>max idle between the pair, s</th></tr></thead><tbody>']
    for c in ORDER:
        for k, lab in (("tuned_vs_boot", "shipped vs boot"), ("tunedplus_vs_boot", "shipped+72-78 vs boot"), ("tunedplus_vs_tuned", "shipped+72-78 vs shipped")):
            p = pairs.get(c, {}).get(k)
            if not p: continue
            flag = " <b>FLAG</b>" if p.get("max_idle_s", 0) > 300 else ""
            h.append(f'<tr><td>{esc(NICE.get(c, c))}</td><td>{lab}</td><td>{p["n"]}</td><td>{f(p["tps_delta_mean"],2,True)} +/- {f(p.get("tps_delta_ci95"),2)}</td><td>{f(p["tps_delta_sd"],2)}</td><td>{f(p["t"],1)}</td><td>{f(p.get("ttft_delta_mean"),2,True)}</td><td>{f(p.get("pkg1_w_delta_mean"),1,True)}</td><td>{f(p.get("max_idle_s"),0)}{flag}</td></tr>')
    h.append('</tbody></table>'); return ''.join(h)

# ---- verdict text (computed, not hand-written) ----
def verdict():
    out = []
    for c in ORDER:
        p = pairs.get(c, {}).get("tuned_vs_boot"); q = pairs.get(c, {}).get("tunedplus_vs_tuned")
        if not p: out.append(f"{NICE.get(c,c)}: no paired data."); continue
        ci = p.get("tps_delta_ci95") or float("nan")
        sig = "the interval excludes zero" if (not math.isnan(ci) and abs(p["tps_delta_mean"]) > ci) else "the interval includes zero"
        s = f"{NICE.get(c,c)}: shipped policy vs boot default {p['tps_delta_mean']:+.2f} % +/- {ci:.2f} % decode TPS over {p['n']} pairs ({sig})"
        if q:
            ci2 = q.get("tps_delta_ci95") or float("nan"); sig2 = "excludes zero" if (not math.isnan(ci2) and abs(q["tps_delta_mean"]) > ci2) else "includes zero"
            s += f"; adding cores 72-78 changes it by {q['tps_delta_mean']:+.2f} % +/- {ci2:.2f} % (interval {sig2})"
        out.append(s + ".")
    return out

part1 = open(os.path.join(RES, "part1-config-coverage.md")).read() if os.path.exists(os.path.join(RES, "part1-config-coverage.md")) else ""

# socket-1 core map (72 physical cores) colored by role, with the CLOS class under each arm
ROLE = {}
for c in range(72, 144): ROLE[c] = "unassigned"
for c in (72,): ROLE[c] = "platform"
for c in (73, 74): ROLE[c] = "front-end (rinzler)"
for c in (75, 76, 77, 78): ROLE[c] = "dev (TX/RX driver)"
for c in list(range(79, 87)) + list(range(96, 144)): ROLE[c] = "tron app"
ROLE_COL = {"tron app": "var(--s1)", "dev (TX/RX driver)": "var(--s2)", "front-end (rinzler)": "var(--s3)", "platform": "var(--ink3)", "unassigned": "var(--line)"}
def clos_of(arm, c):
    fast = {"boot": [72, 73, 90, 91, 108, 109, 126, 127], "tuned": list(range(79, 87)) + list(range(96, 144)), "tunedplus": list(range(72, 87)) + list(range(96, 144))}[arm]
    return 0 if c in fast else 3
def coremap():
    cw, ch, gap = 22, 22, 3; cols = 24
    h = [f'<svg viewBox="0 0 {cols*(cw+gap)+8} {3*(ch+gap)+8}" width="100%" style="max-width:640px" role="img" aria-label="Socket-1 physical cores 72 to 143 by role">']
    for i, c in enumerate(range(72, 144)):
        x = 4 + (i % cols) * (cw + gap); y = 4 + (i // cols) * (ch + gap)
        h.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="3" fill="{ROLE_COL[ROLE[c]]}"><title>cpu {c} (sibling {c+144}): {ROLE[c]}; CLOS boot={clos_of("boot",c)} shipped={clos_of("tuned",c)} shipped+72-78={clos_of("tunedplus",c)}</title></rect>')
        h.append(f'<text x="{x+cw/2}" y="{y+ch/2+4}" class="cm" text-anchor="middle">{c}</text>')
    h.append('</svg>')
    leg = '<div class="legend">' + ''.join(f'<span><i style="background:{v}"></i>{esc(k)}</span>' for k, v in ROLE_COL.items()) + '</div>'
    return ''.join(h) + leg

def md_table_to_html(md):
    # minimal: convert the pipe tables and paragraphs of part1 into html
    out = []; tbl = []
    def flush():
        nonlocal tbl
        if tbl:
            rows_ = [r for r in tbl if not set(r.replace('|', '').strip()) <= set('-: ')]
            out.append('<table>' + ''.join(('<tr>' + ''.join(f'<t{"h" if i == 0 else "d"}>{html.escape(x.strip())}</t{"h" if i == 0 else "d"}>' for x in r.strip().strip('|').split('|')) + '</tr>') for i, r in enumerate(rows_)) + '</table>')
            tbl = []
    for line in md.splitlines():
        if line.startswith('|'): tbl.append(line); continue
        flush()
        if line.startswith('## '): out.append(f'<h3>{html.escape(line[3:])}</h3>')
        elif line.startswith('# '): continue
        elif line.startswith('- '): out.append(f'<p class="li">{html.escape(line[2:])}</p>')
        elif line.strip(): out.append(f'<p>{html.escape(line)}</p>')
    flush(); return ''.join(out)

page = f'''<title>Speed Select Recheck</title>
<style>
:root{{color-scheme:light;--bg:#f7f6f2;--card:#ffffff;--ink:#17201f;--ink2:#4b5654;--ink3:#7d8785;--line:#dcd9d0;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--neutral:#8a8f8d;--ref:#9a958a}}
body{{background:var(--bg);color:var(--ink);font:15px/1.5 "IBM Plex Sans","Segoe UI",system-ui,sans-serif;margin:0;padding-block:28px;padding-inline:max(16px,calc(50% - 480px))}}
h1{{font-family:"IBM Plex Serif",Georgia,serif;font-weight:600;font-size:30px;line-height:1.15;margin:0 0 6px;text-wrap:balance}}
h2{{font-size:20px;margin:36px 0 10px;font-weight:600}} h3{{font-size:16px;margin:22px 0 6px}}
p{{max-width:70ch;margin:8px 0}} .li{{padding-left:1.1em;text-indent:-1.1em}} .li::before{{content:"\\2022  ";color:var(--ink3)}}
.short{{background:var(--card);border-left:4px solid var(--s1);padding:14px 18px;border-radius:0 6px 6px 0;margin:18px 0}}
.short p{{margin:6px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 18px;margin:14px 0}}
.meta{{color:var(--ink2);font-size:13px}}
svg .grid{{stroke:var(--line);stroke-width:1}} svg .ref{{stroke:var(--ref);stroke-width:1.5}} svg .bar{{stroke:var(--ink3);stroke-width:2;stroke-linecap:round}}
svg .dot{{stroke:var(--card);stroke-width:2}} svg .tick{{font-size:12px;fill:var(--ink2);font-variant-numeric:tabular-nums}} svg .axis{{font-size:12px;fill:var(--ink2)}}
svg .rowlab{{font-size:14px;fill:var(--ink)}} svg .dlab{{font-size:12px;fill:var(--ink);font-variant-numeric:tabular-nums}} svg .muted{{fill:var(--ink3)}} svg .cm{{font-size:9px;fill:#fff}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--ink2);margin:6px 0 2px}} .legend i,.sw{{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px}}
.tw{{overflow-x:auto}} table{{border-collapse:collapse;font-size:13px;min-width:100%}} th,td{{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap;font-variant-numeric:tabular-nums}} th{{color:var(--ink2);font-weight:600;background:#f1efe8}}
.take{{font-size:14px;color:var(--ink2);margin-top:4px}}
.glos dt{{font-weight:600;margin-top:8px}} .glos dd{{margin:0 0 0 0;color:var(--ink2)}}
code{{background:#efede6;padding:1px 5px;border-radius:3px;font-size:13px}}
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Serif:wght@600&display=swap">
<h1>Does the speed-select tune-up on delphi-3bda still pay off?</h1>
<p class="meta">Campaign sst-ab-20260917 on delphi-3bda, socket 1 only. {n_runs} measured runs, {utc(t0)} to {utc(t1)}. Engine {esc(", ".join(versions) or "n/a")}. Written by Claude Code on {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}.</p>
<div class="short"><b>Short version</b>
<p>The shipped speed-select policy on delphi-3bda already puts every tron app core of Bill&#39;s current resource map in the fast class, so its core ranges need no update; the one change from the July project that is still not deployed is the front-end un-clamp of rinzler cores 1-2 and 73-74.</p><p>On today&#39;s engine (tron 2026.09.17-31b80a18) the policy still raises decode throughput on all four stable tp2 models: +12.9 % on llama-3.1-8b, +4.0 % on qwen-3-4b, +2.6 % on qwen-2.5-32b and +1.8 % on mixtral-8x7b, each over 6 back-to-back pairs with a 95 % interval that excludes zero, at a cost of +48 to +60 W on socket 1.</p><p>Making the dev, front-end and platform cores fast as well moved runtron throughput by at most 0.5 % in either direction, so the front-end un-clamp cannot be judged with runtron; its evidence stays the July serving-path measurement (+1.1 % decode at 8 users).</p></div>

<h2>Words used here</h2>
<div class="card glos"><dl>
<dt>tron, runtron, rinzler</dt><dd>tron is the inference engine. runtron is its command-line tool, used for every measurement here. rinzler is the production server that wraps the same engine.</dd>
<dt>TPS</dt><dd>decode throughput: generated tokens per second per user, runtron's "average tok/s" line, one per user, averaged over the 8 users of a run.</dd>
<dt>TTFT</dt><dd>time to first token, runtron's "Parsing the prompt took" line, the maximum over the 8 users.</dd>
<dt>Intel Speed Select, CLOS</dt><dd>the CPU feature that assigns each core a frequency class. CLOS0 allows 2.7 to 4.4 GHz; CLOS3 caps the core at 2.7 GHz. The shipped policy is the file /etc/default/intel-speed-select-state applied at boot.</dd>
<dt>boot default</dt><dd>the CLOS partition the machine has without our policy: 8 fixed cores per socket fast, all others capped. On socket 1 these are cores 72-73, 90-91, 108-109, 126-127.</dd>
<dt>resource map</dt><dd>tron's config/resource-map.yaml, which names the cores each thread family uses: tron app cores, dev cores (FPGA driver TX/RX threads), rinzler front-end cores, platform cores.</dd>
<dt>our half</dt><dd>socket 1 (cpus 72-143 with hyper-thread siblings 216-287) and FPGA cards 90, 93, b9, bc. Bill uses the other half; nothing there was touched.</dd>
<dt>tp2, 8u, p1024</dt><dd>tensor parallel over 2 cards, 8 concurrent users, 1024-token prompts; each user generated 1024 tokens.</dd>
<dt>pair, CI, t</dt><dd>a pair is two arms measured back to back in the same repetition on the same model. CI is the two-sided 95 % confidence interval of the mean paired delta. t is mean divided by its standard error.</dd>
</dl></div>

<h2>1. The policy already covers Bill's map; the un-deployed piece is the front-end un-clamp</h2>
<div class="card">
<p>Socket-1 physical cores by the role the current resource map gives them. Hover a core for its CLOS class under each arm.</p>
{coremap()}
<p class="take">Shipped policy: every blue core is fast; orange, aqua and grey cores are capped at 2.7 GHz. The July 2026 ship candidate makes the two aqua (front-end) cores fast; the tunedplus arm below makes the aqua, orange and platform cores fast.</p>
</div>
{md_table_to_html(part1)}

<h2>2. Decode throughput: three frequency arms on four stable models</h2>
<div class="card">
{legend}
{"".join(svg1)}
<p class="take">Only the blue dot moved away from the baseline on every row; the orange dot sits on top of it. The gain differs by model (12.9 % down to 1.8 %); this campaign measured the gain, not the mechanism behind the spread. Grey labels under the baseline dot give the boot-default throughput in tok/s per user; the label above a row is the shipped policy&#39;s paired gain over it, the grey label below the right-hand dot is the extended policy&#39;s.</p>
</div>
<div class="tw">{pair_table()}</div>

<h2>3. The arms did what they were meant to: measured core frequency</h2>
<div class="card">
{legend}
{"".join(svg2)}
<p class="take">Each run's turbostat samples (5 s) were averaged over the 28 app cpus of the tp2 placement. The boot arm keeps 2 of those 28 cpus (126, 127) fast because they are boot PCT cores, so its mean sits slightly above the 2700 MHz cap. The samples cover prefill and decode together.</p>
</div>
<div class="tw">{cell_table()}</div>

<h2>4. Verdict, with the numbers behind each claim</h2>
<div class="card">
{"".join(f'<p class="li">{esc(v)}</p>' for v in verdict())}
<p class="li">Front-end un-clamp (cores 1-2, 73-74): not testable here. runtron places no thread on those cores, and the tunedplus arm confirms it: with cores 72-78 fast, decode changed by +0.15 % (llama-3.1-8b), -0.53 % (qwen-3-4b), +0.03 % (mixtral-8x7b) and +0.13 % (qwen-2.5-32b), all within 0.5 %, while the dev cores that host runtron&#39;s TX/RX driver threads were measured at 4.0 to 4.1 GHz instead of 2.7 GHz. Two conclusions follow. Extending the fast set to the dev cores 75-78 buys nothing in runtron and costs 3.5 to 5.8 W. The front-end un-clamp itself remains supported only by the July 2026 serving-path evidence (ab42: +1.12 % +/- 0.21 decode at 8 users, +2.44 % +/- 1.05 at 24 users, positive in 5 of 5 draws, +6 to 8 W); deploying it means changing FAST_CORE_RANGES in Hannah&#39;s Ansible role to &#39;1-2 7-14 24-71 73-74 79-86 96-143&#39;, and a serving-path check on this engine would be the way to confirm it still holds.</p>
</div>

<h2>5. Method and provenance</h2>
<div class="card">
<p class="li">Arms change only the CLOS association of socket-1 cpus. boot = the boot-default partition on socket 1. tuned = the shipped policy. tunedplus = tuned plus cpus 72-78 and their siblings fast. Socket 0 was never written; the shipped association was restored on socket 1 after every run and verified against a start snapshot at the end.</p>
<p class="li">&quot;1k prompts&quot; was read as a prompt length of 1024 tokens (the p1024 shape of the July campaigns and of the nightly perf test), not as 1000 requests.</p>
<p class="li">Runs: runtron stream-generate-text, tp2 on cards 90 and 93 (--instance 2,4), 8 users, 1024-token prompt, 1024 generated tokens with --dont-stop, production attention default (USE_HW_ATTN unset), TRON_LOG_LEVEL=debug. Per repetition and model the three arms ran back to back; the arm order followed a Williams square over 6 repetitions so each arm took each position and each predecessor equally often.</p>
<p class="li">Models were chosen from the August 2026 perf-fluctuation matrix: the tp2 configurations of llama-3.1-8b, mixtral-8x7b, qwen-2.5-32b and qwen-3-4b were TIGHT (CV 0.06 to 0.67 %); every tp4 configuration rolled (CV 1.1 to 4.6 %). The user asked for qwen3-4b-tp2 explicitly.</p>
<p class="li">Binary: runtron built from tron commit 31b80a18 (the deb installed on delphi-3bda on 2026-09-17), cmake preset cross-avx512 with production and ingest models. Engine version string per run is in the table above.</p>
<p class="li">Machine state after the campaign (15:12 UTC): socket-1 CLOS map identical to the start snapshot on the first restore attempt; machine-wide 224 cpus in CLOS0 and 64 in CLOS3, the shipped split; no runtron, turbostat or hugepage files of the campaign left; campaign flock released. The idle production unit that held our four cards (rinzler@0 at 13:42 UTC) was stopped for the campaign and left stopped, the convention of the AMX campaigns; the 02:45 UTC timer brings serving back. Nothing on socket 0 or on Bill&#39;s cards was written.</p>
<p class="li">Files: results in ~/workspace/intel-vs-amd/speed-select/intel-speed-select-recollect/results/sst-ab-20260917 (rt-results.txt, rt/*.log, power/*/power.tsv, summary.md, summary.json); scripts in exec/sst-ab-20260917 (campaign.sh, power_summary.py, summarize.py, report.py); log in logs/sst-ab-20260917.log.</p>
</div>
'''
open(OUT, "w").write(page)
print(f"wrote {OUT} ({len(page)} bytes); placeholders left for the Short version, the chart takeaway and the front-end verdict")
