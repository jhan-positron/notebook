"""Section 'bandwidth': Bandwidth by footprint (SPEC outline item 6).

Every measured number comes from the data layer D.  Footprints, file names, source line
numbers and documented limits are typed test parameters or typed facts with a reference."""
import math
import os

KEY = 'bandwidth'
TITLE = 'Bandwidth by footprint'

K = 1024
M = 1024 * 1024
BOOTS = ('F2', 'F1')            # drawing order: boot F2 first (blue), then boot F1 (orange)
COL = {'F1': 'f1', 'F2': 'f2'}
L1_BYTES = 64 * K               # typed fact: CME L1 size (operator's README of boot F1, comment of run_cme.sh line 38)
KNAME = {'read': 'read', 'write': 'write', 'copy': 'copy',
         'read64': 'read, 64 B per instruction', 'write64': 'write, 64 B per instruction'}


def _g1(v):
    return 'no row' if v is None else '%.1f' % v


def _g2(v):
    return 'no row' if v is None else '%.2f' % v


def _g3(v):
    return 'no row' if v is None else '%.3f' % v


def _short(size):
    """Short x tick label: '4K', '1M'.  The axis title names the units."""
    return '%gM' % (size / M) if size >= M else '%gK' % (size / K)


def _up1(pct):
    """A percentage rounded up to one decimal, so that it is a bound."""
    return math.ceil(pct * 10 - 1e-9) / 10


def _lines(nums):
    """'95 to 108' or '111, 113, 117' for a list of log line numbers."""
    nums = sorted(nums)
    if nums and nums == list(range(nums[0], nums[-1] + 1)):
        return '%d to %d' % (nums[0], nums[-1])
    return ', '.join(str(n) for n in nums)


def build(D, V, S):
    from . import data as DATA
    cpn = D.cycles_per_ns
    name = D.boot_name
    Name = {b: name[b][0].upper() + name[b][1:] for b in name}

    def bpc(v):
        return v / cpn

    def row(b, group, kernel, size):
        return D.bw_row(b, group, kernel, size)

    def form_rows(b, kernel, form):
        """Rows of one kernel and form over the whole footprint range.  The 4 KiB to 24 KiB
        rows come from the two L1 files, the rows from 48 KiB up from the two sweep files."""
        small, large = ('l1-single', 'sweep-single') if form == 'single-call' else ('l1-looped', 'sweep')
        rows = list(D.bw_table(small, b, kernel))
        top = max([r['size'] for r in rows] or [0])
        return rows + [r for r in D.bw_table(large, b, kernel) if r['size'] > top]

    def pts(rows):
        return [(r['size'], r['best']) for r in rows]

    def val(rows, size):
        for r in rows:
            if r['size'] == size:
                return r['best']
        return None

    def rng(vals, fmt=_g1):
        return '%s to %s' % (fmt(min(vals)), fmt(max(vals)))

    def rel(path):
        return os.path.relpath(path, DATA.ROOT)

    # ------------------------------------------------------------ terms
    T = S.term
    T('CME', 'the Arm C1-SME2 matrix engine unit. One CME serves one cluster of two cores')
    T('footprint', 'the size of the buffer that one test walks. A copy uses two buffers of that size')
    T('pass', 'one walk over the whole buffer or chain')
    T('rep', 'one timed measurement. A bandwidth rep is a group of passes')
    T('kernel', 'the test loop in <code>cme_kern.S</code> that runs on the CME. It is not the Linux kernel')
    T('bracket time', 'the time between two clock reads in the C program around the kernel call or calls of a rep')
    T('span time', 'the time between the two counter reads inside the kernel, after the CME is entered '
                   '(SMSTART) and before it is left (SMSTOP)')
    T('bracket rate', 'bytes moved in a rep divided by the bracket time, in GB/s (CSV column <code>aggregate_GBps</code>)')
    T('span rate', 'bytes moved in a rep divided by the span time, in GB/s (CSV column <code>span_GBps</code>)')
    T('looped form', 'a bandwidth row that makes one kernel call per pass')
    T('single-call form', 'a bandwidth row that runs all passes of a rep in one assembly call')
    T('GB/s', '1e9 bytes per second, which equals 1 byte per ns')
    T('KiB, MiB', '1,024 bytes and 1,024 KiB')
    T('B/cycle', 'bytes per cycle: the rate in GB/s divided by the measured %.2f cycles per ns of the core cycle counter' % cpn)
    T('best row', 'the row that the program prints as <code>best</code>: for bandwidth the rep with the highest bracket rate')
    T('rep spread', '(highest rep minus lowest rep) divided by the lowest rep, in percent')
    T('fold', 'the XOR of all loaded words into one value, which the read kernel returns to the core')
    T('prefetchers', 'the hardware units that request lines before the program loads them. '
                     'They are on in boot F1 and off in boot F2 (operator\'s README)')
    T('boot F1', 'the boot with the cluster L3 on and the hardware prefetchers on (operator\'s README). '
                  'It has core rows and CME rows')
    T('boot F2', 'the boot with the cluster L3 on and the hardware prefetchers off (operator\'s README). '
                  'It has CME rows only')
    T('CME L1', 'the level 1 data cache of the CME. Its size is 64 KiB (operator\'s README)')
    T('pipe', 'One execution unit of the processor model in the LLVM compiler source.')
    T('in flight', 'A line request is in flight between the moment the CME sends it and the moment the line arrives.')
    T('core', 'one of the two Arm C1-Nano processor cores of the cluster. The tests run on CPU 2')
    T('vector', 'one CME register of 64 bytes. One vector load or store moves 64 bytes')
    T('LLVM model', 'the scheduling description of the C1-Nano in the LLVM compiler source')
    T('LDP, STP', 'the core instructions that load or store a pair of registers')
    T('XOR', 'the bitwise exclusive-or operation (instruction EOR)')
    T('est.', 'an estimate: a value derived with an assumption, not read from a row')
    T('LD1D, LD1B', 'vector load instructions. LD1D loads 8-byte elements, LD1B loads bytes')
    T('ST1B', 'a vector store instruction')
    T('EOR', 'the XOR instruction')
    T('LASTB', 'an instruction that copies the last active element of a vector to a register of the core')
    T('effective cycles per 64 bytes transferred',
      '64 divided by the rate in B/cycle: the cycles of the whole loop divided by the 64-byte units that it '
      'transfers. It is a loop throughput. It is not the time that one load or one store takes to complete')

    # ------------------------------------------------------------ references
    def csv_ref(fname, what):
        parts = []
        for b in ('F1', 'F2'):
            ll = D.log_lines(b, fname)
            parts.append('%s: <code>%s/%s</code>, commands at <code>log.txt</code> lines %s' % (
                Name[b], rel(DATA.BOOTDIR[b]), fname, _lines(ll)))
        return S.ref('csv:' + fname, 'File <code>%s</code>, %s. %s. %s.' % (fname, what, parts[0], parts[1]))

    def grp(group):
        """Footprint range and reps per row of one file group, read from the rows of both boots."""
        rows = [r for b in ('F1', 'F2') for r in D.bw_table(group, b)]
        reps = sorted({r['n_reps'] for r in rows})
        return dict(lo=DATA.fmt_size(min(r['size'] for r in rows)), hi=DATA.fmt_size(max(r['size'] for r in rows)),
                    reps=' or '.join(str(n) for n in reps))
    G = {g: grp(g) for g in ('sweep', 'sweep-single', 'l1-looped', 'l1-single')}

    def what(form, kernels, g):
        return 'the %s form of the %s kernels at %s to %s, %s reps per row' % (form, kernels, G[g]['lo'], G[g]['hi'], G[g]['reps'])

    r_sweep = csv_ref('cme-bandwidth-dram-1core.csv', what('looped', 'read, write, copy and 64 B', 'sweep'))
    r_sweep1 = csv_ref('cme-bandwidth-dram-1core-asmpasses.csv', what('single-call', 'read and write', 'sweep-single'))
    r_l1 = csv_ref('cme-bandwidth-l1-passes.csv', what('looped', 'read and write', 'l1-looped'))
    r_l11 = csv_ref('cme-bandwidth-l1-asmpasses.csv', what('single-call', 'read and write', 'l1-single'))
    core0 = D.core_bw[0]
    core_sizes = sorted({r['size'] for r in D.core_bw})
    r_core = S.ref('csv:bandwidth-dram-1core.csv',
                   'File <code>%s</code>, the core rows of %s (read, write and copy at %s to %s, %s reps per row), '
                   'commands at <code>log.txt</code> lines %s.' % (
                       rel(core0['path']) if core0.get('path') else 'bandwidth-dram-1core.csv', name['F1'],
                       DATA.fmt_size(core_sizes[0]), DATA.fmt_size(core_sizes[-1]),
                       ' or '.join(str(n) for n in sorted({r['n_reps'] for r in D.core_bw})),
                       _lines(D.log_lines('F1', 'bandwidth-dram-1core.csv'))))
    r_bwc = S.ref('src:bandwidth.c',
                  'Source <code>bandwidth.c</code>: line 11 (the core kernels use LDP and STP of two 16 B registers), '
                  'line 341 (a copy counts the bytes read plus the bytes written), line 421 (one untimed warm-up pass '
                  'before each rep), lines 425 to 436 (the bracket around the passes of a rep), '
                  'line 519 (<code>--perf</code> is refused with <code>--cme</code>).')
    r_kern = S.ref('src:cme_kern.S',
                   'Source <code>cme_kern.S</code>: macros <code>SM_ENTER</code> (line 71) and <code>SM_LEAVE</code> '
                   '(line 86) hold the two counter reads of the span. Kernels: <code>cme_read4</code> and '
                   '<code>cme_write4</code> (lines 143 to 251), <code>cme_read4_n</code> (line 264), '
                   '<code>cme_write4_n</code> (line 312), <code>cme_copy4</code> (line 339), '
                   '<code>cme_read1</code> (line 363), <code>cme_write1</code> (line 403).')
    # The size of the CME L1 is a typed fact of the operator's README of boot F1 (the source of the
    # glossary entry).  The comment in run_cme.sh repeats it.  No CSV file states it.
    r_l1size = '%s %s' % (
        S.ref('readme:F1'),
        S.ref('src:run_cme.sh',
              'Script <code>run_cme.sh</code>, comment at line 38: the CME has "its own 64 KiB L1, then the DSU L3, '
              'then the mesh". No CSV file states the CME L1 size.'))
    r_sog = S.ref('doc:sog-c1-nano',
                  'Arm C1-Nano Software Optimization Guide, document 109590, section 2.33.3: at most 2 loads or stores '
                  'per cycle.')
    r_llvm = S.ref('doc:llvm-c1-nano',
                   'File <code>refs/AArch64SchedC1Nano.td</code>, lines 84 to 86: the LLVM scheduling model has one CME '
                   'load pipe (line 84), one CME store pipe (line 85) and one CME prefetch pipe (line 86).')
    cache = [c for c in D.platform['caches'] if c['level'] == 1 and c['type'] == 'Data'][0]
    r_sys = S.ref('raw:sysinfo-caches',
                  'File <code>%s/sysinfo.txt</code> of %s, lines 101 to 104: the cache sizes of CPU 2 as Linux reports them.'
                  % (rel(DATA.RUN['F1']), name['F1']))
    callcost = S.xref('callcost', 'The cost of one kernel call')
    # the two cycle counters give the same ratio to two decimals: the text below says so
    for b_ in ('F1', 'F2'):
        assert round(D.clock[b_]['cme_median'], 2) == round(D.clock[b_]['core_median'], 2) == cpn

    # ------------------------------------------------------------ rows used below
    rd = {(b, f): form_rows(b, 'read', f) for b in BOOTS for f in ('single-call', 'looped')}
    wr = {(b, f): form_rows(b, 'write', f) for b in BOOTS for f in ('single-call', 'looped')}
    cp = {b: D.bw_table('sweep', b, 'copy') for b in BOOTS}
    lim = D.limits
    q = D.quote
    l1_sizes = lim['F1']['sizes']
    l1_lo, l1_hi = DATA.fmt_size(min(l1_sizes)), DATA.fmt_size(max(l1_sizes))
    vec_gbps = 64 * cpn            # one 64 B vector per cycle, in GB/s
    l1_txt = DATA.fmt_size(L1_BYTES)
    all_sizes = sorted({r['size'] for k in rd for r in rd[k]} | {r['size'] for k in wr for r in wr[k]}
                       | {r['size'] for b in BOOTS for r in cp[b]})
    XT = [(s, _short(s)) for s in all_sizes]          # the same ticks and x range in the three sweep charts
    XLAB = 'footprint (K = KiB, M = MiB)'
    big_sizes = sorted(s for s in all_sizes if s >= 1 * M)
    gap_lo, gap_hi = DATA.fmt_size(big_sizes[-2]), DATA.fmt_size(big_sizes[-1])   # the last interval with no row

    def pct(a, b):
        return abs(a / b - 1) * 100

    def tick(v):
        return '%g GB/s = %g B/cycle' % (v, bpc(v))

    def series(tab, kernel_word):
        out = []
        # looped first: the single-call circles are drawn on top where the marks coincide
        for f, dash, mk in (('looped', True, 'triangle'), ('single-call', False, 'circle')):
            for b in BOOTS:
                out.append(dict(name='%s form, %s' % (f, name[b]), color=COL[b], points=pts(tab[(b, f)]),
                                dash=dash, marker=mk))
        return out

    out = ''

    # ------------------------------------------------------------ section head
    out += S.takeaways([
        'At %s to %s, below the %s size of its L1, the CME reads %s GB/s on %s and %s GB/s on %s (single-call form).' % (
            l1_lo, l1_hi, l1_txt, rng(q['l1_read_single_F1']), name['F1'], rng(q['l1_read_single_F2']), name['F2']),
        'The CME writes %s GB/s at 4 KiB to 256 KiB on both boots (single-call form), '
        'and %s GB/s at 1 MiB to 32 MiB (looped form).' % (rng(q['write_single']), rng(q['write_large'])),
        'At 32 MiB the read rate is %s GB/s with the prefetchers on and %s GB/s with the prefetchers off.' % (
            _g1(q['read_32m_f1']), _g1(q['read_32m_f2'])),
        'At 16 KiB on %s the CME reads %.2f times and writes %.2f times the bytes per second of the core '
        '(single-call form).' % (
            name['F1'],
            [r for r in D.core_vs_cme_bw if r['kernel'] == 'read' and r['size'] == 16 * K][0]['single_over_core'],
            [r for r in D.core_vs_cme_bw if r['kernel'] == 'write' and r['size'] == 16 * K][0]['single_over_core']),
    ])
    # The test itself is described once, in section 1.  Only what the reader needs to read the rates is said here.
    out += S.p('%s and %s describe the bandwidth test, its two forms and its two times. %s measures the time of '
               'one kernel call. Four points for reading the rates of this section:' % (
                   S.xref('setup-kernels', cap=True), S.xref('setup-times'),
                   S.xref('callcost', 'The cost of one kernel call', cap=True)))
    out += S.bullets([
        'Every rate of this section is a loop throughput: the bytes that the whole loop transfers, divided by the '
        'time of the loop. It is not the time that one load or one store takes to complete.',
        'One iteration of the read loop runs %d LD1B instructions, and each LD1B loads %d vectors of 64 bytes. '
        'The same iteration runs 16 EOR instructions, which fold the loaded vectors into 16 registers (the fold). '
        'So a read rate is the rate of the loads and the EOR work together. '
        'One iteration of the write loop runs 4 ST1B instructions, and each ST1B stores 4 vectors of 64 bytes %s.' % (
            lim['doc']['read_load_instructions_per_iter'], lim['doc']['vectors_per_load'], r_kern),
        'All rates are the best row of each command, and the charts show bracket rates. '
        'Bytes per cycle (B/cycle) is the rate in GB/s divided by %.2f cycles per ns, the measured ratio of the '
        'core cycle counter to the timer (%s). '
        'So %g GB/s is 64 B/cycle, which is one 64-byte vector per cycle.' % (cpn, S.xref('setup-clock'), vec_gbps),
        'These rows carry no cache counter. The program refuses its counter option together with the CME option %s. '
        'So no row of this section names the cache level that served it. The text gives footprints, and it gives the '
        '%s size of the CME L1 (operator\'s README) %s for comparison.' % (r_bwc, l1_txt, r_l1size),
    ])

    # ------------------------------------------------------------ 1. read
    out += S.h3('bw-read', 'Read rate against footprint')
    f1s, f2s, f1l, f2l = rd[('F1', 'single-call')], rd[('F2', 'single-call')], rd[('F1', 'looped')], rd[('F2', 'looped')]
    top32 = 32 * M
    r32 = val(f2l, top32) / val(f1l, top32)
    fall2 = {b: (val(rd[(b, 'looped')], 256 * K), val(rd[(b, 'looped')], 1 * M)) for b in ('F1', 'F2')}
    out += S.bullets([
        'At %s to %s, below the %s size of the CME L1, the single-call read moves %s GB/s on %s and %s GB/s on %s. '
        'That is %s and %s B/cycle.' % (
            l1_lo, l1_hi, l1_txt, rng(q['l1_read_single_F1']), name['F1'], rng(q['l1_read_single_F2']), name['F2'],
            rng([lim['F1']['read_bpc_lo'], lim['F1']['read_bpc_hi']]),
            rng([lim['F2']['read_bpc_lo'], lim['F2']['read_bpc_hi']])),
        'At footprints above that size the looped read moves %s GB/s at 96 KiB to 256 KiB and %s GB/s at 1 MiB to 32 MiB on %s. '
        'On %s the 32 MiB read moves %s GB/s.' % (
            rng(q['read_cluster_f1']), rng(q['read_large_f1']), name['F1'], name['F2'], _g1(q['read_32m_f2'])),
    ])
    # series order of series(): 0 looped F2, 1 looped F1, 2 single-call F2, 3 single-call F1
    svg = V.line_chart(
        series(rd, 'read'), x='log2', xticks=XT, xlabel=XLAB, ylabel='read rate (bracket), GB/s', yunit='GB/s',
        yfmt=lambda v: V.num(v, 1), ytickfmt=tick,
        vlines=[(L1_BYTES, 'CME L1 %s' % l1_txt)],
        hlines=[(vec_gbps, '%g GB/s = 64 B/cycle: one 64 B vector per cycle' % vec_gbps)],
        labels=[(3, 4 * K), (3, 8 * K), (3, 48 * K),
                (3, 96 * K, '%s GB/s (single-call, boot F1)' % _g1(val(f1s, 96 * K))),
                (2, 96 * K, '%s GB/s (single-call, boot F2)' % _g1(val(f2s, 96 * K))),
                (1, 4 * K), (1, 48 * K), (1, 256 * K), (1, 1 * M), (0, 1 * M), (1, top32), (0, top32)],
        gaps=[dict(x=top32, y0=val(f2l, top32), y1=val(f1l, top32), text='%.2f x' % r32, dx=-30)],
        annotations=[dict(x=8 * K, y=val(f1l, 8 * K), text='looped form (dashed):\neach pass includes\none kernel call',
                          dx=110, dy=32),
                     dict(x=8 * M, y=8, text='no row between\n%s and %s' % (gap_lo, gap_hi), dx=0, dy=0)],
        height=460)
    out += S.fig(
        svg,
        'CME read rate against footprint on %s and %s, bracket rates of the best rows. Solid lines are the '
        'single-call form and dashed lines are the looped form. '
        'The y axis is one axis: each tick gives GB/s and the same value in B/cycle. The grey vertical line is the '
        'CME L1 size (operator\'s README) %s.' % (name['F1'], name['F2'], r_l1size),
        'The read rate falls between 48 KiB and 96 KiB on both boots. Both looped lines fall a second time between '
        '256 KiB and 1 MiB, to %s and %s GB/s. Only the %s line falls a third time, at 32 MiB, to %.2f times the %s rate.' % (
            _g1(fall2['F1'][1]), _g1(fall2['F2'][1]), name['F2'], r32, name['F1']),
        note='Single-call form: %s to %s from <code>cme-bandwidth-l1-asmpasses.csv</code> %s, %s to %s from '
        '<code>cme-bandwidth-dram-1core-asmpasses.csv</code> %s. Looped form: %s to %s from '
        '<code>cme-bandwidth-l1-passes.csv</code> %s, 48 KiB to %s from <code>cme-bandwidth-dram-1core.csv</code> %s. '
        'A line between two marks only joins them. '
        'No row exists between %s and %s, so the place of the last fall inside that interval is not known.' % (
            G['l1-single']['lo'], G['l1-single']['hi'], r_l11,
            G['sweep-single']['lo'], G['sweep-single']['hi'], r_sweep1,
            G['l1-looped']['lo'], G['l1-looped']['hi'], r_l1, G['sweep']['hi'], r_sweep, gap_lo, gap_hi))

    sizes_r = sorted({r['size'] for k in rd for r in rd[k]})
    trows = []
    for s in sizes_r:
        a, b_, c, d = val(f1s, s), val(f2s, s), val(f1l, s), val(f2l, s)
        trows.append([DATA.fmt_size(s), _g2(a), '%.2f' % bpc(a) if a else 'no row', _g2(b_),
                      '%.2f' % bpc(b_) if b_ else 'no row', _g2(c), _g2(d)])
    two16 = ('The looped 16 KiB row exists in two files. This table takes <code>cme-bandwidth-l1-passes.csv</code> '
             '(%s reps). <code>cme-bandwidth-dram-1core.csv</code> (%s reps) reads %s GB/s on F1 and %s GB/s on F2. '
             '%s and %s take that second row, so that all rows they compare come from one file. '
             '%s compares the two rows.')
    t_read = S.table(
        ['Footprint', 'Single-call, F1<br>GB/s', 'Single-call, F1<br>B/cycle', 'Single-call, F2<br>GB/s',
         'Single-call, F2<br>B/cycle', 'Looped, F1<br>GB/s', 'Looped, F2<br>GB/s'], trows, align='lrrrrrr',
        caption='CME read rate by footprint, bracket rates of the best rows. F1 is %s. F2 is %s. '
                'Files as in Figure %d. The full tables of %s give three decimals.' % (
                    name['F1'], name['F2'], S.n_fig, S.xref('bw-full')),
        note='"no row": the boots have no row of that form at that footprint. B/cycle = GB/s / %.2f. ' % cpn
             + two16 % (G['l1-looped']['reps'], G['sweep']['reps'],
                        _g2(row('F1', 'sweep', 'read', 16 * K)['best']), _g2(row('F2', 'sweep', 'read', 16 * K)['best']),
                        S.xref('bw-core', cap=True), S.xref('bw-64'), S.xref('glance-repeat', cap=True)))
    out += t_read

    s96 = {b: row(b, 'sweep-single', 'read', 96 * K) for b in ('F1', 'F2')}
    s8 = {b: row(b, 'l1-single', 'read', 8 * K) for b in ('F1', 'F2')}
    l4, s4 = row('F1', 'l1-looped', 'read', 4 * K), row('F1', 'l1-single', 'read', 4 * K)
    agree = [row('F1', g, 'read', s) for g in ('sweep', 'sweep-single') for s in (160 * K, 256 * K)]
    out += S.bullets([
        'The first fall is between 48 KiB and 96 KiB. The CME L1 size of %s (operator\'s README) lies in that interval %s.' % (
            l1_txt, r_l1size),
        'Between 256 KiB and 1 MiB the looped read goes from %s to %s GB/s on %s (%.2f times) and from %s to %s GB/s '
        'on %s (%.2f times). The write rate steps down between the same two footprints (%s).' % (
            _g1(fall2['F1'][0]), _g1(fall2['F1'][1]), name['F1'], fall2['F1'][1] / fall2['F1'][0],
            _g1(fall2['F2'][0]), _g1(fall2['F2'][1]), name['F2'], fall2['F2'][1] / fall2['F2'][0], S.xref('bw-write')),
        'At 4 KiB on %s the looped read moves %s GB/s and the single-call read %s GB/s. '
        'The looped form makes one kernel call per pass, and the single-call form one call per rep. '
        'The span rate of the looped row is also lower: %s against %s GB/s. So part of the difference is inside the span. '
        '%s splits the time of one call.' % (
            name['F1'], _g1(l4['best']), _g1(s4['best']), _g1(l4['best_span']), _g1(s4['best_span']),
            S.xref('callcost', cap=True)),
        'At 160 KiB and 256 KiB the two forms differ by %.1f %% and %.1f %% on %s: %s and %s GB/s (looped) against '
        '%s and %s GB/s (single-call). The rep spread of these four rows is %.1f %% to %.1f %% of the lowest rep. '
        'So the rows do not separate the two forms there.' % (
            pct(val(f1s, 160 * K), val(f1l, 160 * K)), pct(val(f1s, 256 * K), val(f1l, 256 * K)), name['F1'],
            _g1(val(f1l, 160 * K)), _g1(val(f1l, 256 * K)), _g1(val(f1s, 160 * K)), _g1(val(f1s, 256 * K)),
            min(r['spread_pct'] for r in agree), max(r['spread_pct'] for r in agree)),
        'The single-call read at 96 KiB differs between the boots: %s GB/s on %s and %s GB/s on %s. '
        'Its reps spread by %.1f %% and %.1f %% of the lowest rep. The %d reps read %s GB/s on %s and %s GB/s on %s.' % (
            _g1(s96['F1']['best']), name['F1'], _g1(s96['F2']['best']), name['F2'],
            s96['F1']['spread_pct'], s96['F2']['spread_pct'], len(s96['F1']['reps_gbps']),
            ', '.join(_g1(v) for v in s96['F1']['reps_gbps']), name['F1'],
            ', '.join(_g1(v) for v in s96['F2']['reps_gbps']), name['F2']),
        'The single-call read at 8 KiB is lower than at 4 KiB and at 16 KiB on both boots: %s GB/s against %s and %s GB/s '
        'on %s, and %s GB/s against %s and %s GB/s on %s.' % (
            _g1(s8['F1']['best']), _g1(val(f1s, 4 * K)), _g1(val(f1s, 16 * K)), name['F1'],
            _g1(s8['F2']['best']), _g1(val(f2s, 4 * K)), _g1(val(f2s, 16 * K)), name['F2']),
    ])
    out += S.insufficient(
        'No bandwidth row exists between 48 KiB and 96 KiB. '
        'Single-call read rows at 56, 64, 72 and 80 KiB would show whether the first fall is at 64 KiB.')
    out += S.insufficient(
        'No read row exists between 256 KiB and 1 MiB. '
        'Read rows at 320, 384, 512 and 768 KiB would locate the second fall.')
    out += S.insufficient(
        'The 96 KiB single-call read row has %s reps on each boot. '
        'The same row with 10 or more reps on each boot would show whether the difference between the boots repeats.' % G['sweep-single']['reps'])
    out += S.insufficient(
        'No row explains the lower single-call read rate at 8 KiB. '
        'A CME refill counter on the bandwidth rows would show whether that row leaves the CME L1.')
    doc = lim['doc']
    out += S.p('%s compares these rates with two documented limits:' % S.xref('glance-limits', cap=True))
    out += S.bullets([
        'The core issues at most %d load or store instructions per cycle to the CME (Arm Software Optimization Guide) %s.' % (
            doc['loads_or_stores_per_cycle_max'], r_sog),
        'The LLVM model has %d CME load pipe and %d CME store pipe %s. A pipe is one execution unit of that model.' % (
            doc['cme_load_pipes'], doc['cme_store_pipes'], r_llvm),
        'The measured single-call read at %s to %s is %.2f to %.2f vectors of 64 bytes per cycle on %s and %.2f to %.2f on %s.' % (
            l1_lo, l1_hi, lim['F1']['read_vec_per_cycle_lo'], lim['F1']['read_vec_per_cycle_hi'], name['F1'],
            lim['F2']['read_vec_per_cycle_lo'], lim['F2']['read_vec_per_cycle_hi'], name['F2']),
    ])
    # the 4 KiB rows against one vector per cycle
    r4 = {b: row(b, 'l1-single', 'read', 4 * K) for b in ('F1', 'F2')}
    reps4 = [v for b in ('F1', 'F2') for v in r4[b]['reps_gbps']]
    n4_above = len([v for v in reps4 if v > vec_gbps])
    rest = {b: [r['best'] / vec_gbps for r in rd[(b, 'single-call')] if 4 * K < r['size'] <= max(l1_sizes)] for b in ('F1', 'F2')}
    out += S.hyp(
        '%s gives the hypothesis that the load path of the CME limits the read rate at these footprints, and '
        'that the EOR work does not. The LLVM model gives 2 vectors per cycle for this kernel (est.). '
        'One vector per cycle is not the limit. The 4 KiB rows are above it. '
        'Their bracket rate is %.2f vectors per cycle on %s and %.2f on %s, and their span rate is %.2f and %.2f. '
        '%d of the %d reps of those two rows are above one vector per cycle (bracket rate). '
        'The rows from 8 KiB to %s read %.2f to %.2f vectors per cycle on %s and %.2f to %.2f on %s. '
        'No row shows why the 4 KiB rows are the fastest.' % (
            S.xref('glance-limits', cap=True),
            r4['F1']['best'] / vec_gbps, name['F1'], r4['F2']['best'] / vec_gbps, name['F2'],
            r4['F1']['best_span'] / vec_gbps, r4['F2']['best_span'] / vec_gbps, n4_above, len(reps4),
            l1_hi, min(rest['F1']), max(rest['F1']), name['F1'], min(rest['F2']), max(rest['F2']), name['F2']),
        'The read kernel also runs one EOR instruction for every loaded vector. So these rows cannot separate the '
        'load path from the EOR work. A single-call read kernel with no EOR instruction in its loop would '
        'separate them (%s). A single-call read at 1 KiB and 2 KiB would show whether the rate keeps rising '
        'above one vector per cycle at small footprints.' % S.xref('glance-limits'))

    # ------------------------------------------------------------ 2. write
    out += S.h3('bw-write', 'Write rate against footprint')
    w1s, w2s, w1l, w2l = wr[('F1', 'single-call')], wr[('F2', 'single-call')], wr[('F1', 'looped')], wr[('F2', 'looped')]
    lo_sizes = [s for s in (16 * K, 48 * K, 96 * K, 160 * K, 256 * K)]
    small_w = [val(t, s) for t in (w1l, w2l) for s in lo_sizes]
    step = {b: (val(wr[(b, 'looped')], 256 * K), val(wr[(b, 'looped')], 1 * M)) for b in ('F1', 'F2')}
    out += S.bullets([
        'The single-call write moves %s GB/s at 4 KiB to 256 KiB on both boots. That is %s B/cycle. '
        'The range holds on both sides of the %s size of the CME L1.' % (
            rng(q['write_single']), rng([bpc(v) for v in q['write_single']], lambda v: '%.2f' % v), l1_txt),
        'The looped write moves %s GB/s at 16 KiB to 256 KiB and %s GB/s at 1 MiB to 32 MiB on both boots. '
        'The rows do not show the cause of that step.' % (rng(small_w), rng(q['write_large'])),
    ])
    svg = V.line_chart(
        series(wr, 'write'), x='log2', xticks=XT, xlabel=XLAB, ylabel='write rate (bracket), GB/s', yunit='GB/s',
        yfmt=lambda v: V.num(v, 1), ytickfmt=tick,
        vlines=[(L1_BYTES, 'CME L1 %s' % l1_txt)],
        labels=[(3, 4 * K), (1, 4 * K), (1, 8 * K), (3, 256 * K), (1, 1 * M), (0, 2 * M), (1, top32)],
        annotations=[dict(x=1 * M, y=step['F1'][1],
                          text='step between 256 KiB and 1 MiB\nboot F1: %s to %s GB/s\nboot F2: %s to %s GB/s\nno cause claimed' % (
                              _g1(step['F1'][0]), _g1(step['F1'][1]),
                              _g1(step['F2'][0]), _g1(step['F2'][1])),
                          dx=-20, dy=95),
                     dict(x=4 * K, y=val(w1l, 4 * K), text='looped form (dashed):\neach pass includes\none kernel call',
                          dx=95, dy=45),
                     dict(x=8 * M, y=30, text='no row between\n%s and %s' % (gap_lo, gap_hi), dx=0, dy=0)],
        height=400)
    out += S.fig(
        svg,
        'CME write rate against footprint on %s and %s, bracket rates of the best rows. Solid lines: single-call form '
        '(<code>cme-bandwidth-l1-asmpasses.csv</code> %s and <code>cme-bandwidth-dram-1core-asmpasses.csv</code> %s). '
        'Dashed lines: looped form (<code>cme-bandwidth-l1-passes.csv</code> %s and '
        '<code>cme-bandwidth-dram-1core.csv</code> %s). Each y tick gives GB/s and the same value in B/cycle. '
        'A line between two marks only joins them.' % (
            name['F1'], name['F2'], r_l11, r_sweep1, r_l1, r_sweep),
        'The single-call write rate is the same on both sides of the %s size of the CME L1. '
        'The looped write rate steps down once, between 256 KiB and 1 MiB, on both boots.' % l1_txt)
    sizes_w = sorted({r['size'] for k in wr for r in wr[k]})
    trows = []
    for s in sizes_w:
        a, b_, c, d = val(w1s, s), val(w2s, s), val(w1l, s), val(w2l, s)
        trows.append([DATA.fmt_size(s), _g2(a), '%.2f' % bpc(a) if a else 'no row', _g2(b_),
                      '%.2f' % bpc(b_) if b_ else 'no row', _g2(c), _g2(d)])
    out += S.table(
        ['Footprint', 'Single-call, F1<br>GB/s', 'Single-call, F1<br>B/cycle', 'Single-call, F2<br>GB/s',
         'Single-call, F2<br>B/cycle', 'Looped, F1<br>GB/s', 'Looped, F2<br>GB/s'], trows, align='lrrrrrr',
        caption='CME write rate by footprint, bracket rates of the best rows. F1 is %s. F2 is %s. '
                'Files as in Figure %d. The full tables of %s give three decimals.' % (
                    name['F1'], name['F2'], S.n_fig, S.xref('bw-full')),
        note='"no row": the boots have no row of that form at that footprint. B/cycle = GB/s / %.2f. ' % cpn
             + two16 % (G['l1-looped']['reps'], G['sweep']['reps'],
                        _g2(row('F1', 'sweep', 'write', 16 * K)['best']), _g2(row('F2', 'sweep', 'write', 16 * K)['best']),
                        S.xref('bw-core', cap=True), S.xref('bw-64'), S.xref('glance-repeat', cap=True)))
    cmp_sizes = [s for s in sizes_w if val(w1s, s) and val(w1l, s) and s >= 16 * K]
    w_diff = max(pct(val(wr[(b, 'looped')], s), val(wr[(b, 'single-call')], s)) for b in ('F1', 'F2') for s in cmp_sizes)
    w16 = {b: pct(row(b, 'sweep', 'write', 16 * K)['best'], val(wr[(b, 'single-call')], 16 * K)) for b in ('F1', 'F2')}
    # read throughput divided by write throughput, single-call form, span rates
    svl = {r['boot']: r for r in D.store_vs_load}
    for b_ in ('F1', 'F2'):
        assert svl[b_]['size'] == 16 * K
        assert svl[b_]['read_span_gbps'] == row(b_, 'l1-single', 'read', 16 * K)['best_span']
        assert svl[b_]['write_span_gbps'] == row(b_, 'l1-single', 'write', 16 * K)['best_span']
    span_of = {(b, k): {r['size']: r['best_span'] for r in t[(b, 'single-call')]}
               for b in ('F1', 'F2') for k, t in (('read', rd), ('write', wr))}
    rw_span = {b: [span_of[(b, 'read')][s_] / span_of[(b, 'write')][s_] for s_ in l1_sizes] for b in ('F1', 'F2')}
    out += S.bullets([
        'On %s the rate goes from %s to %s GB/s, which is %.2f times. On %s it goes from %s to %s GB/s, which is %.2f times.' % (
            name['F1'], _g1(step['F1'][0]), _g1(step['F1'][1]), step['F1'][1] / step['F1'][0],
            name['F2'], _g1(step['F2'][0]), _g1(step['F2'][1]), step['F2'][1] / step['F2'][0]),
        'In the single-call form at %s to %s, the write loop runs at %.2f to %.2f effective cycles per 64 bytes '
        'transferred on %s and at %.2f to %.2f on %s (bracket rates). That number is 64 divided by the rate in B/cycle. '
        'It is a throughput of the whole loop, not the time of one store.' % (
            l1_lo, l1_hi, lim['F1']['write_cycles_per_vec_lo'], lim['F1']['write_cycles_per_vec_hi'], name['F1'],
            lim['F2']['write_cycles_per_vec_lo'], lim['F2']['write_cycles_per_vec_hi'], name['F2']),
        'At 16 KiB the read throughput divided by the write throughput is %.2f on %s and %.2f on %s '
        '(single-call form, span rates: %s against %s GB/s and %s against %s GB/s). '
        'In effective cycles per 64 bytes transferred that is %.2f for the read loop against %.2f for the write loop '
        'on %s, and %.2f against %.2f on %s.' % (
            svl['F1']['ratio'], name['F1'], svl['F2']['ratio'], name['F2'],
            _g3(svl['F1']['read_span_gbps']), _g3(svl['F1']['write_span_gbps']),
            _g3(svl['F2']['read_span_gbps']), _g3(svl['F2']['write_span_gbps']),
            svl['F1']['read_cycles_per_64b'], svl['F1']['write_cycles_per_64b'], name['F1'],
            svl['F2']['read_cycles_per_64b'], svl['F2']['write_cycles_per_64b'], name['F2']),
        'Over the footprints from %s to %s that ratio of span rates is %.2f to %.2f on %s and %.2f to %.2f on %s. '
        '%s lists this ratio as an open item.' % (
            l1_lo, l1_hi, min(rw_span['F1']), max(rw_span['F1']), name['F1'],
            min(rw_span['F2']), max(rw_span['F2']), name['F2'], S.xref('open-store', cap=True)),
        'From %s to %s the looped form and the single-call form of this table agree within %.1f %% on both boots. '
        'The second looped 16 KiB row, that of <code>cme-bandwidth-dram-1core.csv</code>, differs from the single-call '
        'row by %.1f %% on %s and %.1f %% on %s.' % (
            DATA.fmt_size(cmp_sizes[0]), DATA.fmt_size(cmp_sizes[-1]), _up1(w_diff),
            w16['F1'], name['F1'], w16['F2'], name['F2']),
    ])
    out += S.insufficient(
        'No write row exists between 256 KiB and 1 MiB, and no write row carries a cache counter. '
        'Write rows at 320, 384, 512 and 768 KiB would locate the step. CME refill counters on the bandwidth rows would '
        'name the level that takes the stored lines. No write row of this page is labelled with a destination level.')

    # ------------------------------------------------------------ 3. copy
    out += S.h3('bw-copy', 'Copy rows')
    c1, c2 = cp['F1'], cp['F2']
    big_c = [r['best'] for r in c1 if r['size'] >= 96 * K]
    c32 = val(c2, top32) / val(c1, top32)
    out += S.bullets([
        'The copy moves %s GB/s at 16 KiB and %s GB/s at 48 KiB on %s. The rate counts the bytes read plus the bytes '
        'written %s.' % (_g1(val(c1, 16 * K)), _g1(val(c1, 48 * K)), name['F1'], r_bwc),
        'From 96 KiB to 32 MiB the copy moves %s GB/s on %s. On %s the 32 MiB copy moves %s GB/s, %.2f times the %s rate.' % (
            rng(big_c), name['F1'], name['F2'], _g1(val(c2, top32)), c32, name['F1']),
    ])
    svg = V.line_chart(
        [dict(name='looped form, %s' % name[b], color=COL[b], points=pts(cp[b]), marker='triangle', dash=True) for b in BOOTS],
        x='log2', xticks=XT, xlabel='footprint of each of the two buffers (K = KiB, M = MiB)',
        ylabel='copy rate (bytes read plus bytes written, bracket), GB/s', yunit='GB/s',
        yfmt=lambda v: V.num(v, 1), ytickfmt=tick, vlines=[(L1_BYTES, 'CME L1 %s' % l1_txt)], yrange=(0, 125),
        labels=[(1, 16 * K), (1, 48 * K), (1, 96 * K), (1, top32), (0, top32)],
        gaps=[dict(x=top32, y0=val(c2, top32), y1=val(c1, top32), text='%.2f x' % c32, dx=-30)],
        annotations=[dict(x=8 * M, y=64, text='no row between\n%s and %s' % (gap_lo, gap_hi), dx=0, dy=0)],
        height=340)
    out += S.fig(
        svg,
        'CME copy rate against footprint on %s and %s, looped form, bracket rates of the best rows of '
        '<code>cme-bandwidth-dram-1core.csv</code> %s. A copy reads one buffer and writes a second buffer of the same '
        'footprint. The x axis has the range of Figure %d and Figure %d. The copy rows start at %s.' % (
            name['F1'], name['F2'], r_sweep, S.n_fig - 1, S.n_fig, DATA.fmt_size(min(r['size'] for r in c1))),
        'The copy rate falls between 48 KiB and 96 KiB, at the same footprints as the read rate. '
        'The two lines separate only at 32 MiB, where %s moves %.2f times the %s rate.' % (name['F2'], c32, name['F1']))
    trows = []
    for r1, r2 in zip(c1, c2):
        trows.append([r1['label'], str(r1['passes']), _g2(r1['best']), _g2(r1['best_span']), '%.2f' % r1['bytes_per_cycle'],
                      _g2(r2['best']), _g2(r2['best_span']), '%.2f' % r2['bytes_per_cycle'], '%.2f' % (r2['best'] / r1['best'])])
    out += S.table(
        ['Footprint', 'Passes<br>per rep', 'F1 bracket<br>GB/s', 'F1 span<br>GB/s', 'F1<br>B/cycle',
         'F2 bracket<br>GB/s', 'F2 span<br>GB/s', 'F2<br>B/cycle', 'F2 / F1<br>(bracket)'], trows, align='lrrrrrrrr',
        caption='CME copy rows, looped form, best rows of <code>cme-bandwidth-dram-1core.csv</code> %s. '
                'F1 is %s. F2 is %s.' % (r_sweep, name['F1'], name['F2']),
        note='Rates count bytes read plus bytes written. B/cycle is from the bracket rate. '
             'The full tables of %s give three decimals.' % S.xref('bw-full'))
    rd96 = val(f1l, 96 * K)
    cw = {s_: row('F1', 'sweep', 'write', s_)['best'] for s_ in (16 * K, 48 * K)}
    wr_half_dev = max(abs(val(c1, s_) / 2 - cw[s_]) for s_ in cw)
    # read half of the copy against the read kernel alone, at the footprints above the CME L1
    big_c = [r['size'] for r in c1 if r['size'] >= 96 * K]
    rd_half = {b: {s_: (val(cc_, s_) / 2) / row(b, 'sweep', 'read', s_)['best'] for s_ in big_c}
               for b, cc_ in (('F1', c1), ('F2', c2))}
    top_c = big_c[-1]
    mid_c = big_c[:-1]
    mid_ratio = [rd_half[b][s_] for b in ('F1', 'F2') for s_ in mid_c]
    out += S.bullets([
        'The 48 KiB copy touches two buffers of 48 KiB, which is 96 KiB in total. It moves %s GB/s on %s, '
        'against %s GB/s for the 16 KiB copy.' % (_g1(val(c1, 48 * K)), name['F1'], _g1(val(c1, 16 * K))),
        'Half of a copy rate is bytes written. At 16 KiB and 48 KiB that half is %s and %s GB/s on %s. '
        'The looped write kernel moves %s and %s GB/s at the same footprints.' % (
            _g1(val(c1, 16 * K) / 2), _g1(val(c1, 48 * K) / 2), name['F1'], _g1(cw[16 * K]), _g1(cw[48 * K])),
        'So at 16 KiB and 48 KiB the written half of the copy equals the rate of the write kernel alone within '
        '%s GB/s.' % _g1(wr_half_dev),
        'At 96 KiB the copy moves %s GB/s on %s, of which %s GB/s is bytes read. '
        'The looped read kernel moves %s GB/s at 96 KiB.' % (
            _g1(val(c1, 96 * K)), name['F1'], _g1(val(c1, 96 * K) / 2), _g1(rd96)),
        'So from %s to %s the read half of the copy is %.2f to %.2f times the rate of the read kernel alone '
        '(both boots). At %s it is %.2f times on %s and %.2f times on %s.' % (
            DATA.fmt_size(mid_c[0]), DATA.fmt_size(mid_c[-1]), min(mid_ratio), max(mid_ratio),
            DATA.fmt_size(top_c), rd_half['F1'][top_c], name['F1'], rd_half['F2'][top_c], name['F2']),
    ])
    out += S.insufficient(
        'Why the read half of a copy above the CME L1 is slower than the read kernel alone. The copy rows carry '
        'no counter. CME refill counters on a copy row would show whether the loads or the stores of the copy '
        'wait for refills (%s).' % S.xref('open-small'))
    out += S.hyp(
        'Stored lines do not take CME L1 space the way loaded lines do. Under that reading only the 48 KiB source '
        'buffer has to fit in the %s L1.' % l1_txt,
        'CME refill counters on the copy rows at 48 KiB and 96 KiB. A count near 0 refills per line at 48 KiB would '
        'confirm it.')
    out += S.insufficient(
        'The copy kernel exists in the looped form only, at %s to %s. The boots have no single-call copy row, '
        'no copy row at 4, 8 or 24 KiB, and no copy row on OCM. Those rows would be needed to '
        'give a copy rate without one kernel call per pass.' % (
            DATA.fmt_size(min(r['size'] for r in c1)), DATA.fmt_size(max(r['size'] for r in c1))))

    # ------------------------------------------------------------ 4. core against CME
    out += S.h3('bw-core', 'Core against CME at equal footprints, %s' % name['F1'])
    cv = D.core_vs_cme_bw
    g3r = [r for r in cv if r['kernel'] == 'read' and r['size'] == 16 * K][0]
    g3w = [r for r in cv if r['kernel'] == 'write' and r['size'] == 16 * K][0]
    n_above = len([r for r in cv if r['looped_over_core'] > 1])
    below = [r for r in cv if r['looped_over_core'] <= 1]
    assert len(below) == 1 and below[0]['cme_single'] is not None      # the sentence below names one exception
    out += S.bullets([
        'At 16 KiB the single-call CME read moves %s GB/s against %s GB/s on the core, %.2f times. '
        'The single-call CME write moves %s GB/s against %s GB/s, %.2f times.' % (
            _g1(g3r['cme_single']), _g1(g3r['core']), g3r['single_over_core'],
            _g1(g3w['cme_single']), _g1(g3w['core']), g3w['single_over_core']),
        'In the looped form the CME rate is above the core rate in %d of %d rows. The exception is the %s %s '
        '(%.2f times). Each looped pass includes one kernel call (%s). '
        'The single-call %s at the same footprint is %.2f times the core rate.' % (
            n_above, len(cv), below[0]['label'], below[0]['kernel'], below[0]['looped_over_core'],
            S.xref('callcost'), below[0]['kernel'], below[0]['single_over_core']),
    ])
    drows = []
    for kern in ('read', 'write', 'copy'):
        drows.append(dict(header=kern.capitalize()))
        for r in [x for x in cv if x['kernel'] == kern]:
            if r['cme_single'] is not None:
                drows.append(dict(label='%s, single-call form' % r['label'], a=r['core'], b=r['cme_single'],
                                  gap='%.2f x' % r['single_over_core']))
            drows.append(dict(label='%s, looped form' % r['label'], a=r['core'], b=r['cme_looped'],
                              gap='%.2f x' % r['looped_over_core']))
    svg = V.dumbbell(drows, a_name='core, boot F1', b_name='CME, %s' % name['F1'], a_color='core', b_color='f1',
                     unit='GB/s', fmt=lambda v: V.num(v, 1), xlabel='rate (bracket), GB/s', label_w=200, row_h=28)
    single_sizes = sorted({r['size'] for r in cv if r['cme_single'] is not None and r['size'] > 16 * K})
    r_s1_f1 = S.ref('file:F1:cme-bandwidth-dram-1core-asmpasses.csv')
    core_files = (
        'Core rows: <code>bandwidth-dram-1core.csv</code> %s. CME looped rows: <code>cme-bandwidth-dram-1core.csv</code> %s. '
        'CME single-call rows at 16 KiB: <code>cme-bandwidth-l1-asmpasses.csv</code> %s. CME single-call rows at %s to %s: '
        '<code>cme-bandwidth-dram-1core-asmpasses.csv</code> %s.' % (
            r_core, S.ref('file:F1:cme-bandwidth-dram-1core.csv'), S.ref('file:F1:cme-bandwidth-l1-asmpasses.csv'),
            DATA.fmt_size(single_sizes[0]), DATA.fmt_size(single_sizes[-1]), r_s1_f1))
    top_s = max([r for r in cv if r['cme_single'] is not None], key=lambda r: r['single_over_core'])
    not_right = [r for r in cv if r['cme_looped'] <= r['core']] + [
        r for r in cv if r['cme_single'] is not None and r['cme_single'] <= r['core']]
    assert not_right == below and len(below) == 1          # the takeaway names the one row that is not to the right
    out += S.fig(
        svg,
        'Core rate and CME rate at equal footprints on %s, bracket rates of the best rows. %s The bold number is the CME rate '
        'divided by the core rate. The copy rates count bytes read plus bytes written.' % (name['F1'], core_files),
        'The CME dot is to the right of the core dot in every row except the looped %s %s. '
        'The largest ratio is the single-call %s %s, %.2f times.' % (
            below[0]['label'], below[0]['kernel'], top_s['label'], top_s['kernel'], top_s['single_over_core']))
    trows = []
    for kern in ('read', 'write', 'copy'):
        trows.append(kern.capitalize())
        for r in [x for x in cv if x['kernel'] == kern]:
            trows.append([r['label'], _g3(r['core']), '%.2f' % r['core_bytes_per_cycle'], _g3(r['cme_looped']),
                          '%.2f' % r['looped_over_core'], _g3(r['cme_single']),
                          '%.2f' % r['single_over_core'] if r.get('single_over_core') else 'no row'])
    sweep_sizes = sorted({r['size'] for r in D.bw_table('sweep', 'F1', 'read')})
    no_core = [DATA.fmt_size(s_) for s_ in sweep_sizes if s_ not in core_sizes]
    out += S.table(
        ['Footprint', 'Core<br>GB/s', 'Core<br>B/cycle', 'CME looped<br>GB/s', 'Looped / core', 'CME single-call<br>GB/s',
         'Single-call / core'], trows, align='lrrrrrr',
        caption='Core against CME on %s, bracket rates of the best rows. %s' % (name['F1'], core_files),
        note='"no row": the boot has no single-call CME row at that footprint or for that kernel. '
             'The core file has no row at %s. The rates keep three decimals here, because no other table of this '
             'section holds the core rows. The looped 16 KiB CME rows are those of <code>cme-bandwidth-dram-1core.csv</code> '
             '(%s reps). The rows of <code>cme-bandwidth-l1-passes.csv</code> (%s reps) read %s GB/s (read) and %s GB/s (write), '
             'as in %s and %s.' % (
                 ' and at '.join(no_core), G['sweep']['reps'], G['l1-looped']['reps'],
                 _g3(row('F1', 'l1-looped', 'read', 16 * K)['best']), _g3(row('F1', 'l1-looped', 'write', 16 * K)['best']),
                 S.xref('bw-read'), S.xref('bw-write')))
    big = {k: [r['looped_over_core'] for r in cv if r['kernel'] == k and r['size'] >= 96 * K] for k in ('read', 'write', 'copy')}
    top = max(cv, key=lambda r: r['looped_over_core'])
    cw = [r['core'] for r in cv if r['kernel'] == 'write']
    out += S.bullets([
        'From 96 KiB to 32 MiB the looped CME rate is %s times the core rate for the read, %s times for the write '
        'and %s times for the copy.' % (
            rng(big['read'], lambda v: '%.2f' % v), rng(big['write'], lambda v: '%.2f' % v),
            rng(big['copy'], lambda v: '%.2f' % v)),
        'The largest looped ratio is the %s %s: %s GB/s through the CME against %s GB/s on the core (%.2f times). '
        'The single-call %s at that footprint is %.2f times the core rate. '
        'That footprint is above the %s L1 data cache of the core %s and below the %s L1 of the CME (operator\'s README) %s.' % (
            top['label'], top['kernel'], _g1(top['cme_looped']), _g1(top['core']), top['looped_over_core'],
            top['kernel'], top['single_over_core'],
            DATA.fmt_size(cache['size_bytes']), r_sys, l1_txt, r_l1size),
        'The core write rate is %s GB/s at every footprint.' % rng(cw),
        'The two kernels are not the same code. The core kernel moves 16 bytes per register with LDP and STP and has '
        'no fold %s. The CME kernel moves 64 bytes per vector.' % r_bwc,
    ])
    out += S.insufficient(
        '%s ran the CME rows only. Core rows on a boot with the prefetchers off would be needed to compare the core '
        'and the CME without prefetchers.' % Name['F2'])

    # ------------------------------------------------------------ 5. 64-byte forms
    out += S.h3('bw-64', 'The 64-byte forms')
    f64 = D.forms64
    w64 = [r for r in f64 if r['kernel'] == 'write64']
    r64_16 = {r['boot']: r for r in f64 if r['kernel'] == 'read64' and r['size'] == 16 * K}
    w_f1 = [abs(r['ratio_to_256'] - 1) * 100 for r in w64 if r['boot'] == 'F1']
    w_f2 = max([r for r in w64 if r['boot'] == 'F2'], key=lambda r: abs(r['ratio_to_256'] - 1))
    alt16 = {b: row(b, 'l1-looped', 'read', 16 * K)['best'] for b in ('F1', 'F2')}
    out += S.p('The main read and write kernels move 256 bytes per instruction (four vectors). '
               'The kernels <code>cme-ldr16</code> and <code>cme-str16</code> move 64 bytes per instruction (one vector) %s. '
               'Their CSV names come from the core kernels. They do not mean 16 bytes.' % r_kern)
    n_fp64 = len({r['size'] for r in w64})
    assert len({r['size'] for r in w64 if r['boot'] == 'F1'}) == n_fp64
    bullets64 = S.bullets([
        'The 64-byte write is within %.1f %% of the 256-byte write at all %d footprints on %s. '
        'On %s the largest difference is %.1f %%, at %s.' % (
            _up1(max(w_f1)), n_fp64, name['F1'], name['F2'], abs(w_f2['ratio_to_256'] - 1) * 100, w_f2['label']),
        'The 64-byte read at 16 KiB moves %s GB/s on %s and %s GB/s on %s. The 256-byte read of the same file moves '
        '%s and %s GB/s. So the 64-byte form is %.2f times the 256-byte form on %s and %.2f times on %s.' % (
            _g1(r64_16['F1']['gbps']), name['F1'], _g1(r64_16['F2']['gbps']), name['F2'],
            _g1(r64_16['F1']['gbps_256']), _g1(r64_16['F2']['gbps_256']),
            r64_16['F1']['ratio_to_256'], name['F1'], r64_16['F2']['ratio_to_256'], name['F2']),
        'A second looped 16 KiB read row of the 256-byte form is in <code>cme-bandwidth-l1-passes.csv</code> %s. '
        'It reads %s GB/s on %s and %s GB/s on %s. Against that row the 64-byte form is %.2f times on %s and %.2f times on %s.' % (
            r_l1, _g1(alt16['F1']), name['F1'], _g1(alt16['F2']), name['F2'],
            r64_16['F1']['gbps'] / alt16['F1'], name['F1'], r64_16['F2']['gbps'] / alt16['F2'], name['F2']),
    ])
    hrows = []
    for kern, word in (('read64', 'Read'), ('write64', 'Write')):
        for s in sorted({r['size'] for r in f64}):
            a = {r['boot']: r for r in f64 if r['kernel'] == kern and r['size'] == s}
            hrows.append(dict(header='%s, %s' % (word, DATA.fmt_size(s))))
            hrows.append(dict(label='64 B per instruction', values=[a['F2']['gbps'], a['F1']['gbps']],
                              notes=['= %.2f x the 256 B form' % a['F2']['ratio_to_256'],
                                     '= %.2f x the 256 B form' % a['F1']['ratio_to_256']]))
            hrows.append(dict(label='256 B per instruction', values=[a['F2']['gbps_256'], a['F1']['gbps_256']]))
    svg = V.hbar(hrows, series=[(name['F2'], 'f2'), (name['F1'], 'f1')], unit='GB/s', fmt=lambda v: V.num(v, 1),
                 xlabel='rate (bracket), GB/s', width=900)
    others = [abs(r['ratio_to_256'] - 1) * 100 for r in f64 if not (r['kernel'] == 'read64' and r['size'] == 16 * K)]
    out += S.fig(
        svg,
        'The 64-byte forms beside the 256-byte forms at 16 KiB, 2 MiB and 32 MiB on %s and %s. Looped form, bracket rates '
        'of the best rows of <code>cme-bandwidth-dram-1core.csv</code> %s (kernels <code>cme-ldr16</code>, '
        '<code>cme-str16</code>, <code>cme-read</code>, <code>cme-write</code>). The text after each 64 B bar is the 64 B rate '
        'divided by the 256 B rate of the same boot. In the %d groups other than the 16 KiB read the two forms differ '
        'by at most %.1f %%.' % (name['F1'], name['F2'], r_sweep,
                                 len({(r['kernel'], r['size']) for r in f64}) - 1, _up1(max(others))),
        'The largest difference between the two forms is at the 16 KiB read. There the 64-byte form moves %.2f times the '
        '256-byte rate on %s and %.2f times on %s.' % (
            r64_16['F1']['ratio_to_256'], name['F1'], r64_16['F2']['ratio_to_256'], name['F2']))
    out += bullets64
    trows = []
    for kern, word in (('read64', 'Read'), ('write64', 'Write')):
        trows.append(word)
        for s in sorted({r['size'] for r in f64}):
            a = {r['boot']: r for r in f64 if r['kernel'] == kern and r['size'] == s}
            trows.append([DATA.fmt_size(s), _g2(a['F1']['gbps']), _g2(a['F1']['gbps_256']), '%.2f' % a['F1']['ratio_to_256'],
                          _g2(a['F2']['gbps']), _g2(a['F2']['gbps_256']), '%.2f' % a['F2']['ratio_to_256'],
                          '%.2f' % (a['F2']['gbps'] / a['F1']['gbps'])])
    out += S.table(
        ['Footprint', 'F1, 64 B form<br>GB/s', 'F1, 256 B form<br>GB/s', 'F1<br>64 B / 256 B',
         'F2, 64 B form<br>GB/s', 'F2, 256 B form<br>GB/s', 'F2<br>64 B / 256 B', 'F2 / F1<br>(64 B form)'], trows,
        align='lrrrrrrr',
        caption='The 64-byte forms, looped form, bracket rates of the best rows of '
                '<code>cme-bandwidth-dram-1core.csv</code> %s. F1 is %s. F2 is %s.' % (r_sweep, name['F1'], name['F2']),
        note='The 256 B rows at 16 KiB are those of <code>cme-bandwidth-dram-1core.csv</code>. Against the 16 KiB read row of '
             '<code>cme-bandwidth-l1-passes.csv</code> the 64 B / 256 B ratio is %.2f on F1 and %.2f on F2. '
             'The full tables of %s give three decimals.' % (
                 r64_16['F1']['gbps'] / alt16['F1'], r64_16['F2']['gbps'] / alt16['F2'], S.xref('bw-full')))
    out += S.insufficient(
        'No row explains why the 16 KiB read of the 64-byte form is lower than the 256-byte form on %s and higher on %s. '
        'CME refill counters on these two rows would show whether the prefetchers add L1 refills at 16 KiB.' % (
            name['F1'], name['F2']))

    # ------------------------------------------------------------ 6. prefetchers
    out += S.h3('bw-pf', 'Prefetchers on against off at 1 MiB to 32 MiB')
    pf = [r for r in D.bw_f1_vs_f2 if r['group'] == 'sweep' and r['size'] >= 1 * M]

    def pfr(kern, size):
        return [r for r in pf if r['kernel'] == kern and r['size'] == size][0]
    wpf = [r['f2_over_f1'] for r in pf if r['kernel'] in ('write', 'write64')]
    out += S.bullets([
        'At 32 MiB the read rate on %s is %.3f times the rate on %s (%s against %s GB/s). '
        'At 1 MiB and 2 MiB that ratio is %.3f and %.3f.' % (
            name['F2'], pfr('read', top32)['f2_over_f1'], name['F1'],
            _g1(pfr('read', top32)['f2']), _g1(pfr('read', top32)['f1']),
            pfr('read', 1 * M)['f2_over_f1'], pfr('read', 2 * M)['f2_over_f1']),
        'For the write rows the same ratio is %s. For the 32 MiB copy it is %.3f.' % (
            rng(wpf, lambda v: '%.3f' % v), pfr('copy', top32)['f2_over_f1']),
    ])
    drows = []
    for kern, word in (('read', 'Read'), ('read64', 'Read, 64 B per instruction'), ('write', 'Write'),
                       ('write64', 'Write, 64 B per instruction'), ('copy', 'Copy')):
        rr = [r for r in pf if r['kernel'] == kern]
        if not rr:
            continue
        drows.append(dict(header=word))
        for r in rr:
            drows.append(dict(label=r['label'], a=r['f2'], b=r['f1'], gap='%.3f x' % r['f2_over_f1']))
    svg = V.dumbbell(drows, a_name=name['F2'], b_name=name['F1'], a_color='f2', b_color='f1', unit='GB/s',
                     fmt=lambda v: V.num(v, 1), xlabel='rate (bracket), GB/s', label_w=200, row_h=28)
    rd32 = [pfr(k, top32)['f2_over_f1'] for k in ('read', 'read64')]
    out += S.fig(
        svg,
        'CME rates at 1 MiB to 32 MiB on %s and %s. Looped form, bracket rates of the best rows of '
        '<code>cme-bandwidth-dram-1core.csv</code> %s. The bold number is the %s rate divided by the %s rate.' % (
            name['F2'], name['F1'], r_sweep, name['F2'], name['F1']),
        'With the prefetchers off the two 32 MiB read rows move %.2f and %.2f times the %s rate. '
        'The 32 MiB copy moves %.2f times. The write rows differ by at most %.1f %%.' % (
            rd32[0], rd32[1], name['F1'], pfr('copy', top32)['f2_over_f1'], _up1(max(abs(v - 1) for v in wpf) * 100)))
    trows, hl = [], []
    for kern in ('read', 'read64', 'write', 'write64', 'copy'):
        for r in [x for x in pf if x['kernel'] == kern]:
            trows.append([KNAME[kern], r['label'], _g2(r['f1']), _g2(r['f2']), '%.3f' % r['f2_over_f1'],
                          '%.2f' % r['f1_spread_pct'], '%.2f' % r['f2_spread_pct'], 'yes' if r['reps_apart'] else 'no'])
            hl.append(bool(r['reps_apart']) and abs(r['f2_over_f1'] - 1) > 0.05)
    spread_note = 'Rep spread: highest minus lowest bracket rate of the reps, in percent of the lowest.'
    out += S.table(
        ['Kernel', 'Footprint', 'F1<br>GB/s', 'F2<br>GB/s', 'F2 / F1', 'F1 rep<br>spread, %', 'F2 rep<br>spread, %', 'Reps apart'],
        trows, align='llrrrrrc',
        caption='Rates at 1 MiB to 32 MiB on the two boots, looped form, bracket rates of the best rows of '
                '<code>cme-bandwidth-dram-1core.csv</code> %s. F1 is %s. F2 is %s.' % (r_sweep, name['F1'], name['F2']),
        note='"Reps apart: yes" means that every rep of one boot is above every rep of the other boot. '
             'A highlighted row has its reps apart and a ratio more than 5 %% away from 1. %s '
             'The ratio keeps three decimals, because several ratios are within 1 %% of 1. '
             'The full tables of %s give the rates with three decimals.' % (spread_note, S.xref('bw-full')),
        highlight=lambda i, r: hl[i])
    n_apart = len([r for r in pf if r['reps_apart']])
    out += S.bullets([
        'In %d of the %d rows every rep of one boot is above every rep of the other boot.' % (n_apart, len(pf)),
        'A ratio here is a difference between two boots. The two boots differ in the prefetcher setting '
        '(operator\'s README), and the rows carry no counter that shows prefetched lines.',
    ])
    out += S.insufficient(
        'No boot was run twice, so the spread between two boots with the same setting is unknown. '
        'A second boot with each setting would show how much of a ratio near 1 is that spread.')

    # ------------------------------------------------------------ 7. lines in flight
    out += S.h3('bw-flight', 'Lines in flight (est.)')
    lf = []
    for r in D.lines_in_flight:
        ch = D.chain_row(r['boot'], r['size'])
        assert ch['src'] == r['chain_src'] and ch['best'] == r['chain_ns']
        lf.append(dict(r, kind=ch['kind']))        # a copy: the rows of D stay as they are
    lf2 = [r for r in lf if r['boot'] == 'F2']
    lf1 = [r for r in lf if r['boot'] == 'F1']
    sub2 = [r['ratio_above_rt_est'] for r in lf2]
    assert sub2 == sorted(sub2)                 # the text says that these rise with the footprint
    kind_txt = ' '.join('%s: chain %s (<code>%s</code>).' % (
        r['label'], r['kind'], r['chain_src']) for r in lf2)
    out += S.bullets([
        'A line request is in flight between the moment the CME sends it and the moment the line arrives.',
        'The looped read has an effective time per 64 bytes transferred: 64 divided by its rate in GB/s, in ns. '
        'It is a throughput of the whole loop, not the time of one load.',
        'On %s the chain load time is %s times that effective time (est.), at 256 KiB, 2 MiB and 32 MiB.' % (
            name['F2'], rng([r['ratio_est'] for r in lf2])),
        'This ratio is an estimate of how many line requests overlap in a looped read. No row measures that number.',
    ])
    trows = []
    for grp_ in (lf2, lf1):
        trows.append(Name[grp_[0]['boot']])
        for r in grp_:
            trows.append([r['label'], r['kind'], '%.3f' % r['chain_ns'], _g2(r['read_gbps']), '%.3f' % r['ns_per_line'],
                          '%.1f' % r['ratio_est'], '%.1f' % r['ratio_above_rt_est']])
    r_lat = S.ref('csv:cme-latency-dram-small-large',
                  'Files <code>cme-latency-dram-small.csv</code> (256 KiB row) and <code>cme-latency-dram-large.csv</code> '
                  '(2 MiB and 32 MiB rows) of both boots: the chain load, best rows of the latency test.')
    frows = [dict(label=a['label'], sub='chain ' + a['kind'], values=[a['ratio_est'], b['ratio_est']],
                  notes=['(%.1f with the round-trip baseline subtracted), est.' % a['ratio_above_rt_est'],
                         '(%.1f with the round-trip baseline subtracted), est.' % b['ratio_above_rt_est']])
             for a, b in zip(lf2, lf1)]
    fig = S.fig(
        V.hbar(frows, series=[(name['F2'], 'f2'), (name['F1'], 'f1')], unit='', fmt=lambda v: '%.1f' % v,
               xlabel='chain load time / effective time per 64 bytes transferred of the looped read (est.)',
               width=900, label_w=150),
        'Hypothesis figure. Chain load time divided by the effective time per 64 bytes transferred of the looped read, '
        'at the same footprint and boot (est.). The number in brackets after each bar is the same ratio with the '
        'round-trip baseline subtracted from the chain load time. The round-trip baseline is a separate measurement. '
        'Bracket times of the best rows. %s Chain load: %s. '
        'Read rate: <code>cme-bandwidth-dram-1core.csv</code> %s.' % (kind_txt, r_lat, r_sweep),
        'On %s the ratios are %s with the whole chain load time. With the round-trip baseline subtracted '
        'they are %s and rise with the footprint. On %s the ratios with the whole chain load time are %s.' % (
            name['F2'], rng([r['ratio_est'] for r in lf2]), rng(sub2), name['F1'], rng([r['ratio_est'] for r in lf1])))
    tab = fig + S.table(
        ['Footprint', 'Chain kind', 'Chain load<br>ns', 'Read rate<br>GB/s', 'Effective time per<br>64 B transferred, ns',
         'Ratio<br>(lines in flight, est.)', 'Ratio with the round-trip<br>baseline subtracted (est.)'], trows,
        align='llrrrrr',
        caption='Hypothesis table. Chain load time divided by the effective time per 64 bytes transferred of the looped '
                'read at the same footprint and boot (est.). Chain load: %s. Read rate: <code>cme-bandwidth-dram-1core.csv</code> %s.' % (
                    r_lat, r_sweep),
        note='Effective time per 64 B transferred = 64 / rate in GB/s. It is a throughput of the whole read loop, not the '
             'time of one load. The ratio columns are estimates. The last column subtracts the round-trip baseline of '
             '%.3f ns, a separate measurement with no memory access, from the chain load time. All times are bracket times of '
             'the best row. The 256 KiB chain load comes from <code>cme-latency-dram-small.csv</code>, the 2 MiB and '
             '32 MiB chain loads from <code>cme-latency-dram-large.csv</code>.' % D.rt_ns)
    S.term('chain load', 'one dependent load of the latency test: its address comes from the load before it')
    S.term('round-trip baseline', 'the latency row that sends a value from the core to the CME and back with no '
                                  'memory load. It is a separate measurement. A chain load minus this value is the '
                                  'difference between two kernels, not a memory-access time')
    out += S.hyp(
        '</p>%s<p>'
        'With the prefetchers off the CME keeps between %.0f and %.0f line requests in flight during a looped read (est.). '
        'The upper value is the ratio with the whole chain load time, which is %s on %s at the '
        '%d footprints. '
        'On %s that ratio is %s, and the prefetchers add requests of their own there.'
        '</p><p>Every chain load returns its result to the core through LASTB. A looped read does not. '
        'The round-trip baseline is a separate measurement with no memory access, and it reads %.3f ns per step. '
        'The lower value subtracts that baseline from the chain load time. That subtraction is the measured difference '
        'between two kernels. The rows do not show that it is the time of the memory access alone. '
        'With the baseline subtracted the %s ratios are %s (est.), and they rise with the footprint. '
        'So the rows do not show one fixed number. The %d chain loads are also not of one chain kind. %s' % (
            tab, min(sub2), max(r['ratio_est'] for r in lf2), rng([r['ratio_est'] for r in lf2]), name['F2'], len(lf2),
            name['F1'], rng([r['ratio_est'] for r in lf1]), D.rt_ns, name['F2'],
            ', '.join('%.1f' % v for v in sub2), len(lf2),
            ' '.join('The %s chain is %s.' % (r['label'], r['kind']) for r in lf2)),
        'A latency test that walks N independent chains in the same loop, for N from 1 to 32. The loads per second stop '
        'rising at the N that equals the number of requests in flight.')
    out += S.insufficient(
        'The chain-load kernel and the round-trip baseline kernel share work that is not a memory access. '
        'No row measures that shared work. A calibration of it would be needed to call the chain load minus the '
        'baseline a memory-access time, and to choose between the two ratios of this section.')

    # ------------------------------------------------------------ 8. full tables
    out += S.h3('bw-full', 'Full tables')
    allrows = {f: [r for b in ('F1', 'F2') for g in gs for r in D.bw_table(g, b)]
               for f, gs in (('looped', ('l1-looped', 'sweep')), ('single-call', ('l1-single', 'sweep-single')))}
    assert all(r['best_span'] > r['best'] for f in allrows for r in allrows[f])
    sob = {f: [r['best_span'] / r['best'] for r in allrows[f]] for f in allrows}
    lw4, lr4, lr32 = row('F1', 'l1-looped', 'write', 4 * K), row('F1', 'l1-looped', 'read', 4 * K), row('F1', 'sweep', 'read', top32)
    # the note of the looped table states these two relations
    for b_ in ('F1', 'F2'):
        for r in D.bw_table('l1-looped', b_, 'write'):
            assert r['best_span'] > row(b_, 'l1-single', 'write', r['size'])['best']
        for r in D.bw_table('l1-looped', b_, 'read'):
            assert r['best_span'] < row(b_, 'l1-single', 'read', r['size'])['best']
    out += S.bullets([
        'Table %d holds every looped row of <code>cme-bandwidth-l1-passes.csv</code> and of '
        '<code>cme-bandwidth-dram-1core.csv</code>. Table %d holds every single-call row of the two boots.' % (
            S.n_table + 1, S.n_table + 2),
        'The other looped rows are not in these tables. %s holds the rows of the call-cost file, of the file with no fold '
        'and of the DSB ST file. %s holds the OCM rows.' % (S.xref('callcost', cap=True), S.xref('ocm', cap=True)),
        'The span rate is above the bracket rate in every row.',
        'In the looped form the span rate divided by the bracket rate falls as the footprint grows. On %s it is %.2f for '
        'the write and %.2f for the read at 4 KiB, and %.4f for the read at 32 MiB.' % (
            name['F1'], lw4['best_span'] / lw4['best'], lr4['best_span'] / lr4['best'], lr32['best_span'] / lr32['best']),
        'In the single-call form the same ratio is %.3f to %.3f over all rows of both boots.' % (
            min(sob['single-call']), max(sob['single-call'])),
    ])
    hdr = ['Kernel', 'Footprint', 'Passes<br>per rep', 'F1 bracket<br>GB/s', 'F1 span<br>GB/s', 'F1<br>B/cycle',
           'F1 rep<br>spread, %', 'F2 bracket<br>GB/s', 'F2 span<br>GB/s', 'F2<br>B/cycle', 'F2 rep<br>spread, %',
           'F2 / F1<br>(bracket)']
    short = {'read': 'read', 'write': 'write', 'copy': 'copy', 'read64': 'read, 64 B', 'write64': 'write, 64 B'}

    def full_rows(groups):
        rows = []
        for fname, group, kernels in groups:
            rows.append('<code>%s</code>, %s reps per row' % (fname, G[group]['reps']))
            for kern in kernels:
                for r1 in D.bw_table(group, 'F1', kern):
                    r2 = row('F2', group, kern, r1['size'])
                    rows.append([short[kern].replace(' ', '&nbsp;'), r1['label'], str(r1['passes']), _g3(r1['best']), _g3(r1['best_span']),
                                 '%.2f' % r1['bytes_per_cycle'], '%.2f' % r1['spread_pct'], _g3(r2['best']),
                                 _g3(r2['best_span']), '%.2f' % r2['bytes_per_cycle'], '%.2f' % r2['spread_pct'],
                                 '%.3f' % (r2['best'] / r1['best'])])
        return rows
    out += S.table(
        hdr, full_rows([
            ('cme-bandwidth-l1-passes.csv', 'l1-looped', ('read', 'write')),
            ('cme-bandwidth-dram-1core.csv', 'sweep', ('read', 'write', 'copy', 'read64', 'write64')),
        ]), align='llrrrrrrrrrr',
        caption='Looped form, both boots, best rows of <code>cme-bandwidth-l1-passes.csv</code> %s and '
                '<code>cme-bandwidth-dram-1core.csv</code> %s. F1 is %s. F2 is %s.' % (r_l1, r_sweep, name['F1'], name['F2']),
        note='"read, 64 B" and "write, 64 B" are the kernels that move 64 bytes per instruction. '
             'B/cycle is from the bracket rate. The span rate is that of the rep with the best bracket rate. %s '
             'The span rates of the looped rows at %s to %s are not rates to quote. There the looped write span rate is above '
             'the single-call rate, and the looped read span rate is below it. %s and %s give those rows. '
             'The rates to quote at these footprints are the single-call rates of Table %d.' % (
                 spread_note, G['l1-looped']['lo'], G['l1-looped']['hi'],
                 S.xref('callcost-write', cap=True), S.xref('callcost-scatter'), S.n_table + 2))   # + 2: the table after this one
    out += S.table(
        hdr, full_rows([
            ('cme-bandwidth-l1-asmpasses.csv', 'l1-single', ('read', 'write')),
            ('cme-bandwidth-dram-1core-asmpasses.csv', 'sweep-single', ('read', 'write')),
        ]), align='llrrrrrrrrrr',
        caption='Single-call form, both boots, best rows %s %s. F1 is %s. F2 is %s.' % (
            r_l11, r_sweep1, name['F1'], name['F2']),
        note='B/cycle is from the bracket rate. The span rate is that of the rep with the best bracket rate. %s' % spread_note)
    return out
