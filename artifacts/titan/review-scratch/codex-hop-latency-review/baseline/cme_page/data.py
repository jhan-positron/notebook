"""Data layer of the page "Asimov CME Memory Performance".

Reads the raw result files of boot F1 (results/membench-jibin-011) and boot F2
(results/membench-jibin-012) and exposes them through load(), which returns
one object D. D offers generic row access and named derived tables.
Every table is documented in cme_page/API.md.

Standard library only. Run the self-test from the project folder:
    python3 -m cme_page.data
"""
import functools
import hashlib
import math
import os
import re
import statistics

PKG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG)
RUN = {'F1': os.path.join(ROOT, 'results', 'membench-jibin-011'),
       'F2': os.path.join(ROOT, 'results', 'membench-jibin-012')}
BOOTDIR = {'F1': os.path.join(RUN['F1'], 'results', 'bootF1'),
           'F2': os.path.join(RUN['F2'], 'results', 'bootF2')}
BOOTS = ('F1', 'F2')
BOOT_NAME = {'F1': 'boot F1 (prefetchers on)', 'F2': 'boot F2 (prefetchers off)'}
# The one earlier-boot row the page may cite (SPEC hard rule 2): the address-order chain.
ADDRESS_ORDER_FILE = os.path.join(ROOT, 'results', 'membench-jibin-010', 'results', 'bootE',
                                  'cme-latency-dram-seq.csv')
KIB = 1024
MIB = 1024 * 1024
LINE = 64                      # bytes per cache line
CLOCK_MIN_LOADS = 8192         # a latency row needs this many loads to enter the clock ratio
REGION_BYTES = 256 * KIB       # one OCM region
REGION_LINES = REGION_BYTES // LINE
# OCM region number -> mesh home node id. Typed fact: lib_run.sh line 39 (HNS="88,160,216,288,344").
# load() checks it against the mesh counters (D.mesh_summary['region_nodes_from_counts']).
REGION_NODE = (88, 160, 216, 288, 344)
DSU1_XY = (2, 3)               # hypothesis: the cluster port of CPUs 2-3 (see D.mesh_rnf_steps)

# CSV column name -> short key used in every rep row and derived row.
SHORT = {
    'ns_per_load': 'ns', 'ns_per_load_span': 'span', 'cycles_per_load': 'cycles',
    'cme_cycles_per_load': 'cme_cycles',
    'cme_l1d_refill_inner_per_load': 'inner', 'cme_l1d_refill_outer_per_load': 'outer',
    'cme_l1d_refill_rd_per_load': 'rd', 'cme_l1d_refill_hwprf_per_load': 'hwprf',
    'cme_l1d_refill_wr_per_load': 'wr',
    'cme_l3d_hit_per_load': 'hit', 'cme_l3d_miss_per_load': 'miss',
    'cme_l3d_refill_per_load': 'refill',
    'l1d_refill_per_load': 'l1d', 'l2d_refill_per_load': 'l2d', 'l3d_refill_rd_per_load': 'l3d_rd',
    'l1d_refill_hwprf_per_load': 'l1d_hwprf', 'l2d_refill_hwprf_per_load': 'l2d_hwprf',
    'l2d_refill_l1dhwprf_per_load': 'l2d_l1dhwprf', 'perf_cov': 'perf_cov',
}
CME_COUNTERS = ('inner', 'outer', 'rd', 'hwprf', 'wr')
L3_COUNTERS = ('inner', 'outer', 'hit', 'miss', 'refill')
CORE_COUNTERS = ('l1d', 'l2d', 'l3d_rd', 'l1d_hwprf', 'l2d_hwprf', 'l2d_l1dhwprf')
KERNEL_SHORT = {'cme-read': 'read', 'cme-write': 'write', 'cme-copy': 'copy',
                'cme-ldr16': 'read64', 'cme-str16': 'write64',
                'read': 'read', 'write': 'write', 'copy': 'copy', 'ldr16': 'ldr16', 'str16': 'str16'}
BW_GROUP = {
    'cme-bandwidth-dram-1core.csv': 'sweep',
    'cme-bandwidth-dram-1core-asmpasses.csv': 'sweep-single',
    'cme-bandwidth-l1-passes.csv': 'l1-looped',
    'cme-bandwidth-l1-asmpasses.csv': 'l1-single',
    'cme-bandwidth-l1-nofold.csv': 'l1-nofold',
    'cme-bandwidth-l1-dsb.csv': 'l1-dsb',
    'cme-bandwidth-call-cost.csv': 'call-cost',
}
OCM_NAMES = ('region0', 'region1', 'region2', 'region3', 'region4', 'all5', 'all5-dense')


# ----------------------------------------------------------------------------- small helpers

def _lines(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read().split('\n')


def _val(s):
    """Text field -> int, float, None for '-', or the text itself."""
    if s == '-' or s == '':
        return None
    if re.fullmatch(r'-?\d+', s):
        return int(s)
    try:
        return float(s)
    except ValueError:
        return s


def _kv(text):
    """'a=1 b=x' -> {'a': 1, 'b': 'x'} (tokens without '=' are skipped)."""
    out = {}
    for tok in text.split():
        if '=' in tok:
            k, v = tok.split('=', 1)
            out[k] = _val(v)
    return out


def _spread_pct(vals):
    """(max - min) / min in percent."""
    lo = min(vals)
    return 100.0 * (max(vals) - lo) / lo if lo else 0.0


def _rng(vals):
    vals = list(vals)
    return (min(vals), max(vals))


def fmt_size(nbytes):
    """Footprint label: 4096 -> '4 KiB', 1572864 -> '1.5 MiB'."""
    if nbytes >= MIB:
        v = nbytes / MIB
        unit = 'MiB'
    else:
        v = nbytes / KIB
        unit = 'KiB'
    return ('%d %s' % (v, unit)) if v == int(v) else ('%g %s' % (v, unit))


# ----------------------------------------------------------------------------- linear algebra

def linfit(xs, ys):
    """Least-squares line y = a + s*x. Returns (a, s, residuals)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    s = sxy / sxx
    a = my - s * mx
    return a, s, [y - (a + s * x) for x, y in zip(xs, ys)]


def pearson(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def _gram(A):
    m = len(A[0])
    return [[sum(r[i] * r[j] for r in A) for j in range(m)] for i in range(m)]


def _solve(M, b):
    """Gaussian elimination with partial pivoting. Returns None when singular."""
    n = len(b)
    a = [row[:] + [b[i]] for i, row in enumerate(M)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        if abs(a[p][c]) < 1e-12:
            return None
        a[c], a[p] = a[p], a[c]
        for r in range(c + 1, n):
            f = a[r][c] / a[c][c]
            for k in range(c, n + 1):
                a[r][k] -= f * a[c][k]
    x = [0.0] * n
    for c in range(n - 1, -1, -1):
        x[c] = (a[c][n] - sum(a[c][k] * x[k] for k in range(c + 1, n))) / a[c][c]
    return x


def _sym_eigvals(M):
    """Eigenvalues of a small symmetric matrix (cyclic Jacobi rotations)."""
    n = len(M)
    a = [row[:] for row in M]
    for _ in range(100):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < 1e-30:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
    return sorted(a[i][i] for i in range(n))


def cond_number(A):
    """Largest / smallest singular value of the matrix A (list of rows)."""
    ev = _sym_eigvals(_gram(A))
    if ev[0] <= 0:
        return float('inf')
    return math.sqrt(ev[-1] / ev[0])


def lstsq(A, y):
    """Least squares by the normal equations.
    Returns dict(coef, res, rms, max_res, cond_raw, cond_unit) or None when singular."""
    G = _gram(A)
    m = len(A[0])
    rhs = [sum(r[i] * yy for r, yy in zip(A, y)) for i in range(m)]
    coef = _solve(G, rhs)
    if coef is None:
        return None
    res = [yy - sum(c * v for c, v in zip(coef, r)) for r, yy in zip(A, y)]
    norms = [math.sqrt(G[i][i]) for i in range(m)]
    unit = [[v / norms[i] for i, v in enumerate(r)] for r in A]
    return {'coef': coef, 'res': res,
            'rms': math.sqrt(sum(e * e for e in res) / len(res)),
            'max_res': max(abs(e) for e in res),
            'cond_raw': cond_number(A), 'cond_unit': cond_number(unit)}


# ----------------------------------------------------------------------------- parsers

def parse_latency(path, boot):
    """One latency CSV -> list of blocks (one block per command)."""
    src = os.path.basename(path)
    blocks = []
    blk = None
    cur = None
    for n, line in enumerate(_lines(path), 1):
        if not line:
            continue
        if line.startswith('# latency:'):
            blk = {'boot': boot, 'src': src, 'path': path, 'index': len(blocks), 'line': n,
                   'header': _kv(line.split(';', 1)[1]), 'header_text': line, 'columns': [],
                   'bracket_overhead_ns': None, 'sizes': {}, 'order': [], 'rt': None, 'call': None,
                   'raw': [], 'perf_lines': 0}
            blocks.append(blk)
            cur = None
            blk['raw'].append(line)
            continue
        if blk is None:
            continue
        blk['raw'].append(line)
        if line.startswith('# bracket_overhead_ns='):
            blk['bracket_overhead_ns'] = float(line.split('=', 1)[1].split()[0])
            blk['bracket_overhead_line'] = n
        elif line.startswith('# size='):
            kv = _kv(line[2:])
            cur = {'size': kv['size'], 'lines': kv['lines'], 'backing': kv['backing'],
                   'segments': kv['segments'], 'sparse': kv['sparse'], 'line': n,
                   'reps': [], 'best': None, 'best_line': None}
            blk['sizes'][kv['size']] = cur
            blk['order'].append(kv['size'])
        elif line.startswith('# perf:'):
            blk['perf_lines'] += 1
        elif line.startswith('#'):
            continue
        elif line.startswith('mem,'):
            blk['columns'] = line.split(',')
        else:
            f = line.split(',')
            mode = f[2]
            if mode.endswith('best'):
                tgt = cur
                if mode in ('cme-roundtrip-best',):
                    tgt = blk['rt']
                elif mode in ('cme-call-best',):
                    tgt = blk['call']
                tgt['best'] = float(f[5])
                tgt['best_line'] = n
                continue
            row = {'mem': f[0], 'size': int(f[1]), 'mode': mode, 'line': n}
            for name, text in zip(blk['columns'][3:], f[3:]):
                row[SHORT.get(name, name)] = _val(text)
            if mode == 'cme-roundtrip':
                if blk['rt'] is None:
                    blk['rt'] = {'size': 0, 'reps': [], 'best': None, 'best_line': None}
                blk['rt']['reps'].append(row)
            elif mode == 'cme-call':
                if blk['call'] is None:
                    blk['call'] = {'size': 0, 'reps': [], 'best': None, 'best_line': None}
                blk['call']['reps'].append(row)
            else:
                cur['reps'].append(row)
    return blocks


def best_rep(entry):
    """The first rep whose bracket ns equals the program's -best row."""
    for r in entry['reps']:
        if r['ns'] == entry['best']:
            return r
    raise ValueError('no rep equals the best row')


def parse_bandwidth(path, boot):
    """One bandwidth CSV -> list of rows, one per command and kernel."""
    src = os.path.basename(path)
    rows = []
    hdr = None
    block = -1
    bykernel = {}
    for n, line in enumerate(_lines(path), 1):
        if not line:
            continue
        if line.startswith('# bandwidth:'):
            hdr = {'kv': _kv(line.split(';', 1)[1]), 'line': n, 'backing': None, 'raw': [line],
                   'text': line}
            block += 1
            bykernel = {}
            continue
        if hdr is None:
            continue
        hdr['raw'].append(line)
        if line.startswith('# backing='):
            hdr['backing'] = line.split('=', 1)[1].strip()
        elif line.startswith('#') or line.startswith('mem,'):
            if line.startswith('mem,'):
                hdr['columns'] = line.split(',')
            continue
        else:
            f = line.split(',')
            k = f[1]
            if k not in bykernel:
                kv = hdr['kv']
                bykernel[k] = {
                    'boot': boot, 'src': src, 'path': path, 'block': block, 'line': hdr['line'],
                    'header': kv, 'header_text': hdr['text'], 'raw': hdr['raw'],
                    'backing': hdr['backing'], 'mem': f[0],
                    'kernel_csv': k, 'kernel': KERNEL_SHORT.get(k, k), 'threads': int(f[2]),
                    'size': int(f[3]), 'passes': kv['passes'], 'cme': kv.get('cme', 0),
                    'asm_passes': kv.get('asm_passes', 0), 'dsb_st': kv.get('dsb_st', 0),
                    'no_fold': kv.get('no_fold', 0), 'flush_before': kv.get('flush_before', 0),
                    'reps': [], 'best': None, 'best_span': None}
                rows.append(bykernel[k])
            r = bykernel[k]
            has_span = len(f) > 10
            if f[4] == 'best':
                r['best'] = float(f[7])
                r['best_span'] = float(f[11]) if has_span else None
                r['best_line'] = n
            else:
                r['reps'].append({'rep': int(f[4]), 'total_bytes': int(f[5]),
                                  'elapsed_s': float(f[6]), 'gbps': float(f[7]),
                                  'span_s': float(f[10]) if has_span else None,
                                  'span_gbps': float(f[11]) if has_span else None, 'line': n})
    for r in rows:
        _enrich_bw(r)
    return rows


def _enrich_bw(r):
    """Add the derived times of one bandwidth row (see API.md, 'bandwidth row')."""
    if r['asm_passes']:
        r['form'] = 'single-call'
    elif r['no_fold']:
        r['form'] = 'looped, no fold'
    elif r['dsb_st']:
        r['form'] = 'looped, DSB ST'
    else:
        r['form'] = 'looped'
    r['group'] = BW_GROUP.get(r['src'], 'ocm' if r['mem'] == 'ocm' else 'core')
    r['segments'] = r['size'] // REGION_BYTES if r['mem'] == 'ocm' else 1
    r['calls_per_pass'] = r['segments']
    r['calls_per_rep'] = 1 if r['asm_passes'] else r['passes'] * r['segments']
    tb = r['reps'][0]['total_bytes']
    r['bytes_per_pass'] = tb / r['passes']
    r['n_reps'] = len(r['reps'])
    r['reps_gbps'] = [x['gbps'] for x in r['reps']]
    r['spread_pct'] = _spread_pct(r['reps_gbps'])
    r['ns_per_pass'] = r['bytes_per_pass'] / r['best']          # GB/s = bytes per ns
    r['ns_per_line'] = LINE / r['best']
    for x in r['reps']:
        x['bracket_ns'] = x['total_bytes'] / x['gbps']
        x['bracket_ns_per_pass'] = x['bracket_ns'] / r['passes']
    r['best_rep'] = next(x for x in r['reps'] if x['gbps'] == r['best'])
    r['best_rep_index'] = r['best_rep']['rep']
    r['best_bracket_ns'] = r['best_rep']['bracket_ns']
    if r['best_span'] is None:
        return
    r['reps_span_gbps'] = [x['span_gbps'] for x in r['reps']]
    r['spread_span_pct'] = _spread_pct(r['reps_span_gbps'])
    r['ns_per_pass_span'] = r['bytes_per_pass'] / r['best_span']
    for x in r['reps']:
        x['span_ns'] = x['span_s'] * 1e9
        x['span_ns_per_pass'] = x['span_ns'] / r['passes']
        x['outside_ns'] = x['bracket_ns'] - x['span_ns']
        x['outside_ns_per_pass'] = x['outside_ns'] / r['passes']
        x['outside_ns_per_call'] = x['outside_ns'] / r['calls_per_rep']
    r['outside_ns_per_call'] = r['best_rep']['outside_ns_per_call']
    r['outside_ns_per_pass'] = r['best_rep']['outside_ns_per_pass']
    r['outside_reps'] = [x['outside_ns_per_call'] for x in r['reps']]
    r['outside_lo'], r['outside_hi'] = _rng(r['outside_reps'])
    r['outside_pass_lo'], r['outside_pass_hi'] = _rng(x['outside_ns_per_pass'] for x in r['reps'])


def parse_cmn(path, boot):
    rows = []
    for n, line in enumerate(_lines(path), 1):
        f = line.split(',')
        if len(f) != 7 or f[0] == 'label' or line.startswith('#'):
            continue
        rows.append({'boot': boot, 'src': os.path.basename(path), 'line': n, 'label': f[0],
                     'event': f[1], 'node': _val(f[2]), 'count': int(f[3]),
                     'enabled_ns': int(f[4]), 'running_ns': int(f[5]), 'scaled_count': int(f[6])})
    return rows


_CMD = re.compile(r'^\+ (?:(cmn0?) (\S+) )?(\S*/)?(latency|bandwidth)\b(.*?)(?: \[uptime ([\d.]+)\])?\s*$')


def parse_log(path, boot):
    """log.txt -> dict(commands, notes, done)."""
    cmds, notes, done = [], [], []
    for n, line in enumerate(_lines(path), 1):
        if line.startswith('+ '):
            m = _CMD.match(line)
            text = re.sub(r'\s*\[uptime [\d.]+\]\s*$', '', line[2:])
            c = {'boot': boot, 'src': 'log.txt', 'line': n, 'text': text, 'raw': line,
                 'uptime': None, 'wrapper': None, 'label': None, 'program': None, 'args': '',
                 'cme': '--cme' in line}
            if m:
                c.update(wrapper=m.group(1), label=m.group(2), program=m.group(4),
                         args=m.group(5).strip(),
                         uptime=float(m.group(6)) if m.group(6) else None)
            cmds.append(c)
        elif line.strip():
            notes.append({'line': n, 'text': line})
            m = re.match(r'# (\S+) done .*: (\d+) measurement command\(s\) failed', line)
            if m:
                done.append({'line': n, 'script': m.group(1), 'failed': int(m.group(2)),
                             'text': line})
    return {'commands': cmds, 'notes': notes, 'done': done}


def parse_alltxt(path):
    """all.txt -> list of (command text, output lines)."""
    out = []
    cur = None
    for line in _lines(path):
        if line.startswith('## '):
            cur = [line[3:].strip(), []]
            out.append(cur)
        elif cur is not None and line:
            cur[1].append(line)
    return out


def verify_sha256(run_dir):
    """Check every entry of <run_dir>/SHA256SUMS with hashlib.
    Returns dict(ok, total, bad=[names], entries=[(name, ok)], src)."""
    entries = []
    bad = []
    for line in _lines(os.path.join(run_dir, 'SHA256SUMS')):
        m = re.match(r'^([0-9a-f]{64})\s+\*?(.+)$', line.strip())
        if not m:
            continue
        want, name = m.group(1), m.group(2)
        p = os.path.join(run_dir, name)
        ok = False
        if os.path.isfile(p):
            h = hashlib.sha256()
            with open(p, 'rb') as f:
                for chunk in iter(lambda: f.read(1 << 20), b''):
                    h.update(chunk)
            ok = h.hexdigest() == want
        entries.append((name, ok))
        if not ok:
            bad.append(name)
    return {'ok': sum(1 for _, o in entries if o), 'total': len(entries), 'bad': bad,
            'entries': entries, 'src': 'SHA256SUMS'}


def parse_mesh_map(lines, first_line=1):
    """The arm-cmn mesh map of sysinfo.txt -> list of device cells.
    Each cell: dict(x, y, xp, port, type, index, line). `lines` are the map lines."""
    cells = []
    y = None
    xps = []
    pending = None
    for off, line in enumerate(lines):
        n = first_line + off
        m = re.match(r'^(\d)\s+\|(.*XP #.*)\|\s*$', line)
        if m:
            y = int(m.group(1))
            xps = [int(re.search(r'#(\d+)', c).group(1)) for c in m.group(2).split('|')]
            continue
        m = re.match(r'^  ([01])  \|(.*)\|\s*$', line)
        if m and y is not None:
            pending = (int(m.group(1)), [c.strip() for c in m.group(2).split('|')], n)
            continue
        m = re.match(r'^    0\|(.*)\|\s*$', line)
        if m and pending is not None:
            port, types, tl = pending
            idx = [c.strip() for c in m.group(1).split('|')]
            for x, t in enumerate(types):
                if t:
                    i = idx[x].lstrip('#') if x < len(idx) else ''
                    cells.append({'x': x, 'y': y, 'xp': xps[x], 'port': port, 'type': t,
                                  'index': int(i) if i.isdigit() else None, 'line': tl})
            pending = None
    return cells


def _find_lines(lines, pattern):
    rx = re.compile(pattern)
    return [(n, l) for n, l in enumerate(lines, 1) if rx.search(l)]


# ----------------------------------------------------------------------------- the data object

class Data:
    """Everything the page needs. Build it with load()."""

    def __init__(self):
        self.root = ROOT
        self.boots = BOOTS
        self.boot_name = dict(BOOT_NAME)
        self.run_dir = dict(RUN)
        self.boot_dir = dict(BOOTDIR)
        self._lat = {b: {} for b in BOOTS}
        self._bw = {b: {} for b in BOOTS}
        self._cmn = {}
        self.log = {}
        self._read_files()
        self._build_platform()
        self._build_commands()
        self._build_integrity()
        self._build_baseline()
        self._build_clock()
        self._build_chain()
        self._build_l3()
        self._build_bw()
        self._build_ocm()
        self._build_mesh()
        self._build_cross()

    # ------------------------------------------------------------------ reading
    def _read_files(self):
        for b in BOOTS:
            d = BOOTDIR[b]
            for name in sorted(os.listdir(d)):
                p = os.path.join(d, name)
                if not name.endswith('.csv'):
                    continue
                core_lat = b == 'F1' and (name in ('latency-control-cpu2.csv', 'latency-dram-small.csv',
                                                   'latency-dram-large.csv', 'latency-dram-flushed.csv')
                                          or re.fullmatch(r'latency-ocm-.*-cpu2\.csv', name))
                core_bw = b == 'F1' and (name == 'bandwidth-dram-1core.csv'
                                         or re.fullmatch(r'bandwidth-ocm-(region\d|all5|write)\.csv', name))
                if name.startswith('cme-latency-') or core_lat:
                    self._lat[b][name] = parse_latency(p, b)
                elif name.startswith('cme-bandwidth-') or core_bw:
                    self._bw[b][name] = parse_bandwidth(p, b)
                elif name == 'cmn-counts.csv':
                    self._cmn[b] = parse_cmn(p, b)
            self.log[b] = parse_log(os.path.join(d, 'log.txt'), b)
        self.files = {b: {'latency': sorted(self._lat[b]), 'bandwidth': sorted(self._bw[b])}
                      for b in BOOTS}

    # ------------------------------------------------------------------ generic access
    def latblocks(self, boot, file):
        """All command blocks of one latency file (see API.md, 'latency block')."""
        return self._lat[boot][file]

    def lat(self, boot, file, size, block=0):
        """One footprint entry of a latency file: dict(size, lines, backing, segments, sparse,
        reps=[rep rows], best, line). size=0 returns dict(rt=..., call=...)."""
        blk = self._lat[boot][file][block]
        if size == 0:
            return {'rt': blk['rt'], 'call': blk['call']}
        return blk['sizes'][size]

    def latrow(self, boot, file, size, block=0):
        """The derived row (best bracket, span and counters of the best rep) of one footprint."""
        blk = self._lat[boot][file][block]
        return self._row(blk, blk['sizes'][size])

    def bw(self, boot, file, kernel=None, size=None):
        """Bandwidth rows of one file. With kernel and size it returns the one row (or None)."""
        rows = [r for r in self._bw[boot][file]
                if (kernel is None or kernel in (r['kernel'], r['kernel_csv']))
                and (size is None or r['size'] == size)]
        if kernel is not None and size is not None:
            return rows[0] if rows else None
        return rows

    def cmn(self, boot, label=None, event=None, node=None):
        """Rows of cmn-counts.csv, filtered."""
        return [r for r in self._cmn[boot]
                if (label is None or r['label'] == label)
                and (event is None or r['event'] == event)
                and (node is None or r['node'] == node)]

    def cmn_nodes(self, boot, label):
        """{node id: requests received} of one label (event hns_pocq_reqs_recvd_all)."""
        return {r['node']: r['count'] for r in self.cmn(boot, label, 'hns_pocq_reqs_recvd_all')}

    def verify_sha(self, boot):
        return self.integrity[boot]['sha']

    # ------------------------------------------------------------------ row builder
    @staticmethod
    def _kind(h):
        if h.get('seq'):
            return 'address order'
        if h.get('flush'):
            return 'every line flushed first'
        if h.get('fresh'):
            return 'walked once'
        return 'walked many times'

    def _row(self, blk, e):
        """Derived row of one footprint entry. Keys: API.md, 'chain row'."""
        h = blk['header']
        br = best_rep(e)
        reps = e['reps']
        ns = [r['ns'] for r in reps]
        row = {'boot': blk['boot'], 'src': blk['src'], 'block': blk['index'], 'line': e['line'],
               'mem': h['mem'], 'cme': bool(h.get('cme')), 'events': h.get('events'),
               'size': e['size'], 'label': fmt_size(e['size']), 'lines': e['lines'],
               'backing': e['backing'], 'segments': e['segments'],
               'kind': self._kind(h), 'flush': bool(h.get('flush')), 'seq': bool(h.get('seq')),
               'shape': 'one line per 4 KiB page' if e['sparse'] else 'every line',
               'loads': br['loads'], 'walks_per_rep': br['loads'] / e['lines'],
               'best': e['best'], 'best_mode': br['mode'], 'best_rep': br['rep'],
               'best_rep_line': br['line'], 'n_reps': len(reps), 'reps': reps,
               'reps_ns': ns, 'spread_ns': max(ns) - min(ns), 'spread_pct': _spread_pct(ns),
               'median_ns': statistics.median(ns),
               'bracket_overhead_ns': blk['bracket_overhead_ns']}
        for k, v in br.items():
            if k not in ('mem', 'size', 'mode', 'line', 'rep', 'loads', 'ns'):
                row[k] = v
        row['cyc_per_ns'] = br['cycles'] / br['ns']
        if 'span' in br:
            sp = [r['span'] for r in reps]
            row.update(reps_span=sp, best_span=min(sp), median_span=statistics.median(sp),
                       spread_span_pct=_spread_pct(sp), bracket_minus_span=br['ns'] - br['span'],
                       outside_reps=[(r['ns'] - r['span']) * r['loads'] for r in reps])
            row['outside_lo'], row['outside_hi'] = _rng(row['outside_reps'])
        if blk['rt'] is not None:
            rt = blk['rt']
            rtb = best_rep(rt)
            row.update(rt=rt['best'], above_rt=e['best'] - rt['best'])
            if 'span' in rtb:
                row.update(rt_span=rtb['span'], span_above_rt=br['span'] - rtb['span'],
                           best_span_above_rt=row['best_span'] - rtb['span'])
        if 'inner' in br:
            row['refills'] = br['inner'] + br['outer']
            row['above_rt_per_refill'] = (row['above_rt'] / row['refills']) if row['refills'] else None
            row['refills_per_line'] = [r['inner'] * r['loads'] / e['lines'] for r in reps]
        cnt = CME_COUNTERS if 'rd' in br else (L3_COUNTERS if 'hit' in br else CORE_COUNTERS)
        row['counter_keys'] = cnt
        for k in cnt:
            vals = [r[k] for r in reps]
            row[k + '_reps'] = vals
            row[k + '_min'], row[k + '_max'] = _rng(vals)
            row[k + '_mean'] = sum(vals) / len(vals)
        if 'hwprf' in br:
            row['counter_sum_diff'] = [r['inner'] + r['outer'] - r['rd'] - r['hwprf'] - r['wr']
                                       for r in reps]
            row['demand_only'] = all(r['hwprf'] == 0 for r in reps)
        elif 'l1d_hwprf' in br:
            row['demand_only'] = all(r['l1d_hwprf'] == 0 and r['l2d_hwprf'] == 0
                                     and r['l2d_l1dhwprf'] == 0 for r in reps)
        return row

    def _rows(self, boot, file):
        out = []
        for blk in self._lat[boot][file]:
            for s in blk['order']:
                out.append(self._row(blk, blk['sizes'][s]))
        return out

    # ------------------------------------------------------------------ platform facts
    def _build_platform(self):
        P = {}

        def one(key, boot, src, lines, pattern, value=None):
            hits = _find_lines(lines, pattern)
            if not hits:
                P[key] = None
                return None
            n, text = hits[0]
            P[key] = {'boot': boot, 'src': src, 'line': n, 'text': text.strip(), 'value': None}
            if value:
                m = re.search(value, text)
                if m:
                    P[key]['value'] = _val(m.group(1))
            return P[key]

        self.dmesg_ocm_maps = {}
        for b in BOOTS:
            dl = _lines(os.path.join(RUN[b], 'dmesg.txt'))
            one('timer_' + b, b, 'dmesg.txt', dl, r'arch_timer: .* timer running at', r'at ([\d.]+)MHz')
            one('sched_clock_' + b, b, 'dmesg.txt', dl, r'sched_clock: ', r'resolution (\d+)ns')
            one('bogomips_' + b, b, 'dmesg.txt', dl, r'BogoMIPS \(lpj', r'([\d.]+) BogoMIPS')
            one('sme_vl_max_' + b, b, 'dmesg.txt', dl,
                r'SME: maximum available vector length', r'length (\d+) bytes')
            one('sme_vl_min_' + b, b, 'dmesg.txt', dl,
                r'SME: minimum available vector length', r'length (\d+) bytes')
            one('sme_vl_default_' + b, b, 'dmesg.txt', dl,
                r'SME: default vector length', r'length (\d+) bytes')
            one('sve_vl_max_' + b, b, 'dmesg.txt', dl,
                r'SVE: maximum available vector length', r'length (\d+) bytes')
            one('sme2_' + b, b, 'dmesg.txt', dl, r'CPU features: detected: SME2')
            maps = _find_lines(dl, r'membench_ocm: map ')
            self.dmesg_ocm_maps[b] = {
                'boot': b, 'src': 'dmesg.txt', 'n': len(maps),
                'first_line': maps[0][0] if maps else None,
                'last_line': maps[-1][0] if maps else None,
                'all_len_256k': all('len=0x40000' in t for _, t in maps),
                'all_single_4k': all('cont=0/64' in t and 'same=64/64' in t for _, t in maps),
                'bases': sorted({re.search(r'pa=(0x[0-9a-f]+)', t).group(1) for _, t in maps})}
        sl = _lines(os.path.join(BOOTDIR['F1'], 'sysinfo.txt'))
        caches = []
        for n, t in _find_lines(sl, r'/cache/index\d: level='):
            kv = _kv(t.split(':', 1)[1])
            caches.append({'boot': 'F1', 'src': 'sysinfo.txt', 'line': n, 'text': t.strip(),
                           'level': kv['level'], 'type': kv['type'], 'size': kv['size'],
                           'size_bytes': int(str(kv['size']).rstrip('K')) * KIB,
                           'shared_cpu_list': str(kv['shared_cpu_list'])})
        P['caches'] = caches
        one('hugepages_total', 'F1', 'sysinfo.txt', sl, r'^HugePages_Total:', r'(\d+)')
        one('hugepagesize', 'F1', 'sysinfo.txt', sl, r'^Hugepagesize:', r'(\d+) kB')
        one('cmn_events', 'F1', 'sysinfo.txt', sl, r'^type=\d+ cpumask=\d+ events=', r'events=(\d+)')
        P['ocm_iomem'] = [{'boot': 'F1', 'src': 'sysinfo.txt', 'line': n, 'text': t.strip(),
                           'base': int(t.split('-')[0], 16)}
                          for n, t in _find_lines(sl, r'^[0-9a-f]+-[0-9a-f]+ : ocm')]
        hdr = _find_lines(sl, r'^## arm-cmn mesh map')
        first = hdr[0][0] if hdr else None
        last = first
        if first:
            for n in range(first + 1, len(sl) + 1):
                if sl[n - 1].startswith('## '):
                    break
                if sl[n - 1].strip():
                    last = n
        P['mesh_map'] = {'boot': 'F1', 'src': 'sysinfo.txt', 'line': first, 'last_line': last,
                         'text': sl[first - 1].strip() if first else ''}
        self.mesh_cells = parse_mesh_map(sl[first:last], first + 1) if first else []
        self.platform = P

    # ------------------------------------------------------------------ commands, log
    def _build_commands(self):
        self.commands = {}
        self.cmd_lines = {b: {} for b in BOOTS}      # (file, block) -> log line
        for b in BOOTS:
            L = self.log[b]
            cmds = L['commands']
            cme = [c for c in cmds if c['cme']]
            notes = L['notes']
            row = {
                'boot': b, 'src': 'log.txt',
                'n_commands': len(cmds), 'n_cme': len(cme), 'n_core': len(cmds) - len(cme),
                'n_cme_latency': sum(1 for c in cme if c['program'] == 'latency'),
                'n_cme_bandwidth': sum(1 for c in cme if c['program'] == 'bandwidth'),
                'n_cmn': sum(1 for c in cmds if c['wrapper']),
                'n_cme_cmn': sum(1 for c in cme if c['wrapper'] == 'cmn'),
                'cme_first_line': cme[0]['line'], 'cme_last_line': cme[-1]['line'],
                'cme_first_uptime': cme[0]['uptime'], 'cme_last_uptime': cme[-1]['uptime'],
                'done': L['done'], 'failed': sum(d['failed'] for d in L['done']),
                'cme_done': [d for d in L['done'] if d['script'] == 'run_cme.sh'],
                'cpu3': [n for n in notes if n['text'].startswith('cpu3 online=')],
                'clusterpwrstat': [n for n in notes if 'clusterpwrstat' in n['text']],
                'l3_lines': [c['line'] for c in cme if '--events cme-l3' in c['text']],
                'cme_labels': [c['label'] for c in cme if c['label']],
                'cme_commands': cme, 'commands': cmds}
            cs = [n for n in notes if n['text'].startswith('cpu3 online=')]
            row['cpu3_offline_line'] = next((n['line'] for n in cs if n['text'].endswith('=0')
                                             and n['line'] < cme[0]['line']
                                             and n['line'] > cme[0]['line'] - 5), None)
            row['cpu3_online_line'] = next((n['line'] for n in cs if n['text'].endswith('=1')
                                            and n['line'] > cme[-1]['line']), None)
            self.commands[b] = row
            # map every CSV block to its log line through all.txt (same command order)
            allp = os.path.join(BOOTDIR[b], 'all.txt')
            if os.path.isfile(allp):
                at = parse_alltxt(allp)
                if len(at) == len(cmds):
                    index = {}
                    for i, (_, outl) in enumerate(at):
                        index.setdefault('\n'.join(outl), i)
                    for fam in (self._lat[b], self._bw[b]):
                        for name, blocks in fam.items():
                            seen = set()
                            for blk in blocks:
                                bi = blk['index'] if 'index' in blk else blk['block']
                                if bi in seen:
                                    continue
                                seen.add(bi)
                                i = index.get('\n'.join(blk['raw']))
                                if i is not None:
                                    self.cmd_lines[b][(name, bi)] = cmds[i]['line']
        f1 = [c['text'] for c in self.commands['F1']['cme_commands']]
        f2 = [c['text'] for c in self.commands['F2']['cme_commands']]
        self.commands['same_cme_commands'] = f1 == f2

    def log_lines(self, boot, file):
        """Sorted log.txt line numbers of the commands that wrote one CSV file."""
        return sorted(v for (name, _), v in self.cmd_lines[boot].items() if name == file)

    # ------------------------------------------------------------------ integrity
    def _build_integrity(self):
        self.integrity = {}
        for b in BOOTS:
            reps = 0
            cov = []
            perf_lines = 0
            dash = 0
            for name, blocks in self._lat[b].items():
                if not name.startswith('cme-'):
                    continue
                for blk in blocks:
                    perf_lines += blk['perf_lines']
                    allreps = (blk['rt']['reps'] if blk['rt'] else []) + \
                              (blk['call']['reps'] if blk['call'] else [])
                    for s in blk['order']:
                        allreps = allreps + blk['sizes'][s]['reps']
                    for r in allreps:
                        reps += 1
                        cov.append(r['perf_cov'])
                        dash += sum(1 for v in r.values() if v is None)
            bwreps = sum(len(r['reps']) for rows in self._bw[b].values() for r in rows
                         if r['src'].startswith('cme-'))
            bwbest = sum(1 for rows in self._bw[b].values() for r in rows
                         if r['src'].startswith('cme-'))
            cm = self._cmn[b]
            self.integrity[b] = {
                'boot': b, 'sha': verify_sha256(RUN[b]),
                'n_cme_latency_files': sum(1 for n in self._lat[b] if n.startswith('cme-')),
                'n_cme_bandwidth_files': sum(1 for n in self._bw[b] if n.startswith('cme-')),
                'latency_rep_rows': reps, 'perf_cov_min': min(cov), 'perf_cov_max': max(cov),
                'perf_lines': perf_lines, 'missing_counter_fields': dash,
                'bandwidth_rep_rows': bwreps, 'bandwidth_best_rows': bwbest,
                'bandwidth_reps_with_span': sum(1 for rows in self._bw[b].values() for r in rows
                                                if r['src'].startswith('cme-')
                                                for x in r['reps'] if x['span_s'] is not None),
                'cmn_rows': len(cm), 'cmn_labels': len({r['label'] for r in cm}),
                'cmn_cme_labels': len({r['label'] for r in cm if r['label'].startswith('cme-')}),
                'cmn_multiplexed_rows': sum(1 for r in cm if r['running_ns'] != r['enabled_ns']
                                            or r['scaled_count'] != r['count']),
                'cntfrq_hz': sorted({blk['header'].get('cntfrq_hz')
                                     for n, bl in self._lat[b].items() if n.startswith('cme-')
                                     for blk in bl} |
                                    {r['header'].get('cntfrq_hz')
                                     for n, rows in self._bw[b].items() if n.startswith('cme-')
                                     for r in rows}),
                'cpus': sorted({blk['header'].get('cpu')
                                for n, bl in self._lat[b].items() if n.startswith('cme-')
                                for blk in bl}),
            }

    # ------------------------------------------------------------------ baseline and call rows
    def _cme_lat_files(self, b):
        return sorted(n for n in self._lat[b] if n.startswith('cme-latency-'))

    def _build_baseline(self):
        rows = []
        for b in BOOTS:
            for name in self._cme_lat_files(b):
                blk = self._lat[b][name][0]
                rt, call = blk['rt'], blk['call']
                rb, cb = best_rep(rt), best_rep(call)
                rows.append({
                    'boot': b, 'src': name, 'mem': blk['header']['mem'],
                    'events': blk['header']['events'],
                    'bracket_overhead_ns': blk['bracket_overhead_ns'],
                    'rt_best': rt['best'], 'rt_span': rb['span'], 'rt_cycles': rb['cycles'],
                    'rt_cme_cycles': rb['cme_cycles'], 'rt_loads': rb['loads'],
                    'rt_reps': [r['ns'] for r in rt['reps']],
                    'rt_span_reps': [r['span'] for r in rt['reps']],
                    'rt_cycles_reps': [r['cycles'] for r in rt['reps']],
                    'rt_cme_cycles_reps': [r['cme_cycles'] for r in rt['reps']],
                    'rt_outside_ns_per_call': (rb['ns'] - rb['span']) * rb['loads'],
                    'rt_counters_zero': all(r[k] == 0 for r in rt['reps'] for k in r
                                            if k in CME_COUNTERS + L3_COUNTERS),
                    'call_best': call['best'], 'call_span': cb['span'],
                    'call_outside': cb['ns'] - cb['span'], 'call_calls': cb['loads'],
                    'call_cycles': cb['cycles'], 'call_cme_cycles': cb['cme_cycles'],
                    'call_reps': [r['ns'] for r in call['reps']],
                    'call_span_reps': [r['span'] for r in call['reps']],
                    'call_outside_reps': [r['ns'] - r['span'] for r in call['reps']],
                    'call_cycles_reps': [r['cycles'] for r in call['reps']],
                    'call_cme_cycles_reps': [r['cme_cycles'] for r in call['reps']],
                    'call_span_minus_rt_span': cb['span'] - rb['span']})
        self.baseline = rows
        S = {'n_files': len(rows)}
        for scope in BOOTS + ('all',):
            rr = [r for r in rows if scope == 'all' or r['boot'] == scope]
            spans = [v for r in rr for v in r['call_span_reps']]
            out = [v for r in rr for v in r['call_outside_reps']]
            ovh = [r['bracket_overhead_ns'] for r in rr]
            common = statistics.mode(ovh)
            S[scope] = {
                'n_files': len(rr),
                'rt_best_lo': min(r['rt_best'] for r in rr), 'rt_best_hi': max(r['rt_best'] for r in rr),
                'rt_reps_lo': min(v for r in rr for v in r['rt_reps']),
                'rt_reps_hi': max(v for r in rr for v in r['rt_reps']),
                'rt_span_lo': min(v for r in rr for v in r['rt_span_reps']),
                'rt_span_hi': max(v for r in rr for v in r['rt_span_reps']),
                'rt_cycles_lo': min(v for r in rr for v in r['rt_cycles_reps']),
                'rt_cycles_hi': max(v for r in rr for v in r['rt_cycles_reps']),
                'rt_cme_cycles_lo': min(v for r in rr for v in r['rt_cme_cycles_reps']),
                'rt_cme_cycles_hi': max(v for r in rr for v in r['rt_cme_cycles_reps']),
                'rt_counters_zero': all(r['rt_counters_zero'] for r in rr),
                'call_best_lo': min(r['call_best'] for r in rr),
                'call_best_hi': max(r['call_best'] for r in rr),
                'call_span_n': len(spans), 'call_span_mode': statistics.mode(spans),
                'call_span_n_mode': sum(1 for v in spans if v == statistics.mode(spans)),
                'call_span_lo': min(spans), 'call_span_hi': max(spans),
                'call_outside_lo': min(out), 'call_outside_hi': max(out),
                'call_outside_64_lo': min(out) * 64, 'call_outside_64_hi': max(out) * 64,
                'overhead_common': common,
                'overhead_n_common': sum(1 for v in ovh if v == common),
                'overhead_other': [(r['src'], r['bracket_overhead_ns']) for r in rr
                                   if r['bracket_overhead_ns'] != common],
            }
        self.baseline_summary = S
        self.rt_ns = S['all']['rt_best_lo']          # the round-trip baseline, ns per step
        self.rt_span_ns = S['all']['rt_span_lo']

    # ------------------------------------------------------------------ clock
    def _build_clock(self):
        # Rows with fewer loads than CLOCK_MIN_LOADS are short: their counting window holds
        # many cycles outside the bracket, so they are kept out of the clock ratio.
        self.clock = {}
        allcore = []
        for b in BOOTS:
            core, cme, short = [], [], {'64 loads': [], '320 loads': [], 'cme-call': []}
            for name in self._cme_lat_files(b):
                blk = self._lat[b][name][0]
                groups = [('rt', blk['rt']['reps']), ('cme-call', blk['call']['reps'])]
                groups += [('size', blk['sizes'][s]['reps']) for s in blk['order']]
                for tag, reps in groups:
                    for r in reps:
                        q = r['cycles'] / r['ns']
                        if tag != 'cme-call' and r['loads'] >= CLOCK_MIN_LOADS:
                            core.append(q)
                            cme.append(r['cme_cycles'] / r['span'])
                        elif tag == 'cme-call':
                            short['cme-call'].append(q)
                        elif r['loads'] == 64:
                            short['64 loads'].append(q)
                        elif r['loads'] == 320:
                            short['320 loads'].append(q)
            allcore += core
            self.clock[b] = {
                'boot': b, 'src': 'cme-latency-*.csv (12 files)', 'n_rows': len(core),
                'core_lo': min(core), 'core_hi': max(core), 'core_median': statistics.median(core),
                'cme_lo': min(cme), 'cme_hi': max(cme), 'cme_median': statistics.median(cme),
                'short': {k: {'n': len(v), 'lo': min(v), 'hi': max(v)} for k, v in short.items()}}
        self.cycles_per_ns = round(statistics.median(allcore), 2)     # 2.0 on these boots
        self.clock['cycles_per_ns'] = self.cycles_per_ns
        self.clock['ns_per_cycle'] = 1.0 / self.cycles_per_ns
        self.clock['timer_hz'] = self.integrity['F1']['cntfrq_hz']
        self.clock['min_loads'] = CLOCK_MIN_LOADS

    # ------------------------------------------------------------------ chain load by footprint
    def _build_chain(self):
        self.chain = {}
        self.core_chain = []
        for b in BOOTS:
            self.chain[b] = (self._rows(b, 'cme-latency-dram-small.csv')
                             + self._rows(b, 'cme-latency-dram-large.csv')
                             + self._rows(b, 'cme-latency-dram-flushed.csv'))
        for name in ('latency-control-cpu2.csv', 'latency-dram-small.csv',
                     'latency-dram-large.csv', 'latency-dram-flushed.csv'):
            for r in self._rows('F1', name):
                r['control'] = name == 'latency-control-cpu2.csv'
                self.core_chain.append(r)
        # the one permitted earlier-boot row
        self.address_order = None
        if os.path.isfile(ADDRESS_ORDER_FILE):
            blk = parse_latency(ADDRESS_ORDER_FILE, 'E')[0]
            r = self._row(blk, blk['sizes'][blk['order'][0]])
            r['src'] = 'results/membench-jibin-010/results/bootE/cme-latency-dram-seq.csv'
            r['conditions'] = ('an earlier boot with the L3 on and the prefetchers on '
                               '(operator\'s README), 8 MiB, every line flushed first, address order')
            self.address_order = r
        # F1 against F2, and the core beside them
        core = {(r['size'], r['kind']): r for r in self.core_chain if not r['control']}
        pairs = []
        for r1, r2 in zip(self.chain['F1'], self.chain['F2']):
            assert (r1['size'], r1['kind']) == (r2['size'], r2['kind'])
            c = core.get((r1['size'], r1['kind']))
            p = {'size': r1['size'], 'label': r1['label'], 'kind': r1['kind'], 'src': r1['src'],
                 'f1': r1['best'], 'f2': r2['best'], 'f1_minus_f2': r1['best'] - r2['best'],
                 'f1_over_f2': r1['best'] / r2['best'], 'f2_over_f1': r2['best'] / r1['best'],
                 'f1_hwprf': r1['hwprf'], 'f1_refills': r1['refills'], 'f2_refills': r2['refills'],
                 'f1_rd': r1['rd'], 'f2_rd': r2['rd'], 'f1_inner': r1['inner'], 'f1_outer': r1['outer'],
                 'f2_inner': r2['inner'], 'f2_outer': r2['outer'],
                 'f1_spread_ns': r1['spread_ns'], 'f2_spread_ns': r2['spread_ns'],
                 'reps_apart': (min(r1['reps_ns']) > max(r2['reps_ns'])
                                or min(r2['reps_ns']) > max(r1['reps_ns']))}
            if c:
                p.update(core=c['best'], core_src=c['src'],
                         f1_minus_core=r1['best'] - c['best'], f1_over_core=r1['best'] / c['best'],
                         f2_minus_core=r2['best'] - c['best'],
                         f1_above_rt_minus_core=r1['above_rt'] - c['best'],
                         f2_above_rt_minus_core=r2['above_rt'] - c['best'])
            pairs.append(p)
        self.chain_pairs = pairs
        # G10: chain kinds per footprint, the step across the file boundary, flushed against walked once
        kinds = {}
        for r in self.chain['F2']:
            kinds.setdefault(r['size'], []).append(r['kind'])
        sweep_kinds = {}
        for r in self.chain['F2']:
            if r['kind'] != 'every line flushed first':
                sweep_kinds.setdefault(r['size'], set()).add(r['kind'])
        steps = []
        series = [('CME on boot F1', self.chain['F1']), ('CME on boot F2', self.chain['F2']),
                  ('core on boot F1', [r for r in self.core_chain if not r['control']])]
        for name, rows in series:
            by = {(r['size'], r['kind']): r for r in rows}
            a = by[(384 * KIB, 'walked many times')]
            z = by[(512 * KIB, 'walked once')]
            w = by[(8 * MIB, 'walked once')]
            f = by[(8 * MIB, 'every line flushed first')]
            steps.append({'series': name, 'boot': a['boot'], 'from_size': a['size'], 'to_size': z['size'],
                          'from_ns': a['best'], 'to_ns': z['best'], 'step_ns': z['best'] - a['best'],
                          'from_kind': a['kind'], 'to_kind': z['kind'],
                          'from_src': a['src'], 'to_src': z['src'],
                          'from_hwprf': a.get('hwprf'), 'to_hwprf': z.get('hwprf'),
                          'walked_once_8m': w['best'], 'flushed_8m': f['best'],
                          'flushed_minus_walked_once': f['best'] - w['best']})
        self.chain_steps = {
            'steps': steps,
            'kinds_by_size': [{'size': s, 'label': fmt_size(s), 'kinds': k} for s, k in kinds.items()],
            'sizes_with_both_sweep_kinds': [s for s, k in sweep_kinds.items() if len(k) > 1],
            'largest_walked_many': max(r['size'] for r in self.chain['F2']
                                       if r['kind'] == 'walked many times'),
            'smallest_walked_once': min(r['size'] for r in self.chain['F2']
                                        if r['kind'] == 'walked once')}
        # G5: refills per line of the chain in each timed rep
        rpl = []
        for b in BOOTS:
            for r in self.chain[b]:
                if r['kind'] != 'walked many times':
                    continue
                rpl.append({'boot': b, 'src': r['src'], 'size': r['size'], 'label': r['label'],
                            'lines': r['lines'], 'loads': r['loads'], 'walks_per_rep': r['walks_per_rep'],
                            'inner_per_line_reps': r['refills_per_line'],
                            'rd_per_line_reps': [x['rd'] * x['loads'] / r['lines'] for x in r['reps']],
                            'inner': r['inner'], 'refills': r['refills'], 'above_rt': r['above_rt'],
                            'above_rt_per_refill': r['above_rt_per_refill'],
                            'in_l1': r['size'] <= 64 * KIB})
        self.refills_per_line = rpl
        f2l1 = [r for r in rpl if r['boot'] == 'F2' and r['in_l1']]
        f2cl = [r for r in rpl if r['boot'] == 'F2' and not r['in_l1']]
        vals = [v for r in f2l1 for v in r['inner_per_line_reps']]
        self.refills_per_line_summary = {
            'boot': 'F2', 'src': 'cme-latency-dram-small.csv',
            'n_rep_rows': len(vals), 'per_line_lo': min(vals), 'per_line_hi': max(vals),
            'l1_above_rt_lo': min(r['above_rt'] for r in f2l1),
            'l1_above_rt_hi': max(r['above_rt'] for r in f2l1),
            'l1_ns_per_refill_lo': min(r['above_rt_per_refill'] for r in f2l1),
            'l1_ns_per_refill_hi': max(r['above_rt_per_refill'] for r in f2l1),
            'cluster_ns_per_refill_lo': min(r['above_rt_per_refill'] for r in f2cl),
            'cluster_ns_per_refill_hi': max(r['above_rt_per_refill'] for r in f2cl)}
        # W6: bracket minus span over the footprint rows
        self.bracket_minus_span = {}
        for b in BOOTS:
            allr = [x['ns'] - x['span'] for r in self.chain[b] for x in r['reps']]
            best = [r['bracket_minus_span'] for r in self.chain[b]]
            self.bracket_minus_span[b] = {'boot': b, 'all_lo': round(min(allr), 3),
                                          'all_hi': round(max(allr), 3),
                                          'best_lo': round(min(best), 3), 'best_hi': round(max(best), 3)}

    def chain_row(self, boot, size, kind=None):
        """One row of D.chain[boot] by footprint (and chain kind where two rows share a footprint)."""
        for r in self.chain[boot]:
            if r['size'] == size and (kind is None or r['kind'] == kind):
                return r
        return None

    def chain_sweep(self, boot):
        """The 23 footprint rows without the flushed 8 MiB row, in footprint order."""
        return [r for r in self.chain[boot] if r['kind'] != 'every line flushed first']

    def core_row(self, size, kind=None):
        for r in self.core_chain:
            if not r['control'] and r['size'] == size and (kind is None or r['kind'] == kind):
                return r
        return None

    # ------------------------------------------------------------------ L3-event rows
    def _build_l3(self):
        self.chain_l3 = {}
        self.l3_reps = {}
        self.l3_repeat = {}
        self.l3_checks = {}
        for b in BOOTS:
            rows = (self._rows(b, 'cme-latency-dram-small-l3.csv')
                    + self._rows(b, 'cme-latency-dram-large-l3.csv'))
            plain = {r['size']: r for r in self.chain_sweep(b)}
            reps = []
            for r in rows:
                p = plain[r['size']]
                tot = r['hit'] + r['miss']
                r.update(miss_minus_refill=r['miss'] - r['refill'],
                         hit_share=(r['hit'] / tot) if tot >= 0.5 else None,
                         hit_plus_miss=tot,
                         plain=p['best'], plain_src=p['src'], diff=r['best'] - p['best'],
                         ratio=r['best'] / p['best'], plain_inner=p['inner'], plain_outer=p['outer'],
                         plain_reps_ns=p['reps_ns'])
                for x in r['reps']:
                    reps.append({'boot': b, 'src': r['src'], 'size': r['size'], 'label': r['label'],
                                 'kind': r['kind'], 'mode': x['mode'], 'rep': x['rep'],
                                 'loads': x['loads'], 'ns': x['ns'], 'span': x['span'],
                                 'inner': x['inner'], 'outer': x['outer'], 'hit': x['hit'],
                                 'miss': x['miss'], 'refill': x['refill'],
                                 'mms': x['miss'] - x['refill'],
                                 'hit_share': (x['hit'] / (x['hit'] + x['miss']))
                                 if x['hit'] + x['miss'] >= 0.5 else None})
            self.chain_l3[b] = rows
            self.l3_reps[b] = reps
            pct = [abs(r['ratio'] - 1) * 100 for r in rows]
            worst = max(rows, key=lambda r: abs(r['ratio'] - 1))
            self.l3_repeat[b] = {
                'boot': b, 'n': len(rows), 'n_within_1pct': sum(1 for v in pct if v <= 1.0),
                'ratio_lo': min(r['ratio'] for r in rows), 'ratio_hi': max(r['ratio'] for r in rows),
                'diff_lo': min(r['diff'] for r in rows), 'diff_hi': max(r['diff'] for r in rows),
                'worst_pct': max(pct), 'worst_size': worst['size'], 'worst_label': worst['label'],
                'worst_l3': worst['best'], 'worst_plain': worst['plain'],
                'worst_l3_reps': worst['reps_ns'], 'worst_plain_reps': worst['plain_reps_ns'],
                'outside_1pct': [{'size': r['size'], 'label': r['label'], 'l3': r['best'],
                                  'plain': r['plain'], 'ratio': r['ratio'], 'diff': r['diff'],
                                  'l3_reps': r['reps_ns'], 'plain_reps': r['plain_reps_ns']}
                                 for r in rows if abs(r['ratio'] - 1) * 100 > 1.0]}
            nrep = sum(len(blk['rt']['reps']) + len(blk['call']['reps'])
                       + sum(len(blk['sizes'][s]['reps']) for s in blk['order'])
                       for f in ('cme-latency-dram-small-l3.csv', 'cme-latency-dram-large-l3.csv')
                       for blk in self._lat[b][f])
            d = [abs(x['hit'] + x['miss'] - x['inner'] - x['outer']) for x in reps]
            self.l3_checks[b] = {
                'boot': b, 'rep_rows': nrep, 'chain_rep_rows': len(reps),
                'refill_differs_from_outer': sum(1 for x in reps if x['refill'] != x['outer']),
                'max_hit_miss_minus_refills': max(d),
                'max_hit_miss_minus_refills_counts': max(
                    abs(x['hit'] + x['miss'] - x['inner'] - x['outer']) * x['loads'] for x in reps),
                'hit_plus_miss_lo': min(r['hit_plus_miss'] for r in rows),
                'hit_plus_miss_hi': max(r['hit_plus_miss'] for r in rows)}
        # fits on boot F2 (hypothesis material only)
        R = self.l3_reps['F2']
        rt = self.rt_ns

        def sel(lo, hi, extra=None):
            return [x for x in R if lo <= x['size'] <= hi and (extra is None or extra(x))]

        def fit(name, rows, cols, intercept=False, sub=0.0, desc=''):
            A = [[x[c] for c in cols] + ([1.0] if intercept else []) for x in rows]
            y = [x['ns'] - sub for x in rows]
            f = lstsq(A, y)
            out = {'name': name, 'boot': 'F2', 'desc': desc, 'n': len(rows), 'cols': cols,
                   'src': 'cme-latency-dram-small-l3.csv, cme-latency-dram-large-l3.csv',
                   'intercept_fitted': intercept, 'subtracted': sub, 'ok': f is not None,
                   'hit': None, 'mms': None, 'outer': None, 'intercept': None}
            if f:
                for c, v in zip(cols + (['intercept'] if intercept else []), f['coef']):
                    out[c] = v
                out.update(rms=f['rms'], max_res=f['max_res'], cond_raw=f['cond_raw'],
                           cond_unit=f['cond_unit'], res=f['res'])
            return out

        K, M = KIB, MIB
        c3 = ['hit', 'mms', 'outer']
        fits = [
            fit('A1', sel(96 * K, 384 * K, lambda x: x['outer'] < 0.005), ['hit', 'mms'],
                desc='96 KiB to 384 KiB, rows with under 0.005 outer refills per load, no intercept'),
            fit('A2', sel(96 * K, 384 * K), c3, desc='96 KiB to 384 KiB, no intercept'),
            fit('A3', sel(96 * K, 384 * K), c3, True, desc='96 KiB to 384 KiB, with intercept'),
            fit('B2', sel(512 * K, 3 * M), c3, desc='512 KiB to 3 MiB, no intercept'),
            fit('B1', sel(512 * K, 32 * M), c3, desc='512 KiB to 32 MiB, no intercept'),
            fit('C1', sel(96 * K, 3 * M), c3, desc='96 KiB to 3 MiB, no intercept'),
            fit('C2', sel(96 * K, 3 * M), c3, sub=rt,
                desc='96 KiB to 3 MiB, round-trip baseline subtracted, no intercept'),
            fit('C3', sel(96 * K, 3 * M), c3, True, desc='96 KiB to 3 MiB, with intercept'),
            fit('E1', sel(4 * K, 3 * M), c3, True, desc='4 KiB to 3 MiB, with intercept'),
            fit('D1', sel(96 * K, 32 * M), c3, desc='96 KiB to 32 MiB, no intercept'),
        ]
        self.l3_fits = {f['name']: f for f in fits}
        mid = sel(96 * K, 384 * K)
        a, s, res = linfit([x['hit'] for x in mid], [x['ns'] for x in mid])
        self.l3_line = {
            'boot': 'F2', 'src': 'cme-latency-dram-small-l3.csv', 'n': len(mid),
            'intercept': a, 'slope': s, 'at_hit_1': a + s,
            'rms': math.sqrt(sum(e * e for e in res) / len(res)),
            'r': pearson([x['hit'] for x in mid], [x['ns'] for x in mid]),
            'ns_lo': min(x['ns'] for x in mid), 'ns_hi': max(x['ns'] for x in mid),
            'hit_lo': min(x['hit'] for x in mid), 'hit_hi': max(x['hit'] for x in mid),
            'outer_lo': min(x['outer'] for x in mid), 'outer_hi': max(x['outer'] for x in mid),
            'mms_lo': min(x['mms'] for x in mid), 'mms_hi': max(x['mms'] for x in mid)}
        # C1 with one footprint left out
        c1rows = sel(96 * K, 3 * M)
        loo = []
        for s_ in sorted({x['size'] for x in c1rows}):
            f = fit('C1 without ' + fmt_size(s_), [x for x in c1rows if x['size'] != s_], c3)
            loo.append(f)
        self.l3_loo = {'n_fits': len(loo),
                       'hit_lo': min(f['hit'] for f in loo), 'hit_hi': max(f['hit'] for f in loo),
                       'mms_lo': min(f['mms'] for f in loo), 'mms_hi': max(f['mms'] for f in loo),
                       'outer_lo': min(f['outer'] for f in loo), 'outer_hi': max(f['outer'] for f in loo)}
        # cost of one outer refill implied by the C1 hit and miss-without-outer-refill coefficients
        C1 = self.l3_fits['C1']
        oc = []
        for r in self.chain_l3['F2']:
            if r['size'] >= 512 * K and r['outer'] > 0:
                oc.append({'size': r['size'], 'label': r['label'], 'src': r['src'],
                           'outer': r['outer'],
                           'ns_per_outer_est': (r['best'] - C1['hit'] * r['hit']
                                                - C1['mms'] * r['miss_minus_refill']) / r['outer']})
        self.l3_outer_cost = oc
        large = sel(512 * K, 3 * M)
        self.l3_large = {
            'n': len(large), 'ns_lo': min(x['ns'] for x in large), 'ns_hi': max(x['ns'] for x in large),
            'r_outer': pearson([x['outer'] for x in large], [x['ns'] for x in large]),
            'r_hit': pearson([x['hit'] for x in large], [x['ns'] for x in large]),
            'above_3m': [{'size': r['size'], 'label': r['label'], 'best': r['best'], 'hit': r['hit'],
                          'outer': r['outer'], 'mms': r['miss_minus_refill']}
                         for r in self.chain_l3['F2'] if r['size'] > 3 * M]}

    def l3_row(self, boot, size):
        for r in self.chain_l3[boot]:
            if r['size'] == size:
                return r
        return None

    # ------------------------------------------------------------------ bandwidth
    def _build_bw(self):
        cyc = self.cycles_per_ns
        self.bw_rows = []
        for b in BOOTS:
            for name, rows in self._bw[b].items():
                for r in rows:
                    r['bytes_per_cycle'] = r['best'] / cyc
                    if r['best_span'] is not None:
                        r['span_bytes_per_cycle'] = r['best_span'] / cyc
                    r['label'] = fmt_size(r['size'])
                    r['log_line'] = self.cmd_lines[b].get((name, r['block']))
                    if name.startswith('cme-') and r['mem'] == 'dram':
                        self.bw_rows.append(r)
        self.core_bw = [r for r in self._bw['F1']['bandwidth-dram-1core.csv']]

        def get(boot, group, kernel, size):
            for r in self.bw_rows:
                if (r['boot'], r['group'], r['kernel'], r['size']) == (boot, group, kernel, size):
                    return r
            return None
        self._bwget = get

        # the L1 forms: per-pass times and fits
        forms = [('looped', 'l1-looped', 'read'), ('looped', 'l1-looped', 'write'),
                 ('single-call', 'l1-single', 'read'), ('single-call', 'l1-single', 'write'),
                 ('looped, no fold', 'l1-nofold', 'read'), ('looped, DSB ST', 'l1-dsb', 'write')]
        sizes = [4 * KIB, 8 * KIB, 16 * KIB, 24 * KIB]
        self.l1_sizes = sizes
        self.l1_forms, self.l1_fits = [], []
        for b in BOOTS:
            for form, group, kernel in forms:
                rows = [get(b, group, kernel, s) for s in sizes]
                fr = {'boot': b, 'form': form, 'kernel': kernel, 'group': group, 'src': rows[0]['src'],
                      'sizes': sizes, 'passes': [r['passes'] for r in rows],
                      'ns_bracket': [r['ns_per_pass'] for r in rows],
                      'ns_span': [r['ns_per_pass_span'] for r in rows],
                      'gbps': [r['best'] for r in rows], 'span_gbps': [r['best_span'] for r in rows],
                      'outside': [r['outside_ns_per_call'] for r in rows],
                      'spread_max': max(r['spread_pct'] for r in rows),
                      'spread_span_max': max(r['spread_span_pct'] for r in rows), 'rows': rows}
                self.l1_forms.append(fr)
                for clock in ('bracket', 'span'):
                    ys = fr['ns_bracket'] if clock == 'bracket' else fr['ns_span']
                    a, s, res = linfit(sizes, ys)
                    i_abs = max(range(4), key=lambda i: abs(res[i]))
                    i_rel = max(range(4), key=lambda i: abs(res[i]) / ys[i])
                    pct = 100.0 * abs(res[i_abs]) / min(ys)
                    self.l1_fits.append({
                        'boot': b, 'form': form, 'kernel': kernel, 'clock': clock, 'src': fr['src'],
                        'intercept_ns': a, 'rate_gbps': 1.0 / s, 'rate_bytes_per_cycle': 1.0 / s / cyc,
                        'res': res, 'max_res_ns': abs(res[i_abs]), 'max_res_size': sizes[i_abs],
                        'smallest_pass_ns': min(ys), 'max_res_pct': pct,
                        'max_rel_res_pct': 100.0 * abs(res[i_rel]) / ys[i_rel],
                        'max_rel_res_size': sizes[i_rel], 'max_rel_res_ns': abs(res[i_rel]),
                        'verdict': 'void' if pct > 2.0 else 'pass', 'ns_per_pass': ys})
        # differences between the forms, point by point
        diffs = []
        for b in BOOTS:
            f = {(x['form'], x['kernel']): x for x in self.l1_forms if x['boot'] == b}
            for i, s in enumerate(sizes):
                diffs.append({
                    'boot': b, 'size': s, 'label': fmt_size(s),
                    'fold_ns': f[('looped', 'read')]['ns_bracket'][i]
                    - f[('looped, no fold', 'read')]['ns_bracket'][i],
                    'fold_span_ns': f[('looped', 'read')]['ns_span'][i]
                    - f[('looped, no fold', 'read')]['ns_span'][i],
                    'dsb_ns': f[('looped, DSB ST', 'write')]['ns_bracket'][i]
                    - f[('looped', 'write')]['ns_bracket'][i],
                    'dsb_span_ns': f[('looped, DSB ST', 'write')]['ns_span'][i]
                    - f[('looped', 'write')]['ns_span'][i]})
        self.l1_diffs = diffs
        # looped against single-call, 4 KiB to 256 KiB
        lvs = []
        for b in BOOTS:
            for kernel in ('read', 'write'):
                for s in sizes + [48 * KIB, 96 * KIB, 160 * KIB, 256 * KIB]:
                    small = s <= 24 * KIB
                    lo = get(b, 'l1-looped' if small else 'sweep', kernel, s)
                    si = get(b, 'l1-single' if small else 'sweep-single', kernel, s)
                    lvs.append({'boot': b, 'kernel': kernel, 'size': s, 'label': fmt_size(s),
                                'looped_src': lo['src'], 'single_src': si['src'],
                                'looped_ns': lo['ns_per_pass'], 'single_ns': si['ns_per_pass'],
                                'diff_ns': lo['ns_per_pass'] - si['ns_per_pass'],
                                'looped_gbps': lo['best'], 'single_gbps': si['best'],
                                'looped_span_gbps': lo['best_span'], 'single_span_gbps': si['best_span']})
        self.looped_vs_single = lvs
        # call-cost rows as ns per call
        self.call_cost = []
        for b in BOOTS:
            for r in self._bw[b]['cme-bandwidth-call-cost.csv']:
                self.call_cost.append({
                    'boot': b, 'src': r['src'], 'kernel': r['kernel'], 'size': r['size'],
                    'label': r['label'], 'passes': r['passes'],
                    'bracket_ns': r['ns_per_pass'], 'span_ns': r['ns_per_pass_span'],
                    'outside_ns': r['outside_ns_per_call'], 'outside_lo': r['outside_lo'],
                    'outside_hi': r['outside_hi'], 'outside_reps': r['outside_reps'],
                    'gbps': r['best'], 'span_gbps': r['best_span'],
                    'reps_bracket_ns': [x['bracket_ns_per_pass'] for x in r['reps']],
                    'reps_span_ns': [x['span_ns_per_pass'] for x in r['reps']],
                    'best_rep': r['best_rep_index']})
        # 64-byte forms beside the 256-byte forms
        self.forms64 = []
        for b in BOOTS:
            for k64, k256 in (('read64', 'read'), ('write64', 'write')):
                for r in self.bw_table('sweep', b, k64):
                    o = get(b, 'sweep', k256, r['size'])
                    self.forms64.append({
                        'boot': b, 'src': r['src'], 'kernel': k64, 'size': r['size'],
                        'label': r['label'], 'passes': r['passes'], 'gbps': r['best'],
                        'span_gbps': r['best_span'], 'bytes_per_cycle': r['bytes_per_cycle'],
                        'spread_pct': r['spread_pct'], 'gbps_256': o['best'],
                        'span_gbps_256': o['best_span'], 'ratio_to_256': r['best'] / o['best']})
        # the core against the CME on boot F1
        cvc = []
        for c in self.core_bw:
            if c['kernel'] not in ('read', 'write', 'copy'):
                continue
            lo = get('F1', 'sweep', c['kernel'], c['size'])
            if lo is None:
                continue
            si = (get('F1', 'l1-single', c['kernel'], c['size'])
                  or get('F1', 'sweep-single', c['kernel'], c['size']))
            row = {'boot': 'F1', 'kernel': c['kernel'], 'size': c['size'], 'label': c['label'],
                   'core_src': c['src'], 'cme_src': lo['src'], 'core': c['best'],
                   'core_bytes_per_cycle': c['bytes_per_cycle'], 'core_spread_pct': c['spread_pct'],
                   'cme_looped': lo['best'], 'cme_looped_span': lo['best_span'],
                   'looped_over_core': lo['best'] / c['best'],
                   'looped_span_over_core': lo['best_span'] / c['best'],
                   'cme_single': None, 'single_over_core': None, 'single_src': None}
            if si:
                row.update(cme_single=si['best'], single_over_core=si['best'] / c['best'],
                           single_src=si['src'], cme_single_span=si['best_span'])
            cvc.append(row)
        self.core_vs_cme_bw = cvc
        # boot F2 against boot F1, every CME row
        fvf = []
        for r1 in [r for r in self.bw_rows if r['boot'] == 'F1']:
            r2 = get('F2', r1['group'], r1['kernel'], r1['size'])
            a, z = r1['reps_gbps'], r2['reps_gbps']
            fvf.append({'group': r1['group'], 'form': r1['form'], 'kernel': r1['kernel'],
                        'size': r1['size'], 'label': r1['label'], 'src': r1['src'],
                        'f1': r1['best'], 'f2': r2['best'], 'f2_over_f1': r2['best'] / r1['best'],
                        'f1_span': r1['best_span'], 'f2_span': r2['best_span'],
                        'f2_over_f1_span': r2['best_span'] / r1['best_span'],
                        'f1_spread_pct': r1['spread_pct'], 'f2_spread_pct': r2['spread_pct'],
                        'reps_apart': min(a) > max(z) or min(z) > max(a)})
        self.bw_f1_vs_f2 = fvf
        # W2: single-call read against write at 16 KiB, span rates
        self.store_vs_load = []
        for b in BOOTS:
            rd, wr = get(b, 'l1-single', 'read', 16 * KIB), get(b, 'l1-single', 'write', 16 * KIB)
            self.store_vs_load.append({
                'boot': b, 'src': rd['src'], 'size': 16 * KIB, 'read_span_gbps': rd['best_span'],
                'write_span_gbps': wr['best_span'], 'ratio': rd['best_span'] / wr['best_span'],
                'write_cycles_per_64b': LINE / (wr['best_span'] / cyc),
                'read_cycles_per_64b': LINE / (rd['best_span'] / cyc)})
        # G2: measured rates against the documented limits
        self.limits = {}
        for b in BOOTS:
            rd = [get(b, 'l1-single', 'read', s) for s in sizes] + [get(b, 'sweep-single', 'read', 48 * KIB)]
            wr = [get(b, 'l1-single', 'write', s) for s in sizes] + [get(b, 'sweep-single', 'write', 48 * KIB)]
            v = [r['best'] for r in rd]
            w = [r['best'] for r in wr]
            self.limits[b] = {
                'boot': b, 'src': 'cme-bandwidth-l1-asmpasses.csv, cme-bandwidth-dram-1core-asmpasses.csv',
                'sizes': sizes + [48 * KIB],
                'read_gbps_lo': min(v), 'read_gbps_hi': max(v),
                'read_bpc_lo': min(v) / cyc, 'read_bpc_hi': max(v) / cyc,
                'read_vec_per_cycle_lo': min(v) / cyc / LINE, 'read_vec_per_cycle_hi': max(v) / cyc / LINE,
                'read_cycles_per_kib_lo': 1024 / (max(v) / cyc), 'read_cycles_per_kib_hi': 1024 / (min(v) / cyc),
                'write_gbps_lo': min(w), 'write_gbps_hi': max(w),
                'write_bpc_lo': min(w) / cyc, 'write_bpc_hi': max(w) / cyc,
                'write_cycles_per_vec_lo': LINE / (max(w) / cyc),
                'write_cycles_per_vec_hi': LINE / (min(w) / cyc)}
        self.limits['doc'] = {'loads_or_stores_per_cycle_max': 2, 'cme_load_pipes': 1,
                              'cme_store_pipes': 1, 'read_loop_instructions': 23,
                              'read_load_instructions_per_iter': 4, 'vectors_per_load': 4,
                              'llvm_ld4_release_cycles': 2,
                              'note': 'typed facts: Arm C1-Nano Software Optimization Guide 109590 '
                                      'section 2.33.3; refs/AArch64SchedC1Nano.td lines 84 to 85 (the pipes), '
                                      'line 361 and lines 2885 to 2890 (a 4-vector load holds the load pipe '
                                      'for 2 cycles); cme_kern.S (23 instructions per 1 KiB read loop '
                                      'iteration, 4 of them ld1b of 4 vectors, lines 174 to 177)'}
        # outside-span time per call, by situation
        self._build_outside()
        # G4: lines in flight, est.
        lif = []
        for b in BOOTS:
            for s in (256 * KIB, 2 * MIB, 32 * MIB):
                ch = self.chain_row(b, s)
                rd = get(b, 'sweep', 'read', s)
                per_line = LINE / rd['best']
                lif.append({'boot': b, 'size': s, 'label': fmt_size(s), 'chain_src': ch['src'],
                            'read_src': rd['src'], 'chain_ns': ch['best'], 'read_gbps': rd['best'],
                            'ns_per_line': per_line, 'ratio_est': ch['best'] / per_line,
                            'ratio_above_rt_est': ch['above_rt'] / per_line})
        self.lines_in_flight = lif

    def bw_table(self, group, boot=None, kernel=None):
        """CME DRAM-backed bandwidth rows of one file group, in file order."""
        return [r for r in self.bw_rows if r['group'] == group
                and (boot is None or r['boot'] == boot)
                and (kernel is None or r['kernel'] == kernel)]

    def bw_row(self, boot, group, kernel, size):
        return self._bwget(boot, group, kernel, size)

    def l1_form(self, boot, form, kernel):
        for f in self.l1_forms:
            if (f['boot'], f['form'], f['kernel']) == (boot, form, kernel):
                return f
        return None

    def l1_fit(self, boot, form, kernel, clock):
        for f in self.l1_fits:
            if (f['boot'], f['form'], f['kernel'], f['clock']) == (boot, form, kernel, clock):
                return f
        return None

    def _build_outside(self):
        rows = []

        def add(boot, key, label, vals, src, per='call'):
            vals = sorted(vals)
            rows.append({'boot': boot, 'key': key, 'label': label, 'src': src, 'per': per,
                         'n': len(vals), 'lo': vals[0], 'hi': vals[-1],
                         'median': statistics.median(vals)})

        for b in BOOTS:
            base = [r for r in self.baseline if r['boot'] == b]
            add(b, 'cme-call', 'cme-call rows: 64 calls that follow each other in one bracket',
                [v for r in base for v in r['call_outside_reps']], 'cme-latency-*.csv (12 files)')
            p64, p320, dense = [], [], []
            for name in self._cme_lat_files(b):
                if 'ocm' not in name:
                    continue
                for s, e in self._lat[b][name][0]['sizes'].items():
                    for x in e['reps']:
                        v = (x['ns'] - x['span']) * x['loads']
                        (p64 if x['loads'] == 64 else p320 if x['loads'] == 320 else dense).append(v)
            add(b, 'ocm-64', 'one call alone in its bracket: OCM pass of 64 loads', p64,
                'cme-latency-ocm-region0..4.csv')
            add(b, 'ocm-320', 'one call alone in its bracket: OCM pass of 320 loads', p320,
                'cme-latency-ocm-all5.csv')
            add(b, 'ocm-20480', 'one call alone in its bracket: OCM pass of 20,480 loads', dense,
                'cme-latency-ocm-all5-dense.csv')
            l1 = [v for g in ('l1-looped', 'l1-nofold', 'l1-dsb') for r in self.bw_table(g, b)
                  for v in r['outside_reps']]
            add(b, 'looped-l1', 'looped calls that follow each other, 4 KiB to 24 KiB (all L1 looped files)', l1,
                'cme-bandwidth-l1-passes.csv, -l1-nofold.csv, -l1-dsb.csv')
            sw = self.bw_table('sweep', b)
            add(b, 'looped-sweep-small', 'looped calls that follow each other, 16 KiB to 256 KiB',
                [v for r in sw if r['size'] <= 256 * KIB for v in r['outside_reps']],
                'cme-bandwidth-dram-1core.csv')
            add(b, 'looped-sweep-large', 'looped calls that follow each other, 1 MiB to 32 MiB',
                [v for r in sw if r['size'] >= MIB for v in r['outside_reps']],
                'cme-bandwidth-dram-1core.csv')
            for kernel in ('read', 'write'):
                rr = self.bw_table('l1-single', b, kernel) + self.bw_table('sweep-single', b, kernel)
                add(b, 'single-first-' + kernel,
                    'single-call %s: the one call of the first rep' % kernel,
                    [r['reps'][0]['outside_ns'] for r in rr],
                    'cme-bandwidth-l1-asmpasses.csv, cme-bandwidth-dram-1core-asmpasses.csv')
                add(b, 'single-later-' + kernel,
                    'single-call %s: the one call of each later rep' % kernel,
                    [x['outside_ns'] for r in rr for x in r['reps'][1:]],
                    'cme-bandwidth-l1-asmpasses.csv, cme-bandwidth-dram-1core-asmpasses.csv')
        self.outside_span = rows
        o = {(r['boot'], r['key']): r for r in rows}
        self.outside_check = {}
        for b in BOOTS:
            lone = o[(b, 'ocm-64')]['median']
            c64 = o[(b, 'cme-call')]['lo'] * 64
            self.outside_check[b] = {'boot': b, 'lone_call_ns': lone, 'calls64_ns': c64,
                                     'later_call_est_ns': (c64 - lone) / 63,
                                     'extra_alone_ns': lone - o[(b, 'cme-call')]['median']}

    def outside(self, boot, key):
        for r in self.outside_span:
            if r['boot'] == boot and r['key'] == key:
                return r
        return None

    # ------------------------------------------------------------------ OCM
    def _build_ocm(self):
        self.ocm_lat = {b: [] for b in BOOTS}
        self.ocm_core = []
        for b in BOOTS:
            for name in OCM_NAMES:
                r = self._rows(b, 'cme-latency-ocm-%s.csv' % name)[0]
                self._ocm_tag(r, name)
                self.ocm_lat[b].append(r)
        for name in OCM_NAMES:
            r = self._rows('F1', 'latency-ocm-%s-cpu2.csv' % name)[0]
            self._ocm_tag(r, name)
            self.ocm_core.append(r)
        pairs = []
        for i, name in enumerate(OCM_NAMES):
            r1, r2, c = self.ocm_lat['F1'][i], self.ocm_lat['F2'][i], self.ocm_core[i]
            pairs.append({
                'name': name, 'row_label': r1['row_label'], 'region': r1['region'],
                'shape': r1['shape'], 'steps': r1['steps'], 'node': r1['node'],
                'f1_src': r1['src'], 'f2_src': r2['src'], 'core_src': c['src'],
                'f1': r1['best'], 'f1_span': r1['span'], 'f1_best_span': r1['best_span'],
                'f2': r2['best'], 'f2_span': r2['span'], 'f2_best_span': r2['best_span'],
                'core': c['best'], 'core_median': c['median_ns'], 'core_spread_pct': c['spread_pct'],
                'core_demand_only': c['demand_only'],
                'f2_over_f1': r2['best'] / r1['best'],
                'f2_over_f1_span': r2['best_span'] / r1['best_span'],
                'f2_all_above_f1': min(r2['reps_span']) > max(r1['reps_span']),
                'f1_span_minus_core': r1['best_span'] - c['best'],
                'f1_span_over_core': r1['best_span'] / c['best'],
                'f1_minus_core': r1['best'] - c['best'], 'f1_over_core': r1['best'] / c['best'],
                'f2_span_minus_core': r2['best_span'] - c['best'],
                'f2_span_over_core': r2['best_span'] / c['best']})
        self.ocm_pairs = pairs
        self.ocm_stats = {}
        for b in BOOTS:
            reg = self.ocm_lat[b][:5]
            near = [r for r in reg if r['steps'] == 1]
            far = [r for r in reg if r['steps'] == 3]
            nm = sum(r['best_span'] for r in near) / len(near)
            fm = sum(r['best_span'] for r in far) / len(far)
            xs = [x['rd'] for r in reg for x in r['reps']]
            ys = [x['span'] for r in reg for x in r['reps']]
            st = {'boot': b, 'src': 'cme-latency-ocm-region0..4.csv',
                  'near_lo': min(r['best_span'] for r in near), 'near_hi': max(r['best_span'] for r in near),
                  'far_lo': min(r['best_span'] for r in far), 'far_hi': max(r['best_span'] for r in far),
                  'near_mean': nm, 'far_mean': fm, 'far_minus_near': fm - nm,
                  'extra_steps': 2, 'ns_per_extra_step': (fm - nm) / 2,
                  'near_pass_lo': min(v for r in near for v in r['reps_span']),
                  'near_pass_hi': max(v for r in near for v in r['reps_span']),
                  'far_pass_lo': min(v for r in far for v in r['reps_span']),
                  'far_pass_hi': max(v for r in far for v in r['reps_span']),
                  'mean_of_five': sum(r['best_span'] for r in reg) / 5,
                  'spread_lo': min(r['spread_pct'] for r in reg), 'spread_hi': max(r['spread_pct'] for r in reg),
                  'spread_span_lo': min(r['spread_span_pct'] for r in reg),
                  'spread_span_hi': max(r['spread_span_pct'] for r in reg),
                  'demand_only_rows': sum(1 for r in self.ocm_lat[b] if r['demand_only']),
                  'n_passes': len(xs)}
            st['far_all_above_near'] = st['far_pass_lo'] > st['near_pass_hi']
            if max(xs) > min(xs):
                a, s, _ = linfit(xs, ys)
                st.update(rd_fit_intercept=a, rd_fit_slope=s, rd_fit_r=pearson(xs, ys),
                          rd_fit_at_1=a + s)
            self.ocm_stats[b] = st
        # OCM bandwidth
        self.ocm_bw = {b: [] for b in BOOTS}
        self.ocm_bw_core = []
        names = ['region0', 'region1', 'region2', 'region3', 'region4', 'all5', 'write']
        for b in BOOTS:
            for name in names:
                r = self._bw[b]['cme-bandwidth-ocm-%s.csv' % name][0]
                self._ocm_bw_tag(r, name)
                self.ocm_bw[b].append(r)
        for name in names:
            r = self._bw['F1']['bandwidth-ocm-%s.csv' % name][0]
            self._ocm_bw_tag(r, name)
            self.ocm_bw_core.append(r)
        bp = []
        for i, name in enumerate(names):
            r1, r2, c = self.ocm_bw['F1'][i], self.ocm_bw['F2'][i], self.ocm_bw_core[i]
            bp.append({'name': name, 'row_label': r1['row_label'], 'kernel': r1['kernel'],
                       'region': r1['region'], 'f1_src': r1['src'], 'f2_src': r2['src'],
                       'core_src': c['src'],
                       'f1': r1['best'], 'f1_span': r1['best_span'], 'f2': r2['best'],
                       'f2_span': r2['best_span'], 'core': c['best'],
                       'f1_over_core': r1['best'] / c['best'], 'f2_over_core': r2['best'] / c['best'],
                       'f2_over_f1': r2['best'] / r1['best'],
                       'f2_all_below_f1': max(r2['reps_gbps']) < min(r1['reps_gbps']),
                       'f1_ns_per_line': r1['ns_per_line'], 'f2_ns_per_line': r2['ns_per_line'],
                       'core_ns_per_line': c['ns_per_line']})
        self.ocm_bw_pairs = bp

    def _ocm_tag(self, r, name):
        m = re.fullmatch(r'region(\d)', name)
        r['name'] = name
        r['region'] = int(m.group(1)) if m else None
        r['row_label'] = ('region %d' % r['region']) if m else 'all five regions'
        r['node'] = REGION_NODE[r['region']] if m else None
        if m:
            x, y = r['node'] >> 6, (r['node'] >> 3) & 7
            r['steps'] = abs(x - DSU1_XY[0]) + abs(y - DSU1_XY[1])
        else:
            r['steps'] = None
        r['passes_ns'] = r['reps_ns']
        if 'reps_span' in r:
            r['passes_span'] = r['reps_span']

    def _ocm_bw_tag(self, r, name):
        m = re.fullmatch(r'region(\d)', name)
        r['name'] = name
        r['region'] = int(m.group(1)) if m else None
        r['row_label'] = ('%s, region %d' % (r['kernel'], r['region'])) if m \
            else ('%s, all five regions' % r['kernel'])
        r['lines'] = r['size'] // LINE
        r['kernel_calls_per_pass'] = r['segments']
        r['best_bracket_us'] = r['best_bracket_ns'] / 1000.0

    # ------------------------------------------------------------------ mesh
    def _build_mesh(self):
        hns = sorted([c for c in self.mesh_cells if c['type'] == 'HN-S'], key=lambda c: c['index'])
        by_xy = {(c['x'], c['y']): c for c in hns}
        self.mesh_layout = []
        iomem = self.platform['ocm_iomem']
        for region, node in enumerate(REGION_NODE):
            x, y = node >> 6, (node >> 3) & 7
            c = by_xy.get((x, y))
            self.mesh_layout.append({
                'region': region, 'node': node, 'x': x, 'y': y,
                'hns_index': c['index'] if c else None, 'xp': c['xp'] if c else None,
                'base': iomem[region]['base'] if region < len(iomem) else None,
                'base_line': iomem[region]['line'] if region < len(iomem) else None,
                'steps': abs(x - DSU1_XY[0]) + abs(y - DSU1_XY[1]),
                'map_has_hns': c is not None, 'src': 'sysinfo.txt', 'boot': 'F1',
                'map_line': c['line'] if c else None})
        rnf = [c for c in self.mesh_cells if c['type'].startswith('RN-F')]
        self.mesh_rnf_steps = [{'x': c['x'], 'y': c['y'], 'xp': c['xp'],
                                'steps': [abs(l['x'] - c['x']) + abs(l['y'] - c['y'])
                                          for l in self.mesh_layout],
                                'is_dsu1_hypothesis': (c['x'], c['y']) == DSU1_XY}
                               for c in rnf]
        types = {}
        for c in self.mesh_cells:
            t = 'RN-F' if c['type'].startswith('RN-F') else c['type']
            types[t] = types.get(t, 0) + 1
        self.mesh_summary = {
            'grid_x': 1 + max(c['x'] for c in self.mesh_cells),
            'grid_y': 1 + max(c['y'] for c in self.mesh_cells),
            'device_counts': types, 'dsu1_xy': DSU1_XY, 'dsu1_is_hypothesis': True,
            'rnf_cells_matching_1_1_1_3_3': [(r['x'], r['y']) for r in self.mesh_rnf_steps
                                             if r['steps'] == [1, 1, 1, 3, 3]],
            'map_first_line': self.platform['mesh_map']['line'],
            'map_last_line': self.platform['mesh_map']['last_line']}
        # requests per node per label
        self.mesh_requests = {}
        intended_ok = 0
        intended_n = 0
        from_counts = {}
        for b in BOOTS:
            rows = []
            labels = []
            for r in self._cmn[b]:
                if r['label'].startswith('cme-') and r['label'] not in labels:
                    labels.append(r['label'])
            for lab in labels:
                nodes = self.cmn_nodes(b, lab)
                get1 = lambda ev: next((r['count'] for r in self.cmn(b, lab, ev)), None)
                m = re.search(r'region(\d)', lab)
                bwprog = 'read' in lab or 'write' in lab
                row = {'boot': b, 'src': 'cmn-counts.csv', 'label': lab, 'nodes': nodes,
                       'counts': [nodes[n] for n in REGION_NODE], 'sum': sum(nodes.values()),
                       'lifetime_ms': get1('child_elapsed_ns') / 1e6,
                       'mc_reqs_local': get1('hns_mc_reqs_local_all'),
                       'cache_miss': get1('hns_cache_miss_all'),
                       'program': 'bandwidth' if bwprog else 'latency',
                       'region': int(m.group(1)) if m else None,
                       'top_node': max(nodes, key=nodes.get),
                       'lowest_node': min(nodes, key=nodes.get),
                       'ocm': 'ocm' in lab, 'line': self.cmn(b, lab)[0]['line'],
                       'spread_pct': _spread_pct(list(nodes.values()))}
                if m:
                    own = REGION_NODE[row['region']]
                    others = [v for n, v in nodes.items() if n != own]
                    row.update(own_node=own, own=nodes[own], other_lo=min(others), other_hi=max(others),
                               other_mean=sum(others) / 4, excess=nodes[own] - sum(others) / 4,
                               excess_per_line=(nodes[own] - sum(others) / 4) / REGION_LINES,
                               own_over_largest_other=nodes[own] / max(others),
                               intended_ok=row['top_node'] == own)
                    intended_n += 1
                    intended_ok += row['intended_ok']
                    from_counts.setdefault(row['region'], set()).add(row['top_node'])
                rows.append(row)
            # all-five rows: baseline from the one-region commands of the same program
            for row in rows:
                if row['region'] is not None or not row['ocm']:
                    continue
                base = statistics.median(r['other_mean'] for r in rows
                                         if r['region'] is not None and r['program'] == row['program'])
                net = [v - base for v in row['counts']]
                low = min(range(5), key=lambda i: net[i])
                row.update(baseline=base, net=net, net_per_line=[v / REGION_LINES for v in net],
                           net_per_line_lo=min(net) / REGION_LINES,
                           net_per_line_hi=max(net) / REGION_LINES,
                           lowest_over_mean_others=net[low] / (sum(v for i, v in enumerate(net)
                                                                   if i != low) / 4),
                           net_sum=sum(net))
            self.mesh_requests[b] = rows
        for b in BOOTS:
            for row in self.mesh_requests[b]:
                row['timed'] = self._timed_units(b, row['label'])
                if 'net_sum' in row and row['timed']:
                    row['net_per_timed'] = row['net_sum'] / row['timed']
                elif 'excess' in row and row['timed']:
                    row['excess_per_timed'] = row['excess'] / row['timed']
        self.mesh_summary.update(
            intended_ok=intended_ok, intended_n=intended_n,
            region_nodes_from_counts=[sorted(from_counts[r])[0] if len(from_counts.get(r, ())) == 1
                                      else None for r in range(5)])
        # idle control (boot F1 only: the core latency program on 4 KiB)
        self.mesh_control = {'F1': None, 'F2': None}
        nodes = self.cmn_nodes('F1', 'control-cpu2')
        if nodes:
            self.mesh_control['F1'] = {
                'boot': 'F1', 'src': 'cmn-counts.csv', 'label': 'control-cpu2', 'nodes': nodes,
                'counts': [nodes[n] for n in REGION_NODE], 'lo': min(nodes.values()),
                'hi': max(nodes.values()),
                'lifetime_ms': self.cmn('F1', 'control-cpu2', 'child_elapsed_ns')[0]['count'] / 1e6,
                'what': 'the core latency program on a 4 KiB DRAM buffer, not a CME command'}
        # G7: the flushed 8 MiB DRAM command on both boots
        g7 = {}
        for b in BOOTS:
            row = self.mesh_row(b, 'cme-dram-flushed-8M-cpu2')
            lines = 8 * MIB // LINE
            g7[b] = {'boot': b, 'src': 'cmn-counts.csv', 'label': row['label'], 'sum': row['sum'],
                     'lines': lines, 'per_line': row['sum'] / lines, 'lifetime_ms': row['lifetime_ms'],
                     'node_lo': min(row['counts']), 'node_hi': max(row['counts']),
                     'node_spread_pct': row['spread_pct'], 'mc_reqs_local': row['mc_reqs_local'],
                     'cache_miss': row['cache_miss']}
        g7['f1_over_f2'] = g7['F1']['sum'] / g7['F2']['sum']
        self.mesh_g7 = g7

    def _timed_units(self, boot, label):
        """Timed loads (latency) or timed lines (bandwidth) of the command behind a mesh label."""
        m = re.fullmatch(r'cme-ocm-(region\d|all5|all5-dense)-cpu2', label)
        if m:
            e = self._lat[boot]['cme-latency-ocm-%s.csv' % m.group(1)][0]
            return sum(x['loads'] for s in e['order'] for x in e['sizes'][s]['reps'])
        m = re.fullmatch(r'cme-ocm-(read|write)-(region\d|all5)', label)
        if m:
            name = 'write' if m.group(1) == 'write' else m.group(2)
            r = self._bw[boot]['cme-bandwidth-ocm-%s.csv' % name][0]
            return r['n_reps'] * r['passes'] * r['size'] // LINE
        if label == 'cme-dram-flushed-8M-cpu2':
            e = self._lat[boot]['cme-latency-dram-flushed.csv'][0]
            return sum(x['loads'] for s in e['order'] for x in e['sizes'][s]['reps'])
        return None

    def mesh_row(self, boot, label):
        for r in self.mesh_requests[boot]:
            if r['label'] == label:
                return r
        return None

    # ------------------------------------------------------------------ tables that cross sections
    def _build_cross(self):
        # G6: core cycles minus CME cycles per counting window
        gap = []
        for b in BOOTS:
            g = {'ocm-64': [], 'ocm-320': [], 'cme-call': []}
            for name in self._cme_lat_files(b):
                blk = self._lat[b][name][0]
                for x in blk['call']['reps']:
                    g['cme-call'].append((x['cycles'] - x['cme_cycles']) * x['loads'])
                for s in blk['order']:
                    for x in blk['sizes'][s]['reps']:
                        if x['loads'] in (64, 320):
                            g['ocm-%d' % x['loads']].append((x['cycles'] - x['cme_cycles']) * x['loads'])
            lab = {'ocm-64': 'OCM passes of 64 loads, one call per counting window',
                   'ocm-320': 'OCM passes of 320 loads, one call per counting window',
                   'cme-call': 'cme-call rows, 64 calls per counting window'}
            src = {'ocm-64': 'cme-latency-ocm-region0..4.csv', 'ocm-320': 'cme-latency-ocm-all5.csv',
                   'cme-call': 'cme-latency-*.csv (12 files)'}
            for k in ('ocm-64', 'ocm-320', 'cme-call'):
                v = sorted(g[k])
                gap.append({'boot': b, 'key': k, 'label': lab[k], 'src': src[k], 'n': len(v),
                            'calls_per_window': 64 if k == 'cme-call' else 1,
                            'lo': v[0], 'hi': v[-1], 'median': statistics.median(v),
                            'lo_ns': v[0] / self.cycles_per_ns, 'hi_ns': v[-1] / self.cycles_per_ns,
                            'median_ns': statistics.median(v) / self.cycles_per_ns})
        self.cycle_gap = gap

        # G1: what a chain load costs by where the line comes from
        self.g1 = {}
        for b in BOOTS:
            ch = lambda s, k=None: self.chain_row(b, s, k)
            dense = self.ocm_lat[b][6]
            l1 = [r for r in self.chain[b] if r['size'] <= 64 * KIB]
            spec = [
                ('l1', 'CME L1', '4 KiB to 64 KiB, walked many times', l1),
                ('cluster', 'Inside the cluster', '256 KiB, walked many times', [ch(256 * KIB)]),
                ('outside-1m', 'Outside the cluster', '1 MiB, walked once', [ch(MIB)]),
                ('outside-3m', 'Outside the cluster', '3 MiB, walked once', [ch(3 * MIB)]),
                ('ocm', 'OCM', 'all five regions, chain over every line, every line flushed first', [dense]),
                ('dram', 'DRAM model', '8 MiB, every line flushed first',
                 [ch(8 * MIB, 'every line flushed first')]),
                # No counter separates the SLC from the DRAM model, so this row names what the counters show.
                ('dram-32m', 'Outside the cluster', '32 MiB, walked once', [ch(32 * MIB)]),
            ]
            rows = []
            for key, where, cond, rr in spec:
                rows.append({
                    'boot': b, 'key': key, 'where': where, 'conditions': cond, 'src': rr[0]['src'],
                    'n_rows': len(rr),
                    'bracket_lo': min(r['best'] for r in rr), 'bracket_hi': max(r['best'] for r in rr),
                    'span_lo': min(r['span'] for r in rr), 'span_hi': max(r['span'] for r in rr),
                    'above_rt_lo': min(r['above_rt'] for r in rr),
                    'above_rt_hi': max(r['above_rt'] for r in rr),
                    'outer_lo': min(r['outer'] for r in rr), 'outer_hi': max(r['outer'] for r in rr),
                    'inner_lo': min(r['inner'] for r in rr), 'inner_hi': max(r['inner'] for r in rr),
                    'hwprf_lo': min(r['hwprf'] for r in rr), 'hwprf_hi': max(r['hwprf'] for r in rr),
                    'demand_only': all(r['demand_only'] for r in rr),
                    'backing': rr[0]['backing']})
            self.g1[b] = rows
        g = {r['key']: r for r in self.g1['F2']}
        self.g1_notes = {
            'ocm_minus_outside_lo': g['ocm']['bracket_lo'] - g['outside-3m']['bracket_lo'],
            'ocm_minus_outside_hi': g['ocm']['bracket_lo'] - g['outside-1m']['bracket_lo'],
            'dram_minus_ocm': g['dram']['bracket_lo'] - g['ocm']['bracket_lo']}

        # G8: repeatability
        rep = {}
        for b in BOOTS:
            S = self.baseline_summary[b]
            rd1 = self._bwget(b, 'sweep', 'read', 16 * KIB)
            rd2 = self._bwget(b, 'l1-looped', 'read', 16 * KIB)
            w1 = self._bwget(b, 'l1-looped', 'write', 4 * KIB)
            w2 = self._bwget(b, 'call-cost', 'write', 4 * KIB)
            lo, hi = sorted((w1['ns_per_pass_span'], w2['ns_per_pass_span']))
            rep[b] = {
                'boot': b, 'rt_files': S['n_files'], 'rt_lo': S['rt_best_lo'], 'rt_hi': S['rt_best_hi'],
                'call_lo': S['call_best_lo'], 'call_hi': S['call_best_hi'],
                'sweeps_n': self.l3_repeat[b]['n'],
                'sweeps_within_1pct': self.l3_repeat[b]['n_within_1pct'],
                'sweeps_worst_pct': self.l3_repeat[b]['worst_pct'],
                'sweeps_worst_label': self.l3_repeat[b]['worst_label'],
                'read16_sweep': rd1['best'], 'read16_l1': rd2['best'],
                'read16_diff_pct': 100.0 * abs(rd2['best'] - rd1['best']) / min(rd1['best'], rd2['best']),
                'write4_span_l1': w1['ns_per_pass_span'], 'write4_span_callcost': w2['ns_per_pass_span'],
                'write4_span_diff_pct': 100.0 * (hi - lo) / lo,
                'write4_bracket_l1': w1['ns_per_pass'], 'write4_bracket_callcost': w2['ns_per_pass']}
        rep['all'] = {'rt_files': self.baseline_summary['all']['n_files'],
                      'rt_lo': self.baseline_summary['all']['rt_best_lo'],
                      'rt_hi': self.baseline_summary['all']['rt_best_hi'],
                      'call_lo': self.baseline_summary['all']['call_best_lo'],
                      'call_hi': self.baseline_summary['all']['call_best_hi'],
                      'boots_repeated': 0}
        self.repeatability = rep

        # G20: numbers to quote
        q = {'rt_ns': self.rt_ns, 'rt_files': self.baseline_summary['all']['n_files']}
        f2 = self.chain['F2']
        q['l1_f2'] = _rng(r['best'] for r in f2 if r['size'] <= 64 * KIB)
        q['cluster_f2'] = _rng(r['best'] for r in f2 if 96 * KIB <= r['size'] <= 384 * KIB)
        q['outside_f2'] = _rng(r['best'] for r in f2 if MIB <= r['size'] <= 3 * MIB)
        o = self.ocm_lat['F2']
        q['ocm_near_f2_span'] = _rng(r['best_span'] for r in o[:5] if r['steps'] == 1)
        q['ocm_far_f2_span'] = _rng(r['best_span'] for r in o[:5] if r['steps'] == 3)
        q['ocm_all5_f2_span'] = o[6]['best_span']
        q['dram_f2'] = self.chain_row('F2', 8 * MIB, 'every line flushed first')['best']
        for b in BOOTS:
            q['l1_read_single_' + b] = (self.limits[b]['read_gbps_lo'], self.limits[b]['read_gbps_hi'])
        wr = [r['best'] for b in BOOTS for g_ in ('l1-single', 'sweep-single')
              for r in self.bw_table(g_, b, 'write')]
        q['write_single'] = _rng(wr)
        sw = lambda b, lo, hi: _rng(r['best'] for r in self.bw_table('sweep', b, 'read')
                                    if lo <= r['size'] <= hi)
        q['read_cluster_f1'] = sw('F1', 96 * KIB, 256 * KIB)
        q['read_cluster_f2'] = sw('F2', 96 * KIB, 256 * KIB)
        q['read_large_f1'] = sw('F1', MIB, 32 * MIB)
        q['read_32m_f2'] = self._bwget('F2', 'sweep', 'read', 32 * MIB)['best']
        q['read_32m_f1'] = self._bwget('F1', 'sweep', 'read', 32 * MIB)['best']
        q['write_large'] = _rng(r['best'] for b in BOOTS for r in self.bw_table('sweep', b, 'write')
                                if r['size'] >= MIB)
        for b in BOOTS:
            q['ocm_read_' + b] = _rng(r['best'] for r in self.ocm_bw[b][:5])
            q['ocm_write_' + b] = self.ocm_bw[b][6]['best']
        self.quote = q


@functools.lru_cache(maxsize=1)
def load():
    """Parse every file once and return the Data object D (cached)."""
    return Data()


# Name of every derived table on D -> one line. Keys and units: API.md.
TABLES = {
    'platform': 'raw platform lines (timer, SME vector length, cache sizes, OCM ranges, mesh map) with line numbers',
    'dmesg_ocm_maps': 'per boot: the OCM mapping lines of dmesg.txt (count, 4 KiB entries, bases)',
    'commands': 'per boot: command counts, CME line range, uptime, failures, CPU 3 lines (log.txt)',
    'integrity': 'per boot: SHA-256 check, rep row counts, counter coverage, mesh counter coverage',
    'baseline': '24 rows: round-trip baseline and cme-call rows of every CME latency file',
    'baseline_summary': 'ranges of the baseline and cme-call rows per boot and over both boots',
    'clock': 'per boot: cycles per ns over rep rows of 8,192 loads or more, core and CME counter',
    'chain': 'per boot: CME chain load by footprint (23 sweep rows and the flushed 8 MiB row)',
    'core_chain': 'the core twin rows on boot F1 (control, small, large, flushed)',
    'chain_pairs': 'boot F1 against boot F2 per footprint, with the core on boot F1 beside them',
    'chain_steps': 'G10: chain kinds per footprint, the 384 KiB to 512 KiB step, flushed against walked once',
    'refills_per_line': 'G5: inner refills per line of the chain in every timed rep',
    'refills_per_line_summary': 'G5: ranges on boot F2 at 4 KiB to 64 KiB',
    'bracket_minus_span': 'per boot: bracket minus span ns per load over the footprint rows',
    'address_order': 'the one permitted earlier-boot row (address-order chain, 8 MiB)',
    'chain_l3': 'per boot: the L3-event rows with hit share, miss without outer refill, and the plain twin',
    'l3_reps': 'per boot: every rep row of the L3-event files',
    'l3_repeat': 'per boot: how well the L3-event rows repeat the timing of the plain rows',
    'l3_checks': 'per boot: counter checks of the L3-event rows',
    'l3_fits': 'least-squares fits of the boot F2 L3-event rep rows (hypothesis only)',
    'l3_line': 'straight line of ns against hits per load, 96 KiB to 384 KiB, boot F2',
    'l3_loo': 'fit C1 with one footprint left out: coefficient ranges',
    'l3_outer_cost': 'cost of one outer refill implied by fit C1, by footprint (est.)',
    'l3_large': 'the 512 KiB to 3 MiB correlation and the rows above 3 MiB',
    'bw_rows': 'every DRAM-backed CME bandwidth row of both boots (134 rows)',
    'core_bw': 'the core bandwidth rows on boot F1',
    'l1_forms': 'time per pass at 4, 8, 16, 24 KiB for the L1 forms, bracket and span',
    'l1_fits': '24 straight-line fits of time per pass with the plan-rule verdict',
    'l1_diffs': 'per point: looped read minus no-fold read, DSB ST write minus looped write',
    'looped_vs_single': 'looped form against single-call form, 4 KiB to 256 KiB',
    'call_cost': 'the call-cost rows as ns per call (bracket, span, outside-span)',
    'forms64': 'the 64-byte-per-instruction rows beside the 256-byte rows',
    'core_vs_cme_bw': 'core against CME at equal footprint on boot F1 (looped and single-call)',
    'bw_f1_vs_f2': 'boot F2 over boot F1 for every CME bandwidth row',
    'store_vs_load': 'single-call read span rate over write span rate at 16 KiB',
    'limits': 'G2: single-call L1 rates as bytes and vectors per cycle',
    'outside_span': 'outside-span ns per call by situation (alone, after another call, first rep, later reps)',
    'outside_check': 'per boot: a lone call against 64 calls that follow each other (est. per later call)',
    'lines_in_flight': 'G4: chain load time over time per 64 B line of the read row (est.)',
    'ocm_lat': 'per boot: 7 OCM chain rows (5 regions, all five in two shapes)',
    'ocm_core': 'the core OCM twins on boot F1',
    'ocm_pairs': 'OCM chain rows: boot F1, boot F2 and the core side by side',
    'ocm_stats': 'per boot: OCM order by mesh steps, spreads, the read-refill line on boot F1',
    'ocm_bw': 'per boot: 7 OCM bandwidth rows with per-pass and per-kernel-call accounting',
    'ocm_bw_core': 'the core OCM bandwidth twins on boot F1',
    'ocm_bw_pairs': 'OCM bandwidth: boot F1, boot F2 and the core side by side',
    'mesh_cells': 'every device cell of the mesh map',
    'mesh_layout': 'G9: region, node id, x, y, HN-S index, crosspoint, steps from crosspoint (2,3)',
    'mesh_rnf_steps': 'steps from each cluster port to the five home nodes',
    'mesh_summary': 'grid size, device counts, intended-node check',
    'mesh_requests': 'per boot: requests per home node per label (15 CME labels)',
    'mesh_control': 'the idle control row (boot F1 only)',
    'mesh_g7': 'G7: mesh requests of the flushed 8 MiB command on both boots',
    'cycle_gap': 'G6: core cycles minus CME cycles per counting window',
    'g1': 'G1: what a chain load costs by where the line comes from, per boot',
    'g1_notes': 'G1: differences between the OCM row and the DRAM-backed rows on boot F2',
    'repeatability': 'G8: the three kinds of repeat',
    'quote': 'G20: the numbers to quote',
}


# ----------------------------------------------------------------------------- self-test

def selftest(verbose=False):
    """Assert values against critic.md (its corrected numbers and the G20 list)."""
    D = load()
    n = [0]

    def near(name, got, want, tol=0.0006):
        n[0] += 1
        assert got is not None and abs(got - want) <= tol, '%s: got %r, want %r' % (name, got, want)
        if verbose:
            print('ok', name, got)

    def eq(name, got, want):
        n[0] += 1
        assert got == want, '%s: got %r, want %r' % (name, got, want)
        if verbose:
            print('ok', name, got)

    K, M = KIB, MIB
    eq('every named table exists', [t for t in TABLES if not hasattr(D, t)], [])
    # section 1, item 1: the clock ratio
    for b, lo, hi in (('F1', 1.9999, 2.0019), ('F2', 1.9994, 2.0016)):
        eq('clock rows ' + b, D.clock[b]['n_rows'], 156)
        near('clock lo ' + b, D.clock[b]['core_lo'], lo, 0.00006)
        near('clock hi ' + b, D.clock[b]['core_hi'], hi, 0.00006)
    eq('cycles per ns', D.cycles_per_ns, 2.0)
    # item 3: cache size lines
    eq('cache lines', [c['line'] for c in D.platform['caches']], [101, 102, 103, 104])
    eq('cache sizes', [c['size'] for c in D.platform['caches']], ['32K', '32K', '128K', '256K'])
    eq('timer line', D.platform['timer_F1']['line'], 76)
    eq('SME lines', (D.platform['sme_vl_min_F1']['line'], D.platform['sme_vl_default_F1']['line']),
       (154, 156))
    eq('SME vector length', D.platform['sme_vl_max_F1']['value'], 64)
    # item 4: the plan-rule percentages of the 24 fits
    want = {('F1', 'looped', 'read'): (0.60, 0.44), ('F2', 'looped', 'read'): (3.16, 1.17),
            ('F1', 'looped', 'write'): (18.37, 33.68), ('F2', 'looped', 'write'): (17.78, 35.88),
            ('F1', 'single-call', 'read'): (19.09, 18.83), ('F2', 'single-call', 'read'): (17.61, 17.77),
            ('F1', 'single-call', 'write'): (1.09, 1.12), ('F2', 'single-call', 'write'): (0.81, 0.84),
            ('F1', 'looped, no fold', 'read'): (1.52, 2.13),
            ('F2', 'looped, no fold', 'read'): (1.14, 0.20),
            ('F1', 'looped, DSB ST', 'write'): (5.02, 8.19),
            ('F2', 'looped, DSB ST', 'write'): (5.10, 8.19)}
    for (b, form, k), (wb, ws) in want.items():
        near('fit %% %s %s %s bracket' % (b, form, k), D.l1_fit(b, form, k, 'bracket')['max_res_pct'], wb, 0.006)
        near('fit %% %s %s %s span' % (b, form, k), D.l1_fit(b, form, k, 'span')['max_res_pct'], ws, 0.006)
    eq('fits void', sum(1 for f in D.l1_fits if f['verdict'] == 'void'), 14)
    # item 5: largest absolute residual and its own size
    f = D.l1_fit('F1', 'looped', 'write', 'bracket')
    near('F1 looped write residual ns', f['max_res_ns'], 27.89, 0.006)
    eq('F1 looped write residual size', f['max_res_size'], 8 * K)
    near('F1 looped read intercept', D.l1_fit('F1', 'looped', 'read', 'bracket')['intercept_ns'], 186.23, 0.006)
    near('F1 looped read span rate', D.l1_fit('F1', 'looped', 'read', 'span')['rate_gbps'], 134.67, 0.06)
    near('F2 looped read span rate', D.l1_fit('F2', 'looped', 'read', 'span')['rate_gbps'], 132.85, 0.06)
    # item 6: the L3 fits (hypothesis material)
    A2, C1 = D.l3_fits['A2'], D.l3_fits['C1']
    for name, got, w in (('A2 hit', A2['hit'], 29.833), ('A2 mms', A2['mms'], 37.422),
                         ('A2 outer', A2['outer'], 44.432), ('A2 rms', A2['rms'], 0.089),
                         ('C1 hit', C1['hit'], 29.841), ('C1 mms', C1['mms'], 37.407),
                         ('C1 outer', C1['outer'], 44.106), ('C1 rms', C1['rms'], 0.190)):
        near(name, got, w)
    # item 8: single-call later reps
    eq('single-call later reps lo', round(min(D.outside(b, 'single-later-read')['lo'] for b in BOOTS), 1), 280.0)
    eq('single-call later reps hi', round(max(D.outside(b, 'single-later-read')['hi'] for b in BOOTS), 1), 300.9)
    # item 9: the F2 curve from 1 to 4 MiB
    eq('F2 1 to 3 MiB', D.quote['outside_f2'], (42.125, 43.666))
    eq('F2 4 MiB', D.chain_row('F2', 4 * M)['best'], 47.328)
    # item 10: hits per load at 384 KiB on F2
    h = [x['hit'] for x in D.l3_reps['F2'] if x['size'] == 384 * K]
    eq('F2 384 KiB hit', (min(h), max(h)), (0.6318, 0.6375))
    # item 12: bracket_overhead_ns
    eq('overhead F1', (D.baseline_summary['F1']['overhead_n_common'], D.baseline_summary['F1']['overhead_other']), (12, []))
    eq('overhead F2', (D.baseline_summary['F2']['overhead_n_common'], D.baseline_summary['F2']['overhead_other']),
       (11, [('cme-latency-ocm-region1.csv', 40.0)]))
    # item 13 (W3): the 1 KiB read call on F2
    r = [c for c in D.call_cost if c['boot'] == 'F2' and c['kernel'] == 'read'][0]
    for got, w in zip(r['outside_reps'], (87.602, 88.047, 83.069)):
        near('F2 1 KiB read outside', got, w, 0.002)
    # item 14: looped outside-span time over the sweep
    for b, a, z, c, d in (('F1', 76.0, 106.2, 118.5, 357.8), ('F2', 75.8, 105.6, 120.5, 398.0)):
        s, l = D.outside(b, 'looped-sweep-small'), D.outside(b, 'looped-sweep-large')
        eq('sweep outside ' + b, (round(s['lo'], 1), round(s['hi'], 1), round(l['lo'], 1), round(l['hi'], 1)),
           (a, z, c, d))
    # scope notes
    S = D.baseline_summary['all']
    eq('cme-call best', (S['call_best_lo'], S['call_best_hi']), (124.516, 125.609))
    eq('cme-call span', (S['call_span_n'], S['call_span_n_mode'], S['call_span_mode'], S['call_span_hi']),
       (72, 68, 61.0, 61.25))
    eq('rt cme cycles', (S['rt_cme_cycles_lo'], S['rt_cme_cycles_hi']), (42.0039, 42.0068))
    eq('rt all files', (S['n_files'], S['rt_best_lo'], S['rt_best_hi']), (24, 21.005, 21.005))
    # region against home node (G9)
    eq('HN-S index', [l['hns_index'] for l in D.mesh_layout], [0, 3, 1, 4, 2])
    eq('positions', [(l['x'], l['y']) for l in D.mesh_layout], [(1, 3), (2, 4), (3, 3), (4, 4), (5, 3)])
    eq('steps', [l['steps'] for l in D.mesh_layout], [1, 1, 1, 3, 3])
    eq('nodes from counts', D.mesh_summary['region_nodes_from_counts'], list(REGION_NODE))
    eq('intended node', (D.mesh_summary['intended_ok'], D.mesh_summary['intended_n']), (20, 20))
    eq('one RN-F fits', D.mesh_summary['rnf_cells_matching_1_1_1_3_3'], [(2, 3)])
    eq('mesh map lines', (D.mesh_summary['map_first_line'], D.mesh_summary['map_last_line']), (489, 551))
    # section 2: checksums, log lines
    eq('sha F1', (D.verify_sha('F1')['ok'], D.verify_sha('F1')['total']), (88, 88))
    eq('sha F2', (D.verify_sha('F2')['ok'], D.verify_sha('F2')['total']), (30, 30))
    for b, a, z in (('F1', 85, 156), ('F2', 4, 75)):
        c = D.commands[b]
        eq('commands ' + b, (c['n_cme'], c['n_cme_cmn'], c['cme_first_line'], c['cme_last_line'], c['failed']),
           (70, 15, a, z, 0))
    eq('same commands', D.commands['same_cme_commands'], True)
    eq('F1 commands', D.commands['F1']['n_commands'], 137)
    eq('log line of the small sweep', D.log_lines('F1', 'cme-latency-dram-small.csv'), [85])
    eq('perf_cov rows', [(D.integrity[b]['latency_rep_rows'], D.integrity[b]['perf_cov_min']) for b in BOOTS],
       [(234, 1.0), (234, 1.0)])
    # W2: load against store at 16 KiB
    near('W2 F1', D.store_vs_load[0]['ratio'], 2.31, 0.006)
    near('W2 F2', D.store_vs_load[1]['ratio'], 2.33, 0.006)
    # W5: OCM bandwidth per kernel call
    for b, a, z, c, d in (('F1', 135.5, 155.2, 87.8, 94.3), ('F2', 136.4, 154.1, 89.9, 93.4)):
        rd, wr = D.ocm_bw[b][5], D.ocm_bw[b][6]
        eq('OCM all-five read per call ' + b, (round(rd['outside_lo'], 1), round(rd['outside_hi'], 1)), (a, z))
        eq('OCM write per call ' + b, (round(wr['outside_lo'], 1), round(wr['outside_hi'], 1)), (c, d))
        eq('OCM calls ' + b, (rd['calls_per_rep'], wr['calls_per_rep']), (5, 40))
    one = [v for b in BOOTS for r in D.ocm_bw[b][:5] for v in r['outside_reps']]
    eq('OCM one-region read per call', (round(min(one)), round(max(one))), (328, 485))
    # W6: bracket minus span over all rep rows
    eq('W6', (D.bracket_minus_span['F2']['all_lo'], D.bracket_minus_span['F2']['all_hi']), (0.0, 0.041))
    # smaller defects: the all-node events on F2
    eq('F2 all-node events', (D.mesh_g7['F2']['mc_reqs_local'], D.mesh_g7['F2']['cache_miss']), (2490045, 1687164))
    # G1
    g = {r['key']: r for r in D.g1['F2']}
    eq('G1 l1', (g['l1']['bracket_lo'], g['l1']['bracket_hi'], g['l1']['span_lo'], g['l1']['span_hi']),
       (21.015, 21.240, 21.011, 21.236))
    near('G1 l1 above lo', g['l1']['above_rt_lo'], 0.010)
    near('G1 l1 above hi', g['l1']['above_rt_hi'], 0.235)
    for key, br, sp, ab, ou in (('cluster', 32.779, 32.775, 11.774, 0.0030),
                                ('outside-1m', 42.125, 42.107, 21.120, 0.8134),
                                ('outside-3m', 43.666, 43.659, 22.661, 0.9311),
                                ('ocm', 45.546, 45.532, 24.541, 1.0),
                                ('dram', 71.714, 71.712, 50.709, 1.0),
                                ('dram-32m', 71.068, 71.067, 50.063, 0.9953)):
        eq('G1 ' + key, (g[key]['bracket_lo'], g[key]['span_lo'], g[key]['outer_lo']), (br, sp, ou))
        near('G1 above ' + key, g[key]['above_rt_lo'], ab)
    near('G1 OCM minus 3 MiB', D.g1_notes['ocm_minus_outside_lo'], 1.9, 0.05)
    near('G1 OCM minus 1 MiB', D.g1_notes['ocm_minus_outside_hi'], 3.4, 0.05)
    near('G1 DRAM minus OCM', D.g1_notes['dram_minus_ocm'], 26.2, 0.05)
    # G2
    for b, a, z in (('F1', 54.45, 65.82), ('F2', 55.40, 66.18)):
        near('G2 read lo ' + b, D.limits[b]['read_bpc_lo'], a, 0.006)
        near('G2 read hi ' + b, D.limits[b]['read_bpc_hi'], z, 0.006)
    lim = [D.limits[b] for b in BOOTS]
    eq('G2 write B per cycle', (round(min(l['write_bpc_lo'] for l in lim), 2), round(max(l['write_bpc_hi'] for l in lim), 2)),
       (25.72, 26.86))
    eq('G2 vectors per cycle', (round(min(l['read_vec_per_cycle_lo'] for l in lim), 2),
                                round(max(l['read_vec_per_cycle_hi'] for l in lim), 2)), (0.85, 1.03))
    eq('G2 cycles per iteration', (round(min(l['read_cycles_per_kib_lo'] for l in lim), 1),
                                   round(max(l['read_cycles_per_kib_hi'] for l in lim), 1)), (15.5, 18.8))
    eq('G2 cycles per vector', (round(min(l['write_cycles_per_vec_lo'] for l in lim), 2),
                                round(max(l['write_cycles_per_vec_hi'] for l in lim), 2)), (2.38, 2.49))
    # G3
    cv = {(r['kernel'], r['size']): r for r in D.core_vs_cme_bw}
    eq('G3 read', (cv[('read', 16 * K)]['core'], cv[('read', 16 * K)]['cme_single']), (56.085, 120.132))
    near('G3 read ratio', cv[('read', 16 * K)]['single_over_core'], 2.142)
    eq('G3 write', (cv[('write', 16 * K)]['core'], cv[('write', 16 * K)]['cme_single']), (30.608, 52.098))
    near('G3 write ratio', cv[('write', 16 * K)]['single_over_core'], 1.702)
    # G4
    for r, w in zip(D.lines_in_flight, (33.2, 32.4, 40.3, 21.4, 22.0, 19.7)):
        near('G4 %s %s' % (r['boot'], r['label']), r['ratio_est'], w, 0.06)
    for r, w in zip([r for r in D.lines_in_flight if r['boot'] == 'F2'], (7.7, 11.2, 13.8)):
        near('G4 above baseline ' + r['label'], r['ratio_above_rt_est'], w, 0.06)
    # G5
    s = D.refills_per_line_summary
    eq('G5 rep rows', s['n_rep_rows'], 21)
    eq('G5 refills per line', (round(s['per_line_lo'], 2), round(s['per_line_hi'], 2)), (0.99, 1.02))
    eq('G5 ns per refill', (round(s['l1_ns_per_refill_lo'], 1), round(s['l1_ns_per_refill_hi'], 1)), (10.0, 15.1))
    eq('G5 cluster ns per refill', (round(s['cluster_ns_per_refill_lo'], 1), round(s['cluster_ns_per_refill_hi'], 1)),
       (11.8, 15.2))
    # G6
    cg = {(r['boot'], r['key']): r for r in D.cycle_gap}
    for b, k, lo, med, hi, cnt in (('F1', 'ocm-64', 554, 591, 663, 35), ('F2', 'ocm-64', 556, 583, 706, 35),
                                   ('F1', 'ocm-320', 566, None, 649, 7), ('F2', 'ocm-320', 586, None, 674, 7),
                                   ('F1', 'cme-call', 571, 599, 632, 36), ('F2', 'cme-call', 567, 599, 658, 36)):
        r = cg[(b, k)]
        eq('G6 n %s %s' % (b, k), r['n'], cnt)
        near('G6 lo %s %s' % (b, k), r['lo'], lo, 0.6)
        near('G6 hi %s %s' % (b, k), r['hi'], hi, 0.6)
        if med:
            near('G6 median %s %s' % (b, k), r['median'], med, 1.5)
    near('G6 later call est.', D.outside_check['F1']['later_call_est_ns'], 60.0, 0.06)
    # G7
    g7 = D.mesh_g7
    eq('G7 sums', (g7['F1']['sum'], g7['F2']['sum']), (7061170, 4525175))
    near('G7 per line F1', g7['F1']['per_line'], 53.87, 0.006)
    near('G7 per line F2', g7['F2']['per_line'], 34.52, 0.006)
    near('G7 ratio', g7['f1_over_f2'], 1.56, 0.006)
    near('G7 lifetime F1', g7['F1']['lifetime_ms'], 70.428)
    near('G7 lifetime F2', g7['F2']['lifetime_ms'], 102.733)
    # G8
    R = D.repeatability
    eq('G8 sweeps', (R['F2']['sweeps_within_1pct'], R['F1']['sweeps_within_1pct'], R['F1']['sweeps_n']), (23, 20, 23))
    near('G8 worst', R['F1']['sweeps_worst_pct'], 5.6, 0.06)
    eq('G8 worst size', D.l3_repeat['F1']['worst_size'], 16 * K)
    near('G8 read F1', R['F1']['read16_diff_pct'], 1.6, 0.06)
    near('G8 read F2', R['F2']['read16_diff_pct'], 5.3, 0.06)
    near('G8 write span F1', R['F1']['write4_span_diff_pct'], 12.0, 0.6)
    # G10
    st = D.chain_steps
    eq('G10 no shared footprint', st['sizes_with_both_sweep_kinds'], [])
    eq('G10 kinds meet', (st['largest_walked_many'], st['smallest_walked_once']), (384 * K, 512 * K))
    near('G10 F1 step', st['steps'][0]['step_ns'], -10.594)
    # G20
    q = D.quote
    eq('G20 L1', q['l1_f2'], (21.015, 21.240))
    eq('G20 cluster', q['cluster_f2'], (32.779, 35.979))
    eq('G20 OCM near', q['ocm_near_f2_span'], (43.453, 44.391))
    eq('G20 OCM far', q['ocm_far_f2_span'], (47.266, 47.734))
    eq('G20 OCM all five', q['ocm_all5_f2_span'], 45.532)
    eq('G20 DRAM', q['dram_f2'], 71.714)
    eq('G20 L1 read F1', tuple(round(v, 1) for v in q['l1_read_single_F1']), (108.9, 131.6))
    eq('G20 L1 read F2', tuple(round(v, 1) for v in q['l1_read_single_F2']), (110.8, 132.4))
    eq('G20 write', tuple(round(v, 1) for v in q['write_single']), (51.4, 53.7))
    eq('G20 read 96 to 256 KiB F1', tuple(round(v, 1) for v in q['read_cluster_f1']), (41.4, 43.7))
    eq('G20 read 1 to 32 MiB F1', tuple(round(v, 1) for v in q['read_large_f1']), (36.6, 36.9))
    eq('G20 read 32 MiB F2', round(q['read_32m_f2'], 1), 17.7)
    eq('G20 OCM read F1', tuple(round(v, 1) for v in q['ocm_read_F1']), (33.6, 39.8))
    eq('G20 OCM read F2', tuple(round(v, 1) for v in q['ocm_read_F2']), (27.7, 33.9))
    eq('G20 OCM write', (round(q['ocm_write_F1'], 1), round(q['ocm_write_F2'], 1)), (30.7, 31.0))
    # the one earlier-boot row
    eq('address order', (D.address_order['best'], D.address_order['kind']), (21.417, 'address order'))
    print('selftest OK: %d checks' % n[0])
    return n[0]


if __name__ == '__main__':
    import sys
    selftest(verbose='-v' in sys.argv)
