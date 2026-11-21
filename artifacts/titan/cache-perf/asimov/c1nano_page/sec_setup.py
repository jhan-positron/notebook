"""Section 1 "What was measured" and the Short version with its headline figure H1.

Exposes KEY, TITLE, build(D, V, S) and short_version(D, V, S).
Every measured number is read from the data layer D when the page is built.
Facts that exist only in the operator's README, in a source file or in the SOG
(Arm C1-Nano Core Software Optimization Guide) are typed and carry a reference.
"""

KEY = 'setup'
TITLE = 'What was measured'

KIB = 1024
MIB = 1024 * 1024
BOOTS = ['F1', 'E', 'B', 'C', 'D', 'R3']


def _c(s):
    return '<code>%s</code>' % s


def _fref(S, row, text):
    """[RefN] of the timed row of a derived row."""
    return S.ref('file:%s:%s:%d' % (row['boot'], row['file'], row['line']), text)


def _rng(a, b, digits=4):
    return '%.*f' % (digits, a) if round(a, digits) == round(b, digits) else '%.*f to %.*f' % (digits, a, digits, b)


def _timed_rows(D, boot):
    """Every timed row of every core latency file of a boot (generic row access)."""
    for name in D.files[boot]['latency']:
        for blk in D.latblocks(boot, name):
            for size in blk['order']:
                for rep in blk['sizes'][size]['reps']:
                    yield name, blk, rep


def _event_checks(D):
    """Values for the status column of the event table.  Computed here from generic row access."""
    out = {}
    # L1 prefetch refills and L2 refills by the L1 prefetcher: largest value on the prefetchers-off boots.
    off = [rep.get(k) for b in ('B', 'D') for _, _, rep in _timed_rows(D, b) for k in ('l1pf', 'l2byl1pf')]
    out['pf_off_max'] = max(v for v in off if v is not None)
    seq = [v for r in D.lat_seq if r['boot'] in ('E', 'C') for k in ('l1pf_reps', 'l2byl1pf_reps') for v in r[k]]
    out['pf_seq'] = (min(seq), max(seq))
    # L2 prefetch refills at 192 to 384 KiB, prefetchers on (boots F1, E, C) and off (boots B, D).
    sizes = (192 * KIB, 256 * KIB, 384 * KIB)
    on = [v for b in ('F1', 'E', 'C') for s in sizes for v in D.sweep_row(b, s)['l2pf_reps']]
    offv = [v for b in ('B', 'D') for s in sizes for v in D.sweep_row(b, s)['l2pf_reps']]
    out['l2pf_on'] = (min(on), max(on))
    out['l2pf_off_max'] = max(offv)
    # 0xA2 on the address-order chain of boot E (critic C7).
    e = next(r for r in D.lat_seq if r['boot'] == 'E')
    out['a2_seq_e'] = e['a2']
    out['seq_e'] = e
    return out


def _headline(D):
    H = {h['key']: h for h in D.headline}
    hit = next(r for r in D.lat_hit if r['size'] == H['l3']['size'])
    return H, hit


# ---------------------------------------------------------------------------------- Short version

def short_version(D, V, S):
    H, hit = _headline(D)
    f1 = D.boot['F1']
    r16 = D.one_core('read', 16 * KIB)
    r32 = D.one_core('read', 32 * MIB)
    w32 = D.one_core('write', 32 * MIB)
    c4r = D.mc('one core per cluster', 'read', 2 * MIB)
    c4w = D.mc('one core per cluster', 'write', 2 * MIB)
    dram_ref = S.ref('readme:F1:247,354', 'the DRAM model')
    ratio = H['dram-model']['ns'] / H['l1']['ns']

    out = S.bullets([
        'This page reports the memory latency and bandwidth that the Arm C1-Nano cores of the emulated Asimov '
        'chip see on boot F1 (the main boot: L3 cache on, hardware prefetchers on).',
        'A load whose address is the data of the load before it costs %s from the L1 cache and %s from the '
        'DRAM model (an emulator memory, not silicon timing) on CPU 2, and %s gives the levels between.' % (
            V.ns(H['l1']['ns']), V.ns(H['dram-model']['ns']), S.figref('fig-H1')),
        'One core reads %s GB/s with a %s buffer (the footprint) and %s GB/s at %s, and it writes %s GB/s at '
        '%s.' % (
            V.num(r16['best']), r16['label'], V.num(r32['best']), r32['label'], V.num(w32['best']), w32['label']),
    ])
    c384 = D.sweep_row('F1', H['l3']['size'])
    ocm_region = V.size_label(D.platform['ocm_iomem'][0]['bytes'])

    rows = [
        dict(label='L1', sub='%s chain' % H['l1']['label'], value=H['l1']['ns'],
             note='(%.2f cycles)' % H['l1']['cycles']),
        dict(label='L2', sub='%s chain' % H['l2']['label'], value=H['l2']['ns'],
             note='(%.2f cycles)' % H['l2']['cycles']),
        dict(label='L3', sub='%s chain, %.2f L3 hits per load counted on boot E' % (H['l3']['label'], hit['l3hit']),
             value=H['l3']['ns'], note='(%.2f cycles)' % H['l3']['cycles']),
        dict(label='Home nodes over the mesh (SLC)', sub='%s chain' % H['home-nodes']['label'],
             value=H['home-nodes']['ns'], note='(%.2f cycles)' % H['home-nodes']['cycles']),
        dict(label='OCM', sub='every line, all five regions', value=H['ocm']['ns'],
             note='(%.2f cycles)' % H['ocm']['cycles']),
        dict(label='DRAM model', sub='%s, every line flushed first' % H['dram-model']['label'],
             value=H['dram-model']['ns'], note='(%.2f cycles)' % H['dram-model']['cycles']),
    ]
    svg = V.hbar(rows, unit='ns', fmt=lambda v: V.num(v, 3), xlabel='chain load, ns per load (boot F1, CPU 2)',
                 label_w=330)
    note = (
        'Home nodes are the five devices on the mesh (the grid that joins the core clusters to the memory). '
        'They hold the SLC (system-level cache, shared by all cores) and the OCM (on-chip memory, five '
        'regions of %s). The %s chain counts %.2f L3 read refills (fills from outside the cluster) per load '
        '(best rep). The %s bar is interpreted as the SLC: no counter inside the timed interval '
        'separates an SLC hit from a fill by the DRAM model (%s). Four cores, one per cluster (two cores that '
        'share an L2 and an L3), read %s GB/s and write %s GB/s at %s each. '
        'Chain rows %s %s %s %s. L3 hits: boot E (the firmware state of boot F1, another command '
        'set) %s. Bandwidth rows %s %s. The DRAM model is an emulator memory with zero configured delay, not '
        'silicon timing (operator\'s README) %s. The bandwidth rows of %s and more are DRAM-backed: their '
        'buffers are in memory that this model backs. How their timed lines split between SLC hits and fills by '
        'the DRAM model is not known at 2 MiB (%s). Bandwidth is loop throughput. The L3 status register is read on the cluster '
        'of CPU 2 only (operator\'s README) %s.' % (
            ocm_region, H['l3']['label'], c384['a2'], H['home-nodes']['label'], S.xref('lat-levels'),
            V.num(c4r['best']), V.num(c4w['best']), c4r['label'],
            S.ref('file:F1:%s:%d,%d,%d' % (H['l1']['file'], H['l1']['line'], H['l2']['line'], H['l3']['line']),
                  'the 4 KiB, 128 KiB and 384 KiB chains of the headline figure'),
            _fref(S, H['home-nodes'], 'the 2 MiB chain'),
            _fref(S, H['ocm'], 'the OCM row of CPU 2'),
            _fref(S, H['dram-model'], 'the DRAM-model row'),
            _fref(S, hit, 'the 384 KiB chain with the hit set'),
            S.ref('file:F1:%s:%d,%d,%d' % (r16['file'], r16['line'], r32['line'], w32['line']),
                  'the 16 KiB read, the 32 MiB read and the 32 MiB write'),
            S.ref('file:F1:%s:%d,%d' % (c4r['file'], c4r['line'], c4w['line']), 'the 2 MiB read and write'),
            dram_ref, c4r['label'], S.xref('setup-bandwidth-test'),
            S.ref('readme:F1:74', 'which cluster the L3 register reading covers')))
    out += S.fig(
        svg,
        'What one dependent load costs, by where the line comes from. Boot F1, CPU 2, best row of each chain. '
        'Cycles per load in brackets.',
        'The DRAM-model load costs %s the L1 load. A load from the home nodes or from the OCM costs %.2f to '
        '%.2f times the DRAM-model load.' % (
            V.ratio(ratio, 1).replace(' x', ' times'), H['home-nodes']['ns'] / H['dram-model']['ns'],
            H['ocm']['ns'] / H['dram-model']['ns']),
        id_='fig-H1', note=note)
    for t in ('home node', 'mesh', 'SLC', 'OCM', 'every line', 'every line flushed first'):
        S.term(t)
    assert f1['main']
    return out


# ---------------------------------------------------------------------------------- 1.1 the chip

def _chip(D, V, S):
    P = D.platform
    cb = P['cache_bytes']
    l1, l2, l3 = (V.size_label(cb[k]) for k in ('L1', 'L2', 'L3'))
    ocm_b = P['ocm_iomem'][0]['bytes']
    n_ocm = len(P['ocm_iomem'])
    assert all(o['bytes'] == ocm_b for o in P['ocm_iomem'])
    ocm = V.size_label(ocm_b)
    M = D.mesh
    n_hn, n_port, n_br = M['device_counts']['HN-S'], M['device_counts']['RN-F'], M['device_counts']['SBSX']
    c = P['caches']
    line_bytes = sorted(set(int(x['text'].split(' line=')[1].split()[0]) for x in c))
    assert len(line_bytes) == 1

    sysinfo_caches = S.ref('file:F1:sysinfo.txt:%d-%d' % (c[0]['line'], c[-1]['line']), 'the cache list of CPU 2')
    readme_slc = S.ref('readme:R3:34', 'the SLC and the OCM ways')
    readme_dram = S.ref('readme:F1:247,354', 'the DRAM model')
    readme_pair = S.ref('readme:F1:346', 'what the two cores of a cluster share')

    y, h = 34, 92
    nodes = [
        dict(id='core', x=14, y=y, w=96, h=h, title='core', lines=['C1-Nano', '%d on the chip' % P['n_cpus']],
             kind='accent'),
        dict(id='l1', x=140, y=y, w=96, h=h, title='L1 data', lines=[l1, 'per core']),
        dict(id='l2', x=266, y=y, w=96, h=h, title='L2', lines=[l2, 'per cluster']),
        dict(id='l3', x=392, y=y, w=96, h=h, title='L3', lines=[l3, 'per cluster']),
        dict(id='port', x=518, y=y, w=96, h=h, title='mesh port', lines=['one per cluster']),
        dict(id='hn', x=668, y=y, w=150, h=h, title='home node',
             lines=['1 MiB slice of the SLC', '4 of its 16 ways hold', 'one OCM region', '(%s)' % ocm]),
        dict(id='br', x=848, y=y, w=70, h=h, title='bridge', kind='soft'),
        dict(id='dram', x=946, y=y, w=86, h=h, title='DRAM model', lines=['emulator memory', 'zero delay'],
             kind='dashed'),
    ]
    arrows = [dict(src='core', dst='l1'), dict(src='l1', dst='l2'), dict(src='l2', dst='l3'),
              dict(src='l3', dst='port'), dict(src='port', dst='hn'), dict(src='hn', dst='br'),
              dict(src='br', dst='dram')]
    groups = [dict(x=4, y=6, w=620, h=h + 40, label='cluster: two cores share the L2, the L3 and the port'),
              dict(x=634, y=6, w=294, h=h + 40, label='mesh: %d x %d crosspoints, %d home nodes' % (
                  M['grid_x'], M['grid_y'], n_hn))]
    svg = V.boxes(nodes, arrows, groups=groups, title='data path of one load')

    b = S.h3('setup-chip', 'The chip under test')
    b += S.bullets([
        'The chip is one emulated Asimov chip with %d Arm %s cores %s. Two cores form a %s. The tests use '
        'CPUs 2 to 9, which are four clusters.' % (
            P['n_cpus'], S.term('C1-Nano'),
            S.ref('file:F1:sysinfo.txt:%d,%d' % (P['online_cpus']['line'], P['cpu_part']['line']),
                  'the online CPUs and the CPU part number'), S.term('cluster')),
        'Each core has an L1 data cache of %s that stores %d-byte lines. The two cores of a cluster share an L2 '
        'of %s, an L3 of %s and one port on the %s %s.' % (
            l1, line_bytes[0], l2, l3, S.term('mesh'), sysinfo_caches + ' ' + readme_pair),
        'The mesh has five %s. Each one holds a 1 MiB slice of the %s (system-level cache). Each slice has 16 '
        '%s (a way is one of the equal parts of a cache, and a given line can be stored in one place of each '
        'way). The firmware reserves 4 ways of each slice as one region of %s (on-chip memory). So 3.75 MiB est. '
        'of the SLC is left for DRAM lines (operator\'s README) %s.' % (
            S.term('home nodes'), S.term('SLC'), S.term('ways'), S.term('OCM'), readme_slc),
        'Behind the home nodes is the %s. It is four emulator memory models with every delay control at zero. No '
        'number of this level is silicon timing (operator\'s README) %s. Insufficient data: the share of the '
        'DRAM-model latency that is spent on the mesh. A signal trace of one miss in the emulator would settle '
        'it (operator\'s README) %s.' % (
            S.term('DRAM model'), readme_dram, S.ref('readme:F1:252', 'what is not determined on the DRAM path')),
    ])
    b += S.fig(svg, 'The path of one load from the core to the DRAM model, left to right. Schematic. The sizes '
                    'are the listed capacities.',
               'The figure shows the order of the levels on the path. It does not show which level served a given '
               'load.',
               id_='fig-S1',
               note='A %s is the mesh device that connects the mesh to the DRAM model %s.' % (
                   S.term('bridge'),
                   S.ref('file:F1:sysinfo.txt:%d-%d' % (M['map_first_line'], M['map_last_line']), 'the mesh map')))

    def si(key, text):
        return S.ref('file:F1:sysinfo.txt:%d' % P[key]['line'], text)

    clk = D.clock['F1']
    rows = [
        ['Cores', '%d Arm C1-Nano, CPU part %s, CPUs %s online' % (P['n_cpus'], _c(P['cpu_part']['value']),
                                                                   P['online_cpus']['value'].replace('-', ' to ')),
         si('cpu_part', 'the CPU part number')],
        ['Test CPUs', 'CPUs %s, kept free of the scheduler tick and of device interrupts' % (
            P['nohz']['value'].replace('-', ' to ')),
         si('cmdline', 'the Linux command line') + ' ' + S.ref(
             'run:F1:dmesg.txt:%d' % P['nohz']['line'], 'the CPUs without a scheduler tick')],
        ['OCM', '%d regions x %s, as Linux lists them' % (n_ocm, ocm),
         S.ref('file:F1:sysinfo.txt:%d-%d' % (P['ocm_iomem'][0]['line'], P['ocm_iomem'][-1]['line']),
               'the five OCM address ranges')],
        ['Mesh', '%d x %d crosspoints, %d home nodes, %d cluster ports, %d bridges to memory' % (
            M['grid_x'], M['grid_y'], n_hn, n_port, n_br),
         S.ref('file:F1:sysinfo.txt:%d-%d' % (M['map_first_line'], M['map_last_line']), 'the mesh map')],
        ['DRAM buffers', '%d huge pages of %d MiB' % (P['hugepages_total']['value'],
                                                     P['hugepagesize_kb']['value'] // 1024),
         si('hugepages_total', 'the huge pages')],
        ['Core clock', '%.3f cycles per ns, measured (%s)' % (clk['pooled'], S.xref('setup-counters')),
         'latency files of boot F1'],
        ['Timer', '%.0f MHz, so one count of the timer is 1 ns' % P['timer']['value'],
         S.ref('run:F1:dmesg.txt:%d' % P['timer']['line'], 'the timer frequency')],
        ['Linux version', '%s' % P['kernel']['value'], si('kernel', 'the Linux version')],
        ['Firmware of boot F1', 'SCP 0.48.0-nopcie-l3.1 and TF-A 0.35.0, debug builds',
         'operator\'s README ' + S.ref('readme:F1:344', 'the firmware versions')],
    ]
    b += S.table(['Item', 'Value', 'Source'], rows, caption='Platform facts of boot F1.',
                 note='SCP is the firmware of the system control processor. TF-A is the trusted firmware of the '
                      'cores.',
                 id_='tab-TS1', align='lll')
    return b


# ---------------------------------------------------------------------------------- 1.2 the mesh

def _mesh(D, V, S, data):
    M = D.mesh
    st = {(r['cpu'], r['region']): r for r in D.steps}
    cells = []
    for hn in M['home_nodes']:
        r = hn['region']
        cells.append((hn['x'], hn['y'], 'region %d\nid %d\nsteps %d | %d' % (
            r, hn['node'], st[(2, r)]['steps'], st[(8, r)]['steps']), 'hn'))
    for p in M['ports']:
        if p['used']:
            cells.append((p['x'], p['y'], 'CPUs %d, %d\nid %d' % (p['cpus'][0], p['cpus'][1], p['node']), 'port'))
        else:
            cells.append((p['x'], p['y'], 'port, id %d\nno test CPU' % p['node'], 'plain'))
    p2 = next(p for p in M['ports'] if p['cpu'] == 2)
    ex = st[(2, 3)]
    hn3 = M['home_nodes'][3]
    svg = V.mesh_map(M['grid_x'], M['grid_y'], cells,
                     steps=[dict(src=(p2['x'], p2['y']), dst=(hn3['x'], hn3['y']),
                                 label='%d X steps + %d Y step' % (ex['dx'], ex['dy']), color='ref')],
                     cell_h=50,
                     kinds={'plain': 'port of the cluster that no test uses', 'port': 'cluster port',
                            'hn': 'home node (one OCM region)'})
    sm = D.steps_mean
    assert M['ports_ok'] and M['homes_ok']

    b = S.h3('setup-mesh', 'The mesh')
    b += S.bullets([
        'The mesh is a grid of %d x %d crosspoints. A device at crosspoint (x, y) has node id 64 x + 8 y.' % (
            M['grid_x'], M['grid_y']),
        'The home nodes of OCM regions 0 to 4 have the node ids %s (%s) %s.' % (
            ', '.join('%d' % n for n in data.REGION_NODE), _c('lib_run.sh'),
            S.ref('src:lib_run.sh:39', 'the node ids of the five home nodes')),
        'The ports of the clusters of CPUs 2 to 9 are at %s (operator\'s README) %s. The mesh map of Linux '
        'agrees %s.' % (
            ', '.join('(%d,%d)' % data.PORT_XY[c] for c in data.CPUS),
            S.ref('readme:R3:36', 'the mesh coordinates of the ports and of the home nodes'),
            S.ref('file:F1:sysinfo.txt:%d-%d' % (M['map_first_line'], M['map_last_line']), 'the mesh map')),
        'A %s is one move between neighbour crosspoints. A home node at (hx, hy) is |hx - px| X steps and '
        '|hy - py| Y steps from a port at (px, py). Every shortest route has these counts.' % S.term('step'),
        'Mean steps to the five home nodes: %s.' % ', '.join(
            '%.1f from CPU %d' % (sm[c]['total'], c) for c in data.CPUS),
    ])
    b += S.fig(svg,
               'The mesh. The last line of a home node gives its steps from the port of CPUs 2, 3 and from the '
               'port of CPUs 8, 9. The grey route is one example.',
               'The ports of CPUs 2 and 6 are between home nodes. The port of CPU 8 is at the edge, %d steps from '
               'regions 0 and 1.' % (
                   st[(8, 0)]['steps']),
               id_='fig-S2',
               note='The route of a request is not measured.')
    assert st[(8, 0)]['steps'] == st[(8, 1)]['steps'] and sm[2]['total'] == sm[6]['total']
    return b


# ---------------------------------------------------------------------------------- 1.3 the boots

_USE = {
    'F1': 'every result',
    'E': 'L3 hits, address order, read variants, L1 forms, second sample',
    'B': 'prefetchers-off rows, OCM per region',
    'C': 'separates the L3 state from the prefetchers',
    'D': 'OCM page mapping',
    'R3': 'one open item',
}


_NW = '<span style="white-space:nowrap">%s</span>'


def _hex(v):
    return '0x%x' % v


def _boots(D, V, S):
    f1 = D.boot['F1']
    grid_rows = []
    for k in BOOTS:
        bt = D.boot[k]
        same = lambda key: 'f1' if bt[key] == f1[key] else 'soft'
        reg = ('register %s' % ', '.join(_hex(v) for v in bt['pwrstat_values'])) if bt['pwrstat_values'] \
            else "operator's README"
        if bt['map_cont']:
            (cont, n), = bt['map_cont'].items()
            mp = 'cont=%s on %d lines' % (cont, n)
        else:
            mp = "operator's README"
        grid_rows.append(dict(
            label=bt['name'], sub=_USE[k], hl=bt['main'],
            cells=[dict(text=bt['l3'], kind=same('l3'), sub=reg),
                   dict(text=bt['prefetchers'], kind=same('prefetchers')),
                   dict(text=bt['ocm_mapping'], kind=same('ocm_mapping'), sub=mp)]))
    svg = V.grid(['L3 of the test clusters', 'hardware prefetchers', 'OCM mapping'], grid_rows,
                 legend_items=[('as boot F1', 'f1'), ('differs from boot F1', 'soft')],
                 width=900, corner='boot and its use on this page', cell_h=40, col_w=200)

    def log_ref(k):
        bt = D.boot[k]
        ls = [p['line'] for p in bt['pwrstat_lines']]
        if ls:
            return S.ref('file:%s:log.txt:%s' % (k, ','.join('%d' % x for x in ls)),
                         'the two readings of the L3 status register')
        return S.ref('file:%s:log.txt' % k)

    on = [k for k in BOOTS if D.boot[k]['pwrstat_values'] == [0x70]]
    nod = [k for k in BOOTS if D.boot[k]['pwrstat_values'] == [0]]
    unread = [k for k in BOOTS if not D.boot[k]['pwrstat_values']]
    assert on == ['F1', 'E'] and nod == ['B', 'C', 'D'] and unread == ['R3']
    assert all(D.boot[k]['l3_from_log'] in (None, D.boot[k]['l3']) for k in BOOTS)
    cC, cD = D.boot['C'], D.boot['D']
    assert cC['map_cont'] == {'64/64': cC['map_lines']} and cD['map_cont'] == {'64/64': cD['map_lines']}

    cmp_ec, cmp_db = D.cmd_cmp[('E', 'C')], D.cmd_cmp[('D', 'B')]
    b = S.h3('setup-boots', 'The boots')
    b += S.bullets([
        'A %s is one power-on of the emulated chip with one firmware set. It ran one script once.' % S.term('boot'),
        'Boot F1 gives every row that it has. Five other boots add rows that boot F1 does not have '
        '(%s). The boots differ in three conditions.' % S.tabref('tab-TS3'),
        'L3. In the state "%s" the L3 of a cluster stores lines. In the other state %s: it only tracks which core '
        'has a line. The firmware sets the state before the cores start (operator\'s README) %s.' % (
            S.term('L3 on'), S.term('the L3 holds no data'),
            S.ref('readme:F1:66-67', 'what the register value 0x70 means') + ' ' +
            S.ref('readme:B:27', 'what the register value 0x0 means')),
        'The logs of boots %s each hold two readings of the L3 status register of the cluster of CPU 2. They '
        'read %s on boots %s and %s on boots %s %s. Boot R3 has no reading. Its state is taken from the '
        'operator\'s README %s.' % (
            ', '.join(on + nod), _c('0x70'), ' and '.join(on), _c('0x0'), ', '.join(nod),
            ' '.join(log_ref(k) for k in on + nod),
            S.ref('readme:F1:82-83,89', 'the conditions of boot R3')),
        'Boots F1, E and C have no register reading for the clusters of CPUs 4 to 9 (operator\'s README) %s %s '
        '%s. On boots B and D a firmware hook prints the register at each power-on of CPUs 2 to 9, and every '
        'line reads %s (operator\'s README of boots B and D) %s %s.' % (
            S.ref('readme:F1:74', 'which cluster the L3 register reading covers'),
            S.ref('readme:E:61', 'which cluster the L3 register reading covers'),
            S.ref('readme:C:27'), _c('0x0'), S.ref('readme:B:27'), S.ref('readme:D:11,22')),
        'Prefetchers. "%s" means that the firmware set the disable bit of the hardware data prefetchers on '
        'CPUs 2 to 9 (operator\'s README) %s.' % (
            S.term('prefetchers off'), S.ref('readme:B:16', 'the disable bit of the prefetchers')),
        'OCM mapping. Boots C and D map each OCM region with 4 KiB page-table entries that carry the %s (a flag '
        'that lets the core keep one translation for 16 neighbour entries). So one translation covers 64 KiB. '
        'Every mapping line of their Linux boot logs reads %s %s. Boots F1, E and B use plain 4 KiB entries: '
        'every mapping line reads %s %s. The folder of boot R3 has no Linux boot log. '
        'Its mapping (plain 4 KiB entries) is taken from the operator\'s README %s %s.' % (
            S.term('contiguous hint'), _c('cont=64/64'), S.ref('run:C:dmesg.txt') + ' ' + S.ref('run:D:dmesg.txt'),
            _c('cont=0/64'), ' '.join(S.ref('run:%s:dmesg.txt' % k) for k in ('F1', 'E', 'B')),
            S.ref('readme:R3:37'), S.ref('readme:F1:82-83,89', 'the conditions of boot R3')),
        'Build and commands. The boots also differ in the benchmark build and in the command list (%s). Boots '
        'E and C run one build and the same %d commands in the same order. Boot D runs the %d commands of boot '
        'B in the same order on another build, with %d more commands at positions %d to %d. Boots F1 and R3 '
        'run another script, each on its own build. So two boots that differ in one condition can also differ '
        'in the build and in the commands that ran before a row. A comparison of two boots names the condition '
        'that was set on purpose. It does not prove that this condition alone causes a difference.' % (
            S.tabref('tab-TS2'), cmp_ec['n_a'], cmp_db['n_b'], len(cmp_db['extra']), cmp_db['extra'][0],
            cmp_db['extra'][-1]),
        'The operator compared the machine code of the builds. The loop of the latency test is the same '
        'instructions at the same place in their 64-byte lines in the builds of boots B, C, D, E and F1 '
        '(operator\'s README) %s %s. The read, write and copy loops of the bandwidth test are the same bytes in '
        'the builds of boots F1 and R3. In the build of boot R3 the loop of the latency test lies across two '
        '64-byte lines (operator\'s README) %s.' % (
            S.ref('readme:C:124', 'the loop of the latency test is the same instructions at the same place in '
                                  'their 64-byte lines in the builds of boots B, C and D'),
            S.ref('readme:E:8', 'boot E runs the program build, the OCM driver file and the commands of boot C. '
                                'Only the firmware that turns the L3 on is new, and the OCM is mapped in 4 KiB '
                                'entries'),
            S.ref('readme:F1:84', 'the machine code of the builds of boots F1, E and R3 compared')),
    ])
    if not (cmp_ec['same'] and cmp_ec['same_commit']) or cmp_db['same_commit'] \
            or cmp_db['extra'] != list(range(cmp_db['extra'][0], cmp_db['extra'][-1] + 1)) \
            or D.cmd_cmp[('F1', 'E')]['same_commit'] or D.cmd_cmp[('F1', 'R3')]['same_commit']:
        raise ValueError('sec_setup: the builds or the command lists of the boots are not as the text says')
    for k in ('F1', 'E', 'B'):
        assert D.boot[k]['map_cont'] == {'0/64': D.boot[k]['map_lines']}
    assert D.boot['R3']['map_cont'] is None
    b += S.fig(svg, 'The six boots and their three conditions. The small line in a cell is the evidence for that '
                    'boot.',
               'Only boot E has the three conditions of boot F1. Every other boot differs in one, two or three '
               'of them. Boot E runs another script and another benchmark build than boot F1.',
               id_='fig-S3',
               note='Register lines: %s. Mapping lines: %s %s. Boot R3 has neither, so its two cells are '
                    'taken from the operator\'s README %s.' % (
                        _c('log.txt'), _c('dmesg.txt'),
                        ' '.join(S.ref('run:%s:dmesg.txt' % k) for k in ('F1', 'E', 'B')),
                        S.ref('readme:F1:82-83,89', 'the conditions of boot R3')))

    # One column per boot, so that the folder names and the conditions fit the page width.
    def col(fn):
        return [fn(k, D.boot[k], D.integrity[k]) for k in BOOTS]

    def mapping_lines(k, bt, ig):
        if not bt['map_cont']:
            return 'no Linux boot log'
        (cont, n), = bt['map_cont'].items()
        return '%d, all %s' % (n, _c('cont=' + cont))

    def mesh_counter_rows(k):
        """(rows that shared a counter, rows) of the mesh events of a boot.  The two time rows of each
        command (elapsed time of the command and of the wrapper) are not counters."""
        ev = [r for r in D.cmn(k) if not r['event'].endswith('_elapsed_ns')]
        return sum(1 for r in ev if r['enabled_ns'] != r['running_ns']), len(ev)

    for k in BOOTS:
        assert D.boot[k]['cov_min'] == D.boot[k]['cov_max'] == 1.0 and D.integrity[k]['perf_lines'] == 0
    rows = [
        'Where the files are',
        ['Folder'] + col(lambda k, bt, ig: _NW % _c(bt['folder'])),
        ['Benchmark build'] + col(lambda k, bt, ig: _c(bt['commit'])),
        ['Script'] + col(lambda k, bt, ig: _c(bt['script'])),
        'Conditions',
        ['L3 of the test clusters'] + col(lambda k, bt, ig: bt['l3']),
        ['Hardware prefetchers'] + col(lambda k, bt, ig: bt['prefetchers']),
        ['OCM mapping'] + col(lambda k, bt, ig: bt['ocm_mapping']),
        'Integrity',
        ['Commands (core + CME)'] + col(lambda k, bt, ig: '%d (%d + %d)' % (bt['n_cmd'], bt['n_core'], bt['n_cme'])),
        ['Failed commands'] + col(lambda k, bt, ig: '%d' % bt['n_failed']),
        ['Checksums that match'] + col(lambda k, bt, ig: '%d of %d' % (bt['sha_ok'], bt['sha_total'])),
        ['Counted core rows with full coverage'] + col(
            lambda k, bt, ig: '%d of %d' % (bt['cov_rows'] - ig['cov_none'], bt['cov_rows'])),
        ['Best rows equal to the smallest or largest rep'] + col(
            lambda k, bt, ig: '%d of %d' % (ig['lat_best_ok'] + ig['bw_best_ok'], ig['lat_best_n'] + ig['bw_best_n'])),
        ['Mesh counter rows that shared a counter'] + col(lambda k, bt, ig: '%d of %d' % mesh_counter_rows(k)),
        ['Sources'] + col(lambda k, bt, ig: log_ref(k) + ' ' + S.ref('run:%s:SHA256SUMS' % k) + ' ' +
                          S.ref('readme:%s' % k)),
    ]
    b += S.table([''] + [D.boot[k]['name'] for k in BOOTS], rows,
                 caption='The boots: files, conditions and integrity checks. %s shows the evidence of each '
                         'condition.' % S.figref('fig-S3'),
                 note='Folder: under %s. Benchmark build: the short commit in line 1 of %s. A command is a line of '
                      '%s that starts with "+ ". Full coverage: %s reads 1.0000, so the counters ran for the whole '
                      'timed interval. Mesh counter rows: the rows of %s that hold a mesh event. '
                      'A counter is shared when it ran for a part of the command only.' % (
                          _c('results/'), _c('log.txt'), _c('log.txt'), S.term('perf_cov'), _c('cmn-counts.csv')),
                 id_='tab-TS2', align='lllllll')
    S.term('command')
    S.term('CME')

    # Rows taken from other boots.  Each "has no" statement is checked against the file list of boot F1.
    lat_headers = [blk['header'] for n in D.files['F1']['latency'] for blk in D.latblocks('F1', n)]
    assert all(h['events'] == 'prefetch' and int(h['seq']) == 0 for h in lat_headers)
    for name in ('latency-dram-small-l3.csv', 'latency-dram-seq.csv', 'bandwidth-read-prefetch.csv',
                 'bandwidth-l1-passes.csv', 'bandwidth-l1-asmpasses.csv', 'latency-ocm-region0-route-cpu2.csv'):
        assert not D.has('F1', name), name
    igf = D.integrity['F1']
    assert igf['bw_blocks_with_counters'] == 0
    f1_l1 = sorted(set(r['size'] for r in D.bw_1core if r['size'] <= 32 * KIB))
    assert len(f1_l1) == 1 and all(r['form'] == 'looped' for r in D.bw_1core)
    n_lat_cmd = len(lat_headers)
    t3 = [
        ['L3 hits per load (hit set), 64 KiB to 512 KiB chains', 'E', S.xref('lat-l3'),
         'All %d latency commands of boot F1 use the default counter set.' % n_lat_cmd],
        ['8 MiB chain in address order', 'E, C, B', S.xref('lat-order'),
         'No command of boot F1 walks a chain in address order.'],
        ['L1 forms: looped and single-call, 4 KiB to 24 KiB', 'E', S.xref('bw-l1forms'),
         'Boot F1 has one footprint inside the L1 (%s), in the looped form only.' % V.size_label(f1_l1[0])],
        ['Read variants with counters per 64 bytes', 'E, C, B', S.xref('bw-variants') + ', ' + S.xref('open-l3'),
         'Boot F1 has no such kernel and no counters on a bandwidth row.'],
        ['Every line of one OCM region, per CPU, with flit counts', 'B', S.xref('ocm-region'),
         'The per-region rows of boot F1 use one line per 4 KiB page.'],
        ['OCM rows with 64 KiB translations', 'B, D', S.xref('ocm-pagemap'),
         'Boot F1 maps the OCM with 4 KiB entries only.'],
        ['The commands of boot F1 with the L3 holding no data', 'R3', S.xref('open-l3'),
         'A boot cannot be its own control.'],
        ['Rows shared with boot F1, as a second sample', 'E', S.xref('glance-repeat'),
         'One boot gives no variation from boot to boot.'],
        ['8 MiB chain in random order with every line flushed first, beside the address-order chain', 'E, C, B',
         S.xref('lat-order'), 'Boot F1 has this row. Each address-order row is compared with the random-order '
                              'row of its own boot.'],
        ['Rows that check a counter event', 'B, C, D', S.tabref('tab-TS4'),
         'Boot F1 has one firmware state. A check needs a state where the event must read zero.'],
    ]
    b += S.table(['Row family', 'Boot', 'Used in', 'Why boot F1 has no such row'], t3,
                 caption='Rows taken from the other boots. A row of another boot is used only where boot F1 has '
                         'no row that measures the same thing, and the conditions of that boot stand next to the '
                         'number.',
                 id_='tab-TS3', align='llll')
    for t in ('hit set', 'address order', 'looped form', 'single-call form', 'plain read', 'TLB',
              'one line per 4 KiB page', 'every line'):
        S.term(t)
    return b


# ---------------------------------------------------------------------------------- 1.4 the latency test

def _latency(D, V, S, data):
    many = [r for r in D.lat_sweep if r['kind'] == 'walked many times']
    once = [r for r in D.lat_sweep if r['kind'] == 'walked once']
    fl = D.lat_flushed
    seq = D.lat_seq[0]
    cell = D.ocm_cells[0]
    all5_page = next(r for r in D.ocm_all5 if r['shape'] != 'every line')
    all5_every = next(r for r in D.ocm_all5 if r['shape'] == 'every line')
    ctrl = D.lat_cluster['control'][0]
    br = D.bracket
    ld = (min(r['loads'] for r in many), max(r['loads'] for r in many))
    ps = (int(min(r['passes'] for r in many)), int(max(r['passes'] for r in many)))
    nm, no, nf, ns_ = (sorted(set(r['n_reps'] for r in x)) for x in (many, once, [fl], [seq]))
    assert len(nm) == len(no) == len(nf) == len(ns_) == 1
    assert all(r['passes'] == 1 for r in once + [fl, seq])
    assert cell['loads'] == data.REGION_BYTES // 4096 and all5_every['loads'] == 5 * data.REGION_LINES

    w, g = 244, 14
    top = 8
    panels = [
        ('walked many times', ['one random chain', 'walked %d to %s times in a rep' % (ps[0], V.num(ps[1], 0)),
                               '%d reps' % nm[0]]),
        ('walked once', ['two untimed walks of a first chain', 'then another chain, one walk', '%d reps' % no[0]]),
        ('every line flushed first', ['every line removed from the caches', 'then one walk of another chain',
                                      '%d reps' % nf[0]]),
        ('address order', ['line i points to line i + 1', 'every line flushed first, one walk',
                           '%d reps (boots E, C, B)' % ns_[0]]),
    ]
    nodes = [dict(id='k%d' % i, x=4 + i * (w + g), y=top, w=w, h=92, title=t, lines=l)
             for i, (t, l) in enumerate(panels)]
    sy = 176
    strip = [
        ('s0', 'fill the buffer, build the chains', 140, 'soft'),
        ('s1', 'untimed walks', 96, 'soft'),
        ('s2', 'flush every line', 112, 'dashed'),
        ('s3', 'counters start', 96, 'plain'),
        ('s4', 'clock read', 84, 'plain'),
        ('s5', 'loads of one rep', 136, 'accent'),
        ('s6', 'clock read', 84, 'plain'),
        ('s7', 'counters stop', 96, 'plain'),
    ]
    x = 4
    pos = {}
    for i, (id_, t, bw, kind) in enumerate(strip):
        if id_ == 's3':
            x += 14
        if id_ == 's4':
            x += 8
        if id_ == 's7':
            x += 8
        pos[id_] = (x, bw)
        nodes.append(dict(id=id_, x=x, y=sy, w=bw, h=58, title=t, kind=kind,
                          lines=['two kinds only'] if id_ == 's2' else None))
        x += bw + 16
    arrows = [dict(src='s%d' % i, dst='s%d' % (i + 1)) for i in range(7)]
    x3, x4, x6, x7 = pos['s3'][0], pos['s4'][0], pos['s6'][0], pos['s7'][0]
    groups = [
        dict(x=x3 - 10, y=sy - 58, w=x7 + pos['s7'][1] + 10 - (x3 - 10), h=58 + 58 + 16,
             label='counted by the core counters'),
        dict(x=x4 - 8, y=sy - 30, w=x6 + pos['s6'][1] + 8 - (x4 - 8), h=30 + 58 + 8,
             label='timed interval: elapsed ns / loads = chain load'),
    ]
    svg = V.boxes(nodes, arrows, groups=groups, title='chain kinds and the timed interval')

    src_chain = S.ref('src:latency.c:105-137', 'how a chain is built')
    src_rep = S.ref('src:latency.c:201-222', 'one timed rep')
    src_best = S.ref('src:latency.c:240-259', 'the best row')
    b = S.h3('setup-latency-test', 'The latency test')
    b += S.bullets([
        'The %s builds a chain of pointers over a buffer. Each member line of 64 bytes holds the address of the '
        'next member. The members form one cycle. Its order is random, except in the chain kind "address order" '
        '%s.' % (
            S.term('latency test'), src_chain),
        'The address of each load is the data of the load before it. So a load starts only after the load '
        'before it has returned.',
        'One rep is one timed interval. It holds one walk of the chain, or several walks for the kind "walked '
        'many times". The %s is the elapsed time divided by the loads, in ns per load %s. The timer '
        'counts in units of 1 ns.' % (S.term('chain load'), src_rep),
        'The best row of a footprint is its smallest rep %s. The page quotes best rows, with the counters of '
        'the rep that has the best value.' % src_best,
        'There are four chain kinds (%s). A chain that is walked many times gets %s to %s loads per rep on '
        'boot F1. Every other kind gets one load per member.' % (
            S.figref('fig-S4'), V.num(ld[0], 0), V.num(ld[1], 0)),
        'Buffers in the memory of the DRAM model (%s buffers) use huge pages of 2 MiB. OCM chains have two '
        'shapes: "%s" (all %s lines of a region) and "%s" (%d lines of a region). Both flush every line first.' % (
            S.term('DRAM-backed'), S.term('every line'), V.num(data.REGION_LINES, 0), S.term('one line per 4 KiB page'), cell['loads']),
        'Each command also times two clock reads with no load between them (the %s). The median is %.0f ns on '
        'boot F1 (%d commands, %.0f to %.0f ns) %s. The program does not subtract it. On a row of %d loads that '
        'is %.2f ns per load est., and on a row of %d loads %.2f ns per load est. The counts of a %d-load row '
        'are multiples of 1/%d.' % (
            S.term('clock-read cost'), br['median'], br['n_cmd'], br['min'], br['max'],
            S.ref('file:F1:%s:%d' % (br['max_file'], br['max_line']), 'the largest clock-read cost'),
            cell['loads'], br['per_load_64_est'], all5_page['loads'], br['per_load_320_est'],
            cell['loads'], cell['loads']),
        'The %s is a 4 KiB chain on 4 KiB pages with %s loads. It runs once per CPU under the mesh counters %s. '
        'A difference from it is the measured difference between two loops.' % (
            S.term('background control'), V.num(ctrl['loads'], 0), _fref(S, ctrl, 'the background control of CPU 2')),
    ])
    b += S.fig(svg, 'Top: the four chain kinds. Bottom: the phases of one rep, left to right, with what the timer '
                    'and the counters cover. Schematic, not to scale.',
               'Only the loads and the two clock reads are inside the timed interval. The flush and the untimed '
               'walks are outside it and outside the counts.',
               id_='fig-S4',
               note='Source: %s %s. The flush phase exists for the kinds "every line flushed first" and "address '
                    'order".' % (_c('latency.c'), src_rep))
    for t in ('walked many times', 'walked once', 'every line flushed first', 'address order'):
        S.term(t)
    return b


# ---------------------------------------------------------------------------------- 1.5 the bandwidth test

def _bandwidth(D, V, S):
    doc = D.doc
    rows = D.bw_1core
    small = min(rows, key=lambda r: r['size'])
    big = max(rows, key=lambda r: r['size'])
    reps = sorted(set(r['n_reps'] for r in rows))
    assert len(reps) == 1
    ig = D.integrity['F1']
    cpu3 = D.platform['cpu3']
    cyc = D.cycles_per_ns
    assert doc['read_gbps'] == doc['read_bytes_per_cycle'] * cyc

    b = S.h3('setup-bandwidth-test', 'The bandwidth test')
    b += S.bullets([
        'The %s times whole passes of a fixed loop over a buffer. One iteration moves 256 bytes: 8 loads of '
        '32 bytes in the read loop, 8 stores of 32 bytes in the write loop %s. The copy loop runs both.' % (
            S.term('bandwidth test'), S.ref('src:bandwidth.c:138-141,188-191,240-247', 'the read, write and copy loops')),
        'A rep is one untimed pass and then the timed interval with all its passes. On boot F1 a rep holds '
        '%d passes at %s and %d passes at %s. Each command of the one-core sweep runs %d reps %s.' % (
            small['passes'], small['label'], big['passes'], big['label'], reps[0],
            S.ref('src:bandwidth.c:398-449', 'how a rep is timed')),
        'The rate is the bytes transferred divided by the elapsed time, in %s (1e9 bytes per second). A copy '
        'counts the bytes read plus the bytes written %s.' % (
            S.term('GB/s'), S.ref('src:bandwidth.c:341', 'the byte count of a copy')),
        'The best row is the largest rep %s.' % S.ref('src:bandwidth.c:573-616', 'the best row'),
        'Bandwidth is loop throughput. The timed interval holds the loop and, in the %s, one call of the loop '
        'per pass. So the page never gives a time for one load or one store. It gives "%s": 128 divided by the '
        'rate in GB/s, at %.1f cycles per ns.' % (
            S.term('looped form'), S.term('effective cycles per 64 bytes transferred'), cyc),
        'Documented instruction throughput (%s): %.0f bytes per cycle for the read loop and %.0f bytes per cycle '
        'for the write loop %s. At %.1f cycles per ns that is %.0f GB/s and %.0f GB/s.' % (
            S.term('SOG'), doc['read_bytes_per_cycle'], doc['write_bytes_per_cycle'], S.ref('doc:sog'), cyc,
            doc['read_gbps'], doc['write_gbps']),
        'Rows of 2 MiB and more use buffers larger than the caches of one cluster. These rows are %s: their '
        'buffers are in memory that the DRAM model backs. The DRAM model is an emulator memory with zero '
        'configured delay, not silicon timing (operator\'s README) %s. The page does not name the DRAM model '
        'as the level that serves these rows.' % (S.term('DRAM-backed'), S.ref('readme:F1:247,354')),
        'None of the %d bandwidth files of boot F1 has core counters. CPU 3 is offline during the latency rows '
        'and the one-core rows, and online for the multi-core rows %s.' % (
            ig['n_bandwidth_files'],
            S.ref('file:F1:log.txt:%s' % ','.join('%d' % c['line'] for c in cpu3[:2]),
                  'CPU 3 goes offline and comes back online')),
    ])
    assert [c['online'] for c in cpu3[:2]] == [0, 1] and ig['bw_blocks_with_counters'] == 0
    b += S.insufficient(
        'How the timed lines of a 2 MiB row split between SLC hits and fills by the DRAM model. A 2 MiB buffer '
        'is under the 3.75 MiB est. that the SLC has for DRAM lines (operator\'s README) %s. The mesh counts '
        'cover the whole command with its buffer fill and its untimed passes, not the timed passes (operator\'s '
        'README) %s. Counters that separate the two sources inside the timed interval would resolve it.' % (
            S.ref('readme:R3:34', 'the SLC size that is left for DRAM lines'),
            S.ref('readme:F1:144', 'the one-core read rows carry no core counters, the mesh counters cover the '
                                   'whole command, and no file shows why the reads are faster with the L3 on')))
    return b


# ---------------------------------------------------------------------------------- 1.6 counters, clock, integrity

def _counters(D, V, S):
    ck = _event_checks(D)
    hc = D.lat_hit_check
    ms = D.mesh_summary
    clk = D.clock['F1']
    f1 = D.boot['F1']
    ig = D.integrity['F1']
    P = D.platform
    fl = D.ocm_fit['flits']['B']
    nb = [hc['boots'][k]['n_rows'] for k in ('B', 'C', 'D')]
    assert len(set(nb)) == 1 and all(hc['boots'][k]['l3hit_max'] == 0 for k in ('B', 'C', 'D'))
    assert ck['pf_off_max'] == 0 and ck['l2pf_off_max'] < 0.00005
    assert ms['own_highest'] == ms['n_one_region']
    ident = max(hc['id_access_max'], hc['id_l1_max'])
    two = S.term('checked in two states')
    ex = S.term('exploratory')
    pf_status = ('%s: %.4f on every latency row of boots B and D (prefetchers off), %s per load on the '
                 'address-order chain of boots E and C (prefetchers on)' % (
                     two, ck['pf_off_max'], _rng(*ck['pf_seq'])))

    rows = [
        'Core counters, per load in latency files and per 64 bytes transferred in bandwidth files',
        ['cycle counter', 'CPU_CYCLES', 'cycles', 'core clock cycles in user mode',
         'gives %.3f cycles per ns against the timer' % clk['pooled']],
        [_c('0x03'), 'L1D_CACHE_REFILL', 'L1 refills', 'lines brought into the L1 data cache',
         'not checked in a state where the event must read zero. The counts rise from 0 to 1 at the cache '
         'sizes (%s)' % S.xref('lat-levels')],
        [_c('0x17'), 'L2D_CACHE_REFILL', 'L2 refills', 'every line brought into the L2, prefetch fills included',
         'as above'],
        [_c('0xA2'), 'L3D_CACHE_REFILL_RD', 'L3 read refills', 'L3 fills from outside the cluster caused by a read',
         'does not count the prefetch fills of loads in address order: %.4f per load on the address-order '
         'chain of boot E' %
         ck['a2_seq_e']],
        [_c('0x81BC'), 'L1D_CACHE_REFILL_HWPRF', 'L1 prefetch refills', 'L1 refills that a prefetcher asked for',
         pf_status],
        [_c('0x0111'), 'IMP_L2D_CACHE_REFILL_L1DHWPRF', 'L2 refills by the L1 prefetcher',
         'L2 refills caused by requests of the L1 prefetcher', 'as 0x81BC'],
        [_c('0x81BD'), 'L2D_CACHE_REFILL_HWPRF', 'L2 prefetch refills', 'L2 refills by the prefetchers that fill the L2',
         '%s: %s per load at 192 KiB to 384 KiB with the prefetchers on (boots F1, E, C), %.4f with them off '
         '(boots B, D)' % (two, _rng(ck['l2pf_on'][0], ck['l2pf_on'][1], 2), ck['l2pf_off_max'])],
        [_c('0x81C5') + ', ' + _c('0xA0') + ', ' + _c('0x81C6'), 'L2D_CACHE_HIT_RD, L3D_CACHE_RD, L3D_CACHE_HIT_RD',
         'L2 hits, L3 accesses, L3 hits (the hit set)', 'demand reads that hit the L2, reach the L3, hit the L3',
         '%s, with three consistency checks. L1 refills = L2 hits + L3 accesses, and L3 accesses = L3 hits + '
         'L3 read refills, within %.4f per load (%s). The L3 hits read %.4f in all %d rows of each of boots B, C, '
         'D (the L3 holds no data)' % (ex, ident, S.xref('lat-l3'), 0.0, nb[0])],
        [_c('0x05'), 'L1D_TLB_REFILL', 'L1 TLB refills', 'refills of the first-level cache of translations', ex],
        'Mesh counters, over the whole life of one command',
        [_NW % _c('hns_pocq_reqs_recvd_all'), '-', 'requests received', 'requests that one home node received',
         'checked by the one-region commands: the own node counts most in %d of %d' % (
             ms['own_highest'], ms['n_one_region'])],
        [_NW % _c('hns_mc_reqs_local_all'), '-', 'requests sent on to memory',
         'requests that the home nodes passed to the memory controller', ex],
        [_NW % _c('hns_cache_miss_all'), '-', 'SLC misses', 'misses in the SLC, summed over the home nodes', ex],
        [_NW % _c('mxp_{e,w,n,s}_dat_txflit_valid'), '-', 'data flits sent',
         'data flits that a crosspoint sent in each of four directions (boot B, %d commands)' % fl['n'], ex],
    ]
    b = S.h3('setup-counters', 'Counters, clock, integrity')
    b += S.bullets([
        'Core counters. Each test thread counts cycles and six events in user mode. The counters start just '
        'before the first clock read and stop just after the second %s.' % S.ref(
            'src:common.h:253,327-339', 'the counter group and the default event set'),
        'A count is printed per load or per 64 bytes transferred. It is an aggregate. It does not give the '
        'history of each line, and a %s count includes prefetch fills.' % S.term('refill'),
        'Mesh counters. A wrapper counts mesh events over the whole life of a command: program start, buffer '
        'fill, untimed walks, flushes and timed reps %s. So the page gives mesh counts per command only.' % S.ref(
            'src:cmncount.c:1-40', 'what a mesh count covers'),
        'Clock. The cycle counter and the timer give %.3f cycles per ns on boot F1. The value is the sum of the '
        'cycles over the sum of the ns of the %d timed rows of at least %s loads. The single rows read %.4f to '
        '%.4f cycles per ns. The timer runs at %.0f MHz %s. So the core clock is 2.0 GHz in the time of the '
        'emulated chip.' % (
            clk['pooled'], clk['n_rows'], V.num(clk['min_loads'], 0), clk['min'], clk['max'], P['timer']['value'],
            S.ref('run:F1:dmesg.txt:%d' % P['timer']['line'], 'the timer frequency')),
        'Integrity. On boot F1 %d commands ran (%d core, %d CME) and %d failed %s. The CME rows are on a separate '
        'page. Every check of boot F1 passes: the checksums, the counter coverage (%s), the best rows and the '
        'mesh counter rows (%s).' % (
            f1['n_cmd'], f1['n_core'], f1['n_cme'], f1['n_failed'],
            S.ref('file:F1:log.txt:%s' % ','.join('%d' % x for x in f1['done_lines']),
                  'the two lines that count the failed commands'),
            S.term('perf_cov'), S.tabref('tab-TS2')),
    ])
    assert f1['sha_ok'] == f1['sha_total'] and f1['cov_min'] == 1.0
    assert ig['lat_best_ok'] == ig['lat_best_n'] and ig['bw_best_ok'] == ig['bw_best_n']
    b += S.table(['Event', 'Arm name', 'Name on this page', 'What it counts', 'Status'], rows,
                 caption='The counter events that the page uses, and how far each one is checked.',
                 note='%s defines the status words. Full coverage does not prove that an event counts what its '
                      'name says. Sources: %s %s, hit set rows %s, mesh counts %s.' % (
                          S.xref('words', cap=True), _c('common.h'), S.ref('src:common.h:327-339,346-348,383-385'),
                          S.ref('file:E:latency-dram-small-l3.csv'), S.ref('file:F1:cmn-counts.csv')),
                 id_='tab-TS4', align='lllll')
    for t in ('hit set', 'L3 read refill', 'requests received', 'requests sent on to memory', 'TLB', 'demand read',
              'L2 prefetch refills', 'L2 refills by the L1 prefetcher'):
        S.term(t)
    assert ig['cmn_multiplexed'] == 0 and ig['cov_none'] == 0
    return b


def build(D, V, S):
    from . import data
    b = _chip(D, V, S)
    b += _mesh(D, V, S, data)
    b += _boots(D, V, S)
    b += _latency(D, V, S, data)
    b += _bandwidth(D, V, S)
    b += _counters(D, V, S)
    return b
