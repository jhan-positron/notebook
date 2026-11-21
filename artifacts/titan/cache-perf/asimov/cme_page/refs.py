"""The one list of references of the page.

Each section module calls S.ref(key, text) with its own key and its own text.
install(S, D) gives the page object one canonical entry per file or document
and a rule that maps every section key to canonical keys.  So one file is one
entry in the References, whichever section cites it.

- canonical(D)  -> {canonical key: entry text (html)}
- resolve(key)  -> list of canonical keys, or None for a key that stays as it is
- install(S, D) -> sets both on the page object (S.ref uses them)

The line numbers of result files come from the data layer.  The line numbers of
source files and documents are typed here, once.
"""
import os
import re

from . import data as _data

BOOTS = _data.BOOTS


def _code(s):
    return '<code>%s</code>' % s


def _rel(path):
    return os.path.relpath(path, _data.ROOT)


def _nlines(path):
    with open(path, 'rb') as f:
        return f.read().count(b'\n')


def _processor_lines(path):
    """[(line number, CPU number)] of the 'processor : N' lines of a system listing."""
    out = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, 1):
            m = re.match(r'^processor\s*:\s*(\d+)\s*$', line)
            if m:
                out.append((i, int(m.group(1))))
    return out


def _lines(ls):
    """'line 4' / 'lines 14 to 27' / 'lines 30, 32, 36' for a list of line numbers."""
    ls = sorted(set(ls))
    if not ls:
        return ''
    if len(ls) == 1:
        return 'line %d' % ls[0]
    if ls[-1] - ls[0] == len(ls) - 1:
        return 'lines %d to %d' % (ls[0], ls[-1])
    return 'lines %s' % ', '.join('%d' % x for x in ls)


def _Boot(D, b):
    n = D.boot_name[b]
    return n[0].upper() + n[1:]


# ------------------------------------------------------------------ canonical entries

def _csv_entry(D, b, name):
    path = os.path.join(_data.BOOTDIR[b], name)
    log = D.log_lines(b, name)
    cmd = ''
    if log:
        cmd = ' Its command%s: %s of %s in the same folder.' % (
            's' if len(log) > 1 else '', _lines(log), _code('log.txt'))
    return '%s, file %s (%d lines).%s' % (_Boot(D, b), _code(_rel(path)), _nlines(path), cmd)


def _group(D, b, rows, what, rowtext):
    files = [r['src'] for r in rows]
    log = [l for f in files for l in D.log_lines(b, f)]
    return ('%s of %s: %s to %s, %s and %s in %s. %s Their commands: lines %d to %d of %s in the same folder.' % (
        what, D.boot_name[b], _code(files[0]), _code(files[4]), _code(files[5]), _code(files[6]),
        _code(_rel(_data.BOOTDIR[b]) + '/'), rowtext, min(log), max(log), _code('log.txt')))


def canonical(D):
    """{canonical key: entry text}.  One entry per file, file group or document."""
    C = {}
    cm = D.commands
    plat = D.platform

    # ---- result files, one entry per file and boot (filled on demand by _file_text)
    # ---- the run folders
    for b in BOOTS:
        Bn = _Boot(D, b)
        run = _rel(_data.RUN[b])
        c = cm[b]
        C['file:%s:log.txt' % b] = (
            '%s, command log %s (%d lines). Lines %d to %d: the %d CME commands. Lines %d and %d: CPU 3 goes '
            'offline before them and comes back after them. Lines %s: the L3 status register of the cluster. '
            '%s %s: the count of failed commands that each script prints at its end.' % (
                Bn, _code(_rel(os.path.join(_data.BOOTDIR[b], 'log.txt'))),
                _nlines(os.path.join(_data.BOOTDIR[b], 'log.txt')), c['cme_first_line'], c['cme_last_line'],
                c['n_cme'], c['cpu3_offline_line'], c['cpu3_online_line'],
                ' and '.join('%d' % x['line'] for x in c['clusterpwrstat']),
                'Lines' if len(c['done']) > 1 else 'Line', ' and '.join('%d' % d['line'] for d in c['done'])))
        om = D.dmesg_ocm_maps[b]
        C['run:%s:dmesg.txt' % b] = (
            '%s, Linux boot log %s. Line %d: the timer frequency. Line %d: the clock resolution. Line %d: BogoMIPS, '
            'computed from the timer frequency. Lines %d to %d: the streaming vector length. The %s between line %d and '
            'line %d: the OCM mappings, each made of single 4 KiB pages.' % (
                Bn, _code(run + '/dmesg.txt'), plat['timer_' + b]['line'], plat['sched_clock_' + b]['line'],
                plat['bogomips_' + b]['line'], plat['sme_vl_min_' + b]['line'], plat['sme_vl_default_' + b]['line'],
                '%d mapping lines' % om['n'], om['first_line'], om['last_line']))
        C['run:%s:SHA256SUMS' % b] = '%s, checksum list %s.' % (Bn, _code(run + '/SHA256SUMS'))

        # mesh counters
        rows = [r for r in D.mesh_requests[b] if r['ocm']]
        g = D.mesh_row(b, D.mesh_g7[b]['label'])
        ctl = D.mesh_control[b]
        C['file:%s:cmn-counts.csv' % b] = (
            '%s, mesh counter file %s (%d lines). Label %s begins at line %d. The %d labels that start with %s '
            'begin at lines %d to %d. %sEvent %s has one row per home node. Events %s and %s are sums over all '
            'home nodes.' % (
                Bn, _code(_rel(os.path.join(_data.BOOTDIR[b], 'cmn-counts.csv'))),
                _nlines(os.path.join(_data.BOOTDIR[b], 'cmn-counts.csv')), _code(g['label']), g['line'],
                len(rows), _code('cme-ocm-'), min(r['line'] for r in rows), max(r['line'] for r in rows),
                ('Label %s is the idle control (%s). ' % (_code(ctl['label']), ctl['what'])) if ctl
                else 'The file has no idle control label. ',
                _code('hns_pocq_reqs_recvd_all'), _code('hns_mc_reqs_local_all'), _code('hns_cache_miss_all')))

        # the OCM file groups
        C['ocm-lat:%s' % b] = _group(
            D, b, D.ocm_lat[b], 'The seven CME latency files on OCM',
            'Rows %s to %s (the timed passes) and %s of each file.' % (
                _code('cme-fresh1'), _code('cme-fresh7'), _code('cme-best')))
        C['ocm-bw:%s' % b] = _group(
            D, b, D.ocm_bw[b], 'The seven CME bandwidth files on OCM',
            'All rep rows and the %s row of each file, columns %s and %s.' % (
                _code('best'), _code('aggregate_GBps'), _code('span_s')))

    C['ocm-core-lat-F1'] = _group(
        D, 'F1', D.ocm_core, 'The seven core latency files on OCM',
        'Rows %s to %s and %s of each file.' % (_code('fresh1'), _code('fresh7'), _code('best')))
    C['ocm-core-bw-F1'] = _group(
        D, 'F1', D.ocm_bw_core, 'The seven core bandwidth files on OCM', 'Rep rows and the %s row.' % _code('best'))

    ms = D.mesh_summary
    bl = [r['base_line'] for r in D.mesh_layout]
    cl = [c['line'] for c in plat['caches']]
    proc = _processor_lines(os.path.join(_data.BOOTDIR['F1'], 'sysinfo.txt'))
    pl, pn = [p[0] for p in proc], [p[1] for p in proc]
    C['file:F1:sysinfo.txt'] = (
        '%s, system listing %s. Lines %d to %d: the %d processor entries (CPU %d to CPU %d). Lines %d to %d: the '
        'cache sizes that Linux reports for CPU 2. Line %d: the number '
        'of 2 MiB pages. Line %d: the huge page size. Lines %d to %d: the physical address ranges of the five OCM '
        'regions. Lines %d to %d: the mesh map printed by the Linux mesh driver (%s). Boot F2 wrote no such '
        'file.' % (
            _Boot(D, 'F1'), _code(_rel(os.path.join(_data.BOOTDIR['F1'], 'sysinfo.txt'))), min(pl), max(pl), len(pl),
            min(pn), max(pn), min(cl), max(cl),
            plat['hugepages_total']['line'], plat['hugepagesize']['line'], min(bl), max(bl),
            ms['map_first_line'], ms['map_last_line'], _code('arm-cmn')))

    # ---- file groups over both boots
    dirs = ' and '.join(_code(_rel(_data.BOOTDIR[b]) + '/') for b in BOOTS)
    C['files:cme-lat'] = (
        'The 12 CME latency files of each boot: %s in %s. Each file begins with the rows %s (the round-trip '
        'baseline) and %s (64 kernel calls in one bracket), at lines 4 to 11. Comment line 3 gives the time of '
        'an empty bracket.' % (_code('cme-latency-*.csv'), dirs, _code('cme-roundtrip'), _code('cme-call')))
    C['files:cme-bw'] = (
        'The 14 CME bandwidth files of each boot: %s in %s. The header comment of each command gives its options '
        '(%s, %s, %s, %s).' % (_code('cme-bandwidth-*.csv'), dirs, _code('asm_passes'), _code('no_fold'),
                               _code('dsb_st'), _code('flush_before')))

    # ---- the operator's READMEs (typed line numbers)
    C['readme:F1'] = (
        "Operator's README of %s, file %s. Lines 7 and 36 to 44: the self-test %s. Lines 66 to 68: the L3 power "
        'status register and the reading of the value 0x70. Lines 238 to 241: the reading of the C1-SME2 source '
        "for the refill events and the L3 events (line 240: a core's cache in the cluster can supply a CME L1 "
        'refill). Lines 243 to 253, section "The memory model behind the home node": the DRAM model has no '
        'configured delay. Lines 343 to 354, section "Platform facts": emulator image, firmware, CPU placement, '
        'caches, CME, OCM, DRAM (lines 348 to 349: the SLC is five home nodes of 1 MiB, the firmware locks 4 of '
        '16 ways of each as OCM, the CME has a 64 KiB L1 data cache and a TLB of 24 entries, and the firmware '
        'sets the power controller of each CME to dynamic mode).' % (
            D.boot_name['F1'], _code(_rel(os.path.join(_data.RUN['F1'], 'README.md'))), _code('cme_test')))
    C['readme:F2'] = (
        "Operator's README of %s, file %s. Lines 18 to 29, section \"The prefetchers\": the firmware hook that "
        'turns the prefetchers off (%s bit 48 for the data prefetchers of the cores, %s bit 28 for the '
        'prefetcher of the CME, on CPUs 2 to 9), its register readbacks and its check. Lines 65 to 74: what '
        'differs between the two boots (the firmware, the run order, the physical pages of each buffer) and '
        'what a difference between the boots means. Lines 178 to 183, section "The CME L3 events": the reading '
        'of the C1-SME2 source for the refill events and the L3 events. Lines 269 to 280, section "Platform '
        'facts". Section "OCM mappings".' % (
            D.boot_name['F2'], _code(_rel(os.path.join(_data.RUN['F2'], 'README.md'))),
            _code('IMP_CPUECTLR_EL1'), _code('IMP_CMECFG_EL1')))

    # ---- source files (typed line numbers)
    C['src:cme_kern.S'] = (
        'Benchmark source, file %s: the CME kernels of the latency test and of the bandwidth test. Lines 1 to 67: '
        'header comment. Lines 71 to 104: the entry and the exit of every kernel (macros %s and %s): register '
        'save, SMSTART, ISB, first stamp, then ISB, second stamp, SMSTOP, register restore. Lines 116 to 125: the '
        'chain-load kernel (its loop, lines 120 to 123: LD1D, LASTB, SUBS, B.NE). Lines 131 to 140: %s, the '
        'kernel of the round-trip baseline (its loop, lines 135 to 138: a register copy with DUP, then LASTB, '
        'SUBS, B.NE). Lines 148 to 221: %s, '
        'the read loop (4 load instructions of 4 vectors each at lines 174 to 177, 16 EOR instructions at lines '
        '178 to 193 and 3 loop instructions per 1 KiB). Lines 227 to 253: %s (4 store instructions of 4 vectors '
        'each at lines 240 to 243). Lines 264 to 306: %s (4 load instructions at lines 275 to 278, 16 EOR '
        'instructions at lines 279 to 294). Lines 312 to 333: %s (4 store instructions at lines 323 to 326). '
        'Lines 339 to 357: %s. '
        'Lines 363 to 397: %s. Lines 403 to 421: %s.' % (
            _code('cme_kern.S'), _code('SM_ENTER'), _code('SM_LEAVE'), _code('cme_roundtrip'), _code('cme_read4'),
            _code('cme_write4'), _code('cme_read4_n'), _code('cme_write4_n'), _code('cme_copy4'),
            _code('cme_read1'), _code('cme_write1')))
    C['src:bandwidth.c'] = (
        'Benchmark source, file %s. Line 11: the core kernels use LDP and STP of two 16-byte registers. Lines 314 '
        'to 342: one pass makes one kernel call per segment of the buffer, so one call per OCM region (line 341: '
        'a copy counts the bytes read plus the bytes written). Lines 417 to 447: how a rep runs: one untimed '
        'warm-up pass (line 421), the flush, the reset of the span sum, the two clock reads of the bracket (lines '
        '425 to 436) and one kernel call per pass. Line 519: the program refuses the counter option %s together '
        'with %s. Line 545: %s takes one worker, because the two stamps of a span are one global pair. Lines 573 '
        'to 620: the choice of the best row.' % (
            _code('bandwidth.c'), _code('--perf'), _code('--cme'), _code('--cme')))
    C['src:latency.c'] = (
        'Benchmark source, file %s. Lines 84 to 137: how a chain is built (one random cycle through all member '
        'lines, fixed seeds). Lines 201 to 222: one timed rep (function %s): the flush before it, the counter start and '
        'stop around the bracket, then the counter read and the print of the row. Lines 232 to 243: the chains of a footprint and the two untimed walks before '
        'the first rep (lines 241 to 242). Lines 244 to 258: the timed reps of each chain kind. Lines 259 to '
        '313: the best rows, the rows of the round-trip baseline and the %s rows (lines 299 to 313: 64 calls in '
        'one bracket, their spans summed by the kernel).' % (_code('latency.c'), _code('timed_walk'), _code('cme-call')))
    C['src:common.h'] = (
        'Benchmark source, file %s. Lines 56 to 61: the clock read of the bracket. Lines 248 to 306: the counter '
        'group (line 252: every counter is opened with the flag that excludes kernel-mode cycles) '
        'and the event numbers and names, cited there from the Arm C1-SME2 manual, document 107831, '
        'chapter 12. Lines 430 to 451: the event set %s, the three L3 event names, and the statement that the '
        'three counts are exploratory: no fit or attribution reads them until a control validates them. Lines '
        '462 to 495: the counter read (a %s call), the counter start and the counter stop (%s calls). Lines '
        '585 to 597: the sum of the spans of a rep.' % (_code('common.h'), _code('cme-l3'), _code('read'), _code('ioctl')))
    C['src:cmncount.c'] = ('Benchmark source, file %s, lines 1 to 40: the wrapper that counts mesh events over '
                           'the whole life of a command.' % _code('cmncount.c'))
    C['src:lib_run.sh'] = ('Benchmark script %s, lines 38 to 39: the node ids of the home nodes of OCM regions '
                           '0 to 4 (%s).' % (_code('lib_run.sh'),
                                             _code('HNS="%s"' % ','.join('%d' % n for n in _data.REGION_NODE))))
    C['src:run_cme.sh'] = (
        'Benchmark script %s. Lines 10 to 11: CPU 3 is taken offline so that the CME of the cluster is not '
        'shared. Line 38 (comment): the CME has "its own 64 KiB L1, then the DSU L3, then the mesh". No CSV '
        "file states the size of the CME L1. The operator's README of boot F1 gives it." % _code('run_cme.sh'))

    # ---- documents
    C['doc:plan'] = (
        'Run plan %s, section 13 (lines 251 to 279). Lines 257 and 262: the store hypothesis and what the DSB ST '
        'rows can show. Line 267: the L3 events are exploratory, and no fit reads the hit and miss columns '
        'until a control row validates them. Line 269: the statement that the span of a store call does not '
        'wait for the stores unless the kernel ends with DSB ST. Line 271: the fit rule, "a residual over 2 %% '
        'of the smallest pass time voids that intercept". Line 278: what stays open, by choice.' %
        _code('follow-up-run-plan.md'))
    C['doc:cme-plan'] = (
        'Test plan %s. Section 2.3, line 206: no row with two cores or with several CMEs. Section 6, line 454: '
        'no row isolates the cause of the store rate.' % _code('CME-plan.md'))
    C['doc:project-readme'] = (
        'Project file %s. Lines 39 to 40: the mesh port of CPU 2 is one mesh step from the home nodes of OCM '
        'regions 0 to 2 and three mesh steps from the home nodes of regions 3 and 4. Line 40 gives notes of the '
        'operator as the source of these step counts. Lines 71 to 74: the round-trip baseline has no memory '
        'access. It shares the register return path with a chain load, but it is not a measured part of one. '
        'The chain load minus the baseline is a derived number, not the memory latency. Lines 119 to 123: what the '
        'flush before a timed rep removes.' % _code('README.md'))
    C['doc:sog'] = (
        'Arm C1-Nano Core Software Optimization Guide, document 109590_0001_04, sections 2.33 and 2.33.3: load '
        'and store instructions have a bandwidth of two. The core issues at most 2 load or store instructions '
        'per cycle to the CME. The guide gives no limit in vectors or in bytes. On disk: %s.' %
        _code('refs/arm-c1-nano-r0p1-sog-109590_0001_04.pdf'))
    C['doc:llvm'] = (
        'LLVM scheduling model of the C1-Nano, file %s. Lines 84 to 86: one CME load pipe (line 84), one CME store '
        'pipe (line 85) and one CME prefetch pipe (line 86). Line 361 and lines 2885 to 2890: a load of 4 vectors '
        '(%s) holds the CME load pipe for 2 cycles.' % (_code('refs/AArch64SchedC1Nano.td'), _code('LD1B_4Z')))
    C['doc:trm'] = (
        'Arm C1-SME2 Technical Reference Manual, document 107831, section 6 (the CME L1 data cache) and chapter '
        '12 (the event numbers). The document is not on disk. The page relies on the citation in %s, lines 258 '
        "to 271, and on the operator's README." % _code('common.h'))
    return C


# ------------------------------------------------------------------ section key -> canonical keys

_BOTH = ['F1', 'F2']

ALIAS = {
    # operator's READMEs
    'readme:F1:platform': ['readme:F1'], 'readme:F1:l3': ['readme:F1'], 'readme:F1:cmetest': ['readme:F1'],
    'readme:F1:caches': ['readme:F1'], 'readme:F1:snoop': ['readme:F1'], 'readme-f1-memory-model': ['readme:F1'],
    'readme-f1': ['readme:F1'],
    'readme:F2:platform': ['readme:F2'], 'readme:F2:l3rtl': ['readme:F2'], 'readme:F2:prefetch': ['readme:F2'],
    'readme:F2:order': ['readme:F2'], 'readme:F2:prefetchers': ['readme:F2'], 'readme-f2': ['readme:F2'],
    'l3:readme-f2': ['readme:F2', 'readme:F1'],
    # documents
    'doc:sog-nano': ['doc:sog'], 'sog-109590': ['doc:sog'], 'doc:sog-c1-nano': ['doc:sog'],
    'doc:trm-sme2': ['doc:trm'],
    'llvm-c1nano-td': ['doc:llvm'], 'doc:llvm-c1-nano': ['doc:llvm'],
    'plan-fit-rule': ['doc:plan'], 'doc/plan-fit-rule': ['doc:plan'], 'plan-13': ['doc:plan'],
    'cme-plan': ['doc:cme-plan'],
    'readme:project:flush': ['doc:project-readme'], 'ocm-readme-steps': ['doc:project-readme'],
    # source files
    'src:run_cme': ['src:run_cme.sh'],
    'src:kern-chain': ['src:cme_kern.S'], 'src:kern-all': ['src:cme_kern.S'], 'src:kern-span': ['src:cme_kern.S'],
    'cme-kern-read4': ['src:cme_kern.S'], 'src/cme_kern.S': ['src:cme_kern.S'], 'cme-kern': ['src:cme_kern.S'],
    'src:latency-chain': ['src:latency.c'], 'src:latency-modes': ['src:latency.c'],
    'src:latency-best': ['src:latency.c'], 'src:latency-window': ['src:latency.c'],
    'src:latency.c:walks': ['src:latency.c'], 'src/latency.c': ['src:latency.c'],
    'src:bandwidth-rep': ['src:bandwidth.c'], 'src:bandwidth-best': ['src:bandwidth.c'],
    'src:bandwidth-noperf': ['src:bandwidth.c'], 'src/bandwidth.c': ['src:bandwidth.c'],
    'ocm-bandwidth-c-segments': ['src:bandwidth.c'], 'bandwidth-c-open': ['src:bandwidth.c'],
    'src:common-clock': ['src:common.h'], 'src:common-events': ['src:common.h'], 'l3:common.h': ['src:common.h'],
    'common-h-l3': ['src:common.h'], 'l3-events-rule': ['src:common.h', 'doc:plan'],
    'src:cmncount': ['src:cmncount.c'], 'src:lib_run': ['src:lib_run.sh'], 'ocm-lib-run-hns': ['src:lib_run.sh'],
    # file groups
    'files:ocm-lat': ['ocm-lat:F1', 'ocm-lat:F2'],
    'ocm-cme-lat-F1': ['ocm-lat:F1'], 'ocm-cme-lat-F2': ['ocm-lat:F2'],
    'F1/cme-ocm-pass-rows': ['ocm-lat:F1'], 'F2/cme-ocm-pass-rows': ['ocm-lat:F2'],
    'ocm-cme-bw-F1': ['ocm-bw:F1'], 'ocm-cme-bw-F2': ['ocm-bw:F2'],
    'F1/cme-call-rows': ['files:cme-lat'], 'F2/cme-call-rows': ['files:cme-lat'],
    # mesh counters, system listing, boot logs
    'ocm-cmn-F1': ['file:F1:cmn-counts.csv'], 'ocm-cmn-g7-F1': ['file:F1:cmn-counts.csv'],
    'ocm-cmn-control-F1': ['file:F1:cmn-counts.csv'],
    'ocm-cmn-F2': ['file:F2:cmn-counts.csv'], 'ocm-cmn-g7-F2': ['file:F2:cmn-counts.csv'],
    'ocm-mesh-map': ['file:F1:sysinfo.txt'], 'ocm-iomem': ['file:F1:sysinfo.txt'],
    'sysinfo:F1:caches': ['file:F1:sysinfo.txt'], 'l3:sysinfo-l3': ['file:F1:sysinfo.txt'],
    'raw:sysinfo-caches': ['file:F1:sysinfo.txt'], 'sysinfo-F1-hugepage': ['file:F1:sysinfo.txt'],
    'dmesg-F2-ocm': ['run:F2:dmesg.txt'],
    'log-cme': ['file:F1:log.txt', 'file:F2:log.txt'],
    # several files in one section key
    'ocm-dram-flushed-lat': ['file:F1:cme-latency-dram-flushed.csv', 'file:F2:cme-latency-dram-flushed.csv'],
    'csv:cme-latency-dram-small-large': [
        'file:F1:cme-latency-dram-small.csv', 'file:F1:cme-latency-dram-large.csv',
        'file:F2:cme-latency-dram-small.csv', 'file:F2:cme-latency-dram-large.csv'],
}

_RX_BOOT_FIRST = re.compile(r'^(?:file|run|l3):(F[12]):([^:]+)(?::.*)?$')
_RX_SLASH = re.compile(r'^(F[12])/([^/]+)$')
_RX_CSV = re.compile(r'^csv:([^:]+)$')
_RX_BOOT_LAST = re.compile(r'^file:([^:]+):(F1\+F2|F1|F2)$')


def _one(boot, name):
    """Canonical key of one result file of one boot."""
    if name in ('dmesg.txt', 'SHA256SUMS'):
        return 'run:%s:%s' % (boot, name)
    if name.startswith('cme-latency-ocm-'):
        return 'ocm-lat:%s' % boot
    if name.startswith('cme-bandwidth-ocm-'):
        return 'ocm-bw:%s' % boot
    if name.startswith('latency-ocm-') and name.endswith('-cpu2.csv'):
        return 'ocm-core-lat-F1'
    if name.startswith('bandwidth-ocm-'):
        return 'ocm-core-bw-F1'
    return 'file:%s:%s' % (boot, name)


def resolve(key):
    """Canonical keys of a section key.  None: the key is not known here and stays as it is."""
    if key in ALIAS:
        return ALIAS[key]
    m = _RX_BOOT_FIRST.match(key)
    if m:
        return [_one(m.group(1), m.group(2))]
    m = _RX_SLASH.match(key)
    if m:
        return [_one(m.group(1), m.group(2))]
    m = _RX_CSV.match(key)
    if m:
        name = m.group(1)
        return [_one(b, name) for b in (_BOTH if name.startswith('cme-') else ['F1'])]
    m = _RX_BOOT_LAST.match(key)
    if m:
        return [_one(b, m.group(1)) for b in m.group(2).split('+')]
    return None


def install(S, D):
    """Give the page object the canonical entries and the key rule.  Call before any section."""
    canon = canonical(D)

    def text_of(ckey):
        if ckey in canon:
            return canon[ckey]
        m = re.match(r'^file:(F[12]):(.+)$', ckey)
        if m and os.path.exists(os.path.join(_data.BOOTDIR[m.group(1)], m.group(2))):
            canon[ckey] = _csv_entry(D, m.group(1), m.group(2))
            return canon[ckey]
        return None

    as_is = ('addr-file', 'addr-readme')      # the one row of a third boot: its own two entries

    def res(key):
        if key in canon or key in as_is:
            return [key]
        return resolve(key)

    S.ref_resolve = res
    S.ref_text = text_of
