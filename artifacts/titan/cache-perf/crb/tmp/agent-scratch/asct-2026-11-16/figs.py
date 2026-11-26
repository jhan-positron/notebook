"""figs.py - the figures of the ASCT cross-check report, drawn from facts.json and baseline.json."""
from svgchart import (ASCT, AXIS, CONTEXT, GRID, INK, INK2, MUTED, NEW, OLD, SURFACE, Scale, dumbbell, esc, fmt,
                      frame, hbars, hit_circle, legend, line_panel, marker, text)

MI = 1 << 20
XT = [(MI, '1M'), (2 * MI, '2M'), (4 * MI, '4M'), (8 * MI, '8M'), (16 * MI, '16M'), (32 * MI, '32M'), (64 * MI, None),
      (128 * MI, None), (256 * MI, '256M'), (1024 * MI, '1G')]


def lab(F, b):
    return F['labels'][str(b)]


def fig_size(F, B):
    """Rate against buffer size, 1 MiB to 1 GiB, one panel per CPU."""
    w, h = 940, 420
    out = [frame(w, h, 'Read rate of one core against buffer size',
                 'Three read loops on CRB CPUs 2 and 41 and the ASCT loop on two Arm reference machines.')]
    out.append(legend([('old read', OLD, 'line'), ('new read', NEW, 'line'), ('ASCT read, CRB', ASCT, 'line'),
                       ('ASCT read, Arm reference machines (other firmware)', CONTEXT, 'thin')], 56, 22))
    for i, cpu in enumerate(F['cpus']):
        c = F['one'][str(cpu)]
        x0 = 56 + i * 460
        series = []
        for name, v in B['vendor'].items():
            pts = [(b, r, None, None, None) for b, r in v['sweep'] if MI <= b <= 1024 * MI]
            series.append({'name': name, 'color': CONTEXT, 'pts': pts, 'kind': 'thin', 'nomarker': True})
        for key, color, nm in (('old', OLD, 'old read'), ('new', NEW, 'new read'), ('asct', ASCT, 'ASCT read')):
            pts = []
            for b in F['sizes']:
                v = c[key].get(str(b))
                if key == 'new' and not v:      # 1 GiB exists only for the C form of the new loop (first run)
                    v = c['newc'].get(str(b))
                if b < MI:
                    continue
                if not v:           # a missing size ends the line: no line is drawn across a size without a run
                    if pts:
                        series.append({'name': nm, 'color': color, 'pts': pts})
                    pts = []
                    continue
                tip = f'{nm}, CPU {cpu}, {lab(F, b)}: {v["median"]:.2f} GB/s (range {v["lo"]:.2f} to {v["hi"]:.2f}, {v["n"]} processes)'
                pts.append((b, v['median'], v['lo'], v['hi'], tip))
            if pts:
                series.append({'name': nm, 'color': color, 'pts': pts})
        out.append(line_panel(x0, 66, 400, 290, series, XT, [0, 20, 40, 60, 80, 100, 120], xlog=True,
                              xlabel='buffer size (M = MiB, G = GiB), log scale', yunit='GB/s' if i == 0 else None,
                              title=f'CPU {cpu}', vmark=(8 * MI, '8 MiB')))
        # the three values at 8 MiB, as a small key inside the panel
        bx, by = x0 + 250, 84
        out.append(text(bx, by, 'at 8 MiB', 11, MUTED))
        for j, (key, color, nm) in enumerate((('old', OLD, 'old'), ('new', NEW, 'new'), ('asct', ASCT, 'ASCT'))):
            v = c[key].get(str(8 * MI))
            if v:
                out.append(marker(bx + 4, by + 14 + 15 * j, color, r=3))
                out.append(text(bx + 14, by + 18 + 15 * j, f'{nm} {v["median"]:.1f} GB/s', 11.5, INK, weight=600))
    return ''.join(out) + '</svg>'


def fig_fall(F, B):
    """1 MiB against 8 MiB for every loop and machine."""
    rows = []
    for cpu in F['cpus']:
        c = F['one'][str(cpu)]
        for key, color, nm in (('old', OLD, 'old read'), ('new', NEW, 'new read'), ('asct', ASCT, 'ASCT read')):
            a, b = c[key][str(MI)], c[key][str(8 * MI)]
            if not a or not b:
                continue
            rows.append({'label': f'{nm}, CPU {cpu}', 'sub': 'CRB', 'a': a['median'], 'b': b['median'], 'ca': color, 'cb': color,
                         'tipa': f'{nm}, CPU {cpu}, 1 MiB: {a["median"]:.2f} GB/s (range {a["lo"]:.2f} to {a["hi"]:.2f})',
                         'tipb': f'{nm}, CPU {cpu}, 8 MiB: {b["median"]:.2f} GB/s (range {b["lo"]:.2f} to {b["hi"]:.2f})',
                         'delta': f'{(b["median"] / a["median"] - 1) * 100:+.1f} %'})
    for name, tag in (('a0_numa2_ddr_7200', 'Arm reference machine A0'), ('a1_numa2_ddr_8000', 'Arm reference machine A1')):
        v = F['vendor_ratio'][name]
        cpu = B['vendor'][name]['cpu'][0]
        rows.append({'label': 'ASCT read', 'sub': f'{tag}, CPU {cpu}', 'a': v['m1'], 'b': v['m8'], 'ca': CONTEXT, 'cb': CONTEXT,
                     'tipa': f'ASCT read, {tag}, 1 MiB: {v["m1"]:.2f} GB/s (one process, vendor run)',
                     'tipb': f'ASCT read, {tag}, 8 MiB: {v["m8"]:.2f} GB/s (one process, vendor run)',
                     'delta': f'{(v["ratio"] - 1) * 100:+.1f} %'})
    return dumbbell(940, rows, 250, 800, [0, 20, 40, 60, 80, 100, 120], 'read rate, GB/s', 'Read rate at 1 MiB and at 8 MiB',
                    'One row per loop and machine. The hollow dot is the rate at 1 MiB, the filled dot the rate at 8 MiB.',
                    ('1 MiB', '8 MiB'), rowh=38, top=52)


def fig_pad(F):
    """The ASCT loop with injected NOPs on one core: 1 MiB against 8 MiB."""
    rows = []
    for cpu in F['cpus']:
        c = F['one'][str(cpu)]
        for nn in (0, 1, 2, 4, 8):
            if nn == 0:
                a, b = c['asct'][str(MI)], c['asct'][str(8 * MI)]
                inst = '1.4 instructions per line'
            else:
                r = F['pad'].get(f'{cpu}.{nn}')
                if not r:
                    continue
                a, b = r[str(MI)], r[str(8 * MI)]
                inst = f'{6 + 3 * nn} instructions per line'
            nm = f'{nn} injected NOPs, CPU {cpu}'
            rows.append({'label': nm, 'sub': inst, 'a': a['median'], 'b': b['median'], 'ca': ASCT, 'cb': ASCT,
                         'tipa': f'ASCT read, {nm}, 1 MiB: {a["median"]:.2f} GB/s (range {a["lo"]:.2f} to {a["hi"]:.2f}, {a["n"]} processes)',
                         'tipb': f'ASCT read, {nm}, 8 MiB: {b["median"]:.2f} GB/s (range {b["lo"]:.2f} to {b["hi"]:.2f}, {b["n"]} processes)',
                         'delta': f'{(b["median"] / a["median"] - 1) * 100:+.1f} %'})
    return dumbbell(940, rows, 250, 800, [0, 20, 40, 60, 80, 100, 120], 'read rate, GB/s', 'ASCT read loop with injected NOPs: 1 MiB and 8 MiB',
                    'One row per count of injected NOPs and CPU. The hollow dot is the rate at 1 MiB, the filled dot the rate at 8 MiB.',
                    ('1 MiB', '8 MiB'), rowh=38, top=52)


def fig_cost(F, B):
    """Cycles per line against the share of lines refilled into L2."""
    w, h = 940, 380
    out = [frame(w, h, 'Core cycles per line against L2 refills per line',
                 'ASCT loop and new read loop, CPUs 2 and 41, sizes 1 to 32 MiB.')]
    out.append(legend([('old read', OLD, 'dot'), ('new read', NEW, 'dot'), ('ASCT read', ASCT, 'dot'),
                       ('straight line fitted to the dots', INK2, 'thin')], 56, 22))
    for i, cpu in enumerate(F['cpus']):
        c = F['one'][str(cpu)]
        x0, y0, pw, ph = 56 + i * 460, 62, 400, 250
        sx, sy = Scale(0, 1, x0, x0 + pw), Scale(0, 3.5, y0 + ph, y0)
        series, hits = [], []
        out.append(line_panel(x0, y0, pw, ph, [], [(0, '0'), (0.2, '0.2'), (0.4, '0.4'), (0.6, '0.6'), (0.8, '0.8'), (1.0, '1.0')],
                              [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5], xlog=False, xlabel='L2 refills per line (share of lines that enter L2 from outside)',
                              title=f'CPU {cpu}: core cycles per line', ynd=1))
        for key, color, nm, fitkey in (('oldread', OLD, 'old read', None), ('asmread', NEW, 'new read', 'fit_new')):
            for b in F['sizes']:
                z = B['zs'].get(f'{key}.{cpu}.{b}')
                if not z:
                    continue
                out.append(marker(sx(z['r']), sy(z['cyc']), color, r=3))
                hits.append(hit_circle(sx(z['r']), sy(z['cyc']), f'{nm}, CPU {cpu}, {lab(F, b)}: {z["cyc"]:.3f} cycles and {z["r"]:.3f} L2 refills per line', r=8))
            if fitkey:
                f = c[fitkey]
                out.append(f'<line x1="{sx(0):.1f}" y1="{sy(f["a"]):.1f}" x2="{sx(1):.1f}" y2="{sy(f["a"] + f["b"]):.1f}" stroke="{INK2}" stroke-width="1.2"/>')
        for b in F['sizes']:
            k = c['cnt'].get(str(b))
            if not k or 'l2d_cache_refill' not in k or not (MI <= b <= 32 * MI):
                continue
            out.append(marker(sx(k['l2d_cache_refill']), sy(k['cpu_cycles']), ASCT, r=3))
            hits.append(hit_circle(sx(k['l2d_cache_refill']), sy(k['cpu_cycles']),
                                   f'ASCT read, CPU {cpu}, {lab(F, b)}: {k["cpu_cycles"]:.3f} cycles and {k["l2d_cache_refill"]:.3f} L2 refills per line', r=8))
        if c.get('fit'):
            f = c['fit']
            out.append(f'<line x1="{sx(0):.1f}" y1="{sy(f["a"]):.1f}" x2="{sx(1):.1f}" y2="{sy(f["a"] + f["b"]):.1f}" stroke="{INK2}" stroke-width="1.2"/>')
            out.append(text(x0 + 8, y0 + ph - 30, f'ASCT: {f["a"]:.2f} + {f["b"]:.2f} x refills', 11.5, INK, weight=600))
        fn = c['fit_new']
        out.append(text(x0 + 8, y0 + ph - 12, f'new read: {fn["a"]:.2f} + {fn["b"]:.2f} x refills', 11.5, INK, weight=600))
        out.append(''.join(hits))
    return ''.join(out) + '</svg>'


PF_PANELS = [('l2d_cache_hwprf', 'L2 hardware prefetch events'), ('l1d_cache_hwprf', 'L1 hardware prefetch events'),
             ('l2d_cache_l1hwprf', 'L2 accesses by the L1 prefetcher'), ('l2d_cache_refill_l1hwprf', 'L2 refills by the L1 prefetcher'),
             ('l1d_cache_lmiss_rd', 'L1 long-latency read misses'), ('l2d_cache_lmiss_rd', 'L2 long-latency read misses')]


def fig_prefetch(F):
    """Prefetch-related core counters per line against size, small multiples."""
    panels = [(n, t) for n, t in PF_PANELS if any(n in F['one'][str(c)]['cnt'].get(str(8 * MI), {}) for c in F['cpus'])]
    cols = 3
    rows = (len(panels) + cols - 1) // cols
    w, h = 940, 56 + rows * 218
    out = [frame(w, h, 'Prefetch-related core counters per line against buffer size', 'ASCT read loop, CPUs 2 and 41.')]
    out.append(legend([('CPU 2', INK2, 'line'), ('CPU 41', MUTED, 'hollow')], 50, 22))
    xt = [(MI, '1M'), (2 * MI, '2M'), (4 * MI, '4M'), (8 * MI, '8M'), (16 * MI, '16M'), (32 * MI, '32M')]
    for i, (name, title) in enumerate(panels):
        vals = []
        series = []
        for cpu, color, kind in ((2, INK2, 'line'), (41, MUTED, 'hollow')):
            pts = []
            for b in F['sizes']:
                k = F['one'][str(cpu)]['cnt'].get(str(b))
                if not k or name not in k or not (MI <= b <= 32 * MI):
                    continue
                pts.append((b, k[name], None, None, f'{title}, CPU {cpu}, {lab(F, b)}: {k[name]:.3f} per line'))
                vals.append(k[name])
            series.append({'name': f'CPU {cpu}', 'color': color, 'pts': pts, 'kind': kind})
        top = max(vals + [0.1])
        step = 0.5 if top <= 2 else 1 if top <= 4 else 2 if top <= 8 else 5 if top <= 20 else 10
        if top <= 0.5:
            step = 0.1
        if top <= 0.05:
            step = 0.01
        n = int(top / step) + 1
        yt = [round(step * j, 4) for j in range(n + 1)]
        x0 = 50 + (i % cols) * 300
        y0 = 70 + (i // cols) * 218
        out.append(line_panel(x0, y0, 240, 130, series, xt, yt, xlog=True, title=title, vmark=(8 * MI, ''),
                              ynd=2 if step < 0.1 else 1 if step < 1 else 0, xlabel='buffer size' if i // cols == rows - 1 else None))
    return ''.join(out) + '</svg>'


def fig_chip(F, B):
    """Totals at 64+56."""
    ch = F['chip']
    L = {r[0]: r for r in B['chip']['loops']}
    rows = []

    def ours(name, labeltxt, color):
        r = L[name]
        mid = (r[3] + r[4]) / 2
        rows.append({'label': labeltxt, 'sub': f'{r[1]}; window {r[2].replace("-", " to ")} lines', 'v': mid, 'lo': r[3], 'hi': r[4], 'color': color,
                     'value_label': f'{r[3]:.0f} to {r[4]:.0f}', 'tip': f'{labeltxt}: {r[3]} to {r[4]} GB/s over {r[5]} intervals (2026-11-15)'})
    ours('old read', 'old read', OLD)
    ours('new read (asmread)', 'new read', NEW)
    ours('read_1pl', 'our one-load-per-line loop (read_1pl)', CONTEXT)
    b = ch['base']
    rows.append({'label': 'ASCT read, 0 injected NOPs', 'sub': f'8 ldr x per 8 lines; {b["n"]} processes', 'v': b['median'], 'lo': b['lo'], 'hi': b['hi'], 'color': ASCT,
                 'value_label': f'{b["median"]:.1f}', 'tip': f'ASCT read, 0 NOPs: median {b["median"]:.1f} GB/s, range {b["lo"]:.1f} to {b["hi"]:.1f}, {b["n"]} processes'})
    n = ch['bestN']
    if n is not None and str(n) in ch['nops'] and n != 0:
        v = ch['nops'][str(n)]
        rows.append({'label': f'ASCT read, {n} injected NOPs', 'sub': f'the N with the highest total; {v["n"]} processes', 'v': v['median'], 'lo': v['lo'], 'hi': v['hi'], 'color': ASCT,
                     'value_label': f'{v["median"]:.1f}', 'tip': f'ASCT read, {n} NOPs: median {v["median"]:.1f} GB/s, range {v["lo"]:.1f} to {v["hi"]:.1f}, {v["n"]} processes'})
    for name, tag in (('a0_numa2_ddr_7200', 'A0'), ('a1_numa2_ddr_8000', 'A1')):
        v = B['vendor'][name]
        bw = dict((n, x) for n, _, x in v['nops'])[0]
        rows.append({'label': f'ASCT read, 0 injected NOPs, Arm machine {tag}', 'sub': f'vendor run, {v["cpus"]} CPUs, {v["numa"]} NUMA nodes, firmware {v["bios"].split("-")[-1]}',
                     'v': bw, 'lo': None, 'hi': None, 'color': CONTEXT, 'value_label': f'{bw:.1f}',
                     'tip': f'Vendor run on Arm reference machine {tag}: {bw} GB/s at 0 injected NOPs (loaded-latency table, one process)'})
    return hbars(940, rows, 390, 850, [0, 100, 200, 300, 400, 500, 600, 700], 'total read rate, GB/s',
                 'Total read rate with all threads', 'CRB: 64+56 threads. Old read, new read, a one-load-per-line loop and the ASCT loop. Grey: other loops and other machines.', rowh=40, top=26)


def fig_nops(F, B):
    """Total against injected NOPs, ordinal x axis."""
    ch = F['chip']
    ns = [n for n in (0, 1, 2, 3, 4, 6, 8, 10, 15, 20, 30, 40, 50, 70, 100, 180) if str(n) in ch['nops']]
    w, h = 940, 430
    x0, y0, pw, ph = 60, 70, 700, 290
    pos = {n: x0 + 20 + i * (pw - 40) / (len(ns) - 1) for i, n in enumerate(ns)}
    top = 700
    sy = Scale(0, top, y0 + ph, y0)
    out = [frame(w, h, 'Total read rate at 64+56 threads against injected NOPs',
                 'ASCT loop on CRB, per-mesh sums, and the vendor runs on two Arm reference machines.')]
    out.append(legend([('CRB total', ASCT, 'line'), ('CRB mesh 0 (64 threads)', INK2, 'line'), ('CRB mesh 1 (56 threads)', MUTED, 'hollow'),
                       ('Arm reference machines, vendor runs', CONTEXT, 'thin')], x0, 22))
    for t in range(0, top + 1, 100):
        out.append(f'<line x1="{x0}" y1="{sy(t):.1f}" x2="{x0 + pw}" y2="{sy(t):.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(text(x0 - 6, sy(t) + 4, str(t), 11, MUTED, 'end'))
    out.append(text(x0 - 40, y0 - 14, 'GB/s', 11, MUTED))
    out.append(f'<line x1="{x0}" y1="{y0 + ph}" x2="{x0 + pw}" y2="{y0 + ph}" stroke="{AXIS}" stroke-width="1"/>')
    for n in ns:
        out.append(text(pos[n], y0 + ph + 16, str(n), 11, MUTED, 'middle'))
    out.append(text(x0 + pw / 2, y0 + ph + 34, 'injected NOPs per line (ASCT option --bw-fine-delay); positions are evenly spaced, not to scale', 11, MUTED, 'middle'))
    # reference bands of the 2026-11-15 loops
    L = {r[0]: r for r in B['chip']['loops']}
    for name, color, labeltxt in (('old read', OLD, 'old read'), ('new read (asmread)', NEW, 'new read')):
        r = L[name]
        ya, yb = sy(r[4]), sy(r[3])
        out.append(f'<rect x="{x0}" y="{ya:.1f}" width="{pw}" height="{max(2, yb - ya):.1f}" fill="{color}" opacity="0.28"/>')
        out.append(marker(x0 + pw + 12, (ya + yb) / 2, color, r=3))
        out.append(text(x0 + pw + 22, (ya + yb) / 2 + 4, f'{labeltxt} {r[3]:.0f} to {r[4]:.0f}', 11.5, INK))
    hits = []
    for name, v in B['vendor'].items():
        pts = [(pos[n], sy(bw)) for n, _, bw in sorted(v['nops']) if n in pos]
        d = ' '.join(f'{"M" if i == 0 else "L"}{x:.1f},{y:.1f}' for i, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{CONTEXT}" stroke-width="1.2"/>')
        for n, _, bw in v['nops']:
            if n in pos:
                hits.append(hit_circle(pos[n], sy(bw), f'vendor run {name}, {n} NOPs: {bw} GB/s ({v["cpus"]} CPUs, {v["numa"]} NUMA nodes, firmware {v["bios"]})', r=7))
        last = max((n for n, _, _ in v['nops'] if n in pos), default=None)
    for key, color, kind, nm in (('mesh0', INK2, 'line', 'mesh 0 sum'), ('mesh1', MUTED, 'hollow', 'mesh 1 sum'), ('median', ASCT, 'line', 'total')):
        pts = [(pos[n], sy(ch['nops'][str(n)][key]), n) for n in ns]
        d = ' '.join(f'{"M" if i == 0 else "L"}{x:.1f},{y:.1f}' for i, (x, y, _) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
        for x, y, n in pts:
            v = ch['nops'][str(n)]
            if key == 'median' and abs(sy(v['lo']) - sy(v['hi'])) > 3:
                out.append(f'<line x1="{x:.1f}" y1="{sy(v["lo"]):.1f}" x2="{x:.1f}" y2="{sy(v["hi"]):.1f}" stroke="{color}" stroke-width="1.2" opacity="0.6"/>')
            out.append(marker(x, y, color, hollow=kind == 'hollow', r=3.2))
            hits.append(hit_circle(x, y, f'CRB {nm}, {n} NOPs: {v[key]:.1f} GB/s' + (f' (range {v["lo"]:.1f} to {v["hi"]:.1f}, {v["n"]} processes)' if key == 'median' else ''), r=8))
    # direct labels: N = 0 and the best N
    v0 = ch['nops'][str(ns[0])]
    out.append(text(pos[ns[0]] + 8, sy(v0['median']) - 8, f'{v0["median"]:.1f}', 12, INK, weight=600))
    bn = ch['bestN']
    if bn is not None and bn != ns[0]:
        vb = ch['nops'][str(bn)]
        out.append(text(pos[bn], sy(vb['median']) - 10, f'{vb["median"]:.1f}', 12, INK, 'middle', weight=600))
    return ''.join(out) + ''.join(hits) + '</svg>'


def fig_threads(F):
    """Per-thread rate by mesh, 0 NOPs against the best N."""
    ch = F['chip']
    bn = ch['bestN']
    if bn in (None, 0) or str(bn) not in ch['nops']:
        return ''
    a, b = ch['nops']['0'], ch['nops'][str(bn)]
    rows = []
    for m, nm, k in (('thr0', 'mesh 0, CPUs 0 to 63', 64), ('thr1', 'mesh 1, CPUs 64 to 119', 56)):
        rows.append({'label': nm, 'sub': f'median of {k} threads', 'a': a[m][1], 'b': b[m][1], 'ca': ASCT, 'cb': ASCT,
                     'tipa': f'{nm}, 0 NOPs: median thread {a[m][1]:.2f} GB/s (threads from {a[m][0]:.2f} to {a[m][2]:.2f})',
                     'tipb': f'{nm}, {bn} NOPs: median thread {b[m][1]:.2f} GB/s (threads from {b[m][0]:.2f} to {b[m][2]:.2f})',
                     'delta': f'x {b[m][1] / a[m][1]:.2f}'})
    return dumbbell(940, rows, 250, 800, [0, 1, 2, 3, 4, 5, 6], 'read rate of one thread, GB/s', 'Rate of one thread by mesh',
                    'Hollow dot: 0 injected NOPs. Filled dot: the N with the highest total.', ('0 injected NOPs', f'{bn} injected NOPs'), rowh=42, top=52, nd=2)


def fig_loops():
    """What each loop loads from one 64-byte line."""
    w, h = 940, 250
    out = [frame(w, h, 'What each read loop loads from one 64-byte line', 'Old read and new read load all 64 bytes, the ASCT loop loads 8 bytes.')]
    rows = [('old read', 'loads all 64 bytes (2 ldp q), then 4 vector adds on them', OLD, 8, 'counts 64 bytes'),
            ('new read', 'loads all 64 bytes (2 ldp q), no other work', NEW, 8, 'counts 64 bytes'),
            ('ASCT read', 'loads the first 8 bytes (1 ldr x), no other work', ASCT, 1, 'counts 64 bytes')]
    x0, cw = 330, 52
    out.append(text(x0, 24, 'one 64-byte cache line, drawn as eight 8-byte cells', 11.5, MUTED))
    for i, (nm, what, color, k, cnt) in enumerate(rows):
        y = 44 + i * 62
        out.append(text(12, y + 16, nm, 13, INK, weight=600))
        out.append(text(12, y + 33, what, 11, MUTED))
        for j in range(8):
            fill = color if j < k else SURFACE
            out.append(f'<rect x="{x0 + j * (cw + 2)}" y="{y}" width="{cw}" height="26" rx="3" fill="{fill}" stroke="{AXIS}" stroke-width="1"/>')
        out.append(text(x0 + 8 * (cw + 2) + 12, y + 17, cnt, 11.5, INK2))
    out.append(text(x0, 44 + 3 * 62 + 4, 'filled cell = bytes that the loop loads', 11, MUTED))
    return ''.join(out) + '</svg>'


def fig_path():
    """How ASCT was driven."""
    w, h = 940, 210
    out = [frame(w, h, 'How ASCT was driven in this work', 'The front end asct run was not used; its benchmark binary was called with the same command line.')]

    def box(x, y, bw, bh, t1, t2=None, used=True):
        s = f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="6" fill="{SURFACE}" stroke="{INK2 if used else AXIS}" stroke-width="{1.5 if used else 1}"/>'
        s += text(x + bw / 2, y + (20 if t2 else bh / 2 + 4), t1, 12, INK if used else MUTED, 'middle', weight=600)
        if t2:
            s += text(x + bw / 2, y + 37, t2, 10.5, MUTED, 'middle')
        return s

    def arrow(xa, ya, xb, yb, used=True):
        c = INK2 if used else AXIS
        return (f'<line x1="{xa}" y1="{ya}" x2="{xb - 6}" y2="{yb}" stroke="{c}" stroke-width="1.5"/>'
                f'<path d="M{xb},{yb} l-8,-4 v8 z" fill="{c}"/>')
    out.append(box(20, 24, 250, 50, 'asct run (front end)', 'fixed core CPU 127, needs huge pages', used=False))
    out.append(box(20, 122, 250, 50, 'our run scripts', 'CPUs 2 and 41, CPUs 0 to 119, our sizes'))
    out.append(box(380, 72, 250, 54, 'ASCT benchmark binary', 'loaded-latency-asct-sve.bin, same options'))
    out.append(box(700, 24, 220, 50, 'ASCT read loop', 'my_read_no_nops_rep_64b, my_read'))
    out.append(box(700, 122, 220, 50, 'ASCT counter capture', 'dietperf, probe build of the binary'))
    out.append(arrow(270, 49, 380, 90, used=False))
    out.append(arrow(270, 147, 380, 108))
    out.append(arrow(630, 90, 700, 49))
    out.append(arrow(630, 108, 700, 147))
    out.append(text(300, 52, 'not used', 11, MUTED))
    out.append(text(300, 152, 'used', 11, INK2))
    out.append(text(20, 200, 'Grey box and arrow: the path that this work could not use. Dark boxes and arrows: the path that ran.', 11, MUTED))
    return ''.join(out) + '</svg>'
