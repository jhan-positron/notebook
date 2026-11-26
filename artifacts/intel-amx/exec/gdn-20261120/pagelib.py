#!/usr/bin/env python3
"""Page helpers for gdn-amx-design.html (gdn-20261120): CSS, SVG chart builders, and an ASCII check.

Every builder returns an SVG string with explicit fills, so the figures read the same in a browser and in the
cairosvg render check. Text inside SVG is plain ASCII or numeric character references.
Colors follow the entity, not the chart: GDN = blue, full attention = orange, AMX result = green,
everything else = gray, the serial (critical) path = red.
"""
import html
import zlib

C = {
    "bg": "#f6f7f9", "surface": "#ffffff", "ink": "#131722", "ink2": "#434b59", "muted": "#687180",
    "line": "#dde1e7", "grid": "#e9ecf0", "gdn": "#2a78d6", "attn": "#eb6834", "amx": "#1baf7a",
    "other": "#a3abb6", "crit": "#d43d3c", "note": "#eef4fc", "fpga": "#7d6fd0",
}
FONT = "Inter, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'DejaVu Sans Mono', Menlo, monospace"

CSS = """
/* Layout: one reading column of about 70 characters; figures may use the full 980 px sheet. */
:root {
  color-scheme: light;
  --bg: #f6f7f9; --surface: #ffffff; --ink: #131722; --ink-2: #434b59; --muted: #687180;
  --line: #dde1e7; --gdn: #2a78d6; --attn: #eb6834; --amx: #1baf7a; --other: #a3abb6; --crit: #d43d3c;
  --note: #eef4fc; --warn: #fff6e5; --warn-line: #e8b44c;
  --font-body: Inter, "Helvetica Neue", Arial, sans-serif;
  --font-head: "Space Grotesk", Inter, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "JetBrains Mono", "DejaVu Sans Mono", Menlo, monospace;
}
html { background: var(--bg); }
body { background: var(--bg); color: var(--ink); font-family: var(--font-body); font-size: 16px; line-height: 1.55;
  margin: 0; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.sheet { max-width: 980px; margin: 0 auto; }
.col { max-width: 760px; }
h1 { font-family: var(--font-head); font-size: 34px; line-height: 1.15; margin: 0 0 6px; letter-spacing: -0.01em; text-wrap: balance; }
h2 { font-family: var(--font-head); font-size: 24px; line-height: 1.2; margin: 44px 0 10px; padding-top: 18px; border-top: 2px solid var(--ink); text-wrap: balance; }
h3 { font-family: var(--font-head); font-size: 18px; margin: 26px 0 6px; text-wrap: balance; }
h4 { font-family: var(--font-head); font-size: 15.5px; line-height: 1.3; margin: 18px 0 4px; }
figcaption ul, td ul, li ul { margin: 4px 0 0; }
td:not(:last-child) > ul { min-width: 110px; }
p { margin: 8px 0; }
ul, ol { margin: 6px 0 10px; padding-left: 22px; }
li { margin: 3px 0; }
.meta { color: var(--muted); font-size: 14px; margin: 0 0 18px; }
.short { background: var(--surface); border: 1px solid var(--line); border-left: 5px solid var(--gdn); padding: 14px 18px; margin: 16px 0; }
.short h2 { border: 0; margin: 0 0 6px; padding: 0; font-size: 18px; }
.note { background: var(--note); border: 1px solid #cfe0f6; padding: 10px 14px; margin: 12px 0; font-size: 15px; }
.warn { background: var(--warn); border: 1px solid var(--warn-line); padding: 10px 14px; margin: 12px 0; font-size: 15px; }
details { background: var(--surface); border: 1px solid var(--line); padding: 8px 14px; margin: 12px 0; }
details > summary { cursor: pointer; font-weight: 600; font-family: var(--font-head); }
details[open] > summary { margin-bottom: 6px; }
figure { margin: 18px 0; background: var(--surface); border: 1px solid var(--line); padding: 14px 14px 10px; }
figure .scroll { overflow-x: auto; }
figure svg { display: block; width: 100%; height: auto; min-width: 640px; }
figcaption { color: var(--ink-2); font-size: 14px; margin-top: 8px; }
figcaption b { color: var(--ink); }
.take { font-weight: 600; color: var(--ink); }
.tablewrap { overflow-x: auto; margin: 12px 0; }
table { border-collapse: collapse; font-size: 14px; background: var(--surface); min-width: 520px; }
th, td { border: 1px solid var(--line); padding: 6px 10px; text-align: left; vertical-align: top; }
th { background: #eef0f3; font-family: var(--font-head); font-weight: 600; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
th.n { white-space: normal; }
table { line-height: inherit; }
table.prose th:last-child { min-width: min(400px, calc(100vw - 56px)); }
body, table { font-feature-settings: "calt" 0; }
.nw { white-space: nowrap; }
.short { box-sizing: border-box; }
code, .mono { font-family: var(--font-mono); font-size: 0.88em; background: #eceff3; padding: 1px 4px; border-radius: 3px; }
pre { font-family: var(--font-mono); font-size: 13px; line-height: 1.45; background: var(--surface); color: var(--ink); border: 1px solid var(--line); padding: 12px 14px; overflow-x: auto; margin: 12px 0; }
pre code { background: none; padding: 0; color: inherit; font-size: inherit; }
.key { display: inline-block; width: 11px; height: 11px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.est { color: var(--muted); font-style: italic; }
.ref { color: var(--muted); font-size: 0.85em; white-space: nowrap; }
.refs li { font-size: 14px; overflow-wrap: anywhere; }
.toc { columns: 2; column-gap: 28px; font-size: 15px; padding-left: 20px; }
@media (max-width: 640px) { .toc { columns: 1; } h1 { font-size: 27px; } figure svg { min-width: 880px; } }
"""


def esc(s):
    """Escape for SVG/HTML text and force ASCII (numeric character references)."""
    return html.escape(str(s), quote=True).encode("ascii", "xmlcharrefreplace").decode("ascii")


def text(x, y, s, size=12, fill=None, anchor="start", weight=400, mono=False, italic=False):
    fam = MONO if mono else FONT
    st = f"fill:{fill or C['ink']}"
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}"'
            f'{it} text-anchor="{anchor}" style="{st}">{esc(s)}</text>')


def rect(x, y, w, h, fill, stroke=None, rx=0, dash=None, sw=1, title=None, opacity=None):
    a = f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" fill="{fill}"'
    if stroke:
        a += f' stroke="{stroke}" stroke-width="{sw}"'
    if rx:
        a += f' rx="{rx}"'
    if dash:
        a += f' stroke-dasharray="{dash}"'
    if opacity is not None:
        a += f' fill-opacity="{opacity}"'
    if title:
        return a + f'><title>{esc(title)}</title></rect>'
    return a + "/>"


def line(x1, y1, x2, y2, stroke=None, sw=1, dash=None, marker=None):
    a = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke or C["ink"]}" stroke-width="{sw}"'
    if dash:
        a += f' stroke-dasharray="{dash}"'
    if marker:
        a += f' marker-end="url(#{marker})"'
    return a + "/>"


def arrow_defs(uid, color=None):
    col = color or C["ink2"]
    return (f'<defs><marker id="{uid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker></defs>')


def svg_open(w, h, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="{C["surface"]}"/>')


def figure(svg, caption, fid=None):
    i = f' id="{fid}"' if fid else ""
    return f'<figure{i}><div class="scroll">{svg}</div><figcaption>{caption}</figcaption></figure>'


def nice_ticks(vmax, n=5):
    """Round tick step so that about n ticks cover [0, vmax]."""
    import math
    if vmax <= 0:
        return [0, 1]
    raw = vmax / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    ticks = []
    v = 0.0
    while v <= vmax * 1.0001:
        ticks.append(round(v, 10))
        v += step
    if ticks[-1] < vmax:
        ticks.append(round(ticks[-1] + step, 10))
    return ticks


def fmt(v, digits=None):
    """Compact number: 1234.5 -> 1,234; 12.34 -> 12.3; 0.1234 -> 0.123."""
    if digits is not None:
        return f"{v:,.{digits}f}"
    a = abs(v)
    if a >= 100:
        return f"{v:,.0f}"
    if a >= 10:
        return f"{v:,.1f}"
    if a >= 1:
        return f"{v:,.2f}"
    return f"{v:,.3f}"


def hbars(rows, unit, label, width=960, bar_h=22, gap=10, left=250, right=150, xmax=None, group_gap=14, xlabel=None):
    """Horizontal bars with direct value labels.
    rows: list of dicts {label, value, color, note (optional text after the value), group (optional), hatch (bool = estimate)}.
    A new 'group' value inserts extra space and a group heading.
    """
    vmax = xmax or max(r["value"] for r in rows) * 1.0
    ticks = nice_ticks(vmax)
    vmax = ticks[-1]
    plot_w = width - left - right
    y = 34
    body = []
    last_group = object()
    ys = []
    for r in rows:
        g = r.get("group")
        if g != last_group and g is not None:
            y += group_gap if ys else 0
            body.append(text(10, y + 4, g, size=12.5, weight=600, fill=C["ink"]))
            y += 18
            last_group = g
        ys.append(y)
        y += bar_h + gap
    h = y + 34
    out = [svg_open(width, h, label)]
    hatch_ids = {}
    for r in rows:
        if r.get("hatch") and r["color"] not in hatch_ids:
            hid = f"hatch{len(hatch_ids)}_{zlib.crc32(label.encode()) % 100000}"
            hatch_ids[r["color"]] = hid
            out.append(f'<defs><pattern id="{hid}" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">'
                       f'<rect width="6" height="6" fill="{C["surface"]}"/><rect width="3" height="6" fill="{r["color"]}"/></pattern></defs>')
    for t in ticks:
        x = left + plot_w * t / vmax
        out.append(line(x, 22, x, h - 30, stroke=C["grid"]))
        out.append(text(x, h - 14, fmt(t) if t else "0", size=11, fill=C["muted"], anchor="middle"))
    out.append(text(left + plot_w, 14, xlabel or unit, size=11, fill=C["muted"], anchor="end"))
    out.extend(body)
    for r, yy in zip(rows, ys):
        w = plot_w * r["value"] / vmax
        fill = r["color"]
        out.append(text(left - 8, yy + bar_h * 0.68, r["label"], size=12.5, anchor="end", fill=C["ink"]))
        if r.get("hatch"):
            out.append(f'<rect x="{left:.1f}" y="{yy:.1f}" width="{w:.1f}" height="{bar_h}" fill="url(#{hatch_ids[fill]})" stroke="{fill}" stroke-width="1.2" rx="3">'
                       f'<title>{esc(r["label"])}: {fmt(r["value"])} {esc(unit)} (est.)</title></rect>')
        else:
            out.append(rect(left, yy, w, bar_h, fill, rx=3, title=f'{r["label"]}: {fmt(r["value"])} {unit}'))
        lab = f'{fmt(r["value"])} {unit}' + (f'  {r["note"]}' if r.get("note") else "")
        out.append(text(left + w + 6, yy + bar_h * 0.68, lab, size=12.5, weight=600, fill=C["ink"]))
    out.append(line(left, 22, left, h - 30, stroke=C["ink2"]))
    out.append("</svg>")
    return "".join(out)


def stacked(rows, parts, unit, label, width=960, bar_h=34, gap=30, left=210, right=40, xlabel=None, normalize=False):
    """Horizontal stacked bars to a common scale. rows: [{label, sub (small text), values: {part: v}}];
    parts: [(key, display name, color)]. Each segment is labeled with its value when it is wide enough."""
    totals = [sum(r["values"].get(k, 0.0) for k, _, _ in parts) for r in rows]
    if normalize:
        return _stacked_share(rows, parts, totals, unit, label, width, bar_h, gap, left, right, xlabel)
    ticks = nice_ticks(max(totals))
    vmax = ticks[-1]
    plot_w = width - left - right
    h = 58 + len(rows) * (bar_h + gap) + 24
    out = [svg_open(width, h, label)]
    lx = left
    for k, name, col in parts:
        out.append(rect(lx, 8, 12, 12, col, rx=2))
        out.append(text(lx + 17, 18.5, name, size=12, fill=C["ink2"]))
        lx += 17 + 7.0 * len(name) + 22
    top = 36
    for t in ticks:
        x = left + plot_w * t / vmax
        out.append(line(x, top, x, h - 30, stroke=C["grid"]))
        out.append(text(x, h - 14, fmt(t) if t else "0", size=11, fill=C["muted"], anchor="middle"))
    out.append(text(left + plot_w, h - 2, xlabel or unit, size=11, fill=C["muted"], anchor="end"))
    y = top + 10
    for r, tot in zip(rows, totals):
        out.append(text(left - 8, y + bar_h * 0.45, r["label"], size=12.5, anchor="end", weight=600))
        if r.get("sub"):
            out.append(text(left - 8, y + bar_h * 0.45 + 15, r["sub"], size=11, anchor="end", fill=C["muted"]))
        x = left
        for k, name, col in parts:
            v = r["values"].get(k, 0.0)
            w = plot_w * v / vmax
            if w <= 0:
                continue
            out.append(rect(x + 1, y, max(w - 2, 0.5), bar_h, col, rx=2,
                            title=f'{r["label"]} - {name}: {fmt(v)} {unit} ({100.0 * v / tot:.0f} % of {fmt(tot)} {unit})'))
            if w > 62:
                out.append(text(x + w / 2, y + bar_h * 0.47, f"{fmt(v)} {unit}", size=11.5, anchor="middle", fill="#ffffff", weight=600))
                out.append(text(x + w / 2, y + bar_h * 0.47 + 13, f"{100.0 * v / tot:.0f} %", size=10.5, anchor="middle", fill="#ffffff"))
            x += w
        out.append(text(x + 6, y + bar_h * 0.62, f"{fmt(tot)} {unit}", size=12.5, weight=600))
        y += bar_h + gap
    out.append(line(left, top, left, h - 30, stroke=C["ink2"]))
    out.append("</svg>")
    return "".join(out)


def _labels_above(items, y, xmin, xmax, size=11):
    """Labels above a bar with the top edge y, for the segments that are too narrow for an inside label.
    items: [(center x of the segment, label text, segment color)], from left to right.
    A label sits over its segment when there is room. Otherwise it moves sideways: it stays between xmin and xmax
    and clear of the label next to it. A short leader line joins the label and its segment."""
    half = [0.3 * size * len(s) + 3 for _, s, _ in items]
    xs = [cx for cx, _, _ in items]
    for i in range(len(xs)):
        xs[i] = max(xs[i], (xs[i - 1] + half[i - 1] if i else xmin) + half[i])
    for i in reversed(range(len(xs))):
        xs[i] = min(xs[i], (xs[i + 1] - half[i + 1] if i + 1 < len(xs) else xmax) - half[i])
    out = []
    for (cx, s, col), tx in zip(items, xs):
        out.append(line(tx, y - 7.5, cx, y - 0.5, stroke=col, sw=1.2))
        out.append(text(tx, y - 10, s, size=size, anchor="middle", weight=600))
    return out


def _stacked_share(rows, parts, totals, unit, label, width, bar_h, gap, left, right, xlabel):
    """Every row is scaled to the full width (100 %). Segments carry their absolute value and their share:
    inside the segment when it is wide enough, above the bar with a leader line when it is not."""
    plot_w = width - left - right
    h = 58 + len(rows) * (bar_h + gap) + 18
    out = [svg_open(width, h, label)]
    lx = left
    for k, name, col in parts:
        out.append(rect(lx, 8, 12, 12, col, rx=2))
        out.append(text(lx + 17, 18.5, name, size=12, fill=C["ink2"]))
        lx += 17 + 7.0 * len(name) + 22
    top = 36
    for t in (0, 25, 50, 75, 100):
        x = left + plot_w * t / 100.0
        out.append(line(x, top, x, h - 28, stroke=C["grid"]))
        out.append(text(x, h - 12, f"{t} %", size=11, fill=C["muted"], anchor="middle"))
    out.append(text(left + plot_w + right - 4, top - 6, xlabel or "total", size=11, fill=C["muted"], anchor="end"))
    y = top + 10
    for r, tot in zip(rows, totals):
        out.append(text(left - 8, y + bar_h * 0.45, r["label"], size=12.5, anchor="end", weight=600))
        if r.get("sub"):
            out.append(text(left - 8, y + bar_h * 0.45 + 15, r["sub"], size=11, anchor="end", fill=C["muted"]))
        x = left
        narrow = []
        for k, name, col in parts:
            v = r["values"].get(k, 0.0)
            w = plot_w * v / tot
            if w <= 0:
                continue
            out.append(rect(x + 1, y, max(w - 2, 0.5), bar_h, col, rx=2,
                            title=f'{r["label"]} - {name}: {fmt(v)} {unit} ({100.0 * v / tot:.0f} % of {fmt(tot)} {unit})'))
            if w > 58:
                out.append(text(x + w / 2, y + bar_h * 0.44, f"{100.0 * v / tot:.0f} %", size=12, anchor="middle", fill="#ffffff", weight=600))
                out.append(text(x + w / 2, y + bar_h * 0.44 + 13, f"{fmt(v)} {unit}", size=10.5, anchor="middle", fill="#ffffff"))
            else:
                narrow.append((x + w / 2, f"{100.0 * v / tot:.0f} %, {fmt(v)} {unit}", col))
            x += w
        out.extend(_labels_above(narrow, y, left, left + plot_w))
        out.append(text(left + plot_w + 8, y + bar_h * 0.62, f"{fmt(tot)} {unit}", size=12.5, weight=600))
        y += bar_h + gap
    out.append(line(left, top, left, h - 28, stroke=C["ink2"]))
    out.append("</svg>")
    return "".join(out)


def rel_dots(rows, label, axis_label, width=960, row_h=56, left=200, right=150, xmin=0.0, xmax=100.0, step=20.0,
             a_name="measured today", m_name=None, b_name="predicted (est.)", better="lower", a_dot=True):
    """Dot plot on a relative axis: today's value is 100 %. rows: [{label, a_text, b, b_lo, b_hi, b_text, m, m_text, delta_text}],
    where b, m, b_lo, b_hi are percent of today's value and the *_text fields are the absolute values with units.
    a_dot=False draws no dot for today's value. Use it when every b is 100 %: the b dot would hide the dot of today's value.
    The dotted line at 100 % then stands for today's value, and the legend key shows that line."""
    plot_w = width - left - right
    h = 46 + len(rows) * row_h + 42
    X = lambda v: left + plot_w * (v - xmin) / (xmax - xmin)
    out = [svg_open(width, h, label)]
    a_col, m_col, b_col = C["ink2"], C["gdn"], C["amx"]
    lx = left
    a_key = f'<circle cx="{lx + 6}" cy="14" r="6" fill="{a_col}"/>' if a_dot else line(lx + 6, 6, lx + 6, 22, stroke=a_col, dash="3 3")
    out.append(a_key + text(lx + 17, 18.5, a_name, size=12, fill=C["ink2"]))
    lx += 17 + 6.8 * len(a_name) + 24
    if m_name:
        out.append(f'<circle cx="{lx + 6}" cy="14" r="5" fill="{C["surface"]}" stroke="{m_col}" stroke-width="2.4"/>' + text(lx + 17, 18.5, m_name, size=12, fill=C["ink2"]))
        lx += 17 + 6.6 * len(m_name) + 24
    out.append(f'<circle cx="{lx + 6}" cy="14" r="6" fill="{b_col}"/>' + text(lx + 17, 18.5, b_name, size=12, fill=C["ink2"]))
    top = 34
    t = xmin
    while t <= xmax + 1e-9:
        x = X(t)
        out.append(line(x, top, x, h - 38, stroke=C["ink2"] if abs(t - 100.0) < 1e-9 else C["grid"], dash="3 3" if abs(t - 100.0) < 1e-9 else None))
        out.append(text(x, h - 22, f"{t:g} %", size=11, fill=C["muted"], anchor="middle"))
        t += step
    out.append(text(left + plot_w, h - 6, axis_label, size=11, fill=C["muted"], anchor="end"))
    y = top + row_h / 2 + 2
    for r in rows:
        out.append(text(left - 12, y + 4, r["label"], size=12.5, anchor="end", weight=600))
        xa, xb = X(100.0), X(r["b"])
        out.append(line(X(r["b_lo"]), y, X(r["b_hi"]), y, stroke=b_col, sw=8).replace("/>", ' stroke-opacity="0.28" stroke-linecap="round"/>'))
        out.append(line(xa, y, xb, y, stroke=C["ink2"], sw=1.4))
        if m_name and "m" in r:
            xm = X(r["m"])
            out.append(f'<circle cx="{xm:.1f}" cy="{y:.1f}" r="5.5" fill="{C["surface"]}" stroke="{m_col}" stroke-width="2.4"><title>{esc(r["label"])} {esc(m_name)}: {esc(r["m_text"])}</title></circle>')
            out.append(text(xm, y + 22, r["m_text"], size=11, anchor="middle", fill=m_col, weight=600))
        if a_dot:
            out.append(f'<circle cx="{xa:.1f}" cy="{y:.1f}" r="7" fill="{a_col}" stroke="{C["surface"]}" stroke-width="2"><title>{esc(r["label"])} {esc(a_name)}: {esc(r["a_text"])}</title></circle>')
        b_tip = f'{r["label"]} {b_name}' + (f': {r["b_text"]}' if r["b_text"] else "")
        out.append(f'<circle cx="{xb:.1f}" cy="{y:.1f}" r="7" fill="{b_col}" stroke="{C["surface"]}" stroke-width="2"><title>{esc(b_tip)}</title></circle>')
        if better == "lower":
            out.append(text(xa + 12, y - 11, r["a_text"], size=11.5, anchor="start", fill=C["ink2"]))
        else:
            out.append(text(xa - 12, y - 11, r["a_text"], size=11.5, anchor="end", fill=C["ink2"]))
        if r["b_text"]:
            out.append(text(xb, y - 13, r["b_text"], size=11.5, anchor="middle", weight=600))
        out.append(text(left + plot_w + 22, y + 4, r["delta_text"], size=13, weight=600, fill="#0e7d55"))
        y += row_h
    out.append("</svg>")
    return "".join(out)


def dumbbell(rows, unit, label, width=960, row_h=46, left=250, right=170, xmin=0.0, xmax=None, a_name="today", b_name="predicted",
             a_col=None, b_col=None, better="lower", m_name=None, m_col=None):
    """Paired dots per row: a = measured today, b = predicted. The gap is annotated with the change in percent.
    rows: [{label, sub, a, b, b_lo, b_hi (optional range of the prediction)}]."""
    a_col = a_col or C["other"]
    b_col = b_col or C["amx"]
    vals = [v for r in rows for v in (r["a"], r["b"], r.get("b_lo", r["b"]), r.get("b_hi", r["b"]))]
    ticks = nice_ticks((xmax or max(vals)) - xmin)
    span = ticks[-1]
    plot_w = width - left - right
    h = 50 + len(rows) * row_h + 34
    X = lambda v: left + plot_w * (v - xmin) / span
    out = [svg_open(width, h, label)]
    out.append(f'<circle cx="{left + 6}" cy="14" r="6" fill="{a_col}"/>' + text(left + 17, 18.5, a_name, size=12, fill=C["ink2"]))
    off = left + 17 + 7.0 * len(a_name) + 24
    m_col = m_col or C["gdn"]
    if m_name:
        out.append(f'<circle cx="{off + 6}" cy="14" r="5" fill="{C["surface"]}" stroke="{m_col}" stroke-width="2.4"/>' + text(off + 17, 18.5, m_name, size=12, fill=C["ink2"]))
        off += 17 + 6.6 * len(m_name) + 24
    out.append(f'<circle cx="{off + 6}" cy="14" r="6" fill="{b_col}"/>' + text(off + 17, 18.5, b_name, size=12, fill=C["ink2"]))
    top = 34
    for t in ticks:
        x = left + plot_w * t / span
        out.append(line(x, top, x, h - 30, stroke=C["grid"]))
        out.append(text(x, h - 14, fmt(t + xmin) if (t + xmin) else "0", size=11, fill=C["muted"], anchor="middle"))
    out.append(text(left + plot_w, h - 2, unit, size=11, fill=C["muted"], anchor="end"))
    y = top + row_h / 2 + 4
    for r in rows:
        out.append(text(left - 10, y + 1, r["label"], size=12.5, anchor="end", weight=600))
        if r.get("sub"):
            out.append(text(left - 10, y + 15, r["sub"], size=11, anchor="end", fill=C["muted"]))
        xa, xb = X(r["a"]), X(r["b"])
        if "b_lo" in r and "b_hi" in r:
            out.append(line(X(r["b_lo"]), y, X(r["b_hi"]), y, stroke=b_col, sw=7))
            out[-1] = out[-1].replace("/>", ' stroke-opacity="0.28" stroke-linecap="round"/>')
        out.append(line(xa, y, xb, y, stroke=C["ink2"], sw=1.5))
        if m_name and "m" in r:
            xm = X(r["m"])
            out.append(f'<circle cx="{xm:.1f}" cy="{y:.1f}" r="5.5" fill="{C["surface"]}" stroke="{m_col}" stroke-width="2.4"><title>{esc(r["label"])} {esc(m_name)}: {fmt(r["m"])} {esc(unit)} (est.)</title></circle>')
            out.append(text(xm, y + 21, fmt(r["m"]), size=11, anchor="middle", fill=m_col, weight=600))
        out.append(f'<circle cx="{xa:.1f}" cy="{y:.1f}" r="7" fill="{a_col}" stroke="{C["surface"]}" stroke-width="2"><title>{esc(r["label"])} {esc(a_name)}: {fmt(r["a"])} {esc(unit)}</title></circle>')
        out.append(f'<circle cx="{xb:.1f}" cy="{y:.1f}" r="7" fill="{b_col}" stroke="{C["surface"]}" stroke-width="2"><title>{esc(r["label"])} {esc(b_name)}: {fmt(r["b"])} {esc(unit)} (est.)</title></circle>')
        pct = 100.0 * (r["b"] - r["a"]) / r["a"] if r["a"] else 0.0
        la, lb = (xa, xb)
        # value labels sit outside the pair, the change sits right of the row
        if xa <= xb:
            out.append(text(xa - 11, y - 11, fmt(r["a"]), size=11.5, anchor="end", fill=C["ink2"]))
            out.append(text(xb + 11, y - 11, fmt(r["b"]), size=11.5, anchor="start", weight=600))
        else:
            out.append(text(xb - 11, y - 11, fmt(r["b"]), size=11.5, anchor="end", weight=600))
            out.append(text(xa + 11, y - 11, fmt(r["a"]), size=11.5, anchor="start", fill=C["ink2"]))
        out.append(text(left + plot_w + 14, y + 4, f"{pct:+.0f} % (est.)", size=13, weight=600,
                        fill=C["amx"] if ((pct < 0) == (better == "lower") and abs(pct) >= 0.5) else C["ink2"]))
        y += row_h
    out.append("</svg>")
    return "".join(out)


def lines_chart(series, xlabel, ylabel, label, width=960, height=380, left=70, right=210, top=24, bottom=46, xticks=None, yticks=None,
                marks=None):
    """Line chart, one axis. series: [{name, color, pts: [(x, y)], dash (optional)}]; direct labels at the right end.
    marks: [(x, text)] vertical guide lines."""
    xs = [p[0] for s in series for p in s["pts"]]
    ys = [p[1] for s in series for p in s["pts"]]
    xt = xticks or nice_ticks(max(xs))
    yt = yticks or nice_ticks(max(ys))
    xmax, ymax = xt[-1], yt[-1]
    pw, ph = width - left - right, height - top - bottom
    X = lambda v: left + pw * v / xmax
    Y = lambda v: top + ph * (1 - v / ymax)
    out = [svg_open(width, height, label)]
    for t in yt:
        out.append(line(left, Y(t), left + pw, Y(t), stroke=C["grid"]))
        out.append(text(left - 8, Y(t) + 4, fmt(t) if t else "0", size=11, fill=C["muted"], anchor="end"))
    for t in xt:
        out.append(text(X(t), top + ph + 16, f"{int(t):,}", size=11, fill=C["muted"], anchor="middle"))
    out.append(text(left + pw / 2, height - 8, xlabel, size=12, fill=C["ink2"], anchor="middle"))
    out.append(text(left, 14, ylabel, size=12, fill=C["ink2"]))
    for mx, mt in (marks or []):
        out.append(line(X(mx), top, X(mx), top + ph, stroke=C["muted"], dash="3 3"))
        out.append(text(X(mx) + 4, top + 12, mt, size=11, fill=C["muted"]))
    ends = []
    for s in series:
        d = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in s["pts"])
        dash = f' stroke-dasharray="{s["dash"]}"' if s.get("dash") else ""
        out.append(f'<polyline points="{d}" fill="none" stroke="{s["color"]}" stroke-width="2.4"{dash} stroke-linejoin="round"><title>{esc(s["name"])}</title></polyline>')
        ex, ey = s["pts"][-1]
        out.append(f'<circle cx="{X(ex):.1f}" cy="{Y(ey):.1f}" r="4" fill="{s["color"]}" stroke="{C["surface"]}" stroke-width="2"/>')
        ends.append([Y(ey), s, ey])
    # spread the end labels so that they do not collide
    ends.sort(key=lambda e: e[0])
    for i in range(1, len(ends)):
        if ends[i][0] - ends[i - 1][0] < 30:
            ends[i][0] = ends[i - 1][0] + 30
    for yy, s, ey in ends:
        out.append(rect(left + pw + 12, yy - 9, 10, 10, s["color"], rx=2))
        out.append(text(left + pw + 27, yy, s["name"], size=12, weight=600))
        out.append(text(left + pw + 27, yy + 14, s.get("endlabel", fmt(ey)), size=11, fill=C["muted"]))
    out.append(line(left, top, left, top + ph, stroke=C["ink2"]))
    out.append(line(left, top + ph, left + pw, top + ph, stroke=C["ink2"]))
    out.append("</svg>")
    return "".join(out)


def assert_ascii(page):
    bad = sorted({ch for ch in page if ord(ch) > 127})
    if bad:
        raise SystemExit("non-ASCII characters in the page: " + " ".join(f"U+{ord(c):04X}" for c in bad[:20]))
