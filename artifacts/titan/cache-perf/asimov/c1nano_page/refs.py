"""The one list of references of the page.

Each section module calls S.ref(key) with a canonical key (see below), or with
its own key and its own text.  install(S, D) gives the page object one canonical
entry per file or document.  So one file is one entry in the References,
whichever section cites it.

- canonical(D)  -> {canonical key: entry text (html)}  (documents, sources, READMEs)
- resolve(key)  -> (list of canonical keys, cited lines or None), or None for a key
                   that stays as the section wrote it
- install(S, D) -> sets the key rule, the entry text and the final text on S

Canonical keys:
  file:<boot>:<name>            one result file of a boot (built on demand)
  group:<boot>:<pattern>        a group of result files, pattern with * (built on demand)
  run:<boot>:dmesg.txt          the Linux boot log of the boot's run folder
  run:<boot>:SHA256SUMS         the checksum list of the boot's run folder
  readme:<boot>                 the operator's README of the boot's run folder
  src:<file>                    a benchmark source or script
  doc:plan, doc:seqread, doc:project-readme, doc:sog
<boot> is F1, E, B, C, D or R3.

Cited lines.  A key may end with ":<lines>", for example
"file:F1:latency-dram-small.csv:60-62" or "readme:F1:247,354".  The entry of the
file then lists the cited lines ("Cited: lines 60 to 62 (the text given with the
key)").  All line numbers of the page live in the References this way.

This module does not import the data layer.  It reads the folder names below and
the files themselves.  When D has log_lines(boot, file), the entry of a result
file also names the log.txt lines of its commands.
"""
import fnmatch
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOOTS = ['F1', 'E', 'B', 'C', 'D', 'R3']
BOOT_NAME = {b: 'boot ' + b for b in BOOTS}
RUN = {
    'F1': 'results/membench-jibin-011',
    'E': 'results/membench-jibin-010',
    'B': 'results/membench-jibin-006',
    'C': 'results/membench-jibin-007',
    'D': 'results/membench-jibin-008',
    'R3': 'results/membench-jibin-004',
}
BOOTDIR = {
    'F1': RUN['F1'] + '/results/bootF1',
    'E': RUN['E'] + '/results/bootE',
    'B': RUN['B'] + '/results/bootB',
    'C': RUN['C'] + '/results/bootC',
    'D': RUN['D'] + '/results/bootD',
    'R3': RUN['R3'] + '/results/19700101T000000Z',
}
RUN_F2 = 'results/membench-jibin-012'      # the boot with CME rows only: cited as a folder, not as a boot
_KIND = {'log.txt': 'command log', 'sysinfo.txt': 'system listing', 'cmn-counts.csv': 'mesh counter file',
         'all.txt': 'combined output of all commands'}


def _code(s):
    return '<code>%s</code>' % s


def _abs(rel):
    return os.path.join(ROOT, rel)


def _nlines(rel):
    with open(_abs(rel), 'rb') as f:
        return f.read().count(b'\n')


def _Boot(b):
    return 'Boot ' + b


def _lines(ls):
    """'line 4' / 'lines 14 to 27' / 'lines 30, 32, 36 to 38' for a list of line numbers."""
    ls = sorted(set(ls))
    if not ls:
        return ''
    runs, a = [], ls[0]
    for i, v in enumerate(ls):
        if i + 1 == len(ls) or ls[i + 1] != v + 1:
            runs.append('%d' % a if a == v else ('%d and %d' % (a, v) if v == a + 1 else '%d to %d' % (a, v)))
            if i + 1 < len(ls):
                a = ls[i + 1]
    if len(runs) == 1:
        return ('line ' if len(ls) == 1 else 'lines ') + runs[0]
    if len(runs) == 2 and ' ' not in runs[0] + runs[1]:
        return 'lines %s and %s' % tuple(runs)
    return 'lines ' + ', '.join(runs)


def _lines_short(ls):
    """'line 4' / 'lines 14-27, 30, 36-38': the compact form used in the cited-lines lists."""
    ls = sorted(set(ls))
    runs, a = [], ls[0]
    for i, v in enumerate(ls):
        if i + 1 == len(ls) or ls[i + 1] != v + 1:
            runs.append('%d' % a if a == v else '%d-%d' % (a, v))
            if i + 1 < len(ls):
                a = ls[i + 1]
    return ('line ' if len(ls) == 1 else 'lines ') + ', '.join(runs)


def _grep(rel, rx):
    """[(line number, match)] of the lines of a file that match the pattern."""
    out = []
    with open(_abs(rel), encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, 1):
            m = rx.search(line)
            if m:
                out.append((i, m))
    return out


# ------------------------------------------------------------------ entries built on demand

def _file_entry(D, b, name):
    rel = BOOTDIR[b] + '/' + name
    if not os.path.isfile(_abs(rel)):
        return None
    kind = _KIND.get(name, 'file')
    t = '%s, %s %s.' % (_Boot(b), kind, _code(rel))
    if name == 'log.txt':
        reg = _grep(rel, re.compile(r'clusterpwrstat[^:]*:\s*(0x[0-9a-fA-F]+)'))
        if reg:
            vals = sorted(set(m.group(1) for _, m in reg))
            t += (' %s: the L3 status register of the cluster of CPU 2 (%s), value %s.' % (
                _lines([i for i, _ in reg]).capitalize(), _code('IMP_CLUSTERPWRSTAT_EL1'), ' and '.join(vals)))
    return t


def _group_entry(b, pattern):
    names = sorted(n for n in os.listdir(_abs(BOOTDIR[b])) if fnmatch.fnmatchcase(n, pattern))
    if not names:
        return None
    return '%s, the %d files %s in %s.' % (_Boot(b), len(names), _code(pattern), _code(BOOTDIR[b] + '/'))


def _run_entry(b, name):
    rel = RUN[b] + '/' + name
    if not os.path.isfile(_abs(rel)):
        return None
    if name == 'dmesg.txt':
        t = '%s, Linux boot log %s.' % (_Boot(b), _code(rel))
        maps = _grep(rel, re.compile(r'membench_ocm: map .*\bcont=(\d+/\d+)'))
        if maps:
            vals = sorted(set(m.group(1) for _, m in maps))
            t += (' Lines %d to %d hold the %d OCM mapping lines. Each one reads %s.' % (
                      maps[0][0], maps[-1][0], len(maps), ' or '.join(_code('cont=' + v) for v in vals)))
        return t
    if name == 'SHA256SUMS':
        return '%s, checksum list %s (%d files).' % (_Boot(b), _code(rel), _nlines(rel))
    if name == 'README.md':
        return None
    return '%s, file %s (%d lines).' % (_Boot(b), _code(rel), _nlines(rel))


# ------------------------------------------------------------------ typed entries

def canonical(D=None):
    """{canonical key: entry text} of the READMEs, the sources and the documents.
    The line numbers are typed here, once.  Each was read in the file."""
    C = {}

    def readme(b, body):
        rel = RUN[b] + '/README.md'
        C['readme:%s' % b] = "Operator's README of %s, file %s. %s" % (BOOT_NAME[b], _code(rel), body)

    readme('F1', 'Lines 66 to 67: the L3 status register reads 0x70 before and after a command, and 0x70 means '
                 'that the L3 of the cluster of CPU 2 is fully on. Line 247: the DRAM is four emulator memory '
                 'models with every delay control at zero. Line 346: each pair of CPUs shares an L2, an L3 and one '
                 'mesh port. Line 348: the cache sizes, and the SLC is five home nodes of 1 MiB of which the '
                 'firmware locks 4 of 16 ways as OCM. Line 350: the OCM is mapped with single 4 KiB entries. '
                 'Line 354: the DRAM of this emulator image is an emulator memory, so no DRAM number is like '
                 'silicon.')
    readme('E', 'Lines 16 to 36: how the firmware turns the L3 on. Line 39: the L3 status register reads 0x70 '
                'before and after the command with the hit counters.')
    readme('B', 'Line 16: the firmware sets the disable bit of the prefetchers, bit 48 of %s, on CPUs 2 to 9. '
                'Line 27: the L3 status register reads 0x0 at every power-on of CPUs 2 to 9 (the line that a firmware hook '
                'prints) and before and after the command with the hit counters. '
                'Lines 54 to 61: every OCM mapping uses single 4 KiB entries.' % _code('IMP_CPUECTLR_EL1'))
    readme('C', 'Line 8: all 115 OCM mapping lines read %s, so every 4 KiB entry carries the contiguous hint and '
                'one translation covers 64 KiB. Line 27: the L3 status register reads 0x0 before and after the command '
                'with the hit counters, and the firmware of this boot has no hook that prints the register at '
                'power-on.' % _code('cont=64/64'))
    readme('D', 'Line 8: all 115 OCM mapping lines read %s. Lines 11 and 22: the L3 status register reads 0x0 at '
                'every power-on of CPUs 2 to 9 (line 22 is the line that the firmware hook prints for CPU 8). Line 19: the firmware sets the disable bit of the '
                'prefetchers. Line 32: the L3 status register reads 0x0.' % _code('cont=64/64'))
    readme('R3', 'Line 3: the benchmark commit and the date of the run. Line 34: the cache sizes, the SLC is five '
                 'home nodes of 1 MiB in 16 ways, the firmware locks 4 ways of each as OCM, and 3.75 MiB est. of '
                 'the SLC is left for DRAM lines. Line 36: the mesh is a 6 by 6 grid of crosspoints, the home '
                 'nodes of OCM regions 0 to 4 (node ids 88, 160, 216, 288, 344) are at (1,3), (2,4), (3,3), (4,4) '
                 'and (5,3), and the mesh ports of the clusters of CPUs 2 to 3, 4 to 5, 6 to 7 and 8 to 9 are at '
                 '(2,3), (3,2), (4,3) and (5,2). Line 37: the OCM is five regions of 256 KiB, each in another '
                 'home node, and the Linux driver maps a region in 4 KiB pages.')
    f2 = RUN_F2 + '/results/bootF2'
    C['folder:F2'] = ('Results folder %s (L3 on, prefetchers off): its files other than the CME files are %s. It '
                      'holds no core row.' % (_code(RUN_F2), ', '.join(
                          _code(x) for x in sorted(n for n in os.listdir(_abs(f2)) if not n.startswith('cme-')))))

    def src(name, body):
        C['src:%s' % name] = 'Benchmark source, file %s (%d lines). %s' % (
            _code(name), _nlines(name), body)

    src('latency.c',
        'Line 40: the option %s gives a chain in address order. Lines 105 to 137: how a chain is built (one random '
        'cycle through all member lines, or the lines in address order). Lines 201 to 222: one timed rep (function '
        '%s): the flush, the counter start, the two clock reads around the walk, the counter stop and the print of '
        'the row. Lines 224 to 260: the chains of one footprint, the untimed walks, the timed reps and the best row '
        '(line 253: a chain with every line flushed first is walked once, any other chain until the load count of '
        'the command is reached. Lines 240 to 259: the best row is the smallest rep). Lines 320 to 337: the clock-read '
        'cost (two clock reads with no load between them). Lines 412 to 414: the header comment of each command.' % (
            _code('--seq'), _code('timed_walk')))
    src('bandwidth.c',
        'Line 11: the read, write and copy kernels use LDP and STP of pairs of 16-byte registers. Lines 138 to 141: '
        'the read loop (8 LDP instructions, 256 bytes per iteration). Lines 155 to 160: the read loop with one '
        'prefetch hint per line. Lines 174 to 177: the read loop over two streams. Lines 188 to 191: the write loop '
        '(8 STP instructions). Lines 240 to 247: the copy loop. Lines 314 to 342: one pass of the looped form, one '
        'kernel call per pass (line 341: a copy counts the bytes read plus the bytes written). Lines 346 to 357: '
        'the single-call form, all passes of a rep in one kernel call. Lines 398 to 449: the worker thread and how '
        'a rep is timed. Lines 573 to 616: the best row is the largest rep.')
    src('common.h',
        'Lines 100 to 104 and 110 to 114: a DRAM buffer is an anonymous mapping. Lines 132 to 139 and 149 to 161: '
        'an OCM buffer maps the fixed regions of the device. Line 253: every counter counts in user mode only. Lines 327 to 339: the default counter set and its '
        'event numbers (0x03 L1 refills, 0x17 L2 refills, 0xA2 L3 read refills, 0x81BC L1 prefetch refills, 0x81BD '
        'L2 prefetch refills, 0x0111 L2 refills by the L1 prefetcher). Lines 346 to 348: the translation set '
        '(0x05 L1 TLB refills in place of a prefetch event). Lines 383 to 385: the hit set (events 0x81C5, 0xA0 '
        'and 0x81C6 in place of the three prefetch events).')
    # The line numbers above are typed.  Stop the build when common.h moves under them.
    _ch = open(_abs('common.h'), encoding='utf-8').read().split('\n')
    for _ln, _must in ((114, 'MAP_ANONYMOUS'), (132, 'map_dev('), (139, 'MAP_SHARED'), (150, 'ocm_base + n * ocm_stride'), (161, 'memcfg.ocm_base'), (253, 'exclude_kernel = 1'), (327, 'void perf_open('), (339, '0x81BC, 0x81BD, 0x0111'),
                       (346, 'void perf_open_tlb('), (348, '0x05'), (383, 'void perf_open_l3('),
                       (385, '0x81C5, 0xA0, 0x81C6')):
        if _must not in _ch[_ln - 1]:
            raise ValueError('refs: common.h line %d does not hold %r: update the typed line numbers' % (_ln, _must))
    src('cmncount.c', 'Lines 1 to 40: the wrapper that counts mesh events over the whole life of one command.')
    C['src:lib_run.sh'] = ('Benchmark script %s (%d lines). Line 39: the node ids of the home nodes of OCM regions '
                           '0 to 4 (%s).' % (_code('lib_run.sh'), _nlines('lib_run.sh'),
                                             _code('HNS="88,160,216,288,344"')))
    C['src:run_asimov.sh'] = ('Benchmark script %s (%d lines): the command set of the cores (latency, OCM, '
                              'multi-core bandwidth, mesh counters).' % (_code('run_asimov.sh'), _nlines('run_asimov.sh')))
    C['src:run_followup.sh'] = ('Benchmark script %s (%d lines): the follow-up command set (hit set, address-order '
                                'chain, L1 forms, read variants, per-region OCM rows under the mesh counters).' % (
                                    _code('run_followup.sh'), _nlines('run_followup.sh')))
    C['src:run_all.sh'] = ('Benchmark script %s (%d lines). Lines 20 to 24: it runs %s and then the CME script '
                           'into one results folder.' % (_code('run_all.sh'), _nlines('run_all.sh'),
                                                         _code('run_asimov.sh')))

    C['doc:plan'] = ('Run plan %s (%d lines). Line 239: time per pass = total bytes / (rate x 1e9) / passes, from '
                     'the best rep, and the column %s is not used. Line 261: the fits of the two L1 forms use the '
                     '2 %% residual rule. Line 271: a residual over 2 %% of the smallest pass time voids a fit.' % (
                         _code('follow-up-run-plan.md'), _nlines('follow-up-run-plan.md'), _code('elapsed_s')))
    C['doc:seqread'] = ('Project note %s (%d lines): the read of a large buffer in address order with the L3 on '
                        'and with the L3 holding no data, and how to settle the cause.' % (
                            _code('sequential-reads-L3-on-better-bandwidth.md'),
                            _nlines('sequential-reads-L3-on-better-bandwidth.md')))
    C['doc:project-readme'] = 'Project file %s (%d lines): how the benchmark programs work and what each option does.' % (
        _code('README.md'), _nlines('README.md'))
    C['doc:sog'] = (
        'Arm C1-Nano Core Software Optimization Guide, document 109590_0001_04, file %s. Table 2-13: a load of a '
        'pair of 16-byte registers (LDP, Q form) has a throughput of 1 per cycle. Table 2-14: a store of such a '
        'pair (STP, Q form) has a throughput of 1/2 per cycle. Section 3.1: at most two loads and one store per '
        'cycle, and a store of more than 128 bits takes several cycles. Table 3-2: an L1 hit costs 2 to 4 cycles '
        'and an L2 hit 10 to 12 cycles. Table 2-6: the prefetch hint (PRFM) is listed with the load instructions. Section 3.12: the two cores of a cluster share the vector unit.' %
        _code('refs/arm-c1-nano-r0p1-sog-109590_0001_04.pdf'))
    return C


# ------------------------------------------------------------------ section key -> canonical keys

ALIAS = {
    'sog': ['doc:sog'], 'doc:sog-nano': ['doc:sog'], 'sog-109590': ['doc:sog'],
    'plan': ['doc:plan'], 'plan-fit-rule': ['doc:plan'], 'seqread': ['doc:seqread'],
    'project-readme': ['doc:project-readme'],
    'src:lib_run': ['src:lib_run.sh'], 'src:run_asimov': ['src:run_asimov.sh'],
    'src:run_followup': ['src:run_followup.sh'], 'src:run_all': ['src:run_all.sh'],
    'src:latency': ['src:latency.c'], 'src:bandwidth': ['src:bandwidth.c'], 'src:common': ['src:common.h'],
    'src:cmncount': ['src:cmncount.c'],
    'folder-012-core-files': ['folder:F2'],
}
for _b in BOOTS:
    ALIAS['readme-%s' % _b.lower()] = ['readme:%s' % _b]
    ALIAS['dmesg:%s' % _b] = ['run:%s:dmesg.txt' % _b]
    ALIAS['sha:%s' % _b] = ['run:%s:SHA256SUMS' % _b]
    ALIAS['log:%s' % _b] = ['file:%s:log.txt' % _b]
    ALIAS['sysinfo:%s' % _b] = ['file:%s:sysinfo.txt' % _b]
    ALIAS['cmn:%s' % _b] = ['file:%s:cmn-counts.csv' % _b]

_BOOT_RX = '(%s)' % '|'.join(BOOTS)
_RX_LINES = re.compile(r'^(.*?):(\d+(?:\s*(?:-|to)\s*\d+)?(?:\s*,\s*\d+(?:\s*(?:-|to)\s*\d+)?)*)$')
_RX_SLASH = re.compile(r'^%s/([^/:]+)$' % _BOOT_RX, re.I)
_RX_CSV = re.compile(r'^csv:([^:]+)$')
_RX_CANON = re.compile(r'^(file|group|run|readme):%s(?::([^:]+))?$' % _BOOT_RX, re.I)


def _parse_lines(text):
    out = []
    for part in text.split(','):
        m = re.match(r'^\s*(\d+)(?:\s*(?:-|to)\s*(\d+))?\s*$', part)
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if b < a or b - a > 5000:
            raise ValueError('reference key: bad line range %r' % part)
        out += list(range(a, b + 1))
    return out


def _canon_boot(b):
    for x in BOOTS:
        if x.lower() == b.lower():
            return x
    return b


def resolve(key):
    """(canonical keys, cited lines or None) of a section key.
    None: the key is not known here and stays as the section wrote it."""
    lines = None
    m = _RX_LINES.match(key)
    if m:
        key, lines = m.group(1), _parse_lines(m.group(2))
    if key in ALIAS:
        return list(ALIAS[key]), lines
    m = _RX_CANON.match(key)
    if m:
        kind, b, name = m.group(1).lower(), _canon_boot(m.group(2)), m.group(3)
        if kind == 'readme':
            return ['readme:%s' % b], lines
        if name:
            if kind == 'run' and name == 'README.md':
                return ['readme:%s' % b], lines
            return ['%s:%s:%s' % (kind, b, name)], lines
    m = _RX_SLASH.match(key)
    if m:
        return ['file:%s:%s' % (_canon_boot(m.group(1)), m.group(2))], lines
    m = _RX_CSV.match(key)
    if m:
        return ['file:F1:%s' % m.group(1)], lines
    if key.startswith('src:') or key.startswith('doc:'):
        return [key], lines
    return None


def install(S, D=None):
    """Give the page object the canonical entries and the key rule.  Call before any section.
    D is used only for D.log_lines(boot, file), when the data layer has it."""
    canon = canonical(D)
    cited = {}        # canonical key -> [(lines, text)]

    def text_of(ckey):
        if ckey in canon:
            return canon[ckey]
        m = re.match(r'^(file|group|run):%s:(.+)$' % _BOOT_RX, ckey)
        t = None
        if m:
            kind, b, name = m.groups()
            t = (_file_entry(D, b, name) if kind == 'file' else
                 _group_entry(b, name) if kind == 'group' else _run_entry(b, name))
        if t is None:
            return None
        canon[ckey] = t
        return t

    def res(key, text=None):
        r = resolve(key)
        if r is None:
            return None
        ckeys, lines = r
        for k in ckeys:
            if text_of(k) is None:
                raise ValueError('reference key %r: no such file or document (%s)' % (key, k))
        if lines:
            for k in ckeys:
                item = (tuple(lines), text or '')
                if item not in cited.setdefault(k, []):
                    cited[k].append(item)
        return ckeys

    def final(ckey, text):
        """The entry text with its cited lines.  A result file lists the line numbers only (the
        sentence that carries the mark says what the rows are).  A README, a source or a document
        keeps the text given with each key, since its lines hold statements."""
        items = cited.get(ckey)
        if not items:
            return text
        if ckey.split(':')[0] in ('file', 'group', 'run'):
            return '%s Cited: %s.' % (text, _lines_short(sorted(set(n for l, t in items for n in l))))
        named = set()        # the lines that the entry text itself describes
        for m in re.finditer(r'[Ll]ines? (\d+)(?: to (\d+))?', text):
            named.update(range(int(m.group(1)), int(m.group(2) or m.group(1)) + 1))
        items = [(l, t) for l, t in items if not set(l) <= named]
        if not items:
            return text
        by_lines = {}
        for l, t in sorted(items):
            t = t.rstrip('. ')
            if t and t not in by_lines.setdefault(l, []):
                by_lines[l].append(t)
            by_lines.setdefault(l, [])
        bare = sorted(set(n for l, ts in by_lines.items() if not ts for n in l))
        parts = ['%s (%s)' % (_lines_short(l), ts[0]) for l, ts in sorted(by_lines.items()) if ts]
        if bare:
            parts.append(_lines_short(bare))
        return '%s Cited: %s.' % (text, ', '.join(parts))

    S.ref_resolve = res
    S.ref_text = text_of
    S.ref_final = final
