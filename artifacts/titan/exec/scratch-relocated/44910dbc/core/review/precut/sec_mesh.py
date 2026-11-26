"""Section 7 of asimov-c1nano-perf.html: mesh counters (boot F1).

Every measured number is read from the data layer D at build time.
Binding rules used here (critic sheet): the counts cover the whole command (C12),
"consistent with" for the home-node storage statement (C8), the status words of
the events (C20), own node over the mean of the other four (D5).
"""

KEY = 'mesh'
TITLE = 'Mesh counters'

CMN = 'cmn-counts.csv'
EV_MC = 'hns_mc_reqs_local_all'


def _n(V, v):
    return V.num(v, 0)


def _rng(V, lo, hi, digits=0):
    return '%s to %s' % (V.num(lo, digits), V.num(hi, digits))


def _span(V, vals, digits=0):
    return _rng(V, min(vals), max(vals), digits)


def _lines(ranges):
    """[(first, last)] -> the line suffix of a reference key."""
    return ','.join('%d-%d' % (a, b) if a != b else '%d' % a for a, b in ranges)


def _cores(label):
    """'write-cpus2-3-8-9' -> 'CPUs 2, 3, 8, 9'."""
    return 'CPUs ' + ', '.join(label.split('cpus')[1].split('-'))


def build(D, V, S):
    code = lambda s: '<code>%s</code>' % s
    M = D.mesh_cmd
    sm = D.mesh_summary
    nodes = list(D.cmn_nodes('F1', M[0]['label']).keys())
    ctrl = [r for r in M if r['group'] == 'control']
    ctrl2 = next(r for r in ctrl if r['cpu'] == 2)
    one = [r for r in M if r.get('region') is not None]
    lat1 = [r for r in one if r['group'] == 'OCM chain, one region']
    rd1 = [r for r in one if r['group'] == 'OCM read, one region']
    dram = [r for r in M if r['dram_backed']]

    # ---- values derived here from D.mesh_cmd (reported to the caller) ----
    def others(r):
        return [c for n, c in r['nodes'].items() if n != r['own_node']]

    def group_stats(rows):
        return dict(n=len(rows), own=[r['own'] for r in rows],
                    oth=[c for r in rows for c in others(r)], ratio=[r['ratio'] for r in rows])

    g_lat, g_rd = group_stats(lat1), group_stats(rd1)
    low = min(one, key=lambda r: r['ratio'])            # the command with the lowest ratio
    mc_line = lambda r: D.cmn('F1', label=r['label'], event=EV_MC)[0]['line']
    ocm1 = [r for r in M if r['ocm'] and r['counted'] and r is not sm['four_core'] and
            r['label'] != sm['four_core']['label']]
    four = sm['four_core']
    dram_over_ctrl = sm['dram_mc'][0] / sm['ctrl_mc'][1]
    share_gap = max(r['spread'] for r in D.mesh_share)   # (largest - smallest share) / mean share, %
    writes = [r for r in dram if r['group'] == '16 MiB writes']

    # ---- references ----
    r_node = S.ref('file:F1:%s:%s' % (CMN, _lines([r['node_lines'] for r in ctrl + one])),
                   'requests received per home node of the four counted background controls and of the '
                   '%d one-region commands' % len(one))
    r_mc = S.ref('file:F1:%s:%s' % (CMN, _lines([(mc_line(r), mc_line(r)) for r in M if r['counted']])),
                 'requests sent on to memory of the %d counted core commands' % sm['n_counted_core'])
    r_share = S.ref('file:F1:%s:%s' % (CMN, _lines([r['node_lines'] for r in dram])),
                    'requests received per home node of the %d DRAM-backed commands' % len(dram))
    r_wrap = S.ref('src:cmncount.c')
    r_ids = S.ref('src:lib_run.sh')
    r_readme = S.ref('readme:F1')
    r_r3 = S.ref('readme:R3')

    for t in ('mesh', 'home node', 'own node', 'requests received', 'requests sent on to memory',
              'exploratory', 'background control', 'OCM', 'SLC', 'command'):
        S.term(t)

    # =====================================================================
    # 7.1
    # =====================================================================
    out = S.h3('mesh-own', 'Each command reached its own node')
    out += S.bullets([
        'A wrapper program counts mesh events over the whole life of each command of boot F1 (%s) %s. So no '
        'count is divided by timed loads or timed lines.' % (S.xref('setup-counters'), r_wrap),
        'The file %s holds %d counted core commands. No counter row is multiplexed (counted for only a part '
        'of the command). So no count is scaled %s.' % (code(CMN), sm['n_counted_core'], r_node),
        'The event "requests received" is counted at each of the five home nodes. Node ids %s hold OCM '
        'regions 0 to 4 %s.' % (', '.join(str(n) for n in nodes), r_ids),
    ])

    # Figure N1: grid, own node orange, other nodes grey.
    cmax = max(max(r['counts']) for r in rd1 + lat1 if r['cpu'] == 2)

    def grid_row(r):
        cells = []
        for n in nodes:
            c = r['nodes'][n]
            if n == r.get('own_node'):
                cells.append(dict(text=_n(V, c), kind='f1', shade=c / cmax))
            else:
                cells.append(dict(text=_n(V, c), kind='soft'))
        return cells

    grows = [dict(label='background control', sub='4 KiB chain, DRAM-backed', cells=grid_row(ctrl2)),
             dict(header='OCM read of one region (256 KiB)')]
    grows += [dict(label='region %d' % r['region'], sub='ratio %s' % V.ratio(r['ratio']), cells=grid_row(r))
              for r in rd1]
    grows.append(dict(header='OCM chain in one region'))
    grows += [dict(label='region %d' % r['region'], sub='ratio %s' % V.ratio(r['ratio']), cells=grid_row(r))
              for r in lat1 if r['cpu'] == 2]
    svg = V.grid(['node %d\nregion %d' % (n, i) for i, n in enumerate(nodes)], grows,
                 legend_items=[('own node of the command', 'f1'), ('other node', 'soft')],
                 width=860, label_w=250, corner='command, CPU 2', title='requests received per home node')
    out += S.fig(
        svg,
        'Requests received per home node over the whole command, boot F1, commands on CPU 2. '
        'Each row is one command. The chains have one line per 4 KiB page. "ratio" is the own node over the '
        'mean of the other four nodes.',
        'The own node has the highest count in %d of %d one-region commands.' % (sm['own_highest'],
                                                                              sm['n_one_region']),
        id_='fig-N1',
        note='File %s %s. The commands on CPUs 4, 6 and 8 are in %s.' % (code(CMN), r_node,
                                                                      S.tabref('tab-TN1')))

    out += S.bullets([
        'In the %d latency commands the own node (the home node of the command\'s region) receives %s requests. That is %s times the mean of the '
        'other four nodes.' % (g_lat['n'], _span(V, g_lat['own']), _span(V, g_lat['ratio'], 2)),
        'In the %d read commands the own node receives %s requests, %s times that mean.' % (
            g_rd['n'], _span(V, g_rd['own']), _span(V, g_rd['ratio'], 2)),
        'The other nodes receive %s requests. A background control puts %s requests on each node.' % (
            _span(V, g_lat['oth'] + g_rd['oth']), _rng(V, *sm['ctrl'])),
        'So the status of this event is "checked by the one-region commands (%d of %d)".' % (
            sm['own_highest'], sm['n_one_region']),
    ])
    out += S.insufficient(
        'The lowest ratio (%s) is the region %d command on CPU %d. Its other four nodes receive %s requests, '
        'above every other one-region command. No file gives the cause. A repeat of that command would '
        'show whether it belongs to the command.' % (
            V.ratio(low['ratio']), low['region'], low['cpu'], _span(V, others(low))))

    # Table TN1: by command group.
    def tn1_row(name, rows, c):
        g = group_stats(rows)
        return [name, str(g['n']), _span(V, g['own']), _span(V, g['oth']), _span(V, g['ratio'], 2),
                _span(V, c['counts'])]

    trows = [tn1_row('OCM chain in one region, CPU %d' % c['cpu'], [r for r in lat1 if r['cpu'] == c['cpu']], c)
             for c in ctrl]
    trows.append(tn1_row('OCM read of one region, CPU 2', rd1, ctrl2))
    out += S.table(
        ['Command group', 'Commands', 'Own node', 'Other nodes', 'Own node over mean of others',
         'Background control of that CPU'],
        trows, align='lrrrrr', id_='tab-TN1',
        caption='Requests received per home node by command group, boot F1, smallest to largest count.',
        note='File %s %s. The L3 status register was read on the cluster of CPU 2 only '
             '(operator\'s README) %s.' % (code(CMN), r_node, r_readme))

    # =====================================================================
    # 7.2
    # =====================================================================
    out += S.h3('mesh-dram', 'DRAM-backed commands')
    out += S.bullets([
        'The event "requests sent on to memory" is a sum over all home nodes of a whole command %s. It is '
        'exploratory.' % r_mc,
        'The %d one-core OCM commands read %s, and the four-core OCM read %s. The background controls read %s. '
        'The %d DRAM-backed commands read %s, at least %s times the highest control.' % (
            sm['n_ocm'], _rng(V, *sm['ocm_mc']), _n(V, four['mc']), _rng(V, *sm['ctrl_mc']), sm['n_dram'],
            _rng(V, *sm['dram_mc']), V.num(dram_over_ctrl, 1)) +
        ' This is consistent with a home node that answers an OCM request from its own storage.',
        'The DRAM-backed commands load the five nodes in equal shares. Each node receives %s %% of the '
        'requests. The largest share minus the smallest is at most %s %% of the mean share %s.' % (
            _rng(V, sm['share'][0], sm['share'][1], 2), V.num(share_gap, 2), r_share),
        'Net of the CPU 2 control, the requests sent on to memory per line and pass of the whole command are '
        '%s est. for the 2 MiB read and %s est. for the %d write commands. The pass count comes from the '
        'source, so the value is an estimate.' % (
            V.num(sm['mc_est_read'], 2), _rng(V, sm['mc_est_writes'][0], sm['mc_est_writes'][1], 2),
            len(writes)),
        'The 2 MiB read is smaller than the 3.75 MiB est. of SLC left for DRAM lines (operator\'s README) %s. '
        'Why it sends about one request per line and pass on to memory is an open item of %s.' % (
            r_r3, S.xref('open-items')),
    ])

    # Table TN2: the 10 DRAM-backed commands.
    def tn2_name(r):
        if r['group'] == '2 MiB chain':
            return 'chain, 2 MiB, CPU %d' % r['cpu']
        if r['group'] == '2 MiB read':
            return 'read, 2 MiB, CPU 2'
        return 'write, 16 MiB, %s' % _cores(r['label'])

    by_label = {r['label']: r for r in dram}
    t2 = []
    for s in D.mesh_share:
        r = by_label[s['label']]
        est = s['mc_net_per_line_pass_est']
        t2.append([tn2_name(r)] + [V.num(x, 2) for x in s['shares']] +
                  [V.num(s['spread'], 2), _n(V, s['mc']), V.num(est, 2) if est is not None else '-'])
    out += S.table(
        ['Command'] + ['Node %d' % n for n in nodes] + ['Gap', 'To memory', 'Est.'],
        t2, align='l' + 'r' * 8, id_='tab-TN2',
        caption='The %d DRAM-backed commands of boot F1: share of the requests received per home node, and '
                'requests sent on to memory.' % len(dram),
        note='File %s %s. "Node": share of the requests received, in %%. "Gap": the largest share minus the '
             'smallest, in %% of the mean share. "To memory": requests sent on to memory. "Est.": the same per '
             'line and pass, net of the CPU 2 control, for the bandwidth commands only. The DRAM model is an '
             'emulator memory, not silicon timing (operator\'s README) %s.' % (
                 code(CMN), r_share, r_readme))
    return out
