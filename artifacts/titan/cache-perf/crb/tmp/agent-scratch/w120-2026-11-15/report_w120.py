#!/usr/bin/env python3
"""report_w120.py [OUT.html] - build the report "why the whole-chip read rate fell with the new read kernel".

Source of every number: FINDINGS.md in this folder (the facts sheet).
Four groups of numbers are not copied from the facts sheet. They are recomputed from the raw files that it names:
  - LIF: estimated lines in flight per case (results/w120-R4-20261115T200016Z, T rows of *.m0.csv / *.m1.csv
    and the "nop,0," row of *.probe2.csv / *.probe66.csv): mean per-thread bytes/s / 64 * probe time.
  - LOAD: the 1-minute load average and the runnable-task count in env.txt and launches.txt of the w120-* folders.
  - the midpoints of the window ranges in Figure 1 (arithmetic on the facts-sheet ranges).
  - F5: the sums and per-thread ranges of the scrambled-order run (results/w120-R7-20261115T205946Z, T rows of
    <group>.m0.csv / <group>.m1.csv, thread rate = bytes / elapsed_s). They agree with the facts sheet to 0.1 GB/s.
The recomputed values agree with the facts sheet (the sheet was corrected on 2026-11-15: 7.6 lines in flight, four
variants at 26-32 lines, the load sentence).
In Figure 1, marks that would cover each other are moved sideways (see place() in fig1); the page states the largest move.
Python 3 standard library only. The page has no script, no external font and no external image.
The script prints every label overlap that it can compute, and exits with status 1 if there is one.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(
    os.path.join(HERE, '..', '..', '..', 'new-test-kernel', 'whole-chip-read-drop.html'))

# ---------------------------------------------------------------- palette (light theme only)
C1 = '#2a78d6'   # blue
C2 = '#eb6834'   # orange
C3 = '#1baf7a'   # aqua
INK = '#0b0b0b'
INK2 = '#52514e'
GRID = '#e4e3df'
SURF = '#fcfcfb'

# ---------------------------------------------------------------- data from the facts sheet
# F2 table: name, what the loop holds, window lo, hi (lines), total min, max (GB/s), n, state, class
# class: 'nop' = loads plus nop, 'add' = loads plus vector adds, 'load' = loads only
F2 = [
    ('read_1pl', '4 ldr q, one per line (256 B)', 156, 164, 230.2, 235.0, 16, 'slow', 'load'),
    ('read_sparse', '4 ldp + 9 nop (128 B)', 38, 42, 294.6, 301.5, 6, 'slow', 'nop'),
    ('asmread (= new C read)', '8 ldp q (256 B)', 36, 40, 288.5, 309.8, 22, 'slow', 'load'),
    ('read_pf2048', '8 ldp + 4 prfm 2048 B ahead', 36, 40, 290.5, 306.8, 11, 'slow', 'load'),
    ('read_nop32', '8 ldp + 32 nop', 36, 40, 284.8, 302.7, 4, 'slow', 'nop'),
    ('read_nop48', '8 ldp + 48 nop', 32, 36, 305.4, 307.2, 2, 'slow', 'nop'),
    ('read_dadd2', '8 ldp + 2 vector adds', 32, 36, 290.1, 296.4, 2, 'slow', 'add'),
    ('read_sp24', '4 ldp + 24 nop (128 B)', 32, 34, 280.9, 283.2, 2, 'slow', 'nop'),
    ('read_nop56', '8 ldp + 56 nop', 28, 32, 308.6, 309.1, 2, 'slow', 'nop'),
    ('read_dadd4', '8 ldp + 4 vector adds', 28, 32, 280.1, 283.2, 2, 'slow', 'add'),
    ('read_nop64', '8 ldp + 64 nop', 28, 32, 325.5, 333.9, 13, 'between', 'nop'),
    ('read_sp32', '4 ldp + 32 nop (128 B)', 26, 30, 366.3, 366.6, 2, 'between', 'nop'),
    ('read_nop72', '8 ldp + 72 nop', 24, 28, 459.0, 459.3, 2, 'fast', 'nop'),
    ('read_dadd8', '8 ldp + 8 vector adds', 24, 28, 462.4, 462.6, 2, 'fast', 'add'),
    ('read_1pl_nop96', '4 ldr q + 96 nop', 24, 28, 460.8, 460.9, 2, 'fast', 'nop'),
    ('read_nop80', '8 ldp + 80 nop', 24, 28, 459.7, 459.8, 2, 'fast', 'nop'),
    ('read_sp40', '4 ldp + 40 nop (128 B)', 22, 24, 466.8, 466.9, 2, 'fast', 'nop'),
    ('read_nop88', '', 20, 24, 462.8, 462.9, 2, 'fast', 'nop'),
    ('read_nop96', '', 20, 24, 465.5, 470.6, 16, 'fast', 'nop'),
    ('read_sp48', '', 20, 22, 470.0, 470.1, 2, 'fast', 'nop'),
    ('oldread (old C read)', '4 ldp + 8 vector adds (128 B)', 18, 22, 465.5, 470.1, 22, 'fast', 'add'),
    ('read_sp56', '', 18, 20, 473.6, 473.7, 2, 'fast', 'nop'),
    ('read_dadd16', '8 ldp + 16 vector adds that use the loaded data', 16, 20, 466.7, 469.8, 5, 'fast', 'add'),
    ('read_iadd16', '8 ldp + 16 vector adds that do not use the loaded data', 16, 20, 469.2, 469.7, 2, 'fast', 'add'),
    ('read_nop112', '', 16, 20, 471.1, 471.2, 2, 'fast', 'nop'),
    ('read_nop128', '', 16, 20, 473.8, 476.4, 9, 'fast', 'nop'),
    ('read_nop160', '', 12, 16, 477.9, 478.2, 2, 'fast', 'nop'),
    ('read_nop192', '', 12, 16, 479.6, 479.8, 2, 'fast', 'nop'),
    ('read_nop256', '8 ldp + 256 nop', 8, 12, 543.9, 549.0, 9, 'fastest', 'nop'),
]
CLS = {'nop': (C1, 'circle', 'loads plus padding instructions (nop)'),
       'add': (C2, 'tri', 'loads plus vector adds'),
       'load': (C3, 'square', 'plain loads only')}

# F3: mesh 0 loop, mesh 1 loop, mesh 0 sum, mesh 1 sum, total (GB/s). Order: by the mesh 1 loop.
SHORT = {'asmread': 'load-only', 'read_nop96': 'nop96', 'read_nop256': 'nop256'}
F3 = [
    ('asmread', 'asmread', 175.7, 127.2, 302.9),
    ('read_nop96', 'asmread', 149.5, 154.3, 303.8),
    ('read_nop256', 'asmread', 137.3, 251.3, 388.6),
    ('asmread', 'read_nop96', 331.9, 116.2, 448.1),
    ('read_nop96', 'read_nop96', 318.9, 150.7, 469.5),
    ('read_nop256', 'read_nop96', 238.1, 254.2, 492.3),
    ('asmread', 'read_nop256', 349.8, 108.2, 457.9),
    ('read_nop96', 'read_nop256', 347.8, 123.5, 471.3),
    ('read_nop256', 'read_nop256', 327.4, 221.8, 549.1),
]
F3_REF = 348  # mesh 0 alone with asmread, GB/s

# F4: case label, mesh 0 loop, mesh 1 loop, lines in flight mesh 0, mesh 1 (est., LIF, recomputed), probe ns CPU 2, CPU 66
# LIF values recomputed from results/w120-R4-20261115T200016Z (see the module text): mean over the streaming threads.
F4 = [
    ('load-only (asmread)', 'load-only (asmread)', 8.380, 7.911, 203.1, 211.3),
    ('read_1pl', 'read_1pl', 6.454, 7.061, 219.2, 219.4),
    ('read_nop256', 'load-only (asmread)', 7.006, 16.621, 212.9, 223.5),
    ('load-only (asmread)', 'read_nop256', 25.323, 7.647, 297.1, 236.4),
    ('read_nop96', 'read_nop96', 23.737, 9.190, 286.5, 238.1),
    ('read_nop256', 'read_nop256', 19.197, 14.905, 238.0, 246.9),
    ('load-only (asmread)', None, 23.374, None, 278.0, 165.5),
]
SLOW_MAX = 9.2    # facts sheet: slow or squeezed meshes 6.5-9.2
FAST_MIN = 14.9   # facts sheet: fast meshes 14.9-25.3


# F5: scrambled-order run R7, recomputed from the raw files. One 10 s interval per cell.
# group: mesh 0 loop, mesh 1 loop, mesh 0 sum, mesh 1 sum (GB/s), per-thread min, max of mesh 0 and of mesh 1 (GB/s)
F5 = [
    ('rand_nop0', 'rand_nop0', 268.750, 220.835, 4.14854, 4.23725, 3.89397, 3.97673),
    ('rand_nop96', 'rand_nop96', 250.520, 222.941, 3.87058, 3.96486, 3.93126, 4.01952),
    ('rand_nop256', 'rand_nop256', 204.265, 178.257, 3.15792, 3.22448, 3.14721, 3.21170),
    ('rand_nop0', 'rand_nop256', 264.183, 158.116, 4.08435, 4.17789, 2.78908, 2.84760),
    ('rand_nop256', 'rand_nop0', 192.527, 230.039, 2.97477, 3.03843, 4.06382, 4.14166),
    ('rand_nop0', 'read_nop256', 182.803, 278.791, 2.82650, 2.87686, 4.90710, 5.06743),
    ('read_nop256', 'rand_nop0', 307.240, 158.375, 4.72086, 4.92151, 2.79339, 2.84202),
    ('asmread', 'rand_nop256', 282.896, 134.190, 4.33704, 4.45893, 2.36720, 2.41819),
    ('rand_nop256', 'asmread', 127.489, 266.454, 1.95465, 2.00917, 4.60922, 4.80490),
    ('asmread', 'asmread', 166.274, 131.543, 2.57884, 2.61169, 2.33390, 2.35632),
    ('read_nop256', 'read_nop256', 328.531, 218.714, 5.03461, 5.21434, 3.85705, 3.92891),
    ('rand_nop0', None, 342.759, None, 5.29503, 5.40190, None, None),
    ('rand_nop256', None, 223.251, None, 3.44565, 3.53066, None, None),
]


def f5tot(a, b):
    """Total of the group (mesh 0 loop a, mesh 1 loop b) in GB/s, unrounded."""
    for q in F5:
        if q[0] == a and q[1] == b:
            return q[2] + (q[3] or 0.0)
    raise KeyError((a, b))


# Figure 4 rows: padding, window lo, hi (lines; the window of the sequential loop with the same loads and padding),
# sequential total lo, hi (GB/s), source of the sequential value, scrambled total (GB/s)
SEQ96 = [q for q in F2 if q[0] == 'read_nop96'][0]
FIG4 = [
    ('no padding', 36, 40, f5tot('asmread', 'asmread'), f5tot('asmread', 'asmread'), 'same run',
     f5tot('rand_nop0', 'rand_nop0')),
    ('96 nop', 20, 24, SEQ96[4], SEQ96[5], 'earlier runs, n = %d' % SEQ96[6], f5tot('rand_nop96', 'rand_nop96')),
    ('256 nop', 8, 12, f5tot('read_nop256', 'read_nop256'), f5tot('read_nop256', 'read_nop256'), 'same run',
     f5tot('rand_nop256', 'rand_nop256')),
]


def f1(v):
    """One decimal, one rounding of the unrounded value (7.647 -> 7.6)."""
    return '%.1f' % v


# ---------------------------------------------------------------- SVG helper with a label-overlap check
class Svg:
    def __init__(self, name, w, h, label):
        self.name, self.w, self.h = name, w, h
        self.out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
                    'role="img" aria-label="%s">' % (w, h, w, h, label),
                    '<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (w, h, SURF)]
        self.boxes = []   # (x0, y0, x1, y1, kind, text)

    def raw(self, s):
        self.out.append(s)

    def line(self, x1, y1, x2, y2, col=INK2, w=1, dash=None, op=1):
        self.out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s%s/>' % (
            x1, y1, x2, y2, col, w, ' stroke-dasharray="%s"' % dash if dash else '',
            ' stroke-opacity="%s"' % op if op != 1 else ''))

    def rect(self, x, y, w, h, fill, op=1, rx=0, title=None):
        t = '<title>%s</title>' % title if title else ''
        self.out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"%s%s>%s</rect>' % (
            x, y, w, h, fill, ' fill-opacity="%s"' % op if op != 1 else '', ' rx="%s"' % rx if rx else '', t))

    def text(self, x, y, s, size=12, anchor='start', col=INK, bold=False, halo=False, check=True):
        wd = 0.58 * size * len(s) * (1.06 if bold else 1.0)
        x0 = x if anchor == 'start' else (x - wd if anchor == 'end' else x - wd / 2)
        if check:
            self.boxes.append((x0, y - 0.80 * size, x0 + wd, y + 0.22 * size, 'text', s))
        self.out.append('<text x="%.1f" y="%.1f" font-size="%s" text-anchor="%s" fill="%s"%s%s>%s</text>' % (
            x, y, size, anchor, col, ' font-weight="600"' if bold else '',
            ' stroke="%s" stroke-width="3" paint-order="stroke" stroke-linejoin="round"' % SURF if halo else '',
            s.replace('&', '&amp;')))

    def mark(self, x, y, shape, col, title=None, r=5, check=True, tag=''):
        t = '<title>%s</title>' % title if title else ''
        a = 'fill="%s" stroke="%s" stroke-width="1.5"' % (col, SURF)
        if shape == 'circle':
            self.out.append('<circle cx="%.1f" cy="%.1f" r="%s" %s>%s</circle>' % (x, y, r, a, t))
        elif shape == 'square':
            self.out.append('<rect x="%.1f" y="%.1f" width="%s" height="%s" %s>%s</rect>' % (
                x - r, y - r, 2 * r, 2 * r, a, t))
        else:
            self.out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" %s>%s</polygon>' % (
                x, y - r - 1, x - r - 1, y + r, x + r + 1, y + r, a, t))
        if check:
            self.boxes.append((x - r, y - r, x + r, y + r, 'mark', tag))

    def overlaps(self):
        """Pairs (text, text) and (text, mark) whose boxes intersect."""
        res = []
        for i, a in enumerate(self.boxes):
            for b in self.boxes[i + 1:]:
                if a[4] == 'mark' and b[4] == 'mark':
                    continue
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    res.append((self.name, a[4], a[5], b[4], b[5]))
        for b in self.boxes:
            if b[4] == 'text' and (b[0] < 0 or b[2] > self.w or b[1] < 0 or b[3] > self.h):
                res.append((self.name, 'text outside the figure', b[5], '', ''))
        return res

    def done(self):
        return '\n'.join(self.out) + '\n</svg>'


# ---------------------------------------------------------------- Figure 1
def fig1():
    s = Svg('Figure 1', 920, 480, 'Total read rate at 64+56 against the measured window depth of each loop variant')
    X0, X1, YT, YB = 64, 694, 30, 390
    PX0, PX1 = 744, 884

    def xm(v):
        return X0 + (X1 - X0) * v / 45.0

    def xs(v):
        return PX0 + (PX1 - PX0) * (v - 150) / 20.0

    def yy(v):
        return YB - (YB - YT) * v / 600.0

    # switch band
    s.rect(xm(28), YT, xm(32) - xm(28), YB - YT, '#8a8880', op=0.16)
    s.text(xm(30), 44, 'switch from fast to slow', 12, 'middle', INK, bold=True)
    s.text(xm(30), 58, '28–32 lines', 11, 'middle', INK2)
    # grid and y axis
    for v in range(0, 601, 100):
        s.line(X0, yy(v), X1, yy(v), GRID)
        s.line(PX0, yy(v), PX1, yy(v), GRID)
        s.text(X0 - 6, yy(v) + 4, str(v), 11, 'end', INK2)
    s.line(X0, YB, X1, YB, INK2)
    s.line(PX0, YB, PX1, YB, INK2)
    s.line(X0, YT, X0, YB, INK2)
    s.text(X0 - 40, 16, 'total read rate at 64+56, GB/s (axis starts at 0)', 12, 'start', INK2)
    for v in range(0, 46, 5):
        s.line(xm(v), YB, xm(v), YB + 4, INK2)
        s.text(xm(v), YB + 17, str(v), 11, 'middle', INK2)
    for v in (150, 160, 170):
        s.line(xs(v), YB, xs(v), YB + 4, INK2)
        s.text(xs(v), YB + 17, str(v), 11, 'middle', INK2)
    # axis break
    for dx in (0, 8):
        s.line(710 + dx, YB + 7, 718 + dx, YB - 7, INK2, 1.5)
    s.text(719, YB - 14, 'axis break', 10, 'middle', INK2)
    s.text((X0 + X1) / 2, YB + 38,
           'measured window depth, cache lines (mark = middle of the measured range, thin bar = the range)',
           12, 'middle', INK2)
    # points
    named = {}
    LAB = ('oldread', 'asmread', 'read_nop72', 'read_nop256', 'read_iadd16', 'read_1pl')
    # Several variants have the same window range and nearly the same total. Their marks would cover each other.
    # place(): a mark keeps its y. It moves sideways by the smallest step that leaves SEP px to every placed mark.
    # The six labelled variants are placed first, so they stay at their true x.
    SEP, STEP = 6.0, 3.0
    placed = []

    def place(mx, my):
        for k in range(0, 13):
            for dx in ((0,) if k == 0 else (-k * STEP, k * STEP)):
                if all(abs(mx + dx - px) >= SEP or abs(my - py) >= SEP for px, py in placed):
                    placed.append((mx + dx, my))
                    return dx
        raise SystemExit('Figure 1: no free place for a mark')

    s.maxdx = 0.0
    s.moved = 0
    for name, holds, lo, hi, rmin, rmax, n, state, cls in sorted(
            F2, key=lambda q: (q[0].split(' ')[0] not in LAB, q[2] + q[3], q[4])):
        col, shape, _ = CLS[cls]
        fx = xs if lo > 100 else xm
        mx, my = fx((lo + hi) / 2.0), yy((rmin + rmax) / 2.0)
        dx = place(mx, my)
        key = name.split(' ')[0]
        assert key not in LAB or dx == 0
        s.maxdx = max(s.maxdx, abs(dx))
        s.moved += 1 if dx else 0
        s.line(fx(lo), my, fx(hi), my, col, 1.2, op=0.55)
        s.line(mx + dx, yy(rmin), mx + dx, yy(rmax), col, 2.5)
        named[key] = (mx + dx, my)
    s.px_per_line = (X1 - X0) / 45.0
    # the six labelled variants are drawn last, so that no other mark hides them
    for name, holds, lo, hi, rmin, rmax, n, state, cls in sorted(F2, key=lambda q: q[0].split(' ')[0] in LAB):
        col, shape, _ = CLS[cls]
        mx, my = named[name.split(' ')[0]]
        key = name.split(' ')[0]
        lab = key in LAB
        s.mark(mx, my, shape, col, r=4.5, check=True, tag=key,
               title='%s: window %d to %d lines, total %.1f to %.1f GB/s, n = %d intervals, %s' % (
                   name, lo, hi, rmin, rmax, n, state))

    def leader(x1, y1, key):
        x2, y2 = named[key]
        s.line(x1, y1, x2, y2, INK2, 0.8)

    # direct labels (six named variants)
    x, y = named['read_nop256']
    s.text(x + 12, y + 4, 'read_nop256: 543.9–549.0 GB/s', 12, 'start', INK, halo=True)
    leader(258, 84, 'read_iadd16')
    s.text(70, 84, 'read_iadd16: 469.2–469.7 GB/s', 12, 'start', INK, halo=True)
    leader(250, 142, 'oldread')
    s.text(70, 150, 'old read loop (oldread):', 12, 'start', INK, bold=True, halo=True)
    s.text(70, 165, '465.5–470.1 GB/s', 12, 'start', INK, halo=True)
    leader(516, 130, 'read_nop72')
    s.text(519, 134, 'read_nop72: 459.0–459.3', 12, 'start', INK, halo=True)
    x, y = named['asmread']
    s.line(x, 247, x, y + 6, INK2, 0.8)
    s.text(500, 260, 'new load-only loop (asmread):', 12, 'start', INK, bold=True, halo=True)
    s.text(500, 275, '288.5–309.8 GB/s', 12, 'start', INK, halo=True)
    x, y = named['read_1pl']
    s.text(x, y + 22, 'read_1pl', 12, 'middle', INK, halo=True)
    s.text(x, y + 37, '230.2–235.0 GB/s', 12, 'middle', INK, halo=True)
    # plain-language annotation
    s.text(70, 318, 'Measured range at or below 24–28 lines:', 12, 'start', INK2)
    s.text(70, 334, 'fast, 459 GB/s or more', 12, 'start', INK, bold=True)
    s.text(530, 318, 'Window of 32 lines or more:', 12, 'start', INK2)
    s.text(530, 334, 'slow, 280–310 GB/s', 12, 'start', INK, bold=True)
    s.text(530, 350, '(read_1pl: 230–235 GB/s)', 12, 'start', INK2)
    # legend
    lx = 64
    for cls in ('nop', 'add', 'load'):
        col, shape, txt = CLS[cls]
        s.mark(lx + 5, 456, shape, col, r=4.5, check=False)
        s.text(lx + 16, 460, txt, 12, 'start', INK2)
        lx += 16 + 0.58 * 12 * len(txt) + 22
    s.text(lx, 460, 'vertical bar = min to max', 12, 'start', INK2)
    return s


# ---------------------------------------------------------------- Figure 2
def fig2():
    s = Svg('Figure 2', 920, 440, 'Read rate of each mesh for nine pairs of loops')
    X0, X1, YT, YB = 96, 900, 46, 336
    gw = (X1 - X0) / 9.0

    def yy(v):
        return YB - (YB - YT) * v / 450.0

    for i, (a, b, m0, m1, tot) in enumerate(F3):
        if a == 'asmread' and b != 'asmread':
            s.rect(X0 + i * gw + 3, YT, gw - 6, YB - YT + 46, '#8a8880', op=0.13)
    for v in range(0, 451, 100):
        s.line(X0, yy(v), X1, yy(v), GRID)
        s.text(X0 - 6, yy(v) + 4, str(v), 11, 'end', INK2)
    s.text(X0 - 80, 16, 'sum of the read rate of one mesh, GB/s (axis starts at 0)', 12, 'start', INK2)
    s.line(X0, yy(F3_REF), X1, yy(F3_REF), INK, 1.2, dash='6 4')
    s.text(X0 + 4, 36, 'dashed line: mesh 0 alone with the load-only loop = %d GB/s' % F3_REF, 12, 'start', INK)
    s.line(X0 + 30, 40, X0 + 30, yy(F3_REF), INK2, 0.8)
    s.text(X0 - 6, YB + 20, 'mesh 0 loop', 11, 'end', INK2)
    s.text(X0 - 6, YB + 36, 'mesh 1 loop', 11, 'end', INK2)
    for i, (a, b, m0, m1, tot) in enumerate(F3):
        cx = X0 + (i + 0.5) * gw
        for k, (v, col, nm) in enumerate(((m0, C1, 'mesh 0'), (m1, C2, 'mesh 1'))):
            bx = cx - 33 + k * 34
            s.rect(bx, yy(v), 32, YB - yy(v), col, rx=3,
                   title='%s runs %s, %s runs %s: %s sum %.1f GB/s, total %.1f GB/s' % (
                       'mesh 0', a, 'mesh 1', b, nm, v, tot))
            s.rect(bx, YB - 4, 32, 4, col)
            s.text(bx + 16, yy(v) - 4, '%.1f' % v, 10.5, 'middle', INK, halo=True)
        s.text(cx, 66, 'total %.1f' % tot, 11, 'middle', INK, bold=True, halo=True)
        s.text(cx, YB + 20, SHORT[a], 11, 'middle', INK)
        s.text(cx, YB + 36, SHORT[b], 11, 'middle', INK)
    s.line(X0, YB, X1, YB, INK2)
    # legend and annotation
    s.rect(X0, 395, 12, 12, C1, rx=2)
    s.text(X0 + 18, 406, 'mesh 0 sum (64 threads)', 12, 'start', INK2)
    s.rect(X0 + 190, 395, 12, 12, C2, rx=2)
    s.text(X0 + 208, 406, 'mesh 1 sum (56 threads)', 12, 'start', INK2)
    s.text(X0, 428, 'Shaded groups: the load-only loop on mesh 0 reads as if it were alone. '
           'Mesh 1 is squeezed to 108–116 GB/s.', 12, 'start', INK, bold=True)
    return s


# ---------------------------------------------------------------- Figure 3
def fig3():
    rows = len(F4)
    RH, Y0 = 48, 78
    H = Y0 + rows * RH + 128
    s = Svg('Figure 3', 920, H, 'Estimated lines in flight per core for each case of the latency probe')
    X0, X1 = 330, 700

    def xx(v):
        return X0 + (X1 - X0) * v / 30.0

    yb = Y0 + rows * RH
    s.rect(xx(6.5), Y0 - 8, xx(SLOW_MAX) - xx(6.5), yb - Y0 + 8, C2, op=0.13)
    s.rect(xx(FAST_MIN), Y0 - 8, xx(25.3) - xx(FAST_MIN), yb - Y0 + 8, C1, op=0.11)
    s.text(xx(7.85), Y0 - 30, 'slow or squeezed meshes', 12, 'middle', INK, bold=True)
    s.text(xx(7.85), Y0 - 15, '6.5–9.2 lines (est.)', 11, 'middle', INK2)
    s.text(xx(20.1), Y0 - 30, 'fast meshes', 12, 'middle', INK, bold=True)
    s.text(xx(20.1), Y0 - 15, '14.9–25.3 lines (est.)', 11, 'middle', INK2)
    s.text(16, Y0 - 30, 'case', 12, 'start', INK, bold=True)
    s.text(16, Y0 - 15, 'loop on mesh 0 | loop on mesh 1', 11, 'start', INK2)
    s.text(716, Y0 - 30, 'time of one DRAM read', 12, 'start', INK, bold=True)
    s.text(716, Y0 - 15, 'by the probe, CPU 2 | CPU 66', 11, 'start', INK2)
    for v in range(0, 31, 5):
        s.line(xx(v), Y0 - 8, xx(v), yb, GRID)
        s.text(xx(v), yb + 16, str(v), 11, 'middle', INK2)
    s.line(X0, yb, X1, yb, INK2)
    s.text((X0 + X1) / 2, yb + 34, 'estimated lines in flight per streaming core (est.)', 12, 'middle', INK2)
    for i, (a, b, l0, l1, p2, p66) in enumerate(F4):
        yc = Y0 + i * RH + RH / 2 - 4
        if i:
            s.line(16, Y0 + i * RH - 6, 904, Y0 + i * RH - 6, GRID)
        s.text(16, yc - 3, 'mesh 0: ' + a, 12, 'start', INK)
        s.text(16, yc + 13, 'mesh 1: ' + (b if b else 'idle (no stream)'), 12, 'start', INK)
        s.text(716, yc + 5, '%.1f | %.1f ns' % (p2, p66), 12, 'start', INK)
        pts = [(l0, yc - 8, 'circle', 'mesh 0', a)]
        if l1 is not None:
            pts.append((l1, yc + 8, 'square', 'mesh 1', b))
            s.line(xx(l0), yc - 8, xx(l1), yc + 8, INK2, 1.5, op=0.6)
        for v, y, shape, nm, loop in pts:
            col = C2 if v <= SLOW_MAX + 0.05 else C1
            s.mark(xx(v), y, shape, col, r=5, tag='%s row %d' % (nm, i),
                   title='%s runs %s: %s lines in flight per core (est.)' % (nm, loop, f1(v)))
            # the label goes to the side that the connecting line does not cross
            other = [q[0] for q in pts if q[0] != v]
            if other and other[0] > v + 3:
                s.text(xx(v) - 9, y + 4, f1(v), 11, 'end', INK, halo=True)
            else:
                s.text(xx(v) + 9, y + 4, f1(v), 11, 'start', INK, halo=True)
    # legend and annotation
    ly = yb + 58
    s.mark(22, ly - 4, 'circle', INK2, r=5, check=False)
    s.text(33, ly, 'mesh 0', 12, 'start', INK2)
    s.mark(98, ly - 4, 'square', INK2, r=5, check=False)
    s.text(109, ly, 'mesh 1', 12, 'start', INK2)
    s.mark(178, ly - 4, 'circle', C2, r=5, check=False)
    s.text(189, ly, 'slow or squeezed', 12, 'start', INK2)
    s.mark(308, ly - 4, 'circle', C1, r=5, check=False)
    s.text(319, ly, 'fast', 12, 'start', INK2)
    s.text(16, ly + 24, 'A request is not slower in the slow state: 203–211 ns against 238–297 ns.',
           12.5, 'start', INK, bold=True)
    s.text(16, ly + 42, '203–211 ns: load-only loop on all cores (row 1). 238–297 ns: padded loops on all cores '
           '(rows 5 and 6),', 11.5, 'start', INK2)
    s.text(16, ly + 58, 'and mesh 0 with the load-only loop against read_nop256 (row 4). '
           'The other values are in the column at the right.', 11.5, 'start', INK2)
    return s


# ---------------------------------------------------------------- Figure 4
def sgn(v):
    """Signed value with one decimal and a real minus sign."""
    return ('+' if v >= 0 else '−') + '%.1f' % abs(v)


def fig4():
    RH, Y0 = 62, 84
    rows = len(FIG4)
    yb = Y0 + rows * RH
    s = Svg('Figure 4', 920, yb + 138,
            'Total read rate at 64+56 in sequential order and in scrambled order for three paddings')
    X0, X1 = 232, 692

    def xx(v):
        return X0 + (X1 - X0) * v / 600.0

    s.text(16, Y0 - 34, 'loop', 12, 'start', INK, bold=True)
    s.text(16, Y0 - 19, 'padding per 256 B | window depth', 11, 'start', INK2)
    s.text(716, Y0 - 34, 'scrambled minus sequential', 12, 'start', INK, bold=True)
    s.text(716, Y0 - 19, 'total, GB/s', 11, 'start', INK2)
    for v in range(0, 601, 100):
        s.line(xx(v), Y0 - 8, xx(v), yb, GRID)
        s.text(xx(v), yb + 16, str(v), 11, 'middle', INK2)
    s.line(X0, yb, X1, yb, INK2)
    s.text((X0 + X1) / 2, yb + 34, 'total read rate at 64+56, GB/s (axis starts at 0)', 12, 'middle', INK2)
    seq, scr = [], []
    for i, (pad, lo, hi, s0, s1, src, rnd) in enumerate(FIG4):
        yc = Y0 + i * RH + RH / 2 - 4
        seq.append((xx((s0 + s1) / 2.0), yc + 9))
        scr.append((xx(rnd), yc - 9))
    # the two curves: one line per order, through the three rows
    for pts, col in ((seq, C1), (scr, C2)):
        s.raw('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" stroke-opacity="0.55" '
              'stroke-linejoin="round"/>' % (' '.join('%.1f,%.1f' % q for q in pts), col))
    for i, (pad, lo, hi, s0, s1, src, rnd) in enumerate(FIG4):
        yc = Y0 + i * RH + RH / 2 - 4
        if i:
            s.line(16, Y0 + i * RH - 6, 904, Y0 + i * RH - 6, GRID)
        s.text(16, yc - 3, pad, 12, 'start', INK, bold=True)
        s.text(16, yc + 13, 'window %d–%d lines' % (lo, hi), 12, 'start', INK2)
        one = '%.1f' % s0 == '%.1f' % s1
        slab = '%.1f' % s0 if one else rng(s0, s1)
        (qx, qy), (rx, ry) = seq[i], scr[i]
        s.mark(qx, qy, 'circle', C1, r=5, tag='sequential row %d' % i,
               title='%s, sequential order: %s GB/s (%s)' % (pad, slab, src))
        s.mark(rx, ry, 'square', C2, r=5, tag='scrambled row %d' % i,
               title='%s, scrambled order: %.1f GB/s (one 10 s interval)' % (pad, rnd))
        # labels go to the outer side of each mark. In a row where the marks are close, both go to the right.
        near = abs(qx - rx) < 60
        if near or qx > rx:
            s.text(qx + 9, qy + 4, slab, 11, 'start', INK, halo=True)
        else:
            s.text(qx - 9, qy + 4, slab, 11, 'end', INK, halo=True)
        if near or rx > qx:
            s.text(rx + 9, ry + 4, '%.1f' % rnd, 11, 'start', INK, halo=True)
        else:
            s.text(rx - 9, ry + 4, '%.1f' % rnd, 11, 'end', INK, halo=True)
        s.text(716, yc + 5, sgn(rnd - s0) if one else '%s to %s' % (sgn(rnd - s1), sgn(rnd - s0)), 12, 'start', INK)
    ly = yb + 60
    s.mark(22, ly - 4, 'circle', C1, r=5, check=False)
    s.text(33, ly, 'sequential order (asmread, read_nop96, read_nop256)', 12, 'start', INK2)
    s.mark(420, ly - 4, 'square', C2, r=5, check=False)
    s.text(431, ly, 'scrambled order (rand_nop0, rand_nop96, rand_nop256)', 12, 'start', INK2)
    s.text(16, ly + 24, 'Less padding lowers the total in sequential order and raises it in scrambled order.', 12.5, 'start', INK, bold=True)
    s.text(16, ly + 42, 'Sequential order: the total rises from %.1f to %.1f GB/s when the window gets less deep.'
           % (FIG4[0][3], FIG4[2][3]), 11.5, 'start', INK2)
    s.text(16, ly + 58, 'Scrambled order: the total falls from %.1f to %.1f GB/s.' % (FIG4[0][6], FIG4[2][6]),
           11.5, 'start', INK2)
    return s


# ---------------------------------------------------------------- HTML
CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#fcfcfb;color:#0b0b0b;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:28px;line-height:1.25;margin:0 0 6px}
h2{font-size:21px;margin:40px 0 10px;padding-top:14px;border-top:1px solid #e4e3df}
h3{font-size:16px;margin:22px 0 6px}
p{margin:8px 0}
ul{margin:6px 0 10px;padding-left:22px}
li{margin:4px 0}
.sub{color:#52514e;font-size:14px;margin:0 0 18px}
.short{background:#f1f0ec;border-left:4px solid #2a78d6;padding:12px 16px;margin:14px 0}
.short p{margin:4px 0}
dl.words{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:4px 14px;margin:8px 0;font-size:15px}
dl.words dt{font-weight:600}
dl.words dd{margin:0}
@media (max-width:600px){dl.words{grid-template-columns:1fr;gap:0}dl.words dd{margin:0 0 8px}}
code{font-family:ui-monospace,"DejaVu Sans Mono",Menlo,Consolas,monospace;font-size:0.9em;background:#f1f0ec;padding:0 3px;border-radius:3px}
.tw{overflow-x:auto;margin:10px 0}
table{border-collapse:collapse;font-size:13.5px;line-height:1.35}
th,td{border-bottom:1px solid #e4e3df;padding:3px 9px;text-align:left;vertical-align:top}
th{background:#f1f0ec;font-weight:600}
td:first-child{min-width:150px}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
caption{caption-side:top;text-align:left;font-weight:600;padding:4px 0;font-size:14px}
figure{margin:16px 0}
.fig{overflow-x:auto;border:1px solid #e4e3df;border-radius:6px;background:#fcfcfb}
.fig svg{display:block;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
figcaption{font-size:14.5px;margin-top:6px}
figcaption b{font-weight:600}
.take{font-weight:600}
.ref{color:#52514e;font-size:0.85em;white-space:nowrap}
.note{color:#52514e;font-size:14px}
ol.refs{font-size:14px;padding-left:0;list-style:none}
ol.refs li{margin:5px 0;overflow-wrap:anywhere}
details{margin:8px 0}
summary{cursor:pointer;font-weight:600}
"""


def r(*n):
    return ' <span class="ref">' + ''.join('[Ref%d]' % i for i in n) + '</span>'


def table(caption, head, rows, num_from=1):
    h = ['<div class="tw"><table><caption>%s</caption><thead><tr>' % caption]
    for i, c in enumerate(head):
        h.append('<th%s>%s</th>' % (' class="n"' if i >= num_from else '', c))
    h.append('</tr></thead><tbody>')
    for row in rows:
        h.append('<tr>' + ''.join('<td%s>%s</td>' % (' class="n"' if i >= num_from else '', c)
                                  for i, c in enumerate(row)) + '</tr>')
    h.append('</tbody></table></div>')
    return ''.join(h)


def rng(a, b):
    return '%.1f–%.1f' % (a, b)


def build():
    g1, g2, g3, g4 = fig1(), fig2(), fig3(), fig4()
    P = []
    w = P.append
    w('<!DOCTYPE html>\n<html lang="en" data-theme="light">\n<head>\n<meta charset="utf-8">\n'
      '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
      '<meta name="color-scheme" content="light">\n'
      '<title>Whole-chip read drop</title>\n<style>%s</style>\n</head>\n<body>\n<main>\n' % CSS)
    w('<h1>Why the whole-chip read rate fell with the new test kernel</h1>')
    w('<p class="sub">CRB, 120 threads, DRAM-sized buffers. Measured on 2026-11-15, 16:56 to 21:03 UTC. '
      'A generator script builds this page' + r(19) + '. Its numbers come from the facts sheet' + r(1) + '.</p>')

    # ------------------------------------------------ short version
    w('<h2 id="short">Short version</h2><div class="short">')
    w('<p>With 120 threads only read really dropped (about 300 GB/s against about 468 GB/s, -36 %): copy did not '
      'drop, and most of the write drop comes from the stop rule of the benchmark.</p>')
    w('<p>The new read loop holds loads only, and the out-of-order window of a core (the instructions that it can '
      'start ahead) then covers 36 to 40 cache lines (64 B each) instead of 18 to 22 (one-thread test), and the '
      '120-thread total falls when the window covers more than about 30 lines.</p>')
    w('<p>Adding 72 or more do-nothing instructions per 256 B of data read restores 459 to 480 GB/s, and the drop '
      'did not appear when the same loads read the memory in one scrambled order instead of address order, and '
      'the exact rule inside the core is not established.</p></div>')

    # ------------------------------------------------ words
    w('<h2 id="words">Words used here</h2><dl class="words">')
    words = [
        ('CRB', 'The Arm server under test. It has 128 cores of type Neoverse V3AE. The tests use CPUs 0 to 119. The core clock is 2.8 GHz.'),
        ('kernel', 'One timed loop of the benchmark. It is not the Linux kernel. This page mostly says "loop".'),
        ('old read (<code>oldread</code>)', 'The read loop of the old benchmark, written in C. '
         'Per 128 B it holds 4 load-pair instructions and 8 vector adds.'),
        ('new read, asm read (<code>asmread</code>)', 'The read loops of the new benchmark. One is written in C '
         'and one in assembly. Both hold 8 load-pair instructions per 256 B and nothing else. '
         'This page calls them the load-only loop.'),
        ('nop', 'An instruction that does nothing. It still uses one place in the window.'),
        ('padded loop', 'The load-only loop with nop instructions added. <code>read_nop96</code> has 96 nop per '
         '256 B. <code>read_nop256</code> has 256 nop per 256 B.'),
        ('ldp, ldr, prfm', 'Arm instructions: load a pair of registers, load one register, prefetch.'),
        ('<code>read_1pl</code>', 'A loop with 4 single loads (ldr) per 256 B, one load per 64 B line, and nothing '
         'else. <code>read_1pl_nop96</code> is the same loop plus 96 nop.'),
        ('<code>read_daddN</code>, <code>read_iadd16</code>', 'The load-only loop plus N vector adds per 256 B. '
         'In <code>read_dadd16</code> the adds use the loaded data. '
         'In <code>read_iadd16</code> the 16 adds do not use the loaded data.'),
        ('<code>read_spN</code>, <code>read_sparse</code>', 'Loops with 4 load-pair instructions and N nop per 128 B. '
         '<code>read_sparse</code> has 9 nop.'),
        ('<code>read_pfN</code>', 'The load-only loop plus software prefetch instructions (prfm) that ask for the '
         'data N bytes ahead.'),
        ('sequential order, sequential stream', 'The loop reads its buffer from the lowest address to the highest. '
         'All loops of sections 1 to 5 do this.'),
        ('scrambled order', 'The loop reads the same bytes, but it does not follow the addresses. '
         'Each buffer is cut into chunks of 2 MiB. One chunk has 8192 blocks of 256 B. '
         'The loop visits every block of a chunk once, in an order that jumps between the blocks.'),
        ('<code>rand_nop0</code>, <code>rand_nop96</code>, <code>rand_nop256</code>', 'The scrambled-order loops. '
         'They hold 8 load-pair instructions per 256 B and 0, 96 or 256 nop. These are the loads and the padding of '
         '<code>asmread</code>, <code>read_nop96</code> and <code>read_nop256</code>.'),
        ('request limit', 'The largest number of memory requests that a core keeps outstanding at one time.'),
        ('DRAM', 'The main memory of the machine. It lies outside the caches of the chip.'),
        ('prefetcher', 'The part of a core that requests data before the loop asks for it. '
         'The hardware prefetcher does this without any instruction. '
         'A software prefetch is an instruction in the loop.'),
        ('streaming core', 'A core that runs a read loop over its buffer.'),
        ('latency probe, pointer chase', 'A test loop on one core. Each load gives the address of the next load, '
         'and each load misses the cache. The time of one step is about the time of one DRAM read.'),
        ('huge page', 'A memory page of 2 MiB. The normal page is 4 KiB.'),
        ('line', 'One cache line. It is 64 B.'),
        ('window (out-of-order window)', 'The instructions that a core holds between fetch and retirement. '
         'The core can start the loads of all instructions in the window before the first one finishes.'),
        ('window depth in lines', 'The number of 64 B lines that the loads inside one full window touch. '
         'It was measured for each loop with one thread on CPU 2. The result is a range, for example 36 to 40 lines.'),
        ('lines in flight', 'The lines that one core has requested from memory and has not yet received.'),
        ('mesh 0, mesh 1', 'The chip has two meshes (grids of links that connect cores, cache and memory ports). '
         'CPUs 0 to 63 are on mesh 0. CPUs 64 to 119 are on mesh 1.'),
        ('64+56', '64 threads on CPUs 0 to 63 and 56 threads on CPUs 64 to 119. Each thread has its own 256 MiB '
         'buffer. The data comes from DRAM. Other layouts use the same form, for example 64+0.'),
        ('gateway', 'The link that carries requests and data from one mesh to the other mesh.'),
        ('memory port', 'A port of the mesh that leads to a DRAM controller. The counters cover 24 ports.'),
        ('home node', 'A node of the mesh that receives the memory requests of the cores and passes them on.'),
        ('busy level', 'A value from 0 to 3 that a response message carries. A higher value says that the sender '
         'is more busy.'),
        ('flit', 'One unit of transfer on a mesh link. Two data flits carry one line.'),
        ('whole-pass stop', 'The stop rule of <code>bandwidth.c</code> (the benchmark). A thread stops only at the '
         'end of a whole pass over its buffer. The threads stop at different times.'),
        ('common stop', 'All threads stop at the same time.'),
        ('slow, between, fast, fastest', 'Names for the 120-thread read total. Slow is 280 to 310 GB/s '
         '(230 to 235 GB/s for <code>read_1pl</code>). Between is 325 to 367 GB/s. Fast is 459 to 480 GB/s. '
         'Fastest is 544 to 549 GB/s (<code>read_nop256</code>).'),
        ('squeezed', 'A mesh is squeezed when its threads read less because the other mesh runs a different loop.'),
        ('total', 'The sum of the rates of all threads.'),
        ('n', 'The number of timed intervals behind a value.'),
        ('GB', '1e9 bytes. MiB and KiB are powers of 2.'),
        ('est.', 'Estimate. The value is computed with an assumption. It is not measured directly.'),
    ]
    for t, d in words:
        w('<dt>%s</dt><dd>%s</dd>' % (t, d))
    w('</dl>')

    # ------------------------------------------------ (a)
    w('<h2 id="a">1. Only read really dropped</h2>')
    w('<ul>')
    w('<li>The original run used the whole-pass stop and 0.5 s per interval' + r(2) + '. '
      'Read fell there by more than one third. Write fell by a smaller amount. Copy did not fall.</li>')
    w('<li>Copy was measured again at 64+56 with a common stop and 6 s. All five copy loops gave 152.4 to '
      '153.6 GB/s' + r(3) + '.</li>')
    w('<li>Write was measured again at 64+56 with a common stop and 8 s. The old loop gave 126.1 to 126.8 GB/s. '
      'The new loops gave 120.2 to 129.3 GB/s' + r(3) + '. Padding does not change write.</li>')
    w('<li>The write drop depends on the stop rule. Earlier controlled runs compared old write and new C write under '
      'four timing rules' + r(4) + '. The old loop is 21.5 % higher with the whole-pass stop and 0.5 s. '
      'It is 3.1 % to 3.7 % higher with a common stop.</li>')
    w('<li>So most of the write drop in the original run comes from the whole-pass stop rule. '
      '3 to 4 % remains with a common stop.</li>')
    w('<li>The original file supports this. At equal pass count (296 passes) old write is 144.2 to 145.6 GB/s. '
      'New write is 143.6 GB/s and 147.8 GB/s' + r(2) + '.</li>')
    w('<li>Read is different. The drop stays with a common stop: 288.5 to 309.8 GB/s against 465.5 to 470.1 GB/s '
      '(section 2)' + r(6) + '.</li>')
    w('</ul>')
    w(table('Original run: total in GB/s, 120 threads, whole-pass stop, 0.5 s (n = 6 per loop)' + r(2),
            ['test', 'old C loop', 'new C loop', 'asm loop', 'result'],
            [['read', '464.4–466.7', '279.7–304.1', '271.1–305.9', 'drop'],
             ['write', '140.9–186.9 (median 144.6)', '123.5–147.8 (median 131.9)', 'not in the facts sheet',
              'smaller drop'],
             ['copy (read + written bytes)', '155.0–158.6', '153.9–162.4', 'not in the facts sheet', 'no drop']]))
    w(table('Controlled runs at 64+56 with a common stop: total in GB/s (n = 2 intervals per loop)' + r(3),
            ['test', 'interval', 'old loop', 'asm loop', 'new C loop', 'padded loops'],
            [['copy', '6 s', '152.7–153.0', '152.4–152.6', '152.7–153.4',
              'copy_nop96 153.2–153.6, copy_nop192 153.3–153.4'],
             ['write', '8 s', '126.1–126.8', '121.3–121.8', '121.4–129.3',
              'write_nop32, 96, 128, 256: 120.2–122.9']]))
    w(table('Old write against new C write under four timing rules: median total in GB/s '
            '(64 processes, 64 intervals per cell)' + r(4),
            ['stop rule', 'interval', 'old write', 'new C write', 'old above new'],
            [['whole-pass stop', '0.5 s', '144.1', '118.6', '+21.5 %'],
             ['whole-pass stop', '15 s', '131.3', '117.4', '+11.9 %'],
             ['common stop', '0.5 s', '126.4', '122.0', '+3.7 %'],
             ['common stop', '15 s', '126.6', '122.8', '+3.1 %']]))
    w('<ul><li>Writers on one mesh only (64+0) reach 455 GB/s with <code>oldwrite</code>, <code>asmwrite</code>, '
      '<code>write_nop128</code> and <code>write_nop256</code>' + r(3) + '.</li>'
      '<li>Writers at 32+32 reach 204 to 209 GB/s' + r(3) + '.</li>'
      '<li>So the write total falls from 455 GB/s (64+0) to 120 to 129 GB/s (64+56) when writers run on both '
      'meshes. The fall is the same for old and new loops. It is not explained here.</li></ul>')

    # ------------------------------------------------ (b)
    w('<h2 id="b">2. The read rate follows the window depth</h2>')
    w('<ul>')
    w('<li>A window test with one thread on CPU 2 measured how much one core holds in its window' + r(5) + '. '
      'The window holds 684 nop, or 159 vector-register writes, or 191 integer adds.</li>')
    w('<li>The same test measured the window depth of each loop in lines. One loop body was the unit. '
      'The result is a range: the last count that fits, to the first count that does not fit' + r(5) + '.</li>')
    w('<li>29 loop variants were then run at 64+56. Figure 1 shows the total of each variant against its window '
      'depth' + r(6) + '.</li>')
    w('<li>Every variant with a window of 32 lines or more is slow: 280 to 310 GB/s. '
      '<code>read_1pl</code> covers about 160 lines and gives 230 to 235 GB/s.</li>')
    w('<li>Every variant whose measured range is at or below 24 to 28 lines is fast: 459 to 480 GB/s. '
      '<code>read_nop256</code> covers 8 to 12 lines and gives 543.9 to 549.0 GB/s.</li>')
    w('<li>The four variants whose measured range lies inside 26 to 32 lines are slow or between '
      '(<code>read_nop56</code>, <code>read_dadd4</code>, <code>read_nop64</code>, <code>read_sp32</code>).</li>')
    w('</ul>')
    w('<figure><div class="fig">' + g1.done() + '</div><figcaption><b>Figure 1.</b> Total read rate at 64+56 '
      'against the measured window depth, one mark per loop variant (29 marks). The window depth comes from a '
      'test with one thread on CPU 2. %d marks would cover other marks. They are moved sideways by at most %.1f px '
      '(%.2f lines). The thin horizontal bar and the table below give the exact range. '
      'Hover over a mark for its values. ' % (g1.moved, g1.maxdx, g1.maxdx / g1.px_per_line) +
      '<span class="take">Takeaway: variants below the switch band give 459 GB/s or more, and variants above it give '
      '310 GB/s or less, for every kind of loop.</span></figcaption></figure>')
    w('<ul>')
    w('<li>The old read loop is fast because its 8 vector adds per 128 B occupy vector registers. '
      'The window holds 159 vector-register writes' + r(1, 5) + '.</li>')
    w('<li>The adds do not need to wait for data. <code>read_iadd16</code> has adds that do not use the loaded data. '
      '<code>read_dadd16</code> has adds that use it. The two totals overlap (469.2 to 469.7 GB/s and 466.7 to '
      '469.8 GB/s)' + r(6) + '.</li>')
    w('<li>Software prefetch does not restore the rate. <code>read_pf256</code> gives 289.1 to 300.1 GB/s (n = 4). '
      '<code>read_pf512</code> gives 302.3 to 303.9 GB/s (n = 2). <code>read_pf1024</code> gives 311.8 to '
      '315.8 GB/s (n = 2)' + r(6) + '.</li>')
    w('<li>The page size does not matter. With 4 KiB pages instead of 2 MiB pages (huge pages) the results are the same. '
      'The differences to the process with huge pages are -2.4 % to +0.2 % (one process per page size)' + r(7) + '.</li>')
    w('</ul>')
    w(table('Per-thread read rate in GB/s' + r(6),
            ['state', 'mesh 0 threads', 'mesh 1 threads'],
            [['slow', '2.5–2.75', '2.25–2.45'],
             ['fast (the 459–480 GB/s group)', '4.27–5.45', '2.51–2.78'],
             ['read_nop256', '4.99–5.22', '3.84–3.97']]))
    w('<details><summary>Exact numbers of Figure 1 (29 variants)</summary>')
    rows = []
    for name, holds, lo, hi, rmin, rmax, n, state, cls in F2:
        rows.append(['<code>%s</code>' % name.split(' ')[0] + (' ' + name.split(' ', 1)[1] if ' ' in name else ''),
                     holds if holds else '–', CLS[cls][2], '%d–%d' % (lo, hi), rng(rmin, rmax), str(n), state])
    w(table('Total at 64+56 in GB/s (min–max over all intervals) and window depth in lines (one-thread test). '
            '12 processes. 169 intervals in this table, 177 with the three variants <code>read_pf256</code>, '
            '<code>read_pf512</code> and <code>read_pf1024</code>. The ranges and n include the process with '
            '4 KiB pages (2 intervals for each of its 7 loops)' + r(5, 6, 7),
            ['loop', 'what the loop holds per iteration', 'colour class in Figure 1', 'window depth, lines',
             'total, GB/s', 'n', 'state'], rows, num_from=3))
    w('<p class="note">A dash means that the facts sheet does not list the content of that loop. '
      'The colour class is assigned in this report from the content of the loop.</p>')
    w(table('4 KiB pages: total at 64+56 in GB/s' + r(7),
            ['loop', 'total, GB/s'],
            [['oldread', '466.0–468.5'], ['asmread', '298.0–300.3'], ['read_nop64', '325.9–326.1'],
             ['read_nop96', '467.7–467.8'], ['read_nop256', '543.9–545.0'], ['read_1pl', '234.8–235.0'],
             ['read_pf2048', '297.6–302.5']]))
    w('</details>')

    # ------------------------------------------------ (c)
    w('<h2 id="c">3. The padded loop follows the old loop in every thread layout</h2>')
    w('<ul>')
    w('<li>Four loops were run in seven more thread layouts' + r(8) + '.</li>')
    w('<li>The padded loops follow the old read loop in every layout, within 2.3 %.</li>')
    w('<li>This includes 64+32. There the load-only loop is 8 % faster than the old loop, and the padded loops are '
      'not.</li>')
    w('<li>The drop exists only with many threads on both meshes. With one mesh only (64+0, 0+56) and at 32+32 '
      'all four loops agree within 1.6 %.</li>')
    w('</ul>')
    w(table('Total read rate in GB/s by thread layout (threads on mesh 0 + threads on mesh 1; '
            'one interval per cell)' + r(8),
            ['layout', 'oldread', 'asmread (load-only)', 'read_nop96', 'read_nop128'],
            [['56+56', '534.8', '300.1', '538.1', '547.1'],
             ['48+48', '412.1', '349.9', '414.4', '417.2'],
             ['64+44', '432.9', '356.3', '437.2', '435.0'],
             ['64+32', '412.2', '445.0', '417.8', '413.4'],
             ['64+0', '348.0', '348.4', '349.0', '351.0'],
             ['0+56', '318.0', '318.1', '319.2', '321.7'],
             ['32+32', '336.9', '336.5', '339.9', '341.9']]))

    # ------------------------------------------------ (d)
    w('<h2 id="d">4. With mixed loops, the deeper window takes the larger share</h2>')
    w('<ul>')
    w('<li>Two processes ran at the same time, one per mesh, for 12 s. Each process ran one loop. '
      'The two intervals overlapped by 98.8 % to 99.97 %' + r(9) + '.</li>')
    w('<li>The rate of a thread depends on the loop of the other threads.</li>')
    w('<li>Mesh 0 alone with the load-only loop reads 348 GB/s. With the load-only loop on mesh 0 and a padded loop '
      'on mesh 1, mesh 0 reads 331.9 to 349.8 GB/s. Mesh 1 is squeezed to 108 to 116 GB/s.</li>')
    w('<li>The reverse case also holds. With <code>read_nop256</code> on mesh 0 and the load-only loop on mesh 1, '
      'mesh 0 reads 137.3 GB/s and mesh 1 reads 251.3 GB/s.</li>')
    w('</ul>')
    w('<figure><div class="fig">' + g2.done() + '</div><figcaption><b>Figure 2.</b> Sum of the read rate of each '
      'mesh for nine pairs of loops. "load-only" is <code>asmread</code>, "nop96" is <code>read_nop96</code>, '
      '"nop256" is <code>read_nop256</code>. <span class="take">Takeaway for the question: the read rate of a mesh '
      'depends on the loop of the other mesh. The mesh with the deeper window takes the larger share, and the other '
      'mesh loses rate.</span></figcaption></figure>')
    w(table('Exact numbers of Figure 2: sum in GB/s' + r(9),
            ['mesh 0 loop', 'mesh 1 loop', 'mesh 0 sum', 'mesh 1 sum', 'total'],
            [[a, b, '%.1f' % m0, '%.1f' % m1, '%.1f' % t] for a, b, m0, m1, t in F3], num_from=2))
    w('<ul>')
    w('<li>The loops were also mixed inside both meshes: even CPUs ran the load-only loop and odd CPUs ran a '
      'padded loop' + r(9) + '.</li>')
    w('<li>With <code>read_nop256</code> on the odd CPUs, the load-only threads read 3.04 to 3.36 GB/s each. '
      'The <code>read_nop256</code> threads read 1.99 to 2.20 GB/s each. The total is 318.2 GB/s.</li>')
    w('<li>With <code>read_nop96</code> on the odd CPUs, the values are 2.63 to 3.08 GB/s against 2.06 to '
      '2.40 GB/s. The total is 306.3 GB/s.</li>')
    w('<li>In the same split, all <code>read_nop256</code> gives 548.3 GB/s and all <code>asmread</code> gives '
      '300.3 GB/s.</li>')
    w('</ul>')

    # ------------------------------------------------ (e)
    w('<h2 id="e">5. The slow state is not congestion</h2>')
    w('<h3>Latency probe and lines in flight</h3><ul>')
    w('<li>One core per mesh (CPU 2 and CPU 66) ran a latency probe (a pointer chase). Each step issues two '
      'independent loads that miss the cache at the same time. So the step time is about the time of one DRAM read. '
      'The other 118 cores ran a read loop' + r(10) + '.</li>')
    w('<li>On the idle machine one step takes 146.9 ns on both CPUs' + r(10) + '.</li>')
    w('<li>With the load-only loop on all cores (total 298 GB/s) one step takes 203.1 ns and 211.3 ns. '
      'With the padded loops on all cores one step takes 238.0 to 286.5 ns' + r(10) + '.</li>')
    w('<li>With the load-only loop on mesh 0 against <code>read_nop256</code> on mesh 1, one step takes 297.1 ns '
      'on mesh 0 (fast) and 236.4 ns on mesh 1 (squeezed). In the reverse case one step takes 212.9 ns on mesh 0 '
      '(squeezed) and 223.5 ns on mesh 1 (fast)' + r(10) + '.</li>')
    w('<li>So one memory request takes less time in the slow state than in the fast states: 203 to 211 ns against '
      '238 to 297 ns. The 297 ns is the fast mesh 0 of the mixed case.</li>')
    w('<li>Lines in flight per streaming core (est.) = lines per second per thread x probe time. '
      'The estimate assumes that a request of a streaming core takes as long as a request of the probe.</li>')
    w('<li>Slow or squeezed meshes have 6.5 to 9.2 lines in flight per core (est.). '
      'Fast meshes have 14.9 to 25.3 (est.).</li>')
    w('</ul>')
    w('<figure><div class="fig">' + g3.done() + '</div><figcaption><b>Figure 3.</b> Estimated lines in flight per '
      'streaming core (est.), one row per case of the latency probe. A streaming core is a core that runs a read loop. '
      'The column at the right is the time of one DRAM read by a test core, in ns. '
      '<span class="take">Takeaway for the question: the drop is not congestion. A slow or squeezed mesh keeps about '
      '8 lines (est.) in flight per core instead of about 20 (est.), although each request is served faster.'
      '</span></figcaption></figure>')
    rows = [['idle machine', '–', '–', '–', '146.9', '146.9']]
    for a, b, l0, l1, p2, p66 in F4:
        rows.append([a, b if b else 'idle (no stream)', f1(l0), f1(l1) if l1 is not None else '–',
                     '%.1f' % p2, '%.1f' % p66])
    w(table('Exact numbers of Figure 3: lines in flight per streaming core (est.) and probe time per step' + r(10),
            ['mesh 0 loop', 'mesh 1 loop', 'mesh 0, lines (est.)', 'mesh 1, lines (est.)',
             'CPU 2, ns', 'CPU 66, ns'], rows, num_from=2))
    w('<p class="note">The lines in flight per case were recomputed for this report from the raw files of the probe '
      'run' + r(10) + '. Each value is the mean over the streaming threads of one mesh. '
      'They agree with the ranges in the facts sheet' + r(1) + '.</p>')

    w('<h3>Mesh counters</h3><ul>')
    w('<li>Root counters of the mesh were read during 64+56 runs. No row was multiplexed '
      '(every counter ran for the whole interval)' + r(11) + '.</li>')
    w('<li>Per line read, the slow state has fewer retries, a lower queue occupancy and fewer stalls than the fast '
      'states. The exception is the north and south data links' + r(11) + '.</li>')
    w('<li>Each value in the table is a counter total divided by the number of 64 B lines read. '
      'A lower value means fewer retries or less waiting per line.</li>')
    w('<li><b>Insufficient data:</b> what one count of the queue-occupancy counter and of the busy-level counter '
      'stands for. The facts sheet does not say it. The counter description in the manual of the mesh would resolve '
      'it. The comparison between the states does not need it.</li>')
    w('</ul>')
    w(table('Mesh counters at 64+56: counter events per 64 B line read' + r(11),
            ['counter', 'slow: asmread, 299 GB/s', 'fast: read_nop96, 470 GB/s', 'fast: oldread, 468 GB/s'],
            [['home-node request retries (<code>hns_pocq_retry_all</code>)', '0.047', '0.072', '0.069'],
             ['home-node queue occupancy (<code>hns_qos_pocq_occupancy_all</code>)', '0.087', '0.121', '0.118'],
             ['memory-controller retries (<code>hns_mc_retries_local_all</code>)', '0.0046', '0.043', '0.039'],
             ['gateway data stalls (<code>ccra_chidat_stalls</code>)', '0.21', '0.73', '0.73'],
             ['home-node busy level 3 (<code>hns_cbusy11_all</code>)', '0.21', '1.49', '1.53'],
             ['request-link stalls east (<code>mxp_e_req_txflit_stall</code>)', '0.013', '0.167', '0.163'],
             ['data-link stalls east', '0.162', '0.344', '0.351'],
             ['data-link stalls north (exception)', '0.119', '0.069', '0.073'],
             ['data-link stalls south (exception)', '0.027', '0.020', '0.025']]))
    w('<h3>Memory ports</h3><ul>')
    w('<li>The 24 memory ports get one read request per line in the slow state and in the fast states' + r(12) + '.</li>')
    w('<li>They get almost no write data (0.0003 to 0.0004 per line). So DRAM does one read per line in both '
      'states. DRAM does no extra reads' + r(12) + '.</li>')
    w('</ul>')
    w(table('Memory-port counts per line read, 24 ports' + r(12),
            ['count', 'asmread 64+56 (307 GB/s)', 'read_nop96 (468 GB/s)', 'read_nop256 (550 GB/s)',
             'asmread 64+0 (349 GB/s)'],
            [['read requests into the ports', '1.004', '1.002', '1.076', '0.997'],
             ['request stalls', '0.0005', '0.018', '0.030', '0.000'],
             ['write data into the ports', '0.0004', '0.0003', '0.0003', '0.0003'],
             ['data flits out (2 flits = 1 line)', '1.992', '1.996', '1.995', '1.995']]))
    w('<h3>Data path, busy level and core counters</h3><ul>')
    w('<li>Per line, a core gets 0.50 + 0.50 flits from the two memory-port columns of its own mesh and 1.00 flit '
      'from the gateway row. This holds in every state: slow, fast, squeezed and alone' + r(13) + '.</li>')
    w('<li>So half of the lines arrive directly from the memory ports of the own mesh. '
      'The other half arrive through the gateway from the other mesh.</li>')
    w('<li>Response messages with busy level 0 are 82 to 93 % on slow or squeezed meshes. '
      'They are 4 to 26 % on fast meshes' + r(14) + '.</li>')
    w('<li>Three cases are in between. Mesh 1 under <code>read_nop96</code> or <code>oldread</code> at 64+56 has '
      '73 to 74 %. Mesh 1 with <code>asmread</code> against <code>read_nop256</code> on mesh 0 has 44 to 46 %'
      + r(14) + '.</li>')
    w('<li>So the squeezed cores do not receive a higher busy level than the fast cores.</li>')
    w('<li>Data that arrives through the gateway carries busy level 3 in 89 to 100 % of the flits. '
      'This holds in every state, also with the other mesh idle' + r(14) + '.</li>')
    w('<li>The core counters per line are the same in the slow and fast states. They are 2.08 bus accesses '
      '(transfers between the core and the mesh), 1.000 L2 refills (lines that arrive in the L2 cache, the second '
      'cache level of the core) and 1.000 L2 hardware-prefetch events (as counted by the core for its hardware '
      'prefetcher). The instruction counts are as coded' + r(1) + '.</li>')
    w('<li>Only the cycles per line differ: 66 to 77 in the slow state against 35 to 37 in the fast state on '
      'mesh 0. The core clock is 2.8 GHz in all runs' + r(1) + '.</li>')
    w('</ul>')

    # ------------------------------------------------ (r) scrambled order
    w('<h2 id="r">6. The drop needs a sequential stream</h2>')
    w('<h3>The scrambled-order loops</h3><ul>')
    w('<li>Three more loops were added to the benchmark program (<code>bwx13</code>, the runner): <code>rand_nop0</code>, <code>rand_nop96</code> and '
      '<code>rand_nop256</code>' + r(21) + '.</li>')
    w('<li>They read the same bytes as the load-only loop: 8 load-pair instructions per 256 B block, and every '
      'block once. They add 0, 96 or 256 nop per block.</li>')
    w('<li>So their loads and padding are those of the load-only loop (<code>asmread</code>), of '
      '<code>read_nop96</code> and of <code>read_nop256</code>.</li>')
    w('<li>The difference is the order. The 8192 blocks of each 2 MiB chunk are visited in a scrambled order. '
      'Visit number i reads block (i x (2i + 1)) mod 8192' + r(1) + '.</li>')
    w('<li>The intent was that the hardware prefetcher cannot follow the order from block to block. '
      'The one-thread counters below do not confirm an idle prefetcher.</li>')
    w('<li>The window depth in lines is taken from the sequential loop with the same loads and padding: '
      '36 to 40 lines, 20 to 24 lines and 8 to 12 lines. '
      'The scrambled loops have 5 more integer instructions per block' + r(1) + '. '
      'Their window depth was not measured separately.</li>')
    w('</ul>')
    w('<h3>One thread</h3><ul>')
    w('<li>One thread on CPU 2 read a 256 MiB buffer. This section uses two runs of 0.5 s per loop, both with '
      'the common stop: one for the rate, and one with the core counters switched on' + r(21) + '.</li>')
    w('<li>The load-only loop in sequential order read 35.7 GB/s. In scrambled order the loops read 10.8 GB/s '
      '(no padding), 8.4 GB/s (96 nop) and 4.8 GB/s (256 nop).</li>')
    w('<li>The core counters differ per line. The scrambled loops have 1.63 to 1.64 L2 refills per line against '
      '1.00 in sequential order. They have 0.41 to 0.42 loads per line that miss all caches against 0.00 to 0.06 '
      '(<code>read_nop256</code> has 0.00)' + r(1, 21) + '.</li>')
    w('<li>The scrambled loops show 1.84 to 1.91 L2 hardware-prefetch events per line against 1.00 in sequential '
      'order' + r(1, 21) + '. So the hardware prefetcher is not idle in scrambled order.</li>')
    w('<li>A second counter run of the same test used the whole-pass stop. Its scrambled loops show 1.44 to 1.51 '
      'L2 hardware-prefetch events per line and 0.58 to 0.60 loads per line that miss all caches'
      + r(1, 21) + '.</li>')
    w('<li>So with one thread the scrambled order is the slower one, and the loop has more cache '
      'misses.</li>')
    w('</ul>')
    w('<h3>120 threads at 64+56</h3><ul>')
    w('<li>Two processes ran at the same time, one per mesh, for 10 s. There is one interval per cell' + r(20) + '.</li>')
    w('<li>With the scrambled loops on both meshes the total is %s GB/s (no padding), %s GB/s (96 nop) and '
      '%s GB/s (256 nop).</li>' % (f1(f5tot('rand_nop0', 'rand_nop0')), f1(f5tot('rand_nop96', 'rand_nop96')),
                                   f1(f5tot('rand_nop256', 'rand_nop256'))))
    w('<li>Two sequential controls ran in the same run. The load-only loop gave %s GB/s. '
      '<code>read_nop256</code> gave %s GB/s. Both lie inside the ranges of section 2.</li>' % (
          f1(f5tot('asmread', 'asmread')), f1(f5tot('read_nop256', 'read_nop256'))))
    w('<li><code>read_nop96</code> in sequential order was not repeated in this run. '
      'Figure 4 uses its range from section 2: 465.5 to 470.6 GB/s (n = 16)' + r(6) + '.</li>')
    w('</ul>')
    w('<figure><div class="fig">' + g4.done() + '</div><figcaption><b>Figure 4.</b> Total read rate at 64+56 in '
      'sequential order and in scrambled order, for the same loads and the same padding. One row per padding. '
      'The window depth is that of the sequential loop. Each scrambled value and the sequential values of rows 1 '
      'and 3 are one 10 s interval of the same run. The sequential value of row 2 is the range of 16 intervals of '
      'earlier runs of the same evening, and its mark is the middle of that range. '
      '<span class="take">Takeaway: with the deepest window the scrambled order reads %s GB/s and the sequential '
      'order reads %s GB/s, so the deep window alone does not lower the total.</span> Hypothesis, not tested: part of the fall of the '
      'scrambled values to %s GB/s is the limit of one core with 256 nop (4.8 GB/s with one thread).'
      '</figcaption></figure>' % (
          f1(f5tot('rand_nop0', 'rand_nop0')), f1(f5tot('asmread', 'asmread')),
          f1(f5tot('rand_nop256', 'rand_nop256'))))
    rows = []
    for a, b, m0, m1, a0, a1, b0, b1 in F5:
        rows.append(['<code>%s</code>' % a, '<code>%s</code>' % b if b else 'idle (no stream)', f1(m0),
                     f1(m1) if b else '–', f1(m0 + (m1 or 0.0)), '%.2f–%.2f' % (a0, a1),
                     '%.2f–%.2f' % (b0, b1) if b else '–'])
    w(table('Scrambled-order run: sum in GB/s per mesh and per-thread range in GB/s. 13 groups, 24 processes, '
            'one 10 s interval per cell. 64 threads on mesh 0, 56 threads on mesh 1' + r(20),
            ['mesh 0 loop', 'mesh 1 loop', 'mesh 0 sum', 'mesh 1 sum', 'total', 'mesh 0, per thread',
             'mesh 1, per thread'], rows, num_from=2))
    w('<p class="note">The values of this table were recomputed for this report from the raw files of the run'
      + r(20) + '. They agree with the facts sheet to 0.1 GB/s' + r(1) + '. '
      'A total is the sum of the unrounded mesh sums. So it can differ by 0.1 GB/s from the sum of the two rounded '
      'values.</p>')
    w('<h3>Mixed pairs</h3><ul>')
    w('<li>In the four pairs of a sequential loop against a scrambled loop, the mesh with the sequential loop reads '
      'more (rows 6 to 9 of the table).</li>')
    w('<li>With <code>read_nop256</code> on the other mesh, <code>rand_nop0</code> reads %s GB/s on mesh 0 and '
      '%s GB/s on mesh 1. With <code>rand_nop0</code> on both meshes it reads %s GB/s and %s GB/s.</li>' % (
          f1(F5[5][2]), f1(F5[6][3]), f1(F5[0][2]), f1(F5[0][3])))
    w('<li>Mesh 0 alone reads %s GB/s with <code>rand_nop0</code> and %s GB/s with <code>rand_nop256</code>.</li>' % (
        f1(F5[11][2]), f1(F5[12][2])))
    w('</ul>')
    w('<h3>Reading</h3><ul>')
    w('<li>In scrambled order the deep window is the faster one: %s GB/s (no padding) is above %s GB/s (96 nop), '
      'and that is above %s GB/s (256 nop). In sequential order it is the reverse: %s GB/s is below 465.5 to '
      '470.6 GB/s, and that is below %s GB/s.</li>' % (
          f1(FIG4[0][6]), f1(FIG4[1][6]), f1(FIG4[2][6]), f1(FIG4[0][3]), f1(FIG4[2][3])))
    w('<li>Hypothesis: part of the fall to %s GB/s is the limit of one core with 256 nop. ' % f1(FIG4[2][6]) +
      '<code>rand_nop256</code> reads 4.8 GB/s with one thread' + r(21) + '. It reads 3.15 to 3.22 GB/s per thread '
      'with 120 threads' + r(20) + '. A run of <code>rand_nop256</code> with fewer threads per mesh would test '
      'this. That run was not done.</li>')
    w('<li>The same loads and padding (window depth assumed equal, not measured) read %s GB/s in scrambled order '
      'and %s GB/s in sequential order. So the deep window alone does not lower the total. In this run the drop '
      'appeared in sequential order. It did not appear in the one scrambled order tested.</li>' % (
          f1(FIG4[0][6]), f1(FIG4[0][3])))
    w('<li>So the drop depends on how the cores handle a sequential stream. The facts sheet reads this as: the rule is in the cores, not in the mesh, the gateways or '
      'DRAM' + r(1) + '. This narrows the open item of section 7. The exact rule inside the core is still not '
      'established.</li>')
    w('</ul>')
    w('<p class="note">Limits of this section: every cell is one interval of 10 s from one evening. No cell was '
      'repeated. Only one scrambled pattern was tested. The hardware prefetcher was not switched off. Its settings were not '
      'read. The one-thread counters show hardware-prefetch events in scrambled order too (1.84 to 1.91 per line), '
      'so the scrambled loops do not show the cores without prefetch. The window depth of the scrambled loops was '
      'not measured. The latency probe did not run with the '
      'scrambled loops, so their lines in flight are not known.</p>')

    # ------------------------------------------------ (f)
    w('<h2 id="f">7. What is established and what is not</h2>')
    w('<h3>Established</h3><ul>')
    w('<li>Read is the only real drop. Its size at 64+56 is about 300 GB/s against about 468 GB/s (-36 %) '
      '(sections 1 and 2)' + r(1) + '.</li>')
    w('<li>Cause in the benchmark (section 2)' + r(1) + ':<ul>'
      '<li>The load-only loop lets the window of a core cover 36 to 40 lines.</li>'
      '<li>The old loop covered 18 to 22 lines.</li>'
      '<li>Above about 30 lines the 120-thread total falls.</li>'
      '<li>Vector adds are not needed.</li></ul></li>')
    w('<li>Mechanism as far as measured (sections 4 and 5)' + r(1) + ':<ul>'
      '<li>Cores (or their prefetchers) whose loop covers more lines take a larger share.</li>'
      '<li>A whole mesh then runs with about 8 lines (est.) in flight per core instead of about 20 (est.).</li>'
      '<li>Each request is served faster in that state.</li>'
      '<li>Nothing is congested.</li>'
      '<li>DRAM does one read per line.</li></ul></li>')
    w('<li>Narrowing (section 6)' + r(1, 20) + ':<ul>'
      '<li>A loop with the same loads and padding (window depth assumed equal, not measured) reads 489.6 GB/s '
      'in scrambled order and 297.8 GB/s in sequential order.</li>'
      '<li>So the deep window alone does not lower the total.</li>'
      '<li>The drop depends on how the cores handle a sequential stream.</li>'
      '<li>This rests on one scrambled pattern and on one interval of 10 s per cell from one evening.</li></ul></li>')
    w('<li>Fix verified (section 2)' + r(1) + ': 72 nop or more per 256 B in the load-only loop restores 459 to '
      '480 GB/s. 256 nop gives 544 to 549 GB/s. That is 17 % above the old loop.</li>')
    w('</ul>')
    w('<h3>Not established</h3><ul>')
    w('<li><b>Insufficient data:</b> which rule inside the core lowers the lines in flight for a sequential stream '
      'in the slow state. Section 6 shows that the drop depends on the sequential stream. It does not identify the rule. '
      'The prefetch controls of the V3AE core cannot be read from a normal Linux program. '
      'Two hypotheses exist. Neither is confirmed. H-a and H-b are only labels for them' + r(1) + '.'
      '<ul><li>Hypothesis H-a: the cores set their request limit or their prefetch strength dynamically. '
      'The manual of the Neoverse V2 core documents a dynamic limit of outstanding requests that the busy level '
      'drives (<code>IMP_CPUECTLR2_EL1 TXREQ_LIMIT_DYNAMIC</code>) and adaptive prefetch modes '
      '(<code>PF_MODE</code>). It is not known whether the V3AE core has this limit. '
      'It is not known how the firmware set it. '
      'One finding contradicts a simple form of H-a: the squeezed cores receive lower busy levels.</li>'
      '<li>Hypothesis H-b: a prefetcher adapts its distance to how early the data arrives. '
      'This combines with the need to receive both halves of the lines in order (the half from the own mesh and '
      'the half from the other mesh).</li>'
      '<li>Measurement that would resolve it: read the registers <code>IMP_CPUECTLR_EL1</code> and '
      '<code>IMP_CPUECTLR2_EL1</code> on CRB (this needs a Linux kernel module or firmware access). '
      'Other sources: the prefetch section of the V3AE manual, or a question to Arm support with the data of '
      'sections 4, 5 and 6.</li></ul></li>')
    w('<li><b>Insufficient data:</b> why the write total falls with writers on both meshes. '
      'The fall is the same for old and new loops. The facts sheet names no measurement for it. '
      'A first step would be the mesh counters of section 5 during write runs at 64+0 and at 64+56.</li>')
    w('<li><b>Insufficient data:</b> why old write stays 3 to 4 % above new write under a common stop. '
      'The facts sheet names no measurement for it. A first step would be the core counters per line for both '
      'write loops.</li>')
    w('</ul>')
    w('<h3>Limits of this work</h3><ul>')
    w('<li>All runs come from one evening (2026-11-15, 16:56 to 21:03 UTC) and one machine.</li>')
    w('<li>Many cells have n = 2 intervals from one process. The layout table has one interval per cell. '
      'The sample count of each value is in the tables.</li>')
    w('<li>The window depth of each loop is a measured range from a test with one thread. '
      'It was not measured during the 120-thread runs.</li>')
    w('<li>The lines in flight are estimates (est.). They depend on the assumption named in section 5.</li>')
    w('<li>The scrambled-order results of section 6 have one interval of 10 s per cell. No cell was repeated.</li>')
    w('<li>The two "first step" proposals above come from this report. They are not in the facts sheet.</li>')
    w('</ul>')

    # ------------------------------------------------ (g)
    w('<h2 id="g">8. Recommendation for the benchmark</h2><ul>')
    w('<li>Keep the new load-only loops for one-thread and cache-size measurements. '
      'They measure the load path without extra work.</li>')
    w('<li>For whole-chip DRAM read numbers, state the loop. Report the load-only loop and a window-limited loop. '
      'One example is <code>read_nop256</code>: 544 to 549 GB/s at 64+56. '
      'With one thread and a 32 KiB buffer it reaches 23 GB/s, and the core limits it there' + r(1) + '.</li>')
    w('<li>The 465 to 470 GB/s of the old read loop is one value among several. The value depends on the loop. '
      'It is not a constant of the chip' + r(1) + '.</li>')
    w('<li>For write totals use a common stop time or a long interval. '
      'The whole-pass rule with 0.5 s raises old write by 14 % (144 GB/s against 126 GB/s, median)' + r(1, 4) + '.</li>')
    w('<li>The source of the benchmark was not changed' + r(1) + '.</li>')
    w('</ul>')

    # ------------------------------------------------ (h)
    w('<h2 id="h">9. How it was measured</h2><ul>')
    w('<li>Machine: CRB. All runs: 2026-11-15, 16:56 to 21:03 UTC, a Sunday.</li>')
    w('<li>Machine state: nobody had reserved the machine in the Slack channel #phoenix-crb. The marker file '
      '(a file whose presence says that another performance run is active) was absent. '
      'No other user was logged in' + r(1) + '.</li>')
    w('<li>Load: this report read the load lines in the 14 result folders of 16:56 to 21:03 UTC again. '
      'They agree with the facts sheet' + r(1, 17) + '.<ul>'
      '<li>The 1-minute load average at the start of a script was 0.00 to 71.24.</li>'
      '<li>At the launch of a process it was 0.00 to 109.60.</li>'
      '<li>At every one of the 101 launches 1 task was runnable and 0 users were logged in.</li>'
      '<li>The scripts wait until at most 2 tasks are runnable.</li>'
      '<li>For the scrambled-order run (section 6) the load average was 0.18 at the start of the script and 0.17 to '
      '68.54 at the 13 launches' + r(20) + '.</li>'
      '<li>Hypothesis: the high values are the load average that still falls after the earlier 120-thread '
      'processes of the same script and of this same session. The check: each high value follows the end of such '
      'a process by a few minutes at most (times in <code>launches.txt</code>). This check was not done.</li></ul></li>')
    w('<li>Runner: <code>bwx12.c</code> (the earlier runner program <code>bwx11</code> plus 26 loops). The binary on CRB has the '
      'SHA-256 checksum <code>cd58e564...546a</code>' + r(15) + '.</li>')
    w('<li>Runner of section 6: <code>bwx13</code> (<code>bwx12</code> plus the three scrambled-order loops). '
      'The binary on CRB has the SHA-256 checksum <code>a2858df5...8dad</code>' + r(21) + '.</li>')
    w('<li>Run scripts: plain runs, simultaneous processes, and runs with root counters' + r(16) + '.</li>')
    w('<li>Root use: the user approved <code>sudo perf stat</code> (the Linux counter tool, run as root for the '
      'whole system). The user also approved temporary changes of settings. No setting was changed' + r(1) + '.</li>')
    w('<li>Window test: one thread on CPU 2. Two independent loads that miss the cache are separated by N filler '
      'units. The capacity is the N where the time per iteration rises from the time of about one cache miss to '
      'about two' + r(5) + '.</li>')
    w('<li>Latency probe: the probe cores were CPU 2 and CPU 66. The streaming processes used the other 118 cores'
      + r(10) + '.</li>')
    w('<li>Analysis scripts: six Python scripts compute the totals, the per-mesh rates and the counters per line'
      + r(18) + '.</li>')
    w('<li>Check: an independent checker (a second automated agent, workflow id wf_9d39bfdd-935) recomputed every '
      'number of the facts sheet from the raw files. The facts sheet holds the corrected values' + r(1) + '.</li>')
    w('<li>The scrambled-order section of the facts sheet was added after that check. '
      'This report recomputed its 64+56 sums from the raw files (section 6)' + r(20) + '.</li>')
    w('</ul>')
    w(table('Sample counts' + r(1, 10, 11, 20, 21),
            ['measurement', 'samples'],
            [['original run (section 1)', 'n = 6 per read loop, 0.5 s intervals'],
             ['copy and write at 64+56 (section 1)', 'n = 2 intervals per loop, 6 s and 8 s'],
             ['write under four timing rules (section 1)', '64 processes, 64 intervals per cell'],
             ['window test (section 2)', 'one thread on CPU 2; the number of repetitions is not in the facts sheet'],
             ['read against window depth (section 2)', '12 processes, 177 intervals in total: 169 in the table of '
              'Figure 1 (n per loop 2 to 22) and 8 for the three variants read_pf256, read_pf512, read_pf1024'],
             ['4 KiB pages (section 2)', 'one process per page size'],
             ['thread layouts (section 3)', 'one interval per cell; a second process for 56+56'],
             ['mixed loops (section 4)', 'two processes at the same time, 12 s'],
             ['scrambled-order loops at 64+56 (section 6)', 'run R7: 13 groups, 24 processes, one 10 s interval '
              'each (11 groups of two processes at the same time, 2 groups with mesh 0 alone)'],
             ['scrambled-order loops with one thread (section 6)', 'two runs of 0.5 s per loop on CPU 2: one for the rate, one with counters'],
             ['latency probe (section 5)', 'one run per case; per probe core 9 repetitions of 1,000,000 '
              'iterations (header of the raw probe files)'],
             ['mesh counters (section 5)', 'one run per state; 22 counter windows per run (raw folder); '
              'no multiplexed row'],
             ['memory-port counters, data path, busy level, core counters (section 5)',
              'not in the facts sheet']], num_from=9))

    # ------------------------------------------------ references
    R = '/home/jhan/workspace/titan/cache-perf/crb/results'
    W = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15'
    refs = [
        'Facts sheet: <code>%s/FINDINGS.md</code>' % W,
        'Original run: <code>%s/kernels-20261113T181222Z/threads120.csv</code> (benchmark <code>bandwidth.c</code>)' % R,
        'Copy, write and 56+56 runs: <code>%s/w120-R1-20261115T185140Z/</code> (files <code>p4copy.csv</code>, '
        '<code>p3write.csv</code>, <code>p6w6400.csv</code>, <code>p7w3232.csv</code>, <code>p5r5656.csv</code>)' % R,
        'Write under four timing rules: <code>%s/B10a-*</code> and <code>%s/B10b-*</code>' % (R, R),
        'Window test: <code>%s/robsize/</code> (program <code>robsize.c</code>, results '
        '<code>results/rob-k1-*.csv</code>, <code>rob-k2-*.csv</code>, <code>rob-k3-*.csv</code>)' % W,
        'Read runs at 64+56: <code>%s/w120-R0-20261115T165608Z/</code>, <code>w120-R0b-20261115T170342Z/</code>, '
        '<code>w120-R1-20261115T185140Z/</code>, <code>w120-R5-20261115T203152Z/</code>, '
        '<code>w120-R6-20261115T203438Z/</code>' % R,
        '4 KiB pages: <code>%s/w120-R5-20261115T203152Z/nothp.csv</code>' % R,
        'Thread layouts: <code>%s/w120-R0b-20261115T170342Z/</code> and <code>p5r5656.csv</code> of [Ref3]' % R,
        'Mixed loops: <code>%s/w120-R3-20261115T193922Z/</code>' % R,
        'Latency probe: <code>%s/w120-R4-20261115T200016Z/</code>' % R,
        'Mesh counters: <code>%s/w120-RC1-20261115T190208Z/</code>' % R,
        'Memory-port counters: <code>%s/w120-RC2-20261115T192222Z/</code>' % R,
        'Data path to the cores: <code>%s/w120-RC5-20261115T201920Z/</code>' % R,
        'Busy level on responses: <code>%s/w120-RC4-20261115T201114Z/</code> and '
        '<code>w120-RC6-20261115T202517Z/</code>' % R,
        'Runner: <code>%s/bwx12-2026-11-15/bwx12.c</code>. Binary on CRB: '
        '<code>~/cache-perf/bwx12-20261115/bwx12</code>' % os.path.dirname(W),
        'Run scripts in <code>%s/</code>: <code>r0.sh</code>, <code>rx.sh</code> (plain runs), <code>rg.sh</code> '
        '(simultaneous processes), <code>rc.sh</code>, <code>rc2.sh</code>, <code>rgc.sh</code> (root counters)' % W,
        'All result folders of this session: <code>%s/w120-*</code> (files <code>env.txt</code> and '
        '<code>launches.txt</code>)' % R,
        'Analysis scripts in <code>%s/</code>: <code>an.py</code>, <code>anc.py</code>, <code>anc2.py</code>, '
        '<code>anc3.py</code>, <code>anc4.py</code>, <code>ang.py</code>' % W,
        'Generator of this page: <code>%s/report_w120.py</code>' % W,
        'Scrambled-order run R7: <code>%s/w120-R7-20261115T205946Z/</code> (per group <code>&lt;group&gt;.m0.csv</code> '
        'and <code>&lt;group&gt;.m1.csv</code>, <code>launches.txt</code>, <code>env.txt</code>)' % R,
        'Runner with the scrambled-order loops: <code>%s/bwx13-2026-11-15/</code> (source <code>bwx13.c</code>, '
        'one-thread test <code>crb-build-1/smoke13.txt</code>). Binary on CRB: '
        '<code>~/cache-perf/bwx13-20261115/bwx13</code>' % os.path.dirname(W),
    ]
    w('<h2 id="refs">References</h2><ol class="refs">')
    for i, t in enumerate(refs):
        w('<li>[Ref%d] %s</li>' % (i + 1, t))
    w('</ol>')
    w('</main>\n</body>\n</html>\n')

    bad = g1.overlaps() + g2.overlaps() + g3.overlaps() + g4.overlaps()
    return '\n'.join(P), bad


if __name__ == '__main__':
    html, bad = build()
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print('wrote %s (%d bytes)' % (OUT, len(html.encode('utf-8'))))
    for b in bad:
        print('LABEL OVERLAP:', b)
    print('label overlaps: %d' % len(bad))
    sys.exit(1 if bad else 0)
