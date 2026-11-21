"""Section 'callcost': the cost of one kernel call.

build(D, V, S) returns the html of the section body.  Every measured number is read
from the data layer D.  The values computed here (not in D) are listed in OWN."""

KEY = 'callcost'
TITLE = 'The cost of one kernel call'

# Values this module derives itself (reported to the page owner).
OWN = [
    'whole single-call passes that fit in one looped call = floor(looped bracket / single-call span per pass)',
    'single-call outside-span time per pass = bracket per pass - span per pass',
    'cme-call span - per-step span of the round-trip baseline row (a difference of two rows, not a part of the span)',
    'looped write span rate / single-call write rate, per size',
    'growth of the write call span from 4 KiB to 8 KiB, and the apparent rate of the added bytes',
    'ranges (lowest, highest) over D.l1_diffs, D.looped_vs_single and D.call_cost rows',
    'in-span split of the 4 KiB looped read: grey part = intercept of the span fit, loop = span - intercept (est.)',
    'clock-read share of the lone-call excess = empty-bracket time x 63/64 (est.), and the excess without it',
    'per counting window, medians over rep rows: the four totals as durations (core cycle count / cycles per ns, '
    'bracket time, CME cycle count / cycles per ns, span time) and their per-pass differences',
    'number of passes whose four totals have the order core count >= bracket >= CME count >= span',
    'lowest outside-span time over the six kinds of lone call',
    'per-rep spans of the looped write rows whose best rep differs from the other reps',
    'growth of a looped write pass in ns per KiB between neighbouring footprints',
]

FORMS = [  # (form key of D, kernel, panel title)
    ('looped', 'read', 'Looped form, read'),
    ('looped', 'write', 'Looped form, write'),
    ('looped, no fold', 'read', 'Looped form, read with no fold'),
    ('looped, DSB ST', 'write', 'Looped form, write with DSB ST'),
    ('single-call', 'read', 'Single-call form, read'),
    ('single-call', 'write', 'Single-call form, write'),
]
GREY = '#8b929b'
MUTED = '#5b636d'      # muted ink of the page, for the word "void" in a table cell
NUMWORD = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven'}


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _join(items):
    items = list(items)
    if len(items) < 2:
        return ''.join(items)
    return ', '.join(items[:-1]) + ' and ' + items[-1]


def build(D, V, S):
    BN = D.boot_name
    BS = {b: 'boot ' + b for b in BN}      # short name, used inside parentheses after the full name
    F1, F2 = 'F1', 'F2'
    K = 1024
    n1 = lambda v: V.num(v, 1)
    n2 = lambda v: V.num(v, 2)
    code = lambda s: '<code>%s</code>' % s

    def span_of(lo, hi, d=1, unit='ns'):
        if V.num(lo, d) == V.num(hi, d):
            return '%s %s' % (V.num(lo, d), unit)
        return '%s to %s %s' % (V.num(lo, d), V.num(hi, d), unit)

    from cme_page import data as _data

    def both(v1, v2, d=1, unit='ns'):
        """One value for both boots when the two print the same."""
        if V.num(v1, d) == V.num(v2, d):
            return '%s %s on both boots' % (V.num(v1, d), unit)
        return '%s %s (%s) and %s %s (%s)' % (V.num(v1, d), unit, BS[F1], V.num(v2, d), unit, BS[F2])

    def size_range(sizes):
        """'4 to 24 KiB' when both ends carry the same unit, else '16 KiB to 1 MiB'."""
        a, b = V.size_label(min(sizes)), V.size_label(max(sizes))
        if a.split()[-1] == b.split()[-1]:
            return '%s to %s' % (a.split()[0], b)
        return '%s to %s' % (a, b)

    def nword(n):
        return NUMWORD.get(n, str(n))

    def nof(n, total, noun):
        """'All four fits', 'None of the four fits', '3 of the 4 fits'."""
        if n == total:
            return ('Both %s' if total == 2 else 'All %s %%s' % nword(total)) % noun
        if n == 0:
            return 'None of the %s %s' % (nword(total), noun)
        return '%d of the %d %s' % (n, total, noun)

    def verdicts(form, kern, boots=None):
        return [D.l1_fit(b, form, kern, c)['verdict'] for b in (boots or (F1, F2)) for c in ('bracket', 'span')]

    def fitq(ft, key, d=1):
        """A fitted value, or the word void: a void intercept or rate is never printed."""
        return V.num(ft[key], d) if ft['verdict'] == 'pass' else 'void'

    def icpt(b, form, kern, clock):
        """One sentence part about the intercept of one fit, from its verdict."""
        ft = D.l1_fit(b, form, kern, clock)
        if ft['verdict'] == 'pass':
            return f'the {clock} intercept is {n1(ft["intercept_ns"])} ns (est.)'
        return (f'the {clock} fit is void (largest residual {n2(ft["max_res_pct"])} % of the smallest '
                f'pass time)')

    def cap(s):
        return s[:1].upper() + s[1:]

    def bootdir(b):
        return _data.BOOTDIR[b]

    def BT(b):                      # boot name with a capital, for group rows
        return 'B' + BN[b][1:]

    # ---------------------------------------------------------------- references
    def bwref(b, src):
        rows = D.bw(b, src)
        lo = min(r['line'] for r in rows)
        hi = max(r['best_line'] for r in rows)
        logs = sorted(r['log_line'] for r in rows if r.get('log_line'))
        log = (' The commands are at lines %d to %d of <code>log.txt</code> in the same folder.' % (logs[0], logs[-1])
               if logs else '')
        return S.ref('%s/%s' % (b, src),
                     'Boot %s: <code>%s/%s</code>, lines %d to %d.%s' % (b, bootdir(b), src, lo, hi, log))

    def latref_call(b):
        parts = []
        for f in D.files[b]['latency']:
            if not f.startswith('cme-'):
                continue
            c = D.latblocks(b, f)[0]['call']
            lines = [r['line'] for r in c['reps']] + [c['best_line']]
            parts.append('<code>%s</code> lines %d to %d' % (f, min(lines), max(lines)))
        return S.ref('%s/cme-call-rows' % b,
                     'Boot %s: the <code>cme-call</code> rows of the %d CME latency files in <code>%s/</code>: %s.' % (
                         b, len(parts), bootdir(b), ', '.join(parts)))

    def latref_ocm(b):
        parts = []
        for f in D.files[b]['latency']:
            if not f.startswith('cme-latency-ocm'):
                continue
            blk = D.latblocks(b, f)[0]
            lines = []
            for sz in blk['order']:
                e = blk['sizes'][sz]
                lines += [r['line'] for r in e['reps']] + [e['best_line']]
            parts.append('<code>%s</code> lines %d to %d' % (f, min(lines), max(lines)))
        return S.ref('%s/cme-ocm-pass-rows' % b,
                     'Boot %s: the timed passes of the %d OCM latency files in <code>%s/</code>: %s.' % (
                         b, len(parts), bootdir(b), ', '.join(parts)))

    r_kern = S.ref('src/cme_kern.S',
                   'Source <code>%s/cme_kern.S</code>: header comment lines 1 to 58, <code>SM_ENTER</code> lines 71 to 84 '
                   '(register save, SMSTART, ISB, first stamp), <code>SM_LEAVE</code> lines 86 to 104 (ISB, second stamp, '
                   'SMSTOP, register restore), <code>cme_roundtrip</code> lines 131 to 140, <code>CME_READ4</code> lines '
                   '148 to 221, <code>CME_WRITE4</code> lines 227 to 253, <code>cme_read4_n</code> lines 264 to 306, '
                   '<code>cme_write4_n</code> lines 312 to 333.' % _data.ROOT)
    r_bwc = S.ref('src/bandwidth.c',
                  'Source <code>%s/bandwidth.c</code>: <code>pass()</code> lines 313 to 330 (one kernel call per segment), '
                  'the timed bracket lines 418 to 442 (untimed warm-up pass, span sum reset, two clock reads), line 519 '
                  '(<code>--perf</code> is refused with <code>--cme</code>).' % _data.ROOT)
    r_latc = S.ref('src/latency.c',
                   'Source <code>%s/latency.c</code>: lines 299 to 313 (the <code>cme-call</code> rows: 64 calls in one '
                   'bracket, their spans summed by the kernel).' % _data.ROOT)
    r_plan = S.ref('doc/plan-fit-rule',
                   'Document <code>%s/follow-up-run-plan.md</code>: line 271 (the fit rule: a residual over 2 %% of the '
                   'smallest pass time voids the intercept), lines 257 and 262 (the store hypothesis and what the '
                   'DSB ST rows can show).' % _data.ROOT)

    # --------------------------------------------------------------------- terms
    S.term('CME', 'the Arm C1-SME2 matrix engine unit. One CME serves one cluster of two cores.')
    S.term('kernel', 'one test loop in the assembly file <code>cme_kern.S</code>. It is not the Linux kernel.')
    S.term('streaming mode', 'the processor mode in which vector loads and stores run on the CME. The instruction '
           'SMSTART enters it. The instruction SMSTOP leaves it.')
    S.term('bracket time', 'the time between two clock reads in the C program, placed around the kernel call or calls.')
    S.term('span time', 'the time between two counter reads (stamps) inside the kernel. The first stamp follows SMSTART. '
           'The second stamp comes before SMSTOP.')
    S.term('outside-span time', 'bracket time minus span time. It holds the C call and return, the register save and '
           'restore, SMSTART, SMSTOP and the bookkeeping of the second stamp.')
    S.term('pass', 'one walk over the buffer or over the chain.')
    S.term('rep', 'one timed measurement. A bandwidth rep is made of several passes.')
    S.term('looped form', 'the bandwidth test with one kernel call per pass.')
    S.term('single-call form', 'the bandwidth test with all passes of a rep inside one assembly call.')
    S.term('fold', 'the XOR of all loaded words into one value. The read kernel returns that value to the core at the '
           'end of each call.')
    S.term('ISB', 'an instruction that makes the core finish the instructions in flight before the next one starts.')
    S.term('DSB ST', 'a barrier instruction that waits until the stores issued before it are complete.')
    S.term('plan rule', 'the fit rule of the run plan: when the largest residual of a straight-line fit is over 2 % of '
           'the smallest pass time, the intercept and the rate of that fit are void.')
    S.term('round-trip baseline', 'the latency row that moves a value from a core register to a CME register and back '
           '(DUP then LASTB), with no memory access.')
    S.term('cme-call row', 'a latency row that times 64 kernel calls in one bracket, each call directly after the one before it. Each call runs one '
           'step of the round-trip baseline.')
    S.term('counting window', 'the interval between the counter start and the counter stop of one latency row. In '
           'the code the counter start comes before the first clock read of the bracket, and the counter stop comes '
           'after the second clock read.')
    S.term('OCM', 'on-chip memory: five regions of 256 KiB each, reached over the mesh.')
    S.term('residual', 'The measured value minus the value of the fitted line at the same point.')

    out = []
    add = out.append

    # =============================================================== key points
    lr = {b: D.l1_form(b, 'looped', 'read') for b in (F1, F2)}
    sr = {b: D.l1_form(b, 'single-call', 'read') for b in (F1, F2)}
    fit_b = {b: D.l1_fit(b, 'looped', 'read', 'bracket') for b in (F1, F2)}
    fit_s = {b: D.l1_fit(b, 'looped', 'read', 'span') for b in (F1, F2)}
    oc = D.outside_check
    lone = {b: D.outside(b, 'ocm-64') for b in (F1, F2)}
    b2b = {b: D.outside(b, 'cme-call') for b in (F1, F2)}

    B4 = lr[F1]['ns_bracket'][0]
    S4 = lr[F1]['ns_span'][0]
    O4 = B4 - S4
    sB4 = sr[F1]['ns_bracket'][0]
    sS4 = sr[F1]['ns_span'][0]

    sz0 = D.l1_sizes[0]                              # the smallest L1 footprint (4 KiB)
    L0 = V.size_label(sz0)
    l1_list = _join(V.size_label(s) for s in D.l1_sizes)
    l1_rng = size_range(D.l1_sizes)
    lsm = {b: D.outside(b, 'looped-l1') for b in (F1, F2)}
    lss = {b: D.outside(b, 'looped-sweep-small') for b in (F1, F2)}
    sweep_src = 'cme-bandwidth-dram-1core.csv'
    sweep_rows = {b: D.bw(b, sweep_src) for b in (F1, F2)}
    small_sizes = sorted({r['size'] for r in sweep_rows[F1] if r['size'] <= 256 * K})
    large_sizes = sorted({r['size'] for r in sweep_rows[F1] if r['size'] > 256 * K})
    lr_v = verdicts('looped', 'read')
    lw_v = verdicts('looped', 'write')

    add(S.takeaways([
        f'One looped {L0} read call on {BN[F1]} takes {n1(B4)} ns. The span holds {n1(S4)} ns of it. '
        f'The other {n1(O4)} ns is outside-span time.',
        f'The single-call form reads the same {L0} in {n1(sB4)} ns per pass. So a looped rate at a small footprint '
        f'mostly measures the fixed time of a call (entry, exit, fold and stamps), not the throughput of the read loop.',
        f'A call of loads that stands alone in its bracket spends {n1(lone[F1]["median"])} ns outside its span '
        f'(median, {BS[F1]}). Calls that follow each other spend '
        f'{span_of(min(b2b[F1]["lo"], b2b[F2]["lo"]), max(b2b[F1]["hi"], b2b[F2]["hi"]))} on the cme-call rows '
        f'(both boots). They spend {span_of(min(lsm[F1]["lo"], lss[F1]["lo"]), max(lsm[F1]["hi"], lss[F1]["hi"]))} '
        f'on the looped bandwidth rows up to {V.size_label(max(small_sizes))} ({BS[F1]}). '
        f'No row shows the cause of the difference.',
        f'A fitted cost per call can be quoted only where the fit passes the plan rule. '
        f'{nof(lr_v.count("pass"), len(lr_v), "fits")} of the looped read pass. '
        f'{nof(lw_v.count("void"), len(lw_v), "fits")} of the looped write are void.',
    ]))

    # ============================================== 7.1 one looped call, to scale
    add(S.h3('callcost-lanes', 'One looped read call, to scale'))
    # est.: the part of the span that does not grow with the bytes is the intercept of the span fit
    fixed4 = fit_s[F1]['intercept_ns'] if fit_s[F1]['verdict'] == 'pass' else None
    if fixed4 is None:                               # no quotable split: draw the span as one block
        fixed4 = 0.0
    data4 = S4 - fixed4                              # est.
    nvec = sz0 // 64
    add(S.bullets([
        f'On {BN[F1]} a looped {L0} read call spends {V.pct(100 * O4 / B4, 0)} of its bracket time outside the span.',
        f'Inside the span, {n1(fixed4)} ns est. does not grow with the bytes. '
        f'The loop over the {nvec} vectors of 64 bytes takes the other {n1(data4)} ns est.',
    ]))
    GREY_LAB = 'span time that does not grow with the bytes (est.)'
    # the two parts of the span are totals of a fit: they have a length and no measured place
    SPLIT_LANE = 'span, split by the fit (est.)'
    SPLIT_TIP = 'a length, not a position: the place inside the span is schematic'
    AFTER_TIP = 'a length, not a position: it is drawn as one block after the span'
    lane_legend = lambda grey: V.legend(
        [('work', '#5f6f82', 'swatch'), (grey, GREY, 'swatch'),
         ('waiting, or not split by the rows', '#7d838c', 'dashed'),
         ('serial slice (critical path)', '#e34948', 'swatch')], width=1040)
    svg1 = lane_legend(GREY_LAB) + V.lanes([
        dict(name='C caller (bracket)', blocks=[
            (0, B4, f'one pass = one kernel call: bracket time {n1(B4)} ns', 'work')]),
        dict(name='core: save, SMSTART ... SMSTOP, restore', blocks=[
            (0, S4, 'inside the span (not split between core and CME)', 'wait'),
            dict(start=S4, end=B4, label=f'outside-span time {n1(O4)} ns', kind='critical',
                 tip=f'outside-span time {n1(O4)} ns\n{AFTER_TIP}')]),
        dict(name=SPLIT_LANE, blocks=[
            dict(start=0, end=fixed4, label=f'does not grow with the bytes: {n1(fixed4)} ns est.', kind='work',
                 color=GREY,
                 tip=f'{SPLIT_LANE}: does not grow with the bytes: {n1(fixed4)} ns est.\n{SPLIT_TIP}'),
            dict(start=fixed4, end=S4, label=f'loop: {nvec} vector loads {n1(data4)} ns est.', kind='work',
                 tip=f'{SPLIT_LANE}: loop: {nvec} vector loads {n1(data4)} ns est.\n{SPLIT_TIP}'),
            dict(start=S4, end=B4, label='outside the span', kind='wait',
                 tip=f'outside the span: {n1(O4)} ns\n{AFTER_TIP}')]),
    ], unit='ns', t_range=(0, B4), show_legend=False,
        spans=[(0, S4, f'span time {n1(S4)} ns'), (S4, B4, f'outside-span time {n1(O4)} ns', 'critical')],
        xlabel='time from the first stamp of the call, ns (to scale)',
        title='one looped 4 KiB read call on boot F1, to scale')
    add(S.fig(
        svg1,
        f'One looped {L0} read call on {BN[F1]}, from its first stamp to the first stamp of the next call, with '
        f'durations to scale. The red block is the outside-span time. The grey block is the part of the span that '
        f'does not grow with the bytes (est.), and the block after it is the loop over the {nvec} vector loads '
        f'(est.).',
        f'The loop that loads the data is the smallest part. It takes {n1(data4)} ns est. of the {n1(B4)} ns. '
        f'The red slice is {V.ratio(O4 / data4, 1)} the time of that loop.',
        note=f'Row: the read kernel (CSV name {code("cme-read")}), {L0}, best rep of {code(lr[F1]["src"])} '
        f'{bwref(F1, lr[F1]["src"])}. '
        f'The times are averages per call. The rep has one bracket around all {V.num(lr[F1]["passes"][0], 0)} '
        f'calls, and the kernel sums the spans of those calls {r_bwc}. Each value is that total divided by the '
        f'number of calls. '
        f'The figure draws the span inside the bracket. That placement follows from the order of the code, not '
        f'from a time stamp. The two stamps of every call are executed between the two clock reads of the '
        f'bracket {r_kern} {r_bwc}. '
        f'Simplifications: the outside-span time is drawn as one block after the span. Its place is schematic. '
        f'In the code a part of it comes before the span (call, save, SMSTART). Another part comes after the span '
        f'(the store of the second stamp, the add of the span to the running sum, SMSTOP, restore, return). '
        f'Only its total is measured. '
        f'The split of the span is an estimate. The grey block is the intercept of the fitted span line, '
        f'{n1(fixed4)} ns est. (the fit passes the plan rule). The loop block is the span minus that intercept. '
        f'The order of the two parts inside the '
        f'span is schematic. The loop time includes the XOR of each loaded vector. The code in the grey block is '
        f'16 register clears, the store of the first stamp, the fold and the closing ISB {r_kern}. '
        f'The rows do not show how much of the grey block is work and how much is a wait for the fold value to '
        f'return from the CME to the core. '
        f'The core lane is dashed inside the span. The rows do not split the span between the core and the CME.'))
    add(S.p(
        f'A kernel here is one test loop in {code("cme_kern.S")}, not the Linux kernel. '
        f'Each kernel call saves registers, enters streaming mode with SMSTART, takes the first stamp, runs its loop, '
        f'takes the second stamp, leaves streaming mode with SMSTOP and restores the registers {r_kern}. '
        f'The span time is the time between the two stamps. The bracket time is measured by two clock reads in C '
        f'around all calls of a rep {r_bwc}. The outside-span time is the bracket time minus the span time. '
        f'The rows hold one bracket total and one span total per rep. So a time per call is an average over the '
        f'calls of the rep.'))


    n_fit = int(B4 // sS4)
    s_out_pp = sB4 - sS4
    s_call_out = sr[F1]['outside'][0]
    s_passes = sr[F1]['passes'][0]
    blocks = [dict(start=i * sS4, end=(i + 1) * sS4, label=f'pass {i + 1}: {n1(sS4)} ns', kind='work',
                   tip=f'pass {i + 1}: {n1(sS4)} ns\nthe average span time of one pass of the rep')
              for i in range(n_fit)]
    svg2 = V.legend([('work', '#5f6f82', 'swatch'), ('waiting, or not split by the rows', '#7d838c', 'dashed')],
                    width=1040) + V.lanes([
        dict(name='C caller (bracket)', blocks=[
            (0, B4, f'one call for all {V.num(s_passes, 0)} passes of a rep (the bracket continues)', 'work')]),
        dict(name='core: save, SMSTART ... SMSTOP, restore', blocks=[
            (0, B4, 'inside the span of the one call (not split between core and CME)', 'wait')]),
        dict(name='CME: loads inside the span', blocks=blocks),
    ], unit='ns', t_range=(0, B4), show_legend=False,
        spans=[(0, sS4, f'span time per pass {n1(sS4)} ns')],
        xlabel='time, ns (same scale as the figure above)',
        title='the single-call form over the same 4 KiB, same time scale')
    add(S.fig(
        svg2,
        f'The single-call form over the same {L0} on {BN[F1]}, on the time scale of the figure above. '
        f'Row: the read kernel (CSV name {code("cme-read")}), {L0}, best rep of {code(sr[F1]["src"])} '
        f'{bwref(F1, sr[F1]["src"])}. '
        f'The window shows {n_fit} of the {V.num(s_passes, 0)} passes of the rep. Simplification: the one call of '
        f'this rep spends {n1(s_call_out)} ns outside its span, once. That is {n2(s_out_pp)} ns per pass. '
        f'It lies outside the window.',
        f'In the time of one looped call the single-call form reads the {L0} buffer {n_fit} times.'))

    nowrap = lambda s: '<span style="white-space:nowrap">%s</span>' % s
    rows = []
    for b in (F1, F2):
        rows.append(BT(b))
        l, s = lr[b], sr[b]
        rows.append([nowrap('Looped form (one call per pass)'), n2(l['ns_bracket'][0]), n2(l['ns_span'][0]),
                     n2(l['ns_bracket'][0] - l['ns_span'][0]), n2(l['gbps'][0]), n2(l['span_gbps'][0])])
        rows.append([nowrap('Single-call form (one call per rep)'), n2(s['ns_bracket'][0]), n2(s['ns_span'][0]),
                     n2(s['ns_bracket'][0] - s['ns_span'][0]), n2(s['gbps'][0]), n2(s['span_gbps'][0])])
    add(S.table(
        [f'{L0} read', 'Bracket,<br>ns per pass', 'Span,<br>ns per pass', 'Outside-span,<br>ns per pass',
         'Bracket rate,<br>GB/s', 'Span rate,<br>GB/s'],
        rows,
        caption=f'The {L0} read in both forms on both boots. Best reps of {code(lr[F1]["src"])} '
                f'{bwref(F1, lr[F1]["src"])} {bwref(F2, lr[F2]["src"])} and {code(sr[F1]["src"])} '
                f'{bwref(F1, sr[F1]["src"])} {bwref(F2, sr[F2]["src"])}.',
        note='1 GB/s is 1 byte per ns. A looped pass is one kernel call, so its outside-span time per pass is the '
             'outside-span time per call.'))

    # ============================================ 7.2 time per pass against bytes
    add(S.h3('callcost-scatter', 'Time per pass against bytes per pass'))
    d_fold = [r for r in D.l1_diffs]
    fold = {b: [r['fold_ns'] for r in d_fold if r['boot'] == b] for b in (F1, F2)}
    lvs_r = {b: [r for r in D.looped_vs_single if r['boot'] == b and r['kernel'] == 'read'
                 and r['size'] in D.l1_sizes] for b in (F1, F2)}
    lvs_rng = {b: span_of(min(r['diff_ns'] for r in lvs_r[b]), max(r['diff_ns'] for r in lvs_r[b]))
               for b in (F1, F2)}
    FORM_NAME = {('looped', 'read'): 'the looped read', ('looped', 'write'): 'the looped write',
                 ('looped, no fold', 'read'): 'the looped read with no fold',
                 ('looped, DSB ST', 'write'): 'the looped write with DSB ST',
                 ('single-call', 'read'): 'the single-call read', ('single-call', 'write'): 'the single-call write'}
    all_void = [FORM_NAME[(f, k)] for f, k, _ in FORMS if verdicts(f, k).count('void') == len(verdicts(f, k))]
    all_pass = [FORM_NAME[(f, k)] for f, k, _ in FORMS if verdicts(f, k).count('pass') == len(verdicts(f, k))]
    lead = []
    call_br_txt_early = span_of(D.baseline_summary["all"]["call_best_lo"], D.baseline_summary["all"]["call_best_hi"])
    if fit_b[F1]['verdict'] == 'pass' and fit_s[F1]['verdict'] == 'pass':
        lead.append(
            f'The looped read lies on a straight line that meets the time axis at {n1(fit_b[F1]["intercept_ns"])} ns '
            f'est. (bracket) and {n1(fit_s[F1]["intercept_ns"])} ns est. (span) on {BN[F1]}.')
        lead.append(
            f'That intercept is the fixed time of one looped read call on {BN[F1]}, fold and stamps included. '
            f'It is not the cost of a call in general. A call with one register step takes {call_br_txt_early} '
            f'({S.xref("callcost-cmecall")}).')
    if all_void:
        lead.append(f'The points of {_join(all_void)} do not lie on one line. All their fits are void. '
                    f'No line is drawn for them.')
    add(S.bullets(lead))
    REF_NAME = f'single-call read, {BS[F1]}, bracket time (reference)'
    leg = V.legend([
        (BN[F2] + ', bracket time', 'f2', 'circle'), (BN[F2] + ', span time', 'f2', 'square'),
        (BN[F1] + ', bracket time', 'f1', 'circle'), (BN[F1] + ', span time', 'f1', 'square'),
        (REF_NAME, GREY, 'diamond')], width=1040)
    xt = [(0, '0')] + [(s, V.size_label(s)) for s in D.l1_sizes]
    xmax = D.l1_sizes[-1]
    # one y axis for all six panels, so that equal heights mean equal times
    y_all = [v for f, k, _ in FORMS for b in (F1, F2) for key in ('ns_bracket', 'ns_span')
             for v in D.l1_form(b, f, k)[key]]
    y_top = 100.0 * (int(max(y_all) / 100.0) + 1)   # 500 ns
    DODGE = xmax * 0.011                 # about 4.5 px: the two boots are set apart sideways so that both show
    i16 = len(D.l1_sizes) // 2           # the footprint that carries the gap bracket (16 KiB)
    sc_gap = [abs(a - c) for b in (F1, F2) for k in ('read', 'write')
              for a, c in zip(D.l1_form(b, 'single-call', k)['ns_bracket'], D.l1_form(b, 'single-call', k)['ns_span'])]
    panels = []
    for form, kern, ptitle in FORMS:
        ser = []
        ann = []
        gaps = None
        single = form == 'single-call'
        if form == 'looped' and kern == 'read':
            ref_y = sr[F1]['ns_bracket']
            ser.append(dict(name=REF_NAME, color=GREY, marker='diamond', size=3.6, line=False,
                            points=list(zip(D.l1_sizes, ref_y)),
                            tips=[f'Single-call form, read - {BN[F1]}, bracket time (reference)\n'
                                  f'{V.size_label(s)}: {n2(v)} ns' for s, v in zip(D.l1_sizes, ref_y)]))
            d16 = lr[F1]['ns_bracket'][i16] - ref_y[i16]
            gx = D.l1_sizes[i16] + 3 * DODGE
            gaps = [dict(x=gx, y0=ref_y[i16], y1=lr[F1]['ns_bracket'][i16], text=' ')]
            ann.append(dict(x=gx, y=ref_y[i16], dx=44, dy=36,
                            text=f'looped minus single-call\n{V.signed(d16, 1)} ns at '
                                 f'{V.size_label(D.l1_sizes[i16])} (boot F1)'))
        for b, col, dx in ((F2, 'f2', -DODGE), (F1, 'f1', DODGE)):
            fr = D.l1_form(b, form, kern)
            for clock, key, mk in (('bracket', 'ns_bracket', 'circle'), ('span', 'ns_span', 'square')):
                if single and clock == 'span':
                    continue                 # within sc_gap of the bracket points: not drawn, see the caption
                ft = D.l1_fit(b, form, kern, clock)
                pts = [(s + dx, v) for s, v in zip(fr['sizes'], fr[key])]
                if b == F1:                  # direct label at the right end of each cluster
                    pts[-1] = pts[-1] + (clock,)
                d = dict(name=f'{BN[b]}, {clock} time', color=col, marker=mk, size=4.5, line=False, points=pts,
                         tips=[f'{ptitle} - {BN[b]}, {clock} time\n{V.size_label(s)}: {n2(v)} ns'
                               for s, v in zip(fr['sizes'], fr[key])])
                if ft['verdict'] == 'pass':
                    d['fit'] = (1.0 / ft['rate_gbps'], ft['intercept_ns'])
                    d['fit_range'] = (0, xmax)
                    if b == F1 and form == 'looped' and kern == 'read' and clock == 'bracket':
                        txt = ['intercepts (boot F1, est.)', f'bracket {n1(ft["intercept_ns"])} ns']
                        if fit_s[F1]['verdict'] == 'pass':
                            txt.append(f'span {n1(fit_s[F1]["intercept_ns"])} ns')
                        ann.append(dict(x=0, y=ft['intercept_ns'], dx=78, dy=-92, text='\n'.join(txt)))
                ser.append(d)
        vv = verdicts(form, kern)
        nvoid = vv.count('void')
        sub = (f'all {nword(len(vv))} fits pass' if nvoid == 0 else
               (f'all {nword(len(vv))} fits void: no line' if nvoid == len(vv) else
                f'{len(vv) - nvoid} of {len(vv)} fits pass'))
        if single:
            sub += f', span time within {span_of(min(sc_gap), max(sc_gap))} of bracket time, not drawn'
        svg = V.line_chart(ser, x='linear', xticks=xt, xlabel='bytes per pass', ylabel='time per pass, ns',
                           yunit='ns', xfmt=V.size_label, yfmt=n2, xrange=(0, xmax), yrange=(0, y_top), width=508,
                           height=320, show_legend=False, annotations=ann or None, gaps=gaps,
                           title=ptitle + ': time per pass against bytes per pass')
        panels.append('<div style="font-weight:600;font-size:13px;margin:10px 0 2px">%s '
                      '<span style="font-weight:400;color:#5b636d">(%s)</span></div>%s' % (ptitle, sub, svg))
    grid = leg + ''.join(S.cols(panels[i], panels[i + 1]) for i in range(0, len(panels), 2))
    srcs = sorted({D.l1_form(F1, f, k)['src'] for f, k, _ in FORMS})
    lwb = D.l1_form(F1, 'looped', 'write')['ns_bracket']
    slopes = [(lwb[i + 1] - lwb[i]) / ((D.l1_sizes[i + 1] - D.l1_sizes[i]) / K) for i in range(2)]
    add(S.fig(
        grid,
        f'Time per pass against bytes per pass for the six kinds of row at {l1_rng} (footprints that fit in the '
        f'CME L1), both boots, best reps. Circles are bracket times '
        f'and squares are span times. All six panels have the same time axis. A line is drawn only where the fit '
        f'passes the plan rule, and it is extended to 0 bytes to show the intercept (est.).',
        f'At every size the looped read lies {lvs_rng[F1]} above the single-call read on {BN[F1]} (grey diamonds, '
        f'first panel). The looped write points do not follow one line. A looped write pass grows by '
        f'{n1(slopes[0])} ns per KiB from {V.size_label(D.l1_sizes[0])} to {V.size_label(D.l1_sizes[1])}. It grows '
        f'by {n1(slopes[1])} ns per KiB from {V.size_label(D.l1_sizes[1])} to {V.size_label(D.l1_sizes[2])} '
        f'(bracket, {BS[F1]}).',
        note='Files: ' + ', '.join(f'{code(s)} {bwref(F1, s)} {bwref(F2, s)}' for s in srcs) +
        f'. Simplifications: the marks of the two boots are set 4 px to the left and to the right of their '
        f'footprint, so that both show. In the two single-call panels only the bracket times are drawn. The span '
        f'times lie within {span_of(min(sc_gap), max(sc_gap))} of them and are in the table below. The grey '
        f'diamonds in the first panel repeat the bracket times of the single-call read on {BN[F1]}.'))
    add(S.p(
        f'Each chart plots the time of one pass against the bytes of one pass at {l1_list}. '
        f'All {nword(len(D.l1_sizes))} footprints fit in the CME L1. '
        f'A straight line through the {nword(len(D.l1_sizes))} points has two parts. The intercept is the time of '
        f'a pass of 0 bytes. '
        f'The slope gives the rate. In the looped form a pass is one call, so the intercept is the fixed time per '
        f'call of that kernel. Every intercept and every fitted rate is an estimate (est.). '
        f'The plan rule decides whether a fit counts {r_plan}. '
        f'Two control rows exist beside the looped read and the looped write. The no-fold read leaves out the fold '
        f'(the XOR of all loaded words into one value) at the end '
        f'of each call. The DSB ST write adds a store barrier before the second stamp, inside the span {r_kern}.'))


    hdr = ['Form', 'Kernel', 'Clock'] + [V.size_label(s) for s in D.l1_sizes]
    rows = []
    for b in (F1, F2):
        rows.append(BT(b) + ', ns per pass')
        for form, kern, _ in FORMS:
            fr = D.l1_form(b, form, kern)
            rows.append([form, kern, 'bracket'] + [n2(v) for v in fr['ns_bracket']])
            rows.append([form, kern, 'span'] + [n2(v) for v in fr['ns_span']])
    add(S.table(hdr, rows,
                caption=f'Time per pass of the six kinds of row at {l1_rng}, in ns, best reps. The files are those '
                        f'of Figure {S.n_fig}.',
                note='Passes per rep: %s at %s. A time per pass is the bytes per pass divided by the rate of the '
                     'best row. The file prints that rate with 5 significant digits. So a span time here can differ '
                     'by 0.01 ns from the <code>span_s</code> column of the same rep.' % (
                    ', '.join(V.num(p, 0) for p in lr[F1]['passes']),
                    ', '.join(V.size_label(s) for s in D.l1_sizes)),
                align='lll' + 'r' * len(D.l1_sizes)))

    rate_b, rate_s = fit_b[F1], fit_s[F1]
    sc_lo, sc_hi = min(sr[F1]['gbps']), max(sr[F1]['gbps'])
    blt = [
        f'Without the fold and the return of its value to the core, the looped read takes '
        f'{span_of(min(fold[F1]), max(fold[F1]))} less per pass on {BN[F1]}. On {BN[F2]} it takes '
        f'{span_of(min(fold[F2]), max(fold[F2]))} less (bracket, the {nword(len(D.l1_sizes))} sizes). '
        f'The rows do not separate the work of the fold from the wait for its value.',
        f'With one call per pass, the looped read takes {lvs_rng[F1]} more per pass than the single-call read on '
        f'{BN[F1]}. On {BN[F2]} it takes {lvs_rng[F2]} more. '
        f'The difference holds the call, the fold of each call and the stamps together.',
    ]
    if rate_b['verdict'] == 'pass' and rate_s['verdict'] == 'pass':
        blt.append(
            f'The two clocks give nearly the same slope. The fitted rate of the looped read on {BN[F1]} is '
            f'{V.gbps(rate_b["rate_gbps"])} est. by the bracket and {V.gbps(rate_s["rate_gbps"])} est. by the span.')
        blt.append(
            f'{S.xref("lat-perrep", cap=True)} shows that each timed rep of the latency test counts about one inner '
            f'refill per line of its chain. The looped bandwidth rows carry no refill counter. '
            f'A refill of every line in each call would add time in proportion to the bytes. '
            f'The fitted span rate of the looped read ({V.gbps(rate_s["rate_gbps"])} est.) is '
            f'{"not below" if rate_s["rate_gbps"] >= sc_hi else "below"} the rates of the single-call read at the '
            f'same footprints ({span_of(sc_lo, sc_hi, 1, "GB/s")}).')
    add(S.bullets(blt))

    # ======================================================= 7.3 the fits table
    add(S.h3('callcost-fits', 'The fitted lines and the plan-rule verdict'))
    npass = sum(1 for f in D.l1_fits if f['verdict'] == 'pass')
    add(S.bullets([
        f'{npass} of the {len(D.l1_fits)} fits pass the plan rule. The other {len(D.l1_fits) - npass} are void.',
        'A void fit shows no intercept and no rate. The table keeps its residual. '
        'The residual is the reason for the verdict.',
    ]))

    def fitcell(ft, v, d):
        # a void intercept or rate is never printed: the cell holds the word "void"
        return V.num(v, d) if ft['verdict'] == 'pass' else f'<span style="color:{MUTED}">void</span>'

    rows = []
    hl = []
    i = 0
    for b in (F1, F2):
        rows.append(BT(b))
        for form, kern, _ in FORMS:
            for clock in ('bracket', 'span'):
                ft = D.l1_fit(b, form, kern, clock)
                rows.append([form, kern, clock, fitcell(ft, ft['intercept_ns'], 1), fitcell(ft, ft['rate_gbps'], 1),
                             f'{n2(ft["max_res_ns"])} at {V.size_label(ft["max_res_size"])}',
                             n2(ft['smallest_pass_ns']), n2(ft['max_res_pct']),
                             '<b>void</b>' if ft['verdict'] == 'void' else 'pass'])
                if ft['verdict'] == 'pass':
                    hl.append(i)
                i += 1
    add(S.table(
        ['Form', 'Kernel', 'Clock', 'Intercept,<br>ns est. (fit)', 'Rate,<br>GB/s est. (fit)', 'Largest residual, ns',
         'Smallest pass, ns',
         'Residual /<br>smallest pass, %', 'Verdict'],
        rows,
        caption=f'Least-squares line through the {nword(len(D.l1_sizes))} points of each row of the table above: '
                f'time per pass = intercept + bytes / rate. A residual is the measured time minus the time on the '
                f'line. The plan rule voids a fit whose largest residual is over 2 % of its '
                f'smallest pass time {r_plan}.',
        note='Shaded rows pass. A void fit has no quotable intercept or rate. Every intercept and every rate of '
             'this table is a fitted value, so it is an estimate (est.). '
             'In the single-call form the intercept is a fixed time per pass inside one call, not a cost per call.',
        highlight=hl, align='lllrrrrrl'))

    sw = {b: D.l1_fit(b, 'single-call', 'write', 'bracket') for b in (F1, F2)}
    nf = {b: D.l1_fit(b, 'looped, no fold', 'read', 'bracket') for b in (F1, F2)}
    blt = []
    for b in (F1, F2):
        blt.append(f'Looped read, {BN[b]}: {icpt(b, "looped", "read", "bracket")}. '
                   f'{cap(icpt(b, "looped", "read", "span"))}. An intercept of the looped form is a time per call.')
    blt.append(f'Looped read with no fold, bracket clock: on {BN[F1]} {icpt(F1, "looped, no fold", "read", "bracket")}. '
               f'On {BN[F2]} {icpt(F2, "looped, no fold", "read", "bracket")}.')
    sw_v = verdicts('single-call', 'write')
    t = f'Single-call write: {nof(sw_v.count("pass"), len(sw_v), "fits").lower()} pass.'
    if sw[F1]['verdict'] == 'pass' and sw[F2]['verdict'] == 'pass':
        t += f' The bracket intercept is {both(sw[F1]["intercept_ns"], sw[F2]["intercept_ns"], 1, "ns est.")}.'
        if sw[F1]['intercept_ns'] < 0:
            t += (f' A negative time per pass has no physical meaning. Its size is '
                  f'{V.pct(100 * abs(sw[F1]["intercept_ns"]) / sw[F1]["smallest_pass_ns"])} of the smallest pass '
                  f'time ({n1(sw[F1]["smallest_pass_ns"])} ns, {BS[F1]}).')
        t += (f' The fitted rate is {V.gbps(sw[F1]["rate_gbps"])} est. ({BS[F1]}) and '
              f'{V.gbps(sw[F2]["rate_gbps"])} est. ({BS[F2]}).')
    blt.append(t)
    if all_void:
        blt.append(f'{cap(_join(all_void))}: every fit is void on both boots and both clocks.')
    add(S.bullets(blt))
    add(S.insufficient(
        'The intercepts include the cost of the two stamps and of their bookkeeping (the store of the stamp and '
        'the add of the span to the running sum). No row of these boots runs '
        'the same kernel with the stamps compiled out. That control would give the share of the stamps.'))

    # ===================================================== 7.4 call-cost rows
    add(S.h3('callcost-rows', 'The call-cost rows: short calls, in ns per call'))
    cc = {(r['boot'], r['kernel'], r['size']): r for r in D.call_cost}
    cc_w_sizes = sorted({r['size'] for r in D.call_cost if r['kernel'] == 'write'})
    cc_r_sizes = sorted({r['size'] for r in D.call_cost if r['kernel'] == 'read'})
    wlo, whi = cc_w_sizes[0], cc_w_sizes[-1]              # 1 KiB and 8 KiB
    cr1 = {b: cc[(b, 'read', cc_r_sizes[0])] for b in (F1, F2)}
    cw1 = {b: cc[(b, 'write', wlo)] for b in (F1, F2)}
    cw4 = {b: cc[(b, 'write', cc_w_sizes[-2])] for b in (F1, F2)}
    cw8 = {b: cc[(b, 'write', whi)] for b in (F1, F2)}
    lw = {b: D.l1_form(b, 'looped', 'write') for b in (F1, F2)}
    swf = {b: D.l1_form(b, 'single-call', 'write') for b in (F1, F2)}
    dw = {b: D.l1_form(b, 'looped, DSB ST', 'write') for b in (F1, F2)}
    wratio = {b: cw8[b]['bracket_ns'] / cw1[b]['bracket_ns'] for b in (F1, F2)}
    est1 = wlo / swf[F1]['gbps'][0]                       # est.: 1 KiB at the throughput of the single-call write loop
    add(S.bullets([
        f'A {V.size_label(cc_r_sizes[0])} read call takes {n1(cr1[F1]["bracket_ns"])} ns on {BN[F1]} and '
        f'{n1(cr1[F2]["bracket_ns"])} ns on {BN[F2]}. A {V.size_label(wlo)} write call takes '
        f'{both(cw1[F1]["bracket_ns"], cw1[F2]["bracket_ns"])}.',
        f'A write call of {V.num(whi / wlo, 0)} times the bytes takes only {V.ratio(wratio[F1])} '
        f'({BS[F1]}) and {V.ratio(wratio[F2])} ({BS[F2]}) the time.',
        f'The single-call form writes {V.gbps(swf[F1]["gbps"][0])} at {L0} on {BN[F1]}. At that rate '
        f'the write loop moves {V.size_label(wlo)} in {n1(est1)} ns est. The call takes '
        f'{n1(cw1[F1]["bracket_ns"])} ns. '
        f'So most of the time of a short call does not grow with its bytes. '
        f'{S.xref("callcost-write", cap=True)} shows why the write rows cannot give the exact share.',
    ]))
    hrows = []
    order = [('read', s) for s in cc_r_sizes] + [('write', s) for s in cc_w_sizes]
    for kern, sz in order:
        a, c = cc[(F2, kern, sz)], cc[(F1, kern, sz)]
        lab = f'{V.size_label(sz)} {kern} call'
        notes = [f'= span {n1(a["span_ns"])} + outside {n1(a["outside_ns"])}',
                 f'= span {n1(c["span_ns"])} + outside {n1(c["outside_ns"])}']
        if kern == 'write' and sz == whi:
            notes = [notes[0] + f'  ({V.ratio(wratio[F2])} the {V.size_label(wlo)} write call)',
                     notes[1] + f'  ({V.ratio(wratio[F1])} the {V.size_label(wlo)} write call)']
        hrows.append(dict(label=lab, values=[a['bracket_ns'], c['bracket_ns']], notes=notes,
                          tips=[f'{lab} - {BN[b]}\nbracket {n2(r["bracket_ns"])} ns, span {n2(r["span_ns"])} ns, '
                                f'outside-span {n2(r["outside_ns"])} ns' for b, r in ((F2, a), (F1, c))]))
    svg = V.hbar(hrows, series=[(BN[F2], 'f2'), (BN[F1], 'f1')], unit='ns', fmt=n1,
                 xlabel='bracket time per call, ns', label_w=170, title='call-cost rows, ns per call')
    n_cc_reps = len(cw1[F1]['outside_reps'])
    out_best = [r['outside_ns'] for r in D.call_cost]
    add(S.fig(
        svg,
        f'Bracket time of one kernel call, looped form, best reps. Rows: the read kernel (CSV name '
        f'{code("cme-read")}) at {_join(V.size_label(s) for s in cc_r_sizes)} and the write kernel (CSV name '
        f'{code("cme-write")}) at {_join(V.size_label(s) for s in cc_w_sizes)} of {code(cr1[F1]["src"])} '
        f'{bwref(F1, cr1[F1]["src"])} '
        f'{bwref(F2, cr1[F2]["src"])}. The text after each bar splits the time into span and outside-span time.',
        f'The {V.size_label(whi)} write call takes {V.ratio(wratio[F1])} the time of the {V.size_label(wlo)} write '
        f'call on {BN[F1]}. The outside-span time of the best reps is {span_of(min(out_best), max(out_best))} in '
        f'every row of both boots. The span of the read call is longer than the span of the write call by '
        f'{n1(cr1[F1]["span_ns"] - cw1[F1]["span_ns"])} ns at {V.size_label(wlo)} ({BS[F1]}).'))
    rows = []
    for b in (F1, F2):
        rows.append(BT(b))
        for kern, sz in order:
            r = cc[(b, kern, sz)]
            rows.append([nowrap(f'{V.size_label(sz)} {kern}'), V.num(r['passes'], 0), n2(r['bracket_ns']),
                         n2(r['span_ns']),
                         n2(r['outside_ns']), f'{n1(r["outside_lo"])} to {n1(r["outside_hi"])}',
                         n2(r['gbps']), n2(r['span_gbps'])])
    add(S.table(
        ['Call', 'Calls per rep', 'Bracket, ns', 'Span, ns', 'Outside-span, ns',
         f'Outside-span, {n_cc_reps} reps, ns', 'Bracket rate, GB/s', 'Span rate, GB/s'],
        rows,
        caption=f'The call-cost rows, per kernel call, best reps, {n_cc_reps} reps per row, {code(cr1[F1]["src"])} '
                f'{bwref(F1, cr1[F1]["src"])} {bwref(F2, cr1[F2]["src"])}.',
        note='The bracket and span times of the best rep are the bytes per call divided by the rates of the best '
             'row (5 significant digits). The outside-span times use the <code>span_s</code> column of each rep. '
             'So the outside-span time of a row can differ by 0.01 ns from its bracket time minus its span time.',
        align='lrrrrrrr'))
    grow = {b: cw8[b]['span_ns'] - cw4[b]['span_ns'] for b in (F1, F2)}
    dbytes = cw8[F1]['size'] - cw4[F1]['size']
    app_rate = dbytes / grow[F1]                          # est.
    i8 = D.l1_sizes.index(cw8[F1]['size'])
    sc8 = swf[F1]['gbps'][i8]
    blt = [
        f'The span of a write call grows by {n1(grow[F1])} ns from {cw4[F1]["label"]} to {cw8[F1]["label"]} on '
        f'{BN[F1]} ({n1(grow[F2])} ns on {BS[F2]}). The added {V.num(dbytes, 0)} bytes would then move at '
        f'{V.gbps(app_rate, 0)} est. That is {V.ratio(app_rate / sc8, 1)} the {V.gbps(sc8)} of the single-call '
        f'form at {cw8[F1]["label"]}. {S.xref("callcost-write", cap=True)} treats this.',
        f'The outside-span time of the write calls has two levels on {BN[F1]}. The {nword(n_cc_reps)} reps of the '
        f'{cw4[F1]["label"]} row give {_join(n1(v) for v in cw4[F1]["outside_reps"])} ns. The {cw8[F1]["label"]} '
        f'row gives {span_of(cw8[F1]["outside_lo"], cw8[F1]["outside_hi"])}. On {BN[F2]} the same rows give '
        f'{span_of(cw4[F2]["outside_lo"], cw8[F2]["outside_hi"])}.',
        f'In the {cw4[F1]["label"]} row of {BN[F1]} the bracket times of the {nword(n_cc_reps)} reps are '
        f'{_join(n1(v) for v in cw4[F1]["reps_bracket_ns"])} ns. Their span times are '
        f'{span_of(min(cw4[F1]["reps_span_ns"]), max(cw4[F1]["reps_span_ns"]))}. '
        f'So in that row the higher level is extra bracket time.',
    ]
    # the looped write rows of the L1 files: rows where the reps split into two levels of outside-span time
    two_level_note = []
    for b in (F1, F2):
        for row in lw[b]['rows']:
            reps = row['reps']
            outs = [x['outside_ns_per_call'] for x in reps]
            mid = (min(outs) + max(outs)) / 2.0
            hi_g = [x for x in reps if x['outside_ns_per_call'] > mid]
            lo_g = [x for x in reps if x['outside_ns_per_call'] <= mid]
            if max(outs) - min(outs) < 10.0 or len(hi_g) != 1:
                continue                                  # one level, or no single odd rep
            x = hi_g[0]
            sp = [y['span_ns_per_pass'] for y in lo_g]
            ou = [y['outside_ns_per_call'] for y in lo_g]
            br = [y['bracket_ns_per_pass'] for y in reps]
            blt.append(
                f'The two levels are also in the looped write rows of {l1_rng}. At {row["label"]} on {BN[b]} one '
                f'rep of {nword(len(reps))} has a span of {n1(x["span_ns_per_pass"])} ns and an outside-span time '
                f'of {n1(x["outside_ns_per_call"])} ns. The other {nword(len(lo_g))} have spans of '
                f'{span_of(min(sp), max(sp))} and outside-span times of {span_of(min(ou), max(ou))}. '
                f'The bracket time is {span_of(min(br), max(br))} in all {nword(len(reps))}. '
                f'So in that row the higher level is not extra time. The span is '
                f'{n1(_median(sp) - x["span_ns_per_pass"])} ns shorter in that rep.')
            if row['best_rep_index'] == reps.index(x):
                two_level_note.append(
                    f'The {BS[b]} {row["label"]} looped span is that of the rep with the best bracket rate. '
                    f'The other {nword(len(lo_g))} reps have spans of {span_of(min(sp), max(sp))} '
                    f'({span_of(min(y["span_gbps"] for y in lo_g), max(y["span_gbps"] for y in lo_g), 1, "GB/s")}).')
    add(S.bullets(blt))
    add(S.insufficient(
        f'No row shows the cause of the two levels on {BN[F1]}. These rows carry no counters. '
        f'Ten reps per row would show whether the two levels are stable. A CME cycle count per call on a bandwidth '
        f'row would show whether the core or the CME spends the extra '
        f'{n1(cw8[F1]["outside_ns"] - cw8[F2]["outside_ns"])} ns of the {cw8[F1]["label"]} call-cost row.'))

    # ====================================================== 7.5 cme-call rows
    add(S.h3('callcost-cmecall', 'The cme-call rows: the shortest call'))
    bs = D.baseline_summary
    cs = {b: bs[b] for b in (F1, F2)}
    c_span = cs[F1]['call_span_mode']
    c_out = b2b[F1]['lo']
    c_br = cs[F1]['call_best_lo']
    rt_span = D.rt_span_ns
    c_diff = c_span - rt_span                         # a difference of two rows, not a measured part of the span
    n_lat = cs[F1]['n_files']                         # CME latency files per boot
    call_spans = [v for r in D.baseline for v in r['call_span_reps']]
    span_lo = min(call_spans)
    n_span_lo = sum(1 for v in call_spans if v == span_lo)
    span_txt = (f'{n2(span_lo)} ns in {n_span_lo} of the {len(call_spans)} reps (highest '
                f'{n2(max(call_spans))} ns)')
    call_br_txt = span_of(bs["all"]["call_best_lo"], bs["all"]["call_best_hi"])
    b2b_all = span_of(min(b2b[F1]["lo"], b2b[F2]["lo"]), max(b2b[F1]["hi"], b2b[F2]["hi"]))
    add(S.bullets([
        f'A call that does one register step takes {call_br_txt} over the {bs["all"]["n_files"]} files of both '
        f'boots.',
        f'Its span is {span_txt}. Its outside-span time is {b2b_all}.',
    ]))
    add(S.p(
        f'A cme-call row times 64 kernel calls in one bracket, each call directly after the one before it {r_latc}. Each call runs one step of the '
        f'round-trip baseline. That step moves a value from a core register to a CME register and back. '
        f'The row has no memory access. So it gives the time of a call whose only work is one register step.'))
    svg = V.legend([('work', '#5f6f82', 'swatch'), ('waiting, or not split by the rows', '#7d838c', 'dashed'),
                    ('serial slice (critical path)', '#e34948', 'swatch')], width=1040) + V.lanes([
        dict(name='C caller (bracket)', blocks=[(0, c_br, f'one of 64 calls: bracket time {n1(c_br)} ns', 'work')]),
        dict(name='core: save, SMSTART ... SMSTOP, restore', blocks=[
            (0, c_span, 'inside the span (not split)', 'wait'),
            dict(start=c_span, end=c_br, label=f'outside-span time {n1(c_out)} ns', kind='critical',
                 tip=f'outside-span time {n1(c_out)} ns\n{AFTER_TIP}')]),
        dict(name='CME: one register step', blocks=[
            (0, c_span, f'span time {n1(c_span)} ns (not split)', 'work'),
            dict(start=c_span, end=c_br, label='outside the span', kind='wait',
                 tip=f'outside the span: {n1(c_out)} ns\n{AFTER_TIP}')]),
    ], unit='ns', t_range=(0, B4), show_legend=False,
        spans=[(0, c_span, f'span time {n1(c_span)} ns'), (c_span, c_br, f'outside-span time {n1(c_out)} ns', 'critical')],
        xlabel='time from the first stamp of the call, ns (same scale as the first figure of this section)',
        title='one call of a cme-call row on boot F1, to scale')
    add(S.fig(
        svg,
        f'One call of a cme-call row on {BN[F1]}, drawn on the time scale of the looped read call. Rows: '
        f'{code("cme-call")} of the {n_lat} CME latency files {latref_call(F1)}. '
        f'The values are the lowest bracket time, the span of {cs[F1]["call_span_n_mode"]} of the '
        f'{cs[F1]["call_span_n"]} reps, and the lowest outside-span time. Each value is the total of a rep divided '
        f'by its 64 calls. The span is drawn inside the bracket. That placement follows from the order of the '
        f'code: the two stamps of every call are executed between the two clock reads of the bracket {r_kern} '
        f'{r_latc}. Simplifications: the outside-span time is drawn as one block after the span. Its place is '
        f'schematic. The span is drawn as one block. The rows do not split it into parts. '
        f'The core lane is dashed inside the span. The rows do not split the span between the core and the CME.',
        f'With one register step as the only work, a call still takes {n1(c_br)} ns. '
        f'{V.pct(100 * c_out / c_br, 0)} of that is outside the span.'))
    rows = [
        ['Files', cs[F1]['n_files'], cs[F2]['n_files']],
        ['Bracket, ns per call (best rows)'] + [
            f'{n2(cs[b]["call_best_lo"])} to {n2(cs[b]["call_best_hi"])}' for b in (F1, F2)],
        ['Span, ns per call (all reps)'] + [
            f'{n2(cs[b]["call_span_lo"])} to {n2(cs[b]["call_span_hi"])}' for b in (F1, F2)],
        [f'Reps with a span of {n2(span_lo)} ns'] + [
            '%d of %d' % (sum(1 for r in D.baseline if r['boot'] == b for v in r['call_span_reps'] if v == span_lo),
                          cs[b]['call_span_n']) for b in (F1, F2)],
        ['Outside-span, ns per call (all reps)'] + [
            f'{n2(cs[b]["call_outside_lo"])} to {n2(cs[b]["call_outside_hi"])}' for b in (F1, F2)],
        ['Round-trip baseline span, ns per step'] + [n2(cs[b]['rt_span_lo']) for b in (F1, F2)],
    ]
    add(S.table(
        ['cme-call rows', BT(F1), BT(F2)], rows,
        caption=f'The cme-call rows of the {n_lat} CME latency files of each boot {latref_call(F1)} '
                f'{latref_call(F2)}. Each rep times 64 calls. The values are per call.',
        align='lrr'))
    add(S.bullets([
        f'The span of a cme-call call is {n1(c_span)} ns. The round-trip baseline row gives {n1(rt_span)} ns per '
        f'step (span time of a long loop, divided by its steps). The first value is {n1(c_diff)} ns above the '
        f'second. That number is a difference of two rows. It is not a measured part of the span.',
        f'The outside-span time here ({span_of(b2b[F1]["lo"], b2b[F1]["hi"])}) is lower than that of the looped '
        f'bandwidth calls ({span_of(lsm[F1]["lo"], lsm[F1]["hi"])} at {l1_rng} on {BS[F1]}). '
        f'The outside-span time is not one constant.',
    ]))

    add(S.insufficient(
        'The round-trip baseline is a separate measurement. Its time per step is an average over a long loop. '
        'The rows do not show that the one step of a cme-call call takes that time. So the span of a cme-call '
        'call cannot be split into one step and a fixed rest. A cme-call row whose kernel runs no step would '
        'give the span of a call without the step.'))

    # ================================== 7.6 a call alone against calls that follow each other
    add(S.h3('callcost-alone', 'A call alone in its bracket against calls that follow each other'))
    # the two clock reads of a bracket: the empty-bracket time that each CME latency file prints
    ovh = {b: bs[b]['overhead_common'] for b in (F1, F2)}
    ovh_other = {b: bs[b]['overhead_other'] for b in (F1, F2)}
    clock_share = {b: ovh[b] * 63.0 / 64.0 for b in (F1, F2)}           # est.: lone call minus 1/64 of it
    extra_net = {b: oc[b]['extra_alone_ns'] - clock_share[b] for b in (F1, F2)}   # est.
    ovh_note = ''
    for b in (F1, F2):
        if ovh_other[b]:
            ovh_note += (f' {nword(len(ovh_other[b])).capitalize()} file of {BS[b]} prints '
                         f'{_join(n1(v) for _, v in ovh_other[b])} ns.')
    cg = {(r['boot'], r['key']): r for r in D.cycle_gap}
    cg_keys = ('ocm-64', 'ocm-320', 'cme-call')
    gap_med = [cg[(b, k)]['median_ns'] for b in (F1, F2) for k in cg_keys]
    add(S.bullets([
        f'The outside-span time of a call of loads that stands alone in its bracket is '
        f'{both(lone[F1]["median"], lone[F2]["median"])} (medians of {lone[F1]["n"]} passes each).',
        f'That is {n1(oc[F1]["extra_alone_ns"])} ns ({BS[F1]}) and {n1(oc[F2]["extra_alone_ns"])} ns ({BS[F2]}) '
        f'more than a call of the cme-call rows.',
    ]))
    clock_bullet = (
        f'A bracket also holds its two clock reads. They take {both(ovh[F1], ovh[F2])} in an empty bracket '
        f'{latref_call(F1)} {latref_call(F2)}.{ovh_note} A lone call carries all of that time. A call of a cme-call '
        f'row carries 1/64 of it ({n1(ovh[F1] / 64.0)} ns). So {n1(clock_share[F1])} ns est. of the difference is '
        f'clock-read time. {n1(extra_net[F1])} ns est. ({BS[F1]}) and {n1(extra_net[F2])} ns est. ({BS[F2]}) '
        f'remain without a cause.')
    gap_cyc = [cg[(b, k)]['median'] for b in (F1, F2) for k in cg_keys]
    gap_bullet = (
        f'Per counting window the CME cycle count is {span_of(min(gap_cyc), max(gap_cyc), 0, "cycles")} below the '
        f'core cycle count (medians of the {nword(len(cg_keys))} kinds of row on both boots). At the measured '
        f'{V.num(D.clock["cycles_per_ns"], 3)} cycles per ns that is {span_of(min(gap_med), max(gap_med))}.')
    calls_large = sorted({r['passes'] for b in (F1, F2) for r in sweep_rows[b] if r['size'] in large_sizes},
                         reverse=True)
    keys = [('cme-call', 'cme-call rows: 64 calls that follow each other'),
            ('looped-l1', f'looped bandwidth calls, {l1_rng}'),
            ('looped-sweep-small', f'looped bandwidth calls, {size_range(small_sizes)}'),
            ('looped-sweep-large', f'looped bandwidth calls, {size_range(large_sizes)} '
                                   f'({_join(str(c) for c in calls_large).replace(" and ", " or ")} calls per rep)'),
            ('ocm-64', 'OCM latency pass of 64 loads'),
            ('ocm-320', 'OCM latency pass of 320 loads'),
            ('single-later-read', 'single-call read, reps after the first'),
            ('single-first-read', 'single-call read, first rep'),
            ('single-later-write', 'single-call write, reps after the first'),
            ('single-first-write', 'single-call write, first rep')]
    LONE_KEYS = [k for k, _ in keys[4:]]
    lone_lo = {b: min(D.outside(b, k)['lo'] for k in LONE_KEYS) for b in (F1, F2)}
    hrows = [dict(header='Calls that follow each other in one bracket')]
    for k, lab in keys:
        if k == 'ocm-64':
            hrows.append(dict(header='One call alone in its bracket'))
        a, c = D.outside(F2, k), D.outside(F1, k)
        notes = [f'({n1(a["lo"])} to {n1(a["hi"])})', f'({n1(c["lo"])} to {n1(c["hi"])})']
        if k == 'ocm-64':
            notes = [notes[0] + f'  +{n1(oc[F2]["extra_alone_ns"])} ns over cme-call',
                     notes[1] + f'  +{n1(oc[F1]["extra_alone_ns"])} ns over cme-call']
        hrows.append(dict(label=lab, values=[a['median'], c['median']], notes=notes,
                          tips=[f'{lab} - {BN[b]}\nmedian {n1(r["median"])} ns, lowest {n1(r["lo"])} ns, '
                                f'highest {n1(r["hi"])} ns, {r["n"]} reps' for b, r in ((F2, a), (F1, c))]))
    svg = V.hbar(hrows, series=[(BN[F2], 'f2'), (BN[F1], 'f1')], unit='ns', fmt=n1,
                 xlabel='outside-span time per kernel call, ns (median, lowest to highest in brackets)',
                 label_w=270, title='outside-span time per kernel call by kind of row')
    occ = [f for f in D.files[F1]['bandwidth'] if f.startswith('cme-bandwidth-') and 'ocm' not in f]
    sweep_kernels = sorted({r['kernel_csv'] for r in sweep_rows[F1]})
    add(S.fig(
        svg,
        f'Outside-span time per kernel call, median over all reps of each kind of row, both boots. The brackets '
        f'give the lowest and highest rep.',
        f'Calls that follow each other spend {n1(b2b[F1]["lo"])} ns to '
        f'{n1(lss[F1]["hi"])} ns outside the span up to {V.size_label(max(small_sizes))} ({BS[F1]}, lowest to '
        f'highest rep). A call alone spends {n1(lone_lo[F1])} ns or more (lowest rep of the '
        f'{nword(len(LONE_KEYS))} kinds of lone call, {BS[F1]}).',
        note=f'Rows: the cme-call rows {latref_call(F1)} {latref_call(F2)}, the timed '
        f'passes of the OCM latency files {latref_ocm(F1)} {latref_ocm(F2)}, and the looped and single-call rows of '
        + ', '.join(f'{code(f)} {bwref(F1, f)} {bwref(F2, f)}' for f in occ if 'call-cost' not in f) +
        f'. The looped rows of {code(sweep_src)} hold the kernels '
        f'{_join(code(k) for k in sweep_kernels)}.'))
    rows = []
    for b in (F1, F2):
        rows.append(BT(b))
        for k, lab in keys:
            r = D.outside(b, k)
            rows.append([lab, r['n'], n1(r['lo']), n1(r['median']), n1(r['hi'])])
    add(S.table(['Kind of row', 'Reps', 'Lowest, ns', 'Median, ns', 'Highest, ns'], rows,
                caption='Outside-span time per kernel call over all reps. The files are those of Figure %d.' % S.n_fig,
                note='An OCM latency pass is one kernel call in its own bracket, with a counter start before it. '
                     'A single-call bandwidth rep is one kernel call in its own bracket, after one untimed pass, '
                     'with no counter call.',
                align='lrrrr'))
    slr = {b: D.outside(b, 'single-later-read') for b in (F1, F2)}
    sfr = {b: D.outside(b, 'single-first-read') for b in (F1, F2)}
    slw = {b: D.outside(b, 'single-later-write') for b in (F1, F2)}
    sweepL = {b: D.outside(b, 'looped-sweep-large') for b in (F1, F2)}
    add(S.bullets([
        clock_bullet,
        f'The lone calls of the single-call read rows spend '
        f'{span_of(min(slr[F1]["lo"], slr[F2]["lo"]), max(slr[F1]["hi"], slr[F2]["hi"]))} outside the span in the '
        f'reps after the first, on both boots. The bandwidth program runs no counter call. It refuses the counter '
        f'option together with the CME option {r_bwc}. So a counter call before the bracket cannot be the only '
        f'cause of the extra time.',
        f'The first rep of a single-call read row spends '
        f'{span_of(min(sfr[F1]["lo"], sfr[F2]["lo"]), max(sfr[F1]["hi"], sfr[F2]["hi"]))}. That is more than the '
        f'reps after it spend.',
        f'A lone write call spends more than a lone read call. In the reps after the first, the single-call write '
        f'rows spend {span_of(slw[F1]["lo"], slw[F1]["hi"])} on {BN[F1]} and '
        f'{span_of(slw[F2]["lo"], slw[F2]["hi"])} on {BN[F2]}. The medians are '
        f'{n1(slw[F1]["median"] - slr[F1]["median"])} ns and {n1(slw[F2]["median"] - slr[F2]["median"])} ns above '
        f'the lone read call. Insufficient data: no row shows why. {S.xref("callcost-write", cap=True)} gives a '
        f'hypothesis about stores that end after the span.',
        f'On a pass of 64 loads, {n1(lone[F1]["median"])} ns is '
        f'{n1(lone[F1]["median"] / 64)} ns per load. The bracket value of such a row lies above its span value by '
        f'that amount.',
        f'The outside-span time per looped call is higher in the rows with fewer calls per rep. It is '
        f'{span_of(min(sweepL[F1]["lo"], sweepL[F2]["lo"]), max(sweepL[F1]["hi"], sweepL[F2]["hi"]))} per call at '
        f'{size_range(large_sizes)} over both boots, where a rep is '
        f'{_join(str(c) for c in calls_large).replace(" and ", " or ")} calls. '
        f'In these rows the footprint grows and the number of calls per rep falls together. '
        f'So the rows do not show which of the two sets the time.',
    ]))
    add(S.hyp(
        f'A cost that is paid once per bracket is divided by fewer calls in the rows of {V.size_label(min(large_sizes))} and more. '
        'The two clock reads of the bracket are one such cost.',
        f'The {V.size_label(max(large_sizes))} row with 16 passes per rep. An outside-span time per call near that '
        f'of the rows up to {V.size_label(max(small_sizes))} confirms it. An unchanged time per call rejects it.'))

    add(S.p(f'{S.xref("open-call", cap=True)} gives the hypotheses for the extra time of a lone call, each with '
            f'the measurement that would confirm or reject it.'))

    # ================================================ 7.7 the cycle counter gap (G6)
    add(S.h3('callcost-gap', 'The CME cycle counter gap'))
    cpn = D.clock['cycles_per_ns']
    r_cnt = S.ref('src:common.h',
                  'Source <code>%s/common.h</code>: lines 248 to 256 (the counters are opened with the kernel-mode '
                  'exclusion flag), lines 462 to 495 (the counter read returns totals, the counter start and the '
                  'counter stop).' % _data.ROOT)
    r_win = S.ref('src:latency-window',
                  'Source <code>%s/latency.c</code>: lines 207 to 211 and 298 to 304 (counter start, first clock '
                  'read, kernel call or calls, second clock read, counter stop).' % _data.ROOT)
    add(S.bullets([
        gap_bullet,
        'A link between that amount and the time of a lone call is a hypothesis.',
        'A row gives four totals per pass: two cycle counts, one bracket time and one span time. '
        'It gives no time stamp of a counter start or stop. So the figure below compares the four totals as '
        'durations. It does not place the CME cycle count inside the bracket.',
    ]))

    def window_reps(b, key):
        """The rep rows of one kind of counting window on one boot."""
        reps = []
        for f in D.files[b]['latency']:
            if not f.startswith('cme-'):
                continue
            blk = D.latblocks(b, f)[0]
            if key == 'cme-call':
                reps += blk['call']['reps']
            else:
                want = 64 if key == 'ocm-64' else 320
                if not f.startswith('cme-latency-ocm'):
                    continue
                for sz in blk['order']:
                    reps += [x for x in blk['sizes'][sz]['reps'] if x['loads'] == want]
        return reps

    def window_totals(b, key):
        """Medians over the rep rows of one kind, in ns per counting window.  The four totals as
        durations: the core cycle count and the CME cycle count are converted to time at the
        measured cycles per ns.  The differences are medians of the per-pass differences."""
        reps = window_reps(b, key)
        core = [x['cycles'] * x['loads'] / cpn for x in reps]          # core cycle count as time
        brk = [x['ns'] * x['loads'] for x in reps]                     # bracket time
        cme = [x['cme_cycles'] * x['loads'] / cpn for x in reps]       # CME cycle count as time
        spn = [x['span'] * x['loads'] for x in reps]                   # span time (sum of the spans)
        return dict(
            n=len(reps), core=_median(core), bracket=_median(brk), cme=_median(cme), span=_median(spn),
            core_bracket=_median([a - c for a, c in zip(core, brk)]),
            bracket_cme=_median([a - c for a, c in zip(brk, cme)]),
            cme_span=_median([a - c for a, c in zip(cme, spn)]),
            ordered=sum(1 for a, c, e, g in zip(core, brk, cme, spn) if a >= c >= e >= g))

    ws = {(b, k): window_totals(b, k) for b in (F1, F2) for k in cg_keys}
    w64 = {b: ws[(b, 'ocm-64')] for b in (F1, F2)}
    assert w64[F1]['n'] == lone[F1]['n']
    d_gap = cg[(F1, 'ocm-64')]['median_ns']          # core cycle count minus CME cycle count, as time
    d_cme = w64[F1]['cme_span']                      # CME cycle count as time, minus span time
    # largest distance between a median of per-pass differences and the difference of the two medians
    dev = max(abs(w64[b][k] - (w64[b][p] - w64[b][q])) for b in (F1, F2)
              for k, p, q in (('core_bracket', 'core', 'bracket'), ('bracket_cme', 'bracket', 'cme'),
                              ('cme_span', 'cme', 'span')))
    QUANT = [('core', 'core cycle count, converted to time', None, None),
             ('bracket', 'bracket time (two clock reads)', 'core_bracket', 'core count as time - bracket'),
             ('cme', 'CME cycle count, converted to time', 'bracket_cme', 'bracket - CME count as time'),
             ('span', 'span time (two stamps)', 'cme_span', 'CME count as time - span')]
    hrows = [dict(header='One OCM latency pass of 64 loads: four totals of the same pass, as durations')]
    for key, lab, dkey, dlab in QUANT:
        d = dict(label=lab, values=[w64[F2][key], w64[F1][key]],
                 tips=[f'{lab} - {BN[b]}\nmedian of {w64[b]["n"]} passes: {n1(w64[b][key])} ns'
                       for b in (F2, F1)])
        if dkey:
            d['notes'] = [f'({dlab}: {n1(w64[b][dkey])} ns)' for b in (F2, F1)]
        hrows.append(d)
    svg_w = V.hbar(hrows, series=[(BN[F2], 'f2'), (BN[F1], 'f1')], unit='ns', fmt=n1,
                   xlabel='duration per pass, ns (median; bars compare lengths, not positions in time)',
                   label_w=250, title='four totals of one lone OCM pass of 64 loads, as durations')
    n_ord = {b: w64[b]['ordered'] for b in (F1, F2)}
    add(S.fig(
        svg_w,
        f'Four totals of one OCM latency pass of 64 loads, as durations, on both boots (medians of '
        f'{w64[F1]["n"]} passes per boot). The core cycle count and the CME cycle count are converted to time at '
        f'the measured {V.num(cpn, 3)} cycles per ns. The text after a bar gives the median difference to the '
        f'quantity that it names.',
        f'On {BN[F1]} the CME cycle count, converted to time, is a median of {n1(d_gap)} ns below the core cycle '
        f'count, converted to time. It is a median of {n1(d_cme)} ns above the span time.',
        note=f'The bars compare durations only. The rows hold no time stamp of a counter start or stop, so the '
        f'figure does not show one total inside another. '
        f'The four durations have the order of the figure in {n_ord[F1]} of the {w64[F1]["n"]} passes on '
        f'{BN[F1]} and in {n_ord[F2]} of the {w64[F2]["n"]} passes on {BN[F2]}. '
        f'A difference after a bar is the median of the differences of the single passes. It differs from the '
        f'difference of the two bars by up to {n1(dev)} ns. '
        f'Files: the timed passes of the OCM latency files {latref_ocm(F1)} {latref_ocm(F2)}.'))
    add(S.p(
        f'The latency rows count core cycles and CME cycles over the counting window. The counting window is '
        f'the interval between the counter start and the counter stop of one row. '
        f'Both counts are totals {r_cnt}. Both counters are opened with the kernel-mode exclusion flag {r_cnt}. '
        f'The order of the code is: counter start, first clock read, kernel call, second clock read, counter '
        f'stop {r_win}. The two stamps of the span are executed inside the kernel call {r_kern}. '
        f'So the order of the code places the span between the two clock reads, and the two clock reads between '
        f'the counter start and the counter stop. '
        f'The order of the code does not place the CME cycle count. The rows do not show in which part of the '
        f'window the CME cycles are counted.'))
    add(S.p(
        f'The table below gives the core cycle count minus the CME cycle count per window. At the measured '
        f'{V.num(cpn, 3)} cycles per ns, 600 cycles are {V.num(600 / cpn, 0)} ns. '
        f'The same ratio converts the CME cycle count. In the rows of {V.num(D.clock["min_loads"], 0)} loads or '
        f'more the CME cycle count divided by the span time is '
        f'{span_of(D.clock[F1]["cme_lo"], D.clock[F1]["cme_hi"], 3, "cycles per ns")} on {BN[F1]} and '
        f'{span_of(D.clock[F2]["cme_lo"], D.clock[F2]["cme_hi"], 3, "cycles per ns")} on {BN[F2]}.'))
    short = {'ocm-64': 'OCM latency pass of 64 loads', 'ocm-320': 'OCM latency pass of 320 loads',
             'cme-call': 'cme-call rows'}
    rows = []
    for b in (F1, F2):
        rows.append(BT(b))
        for k in cg_keys:
            r = cg[(b, k)]
            w = ws[(b, k)]
            rows.append([short[k], r['calls_per_window'], r['n'], f'{V.num(r["lo"], 0)} to {V.num(r["hi"], 0)}',
                         V.num(r['median'], 0), n1(r['median_ns']), n1(w['core_bracket']), n1(w['bracket_cme']),
                         n1(w['cme_span'])])
    min_loads = D.clock['min_loads']
    add(S.table(
        ['Rows', 'Calls per<br>window', 'Rep<br>rows',
         'Core cycle count<br>minus CME cycle<br>count, cycles<br>(lowest to highest)',
         'Core cycle count<br>minus CME cycle<br>count, median,<br>cycles',
         'The same<br>median,<br>converted<br>to time, ns',
         'Core cycle count<br>as time minus<br>bracket time,<br>median, ns',
         'Bracket time<br>minus CME cycle<br>count as time,<br>median, ns',
         'CME cycle count<br>as time minus<br>span time,<br>median, ns'],
        rows,
        caption=f'Core cycle count minus CME cycle count per counting window, all rep rows. '
                f'Columns {code("cycles_per_load")} and {code("cme_cycles_per_load")}, times '
                f'{code("loads")}, of the OCM latency files {latref_ocm(F1)} {latref_ocm(F2)} and of the cme-call '
                f'rows {latref_call(F1)} {latref_call(F2)}. The last three columns compare the four totals of a '
                f'window as durations. A cycle count as time is the count divided by {V.num(cpn, 3)} cycles per '
                f'ns.',
        note=f'Rounding limits the precision of a difference that is calculated from a long row. The core column '
             f'prints 0.01 cycles per load. One printed step is {V.num(0.01 * min_loads, 2)} cycles per window at '
             f'{V.num(min_loads, 0)} loads and {V.num(0.01 * 65536, 2)} cycles per window at '
             f'{V.num(65536, 0)} loads. The table uses the short rows for a more precise comparison. '
             f'Each median is taken over the differences of the single rep rows. So the medians of two columns '
             f'do not add up exactly to the median of their sum. '
             f'The span time of a cme-call row is the sum of the spans of its 64 calls.',
        align='lrrrrrrrr'))
    wlo_, whi_ = min(ws[(F1, k)]['core_bracket'] for k in cg_keys), max(ws[(F1, k)]['core_bracket'] for k in cg_keys)
    clo_, chi_ = min(ws[(F1, k)]['bracket_cme'] for k in cg_keys), max(ws[(F1, k)]['bracket_cme'] for k in cg_keys)
    wc = ws[(F1, 'cme-call')]
    add(S.bullets([
        f'The difference of the two counts is the same per window with 1 call or with 64 calls: a median of '
        f'{V.num(cg[(F1, "ocm-64")]["median"], 0)} and {V.num(cg[(F1, "cme-call")]["median"], 0)} cycles on '
        f'{BN[F1]}. Converted to time, the medians of the {nword(len(cg_keys))} kinds of row are '
        f'{n1(cg[(F1, "ocm-64")]["median_ns"])} ns to {n1(cg[(F1, "ocm-320")]["median_ns"])} ns ({BS[F1]}).',
        f'In a window of a cme-call row the CME cycle count, converted to time, is a median of '
        f'{n1(wc["cme_span"])} ns above the sum of the 64 spans ({BS[F1]}). The outside-span time of those 64 '
        f'calls is a median of {n1(b2b[F1]["median"] * 64)} ns. '
        f'The conversion uses {V.num(cpn, 3)} cycles per ns, the ratio that the long rows measure '
        f'({S.xref("setup-clock")}). At that ratio the CME cycle counter also counts outside the spans of '
        f'calls that follow each other.',
        f'The difference of the two counts is taken against the core cycle count. The core cycle count, '
        f'converted to time, is above the bracket time by a median of {span_of(wlo_, whi_)} ({BS[F1]}).',
        f'The bracket time is above the CME cycle count, converted to time, by a median of '
        f'{span_of(clo_, chi_)} ({BS[F1]}).',
        f'That amount is {n1(lone[F1]["median"] - chi_)} to {n1(lone[F1]["median"] - clo_)} ns below '
        f'the {n1(lone[F1]["median"])} ns of outside-span time of a lone call (bracket time minus span time). '
        f'On a lone OCM pass of 64 loads the CME cycle count, converted to time, is a median of '
        f'{n1(w64[F1]["cme_span"])} ns above the span time ({BS[F1]}).',
    ]))
    add(S.insufficient(
        'The rows give totals. They give no time stamp of the counter start, of the counter stop, or of the '
        'first and the last cycle that the CME cycle counter counts. A timer read beside the counter start and '
        'beside the counter stop would place the core cycle count against the bracket. A counting window with '
        'no kernel call in it, with both cycle counts printed, would show whether the CME cycle counter counts '
        'outside a call.'))
    add(S.p(f'What the gap means is not measured. {S.xref("open-call", cap=True)} gives three readings of it as '
            f'hypotheses (the clock of the CME does not run before the first call of a window, the CME leaves a '
            f'low-power state, or the two counters do not start at the same instant), each with the measurement '
            f'that would confirm or reject it.'))

    # ================================================ 7.7 the looped write
    add(S.h3('callcost-write', 'The looped write: a span rate above the single-call rate'))
    L8 = V.size_label(D.l1_sizes[i8])
    ratio8 = {b: lw[b]['span_gbps'][i8] / swf[b]['gbps'][i8] for b in (F1, F2)}
    lvs_w = {b: {r['size']: r for r in D.looped_vs_single if r['boot'] == b and r['kernel'] == 'write'}
             for b in (F1, F2)}
    big = D.l1_sizes[2:]                                   # 16 KiB and 24 KiB
    big_txt = _join(V.size_label(s) for s in big)
    dbig = {b: [lvs_w[b][s]['diff_ns'] for s in big] for b in (F1, F2)}
    dbig_max = max(abs(v) for b in (F1, F2) for v in dbig[b])
    sgn_rng = lambda vs: '%s to %s ns' % (V.signed(min(vs), 1), V.signed(max(vs), 1))
    lead = [
        f'At {L8} the span rate of a looped write call is {V.gbps(lw[F1]["span_gbps"][i8])} on {BN[F1]}. '
        f'The single-call form writes {V.gbps(swf[F1]["gbps"][i8])} at the same footprint. '
        f'The span rate is {V.ratio(ratio8[F1])} the single-call rate.',
        f'At {big_txt} a looped write pass takes the bracket time of a single-call pass within '
        f'{n1(dbig_max)} ns ({sgn_rng(dbig[F1])} on {BS[F1]}, {sgn_rng(dbig[F2])} on {BS[F2]}), although it makes '
        f'one call per pass.',
    ]
    if lw_v.count('void') == len(lw_v):
        lead.append(f'The {nword(len(D.l1_sizes))} points do not lie on a line. The plan rule voids every looped '
                    f'write fit.')
    add(S.bullets(lead))
    hrows = []
    for i, sz in enumerate(D.l1_sizes):
        hrows.append(dict(header=f'{V.size_label(sz)} per pass'))
        for lab, fr, key in (('looped form, span rate', lw, 'span_gbps'),
                             ('looped form with DSB ST, span rate', dw, 'span_gbps'),
                             ('single-call form, bracket rate', swf, 'gbps')):
            notes = None
            if key == 'span_gbps' and fr is lw:
                notes = [f'= {V.ratio(lw[F2]["span_gbps"][i] / swf[F2]["gbps"][i])} single-call',
                         f'= {V.ratio(lw[F1]["span_gbps"][i] / swf[F1]["gbps"][i])} single-call']
            d = dict(label=lab, values=[fr[F2][key][i], fr[F1][key][i]],
                     tips=[f'{V.size_label(sz)} per pass: {lab} - {BN[b]}\n{V.gbps(fr[b][key][i])}'
                           for b in (F2, F1)])
            if notes:
                d['notes'] = notes
            hrows.append(d)
    sc_all = swf[F1]['gbps'] + swf[F2]['gbps']
    sc_ref = min(sc_all)
    svg = V.hbar(hrows, series=[(BN[F2], 'f2'), (BN[F1], 'f1')], unit='GB/s', fmt=n1,
                 refs=[(sc_ref, f'single-call form, lowest rate {V.gbps(sc_ref)}')],
                 xlabel='write rate, GB/s', label_w=250, title='write rates of the three L1 write forms')
    n_above = sum(1 for b in (F1, F2) for i in range(len(D.l1_sizes)) if lw[b]['span_gbps'][i] > swf[b]['gbps'][i])
    n_cmp = 2 * len(D.l1_sizes)
    dsb_big = dw[F1]['span_gbps'][2:]
    dsb_dev = max(abs(a - c) for a, c in zip(dsb_big, swf[F1]['gbps'][2:]))
    add(S.fig(
        svg,
        f'Write rate at {l1_rng}, best reps, both boots: the span rate of the looped form '
        f'({code(lw[F1]["src"])} {bwref(F1, lw[F1]["src"])} {bwref(F2, lw[F2]["src"])}), the span rate of the '
        f'looped form with DSB ST ({code(dw[F1]["src"])} {bwref(F1, dw[F1]["src"])} {bwref(F2, dw[F2]["src"])}) '
        f'and the bracket rate of the single-call form ({code(swf[F1]["src"])} {bwref(F1, swf[F1]["src"])} '
        f'{bwref(F2, swf[F2]["src"])}). All rows run the write kernel (CSV name {code("cme-write")}). The text after the first '
        f'bar pair of each group gives the looped span rate as a multiple of the single-call rate. The grey line '
        f'marks the lowest single-call rate of the {n_cmp} bars of that form.',
        f'The single-call rate is {span_of(min(swf[F1]["gbps"]), max(swf[F1]["gbps"]), 1, "GB/s")} at the '
        f'{nword(len(D.l1_sizes))} footprints ({BS[F1]}). The looped span rate is above it at '
        f'{"every footprint on both boots" if n_above == n_cmp else "%d of the %d bar pairs" % (n_above, n_cmp)}. '
        f'With DSB ST the span rate at {big_txt} is '
        f'{span_of(min(dsb_big), max(dsb_big), 1, "GB/s")} ({BS[F1]}). That is within {n1(dsb_dev)} GB/s of the '
        f'single-call rate at the same footprint.'))
    rows = []
    for b in (F1, F2):
        rows.append(BT(b))
        dd = {r['size']: r for r in D.l1_diffs if r['boot'] == b}
        for i, sz in enumerate(D.l1_sizes):
            rows.append([nowrap(V.size_label(sz)), n2(lw[b]['ns_bracket'][i]), n2(lw[b]['ns_span'][i]),
                         n2(swf[b]['ns_bracket'][i]), V.signed(lvs_w[b][sz]['diff_ns'], 2),
                         n2(dw[b]['ns_bracket'][i]), V.signed(dd[sz]['dsb_ns'], 2),
                         n1(lw[b]['span_gbps'][i]), n1(dw[b]['span_gbps'][i]), n1(swf[b]['gbps'][i])])
    add(S.table(
        ['Bytes per pass', 'Looped,<br>bracket ns', 'Looped,<br>span ns', 'Single-call,<br>bracket ns',
         'Looped minus<br>single-call, ns', 'DSB ST,<br>bracket ns', 'DSB ST minus<br>looped, ns',
         'Looped span<br>rate, GB/s', 'DSB ST span<br>rate, GB/s', 'Single-call<br>rate, GB/s'],
        rows,
        caption='The three write forms, per pass, best reps. The files are those of Figure %d.' % S.n_fig,
        note=' '.join(two_level_note) or None,
        align='lrrrrrrrrr'))
    out_lw = {b: D.l1_form(b, 'looped', 'write')['outside'] for b in (F1, F2)}
    dsb_f1 = {r['size']: r['dsb_ns'] for r in D.l1_diffs if r['boot'] == F1}
    dsb_big_ns = [dsb_f1[s] for s in big]
    lw_out_all = [x['outside_ns_per_call'] for row in lw[F1]['rows'] if row['size'] in big for x in row['reps']]
    add(S.bullets([
        f'At {L0} the looped pass takes {n1(lvs_w[F1][sz0]["diff_ns"])} ns more than the single-call pass on '
        f'{BN[F1]} ({n1(lvs_w[F2][sz0]["diff_ns"])} ns on {BS[F2]}).',
        f'At {L8} the difference is {n1(lvs_w[F1][D.l1_sizes[i8]]["diff_ns"])} ns. At {big_txt} it is '
        f'{sgn_rng(dbig[F1])} ({BS[F1]}).',
        f'Each of those looped calls still spends {span_of(min(out_lw[F1]), max(out_lw[F1]))} outside its span '
        f'(best reps, {BS[F1]}).',
        f'With DSB ST the pass takes '
        f'{_join(n1(dsb_f1[s]) for s in D.l1_sizes)} ns longer at {l1_list} on '
        f'{BN[F1]}. The outside-span time of one looped write call at {big_txt} is '
        f'{span_of(min(lw_out_all), max(lw_out_all))} over all reps.',
    ]))
    add(S.hyp(
        'The span of a write call ends before its stores are complete. The last stores of a call finish while the '
        'call leaves streaming mode and the next call enters it. So the cost of the call overlaps with store work, '
        'and the span is shorter than the store work it started. The DSB ST rows are consistent with this reading. '
        f'They do not prove it. The barrier adds {span_of(min(dsb_big_ns), max(dsb_big_ns))} at {big_txt} '
        f'({BS[F1]}), but the rows do not show that this time is the wait for the stores of the call {r_plan}.',
        'A waveform of the store interface of the CME over one 8 KiB call would show when the last store completes '
        'against the second stamp. The run plan names no row that could identify the mechanism from timing '
        f'alone {r_plan}.'))
    add(S.p(f'{S.xref("open-looped", cap=True)} lists the measurements that would settle this.'))

    # ====================================== 7.8 what can be quoted, and what cannot
    add(S.h3('callcost-quote', 'What can be quoted, and what cannot'))
    add(S.bullets([
        'Quote a time per call only together with its form, its footprint, its boot and its clock.',
        'Do not quote a fixed cost per call for writes. Do not quote any number as the cost of SMSTART and '
        'SMSTOP alone.',
        f'{S.xref("glance-noquote", cap=True)} lists the numbers of the whole page that are not to be quoted. '
        f'{S.xref("open-claims", cap=True)} lists the statements that the rows do not support.',
    ]))
    can = []
    if fit_b[F1]['verdict'] == 'pass' and fit_s[F1]['verdict'] == 'pass':
        can.append([f'Fixed time of one looped read call, {BN[F1]}',
                    f'{n1(fit_b[F1]["intercept_ns"])} ns est. by the bracket, {n1(fit_s[F1]["intercept_ns"])} ns '
                    f'est. of it inside the span',
                    f'Both fits pass the plan rule. Includes the fold, the two stamps and their bookkeeping. '
                    f'{l1_rng}. Say "looped read call on {BS[F1]}". It is not the cost of a call in general: a '
                    f'call with one register step takes {call_br_txt}.'])
    for b in (F1, F2):
        if fit_s[b]['verdict'] == 'pass' and fit_b[b]['verdict'] == 'void':
            can.append([f'Fixed span time of one looped read call, {BN[b]}', f'{n1(fit_s[b]["intercept_ns"])} ns est.',
                        'The span fit passes. The bracket fit of this boot is void.'])
    can += [
        [f'Outside-span time of looped calls that follow each other, {l1_rng}',
         f'{span_of(lsm[F1]["lo"], lsm[F1]["hi"])} ({BS[F1]}), {span_of(lsm[F2]["lo"], lsm[F2]["hi"])} ({BS[F2]})',
         f'All {lsm[F1]["n"]} reps of the three looped L1 files per boot. It is a range, not a constant.'],
        [f'A {V.size_label(cc_r_sizes[0])} read call and a {V.size_label(wlo)} write call',
         f'{n1(cr1[F1]["bracket_ns"])} ns and {n1(cw1[F1]["bracket_ns"])} ns ({BS[F1]})',
         'Bracket time per call, looped form, best rep.'],
        ['A call with one register step (cme-call rows)',
         f'{call_br_txt}, span {span_txt}',
         f'{bs["all"]["n_files"]} files over both boots, 64 calls that follow each other.'],
        ['Outside-span time of a call of loads alone in its bracket',
         both(lone[F1]["median"], lone[F2]["median"]),
         f'Calls of loads only. Median of the OCM latency passes of 64 loads. A lone write call spends '
         f'{span_of(slw[F1]["lo"], slw[F1]["hi"])} ({BS[F1]}). The cause of the extra time over calls that follow each other is '
         f'a hypothesis.'],
        [f'Write rate of the single-call form at {l1_rng}',
         f'{span_of(min(swf[F1]["gbps"]), max(swf[F1]["gbps"]), 1, "GB/s")} ({BS[F1]}), '
         f'{span_of(min(swf[F2]["gbps"]), max(swf[F2]["gbps"]), 1, "GB/s")} ({BS[F2]})',
         f'Bracket rate, best reps. The fitted line gives {fitq(sw[F1], "rate_gbps")} GB/s est. and '
         f'{fitq(sw[F2], "rate_gbps")} GB/s est. {nof(sw_v.count("pass"), len(sw_v), "fits")} of this form pass.'],
    ]
    add(S.table(['Can be quoted', 'Value', 'Conditions to state with it'], can,
                caption='Statements that the rows of this section support.', align='lll'))

    def void_why(ft):
        return (f'the largest residual is {n1(ft["max_res_pct"])} % of the smallest pass time '
                f'({n1(ft["max_res_ns"])} ns at {V.size_label(ft["max_res_size"])})')

    cannot = [
        ['"A CME call costs %s ns."' % fitq(fit_b[F1], 'intercept_ns', 0),
         f'That number is the fitted intercept of one kind of call: the looped read on {BN[F1]}, by the bracket. '
         f'It includes the fold and the stamps. With these conditions it can be quoted (table above). '
         f'A call of a cme-call row takes {call_br_txt} and a {V.size_label(wlo)} write call '
         f'{n1(cw1[F1]["bracket_ns"])} ns.'],
        ['"SMSTART and SMSTOP cost N ns."',
         'No row isolates the two instructions. The outside-span time also holds the call, the return, the '
         'register save and restore, and the bookkeeping of the second stamp (the store of the stamp and the add '
         'of the span to the running sum).'],
    ]
    for form, kern, title in (('looped', 'write', 'The intercept or the rate of the looped write fits'),
                              ('single-call', 'read', 'The fitted rate of the single-call read'),
                              ('looped', 'read', None),
                              ('looped, DSB ST', 'write', 'The intercepts of the DSB ST write')):
        for b in (F1, F2):
            vb = [D.l1_fit(b, form, kern, c) for c in ('bracket', 'span')]
            voids = [ft for ft in vb if ft['verdict'] == 'void']
            if not voids:
                continue
            if title is None:                      # looped read: name the void fit of each boot
                for ft in voids:
                    cannot.append([f'The {ft["clock"]} intercept of the looped read on {BN[b]}',
                                   'Void: ' + void_why(ft) + '.'])
                continue
            if b == F2 and any(D.l1_fit(F1, form, kern, c)['verdict'] == 'void' for c in ('bracket', 'span')):
                continue                           # one row per form: boot F1 carries the numbers
            why = 'Void. ' + ' '.join(f'{cap(ft["clock"])} clock, {BS[b]}: {void_why(ft)}.' for ft in voids)
            if form == 'single-call':
                ft = voids[0]
                why += (f' The residuals of the {ft["clock"]} fit are '
                        f'{_join(V.signed(r, 1) for r in ft["res"])} ns at {l1_list}. Quote the measured rates of '
                        f'{S.xref("bw-read")}.')
            nv = verdicts(form, kern).count('void')
            why += f' {nof(nv, 4, "fits")} of this form are void over both boots.'
            cannot.append([title, why])
    cannot += [
        ['The span rate of a looped write as a store rate',
         f'It is up to {V.gbps(max(lw[F1]["span_gbps"]))} at {l1_rng}. The single-call form writes '
         f'{span_of(min(swf[F1]["gbps"]), max(swf[F1]["gbps"]), 1, "GB/s")} at the same footprints ({BS[F1]}).'],
        ['"The span does not wait for the stores" as a fact', 'It is a hypothesis. No row shows the mechanism.'],
        ['"The looped write has no call cost."',
         f'At {L0} a looped write pass takes {n1(lvs_w[F1][sz0]["diff_ns"])} ns more than a single-call pass '
         f'({BS[F1]}). Every looped write call still spends its outside-span time.'],
        ['"The CME takes N ns to wake up."',
         f'A lone call spends {n1(oc[F1]["extra_alone_ns"])} ns more outside its span than a cme-call call '
         f'({BS[F1]}). {n1(clock_share[F1])} ns est. of that is clock-read time. The other {n1(extra_net[F1])} ns '
         f'est. is not separated from other costs of a first call.'],
        ['A looped rate at a small footprint as the L1 rate of the CME',
         f'At {L0} the looped read gives {V.gbps(lr[F1]["gbps"][0])} and the single-call read '
         f'{V.gbps(sr[F1]["gbps"][0])} ({BS[F1]}).'],
    ]
    add(S.table(['Cannot be quoted', 'Why'], cannot,
                caption='Statements that the rows of this section do not support.', align='ll'))
    add(S.insufficient(
        'The share of the two stamps in every time per call of this section is not measured. A caller without '
        'stamps spends less time per call. The same rows on a build with the stamps compiled out would give the amount.'))
    return ''.join(out)
