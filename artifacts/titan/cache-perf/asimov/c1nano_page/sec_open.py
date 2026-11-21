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
    # both commands with two writers in two clusters (CPUs 2 and 4, CPUs 2 and 8)
    two_cl = w['2-4']['node_counts'] + w['2-8']['node_counts']
    X['w_two_cluster_nodes'] = (min(two_cl), max(two_cl))
    # software prefetch against the plain read: boot E change in percent, boot B ratio, boot E counters
    pf = ('read-pf4', 'read-pf8', 'read-pf16')
    # the 32 MiB rows only, as in the section on the read variants (boot B's 2 MiB rows spread up to 10 %)
    e = [r for r in D.bw_var if r['boot'] == 'E' and r['kernel'] in pf and r['size'] == 32 * MIB]
    b = [r for r in D.bw_var if r['boot'] == 'B' and r['kernel'] in pf and r['size'] == 32 * MIB]
    X['pf_e_rows'], X['pf_b_rows'] = e, b
    X['pf_e_change'] = (max(r['change_pct'] for r in e), min(r['change_pct'] for r in e))
    X['pf_b_ratio'] = (min(r['ratio_plain'] for r in b), max(r['ratio_plain'] for r in b))
    X['pf_e_l1pf'] = (min(r['l1pf'] for r in e), max(r['l1pf'] for r in e))
    c = [r for r in D.bw_var if r['boot'] == 'C' and r['kernel'] in pf and r['size'] == 32 * MIB]
    X['pf_c_rows'] = c
    X['pf_c_change'] = (min(r['change_pct'] for r in c), max(r['change_pct'] for r in c))
    # L2 refills not accounted for on the OCM passes of CPUs 2 and 8, boots with the L3 holding no data
    ubb = D.ocm_cells_summary['unacc_by_boot']
    X['unacc_c_28'] = max(ubb['C'][2], ubb['C'][8])
    X['unacc_bd_28'] = max(ubb[b][cpu] for b in ('B', 'D') for cpu in (2, 8))
    # one-line-per-page OCM files of CPUs 4 and 6 on boots B, C, D (the route files use every line)
    X['n_page_files_46_bcd'] = sum(
        1 for b in ('B', 'C', 'D') for n in D.files[b]['latency']
        if n.startswith('latency-ocm') and 'route' not in n and ('cpu4' in n or 'cpu6' in n))
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
        dict(header='A row that is not a read stream, GB/s'),
        row('write-32m', 'one-core write, 32 MiB'),
    ]   # the 32 MiB chain is in ns per load: it is given as text under the figure, not on the GB/s axis
    return V.dot_rows(
        rows,
        [dict(name='boot F1 (L3 on, prefetchers on)', color='f1'),
         dict(name='boot R3 (the L3 holds no data, prefetchers on)', color='c')],
        unit='', fmt=lambda v: V.num(v, 1), connect=True, labels='all',
        xlabel='GB/s', xrange=(0, None), label_w=230)


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
                      'the L3 on, the Linux driver file for the OCM, the benchmark build, the hardware boards of the emulator')
    readme_dram = S.ref('readme:F1:247', 'every delay control of the memory model is zero')
    readme_f1_code = S.ref('readme:F1:84', 'the machine code of the builds of boots F1, E and R3 compared')
    readme_f1_read = S.ref('readme:F1:144', 'the one-core read rows carry no core counters, the mesh counters '
                           'cover the whole command, and no file shows why the reads are faster with the L3 on')
    cec = D.cmd_cmp[('E', 'C')]
    if not (cec['same'] and cec['same_commit']):
        raise ValueError('sec_open: boots E and C do not run one build and one command list')
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
        f"Of the rows shown, only the read streams differ. The one-core 32 MiB write reads the same on both "
        f"boots. So does the 32 MiB chain, which is not drawn: {n3(o['chain-32m']['f1'])} ns per load on boot F1 "
        f"against {n3(o['chain-32m']['r3'])} ns on boot R3.",
        id_='fig-P1',
        note=(f"Rows of both boots {cite_p1}. The L3 state is the firmware change between the two boots. They "
              f"also differ in the benchmark build, the Linux driver file for the OCM and the hardware boards of "
              f"the emulator, and a test program runs before the script on boot F1 (operator's README) "
              f"{readme_f1}. The read, write and copy loops of the bandwidth test are the same bytes in both "
              f"builds (operator's README) {readme_f1_code}."))

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
        caption='The rows of %s and five more rows of the same boots: four and eight readers at 16 MiB, the '
                'OCM read with four cores, the 32 MiB chain, and the request count of the 2 MiB read command. '
                'Boot F1: L3 on. Boot R3: the L3 holds no data. Prefetchers on for both.'
                % S.figref('fig-P1'),
        note=("Best rows. On boot F1 the L3 register is read on CPU 2's cluster only. Boot R3 has no register "
              "reading, and its L3 state is taken from the operator's README. The request count "
              'covers the whole command, not the timed passes '
              + _cite(S, [(mesh['boot'], mesh['file'], '%d-%d' % (mesh['line'] + 1, mesh['line'] + 5))],
                      'the 2 MiB read command under the mesh counters')
              + _cite(S, [(mesh['r3_boot'], mesh['r3_file'], '%d-%d' % (mesh['r3_line'] + 1, mesh['r3_line'] + 5))],
                      'the 2 MiB read command under the mesh counters on boot R3') + '.'),
        id_='tab-TP1')

    rd = os_['read']
    body += S.bullets([
        f"The 48 KiB and 96 KiB buffers are smaller than the 128 KiB L2 on both boots. Their reads still differ "
        f"{n3(rd[0])} and {n3(rd[1])} times. These rows have no core counters (operator's README) "
        f"{readme_f1_read}. Each rep runs one untimed pass before the timed passes "
        f"{S.ref('src:bandwidth.c:398-449', 'how a rep is timed')}, so the lines can be in the L2 when the "
        f"timed passes start. No file measures where the timed passes get their lines, or how many prefetch "
        f"requests leave the cluster.",
        f"The home nodes receive {n0(mesh['f1'])} requests during the 2 MiB read command on boot F1 and "
        f"{n0(mesh['r3'])} on boot R3 ({n3(mesh['ratio'])} times). So the read command sends about the same number of requests to the home "
        f"nodes in both L3 states.",
        f"The one-region OCM reads gain {n3(os_['ocm_regions'][0])} to {n3(os_['ocm_regions'][1])} times "
        + S.ref('group:F1:bandwidth-ocm-region*.csv') + S.ref('group:R3:bandwidth-ocm-region*.csv') + '.',
    ])

    e32, eseq = ec['read-33554432'], ec['seq-8m']
    body += S.p(
        f"{D.boot_first_use['E'][0].upper() + D.boot_first_use['E'][1:]} and {D.boot_first_use['C']} run one "
        f"benchmark build and the same {cec['n_a']} commands in the same order. The L3 state is their one "
        f"firmware difference. The OCM mapping also differs. That mapping does not act on a DRAM-backed "
        f"buffer (operator's README) "
        f"{S.ref('readme:E:8', 'boot E runs the program build, the OCM driver file and the commands of boot C. Only the firmware that turns the L3 on is new, and the OCM is mapped in 4 KiB entries')} "
        f"{S.ref('readme:C:82-83', 'the contiguous hint does not reach a DRAM-backed buffer')}. "
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
              'aggregate. It does not give the history of each line, and it includes prefetch fills. The L3 '
              'read refills leave out the fills that the prefetchers request (%s) ' % S.xref('bw-variants')
              + _cite(S, [_row(e32)], 'plain read, 32 MiB')
              + _cite(S, [_row(e32, 'c_')], 'plain read, 32 MiB')
              + _cite(S, [_row(eseq)], 'the 8 MiB chain in address order')
              + _cite(S, [_row(eseq, 'c_')], 'the 8 MiB chain in address order') + '. ' + dram_note),
        align='llrrrrrr', id_='tab-TP2')

    body += S.p('No counter on disk shows where a line of the read stream waits. Four hypotheses follow. None is '
                'tested. Hypotheses 1 and 3 act on lines from outside the cluster. They do not cover the 48 KiB '
                'and 96 KiB rows if the timed passes of these rows send almost no request outside the cluster. '
                'That condition is not established. The check is the core counters around the timed 48 KiB and '
                '96 KiB reads in both L3 states, or a trace of the requests of the cluster. The counters of the '
                '2 MiB and 32 MiB rows do not establish it.')
    body += S.hyp(
        f"With the L3 on, the prefetchers place lines of the read stream in the L3 ahead of the core, many lines at "
        f"a time (project note) {note_}.",
        f"Two counts on the 2 MiB and 32 MiB reads, in both L3 states. Count 1: prefetch accesses that target "
        f"the L3. Count 2: demand reads whose line a prefetcher placed in the L3. A prepared command set "
        f"has both (<code>follow-up-run-plan.md</code>) {plan}.")
    body += S.hyp(
        'With the L3 on, the cluster issues or times the prefetch requests in another way, and the lines still '
        'arrive in the L1 and the L2 directly.',
        f"A boot with the L3 on and the stride prefetcher (one of the hardware prefetchers) set to fill the L2 in place of the L3 {plan}, or a "
        f"trace of the requests of the timed read stream.")
    body += S.hyp(
        'With the L3 on, more reads are in progress at the home nodes at one time.',
        f"The mean read-queue occupancy of the five home nodes around the same read, in both L3 states {plan}. "
        f"It is a mean over the whole command.")
    body += S.hyp(
        'The gain needs the prefetchers.',
        f"The one-core read sweep with the prefetchers off, in both L3 states. No boot has core rows with "
        f"the L3 on and the prefetchers off ({S.figref('fig-P2')}).")
    body += S.insufficient(
        'Which of the four hypotheses holds. No results folder holds the rows of the prepared command set. '
        'Its counters can show that prefetch fills of the L3 occur. They cannot show how much of the gain these '
        'fills cause.')

    # ------------------------------------------------------------------ 8.2
    body += S.h3('open-items', 'Other open items')

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
    rpage2, revery2 = rep['ocm-page-cpu2'], rep['ocm-every-cpu2']
    if not all(r['disjoint'] for r in (r768, r4m, rpage2, revery2)):
        raise ValueError('sec_open: a row of open item 6 has rep ranges that overlap on boots F1 and E')
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
    ctl2m = D.mesh_row(rd2m['control'])
    rd2m_bw = D.bw('F1', rd2m['csv'], 'read', 2 * MIB)
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
        'The measured read rows at 2 MiB and 16 MiB per thread use all eight cores when two readers run in each cluster.',
        f"Hypothesis: a limit of about {n1(r8_16['per_cluster'])} GB/s est. per cluster. "
        f"Hypothesis: a chip-wide limit of about {n0(r8_2['best'])} GB/s est.",
        'Two readers on CPUs 2 and 3 against CPUs 2 and 4 at 16 MiB.'])

    # 2 two cores of one cluster
    items.append([
        'What two cores of one cluster share',
        f"Two writers in one cluster reach {n3(w['2-3']['ratio_control'])} times the rate of two writers in two "
        f"clusters (16 MiB). With two writers a cluster writes {n1(two['one cluster busy'])} GB/s (one cluster "
        f"busy), {n1(two['two clusters busy'][0])} and {n1(two['two clusters busy'][1])} GB/s (two busy), "
        f"{n1(two['four clusters busy'])} GB/s (four busy) ({S.xref('mc-writers')}). Two readers on CPUs 2 and 3 "
        f"scale {n3(pair48['scaling'])} times at 48 KiB per thread "
        + _cite(S, [_row(w['2-3'])], 'two writers on CPUs 2 and 3')
        + _cite(S, [_row(w['2-4'])], 'two writers on CPUs 2 and 4')
        + _cite(S, [_row(w['2-3-4-5'])], 'four writers on CPUs 2, 3, 4, 5')
        + _cite(S, [_row(w['2-3-8-9'])], 'four writers on CPUs 2, 3, 8, 9')
        + _cite(S, [_row(w['2-4-6-8'])], 'four writers on CPUs 2, 4, 6, 8')
        + _cite(S, [_row(w8_16)], 'eight writers at 16 MiB')
        + _cite(S, [_row(pair48)], 'pair read at 48 KiB') + '.',
        f"No counter names the shared resource. Each home node receives {n0(X['w_one_cluster_nodes'][0])} to "
        f"{n0(X['w_one_cluster_nodes'][1])} requests with two writers in one cluster (CPUs 2 and 3), and "
        f"{n0(X['w_two_cluster_nodes'][0])} to {n0(X['w_two_cluster_nodes'][1])} with two writers in two "
        f"clusters (CPUs 2 and 4, CPUs 2 and 8) "
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % w['2-3']['mesh_node_lines'])],
                'requests received per node, two writers on CPUs 2 and 3')
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % w['2-4']['mesh_node_lines'])],
                'requests received per node, two writers on CPUs 2 and 4')
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % w['2-8']['mesh_node_lines'])],
                'requests received per node, two writers on CPUs 2 and 8') + '.',
        "Hypothesis: one shared path per cluster, such as its mesh port.",
        'The writer placement rows and the two-reader row with core counters.'])

    # 3 L3 state of the other clusters
    items.append([
        'L3 state of the clusters of CPUs 4 to 9',
        f"On boot F1 the L3 register is read on CPU 2's cluster only (operator's README) "
        + S.ref('readme:F1:74', 'the read of the L3 status register covers the cluster of CPU 2 only')
        + f". Indirect: the L2 refills not accounted for reach {n3(ub[4])}, {n3(ub[6])} and {n3(ub[8])} per "
        f"load on the one-line-per-page rows of one region from CPUs 4, 6 and 8 ({n3(ub[2])} on "
        f"CPU 2). With the L3 holding no data, the OCM reps of CPUs 2 and 8 read at most "
        f"{V.num(X['unacc_c_28'], 4)} on boot C (prefetchers on) and at most {V.num(X['unacc_bd_28'], 4)} on "
        f"boots B and D (prefetchers off, where two of the four counters read zero). These three boots have "
        f"{n0(X['n_page_files_46_bcd'])} files with one line per page from CPUs 4 and 6 "
        + S.ref('group:F1:latency-ocm-*.csv') + S.ref('group:B:latency-ocm-*.csv')
        + S.ref('group:C:latency-ocm-*.csv') + S.ref('group:D:latency-ocm-*.csv') + '.',
        'A difference of four counters is not a register read. Boot C alone differs from boot F1 in the L3 '
        'state without a difference in the prefetchers, and its rows come from CPUs 2 and 8.',
        'Hypothesis: all four clusters run with the L3 on.',
        'A register read on one CPU of each cluster, or a chain of 192 to 384 KiB with the hit set from CPUs '
        '4, 6 and 8.'])

    # 4 L1 read rows
    fe_l, fe_s = fits[('E', 'looped', 'read')], fits[('E', 'single-call', 'read')]
    items.append([
        'The L1 read rows fit no line',
        f"On boot E (L3 on) the line through the read rows of 4, 8, 16 and 24 KiB is void in both forms "
        f"({S.xref('bw-l1forms')}). The 4 KiB looped read reads {n3(l4['E'])} GB/s on boot E and "
        f"{n3(l4['C'])} GB/s on boot C (the L3 holds no data). The reps spread {n2(l4e['spread_pct'])} % and "
        f"{n2(l4c['spread_pct'])} % "
        + _cite(S, [('E', fe_l['file'], fe_l['lines'])], 'looped read rows of 4, 8, 16 and 24 KiB')
        + _cite(S, [('E', fe_s['file'], fe_s['lines'])], 'single-call read rows of 4, 8, 16 and 24 KiB')
        + _cite(S, [_row(l4c)], 'looped read, 4 KiB') + '.',
        'A 4 KiB buffer is smaller than the L1. The two boots run one benchmark build and one command list, '
        'and the L3 state is their one firmware difference. No counter of these rows explains the difference.',
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
        'Rows that differ between boot F1 and boot E',
        f"The 384 KiB chain reads {n3(r384['reps'][0])} ns in its first rep and {n3(r384['reps'][1])} and "
        f"{n3(r384['reps'][2])} ns after it. Four rows differ by more than 2 % between boot F1 and boot "
        f"E (the same firmware state) with rep ranges that do not overlap. The 768 KiB chain reads {n3(r768['f1_lo'])} to "
        f"{n3(r768['f1_hi'])} ns on boot F1 and {n3(r768['e_lo'])} to {n3(r768['e_hi'])} ns on boot E. The 4 MiB "
        f"chain reads {n3(r4m['f1_lo'])} to {n3(r4m['f1_hi'])} ns and {n3(r4m['e_lo'])} to {n3(r4m['e_hi'])} ns. "
        f"The OCM chain of CPU 2 over all five regions with one line per page reads {n3(rpage2['f1_lo'])} to "
        f"{n3(rpage2['f1_hi'])} ns and {n3(rpage2['e_lo'])} to {n3(rpage2['e_hi'])} ns. The same chain with every "
        f"line reads {n3(revery2['f1_lo'])} to {n3(revery2['f1_hi'])} ns and {n3(revery2['e_lo'])} to "
        f"{n3(revery2['e_hi'])} ns ({S.xref('glance-repeat')}) "
        + _cite(S, [('F1', rpage2['file'], rpage2['line']), ('F1', revery2['file'], revery2['line'])],
                'the OCM chains of CPU 2 over all five regions')
        + _cite(S, [('E', rpage2['e_file'], rpage2['e_line']), ('E', revery2['e_file'], revery2['e_line'])],
                'the OCM chains of CPU 2 over all five regions')
        + _cite(S, [('F1', r384['file'], [x['line'] for x in r384['rep_rows']])], 'the three reps of the 384 KiB chain')
        + _cite(S, [_row(r768), _row(r4m)], 'the 768 KiB and 4 MiB chains')
        + _cite(S, [_row(r768, 'e_'), _row(r4m, 'e_')], 'the 768 KiB and 4 MiB chains') + '.',
        "Each boot gives one sample. The two boots run different benchmark builds and command lists. Each "
        "command is its own process. A DRAM-backed buffer is an anonymous allocation, so its physical pages "
        "can differ from process to process. An OCM chain maps the fixed physical regions, so only its "
        "virtual addresses can differ (benchmark source, operator's README) "
        + S.ref('src:common.h:100-161', 'the DRAM allocation and the OCM device mapping') + ' ' + readme_f1 + '.',
        'Hypothesis, DRAM-backed chains only: the placement of the buffer over the cache sets (a set is the '
        'group of places, one per way, that one address can use). Hypothesis: the first rep runs before '
        'the L3 holds the whole chain. No file shows that the physical placement, the virtual mapping or the '
        'translation state explains a difference. Insufficient data: whether a difference belongs to the '
        'boot, to the build or to the process.',
        'The same row in several processes of one boot, with more reps, and a third boot in this firmware '
        'state with the build and the commands of boot F1.'])

    # 7 OCM row above the 2 MiB chain
    items.append([
        'The OCM row reads above the 2 MiB chain',
        f"The OCM row (every line, all five regions) reads {n3(m2[2])}, {n3(m2[4])}, {n3(m2[6])} and "
        f"{n3(m2[8])} ns above the 2 MiB chain from CPUs 2, 4, 6 and 8. Each is the measured difference "
        f"between two loops "
        + ''.join(_cite(S, [_row(r)], 'the OCM row, every line, all five regions') for r in all5rows)
        + ''.join(_cite(S, [_row(r)], 'the 2 MiB chain') for r in c2m) + '.',
        f"The same five home nodes serve both chains. No counter inside the timed interval separates an SLC "
        f"hit from a memory-model fill for the 2 MiB chain. The two chains differ in length "
        f"({n0(all5rows[0]['loads'])} against {n0(c2m[0]['loads'])} loads). On boot B the all-five chain reads "
        f"{n2(min(avc[2]['diff'], avc[8]['diff']))} to {n2(max(avc[2]['diff'], avc[8]['diff']))} ns above the "
        f"mean of the per-region rows (row 12).",
        'Hypothesis: the OCM path inside a home node costs more than the path that serves the 2 MiB chain.',
        'Insufficient data: a reading of the two paths in the design source of the chip or in a signal trace of the emulator.'])

    # 8 OCM bandwidth against DRAM-backed
    oa, ow = obw['all five regions'], obw['all five regions, write']
    items.append([
        'OCM bandwidth against the DRAM-backed rate',
        f"One core reads the five OCM regions at {n2(ob['read_ratio'])} times and writes them at "
        f"{n2(ob['write_ratio'])} times the rate of the DRAM-backed 2 MiB rows ({S.xref('ocm-bw')}) "
        + _cite(S, [_row(oa)], 'OCM read, all five regions') + _cite(S, [_row(ow)], 'OCM write, all five regions')
        + '.',
        'The two rows do not run under the same conditions: the OCM rows flush first. No boot has a '
        'DRAM-backed row with a flush.',
        'Insufficient data: how much of each difference is the row form.',
        'An OCM write row without the flush, or a DRAM-backed read and write row with it.'])

    # 9 software prefetch
    items.append([
        'Software prefetch slows the read with the L3 on',
        f"On boot E a prefetch hint 4, 8 or 16 lines ahead lowers the 32 MiB read rate by "
        f"{n1(-X['pf_e_change'][0])} to {n1(-X['pf_e_change'][1])} % against the plain read. The same hints "
        f"raise it {n2(X['pf_b_ratio'][0])} to {n2(X['pf_b_ratio'][1])} times on boot B (prefetchers off, the "
        f"L3 holds no data) and change it by +{n1(X['pf_c_change'][0])} to +{n1(X['pf_c_change'][1])} % on "
        f"boot C (prefetchers on, the L3 holds no data) ({S.xref('bw-variants')}). So the loss appears only with the L3 on (boot E against boot C) "
        + _cite(S, [_row(r) for r in X['pf_e_rows']], 'the three software-prefetch kernels at 32 MiB')
        + _cite(S, [_row(r) for r in X['pf_c_rows']], 'the three software-prefetch kernels at 32 MiB')
        + _cite(S, [_row(r) for r in X['pf_b_rows']], 'the three software-prefetch kernels at 32 MiB')
        + '.',
        'No counter separates the fills that the hint requests from the fills of the prefetchers.',
        'Hypothesis: with the L3 on, the hint requests lines that the prefetchers would request without it, '
        'and its fills are slower.',
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
        'Hypothesis: a link in X has more register stages (each stage adds one clock cycle) than a link in Y.',
        'Insufficient data: the register stages of the mesh links in the design source of the chip.'])

    # 12 all-five above the per-region mean
    items.append([
        'The all-five chain reads above the mean of its regions',
        f"On boot B the OCM chain over all five regions reads {n2(avc[2]['diff'])} ns (CPU 2) and "
        f"{n2(avc[8]['diff'])} ns (CPU 8) above the mean of that CPU's five per-region rows "
        f"({S.xref('ocm-quote')}). Each is the measured difference between two loops "
        + _cite(S, [_row(avc[2])], 'the OCM chain over all five regions')
        + _cite(S, [_row(avc[8])], 'the OCM chain over all five regions')
        + S.ref('group:B:latency-ocm-region*-route-cpu*.csv') + '.',
        'Both use every line of the same regions. The all-five chain has five times the lines.',
        'Insufficient data: how the difference grows with the number of regions.',
        'Chains over every line of two, three and four regions.'])

    # 13 2 MiB read sends requests on to memory
    items.append([
        'The 2 MiB read sends requests on to memory',
        f"The 2 MiB read command counts {n0(rd2m['mc'])} requests sent on to memory. The control of CPU 2 "
        f"counts {n0(ctl2m['mc'])}. The difference is "
        f"{n2(ms['mc_est_read'])} requests est. per line and pass of the whole command, over {n0(rd2m['lines'])} lines and {n0(rd2m['passes_cmd'])} passes "
        f"(the buffer fill, then per rep one untimed pass and {n0(rd2m_bw['passes'])} timed passes, "
        f"{n0(rd2m_bw['n_reps'])} rep, from the source) "
        + S.ref('src:bandwidth.c:421-423', 'each rep runs one untimed pass, then the flush, then the timed passes')
        + f". A 2 MiB buffer is under the "
        f"3.75 MiB est. that the SLC has for DRAM lines (operator's README) "
        + S.ref('readme:R3:34', 'the SLC size that is left for DRAM lines')
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % (rd2m['line'], rd2m['last_line']))],
                'the 2 MiB read command under the mesh counters')
        + _cite(S, [('F1', 'cmn-counts.csv', '%d-%d' % (ctl2m['line'], ctl2m['last_line']))],
                'the control of CPU 2 under the mesh counters')
        + _cite(S, [_row(rd2m_bw)], 'the 2 MiB read row of the command') + '.',
        'The event is exploratory. The count covers the buffer fill and every pass.',
        'Hypothesis: the SLC does not keep the lines that the read stream passes to the cluster.',
        'Request-type events of the home nodes around a read with more passes.'])

    body += S.table(
        ['#', 'Item', 'Observation', 'Why it is not explained', 'Hypothesis or unknown',
         'Measurement that would settle it'],
        [[str(i + 1)] + it for i, it in enumerate(items)],
        caption='Observations other than the read stream that the files do not explain. Rows without a boot '
                'name are boot F1 rows.',
        note=("The bandwidth rows of 2 MiB and more and the 8 MiB chain with every line flushed first are "
              "DRAM-backed. For the 2 MiB rows, chain and bandwidth, no counter inside the timed interval "
              "separates an SLC hit from a memory-model fill (" + S.xref('setup-bandwidth-test') + "). " + dram_note
              + " On boots F1, E and C the L3 register is read on CPU 2's cluster only. On boots B and D it is "
              "also printed at each power-on of CPUs 2 to 9 (operator's README, " + S.xref('setup-boots') + ")."),
        align='llllll', id_='tab-TP3')

    # ------------------------------------------------------------------ 8.3
    body += S.h3('open-notmeasured', 'Not measured')
    nm = D.not_measured
    n_fam = len(nm['rows'])
    n_none = sum(1 for r in nm['rows'] if r['cells'][1] is None)
    f2 = S.ref('folder-012-core-files',
               'Results folder <code>results/membench-jibin-012</code> (L3 on, prefetchers off): its files other '
               'than the CME files are %s. It holds no core row.' % ', '.join(_c(x) for x in nm['f2_non_cme_files']))
    body += S.fig(
        _fig_p2(D, V, S),
        f"The {n_fam} row families of the page by firmware state. A cell names the boots that hold the rows.",
        f"No core row exists with the L3 on and the prefetchers off ({n_none} of {n_fam} families).",
        id_='fig-P2',
        note=(f"A family is counted for a boot when the boot has its result file or its mesh event. Boot "
              f"conditions: {S.xref('setup-boots')}."))

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
         ['Prefetch target, reads in progress at one time, read-queue occupancy of the home nodes',
          'Not measured. A prepared command set exists (<code>follow-up-run-plan.md</code>) %s.' % plan,
          'That command set on four boots, one per firmware state.'],
         ['Store latency, and write rows that wait for the lines to reach the memory model',
          'Not measured for the core.',
          'A write row that waits after each pass until every stored line has reached the memory model.'],
         ['SPM (the scratchpad memory)',
          'Not measured. The image has no SPM device, and the log of boot F1 reads %s %s.' % (
              _c('spm=%d' % flags['value']['spm']),
              S.ref('file:F1:sysinfo.txt:%d' % spm['line'], 'the SPM device file does not exist')
              + S.ref('file:F1:log.txt:%d' % flags['line'], 'the flags of the script, with spm=0')),
          'An image with the SPM driver.']],
        caption='What no boot measures, and what boot F1 itself does not measure. %s lists the row families '
                'that only other boots have. %s holds two more areas: the L3 state of the clusters of CPUs 4 '
                'to 9, and two readers in one cluster.' % (S.tabref('tab-TS3'), S.tabref('tab-TP3')),
        align='lll', id_='tab-TP4')
    return body
