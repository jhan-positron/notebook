"""Section 6 of the page: OCM latency and bandwidth.

Every measured number is read from the data layer D at build time.  The values that D
does not hold are computed in _derive() from D's rows (listed there).
"""
from . import data as _data

KEY = 'ocm'
TITLE = 'OCM latency and bandwidth'

CPUS = (2, 4, 6, 8)


def _rng(lo, hi, digits=3, unit=''):
    u = (' ' + unit) if unit else ''
    return '%.*f to %.*f%s' % (digits, lo, digits, hi, u)


def _pair(t, digits=3, unit=''):
    return _rng(t[0], t[1], digits, unit)


def _code(s):
    return '<code>%s</code>' % s


def _lines_of(rows):
    """'5-6' or '5-11': the timed rows of a group of files (the same lines in every file)."""
    ls = sorted(set(rr['line'] for r in rows for rr in r['rep_rows']))
    return '%d-%d' % (ls[0], ls[-1])


def _derive(D):
    """Values that the data layer does not hold, computed from its rows."""
    d = {}
    every = {r['cpu']: r for r in D.ocm_all5 if r['shape'] == 'every line'}
    page = {r['cpu']: r for r in D.ocm_all5 if r['shape'] != 'every line'}
    d['every'], d['page'] = every, page
    # one-line-per-page all-five row below the every-line row of the same CPU, ns
    below = [every[c]['best'] - page[c]['best'] for c in CPUS]
    d['page_below'] = (min(below), max(below))
    # largest spread of the two passes of the four every-line rows, %
    d['every_spread_max'] = max(every[c]['spread_pct'] for c in CPUS)
    # cost of the two clock reads per load, est.: the median empty-bracket time over the loads of a pass
    d['bracket_every_est'] = D.bracket['median'] / every[2]['loads']
    d['bracket_page5_est'] = D.bracket['median'] / page[2]['loads']
    # counter ranges over all passes of the four one-line-per-page all-five rows
    for k in ('a2_rng', 'l2pf_rng', 'l2_rng'):
        d['page5_' + k] = (min(page[c][k][0] for c in CPUS), max(page[c][k][1] for c in CPUS))
    d['page5_spread'] = (min(page[c]['spread_pct'] for c in CPUS), max(page[c]['spread_pct'] for c in CPUS))
    # the same OCM row on boots E and B over boot F1 (CPUs 2 and 8)
    bb = D.ocm_all5_by_boot
    d['f1_over_e'] = [bb['F1'][c] / bb['E'][c] for c in (2, 8)]
    d['f1_over_b'] = [bb['F1'][c] / bb['B'][c] for c in (2, 8)]
    # medians of the 20 one-region cells
    med = [r['median'] for r in D.ocm_cells]
    d['cell_median'] = (min(med), max(med))
    # page mapping: mean of the cells of a group on each boot (the dots of figure O4)
    for g in D.ocm_pagemap:
        g = dict(g)
        g['b_mean'] = sum(c['b'] for c in g['cells']) / len(g['cells'])
        g['d_mean'] = sum(c['d'] for c in g['cells']) / len(g['cells'])
        d['pm_' + g['key']] = g
    # OCM bandwidth
    regs = [r for r in D.ocm_bw if r['region'] is not None]
    d['bw_regs'] = regs
    d['bw_rising'] = all(r['reps'] == sorted(r['reps']) for r in regs)
    d['bw_spread'] = (min(r['spread_pct'] for r in regs), max(r['spread_pct'] for r in regs))
    lo = min(regs, key=lambda r: r['best'])
    hi = max(regs, key=lambda r: r['best'])
    d['bw_lo'], d['bw_hi'] = lo, hi
    d['bw_lo_steps'] = sum(D.step(2, lo['region']))
    d['bw_far'] = max(regs, key=lambda r: sum(D.step(2, r['region'])))
    d['bw_far_steps'] = sum(D.step(2, d['bw_far']['region']))
    d['bw_all5'] = next(r for r in D.ocm_bw if r['file'] == 'bandwidth-ocm-all5.csv')
    d['bw_write'] = next(r for r in D.ocm_bw if r['file'] == 'bandwidth-ocm-write.csv')
    d['bw_4core'] = next(r for r in D.ocm_bw if r['threads'] == 4)
    d['bw_write_over_read'] = d['bw_write']['best'] / d['bw_all5']['best']
    d['bw_eff'] = (min(r['eff_cycles_64'] for r in regs), max(r['eff_cycles_64'] for r in regs))
    return d


def build(D, V, S):
    d = _derive(D)
    n3 = lambda v: V.num(v, 3)
    n2 = lambda v: V.num(v, 2)
    every, page = d['every'], d['page']
    sm = D.ocm_all5_summary
    cs = D.ocm_cells_summary
    fit = D.ocm_fit
    fB = fit['B']
    for t in ('OCM', 'home node', 'every line', 'one line per 4 KiB page', 'step', 'mesh', 'refill',
              'L3 read refill', 'L2 refills not accounted for', 'rms', 'residual', 'TLB', 'exploratory',
              'effective cycles per 64 bytes transferred', 'SLC', 'requests sent on to memory'):
        S.term(t)

    out = []
    r_flush = S.ref('src:latency.c:17-20', 'the option that flushes every line before each timed walk')
    out.append(S.p(
        f"Every OCM chain is flushed first: the latency test removes every line of the chain from the caches of "
        f"the core before each timed pass, and a pass walks the chain once {r_flush}. "
        f"{S.figref('fig-S2')} shows where the five home nodes and the four cluster ports are on the mesh."))

    # ------------------------------------------------------------------ 6.1
    out.append(S.h3('ocm-quote', 'The OCM row to quote'))
    rows = []
    for c in CPUS:
        r = every[c]
        rows.append(dict(
            label=f'CPU {c}', sub=f"mean distance {r['mean_steps_x']:.1f} X + {r['mean_steps_y']:.1f} Y steps",
            values=[r['best'], page[c]['best']], tick=r['fit_pred'], labels='none',
            note=f"{n3(r['best'])} ns ({V.signed(r['above_fit'], 2, 'ns')} over the fit)"))
    svg = V.dot_rows(
        rows,
        [dict(name='every line, all five regions (the OCM row)', color='f1'),
         dict(name='one line per 4 KiB page, all five regions', color='f1', hollow=True)],
        unit='ns', fmt=n3, xlabel='chain load, ns', tick_name="boot B's fit at the CPU's mean distance",
        xrange=(22, 29), label_w=230)
    ref_every = S.ref('group:F1:latency-ocm-all5-dense-cpu*.csv:%s' % _lines_of(every.values()),
                      'the two timed passes of each file, with the counters')
    ref_page5 = S.ref('group:F1:latency-ocm-all5-cpu*.csv:%s' % _lines_of(page.values()),
                      'the seven timed passes of each file, with the counters')
    out.append(S.fig(
        svg,
        'OCM chain load on boot F1 by CPU, all five regions. The grey tick comes from boot B (prefetchers off, '
        'the L3 holds no data). The bold text is the filled dot, and in brackets the filled dot minus the grey tick.',
        f"Every line: {sm['a2'][0]:.2f} refill per level per load and {sm['pf_max']:.2f} prefetch refills. "
        f"The four CPUs read {_pair(sm['above_fit'], 2, 'ns')} above boot B's fit.",
        id_='fig-O1',
        note=f"Files {_code('latency-ocm-all5-dense-cpu&lt;c&gt;.csv')} {ref_every} and "
             f"{_code('latency-ocm-all5-cpu&lt;c&gt;.csv')} {ref_page5}. The grey tick is the fit of "
             f"{S.xref('ocm-region')} at the mean X and Y distance from the CPU to the five home nodes. The axis does "
             f"not start at zero."))
    out.append(S.p(
        f"The every-line chain has {V.num(every[2]['loads'], 0)} loads per pass and two timed passes per CPU "
        f"({_rng(min(every[c]['cycles'] for c in CPUS), max(every[c]['cycles'] for c in CPUS), 1, 'cycles')} per "
        f"load). It is the row to quote, for four measured reasons:"))
    out.append(S.bullets([
        f"All eight passes count {_pair(sm['l1'], 4)} L1 refills, {_pair(sm['l2'], 4)} L2 refills and "
        f"{_pair(sm['a2'], 4)} L3 read refills per load. The three prefetch refill counts read at most "
        f"{sm['pf_max']:.4f} per load.",
        f"The two passes of a CPU differ by at most {d['every_spread_max']:.2f} %.",
        f"The cost of the two clock reads is {d['bracket_every_est']:.3f} ns per load est. (one empty timed "
        f"bracket of {D.bracket['median']:.0f} ns over {V.num(every[2]['loads'], 0)} loads).",
        f"The same row exists on boot E (the firmware state of boot F1, another command set). Boot F1 "
        f"over boot E is {d['f1_over_e'][0]:.3f} on CPU 2 and {d['f1_over_e'][1]:.3f} on CPU 8.",
    ]))
    out.append(S.p('Three limits stand next to the number:'))
    out.append(S.bullets([
        'A refill count is an aggregate. It does not give the history of each line, and refill counts include '
        'prefetch fills.',
        'The row is a mean over five home nodes at different distances. It is not the load time of one home node.',
        f"The L3 status register was read on the cluster of CPU 2 only (operator's README) "
        f"{S.ref('readme:F1:66-67', 'the L3 status register of the cluster of CPU 2')}. The rows of CPUs 4, 6 "
        f"and 8 carry no such reading.",
    ]))
    out.append(S.p(
        f"The order of the CPUs is consistent with distance. CPU 8 reads {n3(sm['cpu8_minus_cpu2'])} ns above "
        f"CPU 2. Boot B's fit gives {n3(sm['fit_cpu8_minus_cpu2'])} ns for the same two mean distances. "
        f"Each of the four rows reads {_pair(sm['above_fit'], 2, 'ns')} above the fit, so the offset is the same "
        f"within {sm['above_fit'][1] - sm['above_fit'][0]:.2f} ns. The offset itself is not explained "
        f"({S.xref('open-items')})."))
    t_rows = []
    for shape, grp in (('Every line', every), ('One line per 4 KiB page', page)):
        t_rows.append(f"{shape}: {V.num(grp[2]['loads'], 0)} loads per pass, {grp[2]['n_reps']} passes")
        for c in CPUS:
            r = grp[c]
            t_rows.append([
                f'CPU&nbsp;{c}', n3(r['best']), n2(r['cycles']),
                n2(r['spread_pct']), _pair(r['l1_rng'], 2), _pair(r['l2_rng'], 2), _pair(r['a2_rng'], 2),
                _pair(r['l2pf_rng'], 2),
                V.signed(r['above_fit'], 2) if shape == 'Every line' else '-'])
    out.append(S.table(
        ['CPU', 'Best, ns', 'Cycles', 'Spread, %', 'L1 refills', 'L2 refills', 'L3 read refills',
         'L2 prefetch refills', "Above boot B's fit, ns"],
        t_rows, caption='OCM chains over all five regions, boot F1. Times, cycles and counts are per load. Counter '
                        'cells give the range over the passes.',
        note=f"Files as in {S.figref('fig-O1')}.",
        highlight=[0, 1, 2, 3], align='lrrrrrrrr', id_='tab-TO1'))

    # ------------------------------------------------------------------ 6.2
    out.append(S.h3('ocm-page', 'One line per page: not an OCM latency'))
    rows = []
    for c in CPUS:
        rows.append(dict(header=f"CPU {c} (every-line row {n3(every[c]['best'])} ns)"))
        for r in D.ocm_cells:
            if r['cpu'] != c:
                continue
            rows.append(dict(label=f"region {r['region']} (spread {V.num(r['spread_pct'], 1)} %)",
                             values=[list(r['reps'])], median=r['median'], tick=r['every_line_ns'],
                             labels='none'))
    svg = V.dot_rows(rows, [dict(name='one pass', color='f1', hollow=True)], unit='ns', fmt=n3,
                     xlabel='chain load of one pass, ns', tick_name='the every-line row of that CPU',
                     median_name='median of the 7 passes', row_h=22, xrange=(16, 33), label_w=250)
    ref_cells = S.ref('group:F1:latency-ocm-region[0-4]-cpu[2468].csv:%s' % _lines_of(D.ocm_cells),
                      'the seven timed passes of each file, with the counters')
    out.append(S.fig(
        svg,
        'The seven passes of each one-line-per-page chain over one region, boot F1 (20 chains). One ring is one '
        'pass.',
        f"The passes of one chain spread {_pair(cs['spread'], 1, '%')}, and most of them lie below the every-line "
        f"row.",
        id_='fig-O2', note=f"Files {_code('latency-ocm-region&lt;r&gt;-cpu&lt;c&gt;.csv')} {ref_cells}. The axis "
                           f"does not start at zero."))
    out.append(S.p(
        f"A one-line-per-page chain has {D.ocm_cells[0]['loads']} loads per region, one per 4 KiB page, and seven "
        f"timed passes. The 20 chains over one region read {_pair(cs['best'], 3, 'ns')} per load (best pass) and "
        f"{_pair(d['cell_median'], 3, 'ns')} (median). The four chains over all five regions read "
        f"{_pair(sm['one_line_per_page'], 3, 'ns')}, which is {_pair(d['page_below'], 2, 'ns')} below the every-line "
        f"row of the same CPU."))
    out.append(S.p('These rows do not give the OCM load time. The counters and the timing show why:'))
    out.append(S.bullets([
        f"Each of the {cs['n_passes']} one-region passes counts {_pair(cs['l2pf'], 2)} L2 prefetch refills and "
        f"{_pair(cs['a2'], 2)} L3 read refills per load (mean {cs['a2_mean']:.2f}).",
        f"Up to {cs['unacc_max']:.2f} L2 refills per load are not accounted for by the prefetch counts and the "
        f"L3 read refills. The same difference is at most {cs['unacc_max_bcd']:.4f} per load on the OCM rows of "
        f"boots B, C and D, where the L3 holds no data.",
        f"The all-five chains count {_pair(d['page5_l2pf_rng'], 2)} L2 prefetch refills and "
        f"{_pair(d['page5_a2_rng'], 2)} L3 read refills per load.",
        f"A pass of {D.ocm_cells[0]['loads']} loads includes {cs['bracket_per_load_est']:.2f} ns per load est. of "
        f"clock-read cost ({D.bracket['median']:.0f} ns per pass), which is not subtracted. The counters step by "
        f"1/{D.ocm_cells[0]['loads']} per load.",
        f"A fit of the 20 best values on the X and Y distance is void. Its largest residual is "
        f"{fit['F1']['pct_of_smallest']:.1f} % of the smallest value, and the limit is 2 %.",
    ]))
    out.append(S.hyp(
        'Prefetch fills place chain members in the cluster before the chain reaches them. The counters cannot '
        'show it: the L3 read refill count does not include the prefetch fills of a stream, and a refill count '
        'does not give the history of each line.',
        'The same rows on a boot with the L3 on and the prefetchers off, or the same rows with the hit set '
        '(the events that count L2 hits and L3 hits).'))
    t_rows = []
    for c in CPUS:
        t_rows.append(f'CPU {c}')
        for r in D.ocm_cells:
            if r['cpu'] != c:
                continue
            t_rows.append([
                str(r['region']), f"{r['steps_x']} X, {r['steps_y']} Y", n3(r['best']), n3(r['median']),
                V.num(r['spread_pct'], 1), _pair(r['a2_rng'], 2), _pair(r['l2pf_rng'], 2),
                n2(r['unacc_l2_max'])])
    out.append(S.table(
        ['Region', 'Steps', 'Best, ns', 'Median, ns', 'Spread, %', 'L3 read refills', 'L2 prefetch refills',
         'L2 refills not accounted for, largest'],
        t_rows, caption='One line per 4 KiB page, one region, boot F1: 20 chains, 64 loads per pass, 7 passes. '
                        'Times and counts are per load. Counter cells give the range over the passes.',
        note=f"Files as in {S.figref('fig-O2')}.", align='llrrrrrr', id_='tab-TO2'))

    # ------------------------------------------------------------------ 6.3
    out.append(S.h3('ocm-region', 'Per region and per mesh step'))
    rb = D.ocm_route['B']
    mk = {0: 'circle', 1: 'square', 2: 'triangle'}
    ser = []
    for y in (0, 1, 2):
        pts = [(r['steps_x'], r['best']) for r in rb if r['steps_y'] == y]
        ser.append(dict(name=f"{y} Y step{'s' if y != 1 else ''} (boot B)", color='off', marker=mk[y],
                        points=sorted(pts), size=5, fit=(fB['bx'], fB['a'] + fB['cy'] * y),
                        fit_range=(min(p[0] for p in pts), max(p[0] for p in pts))))
    far = max(rb, key=lambda r: r['best'])
    near = min(rb, key=lambda r: r['best'])
    svg = V.scatter_fit(
        ser, x='linear', xticks=[0, 1, 2, 3, 4], xlabel='X steps from the cluster port to the home node',
        ylabel='chain load, ns', yunit='ns', yrange='fit', height=380,
        annotations=[
            dict(x=3, y=fB['a'] + fB['bx'] * 3, text=f"+{fB['bx']:.2f} ns per X step", dx=30, dy=44),
            dict(x=1, y=fB['a'] + fB['bx'] + fB['cy'] * 2, text=f"+{fB['cy']:.2f} ns per Y step\nrms {fB['rms']:.3f} ns",
                 dx=-150, dy=-46),
            dict(x=far['steps_x'], y=far['best'], text=f"CPU {far['cpu']}, region {far['region']}: {n3(far['best'])} ns",
                 dx=-210, dy=-4),
        ])
    ref_route = S.ref('group:B:latency-ocm-region*-route-cpu*.csv:%s' % _lines_of(rb),
                      'the two timed passes of each file, with the counters')
    out.append(S.fig(
        svg,
        'Chain load over every line of one region against the distance on the mesh, boot B (prefetchers off, the '
        'L3 holds no data). One mark is one CPU and region (20 marks). The three lines are one fit.',
        f"One more X step adds {n3(fB['bx'])} ns and one more Y step {n3(fB['cy'])} ns. The 20 values differ "
        f"from the fit by at most {n3(fB['max_res'])} ns.",
        id_='fig-O3', note=f"Files {_code('latency-ocm-region&lt;r&gt;-route-cpu&lt;c&gt;.csv')} {ref_route}. "
                           f"The y axis does not start at zero. The L3 status register was read on the cluster of "
                           f"CPU 2 only (operator's README)."))
    fE = fit['E']
    out.append(S.p(
        f"Boot F1 has no chain over every line of one region. Boot E has that chain, and it counts "
        f"{_pair(fE['l2pf'], 2)} L2 prefetch refills per load. A fit of boot E's 20 values is void (largest "
        f"residual {fE['pct_of_smallest']:.1f} % of the smallest value). So this subsection uses boot B "
        f"(prefetchers off, the L3 holds no data)."))
    out.append(S.p(
        f"The 20 per-region rows of boot B read {n3(fB['smallest'])} to {n3(fB['largest'])} ns per load "
        f"({V.num(rb[0]['loads'], 0)} loads per pass, two passes). All {2 * fB['n']} passes count "
        f"{_pair(fB['l1'], 4)} L1 refills, {_pair(fB['l2'], 4)} L2 refills and {_pair(fB['a2'], 4)} L3 read "
        f"refills per load, and {fB['pf_max']:.4f} prefetch refills. These counts are aggregates. The two passes "
        f"of a row differ by {_pair((fB['spread_lo'], fB['spread_hi']), 2, '%')}."))
    r_plan = S.ref('doc:plan:271', 'a residual over 2 % of the smallest value voids a fit')
    out.append(S.p(
        f"A least-squares fit of the 20 best values gives {n3(fB['a'])} ns + {n3(fB['bx'])} ns per X step + "
        f"{n3(fB['cy'])} ns per Y step. Its largest residual is {fB['pct_of_smallest']:.2f} % of the smallest "
        f"value. The limit of the page is 2 %, so the fit is valid {r_plan}. How to read it:"))
    out.append(S.bullets([
        f"{n3(fB['a'])} ns is the fitted value at zero steps. No row has zero steps: the nearest has "
        f"{near['steps_x']} X steps and {near['steps_y']} Y step.",
        '"Per step" is the cost of one more step of distance for the whole round trip, request and data.',
        'Any shortest route has the same count of X steps and of Y steps. So the fit needs the coordinates only, '
        'not the route.',
        f"A fit with one cost for every step is void: its largest residual is "
        f"{fit['B_one_slope']['pct_of_smallest']:.1f} % of the smallest value. So an X step and a Y step do not "
        f"cost the same. Why an X step costs about twice a Y step is an open item ({S.xref('open-items')}).",
    ]))
    r_ports = S.ref('readme:R3:36', 'the mesh coordinates of the home nodes and of the cluster ports')
    pp = fit['ports']
    fl = fit['flits']['B']
    out.append(S.p(
        f"The coordinates of the cluster ports are documented (operator's README of boot R3) {r_ports}. Two "
        f"measurements agree with them ({S.tabref('tab-TO4')}). First, the four CPUs can be placed on the five "
        f"port positions in {pp['n_perm']} ways, and the documented placement gives the smallest rms. Second, "
        f"the busiest data direction at the crosspoint of the cluster points toward the home node, and at the "
        f"crosspoint of the home node toward the cluster, in every command "
        f"{S.ref('file:B:cmn-counts.csv', 'the data-flit counts of the 20 commands')}. The flit events are "
        f"exploratory."))
    assert pp['rank'] == 1 and fl['cluster_ok'] == fl['node_ok'] == fl['n']
    av = fit['all5_vs_cells']
    out.append(S.p(
        f"Where every load counts one refill per level on both boots, boot F1 and boot B agree. The OCM "
        f"row of boot F1 over boot B's is {d['f1_over_b'][0]:.3f} on CPU 2 and {d['f1_over_b'][1]:.3f} on CPU 8. "
        f"On boot B the row over all five regions reads {V.signed(av[2]['diff'], 2, 'ns')} (CPU 2) and "
        f"{V.signed(av[8]['diff'], 2, 'ns')} (CPU 8) against the mean of that CPU's five per-region rows. That "
        f"difference is not explained ({S.xref('open-items')})."))
    cell = {(r['cpu'], r['region']): r for r in rb}
    hn = {h['region']: h for h in D.mesh['home_nodes']}
    t_rows = []
    for c in CPUS:
        px, py = _data.PORT_XY[c]
        row = [f'CPU {c}, port ({px},{py})']
        for g in range(5):
            r = cell[(c, g)]
            row.append(f"{r['steps_x']} X, {r['steps_y']} Y<br><b>{n3(r['best'])}</b><br>"
                       f"{V.signed(r['residual'], 3)}")
        t_rows.append(row)
    out.append(S.table(
        ['CPU'] + [f"Region {g}, node {hn[g]['node']} ({hn[g]['x']},{hn[g]['y']})" for g in range(5)],
        t_rows, caption='Per-region rows of boot B. Each cell: the distance in steps, the best chain load in ns '
                        '(bold), and the residual of the fit in ns.',
        note=f"Files as in {S.figref('fig-O3')}. Node ids from {_code('lib_run.sh')} "
             f"{S.ref('src:lib_run.sh')}.", align='lccccc', id_='tab-TO3'))
    out.append(S.table(
        ['Item', 'Value'],
        [['Fitted value at zero steps', f"{n3(fB['a'])} ns"],
         ['One more X step', f"{n3(fB['bx'])} ns"],
         ['One more Y step', f"{n3(fB['cy'])} ns"],
         ['Residual, rms', f"{n3(fB['rms'])} ns"],
         ['Residual, largest', f"{n3(fB['max_res'])} ns ({fB['pct_of_smallest']:.2f} % of the smallest value)"],
         ['Limit (2 % of the smallest value)', f"{n3(fB['limit'])} ns: the fit is valid"],
         ['Fit with one cost for every step', f"largest residual {fit['B_one_slope']['pct_of_smallest']:.1f} %: void"],
         ['Check 1: rank of the documented ports', f"{pp['rank']} of {pp['n_perm']} placements "
                                                    f"(rms {n3(pp['best_rms'])} ns, next {n3(pp['second_rms'])} ns)"],
         ['Check 2: busiest data direction', f"toward the other end in {fl['cluster_ok']} of {fl['n']} (cluster) "
                                              f"and {fl['node_ok']} of {fl['n']} (home node)"]],
        caption='The fit of the 20 per-region rows of boot B, and the two checks of the coordinates.',
        align='ll', id_='tab-TO4'))

    # ------------------------------------------------------------------ 6.4
    out.append(S.h3('ocm-pagemap', 'Page mapping'))
    pm = [d['pm_route'], d['pm_page'], d['pm_all5-every']]
    plab = {'route': 'Every line, one region', 'page': 'One line per page, one region',
            'all5-every': 'Every line, all five regions', 'all5-page': 'One line per page, all five regions'}
    psub = {'route': 'mean of 20 rows, CPUs 2, 4, 6, 8', 'page': 'mean of 10 rows, CPUs 2 and 8',
            'all5-every': 'mean of 2 rows, CPUs 2 and 8', 'all5-page': 'mean of 2 rows, CPUs 2 and 8'}
    rows = [dict(label=plab[g['key']], sub=psub[g['key']], values=[g['b_mean'], g['d_mean']],
                 note=f"{g['geo']:.3f} x") for g in pm]
    svg = V.dot_rows(
        rows,
        [dict(name='boot B (4 KiB entries)', color='off'),
         dict(name='boot D (64 KiB translations)', color='off', hollow=True)],
        unit='ns', fmt=n3, xlabel='chain load, ns (mean of the best values of the group)', connect=True,
        xrange=(24, 27.5), label_w=250)
    tlb = D.ocm_tlb
    bars = []
    for shape in ('every line', 'one line per page'):
        for b in ('B', 'D'):
            t = tlb[shape][b]
            bars.append(dict(label=f"{shape}, boot {b}", value=t['mean'],
                             note=f"({t['min']:.0f} to {t['max']:.0f})"))
    svg2 = V.hbar(bars, unit='', fmt=lambda v: V.num(v, 0), xlabel='L1 TLB refills per pass, mean (range)',
                  color_='off', label_w=250)
    ref_tlb = ' '.join([
        S.ref('group:B:latency-ocm-region[0-4]-dense-tlb-cpu2.csv'), S.ref('group:B:latency-ocm-region[0-4]-tlb-cpu2.csv'),
        S.ref('group:D:latency-ocm-region[0-4]-dense-tlb-cpu2.csv'), S.ref('group:D:latency-ocm-region[0-4]-tlb-cpu2.csv')])
    ref_pm = ' '.join([
        ref_route, S.ref('group:D:latency-ocm-region*-route-cpu*.csv:%s' % _lines_of(D.ocm_route['D']),
                         'the two timed passes of each file, with the counters'),
        S.ref('group:B:latency-ocm-region[0-4]-cpu[28].csv'), S.ref('group:D:latency-ocm-region[0-4]-cpu[28].csv'),
        S.ref('group:B:latency-ocm-all5-dense-cpu*.csv'), S.ref('group:D:latency-ocm-all5-dense-cpu*.csv')])
    out.append(S.fig(
        svg + svg2,
        'Top: OCM chain load on boot B and on boot D. The bold number is boot D over boot B (geometric mean of '
        'the rows). Bottom: L1 TLB refills per pass of the chains of CPU 2 (an exploratory event).',
        f"With 64 KiB translations the L1 TLB refills fall to {tlb['every line']['D']['min']:.0f} to "
        f"{tlb['every line']['D']['max']:.0f} per pass, and the rows read "
        f"{(1 - d['pm_route']['geo']) * 100:.1f} % to {(1 - d['pm_page']['geo']) * 100:.1f} % lower.",
        id_='fig-O4',
        note=f"Chain rows {ref_pm}. Rows with the L1 TLB refill count (CPU 2, five regions) {ref_tlb}. The axis of "
             f"the top chart does not start at zero."))
    bD = D.boot['D']
    bBm = D.boot['B']
    if list(D.boot['F1']['map_cont']) != list(bBm['map_cont']):
        raise ValueError('sec_ocm: boot F1 does not have the OCM mapping of boot B')
    out.append(S.p(
        f"Boot B and boot D (as boot B, OCM mapped with 64 KiB translations) differ in the OCM mapping only "
        f"(operator's README) {S.ref('readme:D')}. Boot B uses single 4 KiB entries {S.ref('run:B:dmesg.txt')}. "
        f"Boot D uses 4 KiB entries with the contiguous hint, one translation per 64 KiB "
        f"{S.ref('run:D:dmesg.txt')} ({S.xref('setup-boots')}). Boot F1 has the mapping of boot B "
        f"{S.ref('run:F1:dmesg.txt')} and no row with a TLB count."))
    assert list(bBm['map_cont']) == ['0/64'] and list(bD['map_cont']) == ['64/64']
    g1, g2, g3, g4 = d['pm_route'], d['pm_page'], d['pm_all5-every'], d['pm_all5-page']
    out.append(S.p(
        f"{S.tabref('tab-TO5')} gives the ratios per row group. On the one-line-per-page rows of one region boot D "
        f"is lower in {g2['n_faster_d']} of {g2['n']} rows, by {abs(g2['mean_diff']):.2f} ns on average. "
        f"Two things differ between the boots at once: the contiguous hint and the 64 KiB alignment of the user "
        f"address (operator's README) {S.ref('readme:D:60', 'boot D against boot B compares the contiguous bit and the 64 KiB placement together')}."))
    out.append(S.insufficient(
        'The cost of one L1 TLB refill. The one-line-per-page rows have 64 loads per pass, and their best values '
        'and medians give different answers. Rows with more loads per pass and the TLB count would resolve it.'))
    t_rows = []
    for g in (g1, g2, g3, g4):
        t_rows.append([
            plab[g['key']].replace(', ', ',&nbsp;').replace(' ', '&nbsp;').replace(',&nbsp;', ', '),
            _pair(g['b'], 3), _pair(g['d'], 3), _rng(g['min'], g['max'], 3), f"{g['geo']:.3f}",
            f"{g['n_faster_d']} of {g['n']}", V.signed(g['mean_diff'], 2)])
    out.append(S.table(
        ['Rows', 'Boot B, ns', 'Boot D, ns', 'D over B', 'Geometric mean', 'Rows lower on D', 'D minus B, ns'],
        t_rows, caption='Page mapping: boot D (64 KiB translations) against boot B (4 KiB entries). Both boots have '
                        'the prefetchers off and an L3 that holds no data.',
        note=f'Times are ns per load, as ranges over the rows. "D minus B" is the mean over the rows. '
             f"{S.figref('fig-O4')} gives the L1 TLB refills per pass. No all-five row has a TLB count.",
        align='lrrrrrr', id_='tab-TO5'))

    # ------------------------------------------------------------------ 6.5
    out.append(S.h3('ocm-bw', 'OCM bandwidth'))
    bs = D.ocm_bw_summary
    a5, wr, c4 = d['bw_all5'], d['bw_write'], d['bw_4core']
    rows = [dict(header='Read, one region (256 KiB)')]
    for r in d['bw_regs']:
        dx, dy = D.step(2, r['region'])
        rows.append(dict(label=f"region {r['region']}", sub=f"{dx + dy} step{'s' if dx + dy != 1 else ''} from CPU 2",
                         values=[r['best'], [v for i, v in enumerate(r['reps']) if i != r['reps'].index(r['best'])]],
                         labels='none', note=f"{n3(r['best'])} GB/s"))
    rows.append(dict(header='All five regions (1.25 MiB)'))
    rows.append(dict(label='read, 1 pass per rep', labels='none',
                     values=[a5['best'], [v for v in a5['reps'] if v != a5['best']]],
                     note=f"{n3(a5['best'])} GB/s ({bs['read_ratio']:.2f} x)"))
    rows.append(dict(label=f"write, {wr['passes']} passes per rep", labels='none',
                     values=[wr['best'], [v for v in wr['reps'] if v != wr['best']]],
                     note=f"{n3(wr['best'])} GB/s ({bs['write_ratio']:.2f} x)"))
    svg = V.dot_rows(
        rows, [dict(name='best rep', color='f1'), dict(name='the other two reps', color='f1', hollow=True)],
        unit='GB/s', fmt=n3, xlabel='rate, GB/s', xrange=(18, 34), label_w=230,
        refs=[(bs['dram_read_2m'], f"DRAM-backed 2 MiB read {n3(bs['dram_read_2m'])} (not flushed, 4 passes)"),
              (bs['dram_write_2m'], f"DRAM-backed 2 MiB write {n3(bs['dram_write_2m'])} (not flushed, 4 passes)")])
    ref_bw = ' '.join([
        S.ref('group:F1:bandwidth-ocm-region*.csv:4-6', 'the three reps of each file'),
        S.ref('file:F1:bandwidth-ocm-all5.csv:%d' % a5['line'], 'the best rep'),
        S.ref('file:F1:bandwidth-ocm-write.csv:%d' % wr['line'], 'the best rep'),
        S.ref('file:F1:bandwidth-ocm-4core.csv:%d' % c4['line'], 'the best rep, with the rates per thread')])
    r1 = D.one_core('read', 2 * _data.MIB)
    w1 = D.one_core('write', 2 * _data.MIB)
    ref_dram = S.ref('file:F1:bandwidth-dram-1core.csv:%d,%d' % (r1['line'], w1['line']),
                     'the best reps of the 2 MiB read and of the 2 MiB write')
    out.append(S.fig(
        svg,
        'OCM bandwidth of one core (CPU 2) on boot F1. Every rep flushes the buffer first. The grey lines are the '
        'DRAM-backed 2 MiB rows of the same core. A one-region read rep is one pass. The number in brackets is the rate over the grey line of the same '
        'kernel.',
        f"The five regions read within {bs['region_apart_pct']:.2f} % of each other, and the write rate is "
        f"{d['bw_write_over_read']:.3f} times the read rate.",
        id_='fig-O5',
        note=f"OCM rows {ref_bw}. DRAM-backed rows {ref_dram}. The axis does not start at zero. The DRAM model is "
             f"an emulator memory, not silicon timing (operator's README) "
             f"{S.ref('readme:F1:247,354', 'the DRAM model')}."))
    r_bwsrc = S.ref('src:bandwidth.c:421-423', 'each rep runs one untimed pass, then the flush, then the timed passes')
    out.append(S.p(
        f"Each rep of an OCM bandwidth row runs one untimed pass, then flushes the buffer, then times its passes "
        f"{r_bwsrc}."))
    lo, hi, farr = d['bw_lo'], d['bw_hi'], d['bw_far']
    out.append(S.bullets([
        f"One region, read: best reps {_pair(bs['region'], 3, 'GB/s')}, {bs['region_apart_pct']:.2f} % apart. That "
        f"is {_pair(d['bw_eff'], 2)} effective cycles per 64 bytes transferred.",
        f"The rate shows no order by distance. Region {lo['region']} is the lowest at {d['bw_lo_steps']} step"
        f"{'s' if d['bw_lo_steps'] != 1 else ''} from CPU 2. Region {farr['region']} at {d['bw_far_steps']} steps "
        f"reads {n3(farr['best'])} GB/s.",
        f"The three reps of a file spread {_pair(d['bw_spread'], 2, '%')}."
        + (' In each file the rate rises from the first rep to the third.' if d['bw_rising'] else ''),
        f"All five regions: read {n3(a5['best'])} GB/s, write {n3(wr['best'])} GB/s (reps within "
        f"{wr['spread_pct']:.2f} %).",
        f"Four cores (CPUs 2, 4, 6, 8), one region each: {n3(c4['best'])} GB/s together, {bs['four_core_ratio_sum']:.3f} "
        f"times the sum of the four one-core rates of those regions. The rates per thread are "
        f"{_rng(c4['thr_min'], c4['thr_max'], 3, 'GB/s')} in the best rep.",
    ]))
    out.append(S.p(
        f"The all-five read is {bs['read_ratio']:.3f} times the DRAM-backed 2 MiB read ({n3(bs['dram_read_2m'])} "
        f"GB/s), and the write is {bs['write_ratio']:.3f} times the DRAM-backed 2 MiB write "
        f"({n3(bs['dram_write_2m'])} GB/s). Each ratio is the measured difference between two loops, and the rows "
        f"are not like for like. The OCM rows flush first, and the OCM read rows run one pass. The DRAM-backed rows "
        f"do not flush and run four passes."))
    out.append(S.insufficient(
        'Whether OCM itself or the flush sets the lower rate. No boot has a DRAM-backed bandwidth row with a '
        'flush before each rep. A DRAM-backed read (1 pass) and write (8 passes) at 256 KiB and 1.25 MiB with the '
        'flush would resolve it.'))
    out.append(S.p(
        f"The mesh counters are consistent with a home node that answers an OCM request from its own storage: the "
        f"count of requests sent on to memory stays at the level of the control on the OCM commands "
        f"({S.xref('mesh-dram')}). That count is exploratory."))
    t_rows = []
    for r in D.ocm_bw:
        what = f"{r['kernel']}, {_data.fmt_size(r['size'])}" + (' per core' if r['threads'] > 1 else '') + \
            f", {r['passes']} pass{'es' if r['passes'] != 1 else ''} per rep"
        t_rows.append([
            r['name'][0].upper() + r['name'][1:], what, ', '.join(n3(v) for v in r['reps']), n3(r['best']),
            n2(r['spread_pct']), n2(r['eff_cycles_64']), f"{r['ratio_dram']:.3f}"])
    out.append(S.table(
        ['Row', 'Kernel, footprint, passes', 'Reps, GB/s', 'Best, GB/s', 'Spread, %',
         'Effective cycles per 64 bytes', 'Over the DRAM-backed rate'],
        t_rows, caption='OCM bandwidth rows of boot F1 (CPU 2, or CPUs 2, 4, 6, 8 for the last row). Every rep '
                        'flushes first.',
        note=f"Files as in {S.figref('fig-O5')}. Effective cycles per 64 bytes transferred are loop throughput. The "
             f"last column is the rate per core over the DRAM-backed 2 MiB rate of the same kernel, which is not "
             f"like for like. The cycles of the four-core row are per core. The L3 status register was read on the "
             f"cluster of CPU 2 only (operator's README).",
        highlight=[5, 6], align='llrrrrr', id_='tab-TO6'))
    return ''.join(out)
