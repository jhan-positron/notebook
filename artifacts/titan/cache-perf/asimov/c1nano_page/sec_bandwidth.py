"""Section 4 of asimov-c1nano-perf.html: one-core bandwidth.

Subsections (ids of IDS.md): bw-1core, bw-l1forms, bw-variants.
Figures fig-B1 to fig-B3, tables tab-TB1 to tab-TB5.

Every measured number is read from the data layer D when the page is built.
Typed facts: the documented instruction throughput (D.doc, the SOG) and the
SLC size est. (operator's README).
"""

KEY = 'bandwidth'
TITLE = 'One-core bandwidth'

KIB = 1024
MIB = 1024 * 1024
SLC_EST_BYTES = 3.75 * MIB        # typed: operator's README (est.)
KERNEL_NAME = {'read': 'read', 'write': 'write', 'copy': 'copy'}


def _code(s):
    return '<code>%s</code>' % s


def _lines(rows, key='line'):
    return ','.join(str(n) for n in sorted(set(r[key] for r in rows)))


def _fref(S, rows, text):
    """[RefN] of the file of the rows, citing the timed rows that carry the best values."""
    r = rows[0]
    return S.ref('file:%s:%s:%s' % (r['boot'], r['file'], _lines(rows)), text)


def _rng(vals):
    vals = list(vals)
    return min(vals), max(vals)


# ---------------------------------------------------------------- 4.1

def _one_core(D, V, S):
    n1, n2, n3 = (lambda v: V.num(v, 1)), (lambda v: V.num(v, 2)), (lambda v: V.num(v, 3))
    rows = D.bw_1core
    by = {(r['kernel'], r['size']): r for r in rows}
    sizes = sorted(set(r['size'] for r in rows))
    lo, hi = sizes[0], sizes[-1]
    rd = [by[('read', s)] for s in sizes]
    wr = [by[('write', s)] for s in sizes]
    cp = [by[('copy', s)] for s in sizes]
    st = D.bw_steps
    doc = D.doc
    cache = D.platform['cache_bytes']
    l1, l2, l23 = cache['L1'], cache['L2'], cache['L2'] + cache['L3']
    fit = next(f for f in D.bw_fit if f['boot'] == 'F1')
    # derived here: ranges over the rows past the L1
    rd_up = [r for r in rd if r['size'] > l1]
    rd_up_gbps = _rng(r['best'] for r in rd_up)
    rd_up_pct = _rng(r['pct_doc'] for r in rd_up)
    wr_spread_max = max(r['spread_pct'] for r in wr)
    rd_spread = _rng(r['spread_pct'] for r in rd)
    cp_data_hi = by[('copy', hi)]['best'] / 2.0          # GB of data copied per second
    rate_step_48k = sizes[1]

    f_csv = _code('bandwidth-dram-1core.csv')
    r_file = _fref(S, rows, 'the rep with the best rate of each of the 18 rows')
    r_src = S.ref('src:bandwidth.c')
    r_sog = S.ref('doc:sog')
    r_dram = S.ref('readme:F1:247,354', 'the memory models have zero configured delay, and no DRAM number is like '
                                        'silicon')
    r_slc = S.ref('readme:R3:34', 'the SLC size that is left for DRAM lines')
    for t in ('bandwidth test', 'effective cycles per 64 bytes transferred', 'SOG', 'SLC', 'GB/s', 'spread',
              'DRAM model'):
        S.term(t)

    svg = V.line_chart(
        [dict(name='read', color='f1', points=[(r['size'], r['best']) for r in rd]),
         # the write line is dashed and drawn last: from 256 KiB up it lies on the copy line
         dict(name='write', color='c', dash='7 4', top=True, points=[(r['size'], r['best']) for r in wr]),
         dict(name='copy (bytes read plus bytes written)', color='alt', points=[(r['size'], r['best']) for r in cp])],
        x='log2', xticks=[(s, V.size_label(s)) for s in sizes], xlabel='footprint', ylabel='rate, GB/s',
        yunit='GB/s', xfmt=V.size_label, yfmt=n3,
        hlines=[(doc['read_gbps'], 'documented, read loop: %s GB/s = %s bytes per cycle' % (
                    V.num(doc['read_gbps'], 0), V.num(doc['read_bytes_per_cycle'], 0))),
                (doc['write_gbps'], 'documented, write loop: %s GB/s = %s bytes per cycle' % (
                    V.num(doc['write_gbps'], 0), V.num(doc['write_bytes_per_cycle'], 0)))],
        vlines=[(l1, 'L1 %s' % V.size_label(l1)), (l2, 'L2 %s' % V.size_label(l2)),
                (l23, 'L2 + L3 sizes added = %s' % V.size_label(l23)), (SLC_EST_BYTES, 'SLC 3.75 MiB est.')],
        labels=[dict(series=0, x=lo, text='read %s' % n1(rd[0]['best']), pos='right'),
                dict(series=0, x=hi, text='read %s' % n1(rd[-1]['best']), pos='right'),
                dict(series=1, x=lo, text='write %s' % n1(wr[0]['best']), pos='below'),
                dict(series=2, x=lo, text='copy %s' % n1(cp[0]['best']), pos='right'),
                dict(series=1, x=hi, text='write %s' % n1(wr[-1]['best']), pos='ur'),
                dict(series=2, x=hi, text='copy %s' % n1(cp[-1]['best']), pos='lr')],
        # the note stands below the read line, between two marker lines: its leader meets the read point only
        annotations=[dict(x=rate_step_48k, y=by[('read', rate_step_48k)]['best'], dx=395, dy=66,
                          text='read: %s %% from %s to %s,\nthen %s %% from %s to %s' % (
                              V.num(st['read_16k_to_48k_pct'], 0), V.size_label(lo), V.size_label(rate_step_48k),
                              V.num(st['read_48k_to_32m_pct'], 0), V.size_label(rate_step_48k),
                              V.size_label(hi)))],
        yrange=(0, 70), height=400, right_room=70)

    h = S.h3('bw-1core', 'One core by footprint')
    h += S.p(f'Boot F1 ran the read loop, the write loop and the copy loop of the bandwidth test on CPU 2 at six '
             f'footprints {r_file}. Each rate is loop throughput: bytes transferred over elapsed time '
             f'({S.xref("setup-bandwidth-test")}).')
    h += S.fig(
        svg,
        'One-core rate by footprint, boot F1, CPU 2, in GB/s. Grey horizontal lines: the documented instruction '
        'throughput. Grey vertical lines: the L1 size, the L2 size, the L2 and L3 sizes added, and the SLC size '
        'est. At 2.0 cycles per ns, 2 GB/s is 1 byte per cycle. From 256 KiB up the write line (dashed) lies on '
        'the copy line.',
        f'The write loop runs at {n1(wr[0]["pct_doc"])} % of the documented {V.num(doc["write_gbps"], 0)} GB/s at '
        f'{V.size_label(lo)} and at {n1(min(r["pct_doc"] for r in wr[1:]))} to '
        f'{n1(max(r["pct_doc"] for r in wr[1:]))} % from {V.size_label(rate_step_48k)} to {V.size_label(hi)}. '
        f'This is the rate of the store loop. The read '
        f'loop runs at {n1(rd[0]["best"])} GB/s inside the L1 and at {n1(rd_up_gbps[0])} to {n1(rd_up_gbps[1])} '
        f'GB/s at every larger footprint.',
        id_='fig-B1',
        note=f'File {f_csv} {r_file}. A copy row counts the bytes read plus the bytes written, and it uses two '
             f'buffers of the listed footprint. The size of the SLC is an estimate (operator\'s README) {r_slc}. '
             f'The rows of {V.size_label(2 * MIB)} and more are {S.term("DRAM-backed")}. The DRAM model is an '
             f'emulator memory with zero configured delay, not silicon timing (operator\'s README) {r_dram}. '
             f'How the timed lines of a {V.size_label(2 * MIB)} row split between SLC hits and fills by the DRAM '
             f'model is not known ({S.xref("setup-bandwidth-test")}).')
    h += S.bullets([
        f'The read rate has one large drop. It falls by {V.num(-st["read_16k_to_48k_pct"], 1)} % from '
        f'{V.size_label(lo)} to {V.size_label(rate_step_48k)}. From {V.size_label(rate_step_48k)} to '
        f'{V.size_label(hi)} it falls by {V.num(-st["read_48k_to_32m_pct"], 1)} % of the '
        f'{V.size_label(rate_step_48k)} rate ({n3(by[("read", rate_step_48k)]["best"])} to {n3(rd[-1]["best"])} '
        f'GB/s). These five rows read '
        f'{n2(st["read_eff_cycles_48k_up"][0])} to {n2(st["read_eff_cycles_48k_up"][1])} effective cycles per '
        f'64 bytes transferred. The spread of the read rows is {n2(rd_spread[0])} to {n2(rd_spread[1])} %.',
        f'The write rate has no drop. It reads {n3(st["write_16k"])} GB/s at {V.size_label(lo)} and '
        f'{n3(st["write_48k_up"][0])} to {n3(st["write_48k_up"][1])} GB/s from {V.size_label(rate_step_48k)} to '
        f'{V.size_label(hi)}. The spread of a write row is at most {n2(wr_spread_max)} %.',
        f'Copy reads {n3(cp[0]["best"])} GB/s at {V.size_label(lo)} and {n3(cp[-1]["best"])} GB/s at '
        f'{V.size_label(hi)}, with both directions counted. So the {V.size_label(hi)} copy moves '
        f'{n3(cp_data_hi)} GB of data per second.'])
    h += S.p(f'The documented instruction throughput (SOG) is {V.num(doc["read_gbps"], 0)} GB/s for the read loop '
             f'and {V.num(doc["write_gbps"], 0)} GB/s for the write loop {r_sog}. The read loop reaches {n1(rd[0]["pct_doc"])} % of its number at '
             f'{V.size_label(lo)} and {n1(rd_up_pct[0])} to {n1(rd_up_pct[1])} % at the larger footprints. The '
             f'SOG gives no number for the copy loop. '
             f'The {n1(wr[-1]["pct_doc"])} % of the {V.size_label(hi)} write row has two limits. It is the rate '
             f'at which the store loop runs. No write row waits for the lines to reach the DRAM model. The DRAM '
             f'model is an emulator memory, not silicon timing (operator\'s README) {r_dram}.')
    h += S.p(f'The write rows of {V.size_label(fit["sizes"][0])} to {V.size_label(fit["sizes"][-1])} fit a '
             f'straight line: {n1(fit["intercept_ns"])} ns per pass plus the bytes at {n3(fit["rate"])} GB/s '
             f'({S.tabref("tab-TB3")}). The fit describes the lower write rate at {V.size_label(lo)} as a fixed '
             f'time per pass. {S.xref("bw-l1forms", cap=True)} measures that time in two forms.')
    h += S.insufficient(
        f'No bandwidth row of boot F1 has counters. So boot F1 does not show which level supplies the lines of '
        f'the read stream at {V.size_label(rate_step_48k)} to {V.size_label(256 * KIB)}. The plain read with '
        f'counters at these footprints on a boot with the L3 on would show it ({S.xref("open-l3")}).')

    trs = []
    for k in ('read', 'write', 'copy'):
        trs.append('%s loop' % k.capitalize())
        for s in sizes:
            r = by[(k, s)]
            trs.append([V.size_label(s), V.num(r['passes'], 0), n3(r['best']), n2(r['spread_pct']),
                        n3(r['bytes_per_cycle']), n3(r['eff_cycles_64']),
                        n1(r['pct_doc']) if r['pct_doc'] is not None else 'not documented'])
    h += S.table(
        ['Footprint', 'Passes per rep', 'Best, GB/s', 'Spread, %', 'Bytes per cycle',
         'Effective cycles per 64 bytes transferred', '% of documented'],
        trs,
        caption='One-core bandwidth rows of boot F1, CPU 2, three reps per row.',
        note=f'File {f_csv} {r_file}. Bytes per cycle is the rate over 2.0 cycles per ns. The copy rows count '
             f'both directions.',
        align='lrrrrrr', id_='tab-TB1')
    return h


# ---------------------------------------------------------------- 4.2

def _l1_forms(D, V, S):
    n1, n2, n3 = (lambda v: V.num(v, 1)), (lambda v: V.num(v, 2)), (lambda v: V.num(v, 3))
    rows = D.bw_l1
    by = {(r['form'], r['kernel'], r['size']): r for r in rows}
    sizes = sorted(set(r['size'] for r in rows))
    sm = D.bw_l1_summary
    doc = D.doc
    looped = [r for r in rows if r['form'] == 'looped']
    single = [r for r in rows if r['form'] == 'single-call']
    fits = {(f['boot'], f['form'], f['kernel']): f for f in list(D.bw_fit) + list(D.bw_fit_extra)}
    f_lw, f_sw = fits[('E', 'looped', 'write')], fits[('E', 'single-call', 'write')]
    f_lr, f_sr = fits[('E', 'looped', 'read')], fits[('E', 'single-call', 'read')]
    c_lw, c_sw = fits[('C', 'looped', 'write')], fits[('C', 'single-call', 'write')]
    c_lr, c_sr = fits[('C', 'looped', 'read')], fits[('C', 'single-call', 'read')]
    f_f1 = fits[('F1', 'looped', 'write')]
    assert f_lw['valid'] and f_sw['valid'] and c_lw['valid'] and c_sw['valid'] and f_f1['valid']
    assert not (f_lr['valid'] or f_sr['valid'] or c_lr['valid'] or c_sr['valid'])
    # derived here
    slope_off = max(abs(f['rate'] / doc['write_gbps'] - 1.0) * 100.0 for f in (f_lw, f_sw))
    icpt_rep = max(abs(f_lw['intercept_ns'] - c_lw['intercept_ns']), abs(f_sw['intercept_ns'] - c_sw['intercept_ns']))
    rep16 = {r['id']: abs(r['ratio'] - 1.0) * 100.0 for r in D.repeat if r['group'] == 'looped 16 KiB'}
    bsr, bsw = sm['best_single_read'], sm['best_single_write']
    sc_pct = {k: _rng(r['pct_doc'] for r in single if r['kernel'] == k) for k in ('read', 'write')}

    f_lp, f_sc = _code('bandwidth-l1-passes.csv'), _code('bandwidth-l1-asmpasses.csv')
    r_lp = _fref(S, looped, 'the best rep of each looped row')
    r_sc = _fref(S, single, 'the best rep of each single-call row')
    r_src = S.ref('src:bandwidth.c')
    r_src_forms = S.ref('src:bandwidth.c:35-38', 'the two forms together measure the net cost of the per-pass work, '
                                                 'not the call and the return alone')
    r_src_save = S.ref('src:bandwidth.c:129-131,199', 'the read kernel saves eight vector registers per call, and '
                                                      'the write kernel saves none')
    r_plan = S.ref('doc:plan')
    r_sog = S.ref('doc:sog')
    r_c = ' '.join([S.ref('file:C:%s:%s' % (c_lw['file'], ','.join(map(str, c_lw['lines']))),
                          'the looped write rows of the fit'),
                    S.ref('file:C:%s:%s' % (c_sw['file'], ','.join(map(str, c_sw['lines']))),
                          'the single-call write rows of the fit')])
    for t in ('looped form', 'single-call form', 'residual', 'refill'):
        S.term(t)

    ser = [dict(name='looped form', color='f1', hollow=True), dict(name='single-call form', color='f1')]
    panels = []
    for k, xr in (('read', (38.0, 66.0)), ('write', (26.0, 33.0))):
        drows = [dict(header='%s loop' % k.capitalize())]
        for s in sizes:
            a, b = by[('looped', k, s)], by[('single-call', k, s)]
            assert xr[0] < a['best'] < b['best'] < doc['%s_gbps' % k] < xr[1]
            drows.append(dict(label=V.size_label(s),
                              sub='looped minus single-call: %s ns per pass' % V.signed(a['diff_ns'], 1),
                              values=[a['best'], b['best']]))
        panels.append(V.dot_rows(
            drows, ser, unit='GB/s', fmt=n1, xlabel='%s rate, GB/s' % k, connect=True, label_w=290, xrange=xr,
            refs=[(doc['%s_gbps' % k], 'documented: %s GB/s' % V.num(doc['%s_gbps' % k], 0))],
            title='the two L1 forms, %s loop' % k))
    svg = ''.join(panels)

    h = S.h3('bw-l1forms', 'Inside the L1: two forms')
    h += S.p(f'Boot F1 has one footprint inside the L1, in one form. {D.boot_first_use["E"].capitalize()[0]}'
             f'{D.boot_first_use["E"][1:]} ran four L1 footprints in two forms, with five reps per row '
             f'{r_lp} {r_sc}. The looped form makes one call of the kernel per pass. The '
             f'single-call form runs all passes of a rep in one call {r_src}. Boot E\'s looped {V.size_label(16 * KIB)} rows are within '
             f'{n2(rep16["looped-16k-read"])} % (read) and {n2(rep16["looped-16k-write"])} % (write) of boot F1\'s.')
    h += S.fig(
        svg,
        'The two L1 forms on boot E, CPU 2. Hollow dot: looped form. Filled dot: single-call form. Small text: '
        'looped minus single-call, in ns per pass. Grey line: the documented instruction throughput. The two '
        'panels have different scales.',
        f'The single-call form reaches {n1(bsr["pct_doc"])} % of the documented read throughput and '
        f'{n1(bsw["pct_doc"])} % of the documented write throughput at {V.size_label(bsr["size"])}.',
        id_='fig-B2',
        note=f'Files {f_lp} {r_lp} and {f_sc} {r_sc}. Documented instruction throughput: SOG {r_sog}.')
    h += S.bullets([
        f'Looped minus single-call is {n1(sm["diff_read"][0])} to {n1(sm["diff_read"][1])} ns per pass for read '
        f'and {n1(sm["diff_write"][0])} to {n1(sm["diff_write"][1])} ns per pass for write. It is the measured '
        f'difference between two loops. The looped form also runs a C loop iteration and a byte count at every pass. '
        f'So the difference is not the time of one call and one return alone {r_src_forms}.',
        f'The best L1 rates are in the single-call form: read {n3(bsr["best"])} GB/s and write {n3(bsw["best"])} '
        f'GB/s at {V.size_label(bsr["size"])} ({S.tabref("tab-TB2")}).'])
    h += S.hyp(
        f'The register save explains the larger read difference. The read kernel saves and restores eight vector '
        f'registers at every call, and the write kernel saves none {r_src_save}.',
        'A read kernel that needs no register save, in both forms. No row isolates the save.')
    h += S.p(f'{S.tabref("tab-TB3")} fits the time per pass against the bytes per pass with a straight line. A fit '
             f'is void when its largest residual is over 2 % of the smallest pass time {r_plan}.')
    h += S.bullets([
        f'The write fits of boot E are valid. Looped form: {n1(f_lw["intercept_ns"])} ns per pass plus the bytes '
        f'at {n3(f_lw["rate"])} GB/s. Single-call form: {n1(f_sw["intercept_ns"])} ns per pass plus the bytes at '
        f'{n3(f_sw["rate"])} GB/s. Both rates are within {n2(slope_off)} % of the documented '
        f'{V.num(doc["write_gbps"], 0)} GB/s.',
        f'The same rows on {D.boot_first_use["C"]} give {n1(c_lw["intercept_ns"])} and '
        f'{n1(c_sw["intercept_ns"])} ns {r_c}. So the fixed time of a fit repeats to about {V.num(icpt_rep, 0)} ns.',
        f'The read fits are void on both boots. The largest residual is {n2(f_lr["max_res_pct"])} % (looped) and '
        f'{n2(f_sr["max_res_pct"])} % (single-call) on boot E, and {n2(c_lr["max_res_pct"])} % and '
        f'{n2(c_sr["max_res_pct"])} % on boot C. So this page quotes no fixed time and no rate from a read fit '
        f'(open item, {S.xref("open-items")}).'])

    trs = []
    for form, f_rows in (('Looped form', looped), ('Single-call form', single)):
        trs.append(form)
        for k in ('read', 'write'):
            for s in sizes:
                r = by[(f_rows[0]['form'], k, s)]
                trs.append([k, V.size_label(s), V.num(r['passes'], 0), n3(r['best']), n2(r['spread_pct']),
                            n1(r['pct_doc']), n3(r['ns_pass']),
                            V.signed(r['diff_ns'], 3) if r['form'] == 'looped' else '-',
                            n3(r['l1_refills_pass'])])
    h += S.table(
        ['Loop', 'Footprint', 'Passes', 'Best, GB/s', 'Spread, %', '% of documented', 'Pass, ns',
         'Looped minus single-call, ns', 'L1 refills per pass'],
        trs,
        caption='The L1 forms on boot E, CPU 2, five reps per row.',
        note=f'Files as in {S.figref("fig-B2")}. Passes are per rep. Time per pass is the bytes of the best rep '
             f'over its rate, divided by the passes. The L1 refills are an aggregate count of the best rep. They '
             f'include prefetch fills, and they do not give the history of a line.',
        align='llrrrrrrr', id_='tab-TB2')

    def fit_row(f):
        srange = '%s to %s' % (V.size_label(f['sizes'][0]), V.size_label(f['sizes'][-1]))
        head = [D.boot_name[f['boot']], f['form'], f['kernel'], srange]
        tail = [n2(f['max_res']), n2(f['limit']), n2(f['max_res_pct']), f['verdict']]
        if f['valid']:
            return head + [n1(f['intercept_ns']), n3(f['rate'])] + tail
        return head + ['void', 'void'] + tail
    h += S.table(
        ['Boot', 'Form', 'Loop', 'Footprints', 'Fixed time, ns', 'Rate, GB/s', 'Largest residual, ns', 'Limit, ns',
         'Residual, %', 'Verdict'],
        [fit_row(f) for f in (f_f1, f_lw, f_sw, f_lr, f_sr)],
        caption='Straight-line fits of the time per pass against the bytes per pass: a fixed time per pass plus '
                'the bytes at one rate.',
        note=f'The limit is 2 % of the smallest pass time of the fit {r_plan}. The last number column is the '
             f'largest residual in percent of that pass time.',
        align='llllrrrrrl', id_='tab-TB3')
    return h


# ---------------------------------------------------------------- 4.3

def _variants(D, V, S):
    n1, n2, n3, n4 = (lambda v: V.num(v, 1)), (lambda v: V.num(v, 2)), (lambda v: V.num(v, 3)), (lambda v: V.num(v, 4))
    boots = ('E', 'C', 'B')
    cmp_ = D.bw_var_cmp
    by = {(r['boot'], r['kernel'], r['size']): r for r in D.bw_var}
    kernels = []
    for r in D.bw_var:
        if r['kernel'] not in kernels:
            kernels.append(r['kernel'])
    sizes = sorted(set(r['size'] for r in D.bw_var))
    big, small = sizes[-1], sizes[0]
    hints = [k for k in kernels if 'pf' in k]
    two = [k for k in kernels if k.endswith('2s')][0]
    plain = {b: by[(b, 'read', big)] for b in boots}
    leg = {'E': 'boot E (L3 on, prefetchers on)', 'C': 'boot C (the L3 holds no data, prefetchers on)',
           'B': 'boot B (the L3 holds no data, prefetchers off)'}
    # derived here
    e_hint = [by[('E', k, big)]['change_pct'] for k in hints]
    c_hint = [by[('C', k, big)]['change_pct'] for k in hints]
    b_hint = [by[('B', k, big)]['ratio_plain'] for k in hints]
    c_hint_small = [by[('C', k, small)]['change_pct'] for k in hints]
    spread_of = {(b, s): _rng(by[(b, k, s)]['spread_pct'] for k in kernels) for b in boots for s in sizes}
    worst_small = max((by[(b, k, small)] for b in boots for k in kernels), key=lambda r: r['spread_pct'])
    big_spread_max = max(by[(b, k, big)]['spread_pct'] for b in boots for k in kernels)
    b_plain_small = by[('B', 'read', small)]
    e_hint_l1pf = [by[('E', k, big)]['l1pf'] for k in hints]
    e_hint_l1 = _rng(by[('E', k, big)]['l1'] for k in hints)
    b_small_spread = _rng(by[('B', k, small)]['spread_pct'] for k in kernels)
    c_a2_max = max(by[('C', 'read', s)]['a2'] for s in sizes)       # best reps of 2 MiB and 32 MiB
    e_f1 = {s: abs(v) for s, v in cmp_['e_vs_f1_pct'].items()}
    pf_events_b_max = max(max(by[('B', k, s)][c] for c in ('l1pf', 'l2pf', 'l2byl1pf'))
                          for k in kernels for s in sizes)

    f_csv = _code('bandwidth-read-prefetch.csv')
    refs = {b: _fref(S, [r for r in D.bw_var if r['boot'] == b], 'the best rep of each of the ten rows')
            for b in boots}
    r_all = ' '.join(refs[b] for b in boots)
    r_src = S.ref('src:bandwidth.c')
    r_sog = S.ref('doc:sog')
    r_dram = S.ref('readme:F1:247,354')
    r_slc = S.ref('readme:R3:34', 'the SLC size that is left for DRAM lines')
    assert big > SLC_EST_BYTES
    for t in ('plain read', 'software prefetch N lines ahead', 'two streams', 'L3 read refill',
              'checked in two states', 'refill', 'L1 prefetch refills', 'kernel'):
        S.term(t)

    drows = []
    for k in kernels:
        r = by[('E', k, big)]
        if k == 'read':
            note = 'C over B %s, E over C %s' % (V.ratio(cmp_['pf_effect']), V.ratio(cmp_['l3_effect']))
        else:
            note = 'E %s %%, C %s %%, B x %s' % (V.signed(r['change_pct'], 1), V.signed(by[('C', k, big)]['change_pct'], 1),
                                                 n2(by[('B', k, big)]['ratio_plain']))
        drows.append(dict(label=r['kernel_label'], values=[by[(b, k, big)]['best'] for b in boots], note=note))
    svg = V.dot_rows(
        drows, [dict(name=leg['E'], color='f1'), dict(name=leg['C'], color='c'), dict(name=leg['B'], color='off')],
        unit='GB/s', fmt=n1, xlabel='rate at %s, GB/s' % V.size_label(big), xrange=(0, None), label_w=230,
        labels='all')

    h = S.h3('bw-variants', 'The read stream and the prefetchers')
    h += S.p(f'No bandwidth row of boot F1 has a prefetch hint, a second stream or a counter. Three boots ran five '
             f'read variants with counters per 64 bytes transferred {r_all}. The plain read is the read loop alone. '
             f'A software prefetch variant adds one prefetch hint (an instruction that asks for a line and returns '
             f'no data) per line, 4, 8 or 16 lines ahead. Two streams reads the two halves of the buffer at once '
             f'{r_src}.')
    h += S.bullets([
        f'The three boots are boot E (L3 on, prefetchers on), boot C (the L3 holds no data, prefetchers on) and '
        f'boot B (the L3 holds no data, prefetchers off). So the prefetcher effect is boot C against boot B, and '
        f'the L3 effect is boot E against boot C.',
        f'Boots E and C run one benchmark build and one command list. Boots C and B also differ in the benchmark '
        f'build, in the OCM mapping and in the command list ({S.xref("setup-boots")}).',
        f'The plain read of boot E is within {n2(e_f1[big])} % of boot F1\'s at {V.size_label(big)} and within '
        f'{n2(e_f1[small])} % at {V.size_label(small)}.'])
    h += S.fig(
        svg,
        f'The read variants at {V.size_label(big)} on CPU 2, one dot per boot. Bold text: the ratios of the plain '
        f'row, and the rate of each variant against the plain read of the same boot.',
        f'With the L3 holding no data, the prefetchers raise the plain read {n2(cmp_["pf_effect"])} times (boot C '
        f'over boot B). The hint lowers the rate by {n1(-max(e_hint))} to {n1(-min(e_hint))} % on boot E and raises '
        f'it {n2(min(b_hint))} to {n2(max(b_hint))} times on boot B.',
        id_='fig-B3',
        note=f'File {f_csv} of each boot {r_all}. The {V.size_label(big)} footprint is larger than the SLC size '
             f'of 3.75 MiB est. (operator\'s README) {r_slc}. These rows are DRAM-backed. The DRAM model is an '
             f'emulator memory with zero configured delay, not silicon timing (operator\'s README) {r_dram}. No '
             f'counter of these rows separates an SLC hit from a fill by the DRAM model.')
    h += S.bullets([
        f'Plain read at {V.size_label(big)}: {n3(plain["E"]["best"])} GB/s on boot E, {n3(plain["C"]["best"])} '
        f'GB/s on boot C and {n3(plain["B"]["best"])} GB/s on boot B. Boot C over boot B is '
        f'{n2(cmp_["pf_effect"])} times (the prefetcher effect). Boot E over boot C is '
        f'{n2(cmp_["l3_effect"])} times (the L3 effect, an open item, {S.xref("open-l3")}). Boot E over boot B is '
        f'{n2(cmp_["e_over_b"])} times, with both the prefetchers and the L3 different.',
        f'Counters of the plain read ({S.tabref("tab-TB5")}): boots E and C count {n4(plain["E"]["l1pf"])} and '
        f'{n4(plain["C"]["l1pf"])} L1 prefetch refills per 64 bytes. '
        f'Boot B counts {n4(plain["B"]["l1pf"])}.',
        f'On boot C the L3 holds no data, so every line comes from outside the cluster. Its plain read still '
        f'counts at most {n4(c_a2_max)} L3 read refills per 64 bytes (best reps of the two footprints). So the L3 read refill count leaves out the '
        f'fills that the prefetchers request.',
        f'The hint and the second stream: {S.figref("fig-B3")} and {S.tabref("tab-TB4")} give each variant on '
        f'each boot. At {V.size_label(big)} the hint changes the rate of boot C (prefetchers on, the L3 holds '
        f'no data) by {V.signed(min(c_hint), 1)} to {V.signed(max(c_hint), 1)} %. At {V.size_label(small)} it '
        f'changes it by {V.signed(min(c_hint_small), 1)} to {V.signed(max(c_hint_small), 1)} %. At '
        f'{V.size_label(big)} the L1 prefetch refills of boot E fall to '
        f'{n2(e_hint_l1pf[0])}, {n2(e_hint_l1pf[1])} and {n2(e_hint_l1pf[2])} per 64 bytes with the hint 4, 8 and '
        f'16 lines ahead, while the L1 refills stay at {n2(e_hint_l1[0])}.'])
    h += S.hyp(
        f'The core starts at most two loads per cycle (SOG). On boot E each hint uses one of them. So fewer '
        f'loads of data start per cycle. The SOG lists the prefetch hint with the load instructions {r_sog}.',
        f'The software prefetch rows on a {V.size_label(16 * KIB)} buffer, where the read stream refills no line.')
    h += S.insufficient(
        'The prefetcher effect with the L3 on. No boot has core rows with the L3 on and the prefetchers off '
        '(%s).' % S.figref('fig-P2'))

    trs = []
    for s in sizes:
        trs.append('%s (spread of the rows: %s)' % (V.size_label(s), ', '.join(
            'boot %s %s to %s %%' % (b, n2(spread_of[(b, s)][0]), n2(spread_of[(b, s)][1])) for b in boots)))
        for k in kernels:
            row = [by[('E', k, s)]['kernel_label']]
            for b in boots:
                r = by[(b, k, s)]
                row += [n3(r['best']), n3(r['ratio_plain'])]
            trs.append(row)
    h += S.table(
        ['Read variant', 'Boot E, GB/s', 'Boot E, ratio to plain', 'Boot C, GB/s', 'Boot C, ratio to plain',
         'Boot B, GB/s', 'Boot B, ratio to plain'],
        trs,
        caption='The read variants on three boots, CPU 2, three reps per row. Boot E: L3 on, prefetchers on. '
                'Boot C: the L3 holds no data, prefetchers on. Boot B: the L3 holds no data, prefetchers off.',
        note=f'File {f_csv} of each boot {r_all}. The {V.size_label(small)} rows spread up to '
             f'{n1(worst_small["spread_pct"])} % (boot {worst_small["boot"]}, {worst_small["kernel_label"]}) '
             f'against at most {n2(big_spread_max)} % at {V.size_label(big)}. So the figure uses the '
             f'{V.size_label(big)} rows. At {V.size_label(small)} boot B reads {n3(b_plain_small["best"])} GB/s, '
             f'{n1(b_plain_small["best"] / plain["B"]["best"])} times its {V.size_label(big)} rate. Insufficient '
             f'data: no counter of these rows separates lines that the SLC serves from lines that the DRAM model '
             f'serves at {V.size_label(small)}. So the page draws no conclusion from the {V.size_label(small)} '
             f'rows.',
        id_='tab-TB4')

    trs = []
    for b in boots:
        trs.append(leg[b])
        for k in kernels:
            r = by[(b, k, big)]
            trs.append([r['kernel_label'], n2(r['cyc_line']), n4(r['l1']), n4(r['l1pf']), n4(r['a2'])])
    h += S.table(
        ['Read variant', 'Counted cycles per 64 bytes transferred', 'L1 refills', 'L1 prefetch refills',
         'L3 read refills'],
        trs,
        caption=f'Counters per 64 bytes transferred at {V.size_label(big)}, best rep.',
        note=f'Files as in {S.tabref("tab-TB4")}. The counts are aggregates and do not give the history of a '
             f'line. The L1 refills include prefetch fills. An L3 read refill count near 0 does not show that the '
             f'lines were served inside the cluster. The three prefetch refill events read at most '
             f'{V.num(pf_events_b_max, 5)} per 64 bytes on boot B ({S.xref("setup-counters")}).',
        id_='tab-TB5')
    return h


def build(D, V, S):
    # The subsection "Stream against chain" is cut (critic sheet, cut order).
    return _one_core(D, V, S) + _l1_forms(D, V, S) + _variants(D, V, S)
