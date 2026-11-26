#!/usr/bin/env python3
"""Estimate the printed height of the two pages of the brief from its CSS and from real font metrics.

No browser is used. The script reads the HTML, measures every text run with the advance widths
(and the pair kerning) of the local IBM Plex Sans files, wraps the text like a browser does
(greedy, breaks at spaces, after a hyphen or a slash that a letter follows), lays out the two
kinds of table with the "automatic table layout" rule of CSS, and adds the heights with the
margin-collapsing rules of CSS 2.1.

Usage: page_estimate.py <brief.html> [width_factor] [mode]
  width_factor: multiplies every glyph width (1.0 = IBM Plex Sans as measured)
  mode: "standards" (line-height 1.35 everywhere) or "quirks-hhea" / "quirks-win"
        (no doctype: the browser resets line-height inside tables to "normal")
"""
import re, sys, html as htmllib
from html.parser import HTMLParser
from fontTools.ttLib import TTFont

FONTS = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/fonts'
PX_PER_MM = 96 / 25.4
PAGE_W = (210 - 2 * 12) * PX_PER_MM   # @page { size: A4; margin: 11mm 12mm }
PAGE_H = (297 - 2 * 11) * PX_PER_MM
LH = 1.35                              # body { font: 10.5px/1.35 ... }


class Face:
    def __init__(self, weight):
        self.f = TTFont(f'{FONTS}/IBMPlexSans-{weight}.ttf')
        self.upm = self.f['head'].unitsPerEm
        self.cmap = self.f.getBestCmap()
        self.hmtx = self.f['hmtx']
        self.kern = self._load_kern()
        self.missing = set()

    def _load_kern(self):
        """pair kerning (GPOS feature 'kern', PairPos formats 1 and 2) -> {(left, right): xAdvance}"""
        out = {}
        gpos = self.f['GPOS'].table
        idx = set()
        for fr in gpos.FeatureList.FeatureRecord:
            if fr.FeatureTag == 'kern':
                idx.update(fr.Feature.LookupListIndex)
        for i in sorted(idx):
            lk = gpos.LookupList.Lookup[i]
            for st in lk.SubTable:
                if st.LookupType == 9:
                    st = st.ExtSubTable
                if st.LookupType != 2:
                    continue
                cov = st.Coverage.glyphs
                if st.Format == 1:
                    for g1, ps in zip(cov, st.PairSet):
                        for pvr in ps.PairValueRecord:
                            v = pvr.Value1.XAdvance if pvr.Value1 and hasattr(pvr.Value1, 'XAdvance') else 0
                            if v:
                                out.setdefault((g1, pvr.SecondGlyph), v)
                elif st.Format == 2:
                    c1 = st.ClassDef1.classDefs
                    c2 = st.ClassDef2.classDefs
                    by2 = {}
                    for g, c in c2.items():
                        by2.setdefault(c, []).append(g)
                    for g1 in cov:
                        k1 = c1.get(g1, 0)
                        rec = st.Class1Record[k1].Class2Record
                        for k2, r in enumerate(rec):
                            v = r.Value1.XAdvance if r.Value1 and hasattr(r.Value1, 'XAdvance') else 0
                            if v and k2 in by2:
                                for g2 in by2[k2]:
                                    out.setdefault((g1, g2), v)
        return out

    def width(self, text, size, letter_spacing=0.0, factor=1.0):
        names = []
        for ch in text:
            g = self.cmap.get(ord(ch))
            if g is None:
                self.missing.add(ch)
                g = self.cmap[ord('n')]
            names.append(g)
        units = sum(self.hmtx[g][0] for g in names)
        units += sum(self.kern.get((a, b), 0) for a, b in zip(names, names[1:]))
        return units / self.upm * size * factor + letter_spacing * len(text)


FACE = {400: Face(400), 600: Face(600)}
FACTOR = 1.0


def tw(text, size, weight=400, ls=0.0):
    return FACE[weight].width(text, size, ls, FACTOR)


def chunks(text):
    """split a text into unbreakable chunks; a chunk ends with its trailing space (if any)"""
    text = ' '.join(text.split())
    out = []
    cur = ''
    for i, ch in enumerate(text):
        cur += ch
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if ch == ' ':
            out.append(cur); cur = ''
        elif ch == '-' and nxt.isalpha() and len(cur) > 1 and cur[-2].isalnum():
            out.append(cur); cur = ''
        elif ch == '/' and nxt.isalpha():
            out.append(cur); cur = ''
    if cur:
        out.append(cur)
    return out


def wrap(text, width, size, weight=400, ls=0.0):
    """greedy line breaking; returns the list of lines"""
    lines = []
    cur = ''
    for c in chunks(text):
        trial = cur + c
        if cur and tw(trial.rstrip(' '), size, weight, ls) > width + 0.01:
            lines.append(cur.rstrip(' ')); cur = c
        else:
            cur = trial
    if cur.strip():
        lines.append(cur.rstrip(' '))
    return lines or ['']


def min_content(text, size, weight=400, ls=0.0):
    return max(tw(c.rstrip(' '), size, weight, ls) for c in chunks(text))


def max_content(text, size, weight=400, ls=0.0):
    return tw(' '.join(text.split()), size, weight, ls)


# ---------------------------------------------------------------- parse the brief into blocks
class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []          # (kind, payload)
        self.stack = []
        self.buf = None
        self.table = None
        self.row = None
        self.cell = None
        self.ul = None
        self.in_svg = 0
        self.rowdiv = None        # flex row: list of items, each a list of blocks
        self.item = None
        self.in_style = False

    def emit(self, b):
        if self.item is not None:
            self.item.append(b)
        else:
            self.blocks.append(b)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get('class', '') or ''
        if tag == 'style':
            self.in_style = True
        if self.in_svg:
            if tag == 'svg':
                self.in_svg += 1
            return
        if tag == 'svg':
            vb = [float(x) for x in a['viewbox'].split()]   # html.parser gives attribute names in lower case
            self.emit(('svg', (vb[2], vb[3])))
            self.in_svg = 1
            return
        if tag in ('h1', 'h2', 'p'):
            self.buf = ''
            self.kind = (tag, cls)
        elif tag == 'table':
            self.table = []
        elif tag == 'tr':
            self.row = []
        elif tag in ('th', 'td'):
            self.cell = ''
            self.cellkind = tag
        elif tag == 'ul':
            self.ul = []
        elif tag == 'li':
            self.buf = ''
            self.kind = ('li', cls)
        elif tag == 'div':
            if cls == 'pb':
                self.emit(('pagebreak', None))
                self.stack.append('pb')
            elif cls == 'row':
                self.rowdiv = []
                self.stack.append('row')
            elif self.rowdiv is not None and self.item is None:
                self.item = []
                self.stack.append('item')
            else:
                self.stack.append('div')

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False
        if self.in_svg:
            if tag == 'svg':
                self.in_svg -= 1
            return
        if tag in ('h1', 'h2', 'p') and self.buf is not None:
            self.emit((self.kind[0] + ('.' + self.kind[1] if self.kind[1] else ''), self.buf))
            self.buf = None
        elif tag in ('th', 'td'):
            self.row.append((self.cellkind, self.cell)); self.cell = None
        elif tag == 'tr':
            self.table.append(self.row); self.row = None
        elif tag == 'table':
            self.emit(('table', self.table)); self.table = None
        elif tag == 'li':
            self.ul.append((self.kind[1], self.buf)); self.buf = None
        elif tag == 'ul':
            self.emit(('ul', self.ul)); self.ul = None
        elif tag == 'div':
            k = self.stack.pop()
            if k == 'item':
                self.rowdiv.append(self.item); self.item = None
            elif k == 'row':
                self.blocks.append(('row', self.rowdiv)); self.rowdiv = None

    def handle_data(self, d):
        if self.in_svg or self.in_style:
            return
        if self.cell is not None:
            self.cell += d
        elif self.buf is not None:
            self.buf += d


# ---------------------------------------------------------------- heights
def table_layout(rows, width, mode):
    """CSS automatic table layout: every column gets min + t * (max - min)."""
    ncol = len(rows[0])
    def style(kind):
        if kind == 'th':
            return dict(size=9.5, weight=600, ls=0.02 * 9.5, upper=True)
        return dict(size=10.0, weight=400, ls=0.0, upper=False)
    def text_of(kind, t):
        t = ' '.join(t.split())
        return t.upper() if style(kind)['upper'] else t
    mins = [0.0] * ncol; maxs = [0.0] * ncol
    for r in rows:
        for j, (kind, t) in enumerate(r):
            s = style(kind); t = text_of(kind, t)
            mins[j] = max(mins[j], min_content(t, s['size'], s['weight'], s['ls']) + 12)
            maxs[j] = max(maxs[j], max_content(t, s['size'], s['weight'], s['ls']) + 12)
    smin, smax = sum(mins), sum(maxs)
    if width >= smax:
        cols = [m + (width - smax) * m / smax for m in maxs]
    elif width <= smin:
        cols = mins[:]
    else:
        t = (width - smin) / (smax - smin)
        cols = [a + (b - a) * t for a, b in zip(mins, maxs)]
    # line height inside the table
    def lh(size):
        if mode == 'standards':
            return LH * size
        if mode == 'quirks-hhea':   # line-height: normal from hhea ascent + descent (1025 + 275) / 1000
            return 1.300 * size
        if mode == 'quirks-win':    # line-height: normal from OS/2 win metrics (1120 + 275) / 1000
            return 1.395 * size
        raise SystemExit('bad mode')
    total = 0.0; detail = []
    for r in rows:
        nl = []
        for j, (kind, t) in enumerate(r):
            s = style(kind); t = text_of(kind, t)
            nl.append((len(wrap(t, cols[j] - 12, s['size'], s['weight'], s['ls'])), lh(s['size'])))
        h = max(n * l for n, l in nl) + 4 + 1     # padding 2 + 2, bottom border 1
        total += h
        detail.append((h, [n for n, _ in nl]))
    return total, cols, detail, (smin, smax)


def lay(blocks, width, mode, verbose=True, indent=''):
    """returns the height of a block list; margins collapse between siblings (max of the two)"""
    y = 0.0
    prev_mb = None      # bottom margin of the previous block (None at the start of the page)
    rep = []
    for kind, payload in blocks:
        if kind == 'h1':
            mt, mb = 0, 2
            n = len(wrap(payload, width, 17, 600)); h = n * 17 * LH; info = f'{n} line(s)'
        elif kind.startswith('h2'):
            mt, mb = 10, 4
            n = len(wrap(payload, width, 12.5, 600)); h = 1 + 4 + n * 12.5 * LH; info = f'{n} line(s)'
        elif kind == 'p.sub':
            mt, mb = 0, 6
            ls = wrap(payload, width, 10.5, 400); n = len(ls); h = n * 10.5 * LH
            info = f'{n} line(s), last line {tw(ls[-1], 10.5):.0f} of {width:.0f} px'
        elif kind == 'p.cap':
            mt, mb = 2, 0
            ls = wrap(payload, width, 9.5, 400); n = len(ls); h = n * 9.5 * LH
            info = f'{n} line(s), last line {tw(ls[-1], 9.5):.0f} of {width:.0f} px'
        elif kind == 'table':
            mt, mb = 0, 0
            h, cols, detail, (smin, smax) = table_layout(payload, width, mode)
            info = 'rows ' + ', '.join(f'{d[0]:.1f} px {d[1]}' for d in detail) + \
                   f'; columns {[round(c, 1) for c in cols]}; sum of min {smin:.0f}, of max {smax:.0f}'
        elif kind == 'ul':
            mt, mb = 4 if False else 2, 4
            # ul margin 2 0 4, li margin 1 0; the margins of the first and the last li collapse with the ul's
            hs = []
            for cls, t in payload:
                wgt = 600 if cls == 'take' else 400
                ls = wrap(t, width - 18, 10.5, wgt)
                hs.append((len(ls), tw(ls[-1], 10.5, wgt)))
            h = sum(n for n, _ in hs) * 10.5 * LH + (len(hs) - 1) * 1
            info = 'lines per item ' + str([n for n, _ in hs]) + '; last-line widths ' + \
                   str([round(w) for _, w in hs]) + f' of {width - 18:.0f} px'
        elif kind == 'svg':
            mt, mb = 0, 0
            h = width * payload[1] / payload[0]; info = f'viewBox {payload[0]:.0f} x {payload[1]:.0f}'
        elif kind == 'row':
            mt, mb = 0, 0
            wi = (width - 12 * (len(payload) - 1)) / len(payload)
            hs = [lay(it, wi, mode, False)[0] for it in payload]
            h = max(hs); info = f'flex row, item width {wi:.1f} px, item heights {[round(x, 1) for x in hs]}'
        else:
            continue
        gap = mt if prev_mb is None else max(prev_mb, mt)
        y += gap + h
        rep.append((kind, gap, h, y, info))
        prev_mb = mb
    y += prev_mb or 0
    return y, rep


def main():
    global FACTOR
    path = sys.argv[1]
    FACTOR = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    mode = sys.argv[3] if len(sys.argv) > 3 else 'standards'
    quiet = len(sys.argv) > 4
    p = P(); p.feed(open(path, encoding='utf-8').read())
    pages = [[]]
    for b in p.blocks:
        if b[0] == 'pagebreak':
            pages.append([])
        else:
            pages[-1].append(b)
    res = []
    for i, pg in enumerate(pages, 1):
        h, rep = lay(pg, PAGE_W, mode)
        res.append(h)
        if not quiet:
            print(f'== page {i}: content {h:.1f} px = {h / PX_PER_MM:.1f} mm; page area {PAGE_H:.1f} px = {PAGE_H / PX_PER_MM:.0f} mm; '
                  f'free {PAGE_H - h:.1f} px = {(PAGE_H - h) / PX_PER_MM:.1f} mm')
            for kind, gap, hh, y, info in rep:
                print(f'   {kind:8s} gap {gap:4.1f}  height {hh:6.1f}  bottom at {y:7.1f}   {info}')
    miss = set().union(*(f.missing for f in FACE.values()))
    if miss and not quiet:
        print('glyphs not in the font (measured as "n"):', sorted(miss))
    if quiet:
        print(f'{path.split("/")[-1]:40s} factor {FACTOR:.2f} {mode:12s} ' +
              '  '.join(f'page {i}: {h:6.1f} px, free {PAGE_H - h:6.1f} px' for i, h in enumerate(res, 1)))


main()
