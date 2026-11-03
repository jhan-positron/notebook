#!/usr/bin/env python3
"""make-brief.py - builds crb-memory-hierarchy-brief.html, a two-page A4 results brief for Bill.
Reads the measured data from crb/results and writes static HTML with inline SVG (no script),
so it prints the same way it displays. Usage: make-brief.py <root-run results dir>"""
import csv, json, re, sys, statistics as st, collections, datetime

BASE = '/home/jhan/workspace/titan/cache-perf/crb'
if len(sys.argv) < 2:
    sys.exit('usage: make-brief.py <root-run results dir>  (no default: the brief must name its result set)')
ROOT = sys.argv[1]
F3 = f'{BASE}/results/followup3-20261102T031936Z'

# ---- data ----
P = json.load(open(f'{ROOT}/core-positions.json'))
pos = {int(c): p for c, p in P['pos'].items()}
far = P['far']
lat = [r for r in csv.DictReader(open(f'{ROOT}/full/latency.csv')) if r['node_id_hex'] != 'mixed']
L = collections.defaultdict(dict)
for r in lat:
    L[int(r['core'])][(int(r['mesh']), int(r['x']), int(r['y']))] = min(L[int(r['core'])].get((int(r['mesh']), int(r['x']), int(r['y'])), 99), float(r['ns_median']))
near = [p['nearest'] for p in pos.values()]; hop = [p['per_hop'] for p in pos.values()]
rep_spread = st.median((float(r['ns_max']) - float(r['ns_min'])) / float(r['ns_median']) for r in lat)

def grid(f):
    d = {}; cur = None
    for line in open(f'{F3}/{f}.csv'):
        m = re.match(r'-- kernel (\S+) mesh0 (\d+) mesh1 (\d+)', line)
        if m: cur = (int(m.group(2)), int(m.group(3))); continue
        q = line.strip().split(',')
        if len(q) > 6 and q[3] == 'best': d[cur] = float(q[6])
    return d
W = grid('writegrid'); R = grid('readgrid')

def percore(f):
    d = {}; cpu = None
    for line in open(f'{F3}/{f}'):
        m = re.match(r'-- cpu (\d+)', line)
        if m: cpu = int(m.group(1)); continue
        q = line.strip().split(',')
        if len(q) == 4 and q[1] == 'best': d.setdefault(cpu, []).append(float(q[3]))
    return d
pc1 = percore('percore-latency-1.csv')
fresh = {c: v[1] for c, v in pc1.items() if len(v) > 1}

thr = collections.defaultdict(list)
for r in csv.reader(open(f'{F3}/perthread-asmread-3M-40.csv')):
    if r and r[0] == 'thread' and r[4] == '0': thr[int(r[2]) < 64].append(float(r[5]))
best_3m = [float(r[6]) for r in csv.reader(open(f'{F3}/perthread-asmread-3M-40.csv')) if len(r) > 6 and r[3] == 'best'][0]

# counter rates per line (subtraction method), from the strict analysis
import subprocess
def rates(f):
    r = subprocess.run(['python3', f'/home/jhan/workspace/titan/cache-perf/bench/subtract.py', f'{ROOT}/{f}'], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'subtract.py failed its checks on {f}; the brief is not written:\n' + r.stdout[-2000:])
    d = {}; gb = {}
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) >= 5 and '/' in p[1]:
            try: d[(p[0], p[1])] = float(p[2]); gb.setdefault(p[0], []).append(float(p[4]))
            except ValueError: pass
    return d, gb
RB, GB_B = rates('writebw.csv'); RX, GB_X = rates('crossmesh.csv')
def rate(d, case, mesh, ev):
    k = (case, f'arm_cmn_{mesh}/{ev}/')
    if k not in d: sys.exit(f'required rate missing: {k}')
    return abs(d[k])
def gbs(g, case): return f'{min(g[case]):.0f} to {max(g[case]):.0f}' if max(g[case]) - min(g[case]) > 2 else f'{min(g[case]):.0f}'
def mcsum(case):
    v = [rate(RX, case, m, e) for m in (0, 1) for e in ('hns_mc_reqs_local_all', 'hns_mc_reqs_remote_all')]
    return v, sum(v[0::2]), sum(v[1::2])

# ---- svg helpers ----
def esc(s): return str(s).replace('&', '&amp;').replace('<', '&lt;')
def shade(v, vmin=18, vmax=44):
    k = max(0, min(1, (v - vmin) / (vmax - vmin))); return f'hsl(213 65% {95 - k * 55:.0f}%)'

def mesh_panel(m, X0, Y0, core_of, lat_from, title):
    """7 x 5 grid of crosspoints: core pair on top, latency from one core below, colour = latency"""
    DX, DY, CW, CH = 58, 44, 54, 40
    s = [f'<text x="{X0}" y="{Y0 - 26}" font-size="11.5" font-weight="600">{esc(title)}</text>']
    for x in range(1, 8): s.append(f'<text x="{X0 + (x - 1) * DX + CW / 2}" y="{Y0 - 8}" text-anchor="middle" font-size="9.5" fill="#5b6470">X{x}</text>')
    for y in range(1, 6): s.append(f'<text x="{X0 - 6}" y="{Y0 + (5 - y) * DY + CH / 2 + 3}" text-anchor="end" font-size="9.5" fill="#5b6470">Y{y}</text>')
    for y in range(1, 6):
        for x in range(1, 8):
            X, Y = X0 + (x - 1) * DX, Y0 + (5 - y) * DY
            cs = sorted(c for c, p in pos.items() if p['mesh'] == m and p['x'] == x and p['y'] == y)
            v = lat_from.get((m, x, y))
            if v is None:
                s.append(f'<rect x="{X}" y="{Y}" width="{CW}" height="{CH}" rx="3" fill="#fff" stroke="#9aa3ad" stroke-dasharray="3 2"/>')
                s.append(f'<text x="{X + CW / 2}" y="{Y + 16}" text-anchor="middle" font-size="9" fill="#5b6470">no slice</text>')
                if cs: s.append(f'<text x="{X + CW / 2}" y="{Y + 31}" text-anchor="middle" font-size="9.5" font-weight="600">cores {cs[0]},{cs[-1]}</text>')
                continue
            here = cs and core_of in cs
            s.append(f'<rect x="{X}" y="{Y}" width="{CW}" height="{CH}" rx="3" fill="{shade(v)}" stroke="{"#c8373a" if here else "#fff"}" stroke-width="{2.5 if here else 1}"/>')
            ink = '#fff' if v > 31 else '#1b1f24'
            s.append(f'<text x="{X + CW / 2}" y="{Y + 15}" text-anchor="middle" font-size="8.5" fill="{ink}">{("cores " + str(cs[0]) + "," + str(cs[-1])) if cs else "no cores"}</text>')
            s.append(f'<text x="{X + CW / 2}" y="{Y + 32}" text-anchor="middle" font-size="12" font-weight="600" fill="{ink}">{v:.1f}</text>')
    return '\n'.join(s)

core_map_svg = '<svg viewBox="0 0 880 292" role="img" aria-label="Core positions and slice latency on both meshes">' + \
    mesh_panel(0, 36, 44, 0, {k: v for k, v in L[0].items() if k[0] == 0}, 'mesh 0 (arm_cmn_0), CPUs 0 to 63: ns from CPU 0 to each slice') + \
    mesh_panel(1, 466, 44, 64, {k: v for k, v in L[64].items() if k[0] == 1}, 'mesh 1 (arm_cmn_1), CPUs 64 to 119: ns from CPU 64') + \
    '<text x="36" y="276" font-size="10.5" fill="#5b6470">Each cell is one crosspoint with two 1 MiB slices. Top line: the core pair on its port. Number: median of 7 fresh pointer chases of 2048 lines homed there.</text>' + \
    '<text x="36" y="289" font-size="10.5" fill="#5b6470">Red border: the measuring core. Dashed: a crosspoint without slices. Nearest slice 19 ns, about 2.7 ns per hop, far corner 33 to 44 ns.</text></svg>'

# write grid
A = [0, 16, 32, 48, 64]; Bv = [0, 16, 32, 48, 56]
def wshade(v): k = max(0, min(1, (v - 120) / 280)); return f'hsl(213 65% {96 - k * 58:.0f}%)'
wg = ['<svg viewBox="0 0 430 250" role="img" aria-label="DRAM write bandwidth against writers per mesh">']
X0, Y0, CW, CH = 92, 44, 64, 34
wg.append(f'<text x="{X0 + 2.5 * CW}" y="14" text-anchor="middle" font-size="11" font-weight="600">writers on mesh 1 (CPUs 64 and up)</text>')
for j, b in enumerate(Bv): wg.append(f'<text x="{X0 + j * CW + CW / 2}" y="34" text-anchor="middle" font-size="10" fill="#5b6470">{b}</text>')
wg.append(f'<text x="14" y="{Y0 + 2.5 * CH}" font-size="11" font-weight="600" text-anchor="middle" transform="rotate(-90 14 {Y0 + 2.5 * CH})">writers on mesh 0 (CPUs 0 to 63)</text>')
for i, a in enumerate(A):
    wg.append(f'<text x="{X0 - 8}" y="{Y0 + i * CH + CH / 2 + 4}" text-anchor="end" font-size="10" fill="#5b6470">{a}</text>')
    for j, b in enumerate(Bv):
        x, y = X0 + j * CW, Y0 + i * CH
        if (a, b) not in W:
            wg.append(f'<rect x="{x}" y="{y}" width="{CW - 2}" height="{CH - 2}" fill="#fff" stroke="#d9dde3"/>'); continue
        v = W[(a, b)]; dark = v > 290
        wg.append(f'<rect x="{x}" y="{y}" width="{CW - 2}" height="{CH - 2}" fill="{wshade(v)}" stroke="#fff"/>')
        wg.append(f'<text x="{x + CW / 2 - 1}" y="{y + CH / 2 + 4}" text-anchor="middle" font-size="12" font-weight="600" fill="{"#fff" if dark else "#1b1f24"}">{v:.0f}</text>')
wg.append(f'<text x="{X0}" y="{Y0 + 5 * CH + 16}" font-size="10.5" font-weight="600">DRAM write GB/s, asmwrite 256 MiB per thread, best of 3.</text>')
wg.append(f'<text x="{X0}" y="{Y0 + 5 * CH + 30}" font-size="10" fill="#5b6470">Reads at the same placements: {min(R.values()):.0f} to {max(R.values()):.0f} GB/s, no collapse.</text></svg>')
write_grid_svg = '\n'.join(wg)

# per-core fresh latency strip (120 dots)
pcs = ['<svg viewBox="0 0 430 150" role="img" aria-label="Per-core mesh-cache latency">']
Lm, Rm, T, H = 40, 10, 24, 90
X = lambda c: Lm + (c + 0.5) / 120 * (430 - Lm - Rm); Y = lambda v: T + (1 - (v - 25) / 6) * H
pcs.append('<text x="40" y="14" font-size="11" font-weight="600">fresh 16 MiB chase per CPU, ns (average over all slices)</text>')
for v in (25, 27, 29, 31): pcs.append(f'<line x1="{Lm}" y1="{Y(v)}" x2="{430 - Rm}" y2="{Y(v)}" stroke="#d9dde3"/><text x="{Lm - 4}" y="{Y(v) + 3}" text-anchor="end" font-size="9" fill="#5b6470">{v}</text>')
for c, v in sorted(fresh.items()): pcs.append(f'<circle cx="{X(c):.1f}" cy="{Y(v):.1f}" r="2.2" fill="{"#2a78d6" if c < 64 else "#eb6834"}"/>')
pcs.append(f'<text x="{X(31)}" y="140" text-anchor="middle" font-size="9.5" fill="#2a78d6">mesh 0, CPUs 0 to 63</text><text x="{X(92)}" y="140" text-anchor="middle" font-size="9.5" fill="#eb6834">mesh 1, CPUs 64 to 119</text>')
lo = min(fresh, key=fresh.get); hi = max(fresh, key=fresh.get)
pcs.append(f'<text x="{X(hi) + 6}" y="{Y(fresh[hi]) - 4}" font-size="9.5" font-weight="600">CPU {hi}: {fresh[hi]:.1f}</text><text x="{X(lo) - 6}" y="{Y(fresh[lo]) + 12}" text-anchor="end" font-size="9.5" font-weight="600">CPU {lo}: {fresh[lo]:.1f}</text></svg>')
percore_svg = '\n'.join(pcs)

m0 = thr[True]; m1 = thr[False]
today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
html = f"""<meta charset="utf-8">
<title>CRB Results Brief</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
@page {{ size: A4; margin: 11mm 12mm; }}
:root {{ --ink: #1b1f24; --muted: #5b6470; --rule: #d9dde3; }}
html {{ color-scheme: light; }}
body {{ margin: 0; background: #fff; color: var(--ink); font: 10.5px/1.35 "IBM Plex Sans", "Segoe UI", system-ui, sans-serif; }}
main {{ max-width: 186mm; margin: 0 auto; padding: 6mm max(16px, env(safe-area-inset-right, 0px)) 6mm max(16px, env(safe-area-inset-left, 0px)); }}
h1 {{ font-size: 17px; margin: 0 0 2px; }} h2 {{ font-size: 12.5px; margin: 10px 0 4px; padding-top: 4px; border-top: 1px solid var(--rule); }}
.sub {{ color: var(--muted); margin: 0 0 6px; }}
table {{ border-collapse: collapse; font-size: 10px; font-variant-numeric: tabular-nums; width: 100%; }}
th, td {{ padding: 2px 6px; border-bottom: 1px solid var(--rule); text-align: right; vertical-align: top; }}
th:first-child, td:first-child {{ text-align: left; }} th {{ font-weight: 600; color: var(--muted); font-size: 9.5px; text-transform: uppercase; letter-spacing: .02em; }}
ul {{ margin: 2px 0 4px; padding-left: 18px; }} li {{ margin: 1px 0; }}
.row {{ display: flex; gap: 12px; align-items: flex-start; }} .row > * {{ flex: 1 1 0; min-width: 0; }}
svg {{ width: 100%; height: auto; display: block; font-family: inherit; }}
.cap {{ color: var(--muted); font-size: 9.5px; margin: 2px 0 0; }}
.pb {{ break-before: page; }}
.take {{ font-weight: 600; }}
@media print {{ main {{ padding: 0; max-width: none; }} }}
</style>
<main>
<h1>CRB memory hierarchy: results brief</h1>
<p class="sub">Phoenix Reference Server, 128 Neoverse V3AE at 2.8 GHz, two CMN S3 meshes. Measured 2026-10-30 to 2026-11-02 on CPUs 0 to 119. Full report with methods: crb-memory-hierarchy.html. Brief generated {today}.</p>

<h2>Levels, one core and whole chip</h2>
<table>
<tr><th>Level</th><th>Size</th><th>Load-to-use latency</th><th>Read, 1 core</th><th>Write, 1 core</th><th>Read, whole chip</th><th>Write, whole chip</th></tr>
<tr><td>L1 data, private, 4-way</td><td>64 KiB</td><td>1.43 ns (4 cycles)</td><td>133 GB/s</td><td>89.5 GB/s</td><td>15.9 TB/s</td><td>10.7 TB/s</td></tr>
<tr><td>L2, private, 8-way</td><td>2 MiB</td><td>3.75 ns (10.5)</td><td>85 GB/s</td><td>89.5 GB/s</td><td>10.2 TB/s</td><td>10.7 TB/s</td></tr>
<tr><td>Mesh cache (SLC), 128 slices of 1 MiB, 16-way</td><td>128 MiB (64 MiB seen by one core)</td><td>19 to 44 ns by slice, 29 avg (85)</td><td>67 GB/s</td><td>73 GB/s, goes to DRAM</td><td>≥ 0.62 TB/s served by slices (1.38 TB/s total at 40 threads)</td><td>not cached</td></tr>
<tr><td>DRAM, 10 ch DDR5-8000</td><td>320 GiB</td><td>148 ns (415)</td><td>30 GB/s</td><td>63 GB/s</td><td>533 GB/s (83 % of 640 peak)</td><td>447 GB/s</td></tr>
</table>
<p class="cap">Latency: one dependent load, random chain, prefetch defeated. Per-core bandwidth: one thread, hand-written ldp/stp loop. Whole chip: best placement on CPUs 0 to 119. Cycles at 2.8 GHz.</p>

<h2>Findings</h2>
<ul>
<li class="take">Pair port: cores 2k and 2k+1 share one crosspoint port. Two partners together read 78 GB/s from the mesh cache; two non-partners 134 GB/s.</li>
<li>One writer's 73 GB/s limit is inside the core: no L1/L2 allocation (0 refills, 0 write-backs), no credit stalls on its crosspoint links, and the same port carries 82 GB/s with the partner core, 229 GB/s with 4 writers [sudo-20261102T211150Z/writepath.csv].</li>
<li class="take">Slice distance: nearest slice {min(near):.1f} to {max(near):.1f} ns, {st.median(hop):.1f} ns per crosspoint hop, farthest {min(far):.1f} to {max(far):.1f} ns. Repeat spread {100 * rep_spread:.0f} %.</li>
<li>Every core's position is known from its latency gradient (map below): CPUs 0 to 63 on mesh 0, 64 to 119 on mesh 1, numbered column by column; pairs 34/35 and 98/99 sit on a crosspoint without slices.</li>
<li>Every 2 MiB chunk of memory is split half and half between the two meshes by an address hash (the XOR of address bits 6, 8, ... 20 and higher bits), not line by line. A hit is always served on the core's own mesh, by the home slice or by a proxy slice for lines homed on the other mesh, at the same 19 to 44 ns. A line held only on the other mesh costs about 85 ns on its first access, then it is kept locally. So one core's data lives on its own mesh: one buffer sees 64 MiB, not 128.</li>
<li>Streaming writes largely bypass the mesh cache: {rate(RB, 'asmwrite-8M-1', 0, 'hns_cache_fill_all'):.3f} fills and {rate(RB, 'asmwrite-8M-1', 0, 'hns_mc_reqs_local_all'):.2f} memory requests per line at 8 MiB per thread. The 73 GB/s "mesh write" is mostly the DRAM write path.</li>
<li class="take">DRAM write collapses only with heavy writers on both meshes: 64 writers on one mesh 394 GB/s, 32 on each mesh 173 GB/s. Reads do not collapse. Home-node retry and throttle counts fall in the collapsed case; the bottleneck is not located (hypothesis: chip-to-chip links).</li>
<li>Concurrent reads from the mesh cache: 32 threads on one mesh share about {sum(m0):.0f} GB/s ({min(m0):.0f} to {max(m0):.0f} each); 8 threads on the other mesh get {min(m1):.0f} to {max(m1):.0f} each (3 MiB per thread, one thread per pair, {best_3m:.0f} GB/s total).</li>
</ul>

<h2>Where the cores are, and how far each slice is</h2>
{core_map_svg}

<div class="pb"></div>
<h2>DRAM write bandwidth against writer placement</h2>
<div class="row">
<div>{write_grid_svg}</div>
<div>{percore_svg}<p class="cap">Average mesh-cache latency by core: {min(fresh.values()):.1f} to {max(fresh.values()):.1f} ns, partners equal, two sweeps agree to 0.2 ns. The spread is the core's distance to the slices.</p></div>
</div>

<h2>What the home-node counters say, per 64 B line streamed</h2>
<table>
<tr><th>Stream (threads on mesh 0 cores)</th><th>GB/s</th><th>Slice accesses, own mesh</th><th>Slice fills</th><th>Slice misses</th><th>Memory requests, own mesh</th><th>Accesses on other mesh</th></tr>
<tr><td>asmread 8 MiB, 1 thread</td><td>{70.8:.0f}</td><td>{rate(RB, 'asmread-8M-1', 0, 'hns_slc_sf_cache_access_all'):.2f}</td><td>{rate(RB, 'asmread-8M-1', 0, 'hns_cache_fill_all'):.2f}</td><td>{rate(RB, 'asmread-8M-1', 0, 'hns_cache_miss_all'):.3f}</td><td>{rate(RB, 'asmread-8M-1', 0, 'hns_mc_reqs_local_all'):.3f}</td><td>{rate(RB, 'asmread-8M-1', 1, 'hns_slc_sf_cache_access_all'):.3f}</td></tr>
<tr><td>asmread 8 MiB, 14 threads (112 MiB)</td><td>285</td><td>{rate(RB, 'asmread-8M-14', 0, 'hns_slc_sf_cache_access_all'):.2f}</td><td>{rate(RB, 'asmread-8M-14', 0, 'hns_cache_fill_all'):.2f}</td><td>{rate(RB, 'asmread-8M-14', 0, 'hns_cache_miss_all'):.2f}</td><td>{rate(RB, 'asmread-8M-14', 0, 'hns_mc_reqs_local_all'):.2f}</td><td>{rate(RB, 'asmread-8M-14', 1, 'hns_slc_sf_cache_access_all'):.3f}</td></tr>
<tr><td>asmwrite 8 MiB, 1 thread</td><td>72</td><td>{rate(RB, 'asmwrite-8M-1', 0, 'hns_slc_sf_cache_access_all'):.2f}</td><td>{rate(RB, 'asmwrite-8M-1', 0, 'hns_cache_fill_all'):.3f}</td><td>{rate(RB, 'asmwrite-8M-1', 0, 'hns_cache_miss_all'):.2f}</td><td>{rate(RB, 'asmwrite-8M-1', 0, 'hns_mc_reqs_local_all'):.2f}</td><td>{rate(RB, 'asmwrite-8M-1', 1, 'hns_slc_sf_cache_access_all'):.2f}</td></tr>
<tr><td>asmwrite 1 GiB, 14 threads</td><td>238</td><td>{rate(RB, 'asmwrite-1G-14', 0, 'hns_slc_sf_cache_access_all'):.2f}</td><td>{rate(RB, 'asmwrite-1G-14', 0, 'hns_cache_fill_all'):.3f}</td><td>{rate(RB, 'asmwrite-1G-14', 0, 'hns_cache_miss_all'):.2f}</td><td>{rate(RB, 'asmwrite-1G-14', 0, 'hns_mc_reqs_local_all'):.2f}</td><td>{rate(RB, 'asmwrite-1G-14', 1, 'hns_slc_sf_cache_access_all'):.2f}</td></tr>
</table>
<p class="cap">Rates = (2 s run − 0.2 s run) counts over the byte difference, idle background subtracted, every counter at 100 % running time, checker exit status verified. A read takes the line out of the slice and the L2 eviction writes it back (exclusive allocation), hence accesses ≈ fills on reads. Writes mostly miss and go to memory. The other mesh sees nothing for an 8 MiB working set: its half of the lines is served by proxies on the core's own mesh.</p>

<h2>Cross-mesh write collapse, per line written</h2>
<table>
<tr><th>Writers</th><th>GB/s (long runs)</th><th>Write requests, mesh 0 / 1</th><th>Write retries, mesh 0 / 1</th><th>Memory throttling, mesh 0 / 1</th><th>Memory requests, local (mesh 0 + 1) / remote (0 + 1) / all</th></tr>
<tr><td>64 on mesh 0</td><td>{gbs(GB_X, 'cross-asmwrite-0-63')}</td><td>{rate(RX, 'cross-asmwrite-0-63', 0, 'hns_pocq_reqs_recvd_write'):.2f} / {rate(RX, 'cross-asmwrite-0-63', 1, 'hns_pocq_reqs_recvd_write'):.2f}</td><td>{rate(RX, 'cross-asmwrite-0-63', 0, 'hns_pocq_retry_write'):.3f} / {rate(RX, 'cross-asmwrite-0-63', 1, 'hns_pocq_retry_write'):.3f}</td><td>{rate(RX, 'cross-asmwrite-0-63', 0, 'hns_sn_throttle_write'):.3f} / {rate(RX, 'cross-asmwrite-0-63', 1, 'hns_sn_throttle_write'):.3f}</td><td>{mcsum('cross-asmwrite-0-63')[1]:.2f} / {mcsum('cross-asmwrite-0-63')[2]:.2f} / {sum(mcsum('cross-asmwrite-0-63')[0]):.2f}</td></tr>
<tr><td>32 on each mesh</td><td>{gbs(GB_X, 'cross-asmwrite-0-31_64-95')}</td><td>{rate(RX, 'cross-asmwrite-0-31_64-95', 0, 'hns_pocq_reqs_recvd_write'):.2f} / {rate(RX, 'cross-asmwrite-0-31_64-95', 1, 'hns_pocq_reqs_recvd_write'):.2f}</td><td>{rate(RX, 'cross-asmwrite-0-31_64-95', 0, 'hns_pocq_retry_write'):.3f} / {rate(RX, 'cross-asmwrite-0-31_64-95', 1, 'hns_pocq_retry_write'):.3f}</td><td>{rate(RX, 'cross-asmwrite-0-31_64-95', 0, 'hns_sn_throttle_write'):.3f} / {rate(RX, 'cross-asmwrite-0-31_64-95', 1, 'hns_sn_throttle_write'):.3f}</td><td>{mcsum('cross-asmwrite-0-31_64-95')[1]:.2f} / {mcsum('cross-asmwrite-0-31_64-95')[2]:.2f} / {sum(mcsum('cross-asmwrite-0-31_64-95')[0]):.2f}</td></tr>
<tr><td>32 on each mesh, reads</td><td>{gbs(GB_X, 'cross-asmread-0-31_64-95')}</td><td>{rate(RX, 'cross-asmread-0-31_64-95', 0, 'hns_pocq_reqs_recvd_write'):.2f} / {rate(RX, 'cross-asmread-0-31_64-95', 1, 'hns_pocq_reqs_recvd_write'):.2f}</td><td>0 / 0</td><td>0 / 0</td><td>{mcsum('cross-asmread-0-31_64-95')[1]:.2f} / {mcsum('cross-asmread-0-31_64-95')[2]:.2f} / {sum(mcsum('cross-asmread-0-31_64-95')[0]):.2f}</td></tr>
</table>
<p class="cap">Events per application line, summed as labelled; a remote-homed request is counted at its proxy and at its home, so totals exceed one per line and are not unique writes. Retry and throttle counts fall in the collapsed case; that does not measure home-node utilisation, and the bottleneck is not located. Each event pair comes from its own run, hence the GB/s range.</p>

<h2>Open</h2>
<ul>
<li>Bottleneck of the cross-mesh write collapse: chip-to-chip gateway and memory-controller counters not yet read.</li>
<li>Slice partition between home lines and proxy lines (configuration register, not perf), and the excess whole-mesh accesses and misses beyond the timed loads, recorded but not attributed.</li>
<li>Cross-chiplet first access: 85 to 88 ns per load at 16 MiB for lines the other chiplet's slices hold, 32 ns on the second walk (matches Bill's 81 to 88 ns); remote-slice hits and lines still in the builder's L2 not separated.</li>
</ul>
</main>
"""
open(f'{BASE}/crb-memory-hierarchy-brief.html', 'w', encoding='utf-8').write(html)
print('written', len(html), 'bytes; nearest', min(near), max(near), 'hop', st.median(hop), 'far', min(far), max(far))
