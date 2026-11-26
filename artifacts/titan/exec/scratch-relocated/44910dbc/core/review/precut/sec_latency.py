"""Section 3 of asimov-c1nano-perf.html: latency by footprint.

build(D, V, S) returns the html of the section body (the generator writes the h2).
Every measured number is read from the data layer D at build time.  Typed values are
test parameters (footprints) and facts of the operator's README, which carry a reference.
"""

KEY = 'latency'
TITLE = 'Latency by footprint'

KIB, MIB = 1024, 1024 * 1024

# Typed facts, operator's README (not measurements).  Each use carries a reference.
SLC_TOTAL_BYTES = 5 * MIB           # five home nodes of 1 MiB
SLC_WAYS, OCM_WAYS = 16, 4          # ways of a home node, ways locked as OCM
SLC_EST_BYTES = SLC_TOTAL_BYTES * (SLC_WAYS - OCM_WAYS) // SLC_WAYS

SMALL, LARGE, FLUSHED = 'latency-dram-small.csv', 'latency-dram-large.csv', 'latency-dram-flushed.csv'
HITS, SEQ = 'latency-dram-small-l3.csv', 'latency-dram-seq.csv'

# Footprints with a direct label in figure L1 (test parameters).
LABELLED = [4 * KIB, 128 * KIB, 384 * KIB, 2 * MIB, 32 * MIB]
# Legend names of the boots (API part 3).
LEGEND = {'E': 'boot E (L3 on, prefetchers on)', 'C': 'boot C (the L3 holds no data, prefetchers on)',
          'B': 'boot B (the L3 holds no data, prefetchers off)'}
COLOR = {'E': 'f1', 'C': 'c', 'B': 'off'}


def n3(v):
    return '%.3f' % v


def n2(v):
    return '%.2f' % v


def n1(v):
    return '%.1f' % v


def c4(v):
    return '%.4f' % v


def rng(t, f=n3):
    """'lo to hi' of a pair or a list, or the one value when both print the same."""
    lo, hi = f(min(t)), f(max(t))
    return lo if lo == hi else '%s to %s' % (lo, hi)


def code(s):
    return '<code>%s</code>' % s


def _lines(nums):
    """[5, 6, 7, 10] -> '5-7,10' (the form of a reference key)."""
    nums = sorted(set(nums))
    out, a, b = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == b + 1:
            b = n
            continue
        out.append((a, b))
        a = b = n
    out.append((a, b))
    return ','.join('%d' % a if a == b else '%d-%d' % (a, b) for a, b in out)


def build(D, V, S):
    def cite(boot, file, lines, text):
        if not isinstance(lines, (list, tuple)):
            lines = [lines]
        return S.ref('file:%s:%s:%s' % (boot, file, _lines(lines)), text)

    def rep_lines(row):
        return [r['line'] for r in row['rep_rows']]

    for t in ('latency test', 'chain load', 'walked many times', 'walked once', 'every line flushed first',
              'address order', 'refill', 'L3 read refill', 'L2 refills not accounted for', 'hit set',
              'exploratory', 'checked in two states', 'background control', 'home node', 'mesh', 'step',
              'SLC', 'OCM', 'SOG', 'chain kind'):
        S.term(t)

    sweep = D.lat_sweep
    chain = [r for r in sweep if r['kind'] != 'every line flushed first']
    fl = D.lat_flushed
    row = {r['size']: r for r in chain}
    r4k, r128, r384, r2m, r8m, r32m = (row[s] for s in (4 * KIB, 128 * KIB, 384 * KIB, 2 * MIB, 8 * MIB, 32 * MIB))
    cache = D.platform['cache_bytes']
    l23 = cache['L2'] + cache['L3']
    summ = D.lat_sweep_summary
    doc = D.doc
    readme_dram = S.ref('readme:F1')
    ref_sysinfo = cite('F1', 'sysinfo.txt', [c['line'] for c in D.platform['caches']],
                       'the cache sizes of CPU 2')
    ref_small = cite('F1', SMALL, [r['line'] for r in chain if r['file'] == SMALL],
                     'the best rep of each footprint from 4 KiB to 384 KiB')
    ref_large = cite('F1', LARGE, [r['line'] for r in chain if r['file'] == LARGE],
                     'the best rep of each footprint from 512 KiB to 32 MiB')
    ref_flushed = cite('F1', FLUSHED, rep_lines(fl), 'the two reps of the 8 MiB chain with every line flushed first')
    slc_label = '%s est.' % V.size_label(SLC_EST_BYTES)

    out = []

    # ------------------------------------------------------------------ 3.1
    out.append(S.h3('lat-footprint', 'By footprint, CPU 2'))
    over = [row[s] for s in (384 * KIB, 512 * KIB, 768 * KIB)]
    svg = V.line_chart(
        [dict(name='boot F1, chain walked many times (to 384 KiB) or once (from 512 KiB)', color='f1',
              points=[(r['size'], r['best']) for r in chain],
              tips=['%s, reps %s ns' % (r['kind'], ', '.join(n3(v) for v in r['reps'])) for r in chain]),
         dict(name='boot F1, 8 MiB, every line flushed first (DRAM-model row)', color='f1', marker='diamond',
              size=6.0, line=False, points=[(fl['size'], fl['best'])])],
        x='log2', xlabel='footprint', ylabel='chain load, ns per load', yunit='ns', xfmt=V.size_label,
        xticks=[r['size'] for r in chain],
        vlines=[(cache['L1'], 'L1 %s' % V.size_label(cache['L1'])),
                (cache['L2'], 'L2 %s' % V.size_label(cache['L2'])),
                (l23, 'L2 + L3 sizes added = %s' % V.size_label(l23)),
                (SLC_EST_BYTES, 'SLC %s' % slc_label)],
        labels=[(0, s, '%s ns' % n3(row[s]['best'])) for s in LABELLED] +
               [(1, fl['size'], '%s ns' % n3(fl['best']))],
        gaps=[dict(x=r['size'], y0=min(r['reps']), y1=max(r['reps']), text='reps %s %%' % n1(r['spread_pct']),
                   dx=-9) for r in over],
        height=430)
    out.append(S.fig(
        svg,
        'Chain load on CPU 2 of boot F1 at %d footprints. Grey lines mark the cache sizes. A bracket marks '
        'the range of the reps on the three rows whose spread is over 0.7 %%.' % len(chain),
        'The chain load has four flat parts: %s ns in the L1, %s ns at %s, %s ns at %s and %s ns at %s. '
        'It then rises to %s ns.' % (
            n3(r4k['best']), n3(r128['best']), r128['label'], n3(r384['best']), r384['label'],
            n3(r2m['best']), r2m['label'], n3(r32m['best'])),
        id_='fig-L1',
        note='Files %s, %s and %s of boot F1 %s %s %s. Cache sizes from %s %s. The SLC size is an estimate '
             '(operator\'s README, %s). The DRAM model is an emulator memory with zero configured delay, not '
             'silicon timing (operator\'s README) %s.' % (
                 code(SMALL), code(LARGE), code(FLUSHED), ref_small, ref_large, ref_flushed,
                 code('sysinfo.txt'), ref_sysinfo, S.xref('setup-chip'), readme_dram)))

    out.append(S.p(
        '%s gives the chain load of boot F1 by footprint, and %s holds the exact rows. %s describes the latency '
        'test.' % (S.figref('fig-L1'), S.tabref('tab-TL1'), S.xref('setup-latency-test', cap=True))))
    out.append(S.bullets([
        'The %s row (the L1 row) reads %s ns per load, which is %s cycles. The SOG documents an L1 hit at %d to '
        '%d cycles %s.' % (r4k['label'], n3(r4k['best']), n2(r4k['cycles']), doc['l1_hit_cycles'][0],
                           doc['l1_hit_cycles'][1], S.ref('doc:sog')),
        'The %s row reads %s ns per load (%s cycles). The SOG documents an L2 hit at %d to %d cycles.' % (
            r128['label'], n3(r128['best']), n2(r128['cycles']), doc['l2_hit_cycles'][0], doc['l2_hit_cycles'][1]),
        'The %s chain (%s cycles) has a footprint equal to the L2 and L3 sizes added. The %s chain (%s cycles) '
        'gets its lines from outside the cluster (%s). The %s chain (%s cycles) is close to the DRAM-model row '
        '(%s).' % (r384['label'], n2(r384['cycles']), r2m['label'], n2(r2m['cycles']), S.xref('lat-levels'),
                   r32m['label'], n2(r32m['cycles']), S.xref('lat-dram')),
    ]))
    out.append(S.p(
        'A chain of up to %s is walked many times in each of three reps. A larger chain is walked once in each '
        'of two reps. The spread of the reps is over 0.7 %% on %d of the %d rows (%s). On the %s chain the reps '
        'read %s ns. These footprints sit at a size where two levels share the chain (%s).' % (
            r384['label'], summ['n'] - summ['n_spread_under_0_7'], summ['n'], S.xref('glance-repeat'),
            r384['label'], ', '.join(n3(v) for v in r384['reps']), S.xref('open-items'))))

    rows, group = [], None
    for r in sweep:
        if r['kind'] != group:
            group = r['kind']
            rows.append(group.capitalize())
        rows.append([r['label'], V.num(r['loads'], 0), n3(r['best']), n2(r['cycles']), n2(r['spread_pct']),
                     c4(r['l1']), c4(r['l2']), c4(r['a2']), c4(r['l2pf'])])
    hl = [i for i, r in enumerate(sweep) if r['size'] in LABELLED and r is not fl and r['size'] != 32 * MIB
          or r is fl]
    out.append(S.table(
        ['Footprint', 'Loads per rep', 'Best, ns per load', 'Cycles per load', 'Spread, %', 'L1 refills',
         'L2 refills', 'L3 read refills', 'L2 prefetch refills'],
        rows, caption='Chain load and counters per load on CPU 2 of boot F1.',
        note='Counters are those of the best rep. The highlighted rows are the five to quote: the L1 row, the %s '
             'row, the %s chain, the %s chain and the DRAM-model row. Files as in %s.' % (
                 r128['label'], r384['label'], r2m['label'], S.figref('fig-L1')),
        highlight=hl, id_='tab-TL1'))

    # ------------------------------------------------------------------ 3.2
    out.append(S.h3('lat-levels', 'Which level serves each footprint'))
    panels = [
        dict(ylabel='L1 refills per load', yrange=(0, 1.2),
             series=[dict(name='L1 refills', color='f1', points=[(r['size'], r['l1']) for r in chain])]),
        dict(ylabel='L2 refills per load', yrange=(0, 1.2),
             series=[dict(name='L2 refills', color='f1', points=[(r['size'], r['l2']) for r in chain]),
                     dict(name='of these: L2 prefetch refills', color='f1', dash=True, size=2.5, marker='square',
                          points=[(r['size'], r['l2pf']) for r in chain])]),
        dict(ylabel='L3 read refills per load (fills from outside the cluster)', yrange=(0, 1.2),
             series=[dict(name='L3 read refills', color='f1', points=[(r['size'], r['a2']) for r in chain])]),
    ]
    svg = V.small_multiples(
        panels, x='log2', xlabel='footprint', xticks=[r['size'] for r in chain], panel_height=150,
        vlines=[(cache['L1'], 'L1 %s' % V.size_label(cache['L1'])),
                (cache['L2'], 'L2 %s' % V.size_label(cache['L2'])),
                (l23, 'L2 + L3 = %s' % V.size_label(l23)),
                (SLC_EST_BYTES, 'SLC %s' % slc_label)])
    bands = {b['key']: b for b in D.lat_bands}
    out.append(S.fig(
        svg,
        'Refills per load of the best rep, boot F1, CPU 2, on the footprints of %s.' % S.figref('fig-L1'),
        'Each count steps from 0 to 1 at one cache size: the L1 refills at %s, the L2 refills at %s and the L3 '
        'read refills past %s.' % (V.size_label(cache['L1']), V.size_label(cache['L2']), V.size_label(l23)),
        id_='fig-L2',
        note='The DRAM-model row is not drawn. It counts %s refills per load at each of the three levels %s.' % (
            c4(fl['l1']), ref_flushed)))

    b = bands
    out.append(S.table(
        ['Footprint', 'Best, ns per load', 'What the counters read, per load (all reps)', 'Reading'],
        [[b['l1']['label'], rng(b['l1']['ns']), 'L1 refills %s' % rng(b['l1']['l1'], c4),
          'The L1 serves the loads.'],
         [b['l1-edge']['label'], rng(b['l1-edge']['ns']), 'L1 refills %s' % rng(b['l1-edge']['l1'], c4),
          'The footprint equals the L1 size. %s %% of the loads refill the L1.' % rng(
              [100 * v for v in b['l1-edge']['l1']], n1)],
         [b['l2']['label'], rng(b['l2']['ns']),
          'L1 refills %s. L2 refills at most %s. L3 read refills at most %s' % (
              rng(b['l2']['l1'], c4), c4(b['l2']['l2'][1]), c4(b['l2']['a2'][1])),
          'The L2 serves the loads that refill the L1.'],
         [b['cluster']['label'], rng(b['cluster']['ns']),
          'L1 refills %s. L2 refills %s, of which prefetch refills %s. L3 read refills at most %s' % (
              rng(b['cluster']['l1'], c4), rng(b['cluster']['l2'], c4), rng(b['cluster']['l2pf'], c4),
              c4(b['cluster']['a2'][1])),
          'Every load refills the L1. The L2 and the L3 share the chain. Boot E counts the hits (%s).' %
          S.xref('lat-l3')],
         [b['mixed']['label'], rng(b['mixed']['ns']),
          'L3 read refills %s. L2 prefetch refills at most %s' % (
              rng(b['mixed']['a2'], c4), c4(b['mixed']['l2pf'][1])),
          'Mixed. That share of the loads is filled from outside the cluster. The rest is served inside the '
          'cluster.'],
         [b['home-nodes']['label'], rng(b['home-nodes']['ns']),
          'L3 read refills %s. Prefetch refills %s' % (
              rng(b['home-nodes']['a2'], c4), c4(max(b['home-nodes']['l2pf'][1], b['home-nodes']['l1pf'][1]))),
          'Served by the home nodes over the mesh (read as the SLC).'],
         [b['rising']['label'], rng(b['rising']['ns']),
          'L3 read refills %s' % rng(b['rising']['a2'], c4),
          'Filled from outside the cluster. The chain load rises with the footprint.']],
        caption='Seven bands of footprint on boot F1, CPU 2.',
        note='Files as in %s.' % S.figref('fig-L1'), align='lrll', id_='tab-TL2'))

    r512, r768 = row[512 * KIB], row[768 * KIB]
    ocm = D.ocm_all5_summary['every_line']
    out.append(S.bullets([
        'A refill count is an aggregate over the rep. It does not give the path of each line, and the L1 and L2 '
        'refill counts include prefetch fills.',
        'The %s chain is a mixed row, not a pure L3 row. Its best rep counts %s L3 read refills per load, so '
        'about %s %% of its loads are filled from outside the cluster.' % (
            r384['label'], c4(r384['a2']), n1(100 * r384['a2'])),
        'From %s to %s the prefetch refill counts read %s per load from %s up, and %s L2 prefetch refills per '
        'load at %s.' % (r512['label'], row[1 * MIB]['label'],
                         c4(max(max(r['l2pf_reps']) for r in chain if r['size'] >= 768 * KIB)),
                         r768['label'], c4(r512['l2pf']), r512['label']),
        'No counter inside the timed interval separates an SLC hit from a fill by the DRAM model. Both are a '
        'fill from outside the cluster. Two facts support the SLC reading of the %s rows. The chain load is '
        'flat at %s ns there, against %s ns for the DRAM-model row. The OCM row, whose lines live in the home '
        'nodes, reads %s ns from the same CPUs (%s).' % (
            b['home-nodes']['label'], rng(b['home-nodes']['ns'], n1), n3(fl['best']), rng(ocm, n1),
            S.xref('ocm-quote')),
    ]))
    out.append(S.hyp(
        'From %s to %s a growing share of the loads is filled by the DRAM model, as the footprint passes the SLC '
        'size (%s, operator\'s README).' % (
            row[4 * MIB]['label'], r32m['label'], slc_label),
        'One command per footprint under the mesh counters, to read the requests sent on to memory at each '
        'footprint.'))

    # ------------------------------------------------------------------ 3.3
    out.append(S.h3('lat-l3', 'What an L3-served load costs'))
    hit = D.lat_hit
    es = D.l3_est_summary
    est = {e['size']: e for e in D.l3_est}
    d = es['direct_row']
    chk = D.lat_hit_check
    svg = V.stacked_hbar(
        [dict(label=h['label'], values=[h['l2hit'], h['l3hit'], h['a2']], note='%s ns' % n1(h['best']),
              sub=('%s L3 hits per load, %s ns' % (n2(h['l3hit']), n1(h['best']))) if h['size'] == d['size'] else None)
         for h in hit],
        [('L2 hits', 'f1'), ('L3 hits', 'c'), ('L3 read refills (from outside the cluster)', 'ref')],
        fmt=lambda v: V.num(v, 2), xlabel='per load (best rep of boot E)', total=False, xmax=1.0)
    ref_hits = cite('E', HITS, [n for h in hit for n in rep_lines(h)], 'the three reps of each footprint, with the hit set')
    out.append(S.fig(
        svg,
        'Where the loads of a chain are served on boot E, CPU 2, from %s to %s. The bold number is the chain '
        'load. The part of a bar that is missing up to 1 is loads that the L1 serves.' % (
            hit[0]['label'], hit[-1]['label']),
        'On the %s chain %s of every load hits the L3, and the chain reads %s ns per load.' % (
            d['label'], rng(d['l3hit_rng'], n2), rng(es['direct_ns'])),
        id_='fig-L3', note='File %s of boot E %s.' % (code(HITS), ref_hits)))

    rs = D.repeat_summary
    out.append(S.p(
        'Boot F1 has no count of L3 hits. Its commands count the prefetch refills in the same three counters. '
        '%s ran the same chains with the hit set %s. Its chain loads of up to %s repeat those of boot F1 '
        '(%s).' % (
            D.boot_first_use['E'].replace('boot E', 'Boot E', 1), S.ref('src:common.h'), r384['label'],
            S.xref('glance-repeat'))))
    out.append(S.p(
        'The direct row comes first. The %s chain of boot E reads %s ns per load. Per load it counts %s L3 '
        'hits, %s L2 hits and %s refills from outside the cluster.' % (
            d['label'], rng(es['direct_ns']), rng(d['l3hit_rng']), rng(d['l2hit_rng']), rng(d['a2_rng']))))
    out.append(S.p(
        'An estimate removes the other loads from the row. A chain is serial. So the time of a walk is the sum '
        'of the times of its loads. For each rep the estimate is (chain load - L1 share x L1 cost - L2 hits x '
        'L2 cost - L3 read refills x outside cost) / L3 hits. The three costs are rows of boot E: %s ns (%s '
        'row), %s ns est. (from the %s row of the hit set) and %s ns (%s chain) %s %s.' % (
            n3(es['tL1']), es['tL1_row']['label'], n3(es['tL2']), es['tL2_row']['label'], n3(es['tOUT']),
            es['tOUT_row']['label'],
            cite('E', SMALL, es['tL1_row']['line'], 'the 4 KiB row, an input of the L3 estimate'),
            cite('E', LARGE, es['tOUT_row']['line'], 'the 2 MiB chain, an input of the L3 estimate'))))
    out.append(S.bullets([
        'On the two rows where L3 hits are the majority of the loads (%s) an L3-served load costs %s to %s ns '
        'est.' % (' and '.join(V.size_label(s) for s in es['sizes']), n1(es['lo']), n1(es['hi'])),
        'The estimate depends on the row. The %s row gives %s ns est. and the %s row %s ns est.' % (
            est[192 * KIB]['label'], rng(es['est_192k'], n1), est[512 * KIB]['label'], rng(es['est_512k'], n2)),
        'The %s row of boot E is walked many times. The %s row of boot F1 is walked once. They are two '
        'different measurements.' % (est[512 * KIB]['label'], r512['label']),
    ]))
    out.append(S.p(
        'The three events of the hit set are exploratory, with three consistency checks (%s). L1 refills equal '
        'L2 hits plus L3 accesses, and L3 accesses equal L3 hits plus L3 read refills, within %s per load on all '
        '%d reps. The L3 hit event reads %s on boots B, C and D, where the L3 holds no data %s.' % (
            S.tabref('tab-TS4'), c4(max(chk['id_l1_max'], chk['id_access_max'])), chk['boots']['E']['n_rows'],
            c4(max(chk['boots'][k]['l3hit_max'] for k in 'BCD')),
            ' '.join(S.ref('file:%s:%s' % (k, HITS)) for k in 'BCD'))))

    f1u = {r['size']: r['unacc_l2'] for r in chain}
    trow = []
    for h in hit:
        e = est.get(h['size'])
        u = f1u.get(h['size'])
        trow.append([h['label'], n3(h['best']), rng(h['l2hit_rng'], c4), rng(h['l3hit_rng'], c4),
                     rng(h['a2_rng'], c4),
                     rng(u, c4) if h['size'] in (192 * KIB, 256 * KIB, 384 * KIB) else '-',
                     ('%s est.' % rng(e['est'], n2)) if e else '-'])
    out.append(S.table(
        ['Footprint', 'Best,<br>ns per load', 'L2 hits', 'L3 hits', 'L3 read refills',
         'Boot F1: L2 refills<br>not accounted for', 'L3-served load,<br>ns per load'],
        trow, caption='The hit-set rows of boot E, CPU 2 (counts per load, range of the three reps).',
        note='The estimate is given for the rows with at least %s L3 hits per load. The highlighted rows are '
             'those where L3 hits are the majority. The boot F1 column is a difference of counters on the same '
             'footprint of boot F1, not a hit count. It reads close to the L3 hits of boot E at 192 KiB and '
             '256 KiB.' % n2(min(e['l3_share'][0] for e in D.l3_est)),
        highlight=[i for i, h in enumerate(hit) if h['majority_l3']], id_='tab-TL3'))

    # ------------------------------------------------------------------ 3.4
    out.append(S.h3('lat-dram', 'The DRAM-model row'))
    out.append(S.p(
        'The DRAM-model row is the %s chain with every line flushed first. The program removes each line of '
        'the chain from the caches and then walks the chain once %s. The row reads %s ns per load (%s cycles) '
        'on both reps, with %s refills per load at each of the three levels %s. The DRAM level is an emulator '
        'memory model with zero configured delay, not silicon timing (operator\'s README) %s.' % (
            fl['label'], S.ref('src:latency.c'), n3(fl['best']), n2(fl['cycles']), c4(fl['a2']), ref_flushed,
            readme_dram)))
    out.append(S.bullets([
        'The %s chain walked once reads %s ns per load. That is %s %% under the DRAM-model row.' % (
            r32m['label'], n3(r32m['best']), n2(100 * (1 - r32m['best'] / fl['best']))),
        'The %s chain walked once reads %s ns per load. That is %s ns under the DRAM-model row at the same '
        'footprint. Both rows count %s L3 read refills per load. The walked-once row is therefore not the row '
        'to quote for the DRAM model. The cause of the difference is an open item (%s).' % (
            r8m['label'], n3(r8m['best']), n3(fl['best'] - r8m['best']), rng([r8m['a2'], fl['a2']], n2),
            S.xref('open-items')),
        'A difference between the DRAM-model row and another row is the measured difference between two loops. '
        'It is not the time of one part of the path.',
    ]))

    # ------------------------------------------------------------------ 3.5
    out.append(S.h3('lat-clusters', 'The other clusters'))
    ctrl = [c for c in D.lat_cluster['control'] if c['counted']]
    unc = [c for c in D.lat_cluster['control'] if not c['counted']][0]
    c2m = D.lat_cluster['chain2m']
    by = {c['cpu']: c for c in c2m}
    tick_name = "boot B's fit at the mean steps of the CPU, plus the offset of CPU 2"
    svg = V.dot_rows(
        [dict(label='CPU %d' % c['cpu'], sub='mean steps: %s along X, %s along Y' % (
            n1(c['mean_steps_x']), n1(c['mean_steps_y'])),
              values=[c['best'], [v for v in c['reps'] if v != c['best']]], tick=c['fit_plus_offset'],
              note=V.signed(c['diff_cpu2'], 3, 'ns') if c['cpu'] != 2 else '', labels='ends')
         for c in c2m],
        [dict(name='best rep', color='f1'), dict(name='other rep', color='f1', hollow=True)],
        unit='ns', fmt=n3, xlabel='chain load of the 2 MiB chain, ns per load', tick_name=tick_name,
        xrange=(23.0, 27.0))
    ref_c2m = ' '.join(cite('F1', c['file'], rep_lines(c), 'the two reps of the 2 MiB chain') for c in c2m)
    out.append(S.fig(
        svg,
        'The 2 MiB chain from one core of each cluster, boot F1. The bold number is the difference from CPU 2.',
        'CPU 8 reads %s ns above CPU 2. CPUs 4 and 6 read %s and %s ns above it.' % (
            n3(by[8]['diff_cpu2']), n3(by[4]['diff_cpu2']), n3(by[6]['diff_cpu2'])),
        id_='fig-L4',
        note='The row of CPU 2 is one footprint of the sweep command. The rows of CPUs 4, 6 and 8 are '
             'single commands under the mesh counters %s. The grey tick uses the fit of the per-region OCM rows '
             'of boot B (%s).' % (ref_c2m, S.xref('ocm-region'))))
    out.append(S.p(
        'The background control (a %s chain on 4 KiB pages) reads %s ns per load on the four CPUs. On CPU 2 it '
        'reads %s ns with the mesh counters and %s ns without them.' % (
            V.size_label(ctrl[0]['size']), rng([c['ns'] for c in ctrl]),
            n3(ctrl[0]['ns']), n3(unc['ns']))))
    out.append(S.p(
        'The L3 status register was read on the cluster of CPU 2 only (operator\'s README) %s.' % readme_dram))
    out.append(S.hyp(
        'The order of the four CPUs follows the distance on the mesh from the cluster port to the five home '
        'nodes. CPU 8 has the most steps and reads highest: %s ns above CPU 2, where the fit of boot B gives '
        '%s ns. The other two do not fit as well. CPU 6 has the mean steps of CPU 2 and reads %s ns above it. '
        'CPU 4 reads %s ns above it, where the fit gives %s ns.' % (
            V.signed(by[8]['diff_cpu2'], 3), V.signed(by[8]['fit_diff_cpu2'], 3), n3(by[6]['diff_cpu2']),
            V.signed(by[4]['diff_cpu2'], 3), V.signed(by[4]['fit_diff_cpu2'], 3)),
        'The 2 MiB chain of CPU 2 as a single command under the mesh counters, and several reps of each of '
        'the four commands.'))
    out.append(S.table(
        ['CPU', 'Background control,<br>ns per load', '2 MiB chain, best,<br>ns per load', 'Other rep,<br>ns per load', 'Spread, %',
         'L3 read refills<br>per load', 'Minus CPU 2,<br>ns', "Boot B's fit<br>minus CPU 2, ns"],
        [['%d' % c['cpu'], n3(k['ns']), n3(c['best']),
          ', '.join(n3(v) for v in c['reps'] if v != c['best']), n2(c['spread_pct']), c4(c['a2']),
          V.signed(c['diff_cpu2'], 3) if c['cpu'] != 2 else '-',
          V.signed(c['fit_diff_cpu2'], 3) if c['cpu'] != 2 else '-'] for c, k in zip(c2m, ctrl)],
        caption='Background control and 2 MiB chain per cluster, boot F1.',
        note='Controls: files %s %s.' % (
            code('latency-control-cpu&lt;c&gt;.csv'),
            ' '.join(cite('F1', k['file'], k['line'], 'the background control') for k in ctrl + [unc])),
        id_='tab-TL4'))

    # ------------------------------------------------------------------ 3.6
    out.append(S.h3('lat-order', 'Address order and the prefetchers'))
    seq = {s['boot']: s for s in D.lat_seq}
    cmp_ = D.lat_seq_cmp
    E, C, B = seq['E'], seq['C'], seq['B']
    order = ['E', 'C', 'B']
    series = [dict(name=LEGEND[k], color=COLOR[k]) for k in order] + \
             [dict(name='', color=COLOR[k], hollow=True) for k in order]
    drows = []
    for i, k in enumerate(order):
        s = seq[k]
        vals = [None] * 6
        vals[i], vals[3 + i] = s['best'], s['random_ns']
        drows.append(dict(label=s['boot'] and D.boot_name[k], sub=s['conditions'], values=vals,
                          note='%s x' % (n1(s['ratio']) if s['ratio'] > 2 else n2(s['ratio']))))
    svg = V.dot_rows(drows, series, x='log', unit='ns', fmt=n3, xlabel='chain load of the 8 MiB chain, ns per load',
                     connect=True, labels='all')
    ref_seq = ' '.join(cite(k, SEQ, rep_lines(seq[k]), 'the two reps of the address-order 8 MiB chain')
                       for k in order)
    ref_rand = ' '.join(cite(k, seq[k]['random_file'], seq[k]['random_line'],
                             'the best rep of the 8 MiB chain with every line flushed first') for k in order)
    out.append(S.fig(
        svg,
        'The 8 MiB chain with every line flushed first, on three boots. Filled dot: the chain in address order. '
        'Hollow dot: the chain in random order. The bold number is random order over address order.',
        'Address order helps only where the prefetchers are on, and it helps most where the L3 is on as well.',
        id_='fig-L5',
        note='Files %s %s and %s %s. The DRAM model is an emulator memory, not silicon timing (operator\'s '
             'README) %s.' % (code(SEQ), ref_seq, code(FLUSHED), ref_rand, readme_dram)))
    out.append(S.p(
        'In the address-order chain each line points to the next line of the buffer, and every line is flushed '
        'first %s. A load still waits for the data of the load before it. Boot F1 has no such command. Three '
        'other boots ran it: %s, %s and %s. Two conditions differ between boot E and boot B, so each effect '
        'is read from one pair of boots.' % (
            S.ref('src:latency.c'), D.boot_first_use['E'], D.boot_first_use['C'], D.boot_first_use['B'])))
    out.append(S.bullets([
        'Prefetchers, with the L3 holding no data: boot C reads %s ns per load and boot B %s ns. That is %s '
        'times.' % (n3(C['best']), n3(B['best']), n2(cmp_['pf_effect'])),
        'L3, with the prefetchers on: boot E reads %s ns per load and boot C %s ns. That is %s times. No '
        'counter explains this step (%s).' % (n3(E['best']), n3(C['best']), n2(cmp_['l3_effect']),
                                             S.xref('open-l3')),
        'Boot B over boot E is %s times, with both the prefetchers and the L3 different.' % n1(cmp_['b_over_e']),
        'With the prefetchers off the order makes no difference: %s ns in address order against %s ns in random '
        'order on boot B.' % (n3(B['best']), n3(B['random_ns'])),
    ]))
    out.append(S.p(
        'On boots E and C the L1 refills read %s per load, and the L1 prefetch refills read %s per load. On '
        'boot B the L1 prefetch refills read %s. The two events of the L1 prefetcher are checked in '
        'two states by these rows. The L3 read refills read %s per load on boot E, although every line comes '
        'from outside the cluster. So this event does not count the fills that the prefetchers cause.' % (
            rng([E['l1'], C['l1']], c4), rng([E['l1pf'], C['l1pf']], c4), c4(B['l1pf']), c4(E['a2']))))

    step, fetch, crit = E['best'], E['random_ns'], B['best']
    n_fetch = int(round(cmp_['fetches_in_flight_est']))
    t_end = 110.0
    lanes = [
        dict(name="boot B, prefetchers off: the core's loads",
             blocks=[(0, crit, 'one load = one fetch, %s ns' % n2(crit), 'critical'), (crit, 2 * crit, '', 'work')]),
        dict(name="boot E, prefetchers on: the core's loads",
             blocks=[(i * step, (i + 1) * step, '', 'work') for i in range(int(t_end / step))]),
        dict(name='boot E: line fetches, est.',
             blocks=[(i * step, i * step + fetch, '', 'wait') for i in range(n_fetch)]),
    ]
    svg = V.lanes(lanes, unit='ns', t_range=(0, t_end),
                  spans=[(0, crit, 'boot B: %s ns per load' % n2(crit), 'critical'),
                         (0, step, 'boot E: %s ns per load' % n2(step))])
    out.append(S.fig(
        svg,
        'Wall-clock lanes of the address-order 8 MiB chain. Durations to scale. The overlap is schematic.',
        'On boot B each load waits for its own fetch. On boot E about %d fetches est. overlap, and a load '
        'completes every %s ns.' % (n_fetch, n2(step)),
        id_='fig-L6',
        note='The length of a fetch is assumed equal to the chain load with every line flushed first. Fetches '
             'in flight are an estimate (%s / %s = %d est.). No counter counts them. With the L3 holding no '
             'data (boot C) the same chain reads %s ns per load.' % (n2(fetch), n2(step), n_fetch, n2(C['best']))))

    out.append(S.table(
        ['Boot', 'L3', 'Prefetchers', 'Address order,<br>ns per load', 'Cycles<br>per load', 'L1 refills',
         'L1 prefetch<br>refills', 'L2 refills by the<br>L1 prefetcher', 'L3 read<br>refills',
         'Random order,<br>ns per load'],
        [[D.boot_name[k].replace(' ', '&nbsp;'), seq[k]['l3'].replace(' ', '&nbsp;'), seq[k]['prefetchers'], n3(seq[k]['best']), n2(seq[k]['cycles']),
          c4(seq[k]['l1']), c4(seq[k]['l1pf']), c4(seq[k]['l2byl1pf']), c4(seq[k]['a2']), n3(seq[k]['random_ns'])]
         for k in order],
        caption='The 8 MiB chain with every line flushed first, in address order and in random order (counts '
                'per load of the address-order row).',
        note='Files as in %s.' % S.figref('fig-L5'), id_='tab-TL5'))

    # ------------------------------------------------------------------ 3.7
    out.append(S.h3('lat-pfoff', 'Random chains with the prefetchers off'))
    pf = D.lat_pfoff
    ps = D.lat_pfoff_summary
    p32 = [p for p in pf if p['size'] == 32 * KIB][0]
    p4m = [p for p in pf if p['size'] == 4 * MIB and p['kind'] == 'walked once'][0]
    left = ps['left_out']
    out.append(S.p(
        '%s ran the footprint sweep of boot F1. %s compares the rows whose level does not depend on the L3. '
        'The rows from %s to %s are left out, since the L3 state differs.' % (
            D.boot_first_use['B'].replace('boot B', 'Boot B', 1), S.tabref('tab-TL6'), V.size_label(min(left)),
            V.size_label(max(left)))))
    pf_from = [r for r in chain if r['size'] >= 768 * KIB]
    out.append(S.bullets([
        'Without 32 KiB and 4 MiB, boot B reads %s times boot F1 from 4 KiB to 128 KiB and %s times from 1.5 MiB '
        'to 32 MiB. The DRAM-model row reads %s times. So on these rows the prefetchers neither help nor slow '
        'a random chain.' % (rng(ps['small'], c4), rng(ps['large'], c4), c4(ps['flushed'])),
        'At 32 KiB boot B reads %s (%s ns against %s ns). The four boots with the prefetchers on read %s ns, '
        'and the two boots with the prefetchers off %s ns. Boot F1 counts %s L1 refills per load there, of '
        'which %s are prefetch refills. Boot B counts %s.' % (
            c4(ps['r32k']), n3(p32['b_ns']), n3(p32['f1_ns']), rng(ps['ns32k_pf_on']), rng(ps['ns32k_pf_off']),
            c4(p32['f1_l1']), c4(p32['f1_l1pf']), c4(p32['b_l1'])),
        'At 4 MiB boot B reads %s (%s ns against %s ns). The six boots read %s ns on this row, in an order that '
        'follows neither the prefetchers nor the L3 (%s).' % (
            c4(ps['r4m']), n3(p4m['b_ns']), n3(p4m['f1_ns']), rng(list(ps['ns4m'].values())),
            S.xref('open-items')),
    ]))
    trows, group = [], None
    for p in pf:
        if p['kind'] != group:
            group = p['kind']
            trows.append(group.capitalize())
        trows.append([p['label'], n3(p['f1_ns']), n3(p['b_ns']), c4(p['ratio'])])
    out.append(S.table(
        ['Footprint', 'Boot F1, ns per load', 'Boot B, ns per load', 'Boot B over boot F1'],
        trows, caption='Random chains on CPU 2: boot F1 (L3 on, prefetchers on) against boot B (the L3 holds no '
                       'data, prefetchers off).',
        note='The highlighted rows are the two that differ by more than 2 %%. The DRAM model is an emulator '
             'memory, not silicon timing (operator\'s README) %s. Rows of boot B %s %s %s. Boot F1 as in %s.' % (
                 readme_dram,
                 cite('B', SMALL, [p['b_line'] for p in pf if p['b_file'] == SMALL], 'the best rep of each footprint'),
                 cite('B', LARGE, [p['b_line'] for p in pf if p['b_file'] == LARGE], 'the best rep of each footprint'),
                 cite('B', FLUSHED, [p['b_line'] for p in pf if p['b_file'] == FLUSHED],
                      'the best rep of the 8 MiB chain with every line flushed first'),
                 S.figref('fig-L1')),
        highlight=[i for i, p in enumerate(pf) if p['callout']], id_='tab-TL6'))

    return ''.join(out)
