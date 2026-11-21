"""Section 7 of asimov-c1nano-perf.html: mesh counters (boot F1).

Every measured number is read from the data layer D at build time.
Binding rules used here (critic sheet): the counts cover the whole command (C12),
"consistent with" for the home-node storage statement (C8), the status words of
the events (C20), own node over the mean of the other four (D5).
"""

import re

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
    ocm1 = [r for r in M if r['ocm'] and r['counted'] and r['label'] != sm['four_core']['label']]

    # The DRAM-backed set in words, from the rows of the data layer.
    d_chain = [r for r in dram if r['group'] == '2 MiB chain']
    d_read = [r for r in dram if r['group'] == '2 MiB read']
    d_write = [r for r in dram if r['group'] == '16 MiB writes']
    if len(d_chain) + len(d_read) + len(d_write) != len(dram) or len(d_read) != 1:
        raise ValueError('sec_mesh: the DRAM-backed commands are not the three groups named in the text')
    cpus = [str(r['cpu']) for r in d_chain]
    dram_set = 'the 2 MiB chain on CPUs %s and %s, the 2 MiB read on CPU %d and the %d write commands of 16 MiB' % (
        ', '.join(cpus[:-1]), cpus[-1], d_read[0]['cpu'], len(d_write))

    # The command with the lowest ratio against the other one-region chain commands.
    rest = [r for r in lat1 if r is not low]
    ocm_rest = [r for r in ocm1 if r is not low]
    ms = lambda r: r['child_ns'] / 1e6                  # life of the command in ms
    rate = lambda r: sum(others(r)) / 4.0 / ms(r)       # requests per other node per ms of life
    if (low not in lat1 or low not in ocm1 or len(ocm1) != sm['n_ocm']
            or ms(low) <= max(ms(r) for r in rest)
            or low['mc'] <= max(r['mc'] for r in ocm_rest) or low['mc'] <= sm['ctrl_mc'][1]
            or not min(rate(r) for r in rest) <= rate(low) <= max(rate(r) for r in rest)):
        raise ValueError('sec_mesh: the text on the lowest ratio does not fit the rows')

    # ---- references ----
    r_node = S.ref('file:F1:%s:%s' % (CMN, _lines([r['node_lines'] for r in ctrl + one])),
                   'requests received per home node of the four counted background controls and of the '
                   '%d one-region commands' % len(one))
    r_mc = S.ref('file:F1:%s:%s' % (CMN, _lines([(mc_line(r), mc_line(r)) for r in M if r['counted']])),
                 'requests sent on to memory of the %d counted core commands' % sm['n_counted_core'])
    r_share = S.ref('file:F1:%s:%s' % (CMN, _lines([r['node_lines'] for r in dram])),
                    'requests received per home node of the %d DRAM-backed commands' % len(dram))
    r_low = S.ref('file:F1:%s:%d-%d' % (CMN, low['line'], low['last_line']),
                  'every counter row of the one-region command with the lowest ratio (%s), with the life of '
                  'the command' % low['label'])
    r_wrap = S.ref('src:cmncount.c')
    r_ids = S.ref('src:lib_run.sh')
    r_readme = S.ref('readme:F1')

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
    # Every own-node cell has the same tint: the count is the text of the cell, not a shade.
    def grid_row(r, what):
        """what: the command in words.  It is the first line of the tip of each cell."""
        cells = []
        for i, n in enumerate(nodes):
            c = r['nodes'][n]
            own = n == r.get('own_node')
            tip = '%s, CPU %d\nnode %d (region %d%s): %s requests received' % (
                what, r['cpu'], n, i, ', own node' if own else '', _n(V, c))
            cells.append(dict(text=_n(V, c), kind='f1' if own else 'soft', tip=tip))
        return cells

    lat1_2 = [r for r in lat1 if r['cpu'] == 2]
    drawn = rd1 + lat1_2                                # the one-region commands of the figure
    grows = [dict(label='background control', sub='4 KiB chain on 4 KiB pages',
                  cells=grid_row(ctrl2, 'background control')),
             dict(header='OCM read of one region (256 KiB)')]
    grows += [dict(label='region %d' % r['region'], sub='ratio %s' % V.ratio(r['ratio']),
                   cells=grid_row(r, 'OCM read of region %d' % r['region'])) for r in rd1]
    grows.append(dict(header='OCM chain in one region'))
    grows += [dict(label='region %d' % r['region'], sub='ratio %s' % V.ratio(r['ratio']),
                   cells=grid_row(r, 'OCM chain in region %d' % r['region'])) for r in lat1_2]
    svg = V.grid(['node %d\nregion %d' % (n, i) for i, n in enumerate(nodes)], grows,
                 legend_items=[('own node of the command', 'f1'), ('other node', 'soft')],
                 width=860, label_w=250, corner='command, CPU 2', title='requests received per home node')
    # V.grid draws the legend swatch of a tinted kind in the full colour.  The own-node cell is a light
    # tint with a strip of the full colour at its left edge, so the swatch is redrawn in that form.
    full = V.COLORS['f1']
    m = re.search(r'<rect x="([0-9.]+)" y="([0-9.]+)" width="12" height="10" rx="2" fill="%s"/>' % full, svg)
    if not m:
        raise ValueError('sec_mesh: the legend swatch of the own node is not in the grid')
    svg = svg.replace(m.group(0),
                      '<rect x="%s" y="%s" width="12" height="10" rx="2" fill="%s" stroke="#d5d9de" '
                      'stroke-width="1"/><rect x="%s" y="%s" width="3" height="10" rx="1.5" fill="%s"/>' % (
                          m.group(1), m.group(2), V._mix(full, 0.16), m.group(1), m.group(2), full), 1)
    out += S.fig(
        svg,
        'Requests received per home node over the whole command, boot F1, commands on CPU 2. '
        'Each row is one command. The chains have one line per 4 KiB page. "ratio" is the own node over the '
        'mean of the other four nodes.',
        'The own node has the highest count in %s %d commands drawn here, and in %d of %d one-region '
        'commands when CPUs 4, 6 and 8 are added (%s).' % (
            'all' if all(r['own_highest'] for r in drawn) else '%d of the' % sum(
                1 for r in drawn if r['own_highest']),
            len(drawn), sm['own_highest'], sm['n_one_region'], S.tabref('tab-TN1')),
        id_='fig-N1',
        note='File %s %s.' % (code(CMN), r_node))

    out += S.bullets([
        'In the %d latency commands the own node (the home node of the command\'s region) receives %s requests. That is %s times the mean of the '
        'other four nodes.' % (g_lat['n'], _span(V, g_lat['own']), _span(V, g_lat['ratio'], 2)),
        'In the %d read commands the own node receives %s requests, %s times that mean.' % (
            g_rd['n'], _span(V, g_rd['own']), _span(V, g_rd['ratio'], 2)),
        'The other nodes receive %s requests. A background control puts %s requests on each node.' % (
            _span(V, g_lat['oth'] + g_rd['oth']), _rng(V, *sm['ctrl'])),
        # The subsection on the DRAM-backed commands is cut (critic sheet, cut order).  Two of its facts stay.
        'The %d DRAM-backed commands are %s. The background controls are not in this set. The %d commands '
        'send equal shares of their requests to the five nodes. Each node receives %s %% of the requests %s.' % (
            sm['n_dram'], dram_set, sm['n_dram'], _rng(V, sm['share'][0], sm['share'][1], 2), r_share),
        'The event "requests sent on to memory" is a sum over all home nodes of a whole command %s. It is '
        'exploratory. The %d one-core OCM commands count %s requests per command. The background controls '
        'count %s requests per command. The %d DRAM-backed commands count %s requests per command. This is '
        'consistent with a home node that answers an OCM request from '
        'its own storage.' % (r_mc, sm['n_ocm'], _rng(V, *sm['ocm_mc']), _rng(V, *sm['ctrl_mc']), sm['n_dram'],
                              _rng(V, *sm['dram_mc'])),
    ])
    out += S.p(
        'The lowest ratio (%s) is the region %d command on CPU %d. Its other four nodes receive %s requests, '
        'above every other one-region command. Three more values of that command %s:'
        % (V.ratio(low['ratio']), low['region'], low['cpu'], _span(V, others(low)), r_low))
    out += S.bullets([
        'The command lives %s ms. The other %d one-region chain commands live %s ms.' % (
            V.num(ms(low), 2), len(rest), _span(V, [ms(r) for r in rest], 2)),
        'Its requests sent on to memory are %s. That is the largest count of the %d one-core OCM '
        'commands (the others read at most %s) and above every background control (at most %s).' % (
            _n(V, low['mc']), sm['n_ocm'], _n(V, max(r['mc'] for r in ocm_rest)), _n(V, sm['ctrl_mc'][1])),
        'Per ms of command life, each of its other four nodes receives %s requests (mean of the four). '
        'The other %d chain commands read %s requests per node per ms.' % (
            _n(V, rate(low)), len(rest), _span(V, [rate(r) for r in rest])),
    ])
    out += S.hyp(
        'The command runs longer, and other activity on the chip adds requests to all five nodes during '
        'that time. Insufficient data: why this command lives longer than the other %d.' % len(rest),
        'A repeat of that command, with the life of the command and the counts of the five nodes. It would '
        'show whether the longer life and the higher counts belong to the command.')

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
        note='File %s %s. The L3 status register is read on the cluster of CPU 2 only '
             '(operator\'s README) %s.' % (code(CMN), r_node, r_readme))

    return out
