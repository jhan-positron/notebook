#!/usr/bin/env python3
"""gen_report.py <config.json> <out.html>: the issue #4934 results page from summarizer JSON files.

The config names the page (title, short version, words, notes) and its groups. A group is one summary.json,
an ordered list of arms (key, label), the reference arm (the band is drawn around it), the headline arm
(its difference to the reference is annotated) and the extra pairs for the table. Every cell of the group
gets one row with two panels: decode TPS per user, prefill TTFT in seconds. Colors are fixed per label
(the Okabe-Ito set validated with the dataviz skill's script), the band is twice the larger sample standard
deviation of the reference and the headline arm, never under 0.40 TPS or 0.15 s (the harness's rule).
"""
import html
import json
import sys

COLORS = {'main': '#009E73', 'PR 3': '#E69F00', 'PR 4': '#D55E00', 'fix': '#0072B2', 'probe': '#CC79A7', 'probe a1': '#CC79A7', 'probe a2': '#000000'}
FLOOR = {'tps': 0.40, 'ttft': 0.15}
DEC = {'tps': 2, 'ttft': 3}
UNIT = {'tps': 'TPS', 'ttft': 's'}
PANEL_TITLE = {'tps': 'Decode TPS per user', 'ttft': 'Prefill TTFT, s'}


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(v, d):
    return f"{v:.{d}f}"


def signed(v, d):
    return ('+' if v >= 0 else '-') + fmt(abs(v), d)


def cell_name(c):
    return f"tp{c['tp']}, {c['users']} users, prompt {c['prompt']:,}"


def load_group(g):
    d = json.load(open(g['summary']))
    cells = {}
    for c in d['cells']:
        if c['arm'] not in {a[0] for a in g['arms']}:
            continue
        key = (c['cell'], c['attn'])
        cells.setdefault(key, {'meta': c, 'arms': {}})['arms'][c['arm']] = c
    paired = {(p['cell'], p['attn'], p['a'], p['b']): p for p in d['paired']}
    return cells, paired


def band_of(ref, arm, key):
    sd = lambda c: c['tps_sd'] if key == 'tps' else c['ttft_sd']
    return max(2 * max(sd(ref), sd(arm)), FLOOR[key])


def mean_of(c, key):
    return c['tps_mean'] if key == 'tps' else c['ttft_mean']


def sd_of(c, key):
    return c['tps_sd'] if key == 'tps' else c['ttft_sd']


def panel(g, cell, key, paired):
    arms = g['arms']  # [[arm, label], ...]
    ref_arm, head_arm = g['reference'], g['headline']
    data = cell['arms']
    missing = [a for a, _ in arms if a not in data]
    if missing:
        return f'<div class="panel"><h3>{PANEL_TITLE[key]}</h3><p class="take">Insufficient data: arms {", ".join(missing)} have no complete run.</p></div>'
    ref, head = data[ref_arm], data[head_arm]
    bw = band_of(ref, head, key)
    dec = DEC[key]
    W, L, R, row_h, top = 560, 64, 150, 26, 16
    n = len(arms)
    H = top + row_h * n + 30
    vals = [mean_of(data[a], key) for a, _ in arms]
    rv = mean_of(ref, key)
    lo, hi = min(vals + [rv - bw]), max(vals + [rv + bw])
    pad = (hi - lo) * 0.12 or 0.3
    lo -= pad
    hi += pad
    x = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(cell_name(cell["meta"]))}, {PANEL_TITLE[key]}">']
    s.append(f'<rect x="{x(rv - bw):.1f}" y="{top - 6}" width="{x(rv + bw) - x(rv - bw):.1f}" height="{row_h * n + 6}" fill="#e6eaef"/>')
    ref_color = COLORS[dict(arms)[ref_arm]]
    s.append(f'<line x1="{x(rv):.1f}" y1="{top - 6}" x2="{x(rv):.1f}" y2="{top + row_h * n}" stroke="{ref_color}" stroke-width="1" opacity="0.6"/>')
    for i, (arm, label) in enumerate(arms):
        y = top + row_h * i + row_h / 2
        v = mean_of(data[arm], key)
        color = COLORS[label]
        if arm == head_arm:
            s.append(f'<line x1="{x(rv):.1f}" y1="{y}" x2="{x(v):.1f}" y2="{y}" stroke="{color}" stroke-width="2"/>')
        s.append(f'<text x="{L - 8}" y="{y + 4}" text-anchor="end" font-size="12" fill="#5b6470">{esc(label)}</text>')
        s.append(f'<g><title>{esc(arm)}: {fmt(v, dec)} {UNIT[key]}, sd {fmt(sd_of(data[arm], key), dec)}, n = {data[arm]["n"]}</title>'
                 f'<circle cx="{x(v):.1f}" cy="{y}" r="7" fill="#fff"/><circle cx="{x(v):.1f}" cy="{y}" r="5" fill="{color}"/></g>')
        # the value label, right of the dot; the headline arm's label sits above its connector. A white
        # halo (a stroked copy under the inked text) keeps it readable over the band and the connector.
        # It flips to the left of the dot when it would run into the annotation column on the right.
        label_w = 8 * (len(fmt(v, dec)) + 1)
        left = x(v) + 10 + label_w > W - R
        lx, anchor = (x(v) - 10, 'end') if left else (x(v) + 10, 'start')
        ly = y - 9 if arm == head_arm else y + 4
        s.append(f'<text x="{lx:.1f}" y="{ly}" text-anchor="{anchor}" font-size="12" fill="none" stroke="#fff" stroke-width="4">{fmt(v, dec)}</text>')
        s.append(f'<text x="{lx:.1f}" y="{ly}" text-anchor="{anchor}" font-size="12" fill="#1b1f23">{fmt(v, dec)}</text>')
    hv = mean_of(head, key)
    delta = hv - rv
    pct = delta / rv * 100
    verdict = 'beyond' if abs(delta) > bw else 'inside'
    yh = top + row_h * [a for a, _ in arms].index(head_arm) + row_h / 2
    hl, rl = dict(arms)[head_arm], dict(arms)[ref_arm]
    s.append(f'<text x="{W - R + 6}" y="{yh - 9}" font-size="11" fill="#1b1f23">{esc(hl)} vs {esc(rl)}</text>')
    s.append(f'<text x="{W - R + 6}" y="{yh + 4}" font-size="11" fill="#1b1f23">{signed(delta, dec)} {UNIT[key]} ({signed(pct, 1)} %)</text>')
    s.append(f'<text x="{W - R + 6}" y="{yh + 17}" font-size="11" fill="#1b1f23">{verdict} the band</text>')
    ay = top + row_h * n + 8
    s.append(f'<line x1="{L}" y1="{ay}" x2="{W - R}" y2="{ay}" stroke="#d0d7de"/>')
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        s.append(f'<line x1="{x(v):.1f}" y1="{ay}" x2="{x(v):.1f}" y2="{ay + 4}" stroke="#d0d7de"/><text x="{x(v):.1f}" y="{ay + 16}" text-anchor="middle" font-size="10" fill="#5b6470">{fmt(v, dec)}</text>')
    s.append('</svg>')
    # the take-away: every non-reference arm against the reference
    parts = []
    for arm, label in arms:
        if arm == ref_arm:
            continue
        v = mean_of(data[arm], key)
        b = band_of(ref, data[arm], key)
        d = v - rv
        word = 'beyond' if abs(d) > b else 'inside'
        unit = 'TPS' if key == 'tps' else 's'
        parts.append(f"{label} is {signed(d, dec)} {unit} ({signed(d / rv * 100, 1)} %) against {rl}, {word} the {fmt(b, 2)} {unit} band")
    take = '. '.join(parts) + '.'
    return f'<div class="panel"><h3>{PANEL_TITLE[key]} (band {fmt(bw, 2)} {UNIT[key]} for {esc(hl)} vs {esc(rl)})</h3>{"".join(s)}<p class="take">{esc(take)}</p></div>'


def group_html(g, paired_rows):
    cells, paired = load_group(g)
    out = [f'<h2>{esc(g["name"])}</h2>']
    if g.get('intro'):
        out.append(f'<p>{esc(g["intro"])}</p>')
    labels = dict(g['arms'])
    out.append('<p class="legend">' + ''.join(
        f'<span><i class="dot" style="background:{COLORS[l]}"></i>{esc(a)} = {esc(l)}{esc(g.get("arm_notes", {}).get(a, ""))}</span>' for a, l in g['arms'])
        + f'<span><i class="swatch"></i>band around {esc(labels[g["reference"]])}</span></p>')
    for key in sorted(cells, key=lambda k: (k[1], cells[k]['meta']['tp'], cells[k]['meta']['prompt'])):
        cell = cells[key]
        out.append(f'<p class="cellhead">{esc(cell_name(cell["meta"]))}, {esc(key[1])} attention</p>')
        out.append(f'<div class="cellrow">{panel(g, cell, "tps", paired)}{panel(g, cell, "ttft", paired)}</div>')
        for a, b in g['pairs']:
            p = paired.get((key[0], key[1], a, b))
            if not p or a not in cell['arms'] or b not in cell['arms']:
                continue
            ca, cb = cell['arms'][a], cell['arms'][b]
            for m in ('tps', 'ttft'):
                bw = band_of(cb, ca, m)
                d = mean_of(ca, m) - mean_of(cb, m)
                st = p['tps'] if m == 'tps' else p['ttft_s']
                paired_rows.append((g['name'], cell_name(cell['meta']) + ', ' + key[1], f"{labels[a]} vs {labels[b]}", m, d, d / mean_of(cb, m) * 100, bw,
                                    'beyond' if abs(d) > bw else 'inside', st['t'], st['n']))
    # the arm table of this group
    rows = []
    for key in sorted(cells, key=lambda k: (k[1], cells[k]['meta']['tp'], cells[k]['meta']['prompt'])):
        cell = cells[key]
        tds = []
        for a, l in g['arms']:
            c = cell['arms'].get(a)
            tds.append(f'<td class="num">{fmt(c["tps_mean"], 2)} ({fmt(c["tps_sd"], 2)})</td>' if c else '<td class="num">no run</td>')
        for a, l in g['arms']:
            c = cell['arms'].get(a)
            tds.append(f'<td class="num">{fmt(c["ttft_mean"], 3)} ({fmt(c["ttft_sd"], 3)})</td>' if c else '<td class="num">no run</td>')
        rows.append(f'<tr><td>{esc(cell_name(cell["meta"]))}, {esc(key[1])}</td>{"".join(tds)}</tr>')
    head = '<tr><th>Cell</th>' + ''.join(f'<th class="num">{esc(l)} TPS</th>' for a, l in g['arms']) + ''.join(f'<th class="num">{esc(l)} TTFT s</th>' for a, l in g['arms']) + '</tr>'
    out.append(f'<p class="cap">Per arm: mean over the repetitions (sample standard deviation). TPS = decode tokens per second per user. TTFT = prefill time in seconds, the maximum over the users.</p>')
    out.append(f'<div class="tablewrap"><table>{head}{"".join(rows)}</table></div>')
    return '\n'.join(out)


CSS = """
  :root { --bg:#ffffff; --ink:#1b1f23; --muted:#5b6470; --line:#d0d7de; --panel:#f6f8fa; --band:#e6eaef; --short:#f3f7fb; --accent:#0072B2; color-scheme: light; }
  html { background:var(--bg); }
  body { margin:0; padding-block:24px; padding-inline:16px; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; max-width:1040px; margin-inline:auto; }
  h1 { font-size:22px; margin:0 0 8px; text-wrap:balance; } h2 { font-size:17px; margin:30px 0 8px; } h3 { font-size:15px; margin:0 0 2px; }
  .short { border-left:4px solid var(--accent); padding:8px 12px; background:var(--short); margin:12px 0 18px; }
  .legend { display:flex; flex-wrap:wrap; gap:6px 18px; margin:8px 0 12px; font-size:14px; }
  .dot { display:inline-block; width:11px; height:11px; border-radius:50%; vertical-align:middle; margin-right:5px; }
  .swatch { display:inline-block; width:14px; height:11px; background:var(--band); border:1px solid var(--line); vertical-align:middle; margin-right:5px; }
  .cellrow { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px; margin:10px 0 14px; }
  @media (max-width:720px) { .cellrow { grid-template-columns:1fr; } }
  .panel { border:1px solid var(--line); border-radius:6px; padding:10px 12px 6px; min-width:0; }
  .panel svg { width:100%; height:auto; display:block; }
  .take { color:var(--muted); font-size:13.5px; margin:4px 0 0; } .cap { color:var(--muted); font-size:13px; }
  .cellhead { font-weight:600; margin:18px 0 0; }
  .tablewrap { overflow-x:auto; }
  table { border-collapse:collapse; width:100%; font-size:13.5px; } th, td { border:1px solid var(--line); padding:5px 7px; text-align:left; vertical-align:top; } th { background:var(--panel); }
  td.num, th.num { text-align:right; white-space:nowrap; }
  dl dt { font-weight:600; margin-top:6px; } dl dd { margin:0 0 4px 0; }
  ul { padding-left:22px; } li { margin:3px 0; }
  code { font-size:13px; background:var(--panel); padding:0 3px; border-radius:3px; }
"""


def main():
    cfg = json.load(open(sys.argv[1]))
    paired_rows = []
    groups = [group_html(g, paired_rows) for g in cfg['groups']]
    pairs_table = ['<tr><th>Group</th><th>Cell</th><th>Pair</th><th>Measure</th><th class="num">Difference</th><th class="num">Percent</th><th class="num">Band</th><th>Verdict</th><th class="num">Paired t (n)</th></tr>']
    for gname, cname, pair, m, d, pct, bw, verdict, t, n in paired_rows:
        unit = 'TPS' if m == 'tps' else 's'
        dec = DEC[m]
        pairs_table.append(f'<tr><td>{esc(gname)}</td><td>{esc(cname)}</td><td>{esc(pair)}</td><td>{"TPS" if m == "tps" else "TTFT"}</td><td class="num">{signed(d, dec)} {unit}</td><td class="num">{signed(pct, 1)} %</td><td class="num">{fmt(bw, 2)} {unit}</td><td>{verdict}</td><td class="num">{signed(t, 1)} ({n})</td></tr>')
    words = ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k, v in cfg['words'])
    notes = ''.join(f'<li>{esc(n)}</li>' for n in cfg.get('notes', []))
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(cfg['title'])}</title>
<style>{CSS}</style>
</head>
<body>
<h1>{esc(cfg['heading'])}</h1>
<div class="short"><b>Short version.</b> {esc(cfg['short'])}</div>
<p class="cap">{esc(cfg.get('caption', 'Each panel has its own axis, which does not start at zero. A dot is the mean of the repetitions. The shaded band is twice the larger sample standard deviation of the reference arm and the headline arm, at least 0.40 TPS or 0.15 s. A difference beyond the band counts as a change.'))}</p>
{''.join(groups)}
<h2>What this means</h2>
<ul>{notes}</ul>
<h2>Pairs</h2>
<p class="cap">Difference of the means (first arm minus second), the percentage of the second arm, the band of the pair, the verdict, and the paired t over the repetition pairs (its sign matters only when the band is crossed).</p>
<div class="tablewrap"><table>{''.join(pairs_table)}</table></div>
<h2>Words used here</h2>
<dl>{words}</dl>
<p class="cap">{esc(cfg.get('records', ''))}</p>
</body>
</html>
"""
    open(sys.argv[2], 'w').write(page)
    print(f"wrote {sys.argv[2]}: {len(cfg['groups'])} groups, {len(paired_rows)} pair rows")


if __name__ == '__main__':
    main()
