"""Section 'open': open items, what the two boots do not measure, and
statements the data do not support.

Every measured number is read from the data layer D at build time.  Two
values are computed here because D does not hold them:
  _address_order()   the one permitted row from a third boot (own small parser)
  _source_fit()      the inner / outer refill cost fit (boot F2, 8 KiB to 384 KiB)

Figures and tables that another section owns are not repeated here: the
subsection links to that section with S.xref.
"""
import collections
import os
import re

from . import data

KEY = 'open'
TITLE = 'Open items and what was not measured'

K = data.KIB
M = data.MIB
F1N = 'boot F1 (prefetchers on)'
F2N = 'boot F2 (prefetchers off)'
BOOTS = ('F1', 'F2')

# Facts that exist only in the operator's README (typed, cited where used).
CME_L1_BYTES = 64 * K            # size of the CME L1
SLC_BYTES = 5 * M                # five home nodes of 1 MiB
SLC_WAYS, SLC_OCM_WAYS = 16, 4   # ways per home node, ways locked for the OCM
CME_TLB_ENTRIES = 24

ADDR_REL = os.path.join('results', 'membench-jibin-010', 'results', 'bootE', 'cme-latency-dram-seq.csv')


# ------------------------------------------------------------ own computations

def _address_order():
    """Parses the address-order file of the third boot.  Returns the conditions of its
    header line, the round-trip baseline and the best 8 MiB row with its counters."""
    path = os.path.join(data.ROOT, ADDR_REL)
    out = {'src': ADDR_REL, 'name': os.path.basename(ADDR_REL), 'reps': []}
    cols = None
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip('\n')
            if line.startswith('# latency:'):
                out['header'] = dict(re.findall(r'(\w+)=(\S+)', line))
                out['header_line'] = n
            elif line.startswith('# size='):
                out['size_line'] = dict(re.findall(r'(\w+)=(\S+)', line))
            elif line.startswith('mem,'):
                cols = line.split(',')
            elif line and not line.startswith('#'):
                c = line.split(',')
                if c[2] == 'cme-roundtrip-best':
                    out['rt'] = float(c[5])
                elif c[2] == 'cme-best':
                    out['best'], out['best_line'] = float(c[5]), n
                elif c[2].startswith('cme-fresh'):
                    row = dict(zip(cols, c))
                    row['_line'] = n
                    out['reps'].append(row)
    rep = [r for r in out['reps'] if float(r['ns_per_load']) == out['best']][0]
    out['rep_line'] = rep['_line']
    out['size'] = int(rep['size_bytes'])
    out['loads'] = int(rep['loads'])
    out['hwprf'] = float(rep['cme_l1d_refill_hwprf_per_load'])
    out['outer'] = float(rep['cme_l1d_refill_outer_per_load'])
    out['inner'] = float(rep['cme_l1d_refill_inner_per_load'])
    out['rd'] = float(rep['cme_l1d_refill_rd_per_load'])
    out['rd_txt'] = rep['cme_l1d_refill_rd_per_load']
    # read refills per timed pass: the printed count per load times the loads of the pass.
    # The file prints the count per load rounded, so the product is rounded to the nearest event.
    ev = [float(r['cme_l1d_refill_rd_per_load']) * int(r['loads']) for r in out['reps']]
    assert all(abs(x - round(x)) < 0.01 for x in ev), 'read refills per pass are not near a whole number'
    assert len({round(x) for x in ev}) == 1 and len({int(r['loads']) for r in out['reps']}) == 1
    out['rd_events'] = int(round(ev[0]))
    out['n_passes'] = len(out['reps'])
    out['above_rt'] = out['best'] - out['rt']
    return out


def _source_fit(D, boot):
    """ns per load minus the 4 KiB best row = inner x b + outer x c, over the rep rows
    of the chains walked many times from 8 KiB to 384 KiB."""
    rows = [r for r in D.chain[boot] if r['src'] == 'cme-latency-dram-small.csv']
    base = [r for r in rows if r['size'] == 4 * K][0]['best']
    A, y, ns = [], [], []
    for r in rows:
        if r['size'] < 8 * K:
            continue
        for rep in r['reps']:
            A.append([rep['inner'], rep['outer']])
            y.append(rep['ns'] - base)
            ns.append(rep['ns'])
    fit = data.lstsq(A, y)
    return {'n': len(y), 'base': base, 'inner': fit['coef'][0], 'outer': fit['coef'][1],
            'cond': fit['cond_unit'],
            'max_pct': max(abs(e) / v for e, v in zip(fit['res'], ns)) * 100.0}


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _rng(lo, hi, d=1, unit=''):
    u = (' ' + unit) if unit else ''
    return f'{lo:.{d}f} to {hi:.{d}f}{u}'


# ------------------------------------------------------------ the section

def build(D, V, S):
    code = lambda t: '<code>%s</code>' % t
    BN = {'F1': 'Boot F1 (prefetchers on)', 'F2': 'Boot F2 (prefetchers off)'}
    bootdir = {b: os.path.relpath(data.BOOTDIR[b], data.ROOT) for b in BOOTS}

    def fref(name, boots=BOOTS):
        """<code>name</code> [RefN]: the file in the folder of each named boot."""
        where = ' and '.join('%s (boot %s)' % (code(bootdir[b] + '/' + name), b) for b in boots)
        return '%s %s' % (code(name), S.ref('file:%s:%s' % (name, '+'.join(boots)), 'File %s.' % where))

    # ---- references used in several places
    def r_plan13():
        return S.ref('plan-13', 'Run plan %s, section 13 (lines 251 to 279): the fit rule "a residual over 2 %% of '
                     'the smallest pass time voids that intercept" (line 271), the statement that a store span does '
                     'not wait for the stores unless the kernel ends with DSB ST (line 269), the exploratory status '
                     'of the L3 events (line 267), and "What stays open, by choice" (line 278).'
                     % code('follow-up-run-plan.md'))

    def r_readme1(what='sections "CME rows", "The memory model behind the home node" and "Platform facts"'):
        return S.ref('readme-f1', "Operator's README of boot F1, %s, %s." % (
            code('results/membench-jibin-011/README.md'), what))

    def r_readme2():
        return S.ref('readme-f2', "Operator's README of boot F2, %s, sections \"The prefetchers\", \"CME rows against "
                     "boot F1: the prefetchers off\" (the list of what differs between the two boots, lines 65 to 73), "
                     "\"The CME L3 events\" and \"OCM mappings\"." % code('results/membench-jibin-012/README.md'))

    def r_bwc():
        return S.ref('bandwidth-c-open', 'Source file %s: line 519 (the counter option <code>--perf</code> is refused '
                     'together with <code>--cme</code>), line 545 (<code>--cme</code> takes one worker, because the '
                     'two span counter reads are one global pair), lines 314 to 323 (one kernel call per OCM region).'
                     % code('bandwidth.c'))

    def r_commonh():
        return S.ref('common-h-l3', 'Source file %s, lines 436 to 447: the three CME L3 events are collected as '
                     'exploratory counts, and no fit or attribution reads them until a control validates them.'
                     % code('common.h'))

    def r_log():
        return S.ref('log-cme', 'Command logs %s (boot F1, lines 85 to 156) and %s (boot F2, lines 4 to 75).' % (
            code(bootdir['F1'] + '/log.txt'), code(bootdir['F2'] + '/log.txt')))

    def r_latc():
        return S.ref('src:latency.c', 'Source file %s: lines 207 to 216 (after each timed rep come the counter '
                     'stop, the counter read and the print of the row), lines 241 to 242 (two walks that are not '
                     'timed run before the first rep).' % code('latency.c'))

    def r_bwrep():
        return S.ref('src:bandwidth-rep', 'Source file %s, lines 417 to 437: each rep runs one warm-up pass that '
                     'is not timed (line 421), waits at the thread barrier (line 424) and then times its passes. '
                     'No counter call lies between two passes.' % code('bandwidth.c'))

    def r_runcme():
        return S.ref('src:run_cme', 'Script %s, lines 10 to 11 and line 31: CPU 3 is taken offline before the '
                     'first CME command.' % code('run_cme.sh'))

    def r_sysinfo_l3():
        return S.ref('sysinfo:F1:caches', 'System listing %s of boot F1: the cache sizes that Linux reports for CPU 2.'
                     % code(bootdir['F1'] + '/sysinfo.txt'))

    def r_cmeplan():
        return S.ref('cme-plan', 'Test plan %s, section 2.3 (line 206: no row with two cores or with several CMEs) '
                     'and section 6 (line 454: no row isolates the cause of the store rate).' % code('CME-plan.md'))

    # ---- terms
    for name, d in [
        ('CME', 'the Arm C1-SME2 matrix engine unit. Each cluster has one, and the two cores of the cluster share it'),
        ('streaming mode', 'the processor mode in which the CME executes the vector instructions. '
                           'The instruction SMSTART enters it and SMSTOP leaves it'),
        ('kernel', 'the test loop in the assembly file <code>cme_kern.S</code>. It does not mean the Linux kernel'),
        ('pass', 'one walk over the buffer or over the chain'),
        ('rep', 'one timed measurement. A rep holds one or more passes'),
        ('looped form', 'a bandwidth row that makes one kernel call per pass'),
        ('single-call form', 'a bandwidth row that runs all passes of a rep in one assembly call'),
        ('bracket time', 'the time between two clock reads in C around the kernel call or calls'),
        ('span time', 'the time between the two counter reads inside the kernel, after SMSTART and before SMSTOP'),
        ('outside-span time', 'bracket time minus span time'),
        ('latency test', 'the loop that follows a chain of addresses. Each load reads the address of the next load'),
        ('chain load', 'one dependent load of the latency test. Its unit is ns per load'),
        ('round-trip baseline', 'the DUP+LASTB row (<code>cme-roundtrip</code>). A value goes from the core to the '
                                'CME and back with no memory access'),
        ('counting window', 'the interval between the counter start and the counter stop of one latency row. '
                            'In the code the counter start comes before the first clock read of the bracket, '
                            'and the counter stop comes after the second clock read'),
        ('inner refill, outer refill', 'a CME L1 refill from inside the cluster (event 0x327D) and from outside the '
                                       'cluster (event 0x327E)'),
        ('prefetch refill', 'a CME L1 refill that the hardware prefetcher of the CME requested (event 0x32B2)'),
        ('L3 events', 'three CME events: 0x328E (L3 hit), 0x328F (L3 miss) and 0x3290 (L3 refill). '
                      'No control row validates them'),
        ('plan rule', 'the fit rule of the run plan. The intercept of a fit is void when the largest residual is '
                      'over 2 % of the smallest pass time'),
        ('fold', 'the XOR of all loaded words into one value'),
        ('DSB ST', 'a barrier instruction that waits until the stores before it have completed'),
        ('OCM', 'on-chip memory: five regions of 256 KiB, one in each home node of the mesh'),
        ('SLC', 'the system-level cache: the cache in the home nodes of the mesh, outside the cluster'),
        ('home node', 'a node of the mesh that holds a part of the SLC and one OCM region'),
        ('mesh', 'the 6 x 6 grid of crosspoints that connects the clusters, the home nodes and the memory'),
        ('mesh counters', 'counters of the mesh. They count the requests that each home node receives during one '
                          'whole command'),
        ('DRAM model', 'the memory model of the emulator behind the home nodes. It is not silicon timing'),
        ('snoop', 'a request to another cache in the cluster for a line it holds'),
        ('GB/s', '1e9 bytes per second. 1 GB/s equals 1 byte per ns'),
        ('est.', 'marks an estimate: a value derived with an assumption, not read from one row'),
        ('TLB', 'translation lookaside buffer: the cache of address translations'),
        ('ZA array', 'the matrix register of the SME instruction set'),
        ('RTL', 'register transfer level: the hardware source code of the chip'),
        ('cme-call row', 'a latency row that times 64 kernel calls in one bracket, each call directly after the one before it. Each call runs '
                         'one register step'),
        ('lone call', 'a kernel call that stands alone in its bracket'),
        ('stamp', 'one read of the timer register inside a kernel. Each kernel call takes two stamps'),
        ('best row', 'the row the test program marks as best: the lowest ns per load of a latency footprint, '
                     'or the highest bracket rate of a bandwidth row'),
    ]:
        S.term(name, d)

    cpn = D.clock['cycles_per_ns']
    l3_bytes = [c for c in D.platform['caches'] if c['level'] == 3][0]['size_bytes']
    slc_est = SLC_BYTES * (SLC_WAYS - SLC_OCM_WAYS) / SLC_WAYS
    L1SZ = V.size_label(CME_L1_BYTES)
    many, once, flushed = 'walked many times', 'walked once', 'every line flushed first'

    def labels(sizes):
        """'4 KiB, 8 KiB and 16 KiB' for a list of sizes."""
        ls = [V.size_label(s) for s in sizes]
        return ls[0] if len(ls) == 1 else ', '.join(ls[:-1]) + ' and ' + ls[-1]

    def span_lab(sizes):
        """'4 KiB to 64 KiB': the lowest and the highest size of a list."""
        return '%s to %s' % (V.size_label(min(sizes)), V.size_label(max(sizes)))

    # ================================================================ data used by the overview
    wsweep = {b: {r['size']: r for r in D.bw_table('sweep', b, 'write')} for b in BOOTS}
    sizes_w = sorted(wsweep['F1'])
    assert sizes_w == sorted(wsweep['F2'])
    # the write step: the pair of neighbouring footprints with the lowest rate ratio
    stp = {b: min((wsweep[b][hi]['best'] / wsweep[b][lo]['best'], lo, hi) for lo, hi in zip(sizes_w, sizes_w[1:]))
           for b in BOOTS}
    assert stp['F1'][1:] == stp['F2'][1:], 'the write rate steps at another footprint on each boot'
    s_lo, s_hi = stp['F1'][1:]
    SLO, SHI = V.size_label(s_lo), V.size_label(s_hi)
    w_ratio = {b: stp[b][0] for b in BOOTS}
    w_small = [r['best'] for b in BOOTS for r in wsweep[b].values() if r['size'] <= s_lo]
    w_large = [r['best'] for b in BOOTS for r in wsweep[b].values() if r['size'] >= s_hi]
    W_SMALL = span_lab([s for s in sizes_w if s <= s_lo])
    W_LARGE = span_lab([s for s in sizes_w if s >= s_hi])
    svl = {r['boot']: r for r in D.store_vs_load}
    assert svl['F1']['size'] == svl['F2']['size']
    SVL = V.size_label(svl['F1']['size'])
    lw = {b: D.l1_form(b, 'looped', 'write') for b in BOOTS}
    sw = {b: D.l1_form(b, 'single-call', 'write') for b in BOOTS}
    lw_peak = {b: max(lw[b]['span_gbps']) for b in BOOTS}
    lw_peak_size = {b: lw[b]['sizes'][lw[b]['span_gbps'].index(lw_peak[b])] for b in BOOTS}
    sw_all = sw['F1']['span_gbps'] + sw['F2']['span_gbps']
    oc = D.outside_check
    osp = {(r['boot'], r['key']): r for r in D.outside_span}
    rps = D.refills_per_line_summary
    steps = {s['series']: s for s in D.chain_steps['steps']}
    st1, st2, stc = steps['CME on boot F1'], steps['CME on boot F2'], steps['core on boot F1']
    assert (st1['from_size'], st1['to_size']) == (st2['from_size'], st2['to_size'])
    ST_FROM, ST_TO = V.size_label(st1['from_size']), V.size_label(st1['to_size'])
    pairs = {(p['size'], p['kind']): p for p in D.chain_pairs}
    l1_pairs = [p for p in D.chain_pairs if p['kind'] == many and p['size'] <= CME_L1_BYTES]
    worst_l1 = max(l1_pairs, key=lambda p: p['f1_minus_f2'])
    pfl = [p for p in D.chain_pairs if p['kind'] == flushed][0]
    l3r = {b: {r['size']: r for r in D.chain_l3[b]} for b in BOOTS}
    f2c = {(r['size'], r['kind']): r for r in D.chain['F2']}
    lg = {b: [r for r in D.chain_sweep(b) if r['kind'] == once] for b in BOOTS}
    # the flat part of the boot F2 line outside the cluster: from 1 MiB up, within 5 % of the 1 MiB row
    after = [r for r in lg['F2'] if r['size'] >= M]
    flat = []
    for r in after:
        if r['best'] > 1.05 * after[0]['best']:
            break
        flat.append(r)
    rise = after[len(flat)]
    flat_lo, flat_hi, top = flat[0], flat[-1], after[-1]
    # the row with the lowest chain load above the CME L1 on boot F2, and its L3-event twin
    cl_best = min((r for r in D.chain['F2'] if r['kind'] == many and r['size'] > CME_L1_BYTES),
                  key=lambda r: r['best'])
    hit_peak = l3r['F2'][cl_best['size']]
    ao = _address_order()
    assert D.address_order is None or abs(D.address_order['best'] - ao['best']) < 1e-9
    bs = D.baseline_summary['all']
    loop_keys = ('looped-l1', 'looped-sweep-small', 'looped-sweep-large')
    loop_lo = min(osp[(b, k)]['lo'] for b in BOOTS for k in loop_keys)
    loop_hi = max(osp[(b, k)]['hi'] for b in BOOTS for k in loop_keys)

    out = []
    A = out.append
    nh = {}                      # heading id -> number of Hypothesis blocks (filled by block())

    # ================================================================ overview
    A(S.takeaways([
        '@@NOPEN@@ observations on boot F1 (prefetchers on) and boot F2 (prefetchers off) have no measured cause.',
        f'The first one is a step of the {S.term("CME", "")} write rate. It reads '
        f'{_rng(min(w_small), max(w_small), 1, "GB/s")} from {W_SMALL} and '
        f'{_rng(min(w_large), max(w_large), 1, "GB/s")} from {W_LARGE}.',
        f'@@NNOT@@ kinds of row do not exist on these boots ({S.xref("open-not")}).',
    ]))
    link = lambda id_, text: '<a href="#%s">%s</a>' % (id_, text)
    T_WRITE = f'The write rate steps down between {SLO} and {SHI}'
    T_STORE = 'The read loop transfers more bytes per cycle than the write loop'
    T_LOOPED = 'The looped write reads faster in its span than the single-call write'
    T_CALL = 'The fixed cost of a call, and the extra time of a call alone in its bracket'
    T_REFILL = 'Every rep counts about one inner refill per line of the chain, also when the chain fits in the CME L1'
    T_L3 = 'What the L3 events count'
    T_STEP = f'The chain load on boot F1 falls between {ST_FROM} and {ST_TO}'
    T_BOOTS = 'Differences between boot F1 and boot F2 whose mechanism is not measured'
    T_OUTSIDE = 'Which level outside the cluster serves a load'
    ST_SOME, ST_NONE, ST_CTRL = 'hypotheses, some rows', 'hypotheses, no row', 'no control row'
    assert svl['F1']['ratio'] > 2 and svl['F2']['ratio'] > 2
    open_items = [
        [link('open-write', T_WRITE),
         f'{wsweep["F1"][s_lo]["best"]:.1f} GB/s at {SLO}, {wsweep["F1"][s_hi]["best"]:.1f} GB/s at {SHI} '
         f'({w_ratio["F1"]:.2f} times) on boot F1. {w_ratio["F2"]:.2f} times on boot F2',
         ST_NONE, '@@H:open-write@@'],
        [link('open-store', T_STORE),
         f'read throughput divided by write throughput: {svl["F1"]["ratio"]:.2f} on boot F1, '
         f'{svl["F2"]["ratio"]:.2f} on boot F2',
         ST_NONE, '@@H:open-store@@'],
        [link('open-looped', T_LOOPED),
         f'up to {lw_peak["F1"]:.1f} GB/s at {V.size_label(lw_peak_size["F1"])} against '
         f'{_rng(min(sw["F1"]["span_gbps"]), max(sw["F1"]["span_gbps"]), 1, "GB/s")} (boot F1)',
         ST_SOME, '@@H:open-looped@@'],
        [link('open-call', T_CALL),
         f'{_rng(bs["call_outside_lo"], bs["call_outside_hi"], 1, "ns")} per call on the {code("cme-call")} rows, '
         f'{oc["F1"]["lone_call_ns"]:.0f} ns alone: {oc["F1"]["extra_alone_ns"]:.0f} ns more (boot F1)',
         ST_SOME, '@@H:open-call@@'],
        [link('open-refill', T_REFILL),
         f'about one inner refill per line of the chain in each rep '
         f'({_rng(rps["per_line_lo"], rps["per_line_hi"], 2)} as printed, boot F2)',
         ST_SOME, '@@H:open-refill@@'],
        [link('open-l3', T_L3),
         f'hit count {_rng(hit_peak["hit_min"], hit_peak["hit_max"], 2)} per load at {hit_peak["label"]} '
         f'on boot F2, the footprint with the lowest chain load above the CME L1',
         ST_CTRL, '@@H:open-l3@@'],
        [link('open-step', T_STEP),
         f'{V.signed(st1["step_ns"], 3, "ns")} on boot F1, {V.signed(st2["step_ns"], 3, "ns")} on boot F2',
         ST_NONE, '@@H:open-step@@'],
        [link('open-boots', T_BOOTS),
         f'{V.signed(worst_l1["f1_minus_f2"], 1, "ns")} per load at {worst_l1["label"]} on boot F1, '
         f'{V.signed(pfl["f1_minus_f2"], 1, "ns")} at {pfl["label"]} with every line flushed first',
         ST_SOME, '@@H:open-boots@@'],
        [link('open-outside', T_OUTSIDE),
         f'{flat_hi["best"]:.1f} ns at {flat_hi["label"]}, {top["best"]:.1f} ns at {top["label"]} (boot F2)',
         ST_SOME, '@@H:open-outside@@'],
    ]
    A(S.table(
        ['Item', 'Size of the effect', 'Status', 'Hypotheses with a test'],
        ['Open items'] + open_items +
        [[link('open-small', 'Smaller items'), '@@NSMALL@@ observations', 'listed in a table', '@@H:open-small@@'],
         'Not measured',
         [link('open-not', 'Rows that do not exist on these boots'), '@@NNOT@@ kinds of row', 'not measured', '0'],
         [link('open-addr', 'A chain in address order'),
          f'{ao["best"]:.3f} ns per load on a third boot (prefetchers on)', 'not measured on these boots', '0']],
        caption='Overview of this section. Each line links to its subsection. A subsection gives the rows, the '
                'reason why they are not explained, the hypotheses and the measurement that would decide.',
        note=f'Status "{ST_SOME}": rows of these boots are consistent with a hypothesis or speak against one. '
             f'No hypothesis is confirmed. Status "{ST_NONE}": no row of these boots is for or against a '
             f'hypothesis. Status "{ST_CTRL}": the counters of the item are not validated.',
        align='lllr'))

    def block(id_, obs, why, hyps, settle=None):
        nh[id_] = len(hyps)
        h = ('<p><b>Observation</b></p>' + S.bullets(obs) +
             '<p><b>Why it is not explained</b></p>' + S.bullets(why) +
             '<p><b>Hypotheses</b></p>' + ''.join(hyps) +
             '<p><b>What would settle it</b></p>')
        return h + (S.bullets(settle) if settle else '')

    # ================================================================ 1 write step
    f_sweep = 'cme-bandwidth-dram-1core.csv'
    f_single = 'cme-bandwidth-dram-1core-asmpasses.csv'
    f_core = 'bandwidth-dram-1core.csv'
    A(S.h3('open-write', T_WRITE))
    A(S.bullets([
        f'The CME write rate is {_rng(min(w_small), max(w_small), 1, "GB/s")} from {W_SMALL} and '
        f'{_rng(min(w_large), max(w_large), 1, "GB/s")} from {W_LARGE}, on both boots '
        f'({S.term("looped form", "")}, {S.term("bracket time", "")}, file {fref(f_sweep)}).',
        f'No CME bandwidth row has a refill counter. No write row on a buffer in the DRAM model ran under the '
        f'{S.term("mesh counters", "")}. So no cache level can be named for either rate.',
        f'The figure and the table of these rows are in {S.xref("bw-write")}. The core rows are in '
        f'{S.xref("bw-core")}.']))
    corew = [r for r in D.core_bw if r['kernel'] == 'write']
    ssw_rows = {b: D.bw_table('sweep-single', b, 'write') for b in BOOTS}
    ssw = {b: [r['best_span'] for r in ssw_rows[b]] for b in BOOTS}
    rsz = sorted(r['size'] for r in D.bw_table('sweep', 'F1', 'read'))
    r_in, r_out = max(s for s in rsz if s <= CME_L1_BYTES), min(s for s in rsz if s > CME_L1_BYTES)
    rd_in, rd_out = D.bw_row('F1', 'sweep', 'read', r_in), D.bw_row('F1', 'sweep', 'read', r_out)
    n_cmn = D.commands['F1']['n_cme_cmn']
    A(block(
        'open-write',
        [f'The {SHI} rate is {w_ratio["F1"]:.3f} times the {SLO} rate on boot F1 and {w_ratio["F2"]:.3f} times on '
         f'boot F2.',
         f'The {S.term("single-call form", "")} reads the same inside the span: '
         f'{_rng(min(ssw["F1"]), max(ssw["F1"]), 1, "GB/s")} from {span_lab([r["size"] for r in ssw_rows["F1"]])} '
         f'on boot F1 and {_rng(min(ssw["F2"]), max(ssw["F2"]), 1, "GB/s")} on boot F2 (file {fref(f_single)}).',
         f'The write rate does not step at {L1SZ}, the size of the CME L1 (operator\'s README) {r_readme1()}. '
         f'It reads {wsweep["F1"][r_in]["best"]:.1f} GB/s at {V.size_label(r_in)} and '
         f'{wsweep["F1"][r_out]["best"]:.1f} GB/s at {V.size_label(r_out)} on boot F1.',
         f'The read rate does step there: {rd_in["best"]:.1f} GB/s at {V.size_label(r_in)} and '
         f'{rd_out["best"]:.1f} GB/s at {V.size_label(r_out)} on boot F1.',
         f'The write of the core on boot F1 reads '
         f'{_rng(min(r["best"] for r in corew), max(r["best"] for r in corew), 1, "GB/s")} '
         f'from {span_lab([r["size"] for r in corew])} and has no step (file {fref(f_core, ("F1",))}).',
         'Both boots show the step. So the prefetcher setting alone does not cause it.'],
        [f'The bandwidth program refuses its counter option together with the CME option {r_bwc()}. '
         f'So no bandwidth row has a CME counter.',
         f'No row lies between {SLO} and {SHI}. So the footprint at which the rate steps is not known.',
         f'{n_cmn} CME commands per boot ran under the mesh counters. The OCM write is the only '
         f'write among them {r_log()}.'],
        [S.hyp(f'Up to {V.size_label(l3_bytes)}, the size of the cluster L3, the written lines stay inside the '
               f'cluster. Above it, each pass sends written lines out to the mesh, and that path limits the rate.',
               f'CME write rows at footprints between {SLO} and {SHI}, under the mesh counters. The hypothesis '
               f'predicts that the mesh requests per pass rise at the footprint where the rate steps.'),
         S.hyp('Above the step, the limit is the rate at which the cluster obtains the right to write a line '
               '(ownership) from outside the cluster. The eviction of written lines is not the limit.',
               'CME refill counters on a bandwidth write row. A count near one outer refill per line above the '
               'step, with a rate that follows the refill latency, would support it.'),
         S.hyp(f'The rate below the step is a store-rate limit of the CME and has no relation to a cache level '
               f'(see {S.xref("open-store")}).',
               f'A store-path counter of the CME on a write row, or the store timing in the RTL. The flat rate '
               f'across the {L1SZ} size of the CME L1 is consistent with this hypothesis and does not prove it.')],
        [f'CME write rows at footprints between {SLO} and {SHI}.',
         f'The same rows under the mesh counters, to compare the mesh requests per pass at {SLO} and at {SHI}.',
         'CME counters on a bandwidth row. The program does not offer this.']))

    # ================================================================ 2 store vs load
    f_l1s = 'cme-bandwidth-l1-asmpasses.csv'
    A(S.h3('open-store', T_STORE))
    r_kern = S.ref('cme-kern', 'Source file %s: the CME kernels of the latency test and of the bandwidth test.'
                   % code('cme_kern.S'))
    A(S.bullets([
        f'At {SVL} the read throughput divided by the write throughput is {svl["F1"]["ratio"]:.2f} on boot F1 and '
        f'{svl["F2"]["ratio"]:.2f} on boot F2 (single-call form, {S.term("span time", "")}).',
        f'Each throughput is the bytes of a whole loop divided by its time. Each load or store instruction of '
        f'these loops transfers four 64-byte vectors. The read loop also runs the XOR instructions of the '
        f'{S.term("fold", "")} {r_kern}.',
        'So these numbers do not give the time that one load or one store takes.',
        f'The buffer is {SVL} and the CME L1 is {L1SZ} (operator\'s README) {r_readme1()}. '
        f'So a refill is not expected in these rows. No bandwidth row has a refill counter to confirm that.']))
    A(S.fig(V.hbar(
        [dict(label='Read loop', sub='single-call read, %s' % SVL,
              values=[svl['F2']['read_cycles_per_64b'], svl['F1']['read_cycles_per_64b']]),
         dict(label='Write loop', sub='single-call write, %s' % SVL,
              values=[svl['F2']['write_cycles_per_64b'], svl['F1']['write_cycles_per_64b']],
              notes=[f'(read / write throughput: {svl["F2"]["ratio"]:.2f})',
                     f'(read / write throughput: {svl["F1"]["ratio"]:.2f})'])],
        series=[(F2N, 'f2'), (F1N, 'f1')], unit='cycles', fmt=lambda v: V.num(v, 2),
        xlabel='effective core cycles per 64 bytes transferred, span time', width=820),
        f'Effective cycles per 64 bytes transferred inside the span. Kernels {code("cme-read")} and '
        f'{code("cme-write")}, single-call form, {SVL}, best rows, span rate, boot F1 and boot F2, file '
        f'{fref(f_l1s)}. Effective cycles = 64 bytes / span rate x {cpn:.2f} core cycles per ns. '
        f'The value is the throughput of a whole loop. It is not the time of one instruction.',
        f'The read loop needs {svl["F1"]["read_cycles_per_64b"]:.2f} effective cycles per 64 bytes transferred '
        f'and the write loop {svl["F1"]["write_cycles_per_64b"]:.2f} on boot F1 '
        f'({svl["F2"]["read_cycles_per_64b"]:.2f} and {svl["F2"]["write_cycles_per_64b"]:.2f} on boot F2).'))
    fits_w = {b: D.l1_fit(b, 'single-call', 'write', 'span') for b in BOOTS}
    A(S.table(
        ['Boot', 'Read,<br>span rate', 'Write,<br>span rate',
         'Read loop,<br>effective cycles per<br>64 bytes transferred',
         'Write loop,<br>effective cycles per<br>64 bytes transferred', 'Read throughput /<br>write throughput'],
        [[BN[b], f'{svl[b]["read_span_gbps"]:.3f} GB/s',
          f'{svl[b]["write_span_gbps"]:.3f} GB/s',
          f'{svl[b]["read_cycles_per_64b"]:.2f}', f'{svl[b]["write_cycles_per_64b"]:.2f}',
          f'{svl[b]["ratio"]:.2f}'] for b in BOOTS],
        caption=f'Single-call read and write at {SVL}, best rows ({code(f_l1s)}).',
        note=f'Effective cycles per 64 bytes transferred = 64 bytes / span rate x {cpn:.2f} core cycles per ns. '
             f'It is a loop throughput and not the time of one load or one store.'))
    fit_txt = []
    for b in BOOTS:
        f = fits_w[b]
        if f['verdict'] == 'pass':
            fit_txt.append(f'{f["rate_gbps"]:.1f} GB/s est. on boot {b} (largest residual {f["max_res_pct"]:.1f} % of the '
                           f'smallest pass time)')
    # single-call write rows that fit in the CME L1, bracket time, cycles per 64-byte vector
    scw = [r for b in BOOTS for g in ('l1-single', 'sweep-single') for r in D.bw_table(g, b, 'write')
           if r['size'] <= CME_L1_BYTES]
    scw_cyc = [64.0 / r['best'] * cpn for r in scw]
    lim = D.limits
    assert abs(min(scw_cyc) - min(lim[b]['write_cycles_per_vec_lo'] for b in BOOTS)) < 0.005
    assert abs(max(scw_cyc) - max(lim[b]['write_cycles_per_vec_hi'] for b in BOOTS)) < 0.005
    # all single-call write rows of both boots, bracket time, cycles per 64-byte vector
    scw_all = [r for b in BOOTS for g in ('l1-single', 'sweep-single') for r in D.bw_table(g, b, 'write')]
    scw_all_cyc = [64.0 / r['best'] * cpn for r in scw_all]
    A(block(
        'open-store',
        [f'The single-call read reads {svl["F1"]["read_span_gbps"]:.1f} GB/s on boot F1 and '
         f'{svl["F2"]["read_span_gbps"]:.1f} GB/s on boot F2 in the span.',
         f'The single-call write reads {svl["F1"]["write_span_gbps"]:.1f} GB/s and '
         f'{svl["F2"]["write_span_gbps"]:.1f} GB/s.',
         f'In the single-call form from {span_lab([r["size"] for r in scw])} the write loop needs '
         f'{_rng(min(scw_cyc), max(scw_cyc), 2)} effective cycles per 64 bytes transferred over both boots '
         f'(bracket time, best rows, files {code(f_l1s)} and {fref(f_single)}).'] +
        ([f'A straight line through the write time per pass at {labels(D.l1_sizes)} passes the '
          f'{S.term("plan rule", "")} (single-call form, span time, best rows, file {code(f_l1s)}). '
          f'Its slope is ' + ' and '.join(fit_txt) + '.'] if len(fit_txt) == 2 else []),
        [f'The buffer of {SVL} is smaller than the CME L1 of {L1SZ}. The ratio is the same with the prefetchers '
         f'on ({svl["F1"]["ratio"]:.2f}) and off ({svl["F2"]["ratio"]:.2f}). So a refill is not expected.',
         f'The bandwidth rows carry no counters {r_bwc()}. So no count confirms that.',
         f'No row isolates the store path. The test plan records the same question and says that no row isolates '
         f'the cause {r_cmeplan()}.'],
        [S.hyp(f'The write throughput is a limit of the store path of the CME itself. The single-call write rows '
               f'transfer 64 bytes every {_rng(min(scw_all_cyc), max(scw_all_cyc), 2)} effective cycles from '
               f'{span_lab([r["size"] for r in scw_all])} (bracket time, best rows, both boots).',
               'A CME event that counts the stores that wait for a free entry of the store buffer, read on a '
               'write row. Or the store timing in the RTL. No kernel on these boots can separate the store path '
               'from the rest of the write loop.')],
        ['A counter of the store path on a write row.',
         'The store timing of the CME in the RTL or in the Arm technical reference manual of the C1-SME2.']))

    # ================================================================ 3 looped write in-span
    f_l1p, f_dsb, f_cc = 'cme-bandwidth-l1-passes.csv', 'cme-bandwidth-l1-dsb.csv', 'cme-bandwidth-call-cost.csv'
    l1s = D.l1_sizes
    L1S = span_lab(l1s)
    if lw_peak_size['F1'] == lw_peak_size['F2']:
        peak_at = 'both at %s' % V.size_label(lw_peak_size['F1'])
    else:
        peak_at = 'at %s and at %s' % (V.size_label(lw_peak_size['F1']), V.size_label(lw_peak_size['F2']))
    A(S.h3('open-looped', T_LOOPED))
    A(S.bullets([
        f'Inside the span the looped write reads up to {lw_peak["F1"]:.1f} GB/s on boot F1 and '
        f'{lw_peak["F2"]:.1f} GB/s on boot F2, {peak_at}. '
        f'The single-call write reads {_rng(min(sw_all), max(sw_all), 1, "GB/s")} in its span.',
        'A span rate above the single-call rate fits a span that does not hold all the store work of its call. '
        'No row shows that mechanism, so it is a hypothesis.',
        f'The figure and the table of the write forms are in {S.xref("callcost-write")}. The rows of one write '
        f'call are in {S.xref("callcost-rows")}.']))
    lvs = {(r['boot'], r['kernel'], r['size']): r for r in D.looped_vs_single}
    dif = {(r['boot'], r['size']): r for r in D.l1_diffs}
    cc = {(r['boot'], r['kernel'], r['size']): r for r in D.call_cost}
    wsz = sorted(s for (b, k, s) in cc if b == 'F1' and k == 'write')
    fl = {b: D.l1_fit(b, 'looped', 'write', 'bracket') for b in BOOTS}
    out_lw = {b: [x for r in lw[b]['rows'] for x in r['outside_reps']] for b in BOOTS}
    dlw = {b: [lvs[(b, 'write', s)]['diff_ns'] for s in l1s] for b in BOOTS}
    same_sz = [s for i, s in enumerate(l1s) if all(abs(dlw[b][i]) <= 3.0 for b in BOOTS)]
    same_max = max(abs(dlw[b][l1s.index(s)]) for b in BOOTS for s in same_sz)
    cc_pair = [s for s in wsz if s in (lw_peak_size['F1'] // 2, lw_peak_size['F1'])]
    c_a, c_b = cc_pair
    assert all(f['verdict'] == 'void' for f in fl.values())
    dsb_sz = [s for s in l1s if s in same_sz]
    A(block(
        'open-looped',
        [f'A looped pass minus a single-call pass reads ' + ', '.join(V.signed(x, 1) for x in dlw['F1']) +
         f' ns at {labels(l1s)} on boot F1, and ' + ', '.join(V.signed(x, 1) for x in dlw['F2']) +
         f' ns on boot F2 (bracket time per pass, files {fref(f_l1p)} and {fref(f_l1s)}).',
         f'So at {labels(same_sz)} a looped pass and a single-call pass take the same time within '
         f'{same_max:.1f} ns, although the looped form makes one kernel call per pass.',
         f'Each looped write call still spends {_rng(min(out_lw["F1"]), max(out_lw["F1"]), 1, "ns")} outside its '
         f'span on boot F1 and {_rng(min(out_lw["F2"]), max(out_lw["F2"]), 1, "ns")} on boot F2 (all reps of the '
         f'looped write rows, {L1S}).',
         f'One write call of ' + labels(wsz) + ' spends ' +
         ', '.join(f'{cc[("F1", "write", s)]["span_ns"]:.1f}' for s in wsz) +
         f' ns in its span on boot F1 (file {fref(f_cc, ("F1",))}).',
         f'From {V.size_label(c_a)} to {V.size_label(c_b)} that is '
         f'{cc[("F1", "write", c_b)]["span_ns"] - cc[("F1", "write", c_a)]["span_ns"]:.1f} ns for '
         f'{V.num(c_b - c_a, 0)} more bytes. The apparent rate of those bytes is '
         f'{(c_b - c_a) / (cc[("F1", "write", c_b)]["span_ns"] - cc[("F1", "write", c_a)]["span_ns"]):.0f} GB/s est. '
         f'The single-call write reads at most {max(sw_all):.1f} GB/s.',
         f'The four looped points do not lie on one line. The largest residual is {fl["F1"]["max_res_pct"]:.1f} % of '
         f'the smallest pass time on boot F1 and {fl["F2"]["max_res_pct"]:.1f} % on boot F2. The plan rule voids the '
         f'intercept. So this page quotes no fixed cost per call for the looped write.',
         f'With a {S.term("DSB ST", "")} before SMSTOP the pass takes ' +
         ' and '.join(f'{dif[("F1", s)]["dsb_ns"]:.1f} ns longer at {V.size_label(s)}' for s in dsb_sz) +
         f' on boot F1 (file {fref(f_dsb)}). That is close to the outside-span time of one call.'],
        [f'The run plan states that the span of a store call does not wait for the stores unless the kernel ends '
         f'with DSB ST {r_plan13()}. No row of these boots shows that mechanism.',
         'If the statement holds, the span time and the outside-span time each include an unknown part of the '
         'store work. These rows do not separate the two parts.',
         f'The run plan names no observation that would identify the mechanism {r_plan13()}.'],
        [S.hyp('The span of a write call ends before the stores of the call have completed. The last stores finish '
               'while the call leaves streaming mode and the next call enters it. So the cost of the call overlaps '
               'with store work.',
               'A write kernel with a third stamp after a DSB ST in the same call. It gives the store '
               'completion time of each call. The DSB ST rows of these boots are consistent with the hypothesis '
               'and do not prove it.')],
        ['A kernel that stamps the time before and after a DSB ST inside one call. This is a proposal of this '
         'page, not of the run plan.']))

    # ================================================================ 4 call cost and the lone call
    A(S.h3('open-call', T_CALL))
    lone = [f'{oc[b]["lone_call_ns"]:.0f}' for b in BOOTS]
    extra = [f'{oc[b]["extra_alone_ns"]:.0f}' for b in BOOTS]
    if lone[0] == lone[1] and extra[0] == extra[1]:
        lone_txt = (f'One call alone in its bracket spends {lone[0]} ns on both boots (median). That is '
                    f'{extra[0]} ns more than a call of the {code("cme-call")} rows.')
    else:
        lone_txt = (f'One call alone in its bracket spends {lone[0]} ns (median, boot F1) and {lone[1]} ns '
                    f'(boot F2). That is {extra[0]} ns and {extra[1]} ns more than a call of the '
                    f'{code("cme-call")} rows.')
    A(S.bullets([
        f'On the {S.term("cme-call row", "")}s (64 calls that follow each other, one register step each) a call spends '
        f'{_rng(bs["call_outside_lo"], bs["call_outside_hi"], 1, "ns")} outside its span.',
        f'Looped bandwidth calls spend {_rng(loop_lo, loop_hi, 1, "ns")} outside their spans.',
        lone_txt,
        'No row separates SMSTART and SMSTOP from the register save, the restore, the call and the return. '
        'No row shows what the extra time of a lone call is.',
        f'The figure and the two tables of these rows are in {S.xref("callcost-alone")}.']))
    cg = {(r['boot'], r['key']): r for r in D.cycle_gap}
    slr = {b: osp[(b, 'single-later-read')] for b in BOOTS}
    sfr = {b: osp[(b, 'single-first-read')] for b in BOOTS}
    slw = {b: osp[(b, 'single-later-write')] for b in BOOTS}
    med_gap = [cg[(b, k)]['median'] for b in BOOTS for k in ('ocm-64', 'ocm-320', 'cme-call')]
    slr_rng = _rng(min(slr[b]["lo"] for b in BOOTS), max(slr[b]["hi"] for b in BOOTS), 1, "ns")
    sfr_rng = _rng(min(sfr[b]["lo"] for b in BOOTS), max(sfr[b]["hi"] for b in BOOTS), 1, "ns")
    assert min(sfr[b]['lo'] for b in BOOTS) > max(slr[b]['hi'] for b in BOOTS)
    A(block(
        'open-call',
        [f'The outside-span time is not one number. It reads '
         f'{_rng(bs["call_outside_lo"], bs["call_outside_hi"], 1, "ns")} per call on the {code("cme-call")} rows, '
         f'{_rng(min(osp[(b, "looped-sweep-small")]["lo"] for b in BOOTS), max(osp[(b, "looped-sweep-small")]["hi"] for b in BOOTS), 1, "ns")} '
         f'on the looped rows from {W_SMALL}, and '
         f'{_rng(min(osp[(b, "looped-sweep-large")]["lo"] for b in BOOTS), max(osp[(b, "looped-sweep-large")]["hi"] for b in BOOTS), 1, "ns")} '
         f'from {W_LARGE}.',
         f'A call alone in its bracket spends {_rng(osp[("F1", "ocm-64")]["lo"], osp[("F1", "ocm-64")]["hi"], 0, "ns")} '
         f'outside its span on boot F1 and {_rng(osp[("F2", "ocm-64")]["lo"], osp[("F2", "ocm-64")]["hi"], 0, "ns")} on '
         f'boot F2 (OCM latency passes of 64 loads, {osp[("F1", "ocm-64")]["n"]} passes per boot).',
         f'The single-call read reps show the same level with no counter call before them: {slr_rng} for the '
         f'reps after the first, on both boots ({slr["F1"]["n"]} reps per boot). So a counter call cannot be the '
         f'only cause.',
         f'Each of these reps follows a warm-up pass that is not timed and a thread barrier (the point where the '
         f'worker thread waits for the main thread before each rep) {r_bwrep()}. So these reps do not test '
         f'whether a thread barrier before the call matters.',
         f'The first rep of each single-call read row spends {sfr_rng}. That is more than every later rep.',
         f'The single-call write reps after the first spend a median of {slw["F1"]["median"]:.1f} ns on boot F1 '
         f'and {slw["F2"]["median"]:.1f} ns on boot F2 '
         f'({_rng(min(slw[b]["lo"] for b in BOOTS), max(slw[b]["hi"] for b in BOOTS), 1, "ns")} over both boots). '
         f'That is {slw["F1"]["median"] - slr["F1"]["median"]:.0f} ns and '
         f'{slw["F2"]["median"] - slr["F2"]["median"]:.0f} ns above the read reps. '
         f'{S.xref("open-looped", cap=True)} gives a hypothesis for the store part.',
         f'The core cycle count of a {S.term("counting window", "")} is '
         f'{_rng(min(med_gap), max(med_gap), 0, "cycles")} above the CME cycle count of the same window '
         f'(medians). The difference is the same with 1 call and with 64 calls per window. Converted to time at '
         f'{cpn:.2f} core cycles per ns it is {min(med_gap) / cpn:.0f} to {max(med_gap) / cpn:.0f} ns.',
         'So each added call adds about the same number of cycles to both counts, its outside-span time included.',
         'Each cycle count is one total per window. The files hold no time of a counter start or stop. '
         'So they do not show at which time in the window the two counters differ.',
         f'The two clock reads of an empty bracket take {bs["overhead_common"]:.1f} ns in '
         f'{bs["overhead_n_common"]} of the {bs["n_files"]} CME latency files '
         f'({bs["overhead_other"][0][1]:.1f} ns in the other one).'],
        ['No row separates SMSTART and SMSTOP from the register save, the restore, the call and the return.',
         f'Every CME kernel of these boots takes the two {S.term("stamp", "")}s of its span. No row runs without '
         f'them. So the share of the stamps in each number is not measured.',
         f'The power controller of each CME is the unit that switches the CME on and off. The firmware sets it '
         f'to dynamic mode (operator\'s README) {r_readme1()}. The files do not record whether the CME powers '
         f'down between two spans.',
         f'The run plan leaves the extra time of a {S.term("lone call", "")} open by choice and has no dedicated '
         f'row for it {r_plan13()}.'],
        [S.hyp('The CME leaves a low-power state at the first streaming instruction after an idle interval. '
               'The extra time of a lone call is the time to leave that state.',
               'Rows that vary the idle time before one call (0, 1, 10 and 100 microseconds) and read the outside-span '
               'time, with the status of the CME power controller read before and after the call.'),
         S.hyp(f'The clock of the CME, or its cycle counter, does not run from the counter start until the first '
               f'streaming entry of the window. Then the extra time occurs once per window and not once per call. '
               f'Under this hypothesis the 64 calls of a {code("cme-call")} rep split as follows. The lowest rep '
               f'spends {V.num(oc["F1"]["calls64_ns"], 0)} ns outside its spans in total on boot F1 '
               f'({V.num(oc["F2"]["calls64_ns"], 0)} ns on boot F2). The first call takes the '
               f'{oc["F1"]["lone_call_ns"]:.0f} ns of a lone call (a median). That leaves '
               f'{oc["F1"]["later_call_est_ns"]:.1f} ns est. for each of the 63 later calls on boot F1 and '
               f'{oc["F2"]["later_call_est_ns"]:.1f} ns est. on boot F2. No row measures a later call alone, so '
               f'this arithmetic is not a test.',
               'A time stamp before SMSTART in the kernel, or the status of the CME power controller read before '
               'and after a lone call.'),
         S.hyp(f'The core cycle counter and the CME cycle counter do not start and stop at the same instant '
               f'inside the counter calls. Then the difference of {_rng(min(med_gap), max(med_gap), 0, "cycles")} '
               f'between the two cycle counts of a window is a property of the counter calls. It says nothing about the '
               f'clock of the CME.',
               'A counting window with no kernel call in it, with both cycle counts printed. '
               'The hypothesis predicts the same difference there.'),
         S.hyp('The first call after a counter start, a flush or a thread barrier has cache misses and branch '
               'predictor misses in the core. The CME is not involved. The single-call read reps show that a '
               'counter start is not needed for the extra time. The longer first rep of each single-call row is '
               'consistent with a first-call cost in the core.',
               'One bracket that holds two calls with a controlled idle time between them and no system call. '
               'The second call shows whether the extra time needs a system call or a barrier before it. '
               'A second test: count the cache refills and the branch mispredictions of the core over a lone call '
               'and over the second of two calls. Equal counts reject this hypothesis.')],
        ['The same script on one boot with a build whose stamps are compiled out.',
         'Rows that vary the idle time before a single call, with the power controller status beside them.',
         'A stamp before SMSTART, to split the time before the span from the time after it.']))

    # ================================================================ 5 once-per-rep refill
    f_small = 'cme-latency-dram-small.csv'
    A(S.h3('open-refill', T_REFILL))
    rpl = [r for r in D.refills_per_line if r['boot'] == 'F2' and r['in_l1']]
    rcl = [r for r in D.refills_per_line if r['boot'] == 'F2' and not r['in_l1']]
    RPL = span_lab([r['size'] for r in rpl])
    fr = {b: D.l1_fit(b, 'looped', 'read', 'span') for b in BOOTS}
    # the file prints the count per load to four decimals: one print step, in refills per line
    pstep = {r['size']: 0.0001 * r['loads'] / r['lines'] for r in rpl}
    A(S.bullets([
        f'On boot F2 every timed rep of a chain of {RPL} counts about one inner refill per line of the chain '
        f'({_rng(rps["per_line_lo"], rps["per_line_hi"], 2)} as printed, in all {rps["n_rep_rows"]} rep rows, '
        f'file {fref(f_small, ("F2",))}).',
        f'Two walks that are not timed run before the first rep {r_latc()}.',
        'The count is a total over one rep. It does not say which lines were refilled, or at which time in the rep.',
        'A rep whose first walk refills every line of the chain would give this count. That reading is a '
        'hypothesis below. The cause of the refills is not measured.',
        f'The figure and the table of these rows are in {S.xref("lat-perrep")}.']))
    looped_ok = all(fr[b]['verdict'] == 'pass' for b in BOOTS)
    A(block(
        'open-refill',
        [f'The count per line reads about one in every rep, although the chain was walked twice before the first '
         f'rep and many times inside each rep.',
         f'The file prints the count per load to four decimals. One print step is '
         f'{pstep[rpl[0]["size"]]:.2f} refills per line at {rpl[0]["label"]} and '
         f'{pstep[rpl[-1]["size"]]:.3f} at {rpl[-1]["label"]}. So the count per line is not known more '
         f'exactly than that.',
         f'The chain load is {_rng(rps["l1_above_rt_lo"], rps["l1_above_rt_hi"], 3, "ns")} above the round-trip '
         f'baseline of {D.rt_ns:.3f} ns at these footprints.'] +
        ([f'The looped bandwidth rows differ for calls that follow each other. The fitted span rate of the looped '
          f'read from {L1S} is {fr["F1"]["rate_gbps"]:.1f} GB/s est. on boot F1 and '
          f'{fr["F2"]["rate_gbps"]:.1f} GB/s est. on boot F2, and both fits pass the plan rule (file {code(f_l1p)}).',
          f'That rate is {fr["F1"]["rate_gbps"] / rd_out["best"]:.1f} times the {rd_out["best"]:.1f} GB/s of the '
          f'{V.size_label(r_out)} read row of boot F1, which does not fit in the CME L1. No bandwidth row has '
          f'a refill counter.'] if looped_ok else []) +
        [f'One known difference between the two cases: a latency rep has a counter stop, a counter read and a '
         f'counter start before its call {r_latc()}. A looped bandwidth pass has none {r_bwrep()}.',
         'The two cases also use different kernels. Only the latency run has the CME counters enabled.'],
        ['Each rep row holds one refill total for the whole rep. No row counts the first walk of a rep apart '
         'from the later walks.',
         'No row records the address of a refilled line. So the rows do not show whether each line of the chain '
         'is refilled one time, or which state the CME L1 has at the start of a rep.',
         'No latency row ran without the counters, and no rep loop ran without a counter call between the reps.'],
        [S.hyp('Each rep starts with a CME L1 that does not hold the chain. The first walk of the rep refills '
               'every line of the chain one time. The later walks of the rep refill no line.',
               'A rep that counts its first walk apart from its later walks. The hypothesis predicts one inner '
               'refill per line in the first walk and none in the later walks. A trace of the refilled addresses '
               'would show the history of each line.'),
         S.hyp(f'The difference between the chain load and the round-trip baseline at {RPL} comes from these '
               f'refills. It is not the cost of a load that hits the CME L1. Support: that difference divided by '
               f'the refill count is '
               f'{_rng(rps["l1_ns_per_refill_lo"], rps["l1_ns_per_refill_hi"], 0, "ns")} est. per refill, close to '
               f'the {_rng(rps["cluster_ns_per_refill_lo"], rps["cluster_ns_per_refill_hi"], 1, "ns")} est. per '
               f'refill of the rows from {span_lab([r["size"] for r in rcl])}. The value at {rpl[0]["label"]} '
               f'has one significant digit, because the count per load prints as {rpl[0]["inner"]:.4f}.',
               'A latency run without the counter option, or a rep loop with no system call between the reps. '
               'The hypothesis predicts a lower chain load at these footprints when the refills are absent.'),
         S.hyp('The CME loses the content of its L1 when the core runs a system call between two spans, for example '
               f'because the CME powers down (see {S.xref("open-call")}).',
               'The same latency rows with a varied idle time and with the number of system calls between the reps '
               'set to zero, one and two.')] +
        ([S.hyp(f'In the looped bandwidth rows from {L1S} the lines of the buffer stay in the CME L1 from one '
                f'call to the next.',
                'The CME refill counters on the looped bandwidth rows. The hypothesis predicts a count near '
                'zero refills per line in a call that follows another call.')] if looped_ok else []),
        ['A rep that counts its first walk and its later walks apart, to show at which time the refills occur.',
         'A trace of the refilled addresses, to show the history of each line.',
         f'A latency sweep from {RPL} without the counter option.',
         'A rep loop with no system call between the reps, with the counters read once around all reps.']))

    # ================================================================ 6 L3 events
    f_l3s, f_l3l = 'cme-latency-dram-small-l3.csv', 'cme-latency-dram-large-l3.csv'
    A(S.h3('open-l3', T_L3))
    chk = D.l3_checks
    l3_cl = [r for r in D.chain_l3['F2'] if r['kind'] == many and r['size'] > CME_L1_BYTES]
    l3_in = [r for r in D.chain_l3['F2'] if r['size'] <= CME_L1_BYTES]
    c_lo, c_hi = l3_cl[0], l3_cl[-1]
    f1_hm = [r['hit'] + r['miss'] for r in D.chain_l3['F1']]
    f1_over = [r['size'] for r in D.chain_l3['F1'] if r['hit'] + r['miss'] > 1.0]
    A(S.bullets([
        f'The three {S.term("L3 events", "")} of the CME are exploratory counts. No row on these boots is built so '
        f'that every L3 access is a hit, or every one a miss.',
        f'On boot F2 the hit count rises from {c_lo["hit"]:.2f} per load at {c_lo["label"]} to '
        f'{c_hi["hit"]:.2f} at {c_hi["label"]} while the chain load falls from '
        f'{c_lo["best"]:.3f} ns to {c_hi["best"]:.3f} ns. '
        f'That agrees with a real hit count and does not validate it.',
        f'The figure and the table of these rows are in {S.xref("l3-rows")} '
        f'(files {fref(f_l3s)} and {fref(f_l3l)}).']))
    # miss minus refill per load times the footprint: a derived product in bytes.  It is built from
    # totals per load, so it does not identify a set of lines of the chain.
    l3r = {}
    for r in D.l3_reps['F2']:
        if r['size'] in {x['size'] for x in l3_cl}:
            l3r.setdefault(r['size'], []).append(r)
    for v in l3r.values():
        v.sort(key=lambda r: r['rep'])
    snoop_kib = {sz: [r['mms'] * sz / 1024.0 for r in v] for sz, v in l3r.items()}
    stable = [sz for sz in sorted(snoop_kib) if sz > l3_cl[0]['size']]        # the footprints above the first one
    last = [snoop_kib[sz][-1] for sz in stable]
    falls_all = all(a > b for sz in stable for a, b in zip(snoop_kib[sz], snoop_kib[sz][1:]))
    core_caches = [c for c in D.platform['caches'] if c['type'] != 'Instruction' and c['level'] in (1, 2)]
    core_bytes = sum(c['size_bytes'] for c in core_caches)
    A(S.table(
        ['Footprint'] + ['Rep %d, KiB' % r['rep'] for r in l3r[stable[0]]] +
        ['Chain load, first to last rep, ns', 'L3 hit count per load, first to last rep'],
        [[c_['label']] + [f'{v:.1f}' for v in snoop_kib[c_['size']]] +
         [f'{l3r[c_["size"]][0]["ns"]:.3f} to {l3r[c_["size"]][-1]["ns"]:.3f}',
          f'{l3r[c_["size"]][0]["hit"]:.4f} to {l3r[c_["size"]][-1]["hit"]:.4f}'] for c_ in l3_cl],
        caption=f'Miss minus refill per load times the footprint, per rep, boot F2, walked many times. The value is '
                f'a derived product in KiB: (L3 miss count per load minus L3 refill count per load) x footprint '
                f'(file {fref(f_l3s, ("F2",))}).',
        note='The product is built from event totals per load. It does not identify a set of lines of the chain. '
             'The three events are exploratory, so the product is an exploratory value too.',
        align='l' + 'r' * (len(l3r[stable[0]]) + 2), id_='open-l3-product'))
    assert all(x['best'] > y['best'] for x, y in zip(l3_cl[:-2], l3_cl[1:-1]))      # the fall named below
    assert all(x['hit'] < y['hit'] for x, y in zip(l3_cl[:-2], l3_cl[1:-1]))
    A(block(
        'open-l3',
        [f'From {l3_cl[0]["label"]} to {V.size_label(stable[-2])} the chain load falls as the footprint grows, and the '
         f'L3 hit count per load rises ({S.xref("lat-serve")}, {S.xref("l3-scatter")}).',
         f'In the last rep the derived product, miss minus refill times the footprint, reads {min(last):.1f} to '
         f'{max(last):.1f} KiB at '
         f'every footprint from {V.size_label(stable[0])} to {V.size_label(stable[-1])}. '
         f'At {l3_cl[0]["label"]} it reads {snoop_kib[l3_cl[0]["size"]][-1]:.1f} KiB.',
         (f'At each of these {len(stable)} footprints the product falls from rep to rep.' if falls_all else
          'The product does not fall from rep to rep at every footprint.'),
         f'So the derived product is nearly the same at these {len(stable)} footprints. '
         f'The product comes from event totals per load. It does not show whether the same lines of the chain '
         f'count as "L3 miss, no L3 refill" in every walk.',
         f'The core writes the buffer and the chain pointers before the CME walks them '
         f'({S.xref("setup-latency")}). The L1 data cache and the L2 of CPU 2 hold '
         f'{V.size_label(core_bytes)} together {r_sysinfo_l3()}.',
         f'The L3 refill count equals the outer refill count to the four printed decimals in all '
         f'{chk["F1"]["chain_rep_rows"]} chain rep rows of each boot.',
         f'Hit plus miss equals inner refills plus outer refills within '
         f'{max(chk[b]["max_hit_miss_minus_refills"] for b in BOOTS):.4f} per load in every row of both boots.',
         f'From {span_lab([r["size"] for r in l3_in])} on boot F2 all three events read at most '
         f'{max(r[k] for r in l3_in for k in ("hit", "miss", "refill")):.3f} per load (best reps).',
         f'On boot F1 hit plus miss reads up to {max(f1_hm):.2f} per load (best reps). It is above one per load '
         f'from {span_lab(f1_over)}. The plain rows of boot F1 count up to '
         f'{max(r["hwprf"] for r in D.chain["F1"]):.2f} prefetch refills per load.'],
        ['The events have no independent control. No boot whose L3 holds no data ran them through the CME. '
         'So "the hit count reads 0 when the L3 is empty" is not checked.',
         f'One reading is: hit = refills that the L3 supplied, miss minus refill = refills that a '
         f'{S.term("snoop", "")} of a core\'s cache supplied. It comes from the operator\'s reading of the RTL '
         f'{r_readme2()}. Under that reading the two equalities above are identities. They validate nothing.',
         f'The test program itself marks the three columns as exploratory {r_commonh()}.'],
        [S.hyp('The hit event counts the CME L1 refills that the cluster L3 supplied. Miss minus refill counts the '
               'refills that a snoop of a core\'s cache supplied. The refill event counts the lines that came from '
               'outside the cluster.',
               'The two L3-event sweeps on a boot whose L3 holds no data: the hit count must read 0 there. '
               'And one row built so that every refill comes from the L3: the hit count must read 1 per load there.'),
         S.hyp(f'The derived product stands for a fixed set of lines. A part of the chain of {min(last):.1f} to '
               f'{max(last):.1f} KiB stays in the caches of CPU 2, the core that wrote the buffer. A CME refill that a snoop of a core\'s cache supplies (operator\'s README) '
               f'does not move the line to the cluster L3. So the same lines are snooped again in every walk. The '
               f'rest of the chain is in the L3, and its share grows with the footprint. A snoop takes longer than '
               f'an L3 hit. So the chain load falls as the footprint grows.',
               'Let the CME write the buffer and the chain pointers. Or let the core walk another buffer of '
               f'{V.size_label(core_bytes)} or more before the reps. The hypothesis predicts a miss minus refill '
               'near 0 per load after either step, and a chain load that does not fall as the footprint grows.')],
        ['The two sweeps with the L3 events on a boot with the L3 in its mode that holds no data.',
         'A row whose refills all come from one source.',
         f'The rows of {span_lab([c_["size"] for c_ in l3_cl])} after the CME wrote the buffer, or after the core '
         f'walked another buffer of {V.size_label(core_bytes)} or more.',
         f'The run plan names both controls and schedules neither {r_plan13()}.']))
    A(S.callout('Until a control validates these events, no result on this page depends on the hit column or on the '
                'miss column. A fit that uses them appears only inside a Hypothesis block.'))

    # ================================================================ 7 the step between the chain kinds
    f_large = 'cme-latency-dram-large.csv'
    A(S.h3('open-step', T_STEP))
    A(S.bullets([
        f'On boot F1 the chain load falls by {abs(st1["step_ns"]):.3f} ns from {ST_FROM} to {ST_TO}. '
        f'On boot F2 it rises by {st2["step_ns"]:.3f} ns. For the core on boot F1 it rises by '
        f'{stc["step_ns"]:.3f} ns.',
        f'The chain kind changes at the same place: "walked many times" stops at {ST_FROM} and "walked once" '
        f'starts at {ST_TO}. So the fall cannot be assigned to the footprint or to the chain kind.',
        f'The figure and the table of the step are in {S.xref("lat-step")} (files {fref(f_small)} and '
        f'{fref(f_large)}).']))
    assert not D.chain_steps['sizes_with_both_sweep_kinds']
    A(block(
        'open-step',
        [f'On boot F1 the CME counts {st1["from_hwprf"]:.2f} {S.term("prefetch refill", "")}s per load at '
         f'{ST_FROM} and {st1["to_hwprf"]:.2f} at {ST_TO}.',
         'Boot F2 and the core on boot F1 both rise at the same place.'],
        ['The two files differ in the footprint and in the chain kind at once.'],
        [S.hyp('The chain kind causes the fall. A chain walked many times gives the prefetcher of the CME the same '
               'lines again and again, and its refills displace lines of the chain. A chain walked once does not.',
               f'The footprints {ST_FROM} and {ST_TO}, each run with both chain kinds, on a boot with the '
               f'prefetchers on. If the fall follows the kind and not the footprint, the hypothesis is confirmed.')]))
    A(S.insufficient(f'No footprint has both chain kinds. One footprint between {ST_FROM} and {ST_TO} that is '
                     f'walked many times and walked once, on both boots, would assign the step to the footprint '
                     f'or to the chain kind.'))

    # ================================================================ 8 F1 against F2
    f_fl = 'cme-latency-dram-flushed.csv'
    A(S.h3('open-boots', T_BOOTS))
    A(S.bullets([
        f'With the prefetchers on, a chain that fits in the CME L1 reads up to {worst_l1["f1_minus_f2"]:.1f} ns '
        f'slower per load ({worst_l1["label"]}). The {pfl["label"]} chain with every line flushed first reads '
        f'{abs(pfl["f1_minus_f2"]):.1f} ns faster.',
        'The two boots differ in more than the prefetcher setting. So a difference between them is not by itself an '
        'effect of the prefetchers.',
        f'The figure and the table of the chain loads of both boots are in {S.xref("lat-prefetch")} '
        f'(files {code(f_small)}, {code(f_large)} and {fref(f_fl)}). The bandwidth rows are drawn below.']))
    ssz = sorted(r['size'] for r in D.bw_table('sweep-single', 'F1', 'read'))
    nb = [ssz[ssz.index(r_out) - 1], ssz[ssz.index(r_out) + 1]]      # the neighbours of the row above the CME L1
    bsel = [('sweep-single', 'read', nb[0]), ('sweep-single', 'read', r_out), ('sweep-single', 'read', nb[1]),
            ('sweep', 'read', r_out), ('sweep', 'read', sizes_w[-1]), ('sweep', 'read64', sizes_w[-1]),
            ('sweep', 'copy', sizes_w[-1]), ('sweep', 'write', sizes_w[-1])]
    bwp = {(r['group'], r['kernel'], r['size']): r for r in D.bw_f1_vs_f2}
    kname = {'read': 'read', 'write': 'write', 'copy': 'copy', 'read64': 'read, 64-byte loads (cme-ldr16)'}
    kshort = {'read': 'read', 'write': 'write', 'copy': 'copy', 'read64': 'read, 64-byte loads'}
    A(S.fig(V.dumbbell(
        [dict(label='%s, %s' % (kshort[k], bwp[(g, k, s)]['label']), sub=bwp[(g, k, s)]['form'] + ' form',
              a=bwp[(g, k, s)]['f2'], b=bwp[(g, k, s)]['f1'], gap=f'{bwp[(g, k, s)]["f2_over_f1"]:.2f} x')
         for g, k, s in bsel],
        a_name=F2N, b_name=F1N, a_color='f2', b_color='f1', unit='GB/s', xlabel='rate, GB/s (bracket time)',
        fmt=lambda v: V.num(v, 1), label_w=230),
        f'Rate on boot F2 and on boot F1 for eight bandwidth rows, best rows, bracket time. Files '
        f'{code(f_single)} and {code(f_sweep)}. The bold number is the boot F2 rate divided by the boot F1 rate.',
        f'The read at {V.size_label(sizes_w[-1])} on boot F2 is '
        f'{bwp[("sweep", "read", sizes_w[-1])]["f2_over_f1"]:.2f} times that of boot F1. The write at the same '
        f'footprint is {bwp[("sweep", "write", sizes_w[-1])]["f2_over_f1"]:.2f} times.'))
    A(S.table(
        ['Kernel', 'Form', 'Footprint', 'Boot F1', 'Boot F2', 'F2 / F1', 'Every rep of one boot above the other'],
        [[kname[k], bwp[(g, k, s)]['form'], bwp[(g, k, s)]['label'], f'{bwp[(g, k, s)]["f1"]:.3f} GB/s',
          f'{bwp[(g, k, s)]["f2"]:.3f} GB/s', f'{bwp[(g, k, s)]["f2_over_f1"]:.3f}',
          'yes' if bwp[(g, k, s)]['reps_apart'] else 'no'] for g, k, s in bsel],
        caption=f'The rows of the figure above with their exact numbers ({code(f_single)}, {code(f_sweep)}).',
        note='Highlighted: the rows where boot F2 reads under 0.7 times boot F1.',
        highlight=[i for i, k in enumerate(bsel) if bwp[k]['f2_over_f1'] < 0.7]))
    s96, r32 = bwp[('sweep-single', 'read', r_out)], bwp[('sweep', 'read', sizes_w[-1])]
    w32 = bwp[('sweep', 'write', sizes_w[-1])]
    l1_pf = [p for p in l1_pairs if p['f1_hwprf'] >= 1.0]
    A(block(
        'open-boots',
        [f'On boot F1 the CME counts {min(p["f1_hwprf"] for p in l1_pf):.1f} to '
         f'{max(p["f1_hwprf"] for p in l1_pf):.1f} prefetch refills per load on chains of '
         f'{span_lab([p["size"] for p in l1_pf])}, which fit in its L1 of {L1SZ}.',
         f'The {pfl["label"]} chain with every line flushed first counts {pfl["f1_outer"]:.2f} outer refills per '
         f'load on boot F1 and {pfl["f2_outer"]:.2f} on boot F2. Its read refills are {pfl["f1_rd"]:.2f} per load '
         f'on boot F1.',
         f'So that row of boot F1 still counts about one read refill per load. Its chain load is '
         f'{abs(pfl["f1_minus_f2"]):.3f} ns below the row of boot F2.',
         f'The single-call read at {s96["label"]} reads {s96["f1"]:.1f} GB/s on boot F1 and {s96["f2"]:.1f} GB/s '
         f'on boot F2 (boot F2 is {s96["f2_over_f1"]:.2f} times boot F1). Its neighbours at '
         f'{labels(nb)} agree between the boots within '
         f'{max(abs(bwp[("sweep-single", "read", s)]["f2_over_f1"] - 1) for s in nb) * 100:.1f} %.',
         f'The looped read at {r32["label"]} reads {r32["f1"]:.1f} GB/s on boot F1 and {r32["f2"]:.1f} GB/s on '
         f'boot F2 (boot F2 is {r32["f2_over_f1"]:.2f} times boot F1). The write at {w32["label"]} differs by '
         f'{abs(w32["f2_over_f1"] - 1) * 100:.1f} %.'],
        [f'The firmware of boot F2 turns off the prefetcher of the core and the prefetcher of the CME together '
         f'(operator\'s README) {r_readme2()}. So the rows do not show which of the two causes a difference.',
         f'The boots differ in what ran before the CME rows. The first CME command starts '
         f'{D.commands["F1"]["cme_first_uptime"]:.2f} s after boot on boot F1, after '
         f'{D.commands["F1"]["n_core"]} core commands, and {D.commands["F2"]["cme_first_uptime"]:.2f} s after boot '
         f'on boot F2, which ran no core command {r_log()}.',
         f'Each command is its own process on each boot. So its buffers need not be on the same physical pages '
         f'(operator\'s README) {r_readme2()}.',
         'The refill events count lines. They do not show which lines a prefetch refill replaced, or which '
         'prefetched lines the walk used.',
         'No boot was repeated. So the spread between two boots with the same settings is not known.'],
        [S.hyp('On a chain that fits in the CME L1, the refills of the prefetcher evict lines of the chain. '
               'Those lines then refill on demand.',
               'A count of CME L1 evictions, or a trace of one walk. The read refills of '
               f'{min(p["f1_rd"] for p in l1_pf):.2f} to '
               f'{max(p["f1_rd"] for p in l1_pf):.2f} per load on boot F1 are consistent with it.'),
         S.hyp('The prefetch refills occupy the refill path of the CME, and loads that hit the CME L1 wait behind them.',
               'The same chains on a boot with only the prefetcher of the CME on. The hypothesis predicts the '
               'same rise with the prefetcher of the core off. The RTL of the refill path would show whether a '
               'load that hits the CME L1 can wait behind a refill.'),
         S.hyp(f'On the {pfl["label"]} chain with every line flushed first, the prefetcher requests the lines next '
               f'to each loaded line. The chain covers every line. So a load finds its line already requested, and '
               f'its read refill completes sooner.',
               f'A chain of {pfl["label"]} with one line per 4 KiB page, walked once, on both boots: no '
               f'neighbouring line is ever loaded there. And a chain in address order (see {S.xref("open-addr")}).'),
         S.hyp(f'At {s96["label"]} in the single-call form, with all passes in one span, the prefetcher fetches '
               f'each line before the read reaches it, at this one footprint.',
               f'Single-call read rows at footprints between {V.size_label(nb[0])} and {V.size_label(nb[1])}, and CME counters '
               f'on a bandwidth row.')],
        ['A boot with only the prefetcher of the CME off and the prefetcher of the core on.',
         'A boot that runs the commands of boot F1 in the same order with the prefetchers off.',
         'A second boot with the settings of boot F1, for the spread between boots.']))

    # ================================================================ 9 outside the cluster
    A(S.h3('open-outside', T_OUTSIDE))
    big = [r for r in lg['F2'] if r['size'] >= flat_hi['size']]
    mid = [r for r in big if r['size'] >= 2 * rise['size']][0]
    A(S.bullets([
        f'On boot F2 the chain load rises from {flat_hi["best"]:.3f} ns at {flat_hi["label"]} to '
        f'{top["best"]:.3f} ns at {top["label"]}. The outer refill count stays at '
        f'{_rng(min(r["outer"] for r in big), max(r["outer"] for r in big), 2)} per load over these rows.',
        f'The outer refill event counts every refill from outside the cluster. It does not separate the '
        f'{S.term("SLC", "")} from the {S.term("DRAM model", "")}.',
        f'The figure of these rows is in {S.xref("lat-curve")} and their table in {S.xref("lat-table")} '
        f'(chains walked once, file {code(f_large)}).']))
    A(block(
        'open-outside',
        [f'The boot F2 line is flat from {flat_lo["label"]} to {flat_hi["label"]} ({flat_lo["best"]:.3f} ns to '
         f'{flat_hi["best"]:.3f} ns) and reads {rise["best"]:.3f} ns at {rise["label"]}.',
         f'From {flat_hi["label"]} to {mid["label"]} it rises by {mid["best"] - flat_hi["best"]:.1f} ns.',
         f'The SLC holds {SLC_BYTES // M} MiB x {SLC_WAYS - SLC_OCM_WAYS}/{SLC_WAYS} = {V.size_label(slc_est)} est. '
         f'after the OCM ways are taken out (operator\'s README) {r_readme1()}. That size lies between '
         f'{flat_hi["label"]} and {rise["label"]}.',
         f'The {pfl["label"]} chain with every line flushed first reads {pfl["f2"]:.3f} ns on boot F2, '
         f'{pfl["f2"] - D.rt_ns:.3f} ns above the round-trip baseline (file {code(f_fl)}).'],
        [f'The mesh counters cover a whole command: the chain build, the flushes and the untimed walks are '
         f'included. They exist for {n_cmn} CME commands per boot, and no footprint sweep is among them {r_log()}.',
         f'The memory behind the home nodes is an emulator model with no configured delay (operator\'s README) '
         f'{r_readme1()}. So the highest level of these rows is the delay of the RTL stages on the path plus '
         f'that model. It is not the timing of silicon DRAM.'],
        [S.hyp(f'The rise between {flat_hi["label"]} and {mid["label"]} is the chain growing beyond the SLC of '
               f'{V.size_label(slc_est)} est.',
               f'Mesh counts restricted to the timed pass of each footprint, or an SLC hit event per load. '
               f'The hypothesis predicts that the share of loads the SLC serves falls from {rise["label"]} up.')],
        ['Mesh counts per footprint that cover only the timed pass.',
         'A run with a DRAM-like delay profile on the memory model, or silicon, for the level above the SLC.']))

    # ================================================================ 10 smaller items
    A(S.h3('open-small', 'Smaller items'))
    wreps = {(b, s): cc[(b, 'write', s)]['outside_reps'] for b in BOOTS for s in wsz}
    allw = [x for v in wreps.values() for x in v]
    thr = (min(allw) + max(allw)) / 2.0
    lvl_lo, lvl_hi = _median([x for x in allw if x < thr]), _median([x for x in allw if x >= thr])
    n_hi = {b: {s: sum(1 for x in wreps[(b, s)] if x >= thr) for s in wsz} for b in BOOTS}
    hi_sz = [s for s in wsz if n_hi['F1'][s]]
    f1_hi_txt = (f'Boot F1 reads a second level {lvl_hi - lvl_lo:.1f} ns higher (median of the higher reps '
                 f'minus median of the lower reps) in '
                 f'{sum(n_hi["F1"].values())} of the {sum(len(wreps[("F1", s)]) for s in hi_sz)} reps at '
                 f'{labels(hi_sz)}.')
    f2_hi_txt = ('Boot F2 reads one level.' if not sum(n_hi['F2'].values()) else
                 f'Boot F2 reads the higher level in {sum(n_hi["F2"].values())} reps.')
    A(S.bullets([
        '@@NSMALL@@ more observations have no measured cause. Each is smaller than the items above.',
        f'The first one is drawn below. The outside-span time of a write call has two levels on boot F1 and one '
        f'level on boot F2.']))

    def jit(s, bi, i):
        # log2 axis: boot F2 left of the tick, boot F1 right of it, the reps side by side
        return s * 2 ** ((bi - 0.5) * 0.30 + (i - 1) * 0.07)
    near = lambda x: V.size_label(min(wsz, key=lambda s: abs(x / s - 1)))
    y0_small = 10 * int((min(allw) - 3) / 10)          # the y axis starts on a multiple of 10 ns below the dots
    A(S.fig(V.scatter_fit(
        [dict(name=F2N, color='f2', points=[(jit(s, 0, i), x) for s in wsz for i, x in enumerate(wreps[('F2', s)])]),
         dict(name=F1N, color='f1', points=[(jit(s, 1, i), x) for s in wsz for i, x in enumerate(wreps[('F1', s)])])],
        x='log2', xticks=[(s, V.size_label(s)) for s in wsz], xfmt=near, xlabel='bytes per write call',
        ylabel='outside-span time per call, ns', yunit='ns', yfmt=lambda v: V.num(v, 1),
        hlines=[(lvl_lo, 'lower level %.1f ns' % lvl_lo), (lvl_hi, 'higher level %.1f ns' % lvl_hi)],
        yrange=(y0_small, None), width=820, height=320),
        f'Outside-span time of one write call, one dot per rep, kernel {code("cme-write")}, boot F1 and boot F2, '
        f'file {fref(f_cc)}. The dots of one size are set side by side: boot F2 left of the tick, boot F1 right '
        f'of it. The two grey lines are the medians of the reps below and above {thr:.1f} ns. '
        f'The y axis starts at {y0_small} ns, not at 0.',
        f2_hi_txt + ' ' + f1_hi_txt))
    A(S.table(
        ['Bytes per call', 'Boot F1, the reps', 'Boot F2, the reps'],
        [[V.size_label(s), ', '.join(f'{x:.1f}' for x in wreps[('F1', s)]) + ' ns',
          ', '.join(f'{x:.1f}' for x in wreps[('F2', s)]) + ' ns'] for s in wsz],
        caption=f'Outside-span time of one write call, every rep ({code(f_cc)}).', align='lll'))
    sr = {b: D.l1_form(b, 'single-call', 'read') for b in BOOTS}
    slow = {b: l1s[sr[b]['span_gbps'].index(min(sr[b]['span_gbps']))] for b in BOOTS}
    assert slow['F1'] == slow['F2']
    sfit = {b: _source_fit(D, b) for b in BOOTS}
    fit_rows = [r for r in D.chain['F2'] if r['src'] == f_small and r['size'] >= 8 * K]
    oc2 = D.ocm_stats['F2']
    rep_ = D.repeatability
    if sfit['F2']['outer'] < 0:
        fit_verdict = ('The fit gives a negative cost for the outer refill, which has no physical meaning. '
                       'So the fit is rejected, and this page prints its two costs as void.')
    else:
        fit_verdict = 'So the fit is rejected, and this page prints its two costs as void.'
    cp_sizes = sorted(r['size'] for r in D.bw_table('sweep', 'F1', 'copy') if r['size'] > CME_L1_BYTES)
    cp_ratio = {b: {s_: D.bw_row(b, 'sweep', 'copy', s_)['best'] / 2 / D.bw_row(b, 'sweep', 'read', s_)['best']
                    for s_ in cp_sizes} for b in BOOTS}
    cp_mid = [cp_ratio[b][s_] for b in BOOTS for s_ in cp_sizes[:-1]]
    small_rows = [
        ['The outside-span time of a write call has two levels on boot F1 and one on boot F2',
         f'Boot F1 reads {_rng(min(min(wreps[("F1", s)]) for s in wsz), max(max(wreps[("F1", s)]) for s in wsz), 1, "ns")} '
         f'over the reps. Boot F2 reads '
         f'{_rng(min(min(wreps[("F2", s)]) for s in wsz), max(max(wreps[("F2", s)]) for s in wsz), 1, "ns")}. '
         f'{f1_hi_txt} File {code(f_cc)}.',
         'Ten reps per row, to see whether the two levels are stable. A CME cycle count per call on a bandwidth '
         'row, to see whether the CME or the core spends the extra time.'],
        [f'The single-call read is slower at {V.size_label(slow["F1"])} than at '
         f'{labels([s for s in l1s if s != slow["F1"]])}',
         f'Span rate at {labels(l1s)}: ' + ', '.join(f'{x:.1f}' for x in sr['F1']['span_gbps']) +
         ' GB/s on boot F1 and ' + ', '.join(f'{x:.1f}' for x in sr['F2']['span_gbps']) +
         f' GB/s on boot F2. File {code(f_l1s)}.',
         f'Rows at footprints between {V.size_label(l1s[0])} and {V.size_label(l1s[2])}, and CME counters on a bandwidth row.'],
        ['A fit of the chain load on the inner and outer refill counts does not give a cost per source',
         f'Boot F2, {sfit["F2"]["n"]} rep rows from {span_lab([r["size"] for r in fit_rows])}. The model is that '
         f'of the run plan {r_plan13()}: chain load minus the 4 KiB best row ({sfit["F2"]["base"]:.3f} ns) = '
         f'inner refills x b + outer refills x c, with no intercept. {fit_verdict} '
         f'The largest residual is {sfit["F2"]["max_pct"]:.1f} % of the chain load of its row '
         f'({sfit["F1"]["max_pct"]:.1f} % on boot F1). File {code(f_small)}.',
         'A validated L3 hit column, or a row whose refills all come from one source. The inner count mixes at '
         'least two sources.'],
        ['The OCM chain load differs by region with the prefetchers off',
         f'Boot F2, span time: {_rng(oc2["near_lo"], oc2["near_hi"], 3, "ns")} for regions 0 to 2 and '
         f'{_rng(oc2["far_lo"], oc2["far_hi"], 3, "ns")} for regions 3 and 4. Files '
         f'{code("cme-latency-ocm-region0.csv")} to {code("cme-latency-ocm-region4.csv")}. '
         f'The rows are in {S.xref("ocm-chain")}.',
         'The same OCM rows from the CME of another cluster. All rows of these boots ran from CPU 2.'],
        ['Above the CME L1 the read half of a copy is slower than the read kernel alone',
         f'Half of the copy rate against the looped read rate, {span_lab(cp_sizes[:-1])}: '
         f'{min(cp_mid):.2f} to {max(cp_mid):.2f} times (both boots). At {V.size_label(cp_sizes[-1])}: '
         f'{cp_ratio["F1"][cp_sizes[-1]]:.2f} times on boot F1 and {cp_ratio["F2"][cp_sizes[-1]]:.2f} times on '
         f'boot F2. File {code(f_sweep)}. The rows are in {S.xref("bw-copy")}.',
         'CME refill counters on a copy row. The bandwidth program does not offer them.'],
        ['Two files with the same looped row do not agree',
         f'{V.size_label(svl["F1"]["size"])} read: {rep_["F1"]["read16_diff_pct"]:.1f} % apart on boot F1 and '
         f'{rep_["F2"]["read16_diff_pct"]:.1f} % on boot F2. {V.size_label(l1s[0])} write, span rate: '
         f'{rep_["F1"]["write4_span_diff_pct"]:.1f} % apart on boot F1. Files {code(f_sweep)}, {code(f_l1p)} and '
         f'{code(f_cc)}.',
         'Ten reps per row and a second boot with the same settings.']]
    A(S.table(['Observation', 'Rows', 'What would settle it'], small_rows,
              caption='Smaller observations without a measured cause.', align='lll'))
    nh['open-small'] = 1
    A(S.hyp(f'The OCM regions differ because of the distance on the mesh. The home nodes of regions 3 and 4 are '
            f'{oc2["extra_steps"]} steps further from the cluster of CPU 2 than those of regions 0 to 2. '
            f'The position of that cluster on the mesh is itself a hypothesis.',
            'The same OCM rows from the CME of another cluster. If the order of the regions follows the distance '
            'from that cluster, the hypothesis is confirmed. If it stays the same, the cause lies in the regions or in the '
            'address translation.'))

    # ================================================================ 11 not measured
    A(S.h3('open-not', 'Not measured on these boots'))
    ncmd = {b: D.commands[b]['n_cme'] for b in BOOTS}
    cpu2 = {b: sum(1 for c in D.commands[b]['cme_commands'] if re.search(r'--cpus? 2\b', c['text'])) for b in BOOTS}
    A(S.bullets([
        f'Every CME row of both boots runs one thread on CPU 2: {cpu2["F1"]} of {ncmd["F1"]} CME commands on boot F1 '
        f'and {cpu2["F2"]} of {ncmd["F2"]} on boot F2 name CPU 2 {r_log()}.',
        f'The other core of the cluster is offline for the whole CME script {r_runcme()} {r_log()}.',
        'So these boots measure one CME, used by one core. Every latency row returns its value to the core.',
        'The diagram shows what lies outside that.']))
    bw_, bh = 190, 86
    nodes = [
        dict(id='cpu2', x=0, y=40, w=bw_, h=bh, title='CPU 2', lines=['one thread, every CME row'], tag='measured',
             kind='accent'),
        dict(id='cme', x=280, y=40, w=bw_, h=bh, title='CME of this cluster', lines=['streaming mode'],
             tag='measured', kind='accent'),
        dict(id='mem', x=560, y=40, w=bw_, h=bh, title='Memory path', lines=['CME L1, cluster L3, mesh, OCM, DRAM model'],
             tag='measured', kind='accent'),
        dict(id='ret', x=840, y=40, w=bw_, h=bh, title='Value back in the core', lines=['every latency row ends here'],
             tag='measured', kind='accent'),
        dict(id='cpu3', x=280, y=220, w=bw_, h=bh, title='CPU 3', lines=['the other core of the cluster, offline'],
             tag='not measured', tag_style='outline', kind='dashed'),
        dict(id='other', x=0, y=220, w=bw_, h=bh, title='Other CMEs', lines=['the CMEs of the other clusters, no row'],
             tag='not measured', tag_style='outline', kind='dashed'),
        dict(id='kinds', x=560, y=220, w=bw_, h=bh, title='Other access kinds',
             lines=['ZA array, gather, unaligned, copy on OCM'], tag='not measured', tag_style='outline',
             kind='dashed'),
        dict(id='inreg', x=840, y=220, w=bw_, h=bh, title='Chain inside the vector registers',
             lines=['no kernel'], tag='not measured', tag_style='outline', kind='dashed'),
    ]
    arrows = [dict(src='cpu2', dst='cme', label='instruction'), dict(src='cme', dst='mem', label='load, store'),
              dict(src='mem', dst='ret', label='LASTB'),
              dict(src='cpu3', dst='cme', dashed=True), dict(src='kinds', dst='mem', dashed=True),
              dict(src='inreg', dst='ret', dashed=True)]
    A(S.fig(V.boxes(nodes, arrows),
            f'What the CME rows of boot F1 and boot F2 cover (solid boxes) and what no row covers (dashed boxes). '
            f'Source: the command lines of both boots {r_log()} and the kernels in {code("cme_kern.S")} '
            f'{S.ref("cme-kern", "Source file %s: the CME kernels of the latency test and of the bandwidth test." % code("cme_kern.S"))}.',
            'These boots measure one core and one CME. No row covers a dashed box.'))
    o5 = {r['name']: r for r in D.ocm_lat['F2']}
    passes_dram = [r['passes'] for r in D.bw_rows if r['group'] == 'sweep']
    copy_sz = sorted({r['size'] for r in D.bw_rows if r['kernel'] == 'copy'})
    assert {r['group'] for r in D.bw_rows if r['kernel'] == 'copy'} == {'sweep'}
    q = D.quote
    ocm_rd_passes = sorted({r['passes'] for r in D.ocm_bw['F1'] if r['kernel'] == 'read'})
    assert bs['rt_best_lo'] == bs['rt_best_hi']
    cyc = collections.Counter(f'{x:.2f}' for r in D.baseline for x in r['rt_cycles_reps']).most_common()
    cyc_n = sum(c for _, c in cyc)
    cyc_txt = f'It reads {cyc[0][0]} core cycles per step in {cyc[0][1]} of the {cyc_n} rep rows'
    if len(cyc) > 1:
        cyc_txt += f' and {" or ".join(v for v, _ in cyc[1:])} in the other {cyc_n - cyc[0][1]}'
    not_rows = ['The CME itself',
         ['What the round-trip baseline is made of',
          f'The baseline is {D.rt_ns:.3f} ns in all {bs["n_files"]} CME latency files (best rows). {cyc_txt}. '
          f'It is a separate measurement of a kernel with no memory access: a register copy takes the place of '
          f'the load. No row splits it into the issue to the CME, the execution and the return. '
          f'Every chain load also returns its value to the core through LASTB. No row calibrates the non-memory '
          f'cost that the chain kernel and the baseline kernel share. So the chain load minus the baseline is a '
          f'difference between two kernels. It is not identified as memory-access time.',
          'A waveform of one DUP+LASTB step from the RTL, or the interface timing in the Arm technical reference '
          'manual of the C1-SME2. A calibration of the non-memory cost that the two kernels share.'],
         ['A load-to-use time that stays in the vector registers',
          'Every latency row returns the value to the core through LASTB.',
          'A kernel with a dependent load chain inside the CME.'],
         ['Access kinds that no kernel runs',
          f'Loads and stores of the {S.term("ZA array", "")}, gather loads, vectors that are not aligned to 64 bytes '
          f'or that cross a page, loads with a partial predicate (other than the 8-byte chain load), a store followed '
          f'by a load of the same line.',
          f'New kernels in {code("cme_kern.S")}.'],
         ['Copy rows beyond the looped sweep',
          f'The copy kernel exists only in the looped sweep (looped form, '
          f'{V.size_label(copy_sz[0])} to {V.size_label(copy_sz[-1])}). No single-call copy and no copy on the OCM '
          f'exist.',
          'Copy rows in the single-call form, below 16 KiB, and on the OCM.'],
         ['A write rate with a known destination level',
          f'The OCM write ({q["ocm_write_F1"]:.1f} GB/s on boot F1, {q["ocm_write_F2"]:.1f} GB/s on boot F2) is '
          f'the only write row under the mesh counters. The destination of no other write row is known.',
          'CME counters on a bandwidth row, and write rows under the mesh counters.'],
         ['CME bandwidth rows with counters',
          f'The bandwidth program refuses its counter option together with the CME option {r_bwc()}.',
          'A CME counter set in the bandwidth program.'],
         'Sharing',
         ['Two cores of one cluster in streaming mode at once',
          f'CPU 3 is offline in every CME command. The program takes one worker with the CME option, because the '
          f'two stamps of a span are one global pair {r_bwc()}.',
          'A CME read and write on CPUs 2 and 3 together. The program needs stamps per thread first.'],
         ['More than one CME at once',
          f'No row runs the CMEs of two clusters together, and no CME row runs on a CPU other than CPU 2 '
          f'{r_cmeplan()}. So the aggregate CME bandwidth and the behaviour of the other CMEs are not known.',
          'The same script pinned to a core of another cluster, and one run with several clusters at once.'],
         'Conditions',
         ['A repeat of a boot',
          f'Boots that were repeated: {rep_["all"]["boots_repeated"]}. Inside one boot the round-trip baseline reads '
          f'{rep_["all"]["rt_lo"]:.3f} ns in all {rep_["all"]["rt_files"]} files.',
          'A second boot with the settings of boot F1 and one with the settings of boot F2.'],
         ['The core with the prefetchers off and the L3 on',
          f'Boot F2 ran {D.commands["F2"]["n_core"]} core commands. So the core rows beside the CME exist on boot F1 '
          f'only.',
          'The core script on a boot with the firmware of boot F2.'],
         ['CME rows with the cluster L3 off', 'Both boots have the L3 on.',
          'The CME script on a boot with the L3 in its mode that holds no data.'],
         ['OCM against DRAM bandwidth under the same conditions',
          f'An OCM read row is {ocm_rd_passes[0]} pass after a flush. Every row of the sweep on the DRAM model runs '
          f'{min(passes_dram)} to {max(passes_dram)} passes after a warm-up pass, with no flush.',
          'Rows on the DRAM model with a flush before one pass, at 256 KiB and at 1,280 KiB.'],
         ['The cost of address translation',
          f'The CME rows carry no TLB counter. The OCM rows use 4 KiB pages and the rows on the DRAM model use 2 MiB '
          f'pages. The two OCM chain shapes agree within '
          f'{abs(o5["all5"]["best_span"] - o5["all5-dense"]["best_span"]):.3f} ns in the span on boot F2 '
          f'({o5["all5"]["best_span"]:.3f} ns and {o5["all5-dense"]["best_span"]:.3f} ns). Both walk the pages in '
          f'random order, so this does not bound the cost. The chain of one line per 4 KiB page touches '
          f'{o5["all5"]["loads"]} pages, more than the {CME_TLB_ENTRIES} entries of the TLB of the CME '
          f'(operator\'s README) {r_readme1()}.',
          'The same OCM rows on a mapping of 64 KiB or 2 MiB pages, with the prefetchers off and the L3 on.'],
         ['Chip time against silicon',
          f'All times are chip time at a measured {cpn:.2f} core cycles per ns. No file says whether the clock of '
          f'the silicon target is 2 GHz.',
          'The clock specification of the design.'],
         ['A chain in address order',
          f'No row. One row of a third boot is shown in {S.xref("open-addr")}.',
          'The address-order command on both boots.']]
    n_not = sum(1 for r in not_rows if not isinstance(r, str))
    # a fixed width for the first column, so that a row title takes at most two lines
    not_rows = [r if isinstance(r, str) else
                ['<span style="display:inline-block;min-width:215px">%s</span>' % r[0]] + r[1:] for r in not_rows]
    A(S.table(['Not measured', 'What the rows of these boots show', 'What would measure it'], not_rows,
              caption='Rows that do not exist on boot F1 or boot F2.', align='lll'))
    A(S.insufficient('Each line of the table above is a measurement that these boots do not hold. '
                     'The right column names the row that would supply it.'))

    # ================================================================ 12 address order
    A(S.h3('open-addr', 'A chain in address order: one row from a third boot'))
    hd = ao['header']
    r_ao = S.ref('addr-file', 'File %s, line %d (header), line %d (the best rep) and line %d (the best row). This '
                 'is the only row on this page that does not come from boot F1 or boot F2.' % (
                     code(ao['src']), ao['header_line'], ao['rep_line'], ao['best_line']))
    r_ao_readme = S.ref('addr-readme', "Operator's README of that boot, %s, lines 3, 7 and 8: the cluster L3 in "
                        "full mode, the data prefetchers on, the OCM in 4 KiB translations, program commit "
                        "<code>b79dffa</code>." % code('results/membench-jibin-010/README.md'))
    A(S.bullets([
        'Boot F1 and boot F2 have no chain in address order. In that chain kind each line holds the address of the next line of the buffer.',
        f'A third boot with the L3 on and the prefetchers on has one such row: {ao["best"]:.3f} ns per load at '
        f'{V.size_label(ao["size"])} with every line flushed first, {ao["above_rt"]:.3f} ns above the round-trip '
        f'baseline of the same file {r_ao}.']))
    A(S.fig(V.hbar(
        [dict(label='Round-trip baseline', sub='boot F1 and boot F2, no memory access', value=D.rt_ns,
              color='#8a9099'),
         dict(label='Address order, third boot (prefetchers on)',
              sub='%s, every line flushed first' % V.size_label(ao['size']),
              value=ao['best'], color='alt', note='(%s above its baseline)' % V.ns(ao['above_rt'])),
         dict(label='Random order, boot F1 (prefetchers on)', sub='%s, every line flushed first' % pfl['label'],
              value=pfl['f1'], color='f1'),
         dict(label='Random order, boot F2 (prefetchers off)', sub='%s, every line flushed first' % pfl['label'],
              value=pfl['f2'], color='f2')],
        unit='ns', fmt=lambda v: V.num(v, 3), xlabel='chain load, ns', width=900),
        f'Chain load at {pfl["label"]} with every line flushed first, best rows. Violet: the address-order chain of a third '
        f'boot, file {code(ao["name"])} {r_ao}. Orange and blue: the random-order chains of boot F1 and boot F2, file '
        f'{code(f_fl)}. Grey: the round-trip baseline of boot F1 and boot F2.',
        f'In address order with the prefetchers on, the chain load reads {ao["best"]:.3f} ns. That is '
        f'{ao["above_rt"]:.3f} ns above the separate round-trip baseline row of its file.'))
    A(S.table(
        ['Condition of the address-order row', 'Value', 'Source'],
        [['Cluster L3', 'on (the operator\'s README calls it full mode)', "operator's README %s" % r_ao_readme],
         ['Hardware prefetchers', 'on', "operator's README %s" % r_ao_readme],
         ['OCM translations', '4 KiB', "operator's README %s" % r_ao_readme],
         ['Program build', 'another commit than boot F1 and boot F2, with no span column',
          "operator's README %s" % r_ao_readme],
         ['CPU and memory', 'CPU %s, %s, huge pages (<code>backing=%s</code> in the file)' % (
             hd['cpu'], hd['mem'].upper(), ao['size_line']['backing']),
          'file header'],
         ['Chain', f'{V.size_label(ao["size"])}, {V.num(int(ao["size_line"]["lines"]), 0)} lines, address order '
                   f'(<code>seq={hd["seq"]}</code>), every line flushed first (<code>flush={hd["flush"]}</code>), '
                   f'walked once per rep', 'file header'],
         ['Best chain load', f'{ao["best"]:.3f} ns', 'file, best row'],
         ['Round-trip baseline of the same file', f'{ao["rt"]:.3f} ns', 'file'],
         ['Prefetch refills per load', f'{ao["hwprf"]:.4f}', 'file, best rep'],
         ['Outer refills per load', f'{ao["outer"]:.4f}', 'file, best rep'],
         ['Read refills per load', f'{ao["rd_txt"]} as printed', 'file, best rep'],
         ['Loads per timed pass', V.num(ao['loads'], 0), 'file, each rep row'],
         ['Read refills per timed pass',
          f'{ao["rd_events"]} in each of the {ao["n_passes"]} timed passes (count per load x loads, rounded to a '
          f'whole event)', 'computed from the file']],
        caption=f'Conditions and counters of the address-order row (file {code(ao["name"])} of the third boot {r_ao}).', align='lll'))
    A(S.bullets([
        f'The row counts {ao["hwprf"]:.2f} prefetch refill and {ao["outer"]:.2f} outer refill per load.',
        f'It also counts {ao["rd_events"]} read refills in each of its {ao["n_passes"]} timed passes of '
        f'{V.num(ao["loads"], 0)} loads. The file prints {ao["rd_txt"]} read refills per load, and that count '
        f'times the loads gives {ao["rd_events"]}.',
        'So the refills are almost all attributed to the prefetcher. The counts are totals of a pass. They do '
        'not show that the prefetcher requested every line of the chain.',
        'The row comes from another boot and another program build. It shows the case and does not belong to the '
        'results of boot F1 or boot F2.',
    ]))
    A(S.insufficient('No address-order chain exists with the L3 on and the prefetchers off. '
                     'The address-order command on boot F2 would give the value with no prefetched lines.'))

    # ================================================================ 13 statements
    A(S.h3('open-claims', 'Statements the data do not support'))
    A(S.bullets([
        'Each statement below is close to a number on this page. The rows of boot F1 and boot F2 do not '
        'support it. The right column says what the rows do show.',
        f'The statements about fits and about the write rate are in {S.xref("glance-noquote")}. The statements '
        f'about the cost of a call are in {S.xref("callcost-quote")}. They are not repeated here.']))
    o1 = D.ocm_lat['F1']
    one_reg1 = [r for r in o1 if r['region'] is not None]
    r_ocm = min(one_reg1, key=lambda r: r['best'])
    pm = [p for p in D.chain_pairs if p['kind'] == many]
    po = [p for p in D.chain_pairs if p['kind'] == once]
    assert all(p['f1_minus_f2'] > 0 for p in pm)
    po_hi = [p['size'] for p in po if p['f1_minus_f2'] > 0]
    po_lo = [p['size'] for p in po if p['f1_minus_f2'] <= 0]
    assert po_hi and po_lo and max(po_hi) < min(po_lo) and pfl['f1_minus_f2'] < 0
    cl256 = cl_best
    A(S.table(
        ['Statement', 'What the rows show'],
        [[f'"An L3-served CME load takes {cl256["best"]:.1f} ns."',
          f'The {cl256["label"]} row of boot F2 reads that. The exploratory hit event counts only '
          f'{_rng(hit_peak["hit_min"], hit_peak["hit_max"], 2)} L3 hits per load at that footprint, and the '
          f'event is not validated.'],
         ['"The L3 supplies X % of the refills of the CME."',
          'The split into hits and misses depends on a reading of the RTL with no control row.'],
         ['"The prefetcher causes every difference between boot F1 and boot F2."',
          'The boots also differ in what ran before the CME rows and in the placement of each buffer. '
          'No boot was repeated.'],
         ['"The prefetcher of the CME helps" or "hurts", as a general rule',
          f'With the prefetchers on the chain load is higher on all {len(pm)} chains walked many times '
          f'({span_lab([p["size"] for p in pm])}) and on the chains walked once from {span_lab(po_hi)}. '
          f'It is lower on the chains walked once at {labels(po_lo)} and on the {pfl["label"]} chain with every '
          f'line flushed first. The looped read rate at {r32["label"]} is {1 / r32["f2_over_f1"]:.1f} times '
          f'higher with the prefetchers on.'],
         [f'"The OCM costs {r_ocm["best"]:.0f} ns through the CME."',
          f'That is the bracket time of one region on boot F1 ({r_ocm["best_span"]:.1f} ns in the span). '
          f'The one-region rows of boot F1 count '
          f'{_rng(min(r["hwprf_min"] for r in one_reg1), max(r["hwprf_max"] for r in one_reg1), 2)} prefetch '
          f'refills per load. With the prefetchers off (boot F2) the regions read '
          f'{_rng(oc2["near_lo"], oc2["far_hi"], 3, "ns")} in the span.'],
         ['"Two cores that share a CME each get half", or any sum over several CMEs',
          'No such row exists.'],
         ['"The outer refills are DRAM reads."',
          'Outer means outside the cluster: the SLC, the OCM or the DRAM model.'],
         ['"The span rate is the rate of the memory path."',
          'Every bandwidth number is the rate of a whole kernel: loads, XOR instructions and loop instructions '
          'are included.'],
         ['"A refill count of 0.5 per load means that half the loads missed."',
          'The refill events count lines that enter the CME L1. They do not say which load waited for which '
          'line.'],
         [f'"A 64-byte load takes {svl["F1"]["read_cycles_per_64b"]:.2f} cycles" or "a 64-byte store takes '
          f'{svl["F1"]["write_cycles_per_64b"]:.2f} cycles."',
          f'Those values are effective cycles per 64 bytes transferred: 64 bytes divided by the throughput of a '
          f'whole loop ({SVL}, single-call form, span time, boot F1). Each load or store instruction of the loop '
          f'transfers four 64-byte vectors, and the read loop also runs XOR instructions. '
          f'No row times one load or one store ({S.xref("open-store")}).'],
         ['"A chain load is the round-trip baseline plus the time of the memory access."',
          f'The round-trip baseline ({D.rt_ns:.3f} ns) is a separate measurement of a kernel with no memory '
          f'access. The chain load minus the baseline is a difference between two kernels. No row calibrates '
          f'the non-memory cost that the two kernels share. So the difference is not identified as '
          f'memory-access time.'],
         ['"Each rep refills every line of the chain one time."',
          f'The rep rows of boot F2 count about one inner refill per line of the chain '
          f'({_rng(rps["per_line_lo"], rps["per_line_hi"], 2)} as printed, {RPL}). That is a total over one '
          f'rep. It does not say which lines were refilled, or at which time in the rep '
          f'({S.xref("open-refill")}).'],
         ['"Every other CME behaves like this one."', 'Only the CME of the cluster of CPU 2 is measured.']],
        caption='Statements that the rows of boot F1 and boot F2 do not support.', align='ll'))
    html_ = ''.join(out)
    for id_, n in nh.items():
        html_ = html_.replace('@@H:%s@@' % id_, '%d' % n)
    assert '@@H:' not in html_
    words = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve']
    return (html_.replace('@@NOPEN@@', words[len(open_items)]).replace('@@NSMALL@@ more', words[len(small_rows)] + ' more')
            .replace('@@NSMALL@@', words[len(small_rows)].lower()).replace('@@NNOT@@', '%d' % n_not))
