#!/usr/bin/env python3
"""Generate Was-AMX-boosting-all-models.html from chartdata.json, packages.json
and findings.json (narrative written after the merge audit workflow).

Usage: python3 gen_page.py [out.html]
Charts are static inline SVG (no JavaScript needed); every mark has a <title>
for hover. Light theme only."""
import json, html, sys, statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.load(open(HERE / 'chartdata.json'))
PK = json.load(open(HERE / 'packages.json'))
F = json.load(open(HERE / 'findings.json')) if (HERE / 'findings.json').exists() else {}
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent.parent / 'PR3879/new-PRs/new-counters/Was-AMX-boosting-all-models.html'

BLUE, ORANGE, MUTED, RULE, INK, INK2, SURF = '#2a78d6', '#eb6834', '#898781', '#e1e0d9', '#0b0b0b', '#52514e', '#fcfcfb'
BLUE_LT, ORANGE_LT = '#9ec5f4', '#f6b89f'
DATES = D['dates']
ROWS = [r for r in D['rows'] if r['series']['intel'].get('tps_delta_pct') is not None]
AMX_NIGHT, STEP2_NIGHT, AMD_STEP = '2026-09-23', '2026-09-29', '2026-09-26'
e = html.escape

def halo_text(x, y, text, size=11, fill=INK2, anchor='start'):
    w = len(text) * size * 0.58 + 4
    rx = x - 2 if anchor == 'start' else x - w + 2
    return (f'<rect x="{rx:.1f}" y="{y - size + 1:.1f}" width="{w:.1f}" height="{size + 3}" fill="{SURF}" fill-opacity="0.92"/>'
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}">{e(text)}</text>')

def fmt(x, nd=1):
    return '—' if x is None else f'{x:,.{nd}f}'

def pct(x):
    return '—' if x is None else f'{x:+.1f} %'

# ---------------------------------------------------------------- Figure 1/3: dot plot of % change
def dotplot(metric, title, desc, xlab):
    key = 'tps' if metric == 'tps' else 'pf'
    rows = sorted(ROWS, key=lambda r: -r['series']['intel'][f'{key}_delta_pct'])
    W, left, right, top, rowh = 980, 330, 70, 88, 34
    H = top + rowh * len(rows) + 56
    vals = []
    for r in rows:
        for m in ('intel', 'amd'):
            s = r['series'][m]
            pre = s[f'{key}_pre_med']
            vals += [s[f'{key}_delta_pct'], 100 * (s[f'{key}_post_min'] / pre - 1), 100 * (s[f'{key}_post_max'] / pre - 1)]
    lo, hi = min(vals), max(vals)
    lo = min(-5, lo - 2); hi = max(hi + 4, 20)
    lo = max(lo, -12)  # AMD anomaly nights reach -40 %; whiskers beyond the axis are dashed and noted in the caption
    if metric == 'tps':
        hi = min(hi, 24)
    pw = W - left - right
    X = lambda v: left + (v - lo) / (hi - lo) * pw
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{e(desc)}">',
           f'<title>{e(desc)}</title>',
           f'<text x="10" y="24" font-size="15" font-weight="600" fill="{INK}">{e(title)}</text>',
           f'<text x="10" y="42" font-size="12" fill="{INK2}">Dot = median of the 12 post nights (09-23..10-04) vs the median of the pre nights (09-15..09-22; 8 Intel, 7 AMD), in %. Every dot is labelled.</text>',
           f'<text x="10" y="58" font-size="12" fill="{INK2}">Whisker = thin line from the lowest to the highest post night, as % of the pre median. Dashed = the whisker continues beyond the axis.</text>']
    # grid
    step = 5 if hi - lo <= 40 else 10
    v = (int(lo) // step) * step
    while v <= hi:
        if v >= lo:
            col = '#c3c2b7' if v == 0 else RULE
            out.append(f'<line x1="{X(v):.1f}" y1="{top-8}" x2="{X(v):.1f}" y2="{H-40}" stroke="{col}" stroke-width="1"/>')
            out.append(f'<text x="{X(v):.1f}" y="{H-24}" font-size="11" fill="{MUTED}" text-anchor="middle">{v:+d} %</text>')
        v += step
    out.append(f'<text x="{left + pw/2:.1f}" y="{H-6}" font-size="12" fill="{INK2}" text-anchor="middle">{e(xlab)}</text>')
    for i, r in enumerate(rows):
        y = top + i * rowh + rowh / 2
        out.append(f'<text x="{left-12}" y="{y+4:.1f}" font-size="12.5" fill="{INK}" text-anchor="end">{e(r["label"])}</text>')
        for m, col, dy in (('intel', BLUE, -6), ('amd', ORANGE, 6)):
            s = r['series'][m]; pre = s[f'{key}_pre_med']
            d = s[f'{key}_delta_pct']; mn = 100 * (s[f'{key}_post_min'] / pre - 1); mx = 100 * (s[f'{key}_post_max'] / pre - 1)
            mnc, mxc = max(mn, lo), min(mx, hi)
            clipped = mn < lo or mx > hi
            tip = (f'{"delphi-3bda (Intel)" if m=="intel" else "andoria-b1a3 (AMD)"} - {r["label"]}: median {fmt(pre, 2 if key=="tps" else 1)} -> '
                   f'{fmt(s[f"{key}_post_med"], 2 if key=="tps" else 1)} ({d:+.1f} %); post-9/22 nights range {mn:+.1f} % .. {mx:+.1f} %')
            out.append(f'<g><title>{e(tip)}</title>')
            dash = ' stroke-dasharray="3 3"' if clipped else ''
            out.append(f'<line x1="{X(mnc):.1f}" y1="{y+dy:.1f}" x2="{X(mxc):.1f}" y2="{y+dy:.1f}" stroke="{col}" stroke-width="2" stroke-opacity="0.45" stroke-linecap="round"{dash}/>')
            out.append(f'<circle cx="{X(d):.1f}" cy="{y+dy:.1f}" r="6" fill="{col}" stroke="{SURF}" stroke-width="2"/>')
            lx = max(X(d), X(mxc)) + 9
            out.append(halo_text(lx, y + dy + 4, f'{d:+.1f} %'))
            out.append('</g>')
    # legend
    ly = top - 14
    out.append(f'<circle cx="16" cy="{ly}" r="5" fill="{BLUE}"/><text x="26" y="{ly+4}" font-size="12" fill="{INK2}">delphi-3bda (Intel Xeon 6, has AMX)</text>')
    out.append(f'<circle cx="276" cy="{ly}" r="5" fill="{ORANGE}"/><text x="286" y="{ly+4}" font-size="12" fill="{INK2}">andoria-b1a3 (AMD Genoa, no AMX)</text>')
    out.append('</svg>')
    return '\n'.join(out)

# ---------------------------------------------------------------- Figure 2: small multiples, indexed lines
def small_multiples():
    big = [r for r in ROWS if r['series']['intel']['tps_delta_pct'] >= 4]
    rest = [r for r in ROWS if r['series']['intel']['tps_delta_pct'] < 4]
    panels = [(r, (92, 124)) for r in big] + [(r, (95, 106)) for r in rest]
    cols, pw, ph, gx, gy, left0, top0 = 3, 320, 150, 20, 52, 10, 92
    nrows = -(-len(panels) // cols)
    W = left0 + cols * (pw + gx) + 50
    H = top0 + nrows * (ph + gy) + 30
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Nightly decode speed per row, indexed to each machine\'s own pre-9/22 median = 100">',
           '<title>Nightly decode speed per row, indexed to each machine\'s pre-9/22 median = 100</title>',
           f'<text x="{left0}" y="18" font-size="15" font-weight="600" fill="{INK}">Night by night: decode speed indexed to each machine\'s own pre-09-22 median (= 100)</text>',
           f'<line x1="{left0}" y1="36" x2="{left0+24}" y2="36" stroke="{BLUE}" stroke-width="2"/><text x="{left0+30}" y="40" font-size="12" fill="{INK2}">delphi-3bda (Intel)</text>',
           f'<line x1="{left0+170}" y1="36" x2="{left0+194}" y2="36" stroke="{ORANGE}" stroke-width="2"/><text x="{left0+200}" y="40" font-size="12" fill="{INK2}">andoria-b1a3 (AMD)</text>',
           f'<text x="{left0}" y="58" font-size="12" fill="{INK2}">The first four panels (group A) use a 92..124 scale, the other nine use 95..106. Hollow triangle at a panel edge = night outside the panel range (hover shows the value).</text>',
           f'<text x="{left0}" y="74" font-size="12" fill="{INK2}">Number at the line end = the last night (10-04) as % above (+) or below (-) the pre median; the short coloured tick before it names the machine.</text>']
    n = len(DATES)
    for pi, (r, (ylo, yhi)) in enumerate(panels):
        px = left0 + (pi % cols) * (pw + gx) + 44
        py = top0 + (pi // cols) * (ph + gy) + 16
        iw, ih = pw - 50, ph - 30
        X = lambda i: px + i / (n - 1) * iw
        Y = lambda v: py + (yhi - min(max(v, ylo), yhi)) / (yhi - ylo) * ih
        lab = r['label'].replace(' (AMX benchmark row)', ' (AMX row)').replace(' users', 'u')
        out.append(f'<text x="{px}" y="{py-6}" font-size="12" font-weight="600" fill="{INK}">{e(lab)}</text>')
        for v in range(ylo, yhi + 1, 4 if yhi - ylo > 20 else 2):
            out.append(f'<line x1="{px}" y1="{Y(v):.1f}" x2="{px+iw}" y2="{Y(v):.1f}" stroke="{"#c3c2b7" if v==100 else RULE}" stroke-width="1"/>')
            out.append(f'<text x="{px-5}" y="{Y(v)+3.5:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{v}</text>')
        wide = yhi - ylo > 20
        for d, lab, ly, anc in ((AMX_NIGHT, 'AMX pkg 09-23', py + 10, 'start'), (STEP2_NIGHT, '09-29', py + ih - 14 if wide else py + ih - 3, 'end')):
            i = DATES.index(d)
            out.append(f'<line x1="{X(i):.1f}" y1="{py}" x2="{X(i):.1f}" y2="{py+ih}" stroke="{MUTED}" stroke-width="1" stroke-dasharray="2 3"/>')
            tx = X(i) + 3 if anc == 'start' else X(i) - 3
            out.append(f'<text x="{tx:.1f}" y="{ly}" font-size="9.5" fill="{MUTED}" text-anchor="{anc}">{lab}</text>')
        for i in (0, DATES.index('2026-09-22'), n - 1):
            out.append(f'<text x="{X(i):.1f}" y="{py+ih+13}" font-size="10" fill="{MUTED}" text-anchor="middle">{DATES[i][5:]}</text>')
        ends = []
        for m, col in (('intel', BLUE), ('amd', ORANGE)):
            s = r['series'][m]; base = s['tps_pre_med']
            pts = [(i, 100 * v / base) for i, v in enumerate(s['tps']) if v is not None]
            inside = lambda v: ylo <= v <= yhi
            path, pen = [], False
            for i, v in pts:
                if inside(v):
                    path.append(f'{"L" if pen else "M"}{X(i):.1f},{Y(v):.1f}'); pen = True
                else:
                    pen = False
            out.append(f'<path d="{" ".join(path)}" fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
            for i, v in pts:
                raw = s['tps'][i]
                tip = e(("Intel" if m=="intel" else "AMD") + " " + DATES[i] + ": " + f"{raw:.2f} TPS = {v:.1f} % of pre median {base:.2f}")
                if inside(v):
                    out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.2" fill="{col}" stroke="{SURF}" stroke-width="1.5"><title>{tip}</title></circle>')
                else:
                    yy = py + ih - 4 if v < ylo else py + 4
                    tri = f'{X(i):.1f},{yy+4 if v<ylo else yy-4} {X(i)-4:.1f},{yy-3 if v<ylo else yy+3} {X(i)+4:.1f},{yy-3 if v<ylo else yy+3}'
                    out.append(f'<polygon points="{tri}" fill="{SURF}" stroke="{col}" stroke-width="1.5"><title>{tip} (outside panel range)</title></polygon>')
            i, v = pts[-1]
            if inside(v):
                ends.append([X(i), Y(v), v - 100, col])
        if len(ends) == 2 and abs(ends[0][1] - ends[1][1]) < 12:
            mid = (ends[0][1] + ends[1][1]) / 2
            hi_, lo_ = (ends[0], ends[1]) if ends[0][1] <= ends[1][1] else (ends[1], ends[0])
            hi_[1], lo_[1] = mid - 6, mid + 6
        for ex, ey, ev, col in ends:
            out.append(f'<line x1="{ex+4:.1f}" y1="{ey:.1f}" x2="{ex+9:.1f}" y2="{ey:.1f}" stroke="{col}" stroke-width="2"/>')
            out.append(halo_text(ex + 11, ey + 3.5, f'{ev:+.1f}', size=10))
    out.append('</svg>')
    return '\n'.join(out)

# ---------------------------------------------------------------- Figure 4: Intel as % of AMD, before -> after (dumbbell)
def gap_dumbbell():
    rows = sorted(ROWS, key=lambda r: 100 * r['series']['intel']['tps_pre_med'] / r['series']['amd']['tps_pre_med'])
    W, left, right, top, rowh = 980, 330, 70, 88, 34
    H = top + rowh * len(rows) + 56
    vals = []
    for r in rows:
        i, a = r['series']['intel'], r['series']['amd']
        vals += [100 * i['tps_pre_med'] / a['tps_pre_med'], 100 * i['tps_post_med'] / a['tps_post_med']]
    lo, hi = min(vals) - 4, max(vals) + 6
    pw = W - left - right
    X = lambda v: left + (v - lo) / (hi - lo) * pw
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Intel decode speed as a percentage of AMD decode speed, before and after 9/22">',
           '<title>Intel decode speed as a percentage of AMD decode speed, before and after 9/22</title>',
           f'<text x="10" y="24" font-size="15" font-weight="600" fill="{INK}">Machine gap: Intel decode speed as % of AMD decode speed, before and after 09-22</text>',
           f'<text x="10" y="42" font-size="12" fill="{INK2}">100 % = both machines equal. Right of 100 % = Intel faster. The number after each pair is the change in percentage points (pt).</text>',
           f'<circle cx="16" cy="{top-14}" r="6" fill="{SURF}" stroke="{BLUE}" stroke-width="2"/><text x="28" y="{top-10}" font-size="12" fill="{INK2}">before: median of the pre nights (09-15..09-22)</text>',
           f'<circle cx="326" cy="{top-14}" r="6" fill="{BLUE}" stroke="{SURF}" stroke-width="2"/><text x="338" y="{top-10}" font-size="12" fill="{INK2}">after: median of the post nights (09-23..10-04)</text>']
    step = 10
    v = (int(lo) // step) * step
    while v <= hi:
        if v >= lo:
            col = '#c3c2b7' if v == 100 else RULE
            out.append(f'<line x1="{X(v):.1f}" y1="{top-8}" x2="{X(v):.1f}" y2="{H-40}" stroke="{col}" stroke-width="1"/>')
            out.append(f'<text x="{X(v):.1f}" y="{H-24}" font-size="11" fill="{MUTED}" text-anchor="middle">{v} %</text>')
        v += step
    out.append(f'<text x="{left + pw/2:.1f}" y="{H-6}" font-size="12" fill="{INK2}" text-anchor="middle">Intel decode TPS / AMD decode TPS, same row, same nights</text>')
    for k, r in enumerate(rows):
        y = top + k * rowh + rowh / 2
        i, a = r['series']['intel'], r['series']['amd']
        b, af = 100 * i['tps_pre_med'] / a['tps_pre_med'], 100 * i['tps_post_med'] / a['tps_post_med']
        tip = f'{r["label"]}: before {b:.1f} % (Intel {i["tps_pre_med"]:.2f} / AMD {a["tps_pre_med"]:.2f} TPS), after {af:.1f} % (Intel {i["tps_post_med"]:.2f} / AMD {a["tps_post_med"]:.2f} TPS)'
        out.append(f'<g><title>{e(tip)}</title>')
        out.append(f'<text x="{left-12}" y="{y+4:.1f}" font-size="12.5" fill="{INK}" text-anchor="end">{e(r["label"])}</text>')
        out.append(f'<line x1="{X(b):.1f}" y1="{y:.1f}" x2="{X(af):.1f}" y2="{y:.1f}" stroke="{BLUE}" stroke-width="2" stroke-opacity="0.5"/>')
        out.append(f'<circle cx="{X(b):.1f}" cy="{y:.1f}" r="6" fill="{SURF}" stroke="{BLUE}" stroke-width="2"/>')
        out.append(f'<circle cx="{X(af):.1f}" cy="{y:.1f}" r="6" fill="{BLUE}" stroke="{SURF}" stroke-width="2"/>')
        lx = X(max(b, af)) + 10
        out.append(halo_text(lx, y + 4, f'{af-b:+.1f} pt'))
        out.append('</g>')
    out.append('</svg>')
    return '\n'.join(out)

# ---------------------------------------------------------------- tables
def table_summary():
    h = ['<table class="num"><thead><tr><th>Row</th><th>Machine</th><th>Decode before<br>(pre median, TPS)</th><th>Decode after<br>(post median, TPS)</th><th>Median change</th><th>Post nights<br>min .. max</th><th>Night-to-night<br>spread before / after (CV %)</th><th>Prefill before<br>(pre median, tok/s)</th><th>Prefill after<br>(post median, tok/s)</th><th>Median change</th></tr></thead><tbody>']
    for r in ROWS:
        for m, name in (('intel', 'delphi-3bda'), ('amd', 'andoria-b1a3')):
            s = r['series'][m]
            h.append(f'<tr><td>{e(r["label"]) if m=="intel" else ""}</td><td>{name}</td><td>{fmt(s["tps_pre_med"],2)}</td><td>{fmt(s["tps_post_med"],2)}</td>'
                     f'<td><b>{pct(s["tps_delta_pct"])}</b></td><td>{fmt(s["tps_post_min"],2)} .. {fmt(s["tps_post_max"],2)}</td>'
                     f'<td>{fmt(s["tps_pre_cv"],2)} / {fmt(s["tps_post_cv"],2)}</td><td>{fmt(s["pf_pre_med"],0)}</td><td>{fmt(s["pf_post_med"],0)}</td><td>{pct(s["pf_delta_pct"])}</td></tr>')
    h.append('</tbody></table>')
    return '\n'.join(h)

def table_nightly(metric):
    key = 'tps' if metric == 'tps' else 'prefill'
    h = ['<table class="num small"><thead><tr><th>Row</th><th>Machine</th>' + ''.join(f'<th>{d[5:]}</th>' for d in DATES) + '</tr></thead><tbody>']
    for r in D['rows']:
        for m, name in (('intel', 'Intel'), ('amd', 'AMD')):
            s = r['series'][m]
            cells = []
            for i, v in enumerate(s[key]):
                cls = ' class="amxn"' if DATES[i] >= AMX_NIGHT else ''
                cells.append(f'<td{cls}>{"—" if v is None else (f"{v:.1f}" if key=="tps" else f"{v:.0f}")}</td>')
            h.append(f'<tr><td>{e(r["label"]) if m=="intel" else ""}</td><td>{name}</td>{"".join(cells)}</tr>')
    h.append('</tbody></table>')
    return '\n'.join(h)

def table_packages():
    h = ['<table><thead><tr><th>First nightly<br>(UTC date)</th><th>tron package installed</th><th>Source head (UTC)</th><th>Merges new in this package</th><th>What moved that night (night step = that night vs the night before)</th></tr></thead><tbody>']
    moved = F.get('package_notes', {})
    for p, v in sorted(PK.items(), key=lambda kv: kv[1]['first_nightly_date']):
        h.append(f'<tr><td>{v["first_nightly_date"][5:]}</td><td><code>{e(p)}</code></td><td>{e(v["head_date"][:16].replace("T"," "))}</td>'
                 f'<td>{v["n_new"]}{(": " + e(", ".join("#"+x for x in v["new_prs"]))) if 0 < v["n_new"] <= 14 else ""}</td><td>{e(moved.get(p, ""))}</td></tr>')
    h.append('</tbody></table>')
    return '\n'.join(h)

def section(key, default=''):
    return F.get(key, default)

# ---------------------------------------------------------------- page
CSS = f"""
:root {{ color-scheme: light; --ground:#f5f5f2; --surface:{SURF}; --ink:{INK}; --ink2:{INK2}; --muted:{MUTED}; --rule:#dcdbd3; --blue:{BLUE}; --orange:{ORANGE}; --code:#efeee9; }}
html, body {{ background: var(--ground); color: var(--ink); }}
body {{ font: 15.5px/1.6 "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; padding-inline: 16px; padding-block: 28px 64px; margin: 0; }}
.wrap {{ max-width: 1040px; margin: 0 auto; display: grid; gap: 18px; }}
h1 {{ font-size: 1.9rem; line-height: 1.2; margin: 0; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.28rem; margin: 30px 0 0; padding-top: 16px; border-top: 1px solid var(--rule); }}
h3 {{ font-size: 1.02rem; margin: 10px 0 0; }}
p, ul, ol {{ margin: 0; max-width: 84ch; }}
ul, ol {{ padding-left: 1.25em; display: grid; gap: 6px; }}
.meta {{ color: var(--ink2); font-size: 0.9rem; }}
.short {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 14px 18px; display: grid; gap: 8px; max-width: 86ch; }}
.short b.lead {{ font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); }}
code {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, monospace; font-size: 0.86em; background: var(--code); padding: 1px 4px; border-radius: 3px; }}
figure {{ margin: 0; display: grid; gap: 8px; }}
.chart {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; overflow-x: auto; padding: 6px; }}
.chart svg {{ display: block; max-width: 100%; height: auto; }}
figcaption {{ color: var(--ink2); font-size: 0.92rem; max-width: 86ch; }}
figcaption b {{ color: var(--ink); }}
.tw {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.86rem; }}
th, td {{ padding: 6px 10px; border-bottom: 1px solid var(--rule); text-align: left; vertical-align: top; }}
th {{ font-weight: 600; color: var(--ink2); background: #f1f0eb; }}
table.num td {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
table.small {{ font-size: 0.76rem; }} table.small th, table.small td {{ padding: 3px 5px; }}
td.amxn {{ background: #eef4fc; }}
dl.words {{ display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; margin: 0; max-width: 96ch; }}
dl.words dt {{ font-weight: 600; }} dl.words dd {{ margin: 0; color: var(--ink2); }}
@media (max-width: 640px) {{ dl.words {{ grid-template-columns: 1fr; }} }}
details {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 8px 12px; }}
summary {{ cursor: pointer; font-weight: 600; }}
.verdict {{ font-size: 1.05rem; font-weight: 600; }}
.callout {{ border-left: 3px solid var(--orange); background: var(--surface); padding: 10px 16px; max-width: 86ch; }}
"""

def page():
    parts = [f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Was AMX boosting all models?</title><style>{CSS}</style></head><body><div class="wrap">
<h1>Was AMX boosting all models? What the nightly CI measured, 2026-09-15 to 2026-10-04</h1>
<p class="meta">delphi-3bda (Intel) and andoria-b1a3 (AMD) nightly System CI perf rows, 20 nightly runs per machine (19 AMD runs with data), read from the GitHub Actions run logs. Written 2026-10-05 (UTC). Generator and data: <code>exec/ci-poll-20261004/</code>.</p>
<div class="short"><b class="lead">Short version</b>{section('short_version')}</div>
<h2>Words used here</h2>{section('words')}
<h2>1. Did several models get faster on the Intel machine after 09-22? Yes, in two groups</h2>
{section('s1_intro')}
<figure><div class="chart">{dotplot('tps', 'Decode speed: median change after 09-22, per row and machine', 'Dot plot of decode TPS change per CI row for Intel and AMD', 'Change of median decode TPS, post nights (09-23..10-04) vs pre nights (09-15..09-22)')}</div>
<figcaption><b>Figure 1.</b> {section('fig1_caption')}</figcaption></figure>
{section('s1_after')}
<h2>2. Consistent or fluctuating? Step changes, then flat</h2>
{section('s2_intro')}
<figure><div class="chart">{small_multiples()}</div>
<figcaption><b>Figure 2.</b> {section('fig2_caption')}</figcaption></figure>
{section('s2_after')}
<h2>3. Prefill (time to first token)</h2>
{section('s3_intro')}
<figure><div class="chart">{dotplot('pf', 'Prefill rate: median change after 09-22, per row and machine', 'Dot plot of prefill rate change per CI row for Intel and AMD', 'Change of median prefill rate (prompt tokens / mean TTFT), post nights vs pre nights')}</div>
<figcaption><b>Figure 3.</b> {section('fig3_caption')}</figcaption></figure>
{section('s3_after')}
<h2>4. The AMD machine over the same nights</h2>
{section('s4')}
<h2>5. delphi vs andoria: how the gap changed</h2>
{section('s5_intro')}
<figure><div class="chart">{gap_dumbbell()}</div>
<figcaption><b>Figure 4.</b> {section('fig4_caption')}</figcaption></figure>
<div class="tw">{table_summary()}</div>
<p class="meta">Table 1. Medians and ranges behind Figures 1, 3 and 4. The CV, min and max columns include the anomalous AMD nights. CV = coefficient of variation (standard deviation divided by mean, in %), computed over the nights in each window. Prefill = prompt length / mean TTFT, as the harness computes it.</p>
<h2>6. Could another change explain the Intel gains? What was installed, night by night</h2>
{section('s6_intro')}
<div class="tw">{table_packages()}</div>
<p class="meta">Table 2. Every tron package the nightly installed, the merges it added over the previous package (counted from <code>git log --first-parent</code> between the two package commits), and what moved that night.</p>
{section('s6_candidates')}
<h2>7. What would settle it</h2>
{section('s7')}
<h2>8. Data and method</h2>
{section('s8')}
<details><summary>Nightly decode TPS, every row and night (tinted = AMX kernels in the package)</summary><div class="tw">{table_nightly('tps')}</div></details>
<details><summary>Nightly prefill rate (tok/s), every row and night</summary><div class="tw">{table_nightly('prefill')}</div></details>
{section('footer')}
</div></body></html>"""]
    return ''.join(parts)

OUT.write_text(page())
print('wrote', OUT, OUT.stat().st_size, 'bytes')
