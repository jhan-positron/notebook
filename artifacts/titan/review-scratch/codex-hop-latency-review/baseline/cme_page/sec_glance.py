"""Section "Results at a glance" of asimov-cme-perf.html (SPEC outline item 3).

Subsections: the chain load by where the line comes from (critic G1), the numbers to quote
(G20), the measured rates against the documented limits (G2), the repeatability (G8) and
the numbers not to quote.  Every measured number is read from the data layer D.
"""

KEY = 'glance'
TITLE = 'Results at a glance'

KIB = 1024
MIB = 1024 * 1024
BOOTS = ('F2', 'F1')

# Typed facts of the sources and documents (not measurements).  Each one is cited where it is printed.
WRITE_STORES_PER_ITER = 4   # st1b instructions per 1 KiB iteration of the write loop (cme_kern.S lines 324 to 327)
READ_EORS_PER_ITER = 16     # EOR instructions per 1 KiB iteration of the read loop (cme_kern.S lines 178 to 193)
READ_LOADS_PER_ITER = 4     # ld1b instructions per 1 KiB iteration of the read loop (cme_kern.S lines 174 to 177)
VECTORS_PER_LOAD = 4        # vectors that one of these ld1b instructions loads
LLVM_LD4_CYCLES = 2         # cycles that the LLVM model holds the CME load pipe for one 4-vector load


# ------------------------------------------------------------------ small helpers

def _n(v, d=3):
    return '%.*f' % (d, v)


def _rng(lo, hi, d=3, unit=''):
    """'21.015 to 21.240 ns', or one value when both ends are equal."""
    u = (' ' + unit) if unit else ''
    if abs(hi - lo) < 0.5 * 10 ** (-d):
        return _n(lo, d) + u
    return '%s to %s%s' % (_n(lo, d), _n(hi, d), u)


def _lohi(vals):
    vals = list(vals)
    return min(vals), max(vals)


def _pct(a, b):
    """Difference of two values in percent of the lower one."""
    lo, hi = sorted((a, b))
    return (hi - lo) / lo * 100.0


def _and(items):
    """'a, b and c'."""
    items = list(items)
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def _reldir(D, boot):
    from . import data
    return data.BOOTDIR[boot].replace(data.ROOT.rstrip('/') + '/', '')


def _fref(D, S, boot, src):
    """[RefN] of one raw file of one boot.  `src` may hold several names joined by ', '."""
    out = []
    for name in [s.strip() for s in src.split(',')]:
        out.append(S.ref('file:%s:%s' % (boot, name),
                         'Boot %s, file <code>%s</code> in <code>%s/</code>.' % (boot, name, _reldir(D, boot))))
    return ' '.join(out)


def _code(src):
    return ', '.join('<code>%s</code>' % s.strip() for s in src.split(','))


def _single(D, boot, kernel):
    """Single-call rows of one boot and kernel, 4 KiB to 256 KiB (two files), by footprint."""
    rows = D.bw_table('l1-single', boot, kernel) + D.bw_table('sweep-single', boot, kernel)
    return sorted((r for r in rows if r['size'] <= 256 * KIB), key=lambda r: r['size'])


def _sweep(D, boot, kernel, lo, hi):
    return [r for r in D.bw_table('sweep', boot, kernel) if lo <= r['size'] <= hi]


def _looped_repeats(D, boot):
    """The looped rows (kernel and footprint) that two files of one boot hold.
    Each entry: kernel, size, label, the two rows, and the difference of the bracket rate and
    of the span rate in percent of the lower value."""
    seen = {}
    for group in ('sweep', 'l1-looped', 'call-cost'):
        for kernel in ('read', 'write'):
            for r in D.bw_table(group, boot, kernel):
                seen.setdefault((kernel, r['size']), []).append(r)
    out = []
    for (kernel, size), rr in sorted(seen.items()):
        if len(rr) != 2:
            continue
        a, b = rr
        if a['passes'] != b['passes']:
            raise ValueError('looped repeat with unequal passes: %s %d' % (kernel, size))
        out.append(dict(kernel=kernel, size=size, label=a['label'], a=a, b=b,
                        bracket_pct=_pct(a['best'], b['best']), span_pct=_pct(a['best_span'], b['best_span'])))
    return out


def _fitval(fit, key, d):
    """A fitted value, or the word 'void' when the plan rule voids the fit."""
    return _n(fit[key], d) if fit['verdict'] == 'pass' else 'void'


# ------------------------------------------------------------------ the section

def build(D, V, S):
    from . import data
    F1N, F2N = D.boot_name['F1'], D.boot_name['F2']
    BN = {'F1': F1N, 'F2': F2N}
    q = D.quote
    rt = D.rt_ns
    cpn = D.clock['cycles_per_ns']
    g2 = {r['key']: r for r in D.g1['F2']}
    g1 = {r['key']: r for r in D.g1['F1']}
    order = [r['key'] for r in D.g1['F2']]
    rp = D.repeatability

    # ---- terms (first definition wins, other sections may define them too)
    S.term('CME', 'the Arm C1-SME2 matrix engine unit. One per cluster, shared by two cores.')
    S.term('boot F1', 'the boot with the L3 on and the hardware prefetchers on. It has core rows and CME rows.')
    S.term('boot F2', 'the boot with the L3 on and the hardware prefetchers off. It has CME rows only.')
    S.term('chain load', 'one dependent load of the latency test. Its address is the value that the load before it returned.')
    S.term('latency test', 'the loop that walks a chain of dependent loads and reports the time per chain load.')
    S.term('round-trip baseline', 'the time of one step that sends a value from the core to the CME and back '
           '(instructions DUP and LASTB) with no memory load. It is a separate measurement, not a measured part '
           'of a chain load.')
    S.term('bracket time', 'the time between two clock reads in the C code around the kernel call or calls.')
    S.term('span time', 'the time between the two counter reads inside the kernel, after the CME enters streaming mode '
           'and before it leaves it.')
    S.term('bracket rate', 'the bytes moved in a rep divided by its bracket time, in GB/s.')
    S.term('span rate', 'the bytes moved in a rep divided by its span time, in GB/s.')
    S.term('best row', 'the row that the test program itself prints with the label <code>best</code>.')
    S.term('kernel', 'the test loop in the assembly file <code>cme_kern.S</code>. It does not mean the Linux kernel.')
    S.term('footprint', 'the number of bytes that a test touches.')
    S.term('pass', 'one walk over the buffer or over the chain.')
    S.term('rep', 'one timed measurement. The program prints several reps and marks the best one.')
    S.term('refill', 'one cache line brought into the CME L1 cache. An inner refill comes from inside the cluster. '
           'An outer refill comes from outside the cluster.')
    S.term('inner refill', 'a CME L1 refill whose line came from inside the cluster.')
    S.term('outer refill', 'a CME L1 refill whose line came from outside the cluster, through the mesh.')
    S.term('prefetch refill', 'a refill that the hardware prefetcher asked for, not a load of the program.')
    S.term('cluster', 'two cores, their shared L3 cache and one CME.')
    S.term('CME L1', 'the level 1 data cache of the CME.')
    S.term('OCM', 'on-chip memory: five regions of 256 KiB, each held by one home node of the mesh.')
    S.term('SLC', 'system level cache: the cache inside the mesh.')
    S.term('DRAM model', 'the memory behind the mesh. It is a memory model of the emulator, not silicon timing.')
    S.term('walked many times', 'a chain kind: the test walks the same chain many times in one rep.')
    S.term('walked once', 'a chain kind: each rep walks a chain that the test has not walked before.')
    S.term('every line flushed first', 'a chain kind: the test flushes every line of the chain from the caches before the timed walk.')
    S.term('chain shape', 'which lines of a buffer belong to the chain: every line, or one line per 4 KiB page.')
    S.term('looped form', 'the bandwidth form with one kernel call per pass.')
    S.term('single-call form', 'the bandwidth form with all passes of a rep in one assembly call.')
    S.term('GB/s', '1e9 bytes per second. 1 GB/s equals 1 byte per ns.')
    S.term('B/cycle', 'bytes per core cycle: the rate in GB/s divided by the measured cycles per ns.')
    S.term('effective rate', 'a throughput: what a whole rep transfers divided by the time of the rep. '
           'It is not the time that one load or one store takes to complete.')
    S.term('vector', 'one CME register of 64 bytes. One vector load or store moves 64 bytes.')
    S.term('LLVM model', 'the scheduling description of the C1-Nano in the LLVM compiler source.')
    S.term('load pipe, store pipe', 'A unit of the CME in the LLVM model. The load pipe runs the vector loads one after '
           'the other. The store pipe does the same for the vector stores.')
    S.term('plan rule', "the rule for a straight-line fit of time per pass against bytes per pass. "
           "A largest residual over 2 % of the smallest pass time makes the fit's intercept void.")
    S.term('intercept', 'The time that a fitted straight line gives at 0 bytes per pass.')
    S.term('residual', 'A measured time minus the time that the fitted line gives for the same bytes per pass.')
    S.term('control row', 'A row whose right answer is known before the run. An example is a run with an L3 that holds no data.')
    S.term('call-cost rows', 'The rows of the file <code>cme-bandwidth-call-cost.csv</code>. Each one times short kernel '
           'calls of the looped form, one call per pass.')
    S.term('repeat difference', 'The difference between two measurements of the same row inside one boot, '
           'in percent of the lower value.')
    S.term('cme-call row', 'a latency row that times 64 kernel calls of 64 bytes each, one directly after the other.')
    S.term('plain rows', 'the rows of the latency test at the same footprints with the refill counters and no L3 event.')
    S.term('L3-event rows', 'the rows of the latency test that were run with the three L3 events of the CME.')

    out = []

    # The two kernels of the latency test (typed fact of the source file, cited where it is printed).
    kc = S.ref('src:kern-chain', 'Source file <code>cme_kern.S</code>, lines 113 to 126: <code>cme_chase</code>, the '
               'chain-load kernel (LD1D, then LASTB). Lines 128 to 141: <code>cme_roundtrip</code>, the kernel of the '
               'round-trip baseline (a register copy in place of LD1D, then LASTB).')
    # Chain load minus round-trip baseline: the difference between two kernels, computed from the rows of D.
    d_l1 = (g2['l1']['bracket_lo'] - rt, g2['l1']['bracket_hi'] - rt)
    d_dram = g2['dram']['bracket_lo'] - rt
    for got, want in ((d_l1[0], g2['l1']['above_rt_lo']), (d_l1[1], g2['l1']['above_rt_hi']), (d_dram, g2['dram']['above_rt_lo'])):
        if abs(got - want) > 1e-9:
            raise ValueError('glance: chain load minus round-trip baseline differs from D.g1')

    no_boot_repeated = rp['all']['boots_repeated'] == 0
    out.append(S.takeaways([
        f'On {F2N}, a chain load takes {_rng(g2["l1"]["bracket_lo"], g2["l1"]["bracket_hi"], 3, "ns")} '
        f'for buffers that fit in the CME L1 and {_n(g2["dram"]["bracket_lo"])} ns in the DRAM-model row.',
        f'The round-trip baseline is {_n(rt)} ns in all {q["rt_files"]} files. '
        f'It is a separate measurement with no memory access.',
        f'The chain loads are {_rng(*d_l1, 3, "ns")} (CME L1) and {_n(d_dram)} ns (DRAM model) above the baseline. '
        f'Each number is the measured difference between two kernels. It does not isolate the time of the memory access.',
        f'A single-call read inside the CME L1 runs at {_rng(*q["l1_read_single_F2"], 1, "GB/s")} on {F2N}. '
        f'A single-call write runs at {_rng(*q["write_single"], 1, "GB/s")} on both boots.',
        ('No boot was repeated. ' if no_boot_repeated else '') +
        'Every repeat difference of this section is a difference inside one boot.',
    ]))

    # =============================================================== 3.1  G1
    out.append(S.h3('glance-where', 'What a chain load costs, by where the line comes from'))
    f1_prf = _lohi(g1[k]['hwprf_lo'] for k in order)
    out.append(S.bullets([
        f'On {F2N} the chain load is {_rng(g2["l1"]["bracket_lo"], g2["l1"]["bracket_hi"], 3, "ns")} (CME L1), '
        f'{_n(g2["cluster"]["bracket_lo"])} ns (inside the cluster), '
        f'{_n(g2["outside-1m"]["bracket_lo"])} to {_n(g2["outside-3m"]["bracket_lo"])} ns (outside the cluster), '
        f'{_n(g2["ocm"]["bracket_lo"])} ns (OCM) and {_n(g2["dram"]["bracket_lo"])} ns (DRAM model).',
        (f'On {F1N} every row counts prefetch refills, at least {_n(f1_prf[0], 4)} per load. '
         if f1_prf[0] > 0 else f'On {F1N} some rows count prefetch refills. ') +
        'So a boot F1 value is not the cost of one cache level.',
    ]))

    # Row names of this section.  The 32 MiB row has no flush and no counter that separates the SLC
    # from the DRAM model, so it is named by what its counter shows: the lines come from outside the cluster.
    where = {k: g2[k]['where'] for k in order}
    where['dram-32m'] = 'Outside the cluster'

    def short(k):
        return g2[k]['conditions'].split(',')[0]

    rows = []
    r2, r1 = g2['l1'], g1['l1']

    def l1_row(boot, value):
        # the footprint row of the CME L1 range whose best bracket time is `value`
        return [r for r in D.chain[boot] if r['kind'] == 'walked many times' and r['best'] == value][0]

    for which, key in (('lowest', 'bracket_lo'), ('highest', 'bracket_hi')):
        fa, fb = l1_row('F2', r2[key]), l1_row('F1', r1[key])
        if fa['size'] == fb['size']:
            label, sub = 'CME L1, %s' % fa['label'], 'the %s row of %s' % (which, r2['conditions'])
            tag = fa['label']
            name = '"%s"' % label
        else:
            label, sub = 'CME L1, %s row of each boot' % which, r2['conditions']
            tag = which
            name = '"CME L1, %s row"' % which
        rows.append(dict(label=label, sub=sub, a=r2[key], b=r1[key], name=name, tag=tag))
    for k in order[1:]:
        rows.append(dict(label=where[k], sub=g2[k]['conditions'], a=g2[k]['bracket_lo'], b=g1[k]['bracket_lo'],
                         name='"%s, %s"' % (where[k], short(k))))
    for r in rows:
        r['tip'] = '%s, %s\n%s: %s ns\n%s: %s ns\nboot F1 minus boot F2: %s' % (
            r['label'], r['sub'], F2N, _n(r['a']), F1N, _n(r['b']), V.signed(r['b'] - r['a'], 3, 'ns'))
    svg = V.dumbbell(rows, a_name=F2N, b_name=F1N, a_color='f2', b_color='f1', unit='ns',
                     xlabel='chain load, bracket time, ns', fmt=lambda v: V.num(v, 3),
                     refs=[(rt, 'round-trip baseline %s ns' % _n(rt))], label_w=270,
                     xrange=(0, 10 * (int(max(max(r['a'], r['b']) for r in rows) * 1.2 / 10) + 1)))
    files = sorted({g2[k]['src'] for k in order})
    cap = (f'Chain load of the CME by where the line comes from, best row of each footprint, bracket time. '
           f'Blue is {F2N}. Orange is {F1N}. The bold number is boot F1 minus boot F2. '
           f'The CME L1 has two rows, the lowest and the highest of its {g2["l1"]["n_rows"]} footprints. '
           f'Every other row is one footprint. '
           f'Files, same names on both boots: {", ".join(_code(f) for f in files)} '
           f'{" ".join(_fref(D, S, "F2", f) for f in files)} {" ".join(_fref(D, S, "F1", f) for f in files)}.')

    # the takeaway is built from the order of the dots, not typed
    blue, orange = [r['a'] for r in rows], [r['b'] for r in rows]
    n_rise = 1
    while n_rise < len(blue) and blue[n_rise] > blue[n_rise - 1]:
        n_rise += 1
    if n_rise == len(blue):
        tk = f'The blue dots are in rising order, from {_n(blue[0])} ns to {_n(blue[-1])} ns.'
    else:
        tk = f'The first {n_rise} blue dots are in rising order, from {_n(blue[0])} ns to {_n(blue[n_rise - 1])} ns.'
        for i in range(n_rise, len(blue)):
            if blue[i] < blue[i - 1]:
                tk += (f' The blue dot of the row {rows[i]["name"]} ({_n(blue[i])} ns) is '
                       f'{_n(blue[i - 1] - blue[i])} ns below the dot above it.')
    drop = [i for i in range(1, len(orange)) if orange[i] < orange[i - 1]]
    if drop:
        i = drop[0]
        tk += (f' The orange dots are not in rising order. The row {rows[i]["name"]} ({_n(orange[i])} ns) is below the row '
               f'{rows[i - 1]["name"]} ({_n(orange[i - 1])} ns).')
    out.append(S.fig(svg, cap, tk))

    def trow(k):
        a, b = g2[k], g1[k]
        if k == 'l1':
            gap = '<br>'.join('%s (%s)' % (V.signed(r['b'] - r['a'], 3), r['tag']) for r in rows[:2])
        else:
            gap = V.signed(b['bracket_lo'] - a['bracket_lo'], 3)
        # A range is set on two lines, so that the number columns stay narrow and the first column keeps its width.
        cells = [_rng(a['bracket_lo'], a['bracket_hi']), _rng(a['span_lo'], a['span_hi']),
                 _rng(a['above_rt_lo'], a['above_rt_hi']),
                 _rng(a['above_rt_lo'] * D.cycles_per_ns, a['above_rt_hi'] * D.cycles_per_ns, 2),
                 _rng(a['outer_lo'], a['outer_hi'], 4),
                 _rng(b['bracket_lo'], b['bracket_hi']), _rng(b['hwprf_lo'], b['hwprf_hi'], 2)]
        return ([f'{where[k]}<br>{a["conditions"]}<br>{_code(a["src"])}']
                + [c.replace(' to ', ' to<br>') for c in cells] + [gap])

    f2_prf_max = max(g2[k]['hwprf_hi'] for k in order)
    out.append(S.table(
        ['Where the line comes from,<br>conditions, file', 'F2 bracket,<br>ns', 'F2 span,<br>ns', 'F2 chain load<br>minus the<br>baseline, ns',
         'F2 chain load<br>minus the<br>baseline,<br>cycles', 'F2 outer<br>refills<br>per load', 'F1 bracket,<br>ns', 'F1 prefetch<br>refills<br>per load', 'F1 minus<br>F2, ns'],
        [trow(k) for k in order],
        caption=f'The rows of Figure {S.n_fig} with their exact numbers. F2 is {F2N}. F1 is {F1N}. '
                f'The CME L1 row holds the range of the two CME L1 rows of the figure.',
        note=f'Best row of each footprint. Span time and counters come from the first rep that equals the best row. '
             f'"Chain load minus the baseline" is the bracket time of the chain-load kernel minus the bracket time of the '
             f'round-trip kernel, which is {_n(rt)} ns. '
             f'It is the measured difference between two kernels {kc}. '
             f'It is not a measured part of a chain load, and it is not the time of the memory access. '
             f'The cycles column is that difference multiplied by the measured {D.cycles_per_ns:.2f} cycles per ns '
             f'({S.xref("setup-clock")}). '
             f'"F1 minus F2" is the F1 bracket time minus the F2 bracket time, the bold number of the figure. '
             f'On boot F2 every row counts {_n(f2_prf_max, 2)} prefetch refills per load.',
        align='lrrrrrrrr'))

    n = D.g1_notes
    out.append(S.p('What the table shows on ' + F2N + ':'))
    out.append(S.bullets([
        f'An OCM load takes {_n(n["ocm_minus_outside_lo"])} to {_n(n["ocm_minus_outside_hi"])} ns more than the '
        f'{short("outside-1m")} and {short("outside-3m")} rows.',
        f'An OCM load takes {_n(n["dram_minus_ocm"])} ns less than the DRAM model row with every line flushed first.',
        f'The {short("dram-32m")} row walked once ({_n(g2["dram-32m"]["bracket_lo"])} ns) is within '
        f'{_n(abs(g2["dram"]["bracket_lo"] - g2["dram-32m"]["bracket_lo"]))} ns of the DRAM model row '
        f'({_n(g2["dram"]["bracket_lo"])} ns). It counts {_n(g2["dram-32m"]["outer_lo"], 4)} outer refills per load. '
        f'No counter says how many of them the SLC serves ({S.xref("open-outside")}).',
    ]))
    hp = D.platform['hugepagesize']
    om = D.dmesg_ocm_maps['F2']
    readme = S.ref('readme-f1-memory-model',
                   "Operator's README of boot F1, <code>results/membench-jibin-011/README.md</code>, lines 243 to 253 "
                   '(the memory model behind the home node).')
    dmesg = S.ref('dmesg-F2-ocm', 'Boot F2, file <code>dmesg.txt</code> in <code>results/membench-jibin-012/</code>, '
                  'lines %d to %d: %d OCM mappings, each of one 4 KiB page.' % (om['first_line'], om['last_line'], om['n']))
    sysinfo = S.ref('sysinfo-F1-hugepage', 'Boot F1, file <code>sysinfo.txt</code> in <code>%s/</code>, line %d (<code>%s</code>).' % (
        _reldir(D, 'F1'), hp['line'], ' '.join(hp['text'].split())))
    outs = [g2['outside-1m'], g2['outside-3m']]
    out_src = sorted({r['src'] for r in outs})
    out_backing = sorted({r['backing'] for r in outs})
    out_flush = sorted({D.latblocks('F2', s)[0]['header']['flush'] for s in out_src})
    out.append(S.p('Limits of this comparison:'))
    out.append(S.bullets([
        ('The rows do not share one setup.', [
            f'The OCM row uses 4 KiB pages and a flush before the walk {dmesg}.',
            f'The outside-the-cluster rows of {short("outside-1m")} and {short("outside-3m")} carry '
            f'<code>backing={",".join(out_backing)}</code> and <code>flush={",".join(str(v) for v in out_flush)}</code> '
            f'in the file of boot F2 {" ".join(_fref(D, S, "F2", s) for s in out_src)}. '
            f'So they use huge pages and no flush.',
            f'The huge page size is {hp["value"] // 1024} MiB. It is read on boot F1, the one boot that wrote a system listing {sysinfo}.',
        ]),
        f'The outside-the-cluster rows count {_n(g2["outside-1m"]["outer_lo"], 4)} and {_n(g2["outside-3m"]["outer_lo"], 4)} '
        f'outer refills per load, not {_n(g2["ocm"]["outer_lo"], 4)}. The same rows count '
        f'{_n(g2["outside-1m"]["inner_lo"], 4)} and {_n(g2["outside-3m"]["inner_lo"], 4)} inner refills per load. '
        f'These counts are totals of a rep.',
        ('The round-trip baseline is a separate measurement.', [
            f'Every chain load returns its result to the core through the instruction LASTB {kc}.',
            'The round-trip kernel runs a register copy in place of the load, then the same LASTB.',
            'No row measures the time that the two kernels share.',
            'So a chain load minus the baseline is a difference between two kernels. '
            'No row gives the time of the memory access alone.',
        ]),
        f"The DRAM model has no configured delay (operator's README) {readme}. Its time is the delay of the emulated path, not the timing of a memory part.",
        f'The inside-the-cluster row counts {_n(g2["cluster"]["inner_lo"], 4)} inner refills per load. '
        f"An inner refill comes from the cluster L3 or from a snoop of a core's cache (operator's README) {S.ref('readme:F2:l3rtl')}. "
        f'The counters of this file do not separate the two.',
    ]))

    out.append(S.insufficient(
        f'The memory-access time of a chain load is unknown. '
        f'The rows give the chain load ({_rng(g2["l1"]["bracket_lo"], g2["l1"]["bracket_hi"], 3, "ns")} in the CME L1 rows of {F2N}) '
        f'and the separate round-trip baseline ({_n(rt)} ns). '
        f'A calibration of the non-memory time that the chain-load kernel and the round-trip kernel share would resolve it. '
        f'With it, the difference of {_rng(*d_l1, 3, "ns")} could be read as memory-access time.'))

    # =============================================================== 3.2  G20
    out.append(S.h3('glance-quote', 'Numbers to quote'))
    lim = D.limits
    wr = {b: _lohi(r['best'] for r in _single(D, b, 'write')) for b in BOOTS}
    wr_src = {b: ', '.join(sorted({r['src'] for r in _single(D, b, 'write')})) for b in BOOTS}
    wr_rows = _single(D, 'F2', 'write')
    wr_cond = f'{wr_rows[0]["label"]} to {wr_rows[-1]["label"]}'
    lsz = [data.fmt_size(s) for s in lim['F2']['sizes']]
    l1cond = f'{lsz[0]} to {lsz[-1]}, single-call form, bracket time'
    cl = {b: _sweep(D, b, 'read', 96 * KIB, 256 * KIB) for b in BOOTS}
    lg = {b: _sweep(D, b, 'read', 1 * MIB, 32 * MIB) for b in BOOTS}
    r32 = {b: D.bw_row(b, 'sweep', 'read', 32 * MIB) for b in BOOTS}
    cl_r = {b: _lohi(r['best'] for r in cl[b]) for b in BOOTS}
    lg_r = {b: _lohi(r['best'] for r in lg[b]) for b in BOOTS}
    ocm_lat = {r['name']: r for r in D.ocm_lat['F2']}
    near = [r for r in D.ocm_lat['F2'] if r['region'] is not None and q['ocm_near_f2_span'][0] <= r['best_span'] <= q['ocm_near_f2_span'][1]]
    far = [r for r in D.ocm_lat['F2'] if r['region'] is not None and q['ocm_far_f2_span'][0] <= r['best_span'] <= q['ocm_far_f2_span'][1]]
    near_l = 'regions ' + ', '.join(str(r['region']) for r in near)
    far_l = 'regions ' + ' and '.join(str(r['region']) for r in far)
    cluster_rows = [r for r in D.chain['F2'] if r['kind'] == 'walked many times'
                    and q['cluster_f2'][0] <= r['best'] <= q['cluster_f2'][1] and r['size'] > 64 * KIB]
    cl_cond = f'{cluster_rows[0]["label"]} to {cluster_rows[-1]["label"]}, walked many times'
    outside_rows = [r for r in D.chain['F2'] if r['kind'] == 'walked once'
                    and q['outside_f2'][0] <= r['best'] <= q['outside_f2'][1]]
    out_cond = f'{outside_rows[0]["label"]} to {outside_rows[-1]["label"]}, walked once'
    ocm_bw = {b: {r['name']: r for r in D.ocm_bw[b]} for b in BOOTS}

    # chain shape, loads per pass and number of passes of the one-region OCM rows (from the rows)
    reg = near + far
    reg_shape = sorted({r['shape'] for r in reg})
    reg_loads = sorted({r['loads'] for r in reg})
    reg_passes = sorted({r['n_reps'] for r in reg})
    reg_cond = (f'{" or ".join(reg_shape)} ({" or ".join(str(v) for v in reg_loads)} loads per pass, '
                f'{" or ".join(str(v) for v in reg_passes)} passes), every line flushed first')
    all5 = ocm_lat['all5-dense']
    all5_cond = f'{all5["shape"]} of the five regions ({V.num(all5["loads"], 0)} loads per pass), every line flushed first'

    f2_rows = D.chain['F2'] + D.ocm_lat['F2']
    f2_all_prf = max(r['hwprf_max'] for r in f2_rows)
    out.append(S.bullets([
        f'For latency, quote the {F2N} rows. Every rep of these rows counts {_n(f2_all_prf, 4)} prefetch refills per load. '
        f'So no prefetched line shortens a chain load.',
        f'For bandwidth, quote the single-call form inside the CME L1 and the looped form above it.',
        f'State the boot with every read rate above the CME L1. '
        f'At {cl["F2"][0]["label"]} the looped read is {_n(cl["F1"][0]["best"], 1)} GB/s on boot F1 and '
        f'{_n(cl["F2"][0]["best"], 1)} GB/s on boot F2. '
        f'At {r32["F2"]["label"]} it is {_n(r32["F1"]["best"], 1)} GB/s and {_n(r32["F2"]["best"], 1)} GB/s.',
    ]))

    # Figure: one range mark per quantity (dot at the lowest row, dot at the highest row)
    lat_marks = [
        ('CME L1', 'bracket time, ' + g2['l1']['conditions'], q['l1_f2']),
        ('Inside the cluster', 'bracket time, ' + cl_cond, q['cluster_f2']),
        ('Outside the cluster', 'bracket time, ' + out_cond, q['outside_f2']),
        ('OCM, ' + near_l, 'span time, ' + reg_cond, q['ocm_near_f2_span']),
        ('OCM, ' + far_l, 'span time, ' + reg_cond, q['ocm_far_f2_span']),
        ('OCM, all five regions', 'span time, ' + all5_cond, (q['ocm_all5_f2_span'], q['ocm_all5_f2_span'])),
        ('DRAM model', 'bracket time, ' + g2['dram']['conditions'], (q['dram_f2'], q['dram_f2'])),
    ]
    lat_rows = []
    for label, sub, (lo, hi) in lat_marks:
        one = hi - lo < 1e-9
        lat_rows.append(dict(
            label=label, sub=sub, a=lo, b=None if one else hi, gap='' if one else 'range %s ns' % _n(hi - lo),
            tip='%s, %s\n%s' % (label, sub, ('%s ns' % _n(lo)) if one else
                                'lowest row %s ns\nhighest row %s ns' % (_n(lo), _n(hi)))))
    svg = V.dumbbell(lat_rows, a_name='lowest row of the range, or the one row', b_name='highest row of the range',
                     a_color='f2', b_color='f2', unit='ns',
                     xlabel='chain load, ns (OCM rows: span time, other rows: bracket time)', fmt=lambda v: V.num(v, 3),
                     refs=[(rt, 'round-trip baseline %s ns' % _n(rt))], label_w=300,
                     xrange=(0, 10 * (int(q['dram_f2'] * 1.2 / 10) + 1)), title='range chart')
    lat_files = ['cme-latency-dram-small.csv', 'cme-latency-dram-large.csv', 'cme-latency-dram-flushed.csv',
                 'cme-latency-ocm-all5-dense.csv'] + [r['src'] for r in near + far]
    above = [lo for _, _, (lo, hi) in lat_marks[1:]]
    ocm_marks = [v for lab, _, lh in lat_marks if lab.startswith('OCM') for v in lh]
    out.append(S.fig(svg,
                     f'Latency numbers to quote, {F2N}. Each mark is the range of one quantity: a dot at its lowest row and a dot '
                     f'at its highest row. A single dot is one row. '
                     f'The OCM marks are the lowest span time of the passes. The other marks are the bracket time of the best row '
                     f'of each footprint. The grey line is the round-trip baseline, which is {_n(rt)} ns in all {q["rt_files"]} '
                     f'files of both boots. It is a separate measurement with no memory access, not a part of a chain load. '
                     f'Files: {", ".join(_code(f) for f in lat_files[:4])} and the five files '
                     f'<code>cme-latency-ocm-region0.csv</code> to <code>cme-latency-ocm-region4.csv</code> '
                     f'{" ".join(_fref(D, S, "F2", f) for f in lat_files)}.',
                     f'Every mark above the CME L1 is at least {_n(min(above) - q["l1_f2"][1], 1)} ns above the highest CME L1 row '
                     f'({_n(q["l1_f2"][1])} ns). The three OCM marks lie between {_n(min(ocm_marks))} ns and {_n(max(ocm_marks))} ns.'))

    l1_diff = max(abs(r['f2_over_f1'] - 1.0) * 100.0 for r in D.bw_f1_vs_f2 if r['group'] == 'l1-single')

    def pair(key_lo_hi):
        return [key_lo_hi['F2'][1], key_lo_hi['F1'][1]]

    def notes(key_lo_hi, d=1):
        return ['(lowest row %s GB/s)' % _n(key_lo_hi[b][0], d) if key_lo_hi[b][1] - key_lo_hi[b][0] > 1e-9 else '' for b in BOOTS]

    rd1 = {b: q['l1_read_single_' + b] for b in BOOTS}
    ocr = {b: q['ocm_read_' + b] for b in BOOTS}
    ocw = {b: (q['ocm_write_' + b], q['ocm_write_' + b]) for b in BOOTS}
    r32p = {b: (r32[b]['best'], r32[b]['best']) for b in BOOTS}
    ow = {b: ocm_bw[b]['write'] for b in BOOTS}
    ow_passes = sorted({ow[b]['passes'] for b in BOOTS})
    ow_calls = sorted({ow[b]['calls_per_rep'] for b in BOOTS})
    ow_cond = (f'{" or ".join(str(v) for v in ow_passes)} passes per rep '
               f'({" or ".join(str(v) for v in ow_calls)} kernel calls), flush before each rep')
    r32_ratio = r32['F1']['best'] / r32['F2']['best']
    r32_notes = ['', '(x %s of boot F2)' % _n(r32_ratio, 1)]

    def bw(label, sub, lohi, nts=None):
        nts = nts or notes(lohi)
        tips = ['%s, %s - %s\n%s GB/s%s' % (label, sub, BN[b], _n(lohi[b][1], 1), ('\n' + nts[i]) if nts[i] else '')
                for i, b in enumerate(BOOTS)]
        return dict(label=label, sub=sub, values=pair(lohi), notes=nts, tips=tips)

    bw_rows = [
        dict(header='Single-call form'),
        bw('Read', f'{lsz[0]} to {lsz[-1]}, inside the CME L1', rd1),
        bw('Write', wr_cond, wr),
        dict(header='Looped form, above the CME L1'),
        bw('Read', f'{cl["F2"][0]["label"]} to {cl["F2"][-1]["label"]}', cl_r),
        bw('Read', r32['F2']['label'], r32p, r32_notes),
        dict(header='OCM'),
        bw('Read, one region', 'one pass over 256 KiB, every line flushed first, five files', ocr),
        bw('Write, all five regions', ow_cond, ocw),
    ]
    svg = V.hbar(bw_rows, series=[(F2N, 'f2'), (F1N, 'f1')], unit='GB/s', fmt=lambda v: V.num(v, 1),
                 xlabel='rate, bracket time, GB/s', label_w=270)
    bw_files = ['cme-bandwidth-l1-asmpasses.csv', 'cme-bandwidth-dram-1core-asmpasses.csv', 'cme-bandwidth-dram-1core.csv',
                'cme-bandwidth-ocm-write.csv']
    out.append(S.fig(svg,
                     f'Bandwidth numbers to quote, both boots, bracket time. A bar shows the highest row of its range. '
                     f'The text after the bar gives the lowest row. Each row is the best row of one footprint or region. '
                     f'The text after the orange {r32["F2"]["label"]} bar gives boot F1 as a multiple of boot F2. '
                     f'Files, same names on both boots: {", ".join(_code(f) for f in bw_files)} and the five files '
                     f'<code>cme-bandwidth-ocm-region0.csv</code> to <code>cme-bandwidth-ocm-region4.csv</code> '
                     f'{" ".join(_fref(D, S, b, f) for b in BOOTS for f in bw_files + [ocm_bw[b]["region%d" % i]["src"] for i in range(5)])}.',
                     f'Inside the CME L1 the single-call rates of the two boots differ by at most {_n(l1_diff, 1)} %. '
                     f'At {r32["F2"]["label"]} the read rate is {_n(r32["F1"]["best"], 1)} GB/s with the '
                     f'prefetchers on and {_n(r32["F2"]["best"], 1)} GB/s with them off.'))

    def qrow(what, val, boot, cond, src_boot, src):
        return [what, val, boot, cond, _code(src) + ' ' + _fref(D, S, src_boot, src)]

    qt = [
        'Latency, ns per chain load',
        ['Round-trip baseline', _n(q['rt_ns']), 'F1 and F2',
         f'best row of each of the {q["rt_files"]} CME latency files, bracket time. '
         f'A separate measurement with no memory access. It is not a measured part of a chain load.',
         f'all CME latency files, for example <code>cme-latency-dram-small.csv</code> {_fref(D, S, "F2", "cme-latency-dram-small.csv")}'],
        qrow('CME L1', _rng(*q['l1_f2']), 'F2', g2['l1']['conditions'] + ', bracket time', 'F2', g2['l1']['src']),
        qrow('Inside the cluster', _rng(*q['cluster_f2']), 'F2', cl_cond + ', bracket time', 'F2', cluster_rows[0]['src']),
        qrow('Outside the cluster', _rng(*q['outside_f2']), 'F2', out_cond + ', bracket time', 'F2', outside_rows[0]['src']),
        ['OCM, ' + near_l, _rng(*q['ocm_near_f2_span']), 'F2', f'one region, {reg_cond}, lowest span time of the passes',
         f'<code>cme-latency-ocm-region0.csv</code> to <code>-region4.csv</code> {" ".join(_fref(D, S, "F2", r["src"]) for r in near)}'],
        ['OCM, ' + far_l, _rng(*q['ocm_far_f2_span']), 'F2', f'one region, {reg_cond}, lowest span time of the passes',
         f'same five files {" ".join(_fref(D, S, "F2", r["src"]) for r in far)}'],
        qrow('OCM, all five regions', _n(q['ocm_all5_f2_span']), 'F2', f'{all5_cond}, span time',
             'F2', all5['src']),
        qrow('DRAM model', _n(q['dram_f2']), 'F2', g2['dram']['conditions'] + ', bracket time. An emulator memory model, not silicon.',
             'F2', g2['dram']['src']),
        'Bandwidth, GB/s',
    ]
    for b in BOOTS:
        qt.append(qrow('Read inside the CME L1', _rng(*rd1[b], 1), b, l1cond, b, lim[b]['src']))
    for b in BOOTS:
        qt.append(qrow('Write, single-call form', _rng(*wr[b], 1), b, f'{wr_cond}, bracket time', b, wr_src[b]))
    for b in BOOTS:
        qt.append(qrow('Read above the CME L1', _rng(*cl_r[b], 1), b,
                       f'{cl[b][0]["label"]} to {cl[b][-1]["label"]}, looped form, bracket time', b, cl[b][0]['src']))
    qt.append(qrow('Read at large footprints', _rng(*lg_r['F1'], 1), 'F1',
                   f'{lg["F1"][0]["label"]} to {lg["F1"][-1]["label"]}, looped form, bracket time', 'F1', lg['F1'][0]['src']))
    qt.append(qrow('Read at ' + r32['F2']['label'], _n(r32['F2']['best'], 1), 'F2', 'looped form, bracket time', 'F2', r32['F2']['src']))
    for b in BOOTS:
        qt.append([f'OCM read, one region', _rng(*ocr[b], 1), b, 'one pass over 256 KiB, every line flushed first, bracket time',
                   f'<code>cme-bandwidth-ocm-region0.csv</code> to <code>-region4.csv</code> '
                   f'{_fref(D, S, b, ocm_bw[b]["region0"]["src"])}'])
    for b in BOOTS:
        qt.append(qrow('OCM write, all five regions', _n(ocw[b][0], 1), b,
                       f'{ow[b]["passes"]} passes per rep ({ow[b]["calls_per_rep"]} kernel calls), flush before each rep, '
                       f'bracket time', b, ow[b]['src']))
    out.append(S.table(['Quantity', 'Value', 'Boot', 'Conditions', 'File'], qt,
                       caption='The numbers to quote, each with its boot, its conditions and its file.',
                       note=f'F2 is {F2N}. F1 is {F1N}. A range covers the best rows of the named footprints or regions. '
                            f'Every latency value is the time of the whole chain load. '
                            f'A chain load minus the round-trip baseline is the difference between two kernels, '
                            f'not the time of the memory access ({S.xref("glance-where")}). '
                            f'Write rows carry no destination level. No counter of these files says where a stored line goes.',
                       align='lrlll'))

    # =============================================================== 3.3  G2
    out.append(S.h3('glance-limits', 'Measured rates against the documented limits'))
    doc = lim['doc']
    vec = data.LINE
    doc_max = doc['loads_or_stores_per_cycle_max']
    llvm_bpc = VECTORS_PER_LOAD * vec / LLVM_LD4_CYCLES      # B/cycle of the LLVM model for this kernel (est.)
    sog = S.ref('sog-109590', 'Arm C1-Nano Core Software Optimization Guide, document 109590_0001_04, section 2.33.3: '
                'load and store instructions have a bandwidth of two per cycle '
                '(<code>refs/arm-c1-nano-r0p1-sog-109590_0001_04.pdf</code>).')
    td = S.ref('llvm-c1nano-td', 'LLVM scheduling model of the C1-Nano, <code>refs/AArch64SchedC1Nano.td</code>. Lines 84 to 86: '
               'one CME load pipe, one CME store pipe. Line 361 and lines 2885 to 2890: a load of 4 vectors holds the CME load '
               'pipe for 2 cycles.')
    ks = S.ref('cme-kern-read4', 'Source file <code>cme_kern.S</code>, lines 148 to 221: the read loop '
               '(4 load instructions of 4 vectors each, 16 EOR instructions, 3 loop instructions per 1 KiB).')

    def ipc(b):
        """Load instructions per cycle of the single-call read: (lowest, highest) over the footprints."""
        return (READ_LOADS_PER_ITER / lim[b]['read_cycles_per_kib_hi'], READ_LOADS_PER_ITER / lim[b]['read_cycles_per_kib_lo'])

    out.append(S.bullets([
        f'The single-call read transfers {_rng(lim["F2"]["read_bpc_lo"], lim["F2"]["read_bpc_hi"], 1)} B/cycle on {F2N}. '
        f'That is an effective rate of {_rng(lim["F2"]["read_vec_per_cycle_lo"], lim["F2"]["read_vec_per_cycle_hi"], 2)} '
        f'vectors of {vec} B per cycle.',
        f'One load instruction of the read kernel loads {VECTORS_PER_LOAD} vectors {ks}. '
        f'So the effective rate is {_rng(*ipc("F2"), 2)} load instructions per cycle on {F2N}. '
        f'The documented limit is {doc_max} load or store instructions per cycle {sog}.',
        f'The single-call write transfers {_rng(lim["F2"]["write_bpc_lo"], lim["F2"]["write_bpc_hi"], 1)} B/cycle on {F2N}. '
        f'That is an effective {_rng(lim["F2"]["write_cycles_per_vec_lo"], lim["F2"]["write_cycles_per_vec_hi"], 2)} cycles '
        f'per {vec} B transferred.',
        ('Every measured number of this subsection is a throughput.', [
            'It divides the bracket time of a whole rep by the bytes that the rep transfers.',
            f'One iteration of the read loop runs {READ_LOADS_PER_ITER} load instructions of {VECTORS_PER_LOAD} vectors each '
            f'and {READ_EORS_PER_ITER} EOR instructions (bitwise exclusive-or) {ks}.',
            f'One iteration of the write loop runs {WRITE_STORES_PER_ITER} store instructions of {VECTORS_PER_LOAD} vectors each {ks}.',
            'So no measured number of this subsection is the time that one load or one store takes to complete.',
        ]),
    ]))

    # Figure: one row per footprint, boot F2 against boot F1
    per = {}
    for kernel, klo, khi in (('read', 'read_bpc_lo', 'read_bpc_hi'), ('write', 'write_bpc_lo', 'write_bpc_hi')):
        for b in BOOTS:
            rr = [r for r in _single(D, b, kernel) if r['size'] in lim[b]['sizes']]
            per[(kernel, b)] = rr
            got = _lohi(r['bytes_per_cycle'] for r in rr)
            if abs(got[0] - lim[b][klo]) > 1e-9 or abs(got[1] - lim[b][khi]) > 1e-9:
                raise ValueError('glance: the footprint rows of %s %s do not give the range of D.limits' % (kernel, b))
    lrows = []
    for kernel in ('read', 'write'):
        lrows.append(dict(header=f'{kernel.capitalize()}, single-call form'))
        for ra, rb in zip(per[(kernel, 'F2')], per[(kernel, 'F1')]):
            a, b_ = ra['bytes_per_cycle'], rb['bytes_per_cycle']
            lab = f'{kernel.capitalize()}, {ra["label"]}'
            lrows.append(dict(label=lab, a=a, b=b_,
                              tip='%s, single-call form\n%s: %s B/cycle (effective %s vectors per cycle)\n%s: %s B/cycle (effective %s vectors per cycle)' % (
                                  lab, F2N, _n(a, 1), _n(a / vec, 2), F1N, _n(b_, 1), _n(b_ / vec, 2))))
    svg = V.dumbbell(lrows, a_name=F2N, b_name=F1N, a_color='f2', b_color='f1', unit='B/cycle',
                     xlabel='bytes per core cycle (B/cycle)', fmt=lambda v: V.num(v, 1), label_w=200,
                     gap_fmt=lambda a, b: V.signed(b - a, 1, 'B/cycle'),
                     refs=[(vec, 'one %d B vector per cycle' % vec),
                           (llvm_bpc, 'est.: %d vectors per cycle (LLVM model)' % (llvm_bpc // vec))])
    core = _lohi(v for b in BOOTS for v in (D.clock[b]['core_lo'], D.clock[b]['core_hi']))
    out.append(S.fig(svg,
                     f'Bytes transferred per core cycle by the single-call form at the {len(lsz)} footprints inside the CME L1 '
                     f'({", ".join(lsz)}), both boots. Each row is the best row of one footprint, bracket rate, '
                     f'divided by {_n(cpn, 2)} cycles per ns. The measured ratio is {_n(core[0], 4)} to {_n(core[1], 4)} cycles per ns. '
                     f'The bold number is boot F1 minus boot F2. Files: {_code(lim["F2"]["src"])} '
                     f'{_fref(D, S, "F2", lim["F2"]["src"])} {_fref(D, S, "F1", lim["F1"]["src"])}. '
                     f'The grey line at {vec} B/cycle is a unit mark for one vector per cycle. '
                     f'The grey line at {_n(llvm_bpc, 0)} B/cycle is an estimate from the LLVM model {td}. '
                     f'Neither line is a measurement. '
                     f'A dot is a throughput of the whole loop, not the time of one load or one store.',
                     f'The read dots lie at an effective {_rng(min(lim[b]["read_vec_per_cycle_lo"] for b in BOOTS), max(lim[b]["read_vec_per_cycle_hi"] for b in BOOTS), 2)} '
                     f'vectors per cycle. The write dots lie at an effective '
                     f'{_rng(min(lim[b]["write_bpc_lo"] for b in BOOTS) / vec, max(lim[b]["write_bpc_hi"] for b in BOOTS) / vec, 2)} '
                     f'vectors per cycle.'))

    def lcol(lo, hi, d):
        return [_rng(lim[b][lo], lim[b][hi], d) for b in BOOTS]

    out.append(S.table(
        ['Quantity', 'Boot F2 (prefetchers off)', 'Boot F1 (prefetchers on)'],
        ['Read',
         ['Rate, GB/s'] + lcol('read_gbps_lo', 'read_gbps_hi', 1),
         ['B/cycle'] + lcol('read_bpc_lo', 'read_bpc_hi', 2),
         [f'Effective vectors of {vec} B per cycle'] + lcol('read_vec_per_cycle_lo', 'read_vec_per_cycle_hi', 2),
         ['Effective cycles per 1 KiB transferred'] + lcol('read_cycles_per_kib_lo', 'read_cycles_per_kib_hi', 1),
         [f'Effective load instructions per cycle ({VECTORS_PER_LOAD} vectors each)'] + [_rng(*ipc(b), 2) for b in BOOTS],
         'Write',
         ['Rate, GB/s'] + lcol('write_gbps_lo', 'write_gbps_hi', 1),
         ['B/cycle'] + lcol('write_bpc_lo', 'write_bpc_hi', 2),
         [f'Effective cycles per {vec} B transferred'] + lcol('write_cycles_per_vec_lo', 'write_cycles_per_vec_hi', 2)],
        caption=f'Single-call form, {lsz[0]} to {lsz[-1]}, bracket time: the measured rates in the units of the documented limits.',
        note=f'A range covers the {len(lsz)} footprints. One iteration of the read loop reads 1 KiB with '
             f'{doc["read_loop_instructions"]} instructions, {READ_LOADS_PER_ITER} of them load instructions {ks}. '
             f'Cycles are core cycles at {_n(cpn, 2)} cycles per ns. '
             f'An effective value is the bracket time of a whole rep divided by what the rep transfers. '
             f'It is not the time that one load or one store takes to complete.',
        align='lrr'))
    out.append(S.p('The documented limits:'))
    out.append(S.bullets([
        f'The core issues at most {doc_max} load or store instructions per cycle to the CME '
        f'(Arm Software Optimization Guide) {sog}. The guide gives no limit in vectors or in bytes.',
        f'The LLVM model of the core has {doc["cme_load_pipes"]} CME load pipe and {doc["cme_store_pipes"]} CME store pipe {td}.',
        f'The LLVM model holds the CME load pipe for {LLVM_LD4_CYCLES} cycles for one load of {VECTORS_PER_LOAD} vectors {td}. '
        f'That is {_n(llvm_bpc / vec, 0)} vectors per cycle, or {_n(llvm_bpc, 0)} B/cycle (est.).',
    ]))
    rd_pct = _lohi(lim[b][k] / llvm_bpc * 100.0 for b in BOOTS for k in ('read_bpc_lo', 'read_bpc_hi'))
    out.append(S.hyp(
        f'The load path of the CME limits the read rate. The EOR work does not. '
        f'The measured read rate is {_n(rd_pct[0], 0)} to {_n(rd_pct[1], 0)} % of the {_n(llvm_bpc, 0)} B/cycle of the LLVM model (est.). '
        f'The read kernel also runs one EOR instruction for every loaded vector. '
        f'So these rows cannot separate the load path from the EOR work.',
        'A read kernel with no EOR instruction in its loop, run at the same footprints. '
        'A rate that stays at the measured value confirms it. A higher rate rejects it.'))
    wcv = _lohi(lim[b][k] for b in BOOTS for k in ('write_cycles_per_vec_lo', 'write_cycles_per_vec_hi'))
    out.append(S.insufficient(
        f'No row explains why the single-call write transfers {vec} B in an effective {_rng(*wcv, 2)} cycles. '
        'A write kernel under a counter of the CME store pipe, or a waveform of one write pass, would show where the cycles go.'))

    # =============================================================== 3.4  G8
    out.append(S.h3('glance-repeat', 'Repeatability'))

    def pct(lo, hi):
        return (hi - lo) / lo * 100.0

    rt_sp = {b: pct(rp[b]['rt_lo'], rp[b]['rt_hi']) for b in BOOTS}
    call_sp = {b: pct(rp[b]['call_lo'], rp[b]['call_hi']) for b in BOOTS}
    l3 = D.l3_repeat
    l3rows = D.chain_l3['F2']
    fp_lo, fp_hi = l3rows[0]['label'], l3rows[-1]['label']
    lrep = {b: _looped_repeats(D, b) for b in BOOTS}
    if [(r['kernel'], r['size']) for r in lrep['F2']] != [(r['kernel'], r['size']) for r in lrep['F1']]:
        raise ValueError('glance: the two boots do not hold the same repeated looped rows')
    # the same repeats as the data layer's own table, where it has them
    for b in BOOTS:
        for r in lrep[b]:
            if (r['kernel'], r['size']) == ('read', 16 * KIB) and abs(r['bracket_pct'] - rp[b]['read16_diff_pct']) > 1e-6:
                raise ValueError('glance: 16 KiB read repeat differs from D.repeatability')
            if (r['kernel'], r['size']) == ('write', 4 * KIB) and abs(r['span_pct'] - rp[b]['write4_span_diff_pct']) > 1e-6:
                raise ValueError('glance: 4 KiB write repeat differs from D.repeatability')

    # every bandwidth repeat as (percent, name, boot), to name the largest ones from the data
    bw_diffs = []
    for b in BOOTS:
        for r in lrep[b]:
            for clock in ('bracket', 'span'):
                bw_diffs.append((r[clock + '_pct'], f'the looped {r["kernel"]} at {r["label"]}, {clock} rate', b))
    bw_diffs.sort(reverse=True)
    lat_diffs = sorted([(rt_sp[b], 'the round-trip baseline', b) for b in BOOTS] +
                       [(call_sp[b], 'the cme-call row', b) for b in BOOTS] +
                       [(rp[b]['sweeps_worst_pct'], 'the chain load at %s' % rp[b]['sweeps_worst_label'], b) for b in BOOTS],
                       reverse=True)
    all_diffs = sorted(bw_diffs + lat_diffs, reverse=True)
    top, second = all_diffs[0], all_diffs[1]

    out.append(S.bullets([
        (f'The round-trip baseline reads {_n(rp["all"]["rt_lo"])} ns in all {rp["all"]["rt_files"]} files. '
         if rp['all']['rt_hi'] - rp['all']['rt_lo'] < 5e-4 else
         f'The round-trip baseline reads {_rng(rp["all"]["rt_lo"], rp["all"]["rt_hi"], 3, "ns")} in the {rp["all"]["rt_files"]} files. ') +
        'The files print it to 0.001 ns.',
        f'The largest difference between two files that hold the same row is '
        f'{_n(top[0], 1)} % ({top[1]}, boot {top[2]}).',
    ]))

    nfiles = rp['F2']['rt_files']
    lat_sub = f'{nfiles} files per boot, highest against lowest'

    def rep_bar(label, sub, vals):
        return dict(label=label, sub=sub, values=vals,
                    tips=['%s, %s - %s\n%s %%' % (label, sub, BN[b], _n(v, 2)) for b, v in zip(BOOTS, vals)])

    drows = [
        dict(header='Latency'),
        rep_bar('Round-trip baseline', lat_sub, [rt_sp[b] for b in BOOTS]),
        rep_bar('cme-call row', lat_sub, [call_sp[b] for b in BOOTS]),
        rep_bar('Chain load, plain row against L3-event row', f'largest difference over {rp["F2"]["sweeps_n"]} footprints',
                [rp[b]['sweeps_worst_pct'] for b in BOOTS]),
        dict(header='Bandwidth, looped form, one row in two files'),
    ]
    for i, r in enumerate(lrep['F2']):
        for clock in ('bracket', 'span'):
            drows.append(rep_bar(f'{r["kernel"].capitalize()} at {r["label"]}, {clock} rate',
                                 f'{r["a"]["src"]} against {r["b"]["src"]}',
                                 [lrep[b][i][clock + '_pct'] for b in BOOTS]))
    svg = V.hbar(drows, series=[(F2N, 'f2'), (F1N, 'f1')], unit='%', fmt=lambda v: V.num(v, 2),
                 xlabel='difference between two measurements of one row, %', label_w=300)
    rep_files = ['cme-latency-dram-small.csv', 'cme-latency-dram-large.csv', 'cme-latency-dram-small-l3.csv',
                 'cme-latency-dram-large-l3.csv', 'cme-bandwidth-dram-1core.csv', 'cme-bandwidth-l1-passes.csv',
                 'cme-bandwidth-call-cost.csv']
    out.append(S.fig(svg,
                     f'Repeat difference inside one boot. Each row is one measurement that one boot holds two times or more. '
                     f'The value is the difference in percent of the lower value. '
                     f'For the chain load it is in percent of the plain row. '
                     f'The bandwidth rows are all the looped rows that two files of one boot hold. '
                     f'Files, same names on both boots: the {nfiles} CME latency files (baseline and cme-call row), '
                     f'{", ".join(_code(f) for f in rep_files)} '
                     f'{" ".join(_fref(D, S, b, f) for b in BOOTS for f in rep_files)}.',
                     f'The largest difference is {_n(top[0], 1)} % ({top[1]}, boot {top[2]}). '
                     f'The next largest is {_n(second[0], 1)} % ({second[1]}, boot {second[2]}). '
                     f'The largest latency difference is {_n(lat_diffs[0][0], 1)} % ({lat_diffs[0][1]}, boot {lat_diffs[0][2]}).'))

    nw = lambda t: '<span style="white-space:nowrap">%s</span>' % t
    trows = [
        'Latency',
        [nw('Round-trip baseline'), f'best row of each of {nfiles} files',
         _rng(rp['F2']['rt_lo'], rp['F2']['rt_hi'], 3, 'ns'), _n(rt_sp['F2'], 2),
         _rng(rp['F1']['rt_lo'], rp['F1']['rt_hi'], 3, 'ns'), _n(rt_sp['F1'], 2)],
        [nw('cme-call row'), f'best row of each of {nfiles} files, ns per call',
         _rng(rp['F2']['call_lo'], rp['F2']['call_hi'], 3, 'ns'), _n(call_sp['F2'], 2),
         _rng(rp['F1']['call_lo'], rp['F1']['call_hi'], 3, 'ns'), _n(call_sp['F1'], 2)],
        [nw('Chain load'), 'footprints where the L3-event row is within 1.0 % of the plain row',
         f'{rp["F2"]["sweeps_within_1pct"]} of {rp["F2"]["sweeps_n"]}', '',
         f'{rp["F1"]["sweeps_within_1pct"]} of {rp["F1"]["sweeps_n"]}', ''],
        [nw('Chain load'), 'largest difference: the footprint, its L3-event row and its plain row',
         f'{rp["F2"]["sweeps_worst_label"]}: {_n(l3["F2"]["worst_l3"])} and {_n(l3["F2"]["worst_plain"])} ns',
         _n(rp['F2']['sweeps_worst_pct'], 2),
         f'{rp["F1"]["sweeps_worst_label"]}: {_n(l3["F1"]["worst_l3"])} and {_n(l3["F1"]["worst_plain"])} ns',
         _n(rp['F1']['sweeps_worst_pct'], 2)],
        'Bandwidth, looped form',
    ]
    ftag = {}                      # file name -> letter, in the order of first use
    for r in lrep['F2']:
        for k in ('a', 'b'):
            ftag.setdefault(r[k]['src'], 'ABCDEFGH'[len(ftag)])
    for i, r in enumerate(lrep['F2']):
        for clock, key in (('bracket', 'best'), ('span', 'best_span')):
            row = [nw(f'Looped {r["kernel"]} at {r["label"]}'),
                   f'{clock} rate, file {ftag[r["a"]["src"]]} and file {ftag[r["b"]["src"]]}']
            for b in BOOTS:
                x = lrep[b][i]
                row += [f'{_n(x["a"][key], 2)} and {_n(x["b"][key], 2)} GB/s', _n(x[clock + '_pct'], 2)]
            trows.append(row)
    out.append(S.table(
        ['Repeat', 'What is compared', 'Boot F2 (prefetchers off)', 'F2 difference, %', 'Boot F1 (prefetchers on)', 'F1 difference, %'],
        trows,
        caption='The repeats that the two boots hold, with their exact values.',
        note='A difference is in percent of the lower value. For the chain load it is in percent of the plain row. '
             + ' '.join('File %s is %s.' % (t, _code(f)) for f, t in ftag.items())
             + ' The first value of a bandwidth cell is from the file named first. '
             'The plain rows are in <code>cme-latency-dram-small.csv</code> and <code>cme-latency-dram-large.csv</code>. '
             'The L3-event rows are in <code>cme-latency-dram-small-l3.csv</code> and <code>cme-latency-dram-large-l3.csv</code>. '
             'They time the same footprints with other counters. '
             f'{S.xref("l3-repeat", cap=True)} gives every footprint of this repeat and the rep values of the boot F1 footprints '
             f'outside 1.0 %.',
        align='llrrrr'))

    bw_br = _lohi(v for v, name, b in bw_diffs if 'bracket rate' in name)
    bw_sp = _lohi(v for v, name, b in bw_diffs if 'span rate' in name)
    out1 = [r['label'] for r in l3['F1']['outside_1pct']]
    out.append(S.p('How to read a difference on this page:'))
    out.append(S.bullets([
        f'On {F2N} the plain row and the L3-event row of each latency footprint agree within '
        f'{_n(rp["F2"]["sweeps_worst_pct"], 2)} % at all {rp["F2"]["sweeps_n"]} footprints ({fp_lo} to {fp_hi}). '
        f'A difference below 1 % between two such rows is not larger than the largest repeat difference of these rows.',
        f'On {F1N}, {rp["F1"]["sweeps_n"] - rp["F1"]["sweeps_within_1pct"]} of {rp["F1"]["sweeps_n"]} footprints differ by more than 1.0 % '
        f'({_and(out1)}).',
        f'A looped rate inside the CME L1 differs by {_n(bw_br[0], 2)} to {_n(bw_br[1], 2)} % (bracket rate) and by '
        f'{_n(bw_sp[0], 2)} to {_n(bw_sp[1], 2)} % (span rate) between two files of one boot. '
        f'A difference below {_n(bw_diffs[0][0], 1)} % between two looped rates inside the CME L1 is not larger than the largest repeat difference of these rows.',
    ]))
    out.append(S.hyp(
        f'The prefetcher makes the reps of {F1N} differ more at {_and(out1)}.',
        f'More reps of these footprints with the prefetch refill counter beside the time. The L3-event rows do not '
        f'carry that counter. {S.xref("l3-repeat", cap=True)} holds the rep values and the inner plus outer '
        f'refills of each rep. '
        f'A count that follows the time confirms it. A count that does not follow the time rejects it.'))
    out.append(S.insufficient(
        ('The boot-to-boot spread is unknown. No boot was repeated. ' if no_boot_repeated else
         f'The boot-to-boot spread is known from {rp["all"]["boots_repeated"]} repeated boots only. ') +
        f'A second boot with the settings of boot F1, and one with the settings of boot F2, would give it. '
        f'Until then, no row separates the effect of the prefetchers from the boot-to-boot spread and from the other '
        f'differences between the two boots ({S.xref("open-boots")}).'))

    # =============================================================== 3.5  not to quote
    out.append(S.h3('glance-noquote', 'Numbers not to quote'))
    lw = {b: D.l1_fit(b, 'looped', 'write', 'bracket') for b in BOOTS}
    sr = {b: D.l1_fit(b, 'single-call', 'read', 'bracket') for b in BOOTS}
    lr = {b: D.l1_fit(b, 'looped', 'read', 'bracket') for b in BOOTS}
    plan = S.ref('plan-fit-rule', 'Run plan <code>follow-up-run-plan.md</code>, line 271: a residual over 2 % of the smallest pass time voids the intercept.')
    l3rule = S.ref('l3-events-rule', 'Source file <code>common.h</code>, lines 439 to 446, and <code>follow-up-run-plan.md</code>, line 267: '
                   'no fit reads the L3 hit and miss columns until a control row validates them.')

    def verdicts(fits, what):
        vs = {b: fits[b]['verdict'] for b in BOOTS}
        if len(set(vs.values())) == 1:
            return f'The {what} is {vs["F2"]} on both boots.'
        return f'The {what} is {vs["F2"]} on boot F2 and {vs["F1"]} on boot F1.'

    lr_good = [b for b in BOOTS if lr[b]['verdict'] == 'pass']
    lr_void = [b for b in BOOTS if lr[b]['verdict'] != 'pass']
    lr_name = ('"A CME call costs %s ns" with no conditions' % _n(lr[lr_good[0]]['intercept_ns'], 0)) if lr_good else \
        'A cost of a CME call from the fit of the looped read'
    lr_why = ''
    for b in lr_good:
        lr_why += (f'{_fitval(lr[b], "intercept_ns", 1)} ns est. is the fitted intercept of one form on boot {b}. '
                   f'The form is the looped read, bracket time, {data.fmt_size(D.l1_sizes[0])} to {data.fmt_size(D.l1_sizes[-1])}. '
                   f'Its largest residual is {_n(lr[b]["max_res_pct"], 2)} %. The fit passes the plan rule. ')
    for b in lr_void:
        lr_why += (f'The same fit on boot {b} has a largest residual of {_n(lr[b]["max_res_pct"], 2)} %. '
                   f'Its intercept is {_fitval(lr[b], "intercept_ns", 1)}. ')
    lr_why += (f'A cme-call row measures {_rng(rp["all"]["call_lo"], rp["all"]["call_hi"], 1, "ns")} per call '
               f'when each call directly follows the one before it.')
    nq = [['The fitted cost of a load that the cluster L3 serves (est.)',
          f'The fit reads the L3 hit and miss events. No control row validates these events {l3rule}. '
          f'The value appears only inside a Hypothesis block of {S.xref("l3-fit")}.',
          f'The inside-the-cluster rows: {_rng(*q["cluster_f2"], 3, "ns")} on boot F2, {cl_cond}.'],
         ['The fitted intercept of the looped write (a cost per kernel call)',
          f'The largest residual is {_n(lw["F2"]["max_res_pct"], 2)} % (boot F2) and {_n(lw["F1"]["max_res_pct"], 2)} % (boot F1) '
          f'of the smallest pass time. The plan rule allows 2 % {plan}. {verdicts(lw, "intercept")}',
          'The measured time of one write call at each footprint (the call-cost rows of %s).' % S.xref('callcost-rows')],
         ['The fitted rate of the single-call read',
          f'The largest residual is {_n(sr["F2"]["max_res_pct"], 2)} % (boot F2) and {_n(sr["F1"]["max_res_pct"], 2)} % (boot F1) '
          f'of the smallest pass time. {verdicts(sr, "fit")}',
          f'The measured rows: {_rng(*rd1["F2"], 1, "GB/s")} (boot F2) and {_rng(*rd1["F1"], 1, "GB/s")} (boot F1), {lsz[0]} to {lsz[-1]}.'],
         [lr_name, lr_why,
          'The number together with its form, its clock (bracket or span), its footprints and its boot.'],
         ['Any DRAM model time as the timing of silicon memory',
          f"The DRAM model is a memory model of the emulator with no configured delay (operator's README) {readme}.",
          f'{_n(q["dram_f2"])} ns "on the emulator memory model".'],
         ['Any write rate as a rate "to the L3", "to the SLC" or "to DRAM"',
          'No counter of the write rows says which level receives the stored lines.',
          'The write rate with its footprint and its form only.']]
    out.append(S.bullets([
        f'The table lists {len(nq)} numbers or statements that must not be quoted as results.',
        'Each one fails a stated rule or lacks its conditions.',
    ]))
    out.append(S.table(
        ['Number or statement', 'Why it is not a result', 'What to quote in its place'], nq,
        caption='Numbers and statements that must not be quoted as results, with the reason and the replacement.',
        note=f'Fit residuals: files {_code(lw["F2"]["src"])} and {_code(sr["F2"]["src"])} of both boots '
             f'{_fref(D, S, "F2", lw["F2"]["src"])} {_fref(D, S, "F1", lw["F1"]["src"])} '
             f'{_fref(D, S, "F2", sr["F2"]["src"])} {_fref(D, S, "F1", sr["F1"]["src"])}. '
             f'{S.xref("callcost-quote", cap=True)} gives the details of the three fit rows. '
             f'{S.xref("open-claims", cap=True)} gives the details of the DRAM model row and of the write row.',
        align='lll'))

    return ''.join(out)
