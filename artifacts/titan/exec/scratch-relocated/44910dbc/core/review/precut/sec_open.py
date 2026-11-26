"""Section 8 of asimov-c1nano-perf.html: open items and what was not measured.

Every measured number is read from the data layer D when the page is built.
Values that D does not hold are computed here from D's rows (see _derived).
"""

KEY = 'open'
TITLE = 'Open items and what was not measured'

KIB = 1024
MIB = 1024 * 1024


def _c(name):
    return '<code>%s</code>' % name


def _cite(S, items, text):
    """One [RefN] link per file.  items: (boot, file, line) tuples.  All line numbers of a
    file go into one key, so the References list each file once."""
    by = {}
    for boot, file_, line in items:
        if line is None:
            continue
        ls = by.setdefault((boot, file_), [])
        for n in (line if isinstance(line, (list, tuple)) else [line]):
            if n not in ls:
                ls.append(n)
    out = []
    for (boot, file_), ls in by.items():
        out.append(S.ref('file:%s:%s:%s' % (boot, file_, ','.join(str(n) for n in sorted(ls))), text))
    return ''.join(out)


def _row(r, prefix=''):
    """(boot, file, line) of a derived row, or of its other side (prefix 'r3_', 'e_', 'c_', 'b_')."""
    return (r[prefix + 'boot'], r[prefix + 'file'], r[prefix + 'line'])


def _derived(D):
    """Values that the data layer does not hold as one number.  Each is computed from D's rows."""
    X = {}
    # the every-line all-five OCM chain: largest over smallest node count, per command
    all5 = [r for r in D.mesh_cmd if r['group'] == 'OCM chain, every line, all five']
    X['all5_mesh'] = all5
    spans = [max(r['counts']) / float(min(r['counts'])) for r in all5]
    X['all5_span'] = (min(spans), max(spans))
    X['all5_low_node'] = sorted(set(min(r['nodes'], key=r['nodes'].get) for r in all5))
    X['all5_high_node'] = sorted(set(max(r['nodes'], key=r['nodes'].get) for r in all5))
    # the four-core OCM read: regions 1 to 4, one reader per region
    fc = D.mesh_summary['four_core']
    busy = [D.REGION_NODE[i] if hasattr(D, 'REGION_NODE') else None for i in (1, 2, 3, 4)]
    if None in busy:
        from . import data as _data
        busy = [_data.REGION_NODE[i] for i in (1, 2, 3, 4)]
    low = min(busy, key=lambda n: fc['nodes'][n])
    others = [fc['nodes'][n] for n in busy if n != low]
    below = [100.0 * (1.0 - fc['nodes'][low] / float(v)) for v in others]
    X['four_core'] = fc
    X['four_low_node'] = low
    X['four_low_count'] = fc['nodes'][low]
    X['four_others'] = (min(others), max(others))
    X['four_below_pct'] = (min(below), max(below))
    # writer placement: requests received per node, two writers in one cluster against two clusters
    w = {r['list']: r for r in D.mc_writers}
    X['w'] = w
    X['w_one_cluster_nodes'] = (min(w['2-3']['node_counts']), max(w['2-3']['node_counts']))
    X['w_two_cluster_nodes'] = (min(w['2-4']['node_counts']), max(w['2-4']['node_counts']))
    # software prefetch against the plain read: boot E change in percent, boot B ratio, boot E counters
    pf = ('read-pf4', 'read-pf8', 'read-pf16')
    e = [r for r in D.bw_var if r['boot'] == 'E' and r['kernel'] in pf]
    b = [r for r in D.bw_var if r['boot'] == 'B' and r['kernel'] in pf]
    X['pf_e_rows'], X['pf_b_rows'] = e, b
    X['pf_e_change'] = (max(r['change_pct'] for r in e), min(r['change_pct'] for r in e))
    X['pf_b_ratio'] = (min(r['ratio_plain'] for r in b), max(r['ratio_plain'] for r in b))
    X['pf_e_l1pf'] = (min(r['l1pf'] for r in e), max(r['l1pf'] for r in e))
    # footprint of the 32 MiB read over the L3 size
    X['x_l3'] = 32 * MIB / float(D.platform['cache_bytes']['L3'])
    # the walked-once 8 MiB chain against the DRAM-model row
    X['once_8m'] = D.sweep_row('F1', 8 * MIB)
    X['flushed'] = D.lat_flushed
    X['once_below_ns'] = X['flushed']['best'] - X['once_8m']['best']
    return X


def _fig_p1(D, V, S):
    o = {r['id']: r for r in D.open_l3}

    def row(id_, label, sub=None):
        r = o[id_]
        d = dict(label=label, values=[r['f1'], r['r3']], note=V.ratio(r['ratio']))
        if sub:
            d['sub'] = sub
        return d

    rows = [
        dict(header='One-core read, GB/s'),
        row('read-49152', '48 KiB', 'fits the L2'),
        row('read-98304', '96 KiB', 'fits the L2'),
        row('read-262144', '256 KiB'),
        row('read-2097152', '2 MiB'),
        row('read-33554432', '32 MiB'),
        dict(header='Several readers, GB/s per reader'),
        row('four-readers-2097152', 'four readers, 2 MiB each', 'one per cluster'),
        row('eight-readers-2097152', 'eight readers, 2 MiB each', 'two per cluster'),
        dict(header='OCM read, GB/s'),
        row('ocm-read-all5', 'all five regions'),
        dict(header='Rows that are not a read stream'),
        row('write-32m', 'one-core write, 32 MiB, GB/s'),
        row('chain-32m', '32 MiB chain, ns per load'),
    ]
    return V.dot_rows(
        rows,
        [dict(name='boot F1 (L3 on, prefetchers on)', color='f1'),
         dict(name='boot R3 (the L3 holds no data, prefetchers on)', color='c')],
        unit='', fmt=lambda v: V.num(v, 1), connect=True, labels='all',
        xlabel='GB/s (last row: ns per load)', xrange=(0, None), label_w=230)


def _fig_p2(D, V, S):
    nm = D.not_measured
    kinds = ['f1', 'f1', 'c', 'off']
    rows = []
    for r in nm['rows']:
        cells = []
        for i, c in enumerate(r['cells']):
            if c:
                cells.append(dict(text=', '.join(c), kind=kinds[i]))
            else:
                cells.append(dict(text='not measured', kind='mute'))
        rows.append(dict(label=r['family'], cells=cells))
    cols = ['L3 on\nprefetchers on', 'L3 on\nprefetchers off', 'L3 holds no data\nprefetchers on',
            'L3 holds no data\nprefetchers off']
    return V.grid(cols, rows,
                  legend_items=[('boots F1, E', 'f1'), ('boots C, R3', 'c'), ('boots B, D', 'off'),
                                ('not measured', 'mute')],
                  width=1000, label_w=250, corner='row family')


def build(D, V, S):
    X = _derived(D)
    n3 = lambda v: V.num(v, 3)
    n2 = lambda v: V.num(v, 2)
    n1 = lambda v: V.num(v, 1)
    n0 = lambda v: V.num(v, 0)
    o = {r['id']: r for r in D.open_l3}
    os_ = D.open_l3_summary
    ec = {r['id']: r for r in D.open_ec}

    for t in ('SLC', 'OCM', 'home node', 'mesh', 'step', 'hit set', 'exploratory', 'looped form',
              'single-call form', 'plain read', 'software prefetch N lines ahead', 'walked once',
              'every line flushed first', 'address order', 'every line', 'refill', 'L3 read refill',
              'requests received', 'requests sent on to memory', 'L2 refills not accounted for',
              'effective cycles per 64 bytes transferred', 'residual', 'rms', 'CME', 'command'):
        S.term(t)

    readme_f1 = S.ref('readme:F1:82-89', 'what differs between boot R3 and boot F1: the firmware that turns '
                      'the L3 on, the OCM module file, the benchmark build, the emulator boards')
    readme_dram = S.ref('readme:F1:247', 'every delay control of the memory model is zero')
    dram_note = ('The DRAM model is an emulator memory with zero configured delay, not silicon timing '
                 "(operator's README) %s." % readme_dram)
    plan = S.ref('doc:plan:280-331', 'the prepared command set for the read stream: the counters of prefetch '
                 'accesses that target the L3 (event 0x8156) and of demand reads that first hit a line that a '
                 'prefetcher placed in the L3 (event 0x81E6), the read-queue occupancy of the home nodes, the '
                 'read sweep with the prefetchers off, and the stride-prefetcher control bit 6 of '
                 '<code>IMP_CPUECTLR_EL1</code>')
    note_ = S.ref('doc:seqread')

    # ------------------------------------------------------------------ 8.1
    body = S.h3('open-l3', 'The read stream and the L3 state')
    r32 = o['read-33554432']
    body += S.p(
        f"One core reads a 32 MiB buffer at {n3(r32['f1'])} GB/s on boot F1. "
        f"The same command reads {n3(r32['r3'])} GB/s on {D.boot_first_use['R3']}. "
        f"The ratio is {n3(r32['ratio'])}. "
        f"The buffer is {n0(X['x_l3'])} times the size of the L3, so the L3 cannot hold it. "
        f"No file on disk shows the cause "
        + S.ref('file:F1:%s' % r32['file']) + S.ref('file:R3:%s' % r32['r3_file']) + ". " + dram_note)

    cite_p1 = (
        _cite(S, [_row(o[i]) for i in ('read-49152', 'read-98304', 'read-262144', 'read-2097152',
                                       'read-33554432', 'write-32m')],
              'one-core read at 48 KiB, 96 KiB, 256 KiB, 2 MiB and 32 MiB, and the 32 MiB write')
        + _cite(S, [_row(o[i], 'r3_') for i in ('read-49152', 'read-98304', 'read-262144', 'read-2097152',
                                                'read-33554432', 'write-32m')], 'the same rows on boot R3')
        + _cite(S, [_row(o['chain-32m'])], 'the 32 MiB chain')
        + _cite(S, [_row(o['chain-32m'], 'r3_')], 'the 32 MiB chain on boot R3')
        + _cite(S, [_row(o[i]) for i in ('four-readers-2097152', 'four-readers-16777216')],
                'four readers at 2 MiB and 16 MiB')
        + _cite(S, [_row(o[i], 'r3_') for i in ('four-readers-2097152', 'four-readers-16777216')],
                'four readers at 2 MiB and 16 MiB on boot R3')
        + _cite(S, [_row(o[i]) for i in ('eight-readers-2097152', 'eight-readers-16777216')],
                'eight readers at 2 MiB and 16 MiB')
        + _cite(S, [_row(o[i], 'r3_') for i in ('eight-readers-2097152', 'eight-readers-16777216')],
                'eight readers at 2 MiB and 16 MiB on boot R3')
        + _cite(S, [_row(o['ocm-read-all5'])], 'the OCM read of all five regions')
        + _cite(S, [_row(o['ocm-read-all5'], 'r3_')], 'the OCM read of all five regions on boot R3')
        + _cite(S, [_row(o['ocm-read-4core'])], 'the OCM read of four cores')
        + _cite(S, [_row(o['ocm-read-4core'], 'r3_')], 'the OCM read of four cores on boot R3'))

    body += S.fig(
        _fig_p1(D, V, S),
        'Boot F1 against boot R3 on the same commands. Each row has one dot per boot. '
        'The bold number is boot F1 over boot R3.',
        'Only the read streams differ. The write and the chain read the same on both boots.',
        id_='fig-P1',
        note=(f"The two boots also differ in the benchmark build, the OCM module file and the emulator boards "
              f"(operator's README) {readme_f1}. " + cite_p1))

    def tp1(id_):
        r = o[id_]
        d = 0 if r['unit'].startswith('requests') else 3
        return [r['label'], r['unit'], V.num(r['f1'], d), V.num(r['r3'], d), n3(r['ratio'])]

    mesh = o['mesh-read-2m']
    body += S.table(
        ['Row', 'Unit', 'Boot F1', 'Boot R3', 'F1 over R3'],
        ['Read streams'] + [tp1(i) for i in (
            'read-49152', 'read-98304', 'read-262144', 'read-2097152', 'read-33554432',
            'four-readers-2097152', 'four-readers-16777216', 'eight-readers-2097152',
            'eight-readers-16777216', 'ocm-read-all5', 'ocm-read-4core')]
        + ['Rows that are not a read stream'] + [tp1(i) for i in ('write-32m', 'chain-32m', 'mesh-read-2m')],
        caption='The rows of %s. Boot F1: L3 on. Boot R3: the L3 holds no data. Prefetchers on for both.'
                % S.figref('fig-P1'),
        note=("Best rows. The L3 register is read on CPU 2's cluster only (operator's README). The request count "
              'covers the whole command, not the timed passes '
              + _cite(S, [(mesh['boot'], mesh['file'], '%d-%d' % (mesh['line'], mesh['line'] + 5))],
                      'the 2 MiB read command under the mesh counters')
              + _cite(S, [(mesh['r3_boot'], mesh['r3_file'], '%d-%d' % (mesh['r3_line'], mesh['r3_line'] + 5))],
                      'the 2 MiB read command under the mesh counters on boot R3') + '.'),
        id_='tab-TP1')

    rd = os_['read']
    body += S.bullets([
        f"The 48 KiB and 96 KiB reads fit the 128 KiB L2 on both boots. They still differ {n3(rd[0])} and "
        f"{n3(rd[1])} times. So the gain does not need a line from outside the cluster.",
        f"The home nodes receive {n0(mesh['f1'])} requests during the 2 MiB read command on boot F1 and "
        f"{n0(mesh['r3'])} on boot R3 ({n3(mesh['ratio'])} times). So the L3 does not take this read off the mesh.",
        f"The one-region OCM reads gain {n3(os_['ocm_regions'][0])} to {n3(os_['ocm_regions'][1])} times "
        + S.ref('group:F1:bandwidth-ocm-region*.csv') + S.ref('group:R3:bandwidth-ocm-region*.csv') + '.',
    ])

    e32, eseq = ec['read-33554432'], ec['seq-8m']
    body += S.p(
        f"{D.boot_first_use['E'][0].upper() + D.boot_first_use['E'][1:]} and {D.boot_first_use['C']} run one "
        f"benchmark build. The L3 state is their one firmware difference. "
        f"Their plain 32 MiB read counts the same L1 refills and L2 refills per 64 bytes ({S.tabref('tab-TP2')}). "
        f"The rate differs {n3(e32['l3_gain'])} times. "
        f"Their 8 MiB chain in address order differs {n3(eseq['l3_gain'])} times ({S.xref('lat-order')}).")

    def tp2(r, side, per):
        ctr = r[side + '_ctr']
        b = 'E' if side == 'e' else 'C'
        cond = '%s, L3 %s' % (D.boot_name[b], D.boot[b]['l3'])
        cyc = ctr.get('cyc_line', ctr.get('cycles'))
        return [r['label'], cond, '%s %s' % (n3(r[side]), r['unit']), n2(cyc) + ' ' + per,
                V.num(ctr['l1'], 4), V.num(ctr['l1pf'], 4), V.num(ctr['l2'], 4), V.num(ctr['a2'], 4)]

    body += S.table(
        ['Row', 'Boot', 'Best', 'Cycles counted', 'L1 refills', 'L1 prefetch refills', 'L2 refills',
         'L3 read refills'],
        [tp2(e32, 'e', 'per 64 bytes'), tp2(e32, 'c', 'per 64 bytes'),
         tp2(eseq, 'e', 'per load'), tp2(eseq, 'c', 'per load')],
        caption='Boots E and C (prefetchers on for both): the same fills, another rate.',
        note=('Counters of the best rep, per 64 bytes transferred (read) or per load (chain). The cycles of a '
              'read row are effective cycles per 64 bytes transferred: loop throughput. A refill count is an '
              'aggregate. It does not give the history of each line, and it includes prefetch fills. On boot C '
              'every line comes from outside the cluster and the L3 read refills stay near 0, so that event '
              'does not count the prefetch fills of this stream '
              + _cite(S, [_row(e32)], 'plain read, 32 MiB')
              + _cite(S, [_row(e32, 'c_')], 'plain read, 32 MiB')
              + _cite(S, [_row(eseq)], 'the 8 MiB chain in address order')
              + _cite(S, [_row(eseq, 'c_')], 'the 8 MiB chain in address order') + '. ' + dram_note),
        align='llrrrrrr', id_='tab-TP2')

    body += S.p('No counter on disk shows where a line of the stream waits. Four causes fit every row.')
    body += S.hyp(
        f"With the L3 on, the prefetchers place lines of the stream in the L3 ahead of the core, many lines at "
        f"a time (project note) {note_}.",
        f"The count of prefetch accesses that target the L3, and of demand reads that first hit a line that a "
        f"prefetcher placed in the L3, on the 2 MiB and 32 MiB reads in both L3 states. A prepared command set "
        f"has both (<code>follow-up-run-plan.md</code>) {plan}.")
    body += S.hyp(
        'With the L3 on, the cluster issues or times the prefetch requests in another way, and the lines still '
        'arrive in the L1 and the L2 directly.',
        f"A boot with the L3 on and the stride prefetcher set to fill the L2 in place of the L3 {plan}, or a "
        f"trace of the requests of the timed stream.")
    body += S.hyp(
        'With the L3 on, more reads are open at the home nodes at one time.',
        f"The mean read-queue occupancy of the five home nodes around the same read, in both L3 states {plan}. "
        f"It is a mean over the whole command.")
    body += S.hyp(
        'The gain needs the prefetchers.',
        f"The one-core read sweep with the prefetchers off, in both L3 states. No boot has core rows with "
        f"the L3 on and the prefetchers off ({S.figref('fig-P2')}).")
    body += S.insufficient(
        'Which of the four causes acts. No results folder holds the rows of the prepared command set. '
        'Its counters can show that prefetch fills of the L3 take part, not how much of the gain they carry.')

    # ------------------------------------------------------------------ 8.2
    body += S.h3('open-items', 'Other open items')
    body += S.p(
        f"{S.tabref('tab-TP3')} lists more observations that the files do not explain. "
        f"Rows without a boot name are boot F1 rows.")

    mc = lambda g, k, s: D.mc(g, k, s)
    r8_16, r8_2 = mc('all eight cores', 'read', 16 * MIB), mc('all eight cores', 'read', 2 * MIB)
    r4_2 = mc('one core per cluster', 'read', 2 * MIB)
    w8_16 = mc('all eight cores', 'write', 16 * MIB)
    pair48 = mc('pair', 'read', 48 * KIB)
    w = X['w']
    ws = D.mc_writers_summary
    two = ws['per_cluster_two_writers']
    cs = D.ocm_cells_summary
    ub = cs['unacc_by_cpu']
    fits = {(f['boot'], f['form'], f['kernel']): f for f in D.bw_fit + D.bw_fit_extra}
    l4 = D.bw_l1_summary['looped_read_4k']
    l4e = [x for x in D.l1_rows('E') if x['form'] == 'looped' and x['kernel'] == 'read' and x['size'] == 4 * KIB][0]
    l4c = [x for x in D.l1_rows('C') if x['form'] == 'looped' and x['kernel'] == 'read' and x['size'] == 4 * KIB][0]
    once, fl = X['once_8m'], X['flushed']
    r384 = D.sweep_row('F1', 384 * KIB)
    rep = {r['id']: r for r in D.repeat}
    r768, r4m = rep['chain-786432-once'], rep['chain-4194304-once']
    rs = D.repeat_summary
    a5 = D.ocm_all5_summary
    m2 = a5['minus_2m_chain']
    all5rows = [r for r in D.ocm_all5 if r['shape'] == 'every line']
    c2m = D.lat_cluster['chain2m']
    ob = D.ocm_bw_summary
    obw = {r['name']: r for r in D.ocm_bw}
    fitB = D.ocm_fit['B']
    avc = D.ocm_fit['all5_vs_cells']
    ms = D.mesh_summary
    rd2m = D.mesh_row('dram-read-2M-cpu2')
    fc = X['four_core']

    items = []

    # 1 read limit
    items.append([
        'Read limit: per cluster or chip-wide',
        f"Eight readers, two per cluster, read {n3(r8_16['best'])} GB/s at 16 MiB and {n3(r8_2['best'])} GB/s "
        f"at 2 MiB. At 2 MiB each reader keeps {n1(100 * r8_2['efficiency'])} % of the one-core rate. Four "
        f"readers on four clusters keep {n1(100 * r4_2['efficiency'])} % "
        + _cite(S, [_row(r8_16), _row(r8_2)], 'eight readers at 2 MiB and 16 MiB')
        + _cite(S, [_row(r4_2)], 'four readers at 2 MiB and 16 MiB') + '.',
        'Every row with two readers in one cluster at a DRAM-backed footprint has all eight cores running.',
        f"Hypothesis: a limit of about {n1(r8_16['per_cluster'])} GB/s est. per cluster. "
        f"Hypothesis: a chip-wide limit near {n0(r8_2['best'])} GB/s.",
        'Two readers on CPUs 2 and 3 against CPUs 2 and 4 at 16 MiB.'])

    # 2 two cores of one cluster
    items.append([
        'What two cores of one cluster share',
        f"Two writers in one cluster reach {n3(w['2-3']['ratio_control'])} times the rate of two writers in two "
        f"clusters (16 MiB). With two writers a cluster writes {n1(two['one cluster busy'])} GB/s (one cluster "
        f"busy), {n1(two['two clusters busy'][0])} and {n1(two['two clusters busy'][1])} GB/s (two busy), "
        f"{n1(two['four clusters busy'])} GB/s (four busy) ({S.xref('mc-writers')}). The pair read at 48 KiB "
        f"scales {n3(pair48['scaling'])} times ({S.xref('mc-pair')}) "
        + _cite(S, [_row(w['2-3'])], 'two writers on CPUs 2 and 3')
        + _cite(S, [_row(w['2-4'])], 'two writers on CPUs 2 and 4')
        + _cite(S, [_row(w['2-3-4-5'])], 'four writers on CPUs 2, 3, 4, 5')
        + _cite(S, [_row(w['2-3-8-9'])], 'four writers on CPUs 2, 3, 8, 9')
        + _cite(S, [_row(w['2-4-6-8'])], 'four writers on CPUs 2, 4, 6, 8')
        + _cite(S, [_row(w8_16)], 'eight writers at 16 MiB')
        + _cite(S, [_row(pair48)], 'pair read at 48 KiB') + '.',
        f"No counter names the shared resource. Each home node receives {n0(X['w_one_cluster_nodes'][0])} to "
        f"{n0(X['w_one_cluster_nodes'][1])} requests with one cluster busy, and "
        f"{n0(X['w_two_cluster_nodes'][0])} to {n0(X['w_two_cluster_nodes'][1])} with two "
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % w['2-3']['mesh_node_lines'])],
                'requests received per node, two writers on CPUs 2 and 3')
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % w['2-4']['mesh_node_lines'])],
                'requests received per node, two writers on CPUs 2 and 4') + '.',
        "Hypothesis: one shared path per cluster, such as its mesh port.",
        'The writer placement rows and the pair rows with core counters.'])

    # 3 L3 state of the other clusters
    items.append([
        'L3 state of the clusters of CPUs 4 to 9',
        f"The L3 register is read on CPU 2's cluster only (operator's README) "
        + S.ref('readme:F1:74', 'the read of the L3 status register covers the cluster of CPU 2 only')
        + f". Indirect: the L2 refills not accounted for reach {n3(ub[4])}, {n3(ub[6])} and {n3(ub[8])} per "
        f"load on the OCM passes of CPUs 4, 6 and 8 ({n3(ub[2])} on CPU 2). On boots B, C and D (the L3 holds "
        f"no data) the same quantity is at most {V.num(cs['unacc_max_bcd'], 4)} "
        + S.ref('group:F1:latency-ocm-*.csv') + S.ref('group:B:latency-ocm-*.csv')
        + S.ref('group:C:latency-ocm-*.csv') + S.ref('group:D:latency-ocm-*.csv') + '.',
        'A difference of four counters is not a register read.',
        'Hypothesis: all four clusters run with the L3 on.',
        'A register read on one CPU of each cluster, or a chain of 192 to 384 KiB with the hit set from CPUs '
        '4, 6 and 8.'])

    # 4 L1 read rows
    fe_l, fe_s = fits[('E', 'looped', 'read')], fits[('E', 'single-call', 'read')]
    items.append([
        'The L1 read rows fit no line',
        f"On boot E (L3 on) the line through the read rows of 4, 8, 16 and 24 KiB leaves a residual of "
        f"{n2(fe_l['max_res_pct'])} % (looped form) and {n2(fe_s['max_res_pct'])} % (single-call form) of the "
        f"smallest pass time. Both fits are void. The 4 KiB looped read reads {n3(l4['E'])} GB/s on boot E and "
        f"{n3(l4['C'])} GB/s on boot C (the L3 holds no data). The reps spread {n2(l4e['spread_pct'])} % and "
        f"{n2(l4c['spread_pct'])} % "
        + _cite(S, [('E', fe_l['file'], fe_l['lines'])], 'looped read rows of 4, 8, 16 and 24 KiB')
        + _cite(S, [('E', fe_s['file'], fe_s['lines'])], 'single-call read rows of 4, 8, 16 and 24 KiB')
        + _cite(S, [_row(l4c)], 'looped read, 4 KiB') + '.',
        'A 4 KiB buffer stays in the L1, and the L3 state is the one firmware difference.',
        'Insufficient data: the shape of the read time per pass.',
        'Read rows at more sizes between 4 and 24 KiB, and the L1 forms on a second boot with the L3 on.'])

    # 5 walked once below the DRAM-model row
    items.append([
        'A chain walked once reads below the DRAM-model row',
        f"The 8 MiB chain walked once reads {n3(once['best'])} ns per load, against {n3(fl['best'])} ns with "
        f"every line flushed first ({S.xref('lat-dram')}). The L3 read refills are {n3(once['a2'])} and "
        f"{n3(fl['a2'])} per load " + _cite(S, [_row(once)], 'the 8 MiB chain walked once')
        + _cite(S, [_row(fl)], 'the 8 MiB chain with every line flushed first') + '.',
        'The refill count is an aggregate count. It does not say whether the home node held the line or '
        'fetched it from the memory model.',
        'Hypothesis: the chain walked once still has part of its lines in the SLC from the chain build.',
        'The SLC-miss count of the home nodes around both commands (exploratory event).'])

    # 6 capacity edges
    items.append([
        'Rows at a capacity edge repeat poorly',
        f"The 384 KiB chain reads {n3(r384['reps'][0])} ns in its first rep and {n3(r384['reps'][1])} and "
        f"{n3(r384['reps'][2])} ns after it. The 768 KiB chain reads {n3(r768['f1'])} ns on boot F1 and "
        f"{n3(r768['e'])} ns on boot E (the same firmware state). The 4 MiB chain reads {n3(r4m['f1'])} and "
        f"{n3(r4m['e'])} ns ({S.xref('glance-repeat')}) "
        + _cite(S, [('F1', r384['file'], [x['line'] for x in r384['rep_rows']])], 'the three reps of the 384 KiB chain')
        + _cite(S, [_row(r768), _row(r4m)], 'the 768 KiB and 4 MiB chains')
        + _cite(S, [_row(r768, 'e_'), _row(r4m, 'e_')], 'the 768 KiB and 4 MiB chains') + '.',
        "Each boot gives one sample. Each command is its own process with its own physical pages (operator's "
        "README) " + readme_f1 + '.',
        'Hypothesis: the placement of the buffer over the cache sets. Hypothesis: the first rep runs before '
        'the L3 holds the whole chain.',
        'The same row in several processes of one boot, with more reps.'])

    # 7 OCM row above the 2 MiB chain
    items.append([
        'The OCM row reads above the 2 MiB chain',
        f"The OCM row (every line, all five regions) reads {n3(m2[2])}, {n3(m2[4])}, {n3(m2[6])} and "
        f"{n3(m2[8])} ns above the 2 MiB chain from CPUs 2, 4, 6 and 8. Each is the measured difference "
        f"between two loops "
        + ''.join(_cite(S, [_row(r)], 'the OCM row, every line, all five regions') for r in all5rows)
        + ''.join(_cite(S, [_row(r)], 'the 2 MiB chain') for r in c2m) + '.',
        "The same five home nodes serve both chains. The L3 register is read on CPU 2's cluster only.",
        'Hypothesis: the OCM path inside a home node costs more than an SLC hit.',
        'Insufficient data: a reading of the two paths in the RTL or in a waveform.'])

    # 8 OCM bandwidth against DRAM-backed
    oa, ow = obw['all five regions'], obw['all five regions, write']
    items.append([
        'OCM bandwidth against the DRAM-backed rate',
        f"One core reads the five OCM regions at {n2(ob['read_ratio'])} times and writes them at "
        f"{n2(ob['write_ratio'])} times the rate of the DRAM-backed 2 MiB rows ({S.xref('ocm-bw')}) "
        + _cite(S, [_row(oa)], 'OCM read, all five regions') + _cite(S, [_row(ow)], 'OCM write, all five regions')
        + '.',
        'Not like for like: the OCM rows flush first. No boot has a DRAM-backed row with a flush.',
        'Insufficient data: how much of each difference is the row form.',
        'An OCM write row without the flush, or a DRAM-backed read and write row with it.'])

    # 9 software prefetch
    items.append([
        'Software prefetch slows the read with the L3 on',
        f"On boot E a prefetch hint 4, 8 or 16 lines ahead lowers the read rate by {n1(-X['pf_e_change'][0])} to "
        f"{n1(-X['pf_e_change'][1])} % against the plain read. On boot B (prefetchers off, the L3 holds no "
        f"data) the same hints raise it {n2(X['pf_b_ratio'][0])} to {n2(X['pf_b_ratio'][1])} times "
        f"({S.xref('bw-variants')}) "
        + _cite(S, [_row(r) for r in X['pf_e_rows']], 'the three software-prefetch kernels at 2 MiB and 32 MiB')
        + _cite(S, [_row(r) for r in X['pf_b_rows']], 'the three software-prefetch kernels at 2 MiB and 32 MiB')
        + '.',
        'No counter separates the fills that the hint requests from the fills of the prefetchers.',
        'Hypothesis: the hint takes over part of the stream of the prefetchers.',
        'The counters of the prefetch target (%s) on these kernels.' % S.xref('open-l3')])

    # 10 uneven node counts
    items.append([
        'Uneven requests per home node on OCM commands',
        f"The OCM chain over all five regions has 4,096 lines in each region. The largest node count is "
        f"{n3(X['all5_span'][0])} to {n3(X['all5_span'][1])} times the smallest, over the four CPUs. On the "
        f"four-core OCM read, node {X['four_low_node']} receives {n0(X['four_low_count'])} requests, "
        f"{n0(X['four_below_pct'][0])} to {n0(X['four_below_pct'][1])} % below the other three busy nodes "
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % r['node_lines']) for r in X['all5_mesh']],
                'requests received per node, the OCM chain over all five regions, CPUs 2, 4, 6 and 8')
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % fc['node_lines'])],
                'requests received per node, the four-core OCM read') + '.',
        'The counts cover the whole command, not the timed passes.',
        'Insufficient data: which part of a command sends the extra requests.',
        'A count per node of the timed passes alone.'])

    # 11 X step against Y step
    items.append([
        'An X step costs more than a Y step',
        f"The fit over the 20 per-region rows of boot B (prefetchers off, the L3 holds no data) gives "
        f"{n3(fitB['bx'])} ns per X step and {n3(fitB['cy'])} ns per Y step ({S.xref('ocm-region')}) "
        + S.ref('group:B:latency-ocm-region*-route-cpu*.csv') + '.',
        'No counter splits the round trip by direction or by link.',
        'Hypothesis: a link in X has more register stages than a link in Y.',
        'Insufficient data: the register stages of the mesh links in the RTL.'])

    # 12 all-five above the per-region mean
    items.append([
        'The all-five chain reads above the mean of its regions',
        f"On boot B the OCM chain over all five regions reads {n2(avc[2]['diff'])} ns (CPU 2) and "
        f"{n2(avc[8]['diff'])} ns (CPU 8) above the mean of that CPU's five per-region rows "
        f"({S.xref('ocm-region')}). Each is the measured difference between two loops "
        + _cite(S, [_row(avc[2])], 'the OCM chain over all five regions')
        + _cite(S, [_row(avc[8])], 'the OCM chain over all five regions')
        + S.ref('group:B:latency-ocm-region*-route-cpu*.csv') + '.',
        'Both use every line of the same regions. The all-five chain has five times the lines.',
        'Insufficient data: how the difference grows with the number of regions.',
        'Chains over every line of two, three and four regions.'])

    # 13 2 MiB read sends requests on to memory
    items.append([
        'The 2 MiB read sends requests on to memory',
        f"The 2 MiB read command sends {n2(ms['mc_est_read'])} requests on to memory per line and pass of the "
        f"whole command, net of the control, est. ({S.xref('mesh-dram')}). A 2 MiB buffer is under the "
        f"3.75 MiB est. that the SLC has for DRAM lines (operator's README) "
        + S.ref('readme:R3:34', 'the SLC size that is left for DRAM lines')
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % (rd2m['line'], rd2m['last_line']))],
                'the 2 MiB read command under the mesh counters') + '.',
        'The event is exploratory. The count covers the buffer fill and every pass.',
        'Hypothesis: the SLC does not keep the lines that the read stream passes to the cluster.',
        'Request-type events of the home nodes around a read with more passes.'])

    body += S.table(
        ['#', 'Item', 'Observation', 'Why it is not explained', 'Hypothesis or unknown',
         'Measurement that would settle it'],
        [[str(i + 1)] + it for i, it in enumerate(items)],
        caption='Open items other than the read stream.',
        note=("Rows of 2 MiB and more reach the DRAM model. " + dram_note
              + " The L3 register is read on CPU 2's cluster only (operator's README)."),
        align='llllll', id_='tab-TP3')

    # ------------------------------------------------------------------ 8.3
    body += S.h3('open-notmeasured', 'Not measured')
    nm = D.not_measured
    n_fam = len(nm['rows'])
    n_none = sum(1 for r in nm['rows'] if r['cells'][1] is None)
    f2 = S.ref('folder-012-core-files',
               'Results folder <code>results/membench-jibin-012</code> (L3 on, prefetchers off): its files other '
               'than the CME files are %s. It holds no core row.' % ', '.join(_c(x) for x in nm['f2_non_cme_files']))
    body += S.p(
        f"{S.figref('fig-P2')} shows which boot measures each row family in each firmware state. "
        f"{S.tabref('tab-TP4')} lists what no boot measures.")
    body += S.fig(
        _fig_p2(D, V, S),
        f"The {n_fam} row families of the page by firmware state. A cell names the boots that hold the rows.",
        f"No core row exists with the L3 on and the prefetchers off ({n_none} of {n_fam} families).",
        id_='fig-P2',
        note=(f"A family is counted for a boot when the boot has its result file or its mesh event. The one "
              f"boot in the state \"L3 on, prefetchers off\" ran CME commands only {f2}. Boot conditions: "
              f"{S.xref('setup-boots')}."))

    spm = D.platform['spm_missing']
    flags = D.platform['log_flags']
    body += S.table(
        ['Area', 'State', 'What would measure it'],
        [['Core rows with the L3 on and the prefetchers off',
          'Not measured. The one boot in that state holds CME rows only %s.' % f2,
          "Boot F1's command set on that firmware state."],
         ["Core counters on boot F1's bandwidth rows, one core and several cores",
          'Not measured. No bandwidth command of boot F1 counts core events '
          + S.ref('file:F1:bandwidth-dram-1core.csv') + '.',
          'The same commands with the counters on.'],
         ['The hit set, the chain in address order, the L1 forms and the read variants on boot F1',
          'Not measured on boot F1. Boot E has them in the same firmware state '
          + S.ref('src:run_followup.sh') + '.',
          "Boot E's command set on boot F1's firmware."],
         ['Prefetch target, reads open at one time, read-queue occupancy of the home nodes',
          'Not measured. A prepared command set exists (<code>follow-up-run-plan.md</code>) %s.' % plan,
          'That command set on four boots, one per firmware state.'],
         ['One-core read at 16 MiB',
          'Not measured. The multi-core rows use 16 MiB, and the one-core sweep has 2 MiB and 32 MiB.',
          'One row.'],
         ['Store latency, and write rows that wait for the lines to reach the memory model',
          'Not measured for the core.', 'A write row with a completion barrier after each pass.'],
         ['Silicon DRAM timing',
          "Not measurable on this emulator image. The memory model has zero configured delay (operator's "
          "README) %s." % readme_dram,
          'Silicon, or a memory model with a timing profile.'],
         ['SPM (the scratchpad memory)',
          'Not measured. The image has no SPM device, and the log of boot F1 reads %s %s.' % (
              _c('spm=%d' % flags['value']['spm']),
              S.ref('file:F1:sysinfo.txt:%d' % spm['line'], 'the SPM device file does not exist')
              + S.ref('file:F1:log.txt:%d' % flags['line'], 'the flags of the script, with spm=0')),
          'An image with the SPM driver.']],
        caption='What no boot measures. %s holds two more: the L3 state of the clusters of CPUs 4 to 9, and '
                'two readers in one cluster.' % S.tabref('tab-TP3'), align='lll', id_='tab-TP4')
    return body
