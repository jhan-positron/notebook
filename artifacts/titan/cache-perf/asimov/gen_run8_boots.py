#!/usr/bin/env python3
"""Run 8 (mesh latency map), the three boots side by side: folders 014, 015, 016.

Reads the raw result files and writes one self-contained HTML page.
Usage: python3 gen_run8_boots.py [--out run8-meshmap-3boots.html]
The boot 1 page (gen_run8_report.py) stays the record for the rehearsal and boot 1.
"""
import csv, sys, os, re, statistics as st, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(HERE, 'run8-meshmap-3boots.html')

NODES = [88, 160, 216, 288, 344]
NPOS = {88: (1, 3), 160: (2, 4), 216: (3, 3), 288: (4, 4), 344: (5, 3)}
CPOS = {0: (1, 2), 2: (2, 3), 3: (2, 3), 4: (3, 2), 5: (3, 2), 6: (4, 3), 7: (4, 3), 8: (5, 2), 9: (5, 2)}
KINDS = ['ocm-flush', 'ocm-evict', 'slc', 'dram-flush']
C29 = [2, 3, 4, 5, 6, 7, 8, 9]
CELLS = [(c, n) for c in C29 for n in NODES]
COLOR = {1: '#2a78d6', 2: '#eb6834', 3: '#1baf7a'}
STATE = {1: 'L3 holds no data, prefetchers off', 2: 'L3 in use, prefetchers off', 3: 'L3 in use, prefetchers on'}
RAMP = ['#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab']


def steps(c, n):
    return abs(CPOS[c][0] - NPOS[n][0]), abs(CPOS[c][1] - NPOS[n][1])


def units(c, n):
    """Distance in boot 1's cost units: 2 per X step, 1 per Y step (1 unit = 1.00 ns on boot 1)."""
    dx, dy = steps(c, n)
    return 2 * dx + dy


def arm_select(pa, n=5):
    a = pa >> 6
    h = (a & 0xfff) ^ ((a >> 12) & 0xfff) ^ ((a >> 24) & 0xfff) ^ ((a >> 36) & 0x3ff)
    top = 0
    for k in range(6):
        top |= (((h >> (11 - k)) ^ (h >> k)) & 1) << (5 - k)
    return (((top << 6) | (h & 0x3f)) * n) >> 12


def tri(c, n, m):
    (cx, cy), (hx, hy) = CPOS[c], NPOS[n]
    return abs(cx - hx) + abs(hx - m[0]) + abs(m[0] - cx), abs(cy - hy) + abs(hy - m[1]) + abs(m[1] - cy)


class Boot:
    def __init__(s, folder, b):
        s.b, s.folder = b, folder
        s.dir = os.path.join(HERE, 'results/membench-jibin-%s/results/bootM%d' % (folder, b))
        L = open(os.path.join(s.dir, 'latency-map.csv')).read().split('\n')
        s.notes = [l for l in L if l.startswith('#')]
        rows = list(csv.reader(l for l in L if l and not l.startswith('#')))
        s.H = {n: i for i, n in enumerate(rows[0])}
        s.rows = rows[1:]
        s.cells = collections.defaultdict(list)
        for r in s.rows:
            if r[0] != 'idle':
                s.cells[(r[0], int(r[1]), int(r[2]))].append(r)
        assert len(s.rows) == 1269 and len(s.cells) == 180 and {len(v) for v in s.cells.values()} == {7}
        assert {len(r) for r in s.rows} == {23}

    def note(s, key):
        return [l for l in s.notes if key in l][-1]

    def col(s, k, c, n, name='ns_per_load'):
        return [float(r[s.H[name]]) for r in s.cells[(k, c, n)]]

    def best(s, k, c, n):
        return min(s.col(k, c, n))

    def med(s, k, c, n, name='ns_per_load'):
        return st.median(s.col(k, c, n, name))

    def allrows(s, k, name):
        return [x for c, n in CELLS for x in s.col(k, c, n, name)]

    def fit_xy(s, kind):
        A = np.array([[1, *steps(c, n)] for c, n in CELLS], float)
        y = np.array([s.best(kind, c, n) for c, n in CELLS])
        co = np.linalg.lstsq(A, y, rcond=None)[0]
        r = y - A @ co
        return co, float((r ** 2).mean() ** .5), float(abs(r).max())

    def fit_tri(s):
        y = np.array([s.best('dram-flush', c, n) for c, n in CELLS])
        out = []
        for mx in range(6):
            for my in range(6):
                A = np.array([[1, *tri(c, n, (mx, my))] for c, n in CELLS], float)
                if np.linalg.matrix_rank(A) < 3:
                    continue
                co = np.linalg.lstsq(A, y, rcond=None)[0]
                r = y - A @ co
                out.append((float((r ** 2).mean() ** .5), (mx, my), co))
        out.sort(key=lambda t: (round(t[0], 6), t[1]))
        return out

    def fit_mix(s, kind):
        """ns = a*(1-f) + f*(b + c*units) over the 280 rows of CPUs 2 to 9; f = l3d_refill_rd."""
        X, y = [], []
        for c, n in CELLS:
            for f, v in zip(s.col(kind, c, n, 'l3d_refill_rd'), s.col(kind, c, n)):
                X.append([1 - f, f, f * units(c, n)])
                y.append(v)
        X, y = np.array(X), np.array(y)
        co = np.linalg.lstsq(X, y, rcond=None)[0]
        r = y - X @ co
        return co, float((r ** 2).mean() ** .5), float(np.corrcoef(y, X[:, 1])[0, 1]), len(y)

    def fit_mix2(s, kind):
        """As fit_mix, with one more term for the mesh loads of passes 4 to 6:
        ns = a*(1-f) + f*(b + c*units + d*[pass >= 4]). On boot 1 (f = 1 in every row) a is dropped."""
        X, y = [], []
        for c, n in CELLS:
            for rep_, (f, v) in enumerate(zip(s.col(kind, c, n, 'l3d_refill_rd'), s.col(kind, c, n))):
                row = [1 - f, f, f * units(c, n), f * (rep_ >= 4)]
                X.append(row[1:] if s.b == 1 else row)
                y.append(v)
        X, y = np.array(X), np.array(y)
        co = np.linalg.lstsq(X, y, rcond=None)[0]
        r = y - X @ co
        return ([None] if s.b == 1 else []) + list(co), float((r ** 2).mean() ** .5)

    def own_req(s, kind):
        """Median over rows of: requests at the cell's node, and mean requests at the other four nodes, per load."""
        own, oth = [], []
        for c, n in CELLS:
            for r in s.cells[(kind, c, n)]:
                own.append(float(r[s.H['req_%d' % n]]))
                oth.append(np.mean([float(r[s.H['req_%d' % m]]) for m in NODES if m != n]))
        return st.median(own), st.median(oth)

    def hash_check(s):
        L = open(os.path.join(s.dir, 'map-homes.txt')).read().split('\n')
        pfn = int(re.search(r'pfn=(0x[0-9a-f]+)', L[0]).group(1), 16)
        t = ''.join(x for x in L[1:] if not x.startswith('#'))
        m = collections.Counter()
        for i, ch in enumerate(t):
            if ch in '01234':
                m[(arm_select((pfn << 12) + 64 * i), int(ch))] += 1
        mp = {}
        for (f, h), c in m.items():
            if c > mp.get(f, (0, 0))[1]:
                mp[f] = (h, c)
        agree = sum(c for (f, h), c in m.items() if mp[f][0] == h)
        return pfn, sum(m.values()), agree, [NODES[mp[f][0]] for f in range(5)], t.count('?')

    def controls(s):
        out = []
        for cpu in (2, 8):
            for reg in (0, 4):
                p = os.path.join(s.dir, 'latency-ocm-region%d-mapctl-cpu%d.csv' % (reg, cpu))
                b = [float(l.split(',')[5]) for l in open(p) if ',best,' in l][0]
                out.append((cpu, NODES[reg], b, s.best('ocm-flush', cpu, NODES[reg])))
        return out

    def hw(s, cpu0):
        return sum(1 for r in s.rows if r[0] != 'idle' and (r[1] == '0') == cpu0
                   and (float(r[s.H['l1d_refill_hwprf']]) > 0 or float(r[s.H['l2d_refill_hwprf']]) > 0))

    def step(s, k):
        v = [np.mean(s.col(k, c, n)[4:]) - np.mean(s.col(k, c, n)[:4]) for c, n in CELLS]
        return float(np.mean(v)), min(v), max(v)


B = {1: Boot('014', 1), 2: Boot('015', 2), 3: Boot('016', 3)}
FIT = {(b, k): B[b].fit_xy(k) for b in B for k in KINDS}
TRI = {b: B[b].fit_tri() for b in B}
MIX = {(b, k): B[b].fit_mix(k) for b, k in ((2, 'ocm-evict'), (2, 'slc'), (3, 'ocm-flush'), (3, 'ocm-evict'), (3, 'slc'), (3, 'dram-flush'))}
MIX2 = {(b, k): B[b].fit_mix2(k) for b, k in ((1, 'ocm-evict'), (1, 'slc'), (2, 'ocm-evict'), (2, 'slc'), (3, 'ocm-flush'), (3, 'ocm-evict'), (3, 'slc'))}
HC = {b: B[b].hash_check() for b in B}
CTL = {b: B[b].controls() for b in B}


def rng(b, k, f=None):
    v = [(f or B[b].best)(k, c, n) for c, n in CELLS]
    return min(v), max(v)


def rrng(b, k, name):
    v = B[b].allrows(k, name)
    return min(v), st.median(v), max(v)


def diff(b2, b1, k):
    d = [B[b2].best(k, c, n) - B[b1].best(k, c, n) for c, n in CELLS]
    return float(np.mean(d)), min(d), max(d)


# ---------- figures ----------
def strip():
    """Four panels (kinds), three rows (boots), one dot per cell of CPUs 2 to 9, shared ns axis."""
    W, lm, rm, ph, top = 1000, 150, 110, 30, 26
    lo, hi = 10, 60
    X = lambda v: lm + (v - lo) / (hi - lo) * (W - lm - rm)
    Hh = top + len(KINDS) * (3 * ph + 22) + 30
    s = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="best ns per load of every cell, by kind and boot">' % (W, Hh)]
    for t in range(lo, hi + 1, 5):
        s.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="grid"/>' % (X(t), top - 4, X(t), Hh - 28))
        s.append('<text x="%.1f" y="%d" class="lab" text-anchor="middle">%d</text>' % (X(t), Hh - 14, t))
    s.append('<text x="%.1f" y="%d" class="lab" text-anchor="end">best ns per load</text>' % (W - rm, Hh - 1))
    y = top
    for k in KINDS:
        s.append('<text x="8" y="%d" class="kind">%s</text>' % (y + 12, k))
        for b in B:
            yy = y + (b - 1) * ph + ph / 2 + 8
            s.append('<text x="%d" y="%.1f" class="lab" text-anchor="end">boot %d</text>' % (lm - 10, yy + 4, b))
            lo_, hi_ = rng(b, k)
            s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2" opacity=".35"/>' % (X(lo_), yy, X(hi_), yy, COLOR[b]))
            for c, n in CELLS:
                v = B[b].best(k, c, n)
                s.append('<circle cx="%.1f" cy="%.1f" r="4.2" fill="%s" class="dot"><title>boot %d, %s, CPU %d to node %d: best %.2f ns, median %.2f ns</title></circle>'
                         % (X(v), yy + ((c * 7 + n) % 5 - 2) * 1.6, COLOR[b], b, k, c, n, v, B[b].med(k, c, n)))
            s.append('<text x="%.1f" y="%.1f" class="val">%.1f to %.1f ns</text>' % (X(hi_) + 9, yy + 4, lo_, hi_))
        y += 3 * ph + 22
        s.append('<line x1="0" y1="%d" x2="%d" y2="%d" class="grid"/>' % (y - 6, W, y - 6))
    s.append('</svg>')
    return ''.join(s)


def scatter():
    """Boot 2, ocm-evict and slc rows: ns per load against the share of loads that left the cluster."""
    W, Hh, lm, bm, tm, rm = 760, 400, 56, 44, 14, 150
    X = lambda f: lm + f * (W - lm - rm)
    Y = lambda v: Hh - bm - (v - 8) / (32 - 8) * (Hh - bm - tm)
    s = ['<svg viewBox="0 0 %d %d" width="100%%" style="max-width:%dpx" role="img" aria-label="boot 2: ns per load against the share of loads that left the cluster">' % (W, Hh, W)]
    for v in range(8, 33, 4):
        s.append('<line x1="%d" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="lab" text-anchor="end">%d</text>' % (lm, Y(v), X(1), Y(v), lm - 6, Y(v) + 4, v))
    for f in (0, .2, .4, .6, .8, 1):
        s.append('<text x="%.1f" y="%d" class="lab" text-anchor="middle">%.1f</text>' % (X(f), Hh - bm + 16, f))
    s.append('<line x1="%d" y1="%.1f" x2="%.1f" y2="%.1f" class="axis"/>' % (lm, Y(8), X(1), Y(8)))
    s.append('<text x="%.1f" y="%d" class="lab" text-anchor="middle">share of loads that left the cluster (l3d_refill_rd per load)</text>' % (X(.5), Hh - 8))
    s.append('<text x="14" y="%.1f" class="lab" transform="rotate(-90 14 %.1f)" text-anchor="middle">ns per load</text>' % (Y(20), Y(20)))
    a = np.mean([MIX[(2, k)][0][0] for k in ('ocm-evict', 'slc')])
    b_ = np.mean([MIX[(2, k)][0][1] for k in ('ocm-evict', 'slc')])
    c_ = np.mean([MIX[(2, k)][0][2] for k in ('ocm-evict', 'slc')])
    for u, lab in ((1, 'nearest node (1 unit)'), (9, 'farthest node (9 units)')):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="model"/>' % (X(0), Y(a), X(1), Y(b_ + c_ * u)))
        s.append('<text x="%.1f" y="%.1f" class="lab">model, %s</text>' % (X(1) + 8, Y(b_ + c_ * u) + 4, lab))
    for k in ('ocm-evict', 'slc'):
        for c, n in CELLS:
            u = units(c, n)
            for f, v, rep in zip(B[2].col(k, c, n, 'l3d_refill_rd'), B[2].col(k, c, n), range(7)):
                s.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s" class="dot"><title>%s, CPU %d to node %d (distance %d), pass %d: %.2f ns, share %.2f</title></circle>'
                         % (X(f), Y(min(v, 32)), RAMP[u - 1], k, c, n, u, rep, v, f))
    s.append('<text x="%.1f" y="%.1f" class="val" text-anchor="middle">in the cluster: %.1f ns est.</text>' % (X(0) + 78, Y(a) + 18, a))
    s.append('<circle cx="%.1f" cy="%.1f" r="4" fill="none" stroke="#1d1d1b" stroke-width="1.5"/>' % (X(0), Y(a)))
    s.append('</svg>')
    leg = '<span class="leg">colour: distance of the node, 1 unit ' + ''.join('<i style="background:%s"></i>' % c for c in RAMP) + ' 9 units</span>'
    return ''.join(s) + '<div>' + leg + '</div>'


def table(b, kind):
    s = ['<table class="num"><thead><tr><th>CPU (crosspoint)</th>' + ''.join('<th>node %d</th>' % n for n in NODES) + '</tr></thead><tbody>']
    for c in [0] + C29:
        cls = ' class="k0"' if c == 0 else ''
        s.append('<tr%s><td>CPU %d (%d,%d)</td>' % (cls, c, *CPOS[c]) + ''.join('<td>%.2f</td>' % B[b].best(kind, c, n) for n in NODES) + '</tr>')
    return ''.join(s) + '</tbody></table>'


def ftable(b, kind, name):
    s = ['<table class="num"><thead><tr><th>CPU</th>' + ''.join('<th>node %d</th>' % n for n in NODES) + '</tr></thead><tbody>']
    for c in [2, 4, 6, 8, 3, 5, 7, 9]:
        s.append('<tr><td>CPU %d</td>' % c + ''.join('<td>%.2f</td>' % B[b].med(kind, c, n, name) for n in NODES) + '</tr>')
    return ''.join(s) + '</tbody></table>'


# ---------- numbers for the text ----------
def classify(b):
    m = re.search(r'probed=(\d+) ambiguous=(\d+) unused=(\d+) per_node=([\d,]+)', B[b].note('probed='))
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)


MMSEC_ = {'1.217': 1.1054, '1.187': 1.0733, '1.157': 1.0466}   # checked against meshmap-log.txt below
CHIP = {1: 1.217, 2: 1.187, 3: 1.157}   # chip seconds of the script, from Jesse's READMEs (the console line is not in our copy)
whole_rows = ''.join(
    '<tr><td>Boot %d (folder %s)</td><td>%s</td><td>1,269 rows, 180 of 180 cells</td><td>%.4f</td><td>%s</td><td>%s; %s per node; %d unused</td><td>%s of %s</td><td>%.3f</td></tr>'
    % (b, B[b].folder, STATE[b], min(float(r[B[b].H['perf_cov']]) for r in B[b].rows), re.search(r'level=(\d)', B[b].note('level=')).group(1),
       '{:,}'.format(classify(b)[0]), classify(b)[3].replace(',', ', '), classify(b)[2], '{:,}'.format(HC[b][2]), '{:,}'.format(HC[b][1]), CHIP[b]) for b in B)
whole_rows = re.sub(r'<td>(1\.\d\d\d)</td></tr>', lambda m: '<td>%s, %.3f</td></tr>' % (m.group(1), MMSEC_[m.group(1)]), whole_rows)
order = {tuple(HC[b][3]) for b in B}
assert len(order) == 1
fit_rows = ''.join('<tr><td>Boot %d</td><td><code>%s</code></td><td>%.2f to %.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td></tr>'
                   % (b, k, *rng(b, k), *FIT[(b, k)][0], FIT[(b, k)][1], FIT[(b, k)][2]) for k in KINDS for b in B)
mix_rows = ''.join('<tr><td>Boot %d</td><td><code>%s</code></td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%+.2f</td></tr>'
                   % (b, k, MIX[(b, k)][0][0], MIX[(b, k)][0][1], MIX[(b, k)][0][2], MIX[(b, k)][1], MIX[(b, k)][2]) for (b, k) in MIX)
cnt_rows = ''.join('<tr><td>Boot %d</td><td><code>%s</code></td><td>%.2f / %.2f / %.2f</td><td>%.2f / %.2f / %.2f</td><td>%s</td></tr>'
                   % (b, k, *rrng(b, k, 'l3d_refill_rd'), *rrng(b, k, 'l2d_refill_hwprf'),
                      '-' if k == 'ocm-flush' else '%.4f to %.4f' % rng(b, k, lambda kk, c, n: B[b].med(kk, c, n, 'mc_reqs'))) for k in KINDS for b in B)
ctl_rows = ''.join('<tr><td>Boot %d</td><td>CPU %d</td><td>node %d</td><td>%.3f</td><td>%.3f</td><td>%+.3f</td></tr>' % (b, c, n, a, m, m - a) for b in B for c, n, a, m in CTL[b])
ctl_max = {b: max(abs(a - m) for _, _, a, m in CTL[b]) for b in B}
step_rows = ''.join('<tr><td><code>%s</code></td>' % k + ''.join('<td>%+.2f (%+.2f to %+.2f)</td>' % B[b].step(k) for b in B) + '</tr>' for k in KINDS)
tri_rows = ''.join('<tr><td>Boot %d</td><td>(%d,%d) or (%d,%d)</td><td>%.3f</td><td>%.3f</td><td>%.3f</td><td>%.3f</td></tr>'
                   % (b, *TRI[b][0][1], *TRI[b][1][1], [t for t in TRI[b] if t[1] == (0, 3)][0][2][0], TRI[b][0][2][1], TRI[b][0][2][2], TRI[b][0][0]) for b in (1, 2))
cpu0_rows = ''.join('<tr><td><code>%s</code></td>' % k + ''.join('<td>%.1f to %.1f</td>' % (min(B[b].best(k, 0, n) for n in NODES), max(B[b].best(k, 0, n) for n in NODES)) for b in B) + '</tr>' for k in KINDS)
d21 = {k: diff(2, 1, k) for k in KINDS}
se = {b: [B[b].best('slc', c, n) - B[b].best('ocm-evict', c, n) for c, n in CELLS] for b in B}
medfit2 = (lambda A, y: (np.linalg.lstsq(A, y, rcond=None)[0], float(((y - A @ np.linalg.lstsq(A, y, rcond=None)[0]) ** 2).mean() ** .5)))(
    np.array([[1, *steps(c, n)] for c, n in CELLS], float), np.array([B[2].med('ocm-flush', c, n) for c, n in CELLS]))
first = {(b, k): ([B[b].med(k, c, 88, 'l3d_refill_rd') for c in (2, 4, 6, 8)], [B[b].med(k, c, 88, 'l3d_refill_rd') for c in (3, 5, 7, 9)],
                  [B[b].med(k, c, n, 'l3d_refill_rd') for c in C29 for n in NODES[1:]]) for b in (2, 3) for k in ('ocm-evict', 'slc')}
first_rows = ''.join('<tr><td>Boot %d</td><td><code>%s</code></td><td>%s</td><td>%s</td><td>%.2f (%.2f to %.2f)</td></tr>'
                     % (b, k, ', '.join('%.2f' % x for x in v[0]), ', '.join('%.2f' % x for x in v[1]), st.median(v[2]), min(v[2]), max(v[2])) for (b, k), v in first.items())
tlb = {b: (rng(b, 'ocm-flush', lambda k, c, n: B[b].med(k, c, n, 'l1d_tlb_refill'))) for b in B}
dram3_spread = (min(max(B[3].col('dram-flush', c, n)) - min(B[3].col('dram-flush', c, n)) for c, n in CELLS),
                max(max(B[3].col('dram-flush', c, n)) - min(B[3].col('dram-flush', c, n)) for c, n in CELLS))
m2e, m2s = MIX[(2, 'ocm-evict')][0], MIX[(2, 'slc')][0]
mix2_rows = ''.join('<tr><td>Boot %d</td><td><code>%s</code></td><td>%s</td><td>%.2f</td><td>%.2f</td><td>%+.2f</td><td>%.2f</td></tr>'
                    % (b, k, '-' if v[0][0] is None else '%.2f' % v[0][0], v[0][1], v[0][2], v[0][3], v[1]) for (b, k), v in MIX2.items())
a_est = np.mean([MIX2[(2, k)][0][0] for k in ('ocm-evict', 'slc')])
AMBIG = {b: classify(b)[1] for b in B}
MMSEC = {b: float(re.search(r'in ([\d.]+) s', open(os.path.join(B[b].dir, 'meshmap-log.txt')).read()).group(1)) for b in B}


def passes(b, k, c, n, name='l3d_refill_rd'):
    return ', '.join('%.2f' % x for x in B[b].col(k, c, n, name))


trans_rows = ''.join('<tr><td>Boot %d</td><td><code>%s</code></td><td>CPU %d to node %d</td><td>%s</td><td>%s</td></tr>' % (b, k, c, n, passes(b, k, c, n), ', '.join('%.1f' % x for x in B[b].col(k, c, n)))
                     for b, k, c, n in ((2, 'slc', 2, 88), (2, 'slc', 8, 88), (2, 'slc', 3, 88), (3, 'slc', 6, 88), (3, 'slc', 8, 88), (3, 'ocm-evict', 8, 160), (1, 'slc', 0, 88)))
d32 = {k: [B[3].best(k, c, n) - B[2].best(k, c, n) for c, n in CELLS] for k in KINDS}
dmed3 = rng(3, 'dram-flush', B[3].med)
noprf = [(c, n, v) for c, n in CELLS for v, h in zip(B[3].col('dram-flush', c, n), B[3].col('dram-flush', c, n, 'l2d_refill_hwprf')) if h == 0]
noprf_rows = ''.join('<tr><td>CPU %d to node %d</td><td>%s</td><td>%.2f</td><td>%.2f</td></tr>' % (c, n, ', '.join('%.2f' % v for cc, nn, v in noprf if (cc, nn) == (c, n)), B[1].med('dram-flush', c, n), B[2].med('dram-flush', c, n))
                     for c, n in sorted({(c, n) for c, n, v in noprf}))
OWN = {(b, k): B[b].own_req(k) for b in B for k in KINDS[1:]}
own_rows = ''.join('<tr><td><code>%s</code></td>' % k + ''.join('<td>%.2f / %.2f</td>' % OWN[(b, k)] for b in B) + '</tr>' for k in KINDS[1:])
slc_mc_row_max = max(x for b in B for x in B[b].allrows('slc', 'mc_reqs'))
tlb3 = {n: sorted({round(B[3].med('ocm-flush', c, n, 'l1d_tlb_refill'), 4) for c in C29}) for n in NODES}
assert [MMSEC[b] for b in B] == list(MMSEC_.values())
cpu0f = {b: [B[b].med('slc', 0, n, 'l3d_refill_rd') for n in NODES] for b in B}

CSS = """
:root{--ink:#1d1d1b;--ink2:#55554f;--line:#d9d8d2;--bg:#ffffff;--soft:#f6f5f1}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,Segoe UI,Helvetica,Arial,sans-serif}
main{max-width:1060px;margin:0 auto;padding:24px 16px 60px}h1{font-size:25px;margin:0 0 4px}h2{font-size:19px;margin:34px 0 8px;border-top:1px solid var(--line);padding-top:18px}
h3{font-size:16px;margin:22px 0 6px}h4{font-size:14px;margin:18px 0 6px;font-weight:600}.sub{color:var(--ink2);margin:0 0 14px}
.short{background:var(--soft);border-left:4px solid #256abf;padding:10px 14px;margin:14px 0}.short p{margin:4px 0}
code{font:13px ui-monospace,Menlo,Consolas,monospace;background:var(--soft);padding:0 3px;border-radius:3px}
table{border-collapse:collapse;margin:8px 0 14px;font-size:13.5px}th,td{border-bottom:1px solid var(--line);padding:4px 10px;text-align:left;vertical-align:top}
th{font-weight:600;color:var(--ink2)}td:first-child{white-space:nowrap}table.num td:not(:first-child),table.num th:not(:first-child){text-align:right;font-variant-numeric:tabular-nums}
tr.k0 td{color:var(--ink2);font-style:italic}.scroll{overflow-x:auto}
.grid{stroke:#e4e3dd;stroke-width:1}.axis{stroke:#a8a79f;stroke-width:1}.dot{stroke:#fff;stroke-width:.8;opacity:.85}.model{stroke:#1d1d1b;stroke-width:1.4;stroke-dasharray:5 3}
.lab{font:11.5px sans-serif;fill:#55554f}.val{font:600 11.5px sans-serif;fill:#1d1d1b}.kind{font:600 13px ui-monospace,Menlo,Consolas,monospace;fill:#1d1d1b}
.leg{font-size:12px;color:var(--ink2);white-space:nowrap}.leg i{display:inline-block;width:14px;height:10px;vertical-align:-1px}
.key i{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 4px 0 12px;vertical-align:-1px}
.take{font-weight:600;margin:6px 0 12px}.two{display:flex;flex-wrap:wrap;gap:22px;align-items:flex-start}.two>div{flex:1 1 320px}
.hyp{border:1px dashed #a8a79f;padding:8px 12px;margin:10px 0;border-radius:4px}
ul{padding-left:20px;margin:6px 0}li{margin:3px 0}details{margin:8px 0}summary{cursor:pointer;font-weight:600}
"""

key = ''.join('<i style="background:%s"></i>boot %d: %s' % (COLOR[b], b, STATE[b]) for b in B)
exact = ''.join('<details><summary>Boot %d, best ns per load of 7 passes, all four kinds</summary><div class="two">%s</div></details>'
                % (b, ''.join('<div><h4><code>%s</code></h4><div class="scroll">%s</div></div>' % (k, table(b, k)) for k in KINDS)) for b in (2, 3))

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Run 8 mesh map: three boots</title><style>{CSS}</style></head><body><main>
<h1>Run 8, the mesh latency map: the three boots</h1>
<p class="sub">Asimov emulator, result folders 014 (boot 1), 015 (boot 2) and 016 (boot 3). Files copied and checked 2026-11-12. The trial run and the full detail of boot 1 are on the page <code>run8-meshmap-boot1.html</code>.</p>

<div class="short"><b>Short version</b>
<p>All three boots returned complete files: 180 of 180 cells each, and Arm's hash formula predicts the home node of every classified line on three different memory pages.</p>
<p>With the L3 in use (boot 2), the flushed kinds repeat boot 1 to within 0.7 ns, but the <code>slc</code> and <code>ocm-evict</code> cells drop to 13 to 17 ns: about 70% of their loads never left the cluster, so on this boot these cells are not a distance map of the slice.</p>
<p>With the prefetchers on as well (boot 3), the flushed kinds drop to 12 to 35 ns and stop following the distance, and the evicted kinds stay as on boot 2.</p></div>

<h2>Words used here</h2>
<ul>
<li><b>Mesh</b>: the chip's interconnect, 6 x 6 crosspoints. A message moves one crosspoint per step. Crosspoints are written (x,y).</li>
<li><b>Home node</b>: one of five cache nodes on the mesh (ids 88, 160, 216, 288, 344). Each holds a slice of the system-level cache (SLC) and 256 KiB of on-chip memory (OCM).</li>
<li><b>DRAM-backed line</b>: a 64-byte line of normal memory (DRAM). A hash of its physical address selects its home node. <b>Frame number</b>: the physical address of a page divided by 4 KiB.</li>
<li><b>Cluster</b>: two CPUs that share one L2 cache and one L3 cache (CPUs 2-3, 4-5, 6-7, 8-9, and 0-1). The L3 sits between the L2 and the mesh. <b>Prefetcher</b>: hardware in a CPU that fetches lines before the program loads them.</li>
<li><b>Cell</b>: one CPU, one home node, one kind of row. Each cell has 7 timed passes of 2,048 dependent loads (each load gives the address of the next). <b>Best</b> is the smallest ns per load of the 7 passes.</li>
<li><b>Kinds</b>: <code>ocm-flush</code> (OCM lines, flushed first), <code>ocm-evict</code> (OCM lines, pushed out of the CPU's caches by the evictor), <code>slc</code> (DRAM-backed lines held in the node's slice, same recipe as <code>ocm-evict</code>), <code>dram-flush</code> (the same DRAM-backed lines, flushed first, so every load goes to memory). The <b>flushed kinds</b> are the first and the last. The <b>evicted kinds</b> are the middle two.</li>
<li><b>Evictor</b>: one load of each of 30,720 other lines, made before a timed pass of an evicted kind.</li>
<li><b><code>meshmap</code></b>: the program that measures the cells. <b>Classification</b>: its first step, which finds the home node of each DRAM-backed line with the mesh counters. <b><code>run_map.sh</code></b>: the script that runs it, after four <b>control rows</b> of the older program <code>latency</code>.</li>
<li><b>Core counters</b>, all per load: <code>l3d_refill_rd</code> counts demand loads whose data came from outside the cluster. <code>l2d_refill_hwprf</code> counts L2 fills made by the prefetcher. <code>l1d_tlb_refill</code> counts misses in the address translation cache (TLB). <code>perf_cov</code> is the share of the pass that the core counters covered.</li>
<li><b>Mesh counters</b>, all per load: <code>req_&lt;node&gt;</code> counts requests that reach a home node. <code>mc_reqs</code> counts requests that a home node sends on to memory. <b>Level 1</b> means that all mesh counters opened.</li>
<li><b>Share</b>: <code>l3d_refill_rd</code> per load of one pass, read as the share of the loads that left the cluster.</li>
<li><b>Unit of distance</b>: 2 per X step plus 1 per Y step. On boot 1 one unit costs 1.00 ns.</li>
<li><b>Chip second</b>: one second of time on the emulated chip. <b>rms</b>: root mean square of a fit's errors. <b>est.</b>: an estimate.</li>
<li><b>Boots</b>: boot 1 = {STATE[1]}. Boot 2 = {STATE[2]}. Boot 3 = {STATE[3]}. The states hold for CPUs 2 to 9. CPU 0's cluster has its L3 in use and its prefetchers on at every boot (section 7). <b>Jesse</b>: Jesse Zhang, who operates the emulator.</li>
</ul>

<h2>1. Are the files complete?</h2>
<p>Each folder passes its checksums, 11 of 11 files [Ref1]. The checksum list does not cover the README. Each <code>latency-map.csv</code> ends with <code>done cells=180/180</code> [Ref2].</p>
<div class="scroll"><table><thead><tr><th>Boot</th><th>State of CPUs 2 to 9</th><th>Rows and cells</th><th>Lowest <code>perf_cov</code></th><th>Mesh counter level</th><th>Classification: lines probed</th><th>Lines whose home node Arm's hash predicts</th><th>Chip seconds: script [Ref5], <code>meshmap</code> alone [Ref2]</th></tr></thead><tbody>{whole_rows}</tbody></table></div>
<ul>
<li><b>The hash check now holds on three physical pages.</b> The buffers sat at frame numbers 0x{HC[1][0]:x}, 0x{HC[2][0]:x} and 0x{HC[3][0]:x}. On each, the formula of the Arm manual gives the measured home node of every classified line, with the same table order 88, 216, 344, 160, 288 [Ref3] [Ref6].</li>
<li><b>Each boot has its own classification.</b> A line's home node depends on its physical address, so the rows of one boot must be read with that boot's <code>map-homes.txt</code>.</li>
<li>The classification probed {AMBIG[1]}, {AMBIG[2]} and {AMBIG[3]} lines a second time (boots 1, 2, 3). The "unused" lines of the table are those that stayed unclassified.</li>
<li>The state of each boot is taken from Jesse's README: firmware versions and register values for boots 1 and 2, and no register value for boot 3 [Ref5]. The counters of section 3 agree with the stated states.</li>
</ul>

<h2>2. The three boots side by side</h2>
<p>One dot is one cell of CPUs 2 to 9 (40 cells per row). The position is the best ns per load. Hover a dot for the cell.</p>
<p class="key">{key}</p>
{strip()}
<p class="take">Flushed OCM lines read the same on boots 1 and 2. The evicted kinds (<code>ocm-evict</code>, <code>slc</code>) move from 21.5-29.7 ns to 13-17 ns when the L3 is in use. With the prefetchers on, the two flushed kinds drop again, and the evicted kinds do not.</p>
<h3>Linear fit of the best values: ns = base + X cost x X steps + Y cost x Y steps</h3>
<div class="scroll"><table class="num"><thead><tr><th>Boot</th><th>Kind</th><th>Range, ns</th><th>Base, ns</th><th>Per X step, ns</th><th>Per Y step, ns</th><th>rms, ns</th><th>Largest error, ns</th></tr></thead><tbody>{fit_rows}</tbody></table></div>
<ul>
<li>A row is a distance map where two things hold: every load left the cluster (section 3), and the fit has about 2 ns per X step and 1 ns per Y step. That is the three cache kinds of boot 1 and <code>ocm-flush</code> of boot 2 [Ref2].</li>
<li><code>dram-flush</code> on boots 1 and 2 fits a different path (section 4, a hypothesis).</li>
<li>Boot 3 against boot 2, best values: <code>ocm-flush</code> is lower in 40 of 40 cells and <code>dram-flush</code> in 40 of 40. <code>slc</code> is higher in {sum(x > 0 for x in d32['slc'])} of 40 cells and <code>ocm-evict</code> in {sum(x > 0 for x in d32['ocm-evict'])} of 40.</li>
</ul>

<h2>3. What the counters say about each row</h2>
<div class="scroll"><table class="num"><thead><tr><th>Boot</th><th>Kind</th><th><code>l3d_refill_rd</code> per load: lowest / median / highest of 280 rows</th><th><code>l2d_refill_hwprf</code> per load: lowest / median / highest</th><th><code>mc_reqs</code> per load, cell medians</th></tr></thead><tbody>{cnt_rows}</tbody></table></div>
<ul>
<li><b>Boot 1:</b> every load left the cluster (1.00 per load), in all four kinds.</li>
<li><b>Boot 2, flushed kinds:</b> every load left the cluster (1.00 per load).</li>
<li><b>Boot 2, evicted kinds:</b> only about 0.3 of the loads left the cluster. The L1 and L2 refill columns read 1.00 per load in these rows, so the other loads were not L1 or L2 hits. They were served by the L3 or by the partner CPU's cache. No L3 hit counter was read in this run, so the split is not measured.</li>
<li><b>Boot 3:</b> the prefetcher columns are nonzero in {B[3].hw(False)} of the 1,120 rows of CPUs 2 to 9. They are zero in all 1,120 rows on boot 1 and on boot 2. On boot 3 the counter <code>l3d_refill_rd</code> misses lines that a prefetch fetched, so it is no longer the share of lines that came from outside.</li>
<li><b><code>slc</code> rows almost never went to memory on any boot:</b> <code>mc_reqs</code> is at most {max(rng(b, 'slc', lambda k, c, n: B[b].med(k, c, n, 'mc_reqs'))[1] for b in B):.4f} per load as a cell median and at most {slc_mc_row_max:.4f} per load in a single row, against 1.00 per load for <code>dram-flush</code>.</li>
</ul>
<h3>Requests at the home nodes</h3>
<p>Each entry is: requests per load at the cell's own node / mean requests per load at each of the other four nodes (medians over 280 rows).</p>
<table class="num"><thead><tr><th>Kind</th><th>Boot 1</th><th>Boot 2</th><th>Boot 3</th></tr></thead><tbody>{own_rows}</tbody></table>
<ul>
<li>On boots 2 and 3 the own-node requests of the evicted kinds follow the share of loads that left the cluster.</li>
<li>On boot 1 the evicted kinds send about 1.5 requests per load to the cell's own node and about 0.25 to each other node. That is more than the one request per load of the chain. Hypothesis: without an L3, lines that leave the L2 during the pass go to the mesh. Not tested.</li>
<li>On boot 3, <code>dram-flush</code> still sends about one request per load to the cell's own node and almost none to the other nodes. So the prefetches fetch the chain's own lines, not their address neighbours (which belong to other nodes).</li>
</ul>

<h2>4. Boot 2: the flushed kinds repeat boot 1</h2>
<ul>
<li><b><code>ocm-flush</code>:</b> boot 2 minus boot 1 is {d21['ocm-flush'][0]:+.2f} ns on average over 40 cells (range {d21['ocm-flush'][1]:+.2f} to {d21['ocm-flush'][2]:+.2f} ns). The fit of the best values is {FIT[(2, 'ocm-flush')][0][0]:.2f} ns + {FIT[(2, 'ocm-flush')][0][1]:.2f} ns per X step + {FIT[(2, 'ocm-flush')][0][2]:.2f} ns per Y step.</li>
<li><b>The medians of boot 2's <code>ocm-flush</code> cells fit with the smallest error of any row so far:</b> {medfit2[0][0]:.2f} ns + {medfit2[0][1]:.2f} ns per X step + {medfit2[0][2]:.2f} ns per Y step, rms {medfit2[1]:.2f} ns over 40 cells. At 2 cycles per ns that is 4 cycles per X step and 2 cycles per Y step, for the request and the data together.</li>
<li>The base of the median fit is 0.19 ns above the base of the best fit. A few cells have one pass that reads about 0.5 ns below the others, and the best value takes that pass.</li>
<li><b><code>dram-flush</code>:</b> boot 2 is {d21['dram-flush'][0]:+.2f} ns above boot 1 in every cell (range {d21['dram-flush'][1]:+.2f} to {d21['dram-flush'][2]:+.2f} ns). The offset does not depend on the CPU or the node.</li>
<li><b>The three-leg memory path of boot 1 fits boot 2 equally well</b>, with the same memory point and the same costs:</li>
</ul>
<table class="num"><thead><tr><th>Boot</th><th>Best memory point</th><th>Base at (0,3), ns</th><th>Per X crossing, ns</th><th>Per Y crossing, ns</th><th>rms, ns</th></tr></thead><tbody>{tri_rows}</tbody></table>
<ul>
<li>The path is: CPU to home node, home node to a memory point, memory point directly to the CPU. A crossing is one link between two crosspoints on that path.</li>
<li>The two points fit equally by construction. No CPU or home node is left of column 1, so the data fix the row (y = 3) and say only that the point is at or left of column 1. The mesh map of an earlier boot shows a memory bridge at (0,3) [Ref7].</li>
<li>The row y = 3 is preferred by rms {TRI[1][0][0]:.3f} ns against {TRI[1][2][0]:.3f} ns for the next row (boot 1), and {TRI[2][0][0]:.3f} against {TRI[2][2][0]:.3f} ns (boot 2).</li>
<li>The path stays a hypothesis about routing. Each boot measured one 2 MiB page, and two pages now agree.</li>
</ul>
<h3>The +{d21['dram-flush'][0]:.2f} ns of <code>dram-flush</code> on boot 2</h3>
<p>Boot 3 has the L3 in use too, on a third page. In {len(noprf)} of its <code>dram-flush</code> passes the prefetcher made no L2 fill. Those passes are a sample of a plain memory load on boot 3:</p>
<table class="num"><thead><tr><th>Cell</th><th>Boot 3 passes with no prefetch fill, ns</th><th>Boot 1 median, ns</th><th>Boot 2 median, ns</th></tr></thead><tbody>{noprf_rows}</tbody></table>
<p class="sub">Four of the five cells read boot 1's value and one reads boot 2's. So an L3 in use does not by itself add the 0.6 ns. The cause is Insufficient data: a repeat of boot 2, or a run on a fourth page, would show whether the offset follows the boot or the page.</p>

<h2>5. Boot 2: <code>slc</code> and <code>ocm-evict</code> mix cluster hits and mesh loads</h2>
<p>Each dot is one timed pass of one cell (560 passes). The horizontal position is the share of the pass's loads that left the cluster. The dashed lines are the fitted model for the nearest and the farthest node.</p>
{scatter()}
<p class="take">Passes with a larger share of mesh loads are slower, and far nodes (dark) rise faster than near nodes (light). Extended to a share of 0, the model gives the cost of a load that stays in the cluster: about {a_est:.1f} ns est.</p>
<p>The model is: ns per load = cluster cost x (1 - share) + share x (mesh base + cost per unit x units of distance + step for passes 4 to 6). All four numbers are fitted, so they are estimates. No pass has a share below 0.21.</p>
<div class="scroll"><table class="num"><thead><tr><th>Boot</th><th>Kind</th><th>Cluster cost, ns est.</th><th>Mesh base, ns est.</th><th>Per unit of distance, ns est.</th><th>Step for passes 4 to 6, ns est.</th><th>rms over 280 passes, ns</th></tr></thead><tbody>{mix2_rows}</tbody></table></div>
<ul>
<li><b>The mesh part keeps boot 1's slope and boot 1's pass step.</b> The cost per unit is {MIX2[(2, 'ocm-evict')][0][2]:.2f} and {MIX2[(2, 'slc')][0][2]:.2f} ns on boot 2 against {MIX2[(1, 'ocm-evict')][0][2]:.2f} and {MIX2[(1, 'slc')][0][2]:.2f} ns on boot 1. The step for passes 4 to 6 is about 1.3 ns in every row of the table, and it applies to the mesh loads only.</li>
<li><b>The mesh base is {MIX2[(2, 'ocm-evict')][0][1] - MIX2[(1, 'ocm-evict')][0][1]:.1f} to {MIX2[(2, 'slc')][0][1] - MIX2[(1, 'slc')][0][1]:.1f} ns above boot 1's</b> ({MIX2[(2, 'ocm-evict')][0][1]:.1f} and {MIX2[(2, 'slc')][0][1]:.1f} ns against {MIX2[(1, 'ocm-evict')][0][1]:.1f} and {MIX2[(1, 'slc')][0][1]:.1f} ns). Insufficient data on the cause.</li>
<li><b>Consequence:</b> the best values of these two kinds on boot 2 ({rng(2, 'ocm-evict')[0]:.1f} to {rng(2, 'slc')[1]:.1f} ns) are averages of two paths. They are not the cost of a load from a slice. Boot 1 remains the distance map for the slice.</li>
<li><b>The cluster cost of about {a_est:.1f} ns est. is not a measured L3 latency.</b> The project README quotes 6.1 ns for a core load from the L3, from another test program [Ref8]. The difference is not explained. The L3 hit counter set (<code>--events l3</code>) on one cell would test it.</li>
<li><b>The <code>ocm-flush</code>, <code>ocm-evict</code> and <code>slc</code> rows of boot 3 follow the same model.</b> For <code>ocm-flush</code> the "cluster cost" is mostly the cost of a load whose line a prefetch fetched. The <code>dram-flush</code> rows of boot 3 do not fit this model (rms 1.3 ns), so they are not in the table.</li>
<li><code>slc</code> minus <code>ocm-evict</code> is {np.mean(se[2]):+.2f} ns on boot 2 (range {min(se[2]):+.2f} to {max(se[2]):+.2f} ns) against {np.mean(se[1]):+.3f} ns on boot 1. The <code>slc</code> rows have a larger share of mesh loads (median 0.32 against 0.29).</li>
</ul>
<h3>The share falls pass by pass in the first cells of a cluster</h3>
<p>Within one kind the program measures CPUs 2, 4, 6, 8 first, each starting at node 88, then CPUs 3, 5, 7, 9. Cell medians of the share:</p>
<table class="num"><thead><tr><th>Boot</th><th>Kind</th><th>Share at node 88, CPUs 2, 4, 6, 8</th><th>Share at node 88, CPUs 3, 5, 7, 9</th><th>Share in all other cells: median (range)</th></tr></thead><tbody>{first_rows}</tbody></table>
<p>Pass by pass, for some of these cells:</p>
<div class="scroll"><table class="num"><thead><tr><th>Boot</th><th>Kind</th><th>Cell</th><th>Share, passes 0 to 6</th><th>ns per load, passes 0 to 6</th></tr></thead><tbody>{trans_rows}</tbody></table></div>
<ul>
<li><b>In the first passes the evictor works as designed.</b> Nearly every load leaves the cluster (share 0.98), and the cell reads a mesh value: 23.5 ns for CPU 2 to node 88 on boot 2.</li>
<li><b>Then the share falls to about 0.35 within a few passes</b>, and stays there for the later cells of that cluster. On boot 3 the fall takes longer and reaches into the second node.</li>
<li><b>The second CPU of a cluster never shows it.</b> CPUs 3, 5, 7, 9 measure the same lines of node 88 with a share of 0.29 to 0.37. So the effect belongs to the cluster's first cells of a kind, not to node 88.</li>
<li><b>CPU 0 shows it on all three boots</b> (last row of the table), since its cluster has its L3 in use on every boot.</li>
</ul>
<div class="hyp"><b>Hypothesis: the cluster keeps the chain lines once it has seen the store-then-evict cycle several times.</b> The evictor is not too small: it loads 30,720 lines (1.875 MiB), 7.5 times the 256 KiB L3 that the project README gives, after one store to every chain line [Ref8]. A fixed rule (for example "dirty lines stay, clean lines go") does not fit, since the first passes of a cluster do evict the chain lines. Something in the cluster changes over about 5 to 10 cycles. What changes is not measured. The test: one boot 2 cell under the L3 hit counter set (<code>--events l3</code>), and one cell whose evictor stores to its lines.</div>

<h2>6. Boot 3: the prefetcher acts on the flushed kinds</h2>
<ul>
<li><b><code>ocm-flush</code>: {rng(3, 'ocm-flush')[0]:.1f} to {rng(3, 'ocm-flush')[1]:.1f} ns</b>, against {rng(2, 'ocm-flush')[0]:.1f} to {rng(2, 'ocm-flush')[1]:.1f} ns on boot 2. The prefetcher made {rrng(3, 'ocm-flush', 'l2d_refill_hwprf')[1]:.2f} L2 fills per load (median), and demand refills from outside the cluster fell to {rrng(3, 'ocm-flush', 'l3d_refill_rd')[1]:.2f} per load.</li>
<li><b><code>dram-flush</code>: {rng(3, 'dram-flush')[0]:.1f} to {rng(3, 'dram-flush')[1]:.1f} ns best</b>, against {rng(2, 'dram-flush')[0]:.1f} to {rng(2, 'dram-flush')[1]:.1f} ns on boot 2. The best value is not a stable number here: the passes of one cell differ by {dram3_spread[0]:.1f} to {dram3_spread[1]:.1f} ns, and the cell medians span {dmed3[0]:.1f} to {dmed3[1]:.1f} ns. In some cells the prefetch fills stop after two passes, and the later passes read boot 1's value (section 4).</li>
<li><b>The evicted kinds are boot 2's mix again.</b> In the <code>slc</code> rows the prefetch columns have a median of 0.00 per load. The slow <code>slc</code> and <code>ocm-evict</code> cells of boot 3 (up to {rng(3, 'slc')[1]:.1f} ns) are first cells of a cluster (section 5), not a prefetcher effect.</li>
<li><b>The chain is a dependent chain in a new random order each pass, yet the prefetcher helps.</b> The request counts of section 3 show that the prefetches go to the chain's own lines. Hypothesis: the prefetcher replays the set of lines that earlier passes touched in the region. The test: one cell whose line set changes between passes.</li>
<li><b>The four control rows read 15.6 to 19.6 ns where the map's cells read 12.6 to 15.4 ns</b> (section 8). The control chain has 4,096 lines of the whole region and the map's chain 2,048 lines. Whether that explains the difference is not tested.</li>
</ul>

<h2>7. CPU 0 cells</h2>
<p>Jesse ran all three boots with the option <code>--kernel-cpus</code>, which adds 20 cells from CPU 0. By Jesse's README, CPU 0's cluster keeps its L3 in use and its prefetchers on at every boot [Ref5]. The files agree: the prefetch columns are nonzero in {B[1].hw(True)}, {B[2].hw(True)} and {B[3].hw(True)} of CPU 0's 140 rows.</p>
<table class="num"><thead><tr><th>Kind</th><th>Boot 1, best ns over 5 nodes</th><th>Boot 2</th><th>Boot 3</th></tr></thead><tbody>{cpu0_rows}</tbody></table>
<ul>
<li>CPU 0's cells read in the same ranges on the three boots. For one node the best value differs by up to 0.5 ns (<code>ocm-flush</code>) and up to 3.2 ns (<code>dram-flush</code>) between boots.</li>
<li>CPU 0's flushed kinds match CPUs 2 to 9 only on boot 3. Its evicted kinds match CPUs 2 to 9 on boots 2 and 3.</li>
<li>CPU 0's cells are not distance numbers on any boot.</li>
</ul>

<h2>8. Other checks</h2>
<h3>Control rows against the map's <code>ocm-flush</code> cells</h3>
<p>The largest difference is {ctl_max[1]:.2f} ns on boot 1, {ctl_max[2]:.2f} ns on boot 2 and {ctl_max[3]:.2f} ns on boot 3 [Ref4].</p>
<div class="scroll"><table class="num"><thead><tr><th>Boot</th><th>CPU</th><th>Node</th><th><code>latency</code> best, ns</th><th><code>meshmap</code> best, ns</th><th>Difference, ns</th></tr></thead><tbody>{ctl_rows}</tbody></table></div>
<ul>
<li>A control row is the smaller of 2 timed passes over 4,096 lines. A map cell is the smallest of 7 passes over 2,048 lines. The two do not use the same lines.</li>
<li>On boot 2 the differences are -0.78 to +0.41 ns, larger than on boot 1. Insufficient data on the cause. Jesse's README notes that the OCM mappings have a different alignment on each boot and for each control [Ref5].</li>
<li>Our files confirm the TLB column of that note. <code>l1d_tlb_refill</code> per load in <code>ocm-flush</code> cells is {tlb[1][0]:.4f} in all 40 cells of boot 1 and {tlb[2][0]:.4f} in all 40 cells of boot 2. On boot 3 it is {tlb3[88][0]:.4f} at nodes 88, 160, 216 and {tlb3[344][0]:.4f} at nodes 288, 344.</li>
<li>Boots 1 and 2 differ in that column, and their <code>ocm-flush</code> cells differ by +0.05 ns on average. So the alignment changes the map by little, if at all.</li>
</ul>
<h3>Passes 4 to 6 against passes 0 to 3</h3>
<p>Pass r reads byte 8 x r of each line, so passes 4 to 6 read the upper 32 bytes. The table gives the mean of passes 4 to 6 minus the mean of passes 0 to 3, in ns, as mean (range) over 40 cells.</p>
<div class="scroll"><table class="num"><thead><tr><th>Kind</th><th>Boot 1</th><th>Boot 2</th><th>Boot 3</th></tr></thead><tbody>{step_rows}</tbody></table></div>
<ul>
<li>The step of about 1.3 ns appears wherever every load comes over the mesh from a cache or the OCM (boot 1's three cache kinds, boot 2's <code>ocm-flush</code>). It is absent in <code>dram-flush</code> on boots 1 and 2.</li>
<li>In the mixed rows this table also contains the falling share of section 5. The model of section 5 separates the two and finds the same 1.3 ns per mesh load.</li>
</ul>
<h3>Single rows that stand out</h3>
<ul>
<li>Boot 1, <code>ocm-evict</code>, CPU 9 to node 160, pass 4: 32.69 ns against about 30.0 ns in the other passes, with fewer cycles per ns than every other row. The pass was probably interrupted.</li>
<li>Boot 1, <code>ocm-evict</code>, CPU 6 to node 344, pass 5: <code>mc_reqs</code> 0.45 per load, and requests raised at all five nodes. The ns value is normal. Other traffic was in the counter window.</li>
<li>No such row sets a best value.</li>
</ul>

<h2>9. Exact numbers</h2>
<p>Boot 1's tables are on the boot 1 page. CPU 0's row is in italics.</p>
{exact}
<details><summary>Boot 2, share of loads that left the cluster (cell medians of <code>l3d_refill_rd</code>)</summary><div class="two"><div><h4><code>ocm-evict</code></h4>{ftable(2, 'ocm-evict', 'l3d_refill_rd')}</div><div><h4><code>slc</code></h4>{ftable(2, 'slc', 'l3d_refill_rd')}</div></div></details>

<h2>10. Not explained, not verified</h2>
<ul>
<li><b>Why the cluster keeps about 70% of the chain lines after the first passes</b> (section 5). Hypothesis and test are stated there.</li>
<li><b>The cluster cost of {a_est:.1f} ns est. against the 6.1 ns L3 latency of the README</b> (section 5). Insufficient data.</li>
<li><b>The +{d21['dram-flush'][0]:.2f} ns of <code>dram-flush</code> on boot 2</b> (section 4). Insufficient data.</li>
<li><b>The mesh base of the mix model, 0.5 to 1.0 ns above boot 1's</b> (section 5). Insufficient data.</li>
<li><b>Which lines the prefetcher fetches on boot 3</b> (section 6). Hypothesis and test are stated there.</li>
<li><b>Open since boot 1:</b> the pass 4 to 6 step, <code>ocm-flush</code> reading above <code>ocm-evict</code> on boot 1, and the Y cost of the memory path (0.31 to 0.32 ns against 0.49 ns per crossing in the cache kinds).</li>
<li><b>Not verified:</b> Jesse's README statements on the kernel's reads of the mesh counters, the mapping alignments, the register values and the script's chip seconds. The console logs are not in our copy.</li>
</ul>

<h2>References</h2>
<ul>
<li>[Ref1] <code>results/membench-jibin-014/SHA256SUMS</code>, <code>results/membench-jibin-015/SHA256SUMS</code>, <code>results/membench-jibin-016/SHA256SUMS</code>: 11 of 11 OK each.</li>
<li>[Ref2] <code>results/membench-jibin-01{{4,5,6}}/results/bootM{{1,2,3}}/latency-map.csv</code> and <code>meshmap-log.txt</code>.</li>
<li>[Ref3] <code>map-homes.txt</code> in the same three folders, and the <code># classify</code> and <code># pagemap</code> lines of [Ref2].</li>
<li>[Ref4] <code>latency-ocm-region{{0,4}}-mapctl-cpu{{2,8}}.csv</code> in the same three folders.</li>
<li>[Ref5] <code>README.md</code> in the three folders, written by Jesse's agent. Statements taken from them are marked.</li>
<li>[Ref6] Arm CMN S3 Technical Reference Manual 107858_0203_05, section 2.4.5.3, page 142 (the hash for a target count that is not a power of two).</li>
<li>[Ref7] <code>run8-meshmap-boot1.html</code> and <code>gen_run8_report.py</code>: the trial run and boot 1 in full, with the mesh map of folder 011. This page is written by <code>gen_run8_boots.py</code>.</li>
<li>[Ref8] <code>meshmap.c</code> lines 21 to 36 and 1098 to 1136 (the evictor and the per-pass recipe), and <code>README.md</code> lines 33, 151 to 156 and 268, commit 3b12e4f.</li>
</ul>
</main></body></html>"""

open(OUT, 'w').write(page)
print('wrote', OUT, len(page), 'bytes')
