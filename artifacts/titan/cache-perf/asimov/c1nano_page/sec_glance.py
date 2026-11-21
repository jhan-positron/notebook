"""Section 2 "Results at a glance" of asimov-c1nano-perf.html.

Subsections: the numbers to quote (table TG1) and the repeatability (figure G1, table TG2).
Every measured number is read from the data layer D when the page is built.
"""

KEY = 'glance'
TITLE = 'Results at a glance'

KIB = 1024
MIB = 1024 * 1024


# ------------------------------------------------------------------ small helpers

def _n(v, d=3):
    return '%.*f' % (d, v)


def _code(name):
    return '<code>%s</code>' % name


def _rowref(S, row, what, prefix=''):
    """[RefN] of the timed row that carries the best value of a derived row."""
    boot = row[prefix + 'boot'] if prefix else row['boot']
    return S.ref('file:%s:%s:%d' % (boot, row[prefix + 'file'], row[prefix + 'line']), what)


def _refs(*links):
    """Several [RefN] links, each one once, in the order given."""
    seen = []
    for l in links:
        for one in l.split(' <a '):
            one = one if one.startswith('<a ') else '<a ' + one
            if one not in seen:
                seen.append(one)
    return ' '.join(seen)


def _slash(vals, d=3):
    return ' / '.join(_n(v, d) for v in vals)


# ------------------------------------------------------------------ 2.1 numbers to quote

def _numbers(D, V, S):
    sw = lambda size: D.sweep_row('F1', size)          # noqa: E731
    l1, l2, c384, c2m = sw(4 * KIB), sw(128 * KIB), sw(384 * KIB), sw(2 * MIB)
    flushed = D.lat_flushed
    est = D.l3_est_summary
    direct = est['direct_row']
    c2 = D.lat_cluster['chain2m']
    seq = {r['boot']: r for r in D.lat_seq}
    every = [r for r in D.ocm_all5 if r['shape'] == 'every line']
    fit = D.ocm_fit['B']
    route = D.ocm_route['B']
    one = D.one_core
    rd16, rd48, rd32m = one('read', 16 * KIB), one('read', 48 * KIB), one('read', 32 * MIB)
    wr48, wr32m = one('write', 48 * KIB), one('write', 32 * MIB)
    cp16, cp32m = one('copy', 16 * KIB), one('copy', 32 * MIB)
    rd_large = [r for r in D.bw_1core if r['kernel'] == 'read' and r['size'] >= 48 * KIB]
    wr_large = [r for r in D.bw_1core if r['kernel'] == 'write' and r['size'] >= 48 * KIB]
    kernels = ('read', 'write', 'copy')
    per = [D.mc('one core per cluster', k, 2 * MIB) for k in kernels]
    all8 = [D.mc('all eight cores', k, 2 * MIB) for k in kernels]
    wr = {r['list']: r for r in D.mc_writers}
    ocm_rd = next(r for r in D.ocm_bw if r['kernel'] == 'read' and r['threads'] == 1 and r['region'] is None)
    ocm_wr = next(r for r in D.ocm_bw if r['kernel'] == 'write')

    S.term('latency test'); S.term('bandwidth test'); S.term('home node'); S.term('SLC'); S.term('OCM')
    S.term('mesh'); S.term('step'); S.term('SOG'); S.term('every line'); S.term('every line flushed first')
    S.term('walked many times'); S.term('walked once'); S.term('address order'); S.term('hit set')
    S.term('effective cycles per 64 bytes transferred'); S.term('residual')

    readme = S.ref('readme:F1')
    sog = S.ref('doc:sog')

    def sec(id_):
        return S.xref(id_)

    def cyc(r):
        return '%s ns (%s cycles)' % (_n(r['best']), _n(r['cycles'], 2))

    def row(quantity, value, id_, *links):
        return [quantity, value, sec(id_) + (' ' + _refs(*links) if links else '')]

    est_sizes = ' and '.join(V.size_label(x) for x in est['sizes'])
    cpus = sorted({r['cpu'] for r in route})
    regions = sorted({r['region'] for r in route})
    rows = [
        'Latency, ns per load (CPU 2 unless the row names another CPU)',
        row('L1, 4 KiB chain', cyc(l1), 'lat-footprint', _rowref(S, l1, 'the 4 KiB chain')),
        row('L2, 128 KiB chain', cyc(l2), 'lat-footprint', _rowref(S, l2, 'the 128 KiB chain')),
        row('384 KiB chain (L2 + L3 sizes added). A mixed row: %s L3 hits per load counted on boot E (the '
            'firmware state of boot F1, another command set)' % _n(direct['l3hit'], 2), cyc(c384), 'lat-footprint', _rowref(S, c384, 'the 384 KiB chain')),
        row('L3-served load (boot E, %s rows of the hit set)' % est_sizes,
            '%s to %s ns est.' % (_n(est['lo'], 1), _n(est['hi'], 1)), 'lat-l3',
            S.ref('file:E:latency-dram-small-l3.csv:%d' % direct['line'], 'the 384 KiB row of the hit set')),
        row('Home nodes over the mesh (interpreted as the SLC), 2 MiB chain', cyc(c2m), 'lat-levels',
            _rowref(S, c2m, 'the 2 MiB chain')),
        row('2 MiB chain on CPUs 4 / 6 / 8', _slash([r['best'] for r in c2 if r['cpu'] != 2]) + ' ns',
            'lat-clusters', S.ref('group:F1:latency-dram-slc-cpu*.csv')),
        row('DRAM model, 8 MiB chain, every line flushed first', cyc(flushed), 'lat-dram',
            _rowref(S, flushed, 'the 8 MiB chain with every line flushed first')),
        row('8 MiB chain in address order: boot E (L3 on, prefetchers on) / boot C (the L3 holds no data, '
            'prefetchers on) / boot B (the L3 holds no data, prefetchers off)',
            _slash([seq[b]['best'] for b in ('E', 'C', 'B')]) + ' ns', 'lat-order',
            *[_rowref(S, seq[b], 'the 8 MiB chain in address order') for b in ('E', 'C', 'B')]),
        'OCM',
        row('OCM row (every line, all five regions) on CPUs 2 / 4 / 6 / 8',
            _slash([r['best'] for r in every]) + ' ns', 'ocm-quote',
            S.ref('group:F1:latency-ocm-all5-dense-cpu*.csv')),
        row('Per-region rows on boot B (prefetchers off, the L3 holds no data), %d cells (%d CPUs x %d regions)'
            % (len(route), len(cpus), len(regions)),
            '%s to %s ns' % (_n(min(r['best'] for r in route)), _n(max(r['best'] for r in route))),
            'ocm-region', S.ref('group:B:latency-ocm-region*-route-cpu*.csv')),
        row('One more mesh step of distance, whole round trip (fit over the %d cells of boot B, prefetchers off, '
            'the L3 holds no data. Largest residual %s ns = %s %% of the smallest cell)' % (
                len(route), _n(fit['max_res']), _n(fit['pct_of_smallest'], 2)),
            '+%s ns per X step, +%s ns per Y step' % (_n(fit['bx']), _n(fit['cy'])), 'ocm-region',
            S.ref('group:B:latency-ocm-region*-route-cpu*.csv')),
        row('OCM bandwidth, all five regions, one core, read / write',
            _slash([ocm_rd['best'], ocm_wr['best']]) + ' GB/s', 'ocm-bw',
            _rowref(S, ocm_rd, 'the read of all five OCM regions'),
            _rowref(S, ocm_wr, 'the write of all five OCM regions')),
        'One-core bandwidth on CPU 2, GB/s',
        row('Read, 16 KiB',
            '%s GB/s (%s bytes per cycle, %s %% of the documented %s bytes per cycle)' % (
                _n(rd16['best']), _n(rd16['bytes_per_cycle'], 2), _n(rd16['pct_doc'], 1),
                _n(D.doc['read_bytes_per_cycle'], 0)),
            'bw-1core', _rowref(S, rd16, 'the 16 KiB read'), sog),
        row('Read, 48 KiB to 32 MiB',
            '%s to %s GB/s (%s to %s effective cycles per 64 bytes transferred)' % (
                _n(max(r['best'] for r in rd_large)), _n(min(r['best'] for r in rd_large)),
                _n(min(r['eff_cycles_64'] for r in rd_large), 2), _n(max(r['eff_cycles_64'] for r in rd_large), 2)),
            'bw-1core', _rowref(S, rd48, 'the 48 KiB read'), _rowref(S, rd32m, 'the 32 MiB read')),
        row('Write, 48 KiB to 32 MiB',
            '%s to %s GB/s (%s effective cycles per 64 bytes transferred at 32 MiB)' % (
                _n(min(r['best'] for r in wr_large)), _n(max(r['best'] for r in wr_large)),
                _n(wr32m['eff_cycles_64'])),
            'bw-1core', _rowref(S, wr48, 'the 48 KiB write'), _rowref(S, wr32m, 'the 32 MiB write')),
        row('Copy, 16 KiB / 32 MiB (read and written bytes both counted)',
            _slash([cp16['best'], cp32m['best']]) + ' GB/s', 'bw-1core',
            _rowref(S, cp16, 'the 16 KiB copy'), _rowref(S, cp32m, 'the 32 MiB copy')),
        'Multi-core bandwidth, GB/s (sum of the cores)',
        row('One core per cluster (%d cores), 2 MiB per core, read / write / copy' % per[0]['threads'],
            '%s GB/s (%s times one core)' % (_slash([r['agg'] for r in per]), _slash([r['scaling'] for r in per])),
            'mc-clusters', S.ref('file:F1:bandwidth-perdsu.csv')),
        row('All eight cores, 2 MiB per core, read / write / copy',
            '%s GB/s (%s times one core)' % (_slash([r['agg'] for r in all8]), _slash([r['scaling'] for r in all8])),
            'mc-clusters', S.ref('file:F1:bandwidth-all8.csv')),
        row('Two writers at 16 MiB each: CPUs 2,4 (two clusters) / CPUs 2,3 (one cluster)',
            '%s GB/s (one cluster: %s times two clusters)' % (_slash([wr['2-4']['agg'], wr['2-3']['agg']]),
                                                             _n(wr['2-3']['ratio_control'])),
            'mc-writers', _rowref(S, wr['2-4'], 'two writers on CPUs 2 and 4'),
            _rowref(S, wr['2-3'], 'two writers on CPUs 2 and 3')),
    ]

    out = S.h3('glance-numbers', 'Numbers to quote')
    out += S.table(['Quantity', 'Value', 'Detail'], rows,
                   caption='Numbers to quote. Each value is a best row of boot F1, unless the row names another '
                           'boot.',
                   note='Latency values are chain loads. "Documented" is the instruction throughput of the '
                        'read loop in bytes per cycle (SOG).',
                   align='lll', id_='tab-TG1')
    out += S.p('Five limits apply to these numbers.')
    out += S.bullets([
        'The DRAM model is an emulator memory with zero configured delay, not silicon timing (operator\'s '
        'README) %s. This applies to the %s ns row, to the 8 MiB chain in address order, to every DRAM-backed '
        'bandwidth row (2 MiB and more), and to every multi-core row.' % (readme, _n(flushed['best'])),
        'A bandwidth value is loop throughput: bytes transferred over elapsed time. No write row waits for '
        'its lines to reach the DRAM model.',
        'No counter inside the timed interval separates an SLC hit from a fill by the DRAM model. So the '
        'split of a 2 MiB row between the two is not known (%s).' % S.xref('setup-bandwidth-test'),
        'The L3 status register is read on the cluster of CPU 2 only (operator\'s README) %s. So no reading '
        'confirms the L3 state for a row from CPUs 4 to 9.' % readme,
        'The L3 hit count and the L3-served estimate come from the hit set of boot E. These events are '
        'exploratory, with three consistency checks (%s). The estimate uses the two rows that count more than '
        '0.5 L3 hits per load. The 192 KiB row gives %s ns est.' % (
            S.xref('lat-l3'), _n(est['est_192k'][0], 1)),
    ])
    assert _n(est['est_192k'][0], 1) == _n(est['est_192k'][1], 1)
    S.term('exploratory')
    return out


# ------------------------------------------------------------------ 2.2 repeatability

GROUP_LABEL = {      # group of D.repeat -> (label, detail)
    'walked many times': ('Chains walked many times', '4 to 384 KiB'),
    'walked once': ('Chains walked once', '512 KiB to 32 MiB'),
    'every line flushed first': ('8 MiB chain, every line flushed first', ''),
    'background control': ('Background control', 'CPUs 2 and 8'),
    'OCM, every line, all five': ('OCM chain, every line', 'all five regions, CPUs 2 and 8'),
    'OCM, one line per page, all five': ('OCM chain, one line per page', 'all five regions, CPUs 2 and 8'),
    'plain read': ('Plain read', '2 MiB and 32 MiB'),
    'looped 16 KiB': ('Looped read and write', '16 KiB'),
}


def _short(label):
    """'768 KiB, walked once' -> '768 KiB'; 'OCM, every line, all five, CPU 2' -> 'CPU 2'."""
    parts = [p.strip() for p in label.split(',')]
    if parts[0].startswith('OCM') or parts[0].startswith('background'):
        return parts[-1]
    if parts[0].startswith('plain read') or parts[0].startswith('looped'):
        return parts[0].replace('plain ', '').replace('looped ', '') if len(parts) == 1 else \
            (parts[1] if parts[0].startswith('plain') else parts[0].replace('looped ', ''))
    return parts[0]


def _worst_label(D, g):
    """Label that names one row: the row with the largest spread of a group of D.spread_groups."""
    if g['group'] == 'OCM chain, one line per page, one region':
        c = next(r for r in D.ocm_cells if r['file'] == g['file'])
        return 'region %d, CPU %d' % (c['region'], c['cpu'])
    if g['group'].startswith('OCM chain'):
        return 'CPU %d' % next(r for r in D.ocm_all5 if r['file'] == g['file'])['cpu']
    if g['group'] == 'OCM bandwidth':
        b = next(r for r in D.ocm_bw if r['file'] == g['file'])
        return '%s, %s' % (b['kernel'], b['name'])
    return g['max_label']


def _repeat(D, V, S):
    rep = D.repeat
    summ = D.repeat_summary
    groups = D.repeat_groups
    by_group = {}
    for r in rep:
        by_group.setdefault(r['group'], []).append(r)
    # Derived here: the rows outside 0.98 to 1.02, and the walked-once range without its two extremes.
    outside = [r for r in rep if not 0.98 <= r['ratio'] <= 1.02]
    once = sorted(by_group['walked once'], key=lambda r: r['ratio'])
    once_mid = once[1:-1]
    once_lo, once_hi = once[0], once[-1]
    n_in = len(rep) - len(outside)
    lat = D.lat_sweep_summary
    over = lat['spread_over_0_7']
    sg = D.spread_groups
    cells = next(g for g in sg if g['group'].startswith('OCM chain, one line per page, one region'))
    every2 = next(r for r in rep if r['id'] == 'ocm-every-cpu2')

    S.term('background control'); S.term('looped form'); S.term('plain read'); S.term('one line per page')
    # The four OCM chains over all five regions, each with the reps of the row itself on both boots.
    ocm4 = [next(r for r in rep if r['id'] == i)
            for i in ('ocm-page-cpu2', 'ocm-page-cpu8', 'ocm-every-cpu2', 'ocm-every-cpu8')]
    page2, page8, every2r, every8r = ocm4
    n_disjoint = sum(1 for r in rep if r['disjoint'])
    # Rows whose ranges are apart by a few units of the last printed digit, and rows whose ranges are
    # apart with best rows more than 2 % apart: the text below names the second set.
    tiny = [r for r in rep if r['disjoint'] and round(r['gap'], 3) <= 0.005]
    far = [r for r in rep if r['disjoint'] and abs(r['ratio'] - 1) > 0.02]
    if sorted(r['id'] for r in far) != ['chain-4194304-once', 'chain-786432-once',
                                        'ocm-every-cpu2', 'ocm-page-cpu2']:
        raise ValueError('glance: the rows with separate rep ranges and best rows over 2 % apart moved')
    once_disjoint = [r for r in by_group['walked once'] if r['disjoint']]
    once_above = [r for r in once_disjoint if r['ratio'] > 1]

    # ---- figure G1
    frows = []
    for g in groups:
        rs = sorted(by_group[g['group']], key=lambda r: r['ratio'])
        lab, sub = GROUP_LABEL[g['group']]
        row = dict(label=lab, sub='%d row%s%s' % (g['n'], '' if g['n'] == 1 else 's', ', ' + sub if sub else ''),
                   values=[[r['ratio'] for r in rs]], labels='none',
                   tip='\n'.join('%s: %s' % (r['label'], _n(r['ratio'])) for r in rs))
        if g['n'] == 1:
            row['note'] = _n(g['lo'])
        elif g['group'] == 'walked once':
            row['note'] = '%s (left), %s (right)' % (_short(once_lo['label']), _short(once_hi['label']))
            row['labels'] = 'ends'
        else:
            row['note'] = '%s to %s' % (_n(g['lo']), _n(g['hi']))
        frows.append(row)
    svg = V.dot_rows(frows, [dict(name='boot E over boot F1', color='f1', hollow=True)],
                     unit='', fmt=lambda v: V.num(v, 3), xlabel='ratio, boot E over boot F1',
                     band=(0.98, 1.02, 'within 2 % of boot F1'), refs=[(1.0, 'equal')],
                     xrange=(0.95, 1.11), label_w=250, title='boot E over boot F1 per shared row')
    fig = S.fig(
        svg,
        'Boot E over boot F1, one ring per shared row (%d rows). The bold text gives the range of the group. '
        'For the chains walked once the two end rings carry their ratio, and the bold text names their '
        'footprints.' % len(rep),
        '%d of %d rows of boot E lie within 2 %% of boot F1, and all %d chains up to 384 KiB lie within %s %%.'
        % (n_in, len(rep), len(by_group['walked many times']),
           _n(max(abs(r['ratio'] - 1) for r in by_group['walked many times']) * 100, 2)),
        id_='fig-G1',
        note='A ratio is the best row of boot E over the best row of boot F1. Rings of near-equal ratio overlap. '
             'The chain rows come from files of the same name on both boots %s. The plain reads and the looped '
             '16 KiB rows of boot E come from other commands with the same kernel and footprint %s %s. The '
             'looped 16 KiB rows of boot E are the best of 5 reps, against 3 reps on boot F1.'
             % (S.ref('group:E:latency-*.csv'), S.ref('file:E:bandwidth-read-prefetch.csv'),
                S.ref('file:E:bandwidth-l1-passes.csv')))

    # ---- figure G2: the reps of the four OCM chains over all five regions, per boot
    def _own(r):
        return ('ranges %s ns apart' % _n(r['gap'])) if r['disjoint'] else 'ranges overlap'

    def _cpu(r):
        return int(r['id'][-1])
    orows = []
    for r in ocm4:
        shape = 'One line per page' if r['id'].startswith('ocm-page') else 'Every line'
        orows.append(dict(label='%s, CPU %d' % (shape, _cpu(r)),
                          sub='%d reps per boot, boot E best over boot F1 best %s' % (len(r['f1_reps']), _n(r['ratio'])),
                          values=[r['f1_reps'], r['e_reps']], labels='none', note=_own(r),
                          tip='boot F1: %s\nboot E: %s' % (', '.join(_n(v) for v in r['f1_reps']),
                                                           ', '.join(_n(v) for v in r['e_reps']))))
    svg2 = V.dot_rows(orows, [dict(name='boot F1, one rep', color='f1'),
                              dict(name='boot E, one rep', color='f1', hollow=True)],
                      unit='ns', fmt=lambda v: V.num(v, 3), xlabel='chain load of one rep, ns',
                      xrange=(23.0, 28.5), label_w=330, title='reps of the OCM chains over all five regions, per boot')

    def _reps_ref(boot, fn):
        rr = D.latrow(boot, fn)['rep_rows']
        return S.ref('file:%s:%s:%d-%d' % (boot, fn, rr[0]['line'], rr[-1]['line']), 'the reps of the row')
    ocm_refs = ' '.join(_reps_ref(b, r['file']) for r in ocm4 for b in ('F1', 'E'))
    fig2 = S.fig(
        svg2,
        'The reps of the four OCM chains over all five regions on boot F1 (filled) and on boot E (hollow). One '
        'mark is one rep. The bold text compares the two ranges of the row.',
        'On CPU 2 every rep of boot E reads above every rep of boot F1, on both chain shapes. On CPU 8 the '
        'one-line-per-page ranges overlap.',
        id_='fig-G2',
        note='Files of the same name on both boots %s. The axis does not start at zero. Boot E runs another '
             'benchmark build and another command order than boot F1 (%s).' % (ocm_refs, S.tabref('tab-TS2')))

    # ---- table TG2
    trows = []
    hl = []
    for i, g in enumerate(sg):
        name = 'Pair (two cores of one cluster)' if g['group'] == 'pair' else g['group'][0].upper() + g['group'][1:]
        trows.append([name, '%d' % g['n'], _n(g['min'], 2), _n(g['max'], 2),
                      '%s %s' % (_worst_label(D, g),
                                 S.ref('file:F1:%s:%d' % (g['file'], g['line']),
                                       'the best rep of the row with the largest spread of its group'))])
        if g['max'] > 2.0:
            hl.append(i)
    tab = S.table(['Row group', 'Rows', 'Lowest', 'Highest', 'Row at the highest value'],
                  trows, caption='Spread of the reps inside boot F1 by row group, in percent of the best row. %s '
                                 'gives boot E over boot F1 for the groups that boot E also ran: the chains of '
                                 'CPU 2, and the all-five OCM chains of CPUs 2 and 8. Boot E has no row for the '
                                 'other groups.' % S.figref('fig-G1'),
                  note='Highlighted: a group with a spread over 2 %.',
                  highlight=hl, align='lrrrl', id_='tab-TG2')

    out = S.h3('glance-repeat', 'Repeatability')
    out += S.p('Two measures show how well a row repeats: the spread of the reps inside boot F1, and the same '
               'row on boot E (the firmware state of boot F1, another command set). Boot E is a second sample '
               'only.')
    out += fig
    out += S.bullets([
        'The %d chains walked once read %s to %s times. Without the %s row (%s) and the %s row (%s) the range '
        'is %s to %s. On %d of the %d the two reps of boot E and the two reps of boot F1 do not overlap, and '
        'boot E reads higher on %d of these.' % (
            len(once), _n(summ['walked_once'][0]), _n(summ['walked_once'][1]),
            _short(once_hi['label']), _n(once_hi['ratio']),
            _short(once_lo['label']), _n(once_lo['ratio']),
            _n(once_mid[0]['ratio']), _n(once_mid[-1]['ratio']),
            len(once_disjoint), len(once), len(once_above)),
        'The other %d rows outside 2 %% are OCM chains over all five regions: %s.'
        % (len([r for r in outside if r['group'].startswith('OCM')]),
           ', '.join('%s on %s (%s)' % (r['group'].split(', ')[1], _short(r['label']), _n(r['ratio']))
                     for r in outside if r['group'].startswith('OCM'))),
        'Inside boot F1 the spread is under 0.7 %% on %d of the %d chains of CPU 2 (4 KiB to 32 MiB). The other '
        '%d are %s.' % (lat['n_spread_under_0_7'], lat['n'], len(over),
                        ', '.join('%s (%s %%)' % (lab, _n(s, 2)) for lab, s in over)),
    ])
    out += tab
    out += S.p('A ratio of two best rows is judged against the reps of the same row on both boots, not against '
               'the spread of a row group. %s shows this for the four OCM chains over all five regions.'
               % S.figref('fig-G2'))
    out += fig2
    out += S.bullets([
        'One line per page, CPU 2: the %d reps read %s to %s ns on boot F1 (spread %s %%) and %s to %s ns on '
        'boot E (spread %s %%). The two ranges do not overlap. They are %s ns apart, and the best row of boot E '
        'is %s %% above the best row of boot F1.' % (
            len(page2['f1_reps']), _n(page2['f1_lo']), _n(page2['f1_hi']), _n(page2['f1_spread_pct'], 2),
            _n(page2['e_lo']), _n(page2['e_hi']), _n(page2['e_spread_pct'], 2), _n(page2['gap']),
            _n((page2['ratio'] - 1) * 100, 2)),
        'One line per page, CPU 8: the reps read %s to %s ns on boot F1 (spread %s %%) and %s to %s ns on boot '
        'E (spread %s %%). The two ranges overlap, and the best row of boot E is %s %% below the best row of '
        'boot F1.' % (
            _n(page8['f1_lo']), _n(page8['f1_hi']), _n(page8['f1_spread_pct'], 2),
            _n(page8['e_lo']), _n(page8['e_hi']), _n(page8['e_spread_pct'], 2),
            _n((1 - page8['ratio']) * 100, 2)),
        'Every line (%d reps per boot): on CPU 2 the ranges are %s ns apart (boot E %s %% higher). On CPU 8 '
        'they are %s ns apart (boot E %s %% lower).' % (
            len(every2r['f1_reps']), _n(every2r['gap']), _n((every2r['ratio'] - 1) * 100, 2),
            _n(every8r['gap']), _n((1 - every8r['ratio']) * 100, 2)),
        'Over all %d shared rows the rep ranges of the two boots do not overlap on %d rows (%d of them have '
        'one rep per boot). On %d of the %d the two ranges are at most %s ns or GB/s apart, and the files '
        'print 3 decimals. On %d of the %d the best rows also differ by more than 2 %%. So the spread of the '
        'reps inside one boot is not a limit for the difference between two boots.' % (
            len(rep), n_disjoint, sum(1 for r in rep if r['disjoint'] and len(r['f1_reps']) == 1),
            len(tiny), n_disjoint, _n(max(r['gap'] for r in tiny)), len(far), n_disjoint),
    ])
    out += S.insufficient(
        'Only boot F1 and boot E have this firmware state. So each ratio has two samples only, and the two '
        'boots also differ in the benchmark build and in the command order. No file shows whether a difference '
        'with separate rep ranges belongs to the boot, to the build or to the process of the command. A third '
        'boot in that state with the build and the commands of boot F1 would show whether the four differences '
        'of more than 2 %% with separate rep ranges repeat: at %s, at %s, and on the two OCM chains of CPU 2 over all five regions (every line %s times, '
        'one line per page %s times) (%s).'
        % (_short(once_hi['label']), _short(once_lo['label']), _n(every2['ratio']), _n(page2['ratio']),
           S.xref('open-items')))
    return out


def build(D, V, S):
    return _numbers(D, V, S) + _repeat(D, V, S)
