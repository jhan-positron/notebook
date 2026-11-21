"""Section 3 of asimov-cme-perf.html: latency by footprint.

build(D, V, S) returns the html of the section body.  Every measured number is
read from the data layer D at build time.  Typed values are footprints (test
parameters) and facts of the operator's README, which carry a reference.
"""
import os

from . import data as _data

KEY = 'latency'
TITLE = 'Latency by footprint'

KIB, MIB = 1024, 1024 * 1024

# Typed facts, operator's README (not measurements).  Each use carries a reference.
CME_L1_BYTES = 64 * KIB             # CME L1 data cache
SLC_TOTAL_BYTES = 5 * MIB           # five home nodes of 1 MiB
SLC_WAYS, OCM_WAYS = 16, 4          # ways of a home node, ways locked as OCM
SLC_EST_BYTES = SLC_TOTAL_BYTES * (SLC_WAYS - OCM_WAYS) // SLC_WAYS

SMALL, LARGE, FLUSHED = ('cme-latency-dram-small.csv', 'cme-latency-dram-large.csv',
                         'cme-latency-dram-flushed.csv')
C_SMALL, C_LARGE, C_FLUSHED = ('latency-dram-small.csv', 'latency-dram-large.csv',
                               'latency-dram-flushed.csv')
K_MANY, K_ONCE, K_FLUSH = 'walked many times', 'walked once', 'every line flushed first'

# Footprint groups of the summary tables (test parameters).
GROUPS = [(4 * KIB, 64 * KIB), (96 * KIB, 384 * KIB), (512 * KIB, 768 * KIB),
          (1 * MIB, 3 * MIB), (4 * MIB, 8 * MIB), (16 * MIB, 32 * MIB)]
# Footprints of the dumbbell (test parameters).
PICK = [4 * KIB, 16 * KIB, 48 * KIB, 64 * KIB, 256 * KIB, 384 * KIB, 512 * KIB, 2 * MIB, 8 * MIB, 32 * MIB]


def n3(v):
    return '%.3f' % v


def c4(v):
    return '%.4f' % v


def c2(v):
    return '%.2f' % v


def rng(vals, f=n3):
    """'lo to hi' of a list, or the one value when all are equal after formatting."""
    lo, hi = f(min(vals)), f(max(vals))
    return lo if lo == hi else '%s to %s' % (lo, hi)


def f1d(v):
    return '%.1f' % v


# Print steps of the CSV columns (file format, not measurements): a counter column
# has four decimals, a time column has three.
CNT_STEP, NS_STEP = 0.0001, 0.001
# The page rule of the repeatability subsection: a difference below this share of
# the value is not larger than the repeat difference of two latency rows inside one boot.
REPEAT_PCT = 1.0


def nw(text):
    """A table cell that does not wrap."""
    return '<span style="white-space:nowrap">%s</span>' % text


def span_label(V, lo, hi):
    return '%s to %s' % (V.size_label(lo), V.size_label(hi))


def build(D, V, S):
    F1 = {r['size']: r for r in D.chain_sweep('F1')}
    F2 = {r['size']: r for r in D.chain_sweep('F2')}
    CORE = {r['size']: r for r in D.core_chain if not r.get('control') and r['kind'] != K_FLUSH}
    sizes = sorted(F2)
    fl = {'F1': D.chain_row('F1', 8 * MIB, K_FLUSH), 'F2': D.chain_row('F2', 8 * MIB, K_FLUSH),
          'core': D.core_row(8 * MIB, K_FLUSH)}
    pairs = {(p['size'], p['kind']): p for p in D.chain_pairs}
    sweep_pairs = [pairs[(s, F2[s]['kind'])] for s in sizes]
    rt = D.rt_ns
    bs = D.baseline_summary['all']
    steps = {s['series']: s for s in D.chain_steps['steps']}
    st_f1, st_f2, st_core = steps['CME on boot F1'], steps['CME on boot F2'], steps['core on boot F1']
    l3_bytes = [c for c in D.platform['caches'] if c['level'] == 3][0]['size_bytes']
    caches = D.platform['caches']
    n1, n2 = D.boot_name['F1'], D.boot_name['F2']          # 'boot F1 (prefetchers on)'
    N1, N2 = n1[0].upper() + n1[1:], n2[0].upper() + n2[1:]

    def grp(tab, lo, hi):
        return [tab[s] for s in sizes if lo <= s <= hi]

    def lab(s):
        return V.size_label(s)

    # ---------------------------------------------------------------- references
    def fref(boot, name):
        blk = D.latblocks(boot, name)[0]
        last = blk['line']
        for e in blk['sizes'].values():
            last = max([last, e['best_line']] + [r['line'] for r in e['reps']])
        rel = os.path.relpath(os.path.join(_data.BOOTDIR[boot], name), _data.ROOT)
        log = D.log_lines(boot, name)
        cmd = (' The command is at line %s of <code>log.txt</code> in the same folder.'
               % ', '.join(str(x) for x in log)) if log else ''
        return S.ref('file:%s:%s' % (boot, name),
                     'Boot %s, file <code>%s</code>, lines %d to %d.%s' % (boot, rel, blk['line'], last, cmd))

    r_s1, r_l1, r_f1 = fref('F1', SMALL), fref('F1', LARGE), fref('F1', FLUSHED)
    r_s2, r_l2, r_f2 = fref('F2', SMALL), fref('F2', LARGE), fref('F2', FLUSHED)
    r_cs, r_cl, r_cf = fref('F1', C_SMALL), fref('F1', C_LARGE), fref('F1', C_FLUSHED)
    readme1 = os.path.relpath(os.path.join(_data.RUN['F1'], 'README.md'), _data.ROOT)
    readme2 = os.path.relpath(os.path.join(_data.RUN['F2'], 'README.md'), _data.ROOT)
    r_caches = S.ref('readme:F1:caches',
                     "Operator's README of boot F1, <code>%s</code>, lines 348 to 349: the SLC is five home nodes "
                     'of 1 MiB, the firmware locks 4 of 16 ways of each as OCM, and the CME has a 64 KiB L1 data '
                     'cache.' % readme1)
    r_pf = S.ref('readme:F2:prefetchers',
                 "Operator's README of boot F2, <code>%s</code>, lines 18 to 25: the firmware sets "
                 'IMP_CPUECTLR_EL1 bit 48 (core data prefetchers off) and IMP_CMECFG_EL1 bit 28 (CME prefetcher '
                 'off) on CPUs 2 to 9.' % readme2)
    r_snoop = S.ref('readme:F1:snoop',
                    "Operator's README of boot F1, <code>%s</code>, line 240: a CME L1 refill can be supplied by "
                    "a core's cache in the cluster." % readme1)
    r_sys = S.ref('sysinfo:F1:caches',
                  'Boot F1, file <code>%s</code>, lines %d to %d: the cache sizes that Linux reports for CPU 2.'
                  % (os.path.relpath(os.path.join(_data.BOOTDIR['F1'], caches[0]['src']), _data.ROOT),
                     caches[0]['line'], caches[-1]['line']))
    r_src = S.ref('src:latency.c:walks',
                  'Source file <code>latency.c</code>, lines 241 to 242 (two untimed walks before the first '
                  'rep) and lines 244 to 258 (the timed walks of each chain kind).')
    r_perf = S.ref('src:common.h',
                   'Source file <code>common.h</code>, lines 462 to 494: the counter read, start and stop of the '
                   'latency test. Each is a system call (read or ioctl).')
    r_proj = S.ref('readme:project:flush',
                   'Project file <code>README.md</code>, lines 119 to 123: what the flush before a timed walk '
                   'removes.')
    r_kern = S.ref('src:kern-chain',
                   'Source file <code>cme_kern.S</code>, lines 114 to 126 (the loop of the chain load: LD1D, '
                   'LASTB) and lines 128 to 140 (the loop of the round-trip baseline: a register copy, LASTB).')

    #---------------------------------------------------------------- terms
    S.term('CME', 'the Arm C1-SME2 matrix engine unit. One CME serves one cluster of two cores.')
    S.term('core', 'one Arm C1-Nano processor core. The core rows run the same latency test with ordinary '
                   'core loads, on boot F1 only.')
    t_test = S.term('latency test', 'the program <code>latency.c</code>. It links the 64-byte lines of a buffer '
                                    'into a chain in random order and times a walk over the chain.')
    t_load = S.term('chain load', 'one load of the latency test. The value that it reads is the address of the '
                                  'next load. Its time is given in ns per load.')
    t_fp = S.term('footprint', 'the size of the buffer that a chain covers. The chain has one member per '
                               '64-byte line.')
    t_rt = S.term('round-trip baseline', 'the <code>cme-roundtrip</code> row. Each step moves a value from a '
                                         'core register to a CME register and back (DUP and LASTB). It reads '
                                         'no memory.')
    t_br = S.term('bracket time', 'the time between two clock reads in C around the call of the test loop, '
                                  'divided by the loads.')
    t_sp = S.term('span time', 'the time between two counter reads inside the test loop, after the CME enters '
                               'streaming mode and before it leaves, divided by the loads.')
    t_rep = S.term('rep', 'one timed measurement. The page quotes the best rep, which is the rep with the '
                          'lowest bracket time.')
    min_loads = D.latblocks('F2', SMALL)[0]['header']['loads']
    t_many = S.term(K_MANY, 'a chain kind. One chain is walked again and again inside a rep until at least '
                            '%s loads are done.' % V.num(min_loads, 0))
    t_once = S.term(K_ONCE, 'a chain kind. Two untimed walks of a first chain load the lines into the caches. Each timed '
                            'rep then walks another chain over the same lines exactly once.')
    t_fl = S.term(K_FLUSH, 'a chain kind. It is "walked once" with one more step: every line is removed '
                           'from the caches (instruction DC CIVAC) before each timed walk.')
    t_rd = S.term('read refill', 'a line brought into the CME L1 for a load that missed, counted per load.')
    t_pf = S.term('prefetch refill', "a line brought into the CME L1 by the CME's hardware prefetcher, "
                                     'counted per load.')
    t_wr = S.term('write refill', 'a line brought into the CME L1 for a store that missed, counted per load.')
    t_in = S.term('inner refill', 'a CME L1 refill whose line came from a cache inside the cluster, counted '
                                  'per load. It counts loads and prefetches alike.')
    t_out = S.term('outer refill', 'a CME L1 refill whose line came from outside the cluster (the mesh), '
                                   'counted per load. It counts loads and prefetches alike.')
    t_l3 = S.term('cluster L3', 'the level 3 cache that the two cores of a cluster and their CME share.')
    t_slc = S.term('SLC', 'the system-level cache in the home nodes of the mesh.')
    t_dram = S.term('DRAM model', "the emulator's model of main memory. Its timing is not silicon timing.")
    t_snoop = S.term('snoop', 'a request to another cache in the cluster for a line that it holds.')
    S.term('OCM', 'on-chip memory: memory inside the home nodes of the mesh, made from cache ways that the '
                  'firmware locks.')
    S.term('mesh', 'the network that joins the clusters, the home nodes and the memory.')
    S.term('home node', 'a mesh node that holds a part of the SLC and of the OCM.')
    S.term('streaming mode', 'the processor mode in which vector instructions run on the CME.')
    t_spread = S.term('rep spread', 'the highest minus the lowest bracket time over the reps of one row.')
    t_kern = S.term('kernel', 'one test loop written in assembly in the file <code>cme_kern.S</code>. On this '
                              'page the word never means the Linux kernel.')

    out = []
    brk = st_f2['to_size']                    # the smallest footprint that is walked once
    f1_of = lambda p: p['f1_minus_f2']

    def modes(rows):
        """The row names of the CSV file that the given chain rows come from, as code."""
        names = []
        for r in rows:
            for x in r['reps']:
                if x['mode'] not in names:
                    names.append(x['mode'])
        names = ['<code>%s</code>' % m for m in names]
        return names[0] if len(names) == 1 else '%s and %s' % (', '.join(names[:-1]), names[-1])

    def seg(tab, key='best', src=None):
        """Points of one curve as two lists: walked many times, walked once."""
        src = sizes if src is None else src
        return ([(s, tab[s][key]) for s in src if s < brk], [(s, tab[s][key]) for s in src if s >= brk])

    def lines(specs, src=None):
        """Two series per curve (same name and color), so that the line breaks where the chain kind differs."""
        ser_ = []
        for name, color, tab, key in specs:
            for part in seg(tab, key, src):
                ser_.append(dict(name=name, color=color, points=part))
        return ser_

    def at(i, s, text=None, pos=None):
        """A direct label on curve i at footprint s."""
        d = dict(series=2 * i + (1 if s >= brk else 0), x=s)
        if text:
            d['text'] = text
        if pos:
            d['pos'] = pos
        return d

    many_rows = [F2[s] for s in sizes if s < brk]
    once_rows = [F2[s] for s in sizes if s >= brk]
    core_many = [CORE[s] for s in sizes if s < brk]
    core_once = [CORE[s] for s in sizes if s >= brk]
    last = sizes[-1]

    # ================================================================ key points
    gA, gB, gD, gF = (grp(F2, *GROUPS[0]), grp(F2, *GROUPS[1]), grp(F2, *GROUPS[3]), grp(F2, *GROUPS[5]))
    slower = []
    for p in sweep_pairs:
        if p['f1_minus_f2'] <= 0:
            break
        slower.append(p)
    faster = [p for p in sweep_pairs if p['f1_minus_f2'] <= 0]
    max_pf = max(F1.values(), key=lambda r: r['hwprf'])
    out.append(S.takeaways([
        'On %s the %s takes these times:' % (n2, t_load),
        ['%s: %s ns.' % (span_label(V, *g), rng([r['best'] for r in rows_]))
         for g, rows_ in ((GROUPS[0], gA), (GROUPS[1], gB), (GROUPS[3], gD), (GROUPS[5], gF))],
        'The %s is a separate measurement with no memory access. It is %s ns per step on both boots.' % (
            t_rt, n3(rt)),
        'The rows that fit the CME L1 read %s ns above it. This is a measured difference between two '
        'kernels. It is not a memory-access time (%s).' % (rng([r['above_rt'] for r in gA]), S.xref('lat-above')),
        'On %s the same test is slower at every %s from %s to %s, by %s ns. The CME counts up to %s prefetch '
        'refills per load there (%s).' % (
            n1, t_fp, slower[0]['label'], slower[-1]['label'], rng([p['f1_minus_f2'] for p in slower]),
            c2(max_pf['hwprf']), max_pf['label']),
    ]))

    # ================================================================ 4.1 the curve
    out.append(S.h3('lat-curve', 'Chain load against footprint'))

    def within(g):
        v = [r['best'] for r in g]
        return n3(max(v) - min(v))

    gE = grp(F2, *GROUPS[4])
    f1_low = min(D.chain_sweep('F1'), key=lambda r: r['above_rt'])
    f1_many = [F1[s]['best'] for s in sizes if s < brk]
    f1_once = [F1[s]['best'] for s in sizes if s >= brk]
    up = lambda v: all(b > a for a, b in zip(v, v[1:]))
    out.append(S.bullets([
        'On %s the chain load stays inside a narrow band in three footprint ranges:' % n2,
        ['%s: within %s ns.' % (span_label(V, *g), within(rows_))
         for g, rows_ in ((GROUPS[0], gA), (GROUPS[1], gB), (GROUPS[3], gD))],
        'From %s to %s it rises by %s ns.' % (lab(GROUPS[4][0]), lab(GROUPS[5][1]),
                                              n3(F2[GROUPS[5][1]]['best'] - F2[GROUPS[4][0]]['best'])),
        'On %s %s. The lowest row (%s) is %s ns above it.' % (
            n1, 'every row is above the baseline' if f1_low['above_rt'] > 0 else 'not every row is above the baseline',
            f1_low['label'], n3(f1_low['above_rt'])),
        'The %s curve %s %s ns at %s. It reads %s ns at %s. It %s %s ns at %s.' % (
            n1, 'rises to' if up(f1_many) else 'reads', n3(st_f1['from_ns']), lab(st_f1['from_size']),
            n3(st_f1['to_ns']), lab(st_f1['to_size']), 'rises again to' if up(f1_once) else 'reads',
            n3(F1[last]['best']), lab(last)),
    ]))

    f2_steps = [(a, b, F2[b]['best'] - F2[a]['best']) for a, b in zip(sizes, sizes[1:])]
    big_a, big_b, big_step = max(f2_steps, key=lambda t: t[2])
    l1p = pairs[(CME_L1_BYTES, F2[CME_L1_BYTES]['kind'])]
    ser = lines([('CME, %s' % n2, 'f2', F2, 'best'), ('CME, %s' % n1, 'f1', F1, 'best'),
                 ('the core, boot F1', 'core', CORE, 'best')])
    caps = [(CME_L1_BYTES, 'CME L1 %s' % lab(CME_L1_BYTES)), (l3_bytes, 'cluster L3 %s' % lab(l3_bytes)),
            (SLC_EST_BYTES, 'SLC %s est.' % lab(SLC_EST_BYTES))]
    xr = (sizes[0], last * 3.2)               # room at the right for the end labels
    svg = V.line_chart(
        ser, x='log2', xticks=sizes, xrange=xr, xlabel='footprint', ylabel='chain load, ns per load', yunit='ns',
        hlines=[(rt, 'round-trip baseline %s ns' % n3(rt), 'left')], vlines=caps,
        labels=[at(0, 256 * KIB), at(0, 3 * MIB),
                at(0, last, 'CME, boot F2: %s ns' % n3(F2[last]['best']), 'ur'),
                at(1, 384 * KIB), at(1, 512 * KIB),
                at(1, last, 'CME, boot F1: %s ns' % n3(F1[last]['best']), 'lr'),
                at(2, 16 * KIB), at(2, 128 * KIB),
                at(2, last, 'the core: %s ns' % n3(CORE[last]['best']), 'right')],
        gaps=[dict(x=big_b, y0=F2[big_a]['best'], y1=F2[big_b]['best'], dx=-12,
                   text=V.signed(big_step, 3, 'ns')),
              dict(x=CME_L1_BYTES, y0=l1p['f2'], y1=l1p['f1'], dx=-12,
                   text=V.signed(l1p['f1_minus_f2'], 3, 'ns'))],
        annotations=[dict(x=st_core['to_size'], y=st_core['to_ns'],
                          text='the lines break here: walked many times\nup to %s, walked once from %s' % (
                              lab(st_f1['from_size']), lab(st_f1['to_size'])), dx=120, dy=30)],
        height=440)
    out.append(S.fig(
        svg,
        'Chain load (best bracket time) against footprint. CME on %s, rows %s of <code>%s</code> and rows %s '
        'of <code>%s</code> %s %s. CME on %s, the same rows %s %s. The core on boot F1, rows %s of '
        '<code>%s</code> and rows %s of <code>%s</code> %s %s. The grey markers are capacities, not '
        'measurements: the CME L1 and the SLC est. are from the operator\'s README %s, the cluster L3 is from '
        '<code>sysinfo.txt</code> %s. The two brackets with bold numbers mark the largest step of boot F2 (%s '
        'to %s) and boot F1 minus boot F2 at %s.' % (
            n2, modes(many_rows), SMALL, modes(once_rows), LARGE, r_s2, r_l2, n1, r_s1, r_l1,
            modes(core_many), C_SMALL, modes(core_once), C_LARGE, r_cs, r_cl, r_caches, r_sys,
            lab(big_a), lab(big_b), l1p['label']),
        'Only the blue line stays within %s ns of the round-trip baseline up to the CME L1 size. The orange '
        'line is %s ns above it at %s and %s ns above it at %s.' % (
            n3(max(r['above_rt'] for r in gA)), n3(F1[sizes[0]]['above_rt']), F1[sizes[0]]['label'],
            n3(F1[CME_L1_BYTES]['above_rt']), F1[CME_L1_BYTES]['label'])))

    rows, kind = [], None
    for lo, hi in GROUPS:
        a, b, c = grp(F2, lo, hi), grp(F1, lo, hi), grp(CORE, lo, hi)
        if a[0]['kind'] != kind:
            kind = a[0]['kind']
            rows.append(kind[0].upper() + kind[1:])
        rows.append([nw(span_label(V, lo, hi)), rng([r['best'] for r in a]),
                     rng([r['above_rt'] for r in a]), rng([r['best'] for r in b]),
                     rng([r['above_rt'] for r in b]), rng([r['best'] for r in c])])
    out.append(S.table(
        ['Footprint', 'CME, boot F2, ns', 'Boot F2 minus baseline, ns', 'CME, boot F1, ns',
         'Boot F1 minus baseline, ns', 'The core, boot F1, ns'], rows,
        caption='Chain load by footprint group: lowest to highest best bracket time of the group, in ns per '
                'load. Files as in Figure %d.' % (S.next_fig() - 1),
        note='"Minus baseline" is the chain load minus the round-trip baseline of %s ns. It is a measured '
             'difference between two kernels (%s). The core has no such baseline.'
             % (n3(rt), S.xref('lat-above'))))
    bms2, bms1 = D.bracket_minus_span['F2'], D.bracket_minus_span['F1']
    nrep_many = sorted({r['n_reps'] for b_ in ('F1', 'F2') for r in D.chain_sweep(b_) if r['kind'] == K_MANY})
    nrep_once = sorted({r['n_reps'] for b_ in ('F1', 'F2') for r in D.chain_sweep(b_) if r['kind'] == K_ONCE})
    ints = lambda v: rng(v, lambda x: '%d' % x)
    out.append(S.p('How to read the rows:'))
    out.append(S.bullets([
        'The %s builds a chain over a buffer. The %s is the size of that buffer.' % (t_test, t_fp),
        'A CME chain load is one vector load (LD1D) and one move of the value back to a core register (LASTB).',
        'Rows up to %s are %s. Rows from %s are %s %s.' % (
            lab(st_f2['from_size']), t_many, lab(st_f2['to_size']), t_once, r_src),
        'Each footprint has %s timed measurements when it is walked many times and %s when it is walked once. '
        'Each one is a %s.' % (ints(nrep_many), ints(nrep_once), t_rep),
        'The table quotes the %s of the best rep.' % t_br,
        'The %s of the same rep is %s to %s ns per load lower on %s, over all rep rows.' % (
            t_sp, n3(bms2['all_lo']), n3(bms2['all_hi']), n2),
        'It is %s to %s ns per load lower on %s.' % (n3(bms1['all_lo']), n3(bms1['all_hi']), n1),
        'The largest step on %s is between %s and %s: %s ns.' % (n2, lab(big_a), lab(big_b),
                                                                V.signed(big_step, 3)),
        'On %s the chain load still rises by %s ns from %s to %s. So the curve is not flat at its last point.'
        % (n2, n3(F2[32 * MIB]['best'] - F2[16 * MIB]['best']), lab(16 * MIB), lab(32 * MIB)),
    ]))

    # ================================================================ 4.2 minus baseline
    out.append(S.h3('lat-above', 'Chain load minus the round-trip baseline'))
    neg = [p for p in sweep_pairs if p['f2_above_rt_minus_core'] < 0]
    pos = [p for p in sweep_pairs if p['f2_above_rt_minus_core'] >= 0]
    out.append(S.bullets([
        'The %s reads %s ns per step in all %d CME latency files of the two boots. It is %s core cycles per '
        'step.' % (t_rt, rng([bs['rt_best_lo'], bs['rt_best_hi']]), bs['n_files'],
                   rng([bs['rt_cycles_lo'], bs['rt_cycles_hi']], c2)),
        'On %s the chain load is %s ns above the baseline at %s.' % (
            n2, rng([r['above_rt'] for r in gA]), span_label(V, *GROUPS[0])),
        'It is %s ns above the baseline at %s.' % (rng([r['above_rt'] for r in gB]), span_label(V, *GROUPS[1])),
    ]))
    ser2 = lines([('CME minus baseline, %s' % n2, 'f2', F2, 'above_rt'),
                  ('CME minus baseline, %s' % n1, 'f1', F1, 'above_rt'),
                  ('the core, chain load, boot F1', 'core', CORE, 'best')])
    pos_mid = pos[len(pos) // 2]
    svg = V.line_chart(
        ser2, x='log2', xticks=sizes, xrange=xr, xlabel='footprint', ylabel='ns per load', yunit='ns',
        vlines=caps,
        labels=[at(0, 2 * MIB), at(1, 384 * KIB), at(2, 32 * KIB), at(2, 2 * MIB),
                at(2, last, 'the core: %s ns' % n3(CORE[last]['best']), 'ur'),
                at(0, last, 'CME, boot F2: %s ns' % n3(F2[last]['above_rt']), 'right'),
                at(1, last, 'CME, boot F1: %s ns' % n3(F1[last]['above_rt']), 'lr')],
        annotations=[dict(x=pos_mid['size'], y=F2[pos_mid['size']]['above_rt'],
                          text='%s to %s:\nblue is above aqua\nby %s ns' % (
                              pos[0]['label'], pos[-1]['label'],
                              rng([p['f2_above_rt_minus_core'] for p in pos])), dx=8, dy=-46)],
        height=400)
    out.append(S.fig(
        svg,
        'Chain load minus the round-trip baseline of the same file, for the CME on both boots, beside the '
        'chain load of the core on boot F1. Rows and files as in Figure %d %s %s %s %s %s %s.' % (
            S.next_fig() - 1, r_s2, r_l2, r_s1, r_l1, r_cs, r_cl),
        'With the baseline subtracted, the blue line of %s is %s ns above the aqua line of the core from %s to '
        '%s. It is %s ns below the aqua line at the other %d of %d footprints. The two lines are from two '
        'boots with different prefetcher settings.' % (
            n2, rng([p['f2_above_rt_minus_core'] for p in pos]), pos[0]['label'], pos[-1]['label'],
            rng([-p['f2_above_rt_minus_core'] for p in neg]), len(neg), len(sweep_pairs))))
    small_neg = [p for p in neg if -p['f2_above_rt_minus_core'] < p['f2_spread_ns']]
    items = [
        'The chain load and the baseline are two %ss %s. A kernel is one test loop in <code>cme_kern.S</code>.'
        % (t_kern, r_kern),
        'A step of the chain kernel is a load (LD1D) and a move of the value back to the core (LASTB).',
        'A step of the baseline kernel is a register copy (DUP) and the same move (LASTB). It reads no memory.',
    ]
    if bs['rt_counters_zero']:
        items.append('Every refill counter reads zero in every rep of the baseline.')
    items += [
        'The cycle columns of the baseline do not read zero. They read %s core cycles and %s CME cycles per '
        'step.' % (rng([bs['rt_cycles_lo'], bs['rt_cycles_hi']], c2),
                   rng([bs['rt_cme_cycles_lo'], bs['rt_cme_cycles_hi']], c4)),
        'So "chain load minus baseline" is a measured difference between two kernels. It is the time of a step '
        'with a load minus the time of a step with a register copy.',
        'The rows do not show that the two kernels share one fixed cost per step. So the rows do not show '
        'that the chain load contains the baseline time, or that the difference is the time of the memory '
        'access.',
        'The core in its own L1 takes %s ns per load (%s, boot F1).' % (
            rng([CORE[s]['best'] for s in sizes if s <= caches[0]['size_bytes']]),
            span_label(V, sizes[0], caches[0]['size_bytes'])),
        'The CME chain load in its own L1 reads %s ns above the baseline (%s, boot F2).' % (
            rng([r['above_rt'] for r in gA]), span_label(V, *GROUPS[0])),
        'The blue line is above the aqua line only from %s to %s, by %s ns.' % (
            pos[0]['label'], pos[-1]['label'], rng([p['f2_above_rt_minus_core'] for p in pos])),
    ]
    for p in small_neg:
        items.append('At %s the blue line is %s ns below the aqua line. That is less than the %s of that row '
                     '(%s ns).' % (p['label'], n3(-p['f2_above_rt_minus_core']), t_spread, n3(p['f2_spread_ns'])))
    items += [
        'This comparison crosses two boots. The core rows are from boot F1, with the prefetchers on.',
        'On boot F1 alone, the CME chain load is %s ns above the core at every footprint from %s to %s.' % (
            rng([p['f1_minus_core'] for p in sweep_pairs]), sweep_pairs[0]['label'], sweep_pairs[-1]['label']),
        'With every line flushed first (%s) the CME on boot F1 is %s ns above the core.' % (
            pairs[(8 * MIB, K_FLUSH)]['label'], n3(pairs[(8 * MIB, K_FLUSH)]['f1_minus_core'])),
    ]
    out.append(S.bullets(items))
    out.append(S.insufficient(
        'Whether "chain load minus baseline" is the time of the memory access. The two boots have no row '
        'that measures the cost that the two kernels share outside the memory access. A calibration of that '
        'shared cost would be needed to read the difference as memory-access time. A kernel with a chain of '
        'loads that stays in the CME registers would give the load time without the move to the core.'))
    out.append(S.insufficient(
        'Boot F2 has no core rows. A core latency run on a boot with the prefetchers off would give the '
        'core against the CME on one boot without prefetch.'))

    # ================================================================ 4.3 counters
    out.append(S.h3('lat-serve', 'Refill counters per load at each footprint'))
    cB_rd, cB_in, cB_out = ([r['rd'] for r in gB], [r['inner'] for r in gB], [r['outer'] for r in gB])
    f1_mid = [F1[s] for s in sizes if 8 * KIB <= s <= 384 * KIB]
    gC = grp(F2, *GROUPS[2])
    out_big = [F2[s] for s in sizes if s >= GROUPS[3][0]]
    out.append(S.bullets([
        'On %s the refill counts per load differ by footprint group:' % n2,
        ['%s: the rows count at most %s refills per load.' % (
            span_label(V, *GROUPS[0]), c4(max(r['refills'] for r in gA))),
         '%s: the rows count %s inner refills per load.' % (
             span_label(V, *GROUPS[1]), rng(cB_in, c4)),
         '%s and %s: the rows count refills of both sources, with %s and %s outer refills per load.' % (
             gC[0]['label'], gC[-1]['label'], c4(gC[0]['outer']), c4(gC[-1]['outer'])),
         '%s to %s: the rows count %s outer refills per load.' % (
             out_big[0]['label'], out_big[-1]['label'], rng([r['outer'] for r in out_big], c4))],
        'On %s the CME refills its L1 %s times per load from %s to %s.' % (
            n1, rng([r['refills'] for r in f1_mid], c2), f1_mid[0]['label'], f1_mid[-1]['label']),
        '%s of these refills per load are prefetch refills.' % rng([r['hwprf'] for r in f1_mid], c2),
    ]))

    f1_sweep = D.chain_sweep('F1')
    cmax = max(max(r[k] for r in f1_sweep) for k in ('hwprf', 'inner', 'outer'))
    ytop = 5.0 * (int(cmax / 5.0) + 1)        # one common scale for the three lower panels

    def cser(key):
        return lines([(n2, 'f2', F2, key), (n1, 'f1', F1, key)])

    def top_f1(key):
        r = max(f1_sweep, key=lambda q: q[key])
        return at(1, r['size'], 'boot F1: %s' % c2(r[key]))

    f2_pf_zero = all(v == 0 for r in D.chain_sweep('F2') for v in r['hwprf_reps'])
    f2_in = max(D.chain_sweep('F2'), key=lambda q: q['inner'])
    svg = V.small_multiples([
        dict(ylabel='read refills per load (own scale)', series=cser('rd'), hlines=[(1.0, 'one per load')],
             yrange=(0, 1.2), yfmt=c4),
        dict(ylabel='prefetch refills per load', series=cser('hwprf'), yfmt=c4, yrange=(0, ytop),
             labels=[top_f1('hwprf')],
             annotations=([dict(x=2 * MIB, y=0.0, text='boot F2: 0 at every footprint', dx=0, dy=-22)]
                          if f2_pf_zero else [])),
        dict(ylabel='inner refills per load', series=cser('inner'), yfmt=c4, yrange=(0, ytop),
             labels=[top_f1('inner'), at(0, f2_in['size'], 'boot F2: %s' % c4(f2_in['inner']))]),
        dict(ylabel='outer refills per load', series=cser('outer'), yfmt=c4, yrange=(0, ytop),
             labels=[top_f1('outer'), at(0, last, 'boot F2: %s' % c4(F2[last]['outer']), 'above')]),
    ], x='log2', xticks=sizes, xlabel='footprint', vlines=caps, panel_height=165)
    out.append(S.fig(
        svg,
        'Refills of the CME L1 per load, at the best rep of each footprint, under the footprint axis of '
        'Figure %d. Top two panels: by cause (%s, %s). Bottom two panels: by source (%s, %s). The top panel '
        'has its own scale (0 to 1.2). The three lower panels share one scale (0 to %d). The lines break '
        'where the chain kind differs. %s: <code>%s</code> and <code>%s</code> %s %s. %s: the same files %s '
        '%s.' % (S.next_fig() - 2, t_rd, t_pf, t_in, t_out, ytop, N2, SMALL, LARGE, r_s2, r_l2, N1, r_s1, r_l1),
        'On boot F2 the blue lines never pass one refill per load, and the prefetch line is zero. On boot F1 '
        'the prefetch, inner and outer lines reach %s to %s refills per load.' % (
            c2(min(max(r[k] for r in f1_sweep) for k in ('hwprf', 'inner', 'outer'))), c2(cmax))))

    rows = []
    for lo, hi in GROUPS:
        a, b = grp(F2, lo, hi), grp(F1, lo, hi)
        rows.append([nw(span_label(V, lo, hi))]
                    + [rng([r[k] for r in a], c4) for k in ('rd', 'inner', 'outer')]
                    + [rng([r[k] for r in b], c2) for k in ('rd', 'hwprf', 'inner', 'outer')])
    out.append(S.table(
        ['Footprint', 'Boot F2 read', 'Boot F2 inner', 'Boot F2 outer', 'Boot F1 read', 'Boot F1 prefetch',
         'Boot F1 inner', 'Boot F1 outer'], rows,
        caption='Refills per load by footprint group, lowest to highest over the best reps of the group. '
                'Files as in Figure %d.' % (S.next_fig() - 1),
        note='Boot F2 counts %s prefetch refills per load in every rep row of these files.' % rng(
            [v for r in D.chain['F2'] for v in r['hwprf_reps']], c4)))

    out.append(S.p('%s, by rows:' % N2))
    out.append(S.bullets([
        '%s: the rows count %s inner refills per load and at most %s outer refills per load. '
        'The CME L1 holds %s (operator\'s README) %s. So these footprints fit in it.' % (
            span_label(V, *GROUPS[0]), rng([r['inner'] for r in gA], c4),
            '%.5f' % max(r['outer'] for r in gA), lab(CME_L1_BYTES), r_caches),
        '%s: the rows count %s read refills per load. Of these, %s per load are inner and %s per load are '
        'outer. So the inner counter counts most refills of these rows.' % (
            span_label(V, *GROUPS[1]), rng(cB_rd, c4), rng(cB_in, c4), rng(cB_out, c4)),
        ['The inner counter does not say which cache inside the cluster.',
         'It can be the %s, which holds %s %s.' % (t_l3, lab(l3_bytes), r_sys),
         'It can also be a %s of a core\'s cache (operator\'s README) %s.' % (t_snoop, r_snoop),
         '%s reads the L3 events of these footprints.' % S.xref('l3', 'The cluster L3 as seen by the CME', cap=True)],
        '%s and %s: the outer refills are %s and %s per load. The inner refills are %s and %s per load. So '
        'these two rows count refills of both sources.' % (
            gC[0]['label'], gC[-1]['label'], c4(gC[0]['outer']), c4(gC[-1]['outer']),
            c4(gC[0]['inner']), c4(gC[-1]['inner'])),
        '%s: the rows count %s outer refills per load. So the outer counter counts most refills of these '
        'rows. The chain load stays within %s ns over the group.' % (
            span_label(V, *GROUPS[3]), rng([r['outer'] for r in gD], c4), within(gD)),
        '%s: the chain load rises from %s ns to %s ns with %s outer refills per load.' % (
            span_label(V, *GROUPS[4]), n3(gE[0]['best']), n3(gE[-1]['best']),
            rng([r['outer'] for r in gE], c4)),
        '%s and %s: the outer refills are %s and %s per load.' % (
            gF[0]['label'], gF[-1]['label'], c4(gF[0]['outer']), c4(gF[-1]['outer'])),
        'Every count of this list is a total of a rep. A total does not say which load caused which refill.',
    ]))
    out.append(S.hyp(
        'The %s supplies the outer refills from %s to %s (%s per load). Its size is %s est.: %s in five home '
        'nodes, with %d of %d ways of each node locked as OCM (operator\'s README) %s. The CME counters say '
        'only "outside the cluster". In support, the chain load stays within %s ns from %s to %s and reads %s '
        'ns more at %s.' % (
            t_slc, lab(GROUPS[3][0]), lab(GROUPS[3][1]), rng([r['outer'] for r in gD], c4), lab(SLC_EST_BYTES),
            lab(SLC_TOTAL_BYTES), OCM_WAYS, SLC_WAYS, r_caches, within(gD), lab(GROUPS[3][0]),
            lab(GROUPS[3][1]), n3(F2[4 * MIB]['best'] - F2[3 * MIB]['best']), lab(4 * MIB)),
        'A walked-once row of %s to %s under the mesh counters. Requests that the home nodes answer without a '
        'cache miss would confirm it. Requests that the home nodes pass on to the %s would reject it.' % (
            lab(GROUPS[3][0]), lab(GROUPS[3][1]), t_dram)))

    r256 = F2[256 * KIB]
    fall = [F2[s] for s in sizes if 96 * KIB <= s <= 256 * KIB]
    last_step = fall[-2]['best'] - fall[-1]['best']
    noisy_end = fall[-1]['spread_ns'] > last_step       # the last step is inside the rep spread of its row
    firm = fall[:-1] if noisy_end else fall
    items = [
        'From %s to %s the chain load falls as the footprint grows: %s ns.' % (
            firm[0]['label'], firm[-1]['label'], ', '.join(n3(r['best']) for r in firm)),
        'The read, inner and outer counters of these best reps differ by at most %s per load. They do not '
        'explain the fall.' % c4(max(max(r[k] for r in firm) - min(r[k] for r in firm)
                                     for k in ('rd', 'inner', 'outer'))),
        'Insufficient data: no validated counter names the source of these inner refills. %s gives the exploratory '
        'L3 event counts of the same footprints, and %s gives one hypothesis with its test.' % (
            S.xref('l3-scatter', cap=True), S.xref('open-l3')),
    ]
    if noisy_end:
        items.append(
            'The %s row reads %s ns. Its %s is %s ns. That is more than its distance of %s ns to the %s row.'
            % (fall[-1]['label'], n3(fall[-1]['best']), t_spread, n3(fall[-1]['spread_ns']), n3(last_step),
               fall[-2]['label']))
    if r256['outer_reps'].index(min(r256['outer_reps'])) == r256['reps_ns'].index(min(r256['reps_ns'])):
        items.append(
            'At %s the %d reps read %s ns and count %s outer refills per load. The rep with the fewest '
            'outer refills is the fastest.' % (
                r256['label'], r256['n_reps'], ', '.join(n3(v) for v in r256['reps_ns']),
                ', '.join(c4(v) for v in r256['outer_reps'])))
    out.append(S.p('Observations on the %s to %s rows of %s %s:' % (
        lab(GROUPS[1][0]), lab(GROUPS[1][1]), n2, r_s2)))
    out.append(S.bullets(items))

    in_l1 = [F1[s] for s in sizes if 8 * KIB <= s <= CME_L1_BYTES]
    r32, r384 = F1[32 * KIB], F1[384 * KIB]
    sum_f1 = [v for r in D.chain['F1'] for v in r['counter_sum_diff']]
    sum_f2 = [v for r in D.chain['F2'] for v in r['counter_sum_diff']]
    wr_all = [v for b_ in ('F1', 'F2') for r in D.chain[b_] for v in r['wr_reps']]
    once1 = [F1[s] for s in sizes if s >= st_f1['to_size']]
    out.append(S.p('%s, by rows %s %s:' % (N1, r_s1, r_l1)))
    out.append(S.bullets([
        '%s to %s: the rows count %s refills per load (inner plus outer). %s of them per load are prefetch '
        'refills. %s per load are read refills.' % (
            f1_mid[0]['label'], f1_mid[-1]['label'], rng([r['refills'] for r in f1_mid], c2),
            rng([r['hwprf'] for r in f1_mid], c2), rng([r['rd'] for r in f1_mid], c2)),
        'Footprints that fit the CME L1 still bring lines from outside the cluster. From %s to %s the rows '
        'count %s outer refills per load.' % (in_l1[0]['label'], in_l1[-1]['label'],
                                              rng([r['outer'] for r in in_l1], c2)),
        'The source moves from inner to outer as the footprint grows. The outer refills are %s per load at %s '
        'and %s per load at %s.' % (c2(r32['outer']), r32['label'], c2(r384['outer']), r384['label']),
        '%s to %s (walked once): the prefetch refills are %s per load. The read refills are %s per load.'
        % (once1[0]['label'], once1[-1]['label'], rng([r['hwprf'] for r in once1], c2),
           rng([r['rd'] for r in once1], c4)),
        'The counters by source (inner, outer) and the counters by cause (read, prefetch, write) give the same '
        'total.',
        ['A %s is a line brought into the CME L1 for a store. The rows count %s write refills per load in '
         'every rep row of both boots.' % (t_wr, rng(wr_all, c4)),
         'Inner plus outer minus read, prefetch and write is %s to %s per load in every rep row of boot F1.' % (
             V.signed(min(sum_f1), 4), V.signed(max(sum_f1), 4)),
         'It is %s per load in every rep row of boot F2.' % rng(sum_f2, c4)],
    ]))

    # ================================================================ 4.4 prefetchers
    out.append(S.h3('lat-prefetch', 'Prefetchers on against off'))
    worst = max(sweep_pairs, key=lambda p: p['f1_over_f2'])
    pf = pairs[(8 * MIB, K_FLUSH)]
    out.append(S.bullets([
        'With the prefetchers on, the chain load is %s ns higher at every footprint from %s to %s.' % (
            rng([p['f1_minus_f2'] for p in slower]), slower[0]['label'], slower[-1]['label']),
        'The largest ratio is at %s: boot F1 takes %s times the time of boot F2 (%s ns against %s ns).' % (
            worst['label'], c2(worst['f1_over_f2']), n3(worst['f1']), n3(worst['f2'])),
    ]))
    pick = sorted(set(PICK) | {worst['size']})
    pick_pairs = [pairs[(s, F2[s]['kind'])] for s in pick]
    drows = [dict(header='Walked many times')]
    for p in pick_pairs:
        if p['size'] == st_f2['to_size']:
            drows.append(dict(header='Walked once'))
        drows.append(dict(label=p['label'], sub='%s prefetch refills per load on boot F1' % c2(p['f1_hwprf']),
                          a=p['f2'], b=p['f1'], gap=V.signed(p['f1_minus_f2'], 3, 'ns')))
    drows.append(dict(header='Every line flushed first'))
    drows.append(dict(label=pf['label'], sub='%s prefetch refills per load on boot F1' % c2(pf['f1_hwprf']),
                      a=pf['f2'], b=pf['f1'], gap=V.signed(pf['f1_minus_f2'], 3, 'ns')))
    svg = V.dumbbell(drows, a_name=n2, b_name=n1, a_color='f2', b_color='f1', unit='ns',
                     xlabel='chain load, ns per load', fmt=n3,
                     refs=[(rt, 'round-trip baseline %s ns' % n3(rt))])
    right = [p for p in pick_pairs if f1_of(p) > 0]
    left = ['at %s %s (by %s ns)' % (p['label'], p['kind'], n3(-f1_of(p))) for p in pick_pairs if f1_of(p) <= 0]
    if f1_of(pf) <= 0:
        left.append('at %s with every line flushed first (by %s ns)' % (pf['label'], n3(-f1_of(pf))))
    tk = 'The orange dot is to the right of the blue dot at the %d rows from %s (%s) to %s (%s).' % (
        len(right), right[0]['label'], right[0]['kind'], right[-1]['label'], right[-1]['kind'])
    if left:
        tk += ' It is to the left %s.' % ' and '.join(left)
    out.append(S.fig(
        svg,
        'CME chain load (best bracket time) on %s and on %s at %d rows. The bold number is boot F1 minus '
        'boot F2. Rows %s of <code>%s</code> %s %s, rows %s of <code>%s</code> %s %s, and rows %s of '
        '<code>%s</code> (every line flushed first) %s %s. Where the two dots would overlap, they are drawn '
        'one above the other.' % (
            n2, n1, len(pick_pairs) + 1, modes(many_rows), SMALL, r_s2, r_s1, modes(once_rows), LARGE, r_l2,
            r_l1, modes([fl['F2'], fl['F1']]), FLUSHED, r_f2, r_f1),
        tk))
    rows, kind = [], None
    all_apart = all(p['reps_apart'] for p in pick_pairs + [pf])
    for p in pick_pairs + [pf]:
        if p['kind'] != kind:
            kind = p['kind']
            rows.append(kind[0].upper() + kind[1:])
        row = [p['label'], n3(p['f2']), n3(p['f1']), V.signed(p['f1_minus_f2'], 3),
               c2(p['f1_over_f2']), c4(p['f2_refills']), c2(p['f1_refills']), c2(p['f1_hwprf'])]
        if not all_apart:
            row.append('yes' if p['reps_apart'] else 'no')
        rows.append(row)
    heads16 = ['Footprint', 'Boot F2, ns', 'Boot F1, ns', 'F1 minus F2, ns', 'F1 / F2', 'Boot F2 refills',
               'Boot F1 refills', 'Boot F1 prefetch'] + ([] if all_apart else ['Reps apart'])
    out.append(S.table(
        heads16, rows,
        caption='The rows of Figure %d. Refills are inner plus outer refills per load at the best rep.'
                % (S.next_fig() - 1),
        note=('In all %d rows every rep of one boot is above every rep of the other boot. ' % len(rows_body(rows))
              if all_apart else
              '"Reps apart" is yes when every rep of one boot is above every rep of the other boot. ')
             + 'The tables of %s have every footprint.' % S.xref('lat-table'),
        align='l' + 'r' * (len(heads16) - 1) if all_apart else None))
    items = [
        'The intended difference between the two boots is one firmware setting: boot F2 turns off the data '
        'prefetchers of the cores and the prefetcher of the CME (operator\'s README) %s.' % r_pf,
        'Two more differences are known (%s). The core commands and a self-test ran before the CME commands on '
        'boot F1 only. Each command draws its own physical pages.' % S.xref('setup-boots'),
        'The counters show the setting. Boot F2 counts %s prefetch refills per load in every rep row. Boot '
        'F1 counts %s prefetch refills per load over the best reps.' % (
            rng([v for r in D.chain['F2'] for v in r['hwprf_reps']], c4),
            rng([r['hwprf'] for r in D.chain['F1']], c4)),
        'At %s, which fits the CME L1, boot F2 counts %s refills per load and boot F1 counts %s.' % (
            worst['label'], c4(worst['f2_refills']), c2(worst['f1_refills'])),
    ]
    if faster:
        fpct = [100.0 * -f1_of(p) / p['f2'] for p in faster]
        items.append(
            'At %s boot F1 is lower, by %s ns. The %s of these rows is %s ns.' % (
                ' and '.join(p['label'] for p in faster), rng([-f1_of(p) for p in faster]), t_spread,
                rng([v for p in faster for v in (p['f1_spread_ns'], p['f2_spread_ns'])])))
        if max(fpct) < REPEAT_PCT:
            items.append(
                'These differences are %s %% of the boot F2 values. A difference below %d %% between two '
                'latency rows is not larger than the repeat difference inside one boot (%s).' % (
                    rng(fpct, f1d), REPEAT_PCT, S.xref('glance-repeat')))
    items += [
        'With every line flushed first (%s), boot F1 is lower by %s ns: %s ns against %s ns.' % (
            pf['label'], n3(-pf['f1_minus_f2']), n3(pf['f1']), n3(pf['f2'])),
        'Boot F1 counts %s prefetch refills per load in that row. Boot F2 counts %s prefetch refills and %s '
        'outer refills per load.' % (c2(pf['f1_hwprf']), c4(fl['F2']['hwprf']), c4(pf['f2_outer'])),
    ]
    out.append(S.bullets(items))
    out.append(S.hyp(
        'The CME prefetcher makes the random chain slower. It brings in lines that the chain does not need '
        'next. These refills delay the lines that the chain needs, or remove them from the CME L1. The '
        'counters prove the extra refills. They do not prove the delay.',
        'A boot with only the CME prefetcher off and the core prefetchers on. The firmware turns the CME '
        'prefetcher off with bit 28 of the CME configuration register IMP_CMECFG_EL1 (operator\'s README) '
        '%s. If the chain load of that boot from %s to %s equals the boot F2 rows, the CME prefetcher is the '
        'cause. If it equals the boot F1 rows, the core prefetchers are the cause.' % (
            r_pf, slower[0]['label'], slower[-1]['label'])))
    if faster:
        out.append(S.insufficient(
            'Whether the lower boot F1 values at %s are a gain from the prefetchers. Each setting has one '
            'boot. A second boot of each setting would give the spread from boot to boot.'
            % ' and '.join(p['label'] for p in faster)))

    # ================================================================ 4.5 the step
    out.append(S.h3('lat-step', 'The %s to %s step and the chain kinds' % (
        lab(st_f1['from_size']), lab(st_f1['to_size']))))

    def moves(st):
        return '%s by %s ns' % ('rises' if st['step_ns'] > 0 else 'falls', n3(abs(st['step_ns'])))

    out.append(S.bullets([
        'On %s the CME chain load %s between %s and %s.' % (
            n1, moves(st_f1), lab(st_f1['from_size']), lab(st_f1['to_size'])),
        'On %s it %s. The core %s.' % (n2, moves(st_f2), moves(st_core)),
        'The chain kind differs between these two footprints.',
        'The number of footprints with rows of both kinds is %d.' % len(
            D.chain_steps['sizes_with_both_sweep_kinds']),
    ]))
    zoom = [s for s in sizes if 192 * KIB <= s <= 1 * MIB]
    mid = (st_f2['from_size'] * st_f2['to_size']) ** 0.5
    zl = []
    for i, st in enumerate((st_f2, st_f1, st_core)):
        zl += [at(i, st['from_size']), at(i, st['to_size'])]
    svg = V.line_chart(
        lines([('CME, %s' % n2, 'f2', F2, 'best'), ('CME, %s' % n1, 'f1', F1, 'best'),
               ('the core, boot F1', 'core', CORE, 'best')], zoom),
        x='log2', xticks=zoom, xlabel='footprint', ylabel='chain load, ns per load', yunit='ns',
        vlines=[(mid, 'walked many times to the left, walked once to the right')],
        labels=zl,
        gaps=[dict(x=mid, y0=st['from_ns'], y1=st['to_ns'], dx=dx, text=V.signed(st['step_ns'], 3, 'ns'))
              for st, dx in ((st_f2, 16), (st_f1, -16), (st_core, -16))],
        height=380)
    out.append(S.fig(
        svg,
        'Chain load (best bracket time) from %s to %s. The lines break where the chain kind differs. The '
        'bold signed numbers beside the brackets are the step from %s to %s. The other values are in the '
        'tables of %s. CME rows of <code>%s</code> and <code>%s</code> on boot '
        'F2 %s %s and on boot F1 %s %s. Core rows of <code>%s</code> and <code>%s</code> on boot F1 %s %s.' % (
            lab(zoom[0]), lab(zoom[-1]), lab(st_f1['from_size']), lab(st_f1['to_size']), S.xref('lat-table'),
            SMALL, LARGE, r_s2, r_l2, r_s1, r_l1, C_SMALL, C_LARGE, r_cs, r_cl),
        'Only the orange line steps down across the boundary.'
        if [st['step_ns'] < 0 for st in (st_f2, st_f1, st_core)] == [False, True, False] else None))
    rows = []
    for st, name in ((st_f2, 'CME, %s' % n2), (st_f1, 'CME, %s' % n1), (st_core, 'The core, boot F1')):
        rows.append([name, n3(st['from_ns']), n3(st['to_ns']), V.signed(st['step_ns'], 3),
                     'n/a' if st['from_hwprf'] is None else c2(st['from_hwprf']),
                     'n/a' if st['to_hwprf'] is None else c2(st['to_hwprf'])])
    out.append(S.table(
        ['Series', '%s, ns' % lab(st_f1['from_size']), '%s, ns' % lab(st_f1['to_size']), 'Step, ns',
         'Prefetch at %s' % lab(st_f1['from_size']), 'Prefetch at %s' % lab(st_f1['to_size'])], rows,
        caption='The step across the boundary between the two chain kinds: chain load at %s (walked many '
                'times) and at %s (walked once), and the prefetch refills per load of the two rows. Files as '
                'in Figure %d.' % (lab(st_f1['from_size']), lab(st_f1['to_size']), S.next_fig() - 1),
        note='The core rows carry other counters. The CME prefetch refill columns read n/a for the core.'))
    w_small = [F2[s]['walks_per_rep'] for s in sizes if F2[s]['kind'] == K_MANY]
    out.append(S.bullets([
        'A rep of the kind "%s" walks the chain %s to %s times.' % (
            t_many, V.num(min(w_small), 0), V.num(max(w_small), 0)),
        'A rep of the kind "%s" walks its chain one time. Before the first rep the program walks another '
        'chain over the same lines two times, untimed %s.' % (t_once, r_src),
        'The largest footprint that is walked many times is %s. The smallest footprint that is walked once '
        'is %s.' % (lab(D.chain_steps['largest_walked_many']), lab(D.chain_steps['smallest_walked_once'])),
        'On %s the prefetch refills fall from %s to %s per load across the boundary.' % (
            n1, c2(st_f1['from_hwprf']), c2(st_f1['to_hwprf'])),
    ]))
    out.append(S.insufficient(
        'Whether the fall of %s ns on boot F1 belongs to the footprint or to the chain kind. The number of '
        'footprints with rows of both kinds is %d. One footprint run with both chain kinds on a boot with '
        'the prefetchers on would settle it. %s lists the hypotheses for this step.' % (
            n3(-st_f1['step_ns']), len(D.chain_steps['sizes_with_both_sweep_kinds']),
            S.xref('open-step', cap=True))))

    # ================================================================ 4.6 flushed rows and the DRAM model
    out.append(S.h3('lat-flushed', 'Every line flushed first at %s, and the DRAM model' % lab(8 * MIB)))
    f2f, f1f, cf = fl['F2'], fl['F1'], fl['core']
    out.append(S.bullets([
        'On %s the row with %s reads %s ns per load. It counts %s outer and %s inner refills per load.' % (
            n2, K_FLUSH, n3(f2f['best']), c4(f2f['outer']), c4(f2f['inner'])),
        'This is the row that the page quotes for the %s.' % t_dram,
        'On %s the same row reads %s ns. That is %s ns less than the walked-once row of the same footprint.'
        % (n1, n3(f1f['best']), n3(-st_f1['flushed_minus_walked_once'])),
    ]))
    big = 32 * MIB
    svg = V.hbar(
        [dict(label='%s, walked once' % lab(8 * MIB),
              values=[F2[8 * MIB]['best'], F1[8 * MIB]['best'], CORE[8 * MIB]['best']]),
         dict(label='%s, every line flushed first' % lab(8 * MIB),
              values=[f2f['best'], f1f['best'], cf['best']],
              notes=['(%s against walked once)' % V.signed(st['flushed_minus_walked_once'], 3, 'ns')
                     for st in (st_f2, st_f1, st_core)]),
         dict(label='%s, walked once' % lab(big), values=[F2[big]['best'], F1[big]['best'], CORE[big]['best']])],
        series=[('CME, %s' % n2, 'f2'), ('CME, %s' % n1, 'f1'), ('the core, boot F1', 'core')],
        unit='ns', fmt=n3, xlabel='chain load, ns per load',
        refs=[(rt, 'round-trip baseline %s ns (CME rows only)' % n3(rt))])
    fsign = [st['flushed_minus_walked_once'] > 0 for st in (st_f2, st_f1, st_core)]
    out.append(S.fig(
        svg,
        'Chain load (best bracket time) of three rows. The number in brackets is the row with every line '
        'flushed first minus the walked-once row of the same footprint. CME: rows %s of <code>%s</code> '
        '(every line flushed first) %s %s and rows %s of <code>%s</code> %s %s. The '
        'core on boot F1: <code>%s</code> %s and <code>%s</code> %s. The grey line is the round-trip baseline '
        'of the CME rows. The core has no such baseline.' % (
            modes([f2f, f1f]), FLUSHED, r_f2, r_f1, modes(once_rows), LARGE, r_l2, r_l1, C_FLUSHED, r_cf,
            C_LARGE, r_cl),
        'The flush adds time on boot F2 and for the core. On boot F1 the walk with every line flushed first '
        'is the faster one.' if fsign == [True, False, True] else None))
    rows = []
    for name, wo, fr, st, big_row in (('CME, %s' % n2, F2[8 * MIB], f2f, st_f2, F2[big]),
                                      ('CME, %s' % n1, F1[8 * MIB], f1f, st_f1, F1[big]),
                                      ('The core, boot F1', CORE[8 * MIB], cf, st_core, CORE[big])):
        cme = 'outer' in fr
        rows.append([name, n3(wo['best']), n3(fr['best']), V.signed(st['flushed_minus_walked_once'], 3),
                     c4(fr['outer']) if cme else 'n/a', c4(fr['inner']) if cme else 'n/a',
                     c4(fr['hwprf']) if cme else 'n/a', n3(big_row['best'])])
    out.append(S.table(
        ['Series', 'Walked once, ns', 'Flushed first, ns', 'Difference, ns', 'Outer', 'Inner', 'Prefetch',
         '%s walked once, ns' % lab(big)], rows,
        caption='The rows of Figure %d. The first three number columns are at %s: walked once, every line '
                'flushed first, and the second minus the first. Outer, inner and prefetch are refills per '
                'load of the walk with every line flushed first.' % (S.next_fig() - 1, lab(8 * MIB)),
        note='With every line flushed first, the core row counts %s read refills of the cluster L3 per load. '
             'Such a refill is a line that enters the cluster L3 for a load of the core.' % c4(cf['l3d_rd'])))
    out.append(S.bullets([
        'A walk with %s removes every line from the caches before it is timed %s.' % (t_fl, r_src),
        'For a buffer in the %s the flush also removes the line from the SLC (project README) %s.' % (
            t_dram, r_proj),
        'On %s that row counts %s outer, %s inner and %s prefetch refills per load. These counts are totals '
        'of a rep. They do not say which load caused which refill.' % (
            n2, c4(f2f['outer']), c4(f2f['inner']), c4(f2f['hwprf'])),
        'The %d reps of that row differ by %s ns.' % (f2f['n_reps'], n3(f2f['spread_ns'])),
        'On %s the walked-once row of %s still counts %s inner refills per load. It is %s ns below the '
        'row with every line flushed first.' % (n2, lab(8 * MIB), c4(F2[8 * MIB]['inner']),
                                                n3(st_f2['flushed_minus_walked_once'])),
        'The walked-once row of %s on boot F2 reads %s ns, with %s outer refills per load. That is %s ns '
        'below the row with every line flushed first.' % (
            lab(big), n3(F2[big]['best']), c4(F2[big]['outer']), n3(f2f['best'] - F2[big]['best'])),
        'That row of boot F2 reads %s ns above the round-trip baseline (bracket time). This is a measured '
        'difference between two kernels. It is not the access time of the %s (%s).' % (
            n3(f2f['above_rt']), t_dram, S.xref('lat-above')),
        'On %s the walk with every line flushed first counts %s prefetch refills and %s read refills per '
        'load. So the prefetcher is active in that row.' % (n1, c2(f1f['hwprf']), c4(f1f['rd'])),
    ]))
    out.append(S.hyp(
        'On %s each load of the row with every line flushed first causes one read refill. The line of that '
        'refill comes from outside the cluster.' % n2,
        'A record of the refilled addresses of that row. The hypothesis predicts each line of the chain one '
        'time in the record, each as an outer refill.'))
    out.append(S.callout(
        'The %s is a memory model of the emulator. Its %s ns is not the timing of a silicon memory.' % (
            t_dram, n3(f2f['best'])), title='Note'))
    out.append(S.insufficient(
        'Why the walk with every line flushed first is %s ns faster than the walked-once row on boot F1 and '
        'slower on boot F2. No '
        'counter of these rows names the cause. The same two rows on a boot with only the CME prefetcher '
        'off would show whether the CME prefetcher makes the difference.'
        % n3(-st_f1['flushed_minus_walked_once'])))

    # ================================================================ 4.7 one refill per line per rep (G5)
    out.append(S.h3('lat-perrep', 'About one inner refill per buffer line in each timed rep (%s)'
                    % span_label(V, *GROUPS[0])))
    rs = D.refills_per_line_summary
    rl = [r for r in D.refills_per_line if r['boot'] == 'F2']
    rl_l1 = [r for r in rl if r['in_l1']]
    rl_cl = [r for r in rl if not r['in_l1']]

    def line_err(r):
        """Half a print step of the counter column, in refills per line of one rep."""
        return 0.5 * CNT_STEP * r['loads'] / r['lines']

    def est_err(r):
        """Half a print step of the two printed values, carried into the ns per refill, est."""
        return r['above_rt_per_refill'] * (0.5 * CNT_STEP / r['refills'] + 0.5 * NS_STEP / r['above_rt'])

    out.append(S.bullets([
        'On %s, from %s to %s, every timed rep counts about one inner refill per line of the chain.' % (
            n2, rl_l1[0]['label'], rl_l1[-1]['label']),
        'The printed columns give %s to %s refills per line in all %d rep rows.' % (
            c2(rs['per_line_lo']), c2(rs['per_line_hi']), rs['n_rep_rows']),
        'Each value is a total of one rep: the refills per load times the loads of the rep, divided by the '
        'lines of the chain. The counters run over the whole rep %s.' % r_perf,
        'A total does not say which lines are refilled. It does not say in which walk of the rep they are '
        'refilled.',
        'The footprint fits the CME L1. The program also walks the chain two times, untimed, before the '
        'first rep %s. So the rows do not show why a rep counts these refills.' % r_src,
    ]))
    l1_lo, l1_hi = f1d(rs['l1_ns_per_refill_lo']), f1d(rs['l1_ns_per_refill_hi'])
    cl_lo, cl_hi = f1d(rs['cluster_ns_per_refill_lo']), f1d(rs['cluster_ns_per_refill_hi'])
    a1, a2 = rl_l1[len(rl_l1) // 2], rl_cl[len(rl_cl) // 2]
    svg = V.small_multiples([
        dict(ylabel='inner refills per line of the chain in one rep (lowest to highest of the reps)',
             height=120,
             series=[dict(name='lowest rep', color='f2',
                          points=[(r['size'], min(r['inner_per_line_reps'])) for r in rl_l1],
                          tips=['highest rep: %s' % c2(max(r['inner_per_line_reps'])) for r in rl_l1])],
             labels=[dict(series=0, x=r['size'], text=rng(r['inner_per_line_reps'], c2)) for r in rl_l1],
             yrange=(0, 1.4), hlines=[(1.0, 'one refill per line')], yfmt=c2),
        dict(ylabel='ns above baseline per refill of the best rep, est.',
             series=[dict(name='best rep, est.', color='f2',
                          points=[(r['size'], r['above_rt_per_refill']) for r in rl], label='all')],
             yfmt=f1d, yunit='ns',
             annotations=[dict(x=a1['size'], y=a1['above_rt_per_refill'], dx=-60, dy=-60,
                               text='%s to %s:\n%s to %s ns est.' % (rl_l1[0]['label'], rl_l1[-1]['label'],
                                                                   l1_lo, l1_hi)),
                          dict(x=a2['size'], y=a2['above_rt_per_refill'], dx=20, dy=70,
                               text='%s to %s:\n%s to %s ns est.' % (rl_cl[0]['label'], rl_cl[-1]['label'],
                                                                   cl_lo, cl_hi))]),
    ], x='log2', xticks=[r['size'] for r in rl], xlabel='footprint', show_legend=False,
        vlines=[(CME_L1_BYTES, 'CME L1 %s' % lab(CME_L1_BYTES))], panel_height=200, width=860)
    out.append(S.fig(
        svg,
        'Top: inner refills per line of the chain in one rep (refills per load times loads, divided by the '
        'lines of the chain), %s to %s. The label gives the lowest to the highest of the %s reps, or one '
        'value where they print the same. Bottom: chain load minus baseline of the best rep, divided by its '
        'inner plus outer refills per load, %s to %s. This value is an estimate (est.): it takes the whole '
        'measured difference between the two kernels as the cost of the refills. %s, rows %s of '
        '<code>%s</code> %s.' % (
            rl_l1[0]['label'], rl_l1[-1]['label'], ints(sorted({len(r['inner_per_line_reps']) for r in rl_l1})),
            rl[0]['label'], rl[-1]['label'], N2, modes(many_rows), SMALL, r_s2),
        'A rep counts about one inner refill per line of the chain. The chain load minus baseline per refill '
        'is %s to %s ns est. up to '
        'the CME L1 size. It is %s to %s ns est. above that size.' % (l1_lo, l1_hi, cl_lo, cl_hi)))
    rows = []
    for r in rl:
        rows.append([r['label'], V.num(r['lines'], 0), V.num(r['walks_per_rep'], 0), c4(r['inner']),
                     c4(r['refills']), rng(r['inner_per_line_reps'], c2),
                     n3(r['above_rt']), f1d(r['above_rt_per_refill'])])
    out.append(S.table(
        ['Footprint', 'Lines of<br>the chain', 'Walks<br>per rep', 'Inner refills<br>per load',
         'Inner plus outer<br>refills per load', 'Inner refills<br>per line, reps', 'Minus<br>baseline, ns',
         'ns per<br>refill, est.'], rows,
        caption='%s, walked many times, <code>%s</code>. The refills per load and "minus baseline" are of '
                'the best rep. "ns per refill, est." is "minus baseline" divided by the inner plus outer '
                'refills per load.' % (N2, SMALL),
        note='Highlighted rows: the chain fits the CME L1 (%s to %s). From %s on the chain does not fit the '
             'CME L1. A rep counts many refills per line there. The counter columns of the file have four '
             'decimals. So the refills per line are known to within %s at %s and to within %s at %s. The ns '
             'per refill est. is known to within %s ns at %s and to within %s ns at %s.' % (
                 rl_l1[0]['label'], rl_l1[-1]['label'], rl_cl[0]['label'],
                 '%.3f' % line_err(rl_l1[0]), rl_l1[0]['label'], '%.3f' % line_err(rl_l1[-1]),
                 rl_l1[-1]['label'], f1d(est_err(rl_l1[0])), rl_l1[0]['label'], f1d(est_err(rl_l1[-1])),
                 rl_l1[-1]['label']),
        highlight=list(range(len(rl_l1))), align='l' + 'r' * 7))
    out.append(S.bullets([
        'The chain load minus baseline grows with the footprint from %s ns to %s ns in the CME L1 rows. The '
        'refills per load grow in the same way. A larger chain is walked fewer times per rep.' % (
            n3(rs['l1_above_rt_lo']), n3(rs['l1_above_rt_hi'])),
        'Divided by the refills, the time above the baseline is %s to %s ns est. per refill from %s to %s.' % (
            l1_lo, l1_hi, rl_l1[0]['label'], rl_l1[-1]['label']),
        'It is %s to %s ns est. per refill from %s to %s, where the rows count %s refills per load.' % (
            cl_lo, cl_hi, rl_cl[0]['label'], rl_cl[-1]['label'], rng([r['refills'] for r in rl_cl], c4)),
        'The estimate takes the whole measured difference between the two kernels as the cost of the refills '
        '(%s).' % S.xref('lat-above'),
        'Between two timed reps the program stops the counters, reads them, formats a row and starts the '
        'counters again %s. The stop, the read and the start are system calls %s.' % (r_src, r_perf),
    ]))
    walks_l1 = [r['walks_per_rep'] for r in rl_l1]
    out.append(S.hyp(
        'Each rep starts with a CME L1 that does not hold the chain. The first walk of the rep refills '
        'every line of the chain one time. The later walks of the rep refill no line. The '
        'total of %s to %s inner refills per line agrees with this. It does not prove it: the same total '
        'results if some lines are refilled several times and other lines are not refilled.' % (
            c2(rs['per_line_lo']), c2(rs['per_line_hi'])),
        'A rep that counts the first walk and the later walks separately. A rep of these rows has %s to %s '
        'walks. If the first walk counts about one inner refill per line and the later walks count zero, the '
        'hypothesis holds. If the refills are spread over the walks, it is rejected. A trace of the refills '
        'by address would give the history of each line.' % (
            V.num(min(walks_l1), 0), V.num(max(walks_l1), 0))))
    out.append(S.hyp(
        'The %s to %s ns above the baseline in the CME L1 rows is the cost of the about one inner refill per '
        'line that each rep counts. It is '
        'not the cost of a load that the CME L1 serves. The cost per refill supports this: its range in '
        'these rows (%s to %s ns est.) overlaps the range of the rows that a cache inside the cluster serves '
        '(%s to %s ns est.).' % (
            n3(rs['l1_above_rt_lo']), n3(rs['l1_above_rt_hi']), l1_lo, l1_hi, cl_lo, cl_hi),
        'A latency run at one footprint with twice and four times the loads per rep. If the hypothesis '
        'holds, the time above the baseline per load halves each time the walks per rep double. If it stays '
        'the same, the hypothesis is rejected.'))
    out.append(S.insufficient(
        'Why a rep counts about one inner refill per line of a chain that fits the CME L1. A latency run '
        'without the counters, or a rep loop with no system call between the reps, would show whether the '
        'time above the baseline disappears. %s lists the hypotheses.' % S.xref('open-refill', cap=True)))

    # ================================================================ 4.8 full table
    out.append(S.h3('lat-table', 'Full table'))
    sp2 = max(D.chain_sweep('F2'), key=lambda r: r['spread_ns'])
    sp1 = max(D.chain_sweep('F1'), key=lambda r: r['spread_ns'])
    nfiles = len({r['src'] for r in D.chain['F2']})
    out.append(S.bullets([
        'The two tables hold every footprint row of the %d CME latency files of each boot that this section '
        'reads.' % nfiles,
        'The largest %s on %s is %s ns at %s (%s of the best value).' % (
            t_spread, n2, n3(sp2['spread_ns']), sp2['label'], V.pct(sp2['spread_pct'])),
        'The largest %s on %s is %s ns at %s (%s of the best value).' % (
            t_spread, n1, n3(sp1['spread_ns']), sp1['label'], V.pct(sp1['spread_pct'])),
    ]))
    heads = ['Footprint', 'Bracket,<br>ns', 'Span,<br>ns', 'Minus<br>baseline,<br>ns', 'Minus<br>baseline,<br>cycles',
             'Read', 'Prefetch', 'Inner', 'Outer', 'Rep<br>spread,<br>ns']

    def full(boot, with_core):
        rows_, kind = [], None
        for r in D.chain[boot]:
            if r['kind'] != kind:
                kind = r['kind']
                rows_.append('%s (<code>%s</code>)' % (kind[0].upper() + kind[1:], r['src']))
            row = [r['label'], n3(r['best']), n3(r['span']), n3(r['above_rt']),
                   '%.2f' % (r['above_rt'] * D.cycles_per_ns), c4(r['rd']), c4(r['hwprf']),
                   c4(r['inner']), c4(r['outer']), n3(r['spread_ns'])]
            if with_core:
                p = pairs[(r['size'], r['kind'])]
                row += [n3(p['core']), n3(p['f1_minus_core'])]
            rows_.append(row)
        return rows_

    out.append(S.table(
        heads, full('F2', False),
        caption='%s: CME chain load and refill counters at every footprint %s %s %s.' % (N2, r_s2, r_l2, r_f2),
        note='Bracket: the best rep. Span and the counters: the same rep. Minus baseline: bracket minus the '
             '%s ns round-trip baseline of the same file. It is a measured difference between two kernels, not '
             'a memory-access time. The cycles column is that time multiplied by the '
             'measured %.2f cycles per ns (%s). Read, prefetch, inner and outer are refills per '
             'load. Rep spread: highest minus lowest bracket time of the reps.' % (
                 n3(rt), D.cycles_per_ns, S.xref('setup-clock')),
        align='l' + 'r' * (len(heads) - 1)))
    out.append(S.table(
        heads + ['The core,<br>ns', 'CME minus<br>the core,<br>ns'], full('F1', True),
        caption='%s: CME chain load and refill counters at every footprint %s %s %s, and the chain load of '
                'the core on the same boot %s %s %s.' % (N1, r_s1, r_l1, r_f1, r_cs, r_cl, r_cf),
        note='Columns as in Table %d. The core column is the best rep of the core row with the same footprint '
             'and chain kind.' % (S.next_table() - 1),
        align='l' + 'r' * (len(heads) + 1)))
    return ''.join(out)


def rows_body(rows):
    """The data rows of a table row list (group headings left out)."""
    return [r for r in rows if not isinstance(r, str)]
