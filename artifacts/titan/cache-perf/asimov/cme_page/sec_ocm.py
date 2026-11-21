"""Section 'ocm': OCM through the CME (mesh map, chain load per region, bandwidth, mesh counters).

Every measured number comes from the data layer D.  The two chart builders at the top
(_strip, _matrix) exist only here: viz.py has no dot strip and no matrix chart."""
import os

from . import data as _data
from . import viz as _V

KEY = 'ocm'
TITLE = 'OCM through the CME'

F2N = 'boot F2 (prefetchers off)'
F1N = 'boot F1 (prefetchers on)'
BOOTN = {'F1': F1N, 'F2': F2N}
BOOTC = {'F1': 'Boot F1 (prefetchers on)', 'F2': 'Boot F2 (prefetchers off)'}
SHAPE_PAGE = 'one line per 4 KiB page'
SHAPE_ALL = 'every line'


# ----------------------------------------------------------------- small helpers

def _n(v, d=3):
    return _V.num(v, d)


def _rng(vals, d=3, unit=''):
    vals = list(vals)
    lo, hi = min(vals), max(vals)
    u = (' ' + unit) if unit else ''
    if _n(lo, d) == _n(hi, d):
        return '%s%s' % (_n(lo, d), u)
    return '%s to %s%s' % (_n(lo, d), _n(hi, d), u)


def _code(s):
    return '<code>%s</code>' % s


def _tab(S, headers, rows, **kw):
    """S.table with '|' as a line break in a header and a first column that does not wrap."""
    headers = [h.replace('|', '<br>') for h in headers]
    rows = [r if isinstance(r, str) else ['<span style="white-space:nowrap">%s</span>' % r[0]] + list(r[1:])
            for r in rows]
    return S.table(headers, rows, **kw)


def _steps_word(n):
    return '%d step%s' % (n, '' if n == 1 else 's')


def _row_name(r):
    """Page label of one of the seven OCM rows."""
    if r['region'] is not None:
        return 'region %d' % r['region']
    return 'all five regions'


def _row_full(r):
    """Table label: the all-five rows also name their shape."""
    if r['region'] is not None:
        return 'region %d' % r['region']
    return 'all five, ' + r['shape']


def _by_steps(rows):
    """One-region rows ordered by mesh steps, then the two all-five rows."""
    one = sorted([r for r in rows if r['region'] is not None], key=lambda r: (r['steps'], r['region']))
    return one, [r for r in rows if r['region'] is None]


# ----------------------------------------------------------------- dot strip (own builder)

def _swarm(pxs, sep=7.0):
    """Level of each dot (0, 1, 2 ...) so that two dots closer than sep px get different levels."""
    levels = [0] * len(pxs)
    placed = []
    for i in sorted(range(len(pxs)), key=lambda k: pxs[k]):
        lv = 0
        while any(l == lv and abs(pxs[i] - x) < sep for x, l in placed):
            lv += 1
        levels[i] = lv
        placed.append((pxs[i], lv))
    return levels


def _level_dy(lv, step=5.0):
    """Vertical offset of a level: 0, -step, +step, -2 step, +2 step ..."""
    return ((lv + 1) // 2) * step * (-1 if lv % 2 else 1)


def _strip(rows, series, unit='', xlabel='', fmt=None, xrange='fit', refs=None, dim=None,
           width=1040, row_h=30, label_w=250, title='dot strip', tipfmt=None):
    """One row per item, one dot per value.  Dots with equal or near-equal values are stacked.
    rows: {'header': text} or {'label', 'sub', 'values': [list per series], 'note': text,
    'names': [list of dot names per series]}.
    series: [(name, color key)].  refs: [(x, label)] grey vertical lines.
    dim: (x0, x1, text) a dimension line between two x values, drawn under the rows.
    tipfmt: function (row, series name, index, value) -> hover text."""
    rows = [dict(r) for r in rows]
    fmt = fmt or (lambda v: _V.num(v, 3))
    lw = _V._label_col(rows, label_w)
    vals = [v for r in rows for vs in (r.get('values') or []) for v in (vs or [])]
    vals += [v for v, _ in (refs or [])]
    lo, hi, ticks, dig = _V._lin_range(vals, xrange, n=7)
    nw = max([_V.tw(r.get('note') or '', 11) for r in rows] + [0])
    L = lw + 22
    R = width - nw - (22 if nw else 14)

    def X0(v):
        return L + (v - lo) / (hi - lo) * (R - L)
    ns = len(series)
    body = []
    lg, lh = _V._legend_row([(n, _V.color(c), 'circle') for n, c in series], 0, 18, width)
    body += lg
    T = 6 + lh + 8 + _V._ref_rows(refs, lo, hi, L, R) * 14
    y = T + 4
    ys = []
    for r in rows:
        if r.get('header'):
            h = _V._row_h(r, 26)
        else:
            r['_lv'] = [_swarm([X0(v) for v in (vs or [])]) for vs in (r.get('values') or [[]] * ns)]
            half = max([abs(_level_dy(l)) for lv in r['_lv'] for l in lv] + [0])
            r['_band'] = 2 * half + 11
            h = _V._row_h(r, max(row_h, ns * r['_band'] + 8))
        ys.append((y, h))
        y += h
    if dim:
        y += 26
    B = y + 4
    X = _V._haxis(body, L, R, T, B, lo, hi, ticks, lambda v: _V.num(v, dig), xlabel, unit)
    _V._ref_lines(body, refs, X, L, R, T, B)
    for r, (y0, h) in zip(rows, ys):
        ym = y0 + h / 2
        if r.get('header'):
            body += _V._row_text(r, 0, ym + 3)
            continue
        body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
            L, y0 + h, R, y0 + h, _V.GRID))
        body += _V._row_text(r, 0, ym)
        for i, (name, c) in enumerate(series):
            vs = (r.get('values') or [None] * ns)[i] or []
            yc = ym + (i - (ns - 1) / 2.0) * r['_band']
            for k, v in enumerate(vs):
                if tipfmt:
                    tip = tipfmt(r, name, k, v)
                else:
                    tip = '%s\n%s, pass %d: %s%s' % (r.get('label', ''), name, k + 1, fmt(v), (' ' + unit) if unit else '')
                body.append('<circle class="mk" cx="%.1f" cy="%.1f" r="3.6" fill="%s" fill-opacity="0.78" '
                            'stroke="%s" stroke-width="1"%s/>' % (
                                X(v), yc + _level_dy(r['_lv'][i][k]), _V.color(c), _V.SURFACE, _V._tip(tip)))
        if r.get('note'):
            body.append(_V._text(R + 12, ym + 4, r['note'], 11, 'start', _V.INK))
    if dim:
        x0, x1, text = dim
        yd = B - 12
        a, b = X(x0), X(x1)
        body.append('<path d="M%.1f %.1fV%.1fM%.1f %.1fV%.1fM%.1f %.1fH%.1f" stroke="%s" stroke-width="1.3" fill="none"/>' % (
            a, yd - 5, yd + 5, b, yd - 5, yd + 5, a, yd, b, _V.INK))
        body.append(_V._text((a + b) / 2, yd - 6, text, 11.5, 'middle', _V.INK, weight='700', halo=True))
    return _V._svg(width, B + 40, body, title)


# ----------------------------------------------------------------- mesh map (own builder)

def _mesh(nx, ny, cells, src, width=530, cw=56, ch=46, title='mesh map'):
    """The mesh as a grid of crosspoints, y upwards.
    cells: [(x, y, [text lines], kind)] with kind 'hn' (home node), 'port' (cluster port) or
    'hyp' (cluster port whose owner is a hypothesis).  src: (x, y) of the start of the routes.
    One route is drawn from src to every 'hn' cell, on the mesh links that it uses (a dark stroke
    behind the boxes).  Of the two L-shaped shortest routes the one that passes fewer boxes is
    taken.  The number at a link is the step count from src at the far end of that link, and
    every route ends with its arrowhead at the edge of the target box."""
    INK, MUTED = _V.INK, _V.MUTED
    dark = '#3d4855'
    grey = _V.color('ref')
    L, T = 44, 50
    px = (width - L - 16) / float(nx)
    busy = {c[1] for c in cells}
    cy = {}
    y = T
    for gy in range(ny - 1, -1, -1):
        h = (ch + 36) if gy in busy else 38
        cy[gy] = y + h / 2.0
        y += h
    H = y + 24

    def cx(gx):
        return L + px * (gx + 0.5)
    body = []
    # legend, drawn with the same marks as the map
    x0 = 0
    body.append('<rect x="%.1f" y="5" width="13" height="10" rx="2" fill="%s"/>' % (x0, dark))
    t = 'home node with its OCM region'
    body.append(_V._text(x0 + 18, 14, t, 12, fill=_V.INK2))
    x0 += 18 + _V.tw(t, 12) + 18
    body.append('<rect x="%.1f" y="5" width="13" height="10" rx="2" fill="#ffffff" stroke="%s" stroke-width="1.3"/>' % (x0, INK))
    t = 'cluster port'
    body.append(_V._text(x0 + 18, 14, t, 12, fill=_V.INK2))
    x0 += 18 + _V.tw(t, 12) + 18
    body.append('<rect x="%.1f" y="5" width="13" height="10" rx="2" fill="#ffffff" stroke="%s" stroke-width="1.3" '
                'stroke-dasharray="3 2"/>' % (x0, INK))
    body.append(_V._text(x0 + 18, 14, 'position is a hypothesis', 12, fill=_V.INK2))
    x0 = 0
    body.append('<rect x="%.1f" y="22" width="15" height="12" rx="4" fill="none" stroke="%s" stroke-width="2.2"/>' % (x0, grey))
    t = 'start of the routes'
    body.append(_V._text(x0 + 20, 32, t, 12, fill=_V.INK2))
    x0 += 20 + _V.tw(t, 12) + 18
    aid = _V._next_id('mr')
    body.append('<defs><marker id="%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
                'orient="auto"><path d="M0 0L10 5L0 10z" fill="%s"/></marker></defs>' % (aid, INK))
    body.append('<path d="M%.1f 28H%.1f" stroke="%s" stroke-width="1.8" fill="none" marker-end="url(#%s)"/>' % (
        x0, x0 + 26, INK, aid))
    body.append(_V._text(x0 + 32, 32, 'route to a home node, with the step number at each link', 12, fill=_V.INK2))
    # links and axis indices
    for gx in range(nx):
        for gy in range(ny):
            if gx + 1 < nx:
                body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#d5d9de" stroke-width="1.5"/>' % (
                    cx(gx), cy[gy], cx(gx + 1), cy[gy]))
            if gy + 1 < ny:
                body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#d5d9de" stroke-width="1.5"/>' % (
                    cx(gx), cy[gy], cx(gx), cy[gy + 1]))
    for gx in range(nx):
        body.append(_V._text(cx(gx), H - 6, 'x = %d' % gx, 11, 'middle', MUTED))
    for gy in range(ny):
        body.append(_V._text(0, cy[gy] + 4, 'y = %d' % gy, 11, fill=MUTED))
    # cells
    cellmap = {(c[0], c[1]): c for c in cells}
    cells_at = len(body)             # the routes are put in here, behind the boxes
    for gx in range(nx):
        for gy in range(ny):
            c = cellmap.get((gx, gy))
            if not c:
                body.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="#ffffff" stroke="#b4bac2" stroke-width="1.5"%s/>' % (
                    cx(gx), cy[gy], _V._tip('crosspoint (%d,%d)' % (gx, gy))))
                continue
            lines, kind = c[2], c[3]
            fill, tc = (dark, '#ffffff') if kind == 'hn' else ('#ffffff', INK)
            body.append('<rect x="%.1f" y="%.1f" width="%g" height="%g" rx="6" fill="%s" stroke="%s" stroke-width="1.4"%s%s/>' % (
                cx(gx) - cw / 2.0, cy[gy] - ch / 2.0, cw, ch, fill, dark if kind == 'hn' else INK,
                ' stroke-dasharray="5 4"' if kind == 'hyp' else '',
                _V._tip('crosspoint (%d,%d)\n%s' % (gx, gy, '\n'.join(lines)))))
            ty = cy[gy] - 6.5 * (len(lines) - 1) + 4
            for i, t in enumerate(lines):
                body.append(_V._text(cx(gx), ty + 13 * i, t, 10 if i else 11.5, 'middle', tc,
                                     weight='600' if i == 0 else None, extra=' pointer-events="none"'))
    sx, sy = src
    body.append('<rect x="%.1f" y="%.1f" width="%g" height="%g" rx="10" fill="none" stroke="%s" stroke-width="2.5"/>' % (
        cx(sx) - cw / 2.0 - 5, cy[sy] - ch / 2.0 - 5, cw + 10, ch + 10, grey))
    # routes, on the links
    def route(dx, dy):
        cands = []
        for order in ('xy', 'yx'):
            x, y, pts = sx, sy, [(sx, sy)]
            for axis in order:
                if axis == 'x':
                    while x != dx:
                        x += 1 if dx > x else -1
                        pts.append((x, y))
                else:
                    while y != dy:
                        y += 1 if dy > y else -1
                        pts.append((x, y))
            cands.append((sum(1 for p in pts[1:-1] if p in cellmap), pts))
        return min(cands, key=lambda t: t[0])[1]

    links = {}                       # (a, b) -> [step number, True when a route ends at b]
    for c in cells:
        if c[3] != 'hn':
            continue
        pts = route(c[0], c[1])
        for k in range(1, len(pts)):
            e = links.setdefault((pts[k - 1], pts[k]), [k, False])
            assert e[0] == k
            e[1] = e[1] or k == len(pts) - 1
    route_svg, num_svg = [], []
    for (a, b), (k, last) in sorted(links.items()):
        ax, ay, bx, by = cx(a[0]), cy[a[1]], cx(b[0]), cy[b[1]]
        if a[1] == b[1]:             # a horizontal link
            sg = 1 if bx > ax else -1
            x0 = ax + sg * (cw / 2.0 if a in cellmap else 0)
            x1 = bx - sg * ((cw / 2.0 if b in cellmap else 0) + (2 if last else 0))
            d = 'M%.1f %.1fH%.1f' % (x0, ay, x1)
            num_svg.append(_V._text((x0 + x1) / 2.0, ay - 6, '%d' % k, 11, 'middle', INK, weight='700', halo=True))
        else:                        # a vertical link (y grows upwards on the map)
            sg = 1 if by > ay else -1
            y0 = ay + sg * (ch / 2.0 if a in cellmap else 0)
            y1 = by - sg * ((ch / 2.0 if b in cellmap else 0) + (2 if last else 0))
            d = 'M%.1f %.1fV%.1f' % (ax, y0, y1)
            num_svg.append(_V._text(ax + 7, (y0 + y1) / 2.0 + 4, '%d' % k, 11, 'start', INK, weight='700', halo=True))
        route_svg.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.6"%s%s/>' % (
            d, INK, ' marker-end="url(#%s)"' % aid if last else '',
            _V._tip('link from crosspoint (%d,%d) to crosspoint (%d,%d)\nstep %d from crosspoint (%d,%d)' % (
                a[0], a[1], b[0], b[1], k, sx, sy))))
    body[cells_at:cells_at] = route_svg
    body += num_svg
    return _V._svg(width, H, body, title)


# ----------------------------------------------------------------- scatter with a line (own builder)

def _scatter(a, b_cols, fit, fit_x, hline, labels, xlabel, ylabel, yunit='ns', xmax=1.05, ylo=20.0,
             width=1040, height=420, title='scatter with a line'):
    """Span time of a pass against a count per load, x axis from 0.
    a: {'name', 'color', 'points': [(x, y, tip)]}: the series that the line is fitted to.
    b_cols: {'name', 'color', 'x', 'cols': [[(y, tip)], ...]}: a series whose dots all have the
    same x.  Dots with equal or near-equal y are drawn side by side around x, so that each can be seen.
    fit: (slope, intercept).  fit_x: (lowest, highest) x of the fitted points.  The line is solid
    inside that range and dashed outside it, from x = 0 to b_cols['x'].
    hline: (y, label).  labels: {'zero', 'end', 'b': [lines]} texts written on the figure."""
    INK, MUTED = _V.INK, _V.MUTED
    ca, cb = _V.color(a['color']), _V.color(b_cols['color'])
    m, c0 = fit
    xb = b_cols['x']
    yv = [p[1] for p in a['points']] + [p[0] for col in b_cols['cols'] for p in col] + [hline[0], c0, m * xb + c0]
    lo, hi, yt, ydig = _V._lin_range(yv, (ylo, None), n=6)
    body = []
    lg, lh = _V._legend_row([(b_cols['name'], cb, 'circle'), (a['name'], ca, 'circle')], 0, 18, width)
    body += lg
    L, R = 56, width - 22
    T = 6 + lh + 26
    B = height - 56

    def X(v):
        return L + 14 + v / xmax * (R - L - 14)

    def Y(v):
        return B - (v - lo) / (hi - lo) * (B - T)
    body.append(_V._text(0, T - 12, ylabel, 12, fill=_V.INK2, weight='600'))
    for t in yt:
        body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, Y(t), R, Y(t), _V.GRID))
        body.append(_V._text(L - 8, Y(t) + 4, _V.num(t, ydig), 11, 'end', MUTED))
    body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, B, R, B, _V.AXIS))
    k = 0
    while k / 10.0 <= xmax + 1e-9:
        body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
            X(k / 10.0), B, X(k / 10.0), B + 4, _V.AXIS))
        body.append(_V._text(X(k / 10.0), B + 17, _V.num(k / 10.0, 2), 11, 'middle', MUTED))
        k += 1
    body.append(_V._text((L + R) / 2.0, B + 36, xlabel, 12, 'middle', _V.INK2))
    body.append(_V._text(L, B + 36, 'axis starts at %s %s' % (_V.num(lo, ydig), yunit), 11, 'start', MUTED,
                         extra=' font-style="italic"'))
    # reference line
    body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (
        L, Y(hline[0]), R, Y(hline[0]), _V.color('ref')))
    body.append(_V._text(R - 4, Y(hline[0]) - 5, hline[1], 11, 'end', MUTED, halo=True))
    # the line: solid over the fitted points, dashed where it is extended
    def seg(x0, x1, dash):
        return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.6"%s/>' % (
            X(x0), Y(m * x0 + c0), X(x1), Y(m * x1 + c0), ca, ' stroke-dasharray="5 4"' if dash else '')
    body.append(seg(0.0, fit_x[0], True))
    body.append(seg(fit_x[0], fit_x[1], False))
    body.append(seg(fit_x[1], xb, True))
    for xe in (0.0, xb):
        body.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s" stroke="%s" stroke-width="1.6"/>' % (
            X(xe), Y(m * xe + c0), _V.SURFACE, ca))
    # dots
    for x, y, tip in a['points']:
        body.append('<circle class="mk" cx="%.1f" cy="%.1f" r="3.8" fill="%s" fill-opacity="0.78" stroke="%s" '
                    'stroke-width="1"%s/>' % (X(x), Y(y), ca, _V.SURFACE, _V._tip(tip)))
    bpts = [p for col in b_cols['cols'] for p in col]
    blv = _swarm([Y(p[0]) for p in bpts], sep=6.0)
    for (y, tip), lv in zip(bpts, blv):
        body.append('<circle class="mk" cx="%.1f" cy="%.1f" r="3.4" fill="%s" fill-opacity="0.78" stroke="%s" '
                    'stroke-width="1"%s/>' % (X(xb) + _level_dy(lv, 6.5), Y(y), cb, _V.SURFACE, _V._tip(tip)))
    bhalf = max(abs(_level_dy(lv, 6.5)) for lv in blv)
    # texts on the figure
    body.append(_V._text(X(0.0) + 34, Y(c0) + 15, labels['zero'], 11, 'start', INK, halo=True))
    body.append(_V._text(R - 4, Y(m * xb + c0) + 62, labels['end'], 11, 'end', INK, halo=True))
    top = min(Y(p[0]) for col in b_cols['cols'] for p in col)
    for i, t in enumerate(labels['b']):
        body.append(_V._text(min(X(xb) + bhalf + 6, R), top - 12 - 14 * (len(labels['b']) - 1 - i), t, 11, 'end',
                             INK, weight='600' if i == 0 else None, halo=True))
    body.append(_V._text((X(fit_x[0]) + X(fit_x[1])) / 2.0, Y(m * fit_x[0] + c0) + 30, labels['fit'], 11, 'middle',
                         _V.INK2, halo=True))
    return _V._svg(width, height, body, title)


# ----------------------------------------------------------------- matrix (own builder)

def _matrix(panels, col_labels, row_groups, fmt=None, width=1040, cell_h=24, label_w=250,
            col_title='', title='matrix'):
    """Side-by-side matrices that share the row labels.
    panels: [{'name', 'color', 'values': [[v per column] per row], 'own': [column index per row],
              'tips': [[text per column] per row]}].
    row_groups: [(header, [row label, ...])], rows numbered in order over the groups."""
    fmt = fmt or (lambda v: _V.num(abs(v) if abs(v) < 0.05 else v, 1))
    np_ = len(panels)
    ncol = len(col_labels)
    gap = 36
    lw = label_w
    cw = (width - lw - gap * (np_ - 1) - 4) / float(np_ * ncol)
    T = 58
    body = []
    vmax = max(v for p in panels for row in p['values'] for v in row)
    y = T
    row_y = []
    for header, labels in row_groups:
        body.append(_V._text(0, y + 17, header, 12, fill=_V.INK, weight='600'))
        y += 26
        for lab in labels:
            body.append(_V._text(10, y + cell_h / 2 + 4, lab, 12, fill=_V.INK))
            row_y.append(y)
            y += cell_h
        y += 6
    for pi, p in enumerate(panels):
        x0 = lw + pi * (ncol * cw + gap)
        c = _V.color(p['color'])
        body.append(_V._text(x0 + ncol * cw / 2, 14, p['name'], 12, 'middle', _V.INK, weight='600'))
        body.append('<rect x="%.1f" y="4" width="11" height="11" rx="2" fill="%s"/>' % (
            x0 + ncol * cw / 2 - _V.tw(p['name'], 12, True) / 2 - 18, c))
        if col_title:
            body.append(_V._text(x0 + ncol * cw / 2, 32, col_title, 11, 'middle', _V.MUTED))
        for ci, cl in enumerate(col_labels):
            body.append(_V._text(x0 + ci * cw + cw / 2, 50, cl, 11, 'middle', _V.INK2))
        for ri, row in enumerate(p['values']):
            yy = row_y[ri]
            for ci, v in enumerate(row):
                op = 0.6 * max(0.0, v) / vmax
                own = p['own'][ri] == ci
                tip = p['tips'][ri][ci]
                body.append('<rect class="mk" x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                            'fill-opacity="%.3f" stroke="%s" stroke-width="%s"%s/>' % (
                                x0 + ci * cw + 1, yy + 1, cw - 2, cell_h - 2, c, op,
                                _V.INK if own else _V.GRID, '1.4' if own else '1', _V._tip(tip)))
                body.append(_V._text(x0 + ci * cw + cw / 2, yy + cell_h / 2 + 4, fmt(v), 11, 'middle',
                                     _V.INK if own else _V.MUTED, weight='700' if own else None,
                                     extra=' pointer-events="none"'))
    return _V._svg(width, y + 4, body, title)


# ----------------------------------------------------------------- references

def _refs(D, S):
    """Register the references of this section and return the [RefN] links by short name."""
    R = {}
    rel = {b: os.path.relpath(_data.BOOTDIR[b], _data.ROOT) for b in _data.BOOTS}

    def loglines(boot, files):
        ls = [l for f in files for l in D.log_lines(boot, f)]
        return (min(ls), max(ls)) if ls else (None, None)

    for b in _data.BOOTS:
        files = [r['src'] for r in D.ocm_lat[b]]
        a, z = loglines(b, files)
        R['lat' + b] = S.ref('ocm-cme-lat-' + b, (
            'CME latency files on OCM of %s: %s to %s, %s and %s in %s. Rows %s to %s and %s of each file. '
            'Their commands are lines %d to %d of %s in the same folder.' % (
                BOOTN[b], _code(files[0]), _code(files[4]), _code(files[5]), _code(files[6]), _code(rel[b] + '/'),
                _code('cme-fresh1'), _code('cme-fresh7'), _code('cme-best'), a, z, _code('log.txt'))))
        files = [r['src'] for r in D.ocm_bw[b]]
        a, z = loglines(b, files)
        R['bw' + b] = S.ref('ocm-cme-bw-' + b, (
            'CME bandwidth files on OCM of %s: %s to %s, %s and %s in %s. All rep rows and the %s row of each '
            'file, columns %s and %s. Their commands are lines %d to %d of %s.' % (
                BOOTN[b], _code(files[0]), _code(files[4]), _code(files[5]), _code(files[6]), _code(rel[b] + '/'),
                _code('best'), _code('aggregate_GBps'), _code('span_s'), a, z, _code('log.txt'))))
        rows = [r for r in D.mesh_requests[b] if r['ocm']]
        R['cmn' + b] = S.ref('ocm-cmn-' + b, (
            'Mesh counter file %s of %s, in %s. The %d labels that start with %s begin at lines %d to %d. '
            'Event %s, one row per home node.' % (
                _code('cmn-counts.csv'), BOOTN[b], _code(rel[b] + '/'), len(rows), _code('cme-ocm-'),
                min(r['line'] for r in rows), max(r['line'] for r in rows), _code('hns_pocq_reqs_recvd_all'))))
        g = D.mesh_row(b, D.mesh_g7[b]['label'])
        R['g7' + b] = S.ref('ocm-cmn-g7-' + b, (
            'Mesh counter file %s of %s, in %s. Label %s, from line %d. Events %s, %s and %s.' % (
                _code('cmn-counts.csv'), BOOTN[b], _code(rel[b] + '/'), _code(g['label']), g['line'],
                _code('hns_pocq_reqs_recvd_all'), _code('hns_mc_reqs_local_all'), _code('hns_cache_miss_all'))))
    files = [r['src'] for r in D.ocm_core]
    a, z = loglines('F1', files)
    R['corelat'] = S.ref('ocm-core-lat-F1', (
        'Core latency files on OCM of %s: %s to %s, %s and %s in %s. Rows %s to %s and %s. '
        'Their commands are lines %d to %d of %s.' % (
            F1N, _code(files[0]), _code(files[4]), _code(files[5]), _code(files[6]), _code(rel['F1'] + '/'),
            _code('fresh1'), _code('fresh7'), _code('best'), a, z, _code('log.txt'))))
    files = [r['src'] for r in D.ocm_bw_core]
    a, z = loglines('F1', files)
    R['corebw'] = S.ref('ocm-core-bw-F1', (
        'Core bandwidth files on OCM of %s: %s to %s, %s and %s in %s. Rep rows and the %s row. '
        'Their commands are lines %d to %d of %s.' % (
            F1N, _code(files[0]), _code(files[4]), _code(files[5]), _code(files[6]), _code(rel['F1'] + '/'),
            _code('best'), a, z, _code('log.txt'))))
    ms = D.mesh_summary
    R['map'] = S.ref('ocm-mesh-map', (
        'Mesh map printed by the Linux mesh driver (%s) in %s of %s, lines %d to %d, in %s. '
        'Boot F2 has no such file.' % (
            _code('arm-cmn'), _code('sysinfo.txt'), F1N, ms['map_first_line'], ms['map_last_line'],
            _code(rel['F1'] + '/'))))
    bl = [r['base_line'] for r in D.mesh_layout]
    R['iomem'] = S.ref('ocm-iomem', (
        'Physical address ranges of the five OCM regions: %s of %s, lines %d to %d, in %s.' % (
            _code('sysinfo.txt'), F1N, min(bl), max(bl), _code(rel['F1'] + '/'))))
    R['hns'] = S.ref('ocm-lib-run-hns', (
        'Home node ids of OCM regions 0 to 4: %s line 39 (%s) in the project folder.' % (
            _code('lib_run.sh'), _code('HNS="%s"' % ','.join('%d' % n for n in _data.REGION_NODE)))))
    R['readme'] = S.ref('ocm-readme-steps', (
        'The project file %s, lines 39 to 40: the mesh port of CPU 2 is one mesh step from the home nodes of '
        'OCM regions 0 to 2 and three mesh steps from the home nodes of regions 3 and 4. Lines 124 to 128: what '
        'the three mesh counter events count.' % _code('README.md')))
    R['bwc'] = S.ref('ocm-bandwidth-c-segments', (
        'Source file %s, lines 314 to 323: the bandwidth program calls the kernel once per region of the '
        'buffer.' % _code('bandwidth.c')))
    c = D.mesh_control['F1']
    R['ctl'] = S.ref('ocm-cmn-control-F1', (
        'Mesh counter file %s of %s, label %s (%s).' % (
            _code('cmn-counts.csv'), F1N, _code(c['label']), c['what'])))
    R['kern'] = S.ref('cme-kern-read4', (
        'Source file %s, lines 174 to 196: the loop of the CME read kernel. One loop iteration has four LD1B '
        'instructions of four 64-byte vectors each and 16 EOR instructions.' % _code('cme_kern.S')))
    fr = [r for r in D.chain['F1'] if r['kind'] == 'every line flushed first'][0]
    R['flat'] = S.ref('ocm-dram-flushed-lat', (
        'CME latency file %s of both boots (8 MiB, every line flushed first), row %s.' % (
            _code(fr['src']), _code('cme-best'))))
    return R


# ----------------------------------------------------------------- the section

def build(D, V, S):
    K = _data.KIB
    R = _refs(D, S)
    lat = {b: D.ocm_lat[b] for b in _data.BOOTS}
    by = {b: {r['name']: r for r in lat[b]} for b in _data.BOOTS}
    st1, st2 = D.ocm_stats['F1'], D.ocm_stats['F2']
    pairs = {p['name']: p for p in D.ocm_pairs}
    one2, all2 = _by_steps(lat['F2'])
    one1, all1 = _by_steps(lat['F1'])
    order = [r['name'] for r in one2] + [r['name'] for r in all2]
    ms = D.mesh_summary
    lay = D.mesh_layout
    dsu = ms['dsu1_xy']
    n_regions = len(lay)
    region_kib = _data.REGION_BYTES // K
    region_lines = _data.REGION_LINES
    near_regions = [r['region'] for r in lay if r['steps'] == min(x['steps'] for x in lay)]
    far_regions = [r['region'] for r in lay if r['steps'] == max(x['steps'] for x in lay)]
    near_steps = min(x['steps'] for x in lay)
    far_steps = max(x['steps'] for x in lay)
    near_txt = 'regions %d to %d' % (near_regions[0], near_regions[-1])
    far_txt = 'regions %d and %d' % (far_regions[0], far_regions[-1])

    # ---- terms
    S.term('OCM', 'on-chip memory. %d regions of %d KiB each (%s lines of %d bytes), held in the home nodes '
                  'of the mesh.' % (n_regions, region_kib, _n(region_lines, 0), _data.LINE))
    S.term('CME', 'the Arm C1-SME2 matrix engine unit. One per cluster, shared by two cores.')
    S.term('Mesh', 'the on-chip network (Arm CMN) that joins the clusters, the home nodes and the bridges to memory.')
    S.term('Crosspoint', 'one junction of the mesh. A crosspoint is named by its position (x,y).')
    S.term('Mesh step', 'a move from one crosspoint to the next one. The step count between two crosspoints '
                        'is the difference in x plus the difference in y.')
    S.term('Home node', 'the mesh device that owns an address range. Each of the five home nodes holds one OCM region.')
    S.term('Cluster port', 'the mesh device through which one cluster (two cores and their CME) sends its requests.')
    S.term('DSU 1', 'the cluster of CPUs 2 and 3. Its CME runs every CME row of this page, called from CPU 2.')
    S.term('Chain load', 'one load of the latency test. Each load reads the address of the next load.')
    S.term('Latency test', 'a loop over a chain of pointers, one pointer per member line. The result is the time per chain load.')
    S.term('Pass', 'one walk over the buffer or over the chain.')
    S.term('Rep', 'one timed measurement.')
    S.term('Kernel', 'the test loop in the assembly file <code>cme_kern.S</code>. It is not the Linux kernel.')
    S.term('Bracket time', 'the time between two clock reads in C around the kernel call or calls.')
    S.term('Span time', 'the time between the two counter reads inside the kernel, after the CME starts its '
                        'streaming mode and before it stops it.')
    S.term('Outside-span time', 'bracket time minus span time.')
    S.term('Round-trip baseline', 'a chain through a CME register with no memory access (instructions DUP and LASTB).')
    S.term('Inner refill', 'a refill of the CME L1 whose line came from inside the cluster.')
    S.term('Outer refill', 'a refill of the CME L1 whose line came from outside the cluster.')
    S.term('Read refill', 'a refill of the CME L1 that a load of the program asked for (a demand refill).')
    S.term('Prefetch refill', 'a refill of the CME L1 that the hardware prefetcher asked for.')
    S.term('Demand-only row', 'a row that counts 0 prefetch refills per load in every pass.')
    S.term('Spread', 'the highest value minus the lowest value, divided by the lowest value, over the passes or reps of one row, in percent.')
    S.term('Idle control', 'a mesh count taken while a small command runs that sends almost no requests to the home '
                          'nodes. It gives the background count.')
    S.term('Command lifetime', 'the time from the start to the end of a command. The mesh counters run during '
                               'that time.')
    S.term('Level subtracted', 'the background count that is taken off the count of a home node. In a one-region '
                               'command it is the mean count of the four home nodes that do not hold the region.')
    S.term('Excess', 'the requests received by the home node of the region minus the level subtracted.')
    S.term('correlation coefficient', 'a number from -1 to 1 that says how close a set of points is to one straight '
                                  'line. 1 means that all points are on a rising line.')

    out = []
    bw = {b: {r['name']: r for r in D.ocm_bw[b]} for b in _data.BOOTS}
    bwp = {p['name']: p for p in D.ocm_bw_pairs}
    rd_names = ['region%d' % i for i in range(n_regions)]
    one_mesh = {b: [r for r in D.mesh_requests[b] if r['ocm'] and r['region'] is not None] for b in _data.BOOTS}
    n_one = sum(len(v) for v in one_mesh.values())

    # ---- key points of the section
    f1_hw = [v for r in one1 for v in r['hwprf_reps']]
    n_demand1 = len([r for r in lat['F1'] if r['demand_only']])

    def cnt(rows, key):
        """Whole count of one refill event in each pass: the rate per load times the loads of the pass."""
        return [x[key] * x['loads'] for r in rows for x in r['reps']]
    f2_outer_all = [v for r in lat['F2'] for v in r['outer_reps']]
    f2_hw_all = [v for r in lat['F2'] for v in r['hwprf_reps']]
    f1_hw_all = [v for r in lat['F1'] for v in r['hwprf_reps']]
    out.append(S.takeaways([
        'On %s every pass of the OCM rows counts %s outer refills and %s prefetch refills per load. A chain load '
        'takes %s of span time for %s and %s for %s.' % (
            F2N, _rng(f2_outer_all, 4), _rng(f2_hw_all, 4), _rng([st2['near_lo'], st2['near_hi']], 3, 'ns'), near_txt,
            _rng([st2['far_lo'], st2['far_hi']], 3, 'ns'), far_txt),
        ('On %s no OCM row is demand-only. ' % F1N if n_demand1 == 0 else
         'On %s %d of the %d OCM rows are demand-only. ' % (F1N, n_demand1, len(lat['F1'])))
        + 'The one-region rows read %s of span time with %s prefetch refills per load.' % (
            _rng([r['best_span'] for r in one1], 3, 'ns'), _rng(f1_hw, 2)),
        'The CME reads one OCM region at %s on boot F1 and at %s on boot F2.' % (
            _rng([bw['F1'][n]['best'] for n in rd_names], 1, 'GB/s'),
            _rng([bw['F2'][n]['best'] for n in rd_names], 1, 'GB/s')),
        'The CME writes all five regions at %s on boot F1 and at %s on boot F2. There is no write row for one region.' % (
            V.gbps(bw['F1']['write']['best']), V.gbps(bw['F2']['write']['best'])),
        'In %d of %d one-region commands the home node of the region receives the most requests. The mesh counts '
        'are totals over the whole command.' % (ms['intended_ok'], ms['intended_n']),
    ]))

    out.append(S.p('Each timed rep of an OCM latency row is one pass over its chain. So this section calls a timed '
                   'rep of these rows a pass, and "pass 1" is the row <code>cme-fresh1</code> of a file, "pass 2" the row '
                   '<code>cme-fresh2</code>, and so on.'))

    # =================================================================== 1. mesh map
    out.append(S.h3('ocm-map', 'The mesh and the five OCM regions'))
    out.append(S.bullets([
        'Each OCM region sits in one home node of the %d x %d mesh. The node id gives the position of the home node.' % (
            ms['grid_x'], ms['grid_y']),
        'The position of DSU 1 at crosspoint (%d,%d) is a hypothesis. From there %s are %s away and %s are %s away.' % (
            dsu[0], dsu[1], near_txt, _steps_word(near_steps), far_txt, _steps_word(far_steps)),
    ]))
    cells = []
    for r in lay:
        cells.append((r['x'], r['y'], ['region %d' % r['region'], 'id %d' % r['node'], _steps_word(r['steps'])], 'hn'))
    for p in D.mesh_rnf_steps:
        if p['is_dsu1_hypothesis']:
            cells.append((p['x'], p['y'], ['DSU 1', 'CME', 'hypothesis'], 'hyp'))
        else:
            cells.append((p['x'], p['y'], ['cluster', 'port'], 'port'))
    others = sum(v for k, v in ms['device_counts'].items() if k not in ('HN-S', 'RN-F'))
    empty_rows = [y for y in range(ms['grid_y']) if y not in {c[1] for c in cells}]
    mesh_svg = _mesh(ms['grid_x'], ms['grid_y'], cells, dsu, width=530)
    fig_map = S.fig(mesh_svg, (
        'The mesh of the chip, from the mesh map of %s (%s) %s. Rows: the %d home nodes and the %d cluster ports. '
        'The other %d devices of the map are left out. Rows y = %s hold none of the devices shown and are drawn '
        'lower. The dark strokes are the routes from the assumed position of DSU 1 to the home nodes, drawn on the '
        'mesh links that they use. The number at a link is its step number, counted from DSU 1. A route of '
        '%s passes behind the boxes on its way. It is one of the shortest routes, and the '
        'step count does not depend on which shortest route is taken.' % (
            F1N, _code('sysinfo.txt'), R['map'], ms['device_counts']['HN-S'], ms['device_counts']['RN-F'], others,
            ', '.join('%d' % y for y in empty_rows), _steps_word(far_steps))),
        '%d regions are %s from crosspoint (%d,%d) and %d regions are %s away.' % (
            len(near_regions), _steps_word(near_steps), dsu[0], dsu[1], len(far_regions), _steps_word(far_steps)))
    trows = []
    for r in lay:
        trows.append(['%d' % r['region'], '0x%08x' % r['base'], '%d' % r['node'], '%d' % r['hns_index'],
                      '(%d,%d)' % (r['x'], r['y']), '%d' % r['steps']])
    tab_map = _tab(S, ['Region', 'Physical|base', 'Home|node id', 'Index|in the map', 'Position|(x,y)', 'Mesh|steps'],
                      trows, caption='OCM region, home node and position. Sources: %s %s %s.' % (R['iomem'], R['hns'], R['map']),
                      note='Position: the crosspoint of the home node, with x = node id / 64 and y = (node id / 8) mod 8, whole numbers. Index in the map: '
                           'the number of the home node in the mesh map, which is not the region number. Mesh steps: '
                           'from crosspoint (%d,%d).' % dsu, align='lrrrcr')
    out.append('<div style="display:flex;gap:28px;flex-wrap:wrap;align-items:flex-start">'
               '<div style="flex:0 1 530px;min-width:0">%s</div><div style="flex:1 1 420px;min-width:0">%s</div></div>\n' % (
                   fig_map, tab_map))
    out.append(S.bullets([
        'Each region is %d KiB long, which is %d pages of 4 KiB. One page holds %d lines of %d bytes.' % (
            region_kib, _data.REGION_BYTES // (4 * K), 4 * K // _data.LINE, _data.LINE),
        'The map shows a home node at each of the five decoded positions %s.' % R['map'],
        'The map does not say which cluster port belongs to which cluster.',
        'The project file <code>README.md</code> states the step counts from CPU 2: one step to the home nodes of '
        'regions 0 to 2 and three steps to the home nodes of regions 3 and 4 %s.' % R['readme'],
        'The README gives notes of the operator as its source for these step counts. It names no design file.',
        'Only %d of the %d cluster ports gives these step counts (Table %d).' % (
            len(ms['rnf_cells_matching_1_1_1_3_3']), len(D.mesh_rnf_steps), S.next_table()),  # the table that follows
    ]))
    tab_ports = S.next_table()
    prow = []
    for p in D.mesh_rnf_steps:
        prow.append(['(%d,%d)' % (p['x'], p['y'])] + ['%d' % s for s in p['steps']]
                    + ['yes (hypothesis)' if p['is_dsu1_hypothesis'] else 'no'])
    out.append(_tab(S, ['Cluster port at crosspoint'] + ['Steps to region %d' % i for i in range(n_regions)]
                       + ['Matches the stated step counts'], prow,
                       caption='Mesh steps from each cluster port of the map to the five home nodes %s.' % R['map'],
                       highlight=lambda i, row: row[-1].startswith('yes')))
    out.append(S.hyp(
        'DSU 1 (CPUs 2 and 3 and their CME) uses the cluster port at crosspoint (%d,%d).' % dsu,
        'A file that names the mesh port of each cluster would confirm or reject it. The device tree or the '
        'mesh configuration of the chip is such a file. Neither is in the result folders.'))
    out.append(S.insufficient(
        'The origin of the step counts in the project file <code>README.md</code> %s. The file does not say '
        'whether they come from the chip design or from latency rows. If they come from latency rows, the time '
        'difference between the regions (%s) is not independent support for them. The mesh configuration of the '
        'chip would resolve it.' % (R['readme'], S.xref('ocm-steps'))))

    # =================================================================== 2. chain load per region
    out.append(S.h3('ocm-chain', 'Chain load per region, both boots'))
    f2_over = [pairs[n]['f2_over_f1_span'] for n in order if pairs[n]['region'] is not None]
    all_above = all(pairs[n]['f2_all_above_f1'] for n in order)
    out.append(S.bullets([
        'A chain load from OCM takes %s of span time on %s. Every pass of these rows counts %s prefetch refills '
        'per load.' % (_rng([r['best_span'] for r in lat['F2']], 3, 'ns'), F2N, _rng(f2_hw_all, 4)),
        'The same rows read %s on %s. Their passes count %s prefetch refills per load. Boot F2 is %s times boot F1 '
        'for one region.' % (
            _rng([r['best_span'] for r in lat['F1']], 3, 'ns'), F1N, _rng(f1_hw_all, 2), _rng(f2_over, 2)),
    ]))
    drows = []
    for steps_n in (near_steps, far_steps):
        drows.append(dict(header='%s from crosspoint (%d,%d), %s' % (_steps_word(steps_n), dsu[0], dsu[1], SHAPE_PAGE)))
        for r in one2:
            if r['steps'] != steps_n:
                continue
            p = pairs[r['name']]
            drows.append(dict(label='region %d' % r['region'], sub='home node %d' % r['node'],
                              a=p['f2_best_span'], b=p['f1_best_span'],
                              gap=V.signed(p['f1_best_span'] - p['f2_best_span'], 3, 'ns')))
    drows.append(dict(header='All five regions in one chain'))
    for r in all2:
        p = pairs[r['name']]
        drows.append(dict(label=r['shape'], sub='%s loads per pass' % _n(r['loads'], 0),
                          a=p['f2_best_span'], b=p['f1_best_span'],
                          gap=V.signed(p['f1_best_span'] - p['f2_best_span'], 3, 'ns')))
    fig_chain = S.next_fig()
    out.append(S.fig(
        V.dumbbell(drows, a_name='CME, ' + F2N, b_name='CME, ' + F1N, a_color='f2', b_color='f1', unit='ns',
                   xlabel='chain load, span time, ns per load', refs=[(D.rt_span_ns, 'round-trip baseline, span time')],
                   xrange=(20, None), label_w=270),
        'Chain load from OCM through the CME, span time of the fastest pass. The bold number is boot F1 minus '
        'boot F2. Rows: the five one-region rows ordered '
        'by mesh steps, and the two all-five rows. Files %s to %s, %s and %s of %s %s and of %s %s.' % (
            _code(by['F2']['region0']['src']), _code(by['F2']['region4']['src']), _code(by['F2']['all5']['src']),
            _code(by['F2']['all5-dense']['src']), F2N, R['latF2'], F1N, R['latF1']),
        'Boot F2 (%s prefetch refills per load) is %s slower than boot F1 (%s prefetch refills per load) in every '
        'row. On boot F2 the one-region rows form two groups by mesh steps.' % (
            _rng(f2_hw_all, 4), _rng([pairs[n]['f2_best_span'] - pairs[n]['f1_best_span'] for n in order], 1, 'ns'),
            _rng(f1_hw_all, 2))))
    out_all = [v for b in _data.BOOTS for r in lat[b] if r['region'] is not None for v in r['outside_reps']]
    bms = [r['best'] - r['best_span'] for b in _data.BOOTS for r in lat[b] if r['region'] is not None]
    out.append(S.bullets([
        'Every OCM row is a chain that is walked once, with every line flushed first.',
        'Each timed pass walks a chain that no pass walked before. So one timed pass is one rep, which is one data '
        'row of the CSV file.',
        'The rows have two shapes. The shape "%s" has %d loads per region and pass. The shape "%s" has %s loads '
        'over all five regions.' % (SHAPE_PAGE, by['F2']['region0']['loads'], SHAPE_ALL, _n(by['F2']['all5-dense']['loads'], 0)),
        'The figure uses span time. One pass is one kernel call.',
        'A call spends %s outside its span in the one-region rows (all %d passes of both boots). Divided by the '
        '%d loads of a pass, that is %s per load.' % (
            _rng(out_all, 0, 'ns'), len(out_all), by['F2']['region0']['loads'],
            _rng([v / by['F2']['region0']['loads'] for v in out_all], 2, 'ns')),
        'The best bracket time of a one-region row is %s per load above its best span time (Table %d).' % (
            _rng(bms, 2, 'ns'), S.next_table()),
        'The span value of a row is the lowest span time over its passes.',
    ]))
    trows = []
    for b in ('F2', 'F1'):
        trows.append(BOOTC[b])
        for n in order:
            r = by[b][n]
            trows.append([
                _row_full(r) + ((' (%s)' % _steps_word(r['steps'])) if r['region'] is not None else ''),
                _n(r['loads'], 0), '%d' % r['n_reps'], _n(r['best_span']), _n(r['best']),
                _n(r['best_span_above_rt']), _rng(r['hwprf_reps'], 2), 'yes' if r['demand_only'] else 'no'])
    out.append(_tab(S, 
        ['Row (mesh steps)', 'Loads|per pass', 'Timed|passes', 'Span time,|ns per load', 'Bracket time,|ns per load',
         'Span time minus|the round-trip|baseline, ns', 'Prefetch refills|per load, over|the passes', 'Demand-|only'],
        trows, caption='Chain load from OCM through the CME. Files as in Figure %d %s %s.' % (
            fig_chain, R['latF2'], R['latF1']),
        note='Span time: lowest over the passes. Bracket time: the %s row of the program. The round-trip baseline '
             'is %s of span time in these files. It is a separate measurement with no memory access (instructions DUP and '
             'LASTB). The chain kernel has the instructions LD1D and LASTB. So the column "span time minus the '
             'round-trip baseline" is the difference between two kernels. It is not the time of the OCM access '
             'alone. The one-region rows have the shape "%s".' % (
                 _code('cme-best'), V.ns(D.rt_span_ns), SHAPE_PAGE)))
    out.append(S.insufficient(
        'What part of the span time minus the round-trip baseline is the time of the OCM access is not known. '
        'The chain kernel and the baseline kernel share the instruction LASTB and the loop. No row measures the '
        'time of the part that they share. A calibration of the non-memory time that the two kernels share would '
        'give it.'))
    a2p, a2e = by['F2']['all5'], by['F2']['all5-dense']
    a1p, a1e = by['F1']['all5'], by['F1']['all5-dense']
    out.append(S.bullets([
        'On boot F2 the two shapes differ by %s. The all-five rows read %s (%s) and %s (%s) of span time. The mean '
        'of the five one-region rows is %s.' % (
            V.ns(abs(a2p['best_span'] - a2e['best_span'])), V.ns(a2p['best_span']), SHAPE_PAGE,
            V.ns(a2e['best_span']), SHAPE_ALL, V.ns(st2['mean_of_five'])),
        'On boot F1 the two shapes differ by %s. The row with every line reads %s and the row with %s reads %s.' % (
            V.ns(abs(a1e['best_span'] - a1p['best_span'])), V.ns(a1e['best_span']), SHAPE_PAGE, V.ns(a1p['best_span'])),
        'The boot F1 row with every line counts %s read refills, %s prefetch refills and %s outer refills per load.' % (
            _rng(a1e['rd_reps'], 4), _rng(a1e['hwprf_reps'], 2), _rng(a1e['outer_reps'], 2)),
        ('Every pass of boot F2 is slower than every pass of boot F1, in all %d rows.' % len(order)) if all_above else
        'The pass ranges of the two boots overlap in at least one row.',
    ]))
    out.append(S.hyp(
        'Most lines that the prefetcher brings in the boot F1 row with every line are not the next member of the '
        'chain.',
        'A count of the chain loads that find their line in the CME L1 would confirm or reject it. The files hold '
        'refill counts only.'))
    out.append(S.insufficient(
        'The cost of address translation in these rows is not known. The OCM rows use 4 KiB pages and carry no '
        'counter of translation misses. The same OCM rows on a mapping with larger pages, on a boot with the '
        'prefetchers off, would give it.'))

    # =================================================================== 3. time against mesh steps
    out.append(S.h3('ocm-steps', 'Time against mesh steps on boot F2'))
    out.append(S.bullets([
        'On %s the regions at %s read %s more span time than the regions at %s (means %s and %s).' % (
            F2N, _steps_word(far_steps), V.ns(st2['far_minus_near']), _steps_word(near_steps),
            V.ns(st2['far_mean']), V.ns(st2['near_mean'])),
        ('Every pass of %s (%s) is slower than every pass of %s (%s).' % (
            far_txt, _rng([st2['far_pass_lo'], st2['far_pass_hi']], 3, 'ns'), near_txt,
            _rng([st2['near_pass_lo'], st2['near_pass_hi']], 3, 'ns'))) if st2['far_all_above_near'] else
        'The pass ranges of the two groups overlap on boot F2.',
    ]))
    srows = []
    for steps_n in (near_steps, far_steps):
        srows.append(dict(header='%s from crosspoint (%d,%d)' % (_steps_word(steps_n), dsu[0], dsu[1])))
        for r in one2:
            if r['steps'] == steps_n:
                srows.append(dict(label='region %d' % r['region'],
                                  sub='home node %d, %d passes' % (r['node'], r['n_reps']),
                                  values=[r['passes_span']], note='best %s' % V.ns(r['best_span'])))
    out.append(S.fig(
        _strip(srows, [('CME, ' + F2N + ', one dot per pass', 'f2')], unit='ns',
               xlabel='chain load, span time, ns per load',
               refs=[(st2['near_mean'], 'mean of the best values, %s: %s' % (_steps_word(near_steps), V.ns(st2['near_mean']))),
                     (st2['far_mean'], 'mean of the best values, %s: %s' % (_steps_word(far_steps), V.ns(st2['far_mean'])))],
               dim=(st2['near_mean'], st2['far_mean'], V.signed(st2['far_minus_near'], 3, 'ns') + ' for %d more steps' % st2['extra_steps']),
               title='span time per pass by mesh steps, boot F2'),
        'Span time of each of the %d timed passes of the five one-region rows of %s, grouped by mesh steps. Passes '
        'with equal or nearly equal values are drawn one above the other. Files %s to %s %s.' % (
            st2['n_passes'], F2N, _code(by['F2']['region0']['src']), _code(by['F2']['region4']['src']), R['latF2']),
        ('The two groups do not overlap. ' if st2['far_all_above_near'] else 'The two groups overlap. ')
        + 'The rows at %s read %s more time per load than the rows at %s.' % (
            _steps_word(far_steps), V.ns(st2['far_minus_near']), _steps_word(near_steps))))
    med1_near = [by['F1']['region%d' % i]['median_span'] for i in near_regions]
    med1_far = [by['F1']['region%d' % i]['median_span'] for i in far_regions]
    f1_best_sep = st1['far_lo'] > st1['near_hi']
    f1_med_sep = min(med1_far) > max(med1_near)
    f1_pass_sep = st1['far_pass_lo'] > st1['near_pass_hi']
    out.append(S.bullets([
        'The two groups are an observation by region: regions 3 and 4 against regions 0 to 2.',
        'The step counts depend on the hypothesis of the position of DSU 1, and the origin of the stated step '
        'counts is not known (%s). So mesh steps are one hypothesis for the two groups.' % S.xref('ocm-map'),
        'The best values of boot F1 %s the two groups. %s read %s and %s read %s there.' % (
            'separate' if f1_best_sep else 'do not separate', near_txt.capitalize(),
            _rng([st1['near_lo'], st1['near_hi']], 3, 'ns'), far_txt, _rng([st1['far_lo'], st1['far_hi']], 3, 'ns')),
        'The medians of boot F1 %s the two groups. They are %s for %s and %s for %s (Table %d).' % (
            'separate' if f1_med_sep else 'do not separate', _rng(med1_near, 3, 'ns'), near_txt,
            _rng(med1_far, 3, 'ns'), far_txt, S.next_table()),
        ('The pass ranges of boot F1 do not overlap (%s and %s).' if f1_pass_sep else
         'The pass ranges of boot F1 overlap (%s and %s). So boot F1 cannot give a cost per step.') % (
            _rng([st1['near_pass_lo'], st1['near_pass_hi']], 3, 'ns'), _rng([st1['far_pass_lo'], st1['far_pass_hi']], 3, 'ns')),
    ]))
    out.append(S.hyp(
        'The %s difference is the cost of %d more mesh steps on the way to the home node and %d more on the way back. '
        'That is %s per step of distance (est.), request and data together.' % (
            V.ns(st2['far_minus_near']), st2['extra_steps'], st2['extra_steps'], V.ns(st2['ns_per_extra_step'], 2)),
        'The same rows from the CME of another cluster would confirm or reject it. The step counts to the five '
        'regions differ there (Table %d).' % tab_ports))

    # =================================================================== 4. pass values and spread
    out.append(S.h3('ocm-spread', 'Pass values and spread'))
    out.append(S.bullets([
        'On %s the passes of a one-region row lie within %s of each other (span time).' % (
            F2N, _rng([st2['spread_span_lo'], st2['spread_span_hi']], 2, '%')),
        'On %s they lie %s apart.' % (F1N, _rng([st1['spread_span_lo'], st1['spread_span_hi']], 1, '%')),
    ]))
    srows = []
    srows.append(dict(header='One region, %s' % SHAPE_PAGE))
    for r in one2:
        r1 = by['F1'][r['name']]
        srows.append(dict(label='region %d' % r['region'], sub=_steps_word(r['steps']),
                          values=[r['passes_span'], r1['passes_span']],
                          note='spread: F2 %s, F1 %s' % (V.pct(r['spread_span_pct'], 2), V.pct(r1['spread_span_pct'], 2))))
    srows.append(dict(header='All five regions'))
    for r in all2:
        r1 = by['F1'][r['name']]
        srows.append(dict(label=r['shape'], sub='%d passes' % r['n_reps'],
                          values=[r['passes_span'], r1['passes_span']],
                          note='spread: F2 %s, F1 %s' % (V.pct(r['spread_span_pct'], 2), V.pct(r1['spread_span_pct'], 2))))
    out.append(S.fig(
        _strip(srows, [('CME, ' + F2N, 'f2'), ('CME, ' + F1N, 'f1')], unit='ns',
               xlabel='chain load, span time, ns per load', title='span time per pass, both boots'),
        'Span time of every timed pass of the seven OCM rows, one dot per pass. Passes with equal or nearly equal '
        'values are drawn one above the other. The text on the right is the spread of each boot. Files as in '
        'Figure %d %s %s.' % (fig_chain, R['latF2'], R['latF1']),
        'The boot F2 passes of a row lie within %s of each other. The boot F1 passes of a one-region row range over %s.' % (
            V.ns(max(max(r['passes_span']) - min(r['passes_span']) for r in lat['F2']), 2),
            _rng([max(r['passes_span']) - min(r['passes_span']) for r in one1], 1, 'ns'))))
    trows = []
    for n in order:
        r2, r1 = by['F2'][n], by['F1'][n]
        trows.append([_row_full(r2), '%d' % r2['n_reps'],
                      _rng(r2['passes_span']), _n(r2['median_span']), _n(r2['spread_span_pct'], 2),
                      _rng(r1['passes_span']), _n(r1['median_span']), _n(r1['spread_span_pct'], 2)])
    out.append(_tab(S, 
        ['Row', 'Timed|passes', 'Boot F2: lowest|to highest, ns', 'Boot F2:|median, ns', 'Boot F2:|spread, %',
         'Boot F1: lowest|to highest, ns', 'Boot F1:|median, ns', 'Boot F1:|spread, %'],
        trows, caption='Span time per load over the timed passes of each row %s %s.' % (R['latF2'], R['latF1'])))
    out.append(S.bullets([
        'A one-region pass has %d loads. On boot F1 a pass counts %s read refills. Their number differs from pass '
        'to pass (%s).' % (
            by['F1']['region0']['loads'],
            _rng([x['rd'] * x['loads'] for r in one1 for x in r['reps']], 0), S.xref('ocm-refills')),
    ]))

    # =================================================================== 5. refill counters
    out.append(S.h3('ocm-refills', 'What the refill counters show'))
    f2rows = lat['F2']
    cdiff = max(abs(v) for b in _data.BOOTS for r in lat[b] for v in r['counter_sum_diff'])
    f2_const = all(_n(min(r[k + '_reps']), 4) == _n(max(r[k + '_reps']), 4) for r in f2rows for k in ('rd', 'outer', 'inner', 'hwprf'))
    out.append(S.bullets([
        'On %s every pass of all %d rows counts %s read refills, %s outer refills, %s inner refills and %s prefetch '
        'refills per load.' % (
            F2N, st2['demand_only_rows'], _rng([v for r in f2rows for v in r['rd_reps']], 4),
            _rng([v for r in f2rows for v in r['outer_reps']], 4), _rng([v for r in f2rows for v in r['inner_reps']], 4),
            _rng([v for r in f2rows for v in r['hwprf_reps']], 4)),
        'A one-region pass of boot F2 has %d loads. Each of the %d one-region passes of boot F2 counts %s read '
        'refills, %s outer refills and %s prefetch refills.' % (
            one2[0]['loads'], len(cnt(one2, 'rd')), _rng(cnt(one2, 'rd'), 0), _rng(cnt(one2, 'outer'), 0),
            _rng(cnt(one2, 'hwprf'), 0)),
        'These counts are totals of a pass. They do not say which load caused which refill.',
        'On %s every pass counts prefetch refills (%s per load in the one-region rows).' % (F1N, _rng(f1_hw, 2)),
        'On boot F1 a pass with fewer read refills is faster. The correlation coefficient between read refills per load '
        'and span time is +%s over the %d one-region passes (+1 is an exact rising line).' % (
            _n(st1['rd_fit_r'], 3), st1['n_passes']),
    ]))

    def ptip(b, r, k):
        return '%s, region %d, pass %d\n%s read refills per load\n%s span time per load' % (
            BOOTN[b], r['region'], k + 1, _n(r['rd_reps'][k], 2), V.ns(r['passes_span'][k]))
    p1 = [(r['rd_reps'][k], r['passes_span'][k], ptip('F1', r, k)) for r in one1 for k in range(r['n_reps'])]
    p2 = [(r['rd_reps'][k], r['passes_span'][k]) for r in one2 for k in range(r['n_reps'])]
    x2 = [x for x, _ in p2]
    f2_one_x = _n(min(x2), 2) == _n(max(x2), 2)
    cols2 = [[(r['passes_span'][k], ptip('F2', r, k)) for k in range(r['n_reps'])] for r in one2]
    fit_x = (min(p[0] for p in p1), max(p[0] for p in p1))
    fig_rd = S.next_fig()
    sc = _scatter(
        dict(name='CME, ' + F1N + ', %d passes' % len(p1), color='f1', points=p1),
        dict(name='CME, ' + F2N + ', %d passes' % len(p2), color='f2', x=sum(x2) / len(x2), cols=cols2),
        (st1['rd_fit_slope'], st1['rd_fit_intercept']), fit_x,
        (D.rt_span_ns, 'round-trip baseline, span time: %s' % V.ns(D.rt_span_ns)),
        dict(zero='0 read refills: %s (est.), %s above the baseline' % (
                 V.ns(st1['rd_fit_intercept'], 2), V.ns(st1['rd_fit_intercept'] - D.rt_span_ns, 2)),
             end='line extended to %s: %s (est.)' % (_n(sum(x2) / len(x2), 2), V.ns(st1['rd_fit_at_1'], 2)),
             b=['boot F2, measured',
                '%s: %s' % (_steps_word(near_steps), _rng([st2['near_pass_lo'], st2['near_pass_hi']], 3, 'ns')),
                '%s: %s' % (_steps_word(far_steps), _rng([st2['far_pass_lo'], st2['far_pass_hi']], 3, 'ns'))],
             fit='line through the boot F1 passes: %s + %s per read refill (est.)' % (
                 V.ns(st1['rd_fit_intercept'], 2), V.ns(st1['rd_fit_slope'], 2))),
        xlabel='read refills per load of the pass', ylabel='span time, ns per load')
    out.append(S.fig(
        sc,
        'Span time of a pass against its read refills per load. Rows: every timed pass of the five one-region rows '
        'of both boots. The line is fitted to the boot F1 passes only. It is solid over the range of those passes '
        '(%s read refills per load) and dashed where it is extended. The boot F2 dots all have %s read %s per load. '
        'Boot F2 dots with equal or nearly equal times are drawn side by side, so that each dot can be seen. '
        'Files %s to %s %s %s.' % (
            _rng(fit_x, 2), _rng(x2, 2), 'refill' if f2_one_x else 'refills',
            _code(by['F1']['region0']['src']), _code(by['F1']['region4']['src']), R['latF1'], R['latF2']),
        'All boot F2 passes have %s read %s per load. The boot F1 passes have %s. On boot F1 a pass with fewer read '
        'refills is faster.' % (_rng(x2, 2), 'refill' if f2_one_x else 'refills', _rng([p[0] for p in p1], 2))))
    tab_refills = S.next_table()
    trows = []
    for b in ('F2', 'F1'):
        trows.append(BOOTC[b])
        for n in order:
            r = by[b][n]
            trows.append([_row_full(r),
                          _rng(r['rd_reps'], 4), _rng(r['hwprf_reps'], 4), _rng(r['outer_reps'], 4),
                          _rng(r['inner_reps'], 4), 'yes' if r['demand_only'] else 'no'])
    out.append(_tab(S, 
        ['Row', 'Read refills|per load', 'Prefetch refills|per load', 'Outer refills|per load',
         'Inner refills|per load', 'Demand-|only'],
        trows, caption='Refills of the CME L1 per chain load, lowest to highest over the timed passes %s %s.' % (
            R['latF2'], R['latF1']),
        note='Read refills plus prefetch refills equal inner refills plus outer refills within %s per load in every '
             'pass of both boots.' % _n(cdiff, 4)))
    out.append(S.bullets([
        'The line through the boot F1 passes gives %s at 1 read refill per load (est.). The measured boot F2 values '
        'are %s.' % (V.ns(st1['rd_fit_at_1'], 2), _rng([r['best_span'] for r in one2], 3, 'ns')),
        'The boot F1 rows count inner refills, although every line is flushed before each pass. The one-region '
        'rows count %s inner refills per load. The row with every line counts %s.' % (
            _rng([v for r in one1 for v in r['inner_reps']], 2), _rng(a1e['inner_reps'], 2)),
        ('Every boot F1 row counts prefetch refills. Every boot F2 row counts %s prefetch refills per load. So the '
         'boot F2 rows are the rows to quote for a chain load from OCM.' % _rng(f2_hw_all, 4)
         if n_demand1 == 0 and st2['demand_only_rows'] == len(f2rows) else
         'Only the demand-only rows of Table %d count 0 prefetch refills per load.' % tab_refills),
    ]))
    out.append(S.hyp(
        'On boot F2 each timed load causes one read refill of the CME L1, and the line of that refill comes from '
        'outside the cluster.',
        'A record of the refills by address would confirm or reject it. The files hold one count per pass.'))
    out.append(S.hyp(
        'A chain load that causes no read refill takes about as long as one step of the round-trip baseline. A '
        'chain load that causes a read refill from OCM takes about %s more (est.). The line of Figure %d gives %s '
        'at 0 read refills (est.). That is %s above the round-trip baseline of %s.' % (
            V.ns(st1['rd_fit_slope'], 1), fig_rd, V.ns(st1['rd_fit_intercept'], 2),
            V.ns(st1['rd_fit_intercept'] - D.rt_span_ns, 2), V.ns(D.rt_span_ns)),
        'A time stamp per load, or a row in which every line is prefetched before the timed pass, would confirm or reject it.'))

    # =================================================================== 6. core beside the CME
    out.append(S.h3('ocm-core', 'The core beside the CME on boot F1'))
    core = {r['name']: r for r in D.ocm_core}
    pe = pairs['all5-dense']
    one_names = [r['name'] for r in one2]
    both_demand = pe['core_demand_only'] and by['F2']['all5-dense']['demand_only']
    core_prf = [v for n in order if not pairs[n]['core_demand_only'] for v in core[n]['l2d_hwprf_reps']]
    n_core_prf = len([n for n in order if not pairs[n]['core_demand_only']])
    out.append(S.bullets([
        'On %s a chain load from one OCM region takes %s on the core (CPU 2) and %s of span time through the CME. '
        'The CME is %s times the core.' % (
            F1N, _rng([core[n]['best'] for n in one_names], 3, 'ns'), _rng([by['F1'][n]['best_span'] for n in one_names], 3, 'ns'),
            _rng([pairs[n]['f1_span_over_core'] for n in one_names], 2)),
        ('The core row with every line is demand-only and reads %s. The CME row with every line on boot F2 is also '
         'demand-only and reads %s. That is %s more.' if both_demand else
         'The core row with every line reads %s. The CME row with every line on boot F2 reads %s. That is %s more. '
         'At least one of the two rows is not demand-only.') % (
            V.ns(pe['core']), V.ns(pe['f2_best_span']), V.ns(pe['f2_span_minus_core'])),
        'The difference of %s is %s %s the round-trip baseline of %s.' % (
            V.ns(pe['f2_span_minus_core']), V.ns(abs(D.rt_span_ns - pe['f2_span_minus_core'])),
            'below' if pe['f2_span_minus_core'] < D.rt_span_ns else 'above', V.ns(D.rt_span_ns)),
        'Put the other way, the boot F2 CME row minus the round-trip baseline is %s, and the core row reads %s.' % (
            V.ns(pe['f2_best_span'] - D.rt_span_ns), V.ns(pe['core'])),
        'The round-trip baseline is a separate measurement with no memory access. The rows do not show that a chain '
        'load contains the baseline time as a fixed part.',
    ]))
    drows = [dict(header='One region, %s' % SHAPE_PAGE)]
    for n in order:
        p = pairs[n]
        if p['region'] is None and len(drows) == 1 + n_regions:
            drows.append(dict(header='All five regions'))
        drows.append(dict(label=(('region %d (%s)' % (p['region'], _steps_word(p['steps']))) if p['region'] is not None
                                 else p['shape']),
                          sub=('core row is demand-only' if p['core_demand_only'] else
                               'core L2 prefetch: %s refills per load' % _rng(core[n]['l2d_hwprf_reps'], 2)),
                          a=p['core'], b=p['f1_best_span'],
                          gap='%s (%s)' % (V.signed(p['f1_span_minus_core'], 3, 'ns'), V.ratio(p['f1_span_over_core']))))
    out.append(S.fig(
        V.dumbbell(drows, a_name='core (CPU 2), boot F1, bracket time', b_name='CME, ' + F1N + ', span time',
                   a_color='core', b_color='f1', unit='ns',
                   xlabel='chain load, ns per load (core: bracket time, CME: span time)', label_w=290),
        'Chain load from OCM on %s: the core against the CME, same chains and same flush rule. Rows: the seven OCM '
        'rows. The core rows have no span time, so the core dot is bracket time. The CME dot is span time. The '
        'small text under each row label gives the prefetch refills of the core L2 in the core row. Core files %s '
        'to %s, %s and %s %s. CME files %s.' % (
            F1N, _code(core['region0']['src']), _code(core['region4']['src']), _code(core['all5']['src']),
            _code(core['all5-dense']['src']), R['corelat'], R['latF1']),
        'On boot F1 a chain load from OCM takes %s longer through the CME (span time) than on the core (bracket '
        'time). That is %s times the core time. %d of the %d core rows and %d of the %d CME rows count prefetch refills.' % (
            _rng([pairs[n]['f1_span_minus_core'] for n in order], 1, 'ns'),
            _rng([pairs[n]['f1_span_over_core'] for n in order], 2),
            n_core_prf, len(order), len(lat['F1']) - n_demand1, len(lat['F1']))))
    trows = []
    for n in order:
        p, c = pairs[n], core[n]
        trows.append([('region %d' % p['region']) if p['region'] is not None else 'all five, ' + p['shape'],
                      _n(p['core']), _n(p['core_spread_pct'], 2), _rng(c['l2d_hwprf_reps'], 2),
                      _n(p['f1_best_span']),
                      _n(p['f1_span_minus_core']), V.ratio(p['f1_span_over_core']), _n(p['f2_best_span']),
                      _n(p['f2_span_minus_core'])])
    out.append(_tab(S, 
        ['Row', 'Core,|boot F1,|ns per load', 'Core|spread,|%', 'Core L2|prefetch refills|per load',
         'CME,|boot F1,|span, ns', 'CME boot F1|minus|core, ns', 'CME|boot F1|over core',
         'CME,|boot F2,|span, ns', 'CME boot F2|minus core|boot F1, ns'],
        trows, caption='The core (CPU 2) beside the CME on OCM %s %s %s.' % (R['corelat'], R['latF1'], R['latF2']),
        note='Core values are bracket time: the core rows have no span time and no kernel call. The last column '
             'compares rows of two boots. The highlighted row is the one demand-only core row.',
        highlight=[i for i, n in enumerate(order) if pairs[n]['core_demand_only']]))
    out.append(S.bullets([
        'The core rows with %s are not demand-only. They count %s prefetch refills of the core L2 per load.' % (
            SHAPE_PAGE, _rng(core_prf, 2)),
        'The CME rows of boot F1 count %s prefetch refills of the CME L1 per load (Table %d).' % (
            _rng([v for r in lat['F1'] for v in r['hwprf_reps']], 2), tab_refills),
        'The core row with every line (boot F1) and the CME row with every line (boot F2) come from different boots. '
        'The core row counts %s prefetch refills of the core L2 per load. The CME row counts %s prefetch refills of '
        'the CME L1 per load.' % (
            _rng(core['all5-dense']['l2d_hwprf_reps'], 4), _rng(by['F2']['all5-dense']['hwprf_reps'], 4)),
    ]))
    out.append(S.hyp(
        'The span time of a CME chain load from OCM is the time of a core chain load from OCM plus the time of '
        'one step of the round-trip baseline. The difference of %s is %s %s the round-trip baseline of %s.' % (
            V.ns(pe['f2_span_minus_core']), V.ns(abs(D.rt_span_ns - pe['f2_span_minus_core'])),
            'below' if pe['f2_span_minus_core'] < D.rt_span_ns else 'above', V.ns(D.rt_span_ns)),
        'Core OCM rows on a boot with the prefetchers off would give both rows on one boot and under the same '
        'prefetcher setting. A calibration of the non-memory time that the chain kernel and the baseline kernel '
        'share is needed as well. The two together would confirm or reject it.'))
    out.append(S.insufficient(
        'A core chain load from one OCM region with 0 prefetch refills per load is not measured. Boot F2 ran no core row. '
        'The core latency commands on OCM, run on a boot with the prefetchers off, would give it.'))

    # =================================================================== 7. bandwidth
    out.append(S.h3('ocm-bw', 'OCM bandwidth'))
    cbw = {r['name']: r for r in D.ocm_bw_core}
    below = all(bwp[n]['f2_all_below_f1'] for n in rd_names + ['all5'])
    out.append(S.bullets([
        'The CME reads one OCM region at %s on %s and at %s on %s. The core reads at %s on boot F1.' % (
            _rng([bw['F1'][n]['best'] for n in rd_names], 1, 'GB/s'), F1N,
            _rng([bw['F2'][n]['best'] for n in rd_names], 1, 'GB/s'), F2N,
            _rng([cbw[n]['best'] for n in rd_names], 1, 'GB/s')),
        'The CME writes all five regions at %s (boot F1) and %s (boot F2). The core writes at %s.' % (
            V.gbps(bw['F1']['write']['best']), V.gbps(bw['F2']['write']['best']), V.gbps(cbw['write']['best'])),
    ]))
    ser_names = ['CME, ' + F2N, 'CME, ' + F1N, 'core (CPU 2), boot F1']

    def bw_row(n, label, sub, kind):
        rr = [bw['F2'][n], bw['F1'][n], cbw[n]]
        p = bwp[n]
        notes = ['(%s x boot F1, reps %s)' % (_n(p['f2_over_f1'], 2), _rng(rr[0]['reps_gbps'], 1)),
                 '(%s x core, reps %s)' % (_n(p['f1_over_core'], 2), _rng(rr[1]['reps_gbps'], 1)),
                 '(reps %s)' % _rng(rr[2]['reps_gbps'], 1)]
        tips = ['%s, %s\n%s\nbest rep: %s\nall reps: %s GB/s' % (
            kind, label, nm, V.gbps(r_['best']), ', '.join(_n(v, 3) for v in r_['reps_gbps']))
            for nm, r_ in zip(ser_names, rr)]
        return dict(label=label, sub=sub, values=[r_['best'] for r_ in rr], notes=notes, tips=tips)
    hrows = [dict(header='Read, one region (%d KiB), one pass after a flush of every line' % region_kib)]
    for n in rd_names:
        hrows.append(bw_row(n, 'region %d' % bw['F2'][n]['region'], _steps_word(by['F2'][n]['steps']), 'read'))
    hrows.append(dict(header='Read, all five regions (%s)' % _data.fmt_size(bw['F2']['all5']['size'])))
    hrows.append(bw_row('all5', 'all five regions', '%d kernel calls per pass' % bw['F2']['all5']['calls_per_pass'], 'read'))
    hrows.append(dict(header='Write, all five regions, %d passes per rep' % bw['F2']['write']['passes']))
    hrows.append(bw_row('write', 'all five regions', '%d kernel calls per rep' % bw['F2']['write']['calls_per_rep'], 'write'))
    f2_f1 = [bwp[n]['f2_over_f1'] for n in rd_names + ['all5']]
    out.append(S.fig(
        V.hbar(hrows, series=[(ser_names[0], 'f2'), (ser_names[1], 'f1'), (ser_names[2], 'core')],
               unit='GB/s', fmt=lambda v: _n(v, 1), xlabel='rate, bracket time, GB/s (GB = 1e9 bytes)', label_w=250),
        'Read and write rate on OCM, best rep, bracket time. Rows: the read of each region, the read of all five '
        'regions and the write of all five regions. The text in brackets after each value gives the ratio of the '
        'best reps (boot F2 over boot F1, boot F1 over the core) and the lowest to highest rep of the bar in GB/s. CME files '
        '%s to %s, %s and %s of both boots %s %s. Core files %s.' % (
            _code(bw['F1']['region0']['src']), _code(bw['F1']['region4']['src']), _code(bw['F1']['all5']['src']),
            _code(bw['F1']['write']['src']), R['bwF1'], R['bwF2'], R['corebw']),
        'On boot F1 the CME reads one OCM region %s times as fast as the core. The boot F2 read rate is %s times '
        'the boot F1 rate. The reps of one bar differ by up to %s.' % (
            _rng([bwp[n]['f1_over_core'] for n in rd_names], 2), _rng(f2_f1, 2),
            V.pct(max(bw[b][n]['spread_pct'] for b in _data.BOOTS for n in rd_names + ['all5', 'write']), 1))))
    trows = []
    for n in rd_names + ['all5', 'write']:
        p = bwp[n]
        trows.append([bw['F1'][n]['row_label'], _n(p['f2']), _n(p['f2_span']), _n(bw['F2'][n]['spread_pct'], 2),
                      _n(p['f1']), _n(p['f1_span']), _n(bw['F1'][n]['spread_pct'], 2), _n(p['core']),
                      V.ratio(p['f1_over_core']), V.ratio(p['f2_over_f1'])])
    out.append(_tab(S, 
        ['Row', 'CME,|boot F2,|bracket,|GB/s', 'CME,|boot F2,|span,|GB/s', 'CME,|boot F2,|spread,|%',
         'CME,|boot F1,|bracket,|GB/s', 'CME,|boot F1,|span,|GB/s', 'CME,|boot F1,|spread,|%',
         'Core,|boot F1,|GB/s', 'CME|boot F1|over|core', 'CME|boot F2|over CME|boot F1'],
        trows, caption='OCM bandwidth: best rep of %d reps %s %s %s.' % (bw['F1']['region0']['n_reps'], R['bwF2'], R['bwF1'], R['corebw']),
        note='"Bracket" and "span" are the rates from bracket time and from span time. Spread is over the reps, '
             'bracket rate. The rates are printed with the three decimals of the files. The spread column shows '
             'how far the reps of a row differ.'))
    rd_spread = [bw[b][n]['spread_pct'] for b in _data.BOOTS for n in rd_names]
    bw_near = [bw['F2']['region%d' % i]['best'] for i in near_regions]
    bw_far = [bw['F2']['region%d' % i]['best'] for i in far_regions]
    bw_step_order = min(bw_near) > max(bw_far)
    out.append(S.bullets([
        ('In all %d read rows every rep of boot F2 is slower than every rep of boot F1.' % (len(rd_names) + 1)) if below else
        'The rep ranges of the two boots overlap in at least one read row.',
        'The write rate is the same on both boots within %s.' % V.pct(abs(bwp['write']['f2_over_f1'] - 1) * 100, 1),
        ('The read rates of boot F2 are not ordered by mesh steps. %s read %s and %s read %s.' if not bw_step_order else
         'On boot F2 every region at the lower step count reads faster. %s read %s and %s read %s.') % (
            near_txt.capitalize(), _rng(bw_near, 1, 'GB/s'), far_txt, _rng(bw_far, 1, 'GB/s')),
        'Put as bracket time per %d bytes transferred, a one-region read is %s through the CME on boot F1, %s on '
        'boot F2 and %s on the core.' % (_data.LINE, _rng([bwp[n]['f1_ns_per_line'] for n in rd_names], 2, 'ns'),
                                         _rng([bwp[n]['f2_ns_per_line'] for n in rd_names], 2, 'ns'),
                                         _rng([bwp[n]['core_ns_per_line'] for n in rd_names], 2, 'ns')),
        'That value is the bracket time of the best pass divided by the %s lines of the region. It is a rate of '
        'the whole loop. It is not the time that one load instruction takes.' % _n(region_lines, 0),
        'One loop iteration of the CME read kernel loads %s bytes with four instructions and runs 16 EOR '
        'instructions %s.' % (_n(16 * _data.LINE, 0), R['kern']),
        'A read row has %d reps. Each rep is %d pass.' % (bw['F1']['region0']['n_reps'], bw['F1']['region0']['passes']),
        'The reps of a one-region row differ by %s. So the best value of a row is one single pass, and no other '
        'rep repeats it.' % _rng(rd_spread, 1, '%'),
    ]))
    out.append(S.insufficient(
        'The write rate of one OCM region is not measured. Each boot holds one write row, over all five regions '
        '(%s). The write command on one region would give it.' % _code(bw['F1']['write']['src'])))
    # per-kernel-call accounting (critic W5)
    out.append(S.p(
        '<b>Kernel calls per pass.</b> The bandwidth program calls the kernel once per region of the buffer %s. '
        'So a pass over all five regions is %d kernel calls. A write rep of %d passes is %d kernel calls. '
        'Table %d gives the outside-span time per kernel call.' % (
            R['bwc'], bw['F1']['all5']['calls_per_pass'], bw['F1']['write']['passes'], bw['F1']['write']['calls_per_rep'],
            S.next_table())))
    def pass_cell(r):
        # one kernel call per pass: the per-pass time is the per-call time
        if r['calls_per_pass'] == 1:
            return 'as per call'
        return _rng([r['outside_pass_lo'], r['outside_pass_hi']], 0)

    def res_ns(r):
        # the rate has three decimals, so the rebuilt bracket time of a rep is known to this many ns
        return max(x['bracket_ns'] * 0.0005 / x['gbps'] for x in r['reps'])
    trows = []
    for n in rd_names + ['all5', 'write']:
        r1, r2 = bw['F1'][n], bw['F2'][n]
        trows.append([r1['row_label'], '%d' % r1['calls_per_pass'], '%d' % r1['calls_per_rep'],
                      _n(r1['ns_per_pass'] / 1000.0, 2), _rng([r1['outside_lo'], r1['outside_hi']], 0), pass_cell(r1),
                      _n(r2['ns_per_pass'] / 1000.0, 2), _rng([r2['outside_lo'], r2['outside_hi']], 0), pass_cell(r2)])
    res_one = max(res_ns(bw[b][n]) for b in _data.BOOTS for n in rd_names)
    res_all = max(res_ns(bw[b]['all5']) for b in _data.BOOTS)
    res_wr = max(res_ns(bw[b]['write']) for b in _data.BOOTS)
    out.append(_tab(S, 
        ['Row', 'Kernel|calls|per pass', 'Kernel|calls|per rep', 'Boot F1:|bracket|per pass, us',
         'Boot F1:|outside-span|per call, ns', 'Boot F1:|outside-span|per pass, ns',
         'Boot F2:|bracket|per pass, us', 'Boot F2:|outside-span|per call, ns',
         'Boot F2:|outside-span|per pass, ns'],
        trows, caption='Time outside the span in the OCM bandwidth rows, lowest to highest over the reps %s %s.' % (
            R['bwF1'], R['bwF2']),
        note='"Per call" means per kernel call. Bracket time per pass is of the best rep. 1 us = 1,000 ns. '
             'Outside-span time = bracket time minus the %s column. The %s column of the files has steps of 1 us. '
             'So the bracket time of a rep is rebuilt as %s divided by %s. That rate has three decimals. The '
             'rebuilt bracket time of a rep is therefore known to %s ns (est.) for a one-region read, to %s ns '
             '(est.) for the all-five read and to %s ns (est.) for a write rep of %d passes. The table prints whole ns for that '
             'reason. "As per call": the row has one kernel call per pass.' % (
                 _code('span_s'), _code('elapsed_s'), _code('total_bytes'), _code('aggregate_GBps'),
                 _n(res_one, 1), _n(res_all, 1), _n(res_wr, 0), bw['F1']['write']['passes']),
        align='lrrrrrrrr'))
    one_out = [v for b in _data.BOOTS for n in rd_names for v in bw[b][n]['outside_reps']]
    first_out = [bw[b][n]['outside_reps'][0] for b in _data.BOOTS for n in rd_names]
    later_out = [v for b in _data.BOOTS for n in rd_names for v in bw[b][n]['outside_reps'][1:]]
    first_highest = all(bw[b][n]['outside_reps'][0] == max(bw[b][n]['outside_reps']) for b in _data.BOOTS for n in rd_names)
    share_hi = max(x['outside_ns_per_pass'] / x['bracket_ns_per_pass'] * 100
                   for b in _data.BOOTS for n in rd_names + ['all5', 'write'] for x in bw[b][n]['reps'])
    out.append(S.bullets([
        'A one-region read call spends %s outside its span.' % _rng(one_out, 0, 'ns'),
        ('The first rep is the highest in all %d one-region files (%s). The later reps read %s.' % (
            len(first_out), _rng(first_out, 0, 'ns'), _rng(later_out, 0, 'ns'))) if first_highest else
        'The first rep of a one-region file reads %s. The later reps read %s.' % (
            _rng(first_out, 0, 'ns'), _rng(later_out, 0, 'ns')),
        'Every rep follows a flush of the region. So the flush alone does not explain the higher first rep.',
        'A call of the all-five read spends %s outside its span. A call of the write spends %s.' % (
            _rng([v for b in _data.BOOTS for v in (bw[b]['all5']['outside_lo'], bw[b]['all5']['outside_hi'])], 0, 'ns'),
            _rng([v for b in _data.BOOTS for v in (bw[b]['write']['outside_lo'], bw[b]['write']['outside_hi'])], 0, 'ns')),
        'Within one rep the outside-span time is at most %s of the bracket time, in every row of both boots.' % V.pct(share_hi, 1),
    ]))
    out.append(S.insufficient(
        'Why the first rep of a one-region read spends more time outside its span is not known. The files hold no '
        'counter for the time outside the span. A run with one untimed kernel call before the first rep would '
        'show whether the first call of a command costs more.'))
    out.append(S.insufficient(
        'The bandwidth files hold no refill counters. So they cannot say what share of the lines of a boot F1 read '
        'came by prefetch. A CME bandwidth run with the refill events of the CME L1 counted would give it.'))
    out.append(S.insufficient(
        'These rows cannot be compared with the bandwidth rows on the DRAM model under equal conditions. An OCM '
        'read rep is one pass after a flush of every line. The rows on the DRAM model run several passes with no '
        'flush. Rows on the DRAM model with one pass after a flush, at %s and at %s, would give the comparison.' % (
            _data.fmt_size(bw['F1']['region0']['size']), _data.fmt_size(bw['F1']['all5']['size']))))

    # =================================================================== 8. mesh counters
    out.append(S.h3('ocm-mesh', 'Mesh counters: where the requests arrive'))
    S.term('Requests received', 'the mesh counter event <code>hns_pocq_reqs_recvd_all</code> of one home node: '
                                'the number of requests that the node received while the command ran.')
    eplo = min(r['excess_per_line'] for b in _data.BOOTS for r in one_mesh[b])
    ephi = max(r['excess_per_line'] for b in _data.BOOTS for r in one_mesh[b])
    ratio_lo = min(r['own_over_largest_other'] for b in _data.BOOTS for r in one_mesh[b])
    ratio_hi = max(r['own_over_largest_other'] for b in _data.BOOTS for r in one_mesh[b])
    out.append(S.bullets([
        'In %d of the %d one-region commands the home node with the most requests received is the node that holds '
        'the region of the command.%s' % (
            ms['intended_ok'], ms['intended_n'],
            ' So the requests of each command arrive mainly at its intended home node.'
            if ms['intended_ok'] == ms['intended_n'] else ''),
        'Every mesh count of this section is a total over the whole command. It is not a count of the timed passes.',
        'Over the whole command that node receives more requests than the mean count of the other four nodes. The '
        'difference, divided by the %s lines of the region, is %s requests per line.' % (
            _n(region_lines, 0), _rng([eplo, ephi], 1)),
        'That value is a total divided by a line count. It is not the number of requests that each line or each '
        'load causes.',
        'It receives %s times the count of the next node.' % _rng([ratio_lo, ratio_hi], 1),
    ]))
    panels = []
    groups = [('Latency test, one region per command', ['region %d' % i for i in range(n_regions)]),
              ('Bandwidth read, one region per command', ['region %d' % i for i in range(n_regions)])]
    for b in ('F2', 'F1'):
        vals, own, tips = [], [], []
        for prog in ('latency', 'bandwidth'):
            for r in sorted([x for x in one_mesh[b] if x['program'] == prog], key=lambda x: x['region']):
                vals.append([(c - r['other_mean']) / float(region_lines) for c in r['counts']])
                own.append(r['region'])
                tips.append(['%s, %s of region %d\nhome node %d (region %d): %s requests received\n'
                             'level subtracted: %s\nper line of the region, after the subtraction: %s' % (
                                 BOOTN[b], 'latency test' if prog == 'latency' else 'read', r['region'],
                                 _data.REGION_NODE[i], i, _n(c, 0), _n(r['other_mean'], 1),
                                 _n((c - r['other_mean']) / float(region_lines), 2))
                             for i, c in enumerate(r['counts'])])
        panels.append(dict(name=BOOTN[b], color=b.lower(), values=vals, own=own, tips=tips))
    out.append(S.fig(
        _matrix(panels, ['%d' % n for n in _data.REGION_NODE], groups, col_title='home node id (regions 0 to 4, left to right)',
                title='requests received per home node', fmt=lambda v: _n(0.0 if abs(v) < 0.005 else v, 2)),
        'Requests received per home node over the whole command, divided by the lines of the region (%s lines), '
        'after the mean count of the other four nodes is subtracted. Rows: the %d one-region CME commands of each '
        'boot. The outlined cell is the home '
        'node of the region of the command. File %s of each boot %s %s.' % (
            _n(region_lines, 0), len(one_mesh['F1']), _code('cmn-counts.csv'), R['cmnF2'], R['cmnF1']),
        ('In every row the intended home node has the highest value (%s requests per line of the region, whole '
         'command). ' % _rng([eplo, ephi], 1)
         if ms['intended_ok'] == ms['intended_n'] else
         'In %d of %d rows the intended home node has the highest value. ' % (ms['intended_ok'], ms['intended_n']))
        + 'Every other cell is within %s requests per line of zero.' % _n(
            max(abs(v) for p in panels for row, o in zip(p['values'], p['own']) for i, v in enumerate(row) if i != o), 2)))
    ctl = D.mesh_control['F1']
    ctl_labels = {}
    for b in _data.BOOTS:
        ctl_labels[b] = []
        for x in D.cmn(b):
            if x['label'].startswith('control') and x['label'] not in ctl_labels[b]:
                ctl_labels[b].append(x['label'])
    # a counted control has rows of the event that this section reads
    ctl_counted = [l for l in ctl_labels['F1'] if D.cmn('F1', label=l, event='hns_pocq_reqs_recvd_all')]
    d_ctl = [c - ctl['nodes'][nd] for r in one_mesh['F1'] for nd, c in r['nodes'].items() if nd != r['own_node']]
    exlo = min(r['excess'] for r in one_mesh['F1'])
    exhi = max(r['excess'] for r in one_mesh['F1'])
    out.append(S.bullets([
        '<b>Which control is subtracted.</b> The level subtracted in a row is the mean count of the four home nodes '
        'that do not hold the region, in the same command.',
        'An idle control is a mesh count of a small command that sends almost no requests to the home nodes. No '
        'idle control was taken with a CME command.',
        ('Boot F2 has no idle control in its mesh counter file.' if not ctl_labels['F2'] else
         'Boot F2 has %d idle control labels in its mesh counter file.' % len(ctl_labels['F2'])),
        'Boot F1 has %d counted idle controls, one per CPU (labels %s). This section uses the one of CPU 2 (%s), the '
        'CPU that runs the CME commands.' % (
            len(ctl_counted), ', '.join(_code(l) for l in ctl_counted), _code(ctl['label'])),
        'That idle control is the core latency program on a 4 KiB buffer in the DRAM model. It runs for %s ms %s.' % (
            _n(ctl['lifetime_ms'], 3), R['ctl']),
        'That idle control counts %s requests per node. The four other nodes of the boot F1 one-region commands count '
        '%s to %s more than it. The excess of the intended node is %s to %s requests.' % (
            _rng([ctl['lo'], ctl['hi']], 0), _n(min(d_ctl), 0), _n(max(d_ctl), 0), _n(exlo, 0), _n(exhi, 0)),
        'The counters run for the whole command lifetime. That covers the fill of the buffer, the build of the '
        'chains, the untimed walks, every flush and the timed passes.',
        'The counts cannot be limited to the timed loads.',
        'So the figure gives requests per line of the region, not per timed load. A latency command has %d timed '
        'loads, which is %s of its excess.' % (
            one_mesh['F1'][0]['timed'],
            _rng([r['timed'] / r['excess'] * 100 for b in _data.BOOTS for r in one_mesh[b] if r['program'] == 'latency'], 1, '%')),
        'For the timed passes the files hold the CME counters only. Every pass on boot F2 counts %s outer refills '
        'per load (Table %d).' % (_rng([v for r in f2rows for v in r['outer_reps']], 4), tab_refills),
    ]))
    tab_one_mesh = S.next_table()
    trows = []
    for b in ('F2', 'F1'):
        trows.append(BOOTC[b])
        for prog, pname in (('latency', 'latency test'), ('bandwidth', 'read')):
            for r in sorted([x for x in one_mesh[b] if x['program'] == prog], key=lambda x: x['region']):
                trows.append(['%s, region %d' % (pname, r['region']), '%d' % r['own_node'], _n(r['own'], 0),
                              '%s to %s' % (_n(r['other_lo'], 0), _n(r['other_hi'], 0)), _n(r['other_mean'], 1),
                              _n(r['excess'], 1), _n(r['excess_per_line'], 2), V.ratio(r['own_over_largest_other']),
                              _n(r['lifetime_ms'], 3)])
    out.append(_tab(S, 
        ['Command', 'Home node|of the|region', 'Requests|received by|that node', 'Other four|nodes, lowest|to highest',
         'Level subtracted|(mean of the|other four)', 'Excess', 'Excess|per line of|the region',
         'That node|over the|next node', 'Command|lifetime,|ms'],
        trows, caption='Requests received per home node, one-region CME commands, whole command %s %s.' % (
            R['cmnF2'], R['cmnF1']),
        note='Excess = requests received by the home node of the region minus the level subtracted. Command '
             'lifetime: the time from the start to the end of the command. The mesh counters run during that time.'))
    # rows that differ from the other rows of their group
    f1rd = sorted([x for x in one_mesh['F1'] if x['program'] == 'bandwidth'], key=lambda x: x['region'])
    f2rd = sorted([x for x in one_mesh['F2'] if x['program'] == 'bandwidth'], key=lambda x: x['region'])
    f2lat = sorted([x for x in one_mesh['F2'] if x['program'] == 'latency'], key=lambda x: x['lifetime_ms'])
    hi1 = max(f1rd, key=lambda x: x['excess_per_line'])
    rest1 = [x['excess_per_line'] for x in f1rd if x is not hi1]
    SLOW_GBPS = 29      # analysis choice, not a measured value: a rep below this rate is called slow
    slow_txt = []
    for b, rows_ in (('F2', f2rd), ('F1', f1rd)):
        bynum = {}
        for x in rows_:
            slow = [v for v in bw[b]['region%d' % x['region']]['reps_gbps'] if v < SLOW_GBPS]
            bynum.setdefault(len(slow), []).append((x, slow))
        parts = []
        for nslow in sorted(bynum, reverse=True):
            regs = ', '.join('%d' % x['region'] for x, _ in bynum[nslow])
            epl = _rng([x['excess_per_line'] for x, _ in bynum[nslow]], 2)
            word = 'region' if len(bynum[nslow]) == 1 else 'regions'
            if nslow:
                parts.append('%s %s: %d slow %s%s (%s) and %s requests per line.' % (
                    word.capitalize(), regs, nslow, 'rep' if nslow == 1 else 'reps',
                    ' each' if len(bynum[nslow]) > 1 else '',
                    _rng([v for _, sl in bynum[nslow] for v in sl], 1, 'GB/s'), epl))
            else:
                parts.append('%s %s: no slow rep and %s requests per line.' % (word.capitalize(), regs, epl))
        slow_txt.append('On %s:' % BOOTN[b])
        slow_txt.append(parts)
    out.append(S.bullets([
        'Some rows of Table %d differ from the other rows of their group. %s' % (
            tab_one_mesh, 'In all of them the intended node still has the highest count.'
            if ms['intended_ok'] == ms['intended_n'] else ''),
        'The values below are the excess of the whole command divided by the lines of the region.',
        ['The boot F1 read of region %d counts %s requests per line. The other four boot F1 reads count %s.' % (
            hi1['region'], _n(hi1['excess_per_line'], 2), _rng(rest1, 2)),
         'The boot F2 reads count %s requests per line for regions 0 to 4.' % (
             ', '.join(_n(x['excess_per_line'], 2) for x in f2rd)),
         'The boot F2 latency command of region %d runs for %s ms. The other four run for %s. The spread of its '
         'timed passes is %s.' % (
             f2lat[-1]['region'], _n(f2lat[-1]['lifetime_ms'], 3), _rng([x['lifetime_ms'] for x in f2lat[:-1]], 3, 'ms'),
             V.pct(by['F2']['region%d' % f2lat[-1]['region']]['spread_span_pct'], 2))],
        'The read rows with more requests per line are the rows with slow reps (Table %d). A slow rep is here a rep '
        'below %d GB/s.' % (S.next_table(), SLOW_GBPS),
    ] + slow_txt))
    trows = []
    for b in ('F2', 'F1'):
        trows.append(BOOTC[b])
        for x in (f2rd if b == 'F2' else f1rd):
            rr = bw[b]['region%d' % x['region']]
            trows.append(['read, region %d' % x['region'], ', '.join(_n(v, 3) for v in rr['reps_gbps']),
                          '%d' % len([v for v in rr['reps_gbps'] if v < SLOW_GBPS]), _n(x['excess_per_line'], 2)])
    out.append(_tab(S,
        ['Command', 'Rate of the %d reps,|GB/s' % bw['F1']['region0']['n_reps'], 'Reps below|%d GB/s' % SLOW_GBPS,
         'Excess|per line of|the region'],
        trows, caption='Rep rates of the one-region reads beside the requests received, whole command %s %s %s %s.' % (
            R['bwF2'], R['bwF1'], R['cmnF2'], R['cmnF1']),
        note='The limit of %d GB/s is a choice of this page. It lies between the two groups of rep rates.' % SLOW_GBPS,
        align='lrrr'))
    out.append(S.hyp(
        'The home node of the region receives more requests during a slow read rep than during a fast read rep.',
        'A mesh count around each timed rep would confirm or reject it.'))
    out.append(S.insufficient(
        'The cause of the extra requests in these rows is not known. The counters cover the whole command. A count '
        'around the timed passes only would show whether the extra requests belong to the timed passes.'))
    # all-five commands
    names5 = {'cme-ocm-all5-cpu2': 'latency test, ' + SHAPE_PAGE,
              'cme-ocm-all5-dense-cpu2': 'latency test, ' + SHAPE_ALL,
              'cme-ocm-read-all5': 'read',
              'cme-ocm-write-all5': 'write'}
    tab_five = S.next_table()
    trows = []
    for b in ('F2', 'F1'):
        trows.append(BOOTC[b])
        for r in D.mesh_requests[b]:
            if r['ocm'] and r['region'] is None:
                trows.append([names5[r['label']]] + [_n(c, 0) for c in r['counts']]
                             + [_n(r['baseline'], 1), _rng([r['net_per_line_lo'], r['net_per_line_hi']], 2),
                                '%d' % r['lowest_node']])
    tab_five_html = (_tab(S,
        ['Command'] + ['Node|%d' % n for n in _data.REGION_NODE]
        + ['Level|subtracted|per node', 'Net requests|per line of|a region, lowest|to highest node', 'Node|with the|lowest|count'],
        trows, caption='Requests received per home node, all-five CME commands, whole command %s %s.' % (R['cmnF2'], R['cmnF1']),
        note='An all-five command has no node without traffic. The level subtracted is the median, over the five '
             'one-region commands of the same program and boot, of the mean of their four other nodes.'))
    five = [(b, r) for b in ('F2', 'F1') for r in D.mesh_requests[b] if r['ocm'] and r['region'] is None]
    last_node = _data.REGION_NODE[-1]
    last_lowest = all(r['lowest_node'] == last_node for _, r in five)
    rel_last = [(r['nodes'][last_node] / (sum(r['counts']) / float(len(r['counts']))) - 1) * 100 for _, r in five]
    net_all = [v for _, r in five for v in (r['net_per_line_lo'], r['net_per_line_hi'])]
    srows = []
    for b in ('F2', 'F1'):
        srows.append(dict(header=BOOTC[b]))
        for bb, r in five:
            if bb != b:
                continue
            mean5 = sum(r['counts']) / float(len(r['counts']))
            rel = {nd: (c / mean5 - 1) * 100 for nd, c in r['nodes'].items()}
            others = [nd for nd in _data.REGION_NODE if nd != last_node]
            srows.append(dict(label=names5[r['label']], values=[[rel[last_node]], [rel[nd] for nd in others]],
                              names=[[last_node], others], counts=r['nodes'],
                              note='node %d: %s' % (last_node, V.signed(rel[last_node], 1, '%'))))

    def tip5(r, name, k, v):
        nd = r['names'][0][k] if name.startswith('home node %d' % last_node) else r['names'][1][k]
        return '%s\nhome node %d (region %d): %s requests received\n%s against the mean of the five nodes' % (
            r['label'], nd, list(_data.REGION_NODE).index(nd), _n(r['counts'][nd], 0), V.signed(v, 1, '%'))
    out.append(S.fig(
        _strip(srows, [('home node %d (region %d)' % (last_node, n_regions - 1), 'alt'),
                       ('home nodes %s' % ', '.join('%d' % nd for nd in _data.REGION_NODE[:-1]), 'ref')],
               unit='%', xlabel='requests received by a home node against the mean of the five nodes, %',
               fmt=lambda v: _n(v, 1), refs=[(0.0, 'mean of the five nodes')], tipfmt=tip5, label_w=270,
               title='requests received per home node in the all-five commands'),
        'Requests received by each home node in the all-five CME commands, as the difference from the mean of the '
        'five nodes of the same command, in percent. Rows: the %d all-five commands of each boot. One dot per home '
        'node. Whole command, no level subtracted. File %s of each boot %s %s.' % (
            len(five) // 2, _code('cmn-counts.csv'), R['cmnF2'], R['cmnF1']),
        ('Home node %d (region %d) has the lowest count in every all-five command. It is %s below the mean of the '
         'five nodes.' % (last_node, n_regions - 1, _rng([-v for v in rel_last], 1, '%'))) if last_lowest else
        'The node with the lowest count differs between the all-five commands.'))
    out.append(tab_five_html)
    out.append(S.bullets([
        'Over a whole all-five command every home node receives more requests than the level subtracted. The '
        'difference is %s requests per line of its region (Table %d).' % (_rng(net_all, 2), tab_five),
        'So no node counts as low as a node without traffic.',
        'Home node %d (region %d) has the lowest count in every all-five command of both boots.' % (
            last_node, n_regions - 1) if last_lowest else
        'The node with the lowest count differs between the all-five commands.',
    ]))
    out.append(S.insufficient(
        'Why one home node receives fewer requests than the other four in the all-five commands is not known. '
        'A count per home node around the timed passes only would show whether the timed passes cause it.'))

    # =================================================================== 9. prefetcher mesh traffic (G7)
    out.append(S.h3('ocm-prefetch-traffic', 'Mesh requests of the 8 MiB command, prefetchers on against off'))
    g = D.mesh_g7
    f1c = [r for r in D.chain['F1'] if r['kind'] == 'every line flushed first'][0]
    f2c = [r for r in D.chain['F2'] if r['kind'] == 'every line flushed first'][0]
    out.append(S.bullets([
        'During the latency command on an %s buffer in the DRAM model, with every line flushed first, the five '
        'home nodes receive %s requests per line of the buffer on %s and %s on %s.' % (
            _data.fmt_size(f1c['size']), _n(g['F1']['per_line'], 2), F1N, _n(g['F2']['per_line'], 2), F2N),
        'The five home nodes receive %s times as many requests on %s as on %s during the same command.' % (
            _n(g['f1_over_f2'], 2), F1N, F2N),
    ]))
    out.append(S.fig(
        V.hbar([dict(label='CME, ' + F2N, sub='command lifetime %s ms' % _n(g['F2']['lifetime_ms'], 3),
                     value=g['F2']['per_line'], color='f2'),
                dict(label='CME, ' + F1N, sub='command lifetime %s ms' % _n(g['F1']['lifetime_ms'], 3),
                     value=g['F1']['per_line'], color='f1',
                     note='(%s x boot F2, %s requests per line)' % (
                         _n(g['f1_over_f2'], 2), V.signed(g['F1']['per_line'] - g['F2']['per_line'], 2)))],
               unit='requests per line', fmt=lambda v: _n(v, 2),
               xlabel='requests received by the five home nodes, per line of the buffer', label_w=270),
        'Requests received by the five home nodes during the CME latency command on %s of the DRAM model with every '
        'line flushed first, divided by the %s lines of the buffer. Rows: one per boot. File %s, label %s %s %s.' % (
            _data.fmt_size(f1c['size']), _n(g['F1']['lines'], 0), _code('cmn-counts.csv'), _code(g['F1']['label']),
            R['g7F2'], R['g7F1']),
        'The five home nodes receive %s times as many requests on %s as on %s during the same command.' % (
            _n(g['f1_over_f2'], 2), F1N, F2N)))
    trows = []
    for b in ('F2', 'F1'):
        x = g[b]
        trows.append([BOOTC[b], _n(x['sum'], 0), _n(x['per_line'], 2),
                      '%s to %s' % (_n(x['node_lo'], 0), _n(x['node_hi'], 0)),
                      _n(x['lifetime_ms'], 3), _n(x['mc_reqs_local'], 0), _n(x['cache_miss'], 0)])
    out.append(_tab(S, 
        ['Boot', 'Requests|received,|five nodes', 'Per line|of the|buffer', 'Per node,|lowest to highest',
         'Command|lifetime,|ms', 'Event|<code>hns_mc_reqs_local_all</code>',
         'Event|<code>hns_cache_miss_all</code>'],
        trows, caption='Mesh counters of the 8 MiB CME latency command with every line flushed first, whole command %s %s.' % (
            R['g7F2'], R['g7F1']),
        note='The last two columns are two more events of the mesh counter file, counted over all home nodes '
             'together. The project file %s describes them %s. Event %s is the number of requests that all home '
             'nodes sent on to memory. Event %s is the miss count of the SLC (the cache in the home nodes) over all '
             'nodes. This page draws no conclusion from them.' % (
                 _code('README.md'), R['readme'], _code('hns_mc_reqs_local_all'), _code('hns_cache_miss_all'))))
    out.append(S.bullets([
        'This buffer is in the DRAM model, not in OCM.',
        'The requests are spread evenly over the five home nodes. The node counts differ by %s on boot F1 and by '
        '%s on boot F2.' % (V.pct(g['F1']['node_spread_pct'], 2), V.pct(g['F2']['node_spread_pct'], 2)),
        'The counts cover the fill of the buffer, the untimed walks and the flushes as well as the timed pass.',
        'So the value per line is the total of the command divided by the lines of the buffer. It is not the '
        'number of requests that each line or each load causes.',
        ('The boot F2 command runs for longer (%s ms against %s ms) and still receives fewer requests. So the time '
         'the counters run does not explain the difference.' if g['F2']['lifetime_ms'] > g['F1']['lifetime_ms'] else
         'The boot F2 command runs for %s ms and the boot F1 command for %s ms.') % (
            _n(g['F2']['lifetime_ms'], 3), _n(g['F1']['lifetime_ms'], 3)),
        'The timed row of the same command counts %s prefetch refills of the CME L1 per load on boot F1 and %s on '
        'boot F2 %s.' % (_n(f1c['hwprf'], 4), _n(f2c['hwprf'], 4), R['flat']),
    ]))
    out.append(S.hyp(
        'The %s more requests on boot F1 (%s per line) are requests of the hardware prefetchers.' % (
            _n(g['F1']['sum'] - g['F2']['sum'], 0), _n(g['F1']['per_line'] - g['F2']['per_line'], 2)),
        'Mesh counters that run around the timed pass only would confirm or reject it. A mesh event that counts '
        'prefetch requests apart from read requests would do the same.'))
    return ''.join(out)
