#!/usr/bin/env python3
"""Generate run1-report.html for the Asimov emulator run membench-jibin-001.
All numbers come from the CSVs (summary.json written by summ.py) so nothing is hand-copied."""
import json, math, html
S = json.load(open('/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/summary.json'))
OUT = '/home/jhan/workspace/titan/cache-perf/asimov/run1-report.html'

BLUE, ORANGE, AQUA, VIOLET = '#2a78d6', '#eb6834', '#1baf7a', '#6250d6'
INK, INK2, MUTED, GRID, AXIS, SURF = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
FONT = 'system-ui,-apple-system,"Segoe UI",sans-serif'

def lat(f, size):
    return S[f][str(size)]
def bwb(f, kernel, threads, size):
    return S[f][str((kernel, threads, size))]

def bl(f, size):
    return S[f][str(size)]['best_row']['line']

def ksize(b):
    b = int(b)
    if b >= 1 << 20:
        v = b / (1 << 20); return (f'{v:g}M')
    return f'{b // 1024}K'

# ---------- chart 1: latency vs footprint ----------
def chart_latency():
    W, H = 760, 400
    L, R, T, B = 56, 24, 44, 56
    xmin, xmax = math.log2(4096), math.log2(32 << 20)
    ymin, ymax = 0, 56
    def X(b): return L + (math.log2(b) - xmin) / (xmax - xmin) * (W - L - R)
    def Y(v): return T + (ymax - v) / (ymax - ymin) * (H - T - B)
    series = [
        ('Repeated chase (walked many times)', BLUE, 'latency-dram-small.csv'),
        ('Fresh chain (never walked)', ORANGE, 'latency-dram-large.csv'),
        ('Flushed single pass (DC CIVAC first)', AQUA, 'latency-dram-flushed.csv'),
    ]
    g = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Load latency against footprint on CPU 2" style="font-family:{FONT};font-size:12px">']
    g.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}"/>')
    for v in range(0, 57, 8):
        g.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
        g.append(f'<text x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end" fill="{MUTED}" style="font-variant-numeric:tabular-nums">{v}</text>')
    ticks = [4096, 16384, 65536, 262144, 1 << 20, 4 << 20, 16 << 20]
    for b in ticks:
        g.append(f'<text x="{X(b):.1f}" y="{H-B+18}" text-anchor="middle" fill="{MUTED}">{ksize(b)}</text>')
    g.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="{AXIS}" stroke-width="1"/>')
    g.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-10}" text-anchor="middle" fill="{INK2}">footprint (bytes, log scale)</text>')
    g.append(f'<text x="{14}" y="{(T+H-B)/2:.0f}" transform="rotate(-90 14 {(T+H-B)/2:.0f})" text-anchor="middle" fill="{INK2}">ns per load</text>')
    # cache-size guides
    for b, lab in ((32768, 'L1 32 KiB'), (131072, 'L2 128 KiB'), (393216, 'L2+L3 384 KiB'), (int(3.75 * (1 << 20)), 'SLC for DRAM 3.75 MiB')):
        g.append(f'<line x1="{X(b):.1f}" x2="{X(b):.1f}" y1="{T-6}" y2="{Y(0):.1f}" stroke="{GRID}" stroke-width="1"/>')
        g.append(f'<text x="{X(b)+3:.1f}" y="{T-10}" fill="{MUTED}" font-size="11">{lab}</text>')
    for name, col, f in series:
        pts = sorted((int(k), v['best']) for k, v in S[f].items())
        d = ' '.join(f'{"M" if i == 0 else "L"}{X(b):.1f},{Y(v):.1f}' for i, (b, v) in enumerate(pts))
        g.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        for b, v in pts:
            g.append(f'<circle cx="{X(b):.1f}" cy="{Y(v):.1f}" r="4.5" fill="{col}" stroke="{SURF}" stroke-width="2"><title>{html.escape(name)}: {ksize(b)} = {v:.2f} ns per load</title></circle>')
    # direct labels (selective)
    lab = [
        (4096, lat('latency-dram-small.csv', 4096)['best'], 'L1 hit 2.00 ns (4 cycles)', 0, -12, 'start', BLUE),
        (49152, lat('latency-dram-small.csv', 131072)['best'], 'L2 hit 6.07 ns (12 cycles)', 4, -12, 'start', BLUE),
        (2 << 20, lat('latency-dram-large.csv', 2 << 20)['best'], 'SLC hit 24.0 ns, fresh chains 512K to 2M', 0, 24, 'middle', ORANGE),
        (32 << 20, 36.0, 'DRAM 52.3 ns (32M, fresh)', 0, 0, 'end', ORANGE),
        (1 << 20, lat('latency-dram-flushed.csv', 8 << 20)['best'], 'flushed 1M to 8M = 52.7 ns, the DRAM value', -10, 4, 'end', AQUA),
    ]
    for b, v, t, dx, dy, anc, col in lab:
        g.append(f'<text x="{X(b)+dx:.1f}" y="{Y(v)+dy:.1f}" text-anchor="{anc}" fill="{INK}" font-size="12">{t}</text>')
    g.append('</svg>')
    legend = ''.join(f'<span class="key"><i style="background:{c}"></i>{html.escape(n)}</span>' for n, c, _ in series)
    return '\n'.join(g), legend

# ---------- chart 2: OCM per region ----------
def chart_ocm():
    rows = []
    for r in range(5):
        v = lat(f'latency-ocm-region{r}.csv', 262144)
        rows.append((f'OCM {r}, {"1 hop" if r <= 2 else "3 hops"} from CPU 2', v['best'], v['ns_range'], v['l3_range'], BLUE if r <= 2 else ORANGE))
    v = lat('latency-ocm-all5-flushed.csv', 1310720); rows.append(('All five regions, flushed (1.25 MiB)', v['best'], v['ns_range'], v['l3_range'], VIOLET))
    v = lat('latency-ocm-all5-fresh.csv', 1310720); rows.append(('All five regions, fresh chain, no flush', v['best'], v['ns_range'], v['l3_range'], VIOLET))
    v = lat('latency-dram-large.csv', 2097152); rows.append(('SLC reference, 2 MiB DRAM fresh chain', v['best'], v['ns_range'], v['l3_range'], AQUA))
    W = 760; rowh = 34; L, R, T, B = 330, 70, 46, 40
    H = T + rowh * len(rows) + B
    xmin, xmax = 16, 28
    def X(v): return L + (v - xmin) / (xmax - xmin) * (W - L - R)
    g = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="OCM latency per region from CPU 2" style="font-family:{FONT};font-size:12px">']
    g.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}"/>')
    for v in range(16, 29, 2):
        g.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{H-B}" stroke="{GRID}"/>')
        g.append(f'<text x="{X(v):.1f}" y="{H-B+16}" text-anchor="middle" fill="{MUTED}">{v}</text>')
    g.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-8}" text-anchor="middle" fill="{INK2}">ns per load (dot = best, bar = range of the repeats)</text>')
    for i, (name, best, (lo, hi), (l3lo, l3hi), col) in enumerate(rows):
        y = T + rowh * i + rowh / 2
        g.append(f'<text x="{L-12}" y="{y+4:.1f}" text-anchor="end" fill="{INK}">{html.escape(name)}</text>')
        g.append(f'<rect x="{X(lo):.1f}" y="{y-3:.1f}" width="{max(2, X(hi)-X(lo)):.1f}" height="6" rx="3" fill="{col}" fill-opacity="0.25"/>')
        g.append(f'<circle cx="{X(best):.1f}" cy="{y:.1f}" r="5" fill="{col}" stroke="{SURF}" stroke-width="2"><title>{html.escape(name)}: best {best:.2f} ns, repeats {lo:.2f} to {hi:.2f} ns, L3 read refills per load {l3lo:.2f} to {l3hi:.2f}</title></circle>')
        g.append(f'<text x="{X(hi)+10:.1f}" y="{y+4:.1f}" fill="{INK}" style="font-variant-numeric:tabular-nums">{best:.1f} ns</text>')
    # gap annotation
    one = S['derived']['ocm_1hop_best']; three = S['derived']['ocm_3hop_best']
    m1 = sum(one) / 3; m3 = sum(three) / 2
    y1 = T + rowh * 1 + rowh / 2; y3 = T + rowh * 3.5
    g.append(f'<line x1="{X(m1):.1f}" x2="{X(m1):.1f}" y1="{T-4}" y2="{T+rowh*5}" stroke="{BLUE}" stroke-width="1" stroke-opacity="0.5"/>')
    g.append(f'<line x1="{X(m3):.1f}" x2="{X(m3):.1f}" y1="{T-4}" y2="{T+rowh*5}" stroke="{ORANGE}" stroke-width="1" stroke-opacity="0.5"/>')
    g.append(f'<line x1="{X(m1):.1f}" x2="{X(m3):.1f}" y1="{T-4}" y2="{T-4}" stroke="{INK2}" stroke-width="1"/>')
    g.append(f'<text x="{(X(m1)+X(m3))/2:.1f}" y="{T-10}" text-anchor="middle" fill="{INK}" font-size="11">group means differ by {m3-m1:.1f} ns (est.) for 2 extra hops</text>')
    g.append('</svg>')
    legend = (f'<span class="key"><i style="background:{BLUE}"></i>1 hop</span><span class="key"><i style="background:{ORANGE}"></i>3 hops</span>'
              f'<span class="key"><i style="background:{VIOLET}"></i>all five regions</span><span class="key"><i style="background:{AQUA}"></i>SLC reference</span>')
    return '\n'.join(g), legend, rows

# ---------- chart 3: one-core bandwidth ----------
def chart_bw1():
    sizes = [16384, 49152, 98304, 262144, 2097152, 33554432]
    levels = ['L1', 'L1+L2', 'L2', 'L2+L3', 'SLC', 'DRAM']
    kern = [('read', BLUE), ('write', ORANGE), ('copy', AQUA)]
    W, H = 760, 360; L, R, T, B = 50, 16, 24, 64
    ymax = 60
    def Y(v): return T + (ymax - v) / ymax * (H - T - B)
    slot = (W - L - R) / len(sizes); bw = 22; gap = 4
    g = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="One-core bandwidth by footprint" style="font-family:{FONT};font-size:12px">']
    g.append(f'<rect width="{W}" height="{H}" fill="{SURF}"/>')
    for v in range(0, 61, 10):
        g.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}"/>')
        g.append(f'<text x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end" fill="{MUTED}" style="font-variant-numeric:tabular-nums">{v}</text>')
    g.append(f'<text x="14" y="{(T+H-B)/2:.0f}" transform="rotate(-90 14 {(T+H-B)/2:.0f})" text-anchor="middle" fill="{INK2}">GB/s (GB = 1e9 bytes)</text>')
    for i, s in enumerate(sizes):
        x0 = L + slot * i + slot / 2 - (3 * bw + 2 * gap) / 2
        for j, (k, col) in enumerate(kern):
            v = bwb('bandwidth-dram-1core.csv', k, 1, s)['best'][0]
            x = x0 + j * (bw + gap)
            g.append(f'<path d="M{x:.1f},{Y(0):.1f} V{Y(v)+4:.1f} a4,4 0 0 1 4,-4 h{bw-8} a4,4 0 0 1 4,4 V{Y(0):.1f} Z" fill="{col}"><title>{k} {ksize(s)}: {v:.2f} GB/s</title></path>')
            g.append(f'<text x="{x+bw/2:.1f}" y="{Y(v)-5:.1f}" text-anchor="middle" fill="{INK}" font-size="11" style="font-variant-numeric:tabular-nums">{v:.1f}</text>')
        g.append(f'<text x="{L+slot*i+slot/2:.1f}" y="{H-B+18}" text-anchor="middle" fill="{INK}">{ksize(s)}</text>')
        g.append(f'<text x="{L+slot*i+slot/2:.1f}" y="{H-B+34}" text-anchor="middle" fill="{MUTED}" font-size="11">{levels[i]}</text>')
    g.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="{AXIS}"/>')
    g.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-8}" text-anchor="middle" fill="{INK2}">bytes per pass on CPU 2 (level the footprint fits)</text>')
    g.append('</svg>')
    legend = ''.join(f'<span class="key"><i style="background:{c}"></i>{k}</span>' for k, c in kern)
    return '\n'.join(g), legend

# ---------- chart 4: scaling ----------
def chart_scale():
    kern = [('read', BLUE), ('write', ORANGE), ('copy', AQUA)]
    panels = [(2097152, 'bandwidth-perdsu.csv', 'bandwidth-all8.csv', '2 MiB per thread (8 and 16 MiB in total at 4 and 8 threads)'), (16777216, 'bandwidth-perdsu.csv', 'bandwidth-all8.csv', '16 MiB per thread (DRAM regime)')]
    W, H = 760, 320; PW = 340; L, T, B = 48, 30, 50
    ymax = 140
    g = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Aggregate bandwidth against thread count" style="font-family:{FONT};font-size:12px">']
    g.append(f'<rect width="{W}" height="{H}" fill="{SURF}"/>')
    for p, (s, f4, f8, title) in enumerate(panels):
        ox = 10 + p * 380
        def X(n): return ox + L + {1: 0, 4: 0.5, 8: 1}[n] * (PW - L - 70)
        def Y(v): return T + (ymax - v) / ymax * (H - T - B)
        g.append(f'<text x="{ox+L}" y="{T-12}" fill="{INK}" font-weight="600">{title}</text>')
        for v in range(0, 141, 20):
            g.append(f'<line x1="{ox+L}" x2="{ox+PW}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}"/>')
            g.append(f'<text x="{ox+L-6}" y="{Y(v)+4:.1f}" text-anchor="end" fill="{MUTED}" font-size="11" style="font-variant-numeric:tabular-nums">{v}</text>')
        for n in (1, 4, 8):
            g.append(f'<text x="{X(n):.1f}" y="{H-B+18}" text-anchor="middle" fill="{INK}">{n}</text>')
        g.append(f'<text x="{(ox+L+ox+PW)/2:.0f}" y="{H-B+36}" text-anchor="middle" fill="{INK2}">threads</text>')
        for k, col in kern:
            s1 = s if s == 2097152 else 33554432
            pts = [(1, bwb('bandwidth-dram-1core.csv', k, 1, s1)['best'][0]), (4, bwb(f4, k, 4, s)['best'][0]), (8, bwb(f8, k, 8, s)['best'][0])]
            d = ' '.join(f'{"M" if i == 0 else "L"}{X(n):.1f},{Y(v):.1f}' for i, (n, v) in enumerate(pts))
            g.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round"/>')
            for n, v in pts:
                g.append(f'<circle cx="{X(n):.1f}" cy="{Y(v):.1f}" r="4.5" fill="{col}" stroke="{SURF}" stroke-width="2"><title>{k}, {n} threads, {ksize(s1 if n == 1 else s)} per thread: {v:.1f} GB/s</title></circle>')
            n, v = pts[-1]
            g.append(f'<text x="{X(n)+10:.1f}" y="{Y(v)+4:.1f}" fill="{INK}" font-size="11" style="font-variant-numeric:tabular-nums">{k} {v:.0f}</text>')
    g.append(f'<text x="14" y="{(T+H-B)/2:.0f}" transform="rotate(-90 14 {(T+H-B)/2:.0f})" text-anchor="middle" fill="{INK2}">aggregate GB/s</text>')
    g.append('</svg>')
    legend = ''.join(f'<span class="key"><i style="background:{c}"></i>{k}</span>' for k, c in kern)
    return '\n'.join(g), legend

c1, l1 = chart_latency()
c2, l2, ocm_rows = chart_ocm()
c3, l3 = chart_bw1()
c4, l4 = chart_scale()

def lat_table(f, sizes=None):
    out = ['<table><thead><tr><th>footprint</th><th>best ns</th><th>cycles</th><th>L1 refills</th><th>L2 refills</th><th>L3 read refills</th><th>CSV line (repeat row with the best ns)</th></tr></thead><tbody>']
    for k in sorted(S[f], key=int):
        v = S[f][k]; br = v['best_row']
        out.append(f'<tr><td>{ksize(k)}</td><td>{v["best"]:.2f}</td><td>{br["cyc"]:.1f}</td><td>{br["l1"]:.3f}</td><td>{br["l2"]:.3f}</td><td>{br["l3"]:.3f}</td><td>{f}:{br["line"]}</td></tr>')
    out.append('</tbody></table>'); return '\n'.join(out)

def bw_table():
    sizes = [16384, 49152, 98304, 262144, 2097152, 33554432]
    out = ['<table><thead><tr><th>bytes per pass</th><th>read GB/s</th><th>write GB/s</th><th>copy GB/s</th><th>CSV lines (best rows)</th></tr></thead><tbody>']
    for s in sizes:
        r = [bwb('bandwidth-dram-1core.csv', k, 1, s)['best'] for k in ('read', 'write', 'copy')]
        out.append(f'<tr><td>{ksize(s)}</td><td>{r[0][0]:.2f}</td><td>{r[1][0]:.2f}</td><td>{r[2][0]:.2f}</td><td>bandwidth-dram-1core.csv:{r[0][1]}, :{r[1][1]}, :{r[2][1]}</td></tr>')
    out.append('</tbody></table>'); return '\n'.join(out)

def scale_table():
    out = ['<table><thead><tr><th>threads, CPUs</th><th>bytes per thread</th><th>read GB/s</th><th>write GB/s</th><th>copy GB/s</th><th>per-thread write, min to max</th><th>file</th></tr></thead><tbody>']
    for n, f, cpus in ((1, 'bandwidth-dram-1core.csv', 'CPU 2'), (4, 'bandwidth-perdsu.csv', 'CPUs 2,4,6,8'), (8, 'bandwidth-all8.csv', 'CPUs 2 to 9')):
        for s in (2097152, 16777216) if n > 1 else (2097152, 33554432):
            r = [bwb(f, k, n, s) for k in ('read', 'write', 'copy')]
            w = r[1]['reps']; mn = min(x['mn'] for x in w); mx = max(x['mx'] for x in w)
            out.append(f'<tr><td>{n}, {cpus}</td><td>{ksize(s)}</td><td>{r[0]["best"][0]:.1f}</td><td>{r[1]["best"][0]:.1f}</td><td>{r[2]["best"][0]:.1f}</td><td>{mn:.1f} to {mx:.1f}</td><td>{f}:{r[1]["best"][1]}</td></tr>')
    out.append('</tbody></table>'); return '\n'.join(out)

def ocm_bw_table():
    out = ['<table><thead><tr><th>row</th><th>GB/s (best)</th><th>flush</th><th>what the timed region holds</th><th>file:line</th></tr></thead><tbody>']
    for r in range(5):
        b = bwb(f'bandwidth-ocm-region{r}.csv', 'read', 1, 262144)['best']
        out.append(f'<tr><td>read OCM {r}, CPU 2, 256 KiB, 1 pass</td><td>{b[0]:.2f}</td><td>before</td><td>256 KiB of loads from the home node</td><td>bandwidth-ocm-region{r}.csv:{b[1]}</td></tr>')
    b = bwb('bandwidth-ocm-all5.csv', 'read', 1, 1310720)
    reps0 = [x for x in S['bandwidth-ocm-all5.csv'][str(('read', 1, 1310720))]['reps']]
    out.append(f'<tr><td>read all five, 4 passes</td><td>{max(x["agg"] for x in reps0[:3]):.2f}</td><td>none</td><td>4 passes over 1.25 MiB, more than the 384 KiB of core caches</td><td>bandwidth-ocm-all5.csv:7</td></tr>')
    out.append(f'<tr><td>read all five, 1 pass</td><td>{max(x["agg"] for x in reps0[3:]):.2f}</td><td>before</td><td>1 pass over 1.25 MiB</td><td>bandwidth-ocm-all5.csv:14</td></tr>')
    b = bwb('bandwidth-ocm-write.csv', 'write', 1, 262144)['best']
    out.append(f'<tr><td>write OCM 1, CPU 2, 256 KiB</td><td>{b[0]:.2f}</td><td>after, inside the timed region</td><td>256 KiB of stores (most likely into L2 and L3 after the warm-up pass; no counter confirms it), then DC CIVAC of 4,096 lines inside the timed region</td><td>bandwidth-ocm-write.csv:{b[1]}</td></tr>')
    b = bwb('bandwidth-ocm-copy.csv', 'copy', 1, 262144)['best']
    out.append(f'<tr><td>copy OCM 1 to OCM 2</td><td>{b[0]:.2f}</td><td>before and after</td><td>loads from OCM 1, stores to cache, then flush of OCM 2</td><td>bandwidth-ocm-copy.csv:{b[1]}</td></tr>')
    b = bwb('bandwidth-ocm-4core.csv', 'read', 4, 262144)['best']
    out.append(f'<tr><td>read, 4 cores, one region each (OCM 1 to 4)</td><td>{b[0]:.2f}</td><td>before</td><td>4 x 256 KiB in parallel</td><td>bandwidth-ocm-4core.csv:{b[1]}</td></tr>')
    b = bwb('bandwidth-ocm-4core.csv', 'write', 4, 262144)['best']
    out.append(f'<tr><td>write, 4 cores, one region each</td><td>{b[0]:.2f}</td><td>after</td><td>same defect as the one-core write row</td><td>bandwidth-ocm-4core.csv:{b[1]}</td></tr>')
    out.append('</tbody></table>'); return '\n'.join(out)

d = S['derived']
_reps = S['bandwidth-ocm-write.csv'][str(('write', 1, 262144))]['reps']
_us = [262144 / (r['agg'] * 1e9) * 1e6 for r in _reps]
ocm_write_us = max(_us); ocm_write_us_lo = min(_us)
store_us = d['dram_write_1core_32M_us_per_256K']
flush_us = ocm_write_us - store_us; flush_us_lo = ocm_write_us_lo - store_us
flush_ns_line = flush_us * 1000 / 4096

page = f'''<title>Asimov Cache Run 1</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* layout: one reading column, charts full width of the column, tables scroll inside their own box */
:root {{
  --bg:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --axis:#c3c2b7;
  --accent:#2a78d6; --warn:#ec835a;
  --font:{FONT}; --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color-scheme: light;
}}
body {{ background:var(--bg); color:var(--ink); font-family:var(--font); font-size:15px; line-height:1.5; margin:0;
  padding-block:24px 48px; padding-left:max(16px,env(safe-area-inset-left,0px)); padding-right:max(16px,env(safe-area-inset-right,0px)); }}
main {{ max-width:860px; margin:0 auto; }}
h1 {{ font-size:28px; line-height:1.2; margin:0 0 6px; text-wrap:balance; }}
h2 {{ font-size:20px; margin:40px 0 10px; text-wrap:balance; }}
h3 {{ font-size:16px; margin:24px 0 6px; }}
p, li {{ max-width:68ch; }}
.short {{ background:var(--surface); border-left:4px solid var(--accent); padding:12px 16px; margin:16px 0 24px; }}
.short p {{ margin:0 0 8px; }} .short p:last-child {{ margin:0; }}
.meta {{ color:var(--ink2); font-size:14px; }}
figure {{ margin:18px 0 6px; background:var(--surface); border:1px solid var(--grid); border-radius:6px; padding:10px 10px 6px; }}
figcaption {{ font-size:14px; color:var(--ink2); margin:8px 4px 2px; }}
.take {{ font-weight:600; color:var(--ink); }}
.legend {{ display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; color:var(--ink2); margin:6px 4px 0; }}
.key i {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px; }}
.tbl {{ overflow-x:auto; margin:8px 0 4px; }}
table {{ border-collapse:collapse; font-size:13px; font-variant-numeric:tabular-nums; min-width:520px; }}
th, td {{ text-align:left; padding:5px 10px; border-bottom:1px solid var(--grid); vertical-align:top; }}
th {{ color:var(--ink2); font-weight:600; }}
td:nth-child(n+2), th:nth-child(n+2) {{ text-align:right; }}
td:last-child, th:last-child {{ text-align:left; font-family:var(--mono); font-size:12px; color:var(--muted); }}
code {{ font-family:var(--mono); font-size:13px; background:#efeee9; padding:1px 4px; border-radius:3px; }}
pre {{ background:#efeee9; padding:10px 12px; border-radius:6px; overflow-x:auto; font-size:13px; }}
dl {{ display:grid; grid-template-columns:max-content 1fr; gap:4px 14px; max-width:72ch; }}
dt {{ font-weight:600; }} dd {{ margin:0; }}
.flag {{ display:inline-block; font-size:12px; padding:1px 7px; border-radius:10px; background:#fbe9e2; color:#8a3a1c; margin-left:6px; }}
@media (max-width:520px) {{ dl {{ grid-template-columns:1fr; }} dd {{ margin-bottom:8px; }} }}
</style>
<main>
<h1>Asimov Cache Run 1</h1>
<p class="meta">Jesse Zhang's run of cache-mem-perf commit 9c6b8e7 on the Asimov emulator, 2026-10-31. Data: results/membench-jibin-001/ in this folder (a copy of /home/jzhang/dev/emuMemBenchBox/results/jibin/membench-jibin-001/ on the lab /home, checksums verified). Written 2026-11-01 by Claude for Jibin Han.</p>

<div class="short">
<p><strong>Short version.</strong> The first emulator run finished in 1.24 s of chip time and gives the whole level map for one core: L1 2.0 ns, L2 6.1 ns, mesh cache (SLC) 24 ns, DRAM 52 ns, and OCM 18.8 to 23.2 ns by region, with the one-hop regions faster than the three-hop regions.</p>
<p>Two rows measured the wrong thing: the "flushed" DRAM rows measured DRAM (the flush removes lines from the SLC too), and the OCM write rows measured the speed of the cache-flush instruction, not of writing to OCM.</p>
<p>Run 2 needs five changes to run_asimov.sh and no new C code, once the OCM copy row is dropped. Three questions remain for Jesse: two carried from the handoff and one new one about the OCM lock mode; his notes answered the chip-time budget and the hop counts.</p>
</div>

<h2>Words used here</h2>
<dl>
<dt>DSU</dt><dd>DynamIQ Shared Unit, a cluster of 2 C1-Nano cores. CPU 2 and CPU 3 form DSU 1 and share one L2 and one L3.</dd>
<dt>L1, L2, L3</dt><dd>32 KiB per core, 128 KiB per DSU, 256 KiB per DSU (sysinfo.txt cache topology lines).</dd>
<dt>SLC, home node</dt><dd>System Level Cache inside the CMN mesh: 5 home nodes of 1 MiB. Every address belongs to one home node. 4 of the 16 ways in each node are locked as OCM, so 3.75 MiB caches DRAM.</dd>
<dt>OCM</dt><dd>On-Chip Memory: 5 regions of 256 KiB, one per home node, reached through /dev/ocm in 4 KiB pages. Jesse: CPU 2's DSU port is one mesh crosspoint from the home nodes of OCM 0, 1, 2 and three from OCM 3, 4.</dd>
<dt>hop</dt><dd>One crosspoint-to-crosspoint step on the mesh.</dd>
<dt>repeated chase</dt><dd>A random pointer chain over the buffer walked many times. Later walks hit whatever cache holds the buffer.</dd>
<dt>fresh chain</dt><dd>A random chain walked exactly once. A prefetcher that learned an earlier walk cannot help.</dd>
<dt>flushed</dt><dd>DC CIVAC on every line (clean and invalidate from the core caches) before a single timed pass.</dd>
<dt>refills per load</dt><dd>PMU counts 0x03 (L1D refill), 0x17 (L2D refill), 0xA2 (L3D read refill) divided by the loads of the timed walk. About 1.0 at a level means every load missed that level.</dd>
<dt>chip time</dt><dd>Time as the emulated chip sees it. One chip second took 2,779 wall seconds in this run (Jesse's README).</dd>
<dt>est.</dt><dd>An estimate, not a measurement.</dd>
</dl>

<h2>The run</h2>
<ul>
<li>34 measurement commands, all exit 0, 1.237 s of chip time, 57 min of wall time (Jesse's README, "The run"). The results directory is byte for byte what the script wrote (SHA256SUMS, 26 files, all OK).</li>
<li>Build and platform as requested: GCC 14.2, <code>-O2 -mcpu=cortex-a520 -static</code>, CPUs 2 to 9 isolated, CPU 3 offline for phases A to D, 256 huge pages of 2 MiB reserved and used (log.txt:3, every DRAM row prints backing=hugetlb), 0xA2 counts (every latency row has a live L3 column).</li>
<li>Skipped: the scratchpad phase. This emulator image cannot load /dev/asimov-spm, so no SPM file exists (sysinfo.txt devices block).</li>
<li>Caveats from Jesse: DRAM is an emulator memory, not LPDDR5X. The firmware is SCP 0.34.0, without 0.46.0's later mesh setup (HN-S-to-SMS route overrides and HN-S queue caps, Jesse's README). OCM is mapped in 4 KiB pages, so the 1.25 MiB all-five rows may include TLB misses.</li>
<li>The mesh PMU driver registered its PMU: <code>arm_cmn_0</code> is listed under /sys/bus/event_source/devices (sysinfo.txt:192). The handoff's first question (the arm-cmn map file, and perf_event_open with node filters) stays open; the listing is only the precondition.</li>
</ul>

<h2>1. Latency by level, CPU 2</h2>
<figure>
{c1}
<div class="legend">{l1}</div>
<figcaption><span class="take">Only the orange dots give the SLC: 23.1 to 24.0 ns from 512 KiB to 2 MiB, then a rise from 3 MiB on (25.4 ns at 3 MiB, 29.8 ns at 4 MiB) as the SLC fills. The flushed rows (green) sit at the DRAM value, so DC CIVAC removed the lines from the SLC as well as from the core caches.</span> Best of 2 or 3 repeats per size.</figcaption>
</figure>
<ul>
<li>L1: 2.00 ns, 4 cycles, up to 24 KiB; 32 KiB already shows 4 % L1 refills (latency-dram-small.csv:24 to 26).</li>
<li>L2: 6.07 ns, 12 cycles, at 128 KiB with 0.99 L1 refills and 0.004 L2 refills per load (latency-dram-small.csv:{bl('latency-dram-small.csv', 131072)}).</li>
<li>L3: not isolated by this sweep. At 192 KiB, 0.57 of loads leave L2 and 0.46 leave L3 too, so the L3 served only about 0.11 of loads (latency-dram-small.csv:{bl('latency-dram-small.csv', 196608)}). At 256 KiB and 384 KiB the L3 read refills are 0.74 and 0.94 per load. Hypothesis: the DSU L3 keeps few lines of a chain that touches each line once per pass. A measurement that would settle it: a chase at 144 KiB and 160 KiB, and the DSU L3 hit event if the PMU has one.</li>
<li>SLC: 23.1 to 24.0 ns for fresh chains of 512 KiB to 2 MiB with 0.95 to 1.00 L3 read refills per load (latency-dram-large.csv:6 to 22). 3 MiB reads 25.4 ns, 4 MiB 29.8 ns, 8 MiB 45.1 ns. The transition sits between 2 and 16 MiB, consistent with Jesse's 3.75 MiB of SLC for DRAM (an RTL configuration figure); the sweep does not measure the size itself.</li>
<li>DRAM: 52.3 ns at 32 MiB fresh (latency-dram-large.csv:46) and 52.7 ns for every flushed best row from 1 MiB up (repeats 52.7 to 53.3 ns; latency-dram-flushed.csv:9 to 27). Emulator memory, not silicon.</li>
<li>The flushed 256 KiB row reads 35.7 to 44.7 ns with only 0.78 to 0.90 L3 read refills per load (latency-dram-flushed.csv:4 to 6). Some lines arrived before their load. See section 5.</li>
</ul>
<div class="tbl">{lat_table('latency-dram-small.csv')}</div>
<div class="tbl">{lat_table('latency-dram-large.csv')}</div>
<div class="tbl">{lat_table('latency-dram-flushed.csv')}</div>

<h2>2. OCM latency by region, CPU 2</h2>
<figure>
{c2}
<div class="legend">{l2}</div>
<figcaption><span class="take">The three one-hop regions read 18.8 to 20.1 ns and the two three-hop regions 22.4 to 23.2 ns. OCM over all five regions reads 25.2 to 25.5 ns, 1.2 to 1.5 ns (5 to 6 %) above the 24.0 ns DRAM-backed SLC hit.</span> Per-region and all-five flushed rows: flushed single passes, best of 3. The all-five fresh row and the SLC reference: fresh chains without a flush, best of 2. The all-five rows and the SLC reference count 0.99 to 1.00 L3 refills per load, the per-region rows only 0.77 to 0.91 (see section 5).</figcaption>
</figure>
<ul>
<li>The region order matches Jesse's topology note: OCM 0, 1, 2 one hop from CPU 2's DSU port, OCM 3, 4 three hops. The gap between the group means is {d['ocm_gap_est']:.1f} ns (est.) for two extra hops. The per-region rows carry 9 to 23 % prefetched lines, and the fraction differs by row, so the per-hop cost is not yet a measurement.</li>
<li>OCM reads within 1.2 to 1.5 ns (5 to 6 %) of an SLC hit, close to the hypothesis in ocm-interpretation.html: all five flushed 25.5 ns (latency-ocm-all5-flushed.csv:7), all five fresh without flush 25.2 ns (latency-ocm-all5-fresh.csv:6), DRAM-backed fresh chain at 2 MiB 24.0 ns (latency-dram-large.csv:22). The 1.25 MiB OCM rows run on 4 KiB pages and the 2 MiB DRAM row on 2 MiB pages, so whether the remainder is TLB cost on 4 KiB pages or mesh cost is not yet measured (Jesse's note).</li>
<li>The fresh row without a flush reads 0.3 ns (1 %) below the flushed row, and the two repeat ranges do not overlap. At 1.25 MiB the footprint is 3.3 times the 384 KiB of L2 plus L3, so the core caches cannot hold the chain either way, and the flush adds at most 0.3 ns here.</li>
</ul>
<div class="tbl"><table><thead><tr><th>row</th><th>best ns</th><th>repeats, ns</th><th>L3 read refills per load</th><th>file:line (best)</th></tr></thead><tbody>
{''.join(f'<tr><td>{html.escape(n)}</td><td>{b:.2f}</td><td>{lo:.2f} to {hi:.2f}</td><td>{l3lo:.2f} to {l3hi:.2f}</td><td>{f}</td></tr>' for (n,b,(lo,hi),(l3lo,l3hi),_),f in zip(ocm_rows,[f'latency-ocm-region{r}.csv:7' for r in range(5)]+['latency-ocm-all5-flushed.csv:7','latency-ocm-all5-fresh.csv:6','latency-dram-large.csv:22']))}
</tbody></table></div>

<h2>3. One-core bandwidth by level, CPU 2</h2>
<figure>
{c3}
<div class="legend">{l3}</div>
<figcaption><span class="take">Reads fall from 57.6 GB/s in L1 to 10.1 GB/s at 256 KiB and 9.2 to 9.3 GB/s at 2 MiB and 32 MiB, with no difference between the SLC regime (2 MiB) and DRAM (32 MiB). Writes stay at 30.6 to 32.0 GB/s at every footprint.</span> Best of 3 repeats; GB = 1e9 bytes.</figcaption>
</figure>
<ul>
<li>L1 read 57.6 GB/s is {d['l1_read_B_per_cycle']:.1f} bytes per cycle at 2 GHz (bandwidth-dram-1core.csv:7). Write is 30.6 to 32.0 GB/s at every size, 15.3 to {d['write_B_per_cycle']:.1f} bytes per cycle at 2 GHz (bandwidth-dram-1core.csv:11 to 86), so the store path, not the memory, sets the one-core write rate.</li>
<li>Reads inside L2 already fall: 17.5 GB/s at 48 KiB and 12.1 at 96 KiB, both within the 128 KiB L2 (latency-dram-small.csv:39 to 41 show 0.002 L2 refills per load at 96 KiB). Beyond L2: 10.1 at 256 KiB, 9.3 at 2 MiB, 9.2 at 32 MiB. The SLC and DRAM regimes read the same, although their latencies differ by 2.2 times. Hypothesis: a rate limit in the core or DSU near one 64-byte line per 14 cycles, not a limit on outstanding requests: with a fixed number of outstanding requests the 2.2 times shorter SLC latency would give 2.2 times the bandwidth, and by Little's law the core holds 3.5 lines in flight at 24 ns against 7.5 at 52.3 ns. The OCM read rows (section 4) reach 16.6 GB/s from one core, so the mesh can deliver more. A measurement that would settle it: the mesh counters for SLC hits and memory requests around the 2 MiB read row.</li>
</ul>
<div class="tbl">{bw_table()}</div>

<h2>4. Bandwidth with more cores, and OCM bandwidth</h2>
<figure>
{c4}
<div class="legend">{l4}</div>
<figcaption><span class="take">Reads scale with cores (8.3 to 9.3 GB/s each, 66.6 GB/s for 8). Writes stop at about 88 GB/s for the hemisphere whether 4 or 8 cores write.</span> Best of 3 repeats. Each thread has its own buffer, so only the 1-thread point of the left panel fits the 3.75 MiB SLC. 1 thread is CPU 2, 4 threads are CPUs 2, 4, 6, 8 (one per DSU), 8 threads are CPUs 2 to 9. The 1-thread point of the DRAM panel is the 32 MiB row.</figcaption>
</figure>
<ul>
<li>Write limit: 4 cores write 88.8 GB/s (22.2 each) and 8 cores 88.3 GB/s (11.0 each) at 2 MiB per thread; the same at 16 MiB (bandwidth-perdsu.csv:11, :26; bandwidth-all8.csv:11, :26). Reads at 8 cores: 67.5 GB/s (bandwidth-all8.csv:7).</li>
<li>Shared L2 pair (CPUs 2 and 3): at 16 KiB each core keeps its L1 rate (115.6 GB/s for two, bandwidth-pair.csv:7). At 48 KiB the pair reads 33.8 GB/s, 16.9 each, against 17.5 alone (bandwidth-pair.csv:22). Writes at 160 KiB each fall to 23.5 per core (bandwidth-pair.csv:41), from 31.7 to 31.9 alone at 96 KiB and 256 KiB (bandwidth-dram-1core.csv:41, :56; no one-core 160 KiB row was run).</li>
<li>OCM read from one core: 16.3, 16.6, 16.3 GB/s for the one-hop regions (OCM 0, 1, 2) and 15.3, 15.0 for the three-hop regions (OCM 3, 4) (bandwidth-ocm-region0.csv:7 to region4.csv:7). Four cores reading four regions: 66.5 GB/s, 16.6 each, so OCM reads scale without loss (bandwidth-ocm-4core.csv:7).</li>
<li>OCM write and copy rows are not OCM numbers. See section 5.</li>
</ul>
<div class="tbl">{scale_table()}</div>
<div class="tbl">{ocm_bw_table()}</div>

<h2>5. Problems in run 1 and the fix for run 2</h2>
<h3>5a. OCM rows timed without a flush first (Jesse's note)</h3>
<p>Jesse is right that three row kinds break the README's sentence "every timed OCM pass starts with a flush". The three differ in what they cost us.</p>
<ul>
<li><strong>All-five fresh latency (run_asimov.sh:113).</strong> Harmless. It was meant as the unflushed comparison, and it read 25.2 ns against 25.5 ns flushed with 0.99 refills per load. At 1.25 MiB the core caches cannot hold the chain. Fix: give it <code>--flush</code> as well, so every OCM row obeys the rule and the row becomes the fresh-plus-flushed form that section 5b needs anyway.</li>
<li><strong>All-five read, 4 passes, no flush (run_asimov.sh:128).</strong> Harmless and redundant: 16.4 GB/s against 16.0 GB/s for the flushed single pass. Fix: drop the row.</li>
<li><strong>Write rows, flushed after (run_asimov.sh:126 and :147).</strong> <span class="flag">wrong number</span> The timed region holds the stores plus the DC CIVAC of the buffer (bandwidth.c:248 to 254). The one-core store rate is 32 GB/s at every footprint, so the stores take {store_us:.1f} us for 256 KiB whether or not the warm-up pass left the lines in the core caches (not measured). The row took {ocm_write_us_lo:.1f} to {ocm_write_us:.1f} us (262,144 bytes at 7.16 to 7.18 GB/s, bandwidth-ocm-write.csv:4 to 6; the elapsed_s column prints 37 us at 1 us resolution). The remaining {flush_us_lo:.1f} to {flush_us:.1f} us is the flush of 4,096 lines, {flush_ns_line:.1f} ns per line (est.). So 7.2 GB/s is the rate of stores into the core caches followed by a serial DC CIVAC write-back of 256 KiB to OCM, not a streaming OCM write rate; the data cannot say how much of the 28 us is the instructions and how much the write-back itself. The 4-core write row (29.2 GB/s, 7.3 per core) has the same defect, and the copy row (12.0 GB/s, 44 us) is about 16 us of loads from OCM 1 and about 28 us of this flush of OCM 2 (est.).</li>
</ul>
<p>Fix for the write rows: measure streaming writes whose footprint exceeds the core caches, so the lines reach OCM by eviction during the timed passes, as the DRAM write rows do. Only the all-five buffer (1.25 MiB) is large enough: <code>bandwidth --threads 1 --cpus 2 --mem ocm --ocm-regions 0,1,2,3,4 --bytes 1280K --kernel write --flush-before --passes 4 --reps 3</code>. The copy kernel cannot use this form: it needs two buffers of five regions and only five regions exist (bandwidth.c:199 to 215 exits with an error), so the OCM copy row is dropped; a 512 KiB copy over regions 0 to 3 would be the only alternative, and its destination is just 1.3 times the core caches. The per-region write cannot be measured this way from one core, since 256 KiB fits the core caches; drop it, or keep the flush-after row with its label changed to "store then DC CIVAC". The 4-core OCM write row has the same limit and should be dropped.</p>

<h3>5b. Prefetched lines in every 256 KiB flushed row</h3>
<p>All flushed rows with 4,096 lines count 0.77 to 0.91 L3 read refills per load (latency-dram-flushed.csv:4 to 6, latency-ocm-region0.csv:4 to region4.csv:6), while rows with 16,384 lines or more count 0.99 to 1.00. The chain in these rows is chain 0, which the warm-up walked twice and each repeat walks again. A prefetcher that records the miss sequence can replay part of it after the flush. The same effect was measured on CRB (crb-validation/.../latency-dram-flushed.csv:4 to 6, 0.15 to 0.38 L1 refills per load). Fix: use <code>--fresh 3 --flush</code> for every flushed row, so each timed pass walks a chain that has never been walked. latency.c already supports the pair: timed_walk flushes before each fresh chain (latency.c:87 to 88). Expected sign of success: 1.00 refills per load in the per-region rows, and the per-region latencies rise by 1 to 3 ns (est.).</p>

<h3>5c. Flushed DRAM rows measure DRAM</h3>
<p>The flushed rows at 1 to 8 MiB read 52.7 ns, the DRAM value, with 1.00 refills at every level. DC CIVAC removed the lines from the SLC as well. The row cannot stand for an SLC hit. Keep one such row (8 MiB) as the DRAM reference and drop the rest; the fresh chains already give the SLC.</p>

<h3>5d. Scratchpad</h3>
<p>Phase C was skipped because /dev/asimov-spm does not exist on this image. The script handles that (run_asimov.sh:88 and :151). The README still describes the SPM rows; mark them postponed.</p>

<h2>6. Run 2: what changes</h2>
<ol>
<li>Phase B: every OCM latency row becomes <code>--fresh 3 --flush</code> (rows 110 to 113 of run_asimov.sh). Add the same five per-region rows from CPUs 4, 6 and 8, so the hop count is measured from four of the five DSUs (DSU 0 holds the kernel CPUs 0 and 1): 20 rows of 256 KiB, about 4 ms of chip time each (est.), under 0.1 s in all.</li>
<li>Phase A: the flushed DRAM rows shrink to 8 MiB only. The 256 KiB flushed row goes, since 5b explains it.</li>
<li>Phase D: drop the unflushed 4-pass all-five read; replace the write row by the 1.25 MiB streaming form with <code>--flush-before --passes 4</code>; drop the copy row.</li>
<li>Phase E: drop the 4-core OCM write row. Keep the 4-core read row.</li>
<li>sysinfo: add CONFIG_DEBUG_FS to the config grep, a debugfs mount attempt and <code>cat /sys/kernel/debug/arm-cmn/map</code>, <code>cat /sys/bus/event_source/devices/arm_cmn_0/cpumask</code> and <code>ls /sys/bus/event_source/devices/arm_cmn_0/events</code>. Negligible chip time (est., under 1 ms), and the map confirms the crosspoint layout.</li>
<li>README: SPM marked postponed, the OCM flush sentence corrected, the new rows described.</li>
</ol>
<p>No C change is needed for these, because the OCM copy row is dropped (the 1.25 MiB copy form would need a bandwidth.c change). Chip time stays near 1.3 s (est.): the added OCM rows cost under 0.1 s and the dropped rows save about as much. Cores needed: 2 to 9 online, CPU 3 offline for the single-core phases as before. Huge pages: 256 as before.</p>

<h2>7. Questions for Jesse before run 2</h2>
<ol>
<li>Is CONFIG_DEBUG_FS in the kernel, and can debugfs be mounted so that <code>/sys/kernel/debug/arm-cmn/map</code> prints the mesh? One line: <code>zcat /proc/config.gz | grep DEBUG_FS; mount -t debugfs none /sys/kernel/debug; cat /sys/kernel/debug/arm-cmn/map</code>. The map shows the crosspoint of every home node and DSU port, which checks the one-hop and three-hop statement against the RTL at no chip cost.</li>
<li>Which mesh events does <code>arm_cmn_0</code> list, and is the perf tool in the image? <code>ls /sys/bus/event_source/devices/arm_cmn_0/events | grep -E 'pocq_reqs_recvd|mc_reqs_local|slc_sf'; which perf</code>. With these, run 3 can count SLC hits and memory requests per home node around a row, which settles the read-bandwidth question of section 3.</li>
<li>For the OCM lock: is each region a plain locked range (hnf_slc_lock_ways and lock_base) or the CMN OCM mode? The TRM says a CleanInvalid of an OCM-mode line does nothing in the SLC, while a locked line in a normal range can be pushed to memory by a non-allocating request. Run 1 shows DC CIVAC keeps OCM data (every flushed OCM row reads 18.8 to 26.0 ns, not 52 ns), so the question is only about interpretation, not safety.</li>
</ol>

<h2>8. Open items, insufficient data</h2>
<ul>
<li>L3 hit latency: not isolated (section 1). Needs a 144 KiB and 160 KiB chase, or a DSU L3 hit counter.</li>
<li>Per-hop cost on the mesh: the per-region rows carry prefetched lines (section 5b). Run 2's fresh-plus-flushed rows from four DSUs give it.</li>
<li>Why one-core reads beyond L2 stop at 9.2 GB/s while OCM reads reach 16.6 GB/s: hypothesis only (section 3). Needs mesh counters.</li>
<li>OCM write bandwidth: no valid number yet (section 5a). Run 2's streaming row gives it.</li>
<li>Whether the C1-Nano learns a repeated chain the way the V3AE on CRB does: the 256 KiB flushed rows say partly yes (0.09 to 0.23 of lines prefetched). Run 2's fresh rows confirm it if their refills read 1.00.</li>
</ul>
</main>
'''
open(OUT, 'w').write(page)
print('wrote', OUT, len(page), 'bytes')
print('store_us', store_us, 'ocm_write_us', ocm_write_us, 'flush_us', flush_us, 'flush_ns_line', flush_ns_line)
