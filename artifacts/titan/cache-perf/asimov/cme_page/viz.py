"""SVG chart builders for the CME page.

Every builder takes plain Python lists and returns one SVG string.
No builder reads a file.  All text is ASCII (a non-ASCII label raises).
Every data mark carries data-tip="..." for the hover tooltip that the
page shell (shell.py) shows with one inline script.

Light theme only.  Series colors are fixed (see COLORS).
Usage examples for every function: API.md in this folder.
"""
import html
import math

# ---------------------------------------------------------------- colors

COLORS = {
    'f2': '#2a78d6',    # boot F2 (prefetchers off): blue
    'f1': '#eb6834',    # boot F1 (prefetchers on): orange
    'core': '#1baf7a',  # the core on boot F1: aqua
    'alt': '#6250d6',   # a fourth series, only if unavoidable: violet
    'crit': '#e34948',  # critical-path slice of a lanes diagram only
    'ref': '#7d838c',   # reference lines and capacity markers: grey
    'work': '#5f6f82',  # solid work block of a lanes diagram: slate
}
INK = '#1c2024'      # primary text
INK2 = '#4a5058'     # secondary text
MUTED = '#6b7280'    # axis text, notes
GRID = '#e7e9ec'     # hairline grid
AXIS = '#b4bac2'     # axis rule
SURFACE = '#ffffff'
FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'

# Narrowest width a chart is drawn at, as a share of its viewBox width.  Below it the
# chart keeps this width and its .figwrap box scrolls sideways.  At 0.92 a 10 px label
# (the smallest in any chart) is drawn at 9.2 px.
MIN_SCALE = 0.92

# CSS that the shell puts in the page once (chart sizing, hover feedback of the marks).
CSS = """
.figwrap{overflow-x:auto;max-width:100%%}
svg.viz{display:block;max-width:100%%;min-width:var(--vmin,0);height:auto;font-family:%s}
@media print{.figwrap{overflow:visible} svg.viz{min-width:0}}
svg.viz .hit{fill:#000;fill-opacity:0}
svg.viz .hit:hover{fill-opacity:.045}
svg.viz .mk:hover{stroke:%s;stroke-width:1.5}
svg.viz .row:hover .rowbg{fill-opacity:.045}
svg.viz .rowbg{fill:#000;fill-opacity:0}
""" % (FONT, INK)

_uid = [0]


def _next_id(prefix):
    _uid[0] += 1
    return '%s%d' % (prefix, _uid[0])


def color(c):
    """Series key ('f2', 'f1', 'core', 'alt', ...) or a hex string -> hex."""
    if c is None:
        return COLORS['f2']
    return COLORS.get(c, c)


# ------------------------------------------------------- format helpers

def num(v, digits=3):
    """Number with a fixed count of decimals and thousands commas."""
    if v is None:
        return 'n/a'
    return '{:,.{d}f}'.format(v, d=digits)


def ns(v, digits=3):
    """Nanoseconds: ns(21.0051) -> '21.005 ns'."""
    return 'n/a' if v is None else num(v, digits) + ' ns'


def gbps(v, digits=1):
    """Gigabytes per second: gbps(52.34) -> '52.3 GB/s'."""
    return 'n/a' if v is None else num(v, digits) + ' GB/s'


def ratio(v, digits=2):
    """A ratio: ratio(2.142) -> '2.14 x'."""
    return 'n/a' if v is None else num(v, digits) + ' x'


def pct(v, digits=1):
    """A percentage from a value already in percent: pct(12.34) -> '12.3 %'."""
    return 'n/a' if v is None else num(v, digits) + ' %'


def signed(v, digits=3, unit=''):
    """A signed difference: signed(12.3, 1, 'ns') -> '+12.3 ns'."""
    if v is None:
        return 'n/a'
    s = '{:+,.{d}f}'.format(v, d=digits)
    return s + (' ' + unit if unit else '')


def size_label(nbytes):
    """Byte count -> '64 B', '4 KiB', '1.5 MiB', '2 GiB'."""
    if nbytes is None:
        return 'n/a'
    for lim, name in ((1 << 30, 'GiB'), (1 << 20, 'MiB'), (1 << 10, 'KiB')):
        if nbytes >= lim:
            v = nbytes / lim
            s = ('%.2f' % v).rstrip('0').rstrip('.')
            return s + ' ' + name
    return '%d B' % nbytes


# -------------------------------------------------------- text helpers

_NARROW = set("iljtfI.,:;'|![]() ")
_WIDE = set('mwMW@%')


def tw(s, size=12, bold=False):
    """Estimated width of a text in px (on the wide side, to keep clear)."""
    w = 0.0
    for ch in str(s):
        if ch in _NARROW:
            w += 0.36
        elif ch in _WIDE:
            w += 0.92
        elif ch.isupper():
            w += 0.70
        elif ch.isdigit():
            w += 0.62
        else:
            w += 0.58
    return w * size * (1.07 if bold else 1.0)


def _ascii(s):
    s = str(s)
    try:
        s.encode('ascii')
    except UnicodeEncodeError:
        raise ValueError('non-ASCII text in an SVG label: %r' % s)
    return s


def _e(s):
    return html.escape(_ascii(s), quote=True)


def _tip(s):
    """data-tip attribute.  Lines are split by a newline in the text."""
    if not s:
        return ''
    return ' data-tip="%s"' % html.escape(_ascii(s), quote=True).replace('\n', '&#10;')


def _text(x, y, s, size=12, anchor='start', fill=INK2, weight=None, halo=False,
          rotate=None, extra=''):
    a = ['x="%.1f"' % x, 'y="%.1f"' % y, 'font-size="%g"' % size, 'fill="%s"' % fill]
    if anchor != 'start':
        a.append('text-anchor="%s"' % anchor)
    if weight:
        a.append('font-weight="%s"' % weight)
    if halo:
        a.append('stroke="%s" stroke-width="3.5" stroke-linejoin="round" paint-order="stroke"' % SURFACE)
    if rotate is not None:
        a.append('transform="rotate(%g %.1f %.1f)"' % (rotate, x, y))
    return '<text %s%s>%s</text>' % (' '.join(a), extra, _e(s))


def _trect(x, y, w, size=12, anchor='start', pad=2):
    """Bounding box (x0, y0, x1, y1) of a text drawn at baseline (x, y)."""
    if anchor == 'middle':
        x0 = x - w / 2
    elif anchor == 'end':
        x0 = x - w
    else:
        x0 = x
    return (x0 - pad, y - size * 0.82 - pad, x0 + w + pad, y + size * 0.24 + pad)


def wrap(s, maxw, size=12):
    """Split a text into lines no wider than maxw px (word wrap)."""
    out = []
    for para in str(s).split('\n'):
        cur = ''
        for word in para.split(' '):
            t = (cur + ' ' + word).strip()
            if cur and tw(t, size) > maxw:
                out.append(cur)
                cur = word
            else:
                cur = t
        out.append(cur)
    return out


class _Placer:
    """Keeps the boxes already taken, so that labels do not overlap.
    Hard boxes are data marks and texts.  Soft boxes are thin grey marker lines:
    a label may sit on one only when no other place is free."""

    def __init__(self, bounds):
        self.b = bounds
        self.rects = []
        self.soft = []

    def add(self, r, soft=False):
        (self.soft if soft else self.rects).append(r)

    def free(self, r, soft_ok=False):
        b = self.b
        if r[0] < b[0] or r[1] < b[1] or r[2] > b[2] or r[3] > b[3]:
            return False
        for q in (self.rects if soft_ok else self.rects + self.soft):
            if r[0] < q[2] and q[0] < r[2] and r[1] < q[3] and q[1] < r[3]:
                return False
        return True

    def hit(self, x, y):
        """True when the point lies in a taken hard box."""
        return any(q[0] <= x <= q[2] and q[1] <= y <= q[3] for q in self.rects)

    def take(self, cands):
        """Index of the first free candidate box.  The box is then taken.
        When none is free the first candidate is used (and taken)."""
        for soft_ok in (False, True):
            for i, r in enumerate(cands):
                if self.free(r, soft_ok):
                    self.add(r)
                    return i
        self.add(cands[0])
        return 0


def _svg(w, h, body, label):
    return ('<div class="figwrap"><svg class="viz" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" '
            'width="%g" height="%g" style="--vmin:%dpx" role="img" aria-label="%s" font-family=\'%s\'>'
            '%s</svg></div>') % (w, h, w, h, int(w * MIN_SCALE + 0.999), _e(label), FONT, ''.join(body))


# ------------------------------------------------------------- scales

def _nice_step(span, n=5):
    if span <= 0:
        return 1.0
    raw = span / max(n, 1)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag * (1 + 1e-9):
            return m * mag
    return 10 * mag


def _ticks(lo, hi, n=5):
    step = _nice_step(hi - lo, n)
    t = math.ceil(lo / step - 1e-9) * step
    out = []
    while t <= hi + step * 1e-6:
        out.append(0.0 if abs(t) < step * 1e-9 else t)
        t += step
    return out, step


def _tick_digits(step):
    d = max(0, -int(math.floor(math.log10(step) + 1e-9)))
    if abs(step * 10 ** d - round(step * 10 ** d)) > 1e-6:
        d += 1
    return d


def _lin_range(vals, rng, zero=True, n=5):
    """(lo, hi, ticks, digits) of a linear axis."""
    vals = [v for v in vals if v is not None]
    vmin, vmax = (min(vals), max(vals)) if vals else (0.0, 1.0)
    lo = hi = None
    if rng == 'fit':
        zero = False
    elif rng:
        lo, hi = rng
    if lo is None:
        lo = min(0.0, vmin) if zero else vmin
    if hi is None:
        hi = vmax + (vmax - lo) * 0.06 if vmax > lo else lo + 1.0
    auto_lo = (rng == 'fit')
    auto_hi = not rng or rng == 'fit' or rng[1] is None
    step = _nice_step(hi - lo, n)
    if auto_lo:
        lo = math.floor(lo / step + 1e-9) * step
    if auto_hi:
        hi = math.ceil(hi / step - 1e-9) * step
    ticks, step = _ticks(lo, hi, n)
    return lo, hi, ticks, _tick_digits(step)


class _X:
    """X scale: 'log2' or 'linear', mapped to the px range [p0, p1]."""

    def __init__(self, kind, lo, hi, p0, p1):
        self.kind, self.p0, self.p1 = kind, p0, p1
        self.lo, self.hi = self._t(lo), self._t(hi)
        if self.hi <= self.lo:
            self.hi = self.lo + 1.0

    def _t(self, v):
        return math.log2(v) if self.kind == 'log2' else float(v)

    def __call__(self, v):
        return self.p0 + (self._t(v) - self.lo) / (self.hi - self.lo) * (self.p1 - self.p0)


def _marker(shape, x, y, c, r=4.0, tip='', cls='mk'):
    ring = 'stroke="%s" stroke-width="2"' % SURFACE
    t = _tip(tip)
    if shape == 'square':
        s = r * 0.9
        return '<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" %s%s/>' % (
            cls, x - s, y - s, 2 * s, 2 * s, c, ring, t)
    if shape == 'diamond':
        s = r * 1.25
        return '<path class="%s" d="M%.1f %.1fL%.1f %.1fL%.1f %.1fL%.1f %.1fZ" fill="%s" %s%s/>' % (
            cls, x, y - s, x + s, y, x, y + s, x - s, y, c, ring, t)
    if shape == 'triangle':
        s = r * 1.2
        return '<path class="%s" d="M%.1f %.1fL%.1f %.1fL%.1f %.1fZ" fill="%s" %s%s/>' % (
            cls, x, y - s, x + s, y + s * 0.8, x - s, y + s * 0.8, c, ring, t)
    return '<circle class="%s" cx="%.1f" cy="%.1f" r="%.1f" fill="%s" %s%s/>' % (cls, x, y, r, c, ring, t)


def _norm_series(series):
    out = []
    for s in series:
        c = color(s.get('color'))
        pts = []
        for p in s.get('points', []):
            p = tuple(p)
            pts.append((p[0], p[1], p[2] if len(p) > 2 else None))
        shape = s.get('marker')
        if shape is None or shape is True:
            shape = 'diamond' if c == COLORS['alt'] else 'circle'
        d = dict(s)
        d.update(name=s.get('name', ''), color=c, points=pts, shape=shape,
                 line=s.get('line', True), markers=s.get('markers', len(pts) <= 48))
        out.append(d)
    return out


def _legend_items(ser):
    seen, out = set(), []
    for s in ser:
        if s['name'] and s['name'] not in seen:
            seen.add(s['name'])
            out.append((s['name'], s['color'], s['shape'], s['line'], bool(s.get('dash'))))
    return out


def _legend_row(items, x, y, maxw):
    """Legend drawn from (x, y).  Returns (svg pieces, height used)."""
    out, cx, cy = [], x, y
    for it in items:
        name, c = it[0], color(it[1])
        shape = it[2] if len(it) > 2 else 'circle'
        line = it[3] if len(it) > 3 else False
        w = ((40 if len(it) > 4 and it[4] else 30) if line else 16) + tw(name, 12) + 18
        if cx + w > x + maxw and cx > x:
            cx, cy = x, cy + 18
        if shape == 'swatch':
            out.append('<rect x="%.1f" y="%.1f" width="12" height="10" rx="2" fill="%s"/>' % (cx, cy - 9, c))
            tx = cx + 17
        elif shape == 'dashed':
            out.append('<rect x="%.1f" y="%.1f" width="12" height="10" rx="2" fill="none" stroke="%s" '
                       'stroke-width="1.2" stroke-dasharray="3 2"/>' % (cx, cy - 9, c))
            tx = cx + 17
        elif line:
            dashed = len(it) > 4 and it[4]
            lw_ = 34 if dashed else 24
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"%s/>' % (
                cx, cy - 4, cx + lw_, cy - 4, c, ' stroke-dasharray="6 4"' if dashed else ''))
            out.append(_marker(shape, cx + lw_ / 2.0, cy - 4, c, cls='lg'))
            tx = cx + lw_ + 6
        else:
            out.append(_marker(shape, cx + 6, cy - 4, c, r=4.5, cls='lg'))
            tx = cx + 16
        out.append(_text(tx, cy, name, 12, fill=INK2))
        cx += w
    return out, cy - y + 18


def legend(items, width=1040):
    """A legend alone, as an SVG.  items: [(name, color[, shape[, line]])]."""
    body, h = _legend_row(items, 2, 14, width - 4)
    return _svg(width, h + 4, body, 'legend')


def _vlabels(labs, L, R, size=11, gap=8):
    """Labels of vertical marker lines.  labs: [(px of the line, text)].
    Returns ([(row, text x, anchor)], row count).  A label is centred on its line,
    or set to one side of it, or moved up one row, so that it covers neither another
    label nor another marker line."""
    order = sorted(range(len(labs)), key=lambda i: labs[i][0])
    lines = [px for px, _ in labs]
    rows, out = {}, [None] * len(labs)
    for i in order:
        px, t = labs[i]
        if not t:
            out[i] = (0, px, 'middle')
            continue
        w = tw(t, size)
        found = None
        for r in range(len(labs) + 1):
            for anc, x0 in (('middle', px - w / 2), ('start', px + 5), ('end', px - 5 - w)):
                x0c = min(max(x0, L), R - w) if anc == 'middle' else x0
                if x0c < L - 1 or x0c + w > R + 1:
                    continue
                if any(x0c - gap < b and a < x0c + w + gap for a, b in rows.get(r, [])):
                    continue
                if any(j != i and x0c - 3 < lines[j] < x0c + w + 3 for j in range(len(labs))):
                    continue
                found = (r, x0c, anc)
                break
            if found:
                break
        if not found:
            r = (max(rows) + 1) if rows else 0
            found = (r, min(max(px - w / 2, L), R - w), 'middle')
        r, x0c, anc = found
        rows.setdefault(r, []).append((x0c, x0c + w))
        out[i] = (r, x0c, 'start')
    return out, ((max(rows) + 1) if rows else 0)


# --------------------------------------------------------- plot panel

def _x_domain(ser, xticks, vlines, xrange_, fits=True):
    xs = [p[0] for s in ser for p in s['points']]
    xs += [t[0] if isinstance(t, (tuple, list)) else t for t in (xticks or [])]
    xs += [v[0] for v in (vlines or [])]
    if xrange_:
        return xrange_
    return (min(xs), max(xs)) if xs else (0.0, 1.0)


def _panel(o):
    """Draw one plot.  o is a dict of options (see line_chart).  Returns svg pieces."""
    L, T, R, B = o['box']
    ser, xs = o['series'], o['xs']
    yfmt = o.get('yfmt') or (lambda v: num(v, 3))
    yunit = o.get('yunit', '')
    xfmt = o['xfmt']
    hlines = o.get('hlines') or []
    out = []

    yvals = [p[1] for s in ser for p in s['points'] if p[1] is not None]
    yvals += [h[0] for h in hlines]
    for s in ser:
        if s.get('fit') and s['points']:
            m, c = s['fit']
            x0, x1 = s.get('fit_range') or (min(p[0] for p in s['points']), max(p[0] for p in s['points']))
            yvals += [m * x0 + c, m * x1 + c]
    for g in o.get('gaps') or []:
        yvals += [g['y0'], g['y1']]
    lo, hi, yt, ydig = _lin_range(yvals, o.get('yrange'), n=max(3, int((B - T) / 55)))
    ytfmt = o.get('ytickfmt') or (lambda v: num(v, ydig))

    def Y(v):
        return B - (v - lo) / (hi - lo) * (B - T)

    # grid, axes, tick labels
    for t in yt:
        y = Y(t)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
            L, y, R, y, AXIS if abs(t - lo) < 1e-12 else GRID))
        out.append(_text(L - 8, y + 4, ytfmt(t), 11, 'end', MUTED))
    if abs(yt[0] - lo) > 1e-12:
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, B, R, B, AXIS))
    if o.get('ylabel'):
        out.append(_text(L - o.get('ylab_dx', 0), T - o['ylab_dy'], o['ylabel'], 12, fill=INK2, weight='600'))

    pl = _Placer((L, T - 2, R + o.get('right_room', 0), B))

    # x ticks
    xt = o['xticks']
    tick_px = [(xs(v), lab) for v, lab in xt]
    for px, lab in tick_px:
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (px, B, px, B + 4, AXIS))
    if o.get('xticklabels', True):
        mode = o.get('xtick_mode', 'auto')

        def clash(step):
            last = -1e9
            for i, (px, lab) in enumerate(tick_px):
                if i % step:
                    continue
                w = tw(lab, 11)
                if px - w / 2 < last + 8:
                    return True
                last = px + w / 2
            return False
        step, rot = 1, False
        if clash(1):
            if mode == 'rotate':
                rot = True
            elif mode == 'thin' or not clash(2):
                while clash(step):
                    step += 1
            else:
                rot = True
        for i, (px, lab) in enumerate(tick_px):
            if rot:
                out.append(_text(px + 3, B + 14, lab, 11, 'end', MUTED, rotate=-40))
            elif i % step == 0:
                w = tw(lab, 11)
                x = min(max(px, w / 2 + 1), o['width'] - w / 2 - 1)
                out.append(_text(x, B + 17, lab, 11, 'middle', MUTED))
        if o.get('xlabel'):
            out.append(_text((L + R) / 2, B + o['xlab_dy'], o['xlabel'], 12, 'middle', INK2))

    # vertical markers (capacities)
    vl = o.get('vlines') or []
    if vl:
        labs = [(xs(v[0]), v[1]) for v in vl]
        show = o.get('vlabels', True)
        place, _ = _vlabels(labs, L, R) if show else ([(0, 0, 'start')] * len(labs), 0)
        for (px, t), (r, tx, anc) in zip(labs, place):
            top = T - 4 - r * 14 if show else T
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
                px, B, px, top, COLORS['ref']))
            pl.add((px - 2.5, T, px + 2.5, B), soft=True)
        for (px, t), (r, tx, anc) in zip(labs, place):
            if show and t:
                out.append(_text(tx, T - 8 - r * 14, t, 11, anc, MUTED, halo=True))

    # hover bands (line series): one band per x value, all series in the tip
    line_ser = [s for s in ser if s['line']]
    tips_at = {}
    if line_ser:
        xvals = sorted({p[0] for s in line_ser for p in s['points']})
        pxs = [xs(v) for v in xvals]
        for i, v in enumerate(xvals):
            lines = [xfmt(v)]
            for s in line_ser:
                for p in s['points']:
                    if p[0] == v and p[1] is not None:
                        lines.append('%s: %s%s' % (s['name'], yfmt(p[1]), (' ' + yunit) if yunit else ''))
            tips_at[v] = '\n'.join(lines)
            a = L if i == 0 else (pxs[i - 1] + pxs[i]) / 2
            b = R if i == len(pxs) - 1 else (pxs[i] + pxs[i + 1]) / 2
            out.append('<rect class="hit" x="%.1f" y="%.1f" width="%.1f" height="%.1f"%s/>' % (
                a, T, max(b - a, 1), B - T, _tip(tips_at[v])))

    # horizontal reference lines
    for h in hlines:
        y = Y(h[0])
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
            L, y, R, y, COLORS['ref']))

    # lines and fits
    for s in ser:
        if s.get('fit') and s['points']:
            m, c = s['fit']
            x0, x1 = s.get('fit_range') or (min(p[0] for p in s['points']), max(p[0] for p in s['points']))
            n = 2 if xs.kind == 'linear' else 40
            pts = []
            for i in range(n):
                xv = x0 + (x1 - x0) * i / (n - 1)
                pts.append('%.1f,%.1f' % (xs(xv), Y(m * xv + c)))
            out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.5" stroke-opacity=".75"/>' % (
                ' '.join(pts), s['color']))
            s['_fit_end'] = (xs(x1), Y(m * x1 + c), xs(x0), Y(m * x0 + c))
        if not s['line']:
            continue
        seg = []
        for p in s['points'] + [(None, None, None)]:
            if p[1] is None:
                if len(seg) > 1:
                    dash = ' stroke-dasharray="6 4"' if s.get('dash') else ''
                    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" '
                               'stroke-linejoin="round" stroke-linecap="round" pointer-events="none"%s/>' % (
                                   ' '.join(seg), s['color'], dash))
                seg = []
            else:
                seg.append('%.1f,%.1f' % (xs(p[0]), Y(p[1])))

    # obstacles for the label placement: the marks themselves
    for s in ser:
        prev = None
        for p in s['points']:
            if p[1] is None:
                prev = None
                continue
            x, y = xs(p[0]), Y(p[1])
            pl.add((x - 5, y - 5, x + 5, y + 5))
            if prev and s['line']:
                d = math.hypot(x - prev[0], y - prev[1])
                k = int(d // 6)
                for i in range(1, k):
                    qx = prev[0] + (x - prev[0]) * i / k
                    qy = prev[1] + (y - prev[1]) * i / k
                    pl.add((qx - 2, qy - 2, qx + 2, qy + 2))
            prev = (x, y)
        if s.get('_fit_end'):
            x1, y1, x0, y0 = s['_fit_end']
            k = max(2, int(math.hypot(x1 - x0, y1 - y0) // 8))
            for i in range(k + 1):
                qx, qy = x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k
                pl.add((qx - 2, qy - 2, qx + 2, qy + 2))

    texts = []   # drawn last, above the marks

    # labels of the horizontal reference lines
    for h in hlines:
        if len(h) < 2 or not h[1]:
            continue
        y, t = Y(h[0]), h[1]
        w = tw(t, 11)
        side = h[2] if len(h) > 2 else 'right'
        xa = (R - 4, 'end') if side == 'right' else (L + 6, 'start')
        xb = (L + 6, 'start') if side == 'right' else (R - 4, 'end')
        cands = [(xa, y - 5), (xa, y + 13), (xb, y - 5), (xb, y + 13)]
        cands += [((L + (R - L) * f, 'middle'), y + dy) for f in (0.5, 0.75, 0.25, 0.62, 0.38)
                  for dy in (-5, 13)]
        i = pl.take([_trect(c[0][0], c[1], w, 11, c[0][1]) for c in cands])
        (x, anc), ty = cands[i if i is not None else 0]
        texts.append(_text(x, ty, t, 11, anc, MUTED, halo=True))
    for h in hlines:
        pl.add((L, Y(h[0]) - 1.5, R, Y(h[0]) + 1.5), soft=True)

    # note of a y axis that does not start at 0
    if abs(lo) > 1e-12 and not lo < 0 < hi:
        t = 'axis starts at %s%s' % (ytfmt(lo), (' ' + yunit) if yunit else '')
        w = tw(t, 11)
        cands = [(L + 6, B - 6, 'start'), (R - 6, B - 6, 'end'), (L + 6, T + 12, 'start')]
        i = pl.take([_trect(x, y, w, 11, a) for x, y, a in cands])
        x, y, a = cands[i if i is not None else 0]
        texts.append(_text(x, y, t, 11, a, MUTED, halo=True, extra=' font-style="italic"'))

    # gap brackets: the difference between two values at one x
    for g in o.get('gaps') or []:
        px, ya, yb = xs(g['x']) + g.get('dx', 0), Y(g['y0']), Y(g['y1'])
        out.append('<path d="M%.1f %.1fh8M%.1f %.1fv%.1fM%.1f %.1fh8" fill="none" stroke="%s" stroke-width="1.2"/>' % (
            px - 4, ya, px, ya, yb - ya, px - 4, yb, INK2))
        pl.add((px - 4, min(ya, yb), px + 4, max(ya, yb)))
        t = g['text']
        w = tw(t, 12, True)
        my = (ya + yb) / 2 + 4
        top_, bot_ = min(ya, yb), max(ya, yb)
        cands = [(px + sx, yy, anc) for yy in (my, my - 13, my + 13, top_ - 6, bot_ + 15, top_ - 20, bot_ + 29)
                 for sx, anc in ((8, 'start'), (-8, 'end'))]
        i = pl.take([_trect(x, y, w, 12, a) for x, y, a in cands])
        x, y, a = cands[i if i is not None else 0]
        texts.append(_text(x, y, t, 12, a, INK, weight='600', halo=True))

    # markers
    for s in ser:
        ptips = s.get('tips')
        for i, p in enumerate(s['points']):
            if p[1] is None:
                continue
            x, y = xs(p[0]), Y(p[1])
            if s['line']:
                tip = tips_at.get(p[0], '')
            else:
                tip = '%s%s\n%s: %s%s' % (s['name'], (' - ' + str(p[2])) if p[2] else '', xfmt(p[0]),
                                          yfmt(p[1]), (' ' + yunit) if yunit else '')
            if ptips and i < len(ptips) and ptips[i]:
                tip = (tip + '\n' + ptips[i]) if s['line'] else ptips[i]
            if not s['line']:
                out.append('<circle class="hit" cx="%.1f" cy="%.1f" r="12"%s/>' % (x, y, _tip(tip)))
            if s['markers'] or not s['line']:
                out.append(_marker(s['shape'], x, y, s['color'], r=s.get('size', 4.0), tip=tip))

    # direct labels
    want = []
    for si, s in enumerate(ser):
        pts = [p for p in s['points'] if p[1] is not None]
        sel = s.get('label')
        if sel and pts:
            if sel == 'last':
                sel = [pts[-1][0]]
            elif sel == 'first':
                sel = [pts[0][0]]
            elif sel == 'max':
                sel = [max(pts, key=lambda p: p[1])[0]]
            elif sel == 'min':
                sel = [min(pts, key=lambda p: p[1])[0]]
            elif sel == 'all':
                sel = [p[0] for p in pts]
            for xv in sel:
                want.append({'series': si, 'x': xv})
        if not s['line']:
            for p in pts:
                if p[2]:
                    want.append({'series': si, 'x': p[0], 'y': p[1], 'text': p[2]})
    for lab in o.get('labels') or []:
        if isinstance(lab, (tuple, list)):
            lab = dict(zip(('series', 'x', 'text'), lab))
        want.append(lab)
    for lab in want:
        s = ser[lab['series']]
        cand = [p for p in s['points'] if p[0] == lab['x'] and p[1] is not None
                and ('y' not in lab or p[1] == lab['y'])]
        if not cand:
            raise ValueError('label: series %r has no point at x=%r' % (s['name'], lab['x']))
        p = cand[0]
        t = lab.get('text') or (yfmt(p[1]) + ((' ' + yunit) if yunit else ''))
        x, y = xs(p[0]), Y(p[1])
        w = tw(t, 11)
        base = [('above', x, y - 9, 'middle'), ('below', x, y + 18, 'middle'),
                ('right', x + 9, y + 4, 'start'), ('left', x - 9, y + 4, 'end'),
                ('ur', x + 7, y - 8, 'start'), ('ul', x - 7, y - 8, 'end'),
                ('lr', x + 7, y + 16, 'start'), ('ll', x - 7, y + 16, 'end')]
        pos = lab.get('pos')
        if pos:
            base.sort(key=lambda c: c[0] != pos)
        far = [(n, x + (cx - x) * k, y + (cy - 4 - y) * k + 4, a) for k in (2.2, 3.4, 4.6)
               for n, cx, cy, a in base]
        cands = base + far
        i = None
        for soft_ok in (False, True):
            for k, (_, cx, cy, a) in enumerate(cands):
                r = _trect(cx, cy, w, 11, a)
                if not pl.free(r, soft_ok):
                    continue
                if k >= len(base):      # a far place: its leader line must not cross a text or a mark
                    ex, ey = min(max(x, r[0]), r[2]), min(max(y, r[1]), r[3])
                    d = math.hypot(ex - x, ey - y)
                    m = max(int(d // 3), 1)
                    if any(pl.hit(x + (ex - x) * j / m, y + (ey - y) * j / m) for j in range(4, m)):
                        continue
                i = k
                break
            if i is not None:
                break
        if i is None:
            i = 0
        pl.add(_trect(cands[i][1], cands[i][2], w, 11, cands[i][3]))
        _, cx, cy, a = cands[i]
        if i >= len(base):
            r = _trect(cx, cy, w, 11, a, pad=0)
            ex = min(max(x, r[0]), r[2])
            ey = min(max(y, r[1]), r[3])
            texts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
                x, y, ex, ey, MUTED))
        texts.append(_text(cx, cy, t, 11, a, INK, halo=True))

    # labels of the fitted lines
    for s in ser:
        if s.get('_fit_end') and s.get('fit_label'):
            x1, y1, x0, y0 = s['_fit_end']
            t = s['fit_label']
            w = tw(t, 11)
            cands = [(x1 - 4, y1 - 10, 'end'), (x1 - 4, y1 + 18, 'end'), (x0 + 4, y0 - 10, 'start'),
                     (x0 + 4, y0 + 18, 'start'), (x1 - 4, y1 - 26, 'end'), (x1 - 4, y1 + 34, 'end'),
                     ((x0 + x1) / 2, (y0 + y1) / 2 - 22, 'middle'), ((x0 + x1) / 2, (y0 + y1) / 2 + 30, 'middle')]
            i = pl.take([_trect(x, y, w, 11, a) for x, y, a in cands])
            x, y, a = cands[i if i is not None else 0]
            texts.append(_text(x, y, t, 11, a, INK2, halo=True))

    # annotations: a text with a leader line to a data position
    for an in o.get('annotations') or []:
        px, py = xs(an['x']), Y(an['y'])
        lines = an['text'].split('\n') if isinstance(an['text'], str) else list(an['text'])
        w = max(tw(t, 12) for t in lines)
        h = 15 * len(lines)

        def box(cx, cy):
            return (cx - w / 2 - 3, cy - h / 2 - 2, cx + w / 2 + 3, cy + h / 2 + 2)
        if 'dx' in an or 'dy' in an:
            cx, cy = px + an.get('dx', 0), py + an.get('dy', 0)
            pl.add(box(cx, cy))
        else:
            cands = []
            for rad in (46, 70, 96, 124, 156):
                for ang in (-90, -45, -135, 0, 180, 45, 135, 90):
                    a = math.radians(ang)
                    cands.append((px + math.cos(a) * (rad + w / 2 * abs(math.cos(a))),
                                  py + math.sin(a) * (rad + h / 2 * abs(math.sin(a)))))
            i = pl.take([box(cx, cy) for cx, cy in cands])
            cx, cy = cands[i if i is not None else 0]
        b = box(cx, cy)
        ex, ey = min(max(px, b[0]), b[2]), min(max(py, b[1]), b[3])
        d = math.hypot(ex - px, ey - py)
        if d > 8:
            sx, sy = px + (ex - px) * 6 / d, py + (ey - py) * 6 / d
            texts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
                sx, sy, ex, ey, INK2))
        for k, t in enumerate(lines):
            texts.append(_text(cx, cy - h / 2 + 12 + 15 * k, t, 12, 'middle', INK, halo=True))
    return out + texts


def _mk_xticks(xticks, ser, xkind, xfmt):
    if xticks is None:
        if xkind == 'log2':
            xticks = sorted({p[0] for s in ser for p in s['points']})
        else:
            xv = [p[0] for s in ser for p in s['points']]
            xticks = _ticks(min(xv), max(xv), 6)[0] if xv else []
    out = []
    for t in xticks:
        if isinstance(t, (tuple, list)):
            out.append((t[0], str(t[1])))
        else:
            out.append((t, xfmt(t)))
    return out


def _default_xfmt(xkind, xticks, ser):
    if xkind == 'log2':
        return size_label
    xv = [p[0] for s in ser for p in s['points']]
    step = _nice_step((max(xv) - min(xv)) if xv else 1, 6)
    d = _tick_digits(step)
    return lambda v: num(v, d)


def line_chart(series, x='log2', xticks=None, xlabel='', ylabel='', yunit='', hlines=None,
               vlines=None, labels=None, annotations=None, gaps=None, yrange=None, xrange=None,
               width=1040, height=380, show_legend=True, yfmt=None, xfmt=None, ytickfmt=None,
               xtick_mode='auto', title='line chart'):
    """Line chart.  See API.md for the fields of each argument."""
    ser = _norm_series(series)
    xfmt = xfmt or _default_xfmt(x, xticks, ser)
    xt = _mk_xticks(xticks, ser, x, xfmt)
    items = _legend_items(ser) if show_legend and len([s for s in ser if s['name']]) > 1 else []
    body = []
    top = 6
    if items:
        lg, lh = _legend_row(items, 0, top + 12, width)
        body += lg
        top += lh + 2
    if ylabel:
        top += 18
    vrows = 0
    if vlines:
        vrows = 3   # worst case; trimmed below
    yv = [p[1] for s in ser for p in s['points'] if p[1] is not None] + [h[0] for h in (hlines or [])]
    lo, hi, yt, ydig = _lin_range(yv, yrange)
    ytf = ytickfmt or (lambda v: num(v, ydig))
    L = max(46, max(tw(ytf(t), 11) for t in yt) + 14)
    R = width - 22
    lo_x, hi_x = _x_domain(ser, xt, vlines, xrange)
    xs = _X(x, lo_x, hi_x, L + 14, R - 14)
    if vlines:
        _, vrows = _vlabels([(xs(v[0]), v[1]) for v in vlines], L, R)
    T = top + vrows * 14 + 8
    rot = _would_rotate(xt, xs, xtick_mode)
    xb = (max(tw(l, 11) for _, l in xt) * 0.66 + 10) if rot else 22
    B = height - xb - (20 if xlabel else 4)
    body += _panel(dict(box=(L, T, R, B), series=ser, xs=xs, ylabel=ylabel, ylab_dy=vrows * 14 + 12,
                        ylab_dx=L, yunit=yunit, yfmt=yfmt, yrange=yrange, hlines=hlines, vlines=vlines,
                        xticks=xt, labels=labels, annotations=annotations, gaps=gaps, xfmt=xfmt,
                        xlabel=xlabel, xlab_dy=xb + 14, width=width, ytickfmt=ytickfmt,
                        xtick_mode=xtick_mode))
    return _svg(width, height, body, title)


def _would_rotate(xt, xs, mode):
    def clash(step):
        last = -1e9
        for i, (v, lab) in enumerate(xt):
            if i % step:
                continue
            w, px = tw(lab, 11), xs(v)
            if px - w / 2 < last + 8:
                return True
            last = px + w / 2
        return False
    if not clash(1):
        return False
    if mode == 'rotate':
        return True
    if mode == 'thin':
        return False
    return clash(2)


def small_multiples(panels, x='log2', xticks=None, xlabel='', vlines=None, width=1040,
                    panel_height=150, show_legend=True, xfmt=None, xrange=None, xtick_mode='auto',
                    title='small multiples'):
    """Panels stacked vertically that share the x axis.  Each panel: a dict with
    ylabel, series, and optionally yunit, yrange, hlines, labels, annotations, gaps, yfmt, height."""
    pans = [dict(p, series=_norm_series(p['series'])) for p in panels]
    allser = [s for p in pans for s in p['series']]
    xfmt = xfmt or _default_xfmt(x, xticks, allser)
    xt = _mk_xticks(xticks, allser, x, xfmt)
    items = _legend_items(allser) if show_legend and len({s['name'] for s in allser if s['name']}) > 1 else []
    body, top = [], 6
    if items:
        lg, lh = _legend_row(items, 0, top + 12, width)
        body += lg
        top += lh + 2
    L = 46
    for p in pans:
        yv = [q[1] for s in p['series'] for q in s['points'] if q[1] is not None] + [h[0] for h in p.get('hlines') or []]
        lo, hi, yt, ydig = _lin_range(yv, p.get('yrange'), n=max(3, int(p.get('height', panel_height) / 55)))
        f = p.get('ytickfmt') or (lambda v, d=ydig: num(v, d))
        L = max(L, max(tw(f(t), 11) for t in yt) + 14)
    R = width - 22
    lo_x, hi_x = _x_domain(allser, xt, vlines, xrange)
    xs = _X(x, lo_x, hi_x, L + 14, R - 14)
    vrows = 0
    if vlines:
        _, vrows = _vlabels([(xs(v[0]), v[1]) for v in vlines], L, R)
    rot = _would_rotate(xt, xs, xtick_mode)
    xb = (max(tw(l, 11) for _, l in xt) * 0.66 + 10) if rot else 22
    y = top
    for i, p in enumerate(pans):
        first, last = i == 0, i == len(pans) - 1
        extra = vrows * 14 if (first and vlines) else 0
        T = y + 18 + extra + 8
        B = T + p.get('height', panel_height)
        body += _panel(dict(box=(L, T, R, B), series=p['series'], xs=xs, ylabel=p.get('ylabel', ''),
                            ylab_dy=extra + 12, ylab_dx=L, yunit=p.get('yunit', ''), yfmt=p.get('yfmt'),
                            yrange=p.get('yrange'), hlines=p.get('hlines'), vlines=vlines, vlabels=first,
                            xticks=xt, xticklabels=last, labels=p.get('labels'),
                            annotations=p.get('annotations'), gaps=p.get('gaps'), xfmt=xfmt,
                            xlabel=xlabel if last else '', xlab_dy=xb + 14, width=width,
                            ytickfmt=p.get('ytickfmt'), xtick_mode=xtick_mode))
        y = B + (10 if not last else 0)
    h = y + xb + (20 if xlabel else 4)
    return _svg(width, h, body, title)


def scatter_fit(series, x='linear', xticks=None, xlabel='', ylabel='', yunit='', hlines=None,
                vlines=None, annotations=None, yrange=None, xrange=None, width=1040, height=360,
                show_legend=True, yfmt=None, xfmt=None, title='scatter with fitted line'):
    """Points with a fitted straight line per series.
    series: dicts with name, color, points [(x, y) or (x, y, label)], and optionally
    fit=(slope, intercept), fit_label, fit_range=(x0, x1), tips."""
    ser = [dict(s, line=s.get('line', False)) for s in series]
    return line_chart(ser, x=x, xticks=xticks, xlabel=xlabel, ylabel=ylabel, yunit=yunit, hlines=hlines,
                      vlines=vlines, annotations=annotations, yrange=yrange, xrange=xrange, width=width,
                      height=height, show_legend=show_legend, yfmt=yfmt, xfmt=xfmt, title=title)


# ------------------------------------------------- dumbbell and bars

_SUB_PX = 11      # size of a row's sub label


def _label_col(rows, maxw):
    w = 0
    for r in rows:
        t = r.get('header') or r.get('label', '')
        size = 12
        lines = wrap(t, maxw, size)
        r['_lines'] = lines
        w = max(w, max(tw(l, size, bool(r.get('header'))) for l in lines))
        if r.get('sub'):
            r['_sub'] = wrap(r['sub'], maxw, _SUB_PX)
            w = max(w, max(tw(l, _SUB_PX) for l in r['_sub']))
    return w


def _row_text(r, x, ymid):
    """Row label (wrapped) and optional sub label, centred on ymid."""
    out = []
    lines = r['_lines']
    sub = r.get('_sub') or []
    total = 14 * len(lines) + 12 * len(sub)
    y = ymid - total / 2 + 11
    for l in lines:
        out.append(_text(x, y, l, 12, fill=INK, weight='600' if r.get('header') else None))
        y += 14
    y -= 1
    for l in sub:
        out.append(_text(x, y, l, _SUB_PX, fill=MUTED))
        y += 12
    return out


def _row_h(r, base):
    return max(base, 14 * len(r['_lines']) + 12 * len(r.get('_sub') or []) + 8)


def _haxis(body, L, R, T, B, lo, hi, ticks, tfmt, xlabel, unit, note_zero=True):
    def X(v):
        return L + (v - lo) / (hi - lo) * (R - L)
    for t in ticks:
        px = X(t)
        body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
            px, T, px, B, AXIS if abs(t - lo) < 1e-12 and lo == 0 else GRID))
        body.append(_text(px, B + 16, tfmt(t), 11, 'middle', MUTED))
    body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, B, R, B, AXIS))
    yb = B + 34
    if xlabel:
        body.append(_text((L + R) / 2, yb, xlabel, 12, 'middle', INK2))
    if abs(lo) > 1e-12 and not lo < 0 < hi and note_zero:
        body.append(_text(L, yb, 'axis starts at %s%s' % (tfmt(lo), (' ' + unit) if unit else ''), 11,
                          'start', MUTED, extra=' font-style="italic"'))
    return X


def _ref_lines(body, refs, X, L, R, T, B):
    """Vertical grey reference lines with staggered labels above the plot."""
    if not refs:
        return
    labs = [(X(v), t) for v, t in refs]
    place, _ = _vlabels(labs, L, R)
    for (px, t), (r, tx, anc) in zip(labs, place):
        body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
            px, B, px, T - 4 - r * 14, COLORS['ref']))
    for (px, t), (r, tx, anc) in zip(labs, place):
        body.append(_text(tx, T - 8 - r * 14, t, 11, anc, MUTED, halo=True))


def _ref_rows(refs, lo, hi, L, R):
    if not refs:
        return 0
    def X(v):
        return L + (v - lo) / (hi - lo) * (R - L)
    return _vlabels([(X(v), t) for v, t in refs], L, R)[1]


def dumbbell(rows, a_name='a', b_name='b', a_color='f2', b_color='f1', unit='', fmt=None,
             xlabel='', xrange=None, refs=None, width=1040, row_h=34, label_w=300,
             gap_fmt=None, title='dumbbell chart'):
    """Paired values, one row per pair: two dots joined by a line, the gap written on the row.
    rows: dicts with label, a, b, and optionally gap (text), sub (small second label), tip,
    or {'header': text} for a group heading."""
    rows = [dict(r) for r in rows]
    fmt = fmt or (lambda v: num(v, 3))
    ca, cb = color(a_color), color(b_color)
    lw = _label_col(rows, label_w)
    vals = [v for r in rows for v in (r.get('a'), r.get('b')) if v is not None] + [v for v, _ in (refs or [])]
    lo, hi, ticks, dig = _lin_range(vals, xrange, n=6)
    tfmt = lambda v: num(v, dig)
    vw = max([tw(fmt(v), 11) for v in vals] + [30])
    gw = 0
    for r in rows:
        if r.get('header'):
            continue
        if 'gap' not in r and r.get('a') is not None and r.get('b') is not None:
            r['gap'] = gap_fmt(r['a'], r['b']) if gap_fmt else signed(r['b'] - r['a'], 3, unit)
        gw = max(gw, tw(r.get('gap') or '', 11, True))
    L = lw + 18 + vw + 12
    R = width - (vw + 14 + gw + 14)
    body = []
    lg, lh = _legend_row([(a_name, ca, 'circle'), (b_name, cb, 'circle')], 0, 18, width)
    body += lg
    T = 6 + lh + 8 + _ref_rows(refs, lo, hi, L, R) * 14
    y = T + 4
    ys = []
    for r in rows:
        h = _row_h(r, row_h if not r.get('header') else 26)
        ys.append((y, h))
        y += h
    B = y + 4
    X = _haxis(body, L, R, T, B, lo, hi, ticks, tfmt, xlabel, unit)
    _ref_lines(body, refs, X, L, R, T, B)
    for r, (y0, h) in zip(rows, ys):
        ym = y0 + h / 2
        if r.get('header'):
            body += _row_text(r, 0, ym + 3)
            continue
        a, b = r.get('a'), r.get('b')
        tip = r.get('tip')
        if not tip:
            tl = [r.get('label', '')]
            if a is not None:
                tl.append('%s: %s%s' % (a_name, fmt(a), (' ' + unit) if unit else ''))
            if b is not None:
                tl.append('%s: %s%s' % (b_name, fmt(b), (' ' + unit) if unit else ''))
            if r.get('gap'):
                tl.append('gap: ' + r['gap'])
            tip = '\n'.join(tl)
        g = ['<g class="row"%s>' % _tip(tip)]
        g.append('<rect class="rowbg" x="0" y="%.1f" width="%g" height="%.1f"/>' % (y0, width, h))
        g += _row_text(r, 0, ym)
        pts = sorted([(v, c) for v, c in ((a, ca), (b, cb)) if v is not None], key=lambda t: t[0])
        if len(pts) == 2:
            xa, xb = X(pts[0][0]), X(pts[1][0])
            g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (
                xa, ym, xb, ym, '#c3c8cf'))
        close = len(pts) == 2 and abs(X(pts[1][0]) - X(pts[0][0])) < 9
        for k, (v, c) in enumerate(pts):
            g.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s" stroke="%s" stroke-width="2"/>' % (
                X(v), ym + ((-4 if k == 0 else 4) if close else 0), c, SURFACE))
        if pts:
            g.append(_text(X(pts[0][0]) - 10, ym + 4, fmt(pts[0][0]), 11, 'end', INK, halo=True))
        if len(pts) == 2:
            g.append(_text(X(pts[1][0]) + 10, ym + 4, fmt(pts[1][0]), 11, 'start', INK, halo=True))
        if r.get('gap') and pts:
            gx = X(pts[-1][0]) + 10 + (tw(fmt(pts[-1][0]), 11) + 10 if len(pts) == 2 else 0)
            g.append(_text(gx, ym + 4, r['gap'], 11, 'start', INK, weight='700', halo=True))
        g.append('</g>')
        body.append(''.join(g))
    return _svg(width, B + 40, body, title)


def hbar(rows, unit='', fmt=None, xlabel='', series=None, refs=None, width=1040, bar_h=16,
         label_w=300, xmax=None, color_='f2', title='bar chart'):
    """Horizontal bars from a zero baseline.
    rows: dicts with label and value (one bar) or values (a list, one bar per entry of
    `series` = [(name, color)]), optionally sub, color, note (text after the value), tips,
    or {'header': text} for a group heading."""
    rows = [dict(r) for r in rows]
    fmt = fmt or (lambda v: num(v, 3))
    lw = _label_col(rows, label_w)
    nser = len(series) if series else 1
    vals, notew = [], 0
    for r in rows:
        if r.get('header'):
            continue
        r['_v'] = list(r['values']) if 'values' in r else [r.get('value')]
        vals += [v for v in r['_v'] if v is not None]
        notes = r.get('notes') or ([r['note']] if r.get('note') else [])
        r['_notes'] = notes
        for i, v in enumerate(r['_v']):
            t = (fmt(v) if v is not None else 'n/a') + ((' ' + unit) if unit and v is not None else '')
            if i < len(notes) and notes[i]:
                t += '  ' + notes[i]
            notew = max(notew, tw(t, 11))
    if any(v < 0 for v in vals):
        raise ValueError('hbar draws magnitudes from zero: negative value given')
    lo, hi, ticks, dig = _lin_range(vals + [v for v, _ in (refs or [])], (0, xmax), n=6)
    tfmt = lambda v: num(v, dig)
    L = lw + 16
    R = width - notew - 16
    body = []
    T = 8
    if series and nser > 1:
        lg, lh = _legend_row([(n, color(c), 'swatch') for n, c in series], 0, 18, width)
        body += lg
        T = 6 + lh + 8
    T += _ref_rows(refs, lo, hi, L, R) * 14 + (6 if refs else 0)
    y = T + 4
    ys = []
    for r in rows:
        if r.get('header'):
            h = 26
        else:
            h = _row_h(r, len(r['_v']) * (bar_h + 2) + 12)
        ys.append((y, h))
        y += h
    B = y + 4
    X = _haxis(body, L, R, T, B, lo, hi, ticks, tfmt, xlabel, unit)
    _ref_lines(body, refs, X, L, R, T, B)
    for r, (y0, h) in zip(rows, ys):
        ym = y0 + h / 2
        if r.get('header'):
            body += _row_text(r, 0, ym + 3)
            continue
        body += _row_text(r, 0, ym)
        n = len(r['_v'])
        by = ym - (n * (bar_h + 2) - 2) / 2
        for i, v in enumerate(r['_v']):
            c = color(series[i][1]) if series else color(r.get('color', color_))
            name = series[i][0] if series else ''
            yy = by + i * (bar_h + 2)
            t = (fmt(v) + ((' ' + unit) if unit else '')) if v is not None else 'n/a'
            tips = r.get('tips')
            tip = tips[i] if tips and i < len(tips) else '%s%s\n%s' % (
                r.get('label', ''), (' - ' + name) if name else '', t)
            if i < len(r['_notes']) and r['_notes'][i]:
                t += '  ' + r['_notes'][i]
            x1 = X(v) if v is not None else L
            wbar = max(x1 - L, 0)
            if wbar > 0:
                rr = min(4, wbar, bar_h / 2)
                body.append('<path class="mk" d="M%.1f %.1fH%.1fQ%.1f %.1f %.1f %.1fV%.1fQ%.1f %.1f %.1f %.1fH%.1fZ" '
                            'fill="%s"%s/>' % (L, yy, x1 - rr, x1, yy, x1, yy + rr, yy + bar_h - rr,
                                               x1, yy + bar_h, x1 - rr, yy + bar_h, L, c, _tip(tip)))
            body.append(_text(x1 + 6, yy + bar_h / 2 + 4, t, 11, 'start', INK, halo=True))
    return _svg(width, B + 40, body, title)


# ------------------------------------------------- wall-clock lanes

def lanes(lanes_, unit='ns', spans=None, t_range=None, width=1040, lane_h=28, xlabel=None,
          show_legend=True, tfmt=None, title='wall-clock lanes'):
    """One lane per actor, time to scale.
    lanes_: [{'name': str, 'blocks': [(start, end, label, kind)]}], kind in
    'work' (solid), 'wait' (dashed outline), 'critical' (red).  A block may be a dict
    with start, end, label, kind and optionally color, tip.
    spans: [(start, end, text)] or [(start, end, text, 'critical')]: dimension lines
    drawn under the lanes, for example the span time and the bracket time."""
    L = max([tw(l['name'], 12) for l in lanes_] + [40]) + 18
    R = width - 20
    norm = []
    for l in lanes_:
        bl = []
        for b in l['blocks']:
            if not isinstance(b, dict):
                b = dict(zip(('start', 'end', 'label', 'kind'), b))
            if b.get('kind', 'work') not in ('work', 'wait', 'critical'):
                raise ValueError('lanes: unknown block kind %r' % b.get('kind'))
            bl.append(dict(b, kind=b.get('kind', 'work')))
        norm.append((l['name'], bl))
    ts = [v for _, bl in norm for b in bl for v in (b['start'], b['end'])] + \
         [v for s in (spans or []) for v in s[:2]]
    t0, t1 = t_range or (min(ts), max(ts))
    ticks, step = _ticks(t0, t1, 8)
    dig = _tick_digits(step)
    tfmt = tfmt or (lambda v: num(v, dig))

    def X(t):
        return L + (t - t0) / (t1 - t0) * (R - L)
    body = []
    y = 8
    if show_legend:
        kinds = {b['kind'] for _, bl in norm for b in bl}
        items = [('work', COLORS['work'], 'swatch')]
        if 'wait' in kinds:
            items.append(('waiting or idle', COLORS['ref'], 'dashed'))
        if 'critical' in kinds or any(len(s) > 3 and s[3] == 'critical' for s in (spans or [])):
            items.append(('serial slice (critical path)', COLORS['crit'], 'swatch'))
        lg, lh = _legend_row(items, 0, y + 12, width)
        body += lg
        y += lh + 6
    grid_top = y
    blocks_svg, lane_boxes = [], []
    for name, bl in norm:
        # which labels fit inside their block
        outside = []
        for b in bl:
            w = X(b['end']) - X(b['start'])
            b['_w'] = w
            b['_in'] = bool(b.get('label')) and tw(b['label'], 11) + 10 <= w
            if b.get('label') and not b['_in']:
                cx = (X(b['start']) + X(b['end'])) / 2
                lwid = tw(b['label'], 11)
                cx_l = min(max(cx, L + lwid / 2), R - lwid / 2)
                outside.append((cx_l, b['label'], b, cx))
        outside.sort(key=lambda t: t[0])
        rows, placed, moved = [], [], []    # placed: (row, x0, x1, leader x)
        for cx_l, t, _, cx in outside:
            hw = tw(t, 11) / 2 + 5
            found = None
            for r in range(len(outside) + 1):
                for sh in (0, hw + 10, -hw - 10, 2 * hw + 14, -2 * hw - 14):
                    c = min(max(cx_l + sh, L + hw), R - hw)
                    ok = True
                    for pr, x0, x1, lx in placed:
                        if pr == r and c - hw < x1 and x0 < c + hw:
                            ok = False      # two labels of one row overlap
                        if pr < r and x0 - 3 < cx < x1 + 3:
                            ok = False      # my leader line would cross a lower label
                        if pr > r and c - hw - 3 < lx < c + hw + 3:
                            ok = False      # the leader line of an upper label would cross me
                    if ok:
                        found = (r, c)
                        break
                if found:
                    break
            if not found:
                found = (max([pr for pr, _, _, _ in placed] + [-1]) + 1, cx_l)
            placed.append((found[0], found[1] - hw, found[1] + hw, cx))
            rows.append(found[0])
            moved.append(found[1])
        outside = [(m, t, b, cx) for m, (_, t, b, cx) in zip(moved, outside)]
        nrows = (max(rows) + 1) if rows else 0
        top = y + nrows * 15 + (4 if nrows else 0)
        for (cx_l, t, b, cx), r in zip(outside, rows):
            ty = top - 8 - r * 15
            blocks_svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
                cx, top - 1, min(max(cx, cx_l - tw(t, 11) / 2), cx_l + tw(t, 11) / 2), ty + 3, MUTED))
            blocks_svg.append(_text(cx_l, ty, t, 11, 'middle', INK, halo=True))
        for b in bl:
            xa, w = X(b['start']), max(b['_w'], 0.75)
            dur = b['end'] - b['start']
            tip = b.get('tip') or '%s: %s\n%s to %s %s (%s %s)' % (
                name, b.get('label', b['kind']), tfmt(b['start']), tfmt(b['end']), unit,
                num(dur, max(dig, 1)), unit)
            if b['kind'] == 'wait':
                blocks_svg.append('<rect class="mk" x="%.2f" y="%.1f" width="%.2f" height="%g" rx="2" fill="%s" '
                                  'stroke="%s" stroke-width="1.2" stroke-dasharray="4 3"%s/>' % (
                                      xa, top + 0.5, w, lane_h - 1, SURFACE, COLORS['ref'], _tip(tip)))
                tc = INK2
            else:
                c = COLORS['crit'] if b['kind'] == 'critical' else color(b.get('color', 'work'))
                blocks_svg.append('<rect class="mk" x="%.2f" y="%.1f" width="%.2f" height="%g" rx="%g" fill="%s"%s/>' % (
                    xa, top, w, lane_h, 2 if w > 4 else 0, c, _tip(tip)))
                tc = '#ffffff'
            if b['_in']:
                blocks_svg.append(_text(xa + w / 2, top + lane_h / 2 + 4, b['label'], 11, 'middle', tc,
                                        weight='600', extra=' pointer-events="none"'))
        blocks_svg.append(_text(0, top + lane_h / 2 + 4, name, 12, fill=INK, weight='600'))
        lane_boxes.append((top, top + lane_h))
        y = top + lane_h + 12
    # dimension lines
    span_svg = []
    for s in spans or []:
        a, b, t = s[0], s[1], s[2]
        crit = len(s) > 3 and s[3] == 'critical'
        c = COLORS['crit'] if crit else INK2
        xa, xb = X(a), X(b)
        yy = y + 14
        span_svg.append('<path d="M%.1f %.1fv8M%.1f %.1fH%.1fM%.1f %.1fv8" fill="none" stroke="%s" stroke-width="%s"/>' % (
            xa, yy - 4, xa, yy, xb, xb, yy - 4, c, '2' if crit else '1.2'))
        w = tw(t, 11, True)
        if w + 8 <= xb - xa:
            span_svg.append(_text((xa + xb) / 2, yy - 5, t, 11, 'middle', INK, weight='600', halo=True))
        elif xb + 6 + w <= R:
            span_svg.append(_text(xb + 6, yy + 4, t, 11, 'start', INK, weight='600', halo=True))
        else:
            span_svg.append(_text(xa - 6, yy + 4, t, 11, 'end', INK, weight='600', halo=True))
        y += 24
    B = y + 6
    for t in ticks:
        px = X(t)
        body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
            px, grid_top, px, B, GRID))
        body.append(_text(px, B + 16, tfmt(t), 11, 'middle', MUTED))
    body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, B, R, B, AXIS))
    body.append(_text((L + R) / 2, B + 34, xlabel or ('time, %s (to scale)' % unit), 12, 'middle', INK2))
    return _svg(width, B + 42, body + blocks_svg + span_svg, title)


# -------------------------------------------- box-and-arrow diagrams

_BOX_STYLE = {
    'plain': ('#ffffff', '#8b929b', ''),
    'accent': ('#eceef1', '#1c2024', ''),      # ink outline: blue means boot F2 on the page
    'soft': ('#f4f5f7', '#a9afb7', ''),
    'dashed': ('#ffffff', '#8b929b', ' stroke-dasharray="5 4"'),
}
_BOX_STROKE_W = {'accent': 1.5}


def boxes(nodes, arrows=(), groups=(), width=1040, height=None, title='diagram'):
    """Box-and-arrow diagram.  Coordinates are px in a width x height canvas.
    nodes: dicts with id, x, y, w, h, title, and optionally lines (list of text, wrapped
    to the box), tag (small pill at the bottom), tag_style ('solid' or 'outline'),
    kind ('plain', 'accent', 'soft', 'dashed'), tip.  A box grows downwards when its
    text needs more than h.
    arrows: dicts with src, dst (node ids) and optionally label, dashed, both (two heads),
    via ([(x, y)] corner points), label_dy.
    groups: dicts with x, y, w, h, label: a light frame drawn behind the boxes."""
    aid = _next_id('ah')
    body = ['<defs><marker id="%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="%s"/></marker></defs>' % (aid, INK2)]
    maxy = 0
    for g in groups:
        body.append('<rect x="%g" y="%g" width="%g" height="%g" rx="8" fill="#f7f8fa" stroke="%s" '
                    'stroke-width="1" stroke-dasharray="2 3"/>' % (g['x'], g['y'], g['w'], g['h'], AXIS))
        if g.get('label'):
            body.append(_text(g['x'] + 10, g['y'] + 16, g['label'], 11, fill=MUTED, weight='600'))
        maxy = max(maxy, g['y'] + g['h'])
    geo = {}
    node_svg = []
    for n in nodes:
        x, y, w = n['x'], n['y'], n['w']
        tl = wrap(n.get('title', ''), w - 16, 12.5)
        ll = []
        for t in n.get('lines') or []:
            ll += wrap(t, w - 16, 11)
        need = 10 + 16 * len(tl) + 14 * len(ll) + (22 if n.get('tag') else 0) + 8
        h = max(n.get('h', 0), need)
        geo[n['id']] = (x, y, w, h)
        maxy = max(maxy, y + h)
        fill, stroke, dash = _BOX_STYLE[n.get('kind', 'plain')]
        tip = n.get('tip') or '\n'.join([n.get('title', '')] + list(n.get('lines') or []) +
                                        ([n['tag']] if n.get('tag') else []))
        g = ['<g%s>' % _tip(tip)]
        g.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" fill="%s" stroke="%s" stroke-width="%g"%s/>' % (
            x, y, w, h, fill, stroke, _BOX_STROKE_W.get(n.get('kind', 'plain'), 1.2), dash))
        ty = y + 10 + 12
        for t in tl:
            g.append(_text(x + w / 2, ty, t, 12.5, 'middle', INK, weight='600'))
            ty += 16
        ty -= 1
        for t in ll:
            g.append(_text(x + w / 2, ty, t, 11, 'middle', INK2))
            ty += 14
        if n.get('tag'):
            t = n['tag']
            pw = min(tw(t, 10) + 14, w - 8)
            px, py = x + w / 2 - pw / 2, y + h - 22
            if n.get('tag_style', 'solid') == 'solid':
                g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="16" rx="8" fill="#dfe3e8"/>' % (px, py, pw))
            else:
                g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="16" rx="8" fill="#ffffff" stroke="%s" '
                         'stroke-width="1" stroke-dasharray="3 2"/>' % (px, py, pw, MUTED))
            g.append(_text(x + w / 2, py + 11.5, t, 10, 'middle', INK2))
        g.append('</g>')
        node_svg.append(''.join(g))
    lab_svg = []
    for a in arrows:
        sx, sy, sw, sh = geo[a['src']]
        dx, dy, dw, dh = geo[a['dst']]
        pts = None
        if a.get('via'):
            v = list(a['via'])
            p0 = _port((sx, sy, sw, sh), v[0])
            p1 = _port((dx, dy, dw, dh), v[-1])
            pts = [p0] + v + [p1]
        elif sx + sw <= dx or dx + dw <= sx:      # side by side
            fwd = sx + sw <= dx
            xa = sx + sw if fwd else sx
            xb = dx if fwd else dx + dw
            o0, o1 = max(sy, dy), min(sy + sh, dy + dh)
            if o1 - o0 >= 12:
                ym = (o0 + o1) / 2 + a.get('shift', 0)
                pts = [(xa, ym), (xb, ym)]
            elif a.get('route') == 'hv':
                pts = [(xa, sy + sh / 2), (dx + dw / 2, sy + sh / 2),
                       (dx + dw / 2, dy if dy > sy else dy + dh)]
            elif sy + sh <= dy or dy + dh <= sy:
                pts = [(sx + sw / 2, sy + sh if dy > sy else sy), (sx + sw / 2, dy + dh / 2), (xb, dy + dh / 2)]
            else:
                xm = (xa + xb) / 2
                pts = [(xa, sy + sh / 2), (xm, sy + sh / 2), (xm, dy + dh / 2), (xb, dy + dh / 2)]
        else:                                      # one above the other
            down = sy + sh <= dy
            ya = sy + sh if down else sy
            yb = dy if down else dy + dh
            o0, o1 = max(sx, dx), min(sx + sw, dx + dw)
            if o1 - o0 >= 12:
                xm = (o0 + o1) / 2 + a.get('shift', 0)
                pts = [(xm, ya), (xm, yb)]
            else:
                ym = (ya + yb) / 2
                pts = [(sx + sw / 2, ya), (sx + sw / 2, ym), (dx + dw / 2, ym), (dx + dw / 2, yb)]
        d = 'M' + 'L'.join('%.1f %.1f' % p for p in pts)
        body.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.4"%s marker-end="url(#%s)"%s/>' % (
            d, INK2, ' stroke-dasharray="5 4"' if a.get('dashed') else '', aid,
            ' marker-start="url(#%s)"' % aid if a.get('both') else ''))
        if a.get('label'):
            # label on the longest segment
            best = max(range(len(pts) - 1), key=lambda i: math.hypot(pts[i + 1][0] - pts[i][0],
                                                                    pts[i + 1][1] - pts[i][1]))
            (x0, y0), (x1, y1) = pts[best], pts[best + 1]
            lines = a['label'].split('\n')
            if abs(y1 - y0) < abs(x1 - x0):
                ly = (y0 + y1) / 2 - 6 - 13 * (len(lines) - 1) + a.get('label_dy', 0)
                for k, t in enumerate(lines):
                    lab_svg.append(_text((x0 + x1) / 2, ly + 13 * k, t, 11, 'middle', INK2, halo=True))
            else:
                ly = (y0 + y1) / 2 + 4 - 6.5 * (len(lines) - 1) + a.get('label_dy', 0)
                for k, t in enumerate(lines):
                    lab_svg.append(_text((x0 + x1) / 2 + 7, ly + 13 * k, t, 11, 'start', INK2, halo=True))
    return _svg(width, height or (maxy + 12), body + node_svg + lab_svg, title)


def _port(box, toward):
    """Point on the edge of a box that faces the point `toward`."""
    x, y, w, h = box
    tx, ty = toward
    if x <= tx <= x + w:
        return (tx, y if ty < y else y + h)
    if y <= ty <= y + h:
        return (x if tx < x else x + w, ty)
    return (x + w / 2, y if ty < y else y + h)


_MESH_STYLE = {
    # kind: (fill, stroke, dash, text color, legend name)
    'plain': ('#ffffff', '#c3c8cf', '', MUTED, 'crosspoint'),
    'hn': ('#3d4855', '#3d4855', '', '#ffffff', 'home node'),
    'port': ('#ffffff', '#1c2024', '', INK, 'cluster port'),
    'mem': ('#e3e6ea', '#8b929b', '', INK, 'bridge to memory'),
    'hyp': ('#ffffff', '#1c2024', ' stroke-dasharray="5 4"', INK, 'position is a hypothesis'),
}


def mesh_map(nx, ny, cells=(), highlights=(), steps=(), width=1040, cell_w=None, cell_h=58,
             y_up=True, kinds=None, title='mesh map', highlight_label='highlighted'):
    """A mesh of nx x ny crosspoints.
    cells: [(x, y, label, kind)], label may hold '\\n', kind in 'plain', 'hn', 'port',
    'mem', 'hyp'.  highlights: [(x, y)] crosspoints that get a ring.
    steps: dicts with src (x, y), dst (x, y), label, optionally color and order
    ('xy' or 'yx'): a route drawn along the mesh links, X first by default.
    kinds: {kind: legend name} to rename or add legend entries."""
    names = {k: v[4] for k, v in _MESH_STYLE.items()}
    names.update(kinds or {})
    L, T = 44, 34
    pitch_x = (width - L - 16) / nx
    cw = cell_w or min(pitch_x - 34, 120)
    pitch_y = cell_h + 34
    H = T + ny * pitch_y + 26

    def C(x, y):
        return (L + pitch_x * (x + 0.5), T + pitch_y * ((ny - 1 - y) if y_up else y) + pitch_y / 2)
    body = []
    used = []
    cellmap = {}
    for c in cells:
        cellmap[(c[0], c[1])] = c
        k = c[3] if len(c) > 3 else 'plain'
        if k not in used:
            used.append(k)
    items = []
    for k in used:
        f, s, d, _, _ = _MESH_STYLE[k]
        items.append((names[k], s if f == '#ffffff' else f, 'dashed' if d else 'swatch'))
    if highlights:
        items.append((highlight_label, COLORS['ref'], 'circle'))
    if items:
        lg, _ = _legend_row(items, 0, 16, width)
        body += lg
    # links
    for x in range(nx):
        for y in range(ny):
            cx, cy = C(x, y)
            if x + 1 < nx:
                ex, ey = C(x + 1, y)
                body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.5"/>' % (cx, cy, ex, ey, '#d5d9de'))
            if y + 1 < ny:
                ex, ey = C(x, y + 1)
                body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.5"/>' % (cx, cy, ex, ey, '#d5d9de'))
    # axis indices
    for x in range(nx):
        cx, _ = C(x, 0)
        body.append(_text(cx, H - 6, 'x = %d' % x, 11, 'middle', MUTED))
    for y in range(ny):
        _, cy = C(0, y)
        body.append(_text(0, cy + 4, 'y = %d' % y, 11, fill=MUTED))
    # routes
    route_svg, lab_svg = [], []
    aid = _next_id('ms')
    offs = {}
    for st in steps:
        c = color(st.get('color', INK))
        (sx, sy), (dx, dy) = st['src'], st['dst']
        corner = (dx, sy) if st.get('order', 'xy') == 'xy' else (sx, dy)
        key = (st['src'], corner)
        k = offs.get(key, 0)
        offs[key] = k + 1
        off = (k - 0) * 5
        pts = [C(*st['src']), C(*corner), C(*st['dst'])]
        pts = [(px + off, py - off) for px, py in pts]
        # stop at the edge of the destination cell
        (ax, ay), (bx, by) = pts[1], pts[2]
        if (ax, ay) == (bx, by):
            (ax, ay) = pts[0]
        if abs(bx - ax) > abs(by - ay):
            bx += -(cw / 2 + 3) if bx > ax else (cw / 2 + 3)
        elif by != ay:
            by += -(cell_h / 2 + 3) if by > ay else (cell_h / 2 + 3)
        pts[2] = (bx, by)
        mid = _next_id(aid + '_')
        route_svg.append('<defs><marker id="%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
                         'orient="auto"><path d="M0 0L10 5L0 10z" fill="%s"/></marker></defs>' % (mid, c))
        route_svg.append('<path d="M%s" fill="none" stroke="%s" stroke-width="2.2" stroke-linejoin="round" '
                         'marker-end="url(#%s)"%s/>' % ('L'.join('%.1f %.1f' % p for p in pts), c, mid,
                                                        _tip(st.get('tip') or st.get('label', ''))))
        if st.get('label'):
            # label in the free band between two rows of cells, next to the destination
            tx, ty = C(*st['dst'])
            below = (corner[1] < dy) if y_up else (corner[1] > dy)
            if corner[1] == dy:
                below = st.get('label_below', False)
            vertical = corner[0] == dx and corner[1] != dy
            ly = ty + (cell_h / 2 + 15 if below else -cell_h / 2 - 7)
            lab_svg.append(_text(tx + (9 + off if vertical else 0) + st.get('label_dx', 0),
                                 ly + st.get('label_dy', 0), st['label'], 11,
                                 'start' if vertical else 'middle', INK, weight='600', halo=True))
    # cells
    cell_svg = []
    for x in range(nx):
        for y in range(ny):
            cx, cy = C(x, y)
            c = cellmap.get((x, y))
            if not c:
                cell_svg.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#ffffff" stroke="%s" stroke-width="1.5"%s/>' % (
                    cx, cy, '#b4bac2', _tip('crosspoint (%d,%d)' % (x, y))))
                continue
            kind = c[3] if len(c) > 3 else 'plain'
            f, s, d, tc, _ = _MESH_STYLE[kind]
            lines = str(c[2]).split('\n')
            tip = 'crosspoint (%d,%d)\n%s' % (x, y, '\n'.join(lines))
            cell_svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%g" rx="6" fill="%s" stroke="%s" '
                            'stroke-width="1.4"%s%s/>' % (cx - cw / 2, cy - cell_h / 2, cw, cell_h, f, s, d, _tip(tip)))
            ty = cy - 6.5 * (len(lines) - 1) + 4
            for i, t in enumerate(lines):
                cell_svg.append(_text(cx, ty + 13 * i, t, 11 if i else 11.5, 'middle', tc,
                                      weight='600' if i == 0 else None, extra=' pointer-events="none"'))
    for (x, y) in highlights:
        cx, cy = C(x, y)
        cell_svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%g" rx="10" fill="none" stroke="%s" '
                        'stroke-width="2.5"/>' % (cx - cw / 2 - 5, cy - cell_h / 2 - 5, cw + 10, cell_h + 10, COLORS['ref']))
    return _svg(width, H, body + route_svg + cell_svg + lab_svg, title)
