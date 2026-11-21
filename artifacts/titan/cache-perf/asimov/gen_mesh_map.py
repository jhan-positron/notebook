#!/usr/bin/env python3
"""The mesh latency map of the Asimov emulator: one report page for run 8.

Usage: python3 gen_mesh_map.py [--out asimov-mesh-map.html]
Reuses the data layers and figures of gen_run8_report.py (trial run and boot 1) and
gen_run8_boots.py (the three boots). Both write a page when imported, so they are
imported with --out /dev/null.
"""
import sys, os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(HERE, 'asimov-mesh-map.html')
sys.argv = [sys.argv[0], '--out', '/dev/null']
sys.path.insert(0, HERE)
import gen_run8_report as r   # noqa: E402
import gen_run8_boots as g    # noqa: E402

B, NODES, NPOS, CPOS = g.B, g.NODES, g.NPOS, g.CPOS
PAIRS = [(2, 3), (4, 5), (6, 7), (8, 9)]
SBSX_ALL = [(0, 0), (0, 1), (0, 3), (0, 4), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]
BASE, CX, CY = r.FIT['ocm-evict'][0]
MB, MX, MY = round(BASE, 1), round(CX, 1), round(CY, 1)   # the formula as the page prints it
assert all(n == 64 * NPOS[n][0] + 8 * NPOS[n][1] for n in NODES)
model = lambda c, n: MB + MX * g.steps(c, n)[0] + MY * g.steps(c, n)[1]
CACHE2 = ('ocm-evict', 'slc')


def must(text, old, new):
    """Replace one known string of a reused figure or table. Fail if the source generator changed."""
    assert text.count(old) >= 1, old
    return text.replace(old, new)


r.legend = lambda lo, hi: ('<span class="leg">%.1f ns ' % lo + ''.join('<i style="background:%s"></i>' % c for c in r.RAMP) + ' %.1f ns</span>' % hi)


def layout():
    """The 6 x 6 mesh with the CPU pairs, the home nodes and the memory bridges."""
    W, Hh, m, gp = 470, 430, 50, 70
    X = lambda x: m + x * gp
    Y = lambda y: Hh - 40 - y * gp
    s = ['<svg viewBox="0 0 %d %d" width="100%%" style="max-width:%dpx" role="img" aria-label="the mesh: CPU pairs, home nodes and memory bridges">' % (W, Hh, W)]
    for i in range(6):
        s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" class="grid2"/>' % (X(i), Y(0), X(i), Y(5)))
        s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" class="grid2"/>' % (X(0), Y(i), X(5), Y(i)))
        s.append('<text x="%d" y="%d" class="lab" text-anchor="middle">x=%d</text>' % (X(i), Y(0) + 30, i))
        s.append('<text x="%d" y="%d" class="lab" text-anchor="end">y=%d</text>' % (X(0) - 22, Y(i) + 4, i))
    for x in range(6):
        for y in range(6):
            s.append('<circle cx="%d" cy="%d" r="2.2" class="xp"/>' % (X(x), Y(y)))
    for (x, y) in SBSX_ALL:
        s.append('<rect x="%d" y="%d" width="13" height="13" class="mem"><title>memory bridge (SBSX) at crosspoint (%d,%d)</title></rect>' % (X(x) - 6.5, Y(y) - 6.5, x, y))
    for n in NODES:
        x, y = NPOS[n]
        s.append('<circle cx="%d" cy="%d" r="13" fill="#6da7ec" class="hn"><title>home node %d at crosspoint (%d,%d)</title></circle>' % (X(x), Y(y), n, x, y))
        s.append('<text x="%d" y="%d" class="val" text-anchor="middle">%d</text>' % (X(x), Y(y) - 18, n))
    for c in (0, 2, 4, 6, 8):
        x, y = CPOS[c]
        s.append('<path d="M%d %d l10 17 h-20 z" class="cpu"><title>CPUs %d and %d at crosspoint (%d,%d)</title></path>' % (X(x), Y(y) - 11, c, c + 1, x, y))
        s.append('<text x="%d" y="%d" class="val" text-anchor="middle">CPU %d-%d</text>' % (X(x), Y(y) + 22, c, c + 1))
    s.append('</svg>')
    key = ('<p class="key2"><span class="nw"><svg width="16" height="14"><path d="M8 1 l7 12 h-14 z" class="cpu"/></svg> CPU pair (one cluster)</span> '
           '<span class="nw"><svg width="16" height="16"><circle cx="8" cy="8" r="6.5" fill="#6da7ec"/></svg> home node</span> '
           '<span class="nw"><svg width="16" height="16"><rect x="2" y="2" width="11" height="11" class="mem"/></svg> memory bridge</span><br>'
           'The number above a blue circle (88, 160, 216, 288, 344) is the id of that home node.</p>')
    return ''.join(s) + key


def flow():
    """How one cell is measured, left to right."""
    boxes = [('1. Find the lines', 'For DRAM-backed lines (not OCM):', 'flush and load each line', '64 times, see which', 'node counts requests'),
             ('2. Build a chain', '2,048 lines of ONE node,', 'each line holds the', 'address of the next,', 'in a new random order'),
             ('3. Empty the caches', 'flush every chain line,', 'or store to it and then', 'load 30,720 other lines', '(the evictor)'),
             ('4. Time one pass', 'walk the chain:', '2,048 dependent loads,', 'ns per load =', 'time / 2,048'),
             ('5. Repeat', '7 timed passes per cell.', 'Best = smallest of 7.', 'Core counters are read', 'around every pass')]
    bw, bh, gp = 220, 112, 22
    W = len(boxes) * bw + (len(boxes) - 1) * gp + 4
    s = ['<svg viewBox="0 0 %d %d" width="100%%" style="min-width:1000px" role="img" aria-label="the five steps of the measurement">' % (W, bh + 8)]
    for i, b in enumerate(boxes):
        x = 2 + i * (bw + gp)
        s.append('<rect x="%d" y="4" width="%d" height="%d" rx="6" class="box"/>' % (x, bw, bh))
        s.append('<text x="%d" y="26" class="bt">%s</text>' % (x + 10, b[0]))
        for j, line in enumerate(b[1:]):
            s.append('<text x="%d" y="%d" class="lab">%s</text>' % (x + 10, 46 + 16 * j, line))
        if i:
            s.append('<path d="M%d %d h%d m-7 -5 l7 5 l-7 5" class="arrow"/>' % (x - gp + 4, 4 + bh // 2, gp - 8))
    s.append('</svg>')
    return ''.join(s)


def model_fig():
    """Measured ns against the distance in units, with the model line."""
    W, Hh, lm, bm, tm, rm = 760, 380, 56, 46, 14, 220
    X = lambda u: lm + (u - 0.5) / 9 * (W - lm - rm)
    Y = lambda v: Hh - bm - (v - 20) / (31 - 20) * (Hh - bm - tm)
    s = ['<svg viewBox="0 0 %d %d" width="100%%" style="max-width:%dpx" role="img" aria-label="measured ns per load against distance">' % (W, Hh, W)]
    for v in range(20, 32, 2):
        s.append('<line x1="%d" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="lab" text-anchor="end">%d</text>' % (lm, Y(v), X(9.5), Y(v), lm - 6, Y(v) + 4, v))
    for u in range(1, 10):
        s.append('<text x="%.1f" y="%d" class="lab" text-anchor="middle">%d</text>' % (X(u), Hh - bm + 16, u))
    s.append('<text x="%.1f" y="%d" class="lab" text-anchor="middle">distance in units (2 per X step + 1 per Y step)</text>' % (X(5), Hh - 8))
    s.append('<text x="14" y="%.1f" class="lab" transform="rotate(-90 14 %.1f)" text-anchor="middle">best ns per load</text>' % (Y(25.5), Y(25.5)))
    s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="model"/>' % (X(0.5), Y(MB + 0.5), X(9.5), Y(MB + 9.5)))
    s.append('<text x="%.1f" y="%.1f" class="lab">model: %.1f ns + 1.0 ns per unit</text>' % (X(9.5) + 8, Y(MB + 9.5) + 4, MB))
    for u in sorted({g.units(c, n) for c, n in g.CELLS}):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="mtick"><title>model at %d units: %.1f ns</title></line>' % (X(u - 0.3), Y(MB + u), X(u + 0.3), Y(MB + u), u, MB + u))
    series = [('ocm-evict', 1, g.COLOR[1], -0.16, 'boot 1, OCM lines (ocm-evict)'), ('slc', 1, g.COLOR[2], 0, 'boot 1, slice lines (slc)'), ('ocm-flush', 2, g.COLOR[3], 0.16, 'boot 2, OCM lines (ocm-flush)')]
    for k, b, colr, off, name in series:
        for c, n in g.CELLS:
            v = B[b].best(k, c, n)
            s.append('<circle cx="%.1f" cy="%.1f" r="3.8" fill="%s" class="dot"><title>%s, CPU %d to node %d (%d units): %.2f ns</title></circle>' % (X(g.units(c, n) + off), Y(v), colr, name, c, n, g.units(c, n), v))
    for i, (k, b, colr, off, name) in enumerate(series):
        s.append('<circle cx="%.1f" cy="%d" r="5" fill="%s"/><text x="%.1f" y="%d" class="lab">%s</text>' % (X(9.5) + 14, 150 + 20 * i, colr, X(9.5) + 24, 154 + 20 * i, name))
    s.append('</svg>')
    return ''.join(s)


def dist_table():
    s = ['<table class="num"><thead><tr><th>CPU pair (crosspoint)</th><th>Node (crosspoint)</th><th>X steps</th><th>Y steps</th><th>Distance units (2 per X step + 1 per Y step)</th><th>Model, ns</th>'
         '<th>OCM line, ns</th><th>Slice line, ns</th><th>Flushed DRAM line, ns</th></tr></thead><tbody>']
    for a, b in PAIRS:
        for n in NODES:
            dx, dy = g.steps(a, n)
            f = lambda k: '%.2f / %.2f' % (B[1].best(k, a, n), B[1].best(k, b, n))
            s.append('<tr><td>CPUs %d, %d (%d,%d)</td><td>%d (%d,%d)</td><td>%d</td><td>%d</td><td>%d</td><td>%.2f</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                     % (a, b, *CPOS[a], n, *NPOS[n], dx, dy, 2 * dx + dy, model(a, n), f('ocm-evict'), f('slc'), f('dram-flush')))
    return ''.join(s) + '</tbody></table>'


fit12 = ''.join('<tr><td>Boot %d</td><td><code>%s</code></td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td></tr>'
                % (b, k, *g.FIT[(b, k)][0], g.FIT[(b, k)][1], g.FIT[(b, k)][2]) for b, k in ((1, 'ocm-evict'), (1, 'slc'), (1, 'ocm-flush'), (2, 'ocm-flush')))
err = [B[1].best(k, c, n) - model(c, n) for k in CACHE2 for c, n in g.CELLS]
errmax = max(abs(x) for x in err)
near = np.mean([B[1].best(k, c, n) for k in CACHE2 for c, n in g.CELLS if g.units(c, n) == 1])
far = np.mean([B[1].best(k, c, n) for k in CACHE2 for c, n in g.CELLS if g.units(c, n) == 9])
lo_c, hi_c = min(g.rng(1, k)[0] for k in CACHE2), max(g.rng(1, k)[1] for k in CACHE2)
pair_c = max(abs(B[1].best(k, a, n) - B[1].best(k, b, n)) for k in CACHE2 for a, b in PAIRS for n in NODES)
pair_d = max(abs(B[1].best('dram-flush', a, n) - B[1].best('dram-flush', b, n)) for a, b in PAIRS for n in NODES)
omo = [r.own_minus_others(k) for k in ('ocm-evict', 'slc', 'dram-flush')]
omo_lo, omo_hi = min(x[0] for x in omo), max(x[1] for x in omo)
own_e, oth_e = B[1].own_req('ocm-evict')
own_s, oth_s = B[1].own_req('slc')
mc_pass = {k: max(B[1].allrows(k, 'mc_reqs')) for k in CACHE2}
spread = {b: max(max(B[b].col('dram-flush', c, n)) - min(B[b].col('dram-flush', c, n)) for c, n in g.CELLS) for b in (1, 2)}
up2 = lambda v: np.ceil(v * 100 - 1e-9) / 100          # a bound, so round up
half = lambda b, k: float(np.mean([np.mean(B[b].col(k, c, n)[4:]) - np.mean(B[b].col(k, c, n)[:4]) for c, n in g.CELLS]))
HALF = [half(1, 'ocm-flush'), half(1, 'ocm-evict'), half(1, 'slc'), half(2, 'ocm-flush')]
late = lambda b, k: sum(int(np.argmin(B[b].col(k, c, n))) >= 4 for c, n in g.CELLS)
assert [late(1, 'ocm-flush'), late(1, 'ocm-evict'), late(1, 'slc'), late(2, 'ocm-flush')] == [0, 0, 0, 0]
sh0 = [B[2].col('slc', c, 88, 'l3d_refill_rd')[0] for c in (2, 4, 6, 8)]
sh6 = [B[2].col('slc', c, 88, 'l3d_refill_rd')[6] for c in (2, 4, 6, 8)]
f3, f3rms = g.FIT[(3, 'ocm-flush')][0], g.FIT[(3, 'ocm-flush')][1]
r3o, r3d = g.rng(3, 'ocm-flush'), g.rng(3, 'dram-flush')
ratio3 = [B[3].best('dram-flush', c, n) / B[1].best('dram-flush', c, n) for c, n in g.CELLS]
med3 = g.rng(3, 'dram-flush', B[3].med)
mixrms = [g.MIX2[(2, k)][1] for k in CACHE2]
mixrms0 = [B[2].fit_mix(k)[1] for k in CACHE2]
base2 = [g.MIX2[(2, k)][0][1] for k in CACHE2]
base1 = [g.MIX2[(1, k)][0][1] for k in CACHE2]
unit2 = sorted(g.MIX2[(2, k)][0][2] for k in CACHE2)
step2 = sorted(g.MIX2[(2, k)][0][3] for k in CACHE2)
kinds_tbl = ''.join('<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>' % x for x in (
    ('ocm-flush', 'the node\'s on-chip memory (OCM)', 'flush every chain line', 'the node\'s OCM, over the mesh'),
    ('ocm-evict', 'the node\'s OCM', 'store to every chain line, then the evictor', 'the node\'s OCM, over the mesh'),
    ('slc', 'normal memory (DRAM). The node is the home node of all these lines', 'store to every chain line, then the evictor', 'the node\'s cache slice, over the mesh'),
    ('dram-flush', 'normal memory (DRAM), the same lines as <code>slc</code>', 'flush every chain line', 'memory (DRAM), through the node')))
boots_tbl = ''.join('<tr><td>Boot %d</td><td>%s</td><td>%s</td><td>%s</td></tr>' % x for x in (
    (1, '014', g.STATE[1], 'The distance map. On CPUs 2 to 9, every load of every kind leaves the cluster.'),
    (2, '015', g.STATE[2], 'Flushed kinds repeat boot 1. Evicted kinds mix two paths.'),
    (3, '016', g.STATE[3], 'Shows what the prefetchers do. Not a distance map.')))
t1, t2 = g.TRI[1], g.TRI[2]
at = lambda t, m: [x for x in t if x[1] == m][0]
assert {t1[0][1], t1[1][1]} == {(0, 3), (1, 3)} and abs(t1[0][0] - t1[1][0]) < 1e-6      # the fit cannot tell column 0 from column 1
assert {t2[0][1], t2[1][1]} == {(0, 3), (1, 3)}
bridges1 = sorted(x for x in t1 if x[1] in SBSX_ALL)
assert bridges1[0][1] == (0, 3)
row_next = t1[2]

maps_html = r.maps()
path_html = must(r.path_fig(), 'crossings', 'steps')
path_html = must(path_html, 'viewBox="0 0 300 310" width="300" height="310"', 'viewBox="0 0 400 310" width="400" height="310" style="max-width:100%;height:auto"')
strip_html = must(g.strip(), 'viewBox="0 0 1000 504"', 'viewBox="0 0 1000 518"')
key9 = ''.join('<span class="nw"><i style="background:%s"></i>boot %d: %s</span> ' % (g.COLOR[b], b, g.STATE[b]) for b in B)
reh = must(r.reh_rows, 'winning count 133 to 144 of 64 pairs, next largest at most 22',
           'the home node counted 133 to 144 requests during the 64 flush-and-load pairs of one probe (about 2 per pair). The next largest node counted at most 22')
reh = must(reh, '<code># meshmap: done cells=20/20</code>', 'exit status 0 [Ref6], <code># meshmap: done cells=20/20</code>')
reh = must(reh, 'The limit for 2,048 lines per cell is 78 us', 'The limit for 2,048 lines per cell is 78 us (a budget of 1 s / (1.25 x 5 nodes x 2,048 lines)) [Ref10]')
reh = must(reh, '1.0000 in all 21 rows', '1.0000 in all 21 rows (20 cells and 1 idle row)')
whole = must(g.whole_rows, '1,269 rows, 180 of 180 cells', '1,269 rows (1,260 timed passes and 9 idle rows, one per CPU), 180 of 180 cells')
whole = re.sub(r'(?<![\d.,])(\d)(\d{3})(?![\d.])', r'\1,\2', whole)

CSS = r.CSS + g.CSS + """
.grid2{stroke:#cfcec7;stroke-width:1.4}.box{fill:#f6f5f1;stroke:#a8a79f;stroke-width:1.2}.bt{font:600 13px sans-serif;fill:#1d1d1b}
.arrow{fill:none;stroke:#55554f;stroke-width:1.6}.key2{font-size:12.5px;color:#55554f;margin:4px 0}.key2 svg{vertical-align:-3px;margin-left:10px}
.nw{white-space:nowrap}.key .nw i{margin-left:12px}table.num td{white-space:nowrap}
.mtick{stroke:#1d1d1b;stroke-width:1.6}
.big{font-size:17px;font-weight:600;background:#f6f5f1;padding:10px 14px;border-radius:4px;margin:10px 0}
"""

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Asimov mesh latency map</title><style>{CSS}</style></head><body><main>
<h1>The mesh latency map of the Asimov emulator</h1>
<p class="sub">What a load costs from each CPU to each home node of the mesh, measured in run 8 (2026-11-12 UTC, result folders 013 to 016) [Ref6]. Written 2026-11-12.</p>

<div class="short"><b>Short version</b>
<p>A load from a CPU to a home node of the mesh costs about {BASE:.1f} ns, plus {CX:.1f} ns for each step in X and {CY:.1f} ns for each step in Y between the CPU and the node.</p>
<p>On boot 1 (the run used for the map), this formula gives the fastest of 7 timed passes to within {up2(errmax):.2f} ns for all 40 pairs of CPU and node, for lines in a node's on-chip memory and equally for lines in a node's cache slice.</p>
<p>A load that must go to memory costs {g.rng(1, 'dram-flush')[0]:.1f} to {g.rng(1, 'dram-flush')[1]:.1f} ns on boot 1 of the emulator, and its cost follows a longer path through the home node and a memory bridge.</p></div>

<p class="sub">The terms of this page are defined in the list "Words used here", before the references.</p>

<h2>1. The mesh</h2>
<div class="two">
<div>{layout()}</div>
<div>
<ul>
<li><b>Five CPU pairs</b> sit at five crosspoints [Ref8]. Four of them (CPUs 2 to 9) are the test CPUs.</li>
<li><b>Which pair sits where:</b> the operator's README gives CPUs 0-1 at (1,2) and CPUs 8-9 at (5,2) [Ref6]. This page places the pairs between them in CPU order. No cited file states the places of CPUs 4-5 and 6-7. The fit of section 4 agrees with this placement (rms {g.FIT[(1, 'ocm-evict')][1]:.2f} ns).</li>
<li><b>Five home nodes</b> sit in the middle rows, at (1,3), (2,4), (3,3), (4,4) and (5,3) [Ref8].</li>
<li><b>The numbers 88, 160, 216, 288 and 344 in the figure are the ids of the five home nodes.</b> The mesh gives every device an id, and the mesh map lists these five [Ref8]. The mesh counters use the same ids: the counter <code>req_88</code> counts the requests that node 88 received. This page uses the id as the name of the node.</li>
<li><b>The id encodes the place.</b> For these five nodes the id equals 64 x X + 8 x Y. Node 88 sits at (1,3): 64 x 1 + 8 x 3 = 88.</li>
<li><b>Clock:</b> the CPU clock is 2.000 GHz, so one cycle is 0.5 ns [Ref11]. Insufficient data on the mesh clock: no file cited here states it. The measured step costs (2.0 ns and 1.0 ns, section 4) are whole multiples of 0.5 ns, which agrees with a 2 GHz mesh clock but does not prove it. The emulator's clock setup or the design's clock tree would resolve it.</li>
<li><b>Ten memory bridges</b> sit on the left and top edges [Ref8].</li>
<li><b>A load that misses the cluster's caches</b> sends a request over the mesh to one home node. The data returns over the mesh.</li>
<li><b>The distance</b> between a CPU and a node is counted in X steps and Y steps. From CPUs 2-3 at (2,3) to node 344 at (5,3) it is 3 X steps and 0 Y steps.</li>
<li><b>The question of this run:</b> what does each of the 4 x 5 = 20 distances cost, and does it cost the same for the node's OCM and for its cache slice?</li>
</ul>
</div></div>

<h2>2. How the map was measured</h2>
<div class="scroll">{flow()}</div>
<p class="sub">The five steps are the code of <code>meshmap.c</code> and <code>run_map.sh</code> [Ref10].</p>
<ul>
<li><b>Step 1 is needed only for DRAM-backed lines.</b> An OCM line belongs to its node by address. For a DRAM-backed line the program finds the node with the mesh counters: it flushes and loads the line 64 times and reads which node counted the requests.</li>
<li><b>Step 2 isolates one node.</b> All 2,048 lines of a chain belong to the same home node. Every load that reaches the home node therefore travels the same distance.</li>
<li><b>Step 3 is meant to decide who answers the load.</b> The four kinds differ only here:</li>
</ul>
<div class="scroll"><table><thead><tr><th>Kind</th><th>Memory that holds the 2,048 lines of the chain</th><th>Before each timed pass</th><th>Intended source of the data</th></tr></thead><tbody>{kinds_tbl}</tbody></table></div>
<ul>
<li><b>The last column is the intended source.</b> On boot 1 the core counters show that every load of CPUs 2 to 9 left the cluster, in all four kinds (section 8.4). The mesh counters also confirm the source for <code>ocm-evict</code>, <code>slc</code> and <code>dram-flush</code> (section 5). The <code>ocm-flush</code> cells have no mesh counts, and their timing is the only check of their node. On boot 2 only about 0.3 of the loads of the two evicted kinds left the cluster (section 9).</li>
<li><b>Why a store before the evictor:</b> the store changes the line. The cluster must then write the line to the home node's slice at eviction.</li>
<li><b>Step 5 gives 7 passes per cell.</b> The page quotes the best pass. Each pass walks its own random chain over the same 2,048 lines. The addresses of pass r (r = 0 to 6) sit at byte 8 x r of each line [Ref10].</li>
<li><b>Counters:</b> the core counters are read around every pass. The mesh counters are read around every pass except in the <code>ocm-flush</code> cells of CPUs 2 to 9. Those cells ran before the mesh counters opened.</li>
<li><b>Size of one boot:</b> 9 CPUs x 5 nodes x 4 kinds = 180 cells, 1,260 timed passes, about 1.1 chip seconds. The 9 CPUs are the 8 test CPUs and CPU 0.</li>
<li><b>CPU 0's 20 cells are not distance numbers.</b> Its cluster has the L3 in use and the prefetchers on at every boot [Ref6]. Every latency comparison, fit and figure below uses CPUs 2 to 9 only. The completeness table of section 8.2 counts the full files, including CPU 0.</li>
</ul>
<h3>The three boots</h3>
<div class="scroll"><table><thead><tr><th>Boot</th><th>Folder</th><th>State of CPUs 2 to 9</th><th>Use</th></tr></thead><tbody>{boots_tbl}</tbody></table></div>
<p class="sub">Before the three boots, a short trial run (folder 013) checked the new counter code on the emulator (section 8.1).</p>

<h2>3. The map</h2>
<div class="big">ns per load = {MB:.1f} + {MX:.1f} x (X steps) + {MY:.1f} x (Y steps)</div>
<p>Each small mesh shows one CPU pair (black triangle) and the five home nodes (circles). The number above a circle is the best ns per load on boot 1. Darker means slower. The two upper rows share one colour scale, and the DRAM row has its own. Hover a circle for the median. In the DRAM row the square is the memory bridge at (0,3) (section 6).</p>
{maps_html}
<p class="take">The two upper rows show the same values: a node's cache slice answers as fast as its OCM. The nearest node costs about {near:.1f} ns and the farthest about {far:.1f} ns (smallest cell {lo_c:.2f} ns, largest cell {hi_c:.2f} ns over the 8 CPUs).</p>
<h3>All 20 distances</h3>
<p>Measured values are the best of 7 passes on boot 1, given for the two CPUs of the pair.</p>
<div class="scroll">{dist_table()}</div>
<ul>
<li><b>The model column</b> is the formula above. The unrounded fit is {BASE:.3f} + {CX:.3f} x (X steps) + {CY:.3f} x (Y steps) ns (boot 1, kind <code>ocm-evict</code>, section 4).</li>
<li><b>The largest difference</b> between a measured OCM or slice value and the model column is at most {up2(errmax):.2f} ns.</li>
<li><b>The two CPUs of a pair agree</b> to within {up2(pair_c):.2f} ns in the OCM and slice columns and {up2(pair_d):.2f} ns in the DRAM column [Ref2].</li>
<li><b>The DRAM column does not follow the model.</b> It follows the path of section 6.</li>
</ul>

<h2>4. The cost of one step</h2>
<p>Each dot is one cell: a CPU and a node. The distance is counted in units, where one X step counts 2 and one Y step counts 1. Every cell has a whole number of units: 1, 2, 4, 5, 6, 8 or 9.</p>
<ul>
<li><b>The three series are drawn side by side.</b> Their dots are shifted by -0.16, 0 and +0.16 units so that they do not cover each other. The shift is for display only and is not a measured distance.</li>
<li><b>Each short black mark is the model value at one whole distance.</b> Compare the height of a dot with the mark of its group, not with the sloped line beside it.</li>
</ul>
{model_fig()}
<p class="take">All three series have the same slope: 1.0 ns per unit. The two boot 1 series lie on the model line. The boot 2 flushed series lies about {g.FIT[(2, 'ocm-flush')][0][0] - BASE:.1f} ns above it. One X step costs 2.0 ns and one Y step costs 1.0 ns.</p>
<p>Each row of the table is a least-squares fit of the best of 7 passes of the 40 cells (CPUs 2 to 9, five nodes). Largest error is the largest difference between a cell and its fit [Ref2] [Ref3].</p>
<div class="scroll"><table class="num"><thead><tr><th>Boot</th><th>Kind</th><th>Base, ns</th><th>Per X step, ns</th><th>Per Y step, ns</th><th>rms, ns</th><th>Largest error, ns</th></tr></thead><tbody>{fit12}</tbody></table></div>
<ul>
<li><b>In cycles:</b> the CPU clock is 2.000 GHz, which is 2 cycles per ns [Ref11]. One X step therefore costs 4 cycles and one Y step costs 2 cycles. Each figure covers the request going out and the data coming back.</li>
<li><b>One way, that is 2 cycles per X step and 1 cycle per Y step.</b> This split assumes that both directions cost the same. The data give only the sum.</li>
<li><b>The base of about {BASE:.1f} ns</b> is the part that does not depend on distance. Its parts were not measured. Hypothesis: the CPU's own cache lookups, the cluster's port and the home node's lookup. A run with a counter or a timestamp at each of these points would confirm or reject it.</li>
<li><b>The step cost does not depend on the L3 state.</b> Boot 2's flushed OCM cells give 1.99 and 1.01 ns per step with the L3 in use. Their medians fit {g.medfit2[0][0]:.2f} ns + {g.medfit2[0][1]:.2f} ns per X step + {g.medfit2[0][2]:.2f} ns per Y step with an rms of {g.medfit2[1]:.2f} ns [Ref3].</li>
<li><b>Flushed OCM lines read about 0.4 ns above evicted ones on boot 1</b> (base 21.03 against 20.61 ns). The cause is not known.</li>
</ul>

<h2>5. Is the cache slice as fast as the on-chip memory?</h2>
<p><b>Yes.</b></p>
<ul>
<li><b>The test:</b> <code>slc</code> and <code>ocm-evict</code> use the same recipe on two kinds of line. Their difference is the difference between a slice and the OCM of the same node.</li>
<li><b>The result:</b> <code>slc</code> minus <code>ocm-evict</code> is {np.mean(r.d_se):+.3f} ns on average over 40 cells. The range is {min(r.d_se):+.2f} to {max(r.d_se):+.2f} ns [Ref2].</li>
<li><b>The check that the slice answered:</b> the mesh counter for requests sent on to memory reads at most {r.mc['slc'][1]:.4f} per load in <code>slc</code> cells (cell medians). It reads 1.00 per load in <code>dram-flush</code> cells.</li>
<li><b>The check that the right node answered:</b> on boot 1, in every <code>slc</code>, <code>ocm-evict</code> and <code>dram-flush</code> cell of CPUs 2 to 9, the cell's own node counts {omo_lo:.1f} to {omo_hi:.1f} more requests per load than the other nodes on average (cell medians) [Ref2].</li>
<li><b>In absolute numbers</b> the own node counts about {own_e:.1f} requests per load in the two evicted kinds, and each other node about {oth_e:.2f}. Insufficient data on why the own node counts more than 1.0: the mesh counters do not separate the kinds of request.</li>
<li><b>Not covered by this check:</b> the <code>ocm-flush</code> cells of CPUs 2 to 9 have no mesh counts. Their timing is the only check of their node.</li>
</ul>

<h2>6. A load that goes to memory</h2>
<div class="two">
<div>{path_html}<p class="sub">Example: CPU 8 through node 216. The step counts are exact. The route drawn between two points is schematic.</p></div>
<div>
<ul>
<li><b>Measured</b> (best pass, the 40 cells of CPUs 2 to 9): {g.rng(1, 'dram-flush')[0]:.1f} to {g.rng(1, 'dram-flush')[1]:.1f} ns on boot 1 and {g.rng(2, 'dram-flush')[0]:.1f} to {g.rng(2, 'dram-flush')[1]:.1f} ns on boot 2 [Ref2] [Ref3]. The 7 passes of a cell differ by at most {up2(spread[1]):.2f} ns on boot 1 and {up2(spread[2]):.2f} ns on boot 2.</li>
<li><b>The plain distance to the home node does not explain these cells</b> (rms {g.FIT[(1, 'dram-flush')][1]:.2f} ns).</li>
<li><b>A three-leg path does</b> (rms {t1[0][0]:.3f} ns on boot 1, {t2[0][0]:.3f} ns on boot 2): request to the home node, then on to a memory bridge, then the data directly back to the CPU.</li>
<li><b>Where the bridge is:</b> the fit selects row y = 3. It cannot tell column 0 from column 1: both give an rms of {t1[0][0]:.3f} ns, because no CPU or home node sits left of column 1. The next best crosspoint, ({row_next[1][0]},{row_next[1][1]}), gives {row_next[0]:.2f} ns. The mesh map shows a bridge at (0,3) and none at (1,3) [Ref8], so the page takes (0,3). Of the ten bridges, (0,3) fits best (next best: rms {bridges1[1][0]:.2f} ns).</li>
<li><b>Cost on boot 1:</b> {at(t1, (0, 3))[2][0]:.1f} ns (the base for a bridge at (0,3)) + {t1[0][2][1]:.2f} ns per X step + {t1[0][2][2]:.2f} ns per Y step on that path. On boot 2 the base is {at(t2, (0, 3))[2][0]:.1f} ns and the step costs are {t2[0][2][1]:.2f} and {t2[0][2][2]:.2f} ns.</li>
<li><b>Each step is counted once here</b> (one way). The 2.0 ns and 1.0 ns of section 4 count each step twice: once for the request and once for the data.</li>
<li><b>A path that returns through the home node fits worse</b> (rms {r.VIA[0][0]:.2f} ns).</li>
</ul>
</div></div>
<div class="hyp"><b>Limits on this section.</b><ul>
<li>The path is a hypothesis about routing. Its support is a timing fit of 40 cells on each of boots 1 and 2, with one 2 MiB page per boot.</li>
<li>No counter at a bridge was read. A run with a counter at each memory bridge would confirm or reject the path.</li>
<li>The fit fixes the row of the memory point (y = 3) but not its column (0 or 1).</li>
<li>Boot 3 cannot test the path, because its prefetchers are on.</li>
<li>The absolute values are not silicon values. The emulator's memory is a model, not real DRAM (Jesse's README) [Ref6].</li>
</ul></div>

<h2>7. Which node holds a line</h2>
<ul>
<li><b>The program probed 10,255 DRAM-backed lines per boot</b> with the mesh counters. It found a clear home node for {g.HC[1][1]:,}, {g.HC[2][1]:,} and {g.HC[3][1]:,} of them (boots 1, 2, 3). It left {g.HC[1][4]}, {g.HC[2][4]} and {g.HC[3][4]} lines out, because three probes gave no clear home [Ref4].</li>
<li><b>Arm's manual gives a hash formula</b> from a line's physical address to an index into a table of home nodes [Ref7]. The manual does not give the order of the table.</li>
<li><b>With 5 nodes, the index and the measured node agree for every classified line:</b> {g.HC[1][2]:,} of {g.HC[1][1]:,} on boot 1, {g.HC[2][2]:,} of {g.HC[2][1]:,} on boot 2, {g.HC[3][2]:,} of {g.HC[3][1]:,} on boot 3. The three boots used three different memory pages [Ref4].</li>
<li><b>The table order that the data give is {', '.join(str(x) for x in g.HC[1][3])}.</b> It is the order of the home nodes' numbers #0 to #4 on the mesh map [Ref8].</li>
<li><b>Use:</b> the home node of a DRAM-backed line can be computed from its address. This was tested on three 2 MiB pages whose addresses differ only in bits 6 to 23. For other addresses it is an estimate (est.).</li>
<li><b>Each node holds one fifth of the lines:</b> 2,048 to 2,053 of the classified lines per node.</li>
</ul>

<h2>8. Tests that support the numbers</h2>
<h3>8.1 The trial run (folder 013)</h3>
<p>One command on CPU 2 with 64 lines per cell and one timed pass. It checked the new mesh counter code before the long run. All ten checks passed [Ref1] [Ref6].</p>
<div class="scroll"><table><thead><tr><th>#</th><th>Check</th><th>What the files show</th><th>Result</th></tr></thead><tbody>{reh}</tbody></table></div>
<ul>
<li><b>Note on check 8.</b> Two OCM rows read above the expected 27 ns (27.03 and 27.95 ns). Each row is one pass of 64 loads. The same two cells read 26.30 and 26.78 ns on boot 1 with 2,048 loads.</li>
<li><b>Terms of this table.</b> Probe: 64 flush-and-load pairs of one line while the mesh counters run. Read floor: the counts that one empty read of the mesh counters adds. Frame number (<code>pfn</code>): the number of a physical memory page. <code>perf_cov</code>: the core counter coverage of section 8.2. <code>arm-cmn</code>: the Linux driver of the mesh counters. Taint line: a kernel message printed when a module from outside the kernel tree loads. Unused: defined in section 8.2.</li>
</ul>
<h3>8.2 Complete files</h3>
<div class="scroll"><table><thead><tr><th>Boot</th><th>State of CPUs 2 to 9</th><th>Rows and cells</th><th>Lowest core counter coverage</th><th>Mesh counter level</th><th>Lines probed [Ref4]</th><th>Lines whose home node Arm's hash formula gives [Ref4] [Ref7]</th><th>Chip seconds: the operator's wrapper with the script inside [Ref6], <code>meshmap</code> alone</th></tr></thead><tbody>{whole}</tbody></table></div>
<ul>
<li>Every folder passes its checksums [Ref1].</li>
<li>Coverage 1.0000 means that the core counters ran for the whole of every pass. Level 1 means that all mesh counters opened.</li>
<li>Unused: a line whose probe gave no clear home node three times. The program leaves it out of every chain.</li>
</ul>
<h3>8.3 Control rows with the older program</h3>
<p>Before <code>meshmap</code>, the script ran four rows of <code>latency</code> on flushed OCM lines [Ref5]. They use another program, another chain and 2 timed passes. The <code>meshmap</code> column comes from the map files [Ref2] [Ref3].</p>
<div class="scroll"><table class="num"><thead><tr><th>Boot</th><th>CPU</th><th>Node</th><th><code>latency</code> best, ns</th><th><code>meshmap</code> best, ns</th><th>Difference, ns</th></tr></thead><tbody>{g.ctl_rows}</tbody></table></div>
<ul>
<li><b>Boot 1:</b> the two programs agree to within {g.ctl_max[1]:.2f} ns.</li>
<li><b>Boot 2:</b> to within {g.ctl_max[2]:.2f} ns. Insufficient data on why this is larger.</li>
<li><b>Boot 3:</b> the prefetchers are on, and the two programs are not comparable.</li>
</ul>
<h3>8.4 Counters: did every load take the intended path?</h3>
<div class="scroll"><table class="num"><thead><tr><th>Boot</th><th>Kind</th><th>Loads that left the cluster, per load: lowest / median / highest of 280 passes</th><th>Prefetcher fills, per load: lowest / median / highest</th><th>Requests sent on to memory, per load (cell medians)</th></tr></thead><tbody>{g.cnt_rows}</tbody></table></div>
<ul>
<li><b>What the columns are:</b> all values are for CPUs 2 to 9 (280 passes and 40 cells per boot and kind) [Ref2] [Ref3]. Loads that left the cluster: core counter <code>l3d_refill_rd</code>. Prefetcher fills: core counter <code>l2d_refill_hwprf</code>. Requests sent on to memory: mesh counter <code>mc_reqs</code>, a sum over all five home nodes, shown as the lowest and highest cell median.</li>
<li><b>A dash means not measured.</b> The <code>ocm-flush</code> cells of CPUs 2 to 9 ran before the mesh counters opened.</li>
<li><b>Boot 1:</b> every load left the cluster, and no prefetcher fill occurred, in all four kinds. This is why boot 1 is the map.</li>
<li><b>Single passes read higher than the cell medians.</b> The largest <code>slc</code> pass on boot 1 reads {mc_pass['slc']:.3f} requests to memory per load. One <code>ocm-evict</code> pass on boot 1 (CPU 6, node 344, pass 5) reads {mc_pass['ocm-evict']:.2f} per load. Its time is within 0.12 ns of the passes beside it, and it is not the cell's best pass. <code>mc_reqs</code> counts the whole mesh, so it also counts other traffic.</li>
<li><b>Boot 2, evicted kinds:</b> only about 0.3 of the loads left the cluster (section 9).</li>
<li><b>Boot 3:</b> the first column counts demand loads only. It does not count lines that a prefetcher fetched. On boot 3 it is therefore not the share of loads that left the cluster.</li>
</ul>
<h3>8.5 Independent recomputation</h3>
<ul>
<li>This page takes its numbers from the two scripts that wrote the two source pages: <code>gen_run8_report.py</code> and <code>gen_run8_boots.py</code> [Ref9].</li>
<li>The boot 1 source page records that four independent checkers recomputed its numbers from the raw files on 2026-11-11 [Ref9].</li>
<li>On 2026-11-12, eight checker agents (separate Claude sessions) recomputed the numbers of this page from the raw files with their own scripts. Their findings were applied to this page. The review record lists them [Ref12].</li>
</ul>

<h2>9. What the L3 and the prefetchers change</h2>
<p>One dot is one cell of CPUs 2 to 9. The position is the best ns per load.</p>
<p class="key">{key9}</p>
{strip_html}
<ul>
<li><b>Flushed OCM lines:</b> boots 1 and 2 agree (boot 2 minus boot 1 is {g.d21['ocm-flush'][0]:+.2f} ns on average) [Ref2] [Ref3]. The map does not depend on the L3.</li>
<li><b>Flushed DRAM lines:</b> boot 2 reads above boot 1 in every cell, by {g.d21['dram-flush'][0]:.2f} ns on average ({g.d21['dram-flush'][1]:.2f} to {g.d21['dram-flush'][2]:.2f} ns). Insufficient data on the cause.</li>
<li><b>Evicted kinds on boot 2: 13 to 17 ns, and not a distance map.</b> Only about 0.3 of the loads left the cluster. The cluster kept the other lines. The evictor loads 1.875 MiB (30,720 lines), which is 7.5 times the 256 KiB L3 of a cluster [Ref8] [Ref10].</li>
<li><b>Those cells are a mix of two costs.</b> A model fits the 280 passes of each kind to an rms of {min(mixrms):.2f} to {max(mixrms):.2f} ns. A load that stays in the cluster costs about {g.a_est:.1f} ns est. A load that leaves it costs a base of {base2[0]:.1f} ns est. (<code>ocm-evict</code>) or {base2[1]:.1f} ns est. (<code>slc</code>), plus {unit2[0]:.2f} to {unit2[1]:.2f} ns est. per unit.</li>
<li><b>The model has a third term:</b> the step of passes 4 to 6 (section 10), {step2[0]:.2f} to {step2[1]:.2f} ns est. per load that leaves the cluster. Without this term the rms is {min(mixrms0):.2f} to {max(mixrms0):.2f} ns.</li>
<li><b>Against boot 1:</b> the cost per unit repeats boot 1. The base is higher: the same model gives {base1[0]:.1f} and {base1[1]:.1f} ns on boot 1. The cause is not known. The {g.a_est:.1f} ns est. is a fitted value, not a measured L3 latency.</li>
<li><b>Boot 3, flushed OCM lines:</b> with the prefetchers on, the best values drop to {r3o[0]:.1f} to {r3o[1]:.1f} ns. They still rise with distance, at about one third of boot 1's step cost ({f3[1]:.2f} ns per X step and {f3[2]:.2f} ns per Y step, rms {f3rms:.2f} ns).</li>
<li><b>Boot 3, flushed DRAM lines:</b> the best values drop to {r3d[0]:.1f} to {r3d[1]:.1f} ns, which is {min(ratio3):.2f} to {max(ratio3):.2f} of the boot 1 value. They no longer follow the distance. The best value is not a stable number here: the 7 passes of one cell differ by {g.dram3_spread[0]:.1f} to {g.dram3_spread[1]:.1f} ns, and the cell medians span {med3[0]:.1f} to {med3[1]:.1f} ns.</li>
<li><b>CPU 0:</b> its cluster has the L3 in use and the prefetchers on at every boot [Ref6]. Its 20 cells are therefore not distance numbers.</li>
</ul>

<h2>10. Limits and open questions</h2>
<ul>
<li><b>Emulator, not silicon.</b> The mesh is the chip's design, run by the emulator. The memory is a model, so memory latency is not a silicon value [Ref6].</li>
<li><b>One X and one Y cost for the whole mesh.</b> The CPUs and nodes use columns 1 to 5 and rows 2 to 4. Steps outside that area were not measured.</li>
<li><b>Passes 4 to 6 read {min(HALF):.1f} to {max(HALF):.1f} ns above passes 0 to 3</b> wherever every load comes over the mesh from a cache or the OCM. These passes read bytes 32, 40 and 48, in the upper 32 bytes of the line. Every best value of the map (boot 1: the two OCM kinds and <code>slc</code>; boot 2: <code>ocm-flush</code>) is therefore a lower-half value. The flushed DRAM kind shows no such step. The cause is not known.</li>
<li><b>The slice was compared with the OCM on boot 1 only.</b> On boot 2 the evicted kinds are a mix (section 9).</li>
<li><b>Why the cluster keeps the chain lines on boot 2.</b> In a cluster's first <code>slc</code> cell (node 88), the share of loads that leave the cluster at pass 0 is {', '.join('%.2f' % x for x in sh0)} for CPUs 2, 4, 6 and 8. At pass 6 it is {', '.join('%.2f' % x for x in sh6)}. Later cells stay near 0.3. Two tests would help to find the cause: one cell under the L3 hit counters, and one cell whose evictor stores to its lines.</li>
<li><b>The Y cost on the memory path is {t1[0][2][2]:.2f} ns per step</b>, against 0.5 ns one way in the cache kinds. Insufficient data: the test uses only three rows.</li>
<li><b>Not verified:</b> the firmware state of each boot is taken from Jesse's README. The counters agree with it.</li>
</ul>

<h2>Words used here</h2>
<ul>
<li><b>Asimov emulator</b>: the hardware emulator that runs the chip's design before silicon exists. It is slow: an earlier run took about 2,780 wall-clock seconds for one chip second [Ref11]. Jesse Zhang operates it.</li>
<li><b>Mesh</b>: the chip's interconnect, a grid of 6 x 6 crosspoints. A message moves from one crosspoint to a neighbour at a time. Crosspoints are written (x,y).</li>
<li><b>Step</b>: one move of a message from a crosspoint to its neighbour. <b>Distance unit</b>: a measure of distance used in sections 3 and 4. One X step counts 2 units and one Y step counts 1 unit.</li>
<li><b>L1, L2, L3</b>: the three cache levels of a CPU, from smallest to largest. <b>DRAM</b>: the main memory outside the chip.</li>
<li><b>Cluster</b>: two CPUs that share one L2 cache and one L3 cache, attached to one crosspoint. CPUs 2 to 9 form four clusters for tests. CPUs 0 and 1 run the operating system.</li>
<li><b>Home node</b>: one of five cache nodes on the mesh (ids 88, 160, 216, 288, 344). Each holds two things: a slice of the system-level cache (SLC), and 256 KiB of on-chip memory (OCM).</li>
<li><b>Line</b>: 64 bytes of memory, the unit that caches hold. A <b>DRAM-backed line</b> is a line of normal memory. A hash of its address selects the one home node that may hold it.</li>
<li><b>Memory bridge (SBSX)</b>: a port at the edge of the mesh that leads to memory (DRAM).</li>
<li><b>Dependent load</b>: a load whose address comes from the load before it. The loads of a chain cannot overlap. Time per load is therefore the latency of one load.</li>
<li><b>Flush</b>: an instruction that removes a line from every cache. <b>Evictor</b>: loads of 30,720 other lines of the 2 MiB test buffer. They are meant to push the chain lines out of the cluster's caches. On boot 2 most chain lines stayed in the cluster (section 9).</li>
<li><b>Prefetcher</b>: hardware in a CPU that fetches lines before the program loads them.</li>
<li><b>Cell</b>: one CPU, one home node, one kind of row. <b>Pass</b>: one timed walk of the chain. Passes are numbered 0 to 6. <b>Best</b>: the smallest ns per load of a cell's 7 passes.</li>
<li><b><code>meshmap</code></b>: the program that measures the map. <b><code>run_map.sh</code></b>: the script that runs it [Ref10]. <b><code>latency</code></b>: the older program, used for control rows.</li>
<li><b>Mesh counters</b>: event counters in the mesh. One counter per home node counts the requests that the node received. Three more counters are sums over all five home nodes. <b>Core counters</b>: event counters in a CPU.</li>
<li><b>Boot</b>: one start of the emulator with one firmware setting. <b>rms</b>: root mean square of a fit's errors. <b>est.</b>: an estimate.</li>
</ul>

<h2>References</h2>
<ul>
<li>[Ref1] <code>results/membench-jibin-013/</code> (trial run: <code>map-rehearsal.csv</code>, <code>map-rehearsal-log.txt</code>, <code>map-rehearsal-homes.txt</code>, <code>dmesg.txt</code>) and the <code>SHA256SUMS</code> of folders 013 to 016.</li>
<li>[Ref2] <code>results/membench-jibin-014/results/bootM1/latency-map.csv</code> (boot 1).</li>
<li>[Ref3] <code>results/membench-jibin-015/results/bootM2/latency-map.csv</code> (boot 2) and <code>results/membench-jibin-016/results/bootM3/latency-map.csv</code> (boot 3).</li>
<li>[Ref4] <code>map-homes.txt</code> in the three boot folders.</li>
<li>[Ref5] <code>latency-ocm-region{{0,4}}-mapctl-cpu{{2,8}}.csv</code> in the three boot folders (the control rows of section 8.3).</li>
<li>[Ref6] <code>README.md</code> in folders 013 to 016, written by Jesse's agent.</li>
<li>[Ref7] Arm CMN S3 Technical Reference Manual 107858_0203_05, section 2.4.5.3, page 142.</li>
<li>[Ref8] <code>results/membench-jibin-011/results/bootF1/sysinfo.txt</code>, an earlier boot: lines 489 to 551 (the mesh map) and lines 103 to 104 (the L2 and L3 sizes of a cluster).</li>
<li>[Ref9] <code>run8-meshmap-boot1.html</code> (trial run and boot 1 in full) and <code>run8-meshmap-3boots.html</code> (the three boots in full). This page is written by <code>gen_mesh_map.py</code>.</li>
<li>[Ref10] <code>meshmap.c</code> and <code>run_map.sh</code>, commit 3b12e4f of jhan-positron/asimov, folder <code>cache-mem-perf</code>.</li>
<li>[Ref11] <code>results/membench-jibin-011/README.md</code> line 347 (core clock 2.000 GHz) and <code>results/membench-jibin-004/README.md</code> line 23 (wall-clock seconds per chip second). Both are earlier runs on the same emulator.</li>
<li>[Ref12] <code>asimov-mesh-map.html.review.md</code>, the review record of this page.</li>
</ul>
</main></body></html>"""

assert 'hop' not in page.lower()
open(OUT, 'w').write(page)
print('wrote', OUT, len(page), 'bytes')
