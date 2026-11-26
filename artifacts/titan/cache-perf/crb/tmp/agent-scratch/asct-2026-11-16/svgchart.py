"""svgchart.py - small inline-SVG chart helpers for the ASCT cross-check report.
Light theme only. Marks follow the dataviz skill: 2 px lines, markers r >= 4 with a 2 px surface ring,
bars at most 24 px thick with a rounded data end, hairline solid grid, text in ink colors (never series color),
a legend for two or more series, and a hover or focus tooltip on every mark (class "hit", attribute data-tip)."""
import html
import math

INK = '#0b0b0b'
INK2 = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
AXIS = '#c3c2b7'
SURFACE = '#fcfcfb'
OLD = '#2a78d6'      # categorical slot 1: old read loop
NEW = '#eb6834'      # categorical slot 2: new read loop
ASCT = '#1baf7a'     # categorical slot 3: ASCT read loop
CONTEXT = '#898781'  # other machines, context only


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(v, nd=1):
    return f'{v:.{nd}f}'


class Scale:
    def __init__(self, d0, d1, r0, r1, log=False):
        self.d0, self.d1, self.r0, self.r1, self.log = d0, d1, r0, r1, log

    def __call__(self, v):
        if self.log:
            t = (math.log(v) - math.log(self.d0)) / (math.log(self.d1) - math.log(self.d0))
        else:
            t = (v - self.d0) / (self.d1 - self.d0)
        return self.r0 + t * (self.r1 - self.r0)


def text(x, y, s, size=12, fill=INK2, anchor='start', weight=None, extra=''):
    w = f' font-weight="{weight}"' if weight else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}{extra}>{esc(s)}</text>'


def hit_circle(x, y, tip, r=12):
    return (f'<circle class="hit" tabindex="0" cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="transparent" '
            f'data-tip="{esc(tip)}"><title>{esc(tip)}</title></circle>')


def hit_rect(x, y, w, h, tip):
    return (f'<rect class="hit" tabindex="0" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="transparent" '
            f'data-tip="{esc(tip)}"><title>{esc(tip)}</title></rect>')


def marker(x, y, color, hollow=False, r=4.5):
    if hollow:
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{SURFACE}" stroke="{color}" stroke-width="2"/>'
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 1}" fill="{color}" stroke="{SURFACE}" stroke-width="2"/>'


def legend(items, x, y, gap=18):
    """items: (label, color, kind) with kind 'line', 'thin', 'dot', 'hollow', 'bar'."""
    out, cx = [], x
    for label, color, kind in items:
        if kind == 'bar':
            out.append(f'<rect x="{cx}" y="{y - 9}" width="12" height="10" rx="2" fill="{color}"/>')
            tx = cx + 17
        else:
            sw = 1.2 if kind == 'thin' else 2
            if kind in ('line', 'thin'):
                out.append(f'<line x1="{cx}" y1="{y - 4}" x2="{cx + 22}" y2="{y - 4}" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>')
            if kind in ('line', 'dot'):
                out.append(marker(cx + 11, y - 4, color, r=3.5))
            if kind == 'hollow':
                out.append(f'<line x1="{cx}" y1="{y - 4}" x2="{cx + 22}" y2="{y - 4}" stroke="{color}" stroke-width="2"/>')
                out.append(marker(cx + 11, y - 4, color, hollow=True, r=3.5))
            tx = cx + 28
        out.append(text(tx, y, label, 12, INK2))
        cx = tx + 7.0 * len(label) + gap
    return ''.join(out)


def frame(w, h, title, desc):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(title)}" '
            f'font-family="system-ui, -apple-system, Segoe UI, sans-serif"><title>{esc(title)}</title><desc>{esc(desc)}</desc>'
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="{SURFACE}"/>')


def y_axis(sy, ticks, x0, x1, unit=None, nd=0):
    out = []
    for t in ticks:
        y = sy(t)
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(text(x0 - 6, y + 4, fmt(t, nd), 11, MUTED, 'end', extra=' style="font-variant-numeric:tabular-nums"'))
    if unit:
        out.append(text(x0 - 34, sy(ticks[-1]) - 12, unit, 11, MUTED))
    return ''.join(out)


def line_panel(x0, y0, pw, ph, series, xticks, yticks, xlog=True, xlabel=None, yunit=None, title=None,
               vmark=None, ynd=0, xfmt=None, labels=()):
    """One plot panel. series: dict(name, color, pts=[(x, y, lo, hi, tip)], kind='line'|'thin'|'hollow', nomarker).
    vmark: (x value, label) draws a vertical reference line. labels: (x, y, text, dx, dy, anchor) direct labels."""
    sx = Scale(xticks[0][0], xticks[-1][0], x0, x0 + pw, log=xlog)
    sy = Scale(yticks[0], yticks[-1], y0 + ph, y0)
    out = [y_axis(sy, yticks, x0, x0 + pw, yunit, ynd)]
    out.append(f'<line x1="{x0}" y1="{y0 + ph}" x2="{x0 + pw}" y2="{y0 + ph}" stroke="{AXIS}" stroke-width="1"/>')
    for xv, lab in xticks:
        if lab is None:
            continue
        out.append(f'<line x1="{sx(xv):.1f}" y1="{y0 + ph}" x2="{sx(xv):.1f}" y2="{y0 + ph + 4}" stroke="{AXIS}" stroke-width="1"/>')
        out.append(text(sx(xv), y0 + ph + 16, lab, 11, MUTED, 'middle'))
    if xlabel:
        out.append(text(x0 + pw / 2, y0 + ph + 32, xlabel, 11, MUTED, 'middle'))
    if title:
        out.append(text(x0, y0 - 12, title, 13, INK, weight=600))
    if vmark:
        xv, lab = vmark
        out.append(f'<line x1="{sx(xv):.1f}" y1="{y0}" x2="{sx(xv):.1f}" y2="{y0 + ph}" stroke="{AXIS}" stroke-width="1"/>')
        out.append(text(sx(xv) + 4, y0 + 10, lab, 11, INK2))
    hits = []
    for s in series:
        pts = [p for p in s['pts'] if p[1] is not None]
        if not pts:
            continue
        sw = 1.2 if s.get('kind') == 'thin' else 2
        d = ' '.join(f'{"M" if i == 0 else "L"}{sx(p[0]):.1f},{sy(p[1]):.1f}' for i, p in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{s["color"]}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>')
        for p in pts:
            if p[2] is not None and p[3] is not None and abs(sy(p[2]) - sy(p[3])) > 3:
                out.append(f'<line x1="{sx(p[0]):.1f}" y1="{sy(p[2]):.1f}" x2="{sx(p[0]):.1f}" y2="{sy(p[3]):.1f}" stroke="{s["color"]}" stroke-width="1.2" opacity="0.55"/>')
        if not s.get('nomarker'):
            for p in pts:
                out.append(marker(sx(p[0]), sy(p[1]), s['color'], hollow=s.get('kind') == 'hollow', r=3.2))
        for p in pts:
            if len(p) > 4 and p[4]:
                hits.append(hit_circle(sx(p[0]), sy(p[1]), p[4], r=9))
    for lx, ly, lt, dx, dy, anchor in labels:
        out.append(text(sx(lx) + dx, sy(ly) + dy, lt, 11, INK, anchor, weight=600))
    return ''.join(out) + ''.join(hits)


def dumbbell(w, rows, x0, x1, ticks, unit, title, desc, key, rowh=40, top=58, nd=1, note=None):
    """rows: dict(label, sub, a, b, ca, cb, tipa, tipb, delta). key: (label a, label b). a, b in data units."""
    h = top + rowh * len(rows) + 46
    sx = Scale(ticks[0], ticks[-1], x0, x1)
    out = [frame(w, h, title, desc)]
    out.append(f'<circle cx="{x0 + 5}" cy="16" r="5" fill="{SURFACE}" stroke="{INK2}" stroke-width="2"/>' + text(x0 + 16, 20, key[0], 12, INK2))
    kx = x0 + 30 + 7 * len(key[0])
    out.append(f'<circle cx="{kx + 5}" cy="16" r="5.5" fill="{INK2}"/>' + text(kx + 16, 20, key[1], 12, INK2))
    for t in ticks:
        out.append(f'<line x1="{sx(t):.1f}" y1="{top - 14}" x2="{sx(t):.1f}" y2="{top + rowh * len(rows) - 8}" stroke="{GRID}" stroke-width="1"/>')
        out.append(text(sx(t), top + rowh * len(rows) + 8, fmt(t, 0), 11, MUTED, 'middle'))
    out.append(text((x0 + x1) / 2, top + rowh * len(rows) + 26, unit, 11, MUTED, 'middle'))
    hits = []
    for i, r in enumerate(rows):
        y = top + rowh * i + 6
        out.append(text(12, y + 1, r['label'], 12.5, INK, weight=600))
        if r.get('sub'):
            out.append(text(12, y + 15, r['sub'], 11, MUTED))
        xa, xb = sx(r['a']), sx(r['b'])
        out.append(f'<line x1="{xa:.1f}" y1="{y}" x2="{xb:.1f}" y2="{y}" stroke="{r["cb"]}" stroke-width="2" opacity="0.45"/>')
        out.append(f'<circle cx="{xa:.1f}" cy="{y}" r="5" fill="{SURFACE}" stroke="{r["ca"]}" stroke-width="2"/>')
        out.append(f'<circle cx="{xb:.1f}" cy="{y}" r="6.5" fill="{r["cb"]}" stroke="{SURFACE}" stroke-width="2"/>')
        la, lb = fmt(r['a'], nd), fmt(r['b'], nd)
        left, right = (xa, la), (xb, lb)
        if xa > xb:
            left, right = (xb, lb), (xa, la)
        out.append(text(left[0] - 10, y + 4, left[1], 11.5, INK, 'end', extra=' style="font-variant-numeric:tabular-nums"'))
        out.append(text(right[0] + 10, y + 4, right[1], 11.5, INK, 'start', extra=' style="font-variant-numeric:tabular-nums"'))
        if r.get('delta'):
            out.append(text(w - 12, y + 4, r['delta'], 12, INK, 'end', weight=600))
        hits.append(hit_circle(xa, y, r['tipa']))
        hits.append(hit_circle(xb, y, r['tipb']))
    if note:
        out.append(text(12, h - 6, note, 11, MUTED))
    return ''.join(out) + ''.join(hits) + '</svg>'


def hbars(w, rows, x0, x1, ticks, unit, title, desc, rowh=34, top=20, nd=0, bands=()):
    """rows: dict(label, sub, v, lo, hi, color, tip, value_label). bands: (from, to, label) shaded reference ranges."""
    h = top + rowh * len(rows) + 44
    sx = Scale(ticks[0], ticks[-1], x0, x1)
    out = [frame(w, h, title, desc)]
    for a, b, lab in bands:
        out.append(f'<rect x="{sx(a):.1f}" y="{top - 6}" width="{sx(b) - sx(a):.1f}" height="{rowh * len(rows) + 4}" fill="{GRID}" opacity="0.55"/>')
        out.append(text((sx(a) + sx(b)) / 2, top + rowh * len(rows) + 30, lab, 10.5, MUTED, 'middle'))
    for t in ticks:
        out.append(f'<line x1="{sx(t):.1f}" y1="{top - 6}" x2="{sx(t):.1f}" y2="{top + rowh * len(rows) - 2}" stroke="{GRID}" stroke-width="1"/>')
        out.append(text(sx(t), top + rowh * len(rows) + 12, fmt(t, 0), 11, MUTED, 'middle'))
    out.append(f'<line x1="{x0}" y1="{top - 6}" x2="{x0}" y2="{top + rowh * len(rows) - 2}" stroke="{AXIS}" stroke-width="1"/>')
    out.append(text(x1, top + rowh * len(rows) + 30, unit, 11, MUTED, 'end'))
    hits = []
    for i, r in enumerate(rows):
        y = top + rowh * i
        bh = 16
        out.append(text(12, y + 9, r['label'], 12.5, INK, weight=600))
        if r.get('sub'):
            out.append(text(12, y + 23, r['sub'], 10.5, MUTED))
        xe = sx(r['v'])
        rr = 4
        out.append(f'<path d="M{x0},{y} H{xe - rr:.1f} Q{xe:.1f},{y} {xe:.1f},{y + rr} V{y + bh - rr} Q{xe:.1f},{y + bh} {xe - rr:.1f},{y + bh} H{x0} Z" fill="{r["color"]}"/>')
        if r.get('lo') is not None and r.get('hi') is not None and r['hi'] > r['lo']:
            out.append(f'<line x1="{sx(r["lo"]):.1f}" y1="{y + bh / 2}" x2="{sx(r["hi"]):.1f}" y2="{y + bh / 2}" stroke="{INK}" stroke-width="1.5"/>')
            for e in (r['lo'], r['hi']):
                out.append(f'<line x1="{sx(e):.1f}" y1="{y + 3}" x2="{sx(e):.1f}" y2="{y + bh - 3}" stroke="{INK}" stroke-width="1.5"/>')
        lx = max(xe, sx(r['hi']) if r.get('hi') is not None else xe) + 8
        out.append(text(lx, y + 12, r.get('value_label') or fmt(r['v'], nd), 12, INK, extra=' style="font-variant-numeric:tabular-nums"'))
        hits.append(hit_rect(x0, y - 4, x1 - x0, bh + 8, r['tip']))
    return ''.join(out) + ''.join(hits) + '</svg>'
