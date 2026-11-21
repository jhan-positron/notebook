"""Section 4 of the page: the cluster L3 as seen by the CME (the L3-event rows of boots F1 and F2).

Every measured number comes from the data layer D.  Typed text is limited to event numbers,
file names and document facts, each with a reference."""

from . import data as _data          # lstsq, for the leave-one-out check of fit C1

KEY = 'l3'
TITLE = 'The cluster L3 as seen by the CME'

K = 1024
M = 1024 * 1024
SMALL = 'cme-latency-dram-small-l3.csv'
LARGE = 'cme-latency-dram-large-l3.csv'
PSMALL = 'cme-latency-dram-small.csv'
PLARGE = 'cme-latency-dram-large.csv'
RUNDIR = {'F1': 'results/membench-jibin-011/results/bootF1/', 'F2': 'results/membench-jibin-012/results/bootF2/'}
MID_LO, MID_HI = 96 * K, 384 * K          # the footprints of the lead figure
TOP_LO = 192 * K                          # the rows with the largest hit counts
EDGE = 3 * M                              # the counts explain the time up to here
FIG_Y0 = 30                               # ns: start of the y axis of the two scatter figures
# Typed facts of the operator's README of boot F1 (lines 348 to 349): the SLC is five home nodes of
# 1 MiB, and the firmware locks 4 of 16 ways of each as OCM.
SLC_NODES, SLC_NODE_BYTES, SLC_WAYS, SLC_OCM_WAYS = 5, M, 16, 4


def n4(v):
    return 'n/a' if v is None else '%.4f' % v


def n3(v):
    return 'n/a' if v is None else '%.3f' % v


def n2(v):
    return 'n/a' if v is None else '%.2f' % v


def code(s):
    return '<code>%s</code>' % s


def join_and(items):
    """'a', 'a and b', 'a, b and c'."""
    items = list(items)
    if len(items) < 2:
        return ''.join(items)
    return '%s and %s' % (', '.join(items[:-1]), items[-1])


def pct2(v):
    """Signed percent with 2 decimals and no signed zero."""
    s = '%+.2f' % v
    return '0.00' if s in ('+0.00', '-0.00') else s


def build(D, V, S):
    F1, F2 = D.boot_name['F1'], D.boot_name['F2']
    cap = lambda s: s[0].upper() + s[1:]
    rt = D.rt_ns

    # ------------------------------------------------------------ references
    def fref(boot, name):
        blk = D.latblocks(boot, name)[0]
        log = D.log_lines(boot, name)
        return S.ref('l3:%s:%s' % (boot, name),
                     'File <code>%s%s</code> (%s). The command is in <code>log.txt</code> of the same folder, line %s. '
                     'The header comment is at line %d of the file.' % (
                         RUNDIR[boot], name, D.boot_name[boot], ', '.join(str(x) for x in log), blk['line']))

    r_s2, r_l2 = fref('F2', SMALL), fref('F2', LARGE)
    r_s1, r_l1 = fref('F1', SMALL), fref('F1', LARGE)
    r_ps2, r_pl2 = fref('F2', PSMALL), fref('F2', PLARGE)
    r_ps1, r_pl1 = fref('F1', PSMALL), fref('F1', PLARGE)
    r_code = S.ref('l3:common.h',
                   'Source file <code>common.h</code>, lines 436 to 451: the event set <code>cme-l3</code>, the three '
                   'event names from the event table of the Arm C1-SME2 Technical Reference Manual 107831, and the '
                   'statement that the three counts are exploratory.')
    r_readme = S.ref('l3:readme-f2',
                     'Operator\'s README of boot F2, <code>results/membench-jibin-012/README.md</code>, section '
                     '"The CME L3 events", lines 178 to 183. The same statements for boot F1 are in '
                     '<code>results/membench-jibin-011/README.md</code>, lines 238 to 241.')
    r_slc = S.ref('readme:F1:platform',
                  'Operator\'s README of boot F1, <code>results/membench-jibin-011/README.md</code>, lines 348 to 349: '
                  'the SLC is five home nodes of 1 MiB, and the firmware locks 4 of 16 ways of each as OCM.')
    r_mem = S.ref('readme-f1-memory-model',
                  'Operator\'s README of boot F1, <code>results/membench-jibin-011/README.md</code>, lines 243 to 253, '
                  'section "The memory model behind the home node": the DRAM model has no configured delay.')
    r_kern = S.ref('src:kern-chain',
                   'Source file <code>cme_kern.S</code>, lines 116 to 140: the chain-load kernel (LD1D, then LASTB) and '
                   'the kernel of the round-trip baseline (a register copy, then LASTB).')
    # The wording of every "above the round-trip baseline" number of this section.
    two_kernels = ('The round-trip baseline is a separate measurement with no memory access. Its kernel replaces the '
                   'LD1D load of the chain kernel by a register copy, and both kernels return the value to the core '
                   'through LASTB %s.' % r_kern)
    l3c = [c for c in D.platform['caches'] if c['level'] == 3][0]
    r_sys = S.ref('l3:sysinfo-l3',
                  'File <code>%ssysinfo.txt</code>, line %d: the level 3 cache of CPU 2 (size and the CPUs that share it).'
                  % (RUNDIR[l3c['boot']], l3c['line']))
    l3_size = V.size_label(l3c['size_bytes'])
    # typed facts of the operator's README (r_slc): five home nodes of 1 MiB, 4 of 16 ways locked as OCM
    slc_est = V.size_label(SLC_NODES * SLC_NODE_BYTES * (SLC_WAYS - SLC_OCM_WAYS) // SLC_WAYS)

    # ------------------------------------------------------------ terms
    S.term('CME', 'the Arm C1-SME2 matrix engine unit. One per cluster, shared by two cores')
    S.term('chain load', 'one dependent load of the latency test. Its time is given in ns per load')
    S.term('latency test', 'the loop that times a chain of dependent loads through the CME')
    S.term('round-trip baseline', 'the row that moves a value into the CME and back to the core with no memory load '
                                  '(the DUP+LASTB row)')
    S.term('footprint', 'the size of the buffer that holds the chain')
    S.term('cluster L3', 'the level 3 cache that the two cores of a cluster and their CME share')
    S.term('rep', 'one timed measurement')
    S.term('pass', 'one walk over the buffer or the chain')
    S.term('walked many times', 'chain kind: the same chain is walked again and again inside one rep')
    S.term('walked once', 'chain kind: each rep is one pass over a chain that was not walked before')
    S.term('bracket time', 'the time between two clock reads in C around the kernel call')
    S.term('span time', 'the time between the two counter reads inside the kernel, after SMSTART and before SMSTOP')
    S.term('best row', 'the row that the program prints with the lowest time of the reps')
    S.term('inner refill', 'a refill of the CME L1 from inside the cluster (event 0x327D)')
    S.term('outer refill', 'a refill of the CME L1 from outside the cluster (event 0x327E)')
    S.term('prefetch refill', 'a refill of the CME L1 that the hardware prefetcher of the CME asked for (event 0x32B2)')
    S.term('read refill', 'a refill of the CME L1 caused by a load of the program that missed (event 0x3280)')
    S.term('L3 hit count', 'event 0x328E (CME_L3D_CACHE_HIT) per chain load. Exploratory')
    S.term('L3 miss count', 'event 0x328F (CME_L3D_CACHE_MISS) per chain load. Exploratory')
    S.term('L3 refill count', 'event 0x3290 (CME_L3D_CACHE_REFILL) per chain load. Exploratory')
    S.term('miss minus refill', 'the L3 miss count minus the L3 refill count of one row')
    S.term('hit share', 'the L3 hit count divided by the sum of the L3 hit count and the L3 miss count of one row')
    S.term('L3-event rows', 'the rows of the latency test that count the three L3 events of the CME')
    S.term('plain rows', 'the rows of the latency test at the same footprints with the refill counters and no L3 event')
    S.term('control row', 'A row whose count is known in advance. Example: an L3 hit count of 0 on a boot whose L3 '
                          'holds no data.')
    S.term('residual', 'The measured value of a row minus the value that a fit gives for the same row.')
    S.term('free intercept', 'A constant term of a fit whose value the fit chooses.')
    S.term('correlation coefficient', 'A value from -1 to +1 that says how closely two columns follow one straight '
                                      'line. -1 or +1 means exactly.')
    S.term('rms', 'root mean square: the square root of the mean of the squared residuals of a fit')
    S.term('condition number', 'the ratio of the largest to the smallest singular value of the matrix of a fit. '
                               'A large value means that the fit cannot separate its coefficients')
    S.term('least-squares fit', 'the coefficients that make the sum of the squared residuals smallest')
    S.term('snoop', 'a request to another cache in the cluster for a line that it holds')
    S.term('SLC', 'system level cache: the cache inside the mesh, held by the five home nodes')
    S.term('DRAM model', 'the memory behind the mesh on this emulator. It is an emulator memory model, not silicon '
                         'DRAM timing')
    S.term('mesh counters', 'counters of the mesh. They count the requests that each home node receives during one '
                            'whole command')
    S.term('RTL', 'register transfer level: the source text of the hardware design')
    S.term('TRM', 'Arm Technical Reference Manual')

    # ------------------------------------------------------------ data
    reps2, reps1 = D.l3_reps['F2'], D.l3_reps['F1']
    rows2, rows1 = D.chain_l3['F2'], D.chain_l3['F1']
    mid_reps = [r for r in reps2 if MID_LO <= r['size'] <= MID_HI]
    mid_rows = [r for r in rows2 if MID_LO <= r['size'] <= MID_HI]
    lo_row, hi_row = mid_rows[0], mid_rows[-1]
    lo_lab, hi_lab = lo_row['label'], hi_row['label']
    top_rows = [r for r in mid_rows if r['size'] >= TOP_LO]
    top_reps = [r for r in mid_reps if r['size'] >= TOP_LO]
    top_lo_lab = top_rows[0]['label']
    ck1, ck2 = D.l3_checks['F1'], D.l3_checks['F2']
    line = D.l3_line
    rp1, rp2 = D.l3_repeat['F1'], D.l3_repeat['F2']
    large = D.l3_large
    edge_row = [r for r in rows2 if r['size'] == EDGE][0]
    last_row = rows2[-1]
    above = [r for r in rows2 if r['size'] > EDGE]
    edge_lab = edge_row['label']
    fast = min(mid_rows, key=lambda r: r['best'])                   # the fastest best row of the footprints
    max_hit = max(reps2, key=lambda r: r['hit'])                    # over every rep row of boot F2
    max_share = max(r['hit_share'] for r in mid_reps)
    two_best = sorted(mid_rows, key=lambda r: -r['hit'])[:2]
    two_best.sort(key=lambda r: r['size'])
    tb_labs = '%s and %s' % (two_best[0]['label'], two_best[1]['label'])
    tb_ns = (min(r['best'] for r in two_best), max(r['best'] for r in two_best))
    tb_hit = (min(r['hit'] for r in two_best), max(r['hit'] for r in two_best))
    tb_above = (tb_ns[0] - rt, tb_ns[1] - rt)                       # derived here: best minus the baseline
    top_ns = (min(r['ns'] for r in top_reps), max(r['ns'] for r in top_reps))
    top_hit = (min(r['hit'] for r in top_reps), max(r['hit'] for r in top_reps))
    top_above = (top_ns[0] - rt, top_ns[1] - rt)
    rise_ns = last_row['best'] - edge_row['best']                   # derived here
    rise_outer = last_row['outer'] - edge_row['outer']              # derived here
    hit_above_hi = max(r['hit'] for r in above)
    reps_of = lambda size: sorted([r for r in mid_reps if r['size'] == size], key=lambda r: r['rep'])
    best_of = {r['size']: r['best_rep'] for r in mid_rows}

    def fall(key, name, fmt):
        """The fall of the chain load over the footprints of the lead figure, against one count."""
        s = 'On %s the chain load falls from %s at %s (%s %s) to %s at %s (%s %s).' % (
            F2, V.ns(lo_row['best']), lo_lab, name, fmt(lo_row[key]), V.ns(fast['best']), fast['label'], name,
            fmt(fast[key]))
        if fast is not hi_row:
            s += ' The %s row has the largest %s, %s, and reads %s (best rows).' % (
                hi_lab, name, fmt(hi_row[key]), V.ns(hi_row['best']))
        return s

    out = S.h2('l3', TITLE)
    out += S.takeaways([
        'Each boot has a second set of latency rows that count three L3 events of the CME (the L3-event rows). '
        'The benchmark source (file %s) calls these three counts exploratory %s. '
        'No control row validates them.' % (code('common.h'), r_code),
        fall('hit_share', 'hit share', n4) + ' The hit share is the L3 hit count divided by the sum of the L3 hit '
        'count and the L3 miss count.',
        'On %s no row counts one L3 hit per load. The largest L3 hit count there is %s per load. '
        'The two best rows with the largest counts (%s) take %s to %s. '
        'These times are %s to %s above the separate round-trip baseline measurement. '
        'That difference compares two kernels, and it does not isolate the time of an L3 access.' % (
            F2, n4(max_hit['hit']), tb_labs, V.ns(tb_ns[0]), V.ns(tb_ns[1]), V.ns(tb_above[0]), V.ns(tb_above[1])),
        'On %s the chain load rises by %s from %s to %s. The outer refill count moves by %s per load over these '
        'rows, and the L3 hit count stays at or below %s per load. The counts do not explain the time there.' % (
            F2, V.ns(rise_ns), edge_lab, last_row['label'], n4(rise_outer), n4(hit_above_hi)),
        'The L3-event rows repeat the times of the plain rows within 1 %% at %d of %d footprints on %s and at '
        '%d of %d on %s.' % (rp2['n_within_1pct'], rp2['n'], F2, rp1['n_within_1pct'], rp1['n'], F1),
    ])

    # ============================================================ 5.1 the events
    out += S.h3('l3-events', 'What the three events are')
    eq_tol = n4(max(ck1['max_hit_miss_minus_refills'], ck2['max_hit_miss_minus_refills']))
    out += S.bullets([
        'The three counts are exploratory: no control row validates them. A control row is a row whose count is '
        'known in advance.',
        'The benchmark source says that no fit and no attribution may read the three counts until an independent '
        'control validates them %s.' % r_code,
        'In every chain row of both boots the L3 refill count equals the outer refill count.',
        'In the same rows the L3 hit count plus the L3 miss count equals the inner plus the outer refill count '
        'within %s per load.' % eq_tol,
        'Each count is the total of one rep divided by the number of chain loads of that rep. '
        'A count does not name the lines of the chain that the events belong to.',
    ])
    n_chain = ck2['chain_rep_rows']
    assert ck1['chain_rep_rows'] == n_chain
    nodes = [
        dict(id='inner', x=10, y=40, w=250, h=62, title='inner refill, 0x327D',
             lines=['CME L1 refill from inside the cluster']),
        dict(id='outer', x=10, y=196, w=250, h=62, title='outer refill, 0x327E',
             lines=['CME L1 refill from outside the cluster']),
        dict(id='sum', x=352, y=66, w=336, h=66, kind='soft', title='inner + outer = hit + miss',
             lines=['within %s per load in all %d chain rep rows of each boot' % (eq_tol, n_chain)]),
        dict(id='same', x=352, y=202, w=336, h=50, kind='soft', title='outer = L3 refill',
             lines=['equal in all %d chain rep rows of each boot' % n_chain]),
        dict(id='hit', x=780, y=40, w=250, h=62, title='L3 hit count, 0x328E',
             lines=['L3 accesses by the CME that hit']),
        dict(id='miss', x=780, y=112, w=250, h=62, title='L3 miss count, 0x328F',
             lines=['L3 demand accesses by the CME that missed']),
        dict(id='refill', x=780, y=196, w=250, h=62, title='L3 refill count, 0x3290',
             lines=['L3 refills caused by the CME']),
    ]
    arrows = [dict(src='inner', dst='sum', dashed=True),
              dict(src='outer', dst='sum', dashed=True, via=[(306, 210), (306, 118)]),
              dict(src='hit', dst='sum', dashed=True),
              dict(src='miss', dst='sum', dashed=True),
              dict(src='outer', dst='same', dashed=True, shift=8),
              dict(src='refill', dst='same', dashed=True)]
    groups = [dict(x=0, y=4, w=270, h=266, label='CME L1 refills by source'),
              dict(x=770, y=4, w=270, h=266, label='CME L3 events (exploratory)')]
    dia = V.boxes(nodes, arrows, groups=groups)
    out += S.fig(
        dia,
        'The five counters of the L3-event rows and the two equalities that the rows show (the two boxes in the '
        'middle). Both boots, all rep rows of '
        '%s and %s %s %s %s %s. The event names are the names of the benchmark source %s. A dashed arrow joins a '
        'counter to an equality that it enters. The equalities are seen in the rows. They are not a statement about '
        'the hardware.' % (
            code(SMALL), code(LARGE), r_s1, r_l1, r_s2, r_l2, r_code),
        'The three L3 counts carry one number that the refill counts do not: how inner plus outer divides into hit and miss.')
    out += S.bullets([
        'The event set %s counts seven events: the core cycle counter and six raw events %s. The six raw events are '
        'the CME cycles, the inner and outer refills, and the three L3 events.' % (code('cme-l3'), r_code),
        'The benchmark source names two checks and says that neither validates the counts %s.' % r_code,
        ['The first check compares hit plus miss with inner plus outer. The Arm manual defines the two totals over '
         'different sets of events: hit plus miss counts L3 accesses, and inner plus outer counts CME L1 refills %s.' % r_code,
         'The agreement of the two totals is therefore not a proof. It also does not show how the total divides into '
         'hits and misses.',
         'The second check is a control row: an L3 hit count of 0 on a boot whose L3 holds no data. Neither boot '
         'provides it.'],
        'The operator\'s README gives one reading of the counts. It comes from the RTL source of the CME and not from '
        'a simulation %s.' % r_readme,
        ['By that reading the L3 hit count is the number of CME L1 refills that the cluster L3 supplied (operator\'s README).',
         'By that reading miss minus refill is the number of refills supplied by a snoop of a core\'s cache in the '
         'cluster (operator\'s README).',
         'The README states that this reading is not the independent control that the benchmark source asks for '
         '(operator\'s README).'],
        'This section therefore reports the counts and the times beside them. Every reading of a count as '
        '"the level that served the load" is inside a Hypothesis block.',
        'The same holds for every reading of a count as a part of the chain or as a set of lines.',
    ])
    rep_hm = lambda reps: (min(x['hit'] + x['miss'] for x in reps), max(x['hit'] + x['miss'] for x in reps))
    hm1, hm2 = rep_hm(reps1), rep_hm(reps2)
    out += S.table(
        ['Check on the rep rows of the two L3-event files', cap(F1), cap(F2)],
        [['Rep rows', '%d' % ck1['rep_rows'], '%d' % ck2['rep_rows']],
         ['Chain rep rows (footprint above 0)', '%d' % ck1['chain_rep_rows'], '%d' % ck2['chain_rep_rows']],
         ['Chain rep rows where the L3 refill count differs from the outer refill count',
          '%d' % ck1['refill_differs_from_outer'], '%d' % ck2['refill_differs_from_outer']],
         ['Largest difference between hit + miss and inner + outer, per load',
          n4(ck1['max_hit_miss_minus_refills']), n4(ck2['max_hit_miss_minus_refills'])],
         ['The same difference in counts per rep row', '%.1f counts' % ck1['max_hit_miss_minus_refills_counts'],
          '%.1f counts' % ck2['max_hit_miss_minus_refills_counts']],
         ['Lowest and highest hit + miss per load (best rows)',
          '%s to %s' % (n4(ck1['hit_plus_miss_lo']), n4(ck1['hit_plus_miss_hi'])),
          '%s to %s' % (n4(ck2['hit_plus_miss_lo']), n4(ck2['hit_plus_miss_hi']))],
         ['Lowest and highest hit + miss per load (all chain rep rows)',
          '%s to %s' % (n4(hm1[0]), n4(hm1[1])), '%s to %s' % (n4(hm2[0]), n4(hm2[1]))]],
        caption='Counter checks. Files %s and %s of each boot.' % (code(SMALL), code(LARGE)),
        note='The counter columns are printed with 4 decimals, so 0.0001 per load is one print step.',
        id_='l3-checks')

    # ============================================================ 5.2 scatter of time against hit share
    out += S.h3('l3-scatter', 'Chain load against L3 hit share, boot F2 (prefetchers off)')
    out += S.bullets([
        fall('hit_share', 'hit share', n4),
        'The hit share never passes %s. Every row therefore counts L3 misses beside its L3 hits.' % n4(max_share),
    ])
    tip_of = lambda r: '%s, rep %d: %s, hit share %s\nhit %s, miss minus refill %s, outer %s per load' % (
        r['label'], r['rep'], V.ns(r['ns']), n4(r['hit_share']), n4(r['hit']), n4(r['mms']), n4(r['outer']))
    ser, labs = [], []
    for i, row in enumerate(mid_rows):
        rr = reps_of(row['size'])
        ser.append(dict(name='CME, %s, one point per rep' % F2, color='f2', size=3.0, line=True,
                        points=[(r['hit_share'], r['ns']) for r in rr], tips=[tip_of(r) for r in rr]))
        b = [r for r in rr if r['rep'] == best_of[row['size']]][0]
        labs.append(dict(series=i, x=b['hit_share'], y=b['ns'], text=row['label']))
    r384 = reps_of(MID_HI)
    ann = [dict(x=r384[-1]['hit_share'], y=r384[-1]['ns'], dx=40, dy=-70,
                text='%s: the three reps read %s, %s and %s ns\nwith %s, %s and %s outer refills per load' % (
                    hi_lab, n3(r384[0]['ns']), n3(r384[1]['ns']), n3(r384[2]['ns']),
                    n4(r384[0]['outer']), n4(r384[1]['outer']), n4(r384[2]['outer'])))]
    share_ticks = [(i / 5.0, '%.1f' % (i / 5.0)) for i in range(6)]
    svg = V.line_chart(
        ser, x='linear', xrange=(0, 1), xticks=share_ticks,
        xlabel='hit share (L3 hit count / (L3 hit count + L3 miss count))',
        ylabel='chain load, ns', yunit='ns', yrange=(FIG_Y0, None), labels=labs, annotations=ann,
        xfmt=lambda v: '%.4f' % v, height=400, show_legend=False, title='chain load against hit share')
    out += S.fig(
        svg,
        'Chain load against hit share on %s. Rows: the %d rep rows of the footprints %s to %s (walked many times), '
        'file %s %s. Each point is one rep. A line joins the reps of one footprint in the order rep 0, rep 1, rep 2. '
        'The label marks the rep of the best row of each footprint. '
        'The y axis starts at %d ns. The round-trip baseline (%s) lies below the axis. '
        'No row exists to the right of a hit share of %s.' % (
            F2, len(mid_reps), lo_lab, hi_lab, code(SMALL), r_s2, FIG_Y0, V.ns(rt), n4(max_share)),
        'A larger hit share goes with a shorter chain load up to %s, and the points stop at a hit share of %s.' % (
            fast['label'], n4(max_share)))
    lead_fig_n = S.n_fig

    rep_tab = [[r['label'], '%d%s' % (r['rep'], ' (best)' if best_of[r['size']] == r['rep'] else ''), n3(r['ns']),
                n3(r['span']), n3(r['ns'] - rt), n4(r['hit']), n4(r['mms']), n4(r['outer']), n4(r['hit_share'])]
               for row in mid_rows for r in reps_of(row['size'])]
    same_share = [row['label'] for row in mid_rows
                  if all(n4(r['hit_share']) == n4(r['hit']) for r in reps_of(row['size']))]
    same_hm = [r['hit'] + r['miss'] for row in mid_rows if row['label'] in same_share for r in reps_of(row['size'])]
    same_sum = '' if not same_hm else (n4(min(same_hm)) if n4(min(same_hm)) == n4(max(same_hm)) else
                                       '%s to %s' % (n4(min(same_hm)), n4(max(same_hm))))
    plain_of = {r['size']: r for r in rows2}
    out += S.table(
        ['Footprint', 'Rep', 'Bracket ns', 'Span ns', 'Bracket ns minus baseline (ns)', 'Hit', 'Miss minus refill',
         'Outer', 'Hit share'],
        rep_tab,
        caption='The rep rows of Figure %d. %s, file %s.' % (S.n_fig, cap(F2), code(SMALL)),
        note='The round-trip baseline is %s. %s '
             'The column "Bracket ns minus baseline" is therefore the difference between two kernels. '
             'It is not a measured time of the memory access. '
             'Counts are events per chain load: the total of the rep divided by its loads. '
             'The L3 of the cluster is %s %s, and the %s footprint is larger than it. %s'
             'The plain rows of the same footprints read %s %s.' % (
                 V.ns(rt), two_kernels.replace('The round-trip baseline is', 'It is', 1), l3_size, r_sys, hi_lab,
                 ('At %s the L3 hit count plus the L3 miss count prints as %s per load, so the hit share equals '
                  'the L3 hit count there. ' % (join_and(same_share), same_sum)) if same_share else '',
                 ', '.join('%s (%s)' % (V.ns(plain_of[r['size']]['plain']), r['label']) for r in mid_rows), r_ps2),
        highlight=lambda i, row: '(best)' in row[1], id_='l3-reptable')
    rep_table_n = S.n_table
    falls = [row['label'] for row in mid_rows
             if all(a['ns'] > b['ns'] and a['hit'] < b['hit']
                    for a, b in zip(reps_of(row['size']), reps_of(row['size'])[1:]))]
    rises = [row for row in mid_rows
             if all(a['ns'] < b['ns'] for a, b in zip(reps_of(row['size']), reps_of(row['size'])[1:]))]
    items = []
    if falls:
        items.append('Within %s the chain load falls from rep to rep while the L3 hit count rises.' % join_and(falls))
    for row in rises:
        rr = reps_of(row['size'])
        items.append(
            'At %s the chain load rises from rep to rep. The L3 hit count stays within %s to %s per load there. '
            'The outer refill count goes from %s to %s per load.' % (
                row['label'], n4(min(r['hit'] for r in rr)), n4(max(r['hit'] for r in rr)),
                n4(rr[0]['outer']), n4(rr[-1]['outer'])))
    out += S.bullets(items)

    # ============================================================ 5.3 the rows of both boots
    out += S.h3('l3-rows', 'The L3-event rows of both boots')
    f1_gt1 = [r for r in rows1 if r['hit_plus_miss'] > 1.0005]
    from_lo = [r['hit_plus_miss'] for r in rows2 if r['size'] >= MID_LO]
    out += S.bullets([
        'On %s the L3 hit count plus the L3 miss count is at most %s per load in every rep row. '
        'It is %s to %s per load from %s up (best rows).' % (
            F2, n4(hm2[1]), n4(min(from_lo)), n4(max(from_lo)), lo_lab),
        'On %s the same sum reaches %s per load in the best rows and %s per load over all rep rows. '
        'It is above 1 per load at %d of %d footprints (best rows).' % (
            F1, n4(ck1['hit_plus_miss_hi']), n4(hm1[1]), len(f1_gt1), len(rows1)),
        'The rows of %s therefore count more L3 accesses than chain loads. This section gives no hit share for '
        'that boot.' % F1,
    ])
    pt = lambda rows, key: [(r['size'], r[key]) for r in rows]
    caps = [(l3c['size_bytes'], 'cluster L3 %s' % l3_size)]
    f1_max = max(rows1, key=lambda r: r['hit_plus_miss'])
    panels = [
        dict(ylabel='L3 hit count per load, %s' % F2, yrange=(0, 1.05),
             series=[dict(name=F2, color='f2', points=pt(rows2, 'hit'), label='max')], yfmt=n4),
        dict(ylabel='miss minus refill per load, %s' % F2, yrange=(0, 1.05),
             series=[dict(name=F2, color='f2', points=pt(rows2, 'miss_minus_refill'), label='max')], yfmt=n4),
        dict(ylabel='outer refills per load (equal to the L3 refill count), %s' % F2, yrange=(0, 1.05),
             series=[dict(name=F2, color='f2', points=pt(rows2, 'outer'), label='last')], yfmt=n4),
        dict(ylabel='L3 hit count + L3 miss count per load, both boots', hlines=[(1.0, 'one per load', 'left')],
             series=[dict(name=F2, color='f2', points=pt(rows2, 'hit_plus_miss')),
                     dict(name=F1, color='f1', points=pt(rows1, 'hit_plus_miss'),
                          label=sorted({f1_max['size'], rows1[-1]['size']}))],
             labels=[dict(series=0, x=2 * M, pos='above',
                          text='boot F2: %s to %s from %s up' % (n4(min(from_lo)), n4(max(from_lo)), lo_lab))],
             yfmt=n4, height=170),
    ]
    out += S.fig(
        V.small_multiples(panels, x='log2', xlabel='footprint', vlines=caps, panel_height=140),
        'The L3-event counts per chain load against footprint. Rows: the best rows of %s (up to %s, walked many times) '
        'and %s (from %s, walked once) on both boots %s %s %s %s. The counts are those of the rep of the best row. '
        'Panels 1 to 3 show %s only. %s appears in panel 4 only. '
        'The vertical line in every panel marks the %s cluster L3.' % (
            code(SMALL), hi_lab, code(LARGE), [r for r in rows2 if r['kind'] == 'walked once'][0]['label'],
            r_s2, r_l2, r_s1, r_l1, F2, cap(F1), l3_size),
        'On %s the L3 hit count, miss minus refill and the outer refill count add up to %s to %s per load from %s up. '
        'On %s the L3 hit count plus the L3 miss count reaches %s per load.' % (
            F2, n4(min(from_lo)), n4(max(from_lo)), lo_lab, F1, n4(ck1['hit_plus_miss_hi'])))

    def row_cells(r, share):
        return [r['label'], r['kind'], n3(r['best']), n3(r['span']), n4(r['inner']), n4(r['outer']), n4(r['hit']),
                n4(r['miss']), n4(r['refill']), n4(r['miss_minus_refill']),
                n4(r['hit_share']) if share else 'not given']
    trows = [cap(F2)] + [row_cells(r, True) for r in rows2] + [cap(F1)] + [row_cells(r, False) for r in rows1]
    out += S.table(
        ['Footprint', 'Chain kind', 'Bracket ns', 'Span ns', 'Inner', 'Outer', 'Hit', 'Miss', 'Refill',
         'Miss minus refill', 'Hit share'],
        trows,
        caption='The L3-event rows of both boots. Files %s (walked many times) and %s (walked once).' % (
            code(SMALL), code(LARGE)),
        note='Times are ns per chain load: the bracket time of the best row and the span time of the same rep. '
             'Counts are events per chain load of that rep. The hit share is "n/a" where hit + miss is below 0.5 per load. '
             'It is "not given" on %s, where hit + miss exceeds one per load.' % F1,
        align='ll' + 'r' * 9, id_='l3-rowtable')

    # support for the hypothesis: the plain rows of boot F1 count the prefetch refills at the same footprints
    plain1 = [x for f in (PSMALL, PLARGE) for s in D.latblocks('F1', f)[0]['order']
              for x in D.lat('F1', f, s)['reps'] if s in {r['size'] for r in f1_gt1}]
    pf = (min(x['hwprf'] for x in plain1), max(x['hwprf'] for x in plain1))
    pf_tol = max(abs(x['inner'] + x['outer'] - x['rd'] - x['hwprf']) for x in plain1)
    rd_hi = max(x['rd'] for x in plain1)
    ex = f1_max['size']                                              # the footprint with the largest sum
    ex_l3 = [x['inner'] + x['outer'] for x in reps1 if x['size'] == ex]
    ex_pl = [x['inner'] + x['outer'] for x in plain1 if x['size'] == ex]
    out += S.hyp(
        'The counts above one per load on %s include refills that the hardware prefetchers cause. '
        'The same footprints on %s count at most %s L3 hits plus L3 misses per load.</p>' % (F1, F2, n4(hm2[1]))
        + S.bullets([
            'Rows that support it: the plain rows of %s count %s to %s prefetch refills per load at the %d footprints '
            'above one per load (all rep rows) %s %s.' % (F1, n4(pf[0]), n4(pf[1]), len(f1_gt1), r_ps1, r_pl1),
            'In those plain rows the inner plus the outer refill count equals the read refill count plus the prefetch '
            'refill count within %s per load. The read refill count is at most %s per load.' % (n4(pf_tol), n4(rd_hi)),
            'The L3-event rows count similar inner plus outer totals. Example, %s: %s to %s per load in the L3-event '
            'reps and %s to %s per load in the plain reps.' % (
                f1_max['label'], n4(min(ex_l3)), n4(max(ex_l3)), n4(min(ex_pl)), n4(max(ex_pl))),
            'The prefetch refill count and the L3 events are in different rows. This is support and not proof.',
        ]) + '<p>',
        'The prefetch refill counter of the CME (event 0x32B2) in one event set with the three L3 events on a '
        'boot with the prefetchers on %s. Neither event set of these boots holds both.' % r_code)

    # ============================================================ 5.4 cost from rows alone
    out += S.h3('l3-cost', 'The chain load in the rows with the most L3 hits')
    out += S.bullets([
        'The rep rows from %s to %s on %s count %s to %s L3 hits per load. They take %s to %s. '
        'These times are %s to %s above the round-trip baseline (%s).' % (
            top_lo_lab, hi_lab, F2, n4(top_hit[0]), n4(top_hit[1]), V.ns(top_ns[0]), V.ns(top_ns[1]),
            V.ns(top_above[0]), V.ns(top_above[1]), V.ns(rt)),
        two_kernels,
        'Each time above the round-trip baseline in this section is therefore the measured difference between two '
        'kernels. It is not a measured time of the memory access or of an L3 hit.',
        'Each of these rows counts L3 hits and L3 misses together. No row has a hit share of 1. '
        'No row therefore gives the chain load at a hit share of 1.',
    ])
    out += S.fig(
        V.dumbbell([dict(label=r['label'], sub='%s L3 hits per load' % n4(r['hit']), a=rt, b=r['best'])
                    for r in mid_rows],
                   a_name='round-trip baseline', b_name='chain load, best row, %s' % F2, a_color='ref', b_color='f2',
                   unit='ns', xlabel='time per chain load, ns', fmt=lambda v: V.num(v, 3), label_w=200,
                   xrange=(5 * int(rt / 5), None)),
        'The chain load beside the round-trip baseline (%s) on %s. Rows: the best rows of %s to %s, file %s %s. '
        'The bold text of each row is the chain load minus the baseline. It is the difference between two kernels. '
        'The text under each footprint is the L3 hit '
        'count of the same rep. The x axis starts at %d ns, not at 0.' % (
            V.ns(rt), F2, lo_lab, hi_lab, code(SMALL), r_s2, 5 * int(rt / 5)),
        'The chain load reads %s to %s above the separate round-trip baseline in the three rows with the most L3 hits, '
        'and no row has a hit share of 1.' % (V.ns(min(r['best'] for r in top_rows) - rt), V.ns(max(r['best'] for r in top_rows) - rt)))
    out += S.p('The rep rows of these footprints are in <a href="#l3-reptable">Table %d</a>.' % rep_table_n)
    out += S.p('What the rows establish:')
    out += S.bullets([
        'A chain load takes %s to %s when the CME counts %s to %s L3 hits per load (the best rows of %s).' % (
            V.ns(tb_ns[0]), V.ns(tb_ns[1]), n4(tb_hit[0]), n4(tb_hit[1]), tb_labs),
        'These times are %s to %s above the round-trip baseline of %s. Each is the measured difference between two '
        'kernels.' % (V.ns(tb_above[0]), V.ns(tb_above[1]), V.ns(rt)),
        'These two rows count %s outer refills per load and %s inner refills per load.' % (
            join_and(n4(r['outer']) for r in two_best), join_and(n4(r['inner']) for r in two_best)),
    ])
    out += S.p('What the rows do not establish:')
    out += S.insufficient(
        'That event 0x328E counts the loads that the L3 served. The benchmark source asks for a control row: a boot '
        'whose L3 holds no data must count 0 hits %s. The L3-event rows on a boot with the L3 off would resolve it.' % r_code)
    out += S.insufficient(
        'The part of the time above the round-trip baseline that is memory-access time. The chain kernel and the '
        'round-trip kernel differ in one instruction %s. No row measures the time that the two kernels share outside '
        'the memory access. A calibration of that shared time would resolve it.' % r_kern)
    out += S.insufficient(
        'Which lines of the chain the L3 hits of a row belong to. Each count is a total over one rep. '
        'A trace of the refills by address would resolve it.')
    out += S.insufficient(
        'The chain load at a hit share of 1. The largest hit share is %s. A row with an L3 hit count close to 1 per '
        'load would resolve it. One example is a chain inside the %s of the L3 that is walked many times after its '
        'lines left the caches of the core.' % (n4(max_share), l3_size))
    out += S.insufficient(
        'What supplies a refill that is counted in miss minus refill. The operator\'s README names a snoop '
        'of a core\'s cache (operator\'s README) %s. No counter of these rows separates that source. '
        'A counter of the refills that a snoop of a core\'s cache supplies, read beside the three L3 events, would '
        'resolve it. The sources of this page name no such event number.' % r_readme)
    out += S.insufficient(
        'Any time per kind of refill on %s. Its L3 hit count plus L3 miss count exceeds one per load. '
        'An event set with the prefetch refill counter beside the three L3 events would resolve it.' % F1)

    # ============================================================ 5.5 the fit
    out += S.h3('l3-fit', 'The fit of time against the counts (hypothesis)')
    out += S.bullets([
        'A least-squares fit of the chain load against the three counts gives an estimate of the time per kind of '
        'CME L1 refill.',
        'Every fitted value of this subsection is an estimate (est.). All of them belong to one hypothesis.',
        'The estimate is not a result of this page. The reading of the events is not validated, and the value '
        'at a hit share of 1 lies outside the rows.',
    ])
    fits = D.l3_fits
    A1, A2, C1, C2, E1 = fits['A1'], fits['A2'], fits['C1'], fits['C2'], fits['E1']
    loo = D.l3_loo
    # derived here: fit C1 with one footprint left out, and its error on the rows that were left out
    c3 = ['hit', 'mms', 'outer']
    c1rows = [x for x in reps2 if MID_LO <= x['size'] <= EDGE]
    loo_err = 0.0
    for s_ in sorted({x['size'] for x in c1rows}):
        f = _data.lstsq([[x[c] for c in c3] for x in c1rows if x['size'] != s_],
                        [x['ns'] for x in c1rows if x['size'] != s_])
        loo_err = max([loo_err] + [abs(x['ns'] - sum(k * x[c] for k, c in zip(f['coef'], c3)))
                                   for x in c1rows if x['size'] == s_])
    fpts, ftips = [], []
    for r in mid_reps:
        is_best = best_of[r['size']] == r['rep']
        fpts.append((r['hit'], r['ns'], r['label']) if is_best else (r['hit'], r['ns']))
        ftips.append('%s, rep %d: %s, L3 hit count %s per load\nmiss minus refill %s, outer %s per load' % (
            r['label'], r['rep'], V.ns(r['ns']), n4(r['hit']), n4(r['mms']), n4(r['outer'])))
    yl = lambda x: line['intercept'] + line['slope'] * x
    fsvg = V.scatter_fit(
        [dict(name='CME, %s, one point per rep' % F2, color='f2', points=fpts, tips=ftips, size=3.0,
              fit=(line['slope'], line['intercept']), fit_range=(line['hit_lo'], line['hit_hi'])),
         dict(name='the line outside the rows (est.)', color='f2', line=True, dash=True, markers=False,
              points=[(0.0, yl(0.0)), (line['hit_lo'], yl(line['hit_lo'])), (line['hit_lo'], None),
                      (line['hit_hi'], yl(line['hit_hi'])), (1.0, yl(1.0))])],
        x='linear', xrange=(0, 1), xticks=share_ticks, xlabel='L3 hit count per load', ylabel='chain load, ns',
        yunit='ns', yrange=(FIG_Y0, None), xfmt=lambda v: '%.4f' % v, height=380,
        annotations=[dict(x=1.0, y=line['at_hit_1'], dx=-150, dy=-120,
                          text='%.1f ns est. at 1 hit per load\n(outside the rows: the largest count is %s)' % (
                              line['at_hit_1'], n4(line['hit_hi'])))])
    fig_h = S.fig(
        fsvg,
        'Hypothesis figure. Chain load against the L3 hit count per load on %s with a least-squares straight line. '
        'Rows: the %d rep rows of %s to %s, file %s %s. These are the points of Figure %d on the same y axis, which '
        'starts at %d ns. The line is solid over the L3 hit counts of the rows (%s to %s per load) and dashed '
        'outside them. The line is %.3f ns - %.3f ns x L3 hit count per load (est.).' % (
            F2, line['n'], lo_lab, hi_lab, code(SMALL), r_s2, lead_fig_n, FIG_Y0,
            n4(line['hit_lo']), n4(line['hit_hi']), line['intercept'], -line['slope']),
        'The line fits the rows with a residual rms of %s, and its value at 1 hit per load is an extrapolation (est.).' % (
            V.ns(line['rms'])))
    fit_fig_n = S.n_fig

    def fit_row(f, shown, why=''):
        e = lambda v: 'n/a' if v is None else '%.1f est.' % v
        if shown:
            cells = [e(f['hit']), e(f['mms']), e(f['outer']),
                     ('%.3f est.' % f['intercept']) if f['intercept'] is not None else
                     ('%.3f fixed' % f['subtracted'] if f['subtracted'] else 'none')]
        else:
            cells = ['-'] * 3 + ['-' if f['intercept_fitted'] else 'none']
        desc = f['desc'].replace(', no intercept', '').replace(', with intercept', ', with a free intercept')
        return [f['name'], desc, '%d' % f['n']] + cells + [
            n3(f['rms']), n3(f['max_res']), '%.1f / %.1f' % (f['cond_raw'], f['cond_unit']), 'yes' if shown else why]
    ftab = S.table(
        ['Fit', 'Footprints of the rep rows', 'Rep rows (count)', 'a (ns)', 'b (ns)', 'c (ns)', 'Intercept (ns)',
         'Rms (ns)', 'Largest (ns)', 'Condition number, raw / unit columns', 'Coefficients printed'],
        ['Fits whose coefficients can be separated: the coefficients are printed',
         fit_row(A1, True), fit_row(A2, True), fit_row(C1, True), fit_row(C2, True), fit_row(E1, True),
         'Fits whose coefficients are not printed: the fit cannot separate them, or the model does not hold',
         fit_row(fits['A3'], False, 'no (1)'),
         fit_row(fits['C3'], False, 'no (1)'),
         fit_row(fits['B2'], False, 'no (2)'),
         fit_row(fits['B1'], False, 'no (3)'),
         fit_row(fits['D1'], False, 'no (3)')],
        caption='Hypothesis table. Least-squares fits of the model: chain load = a x hit + b x (miss minus refill) + '
                'c x outer, over rep rows of %s. Files %s and %s.' % (F2, code(SMALL), code(LARGE)),
        note='No fit of this table is a result of this page, because the events are not validated %s. '
             'The name in the first column only identifies a fit, so that the text can refer to it. The column '
             'beside it gives the rows of the fit. The text below uses fits A2, C1 and E1. '
             'a is the coefficient of the L3 hit count, b the coefficient of miss minus refill, c the coefficient of '
             'the outer refill count, each in ns per event (est.). '
             'In a fit with no intercept each coefficient is a whole chain load time (est.), not a time above the '
             'round-trip baseline. '
             'Fit C2 fits the chain load minus the round-trip baseline ("fixed"). It assumes that the round-trip '
             'baseline is an additive part of every chain load. No row establishes that. '
             'Intercept "none": the fit has no intercept. Intercept "-": the fit has a free intercept (a constant '
             'that the fit chooses) and its value is not printed. '
             '"Rms" is the residual rms and "Largest" is the largest residual. '
             'The condition number is printed twice: for the raw columns, and after each column is scaled to unit length. '
             'Coefficients printed "no (1)": the three count columns sum to about 1 per load, so a free intercept '
             'cannot be separated from the coefficients. "no (2)": the three columns move together in these rows. '
             '"no (3)": the residual rms is %.1f ns or more, so the model does not hold above %s. '
             '"yes" means only that the coefficients can be separated numerically.' % (
                 r_code, min(fits['B1']['rms'], fits['D1']['rms']), edge_lab),
        id_='l3-fittable')
    pred_row = [r for r in rows2 if r['size'] == fast['size']][0]
    pred = C1['hit'] * pred_row['hit'] + C1['mms'] * pred_row['miss_minus_refill'] + C1['outer'] * pred_row['outer']
    small_reps = [x for x in reps2 if x['size'] < MID_LO]            # the rows that fit E1 adds to fit C1
    ordered = all(f['hit'] < f['mms'] < f['outer'] for f in (A2, C1))
    order_text = (
        'In fits A2 and C1 the coefficient of the L3 hit count is the lowest of the three: %.1f ns est. and %.1f ns est. '
        'against %.1f ns est. and %.1f ns est. for miss minus refill, and %.1f ns est. and %.1f ns est. for the outer '
        'refill count. The reading of the operator\'s README predicts that order: by it a hit is a refill that the L3 '
        'supplied (operator\'s README) %s. The order does not validate the reading.' % (
            A2['hit'], C1['hit'], A2['mms'], C1['mms'], A2['outer'], C1['outer'], r_readme)
        if ordered else
        'The three coefficients of fits A2 and C1 are not in the order that the reading of the operator\'s README '
        'predicts (operator\'s README) %s.' % r_readme)
    hyp_text = (
        'On %(F2)s, from %(lo)s to %(edge)s, a chain load takes one fixed time per kind of CME L1 refill. '
        'The three kinds are: a refill counted as an L3 hit, a refill counted in miss minus refill, and an outer '
        'refill.</p>' % dict(F2=F2, lo=lo_lab, edge=edge_lab)
        + fig_h + ftab + S.bullets([
            'Fit A2 (%d rep rows, %s to %s) gives a coefficient of %.1f ns est. per L3 hit. '
            'That is %.1f ns est. above the round-trip baseline, which is a separate measurement of another kernel.' % (
                A2['n'], lo_lab, hi_lab, A2['hit'], A2['hit'] - rt),
            'The same fit gives %.1f ns est. per unit of miss minus refill and %.1f ns est. per outer refill.' % (
                A2['mms'], A2['outer']),
            'The residual rms of fit A2 is %s and its condition number is %.1f (%.1f with unit columns).' % (
                V.ns(A2['rms']), A2['cond_raw'], A2['cond_unit']),
            'Fit C1 adds the walked-once rows up to %s (%d rep rows). It gives %.1f ns est., %.1f ns est. and %.1f ns est. '
            'with a residual rms of %s and a condition number of %.1f.' % (
                edge_lab, C1['n'], C1['hit'], C1['mms'], C1['outer'], V.ns(C1['rms']), C1['cond_raw']),
            'The coefficients of fit C1 move little when one footprint is left out (%d fits): %.1f to %.1f ns est. per '
            'hit, %.1f to %.1f ns est. per unit of miss minus refill, %.1f to %.1f ns est. per outer refill.' % (
                loo['n_fits'], loo['hit_lo'], loo['hit_hi'], loo['mms_lo'], loo['mms_hi'], loo['outer_lo'], loo['outer_hi']),
            'With one footprint left out, fit C1 predicts the rep rows of that footprint within %s est.' % V.ns(loo_err),
            'Fit C1 reproduces a row that it was fitted on: %.2f ns est. for the best row of %s, which measures %s. '
            'This is not an independent check.' % (pred, pred_row['label'], V.ns(pred_row['best'])),
            'Fit E1 adds the %d rep rows from %s to %s and a free intercept. These rows count at most %s refills per '
            'load and read %s to %s. They set the intercept.' % (
                len(small_reps), small_reps[0]['label'], small_reps[-1]['label'],
                n4(max(x['inner'] + x['outer'] for x in small_reps)),
                V.ns(min(x['ns'] for x in small_reps)), V.ns(max(x['ns'] for x in small_reps))),
            'The intercept of fit E1 is %.3f ns est. and the round-trip baseline is %s. The largest residual of fit E1 '
            'is %s, so the agreement is not the precision of the fit.' % (E1['intercept'], V.ns(rt), V.ns(E1['max_res'])),
            'The straight line of Figure %d has a correlation coefficient of %.4f between the chain load and the L3 hit '
            'count (-1 is an exact falling line). It gives %.1f ns est. at 1 hit per load.' % (
                fit_fig_n, line['r'], line['at_hit_1']),
            'Limit: the largest hit share of the rows is %s. Every value at a hit share of 1 is an extrapolation.' % n4(
                max_share),
            'Limit: fit C1 and fit E1 mix the two chain kinds. They assume one time per kind of refill for both.',
        ]) + '<p>' + order_text)
    out += S.hyp(
        hyp_text,
        'Two rows are needed. First, the L3-event rows on a boot with the L3 off: the L3 hit count must read 0. '
        'Second, a row with an L3 hit count close to 1 per load: its chain load must read close to the fitted %.1f ns est.'
        % A2['hit'])

    # ============================================================ 5.6 where the counts stop
    out += S.h3('l3-above', 'Where the counts stop explaining the time')
    first_once = [r for r in rows2 if r['kind'] == 'walked once'][0]
    out += S.bullets([
        'From %s to %s on %s the chain load rises from %s to %s as the outer refill count rises from %s to %s per load.' % (
            first_once['label'], edge_lab, F2, V.ns(first_once['best']), V.ns(edge_row['best']),
            n4(first_once['outer']), n4(edge_row['outer'])),
        'From %s to %s the chain load rises by %s, from %s to %s. The outer refill count moves by %s per load and '
        'the L3 hit count stays at or below %s per load.' % (
            edge_lab, last_row['label'], V.ns(rise_ns), V.ns(edge_row['best']), V.ns(last_row['best']),
            n4(rise_outer), n4(hit_above_hi)),
        '%s shows the same rise in the plain rows, with the SLC marker and the hypothesis for it.' % S.xref(
            'open-outside', cap=True),
    ])
    once = [r for r in rows2 if r['kind'] == 'walked once']
    marks = [first_once['size'], EDGE, last_row['size']]
    osvg = V.line_chart(
        [dict(name='CME, %s, best rows walked once' % F2, color='f2', points=[(r['outer'], r['best']) for r in once],
              tips=['%s: %s, outer %s, hit %s per load' % (r['label'], V.ns(r['best']), n4(r['outer']), n4(r['hit']))
                    for r in once])],
        x='linear', xrange=(0, 1.0), xticks=share_ticks, xlabel='outer refills per load', ylabel='chain load, ns',
        yunit='ns', yrange=(FIG_Y0, None), xfmt=n4, height=380, show_legend=False,
        labels=[dict(series=0, x=r['outer'], y=r['best'], text='%s: %s' % (r['label'], V.ns(r['best'])),
                     pos='left' if r['size'] >= EDGE else 'below')
                for r in once if r['size'] in marks],
        annotations=[dict(x=last_row['outer'], y=(edge_row['best'] + last_row['best']) / 2.0, dx=-330, dy=-10,
                          text='%s from %s to %s\nwhile the outer refill count moves by %s per load' % (
                              V.signed(rise_ns, 3, 'ns'), edge_lab, last_row['label'], n4(rise_outer)))],
        title='chain load against outer refills per load')
    out += S.fig(
        osvg,
        'Chain load against the outer refill count on %s. Rows: the best rows of %s to %s (walked once), file %s %s. '
        'The line joins the rows in footprint order. The y axis starts at %d ns.' % (
            F2, first_once['label'], last_row['label'], code(LARGE), r_l2, FIG_Y0),
        'Up to %s the chain load rises with the outer refill count. Above %s it rises by %s at an almost fixed '
        'outer refill count.' % (edge_lab, edge_lab, V.ns(rise_ns)))
    panels = [
        dict(ylabel='chain load, ns', yunit='ns', yrange=(FIG_Y0, None),
             series=[dict(name=F2, color='f2', points=pt(once, 'best'), label=marks)],
             gaps=[dict(x=last_row['size'], y0=edge_row['best'], y1=last_row['best'], dx=-34,
                        text='%s from %s to %s' % (V.signed(rise_ns, 3, 'ns'), edge_lab, last_row['label']))]),
        dict(ylabel='outer refills per load', yrange=(0, 1.1), yfmt=n4,
             series=[dict(name=F2, color='f2', points=pt(once, 'outer'), label=marks)]),
        dict(ylabel='L3 hit count per load', yrange=(0, 1.1), yfmt=n4,
             series=[dict(name=F2, color='f2', points=pt(once, 'hit'), label=marks)]),
    ]
    out += S.fig(
        V.small_multiples(panels, x='log2', xlabel='footprint', vlines=[(EDGE, edge_lab)], panel_height=150),
        'Chain load and two counts against footprint on %s. Rows: the best rows of %s to %s (walked once), file %s %s. '
        'The y axis of the first panel starts at %d ns.' % (
            F2, first_once['label'], last_row['label'], code(LARGE), r_l2, FIG_Y0),
        'Right of the %s marker the chain load rises by %s. The outer refill count moves by %s per load there, and '
        'the L3 hit count stays at or below %s per load.' % (edge_lab, V.ns(rise_ns), n4(rise_outer), n4(hit_above_hi)))
    out += S.table(
        ['Footprint', 'Bracket ns', 'Rise from the row above (ns)', 'Hit', 'Miss minus refill', 'Outer'],
        [[r['label'], n3(r['best']), 'n/a' if i == 0 else V.signed(r['best'] - once[i - 1]['best'], 3), n4(r['hit']),
          n4(r['miss_minus_refill']), n4(r['outer'])] for i, r in enumerate(once)],
        caption='The walked-once L3-event rows of %s, file %s.' % (F2, code(LARGE)),
        note='Best rows. Counts are per chain load, from the rep of the best row. The highlighted rows are above %s.' % edge_lab,
        highlight=lambda i, row: once[i]['size'] > EDGE, id_='l3-abovetable')
    out += S.bullets([
        'Over the %d rep rows from %s to %s the chain load runs from %s to %s. Its correlation coefficient with the outer '
        'refill count is %s (+1 is an exact rising line).' % (
            large['n'], first_once['label'], edge_lab, V.ns(large['ns_lo']), V.ns(large['ns_hi']),
            V.signed(large['r_outer'], 4)),
        'Above %s the outer refill count is %s to %s per load. The count of outer refills therefore does not account '
        'for the rise.' % (edge_lab, n4(min(r['outer'] for r in above)), n4(max(r['outer'] for r in above))),
    ])
    out += S.insufficient(
        'Which level outside the cluster supplies the outer refills above %s. The SLC is %s est. after the OCM ways are taken '
        'out (operator\'s README) %s. The memory behind it is an emulator memory model, not silicon DRAM timing '
        '(operator\'s README) %s. The outer refill count does not separate the two. The three L3 events and the two '
        'refill-source events count at the CME and at the cluster L3 only. Mesh counts per home node that cover only '
        'the timed pass of each footprint would resolve it (%s).' % (
            edge_lab, slc_est, r_slc, r_mem, S.xref('open-outside')))

    # ============================================================ 5.7 the timing repeat
    out += S.h3('l3-repeat', 'The timing repeat against the plain rows')
    outside = rp1['outside_1pct']
    n_out = len(outside)
    out += S.bullets([
        'On %s the L3-event rows read within %s of the plain rows at all %d footprints. The differences run from %s to %s.' % (
            F2, V.pct(rp2['worst_pct'], 2), rp2['n'], V.signed(rp2['diff_lo'], 3, 'ns'), V.signed(rp2['diff_hi'], 3, 'ns')),
        'On %s %d of %d footprints are within 1 %%. The largest difference is %s at %s (%s against %s).' % (
            F1, rp1['n_within_1pct'], rp1['n'], V.pct(rp1['worst_pct'], 2), rp1['worst_label'],
            V.ns(rp1['worst_l3']), V.ns(rp1['worst_plain'])),
    ])
    pc = lambda rows: [(r['size'], (r['ratio'] - 1.0) * 100.0) for r in rows]      # derived here: percent difference
    out_sizes = [o['size'] for o in outside]
    worst2 = max(rows2, key=lambda r: abs(r['ratio'] - 1.0))
    svg = V.line_chart(
        [dict(name=F2, color='f2', points=pc(rows2), label=[worst2['size']]),
         dict(name=F1, color='f1', points=pc(rows1), label=out_sizes)],
        x='log2', xlabel='footprint', ylabel='L3-event best row minus plain best row, % of the plain row', yunit='%',
        hlines=[(0.0, 'no difference', 'left'), (1.0, '+1 %'), (-1.0, '-1 %')], yrange='fit', height=420,
        yfmt=pct2)
    out += S.fig(
        svg,
        'Difference of the L3-event rows from the plain rows, in percent of the plain row. Rows: the best rows of all '
        '%d footprints of %s and %s against %s and %s, both boots %s %s %s %s %s %s %s %s. '
        'The y axis holds 0 and is not cut.' % (
            rp2['n'], code(SMALL), code(LARGE), code(PSMALL), code(PLARGE),
            r_s2, r_l2, r_ps2, r_pl2, r_s1, r_l1, r_ps1, r_pl1),
        'Every point of %s lies inside the 1 %% band (largest difference %s %% at %s), and %d points of %s lie below it.' % (
            F2, pct2((worst2['ratio'] - 1.0) * 100.0), worst2['label'], n_out, F1))
    out += S.table(
        ['Boot', 'Footprints', 'Within 1 %', 'Lowest and highest ratio', 'Lowest and highest difference (ns)',
         'Largest difference'],
        [[cap(b), '%d' % rp['n'], '%d' % rp['n_within_1pct'], '%.4f to %.4f' % (rp['ratio_lo'], rp['ratio_hi']),
          '%s to %s' % (V.signed(rp['diff_lo'], 3), V.signed(rp['diff_hi'], 3)),
          '%s at %s' % (V.pct(rp['worst_pct'], 2), rp['worst_label'])] for b, rp in ((F2, rp2), (F1, rp1))],
        caption='The repeat in numbers. Ratio = best row of the L3-event file / best row of the plain file at the same footprint.',
        id_='l3-repeattable')
    row1 = {r['size']: r for r in rows1}
    out_files = sorted({row1[o['size']]['src'] for o in outside}) + sorted({row1[o['size']]['plain_src'] for o in outside})
    tot_of = lambda size: [x['inner'] + x['outer'] for x in sorted(
        [x for x in reps1 if x['size'] == size], key=lambda x: x['rep'])]
    below_all = lambda o: sum(1 for v in o['l3_reps'] if v < min(o['plain_reps']))
    rep0_low = n_out > 0 and all(o['l3_reps'][0] == min(o['l3_reps']) and o['l3_reps'][0] < min(o['plain_reps'])
                                 for o in outside)
    rep0_few = n_out > 0 and all(tot_of(o['size'])[0] == min(tot_of(o['size'])) for o in outside)
    out += S.table(
        ['Footprint', 'L3-event best (ns)', 'Plain best (ns)', 'Difference (ns)', 'Ratio', 'L3-event reps (ns)',
         'Plain reps (ns)', 'Inner + outer refills per load of the L3-event reps'],
        [[o['label'], n3(o['l3']), n3(o['plain']), V.signed(o['diff'], 3), '%.4f' % o['ratio'],
          ', '.join(n3(v) for v in o['l3_reps']), ', '.join(n3(v) for v in o['plain_reps']),
          ', '.join(n2(v) for v in tot_of(o['size']))] for o in outside],
        caption='The %d footprints of %s outside 1 %%. Files %s.' % (n_out, F1, join_and(code(f) for f in out_files)),
        note='Reps are listed in the order rep 0, rep 1, rep 2. In each of these rows the lowest rep of the L3-event '
             'file is rep 0, and it is below every plain rep.' if rep0_low else
             'Reps are listed in the order rep 0, rep 1, rep 2.',
        id_='l3-outside')
    items = []
    if rep0_few:
        items.append('In each of these footprints rep 0 also counts the fewest refills per load (inner plus outer): %s.' % (
            ', '.join('%s against %s at %s' % (n2(tot_of(o['size'])[0]), join_and(n2(v) for v in tot_of(o['size'])[1:]),
                                               o['label']) for o in outside)))
    all_below = [o['label'] for o in outside if below_all(o) == len(o['l3_reps'])]
    if all_below:
        items.append('At %s every rep of the L3-event file reads below every plain rep. This is more than one low rep.' % (
            join_and(all_below)))
    items += [
        'The round-trip baseline reads %s in the L3-event files and in the plain files of both boots.' % V.ns(rt),
        'The times of this section can therefore be read beside the times of the plain rows of %s%s.' % (
            S.xref('latency'),
            (', except at the %d footprints of %s in <a href="#l3-outside">Table %d</a>' % (n_out, F1, S.n_table))
            if n_out else ''),
    ]
    out += S.bullets(items)
    if n_out:
        out += S.insufficient(
            'Why rep 0 counts fewer refills and reads lower at these %d footprints on %s. More reps of these '
            'footprints on a boot with the prefetchers on would show whether the low value repeats.' % (n_out, F1))
    return out
