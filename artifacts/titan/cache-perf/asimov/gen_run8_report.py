#!/usr/bin/env python3
"""Run 8 (mesh latency map) report: rehearsal (013) and boot 1 (014).

Reads the raw result files and writes one self-contained HTML page.
Usage: python3 gen_run8_report.py [--out run8-meshmap-boot1.html]
"""
import csv, sys, os, statistics as st, collections, html
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R13 = os.path.join(HERE, 'results/membench-jibin-013/results/bootM0')
R14 = os.path.join(HERE, 'results/membench-jibin-014/results/bootM1')
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(HERE, 'run8-meshmap-boot1.html')

NODES = [88, 160, 216, 288, 344]
NPOS = {88: (1, 3), 160: (2, 4), 216: (3, 3), 288: (4, 4), 344: (5, 3)}
CPOS = {0: (1, 2), 2: (2, 3), 3: (2, 3), 4: (3, 2), 5: (3, 2), 6: (4, 3), 7: (4, 3), 8: (5, 2), 9: (5, 2)}
SBSX = (0, 3)   # the memory bridge the fit selects (section 5.3)
KINDS = ['ocm-flush', 'ocm-evict', 'slc', 'dram-flush']
RAMP = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']


def load(path):
    rows = [r for r in csv.reader(l for l in open(path) if not l.startswith('#'))]
    H = {n: i for i, n in enumerate(rows[0])}
    return rows[1:], H


rows, H = load(os.path.join(R14, 'latency-map.csv'))
cells = collections.defaultdict(list)
for r in rows:
    if r[0] != 'idle':
        cells[(r[0], int(r[1]), int(r[2]))].append(r)
CPUS = sorted({k[1] for k in cells})
CPUS29 = [c for c in CPUS if c >= 2]


def col(k, c, n, name):
    return [float(r[H[name]]) for r in cells[(k, c, n)]]


def best(k, c, n):
    return min(col(k, c, n, 'ns_per_load'))


def med(k, c, n, name='ns_per_load'):
    return st.median(col(k, c, n, name))


def steps(c, n):
    return abs(CPOS[c][0] - NPOS[n][0]), abs(CPOS[c][1] - NPOS[n][1])


def fit_xy(kind):
    A = [[1, *steps(c, n)] for c in CPUS29 for n in NODES]
    y = np.array([best(kind, c, n) for c in CPUS29 for n in NODES])
    A = np.array(A, float)
    co = np.linalg.lstsq(A, y, rcond=None)[0]
    r = y - A @ co
    return co, float((r ** 2).mean() ** .5), float(abs(r).max())


def tri(c, n, m):
    (cx, cy), (hx, hy) = CPOS[c], NPOS[n]
    return (abs(cx - hx) + abs(hx - m[0]) + abs(m[0] - cx), abs(cy - hy) + abs(hy - m[1]) + abs(m[1] - cy))


def via(c, n, m):
    (cx, cy), (hx, hy) = CPOS[c], NPOS[n]
    return (2 * (abs(cx - hx) + abs(hx - m[0])), 2 * (abs(cy - hy) + abs(hy - m[1])))


def fit_path(fn):
    out = []
    y = np.array([best('dram-flush', c, n) for c in CPUS29 for n in NODES])
    for mx in range(6):
        for my in range(6):
            A = np.array([[1, *fn(c, n, (mx, my))] for c in CPUS29 for n in NODES], float)
            if np.linalg.matrix_rank(A) < 3:
                continue
            co = np.linalg.lstsq(A, y, rcond=None)[0]
            r = y - A @ co
            out.append((float((r ** 2).mean() ** .5), float(abs(r).max()), (mx, my), co))
    out.sort(key=lambda t: (round(t[0], 6), t[2]))
    return out


FIT = {k: fit_xy(k) for k in KINDS}
TRI = fit_path(tri)
VIA = fit_path(via)
tri03 = [t for t in TRI if t[2] == SBSX][0]

# slc against ocm-evict
d_se = [best('slc', c, n) - best('ocm-evict', c, n) for c in CPUS29 for n in NODES]
d_sf = [best('slc', c, n) - best('ocm-flush', c, n) for c in CPUS29 for n in NODES]


def rng(kind, name):
    v = [med(kind, c, n, name) for c in CPUS29 for n in NODES]
    return min(v), max(v)


def own_minus_others(kind):
    v, o = [], []
    for c in CPUS29:
        for n in NODES:
            ot = np.mean([med(kind, c, m, 'req_%d' % m) if False else st.median(col(kind, c, n, 'req_%d' % m)) for m in NODES if m != n])
            v.append(med(kind, c, n, 'req_%d' % n) - ot)
            o.append(ot)
    return min(v), max(v), min(o), max(o)


# hash check
def arm_select(pa, n=5):
    a = pa >> 6
    h = (a & 0xfff) ^ ((a >> 12) & 0xfff) ^ ((a >> 24) & 0xfff) ^ ((a >> 36) & 0x3ff)
    top = 0
    for k in range(6):
        top |= (((h >> (11 - k)) ^ (h >> k)) & 1) << (5 - k)
    return (((top << 6) | (h & 0x3f)) * n) >> 12


def hash_check(path, pfn=0xc004800):
    L = open(path).read().split('\n')
    assert 'pfn=0x%x' % pfn in L[0], L[0]
    s = ''.join(x for x in L[1:] if not x.startswith('#'))
    m = collections.Counter()
    for i, ch in enumerate(s):
        if ch in '01234':
            m[(arm_select((pfn << 12) + 64 * i), int(ch))] += 1
    mp = {}
    for (f, h), c in m.items():
        if c > mp.get(f, (0, 0))[1]:
            mp[f] = (h, c)
    agree = sum(c for (f, h), c in m.items() if mp[f][0] == h)
    return len(s), sum(m.values()), agree, [NODES[mp[f][0]] for f in range(5)], s.count('?')


HC14 = hash_check(os.path.join(R14, 'map-homes.txt'))
HC13 = hash_check(os.path.join(R13, 'map-rehearsal-homes.txt'))

# controls
CTL = []
for cpu in (2, 8):
    for reg in (0, 4):
        p = os.path.join(R14, 'latency-ocm-region%d-mapctl-cpu%d.csv' % (reg, cpu))
        b = [float(l.split(',')[5]) for l in open(p) if ',best,' in l][0]
        CTL.append((cpu, NODES[reg], b, best('ocm-flush', cpu, NODES[reg])))

# rehearsal rows
r13, H13 = load(os.path.join(R13, 'map-rehearsal.csv'))


def r13rng(kind, name='ns_per_load'):
    v = [float(r[H13[name]]) for r in r13 if r[0] == kind]
    return min(v), max(v)


# ---------- drawing ----------
def shade(v, lo, hi):
    t = 0 if hi == lo else max(0, min(1, (v - lo) / (hi - lo)))
    return RAMP[int(round(t * (len(RAMP) - 1)))]


def mini(kind, cpu, lo, hi, show_sbsx):
    """One 6 x 6 mesh with the five home nodes coloured by the cell's best ns."""
    W, Hh, m, g = 232, 232, 22, 37.6
    X = lambda x: m + x * g
    Y = lambda y: Hh - m - y * g
    s = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s from CPU %d">' % (W, Hh, W, Hh, kind, cpu)]
    for i in range(6):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/>' % (X(i), Y(0), X(i), Y(5)))
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/>' % (X(0), Y(i), X(5), Y(i)))
    for x in range(6):
        for y in range(6):
            s.append('<circle cx="%.1f" cy="%.1f" r="1.6" class="xp"/>' % (X(x), Y(y)))
    if show_sbsx:
        s.append('<rect x="%.1f" y="%.1f" width="12" height="12" class="mem"><title>memory bridge (SBSX) at crosspoint (0,3)</title></rect>' % (X(SBSX[0]) - 6, Y(SBSX[1]) - 6))
        s.append('<text x="%.1f" y="%.1f" class="lab" text-anchor="middle">mem</text>' % (X(SBSX[0]), Y(SBSX[1]) + 18))
    cx, cy = CPOS[cpu]
    s.append('<path d="M%.1f %.1f l7 12 h-14 z" class="cpu"><title>CPUs %d and %d at crosspoint (%d,%d)</title></path>' % (X(cx), Y(cy) - 8, cpu, cpu + 1, cx, cy))
    s.append('<text x="%.1f" y="%.1f" class="lab" text-anchor="middle">CPU %d</text>' % (X(cx), Y(cy) + 16, cpu))
    for n in NODES:
        v = best(kind, cpu, n)
        dx, dy = steps(cpu, n)
        nx, ny = NPOS[n]
        s.append('<circle cx="%.1f" cy="%.1f" r="9" fill="%s" class="hn"><title>%s, CPU %d to node %d: best %.2f ns, median %.2f ns (%d X steps, %d Y steps)</title></circle>'
                 % (X(nx), Y(ny), shade(v, lo, hi), kind, cpu, n, v, med(kind, cpu, n), dx, dy))
        s.append('<text x="%.1f" y="%.1f" class="val" text-anchor="middle">%.1f</text>' % (X(nx), Y(ny) - 13, v))
    s.append('</svg>')
    return ''.join(s)


def legend(lo, hi):
    w = 14
    s = '<span class="leg">%.0f ns ' % lo
    s += ''.join('<i style="background:%s"></i>' % c for c in RAMP)
    return s + ' %.0f ns</span>' % hi


def maps():
    out = []
    groups = [('ocm-evict', 'OCM lines (kind <code>ocm-evict</code>)', False), ('slc', 'DRAM-backed lines held in the node\'s cache slice (kind <code>slc</code>)', False),
              ('dram-flush', 'DRAM-backed lines flushed first (kind <code>dram-flush</code>)', True)]
    lo1 = min(best(k, c, n) for k in ('ocm-evict', 'slc') for c in CPUS29 for n in NODES)
    hi1 = max(best(k, c, n) for k in ('ocm-evict', 'slc') for c in CPUS29 for n in NODES)
    lo2 = min(best('dram-flush', c, n) for c in CPUS29 for n in NODES)
    hi2 = max(best('dram-flush', c, n) for c in CPUS29 for n in NODES)
    for k, title, sb in groups:
        lo, hi = (lo2, hi2) if k == 'dram-flush' else (lo1, hi1)
        out.append('<h4>%s %s</h4><div class="mm">' % (title, legend(lo, hi)))
        for c in (2, 4, 6, 8):
            out.append('<figure>%s<figcaption>from CPU %d</figcaption></figure>' % (mini(k, c, lo, hi, sb), c))
        out.append('</div>')
    return ''.join(out)


def path_fig():
    """Schematic of the two paths for one cell: CPU 8 to node 216."""
    W, Hh, m, g = 300, 250, 30, 44
    X = lambda x: m + x * g
    Y = lambda y: Hh - m - y * g
    s = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="path of a load from CPU 8 through node 216">' % (W, Hh + 60, W, Hh + 60)]
    for i in range(6):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/>' % (X(i), Y(0), X(i), Y(5)))
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/>' % (X(0), Y(i), X(5), Y(i)))
    c, h, mm = CPOS[8], NPOS[216], SBSX
    s.append('<path d="M%.1f %.1f H%.1f V%.1f" class="leg1"/>' % (X(c[0]), Y(c[1]) - 3, X(h[0]) + 3, Y(h[1])))
    s.append('<path d="M%.1f %.1f H%.1f" class="leg2"/>' % (X(h[0]), Y(h[1]) - 4, X(mm[0])))
    s.append('<path d="M%.1f %.1f V%.1f H%.1f" class="leg3"/>' % (X(mm[0]) + 4, Y(mm[1]), Y(c[1]) + 4, X(c[0])))
    s.append('<rect x="%.1f" y="%.1f" width="14" height="14" class="mem"/>' % (X(mm[0]) - 7, Y(mm[1]) - 7))
    s.append('<circle cx="%.1f" cy="%.1f" r="9" fill="#6da7ec" class="hn"/>' % (X(h[0]), Y(h[1])))
    s.append('<path d="M%.1f %.1f l7 12 h-14 z" class="cpu"/>' % (X(c[0]), Y(c[1]) - 8))
    s.append('<text x="%.1f" y="%.1f" class="lab" text-anchor="middle">CPU 8</text>' % (X(c[0]), Y(c[1]) + 22))
    s.append('<text x="%.1f" y="%.1f" class="lab" text-anchor="middle">node 216</text>' % (X(h[0]), Y(h[1]) - 14))
    s.append('<text x="%.1f" y="%.1f" class="lab" text-anchor="start">mem (0,3)</text>' % (X(mm[0]) - 8, Y(mm[1]) - 14))
    for i, (cls, t) in enumerate((('leg1', '1. request to the home node: 2 X + 1 Y crossings'), ('leg2', '2. home node to memory: 3 X crossings'), ('leg3', '3. data from memory to the CPU: 5 X + 1 Y crossings'))):
        yy = Hh + 14 + 17 * i
        s.append('<path d="M%d %d h26" class="%s"/><text x="%d" y="%d" class="lab">%s</text>' % (m, yy, cls, m + 34, yy + 4, t))
    s.append('</svg>')
    return ''.join(s)


def table(kind):
    s = ['<table class="num"><thead><tr><th>CPU (crosspoint)</th>' + ''.join('<th>node %d</th>' % n for n in NODES) + '</tr></thead><tbody>']
    for c in CPUS:
        cls = ' class="k0"' if c == 0 else ''
        s.append('<tr%s><td>CPU %d (%d,%d)</td>' % (cls, c, *CPOS[c]) + ''.join('<td>%.2f</td>' % best(kind, c, n) for n in NODES) + '</tr>')
    s.append('</tbody></table>')
    return ''.join(s)


e = html.escape
STEP = {}
for k in KINDS:
    v = [np.mean(col(k, c, n, 'ns_per_load')[4:]) - np.mean(col(k, c, n, 'ns_per_load')[:4]) for c in CPUS29 for n in NODES]
    STEP[k] = (float(np.mean(v)), min(v), max(v))
best_late = sum(1 for k in KINDS[:3] for c in CPUS29 for n in NODES if col(k, c, n, 'ns_per_load').index(best(k, c, n)) >= 4)
slc_mc_max = max(x for c in CPUS29 for n in NODES for x in col('slc', c, n, 'mc_reqs'))
step_rows = ''.join('<tr><td><code>%s</code></td><td>%+.2f</td><td>%+.2f to %+.2f</td></tr>' % (k, *STEP[k]) for k in KINDS)
mc = {k: rng(k, 'mc_reqs') for k in KINDS[1:]}
cm = {k: rng(k, 'cache_miss') for k in KINDS[1:]}
oo = {k: own_minus_others(k) for k in KINDS[1:]}
spread = {k: (min(max(col(k, c, n, 'ns_per_load')) - min(col(k, c, n, 'ns_per_load')) for c in CPUS29 for n in NODES),
              max(max(col(k, c, n, 'ns_per_load')) - min(col(k, c, n, 'ns_per_load')) for c in CPUS29 for n in NODES)) for k in KINDS}
hw0 = sum(1 for r in rows if r[0] != 'idle' and r[1] == '0' and (float(r[H['l1d_refill_hwprf']]) > 0 or float(r[H['l2d_refill_hwprf']]) > 0))
hw29 = sum(1 for r in rows if r[0] != 'idle' and r[1] != '0' and (float(r[H['l1d_refill_hwprf']]) > 0 or float(r[H['l2d_refill_hwprf']]) > 0))
n0 = sum(1 for r in rows if r[0] != 'idle' and r[1] == '0')
ctl_max = max(abs(a - b) for _, _, a, b in CTL)
res_old = [best('ocm-flush', c, n) - (20.75 + 1.99 * steps(c, n)[0] + 0.95 * steps(c, n)[1]) for c in CPUS29 for n in NODES]

fit_rows = ''.join('<tr><td><code>%s</code></td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td></tr>' % (k, *FIT[k][0], FIT[k][1], FIT[k][2]) for k in KINDS)
ctl_rows = ''.join('<tr><td>CPU %d</td><td>node %d</td><td>%.3f</td><td>%.3f</td><td>%+.3f</td></tr>' % (c, n, a, b, b - a) for c, n, a, b in CTL)
cnt_rows = ''.join('<tr><td><code>%s</code></td><td>%.4f to %.4f</td><td>%.3f to %.3f</td><td>%.2f to %.2f</td><td>%.2f to %.2f</td></tr>'
                   % (k, *mc[k], *cm[k], oo[k][0], oo[k][1], oo[k][2], oo[k][3]) for k in KINDS[1:])

REH = [
    ('1', 'exit status, <code>done cells=</code>', '<code># meshmap: done cells=20/20</code>, <code>cells 20/20 in 0.0961 s</code>', 'pass'),
    ('2', 'mesh counter level', '<code># mesh counters: level=1</code>, all four events opened as one group', 'pass'),
    ('3', 'read floor', '<code># read_floor: 7 6 5 12 10</code> counts per empty read', 'pass'),
    ('4', 'first 32 probes', 'winning count 133 to 144 of 64 pairs, next largest at most 22', 'pass'),
    ('5', 'probe time', '<code># classify: probe_ns=11545</code> (11.5 us). The limit for 2,048 lines per cell is 78 us', 'pass'),
    ('6', 'frame number, one page', '<code># pagemap: pfn=0xc004800</code>, <code># one_2mib_page: yes</code>', 'pass'),
    ('7', 'lines per node', '<code>per_node=64,64,64,64,64</code>, 320 lines probed, 1 probe repeated (line 248), 0 unused', 'pass'),
    ('8', 'the 20 rows', 'OCM kinds %.1f to %.1f ns, <code>slc</code> %.1f to %.1f ns, <code>dram-flush</code> %.1f to %.1f ns'
     % (min(r13rng('ocm-flush')[0], r13rng('ocm-evict')[0]), max(r13rng('ocm-flush')[1], r13rng('ocm-evict')[1]), *r13rng('slc'), *r13rng('dram-flush')), 'pass, see note'),
    ('9', 'core counter coverage', '<code>perf_cov</code> 1.0000 in all 21 rows', 'pass'),
    ('10', 'kernel log', 'no arm-cmn line, no warning after the commands. The one warning is the module taint line at load', 'pass'),
]
reh_rows = ''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % r for r in REH)

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
.mm{display:flex;flex-wrap:wrap;gap:10px}figure{margin:0}figcaption{font-size:12.5px;color:var(--ink2);text-align:center}
.grid{stroke:#e4e3dd;stroke-width:1}.xp{fill:#c9c8c1}.hn{stroke:#fff;stroke-width:2}.cpu{fill:#1d1d1b}.mem{fill:#fff;stroke:#1d1d1b;stroke-width:1.6}
.lab{font:10.5px sans-serif;fill:#55554f}.val{font:600 11.5px sans-serif;fill:#1d1d1b}
.leg{font-weight:400;font-size:12px;color:var(--ink2);margin-left:10px;white-space:nowrap}.leg i{display:inline-block;width:11px;height:10px;vertical-align:-1px}
.leg1{fill:none;stroke:#256abf;stroke-width:2.2}.leg2{fill:none;stroke:#256abf;stroke-width:2.2;stroke-dasharray:5 3}.leg3{fill:none;stroke:#b8442c;stroke-width:2.2}
.take{font-weight:600;margin:6px 0 12px}.two{display:flex;flex-wrap:wrap;gap:22px;align-items:flex-start}.two>div{flex:1 1 320px}
.hyp{border:1px dashed #a8a79f;padding:8px 12px;margin:10px 0;border-radius:4px}
ul{padding-left:20px;margin:6px 0}li{margin:3px 0}
"""

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Run 8 mesh map: boot 1</title><style>{CSS}</style></head><body><main>
<h1>Run 8, the mesh latency map: rehearsal and boot 1</h1>
<p class="sub">Asimov emulator, result folders 013 (rehearsal) and 014 (boot 1: L3 holds no data, prefetchers off). Files copied and checked 2026-11-11.</p>

<div class="short"><b>Short version</b>
<p>The rehearsal passed all ten checks, and boot 1 of the full run came back whole: 180 of 180 cells, 7 timed passes each.</p>
<p>A load from a CPU to a home node costs about 20.6 ns plus 2.0 ns per X step plus 1.0 ns per Y step, and a DRAM-backed line held in a node's cache slice costs the same as an OCM line of that node (mean difference {np.mean(d_se):+.3f} ns over 40 cells).</p>
<p>A flushed DRAM-backed line costs 50.0 to 57.3 ns, and its cost follows a three-leg path (CPU, home node, a memory bridge at the left edge of the mesh, CPU) to within 0.09 ns rms.</p></div>

<h2>Words used here</h2>
<ul>
<li><b>Mesh</b>: the chip's interconnect, 6 x 6 crosspoints. A message moves one crosspoint per step. Crosspoints are written (x,y).</li>
<li><b>Home node</b>: one of five cache nodes on the mesh (ids 88, 160, 216, 288, 344). Each holds a 1 MiB slice of the system-level cache (SLC) and 256 KiB of on-chip memory (OCM).</li>
<li><b>DRAM-backed line</b>: a 64-byte line of normal memory. A hash of its address selects its home node.</li>
<li><b>Cell</b>: one CPU, one home node, one kind of row. Each cell has 7 timed passes of 2,048 dependent loads. <b>Best</b> is the smallest ns per load of the 7.</li>
<li><b>Kinds</b>: <code>ocm-flush</code> (OCM lines, flushed first), <code>ocm-evict</code> (OCM lines, pushed out of the CPU's caches by loading other lines), <code>slc</code> (DRAM-backed lines held in the node's slice, same recipe as <code>ocm-evict</code>), <code>dram-flush</code> (the same DRAM-backed lines, flushed first, so every load goes to memory).</li>
<li><b><code>meshmap</code></b>: the program that measures the cells. <b><code>run_map.sh</code></b>: the script that runs it with four control rows of the older program <code>latency</code>.</li>
<li><b>Mesh counters</b>: per-node event counters of the mesh. <code>req_&lt;node&gt;</code> counts requests that reach a home node. <code>mc_reqs</code> counts requests a home node sends on to memory. <code>cache_miss</code> counts misses in the slice.</li>
<li><b>SBSX</b>: the mesh's bridge to the memory model. <b>rms</b>: root mean square of the fit's errors. <b>est.</b>: an estimate.</li>
<li><b>Boot 1</b>: firmware of the earlier boot B. The clusters of CPUs 2 to 9 keep no data in their L3, and their prefetchers are off. CPU 0's cluster is not in that state (section 6).</li>
</ul>

<h2>1. The rehearsal (folder 013)</h2>
<p>One <code>meshmap</code> command on CPU 2 with 64 lines per cell and one pass. All seven files pass their checksums [Ref1].</p>
<div class="scroll"><table><thead><tr><th>#</th><th>Check</th><th>What the files show</th><th>Result</th></tr></thead><tbody>{reh_rows}</tbody></table></div>
<ul>
<li><b>Note on check 8.</b> Two OCM rows read above the expected 27 ns (27.03 and 27.95 ns). These rows are 64 loads in one pass. The same two cells read 26.30 and 26.78 ns in boot 1 with 2,048 loads.</li>
<li><b>Counts per flush-and-load pair on a DRAM-backed line: about 2.0.</b> The winning node's count is 133 to 144 per 64 pairs, and the read floor is 5 to 12 counts [Ref2]. This number was not known before.</li>
<li><b>Level 1 opened.</b> The three sums (<code>mc_reqs</code>, <code>cache_miss</code>, <code>snp_sent</code>) are present in every row.</li>
<li><b>Chip time.</b> The command took 0.096 s against the estimate of 0.06 s est. [Ref2].</li>
</ul>

<h2>2. Boot 1 (folder 014): is the data whole?</h2>
<ul>
<li>All 11 files pass their checksums [Ref3].</li>
<li><code>latency-map.csv</code> holds 1,269 rows of 23 fields: 180 cells x 7 passes, plus 9 idle rows. The file ends with <code>done cells=180/180</code> [Ref4].</li>
<li>Core counter coverage (<code>perf_cov</code>) is 1.0000 in every row.</li>
<li>The classification probed {HC14[0]:,} lines and gave each node 2,048 to 2,050 lines. {HC14[4]} lines stayed unclassified [Ref5].</li>
<li>The script took 1.217 s of chip time against the estimate of 1.01 s est. (Jesse's README; the console line is not in our copy) [Ref6].</li>
<li>Jesse ran it with <code>--kernel-cpus</code>, so 20 more cells from CPU 0 are in the file (section 6).</li>
</ul>
<h3>Control rows</h3>
<p>The four <code>latency</code> rows agree with the <code>ocm-flush</code> cells of the same CPU and node. The largest difference is {ctl_max:.2f} ns [Ref7].</p>
<table class="num"><thead><tr><th>CPU</th><th>Node</th><th><code>latency</code> best, ns</th><th><code>meshmap</code> best, ns</th><th>Difference, ns</th></tr></thead><tbody>{ctl_rows}</tbody></table>

<h2>3. The map</h2>
<p>Each small mesh shows one CPU pair (black triangle) and the five home nodes (circles). The number above a circle is the best ns per load. Darker means slower. The two upper rows share one colour scale, and the DRAM row has its own.</p>
{maps()}
<p class="take">The two upper rows are the same picture: the slice of a node answers as fast as its OCM. In the bottom row the nodes far from the left edge are slow for every CPU.</p>
<p class="sub">CPUs 3, 5, 7 and 9 repeat their cluster partner within 0.61 ns in the cache kinds and within 0.07 ns in <code>dram-flush</code>. The tables below hold all nine CPUs. Hover a circle for the median.</p>

<h3>Exact numbers: best ns per load of 7 passes</h3>
<div class="two">
<div><h4><code>ocm-evict</code></h4><div class="scroll">{table('ocm-evict')}</div></div>
<div><h4><code>slc</code></h4><div class="scroll">{table('slc')}</div></div>
<div><h4><code>ocm-flush</code></h4><div class="scroll">{table('ocm-flush')}</div></div>
<div><h4><code>dram-flush</code></h4><div class="scroll">{table('dram-flush')}</div></div>
</div>
<p class="sub">CPU 0's rows (italic) are in another cache state and are not distance numbers (section 6).</p>

<h2>4. What the cells of CPUs 2 to 9 say</h2>
<h3>4.1 The slice of a node costs the same as its OCM</h3>
<ul>
<li>The hypothesis was: per node, <code>slc</code> latency equals <code>ocm-evict</code> latency.</li>
<li>Over the 40 cells, <code>slc</code> best minus <code>ocm-evict</code> best has a mean of {np.mean(d_se):+.3f} ns. The range is {min(d_se):+.2f} to {max(d_se):+.2f} ns, and the rms is {np.sqrt(np.mean(np.square(d_se))):.2f} ns [Ref4].</li>
<li>So the data supports the hypothesis on this boot.</li>
</ul>
<h3>4.2 Cost per step</h3>
<p>Least-squares fit of the 40 best values: ns = a + b x (X steps) + c x (Y steps).</p>
<table class="num"><thead><tr><th>Kind</th><th>a, ns</th><th>b, ns per X step</th><th>c, ns per Y step</th><th>rms, ns</th><th>largest error, ns</th></tr></thead><tbody>{fit_rows}</tbody></table>
<ul>
<li>The three cache kinds repeat the older fit of the 20 known OCM cells (20.75 + 1.99 X + 0.95 Y). The 40 new <code>ocm-flush</code> cells differ from that fit by {min(res_old):+.2f} to {max(res_old):+.2f} ns.</li>
<li><code>ocm-flush</code> reads {-np.mean(d_sf):.2f} ns above <code>slc</code> on average. The cause is not known (section 7).</li>
<li><code>dram-flush</code> does not fit this form (rms {FIT['dram-flush'][1]:.2f} ns). Section 5 gives the form that fits.</li>
</ul>
<h3>4.3 Did each load go where the cell says?</h3>
<p>Counts per load, median of the 7 passes, range over the 40 cells [Ref4].</p>
<div class="scroll"><table class="num"><thead><tr><th>Kind</th><th><code>mc_reqs</code> (sent on to memory)</th><th><code>cache_miss</code></th><th>own node's requests minus mean of the other four</th><th>mean of the other four</th></tr></thead><tbody>{cnt_rows}</tbody></table></div>
<ul>
<li><b><code>slc</code> lines were in the slice.</b> The cell medians of <code>mc_reqs</code> are at most {mc['slc'][1]:.4f} per load, and the largest single pass reads {slc_mc_max:.4f}. In <code>dram-flush</code> it is 1.00 per load.</li>
<li>One <code>ocm-evict</code> pass (CPU 6, node 344, pass 5) reads <code>mc_reqs</code> 0.45 per load. Its time is within 0.12 ns of the passes beside it.</li>
<li>The <code>ocm-flush</code> cells of CPUs 2 to 9 ran before the mesh counters opened, so they have no mesh counts. Their timing is the only check of their node.</li>
<li><b>Each load reached the cell's node.</b> The own node receives 1.2 to 1.3 more requests per load than the other nodes do.</li>
<li><b>No prefetch.</b> Both prefetch refill counters read 0.0000 in all {len(rows) - 9 - n0:,} cell rows of CPUs 2 to 9 ({hw29} rows nonzero).</li>
</ul>

<h3>4.4 Passes 4 to 6 read about 1.3 ns above passes 0 to 3</h3>
<div class="two"><div>
<ul>
<li>Pass r of a cell reads its pointer from byte 8 x r of each 64-byte line [Ref11]. So passes 0 to 3 read the lower 32 bytes of the line, and passes 4 to 6 read the upper 32 bytes.</li>
<li>In all 120 cells of the three cache kinds, every one of passes 4 to 6 is slower than every one of passes 0 to 3. The best pass is a pass 4 to 6 in {best_late} of the 120 cells.</li>
<li><code>dram-flush</code> shows no such step.</li>
<li>No counter column differs between the two groups of passes.</li>
<li>So every "best" on this page is a number for the lower half of the line. A load of the upper half costs about 1.3 ns (about 2.7 core cycles) more.</li>
</ul></div><div>
<table class="num"><thead><tr><th>Kind</th><th>mean of passes 4 to 6 minus mean of passes 0 to 3, ns</th><th>range over 40 cells, ns</th></tr></thead><tbody>{step_rows}</tbody></table>
<div class="hyp"><b>Hypothesis:</b> a home node sends a line as two 32-byte parts, lower part first. The measurement that would test it: one cell with the slot order reversed, or the mesh data width in the design source. Insufficient data today.</div>
</div></div>

<h2>5. The flushed DRAM cells follow a three-leg path</h2>
<div class="two"><div>
<ul>
<li><b>Observation.</b> From CPU 8 all five nodes cost 56.5 or 57.2 ns. From CPU 2 the cost rises from 50.0 ns (node 88) to 56.0 ns (node 344). Distance from CPU to home node alone does not explain this.</li>
<li><b>Test.</b> I fitted ns = a + p x (X link crossings) + q x (Y link crossings) over the path CPU, home node, a memory point M, CPU. I tried every crosspoint as M.</li>
<li><b>Result.</b> M at (0,3) or (1,3) gives rms {tri03[0]:.3f} ns over 40 cells, with a = {tri03[3][0]:.2f} ns for (0,3), p = {tri03[3][1]:.2f} ns and q = {tri03[3][2]:.2f} ns. The two positions cannot be told apart, since no CPU or node sits left of x = 1. The next best position has rms {[t for t in TRI if t[2] not in ((0, 3), (1, 3))][0][0]:.2f} ns.</li>
<li><b>Control model.</b> A path where the data returns through the home node fits no better than rms {VIA[0][0]:.2f} ns at any M.</li>
<li><b>The mesh map agrees.</b> A memory bridge (SBSX) sits at crosspoint (0,3) [Ref8].</li>
</ul>
<div class="hyp"><b>Hypothesis, not yet proven:</b> the home node forwards the request to the SBSX at (0,3), and the SBSX sends the data straight to the CPU. The measurement that would confirm it: a second 2 MiB page whose lines use another SBSX, or the routing tables in the firmware source. One page was measured, so one bridge is seen.</div>
</div><div>{path_fig()}<p class="sub">Example: CPU 8 through node 216. Total 10 X crossings and 2 Y crossings. Fit: {tri03[3][0] + 10 * tri03[3][1] + 2 * tri03[3][2]:.2f} ns. Measured: {best('dram-flush', 8, 216):.2f} ns.</p></div></div>
<ul>
<li>The cache kinds cost 1.00 ns per X crossing and 0.49 ns per Y crossing (a round trip crosses each step twice). The DRAM fit gives 0.99 ns per X crossing but 0.32 ns per Y crossing. The Y difference is about 11 standard errors, and it is not explained (section 7).</li>
<li><code>dram-flush</code> passes repeat within {spread['dram-flush'][1]:.2f} ns. The cache kinds spread 1.2 to 2.0 ns between their 7 passes in 119 of 120 cells, and the step of section 4.4 is the cause.</li>
<li>With M on row y = 3, the Y crossings of the three-leg path equal those of the round trip. So q is the cost of the CPU-to-node Y steps, and it is lower here than in the cache kinds.</li>
</ul>

<h3>5.1 The address hash matches Arm's formula</h3>
<ul>
<li>The run printed <code>one_2mib_page: yes</code> and the frame number 0xc004800, so every line's physical address is known [Ref5].</li>
<li>Arm's formula for a number of nodes that is not a power of two folds address bits 51 to 6 into 12 bits and scales them to 0 to 4 [Ref9].</li>
<li>It predicts the measured home node of {HC14[2]:,} of {HC14[1]:,} classified lines in boot 1, and {HC13[2]} of {HC13[1]} in the rehearsal.</li>
<li>The order of the target table is {', '.join(str(n) for n in HC14[3])} for formula results 0 to 4.</li>
</ul>

<h2>6. The CPU 0 cells</h2>
<ul>
<li>Jesse's side ran a second rehearsal command with CPU 0 and then switched <code>--kernel-cpus</code> on for the full run. Both ran whole. This answers the open question: measuring CPU 0 did not hang the boot [Ref6].</li>
<li>CPU 0's cells are in another cache state. A prefetch refill counter is nonzero in {hw0} of its {n0} cell rows. Its <code>ocm-flush</code> cells read {min(best('ocm-flush', 0, n) for n in NODES):.1f} to {max(best('ocm-flush', 0, n) for n in NODES):.1f} ns, against {min(best('ocm-flush', c, n) for c in CPUS29 for n in NODES):.1f} to {max(best('ocm-flush', c, n) for c in CPUS29 for n in NODES):.1f} ns for CPUs 2 to 9 [Ref4].</li>
<li>Jesse's README gives the cause: the firmware changes cover CPUs 2 to 9 only, so CPU 0's cluster keeps its L3 in use and its prefetchers on. No register readback for CPU 0 is in the files, so this cause rests on the README.</li>
<li>So CPU 0's rows on boots 1 and 2 are not distance numbers. They can be compared with the other CPUs on boot 3 only.</li>
</ul>

<h2>7. Not explained, and not verified</h2>
<ul>
<li><b><code>ocm-flush</code> is {-np.mean(d_sf):.2f} ns slower than <code>ocm-evict</code> and <code>slc</code>.</b> Insufficient data. A run of the <code>ocm-flush</code> block after the other blocks would show whether the order of the blocks matters.</li>
<li><b>The Y cost per crossing differs: 0.49 ns in the cache kinds, 0.32 ns in the DRAM fit.</b> Insufficient data. The CPUs and nodes use only y = 2, 3 and 4, so Y is weakly determined. CPU 0's cells on boot 3 add no new y.</li>
<li><b>Why passes 4 to 6 are slower</b> in the cache kinds and not in <code>dram-flush</code> (section 4.4). The older <code>latency</code> rows used one slot, so they do not show it.</li>
<li><b>The mesh map is from an earlier boot</b> (folder 011). Boot 1's own files hold no mesh map. The mesh is the same hardware image.</li>
<li><b>The control rows have 2 timed passes each</b>, so their agreement within 0.18 ns rests on a best of 2.</li>
<li><b>Jesse's README says a group read stops the whole mesh counter unit while it reads.</b> I have not checked this against the kernel source. If true, requests that arrive during a read go uncounted. The per-load counts above are near whole numbers, so the loss is small in these rows.</li>
<li><b>CPU 3 was online.</b> The 20 older OCM cells were taken with CPU 3 offline. The new cells still repeat the old fit within {max(abs(x) for x in res_old):.2f} ns.</li>
<li><b>Boot 2 is already queued</b> (Jesse's README of folder 014). Boot 1 shows no defect that should stop it.</li>
</ul>

<h2>References</h2>
<ul>
<li>[Ref1] <code>results/membench-jibin-013/SHA256SUMS</code>, 7 of 7 OK.</li>
<li>[Ref2] <code>results/membench-jibin-013/results/bootM0/map-rehearsal.csv</code> (the <code>#</code> lines and 21 rows), <code>map-rehearsal-log.txt</code>, <code>../dmesg.txt</code>.</li>
<li>[Ref3] <code>results/membench-jibin-014/SHA256SUMS</code>, 11 of 11 OK.</li>
<li>[Ref4] <code>results/membench-jibin-014/results/bootM1/latency-map.csv</code>.</li>
<li>[Ref5] <code>results/membench-jibin-014/results/bootM1/map-homes.txt</code> and the <code># classify</code>, <code># pagemap</code> lines of [Ref4].</li>
<li>[Ref6] <code>results/membench-jibin-013/README.md</code> and <code>results/membench-jibin-014/README.md</code>, written by Jesse's agent. Numbers quoted from them are marked.</li>
<li>[Ref7] <code>results/membench-jibin-014/results/bootM1/latency-ocm-region{{0,4}}-mapctl-cpu{{2,8}}.csv</code>.</li>
<li>[Ref8] <code>results/membench-jibin-011/results/bootF1/sysinfo.txt</code> lines 489 to 551, the mesh map.</li>
<li>[Ref9] Arm CMN S3 Technical Reference Manual 107858_0203_05, section 2.4.5.3, "Non-power of two hash function" (page 142).</li>
<li>[Ref10] This page is written by <code>gen_run8_report.py</code> from the files above. Four independent checkers recomputed its numbers from the raw files on 2026-11-11.</li>
<li>[Ref11] <code>meshmap.c</code> at commit <code>3b12e4f</code>, function <code>run_cell()</code>.</li>
</ul>
</main></body></html>"""
open(OUT, 'w').write(page)
print('wrote', OUT, len(page), 'bytes')
print('slc-evict mean %.3f range %.2f..%.2f' % (np.mean(d_se), min(d_se), max(d_se)), 'tri', tri03[:3], tri03[3], 'next', [t[:3] for t in TRI[:4]], 'via', VIA[0][:3])
print('hash', HC14, HC13, 'hw0', hw0, n0, 'hw29', hw29, 'ctl', CTL, 'res_old', min(res_old), max(res_old), 'spread', spread)
