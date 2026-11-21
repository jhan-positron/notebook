"""Section 5 of asimov-c1nano-perf.html: multi-core DRAM bandwidth and writer placement.

Every measured number comes from the data layer D (boot F1) at build time.
Values derived here (not in D): see _derived().
"""

import math

KEY = 'multicore'
TITLE = 'Multi-core bandwidth'

KERNELS = ('read', 'write', 'copy')
KCOLOR = {'read': 'f1', 'write': 'c', 'copy': 'alt'}
CLUSTERS = ((2, 3), (4, 5), (6, 7), (8, 9))
MIB = 1024 * 1024
KIB = 1024


def _cite(S, rows, text):
    """One [RefN] per file of the rows, with the timed rows that carry the best values."""
    by = {}
    for r in rows:
        by.setdefault(r['file'], []).append(r['line'])
    return ''.join(S.ref('file:F1:%s:%s' % (f, ','.join(str(n) for n in sorted(set(ls)))), text)
                   for f, ls in by.items())


def _derived(D):
    """Values that the data layer does not hold, computed from its rows."""
    d = {}
    mc = {(r['group'], r['kernel'], r['size']): r for r in D.mc_rows}
    d['mc'] = mc
    # largest thread minus smallest thread of the best rep, over the largest, in percent
    d['thr_gap'] = {k: (r['thr_max'] - r['thr_min']) / r['thr_max'] * 100.0 for k, r in mc.items()}
    wr = {r['cpus_label']: r for r in D.mc_writers}
    d['wr'] = wr
    d['wr_gap'] = {k: (r['thr_max'] - r['thr_min']) / r['thr_max'] * 100.0 for k, r in wr.items()}
    # the counted control row (writer placement command) against the one-core-per-cluster write row at
    # 16 MiB, which runs without the mesh counters and with other pass and rep counts
    unc = mc[('one core per cluster', 'write', 16 * MIB)]
    d['unc'] = unc
    d['ctrl_vs_uncounted_pct'] = (unc['agg'] - wr['2,4,6,8']['agg']) / unc['agg'] * 100.0
    d['four_over_two'] = wr['2,4,6,8']['agg'] / wr['2,4']['agg']
    shares = [s for r in D.mc_writers for s in r['shares']]
    d['share'] = (min(shares), max(shares))
    est = [r['mc_net_per_line_pass_est'] for r in D.mc_writers]
    d['mc_est'] = (min(est), max(est))
    sums2 = [r['node_sum'] for r in D.mc_writers if r['threads'] == 2]
    sums4 = [r['node_sum'] for r in D.mc_writers if r['threads'] == 4]
    d['sum2'], d['sum4'] = (min(sums2), max(sums2)), (min(sums4), max(sums4))
    d['gap_2389_pct'] = (1.0 - D.mc_writers_summary['r2389_over_2345']) * 100.0
    # each thread of the one-core-per-cluster rows at 2 MiB against the one-core rate, in percent
    d['thr_vs_one'] = {}
    for k in KERNELS:
        r = mc[('one core per cluster', k, 2 * MIB)]
        d['thr_vs_one'][k] = ((r['thr_min'] / r['one_core'] - 1.0) * 100.0,
                              (r['thr_max'] / r['one_core'] - 1.0) * 100.0)
    return d


def _passes_reps(r):
    return '%d pass%s, %d rep%s' % (r['passes'], '' if r['passes'] == 1 else 'es',
                                    r['n_reps'], '' if r['n_reps'] == 1 else 's')


def _thr_range(lo, hi):
    """Range of the threads against the one-core rate, as text."""
    worst = max(abs(lo), abs(hi))
    if worst < 0.05:
        return 'within %.2f %%' % (math.ceil(worst * 100.0) / 100.0)
    return '%+.1f to %+.1f %%' % (lo, hi)


def _fig_m1(D, V, d):
    size = 2 * MIB
    rows = []
    for k in KERNELS:
        one = D.one_core(k, size)
        rows.append(dict(header='%s, 2 MiB per thread' % k.capitalize()))

        def vals(v, k=k):
            return [v if kk == k else None for kk in KERNELS]
        rows.append(dict(label='1 core', sub='CPU 2', values=vals(one['best']), tick=one['best']))
        for group, label, sub in (('one core per cluster', '4 cores', 'CPUs 2, 4, 6, 8: one per cluster'),
                                  ('all eight cores', '8 cores', 'CPUs 2 to 9: two per cluster')):
            r = d['mc'][(group, k, size)]
            rows.append(dict(label=label, sub=sub, values=vals(r['agg']), tick=r['threads'] * one['best'],
                             note='%s, %s' % (V.ratio(r['scaling']), V.pct(r['efficiency'] * 100.0))))
    return V.dot_rows(rows, [dict(name=k, color=KCOLOR[k]) for k in KERNELS], unit='GB/s',
                      fmt=lambda v: V.num(v, 1), xlabel='aggregate rate, GB/s', xrange=(0, None),
                      tick_name='cores x the one-core rate', labels='all', label_w=250)


def _fig_m2(D, V, d):
    rows = []
    for n in (2, 4):
        rows.append(dict(header='%s writers, 16 MiB each' % ('Two' if n == 2 else 'Four')))
        for r in D.mc_writers:
            if r['threads'] != n:
                continue
            chips = []
            for cl in CLUSTERS:
                on = [c for c in cl if c in r['cpus']]
                chips.append((','.join(str(c) for c in on) if on else '-', bool(on)))
            if r['is_control']:
                note = 'control'
            else:
                note = '%s%s' % ('one cluster: ' if r['clusters'] == 1 else '', V.ratio(r['ratio_control']))
            rows.append(dict(label='CPUs %s' % r['cpus_label'].replace(',', ', '),
                             sub='%d per cluster' % r['cores_per_cluster'], values=[r['agg']], note=note,
                             chips=chips))
    return V.stacked_hbar(rows, [('16 MiB write, all threads', 'f1')], unit='GB/s', fmt=lambda v: V.num(v, 1),
                          xlabel='aggregate rate, GB/s', total=False, label_w=200,
                          chip_name='cluster with a writing core (the CPUs that write)')


def build(D, V, S):
    d = _derived(D)
    mc, wr = d['mc'], d['wr']
    ws = D.mc_writers_summary
    n3 = lambda v: V.num(v, 3)
    for t in ('cluster', 'GB/s', 'spread', 'best row', 'DRAM model', 'footprint', 'home node', 'mesh',
              'bandwidth test', 'requests received', 'requests sent on to memory', 'exploratory', 'SOG',
              "operator's README", 'est.', 'rep', 'pass'):
        S.term(t)
    for t in ('aggregate rate', 'scaling', 'efficiency', 'kernel'):
        S.term(t)

    two, eight = 2 * MIB, 16 * MIB
    pc = {k: mc[('one core per cluster', k, two)] for k in KERNELS}
    a8 = {k: mc[('all eight cores', k, two)] for k in KERNELS}
    sc4 = [pc[k]['scaling'] for k in KERNELS]
    gain = {(g['kernel'], g['size']): g['gain_pct'] for g in D.mc_second_core}
    gains = sorted(gain.values())
    readme_dram = S.ref('readme:F1:247,354', 'the DRAM is an emulator memory model with every delay control at zero')
    readme_l3 = S.ref('readme:F1:74', 'the run-time reading of the L3 status register covers the cluster of CPU 2 only')
    src_agg = S.ref('src:bandwidth.c:573-590', 'the aggregate rate is the total bytes over the longest elapsed '
                                               'time of a thread, and the best row is the largest rep')

    out = ''

    # ---------------------------------------------------------------- 5.1
    out += S.h3('mc-clusters', 'One core per cluster, all eight')
    out += S.p(
        f'The {S.term("bandwidth test")} runs one thread per listed CPU, each with its own buffer. The aggregate '
        f'rate is the bytes of all threads divided by the elapsed time of the slowest thread {src_agg}. Scaling '
        f'is the aggregate rate divided by the one-core rate of the same kernel (read, write or copy) and '
        f'footprint ({S.xref("bw-1core")}). Efficiency is the scaling divided by the number of cores.')
    r8w = a8['write']
    out += S.fig(
        _fig_m1(D, V, d),
        'Aggregate rate of 1, 4 and 8 cores at 2 MiB per thread, boot F1. The grey tick is the number of cores '
        'times the one-core rate. The bold text is the scaling and the efficiency.',
        f'One core per cluster reaches the grey tick. Eight cores reach {a8["read"]["efficiency"] * 100:.0f} % '
        f'(read), {a8["write"]["efficiency"] * 100:.0f} % (write) and {a8["copy"]["efficiency"] * 100:.0f} % '
        f'(copy) of it.',
        id_='fig-M1',
        note='Files <code>bandwidth-dram-1core.csv</code>, <code>bandwidth-perdsu.csv</code>, '
             '<code>bandwidth-all8.csv</code>. A copy counts the bytes read plus the bytes written. The DRAM '
             'model is an emulator memory (operator\'s README).')
    tvo = d['thr_vs_one']
    thr_worst = math.ceil(max(abs(v) for pair in tvo.values() for v in pair) * 10.0) / 10.0
    out += S.bullets([
        f'With one core per cluster, four cores scale {min(sc4):.3f} to {max(sc4):.3f} times at 2 MiB '
        f'{_cite(S, list(pc.values()), "one core per cluster, best reps")}. Each thread of the best rep runs within '
        f'{thr_worst:.1f} % of the one-core rate (read {_thr_range(*tvo["read"])}, write '
        f'{_thr_range(*tvo["write"])}, copy {_thr_range(*tvo["copy"])}).',
        f'The second core of each cluster adds {gain[("read", two)]:.1f} % and {gain[("read", eight)]:.1f} % '
        f'(read, 2 MiB and 16 MiB), {gain[("copy", two)]:.1f} % and {gain[("copy", eight)]:.1f} % (copy), '
        f'{gain[("write", two)]:.1f} % and {gain[("write", eight)]:.1f} % (write) '
        f'{_cite(S, [mc[(g, k, eight)] for g in ("one core per cluster", "all eight cores") for k in KERNELS], "the 16 MiB rows, best reps")}.',
        f'All eight cores write {n3(r8w["agg"])} GB/s at 2 MiB, {r8w["scaling"]:.3f} times one core '
        f'{_cite(S, list(a8.values()), "all eight cores, best reps")}. It is the highest aggregate rate of any '
        f'row. It is not a measured limit of the mesh or of the DRAM model.',
        f'The eight write threads are unequal. The slowest thread is {d["thr_gap"][("all eight cores", "write", two)]:.1f} % '
        f'(2 MiB) and {d["thr_gap"][("all eight cores", "write", eight)]:.1f} % (16 MiB) below the fastest. The file '
        f'gives the rate of the slowest thread and of the fastest thread only, not the CPU of each.',
    ])
    out += S.callout(
        f'The rows of {S.tabref("tab-TM1")} and {S.tabref("tab-TM2")} use 2 MiB or 16 MiB per thread, more than '
        f'the caches of one cluster hold. These rows are DRAM-backed. The DRAM model is an emulator memory '
        f'with zero configured delay, not silicon timing (operator\'s README) {readme_dram}. No counter inside '
        f'the timed interval separates an SLC hit from a fill by the DRAM model, so the split of a 2 MiB row '
        f'between the two is not known ({S.xref("setup-bandwidth-test")}). A write rate is the rate at '
        f'which the store loop runs. No write row waits for the lines to reach the DRAM model. The L3 status '
        f'register is read on the cluster of CPU 2 only (operator\'s README) {readme_l3}. So no reading '
        f'confirms the L3 state for a row that uses CPUs 4 to 9.',
        title='Limits of these rows')

    rows = []
    for group in ('one core per cluster', 'all eight cores'):
        rows.append('%s (%s)' % (group.capitalize(), 'CPUs 2, 4, 6, 8' if group.startswith('one') else 'CPUs 2 to 9'))
        for size in (two, eight):
            for k in KERNELS:
                r = mc[(group, k, size)]
                rows.append([
                    r['label'], k, n3(r['agg']), '%s to %s' % (n3(r['thr_min']), n3(r['thr_max'])),
                    n3(r['per_cluster']), V.num(r['spread_pct'], 3),
                    n3(r['one_core']) if r['one_core'] else 'no row',
                    V.num(r['scaling'], 3) if r['scaling'] else 'n/a',
                    V.num(r['efficiency'] * 100.0, 1) if r['efficiency'] else 'n/a',
                    ('+%.1f' % gain[(k, size)]) if group.startswith('all') else '',
                ])
    out += S.table(
        ['Footprint', 'Kernel', 'Aggregate,<br>GB/s', 'Threads,<br>GB/s', 'Per cluster,<br>GB/s', 'Spread,<br>%',
         'One core,<br>GB/s', 'Scaling', 'Efficiency,<br>%', 'Second core,<br>%'],
        rows, caption='Four and eight cores at 2 MiB and 16 MiB per thread, boot F1, best reps.',
        note='Footprint is per thread. Threads: the rate of the slowest thread and of the fastest thread in the '
             'best rep. Per '
             'cluster = aggregate / 4. Scaling is in times the one-core rate. Boot F1 has no one-core row at '
             '16 MiB, so those rows have no scaling. "Second core" compares the all-eight row with the '
             'one-core-per-cluster row of the same kernel and footprint.',
        id_='tab-TM1', align='llrrrrrrrr')
    out += S.insufficient(
        'Whether two readers or two copy threads in one cluster are limited when the other clusters are idle. '
        'Measurement: two readers on CPUs 2 and 3 against CPUs 2 and 4 at 16 MiB (%s).' % S.xref('open-items'))

    # ---------------------------------------------------------------- 5.2
    out += S.h3('mc-writers', 'Writer placement')
    w23, w24, w28 = wr['2,3'], wr['2,4'], wr['2,8']
    w4, w2345, w2389 = wr['2,4,6,8'], wr['2,3,4,5'], wr['2,3,8,9']
    out += S.p(
        f'Six commands place two or four writers on chosen CPUs. Each writer stores to 16 MiB once per rep, and '
        f'each command has two reps. The rows show a limit per cluster for writes.')
    out += S.fig(
        _fig_m2(D, V, d),
        'Aggregate write rate by placement of the writers, boot F1. The four boxes are the four clusters. A '
        'filled box names the CPUs that write. The bold text is the ratio to the control row of the group.',
        f'Two writers in one cluster reach {w23["ratio_control"]:.2f} times the rate of two writers in two '
        f'clusters. With one writer per cluster, the position of the second cluster on the mesh makes no '
        f'difference ({w24["agg"]:.1f} against {w28["agg"]:.1f} GB/s). With two writers per cluster, CPUs 2, 3, '
        f'8, 9 read {d["gap_2389_pct"]:.1f} % below CPUs 2, 3, 4, 5 (unexplained, {S.xref("open-items")}).',
        id_='fig-M2',
        note='Files <code>bandwidth-write-cpus*.csv</code>. The control row of a group has one writer per '
             'cluster. A control row is a separate measurement. The DRAM model is an emulator memory (operator\'s '
             'README).')
    sp24, sp28 = '%.3f' % w24['spread_pct'], '%.3f' % w28['spread_pct']
    sp2 = ('%s %% each' % sp24) if sp24 == sp28 else ('%s %% and %s %%' % (sp24, sp28))
    out += S.bullets([
        f'Position on the mesh: CPUs 2 and 4 give {n3(w24["agg"])} GB/s and CPUs 2 and 8 give {n3(w28["agg"])} GB/s '
        f'{_cite(S, [w24, w28], "two writers in two clusters, best rep")}. The spread of the two rows is {sp2}.',
        f'Same cluster: CPUs 2 and 3 give {n3(w23["agg"])} GB/s, {w23["ratio_control"]:.3f} times the control '
        f'{_cite(S, [w23], "two writers in one cluster, best rep")}. Its two threads move {n3(w23["thr_min"])} and '
        f'{n3(w23["thr_max"])} GB/s.',
        f'Four writers: one per cluster gives {n3(w4["agg"])} GB/s, {d["four_over_two"]:.3f} times the two-writer '
        f'control. Two full clusters give {n3(w2345["agg"])} GB/s (CPUs 2, 3, 4, 5: {w2345["ratio_control"]:.3f} '
        f'times) and {n3(w2389["agg"])} GB/s (CPUs 2, 3, 8, 9: {w2389["ratio_control"]:.3f} times) '
        f'{_cite(S, [w4, w2345, w2389], "four writers, best rep")}.',
        f'A cluster with one writer writes {ws["per_cluster_one_writer"][0]:.3f} to '
        f'{ws["per_cluster_one_writer"][1]:.3f} GB/s in every row. A cluster with two writers writes '
        f'{ws["per_cluster_two_writers"]["one cluster busy"]:.1f} GB/s (one cluster busy), '
        f'{ws["per_cluster_two_writers"]["two clusters busy"][0]:.1f} and '
        f'{ws["per_cluster_two_writers"]["two clusters busy"][1]:.1f} GB/s (two busy). With four clusters busy '
        f'it writes {mc[("all eight cores", "write", eight)]["per_cluster"]:.1f} GB/s at 16 MiB and '
        f'{r8w["per_cluster"]:.1f} GB/s at 2 MiB. These two values are the aggregate rate divided by 4. The '
        f'aggregate rate uses the time of the slowest thread, and the file does not give the rate of each '
        f'cluster. Two differences '
        f'are not explained: the rate per cluster with two writers changes with the number of busy clusters, '
        f'and CPUs 2, 3, 8, 9 read {d["gap_2389_pct"]:.1f} % below CPUs 2, 3, 4, 5 ({S.xref("open-items")}).',
        f'The four-writer control (CPUs 2, 4, 6, 8) runs under the mesh counters ({_passes_reps(w4)}) and reads '
        f'{n3(w4["agg"])} GB/s. The one-core-per-cluster write row at 16 MiB runs without the mesh counters '
        f'({_passes_reps(d["unc"])}, {S.tabref("tab-TM1")}) and reads {n3(d["unc"]["agg"])} GB/s. The control '
        f'is {d["ctrl_vs_uncounted_pct"]:.3f} % below it. This is the measured difference between two loops. '
        f'It does not show that the counters disturb the rate.',
    ])
    cmn = S.ref('file:F1:cmn-counts.csv:%d-%d' % (min(r['mesh_line'] for r in D.mc_writers),
                                                 max(r['mesh_node_lines'][1] for r in D.mc_writers) + 3),
                'the mesh counts of the six writer placement commands')
    out += S.p(
        f'The mesh counters cover the whole command, not only the timed passes. Each home node receives '
        f'{d["share"][0]:.2f} to {d["share"][1]:.2f} % of the requests of a command, for every placement of the '
        f'writers {cmn}. The count of requests sent on to memory is an exploratory event. The page subtracts '
        f'the count of the background control from the count of the command. The rest is '
        f'{d["mc_est"][0]:.2f} to {d["mc_est"][1]:.2f} requests est. per line and pass of the whole command. '
        f'It is an estimate: the pass count comes from the source, not from the file.')
    rows = []
    for n in (2, 4):
        rows.append('%s writers' % ('Two' if n == 2 else 'Four'))
        for r in D.mc_writers:
            if r['threads'] != n:
                continue
            rows.append([
                r['cpus_label'], str(r['clusters']), n3(r['agg']),
                '%s to %s' % (n3(r['thr_min']), n3(r['thr_max'])), n3(r['per_cluster']),
                V.num(r['spread_pct'], 3), 'control' if r['is_control'] else V.num(r['ratio_control'], 3),
                V.num(r['node_sum'], 0), V.num(r['mc'], 0), V.num(r['mc_net_per_line_pass_est'], 2),
            ])
    out += S.table(
        ['CPUs', 'Clusters', 'Aggregate,<br>GB/s', 'Threads,<br>GB/s', 'Per cluster,<br>GB/s', 'Spread,<br>%',
         'Ratio to<br>control', 'Requests<br>received', 'Sent on to<br>memory', 'Sent on,<br>est.'],
        rows, caption='Writer placement rows: write, 16 MiB per thread, 1 pass, 2 reps, boot F1.',
        note='Clusters = clusters with a writer. Threads: the rate of the slowest thread and of the fastest '
             'thread in the best rep. '
             'The last three columns cover the whole command. "Requests received" sums the five home nodes. '
             '"Sent on to memory" is an exploratory event. "Sent on, est." is that count minus the count of '
             'the background control, per line and pass.',
        id_='tab-TM2', align='lrrrrrrrrr', highlight=lambda i, r: r[6] != 'control' and float(r[6]) < 0.9)
    p48, p160 = mc[('pair', 'write', 48 * KIB)], mc[('pair', 'write', 160 * KIB)]
    out += S.p(
        f'Two writers on CPUs 2 and 3 write {n3(p48["agg"])} GB/s at {p48["label"]} per thread '
        f'({p48["scaling"]:.3f} times one core) and {n3(p160["agg"])} GB/s at {p160["label"]} per thread '
        f'{S.ref("file:F1:bandwidth-pair.csv:%d,%d" % (p48["line"], p160["line"]), "two writers on CPUs 2 and 3 at 48 KiB and at 160 KiB, best reps")}. '
        f'Both footprints fit the L2 and the L3 of the cluster. At 16 MiB per thread the same two CPUs write '
        f'{n3(w23["agg"])} GB/s. So the lower rate appears only at a footprint that the cluster cannot hold. '
        f'No per-thread core counter exists for a two-thread row: the bandwidth test counts with one thread '
        f'only {S.ref("src:bandwidth.c:19", "the counter option works with one thread only")}.')
    out += S.hyp(
        'The path that carries lines out of the cluster limits the write rate of the cluster. That path is the '
        'one mesh port of the cluster, or the move of lines from the L3 to the home nodes. The two cores share '
        'one L2, one L3 and one mesh port (operator\'s README) %s.' % S.ref(
            'readme:F1:346', 'each pair of CPUs shares an L2, an L3 and one mesh port'),
        'The write row of CPUs 2 and 3 at 384 KiB, 1 MiB and 2 MiB per thread, each under the mesh counters. '
        'It would show the footprint where the rate falls, and whether the requests received per second stop '
        'rising there.')

    # The subsection on the pair at small footprints is cut (critic sheet, cut order).  One fact stays.
    p16 = [mc[('pair', k, 16 * KIB)] for k in KERNELS]
    s16 = [r['scaling'] for r in p16]
    out += S.p(
        f'The two cores of a cluster also share the vector unit ({S.term("SOG")}, section 3.12) '
        f'{S.ref("doc:sog")}. It is not this limit: CPUs 2 and 3 together scale {min(s16):.2f} to {max(s16):.2f} '
        f'times at 16 KiB per thread with the same instructions '
        f'{S.ref("file:F1:bandwidth-pair.csv:%s" % ",".join(str(r["line"]) for r in p16), "the pair at 16 KiB, best reps")}.')
    return out
