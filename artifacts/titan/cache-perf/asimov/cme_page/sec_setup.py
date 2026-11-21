"""Section 1 of the page, "What was measured", and the page's Short version.

build(D, V, S)          -> html of the section body (platform, boots, tests, counters, clock, integrity)
short_version(D, V, S)  -> html of the Short version: three sentences, the headline figure, four stat tiles

Every measured number is read from the data layer D at build time.  Facts that
exist only in a document, in the source code or in the operator's README are
typed here and carry a reference.
"""
import os
import re

from . import data as _data

KEY = 'setup'
TITLE = 'What was measured'

KIB = 1024
MIB = 1024 * 1024
BOOTS = ('F2', 'F1')            # page order: the demand-only boot first
COLOR = {'F1': 'f1', 'F2': 'f2'}

# ---- typed facts (not measurements): each one is cited where it is used ----
CME_L1_KIB = 64                 # Arm C1-SME2 TRM 107831 section 6 (document not on disk)
SLC_NODES = 5                   # operator's README: five home nodes
SLC_NODE_MIB = 1                # operator's README: 1 MiB each
SLC_WAYS = 16                   # operator's README: 16 ways per home node
OCM_WAYS = 4                    # operator's README: 4 ways of each home node locked as OCM
CME_TLB = 24                    # operator's README: entries of the CME's TLB
CALLS_PER_CME_CALL_ROW = 64     # latency.c: calls timed in one bracket by a cme-call row


# ------------------------------------------------------------------ small helpers

def _rng(lo, hi, digits=3, unit=''):
    """'21.015 to 21.240 ns', or one value when both ends print the same."""
    a, b = '%.*f' % (digits, lo), '%.*f' % (digits, hi)
    u = (' ' + unit) if unit else ''
    return (a + u) if a == b else '%s to %s%s' % (a, b, u)


def _n(v):
    return '{:,}'.format(int(v))


def _code(s):
    return '<code>%s</code>' % s


def _rel(D, boot):
    """Boot folder relative to the project folder."""
    return _data.BOOTDIR[boot].replace(_data.ROOT + '/', '')


def _fref(S, D, boot, name, lines=None):
    """Reference to one raw file of a boot (key 'file:<boot>:<name>[:<lines>]')."""
    key = 'file:%s:%s' % (boot, name) + ((':' + lines) if lines else '')
    text = 'B%s, file %s%s.' % (D.boot_name[boot][1:], _code('%s/%s' % (_rel(D, boot), name)),
                                (', ' + lines) if lines else '')
    return S.ref(key, text)


def _runref(S, D, boot, name, lines=None):
    """Reference to a file of the run folder (dmesg.txt, SHA256SUMS)."""
    run = _data.RUN[boot].replace(_data.ROOT + '/', '')
    key = 'run:%s:%s' % (boot, name) + ((':' + lines) if lines else '')
    text = 'B%s, file %s%s.' % (D.boot_name[boot][1:], _code('%s/%s' % (run, name)), (', ' + lines) if lines else '')
    return S.ref(key, text)


def _readme(S, D, boot, topic, lines):
    run = _data.RUN[boot].replace(_data.ROOT + '/', '')
    return S.ref('readme:%s:%s' % (boot, topic),
                 "Operator's README of b%s, file %s, %s." % (D.boot_name[boot][1:], _code(run + '/README.md'), lines))


def _src(S, key, name, lines, what):
    return S.ref('src:' + key, 'Benchmark source, file %s, %s: %s.' % (_code(name), lines, what))


def _dot(boot):
    return ('<span style="display:inline-block;width:9px;height:9px;border-radius:50%%;background:%s;'
            'margin-right:5px;vertical-align:baseline"></span>' % {'F1': '#eb6834', 'F2': '#2a78d6'}[boot])


def _nb(html):
    """Keeps a run of text (a file name, a pair of references) on one line."""
    return '<span style="white-space:nowrap">%s</span>' % html


def _neutral(svg):
    """Draws the highlighted boxes of a V.boxes diagram with an ink outline and a grey fill.
    The blue of the builder's 'accent' style means boot F2 on this page, so a box must not use it."""
    return svg.replace('fill="#eef4fc" stroke="#2a78d6" stroke-width="1.2"',
                       'fill="#eceef1" stroke="#1c2024" stroke-width="1.5"')


def _cme_lat_files(D, boot):
    return [f for f in D.files[boot]['latency'] if f.startswith('cme-')]


def _l3_files(D, boot):
    """The CME latency files whose rows carry the three L3 event columns."""
    return [f for f in _cme_lat_files(D, boot)
            if any('l3d' in c for blk in D.latblocks(boot, f) for c in blk['columns'])]


def _file_counts(D):
    """(CME latency files, files without the L3 columns, files with them), the same on both boots."""
    out = set()
    for b in BOOTS:
        n, n3 = len(_cme_lat_files(D, b)), len(_l3_files(D, b))
        assert n == D.integrity[b]['n_cme_latency_files']
        out.add((n, n - n3, n3))
    assert len(out) == 1, out
    return out.pop()


def _terms(S):
    """Terms this section uses.  The first definition of a name wins."""
    t = S.term
    t('CME', 'the Arm C1-SME2 matrix engine unit. Each cluster has one, and the two cores of the cluster share it.')
    t('cluster', 'two cores that share an L2 cache, an L3 cache, one CME and one port to the mesh. '
                 'Arm calls it a DSU (DynamIQ Shared Unit).')
    t('core', 'one Arm C1-Nano processor. Linux numbers the ten cores CPU 0 to CPU 9.')
    t('streaming mode', 'the processor state between the instructions SMSTART and SMSTOP. '
                        'In it, vector loads and stores run on the CME.')
    t('kernel', 'one test loop written in assembly in the file <code>cme_kern.S</code>. '
                'On this page the word never means the Linux kernel.')
    t('chain load', 'one load of the latency test. It loads 8 bytes through the CME, and the loaded value is the '
                    'address of the next load. The instruction LASTB returns that value to the core.')
    t('latency test', 'the loop of chain loads. Its result is the time per chain load in ns.')
    t('round-trip baseline', 'the row <code>cme-roundtrip</code>: the same loop as the latency test with a register '
                             'copy (DUP) in place of the load. It touches no memory. It is a separate '
                             'measurement, not a part of a chain load.')
    t('footprint', 'the size of the buffer that a test walks.')
    t('bracket time', 'the time between two clock reads in C, one before the kernel call or calls and one after.')
    t('span time', 'the time between two timer reads inside the kernel, the first after SMSTART and the second '
                   'before SMSTOP.')
    t('outside-span time', 'bracket time minus span time.')
    t('pass', 'one walk over the whole buffer or the whole chain.')
    t('rep', 'one timed measurement. It is one data row of a CSV file and can hold many passes.')
    t('best row', 'the row that the test program itself prints with the label <code>best</code>: the lowest ns per '
                  'load of a latency footprint, or the highest GB/s of a bandwidth command.')
    t('looped form', 'the bandwidth test with one kernel call per pass.')
    t('single-call form', 'the bandwidth test with all passes of a rep inside one kernel call.')
    t('fold', 'the XOR of all loaded 8-byte words into one value, which the read kernels return.')
    t('refill', 'the arrival of one 64-byte line in the CME L1 cache after a miss or a prefetch.')
    t('prefetcher', 'hardware that loads lines into a cache before the program asks for them.')
    t('mesh', 'the on-chip network (Arm CMN) that joins the clusters, the home nodes and the bridges to memory. '
              'A move from one crosspoint to the next is one step.')
    t('home node', 'a mesh node that owns a range of addresses. Each of the five holds one part of the SLC and '
                   'one OCM region.')
    t('SLC', 'system level cache: the cache inside the mesh, held by the five home nodes.')
    t('OCM', 'on-chip memory: cache ways of the home nodes that the firmware locks and maps as memory. '
             'Five regions of 256 KiB.')
    t('DRAM model', 'the memory behind the mesh on this emulator. It is an emulator memory model, not silicon DRAM '
                    'timing.')
    t('GB/s', 'gigabytes per second, with 1 GB = 1,000,000,000 bytes. 1 GB/s equals 1 byte per ns.')
    t('chip time', "time on the emulated chip's own clock. Every time on this page is chip time.")
    t('PMU', "performance monitoring unit: the core's event counters.")
    t('counting window', 'the interval between the counter start and the counter stop of one latency row. '
                         'In the code the counter start comes before the first clock read of the bracket, and '
                         'the counter stop comes after the second clock read.')
    t('ISB', 'an instruction that makes the core finish the instructions in flight before the next one starts.')
    t('DSB ST', 'a barrier instruction that waits until the stores before it are complete.')
    t('DSB SY', 'a barrier instruction that waits until all memory accesses before it are complete.')
    t('snoop', 'a request to another cache of the cluster for a line that it holds.')
    t('TRM', 'Arm Technical Reference Manual.')
    t('TF-A', "Trusted Firmware-A: the firmware stage that sets the prefetcher controls before Linux starts "
              "(operator's README).")
    t('LD1D, LD1B', 'vector load instructions. LD1D loads 8-byte elements, LD1B loads bytes.')
    t('ST1B', 'a vector store instruction.')
    t('LASTB', 'an instruction that copies the last active element of a vector to a register of the core.')
    t('DUP', 'an instruction that copies a register of the core into a vector.')
    t('EOR', 'the XOR instruction.')
    t('SMSTART, SMSTOP', 'the instructions that enter and leave streaming mode.')
    t('SOG', 'Arm Software Optimization Guide.')
    t('SHA-256 checksum', 'a 256-bit value computed from the bytes of a file. Two files with the same checksum '
                          'have the same content.')


# ------------------------------------------------------------------ derived values (outside D)

def _g1(D, boot):
    return {r['key']: r for r in D.g1[boot]}


def _l1_rows(D, boot):
    """The chain rows behind the 'CME L1' entry of D.g1 (the smallest footprints of the sweep)."""
    g = _g1(D, boot)['l1']
    rows = sorted(D.chain_sweep(boot), key=lambda r: r['size'])[:g['n_rows']]
    assert abs(min(r['best'] for r in rows) - g['bracket_lo']) < 1e-9
    assert abs(max(r['best'] for r in rows) - g['bracket_hi']) < 1e-9
    return rows


def _levels(D):
    """Six rows for the headline figure and the table under the path diagram.
    Each row: where, cond, the best bracket ns of both boots, and (inner, outer, prefetch) refills per load."""
    out = []
    l2, l1 = _l1_rows(D, 'F2'), _l1_rows(D, 'F1')
    cnt = lambda r: (r['inner'], r['outer'], r['hwprf'])
    for i in (0, -1):
        assert l2[i]['size'] == l1[i]['size']
        out.append(dict(where='CME L1', cond='%s, %s' % (l2[i]['label'], l2[i]['kind']),
                        F2=l2[i]['best'], F1=l1[i]['best'], c2=cnt(l2[i]), c1=cnt(l1[i]), src=l2[i]['src'], key='l1',
                        label=l2[i]['label']))
    for key in ('cluster', 'outside-3m', 'ocm', 'dram'):
        a, b = _g1(D, 'F2')[key], _g1(D, 'F1')[key]
        cond = a['conditions']
        if key == 'ocm':
            r = [x for x in D.ocm_lat['F2'] if x['src'] == a['src']][0]
            assert r['shape'] == 'every line' and r['kind'] == 'every line flushed first'
            cond = 'all %d regions (%s), chain over every line, flushed first' % (r['segments'], r['label'])
        g = lambda r: (r['inner_lo'], r['outer_lo'], r['hwprf_lo'])
        out.append(dict(where=a['where'], cond=cond, F2=a['bracket_lo'], F1=b['bracket_lo'], c2=g(a), c1=g(b),
                        src=a['src'], key=key, label=cond.split(',')[0]))
    return out


def _hwprf_reps(D, boot):
    """Prefetch refills per load of every chain rep row that carries the column."""
    vals = []
    for f in D.files[boot]['latency']:
        if not f.startswith('cme-'):
            continue
        for blk in D.latblocks(boot, f):
            for e in blk['sizes'].values():
                vals += [r['hwprf'] for r in e['reps'] if r.get('hwprf') is not None]
    return vals


def _cause_minus_source(D, boot):
    """Largest |inner + outer - rd - hwprf - wr| per load, and the number of rep rows."""
    worst, n = 0.0, 0
    for f in D.files[boot]['latency']:
        if not f.startswith('cme-'):
            continue
        for blk in D.latblocks(boot, f):
            for e in blk['sizes'].values():
                for r in e['reps']:
                    if r.get('rd') is None:
                        continue
                    n += 1
                    worst = max(worst, abs(r['inner'] + r['outer'] - r['rd'] - r['hwprf'] - r['wr']))
    return worst, n


def _commit(D, boot):
    """Short commit id in the program path of every command line of the log."""
    ids = set(re.findall(r'cache-mem-perf-([0-9a-f]{7,40})/', ' '.join(c['raw'] for c in D.commands[boot]['commands'])))
    return sorted(ids)


def _bw_counts(D, boot):
    """Best rows per (kernel, form) of one boot, DRAM-backed and OCM together."""
    out = {}
    for r in [r for r in D.bw_rows if r['boot'] == boot] + list(D.ocm_bw[boot]):
        k = (r['kernel'], r['form'])
        out[k] = out.get(k, 0) + 1
    return out


def _lat_counts(D, boot):
    """Footprint best rows, and files with a round-trip baseline, of the CME latency files."""
    sizes = files = 0
    for f in D.files[boot]['latency']:
        if not f.startswith('cme-'):
            continue
        for blk in D.latblocks(boot, f):
            sizes += len(blk['sizes'])
            files += 1 if blk.get('rt') else 0
    return sizes, files


# ------------------------------------------------------------------ Short version

def _tile(label, lines, sub):
    return ('<div style="border:1px solid #d9dde2;border-radius:8px;background:#fff;padding:10px 12px">'
            '<div style="font-size:12.5px;color:#4a5058;font-weight:600">%s</div>%s'
            '<div style="font-size:12px;color:#6b7280;margin-top:4px;line-height:1.35">%s</div></div>' % (
                label, ''.join('<div style="font-size:15.5px;font-weight:650;line-height:1.55;white-space:nowrap">%s</div>'
                               % x for x in lines), sub))


def _single_rows(D, boot, kernel):
    """Single-call rows of one kernel: the L1 file and the sweep file together."""
    return D.bw_table('l1-single', boot, kernel) + D.bw_table('sweep-single', boot, kernel)


def _size_span(V, rows):
    sizes = sorted(set(r['size'] for r in rows))
    return '%s to %s' % (V.size_label(sizes[0]), V.size_label(sizes[-1]))


def short_version(D, V, S):
    """The Short version of the page: three sentences, Figure 1 (critic G1) and four bandwidth tiles."""
    _terms(S)
    q = D.quote
    lv = _levels(D)
    n_files = D.baseline_summary['all']['n_files']
    lat_names = ('cme-latency-dram-small.csv', 'cme-latency-dram-large.csv', 'cme-latency-ocm-all5-dense.csv',
                 'cme-latency-dram-flushed.csv')
    r_lat2 = [_fref(S, D, 'F2', n) for n in lat_names]
    r_lat1 = [_fref(S, D, 'F1', n) for n in lat_names]
    r_single = [_fref(S, D, b, 'cme-bandwidth-l1-asmpasses.csv') for b in BOOTS]
    r_ss = [_fref(S, D, b, 'cme-bandwidth-dram-1core-asmpasses.csv') for b in BOOTS]
    r_sweep = [_fref(S, D, b, 'cme-bandwidth-dram-1core.csv') for b in BOOTS]
    f2v = [x['F2'] for x in lv]

    g2 = _g1(D, 'F2')
    l1_bytes = CME_L1_KIB * KIB
    assert abs(g2['dram']['bracket_lo'] - max(f2v)) < 1e-9 and abs(g2['l1']['bracket_lo'] - min(f2v)) < 1e-9
    # the differences of the Short version are the printed times minus the baseline row
    assert abs(g2['l1']['bracket_lo'] - D.rt_ns - g2['l1']['above_rt_lo']) < 1e-9
    assert abs(g2['l1']['bracket_hi'] - D.rt_ns - g2['l1']['above_rt_hi']) < 1e-9
    assert abs(g2['dram']['bracket_lo'] - D.rt_ns - g2['dram']['above_rt_lo']) < 1e-9
    text = (
        '<p>This page reports how fast the CME (the Arm C1-SME2 matrix engine unit, shared by the two cores of '
        'one cluster) loads and stores memory on the Asimov chip, which runs on a hardware emulator, and the '
        'tiles under Figure %d give its read and write rates. '
        'With the hardware prefetchers off (boot F2), one chain load (a test load whose value is the address of '
        'the next load) takes %s for buffers that fit in the L1 cache of the CME and %s in the DRAM-model row '
        '%s %s. '
        'These times are %s and %s above the separate register-only measurement of %s (the round-trip baseline), '
        'and the differences do not isolate memory-access time.</p>\n'
        '<p class="fnote">Boot F1 has the prefetchers on. Its values are in the figure and in the tiles. '
        'A prefetcher loads data into a cache before the program asks for it. '
        'The DRAM model is an emulator memory model, not silicon timing.</p>\n' % (
            S.next_fig(), _rng(g2['l1']['bracket_lo'], g2['l1']['bracket_hi'], 3, 'ns'),
            V.ns(g2['dram']['bracket_lo'], 3), r_lat2[0], r_lat2[3],
            _rng(g2['l1']['above_rt_lo'], g2['l1']['above_rt_hi'], 3, 'ns'), V.ns(g2['dram']['above_rt_lo'], 3),
            V.ns(D.rt_ns, 3)))

    # ---- Figure 1
    f3 = lambda v: V.num(v, 3)
    rows = []
    for x in lv:
        rows.append(dict(label=x['where'], sub=x['cond'], a=x['F2'], b=x['F1'],
                         tip='%s, %s\nb%s: %s ns (%s above the round-trip baseline row, a separate measurement)\n'
                             'b%s: %s ns\nboot F1 minus boot F2: %s' % (
                             x['where'], x['cond'], D.boot_name['F2'][1:], f3(x['F2']),
                             V.ns(x['F2'] - D.rt_ns, 3),
                             D.boot_name['F1'][1:], f3(x['F1']), V.signed(x['F1'] - x['F2'], 3, 'ns'))))
    svg = V.dumbbell(rows, a_name='b' + D.boot_name['F2'][1:], b_name='b' + D.boot_name['F1'][1:],
                     a_color='f2', b_color='f1', unit='ns', xlabel='chain load, ns (bracket time, best row)',
                     fmt=lambda v: V.num(v, 2), gap_fmt=lambda a, b: V.signed(b - a, 2, 'ns'),
                     refs=[(D.rt_ns, 'round-trip baseline %s' % V.ns(D.rt_ns))], xrange=(0, None), label_w=330,
                     width=970)
    higher = sum(1 for x in lv if x['F1'] > x['F2'])
    rising = all(b > a for a, b in zip(f2v, f2v[1:]))
    take = ('On boot F2 (blue) %s, from %s to %s. The separate round-trip baseline reads %s. The first row is %s '
            'above it, and the last row is %s above it. Boot F1 (orange) reads higher in %d of the %d rows.' % (
                'each row costs more than the row above it' if rising else 'the rows do not rise in order',
                V.ns(f2v[0], 2), V.ns(f2v[-1], 2), V.ns(D.rt_ns), V.ns(f2v[0] - D.rt_ns, 3),
                V.ns(f2v[-1] - D.rt_ns, 3), higher, len(lv)))
    pf2 = [x['c2'][2] for x in lv]
    pf1 = [x['c1'][2] for x in lv]
    assert max(pf2) == 0.0 and min(pf1) > 0.0, (pf2, pf1)
    top = lv[1]                                # the largest footprint of the CME L1 rows
    cap = ('What a CME chain load costs, by where the line comes from. A chain load is one 8-byte load through the '
           'CME whose value is the address of the next load, and a line is 64 bytes of memory, the unit that a '
           'cache holds. Each row is the best row of one footprint (buffer size) on b%s and on b%s, and the gap at '
           'the end of a row is boot F1 minus boot F2. The grey line is the round-trip baseline. It is a separate '
           'measurement: the loop of the test with a register copy in place of the load, and with no memory '
           'access.' % (D.boot_name['F2'][1:], D.boot_name['F1'][1:]))
    note = ('Words in the row labels: a cluster is two cores that share an L3 cache and one CME. OCM (on-chip '
            'memory) is memory inside the mesh, which is the on-chip network. The DRAM model is an emulator memory '
            'model, not silicon timing. "Walked many times": the test walks one chain again and again inside a '
            'timed measurement. "Walked once": each timed measurement loads every line of its chain one time. '
            '"Flushed first": the core removes every line of the buffer from the caches before each timed '
            'measurement. '
            'The row names describe boot F2. Its counters show %s prefetch refills per load in these rows (a refill '
            'is the arrival of one line in the CME L1 cache). '
            'On boot F1 every row counts prefetch refills, %s per load. Its %s row counts %s refills per load from '
            'outside the cluster. So a boot F1 value is not the cost of one place. '
            'The rows do not share one setup, and %s lists the limits. '
            'The round-trip baseline reads the same in all %d CME latency files of the two boots. '
            'A row minus the baseline is the measured difference between two kernels (a kernel is one test '
            'loop). It does not isolate the '
            'memory-access time of the row, and %s says why. '
            'The labels are rounded to 0.01 ns, and the tooltips give 0.001 ns. '
            'Files: %s, %s, %s and %s of boot F2 %s and of boot F1 %s.' % (
                V.num(max(pf2), 0),
                _rng(min(pf1), max(pf1), 2), top['label'], V.num(top['c1'][1], 2), S.xref('glance-where'), n_files,
                S.xref('setup-latency'),
                _code(lat_names[0]), _code(lat_names[1]), _code(lat_names[2]), _code(lat_names[3]),
                ' '.join(r_lat2), ' '.join(r_lat1)))
    fig = S.fig(svg, cap, take, id_='fig-headline', note=note)

    # ---- tiles
    small = 'font-size:12px;font-weight:400;color:#4a5058'

    def line(b, v, digits=1):
        s_ = _rng(v[0], v[1], digits, 'GB/s') if isinstance(v, tuple) else V.gbps(v, digits)
        return '%s<span style="%s">%s</span> %s' % (_dot(b), small, b, s_)

    def two(key1, key2):
        return [line('F2', q[key2]), line('F1', q[key1])]

    l1_bytes = CME_L1_KIB * KIB
    rd = {b: [r for r in _single_rows(D, b, 'read') if r['size'] <= l1_bytes] for b in BOOTS}
    wr = {b: _single_rows(D, b, 'write') for b in BOOTS}
    wv = {b: (min(r['best'] for r in wr[b]), max(r['best'] for r in wr[b])) for b in BOOTS}
    for b in BOOTS:
        k = q['l1_read_single_' + b]
        assert abs(min(r['best'] for r in rd[b]) - k[0]) < 1e-9 and abs(max(r['best'] for r in rd[b]) - k[1]) < 1e-9
    assert abs(min(wv['F1'][0], wv['F2'][0]) - q['write_single'][0]) < 1e-9
    assert abs(max(wv['F1'][1], wv['F2'][1]) - q['write_single'][1]) < 1e-9
    rc = D.bw_table('sweep', 'F2', 'read')
    mid = [r for r in rc if l1_bytes < r['size'] <= 4 * l1_bytes]
    assert abs(min(r['best'] for r in mid) - q['read_cluster_f2'][0]) < 1e-9, (mid, q['read_cluster_f2'])
    assert abs(max(r['best'] for r in mid) - q['read_cluster_f2'][1]) < 1e-9
    big = max(r['size'] for r in rc)
    f1_over_f2 = q['read_32m_f1'] / q['read_32m_f2']
    tiles = [
        _tile('Read inside the CME L1', two('l1_read_single_F1', 'l1_read_single_F2'),
              'single-call form, %s, bracket time' % _size_span(V, rd['F2'])),
        _tile('Write, %s' % _size_span(V, wr['F2']), [line('F2', wv['F2']), line('F1', wv['F1'])],
              'single-call form, bracket time'),
        _tile('Read above the CME L1', two('read_cluster_f1', 'read_cluster_f2'),
              'looped form, %s, bracket time' % _size_span(V, mid)),
        _tile('Read at %s' % V.size_label(big),
              two('read_32m_f1', 'read_32m_f2') + ['<span style="%s">F1 is %s F2</span>' % (small, V.ratio(f1_over_f2))],
              'looped form, bracket time. The bandwidth rows have no counter that names the level.'),
    ]
    grid = ('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin:10px 0 4px">%s</div>'
            '<p style="font-size:12.5px;color:#6b7280;margin:4px 0 0">Bandwidth headline numbers: the best rows of '
            'three files of each boot. Each row reads or writes the whole buffer in address order. '
            'The single-call rows are in %s %s and %s %s. The looped rows are in %s %s. '
            'F2 is b%s and F1 is b%s. '
            'Single-call form: all passes of a rep (one timed measurement) in one call of the test loop. '
            'Looped form: one call per pass. '
            'Bracket time: the time between two clock reads in the C program, around the call or calls. '
            '1 GB/s is 1,000,000,000 bytes per second.</p>' % (
                ''.join(tiles), _code('cme-bandwidth-l1-asmpasses.csv'), ' '.join(r_single),
                _code('cme-bandwidth-dram-1core-asmpasses.csv'), ' '.join(r_ss),
                _code('cme-bandwidth-dram-1core.csv'), ' '.join(r_sweep),
                D.boot_name['F2'][1:], D.boot_name['F1'][1:]))
    return text + ('<div style="background:#fff;border:1px solid #d9dde2;border-radius:6px;padding:4px 14px 10px;'
                   'margin-top:10px">%s</div>%s' % (fig, grid))


# ------------------------------------------------------------------ 2.1 the platform and the path

def _path_diagram(D, V):
    pf = D.platform
    svl = pf['sme_vl_max_F2']['value']
    l3 = [c for c in pf['caches'] if c['level'] == 3][0]
    ms = D.mesh_summary
    slc_est = SLC_NODES * SLC_NODE_MIB * (SLC_WAYS - OCM_WAYS) / SLC_WAYS
    n_ocm = len(pf['ocm_iomem'])
    y, h, y2 = 34, 122, 206
    nodes = [
        dict(id='core', x=6, y=y, w=108, h=h, title='Core (CPU 2)',
             lines=['C1-Nano', 'decodes the load and issues it to the CME'], tag='document on disk'),
        dict(id='cme', x=134, y=y, w=108, h=h, title='CME', kind='accent',
             lines=['C1-SME2 unit', '%d B vectors in streaming mode' % svl], tag='raw file'),
        dict(id='l1', x=262, y=y, w=130, h=h, title='CME L1', kind='accent',
             lines=['%d KiB data cache of the CME' % CME_L1_KIB], tag='document not on disk', tag_style='outline'),
        dict(id='l3', x=438, y=y, w=114, h=h, title='Cluster L3',
             lines=['%s, shared by CPUs %s' % (V.size_label(l3['size_bytes']), l3['shared_cpu_list'].replace('-', ' and '))],
             tag='raw file'),
        dict(id='snoop', x=438, y=y2, w=114, h=96, title="A core's cache", kind='soft',
             lines=['a snoop takes the line when a core holds it'], tag="operator's README", tag_style='outline'),
        dict(id='mesh', x=606, y=y, w=108, h=h, title='Mesh',
             lines=['%d x %d crosspoints' % (ms['grid_x'], ms['grid_y']), 'cluster port to home node'], tag='raw file'),
        dict(id='slc', x=754, y=y, w=126, h=h, title='Home node: SLC',
             lines=['%d parts' % SLC_NODES, '%.2f MiB est. in all' % slc_est], tag="operator's README",
             tag_style='outline'),
        dict(id='ocm', x=754, y=y2, w=126, h=96, title='Home node: OCM',
             lines=['%d regions of %s' % (n_ocm, V.size_label(_data.REGION_BYTES))], tag='raw file'),
        dict(id='dram', x=926, y=y, w=114, h=h, title='DRAM model', kind='dashed',
             lines=['emulator memory model'], tag="operator's README", tag_style='outline'),
    ]
    arrows = [dict(src='core', dst='cme'), dict(src='cme', dst='l1'),
              dict(src='l1', dst='l3', label='miss'), dict(src='l3', dst='mesh', label='miss'),
              dict(src='l1', dst='snoop', dashed=True), dict(src='mesh', dst='slc'),
              dict(src='mesh', dst='ocm', dashed=True), dict(src='slc', dst='dram', label='miss')]
    groups = [dict(x=0, y=6, w=560, h=306, label='cluster of CPUs 2 and 3'),
              dict(x=744, y=6, w=144, h=306, label='one of %d home nodes' % SLC_NODES)]
    return _neutral(V.boxes(nodes, arrows, groups=groups, title='data path of one CME load'))


def _cpu_count(D):
    """(number of processors, lowest id, highest id, first and last line) in sysinfo.txt of boot F1."""
    ids, at = [], []
    with open(os.path.join(_data.BOOTDIR['F1'], 'sysinfo.txt'), encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, 1):
            m = re.match(r'processor\s*:\s*(\d+)\s*$', line)
            if m:
                ids.append(int(m.group(1)))
                at.append(i)
    assert ids == list(range(len(ids))) and ids, ids
    return len(ids), ids[0], ids[-1], at[0], at[-1]


def _sec_path(D, V, S):
    pf = D.platform
    ms = D.mesh_summary
    g2 = _g1(D, 'F2')
    q = D.quote
    cm = D.commands
    caches = {(c['level'], c['type']): c for c in pf['caches']}
    slc_est = SLC_NODES * SLC_NODE_MIB * (SLC_WAYS - OCM_WAYS) / SLC_WAYS
    svl = pf['sme_vl_max_F2']['value']
    dc = ms['device_counts']
    l3c = caches[(3, 'Unified')]

    r_sys = _fref(S, D, 'F1', 'sysinfo.txt', 'lines %d to %d (caches of CPU 2), lines %d to %d (OCM regions), '
                  'lines %d to %d (mesh map)' % (pf['caches'][0]['line'], pf['caches'][-1]['line'],
                                                 pf['ocm_iomem'][0]['line'], pf['ocm_iomem'][-1]['line'],
                                                 pf['mesh_map']['line'], pf['mesh_map']['last_line']))
    r_dm1 = _runref(S, D, 'F1', 'dmesg.txt', 'lines %d to %d (streaming vector length), line %d (timer)' % (
        pf['sme_vl_min_F1']['line'], pf['sme_vl_default_F1']['line'], pf['timer_F1']['line']))
    r_dm2 = _runref(S, D, 'F2', 'dmesg.txt', 'lines %d to %d (streaming vector length), line %d (timer)' % (
        pf['sme_vl_min_F2']['line'], pf['sme_vl_default_F2']['line'], pf['timer_F2']['line']))
    r_rd1 = _readme(S, D, 'F1', 'platform', 'lines 343 to 354 (emulator image, firmware, CPU placement, caches, CME, DRAM)')
    r_rd2 = _readme(S, D, 'F2', 'platform', 'lines 269 to 280 (emulator image, firmware, CPU placement, caches, CME, DRAM)')
    r_rtl = _readme(S, D, 'F2', 'l3rtl', "line 181 (the operator's reading of the C1-SME2 source for the refill events)")
    r_sog = S.ref('doc:sog-nano', 'Arm C1-Nano Core Software Optimization Guide, document 109590_0001_04, sections '
                  '2.33 and 2.33.3. On disk: <code>refs/arm-c1-nano-r0p1-sog-109590_0001_04.pdf</code>.')
    r_trm = S.ref('doc:trm-sme2', 'Arm C1-SME2 Technical Reference Manual, document 107831, section 6 (the CME L1 '
                  'data cache) and chapter 12 (the event numbers). The document is not on disk. The page relies on '
                  'the citation in <code>common.h</code>, lines 258 to 271, and on the operator\'s README.')
    r_log1 = _fref(S, D, 'F1', 'log.txt', 'lines %d to %d (the CME commands), lines %d and %d (CPU 3 offline and '
                   'online)' % (cm['F1']['cme_first_line'], cm['F1']['cme_last_line'],
                                cm['F1']['cpu3_offline_line'], cm['F1']['cpu3_online_line']))
    r_log2 = _fref(S, D, 'F2', 'log.txt', 'lines %d to %d (the CME commands), lines %d and %d (CPU 3 offline and '
                   'online)' % (cm['F2']['cme_first_line'], cm['F2']['cme_last_line'],
                                cm['F2']['cpu3_offline_line'], cm['F2']['cpu3_online_line']))
    r_run = _src(S, 'run_cme', 'run_cme.sh', 'lines 10 to 11', 'CPU 3 is taken offline so that the CME of the '
                 'cluster is not shared')
    n_cpu, cpu_lo, cpu_hi, cpu_l0, cpu_l1 = _cpu_count(D)
    test_cpus = ', '.join('CPU %d' % c for c in D.integrity['F2']['cpus'])
    f1all = [r for r in D.g1['F1'] if r['key'] != 'dram-32m']
    assert min(r['hwprf_lo'] for r in f1all) > 0 and max(r['hwprf_hi'] for r in D.g1['F2']) == 0.0
    for b in BOOTS:
        assert D.dmesg_ocm_maps[b]['all_single_4k']

    h = S.h3('setup-path', 'The platform and the path of one CME load')
    h += S.bullets([
        'A CME load that misses the CME L1 cache gets its line from one of two places. One is inside the '
        'cluster. The other is outside it, through the mesh: a home node or the DRAM model.',
        'The raw files show only part of this path. The tag on each box of Figure %d names the source of the fact '
        'in the box.' % S.next_fig()])
    cap = ('Path of one CME load on %s, left to right. A dashed arrow is a second possible source at the same '
           'step. The boxes with a dark outline are the CME and its cache, and the box with a dashed outline (DRAM '
           'model) is an emulator model, not a part of the chip design. The tag at the bottom of a box names the '
           'source of the fact in the box.' % test_cpus)
    note = ('A filled tag names a source on disk. A tag with a dashed outline names a source that is not on disk, '
            'or the statement of the operator. '
            'Tags: "raw file" is a file of the results folders %s %s %s, "document on disk" is the Arm guide '
            '%s, "document not on disk" is the Arm manual %s, "operator\'s README" is the README of the run '
            '%s %s. '
            'The CME L1 counts its refills per load in two groups (inner: from inside the cluster, outer: from '
            'outside it). No counter separates the SLC from the DRAM model: both count as outer refills. '
            '%s gives the measured chain load for each place of this path, with span time and counters. Its row '
            '"Inside the cluster" stands for the boxes "Cluster L3" and "A core\'s cache". Its rows "Outside the '
            'cluster" stand for the boxes "Home node: SLC" and "DRAM model". '
            'The place names describe boot F2, whose rows count %s prefetch refills per load. On boot F1 every '
            'row counts prefetch refills. So a boot F1 row is the same footprint and not the cost of one place.' % (
                r_sys, r_dm1, r_dm2, r_sog, r_trm, r_rd1, r_rd2, S.xref('glance-where', cap=True),
                V.num(max(r['hwprf_hi'] for r in D.g1['F2']), 0)))
    take = ('A load that misses the CME L1 has two sources inside the cluster and three outside it. The counters '
            'separate inside from outside, and nothing else.')
    h += S.fig(_path_diagram(D, V), cap, take, id_='fig-path', note=note)

    core_sizes = ', '.join('L%d %s %s' % (c['level'], c['type'].lower(), V.size_label(c['size_bytes']))
                           for c in pf['caches'] if c['type'] != 'Instruction')
    l3 = caches[(3, 'Unified')]
    rows = [
        ['Cores', '%d C1-Nano cores, CPU %d to CPU %d (the processor entries of <code>sysinfo.txt</code>).'
                  % (n_cpu, cpu_lo, cpu_hi), 'raw file (boot F1)', r_sys],
        ['Clusters', 'CPUs %s share an L2 and an L3 (raw file). The pairs {2,3}, {4,5}, {6,7} and {8,9} are one '
                     'cluster each (operator\'s README).' % l3c['shared_cpu_list'].replace('-', ' and '),
         "raw file (boot F1), operator's README", '%s %s %s' % (r_sys, r_rd1, r_rd2)],
        ['Test CPU', 'Every CME command names %s. CPU 3, the other core of the cluster, is offline while the CME '
                     'commands run.' % test_cpus, 'raw file', '%s %s %s' % (r_log1, r_log2, r_run)],
        ['CME', 'One per cluster, shared by its two cores.', "operator's README", '%s %s' % (r_rd1, r_rd2)],
        ['CME vectors', 'The streaming vector length is %d bytes. One vector is one cache line.' % svl,
         'raw file', '%s %s' % (r_dm1, r_dm2)],
        ['Issue rate', 'The core issues at most %d load or store instructions per cycle to the CME.'
         % D.limits['doc']['loads_or_stores_per_cycle_max'], 'document on disk', r_sog],
        ['CME L1', '%d KiB data cache with 64-byte lines. The CME also has a TLB (address translation cache) of '
                   '%d entries.' % (CME_L1_KIB, CME_TLB), "document not on disk, operator's README",
         '%s %s' % (r_trm, r_rd1)],
        ['Caches of CPU 2', '%s. The L2 and the L3 are shared by CPUs %s. Boot F2 wrote no <code>sysinfo.txt</code>.'
         % (core_sizes, l3['shared_cpu_list']), 'raw file (boot F1)', r_sys],
        ['Inside the cluster', "A refill from inside the cluster comes from the cluster L3 or from a snoop of a "
                               "core's cache. The core's L1 and L2 are not levels on the CME's path.",
         "operator's README", r_rtl],
        ['Mesh', '%d x %d crosspoints with %d home nodes, %d cluster ports and %d bridges to memory.'
         % (ms['grid_x'], ms['grid_y'], dc['HN-S'], dc['RN-F'], dc['SBSX']), 'raw file (boot F1)', r_sys],
        ['SLC', '%d home nodes of %d MiB each. The firmware locks %d of the %d ways of each home node as OCM. '
                'That leaves %.2f MiB est. as cache.' % (SLC_NODES, SLC_NODE_MIB, OCM_WAYS, SLC_WAYS, slc_est),
         "operator's README", '%s %s' % (r_rd1, r_rd2)],
        ['OCM', '%d regions of %s, one per home node.'
         % (len(pf['ocm_iomem']), V.size_label(_data.REGION_BYTES)), 'raw file', r_sys],
        ['Pages', 'The buffers of the DRAM rows use pages of %g MiB. Boot F1 lists %d such pages. The OCM '
                  'buffers use pages of 4 KiB: each of the %d OCM mappings of boot F1 and the %d of boot F2 is made '
                  'of single 4 KiB entries.' % (pf['hugepagesize']['value'] / 1024.0, pf['hugepages_total']['value'],
                                                D.dmesg_ocm_maps['F1']['n'], D.dmesg_ocm_maps['F2']['n']),
         'raw file', '%s %s %s' % (r_sys, r_dm1, r_dm2)],
        ['DRAM model', 'An emulator memory model with no configured delay. It is not the timing of a real DRAM part.',
         "operator's README", '%s %s' % (r_rd1, r_rd2)],
        ['Emulator', 'One half of the Asimov chip (a hemisphere) runs on a Palladium hardware emulator, a machine '
                     'that runs the chip design slowly. The cores, the clusters with their CMEs and the mesh with '
                     'its SLC and OCM are the real design.', "operator's README",
         '%s %s' % (r_rd1, r_rd2)],
    ]
    h += S.table(['Part', 'Fact', 'Source', 'Reference'], rows,
                 caption='The platform, part by part, with the source of each fact.',
                 note='"est." marks a value computed from facts of the operator\'s README, not measured.')
    h += S.callout('The DRAM model is an emulator memory model. No DRAM latency or bandwidth number on this page is '
                   'silicon DRAM timing %s.' % r_rd1)
    h += S.insufficient('The Arm C1-SME2 manual is not on disk. So the size of the CME L1 cache is not confirmed '
                        'from the document itself %s. The Linux cache listing prints <code>ways=0</code> for every '
                        'level. So the folders do not give the number of ways of any cache %s. A copy of the '
                        'manual and a read of the cache geometry registers would resolve both.' % (r_trm, r_sys))
    return h


# ------------------------------------------------------------------ 2.2 the two boots

def _cpu3_note(c):
    """Says where the two CPU 3 lines of a command log stand (the line numbers are in the reference)."""
    ok = c['cpu3_offline_line'] < c['cme_first_line'] and c['cme_last_line'] < c['cpu3_online_line']
    return ('offline before the first CME command, online after the last one' if ok else
            'the offline and online lines do not enclose the CME commands')


def _sec_boots(D, V, S):
    cm = D.commands
    it = D.integrity
    bs = D.baseline_summary
    hw = {b: _hwprf_reps(D, b) for b in BOOTS}
    commits = {b: _commit(D, b) for b in BOOTS}
    r_log1, r_log2 = _fref(S, D, 'F1', 'log.txt'), _fref(S, D, 'F2', 'log.txt')
    r_pf = _readme(S, D, 'F2', 'prefetch', 'lines 18 to 29 (the firmware hook that turns the prefetchers off, its '
                   'register readbacks and its check)')
    r_rd1 = _readme(S, D, 'F1', 'platform', 'lines 343 to 354')
    r_rd2 = _readme(S, D, 'F2', 'platform', 'lines 269 to 280')
    r_l3 = _readme(S, D, 'F1', 'l3', 'lines 66 to 68 (the L3 power status register and the reading of the value 0x70)')
    r_test = _readme(S, D, 'F1', 'cmetest', 'lines 7 and 36 to 44 (the self-test <code>cme_test</code>)')
    r_order = _readme(S, D, 'F2', 'order', 'lines 68, 69, 71 and 74 (run order, page placement, emulator boards, '
                      'and what a difference between the boots means)')
    r_small = [_fref(S, D, b, 'cme-latency-dram-small.csv') for b in BOOTS]
    r_large = [_fref(S, D, b, 'cme-latency-dram-large.csv') for b in BOOTS]
    r_all = S.ref('files:cme-lat')
    r_plain = r_all
    r_sha1, r_sha2 = _runref(S, D, 'F1', 'SHA256SUMS'), _runref(S, D, 'F2', 'SHA256SUMS')

    h = S.h3('setup-boots', 'The two boots')
    same = cm['same_cme_commands']
    n_lat, n_plain, n_l3 = _file_counts(D)
    test_cpus = ', '.join('CPU %d' % c for c in it['F2']['cpus'])
    h += S.bullets([
        'Both boots ran %s %d CME command lines in the same order on %s, with the cluster L3 on %s %s.' % (
            'the same' if same else 'different', cm['F2']['n_cme'], test_cpus, r_log1, r_log2),
        'The intended difference is the firmware setting of the hardware prefetchers %s.' % r_pf,
        'The counters agree with the setting. The CME L1 refills caused by the prefetcher read %s per load on boot '
        'F1 and %s per load on boot F2, in all %d chain rep rows of each boot. A value above 1 means that the '
        'row counts more prefetch refills than loads.' % (
            _rng(min(hw['F1']), max(hw['F1']), 4), _rng(min(hw['F2']), max(hw['F2']), 4), len(hw['F2'])),
        '%s draws the prefetch refills per load against the footprint for both boots %s %s %s %s.' % (
            S.xref('lat-serve', cap=True), r_small[0], r_large[0], r_small[1], r_large[1])])

    def ov(b):
        s = bs[b]
        t = '%s in %d files' % (V.ns(s['overhead_common'], 1), s['overhead_n_common'])
        for name, v in s['overhead_other']:
            t += ', %s in %s' % (V.ns(v, 1), _code(name))
        return t

    def l3(b):
        return len(cm[b]['clusterpwrstat']), \
            sorted(set(x['text'].split(':')[-1].strip() for x in cm[b]['clusterpwrstat']))

    rows = [
        'Differences',
        ['Hardware prefetchers', 'on (firmware TF-A 0.35.0 does not turn the prefetchers off)',
         'off on CPUs 2 to 9 and on their CMEs (firmware TF-A 0.35.0-pfoff.1)', "operator's README", r_pf],
        ['Prefetch refills per load, all chain rep rows',
         '%s (%d rows, %d read zero)' % (_rng(min(hw['F1']), max(hw['F1']), 4), len(hw['F1']), hw['F1'].count(0.0)),
         '%s (%d rows, %d read zero)' % (_rng(min(hw['F2']), max(hw['F2']), 4), len(hw['F2']), hw['F2'].count(0.0)),
         'raw file: the %d CME latency files of each boot that carry the column' % n_plain, r_plain],
        ['Commands in <code>log.txt</code>',
         '%d: %d core commands, then %d CME commands' % (cm['F1']['n_commands'], cm['F1']['n_core'], cm['F1']['n_cme']),
         '%d: %d core commands, %d CME commands' % (cm['F2']['n_commands'], cm['F2']['n_core'], cm['F2']['n_cme']),
         'raw file', '%s %s' % (r_log1, r_log2)],
        ['Uptime stamp of the first and the last CME command',
         '%.2f s and %.2f s' % (cm['F1']['cme_first_uptime'], cm['F1']['cme_last_uptime']),
         '%.2f s and %.2f s' % (cm['F2']['cme_first_uptime'], cm['F2']['cme_last_uptime']),
         'raw file', '%s %s' % (r_log1, r_log2)],
        ['Self-test <code>cme_test</code> (checks the folds of the kernels)', 'ran once, 0 failures', 'not run',
         "operator's README", r_test],
        ['<code>sysinfo.txt</code> (CPU, cache and mesh listing)', 'written', 'not written',
         'raw file: the checksum list of boot F2 names no such file', '%s %s' % (r_sha1, r_sha2)],
        ['Empty bracket (two clock reads with nothing between)', ov('F1'), ov('F2'),
         'raw file: a comment line of each CME latency file', r_all],
        ['Run order', 'the self-test and %d core commands ran before the CME commands' % cm['F1']['n_core'],
         'the CME commands ran alone', "raw file for the counts, operator's README for the self-test",
         '%s %s %s' % (r_log1, r_log2, r_order)],
        ['Physical pages of the buffers', 'drawn by each command, not printed', 'drawn by each command, not printed',
         "operator's README", r_order],
        ['Emulator boards', '18 to 21', '12 to 15', "operator's README", r_order],
        'The same on both boots',
        ['Cluster L3', 'on. Status %s in the %d status lines of the log' % (', '.join(l3('F1')[1]), l3('F1')[0]),
         'on. Status %s in the %d status lines of the log' % (', '.join(l3('F2')[1]), l3('F2')[0]),
         "raw file for the value, operator's README for its meaning", '%s %s %s' % (r_log1, r_log2, r_l3)],
        ['Benchmark build in the command paths', ', '.join(_code(c) for c in commits['F1']),
         ', '.join(_code(c) for c in commits['F2']), 'raw file', '%s %s' % (r_log1, r_log2)],
        ['CPU named by the CME commands', ', '.join('CPU %d' % c for c in it['F1']['cpus']),
         ', '.join('CPU %d' % c for c in it['F2']['cpus']), 'raw file', '%s %s' % (r_log1, r_log2)],
        ['CPU 3 offline around the CME commands',
         _cpu3_note(cm['F1']), _cpu3_note(cm['F2']),
         'raw file', '%s %s' % (r_log1, r_log2)],
        ['Emulator image, Linux image, first-stage firmware', 'same as boot F2', 'same as boot F1',
         "operator's README", '%s %s' % (r_rd1, r_rd2)],
    ]
    h += S.table(['Item', 'B' + D.boot_name['F1'][1:], 'B' + D.boot_name['F2'][1:], 'Source', 'Reference'], rows,
                 caption='The two boots: what differs and what is the same.',
                 note='Uptime is chip time since the Linux boot, printed in steps of 0.01 s.', align='lllll')
    h += S.callout('A difference between a boot F1 row and a boot F2 row is a difference between two boots. The '
                   'prefetcher setting is one difference. Two more are known. Boot F1 ran its self-test and %d core '
                   'commands before the CME commands, and boot F2 ran the CME commands alone. Each command draws its '
                   'own physical pages. So the buffers of a row need not sit on the same pages on the two boots '
                   '%s.' % (cm['F1']['n_core'], r_order))
    h += S.callout('How the page compares the two boots: a difference in ns is boot F1 minus boot F2. A ratio names '
                   'its two boots in the column header or in the sentence, for example "F2 / F1" or "boot F1 is 2 '
                   'times boot F2".', title='Sign of a difference')
    h += S.insufficient('Each setting was booted %s. The boot-to-boot spread of a row is unknown. A second boot with '
                        'the same settings would give it.' % (
                            'once' if D.repeatability['all']['boots_repeated'] == 0 else 'more than once'))
    return h


# ------------------------------------------------------------------ 2.3 the latency test

def _latency_diagram(D, V):
    g2 = _g1(D, 'F2')
    lo = g2['l1']['bracket_lo']
    hi = max(r['bracket_hi'] for r in D.g1['F2'])
    n_files = D.baseline_summary['all']['n_files']

    def row(y, pre, mid_title, mid_line, first_line, back):
        yb = y + 78 + 34
        nodes = [dict(id=pre + '1', x=110, y=y, w=210, h=78, title='Core: register x0', lines=[first_line]),
                 dict(id=pre + '2', x=415, y=y, w=230, h=78, title=mid_title, lines=[mid_line], kind='accent'),
                 dict(id=pre + '3', x=740, y=y, w=230, h=78, title='CME: LASTB',
                      lines=['moves the 8 bytes back to x0 on the core'], kind='accent')]
        arrows = [dict(src=pre + '1', dst=pre + '2'), dict(src=pre + '2', dst=pre + '3'),
                  dict(src=pre + '3', dst=pre + '1', via=[(855, yb), (215, yb)], label=back)]
        return nodes, arrows

    na, aa = row(34, 'a', 'CME: LD1D', 'loads 8 bytes at that address into a vector register',
                 'holds the address of the load', 'the loaded value is the address of the next load')
    nb, ab = row(214, 'b', 'CME: DUP', 'copies x0 into a vector register, no memory access',
                 'holds a value', 'the same value is used again')
    groups = [dict(x=0, y=6, w=1040, h=160,
                   label='one chain load: %s to %s ns on boot F2, by footprint' % (V.num(lo, 3), V.num(hi, 3))),
              dict(x=0, y=186, w=1040, h=160,
                   label='one step of the round-trip baseline: %s ns in all %d files' % (V.num(D.rt_ns, 3), n_files))]
    return _neutral(V.boxes(na + nb, aa + ab, groups=groups, title='the latency test and the round-trip baseline'))


def _kind_rows(D, S):
    """One table row per chain kind and shape that the two boots ran (from the rows of boot F2)."""
    out = []
    groups = {}
    for r in D.chain['F2']:
        groups.setdefault((r['kind'], r['src']), []).append(r)
    nw = lambda *a: ' '.join('<code style="white-space:nowrap">%s</code>' % x for x in a)
    ks = lambda kind, shape: '<div style="min-width:105px">%s<br><span style="color:#4a5058">shape: %s</span></div>' % (
        kind, shape)
    wide = lambda t: '<div style="min-width:185px">%s</div>' % t
    opt = {'walked many times': 'default', 'walked once': nw('--fresh 3'),
           'every line flushed first': nw('--fresh 3', '--flush')}
    what = {'walked many times': 'One chain is walked again and again inside a rep. After the first pass the '
                                 'loads visit the same lines in the same order.',
            'walked once': 'Each rep is one pass. Each rep uses its own chain over the same lines and visits each '
                           'line once. Two untimed passes over a first chain have touched the lines before.',
            'every line flushed first': 'As "walked once". Before each rep the core removes every line '
                                        'of the buffer from the caches with the instruction DC CIVAC, then '
                                        'runs DSB SY.'}
    for (kind, src), rs in groups.items():
        sizes = sorted(r['size'] for r in rs)
        loads = sorted(r['loads'] for r in rs)
        walks = sorted(r['walks_per_rep'] for r in rs)
        fp = _data.fmt_size(sizes[0]) if len(sizes) == 1 else '%s to %s' % (_data.fmt_size(sizes[0]), _data.fmt_size(sizes[-1]))
        passes = _n(walks[0]) if walks[0] == walks[-1] else '%s to %s' % (_n(walks[0]), _n(walks[-1]))
        out.append([ks(kind, 'every line'), opt[kind], wide(what[kind]), fp + ', DRAM model',
                    '%d' % rs[0]['n_reps'], passes,
                    _n(loads[0]) if loads[0] == loads[-1] else '%s to %s' % (_n(loads[0]), _n(loads[-1])),
                    _nb(_code(src))])
    seen = {}
    for r in D.ocm_lat['F2']:
        k = (r['shape'], r['loads'], r['n_reps'])
        seen.setdefault(k, []).append(r)
    for (shape, loads, n_reps), rs in seen.items():
        one = len(rs) > 1
        assert all(r['walks_per_rep'] == 1 for r in rs)
        out.append([ks(rs[0]['kind'], shape),
                    nw(*(['--fresh %d' % (n_reps + 1), '--flush'] + (['--sparse'] if 'page' in shape else []))),
                    wide('As "every line flushed first" above, on OCM buffers (pages of 4 KiB). %s' % (
                        'The chain uses one 64-byte line of each 4 KiB page.' if 'page' in shape else
                        'The chain uses every 64-byte line.')),
                    '%s, OCM%s' % (_data.fmt_size(rs[0]['size']), ' (one region)' if one else ' (all five regions)'),
                    '%d' % n_reps, '1', _n(loads),
                    _nb(_code('cme-latency-ocm-region0.csv')) + ' to ' + _nb(_code('-region4.csv')) if one
                    else _nb(_code(rs[0]['src']))])
    return out


def _sec_latency(D, V, S):
    bs = D.baseline_summary['all']
    g2 = _g1(D, 'F2')
    r_kern = _src(S, 'kern-chain', 'cme_kern.S', 'lines 116 to 140', 'the chain-load kernel and the kernel of the '
                  'round-trip baseline')
    r_lat = _src(S, 'latency-chain', 'latency.c', 'lines 84 to 137 and 232 to 243', 'how a chain is built (one '
                 'random cycle through all member lines, fixed seeds) and the two untimed walks before the first rep')
    r_modes = _src(S, 'latency-modes', 'latency.c', 'lines 180 to 313', 'the reps, the flush before a rep, '
                   'the round-trip baseline rows, the <code>cme-call</code> rows and the best rows')
    r_f = [_fref(S, D, 'F2', n) for n in ('cme-latency-dram-small.csv', 'cme-latency-dram-large.csv',
                                          'cme-latency-dram-flushed.csv')]
    r_ocm = S.ref('files:ocm-lat', 'The seven OCM latency files of each boot: <code>cme-latency-ocm-region0.csv</code> '
                  'to <code>cme-latency-ocm-region4.csv</code>, <code>cme-latency-ocm-all5.csv</code> and '
                  '<code>cme-latency-ocm-all5-dense.csv</code>, in <code>%s/</code> and <code>%s/</code>.' % (
                      _rel(D, 'F1'), _rel(D, 'F2')))
    r_all = S.ref('files:cme-lat', 'The %d CME latency files of each boot: <code>cme-latency-*.csv</code> in '
                  '<code>%s/</code> and <code>%s/</code>. Each begins with the rows <code>cme-roundtrip</code> and '
                  '<code>cme-call</code>.' % (_file_counts(D)[0], _rel(D, 'F1'), _rel(D, 'F2')))

    h = S.h3('setup-latency', 'The latency test and the round-trip baseline')
    h += S.bullets([
        'One chain load is two instructions on the CME. LD1D loads 8 bytes. LASTB moves them to the core as '
        'the address of the next load %s. So each load waits for the load before it. The time per load is the '
        'time from the start of one load to the start of the next.' % r_kern,
        'The round-trip baseline runs the same loop with a register copy in place of the load. It reads %s in '
        'all %d CME latency files of the two boots %s. It is a separate measurement with no memory access.' % (
            _rng(bs['rt_best_lo'], bs['rt_best_hi'], 3, 'ns'), bs['n_files'], r_all),
        'Both loops return a value to the core through LASTB %s. The rows do not show that the instructions which '
        'the two loops share cost the same time in both.' % r_kern])
    cap = ('The loop of the latency test (top) and the loop of the round-trip baseline (bottom). Each box is one '
           'instruction or one register. The boxes with a dark outline run on the CME. Rows: the best rows of b%s for the chain load %s %s %s, and the rows '
           '%s of both boots for the baseline %s. Source of the loops: %s.' % (
               D.boot_name['F2'][1:], r_f[0], r_f[1], r_f[2], _code('cme-roundtrip-best'), r_all, r_kern))
    top = max(D.g1['F2'], key=lambda r: r['above_rt_hi'])
    take = ('The two loops differ in one instruction. On boot F2 the lowest chain load row (%s) reads %s above the '
            'baseline row, and the highest (%s, %s) reads %s above it. Each value is the difference between two '
            'kernels, not a memory-access time.' % (
                g2['l1']['where'], V.ns(g2['l1']['above_rt_lo']), top['where'], top['conditions'],
                V.ns(top['above_rt_hi'])))
    h += S.fig(_latency_diagram(D, V), cap, take, id_='fig-latency-loop')

    h += S.table(['Chain kind and chain shape', 'Options', 'What happens', 'Footprints', 'Timed<br>reps',
                  'Passes<br>per rep', 'Loads per rep', 'File'], _kind_rows(D, S),
                 caption='The chain kinds and chain shapes that the two boots ran. Both boots ran the same '
                         'commands %s %s.' % (r_modes, r_ocm),
                 note='A rep is one timed measurement, and a pass is one walk over the whole chain. The reps are '
                      'counted per footprint. In the kind "walked many times" one rep is many passes. In the other '
                      'kinds one rep is one pass. Counts are from the rows of boot F2. The address-order kind '
                      '(each line points to the next line) was not run on these boots.', align='llllrrrl')
    cs = D.baseline_summary['all']
    h += S.bullets([
        'A chain is one random cycle through all its lines. The seeds are fixed. So both boots walk the same '
        'chains %s.' % r_lat,
        'The core writes the buffer and the chain pointers. Then the CME walks the first chain twice, untimed, '
        'before the first rep %s.' % r_lat,
        'Each latency file also holds %s rows: %d calls of the baseline kernel with one step each, timed in one '
        'bracket. Their best rows read %s per call over the %d files %s. %s uses them.' % (
            _code('cme-call'), CALLS_PER_CME_CALL_ROW, _rng(cs['call_best_lo'], cs['call_best_hi'], 3, 'ns'),
            cs['n_files'], r_all, S.xref('callcost-cmecall', cap=True)),
        'No row gives a CME load time without the return to the core. Every latency kernel returns the loaded '
        'value to the core through LASTB.',
        'The page gives "chain load minus round-trip baseline" as the measured difference between two kernels: '
        'the chain-load kernel and the baseline kernel %s.' % r_kern])
    h += S.insufficient('The rows do not show how much of a chain load time is memory-access time. The chain-load '
                        'kernel runs LD1D and then LASTB. The baseline kernel runs DUP and then LASTB %s. No row '
                        'measures the time that the two kernels share outside the memory access. A calibration of '
                        'that shared time would resolve it, for example a waveform of one iteration of each '
                        'kernel. The project file <code>README.md</code> states the same limit: the chain load '
                        'minus the baseline is a derived number, not the memory latency %s.' % (
                            r_kern, S.ref('doc:project-readme')))
    return h


# ------------------------------------------------------------------ 2.4 the bandwidth test and the kernels

def _forms_diagram(V):
    """Looped form and single-call form, with one bar per span and one bar per bracket under each row."""
    y1 = 34
    ys, yb = y1 + 80, y1 + 124          # the span bars and the bracket bar of the first row
    dy = 216                            # distance between the two rows
    nodes, arrows = [], []
    for row, pre in ((0, 'a'), (1, 'b')):
        o = row * dy
        nodes += [dict(id=pre + 'c1', x=20, y=y1 + o, w=110, h=70, title='clock read', lines=['in C']),
                  dict(id=pre + 'c2', x=910, y=y1 + o, w=110, h=70, title='clock read', lines=['in C']),
                  dict(id=pre + 'br', x=130, y=yb + o, w=780, h=34, kind='soft',
                       title='bracket time: from the first clock read to the second')]
        if row == 0:
            calls = [(180, 190, 'kernel call 1', 'SMSTART, one pass, SMSTOP', 'span 1'),
                     (420, 190, 'kernel call 2', 'SMSTART, one pass, SMSTOP', 'span 2'),
                     (660, 200, '... kernel call N', 'N = passes of the rep', 'span N')]
        else:
            calls = [(180, 680, 'one kernel call', 'SMSTART, all N passes of the rep, SMSTOP',
                      'the one span: after SMSTART, before SMSTOP')]
        prev = pre + 'c1'
        for i, (x, w, title, line, span) in enumerate(calls):
            nodes.append(dict(id='%sk%d' % (pre, i), x=x, y=y1 + o, w=w, h=70, title=title, kind='accent', lines=[line]))
            nodes.append(dict(id='%ss%d' % (pre, i), x=x + 30, y=ys + o, w=w - 60, h=34, kind='soft', title=span))
            arrows.append(dict(src=prev, dst='%sk%d' % (pre, i)))
            prev = '%sk%d' % (pre, i)
        arrows.append(dict(src=prev, dst=pre + 'c2'))
    groups = [dict(x=0, y=6, w=1040, h=194, label='looped form: one kernel call per pass, N spans in one bracket'),
              dict(x=0, y=6 + dy, w=1040, h=194,
                   label='single-call form: one kernel call per rep, one span in one bracket')]
    return _neutral(V.boxes(nodes, arrows, groups=groups, title='looped form and single-call form'))


def _sec_kernels(D, V, S):
    it = D.integrity
    cnt = {b: _bw_counts(D, b) for b in BOOTS}
    lat = {b: _lat_counts(D, b) for b in BOOTS}
    n_lat, n_plain, n_l3 = _file_counts(D)
    l3f = set(_l3_files(D, 'F2'))
    best_l3 = sum(len(blk['sizes']) for f in l3f for blk in D.latblocks('F2', f))
    best_plain = lat['F2'][0] - best_l3
    assert lat['F2'] == lat['F1'], lat
    n_ocm_bw = len(D.ocm_bw['F2'])
    assert n_ocm_bw == len(D.ocm_bw['F1'])
    assert sum(cnt['F2'].values()) == it['F2']['bandwidth_best_rows'], (cnt['F2'], it['F2']['bandwidth_best_rows'])
    names = sorted(set(k for k, _ in cnt['F2']))

    def c(kernel, form):
        a, b = cnt['F2'].get((kernel, form), 0), cnt['F1'].get((kernel, form), 0)
        return '%d' % a if a == b else '%d (boot F2), %d (boot F1)' % (a, b)

    r_k = _src(S, 'kern-all', 'cme_kern.S', 'lines 71 to 104 (entry and exit of every kernel) and lines 116 to 421 '
               '(the kernels)', 'the instructions of each loop')
    r_bw = _src(S, 'bandwidth-rep', 'bandwidth.c', 'lines 314 to 342 and 417 to 447', 'how a rep runs: the untimed '
                'pass, the flush, the clock reads, one kernel call per pass and per OCM region')
    r_best = _src(S, 'bandwidth-best', 'bandwidth.c', 'lines 573 to 620', 'the choice of the best row')
    r_noperf = _src(S, 'bandwidth-noperf', 'bandwidth.c', 'line 519', 'the bandwidth test refuses the counter option '
                    'together with the CME option')
    r_test = _readme(S, D, 'F1', 'cmetest', 'lines 7 and 36 to 44 (the self-test <code>cme_test</code>)')
    r_bwf = S.ref('files:cme-bw', 'The %d CME bandwidth files of each boot: <code>cme-bandwidth-*.csv</code> in '
                  '<code>%s/</code> and <code>%s/</code>. The header comment of each command gives the options '
                  '(<code>asm_passes</code>, <code>no_fold</code>, <code>dsb_st</code>, <code>flush_before</code>).'
                  % (it['F2']['n_cme_bandwidth_files'], _rel(D, 'F1'), _rel(D, 'F2')))

    h = S.h3('setup-kernels', 'The bandwidth test and the kernels')
    h += S.bullets([
        'A bandwidth row is the bytes moved in a rep divided by the time.',
        'The CSV files use %d kernel names. A kernel name can stand for several forms: looped, single-call, looped '
        'without the final fold, and looped with a DSB ST barrier. Figure %d and Table %d define them. The CSV row '
        'does not name its form. The file name and the header comment of the command do %s.' % (
            len(names), S.next_fig(), S.next_table(), r_bwf),
        'A read row measures the loads together with the XOR work of the fold. It is not the rate of the loads '
        'alone %s.' % r_k])
    cap = ('The two forms of the bandwidth test. Each kernel call enters streaming mode once (SMSTART) and leaves '
           'it once (SMSTOP). So the looped form has that cost once per pass, and the single-call form has it once '
           'per rep. The boxes with a dark outline run on the CME. The grey bars under each row show what each '
           'time covers. A span covers the inner part of one kernel call, after SMSTART and before SMSTOP. The '
           'bracket covers everything between the two clock reads.')
    note = ('Schematic, not to scale: %s draws one call to '
            'scale. Rows of the looped form: %s, %s and others. Rows of the single-call '
            'form: %s and %s. All of both boots %s. Source: %s.' % (
                S.xref('callcost-lanes'),
                _code('cme-bandwidth-dram-1core.csv'), _code('cme-bandwidth-l1-passes.csv'),
                _code('cme-bandwidth-l1-asmpasses.csv'), _code('cme-bandwidth-dram-1core-asmpasses.csv'), r_bwf, r_bw))
    h += S.fig(_forms_diagram(V), cap, 'The single-call form has one span per rep. So its bracket time holds the '
               'cost of one kernel call, not of N calls.', id_='fig-forms', note=note)

    rows = [
        'Latency test (program <code>latency --cme</code>)',
        [_code('cme-repeat') + ', ' + _code('cme-fresh1') + ' to ' + _code('cme-fresh7'),
         'the chain-load kernel', 'LD1D of one 8-byte element, LASTB, SUBS, B.NE: 4 instructions',
         '8 B loaded', 'nothing. The last pointer goes back to C.',
         '%d (%d in the %d files without <code>-l3</code> in the name, %d in the %d files with it)' % (
             lat['F2'][0], best_plain, n_plain, best_l3, n_l3)],
        [_code('cme-roundtrip') + ', ' + _code('cme-call'), _code('cme_roundtrip'),
         'DUP, LASTB, SUBS, B.NE: 4 instructions', '0 B', 'nothing. No memory access.',
         '%d files, each with one best row of %s and one of %s' % (
             lat['F2'][1], _code('cme-roundtrip'), _code('cme-call'))],
        'Bandwidth test (program <code>bandwidth --cme</code>)',
        [_code('cme-read') + ', looped form', _code('cme_read4'),
         '4 LD1B of four vectors each, 16 EOR, ADD, CMP, B.LO: 23 instructions', '1,024 B read',
         'returns the fold of all loaded words', c('read', 'looped')],
        [_code('cme-read') + ', looped form, no fold', _code('cme_read4_nofold') + ', the lines of ' + _code('cme_read4'),
         'the same loop', '1,024 B read', 'returns 0. The 16 EOR of each iteration stay. Only the fold after the '
         'loop is left out.', c('read', 'looped, no fold')],
        [_code('cme-read') + ', single-call form', _code('cme_read4_n'),
         'the same loop inside a loop over the passes', '1,024 B read', 'one fold at the end of the call',
         c('read', 'single-call')],
        [_code('cme-write') + ', looped form', _code('cme_write4'),
         '4 ST1B of four vectors each, ADD, CMP, B.LO: 7 instructions', '1,024 B written', 'nothing',
         c('write', 'looped')],
        [_code('cme-write') + ', looped form, DSB ST', _code('cme_write4_dsb') + ', the lines of ' + _code('cme_write4'), 'the same loop',
         '1,024 B written', 'DSB ST after the loop and inside the span: the span waits for the stores',
         c('write', 'looped, DSB ST')],
        [_code('cme-write') + ', single-call form', _code('cme_write4_n'),
         'the same loop inside a loop over the passes', '1,024 B written', 'nothing', c('write', 'single-call')],
        [_code('cme-copy'), _code('cme_copy4'),
         '4 LD1B and 4 ST1B of four vectors each, 2 ADD, CMP, B.LO: 12 instructions',
         '1,024 B read and 1,024 B written', 'nothing. The CSV counts read plus written bytes.', c('copy', 'looped')],
        [_code('cme-ldr16'), _code('cme_read1'),
         '8 LD1B of one vector each, 8 EOR, ADD, CMP, B.LO: 19 instructions', '512 B read',
         'returns the fold of all loaded words', c('read64', 'looped')],
        [_code('cme-str16'), _code('cme_write1'),
         '8 ST1B of one vector each, ADD, CMP, B.LO: 11 instructions', '512 B written', 'nothing',
         c('write64', 'looped')],
    ]
    h += S.table(['Name in the CSV', 'Routine in <code>cme_kern.S</code>', 'Loop body', 'Bytes per loop iteration',
                  'What it returns or checks', 'Best rows per boot'], rows,
                 caption='The kernels. One vector is 64 bytes. The instruction counts are from the source file, '
                         'and its reference entry gives the lines of each routine %s.' % r_k,
                 note='The names <code>cme-ldr16</code> and <code>cme-str16</code> come from the options of the '
                      'core test. Through the CME they move 64 bytes per instruction. The %d bandwidth best rows '
                      'of a boot include the %d OCM rows.' % (it['F2']['bandwidth_best_rows'], n_ocm_bw),
                 align='llllll')
    h += S.bullets([
        'A rep runs in this order: one untimed pass in the looped form (also for a single-call rep), a flush of '
        'every line when the command asks for it, a wait at a thread barrier, a clock read, the kernel call or '
        'calls, a clock read %s.' % r_bw,
        'A buffer over all five OCM regions is five segments. One looped pass over it is five kernel calls, one '
        'per region %s.' % r_bw,
        'The fold is not printed. A separate self-test checks the folds. It ran on boot F1 with 0 failures and did '
        'not run on boot F2 (operator\'s README) %s.' % r_test,
        'The bandwidth rows carry no counters. The program refuses its counter option together with the CME '
        'option %s.' % r_noperf])
    h += S.insufficient('The files do not show whether the ISB that closes a span waits for the loads or stores of '
                        'the span to complete. A waveform of one call, or a statement by Arm on ISB and CME '
                        'operations in flight, would resolve it %s.' % r_k)
    return h, r_best


# ------------------------------------------------------------------ 2.5 bracket time, span time, best row

def _sec_times(D, V, S, r_best):
    bm = D.bracket_minus_span
    bs = D.baseline_summary
    it = D.integrity
    r_k = _src(S, 'kern-span', 'cme_kern.S', 'lines 71 to 104', 'the two timer reads of a span: after SMSTART and '
               'an ISB, and after the loop and an ISB, before SMSTOP')
    r_c = _src(S, 'common-clock', 'common.h', 'lines 56 to 61 and 585 to 597', 'the clock read of the bracket and '
               'the sum of the spans of a rep')
    r_lbest = _src(S, 'latency-best', 'latency.c', 'lines 240 to 313', 'the best rows of the latency test')
    r_all = S.ref('files:cme-lat')
    sweep_names = ('cme-latency-dram-small.csv', 'cme-latency-dram-large.csv')
    r_sweeps = ' '.join(_fref(S, D, b, n) for b in BOOTS for n in sweep_names)
    d_sw = {}
    for b in BOOTS:
        d = [r['ns'] - r['span'] for n in sweep_names for blk in D.latblocks(b, n)
             for e in blk['sizes'].values() for r in e['reps']]
        d_sw[b] = (min(d), max(d), len(d))
        assert abs(d_sw[b][0] - bm[b]['all_lo']) < 1e-9 and abs(d_sw[b][1] - bm[b]['all_hi']) < 1e-9
    assert d_sw['F1'][2] == d_sw['F2'][2]

    h = S.h3('setup-times', 'Bracket time, span time and the best row')
    h += S.bullets([
        'Every CME row carries two times. The bracket time runs between two clock reads in C around the kernel '
        'call or calls. The span time runs between two stamps (timer reads inside the kernel), after SMSTART and before '
        'SMSTOP %s %s.' % (r_k, r_c),
        'The outside-span time is the bracket time minus the span time. Figure %d shows what each time covers. '
        'The wall-clock lanes figure in %s draws the two times of one call to scale.' % (
            S.n_fig, S.xref('callcost-lanes'))])
    rows = [
        ['Clock', '<code>clock_gettime(CLOCK_MONOTONIC)</code>, read in C', 'the timer register '
         '<code>CNTVCT_EL0</code>, read in the kernel'],
        ['Starts', 'before the C call of the kernel', 'after SMSTART and an ISB'],
        ['Ends', 'after the kernel returns', 'after the loop, the fold or the DSB ST, and an ISB. Before SMSTOP.'],
        ['Holds', 'the span, and also the call and the return, the save and restore of registers, SMSTART, '
                  'SMSTOP, and the C loop around the calls of the looped form',
         'the setup of the kernel, the loop, the fold or the DSB ST, and the closing ISB'],
        ['Latency CSV column', '<code>ns_per_load</code>', '<code>ns_per_load_span</code>'],
        ['Bandwidth CSV column', '<code>aggregate_GBps</code> (bytes / bracket time)',
         '<code>span_GBps</code> (bytes / sum of the spans of the rep)'],
    ]
    h += S.table(['', 'Bracket time', 'Span time'], rows,
                 caption='The two times of a row %s %s.' % (r_k, r_c),
                 note='The outside-span time is not the cost of the mode switch alone. It holds every item of the '
                      'bracket column that the span column lacks.', align='lll')
    h += S.bullets([
        'On the footprint rows of the latency test the two times are close. Bracket minus span is %s per load on '
        'boot F1 and %s per load on boot F2. Rows: the %d chain rep rows of %s and %s of each boot %s. One kernel '
        'call covers thousands of loads there.' % (
            _rng(d_sw['F1'][0], d_sw['F1'][1], 3, 'ns'), _rng(d_sw['F2'][0], d_sw['F2'][1], 3, 'ns'),
            d_sw['F2'][2], _code(sweep_names[0]), _code(sweep_names[1]), r_sweeps),
        'The two clock reads of an empty bracket cost %s (boot F1) and %s (boot F2). Each CME latency file prints '
        'this value in a comment line %s.' % (
            _rng(min([bs['F1']['overhead_common']] + [v for _, v in bs['F1']['overhead_other']]),
                 max([bs['F1']['overhead_common']] + [v for _, v in bs['F1']['overhead_other']]), 1, 'ns'),
            _rng(min([bs['F2']['overhead_common']] + [v for _, v in bs['F2']['overhead_other']]),
                 max([bs['F2']['overhead_common']] + [v for _, v in bs['F2']['overhead_other']]), 1, 'ns'), r_all),
        ('Which row the page quotes:', [
            'Latency: the best row is the lowest bracket ns per load over the reps of a footprint %s.' % r_lbest,
            'Bandwidth: the best row is the rep with the highest bracket GB/s. Its span rate is the span rate of '
            'that same rep %s.' % r_best,
            'A latency best row prints no span time and no counters. The page takes them from the first rep row '
            'whose bracket ns per load equals the best row.',
            'The files hold %d latency rep rows and %d bandwidth rep rows per boot. The page states it when it '
            'uses rep rows and not best rows.' % (it['F2']['latency_rep_rows'], it['F2']['bandwidth_rep_rows'])])])
    return h


# ------------------------------------------------------------------ 2.6 the counters

def _counter_diagram(V):
    cx, cy, cw, ch = 430, 84, 180, 78
    mid = cy + ch / 2
    nodes = [dict(id='l1', x=cx, y=cy, w=cw, h=ch, title='one CME L1 refill', lines=['one 64 B line arrives'],
                  kind='accent')]
    arrows = []
    for i, (t, ev) in enumerate((('a load that missed', '0x3280'), ('the CME prefetcher', '0x32B2'),
                                 ('a store that missed', '0x3281'))):
        y = 30 + i * 66
        nodes.append(dict(id='c%d' % i, x=40, y=y, w=250, h=52, title=t, lines=['event ' + ev]))
        arrows.append(dict(src='c%d' % i, dst='l1', via=[(360, y + 26), (360, mid)]) if i != 1 else
                      dict(src='c%d' % i, dst='l1'))
    for i, (t, ev, ln) in enumerate((('from inside the cluster', '0x327D', "cluster L3, or a snoop of a core's cache"),
                                     ('from outside the cluster', '0x327E', 'SLC, OCM or DRAM model, through the mesh'))):
        y = 40 + i * 96
        nodes.append(dict(id='s%d' % i, x=750, y=y, w=260, h=66, title=t, lines=['event ' + ev, ln]))
        arrows.append(dict(src='l1', dst='s%d' % i, via=[(680, mid), (680, y + 33)]))
    groups = [dict(x=20, y=4, w=290, h=232, label='the cause: counted once here'),
              dict(x=730, y=4, w=300, h=232, label='the source of the line: counted once more here')]
    return _neutral(V.boxes(nodes, arrows, groups=groups, title='the refill events of the CME L1'))


def _sec_counters(D, V, S):
    it = D.integrity
    worst = {b: _cause_minus_source(D, b) for b in BOOTS}
    events = sorted(set(r['event'] for r in D.cmn('F2')))
    nodes = ', '.join(str(n) for n in _data.REGION_NODE)
    r_ev = _src(S, 'common-events', 'common.h', 'lines 248 to 306 and 430 to 450', 'the counter group, the event '
                'numbers and names (cited there from the Arm C1-SME2 manual, document 107831, chapter 12), and the '
                'note that the L3 events are exploratory')
    r_win = _src(S, 'latency-window', 'latency.c', 'lines 180 to 222', 'the counter start and stop around the bracket')
    r_cmn = _src(S, 'cmncount', 'cmncount.c', 'lines 1 to 40', 'the wrapper that counts mesh events over the whole '
                 'life of a command')
    r_lib = _src(S, 'lib_run', 'lib_run.sh', 'lines 38 to 39', 'the node ids of the five home nodes')
    r_rtl = _readme(S, D, 'F2', 'l3rtl', "line 181 (the operator's reading of the C1-SME2 source for the refill events)")
    r_all = S.ref('files:cme-lat')
    r_l3 = [_fref(S, D, 'F2', 'cme-latency-dram-small-l3.csv'), _fref(S, D, 'F2', 'cme-latency-dram-large-l3.csv')]
    r_cmnf = [_fref(S, D, b, 'cmn-counts.csv') for b in BOOTS]

    n_lat, n_plain, n_l3 = _file_counts(D)
    no_l3 = 'the %d files without <code>-l3</code> in the name' % n_plain
    with_l3 = 'the %d files with <code>-l3</code> in the name' % n_l3
    h = S.h3('setup-counters', 'The counters')
    h += S.bullets([
        'Each latency rep row carries the core cycle counter and six CME events, read through the PMU of the '
        'core %s.' % r_ev,
        'In %s, five of the six events count CME L1 refills: three by cause and two by source. In %s the three '
        'cause events give way to the three L3 events %s.' % (no_l3, with_l3, r_all),
        'The two groups count the same refills in these rows: cause and source differ by at most %s per load on '
        'boot F2 and %s per load on boot F1, over %d rep rows of each boot %s.' % (
            V.num(worst['F2'][0], 5), V.num(worst['F1'][0], 5), worst['F2'][1], r_all)])
    cap = ('The five refill events of the CME L1 cache. Each refill is counted once on the left, by what caused '
           'it, and once on the right, by where the line came from. An arrow on the left leads from a cause to '
           'the refill. An arrow on the right leads from the refill to the event that counts its source. Event numbers from %s. The meaning "a snoop of '
           'a core\'s cache" is from the operator\'s README %s. Rows checked: the %d chain rep rows of each boot '
           'that carry all five columns %s.' % (r_ev, r_rtl, worst['F2'][1], r_all))
    h += S.fig(_counter_diagram(V), cap, 'A load that hits the CME L1 cache counts in none of the five events.',
               id_='fig-counters')

    rows = [
        'Latency rows, read through the PMU of the core (user mode only)',
        [_code('cycles_per_load'), 'core cycle counter', 'cycles of the core clock', 'all CME latency files'],
        [_code('cme_cycles_per_load'), '0x3246<br><code>CME_CYCLES</code>', 'cycles of the CME clock: one total per '
         'counting window', 'all'],
        [_code('cme_l1d_refill_inner_per_load'), '0x327D<br><code style=\"white-space:nowrap\">CME_L1D_CACHE_REFILL_INNER</code>',
         'CME L1 refills with a line from inside the cluster', 'all'],
        [_code('cme_l1d_refill_outer_per_load'), '0x327E<br><code style=\"white-space:nowrap\">CME_L1D_CACHE_REFILL_OUTER</code>',
         'CME L1 refills with a line from outside the cluster', 'all'],
        [_code('cme_l1d_refill_rd_per_load'), '0x3280<br><code style=\"white-space:nowrap\">CME_L1D_CACHE_REFILL_RD</code>',
         'CME L1 refills caused by a load that missed', no_l3],
        [_code('cme_l1d_refill_hwprf_per_load'), '0x32B2<br><code style=\"white-space:nowrap\">CME_L1D_CACHE_REFILL_HWPRF</code>',
         'CME L1 refills caused by the hardware prefetcher of the CME', 'the same %d files' % n_plain],
        [_code('cme_l1d_refill_wr_per_load'), '0x3281<br><code style=\"white-space:nowrap\">CME_L1D_CACHE_REFILL_WR</code>',
         'CME L1 refills caused by a store that missed', 'the same %d files' % n_plain],
        [_code('cme_l3d_hit_per_load'), '0x328E<br><code style=\"white-space:nowrap\">CME_L3D_CACHE_HIT</code>',
         'The event that the Arm manual names L3 hit. What it counts is not validated.', with_l3],
        [_code('cme_l3d_miss_per_load'), '0x328F<br><code style=\"white-space:nowrap\">CME_L3D_CACHE_MISS</code>',
         'The event that the Arm manual names L3 miss. What it counts is not validated.',
         'the same %d files' % n_l3],
        [_code('cme_l3d_refill_per_load'), '0x3290<br><code style=\"white-space:nowrap\">CME_L3D_CACHE_REFILL</code>',
         'The event that the Arm manual names L3 refill. What it counts is not validated.',
         'the same %d files' % n_l3],
        [_code('perf_cov'), '-', 'running time of the counter group divided by its enabled time. The value 1 means '
         'that the group ran for the whole time it was enabled.', 'all'],
        'Mesh counters, one set per command run under the wrapper <code>cmn</code>',
        [_code('hns_pocq_reqs_recvd_all'), 'node ids %s' % nodes, 'requests received by one home node. One row per '
         'home node.', _code('cmn-counts.csv')],
        [_code('hns_mc_reqs_local_all') + ', ' + _code('hns_cache_miss_all'), '-',
         'two sums over all home nodes', _code('cmn-counts.csv')],
        [_code('child_elapsed_ns') + ', ' + _code('helper_elapsed_ns'), '-',
         'life of the command and of the wrapper, in ns of chip time', _code('cmn-counts.csv')],
    ]
    assert set(events) == {'child_elapsed_ns', 'helper_elapsed_ns', 'hns_cache_miss_all', 'hns_mc_reqs_local_all',
                           'hns_pocq_reqs_recvd_all'}, events
    h += S.table(['CSV column or event', 'Event number and name', 'What it counts', 'Files'], rows,
                 caption='The counters of the CME rows %s %s %s %s %s.' % (r_ev, r_cmn, r_lib, r_cmnf[0], r_cmnf[1]),
                 note='Counts per load are the count of the window divided by the loads of the row.', align='llll')
    h = h.replace('<td><code>c', '<td style="white-space:nowrap"><code>c').replace(
        '<td><code>hns_', '<td style="white-space:nowrap"><code>hns_')
    h += S.bullets([
        'In the order of the code the counter start comes before the first clock read of the bracket, and the '
        'counter stop comes after the second clock read. So the counting window holds the bracket, the two '
        'clock reads and the return from the system call that starts the counters. The flush runs before the '
        'window %s.' % r_win,
        'Every count of a row is a total over its window. The rows hold no time stamp of a counter start or '
        'stop.',
        'The mesh counters cover the whole life of a command: the fill of the buffer, the untimed passes, the '
        'flushes and the reps together. %d of the %d CME commands of each boot ran under them %s.' % (
            it['F2']['cmn_cme_labels'], D.commands['F2']['n_cme'], r_cmn),
        'The bandwidth rows carry no counter of the core or of the CME.'])
    h += S.insufficient('The three L3 events (0x328E, 0x328F, 0x3290) have no independent check of their hit and '
                        'miss meaning %s %s %s. A boot whose L3 holds no data, where the hit event must read 0, '
                        'would be one necessary check. The page reports these columns as counts. Every reading of '
                        'a count as the level that served a load is inside a block labelled Hypothesis.'
                        % (r_ev, r_l3[0], r_l3[1]))
    h += S.insufficient('The project file <code>README.md</code> describes the two mesh sums in one line each %s. '
                        '<code>hns_mc_reqs_local_all</code> is the number of requests that all home nodes sent on '
                        'to memory. <code>hns_cache_miss_all</code> is the miss count of the SLC over all nodes. '
                        'Their exact definitions are not in the folders. The event table of the Arm CMN manual '
                        'would give them.' % S.ref('doc:project-readme'))
    return h


# ------------------------------------------------------------------ 2.7 the clock

def _sec_clock(D, V, S):
    ck = D.clock
    pf = D.platform
    bs = D.baseline_summary
    hz = ck['timer_hz']
    r_all = S.ref('files:cme-lat')
    r_dm = [_runref(S, D, b, 'dmesg.txt', 'line %d (timer frequency), line %d (clock resolution), line %d '
                    '(BogoMIPS computed from the timer frequency)' % (
                        pf['timer_' + b]['line'], pf['sched_clock_' + b]['line'], pf['bogomips_' + b]['line']))
            for b in ('F1', 'F2')]

    r_bwf = S.ref('files:cme-bw')
    n_lat = _file_counts(D)[0]
    # the lowest number of loads of the rep rows that D.clock counts (the cme-call rows are left out)
    loads = {}
    for b in BOOTS:
        ls = sorted((r['loads'] for f in _cme_lat_files(D, b) for blk in D.latblocks(b, f)
                     for e in list(blk['sizes'].values()) + [blk['rt']] for r in e['reps']), reverse=True)
        loads[b] = ls[ck[b]['n_rows'] - 1]
        assert len([x for x in ls if x >= loads[b]]) == ck[b]['n_rows'], (b, loads[b])
    assert loads['F1'] == loads['F2'] and ck['F1']['n_rows'] == ck['F2']['n_rows']
    step_ns = 1e9 / hz[0]

    h = S.h3('setup-clock', 'The clock')
    h += S.bullets([
        'The timer behind both times ticks at %s Hz. One tick is %g ns.' % (' and '.join(_n(x) for x in hz), step_ns),
        'The header of every CME command prints this frequency %s %s, and the Linux boot log of both boots prints '
        'it too %s %s.' % (r_all, r_bwf, r_dm[0], r_dm[1]),
        'The cycle counter of the core and the cycle counter of the CME both read %.3f cycles per ns. This is a '
        'measurement: the counted cycles of a row divided by its time %s.' % (ck['cycles_per_ns'], r_all)])
    rows, trows = [], []
    for name, key, per, unit in (('Core cycle counter', 'core', 'cycles / bracket ns', 'core cycles per bracket ns'),
                                 ('CME cycle counter (0x3246)', 'cme', 'CME cycles / span ns', 'CME cycles per span ns')):
        rows.append(dict(header=name))
        for b in BOOTS:
            c = ck[b]
            wide = (c[key + '_hi'] - c[key + '_lo']) / ck['cycles_per_ns'] * 100
            rows.append(dict(label='b' + D.boot_name[b][1:], sub='%d rep rows' % c['n_rows'],
                             a=c[key + '_lo'], b=c[key + '_hi'], gap='%.2f %% wide' % wide,
                             tip='%s, b%s\nlowest rep row: %.4f %s\nmedian: %.4f %s\nhighest rep row: %.4f %s\n'
                                 'highest minus lowest: %.4f (%.2f %% of %.3f)' % (
                                     name, D.boot_name[b][1:], c[key + '_lo'], unit, c[key + '_median'], unit,
                                     c[key + '_hi'], unit, c[key + '_hi'] - c[key + '_lo'], wide, ck['cycles_per_ns'])))
            trows.append(['B' + D.boot_name[b][1:], name, per, '%d' % c['n_rows'], '%.4f' % c[key + '_lo'],
                          '%.4f' % c[key + '_median'], '%.4f' % c[key + '_hi']])
    allv = [r[k] for r in rows if 'a' in r for k in ('a', 'b')]
    # the axis starts on a tick (a multiple of 0.001) below the lowest dot
    lo = int((min(min(allv), ck['cycles_per_ns']) - 0.0003) * 1000) / 1000.0
    svg = V.dumbbell(rows, a_name='lowest rep row', b_name='highest rep row', a_color='#aab1ba', b_color='#1c2024',
                     unit='', xlabel='cycles per ns', fmt=lambda v: '%.4f' % v,
                     refs=[(ck['cycles_per_ns'], '%.3f cycles per ns' % ck['cycles_per_ns'])],
                     xrange=(lo, None), label_w=240)
    cap = ('Counted cycles per ns of chip time: the lowest and the highest rep row of each counter on each boot. '
           'The core cycle counter is divided by the bracket ns of the row. The CME cycle counter is divided by '
           'the span ns of the row. The bold text is the distance between the two dots, in percent of %.3f cycles '
           'per ns. Table %d gives the medians. '
           'Rows: the %d rep rows of %s loads or more in the %d CME latency files of each boot (the '
           '<code>cme-call</code> rows are left out) %s. The axis does not start at 0.' % (
               ck['cycles_per_ns'], S.next_table(), ck['F2']['n_rows'], _n(loads['F2']), n_lat, r_all))
    spread = max(abs(v - ck['cycles_per_ns']) for v in allv) / ck['cycles_per_ns'] * 100
    take = ('Every row is within %.2f %% of %.3f cycles per ns, on both counters and both boots. So one cycle of '
            'the core or of the CME is %.1f ns of chip time.' % (spread, ck['cycles_per_ns'], ck['ns_per_cycle']))
    h += S.fig(svg, cap, take, id_='fig-clock')
    h += S.table(['Boot', 'Counter', 'Ratio', 'Rep rows', 'Lowest', 'Median', 'Highest'], trows,
                 caption='Cycles per ns, exact values %s.' % r_all, align='lllrrrr')
    sh = ck['F2']['short']
    sh1 = ck['F1']['short']
    k64, k320 = [k for k in sh if k != 'cme-call']
    assert sorted(sh) == sorted(sh1)
    r_win = _src(S, 'latency-window', 'latency.c', 'lines 180 to 222', 'the counter start and stop around the bracket')
    rt = bs['all']
    h += S.bullets([
        'Example: one step of the round-trip baseline reads %s and %s core cycles in the rep rows of both '
        'boots %s.' % (_rng(rt['rt_reps_lo'], rt['rt_reps_hi'], 3, 'ns'), _rng(rt['rt_cycles_lo'], rt['rt_cycles_hi'], 2), r_all),
        'On short rows the core cycle counter reads above %.1f cycles per bracket ns: %s on passes of %s, %s on '
        'passes of %s and %s on the <code>cme-call</code> rows (both boots) %s.' % (
            ck['cycles_per_ns'],
            _rng(min(sh[k64]['lo'], sh1[k64]['lo']), max(sh[k64]['hi'], sh1[k64]['hi']), 2), k64,
            _rng(min(sh[k320]['lo'], sh1[k320]['lo']), max(sh[k320]['hi'], sh1[k320]['hi']), 2), k320,
            _rng(min(sh['cme-call']['lo'], sh1['cme-call']['lo']), max(sh['cme-call']['hi'], sh1['cme-call']['hi']), 2),
            r_all),
        'In the order of the code the counting window starts before the bracket and ends after it. So it counts '
        'cycles that the bracket time does not hold %s. '
        '%s gives the core cycle count as time minus the bracket time. The rows hold no time stamp that places '
        'that difference before or after the bracket.' % (r_win, S.xref('callcost-gap', cap=True)),
        'For time on those rows the page uses the ns columns, not the cycle columns. %s also covers the CME '
        'cycle counter on the <code>cme-call</code> rows.' % S.xref('callcost-gap', cap=True),
        'The Linux boot log also prints "%.2f BogoMIPS" (a speed value that Linux prints at boot). Linux computes '
        'it from the timer frequency. So it is not evidence of the core clock %s.' % (pf['bogomips_F1']['value'], r_dm[0]),
        'All times are chip time on the emulator. The real time on the emulator host is much longer and is in no CSV file.'])
    return h


# ------------------------------------------------------------------ 2.8 data integrity

def _unlisted(D, boot):
    """Files of the run folder that its checksum list does not name (relative paths, sorted)."""
    run = _data.RUN[boot]
    listed = set(name for name, _ in D.integrity[boot]['sha']['entries'])
    found = []
    for d, _, files in os.walk(run):
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), run)
            if rel not in listed:
                found.append(rel)
    return sorted(found)


def _sec_integrity(D, V, S):
    it = D.integrity
    cm = D.commands
    r_sha = [_runref(S, D, b, 'SHA256SUMS') for b in ('F1', 'F2')]
    r_log = [_fref(S, D, b, 'log.txt') for b in ('F1', 'F2')]
    r_all = S.ref('files:cme-lat')
    r_bwf = S.ref('files:cme-bw')
    r_cmnf = [_fref(S, D, b, 'cmn-counts.csv') for b in ('F1', 'F2')]

    unl = {b: _unlisted(D, b) for b in BOOTS}

    def both(f):
        return [f('F1'), f('F2')]

    h = S.h3('setup-integrity', 'Data integrity')
    h += S.bullets([
        'Every file listed in the checksum list of each run folder matches its SHA-256 checksum: %d of %d on '
        'boot F1 and %d of %d on boot F2. The page generator computes the checksums when it builds the page '
        '%s %s.' % (it['F1']['sha']['ok'], it['F1']['sha']['total'], it['F2']['sha']['ok'], it['F2']['sha']['total'],
                    r_sha[0], r_sha[1]),
        'The lists cover every result file and the Linux boot log. They do not cover %s.' % (
            ' and '.join(_code(x) for x in unl['F2']) if unl['F1'] == unl['F2'] else
            '%s (boot F1) and %s (boot F2)' % (', '.join(_code(x) for x in unl['F1']),
                                               ', '.join(_code(x) for x in unl['F2']))),
        '<code>README.md</code> is the operator\'s README, the source of every fact with that tag on this page. '
        'It has no checksum.',
        'No command failed %s %s.' % (r_log[0], r_log[1]),
        'In every counter row the counter group ran for the whole time it was enabled %s.' % r_all])
    done = lambda b: ', '.join('%s: %d failed' % (_code(d['script']), d['failed']) for d in cm[b]['done'])
    rows = [
        'Files',
        ['Files that match their checksum / files listed'] + both(
            lambda b: '%d / %d' % (it[b]['sha']['ok'], it[b]['sha']['total'])) + [_nb('%s %s' % tuple(r_sha))],
        ['Files in the run folder that the list does not cover'] + both(
            lambda b: ', '.join(_code(x) for x in unl[b]) or 'none') + [''],
        ['CME latency files, CME bandwidth files'] + both(
            lambda b: '%d, %d' % (it[b]['n_cme_latency_files'], it[b]['n_cme_bandwidth_files'])) + [_nb('%s %s' % (r_all, r_bwf))],
        'Commands',
        ['Commands in <code>log.txt</code>'] + both(lambda b: '%d' % cm[b]['n_commands']) + [_nb('%s %s' % tuple(r_log))],
        ['CME commands: latency + bandwidth'] + both(
            lambda b: '%d = %d + %d' % (cm[b]['n_cme'], cm[b]['n_cme_latency'], cm[b]['n_cme_bandwidth'])) + [''],
        ['CME commands under the mesh counters'] + both(lambda b: '%d' % cm[b]['n_cme_cmn']) + [''],
        ['Failed commands, as each script reports at its end'] + both(done) + [''],
        ['CPUs named by the CME commands'] + both(lambda b: ', '.join('CPU %d' % c for c in it[b]['cpus'])) + [''],
        ['Timer frequency in the command headers'] + both(
            lambda b: ', '.join('%s Hz' % _n(x) for x in it[b]['cntfrq_hz'])) + [_nb('%s %s' % (r_all, r_bwf))],
        'Counter coverage of the CME latency rows',
        ['Rep rows'] + both(lambda b: '%d' % it[b]['latency_rep_rows']) + [r_all],
        ['<code>perf_cov</code>, lowest to highest (1 = the group ran for the whole time it was enabled)'] + both(
            lambda b: _rng(it[b]['perf_cov_min'], it[b]['perf_cov_max'], 4)) + [''],
        ['Comment lines <code># perf:</code> (a counter was refused or shared its time)'] + both(
            lambda b: '%d' % it[b]['perf_lines']) + [''],
        ['Rep rows with a missing counter field'] + both(lambda b: '%d' % it[b]['missing_counter_fields']) + [''],
        'CME bandwidth rows',
        ['Rep rows with a span time / rep rows'] + both(
            lambda b: '%d / %d' % (it[b]['bandwidth_reps_with_span'], it[b]['bandwidth_rep_rows'])) + [r_bwf],
        ['Best rows'] + both(lambda b: '%d' % it[b]['bandwidth_best_rows']) + [''],
        'Mesh counters',
        ['Rows in <code>cmn-counts.csv</code> / labels / CME labels'] + both(
            lambda b: '%d / %d / %d' % (it[b]['cmn_rows'], it[b]['cmn_labels'], it[b]['cmn_cme_labels'])) + [_nb('%s %s' % tuple(r_cmnf))],
        ['Rows whose counter did not run for its whole enabled time'] + both(
            lambda b: '%d' % it[b]['cmn_multiplexed_rows']) + [''],
    ]
    h += S.table(['Check', 'B' + D.boot_name['F1'][1:], 'B' + D.boot_name['F2'][1:], 'Reference'], rows,
                 caption='Integrity checks, computed from the raw files when the page is built.',
                 note='Boot F1 also ran %d core commands before its CME commands. Their mesh labels are in its '
                      '<code>cmn-counts.csv</code>.' % cm['F1']['n_core'], align='llll')
    return h


# ------------------------------------------------------------------ the section

def build(D, V, S):
    """html of the section body.  The caller adds the h2 (KEY, TITLE)."""
    _terms(S)
    cm = D.commands
    h = S.takeaways([
        'The page uses two boots of one emulated chip. B%s and b%s ran the same %d CME commands on %s.' % (
            D.boot_name['F1'][1:], D.boot_name['F2'][1:], cm['F2']['n_cme'],
            ', '.join('CPU %d' % c for c in D.integrity['F2']['cpus'])),
        'Two tests produce every CME row. The latency test gives the time per chain load. The bandwidth test '
        'gives the bytes per time when the CME reads, writes or copies a whole buffer in address order.',
        'Each row has a bracket time and a span time. Both come from a timer of %g ns steps. Both cycle '
        'counters read %.3f cycles per ns.' % (1e9 / D.clock['timer_hz'][0], D.clock['cycles_per_ns']),
        'All files that the checksum lists name match their checksums. No command failed.' if all(
            D.integrity[b]['sha']['ok'] == D.integrity[b]['sha']['total'] and cm[b]['failed'] == 0 for b in BOOTS)
        else 'Some files or commands fail their checks: see the last table of this section.'])
    h += _sec_path(D, V, S)
    h += _sec_boots(D, V, S)
    h += _sec_latency(D, V, S)
    k, r_best = _sec_kernels(D, V, S)
    h += k
    h += _sec_times(D, V, S, r_best)
    h += _sec_counters(D, V, S)
    h += _sec_clock(D, V, S)
    h += _sec_integrity(D, V, S)
    return h
