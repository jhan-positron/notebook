"""Data layer of the page "Asimov C1-Nano Memory Performance".

Reads the raw result files of six boots (F1, E, B, C, D, R3) and exposes them
through load(), which returns one object D. D offers generic row access for
the latency, bandwidth and mesh-counter files of any boot, and named derived
tables. Every name and key is documented in c1nano_page/API.md, Part 1.

Standard library only. Run the self-test from the project folder:
    python3 -m c1nano_page.data
"""
import functools
import hashlib
import itertools
import math
import os
import re
import statistics

PKG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG)
BOOTS = ('F1', 'E', 'B', 'C', 'D', 'R3')
FOLDER = {'F1': 'membench-jibin-011', 'E': 'membench-jibin-010', 'B': 'membench-jibin-006',
          'C': 'membench-jibin-007', 'D': 'membench-jibin-008', 'R3': 'membench-jibin-004'}
SUBDIR = {'F1': 'bootF1', 'E': 'bootE', 'B': 'bootB', 'C': 'bootC', 'D': 'bootD',
          'R3': '19700101T000000Z'}
RUN = {b: os.path.join(ROOT, 'results', FOLDER[b]) for b in BOOTS}
BOOTDIR = {b: os.path.join(RUN[b], 'results', SUBDIR[b]) for b in BOOTS}
BOOT_NAME = {b: 'boot ' + b for b in BOOTS}
# Typed facts (operator's README of each run). load() checks them against log.txt and dmesg.txt
# where a file exists: the L3 register lines (0x70 = on, 0x0 = no data) and the dmesg map lines.
BOOT_COND = {
    'F1': {'l3': 'on', 'prefetchers': 'on', 'ocm_mapping': '4 KiB entries', 'script': 'run_all.sh'},
    'E': {'l3': 'on', 'prefetchers': 'on', 'ocm_mapping': '4 KiB entries', 'script': 'run_followup.sh'},
    'B': {'l3': 'no data', 'prefetchers': 'off', 'ocm_mapping': '4 KiB entries',
          'script': 'run_followup.sh'},
    'C': {'l3': 'no data', 'prefetchers': 'on', 'ocm_mapping': '64 KiB translations',
          'script': 'run_followup.sh'},
    'D': {'l3': 'no data', 'prefetchers': 'off', 'ocm_mapping': '64 KiB translations',
          'script': 'run_followup.sh'},
    'R3': {'l3': 'no data', 'prefetchers': 'on', 'ocm_mapping': '4 KiB entries',
           'script': 'run_all.sh'},
}
# Wording of critic.md section 9 for the first use of a boot in a section.
BOOT_FIRST_USE = {
    'F1': 'boot F1',
    'E': 'boot E (the firmware state of boot F1, another command set)',
    'B': 'boot B (prefetchers off, the L3 holds no data)',
    'C': 'boot C (prefetchers on, the L3 holds no data)',
    'D': 'boot D (as boot B, OCM mapped with 64 KiB translations)',
    'R3': "boot R3 (boot F1's commands, the L3 holds no data, an older build)",
}
KIB = 1024
MIB = 1024 * 1024
LINE = 64                       # bytes per cache line
CYCLES_PER_NS = 2.0             # core clock; load() checks it against the pooled ratio of boot F1
CLOCK_MIN_LOADS = 4096          # a timed latency row needs this many loads to enter the clock ratio
REGION_BYTES = 256 * KIB        # one OCM region
REGION_LINES = REGION_BYTES // LINE
# OCM region number -> home node id. Typed fact: lib_run.sh line 39 (HNS="88,160,216,288,344").
REGION_NODE = (88, 160, 216, 288, 344)
# CPU -> (x, y) of the mesh port of its cluster. Typed fact: operator's README of
# membench-jibin-004, line 36. load() checks that the mesh map has a cluster port at each place.
PORT_XY = {2: (2, 3), 4: (3, 2), 6: (4, 3), 8: (5, 2)}
FIFTH_PORT_XY = (1, 2)          # the cluster port that no test CPU uses
CPUS = (2, 4, 6, 8)
# Documented instruction throughput (SOG Tables 2-13, 2-14, 3-2). Typed facts, not measurements.
DOC = {
    'read_bytes_per_cycle': 32.0, 'write_bytes_per_cycle': 16.0,
    'read_gbps': 32.0 * CYCLES_PER_NS, 'write_gbps': 16.0 * CYCLES_PER_NS,
    'l1_hit_cycles': (2, 4), 'l2_hit_cycles': (10, 12),
    'source': 'Arm C1-Nano Core Software Optimization Guide 109590_0001_04, '
              'Tables 2-13, 2-14, 3-2 and section 3.1',
}

# CSV column name (without the _per_load or _per_line ending) -> short key of a rep row.
SHORT = {
    'ns_per_load': 'ns', 'cycles_per_load': 'cycles', 'cycles_per_line': 'cyc_line',
    'l1d_refill': 'l1', 'l2d_refill': 'l2', 'l3d_refill_rd': 'a2',
    'l1d_refill_hwprf': 'l1pf', 'l2d_refill_hwprf': 'l2pf', 'l2d_refill_l1dhwprf': 'l2byl1pf',
    'l2d_hit_rd': 'l2hit', 'l3d_access_rd': 'l3acc', 'l3d_hit_rd': 'l3hit',
    'l1d_tlb_refill': 'l1tlb', 'l2d_tlb_refill': 'l2tlb', 'dtlb_walk': 'walk',
    'dtlb_walk_block': 'walk_block', 'dtlb_walk_page': 'walk_page', 'perf_cov': 'perf_cov',
}
PF_KEYS = ('l1pf', 'l2pf', 'l2byl1pf')
COUNTER_KEYS = ('l1', 'l2', 'a2', 'l1pf', 'l2pf', 'l2byl1pf', 'l2hit', 'l3acc', 'l3hit',
                'l1tlb', 'l2tlb', 'walk', 'walk_block', 'walk_page')
KERNEL_LABEL = {
    'read': 'plain read', 'write': 'write', 'copy': 'copy',
    'read-pf4': 'software prefetch 4 lines ahead', 'read-pf8': 'software prefetch 8 lines ahead',
    'read-pf16': 'software prefetch 16 lines ahead', 'read-2s': 'two streams',
}
VAR_KERNELS = ('read', 'read-pf4', 'read-pf8', 'read-pf16', 'read-2s')
L1_SIZES = (4 * KIB, 8 * KIB, 16 * KIB, 24 * KIB)
WRITER_LISTS = ('2-4', '2-8', '2-3', '2-4-6-8', '2-3-4-5', '2-3-8-9')


# ----------------------------------------------------------------------------- small helpers

def _lines(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read().split('\n')


def _val(s):
    """Text field -> int, float, None for '-' or '', or the text itself."""
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


def _short(col):
    for end in ('_per_load', '_per_line'):
        if col.endswith(end) and col not in SHORT:
            col = col[:-len(end)]
    return SHORT.get(col, col)


def _cpu_list(text):
    """'2,4' -> [2, 4]; '2-9' -> [2, 3, ..., 9]."""
    out = []
    for part in text.split(','):
        if '-' in part:
            a, b = part.split('-')
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def spread_pct(vals, best):
    """The one spread of the page: (largest - smallest) / best row, in percent."""
    return 100.0 * (max(vals) - min(vals)) / best if best else 0.0


def _rng(vals):
    vals = list(vals)
    return (min(vals), max(vals))


def geomean(vals):
    vals = list(vals)
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def fmt_size(nbytes):
    """Footprint label: 4096 -> '4 KiB', 1572864 -> '1.5 MiB'."""
    if nbytes >= MIB:
        v, unit = nbytes / MIB, 'MiB'
    else:
        v, unit = nbytes / KIB, 'KiB'
    return ('%d %s' % (v, unit)) if v == int(v) else ('%g %s' % (v, unit))


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


def lstsq(A, y):
    """Least squares by the normal equations.
    Returns dict(coef, res, rms, max_res) or None when the matrix is singular."""
    m = len(A[0])
    G = [[sum(r[i] * r[j] for r in A) for j in range(m)] for i in range(m)]
    rhs = [sum(r[i] * yy for r, yy in zip(A, y)) for i in range(m)]
    coef = _solve(G, rhs)
    if coef is None:
        return None
    res = [yy - sum(c * v for c, v in zip(coef, r)) for r, yy in zip(A, y)]
    return {'coef': coef, 'res': res, 'rms': math.sqrt(sum(e * e for e in res) / len(res)),
            'max_res': max(abs(e) for e in res)}


def two_pct_rule(max_res, smallest):
    """The 2 % rule: a fit is void when its largest residual is over 2 % of the smallest
    fitted value. Returns dict(limit, pct, valid)."""
    return {'limit': 0.02 * smallest, 'pct': 100.0 * max_res / smallest,
            'valid': max_res <= 0.02 * smallest}


# ----------------------------------------------------------------------------- parsers

def parse_latency(path, boot):
    """One latency CSV -> list of blocks (one block per command)."""
    src = os.path.basename(path)
    blocks, blk, cur = [], None, None
    for n, line in enumerate(_lines(path), 1):
        if not line:
            continue
        if line.startswith('# latency:'):
            hdr = _kv(line.split(';', 1)[1])
            hdr.setdefault('seq', 0)
            hdr.setdefault('events', 'refill3')
            blk = {'boot': boot, 'file': src, 'path': path, 'index': len(blocks), 'line': n,
                   'header': hdr, 'header_text': line, 'columns': [],
                   'bracket_overhead_ns': None, 'bracket_overhead_line': None,
                   'sizes': {}, 'order': [], 'perf_lines': 0}
            blocks.append(blk)
            cur = None
            continue
        if blk is None:
            continue
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
            if f[2] == 'best':
                cur['best'] = float(f[5])
                cur['best_line'] = n
                continue
            row = {'mem': f[0], 'size': int(f[1]), 'mode': f[2], 'rep': _val(f[3]),
                   'loads': int(f[4]), 'line': n}
            for name, text in zip(blk['columns'][5:], f[5:]):
                row[_short(name)] = _val(text)
            cur['reps'].append(row)
    return blocks


def parse_bandwidth(path, boot):
    """One bandwidth CSV -> list of rows, one per command and kernel."""
    src = os.path.basename(path)
    rows, hdr, block, bykernel = [], None, -1, {}
    for n, line in enumerate(_lines(path), 1):
        if not line:
            continue
        if line.startswith('# bandwidth:'):
            kv = _kv(line.split(';', 1)[1])
            for k in ('asm_passes', 'cme', 'dsb_st', 'no_fold'):
                kv.setdefault(k, 0)
            hdr = {'kv': kv, 'line': n, 'backing': None, 'text': line, 'columns': [],
                   'perf_lines': 0}
            block += 1
            bykernel = {}
            continue
        if hdr is None:
            continue
        if line.startswith('# backing='):
            hdr['backing'] = line.split('=', 1)[1].strip()
        elif line.startswith('# perf:'):
            hdr['perf_lines'] += 1
        elif line.startswith('#'):
            continue
        elif line.startswith('mem,'):
            hdr['columns'] = line.split(',')
        else:
            f = line.split(',')
            k = f[1]
            if k not in bykernel:
                kv = hdr['kv']
                bykernel[k] = {
                    'boot': boot, 'file': src, 'path': path, 'block': block,
                    'header_line': hdr['line'], 'header': kv, 'header_text': hdr['text'],
                    'columns': hdr['columns'], 'backing': hdr['backing'], 'mem': f[0],
                    'kernel': k, 'kernel_label': KERNEL_LABEL.get(k, k), 'threads': int(f[2]),
                    'size': int(f[3]), 'label': fmt_size(int(f[3])), 'passes': kv['passes'],
                    'form': 'single-call' if kv['asm_passes'] else 'looped',
                    'flush_before': kv.get('flush_before', 0),
                    'has_counters': 'perf_cov' in hdr['columns'],
                    'rep_rows': [], 'best': None, 'best_line': None, '_hdr': hdr}
                rows.append(bykernel[k])
            r = bykernel[k]
            if f[4] == 'best':
                r['best'] = float(f[7])
                r['best_line'] = n
            else:
                rep = {'rep': int(f[4]), 'total_bytes': int(f[5]), 'elapsed_s': float(f[6]),
                       'gbps': float(f[7]), 'thr_min': float(f[8]), 'thr_max': float(f[9]),
                       'line': n}
                for name, text in zip(hdr['columns'][10:], f[10:]):
                    rep[_short(name)] = _val(text)
                r['rep_rows'].append(rep)
    for r in rows:
        _enrich_bw(r)
    return rows


def _enrich_bw(r):
    """Add the derived values of one bandwidth row (API.md, 'bandwidth row')."""
    r['perf_lines'] = r.pop('_hdr')['perf_lines']
    r['n_reps'] = len(r['rep_rows'])
    r['reps'] = [x['gbps'] for x in r['rep_rows']]
    r['reps_gbps'] = r['reps']
    r['spread_pct'] = spread_pct(r['reps_gbps'], r['best'])
    br = next(x for x in r['rep_rows'] if x['gbps'] == r['best'])
    r['best_rep'] = br
    r['line'] = br['line']
    r['total_bytes'] = br['total_bytes']
    r['bytes_per_pass'] = br['total_bytes'] / r['passes']
    for x in r['rep_rows']:
        x['ns'] = x['total_bytes'] / x['gbps']            # 1 GB/s = 1 byte per ns
        x['ns_pass'] = x['ns'] / r['passes']
    r['ns_rep'] = br['ns']
    r['ns_pass'] = br['ns_pass']
    r['thr_min'], r['thr_max'] = br['thr_min'], br['thr_max']
    r['per_thread'] = r['best'] / r['threads']
    r['ns_per_64'] = LINE / r['per_thread']
    r['bytes_per_cycle'] = r['per_thread'] / CYCLES_PER_NS
    r['eff_cycles_64'] = r['ns_per_64'] * CYCLES_PER_NS
    for k in ('cyc_line',) + COUNTER_KEYS:
        if k in br:
            r[k] = br[k]
            r[k + '_reps'] = [x[k] for x in r['rep_rows']]


def parse_cmn(path, boot):
    """cmn-counts.csv -> list of rows (label, event, node, count, enabled_ns, running_ns, line)."""
    rows = []
    for n, line in enumerate(_lines(path), 1):
        f = line.split(',')
        if len(f) != 7 or f[0] == 'label' or line.startswith('#'):
            continue
        rows.append({'boot': boot, 'file': os.path.basename(path), 'line': n, 'label': f[0],
                     'event': f[1], 'node': _val(f[2]), 'count': int(float(f[3])),
                     'enabled_ns': int(float(f[4])), 'running_ns': int(float(f[5])),
                     'scaled_count': int(float(f[6]))})
    return rows


_CMD = re.compile(r'^\+ (?:(cmn0?|xp|cmnq) (\S+) (?:[\d,]+ )?)?(\S*/)?(latency|bandwidth)\b(.*?)'
                  r'(?: \[uptime ([\d.]+)\])?\s*$')


def parse_log(path, boot):
    """log.txt -> dict(commands, starts, done, exits, pwrstat, cpu3, flags, n_lines)."""
    out = {'commands': [], 'starts': [], 'done': [], 'exits': [], 'pwrstat': [], 'cpu3': [],
           'flags': None, 'commit': None}
    lines = _lines(path)
    out['n_lines'] = len(lines) - (1 if lines and lines[-1] == '' else 0)
    for n, line in enumerate(lines, 1):
        if line.startswith('+ '):
            m = _CMD.match(line)
            c = {'boot': boot, 'file': 'log.txt', 'line': n,
                 'text': re.sub(r'\s*\[uptime [\d.]+\]\s*$', '', line[2:]),
                 'uptime': None, 'wrapper': None, 'label': None, 'program': None, 'args': '',
                 'cme': '--cme' in line, 'threads': 1, 'cpus': None}
            if m:
                c.update(wrapper=m.group(1), label=m.group(2), program=m.group(4),
                         args=m.group(5).strip(),
                         uptime=float(m.group(6)) if m.group(6) else None)
                mt = re.search(r'--threads (\d+)', c['args'])
                mc = re.search(r'--cpus? ([\d,-]+)', c['args'])
                if mt:
                    c['threads'] = int(mt.group(1))
                if mc:
                    c['cpus'] = _cpu_list(mc.group(1))
            out['commands'].append(c)
            continue
        if '(exit' in line:
            out['exits'].append({'line': n, 'text': line})
        m = re.match(r'# (\S+) start .*out=\S*cache-mem-perf-([0-9a-f]+)/', line)
        if m:
            out['starts'].append({'line': n, 'script': m.group(1), 'text': line})
            out['commit'] = out['commit'] or m.group(2)
        m = re.match(r'# (\S+) done .*: (\d+) measurement command\(s\) failed', line)
        if m:
            out['done'].append({'line': n, 'script': m.group(1), 'failed': int(m.group(2)),
                                'text': line})
        m = re.match(r'# box clusterpwrstat (.*): (0x[0-9a-fA-F]+)\s*$', line)
        if m:
            out['pwrstat'].append({'line': n, 'when': m.group(1), 'value': int(m.group(2), 16),
                                   'text': line})
        m = re.match(r'cpu3 online=(\d)', line)
        if m:
            out['cpu3'].append({'line': n, 'online': int(m.group(1)), 'text': line})
        if line.startswith('ocm=') and out['flags'] is None:
            out['flags'] = {'line': n, 'text': line, 'value': _kv(line)}
    return out


def verify_sha256(run_dir):
    """Check every entry of <run_dir>/SHA256SUMS with hashlib.
    Returns dict(ok, total, bad=[names], missing=[names], entries=[(name, ok)], file)."""
    entries, bad, missing = [], [], []
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
            if not ok:
                bad.append(name)
        else:
            missing.append(name)
        entries.append((name, ok))
    return {'ok': sum(1 for _, o in entries if o), 'total': len(entries), 'bad': bad,
            'missing': missing, 'entries': entries, 'file': 'SHA256SUMS'}


def parse_mesh_map(lines, first_line=1):
    """The arm-cmn mesh map of sysinfo.txt -> list of device cells.
    Each cell: dict(x, y, xp, port, type, index, node, line). `lines` are the map lines."""
    cells, y, xps, pending = [], None, [], None
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
                                  'index': int(i) if i.isdigit() else None,
                                  'node': 64 * x + 8 * y, 'line': tl})
            pending = None
    return cells


def _find(lines, pattern):
    """All (line number, text) of the lines that match the regular expression."""
    rx = re.compile(pattern)
    return [(n, l) for n, l in enumerate(lines, 1) if rx.search(l)]


def _fact(boot, file, hit, value=None):
    return {'boot': boot, 'file': file, 'line': hit[0], 'text': hit[1], 'value': value}


def node_xy(node):
    """Mesh coordinates of a node id on port 0: id = 64 x + 8 y."""
    return (node >> 6, (node >> 3) & 7)


def steps_xy(cpu, region, ports=None):
    """(X steps, Y steps) from the cluster port of a CPU to the home node of an OCM region.
    Any shortest route has |dx| X steps and |dy| Y steps."""
    px, py = (ports or PORT_XY)[cpu]
    hx, hy = node_xy(REGION_NODE[region])
    return (abs(px - hx), abs(py - hy))


def mean_steps(cpu):
    """Mean (X steps, Y steps) from a CPU to the five regions."""
    s = [steps_xy(cpu, r) for r in range(5)]
    return (sum(a for a, _ in s) / 5.0, sum(b for _, b in s) / 5.0)


def chain_kind(header):
    if header.get('seq'):
        return 'address order'
    if header.get('flush'):
        return 'every line flushed first'
    if header.get('fresh'):
        return 'walked once'
    return 'walked many times'


def chain_shape(sparse):
    return {0: 'every line', 1: 'one line per 4 KiB page',
            2: 'one line per page at varied offsets'}.get(sparse, 'every line')


def cite(row):
    """'F1 latency-dram-small.csv:5' for a row that carries boot, file, line."""
    return '%s %s:%s' % (row['boot'], row['file'], row['line'])


# ----------------------------------------------------------------------------- the data object

class Data:
    """Everything the page needs. Build it with load()."""

    def __init__(self):
        self.root = ROOT
        self.boots_order = BOOTS
        self.boot_name = dict(BOOT_NAME)
        self.boot_first_use = dict(BOOT_FIRST_USE)
        self.run_dir = dict(RUN)
        self.boot_dir = dict(BOOTDIR)
        self.cycles_per_ns = CYCLES_PER_NS
        self.doc = dict(DOC)
        self._lat = {b: {} for b in BOOTS}
        self._bw = {b: {} for b in BOOTS}
        self._cmn = {}
        self._text = {}
        self._cmdmap = {}
        self.log = {}
        self._read_files()
        self._build_platform()
        self._build_boots()
        self._build_clock()
        self._build_mesh_map()
        self._build_ocm_fit()        # the latency tables use boot B's fit
        self._build_latency()
        self._build_bandwidth()
        self._build_multicore()
        self._build_ocm()
        self._build_mesh_counts()
        self._build_open()
        self._build_cross()
        self._build_cmd_cmp()

    # ------------------------------------------------------------------ reading
    def _read_files(self):
        self.files = {}
        for b in BOOTS:
            d = BOOTDIR[b]
            names = sorted(os.listdir(d))
            for name in names:
                if not name.endswith('.csv') or name.startswith('cme-'):
                    continue
                p = os.path.join(d, name)
                if name == 'cmn-counts.csv':
                    self._cmn[b] = parse_cmn(p, b)
                elif name.startswith('latency-'):
                    self._lat[b][name] = parse_latency(p, b)
                elif name.startswith('bandwidth-'):
                    self._bw[b][name] = parse_bandwidth(p, b)
            self.log[b] = parse_log(os.path.join(d, 'log.txt'), b)
            self.files[b] = {'latency': sorted(self._lat[b]), 'bandwidth': sorted(self._bw[b]),
                             'all': names,
                             'cme': [n for n in names if n.startswith('cme-')]}

    # ------------------------------------------------------------------ generic access
    def text(self, boot, name):
        """Lines of 'log.txt', 'sysinfo.txt', 'all.txt' (boot folder) or 'dmesg.txt',
        'README.md', 'SHA256SUMS' (run folder). Returns None when the file does not exist."""
        key = (boot, name)
        if key not in self._text:
            base = RUN[boot] if name in ('dmesg.txt', 'README.md', 'SHA256SUMS') else BOOTDIR[boot]
            p = os.path.join(base, name)
            self._text[key] = _lines(p) if os.path.isfile(p) else None
        return self._text[key]

    def text_line(self, boot, name, n):
        """Line n (1-based) of a text file of a boot."""
        return self.text(boot, name)[n - 1]

    def has(self, boot, file):
        return file in self._lat[boot] or file in self._bw[boot]

    def latblocks(self, boot, file):
        """All command blocks of one latency file (API.md, 'latency block')."""
        return self._lat[boot][file]

    def lat(self, boot, file, size=None, block=0):
        """One footprint entry of a latency file. size=None takes the only footprint."""
        blk = self._lat[boot][file][block]
        if size is None:
            size = blk['order'][0]
        return blk['sizes'][size]

    def latrow(self, boot, file, size=None, block=0):
        """The derived chain row of one footprint (API.md, 'chain row')."""
        blk = self._lat[boot][file][block]
        if size is None:
            size = blk['order'][0]
        return self._row(blk, blk['sizes'][size])

    def latrows(self, boot, file, block=0):
        """The derived chain rows of every footprint of one block, in file order."""
        blk = self._lat[boot][file][block]
        return [self._row(blk, blk['sizes'][s]) for s in blk['order']]

    def bw(self, boot, file, kernel=None, size=None):
        """Bandwidth rows of one file. With kernel and size it returns the one row (or None)."""
        rows = [r for r in self._bw[boot][file]
                if (kernel is None or r['kernel'] == kernel)
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

    def cmn_labels(self, boot):
        seen = []
        for r in self._cmn[boot]:
            if r['label'] not in seen:
                seen.append(r['label'])
        return seen

    def cmn_nodes(self, boot, label):
        """{node id: requests received} of one label (event hns_pocq_reqs_recvd_all)."""
        return {r['node']: r['count'] for r in self.cmn(boot, label, 'hns_pocq_reqs_recvd_all')}

    def cmn_value(self, boot, label, event):
        """The count of an event that has one row per label (sums and the two timing rows)."""
        rows = self.cmn(boot, label, event)
        return rows[0]['count'] if rows else None

    def _cmd_map(self, boot):
        """{(file, block index): log line} of a boot. all.txt lists the commands in the order of
        log.txt, each followed by its output, which is the text of one CSV block."""
        if boot in self._cmdmap:
            return self._cmdmap[boot]
        blocks = {}
        for name in self.files[boot]['latency'] + self.files[boot]['bandwidth']:
            cur, idx = None, -1
            for line in _lines(os.path.join(BOOTDIR[boot], name)):
                if line.startswith('# latency:') or line.startswith('# bandwidth:'):
                    idx += 1
                    cur = blocks.setdefault((name, idx), [])
                if cur is not None and line:
                    cur.append(line)
        bytext = {}
        for key, lines in blocks.items():
            bytext.setdefault('\n'.join(lines), []).append(key)
        sections, cur = [], None
        for line in self.text(boot, 'all.txt') or []:
            if line.startswith('## '):
                cur = []
                sections.append(cur)
            elif cur is not None and line:
                cur.append(line)
        out = {}
        cmds = self.log[boot]['commands']
        if len(sections) == len(cmds):
            for c, sec in zip(cmds, sections):
                keys = bytext.get('\n'.join(sec))
                if keys:
                    out[keys.pop(0)] = c['line']
        self._cmdmap[boot] = out
        return out

    def log_lines(self, boot, file):
        """Line numbers in log.txt of the commands that wrote a CSV file of a boot (one per
        block). An empty list when the file cannot be matched."""
        return sorted(v for (name, _), v in self._cmd_map(boot).items() if name == file)

    def log_line(self, boot, file, block=0):
        """Line number in log.txt of the command that wrote one block of a CSV file, or None."""
        return self._cmd_map(boot).get((file, block))

    def sweep(self, boot):
        """The 24 chain rows of the footprint sweep of a boot: 12 walked many times, 11 walked
        once, then the 8 MiB row with every line flushed first."""
        rows = self.latrows(boot, 'latency-dram-small.csv') + \
            self.latrows(boot, 'latency-dram-large.csv') + \
            self.latrows(boot, 'latency-dram-flushed.csv')
        return rows

    def sweep_row(self, boot, size, kind=None):
        for r in self.sweep(boot):
            if r['size'] == size and (kind is None or r['kind'] == kind):
                if kind is None and r['kind'] == 'every line flushed first':
                    continue
                return r
        raise KeyError((boot, size, kind))

    def verify_sha(self, boot):
        return self._sha[boot]

    # ------------------------------------------------------------------ row builder
    def _row(self, blk, e):
        """Derived row of one footprint entry. Keys: API.md, 'chain row'."""
        h = blk['header']
        reps = e['reps']
        ns = [r['ns'] for r in reps]
        br = next(r for r in reps if r['ns'] == e['best'])
        row = {'boot': blk['boot'], 'file': blk['file'], 'block': blk['index'],
               'line': br['line'], 'best_line': e['best_line'], 'size_line': e['line'],
               'header_line': blk['line'], 'cpu': h['cpu'], 'mem': h['mem'],
               'events': h['events'], 'size': e['size'], 'label': fmt_size(e['size']),
               'lines': e['lines'], 'backing': e['backing'], 'segments': e['segments'],
               'kind': chain_kind(h), 'shape': chain_shape(e['sparse']),
               'loads': br['loads'], 'passes': br['loads'] / e['lines'],
               'best': e['best'], 'best_ns': e['best'], 'best_mode': br['mode'],
               'n_reps': len(reps), 'reps': ns, 'rep_rows': reps,
               'spread_pct': spread_pct(ns, e['best']), 'median': statistics.median(ns),
               'max': max(ns), 'cycles': br.get('cycles'),
               'cyc_per_ns': br['cycles'] / br['ns'] if br.get('cycles') else None,
               'bracket_overhead_ns': blk['bracket_overhead_ns']}
        for k in COUNTER_KEYS:
            if k in br:
                row[k] = br[k]
                row[k + '_reps'] = [r[k] for r in reps]
            elif k in ('l1', 'l2', 'a2') + PF_KEYS:
                row[k] = None
                row[k + '_reps'] = None
        if row['l2pf'] is not None:
            row['unacc_l2'] = [r['l2'] - r['l2pf'] - r['l2byl1pf'] - r['a2'] for r in reps]
        else:
            row['unacc_l2'] = None
        return row

    # ------------------------------------------------------------------ platform
    def _build_platform(self):
        si = self.text('F1', 'sysinfo.txt')
        dm = self.text('F1', 'dmesg.txt')
        P = {}
        caches = []
        for hit in _find(si, r'cache/index\d: level='):
            kv = _kv(hit[1].split(':', 1)[1])
            unit = {'K': KIB, 'M': MIB}[kv['size'][-1]]
            caches.append({'boot': 'F1', 'file': 'sysinfo.txt', 'line': hit[0], 'text': hit[1],
                           'level': kv['level'], 'type': kv['type'], 'size': kv['size'],
                           'size_bytes': int(kv['size'][:-1]) * unit,
                           'shared_cpu_list': str(kv['shared_cpu_list'])})
        P['caches'] = caches
        P['cache_bytes'] = {('L1' if c['level'] == 1 else 'L%d' % c['level']): c['size_bytes']
                            for c in caches if c['type'] != 'Instruction'}
        P['ocm_iomem'] = [{'boot': 'F1', 'file': 'sysinfo.txt', 'line': n, 'text': t,
                           'region': i, 'base': int(t.split('-')[0], 16),
                           'bytes': int(t.split('-')[1].split()[0], 16)
                           - int(t.split('-')[0], 16) + 1}
                          for i, (n, t) in enumerate(_find(si, r': ocm\s*$'))]

        def one(lines, file, pattern, conv=None, boot='F1'):
            hits = _find(lines, pattern)
            if not hits:
                return None
            m = re.search(pattern, hits[0][1])
            v = m.group(1) if m.groups() else None
            return _fact(boot, file, hits[0], conv(v) if conv and v is not None else v)

        P['kernel'] = one(si, 'sysinfo.txt', r'^Linux \S+ (\S+)')
        cl = _find(si, r'^## cmdline')
        P['cmdline'] = _fact('F1', 'sysinfo.txt', (cl[0][0] + 1, si[cl[0][0]]), si[cl[0][0]])
        oc = _find(si, r'^## online cpus')
        P['online_cpus'] = _fact('F1', 'sysinfo.txt', (oc[0][0] + 1, si[oc[0][0]]), si[oc[0][0]])
        P['n_cpus'] = len(_find(si, r'^processor\s*:'))
        P['cpu_part'] = one(si, 'sysinfo.txt', r'^CPU part\s*:\s*(\S+)')
        P['hugepages_total'] = one(si, 'sysinfo.txt', r'^HugePages_Total:\s+(\d+)', int)
        P['hugepages_free'] = one(si, 'sysinfo.txt', r'^HugePages_Free:\s+(\d+)', int)
        P['hugepagesize_kb'] = one(si, 'sysinfo.txt', r'^Hugepagesize:\s+(\d+) kB', int)
        P['memtotal_kb'] = one(si, 'sysinfo.txt', r'^MemTotal:\s+(\d+) kB', int)
        P['spm_missing'] = one(si, 'sysinfo.txt', r'/dev/asimov-spm: No such file')
        P['ocm_device'] = one(si, 'sysinfo.txt', r'\s/dev/ocm\s*$')
        P['cmn_events'] = one(si, 'sysinfo.txt', r'^type=\d+ cpumask=\d+ events=(\d+)', int)
        P['timer'] = one(dm, 'dmesg.txt', r'arch_timer: cp15 timer running at ([\d.]+)MHz', float)
        P['sched_clock'] = one(dm, 'dmesg.txt', r'sched_clock: .*resolution (\d+)ns', int)
        P['nohz'] = one(dm, 'dmesg.txt', r'NO_HZ: Full dynticks CPUs: ([\d-]+)')
        P['pmu'] = one(dm, 'dmesg.txt', r'enabled with (\S+) PMU driver, (\d+)')
        if P['pmu']:
            P['pmu']['counters'] = int(re.search(r'driver, (\d+)', P['pmu']['text']).group(1))
        mm = _find(si, r'^## arm-cmn mesh map')
        first = mm[0][0]
        last = max(n for n, _ in _find(si, r'^-----\+--------'))
        P['mesh_map'] = {'boot': 'F1', 'file': 'sysinfo.txt', 'line': first, 'last_line': last,
                         'text': si[first - 1]}
        P['log_flags'] = dict(self.log['F1']['flags'], boot='F1', file='log.txt')
        P['cpu3'] = [dict(c, boot='F1', file='log.txt') for c in self.log['F1']['cpu3']]
        cnt = {}
        for b in BOOTS:
            for f in self._lat[b].values():
                for blk in f:
                    cnt.setdefault(b, set()).add(blk['header']['cntfrq_hz'])
        P['cntfrq_hz'] = {b: sorted(v) for b, v in cnt.items()}
        self.platform = P
        self._mesh_lines = (si[first - 1:last], first)

    def _dmesg_maps(self, boot):
        dm = self.text(boot, 'dmesg.txt')
        if dm is None:
            return None
        maps = _find(dm, r'membench_ocm: map ')
        cont = {}
        aligned64 = 0
        for _, l in maps:
            k = re.search(r'cont=(\d+/\d+)', l).group(1)
            cont[k] = cont.get(k, 0) + 1
            va = int(re.search(r'va=(0x[0-9a-f]+)', l).group(1), 16)
            pa = int(re.search(r'pa=(0x[0-9a-f]+)', l).group(1), 16)
            aligned64 += (va - pa) % (64 * KIB) == 0
        ready = _find(dm, r'membench_ocm: /dev/ocm ready')
        return {'boot': boot, 'file': 'dmesg.txt', 'n': len(maps),
                'first_line': maps[0][0] if maps else None,
                'last_line': maps[-1][0] if maps else None, 'cont': cont,
                'aligned_64k': aligned64,
                'all_len_256k': all('len=0x40000' in l for _, l in maps),
                'module_line': ready[0][0] if ready else None,
                'module_text': ready[0][1] if ready else None}

    def _build_boots(self):
        self._sha = {b: verify_sha256(RUN[b]) for b in BOOTS}
        self.dmesg_maps = {b: self._dmesg_maps(b) for b in BOOTS}
        self.commands = {}
        self.integrity = {}
        self.boots = []
        for b in BOOTS:
            lg = self.log[b]
            cmds = lg['commands']
            core = [c for c in cmds if not c['cme']]
            self.commands[b] = {
                'n_cmd': len(cmds), 'n_core': len(core), 'n_cme': len(cmds) - len(core),
                'n_core_latency': sum(1 for c in core if c['program'] == 'latency'),
                'n_core_bandwidth': sum(1 for c in core if c['program'] == 'bandwidth'),
                'n_core_other': sum(1 for c in core if c['program'] is None),
                'n_core_wrapped': {w: sum(1 for c in core if c['wrapper'] == w)
                                   for w in ('cmn', 'cmn0', 'xp')},
                'n_exit_lines': len(lg['exits']), 'done': lg['done'],
                'n_failed': sum(d['failed'] for d in lg['done']) + len(lg['exits']),
                'first_uptime': min((c['uptime'] for c in cmds if c['uptime'] is not None),
                                    default=None),
                'last_uptime': max((c['uptime'] for c in cmds if c['uptime'] is not None),
                                   default=None),
                'commands': cmds, 'core': core, 'log_lines': lg['n_lines']}
            cov, lat_n, lat_ok, bw_n, bw_ok = [], 0, 0, 0, 0
            perf_lines = lat_rows = bw_rows = 0
            for f in self._lat[b].values():
                for blk in f:
                    perf_lines += blk['perf_lines']
                    for e in blk['sizes'].values():
                        lat_n += 1
                        lat_ok += e['best'] == min(r['ns'] for r in e['reps'])
                        lat_rows += len(e['reps'])
                        cov += [r['perf_cov'] for r in e['reps'] if 'perf_cov' in r]
            seen = set()
            for f in self._bw[b].values():
                for r in f:
                    bw_n += 1
                    bw_ok += r['best'] == max(r['reps_gbps'])
                    bw_rows += r['n_reps']
                    cov += [x['perf_cov'] for x in r['rep_rows'] if 'perf_cov' in x]
                    if (r['file'], r['block']) not in seen:
                        seen.add((r['file'], r['block']))
                        perf_lines += r['perf_lines']
            cm = self._cmn.get(b, [])
            self.integrity[b] = {
                'sha': self._sha[b], 'n_core_csv': len(self._lat[b]) + len(self._bw[b]),
                'n_latency_files': len(self._lat[b]), 'n_bandwidth_files': len(self._bw[b]),
                'n_cme_csv': len(self.files[b]['cme']),
                'latency_timed_rows': lat_rows, 'bandwidth_timed_rows': bw_rows,
                'timed_rows': lat_rows + bw_rows,
                'lat_best_n': lat_n, 'lat_best_ok': lat_ok, 'bw_best_n': bw_n, 'bw_best_ok': bw_ok,
                'cov_rows': len(cov), 'cov_min': min(cov) if cov else None,
                'cov_max': max(cov) if cov else None,
                'cov_none': sum(1 for v in cov if v is None), 'perf_lines': perf_lines,
                'bw_blocks_with_counters': len({(r['file'], r['block'])
                                                for f in self._bw[b].values() for r in f
                                                if r['has_counters']}),
                'cmn_rows': len(cm), 'cmn_labels': len(self.cmn_labels(b)) if cm else 0,
                'cmn_core_labels': sum(1 for l in self.cmn_labels(b) if not l.startswith('cme'))
                if cm else 0,
                'cmn_events': sorted({r['event'] for r in cm}),
                'cmn_multiplexed': sum(1 for r in cm if r['enabled_ns'] != r['running_ns'])}
            dmm = self.dmesg_maps[b]
            cond = BOOT_COND[b]
            pw = lg['pwrstat']
            row = {'key': b, 'name': BOOT_NAME[b], 'first_use': BOOT_FIRST_USE[b],
                   'folder': FOLDER[b],
                   'path': os.path.relpath(BOOTDIR[b], ROOT), 'l3': cond['l3'],
                   'prefetchers': cond['prefetchers'], 'ocm_mapping': cond['ocm_mapping'],
                   'script': cond['script'], 'scripts': [s['script'] for s in lg['starts']],
                   'commit': lg['commit'], 'n_cmd': self.commands[b]['n_cmd'],
                   'n_core': self.commands[b]['n_core'], 'n_cme': self.commands[b]['n_cme'],
                   'n_failed': self.commands[b]['n_failed'],
                   'sha_ok': self._sha[b]['ok'], 'sha_total': self._sha[b]['total'],
                   'cov_rows': self.integrity[b]['cov_rows'],
                   'cov_min': self.integrity[b]['cov_min'],
                   'cov_max': self.integrity[b]['cov_max'],
                   'pwrstat_lines': pw, 'pwrstat_values': sorted({p['value'] for p in pw}),
                   'l3_from_log': None, 'map_lines': dmm['n'] if dmm else None,
                   'map_first_line': dmm['first_line'] if dmm else None,
                   'map_last_line': dmm['last_line'] if dmm else None,
                   'map_cont': dmm['cont'] if dmm else None,
                   'n_core_csv': self.integrity[b]['n_core_csv'],
                   'done_lines': [d['line'] for d in lg['done']],
                   'log_lines': lg['n_lines'], 'main': b == 'F1'}
            if pw:
                vals = row['pwrstat_values']
                row['l3_from_log'] = ('on' if vals == [0x70] else
                                      'no data' if vals == [0] else 'mixed')
            self.boots.append(row)
        self.boot = {r['key']: r for r in self.boots}

    # ------------------------------------------------------------------ clock, bracket
    def _timed_lat_rows(self, boot):
        for name in self.files[boot]['latency']:
            for blk in self._lat[boot][name]:
                for s in blk['order']:
                    for r in blk['sizes'][s]['reps']:
                        yield name, blk, r

    def _build_clock(self):
        self.clock = {}
        for b in BOOTS:
            num = den = 0.0
            rows = []
            for name, blk, r in self._timed_lat_rows(b):
                if r['loads'] >= CLOCK_MIN_LOADS and r.get('cycles') is not None:
                    num += r['cycles'] * r['loads']
                    den += r['ns'] * r['loads']
                    rows.append((r['cycles'] / r['ns'], name, r['line']))
            short = [r['cycles'] / r['ns'] for _, _, r in self._timed_lat_rows(b)
                     if r['loads'] < CLOCK_MIN_LOADS and r.get('cycles') is not None]
            lo, hi = min(rows), max(rows)
            self.clock[b] = {'boot': b, 'pooled': num / den, 'n_rows': len(rows),
                             'min': lo[0], 'min_file': lo[1], 'min_line': lo[2],
                             'max': hi[0], 'max_file': hi[1], 'max_line': hi[2],
                             'median': statistics.median(v for v, _, _ in rows),
                             'min_loads': CLOCK_MIN_LOADS, 'n_short_rows': len(short),
                             'short_median': statistics.median(short) if short else None,
                             'short_max': max(short) if short else None}
        self.bracket_by_boot = {}
        for b in BOOTS:
            vals = []
            for name in self.files[b]['latency']:
                for blk in self._lat[b][name]:
                    if blk['bracket_overhead_ns'] is not None:
                        vals.append((blk['bracket_overhead_ns'], name,
                                     blk['bracket_overhead_line']))
            vs = sorted(v for v, _, _ in vals)
            mx = max(vals)
            med = vs[len(vs) // 2]
            self.bracket_by_boot[b] = {
                'boot': b, 'n_cmd': len(vs), 'min': vs[0], 'median': med, 'max': vs[-1],
                'max_file': mx[1], 'max_line': mx[2], 'file': mx[1], 'line': mx[2],
                'n_at_median': sum(1 for v in vs if v == med),
                'per_load_64_est': med / 64.0, 'per_load_320_est': med / 320.0,
                'per_load_4096_est': med / 4096.0}
        self.bracket = self.bracket_by_boot['F1']

    # ------------------------------------------------------------------ mesh map and steps
    def _build_mesh_map(self):
        lines, first = self._mesh_lines
        cells = parse_mesh_map(lines, first)
        self.mesh_cells = cells
        counts = {}
        for c in cells:
            t = 'RN-F' if c['type'].startswith('RN-F') else c['type']
            counts[t] = counts.get(t, 0) + 1
        hn = {(c['x'], c['y']): c for c in cells if c['type'] == 'HN-S'}
        rnf = {(c['x'], c['y']): c for c in cells if c['type'].startswith('RN-F')}
        iom = self.platform['ocm_iomem']
        homes = []
        for reg, node in enumerate(REGION_NODE):
            x, y = node_xy(node)
            c = hn.get((x, y))
            homes.append({'region': reg, 'node': node, 'x': x, 'y': y,
                          'hns_index': c['index'] if c else None, 'xp': c['xp'] if c else None,
                          'map_has_hns': c is not None, 'line': c['line'] if c else None,
                          'boot': 'F1', 'file': 'sysinfo.txt',
                          'base': iom[reg]['base'] if reg < len(iom) else None,
                          'base_line': iom[reg]['line'] if reg < len(iom) else None})
        ports = []
        for cpu, (x, y) in sorted(PORT_XY.items()):
            c = rnf.get((x, y))
            ports.append({'cpus': (cpu, cpu + 1), 'cpu': cpu, 'x': x, 'y': y, 'node': 64 * x + 8 * y,
                          'map_has_port': c is not None, 'line': c['line'] if c else None,
                          'xp': c['xp'] if c else None, 'boot': 'F1', 'file': 'sysinfo.txt',
                          'used': True})
        fx, fy = FIFTH_PORT_XY
        c = rnf.get((fx, fy))
        ports.append({'cpus': None, 'cpu': None, 'x': fx, 'y': fy, 'node': 64 * fx + 8 * fy,
                      'map_has_port': c is not None, 'line': c['line'] if c else None,
                      'xp': c['xp'] if c else None, 'boot': 'F1', 'file': 'sysinfo.txt',
                      'used': False})
        self.mesh = {
            'grid_x': 1 + max(c['x'] for c in cells), 'grid_y': 1 + max(c['y'] for c in cells),
            'device_counts': counts, 'home_nodes': homes, 'ports': ports,
            'rnf_xy': sorted(rnf), 'hns_xy': sorted(hn),
            'map_first_line': first, 'map_last_line': first + len(lines) - 1,
            'boot': 'F1', 'file': 'sysinfo.txt', 'line': first,
            'ports_ok': all(p['map_has_port'] for p in ports),
            'homes_ok': all(h['map_has_hns'] for h in homes)}
        self.steps = []
        for cpu in CPUS:
            for reg in range(5):
                dx, dy = steps_xy(cpu, reg)
                self.steps.append({'cpu': cpu, 'region': reg, 'dx': dx, 'dy': dy,
                                   'steps': dx + dy, 'node': REGION_NODE[reg],
                                   'port_xy': PORT_XY[cpu], 'hn_xy': node_xy(REGION_NODE[reg])})
        self.steps_mean = {cpu: {'x': mean_steps(cpu)[0], 'y': mean_steps(cpu)[1],
                                 'total': sum(mean_steps(cpu))} for cpu in CPUS}

    def step(self, cpu, region):
        """(dx, dy) of one cell of D.steps."""
        return steps_xy(cpu, region)

    # ------------------------------------------------------------------ OCM route fits
    def _route_cells(self, boot):
        """Every line of one region under the mesh counters: 20 cells (4 CPUs x 5 regions)."""
        out = []
        for cpu in CPUS:
            for reg in range(5):
                r = self.latrow(boot, 'latency-ocm-region%d-route-cpu%d.csv' % (reg, cpu))
                dx, dy = steps_xy(cpu, reg)
                others = [v for v in r['reps'] if v != r['best']] or [r['best']]
                r.update(region=reg, node=REGION_NODE[reg], steps_x=dx, steps_y=dy,
                         steps=dx + dy, other=others[0],
                         pf_max=max(max(r[k + '_reps']) for k in PF_KEYS),
                         l1_rng=_rng(r['l1_reps']), l2_rng=_rng(r['l2_reps']),
                         a2_rng=_rng(r['a2_reps']), residual=None)
                out.append(r)
        return out

    @staticmethod
    def _xy_fit(cells, value='best', ports=None):
        A, y = [], []
        for c in cells:
            dx, dy = steps_xy(c['cpu'], c['region'], ports)
            A.append([1.0, dx, dy])
            y.append(c[value])
        f = lstsq(A, y)
        if f is None:
            return None
        rule = two_pct_rule(f['max_res'], min(y))
        return {'a': f['coef'][0], 'bx': f['coef'][1], 'cy': f['coef'][2], 'rms': f['rms'],
                'max_res': f['max_res'], 'pct_of_smallest': rule['pct'], 'limit': rule['limit'],
                'valid': rule['valid'], 'n': len(y), 'smallest': min(y), 'largest': max(y),
                'res': f['res']}

    def _flits(self, boot):
        """Does the direction with the most data flits at each end point toward the other end?
        Events mxp_{e,w,n,s}_dat_txflit_valid, labels route-ocmR-cpuN (exploratory)."""
        ok_c = ok_n = n = 0
        for cpu in CPUS:
            for reg in range(5):
                rows = self.cmn(boot, 'route-ocm%d-cpu%d' % (reg, cpu))
                if not rows:
                    return None
                px, py = PORT_XY[cpu]
                hx, hy = node_xy(REGION_NODE[reg])

                def top(node):
                    d = {r['event'].split('_')[1]: r['count'] for r in rows
                         if r['event'].startswith('mxp_') and r['node'] == node}
                    return max(d, key=d.get)
                dx, dy = hx - px, hy - py
                want_c = ('e' if dx > 0 else 'w') if dx != 0 else ('n' if dy > 0 else 's')
                want_n = ('w' if dx > 0 else 'e') if dx != 0 else ('s' if dy > 0 else 'n')
                ok_c += top(64 * px + 8 * py) == want_c
                ok_n += top(REGION_NODE[reg]) == want_n
                n += 1
        return {'boot': boot, 'file': 'cmn-counts.csv', 'n': n, 'cluster_ok': ok_c,
                'node_ok': ok_n}

    def _build_ocm_fit(self):
        self.ocm_route = {b: self._route_cells(b) for b in ('B', 'D', 'E')}
        fit = {}
        for b in ('B', 'D', 'E'):
            f = self._xy_fit(self.ocm_route[b])
            f.update(boot=b, rows='every line of one region, 20 cells',
                     file='latency-ocm-region<r>-route-cpu<c>.csv')
            for c, e in zip(self.ocm_route[b], f['res']):
                c['residual'] = e
            sp = [c['spread_pct'] for c in self.ocm_route[b]]
            f.update(l1=_rng(v for c in self.ocm_route[b] for v in c['l1_reps']),
                     l2=_rng(v for c in self.ocm_route[b] for v in c['l2_reps']),
                     a2=_rng(v for c in self.ocm_route[b] for v in c['a2_reps']),
                     l2pf=_rng(v for c in self.ocm_route[b] for v in c['l2pf_reps']),
                     pf_max=max(c['pf_max'] for c in self.ocm_route[b]),
                     spread_lo=min(sp), spread_hi=max(sp))
            fit[b] = f
        cellsB = self.ocm_route['B']
        one = lstsq([[1.0, c['steps']] for c in cellsB], [c['best'] for c in cellsB])
        fit['B_one_slope'] = {'boot': 'B', 'a': one['coef'][0], 'per_step': one['coef'][1],
                              'rms': one['rms'], 'max_res': one['max_res'],
                              'pct_of_smallest': 100.0 * one['max_res'] / fit['B']['smallest'],
                              'valid': one['max_res'] <= 0.02 * fit['B']['smallest']}
        rank = []
        for perm in itertools.permutations(self.mesh['rnf_xy'], 4):
            f = self._xy_fit(cellsB, ports=dict(zip(CPUS, perm)))
            if f is not None:
                rank.append((f['rms'], perm))
        rank.sort()
        doc = tuple(PORT_XY[c] for c in CPUS)
        fit['ports'] = {'n_perm': len(rank), 'best_rms': rank[0][0], 'best_ports': rank[0][1],
                        'second_rms': rank[1][0], 'second_ports': rank[1][1],
                        'rank': 1 + [p for _, p in rank].index(doc),
                        'documented_is_best': rank[0][1] == doc}
        fit['flits'] = {b: self._flits(b) for b in ('B', 'E')}
        grp = {}
        for c in cellsB:
            grp.setdefault((c['steps_x'], c['steps_y']), []).append(c['best'])
        fit['by_steps'] = [{'steps_x': k[0], 'steps_y': k[1], 'n': len(v), 'lo': min(v),
                            'hi': max(v)} for k, v in sorted(grp.items())]
        self.ocm_fit = fit

    def fit_pred(self, steps_x, steps_y, boot='B'):
        """Value of a boot's route fit at a number of X steps and Y steps (ns per load)."""
        f = self.ocm_fit[boot]
        return f['a'] + f['bx'] * steps_x + f['cy'] * steps_y

    # ------------------------------------------------------------------ latency tables
    def _build_latency(self):
        self.lat_sweep = self.sweep('F1')
        sw = [r for r in self.lat_sweep if r['kind'] != 'every line flushed first']
        fl = self.lat_sweep[-1]
        self.lat_flushed = fl
        self.lat_sweep_summary = {
            'n': len(self.lat_sweep),
            'n_spread_under_0_7': sum(1 for r in self.lat_sweep if r['spread_pct'] < 0.7),
            'spread_over_0_7': [(r['label'], r['spread_pct']) for r in self.lat_sweep
                                if r['spread_pct'] >= 0.7]}
        bands = [('l1', 4 * KIB, 24 * KIB), ('l1-edge', 32 * KIB, 32 * KIB),
                 ('l2', 48 * KIB, 128 * KIB), ('cluster', 192 * KIB, 384 * KIB),
                 ('mixed', 512 * KIB, MIB), ('home-nodes', 1536 * KIB, 3 * MIB),
                 ('rising', 4 * MIB, 32 * MIB)]
        self.lat_bands = []
        for key, lo, hi in bands:
            rows = [r for r in sw if lo <= r['size'] <= hi]
            band = {'key': key, 'lo': lo, 'hi': hi, 'n': len(rows), 'boot': 'F1',
                    'label': fmt_size(lo) if lo == hi else '%s to %s' % (fmt_size(lo), fmt_size(hi)),
                    'file': rows[0]['file'], 'line': rows[0]['line'],
                    'best_line': rows[0]['best_line'], 'last_line': rows[-1]['line'],
                    'ns': _rng(r['best'] for r in rows), 'kinds': sorted({r['kind'] for r in rows}),
                    'rows': rows}
            for k in ('l1', 'l2', 'a2') + PF_KEYS:
                band[k] = _rng(v for r in rows for v in r[k + '_reps'])
                band[k + '_best'] = _rng(r[k] for r in rows)
            band['unacc_l2'] = _rng(v for r in rows for v in r['unacc_l2'])
            self.lat_bands.append(band)

        # hit set (boot E), and the check of the L3 hit event on boots B, C, D
        self.lat_hit = []
        id1 = id2 = 0.0
        for r in self.latrows('E', 'latency-dram-small-l3.csv'):
            for k in ('l1', 'l2', 'l2hit', 'l3hit', 'l3acc', 'a2'):
                r[k + '_rng'] = _rng(r[k + '_reps'])
            r['id_access'] = max(abs(x['l3acc'] - x['a2'] - x['l3hit']) for x in r['rep_rows'])
            r['id_l1'] = max(abs(x['l1'] - x['l2hit'] - x['l3acc']) for x in r['rep_rows'])
            r['majority_l3'] = min(r['l3hit_reps']) > 0.5
            id1, id2 = max(id1, r['id_access']), max(id2, r['id_l1'])
            self.lat_hit.append(r)
        self.lat_hit_check = {'id_access_max': id1, 'id_l1_max': id2, 'boots': {}}
        for b in ('E', 'B', 'C', 'D'):
            v = [x['l3hit'] for r in self.latrows(b, 'latency-dram-small-l3.csv')
                 for x in r['rep_rows']]
            self.lat_hit_check['boots'][b] = {'n_rows': len(v), 'l3hit_max': max(v),
                                              'l3hit_min': min(v),
                                              'file': 'latency-dram-small-l3.csv'}

        # L3-served load, est.
        hit = {r['size']: r for r in self.lat_hit}
        e4k = self.sweep_row('E', 4 * KIB)
        e2m = self.sweep_row('E', 2 * MIB)
        tL1, tOUT = e4k['best'], e2m['best']
        tL2 = min((x['ns'] - (1 - x['l1']) * tL1) / x['l1'] for x in hit[96 * KIB]['rep_rows'])
        self.l3_est = []
        for s in (192 * KIB, 256 * KIB, 384 * KIB, 512 * KIB):
            r = hit[s]
            est = [(x['ns'] - (1 - x['l1']) * tL1 - x['l2hit'] * tL2 - x['a2'] * tOUT) / x['l3hit']
                   for x in r['rep_rows']]
            self.l3_est.append({'boot': 'E', 'file': r['file'], 'line': r['line'],
                                'best_line': r['best_line'], 'size': s, 'label': r['label'],
                                'kind': r['kind'], 'est': est, 'est_lo': min(est),
                                'est_hi': max(est), 'tL1': tL1, 'tL2': tL2, 'tOUT': tOUT,
                                'l3_share': r['l3hit_rng'], 'majority_l3': r['majority_l3'],
                                'reps': r['reps']})
        maj = [e for r in self.l3_est if r['majority_l3'] for e in r['est']]
        self.l3_est_summary = {
            'lo': min(maj), 'hi': max(maj),
            'sizes': [r['size'] for r in self.l3_est if r['majority_l3']],
            'tL1': tL1, 'tL1_row': e4k, 'tL2': tL2, 'tL2_row': hit[96 * KIB],
            'tOUT': tOUT, 'tOUT_row': e2m,
            'direct_row': hit[384 * KIB], 'direct_ns': _rng(hit[384 * KIB]['reps']),
            'est_192k': _rng(self.l3_est[0]['est']), 'est_512k': _rng(self.l3_est[3]['est'])}

        # controls and the 2 MiB chain from the four clusters
        ctrl = []
        for cpu in CPUS:
            for i, blk in enumerate(self.latblocks('F1', 'latency-control-cpu%d.csv' % cpu)):
                r = self.latrow('F1', 'latency-control-cpu%d.csv' % cpu, block=i)
                r.update(counted=(i == 0), ns=r['best'],
                         label='control-cpu%d' % cpu if i == 0 else 'control-nocount-cpu%d' % cpu)
                ctrl.append(r)
        chain = []
        r2 = self.sweep_row('F1', 2 * MIB)
        r2['same_command'] = False
        chain.append(r2)
        for cpu in (4, 6, 8):
            r = self.latrow('F1', 'latency-dram-slc-cpu%d.csv' % cpu)
            r['same_command'] = True
            chain.append(r)
        p2 = self.fit_pred(*mean_steps(2))
        for r, cpu in zip(chain, CPUS):
            mx, my = mean_steps(cpu)
            pred = self.fit_pred(mx, my)
            r.update(cpu=cpu, mean_steps_x=mx, mean_steps_y=my, fit_pred=pred,
                     diff_cpu2=r['best'] - r2['best'], fit_diff_cpu2=pred - p2,
                     fit_plus_offset=pred + (r2['best'] - p2), ratio_cpu2=r['best'] / r2['best'],
                     a2_rng=_rng(r['a2_reps']))
        self.lat_cluster = {'control': ctrl, 'chain2m': chain,
                            'control_ns': _rng(r['best'] for r in ctrl if r['counted'])}

        # address order (boots E, C, B)
        self.lat_seq = []
        for b in ('E', 'C', 'B'):
            r = self.latrow(b, 'latency-dram-seq.csv')
            fl_b = self.latrow(b, 'latency-dram-flushed.csv')
            r.update(conditions='L3 %s, prefetchers %s' % (
                'on' if BOOT_COND[b]['l3'] == 'on' else 'holds no data',
                BOOT_COND[b]['prefetchers']),
                l3=BOOT_COND[b]['l3'], prefetchers=BOOT_COND[b]['prefetchers'],
                random_ns=fl_b['best'], random_file=fl_b['file'], random_line=fl_b['line'],
                random_best_line=fl_b['best_line'], random_cycles=fl_b['cycles'],
                ratio=fl_b['best'] / r['best'])
            self.lat_seq.append(r)
        sq = {r['boot']: r['best'] for r in self.lat_seq}
        self.lat_seq_cmp = {'pf_effect': sq['B'] / sq['C'], 'l3_effect': sq['C'] / sq['E'],
                            'b_over_e': sq['B'] / sq['E'],
                            'fetches_in_flight_est': self.lat_seq[0]['random_ns'] / sq['E'],
                            'd_ns': self.latrow('D', 'latency-dram-seq.csv')['best']}

        # random chains with the prefetchers off (boot B against boot F1)
        f1 = {(r['size'], r['kind']): r for r in self.lat_sweep}
        bb = {(r['size'], r['kind']): r for r in self.sweep('B')}
        self.lat_pfoff = []
        for key in f1:
            size, kind = key
            flushed = kind == 'every line flushed first'
            if not flushed and not (size <= 128 * KIB or size >= 1536 * KIB):
                continue
            a, b = f1[key], bb[key]
            self.lat_pfoff.append({
                'boot': 'F1', 'file': a['file'], 'line': a['line'], 'best_line': a['best_line'],
                'b_boot': 'B', 'b_file': b['file'], 'b_line': b['line'],
                'b_best_line': b['best_line'], 'size': size, 'label': a['label'], 'kind': kind,
                'f1_ns': a['best'], 'b_ns': b['best'], 'ratio': b['best'] / a['best'],
                'callout': (not flushed) and size in (32 * KIB, 4 * MIB),
                'f1_l1': a['l1'], 'f1_l1pf': a['l1pf'], 'b_l1': b['l1'], 'b_l1pf': b['l1pf'],
                'f1_a2': a['a2'], 'b_a2': b['a2']})
        plain = [r for r in self.lat_pfoff if not r['callout']
                 and r['kind'] != 'every line flushed first']

        def by_boot(size):
            return {b: self.sweep_row(b, size)['best'] for b in BOOTS}
        self.lat_pfoff_summary = {
            'small': _rng(r['ratio'] for r in plain if r['size'] <= 128 * KIB),
            'large': _rng(r['ratio'] for r in plain if r['size'] >= 1536 * KIB),
            'r32k': next(r['ratio'] for r in self.lat_pfoff if r['size'] == 32 * KIB),
            'r4m': next(r['ratio'] for r in self.lat_pfoff
                        if r['size'] == 4 * MIB and r['callout']),
            'flushed': self.lat_pfoff[-1]['ratio'],
            'ns32k': by_boot(32 * KIB), 'ns4m': by_boot(4 * MIB),
            'ns32k_pf_on': _rng(self.sweep_row(b, 32 * KIB)['best']
                                for b in BOOTS if BOOT_COND[b]['prefetchers'] == 'on'),
            'ns32k_pf_off': _rng(self.sweep_row(b, 32 * KIB)['best']
                                 for b in BOOTS if BOOT_COND[b]['prefetchers'] == 'off'),
            'left_out': [s for s in (192 * KIB, 256 * KIB, 384 * KIB, 512 * KIB, 768 * KIB, MIB)]}

        # the headline figure
        ocm2 = self.latrow('F1', 'latency-ocm-all5-dense-cpu2.csv')
        hl = [('l1', 'L1', self.sweep_row('F1', 4 * KIB)),
              ('l2', 'L2', self.sweep_row('F1', 128 * KIB)),
              ('l3', 'L3 (384 KiB chain)', self.sweep_row('F1', 384 * KIB)),
              ('home-nodes', 'home nodes over the mesh (SLC)', r2),
              ('ocm', 'OCM (every line, all five regions)', ocm2),
              ('dram-model', 'DRAM model (8 MiB, every line flushed first)', fl)]
        self.headline = [{'key': k, 'level': lab, 'ns': r['best'], 'cycles': r['cycles'],
                          'size': r['size'], 'label': r['label'], 'kind': r['kind'],
                          'boot': 'F1', 'file': r['file'], 'line': r['line'],
                          'best_line': r['best_line'], 'row': r} for k, lab, r in hl]

    # ------------------------------------------------------------------ bandwidth tables
    def _fit_bw(self, boot, form, kernel, rows):
        xs = [r['size'] for r in rows]
        ys = [r['ns_pass'] for r in rows]
        f = lstsq([[1.0, x] for x in xs], ys)
        rule = two_pct_rule(f['max_res'], min(ys))
        return {'boot': boot, 'form': form, 'kernel': kernel, 'file': rows[0]['file'],
                'line': rows[0]['line'], 'best_line': rows[0]['best_line'],
                'lines': [r['line'] for r in rows], 'sizes': xs, 'ns_pass': ys,
                'gbps': [r['best'] for r in rows],
                'intercept_ns': f['coef'][0], 'rate': 1.0 / f['coef'][1],
                'rate_bytes_per_cycle': 1.0 / f['coef'][1] / CYCLES_PER_NS,
                'residuals': f['res'], 'max_res': f['max_res'], 'max_res_pct': rule['pct'],
                'limit': rule['limit'], 'valid': rule['valid'],
                'verdict': 'valid' if rule['valid'] else 'void', 'smallest_pass_ns': min(ys)}

    def l1_rows(self, boot):
        """The 16 L1-form rows of a boot (E or C): looped then single-call, each read and write
        at 4, 8, 16, 24 KiB."""
        out = []
        for fn, form in (('bandwidth-l1-passes.csv', 'looped'),
                         ('bandwidth-l1-asmpasses.csv', 'single-call')):
            for r in self._bw[boot][fn]:
                r = dict(r)
                r['l1_refills_pass'] = r['l1'] * r['size'] / LINE
                r['pct_doc'] = 100.0 * r['best'] / DOC[r['kernel'] + '_gbps']
                out.append(r)
        by = {(r['form'], r['kernel'], r['size']): r for r in out}
        for r in out:
            r['diff_ns'] = (by[('looped', r['kernel'], r['size'])]['ns_pass']
                            - by[('single-call', r['kernel'], r['size'])]['ns_pass'])
        return out

    def _build_bandwidth(self):
        one = []
        for r in self._bw['F1']['bandwidth-dram-1core.csv']:
            r = dict(r)
            doc = DOC.get(r['kernel'] + '_gbps')
            r['pct_doc'] = 100.0 * r['best'] / doc if doc else None
            one.append(r)
        self.bw_1core = one
        self._one = {(r['kernel'], r['size']): r for r in one}
        rd = {s: self._one[('read', s)]['best'] for s in (16 * KIB, 48 * KIB, 32 * MIB)}
        wr = [self._one[('write', s)]['best'] for s in sorted({r['size'] for r in one})]
        self.bw_steps = {
            'read_16k_to_48k_pct': 100.0 * (rd[48 * KIB] / rd[16 * KIB] - 1),
            'read_48k_to_32m_pct': 100.0 * (rd[32 * MIB] / rd[48 * KIB] - 1),
            'read_eff_cycles_48k_up': _rng(self._one[('read', s)]['eff_cycles_64']
                                           for s in sorted({r['size'] for r in one})[1:]),
            'write_48k_up': _rng(wr[1:]), 'write_16k': wr[0]}

        self.bw_l1 = self.l1_rows('E')
        self.bw_l1_c = self.l1_rows('C')
        fits = [self._fit_bw('F1', 'looped', 'write',
                             [self._one[('write', s)] for s in
                              (16 * KIB, 48 * KIB, 96 * KIB, 256 * KIB)])]
        extra = []
        for boot, rows in (('E', self.bw_l1), ('C', self.bw_l1_c)):
            for form in ('looped', 'single-call'):
                for k in ('read', 'write'):
                    f = self._fit_bw(boot, form, k, [r for r in rows
                                                     if r['form'] == form and r['kernel'] == k])
                    if boot == 'E' or k == 'write':
                        fits.append(f)
                    else:
                        extra.append(f)
        for f in fits:
            f['role'] = 'caveat' if f['boot'] == 'C' else 'quote'
        self.bw_fit = fits
        self.bw_fit_extra = extra
        self.bw_l1_summary = {
            'diff_read': _rng(r['diff_ns'] for r in self.bw_l1 if r['kernel'] == 'read'),
            'diff_write': _rng(r['diff_ns'] for r in self.bw_l1 if r['kernel'] == 'write'),
            'best_single_read': max((r for r in self.bw_l1 if r['form'] == 'single-call'
                                     and r['kernel'] == 'read'), key=lambda r: r['best']),
            'best_single_write': max((r for r in self.bw_l1 if r['form'] == 'single-call'
                                      and r['kernel'] == 'write'), key=lambda r: r['best']),
            'looped_read_4k': {b: next(r['best'] for r in rows if r['form'] == 'looped'
                                       and r['kernel'] == 'read' and r['size'] == 4 * KIB)
                               for b, rows in (('E', self.bw_l1), ('C', self.bw_l1_c))}}

        self.bw_var = []
        for b in ('E', 'C', 'B'):
            rows = self._bw[b]['bandwidth-read-prefetch.csv']
            plain = {r['size']: r['best'] for r in rows if r['kernel'] == 'read'}
            for r in rows:
                r = dict(r)
                r['ratio_plain'] = r['best'] / plain[r['size']]
                r['change_pct'] = 100.0 * (r['ratio_plain'] - 1)
                r['l3'] = BOOT_COND[b]['l3']
                r['prefetchers'] = BOOT_COND[b]['prefetchers']
                self.bw_var.append(r)
        self._var = {(r['boot'], r['kernel'], r['size']): r for r in self.bw_var}
        p = {b: self._var[(b, 'read', 32 * MIB)]['best'] for b in ('E', 'C', 'B')}
        dmax = max(abs(d['best'] / self._var[('B', d['kernel'], d['size'])]['best'] - 1) * 100
                   for d in self._bw['D']['bandwidth-read-prefetch.csv'])
        self.bw_var_cmp = {'pf_effect': p['C'] / p['B'], 'l3_effect': p['E'] / p['C'],
                           'e_over_b': p['E'] / p['B'], 'd_vs_b_max_pct': dmax,
                           'e_vs_f1_pct': {s: 100.0 * (self._var[('E', 'read', s)]['best']
                                                       / self._one[('read', s)]['best'] - 1)
                                           for s in (2 * MIB, 32 * MIB)}}

        self.stream_chain = []
        for s in (2 * MIB, 32 * MIB):
            ch = self.sweep_row('F1', s)
            r = self._one[('read', s)]
            self.stream_chain.append({
                'boot': 'F1', 'file': r['file'], 'line': r['line'], 'best_line': r['best_line'],
                'chain_file': ch['file'], 'chain_line': ch['line'],
                'chain_best_line': ch['best_line'], 'size': s, 'label': fmt_size(s),
                'chain_ns': ch['best'], 'read_gbps': r['best'], 'ns_per_line': r['ns_per_64'],
                'ratio_est': ch['best'] / r['ns_per_64']})

    def var(self, boot, kernel, size):
        """One read-variant row of boot E, C or B (D.bw_var)."""
        return self._var[(boot, kernel, size)]

    def one_core(self, kernel, size):
        """One row of D.bw_1core, or None."""
        return self._one.get((kernel, size))

    # ------------------------------------------------------------------ multi-core tables
    def _build_multicore(self):
        groups = (('bandwidth-pair.csv', 'pair', 2),
                  ('bandwidth-perdsu.csv', 'one core per cluster', 4),
                  ('bandwidth-all8.csv', 'all eight cores', 8))
        self.mc_rows = []
        for fn, group, thr in groups:
            bylines = {c['line']: c for c in self.commands['F1']['core']}
            for r in self._bw['F1'][fn]:
                r = dict(r)
                cmd = bylines[self.log_line('F1', fn, r['block'])]
                r['log_line'] = cmd['line']
                ref = self._one.get((r['kernel'], r['size']))
                clusters = len({c // 2 for c in cmd['cpus']})
                r.update(group=group, cpus=cmd['cpus'], agg=r['best'], clusters=clusters,
                         cores_per_cluster=thr // clusters,
                         one_core=ref['best'] if ref else None,
                         scaling=r['best'] / ref['best'] if ref else None,
                         efficiency=r['best'] / ref['best'] / thr if ref else None,
                         per_cluster=r['best'] / clusters)
                self.mc_rows.append(r)
        self._mc = {(r['group'], r['kernel'], r['size']): r for r in self.mc_rows}
        self.mc_second_core = []
        for k in ('read', 'write', 'copy'):
            for s in (2 * MIB, 16 * MIB):
                a = self._mc[('one core per cluster', k, s)]
                b = self._mc[('all eight cores', k, s)]
                self.mc_second_core.append({
                    'boot': 'F1', 'file': b['file'], 'line': b['line'],
                    'best_line': b['best_line'], 'kernel': k, 'size': s, 'label': fmt_size(s),
                    'one_per_cluster': a['best'], 'all_eight': b['best'],
                    'gain_pct': 100.0 * (b['best'] / a['best'] - 1)})
        self.mc_writers = []
        for lst in WRITER_LISTS:
            r = dict(self._bw['F1']['bandwidth-write-cpus%s.csv' % lst][0])
            cpus = [int(x) for x in lst.split('-')]
            clusters = len({c // 2 for c in cpus})
            r.update(cpus=cpus, cpus_label=','.join(str(c) for c in cpus), list=lst,
                     mesh_label='write-cpus' + lst, agg=r['best'], clusters=clusters,
                     cores_per_cluster=len(cpus) // clusters, per_cluster=r['best'] / clusters,
                     control='2-4' if len(cpus) == 2 else '2-4-6-8')
            self.mc_writers.append(r)
        by = {r['list']: r for r in self.mc_writers}
        for r in self.mc_writers:
            r['ratio_control'] = r['best'] / by[r['control']]['best']
            r['is_control'] = r['list'] == r['control']
        self.mc_writers_summary = {
            'r2389_over_2345': by['2-3-8-9']['best'] / by['2-3-4-5']['best'],
            'per_cluster_two_writers': {
                'one cluster busy': by['2-3']['per_cluster'],
                'two clusters busy': (by['2-3-4-5']['per_cluster'], by['2-3-8-9']['per_cluster']),
                'four clusters busy': self._mc[('all eight cores', 'write', 16 * MIB)]['per_cluster']},
            'per_cluster_one_writer': _rng(by[l]['per_cluster'] for l in ('2-4', '2-8', '2-4-6-8'))}

    def mc(self, group, kernel, size):
        """One row of D.mc_rows: group 'pair', 'one core per cluster' or 'all eight cores'."""
        return self._mc[(group, kernel, size)]

    # ------------------------------------------------------------------ OCM tables
    def unacc_ocm(self, boot):
        """{cpu: largest 'L2 refills not accounted for' over every pass of the OCM latency files
        of a boot} (files with the TLB or walk set left out). None for boot R3."""
        mx = {}
        for name in self.files[boot]['latency']:
            if not name.startswith('latency-ocm') or 'tlb' in name or 'walk' in name:
                continue
            cpu = int(name.split('cpu')[1][0])
            for blk in self._lat[boot][name]:
                for e in blk['sizes'].values():
                    for r in e['reps']:
                        if 'l2pf' in r:
                            u = r['l2'] - r['l2pf'] - r['l2byl1pf'] - r['a2']
                            mx[cpu] = max(mx.get(cpu, -9.0), u)
        return mx or None

    def _build_ocm(self):
        # all-five rows of boot F1: every line, then one line per page
        self.ocm_all5 = []
        for fn, shape in (('latency-ocm-all5-dense-cpu%d.csv', 'every line'),
                          ('latency-ocm-all5-cpu%d.csv', 'one line per 4 KiB page')):
            for cpu in CPUS:
                r = self.latrow('F1', fn % cpu)
                mx, my = mean_steps(cpu)
                pred = self.fit_pred(mx, my)
                r.update(mean_steps_x=mx, mean_steps_y=my, mean_steps=mx + my, fit_pred=pred,
                         above_fit=r['best'] - pred, n_passes=r['n_reps'],
                         l1_rng=_rng(r['l1_reps']), l2_rng=_rng(r['l2_reps']),
                         a2_rng=_rng(r['a2_reps']), l2pf_rng=_rng(r['l2pf_reps']),
                         unacc_l2_max=max(r['unacc_l2']))
                self.ocm_all5.append(r)
        ev = [r for r in self.ocm_all5 if r['shape'] == 'every line']
        pp = [r for r in self.ocm_all5 if r['shape'] != 'every line']
        self.ocm_all5_summary = {
            'l1': _rng(v for r in ev for v in r['l1_reps']),
            'l2': _rng(v for r in ev for v in r['l2_reps']),
            'a2': _rng(v for r in ev for v in r['a2_reps']),
            'pf_max': max(v for r in ev for k in PF_KEYS for v in r[k + '_reps']),
            'above_fit': _rng(r['above_fit'] for r in ev),
            'every_line': _rng(r['best'] for r in ev),
            'one_line_per_page': _rng(r['best'] for r in pp),
            'cpu8_minus_cpu2': ev[3]['best'] - ev[0]['best'],
            'fit_cpu8_minus_cpu2': ev[3]['fit_pred'] - ev[0]['fit_pred'],
            'minus_2m_chain': {r['cpu']: r['best'] - c['best']
                               for r, c in zip(ev, self.lat_cluster['chain2m'])}}
        by_boot = {}
        for b in BOOTS:
            by_boot[b] = {cpu: self.latrow(b, 'latency-ocm-all5-dense-cpu%d.csv' % cpu)['best']
                          for cpu in (2, 8)}
        self.ocm_all5_by_boot = by_boot

        # one line per page, one region: 20 cells of boot F1
        self.ocm_cells = []
        for cpu in CPUS:
            for reg in range(5):
                r = self.latrow('F1', 'latency-ocm-region%d-cpu%d.csv' % (reg, cpu))
                dx, dy = steps_xy(cpu, reg)
                r.update(region=reg, node=REGION_NODE[reg], steps_x=dx, steps_y=dy,
                         steps=dx + dy, a2_rng=_rng(r['a2_reps']), l2pf_rng=_rng(r['l2pf_reps']),
                         unacc_l2_max=max(r['unacc_l2']), n_passes=r['n_reps'],
                         every_line_ns=ev[CPUS.index(cpu)]['best'])
                self.ocm_cells.append(r)
        f1fit = self._xy_fit(self.ocm_cells)
        f1fit.update(boot='F1', rows='one line per page, one region, 20 cells',
                     file='latency-ocm-region<r>-cpu<c>.csv')
        for c, e in zip(self.ocm_cells, f1fit['res']):
            c['residual'] = e
        self.ocm_fit['F1'] = f1fit
        allp = [x for r in self.ocm_cells for x in r['rep_rows']]
        self.ocm_cells_summary = {
            'best': _rng(r['best'] for r in self.ocm_cells),
            'spread': _rng(r['spread_pct'] for r in self.ocm_cells),
            'a2': _rng(x['a2'] for x in allp), 'a2_mean': sum(x['a2'] for x in allp) / len(allp),
            'l2pf': _rng(x['l2pf'] for x in allp), 'n_passes': len(allp),
            'unacc_by_cpu': {cpu: max(r['unacc_l2_max'] for r in self.ocm_cells if r['cpu'] == cpu)
                             for cpu in CPUS},
            'unacc_max': max(r['unacc_l2_max'] for r in self.ocm_cells),
            'unacc_by_boot': {b: self.unacc_ocm(b) for b in BOOTS},
            'bracket_per_load_est': self.bracket['per_load_64_est']}
        self.ocm_cells_summary['unacc_max_bcd'] = max(
            v for b in ('B', 'C', 'D') for v in self.ocm_cells_summary['unacc_by_boot'][b].values())

        # the fit at the mean steps, and the all-five row against the per-region rows (boot B)
        self.ocm_fit['mean_steps'] = {
            r['cpu']: {'x': r['mean_steps_x'], 'y': r['mean_steps_y'], 'pred': r['fit_pred'],
                       'f1': r['best'], 'diff': r['above_fit']} for r in ev}
        a5 = {}
        for cpu in (2, 8):
            cells = [c['best'] for c in self.ocm_route['B'] if c['cpu'] == cpu]
            row = self.latrow('B', 'latency-ocm-all5-dense-cpu%d.csv' % cpu)
            a5[cpu] = {'boot': 'B', 'file': row['file'], 'line': row['line'],
                       'best_line': row['best_line'], 'all5': row['best'],
                       'mean_cells': sum(cells) / 5.0, 'diff': row['best'] - sum(cells) / 5.0}
        self.ocm_fit['all5_vs_cells'] = a5

        # page mapping: boot D over boot B
        def pair(fn):
            b, d = self.latrow('B', fn), self.latrow('D', fn)
            return {'file': fn, 'b': b['best'], 'd': d['best'], 'ratio': d['best'] / b['best'],
                    'diff': d['best'] - b['best'], 'b_line': b['line'], 'd_line': d['line'],
                    'b_best_line': b['best_line'], 'd_best_line': d['best_line'], 'cpu': b['cpu']}
        grp = [('every line, one region', 'route',
                ['latency-ocm-region%d-route-cpu%d.csv' % (r, c) for c in CPUS for r in range(5)]),
               ('one line per page, one region', 'page',
                ['latency-ocm-region%d-cpu%d.csv' % (r, c) for c in (2, 8) for r in range(5)]),
               ('every line, all five', 'all5-every',
                ['latency-ocm-all5-dense-cpu%d.csv' % c for c in (2, 8)]),
               ('one line per page, all five', 'all5-page',
                ['latency-ocm-all5-cpu%d.csv' % c for c in (2, 8)])]
        self.ocm_pagemap = []
        for name, key, fns in grp:
            cells = [pair(fn) for fn in fns]
            rat = [c['ratio'] for c in cells]
            self.ocm_pagemap.append({
                'group': name, 'key': key, 'boot': 'D', 'b_boot': 'B', 'file': fns[0],
                'line': cells[0]['d_line'], 'best_line': cells[0]['d_best_line'],
                'n': len(cells), 'min': min(rat), 'max': max(rat), 'geo': geomean(rat),
                'n_faster_d': sum(1 for v in rat if v < 1),
                'mean_diff': sum(c['diff'] for c in cells) / len(cells),
                'b': _rng(c['b'] for c in cells), 'd': _rng(c['d'] for c in cells),
                'cells': cells})
        self.ocm_tlb = {}
        for shape, pat in (('every line', 'latency-ocm-region%d-dense-tlb-cpu2.csv'),
                           ('one line per page', 'latency-ocm-region%d-tlb-cpu2.csv')):
            self.ocm_tlb[shape] = {}
            for b in ('B', 'D'):
                v, l2t, wk = [], [], []
                for reg in range(5):
                    for x in self.lat(b, pat % reg)['reps']:
                        v.append(x['l1tlb'] * x['loads'])
                        l2t.append(x['l2tlb'])
                        wk.append(x['walk'])
                self.ocm_tlb[shape][b] = {'boot': b, 'file': pat.replace('%d', '<r>'),
                                          'min': min(v), 'max': max(v), 'mean': sum(v) / len(v),
                                          'n_passes': len(v), 'l2tlb_max': max(l2t),
                                          'walk_max': max(wk)}

        # OCM bandwidth of boot F1
        rd2 = self._one[('read', 2 * MIB)]['best']
        wr2 = self._one[('write', 2 * MIB)]['best']
        self.ocm_bw = []
        names = [('bandwidth-ocm-region%d.csv' % i, 'region %d' % i, i) for i in range(5)] + \
            [('bandwidth-ocm-all5.csv', 'all five regions', None),
             ('bandwidth-ocm-write.csv', 'all five regions, write', None),
             ('bandwidth-ocm-4core.csv', 'four cores, regions 1 to 4', None)]
        for fn, name, reg in names:
            r = dict(self._bw['F1'][fn][0])
            ref = wr2 if r['kernel'] == 'write' else rd2
            r.update(name=name, region=reg, reps_n=r['n_reps'], dram_2m=ref,
                     ratio_dram=r['per_thread'] / ref, ratio_sum=None)
            self.ocm_bw.append(r)
        regs = [r['best'] for r in self.ocm_bw[:5]]
        four = self.ocm_bw[7]
        four['ratio_sum'] = four['best'] / sum(regs[1:])
        self.ocm_bw_summary = {
            'region': _rng(regs), 'region_apart_pct': 100.0 * (max(regs) - min(regs)) / max(regs),
            'read_ratio': self.ocm_bw[5]['ratio_dram'], 'write_ratio': self.ocm_bw[6]['ratio_dram'],
            'four_core_ratio_sum': four['ratio_sum'], 'dram_read_2m': rd2, 'dram_write_2m': wr2,
            'counted_2m_read': self._bw['F1']['bandwidth-dram-spread.csv'][0]['best']}

    # ------------------------------------------------------------------ mesh counters
    @staticmethod
    def _mesh_group(label):
        rules = (
            (r'control-nocount-', 'control, no counters', None),
            (r'control-cpu', 'control', 'latency-control-cpu%s.csv'),
            (r'ocm-region\d-cpu', 'OCM chain, one region', None),
            (r'ocm-all5-dense-cpu', 'OCM chain, every line, all five', None),
            (r'ocm-all5-cpu', 'OCM chain, one line per page, all five', None),
            (r'dram-slc-2M-cpu', '2 MiB chain', None),
            (r'dram-read-2M-cpu', '2 MiB read', None),
            (r'ocm-read-region', 'OCM read, one region', None),
            (r'ocm-read-all5', 'OCM read, all five', None),
            (r'ocm-write-all5', 'OCM write, all five', None),
            (r'ocm-read-4core', 'OCM read, four cores', None),
            (r'write-cpus', '16 MiB writes', None))
        for rx, group, _ in rules:
            if re.match(rx, label):
                return group
        return 'other'

    @staticmethod
    def _mesh_file(label):
        m = re.match(r'control(?:-nocount)?-cpu(\d)$', label)
        if m:
            return 'latency-control-cpu%s.csv' % m.group(1)
        m = re.match(r'ocm-(region\d|all5|all5-dense)-cpu(\d)$', label)
        if m:
            return 'latency-ocm-%s-cpu%s.csv' % (m.group(1), m.group(2))
        m = re.match(r'dram-slc-2M-cpu(\d)$', label)
        if m:
            return 'latency-dram-slc-cpu%s.csv' % m.group(1)
        if label == 'dram-read-2M-cpu2':
            return 'bandwidth-dram-spread.csv'
        m = re.match(r'ocm-read-(region\d|all5)$', label)
        if m:
            return 'bandwidth-ocm-%s.csv' % m.group(1)
        if label == 'ocm-write-all5':
            return 'bandwidth-ocm-write.csv'
        if label == 'ocm-read-4core':
            return 'bandwidth-ocm-4core.csv'
        m = re.match(r'write-cpus([\d-]+)$', label)
        if m:
            return 'bandwidth-write-cpus%s.csv' % m.group(1)
        return None

    def _mesh_row(self, boot, label):
        rows = self.cmn(boot, label)
        nodes = self.cmn_nodes(boot, label)
        group = self._mesh_group(label)
        fn = self._mesh_file(label)
        m = re.search(r'-cpu(\d)$', label)
        cpu = int(m.group(1)) if m else 2
        out = {'boot': boot, 'file': 'cmn-counts.csv', 'line': rows[0]['line'],
               'best_line': None, 'last_line': rows[-1]['line'],
               'node_lines': _rng(r['line'] for r in rows
                                  if r['event'] == 'hns_pocq_reqs_recvd_all') if nodes else None,
               'label': label, 'group': group,
               'csv': fn, 'cpu': cpu, 'nodes': nodes,
               'counts': [nodes.get(n) for n in REGION_NODE] if nodes else None,
               'sum': sum(nodes.values()) if nodes else None,
               'mc': self.cmn_value(boot, label, 'hns_mc_reqs_local_all'),
               'miss': self.cmn_value(boot, label, 'hns_cache_miss_all'),
               'child_ns': self.cmn_value(boot, label, 'child_elapsed_ns'),
               'helper_ns': self.cmn_value(boot, label, 'helper_elapsed_ns'),
               'multiplexed': sum(1 for r in rows if r['enabled_ns'] != r['running_ns']),
               'counted': bool(nodes), 'control': 'control-cpu%d' % cpu,
               'dram_backed': group in ('2 MiB chain', '2 MiB read', '16 MiB writes'),
               'ocm': label.startswith('ocm'), 'region': None, 'own_node': None, 'own': None,
               'others_mean': None, 'others_max': None, 'ratio': None, 'ratio_next': None,
               'own_highest': None, 'shares': None, 'share_spread': None,
               'mc_net': None, 'lines': None, 'passes_cmd': None,
               'mc_net_per_line_pass_est': None}
        m = re.search(r'region(\d)', label)
        if m and nodes:
            reg = int(m.group(1))
            own = nodes[REGION_NODE[reg]]
            oth = [v for k, v in nodes.items() if k != REGION_NODE[reg]]
            out.update(region=reg, own_node=REGION_NODE[reg], own=own,
                       others_mean=sum(oth) / 4.0, others_max=max(oth),
                       ratio=own / (sum(oth) / 4.0), ratio_next=own / max(oth),
                       own_highest=own == max(nodes.values()))
        if nodes:
            s = float(out['sum'])
            sh = [100.0 * nodes[n] / s for n in REGION_NODE]
            out['shares'] = sh
            out['share_spread'] = 100.0 * (max(sh) - min(sh)) / (sum(sh) / 5.0)
        return out

    def _build_mesh_counts(self):
        labels = [l for l in self.cmn_labels('F1') if not l.startswith('cme')]
        self.mesh_cmd = [self._mesh_row('F1', l) for l in labels]
        by = {r['label']: r for r in self.mesh_cmd}
        self._mesh = by
        for r in self.mesh_cmd:
            if not r['counted'] or r['group'].startswith('control'):
                continue
            c = by[r['control']]
            r['mc_net'] = r['mc'] - c['mc']
            r['miss_net'] = r['miss'] - c['miss']
            r['sum_net'] = r['sum'] - c['sum']
            if r['csv'] and r['csv'].startswith('bandwidth-'):
                b = self._bw['F1'][r['csv']][0]
                # fill + per rep (one warm-up pass + the timed passes): from bandwidth.c, so est.
                r['lines'] = b['threads'] * b['size'] // LINE
                r['passes_cmd'] = 1 + b['n_reps'] * (1 + b['passes'])
                r['mc_net_per_line_pass_est'] = r['mc_net'] / float(r['lines'] * r['passes_cmd'])
        self.mesh_ctrl = [r for r in self.mesh_cmd if r['group'].startswith('control')]
        for r in self.mesh_ctrl:
            r['lo'] = min(r['counts']) if r['counts'] else None
            r['hi'] = max(r['counts']) if r['counts'] else None
        dram = [r for r in self.mesh_cmd if r['dram_backed']]
        self.mesh_share = [{'boot': 'F1', 'file': 'cmn-counts.csv', 'line': r['line'],
                            'best_line': None, 'label': r['label'], 'group': r['group'],
                            'shares': r['shares'], 'share_lo': min(r['shares']),
                            'share_hi': max(r['shares']), 'spread': r['share_spread'],
                            'sum': r['sum'], 'mc': r['mc'],
                            'mc_net_per_line_pass_est': r['mc_net_per_line_pass_est']}
                           for r in dram]
        one_reg = [r for r in self.mesh_cmd if r['region'] is not None]
        lat1 = [r for r in one_reg if r['group'] == 'OCM chain, one region']
        bw1 = [r for r in one_reg if r['group'] == 'OCM read, one region']
        ocm1 = [r for r in self.mesh_cmd if r['ocm'] and r['group'] != 'OCM read, four cores']
        counted_ctrl = [r for r in self.mesh_ctrl if r['counted']]
        wr = [r for r in dram if r['group'] == '16 MiB writes']
        bwd = [r for r in dram if r['group'] != '2 MiB chain']
        cm = self._cmn['F1']
        self.mesh_summary = {
            'n_labels': len(self.cmn_labels('F1')), 'n_core_labels': len(labels),
            'n_rows': len(cm), 'n_counted_core': sum(1 for r in self.mesh_cmd if r['counted']),
            'multiplexed': sum(1 for r in cm if r['enabled_ns'] != r['running_ns']),
            'multiplexed_core': sum(r['multiplexed'] for r in self.mesh_cmd),
            'ctrl': _rng(v for r in counted_ctrl for v in r['counts']),
            'ctrl_mc': _rng(r['mc'] for r in counted_ctrl),
            'ctrl_miss': _rng(r['miss'] for r in counted_ctrl),
            'helper_cost_ns': by['control-cpu2']['helper_ns'] - by['control-nocount-cpu2']['helper_ns'],
            'child_diff_ns': by['control-cpu2']['child_ns'] - by['control-nocount-cpu2']['child_ns'],
            'n_one_region': len(one_reg), 'own_highest': sum(1 for r in one_reg if r['own_highest']),
            'ratio_lat': _rng(r['ratio'] for r in lat1), 'ratio_bw': _rng(r['ratio'] for r in bw1),
            'ratio_next_lat': _rng(r['ratio_next'] for r in lat1),
            'n_ocm': len(ocm1), 'ocm_mc': _rng(r['mc'] for r in ocm1),
            'ocm_miss': _rng(r['miss'] for r in ocm1),
            'n_dram': len(dram), 'dram_mc': _rng(r['mc'] for r in dram),
            'share': _rng(v for r in dram for v in r['shares']),
            'share_bw': _rng(v for r in bwd for v in r['shares']),
            'mc_est_read': by['dram-read-2M-cpu2']['mc_net_per_line_pass_est'],
            'mc_est_writes': _rng(r['mc_net_per_line_pass_est'] for r in wr),
            'four_core': by['ocm-read-4core']}
        for w in self.mc_writers:
            m = by[w['mesh_label']]
            w.update(nodes=m['nodes'], node_counts=m['counts'], node_sum=m['sum'], mc=m['mc'],
                     shares=m['shares'], mc_net_per_line_pass_est=m['mc_net_per_line_pass_est'],
                     mesh_line=m['line'], mesh_node_lines=m['node_lines'])

    def mesh_row(self, label, boot='F1'):
        """One row of D.mesh_cmd by its label. boot='R3' builds the same row from boot R3."""
        if boot == 'F1':
            return self._mesh[label]
        return self._mesh_row(boot, label)

    # ------------------------------------------------------------------ open items
    def _build_open(self):
        rows = []

        def add(rid, group, label, unit, a, b, per=1, lower_is_better=False):
            rows.append({'id': rid, 'group': group, 'label': label, 'unit': unit,
                         'boot': 'F1', 'file': a['file'], 'line': a['line'],
                         'best_line': a['best_line'], 'r3_boot': 'R3', 'r3_file': b['file'],
                         'r3_line': b['line'], 'r3_best_line': b['best_line'],
                         'f1': a['best'] / per, 'r3': b['best'] / per,
                         'f1_agg': a['best'], 'r3_agg': b['best'], 'threads': per,
                         'ratio': a['best'] / b['best'], 'lower_is_better': lower_is_better})

        def bwp(fn, kernel=None, size=None):
            pick = lambda b: next(r for r in self._bw[b][fn]
                                  if (kernel is None or r['kernel'] == kernel)
                                  and (size is None or r['size'] == size))
            return pick('F1'), pick('R3')
        for s in (48 * KIB, 96 * KIB, 256 * KIB, 2 * MIB, 32 * MIB):
            add('read-%d' % s, 'one-core read', 'one-core read, ' + fmt_size(s), 'GB/s',
                *bwp('bandwidth-dram-1core.csv', 'read', s))
        add('write-32m', 'one-core write', 'one-core write, 32 MiB', 'GB/s',
            *bwp('bandwidth-dram-1core.csv', 'write', 32 * MIB))
        add('chain-32m', 'chain', '32 MiB chain', 'ns per load',
            self.sweep_row('F1', 32 * MIB), self.sweep_row('R3', 32 * MIB), lower_is_better=True)
        for s in (2 * MIB, 16 * MIB):
            add('four-readers-%d' % s, 'four readers', 'four readers, %s each, per reader'
                % fmt_size(s), 'GB/s', *bwp('bandwidth-perdsu.csv', 'read', s), per=4)
        for s in (2 * MIB, 16 * MIB):
            add('eight-readers-%d' % s, 'eight readers', 'eight readers, %s each, per reader'
                % fmt_size(s), 'GB/s', *bwp('bandwidth-all8.csv', 'read', s), per=8)
        add('ocm-read-all5', 'OCM read', 'OCM read, all five regions', 'GB/s',
            *bwp('bandwidth-ocm-all5.csv'))
        add('ocm-read-4core', 'OCM read', 'OCM read, four cores, per reader', 'GB/s',
            *bwp('bandwidth-ocm-4core.csv'), per=4)
        mf, mr = self.mesh_row('dram-read-2M-cpu2'), self.mesh_row('dram-read-2M-cpu2', 'R3')
        rows.append({'id': 'mesh-read-2m', 'group': 'mesh requests',
                     'label': 'requests received by the five home nodes, 2 MiB read command',
                     'unit': 'requests per command', 'boot': 'F1', 'file': 'cmn-counts.csv',
                     'line': mf['line'], 'best_line': None, 'r3_boot': 'R3',
                     'r3_file': 'cmn-counts.csv', 'r3_line': mr['line'], 'r3_best_line': None,
                     'f1': mf['sum'], 'r3': mr['sum'], 'f1_agg': mf['sum'], 'r3_agg': mr['sum'],
                     'threads': 1, 'ratio': mf['sum'] / float(mr['sum']),
                     'lower_is_better': False})
        self.open_l3 = rows
        regs = []
        for i in range(5):
            a, b = bwp('bandwidth-ocm-region%d.csv' % i)
            regs.append({'region': i, 'boot': 'F1', 'file': a['file'], 'line': a['line'],
                         'best_line': a['best_line'], 'r3_line': b['line'], 'f1': a['best'],
                         'r3': b['best'], 'ratio': a['best'] / b['best']})
        self.open_l3_regions = regs
        allk = []
        for s in sorted({r['size'] for r in self.bw_1core}):
            for k in ('read', 'write', 'copy'):
                a, b = bwp('bandwidth-dram-1core.csv', k, s)
                allk.append({'kernel': k, 'size': s, 'label': fmt_size(s), 'boot': 'F1',
                             'file': a['file'], 'line': a['line'], 'best_line': a['best_line'],
                             'r3_line': b['line'], 'f1': a['best'], 'r3': b['best'],
                             'ratio': a['best'] / b['best']})
        self.open_l3_1core = allk
        wrr = [a['best'] / b['best'] for a, b in
               (bwp('bandwidth-write-cpus%s.csv' % l) for l in WRITER_LISTS)]
        by = {r['id']: r for r in rows}
        self.open_l3_summary = {
            'read': [by['read-%d' % s]['ratio'] for s in
                     (48 * KIB, 96 * KIB, 256 * KIB, 2 * MIB, 32 * MIB)],
            'write_32m': by['write-32m']['ratio'], 'chain_32m': by['chain-32m']['ratio'],
            'four_readers': _rng(by['four-readers-%d' % s]['ratio'] for s in (2 * MIB, 16 * MIB)),
            'eight_readers': _rng(by['eight-readers-%d' % s]['ratio'] for s in (2 * MIB, 16 * MIB)),
            'ocm_regions': _rng(r['ratio'] for r in regs),
            'ocm_all5': by['ocm-read-all5']['ratio'], 'writers': _rng(wrr),
            'mesh_f1': mf['sum'], 'mesh_r3': mr['sum'], 'mesh_ratio': by['mesh-read-2m']['ratio'],
            'child_ns_f1': mf['child_ns'], 'child_ns_r3': mr['child_ns'],
            'r3_columns': self.latblocks('R3', 'latency-dram-small.csv')[0]['columns'],
            'commit_f1': self.boot['F1']['commit'], 'commit_r3': self.boot['R3']['commit']}

        # boots E and C: the L3 as the one difference
        ctr = ('cyc_line', 'l1', 'l1pf', 'l2', 'l2pf', 'l2byl1pf', 'a2')
        self.open_ec = []
        for s in (2 * MIB, 32 * MIB):
            e, c = self._var[('E', 'read', s)], self._var[('C', 'read', s)]
            self.open_ec.append({
                'id': 'read-%d' % s, 'label': 'plain read, ' + fmt_size(s), 'unit': 'GB/s',
                'boot': 'E', 'file': e['file'], 'line': e['line'], 'best_line': e['best_line'],
                'c_boot': 'C', 'c_file': c['file'], 'c_line': c['line'],
                'c_best_line': c['best_line'], 'e': e['best'], 'c': c['best'],
                'l3_gain': e['best'] / c['best'],
                'e_ctr': {k: e[k] for k in ctr}, 'c_ctr': {k: c[k] for k in ctr}})
        sq = {r['boot']: r for r in self.lat_seq}
        e, c = sq['E'], sq['C']
        ctr = ('cycles', 'l1', 'l1pf', 'l2', 'l2pf', 'l2byl1pf', 'a2')
        self.open_ec.append({
            'id': 'seq-8m', 'label': '8 MiB chain in address order', 'unit': 'ns per load',
            'boot': 'E', 'file': e['file'], 'line': e['line'], 'best_line': e['best_line'],
            'c_boot': 'C', 'c_file': c['file'], 'c_line': c['line'],
            'c_best_line': c['best_line'], 'e': e['best'], 'c': c['best'],
            'l3_gain': c['best'] / e['best'],
            'e_ctr': {k: e[k] for k in ctr}, 'c_ctr': {k: c[k] for k in ctr}})

        # which row family exists in which firmware state
        states = [('on', 'on'), ('on', 'off'), ('no data', 'on'), ('no data', 'off')]
        fams = [('footprint sweep', 'latency-dram-small.csv'),
                ('L3 hit set', 'latency-dram-small-l3.csv'),
                ('address-order chain', 'latency-dram-seq.csv'),
                ('2 MiB chain from CPUs 4, 6, 8', 'latency-dram-slc-cpu4.csv'),
                ('OCM chain, every line, all five', 'latency-ocm-all5-dense-cpu2.csv'),
                ('OCM chain, one line per page', 'latency-ocm-region0-cpu2.csv'),
                ('OCM chain, every line, one region', 'latency-ocm-region0-route-cpu2.csv'),
                ('one-core bandwidth sweep', 'bandwidth-dram-1core.csv'),
                ('read variants with counters', 'bandwidth-read-prefetch.csv'),
                ('L1 forms', 'bandwidth-l1-passes.csv'),
                ('multi-core bandwidth', 'bandwidth-perdsu.csv'),
                ('writer placement', 'bandwidth-write-cpus2-3.csv'),
                ('OCM bandwidth', 'bandwidth-ocm-all5.csv'),
                ('home-node request counters', 'event:hns_pocq_reqs_recvd_all'),
                ('crosspoint flit counters', 'event:mxp_e_dat_txflit_valid')]

        def has(b, probe):
            if probe.startswith('event:'):
                return probe[6:] in self.integrity[b]['cmn_events']
            return self.has(b, probe)
        grid = []
        for fam, probe in fams:
            cells = []
            for l3, pf in states:
                bs = [b for b in BOOTS if BOOT_COND[b]['l3'] == l3
                      and BOOT_COND[b]['prefetchers'] == pf and has(b, probe)]
                cells.append(bs or None)
            grid.append({'family': fam, 'probe': probe, 'cells': cells,
                         'by_state': dict(zip(states, cells))})
        self.not_measured = {
            'states': [{'l3': l3, 'prefetchers': pf,
                        'label': 'L3 %s, prefetchers %s' % ('on' if l3 == 'on' else 'holds no data',
                                                            pf),
                        'boots': [b for b in BOOTS if BOOT_COND[b]['l3'] == l3
                                  and BOOT_COND[b]['prefetchers'] == pf]}
                       for l3, pf in states],
            'rows': grid,
            'f2_non_cme_files': sorted(
                f for f in os.listdir(os.path.join(ROOT, 'results', 'membench-jibin-012',
                                                   'results', 'bootF2'))
                if not f.startswith('cme-'))}

    # ------------------------------------------------------------------ command lists of two boots
    def _cmd_lines(self, boot):
        """The command lines of log.txt in order, without the folder of the build and of the boot."""
        return [re.sub(r'cache-mem-perf-[0-9a-f]+|boot[A-Z][0-9A-Z]*', '_', c['text'])
                for c in self.log[boot]['commands']]

    def _build_cmd_cmp(self):
        """cmd_cmp[(a, b)]: the command list of boot a against that of boot b.  'same': equal lists.
        'extra': the 1-based positions of the commands of a that b does not have, when the list of b
        is the list of a without them (else None)."""
        self.cmd_cmp = {}
        for a, b in (('E', 'C'), ('D', 'B'), ('C', 'D'), ('C', 'B'), ('E', 'B'), ('F1', 'R3'), ('F1', 'E')):
            la, lb = self._cmd_lines(a), self._cmd_lines(b)
            extra, j = [], 0
            for i, t in enumerate(la):
                if j < len(lb) and t == lb[j]:
                    j += 1
                else:
                    extra.append(i + 1)
            self.cmd_cmp[(a, b)] = {'a': a, 'b': b, 'n_a': len(la), 'n_b': len(lb), 'same': la == lb,
                                    'extra': extra if j == len(lb) else None,
                                    'commit_a': self.log[a]['commit'], 'commit_b': self.log[b]['commit'],
                                    'same_commit': self.log[a]['commit'] == self.log[b]['commit']}

    # ------------------------------------------------------------------ repeatability
    def _build_cross(self):
        rep = []

        def add(rid, group, label, unit, a, b):
            rep.append({'id': rid, 'group': group, 'label': label, 'unit': unit, 'boot': 'F1',
                        'file': a['file'], 'line': a['line'], 'best_line': a['best_line'],
                        'e_boot': 'E', 'e_file': b['file'], 'e_line': b['line'],
                        'e_best_line': b['best_line'], 'f1': a['best'], 'e': b['best'],
                        'ratio': b['best'] / a['best'], 'size': a['size'],
                        # The reps of the row itself on each boot.  gap > 0: the two rep ranges
                        # do not overlap, and gap is the distance between them (unit of the row).
                        'f1_reps': list(a['reps']), 'e_reps': list(b['reps']),
                        'f1_lo': min(a['reps']), 'f1_hi': max(a['reps']),
                        'e_lo': min(b['reps']), 'e_hi': max(b['reps']),
                        'f1_spread_pct': a['spread_pct'], 'e_spread_pct': b['spread_pct'],
                        'gap': max(min(a['reps']), min(b['reps'])) - min(max(a['reps']), max(b['reps'])),
                        'disjoint': max(min(a['reps']), min(b['reps'])) > min(max(a['reps']), max(b['reps']))})
        for a, b in zip(self.sweep('F1'), self.sweep('E')):
            add('chain-%d-%s' % (a['size'], a['kind'].split()[-1]), a['kind'],
                '%s, %s' % (a['label'], a['kind']), 'ns per load', a, b)
        for cpu in (2, 8):
            fn = 'latency-control-cpu%d.csv' % cpu
            add('control-cpu%d' % cpu, 'background control', 'background control, CPU %d' % cpu,
                'ns per load', self.latrow('F1', fn), self.latrow('E', fn))
        for fn, g in (('latency-ocm-all5-dense-cpu%d.csv', 'OCM, every line, all five'),
                      ('latency-ocm-all5-cpu%d.csv', 'OCM, one line per page, all five')):
            for cpu in (2, 8):
                add('%s-cpu%d' % ('ocm-every' if 'dense' in fn else 'ocm-page', cpu), g,
                    '%s, CPU %d' % (g, cpu), 'ns per load',
                    self.latrow('F1', fn % cpu), self.latrow('E', fn % cpu))
        for s in (2 * MIB, 32 * MIB):
            add('read-%d' % s, 'plain read', 'plain read, ' + fmt_size(s), 'GB/s',
                self._one[('read', s)], self._var[('E', 'read', s)])
        l1 = {(r['form'], r['kernel'], r['size']): r for r in self.bw_l1}
        for k in ('read', 'write'):
            add('looped-16k-' + k, 'looped 16 KiB', 'looped %s, 16 KiB' % k, 'GB/s',
                self._one[(k, 16 * KIB)], l1[('looped', k, 16 * KIB)])
        self.repeat = rep
        order = []
        for r in rep:
            if r['group'] not in order:
                order.append(r['group'])
        self.repeat_groups = []
        for g in order:
            rr = [r for r in rep if r['group'] == g]
            self.repeat_groups.append({'group': g, 'n': len(rr),
                                       'lo': min(r['ratio'] for r in rr),
                                       'hi': max(r['ratio'] for r in rr),
                                       'lo_label': min(rr, key=lambda r: r['ratio'])['label'],
                                       'hi_label': max(rr, key=lambda r: r['ratio'])['label']})
        ch = [r for r in rep if r['id'].startswith('chain-')]
        self.repeat_summary = {
            'n': len(rep), 'small': _rng(r['ratio'] for r in ch
                                         if r['group'] == 'walked many times'),
            'walked_once': _rng(r['ratio'] for r in ch if r['group'] == 'walked once'),
            'flushed': next(r['ratio'] for r in ch if r['group'] == 'every line flushed first'),
            'r768k': next(r['ratio'] for r in ch if r['size'] == 768 * KIB),
            'r4m': next(r['ratio'] for r in ch if r['size'] == 4 * MIB
                        and r['group'] == 'walked once'),
            'n_within_2pct': sum(1 for r in rep if 0.98 <= r['ratio'] <= 1.02),
            'all': _rng(r['ratio'] for r in rep)}

        sw = self.lat_sweep
        groups = [
            ('chains walked many times', [r for r in sw if r['kind'] == 'walked many times']),
            ('chains walked once', [r for r in sw if r['kind'] == 'walked once']),
            ('8 MiB chain, every line flushed first', [self.lat_flushed]),
            ('2 MiB chain from CPUs 4, 6, 8', self.lat_cluster['chain2m'][1:]),
            ('OCM chain, every line, all five',
             [r for r in self.ocm_all5 if r['shape'] == 'every line']),
            ('OCM chain, one line per page, all five',
             [r for r in self.ocm_all5 if r['shape'] != 'every line']),
            ('OCM chain, one line per page, one region', self.ocm_cells),
            ('one-core read', [r for r in self.bw_1core if r['kernel'] == 'read']),
            ('one-core write', [r for r in self.bw_1core if r['kernel'] == 'write']),
            ('one-core copy', [r for r in self.bw_1core if r['kernel'] == 'copy']),
            ('pair', [r for r in self.mc_rows if r['group'] == 'pair']),
            ('one core per cluster', [r for r in self.mc_rows
                                      if r['group'] == 'one core per cluster']),
            ('all eight cores', [r for r in self.mc_rows if r['group'] == 'all eight cores']),
            ('writer placement', self.mc_writers),
            ('OCM bandwidth', self.ocm_bw)]
        self.spread_groups = []
        for g, rr in groups:
            worst = max(rr, key=lambda r: r['spread_pct'])
            self.spread_groups.append({
                'group': g, 'n': len(rr), 'boot': 'F1', 'file': worst['file'],
                'line': worst['line'], 'best_line': worst['best_line'],
                'min': min(r['spread_pct'] for r in rr), 'max': worst['spread_pct'],
                'max_label': ' '.join(str(x) for x in (
                    worst.get('kernel'), worst['label'],
                    ('CPUs ' + worst['cpus_label']) if 'cpus_label' in worst else None,
                    ('CPU %d' % worst['cpu']) if 'cpu' in worst and 'best_ns' in worst
                    and worst['cpu'] != 2 else None) if x),
                'reps': worst['n_reps'],
                'kind': 'latency' if 'best_ns' in worst else 'bandwidth'})


@functools.lru_cache(maxsize=1)
def load():
    """Parse the raw files once and return the data object D."""
    return Data()


TABLES = {
    'boots': '6 rows: the boots, their conditions, command counts, checksums, counter coverage',
    'platform': 'dict: facts parsed from sysinfo.txt, dmesg.txt, log.txt of boot F1 with lines',
    'commands': 'per boot: command counts from log.txt',
    'integrity': 'per boot: checksums, row counts, best-row checks, counter coverage',
    'dmesg_maps': 'per boot: the OCM map lines of dmesg.txt (None for boot R3)',
    'clock': 'per boot: pooled cycles per ns over the timed rows of at least 4,096 loads',
    'bracket': 'boot F1: the bracket overhead lines (bracket_by_boot has every boot)',
    'mesh': 'dict: grid, home nodes, cluster ports from the mesh map',
    'mesh_cells': 'device cells of the mesh map',
    'steps': '20 rows: X steps and Y steps from each CPU to each region (steps_mean per CPU)',
    'lat_sweep': '24 rows: boot F1 footprint sweep (lat_sweep_summary, lat_flushed)',
    'lat_bands': '7 rows: footprint bands with counter ranges',
    'lat_hit': '7 rows: boot E hit-set rows (lat_hit_check)',
    'l3_est': '4 rows: the L3-served load est. per rep (l3_est_summary)',
    'lat_cluster': "dict: 'control' 5 rows, 'chain2m' 4 rows",
    'lat_seq': '3 rows: address-order chain on boots E, C, B (lat_seq_cmp)',
    'lat_pfoff': '18 rows: random chains, boot B against boot F1 (lat_pfoff_summary)',
    'headline': '6 rows: what one dependent load costs, by where the line comes from',
    'repeat': '34 rows: boot E over boot F1 on the shared rows (repeat_groups, repeat_summary)',
    'spread_groups': '15 rows: rep spread inside boot F1 by row group',
    'bw_1core': '18 rows: boot F1 one-core sweep (bw_steps)',
    'bw_fit': '7 rows: straight-line fits with the 2 % rule (bw_fit_extra: 2 void fits of boot C)',
    'bw_l1': '16 rows: boot E L1 forms (bw_l1_c: boot C, bw_l1_summary)',
    'bw_var': '30 rows: read variants on boots E, C, B (bw_var_cmp)',
    'stream_chain': '2 rows: stream over chain est., boot F1 read',
    'mc_rows': '21 rows: pair, one core per cluster, all eight cores',
    'mc_second_core': '6 rows: what the second core of each cluster adds',
    'mc_writers': '6 rows: writer placement with the mesh counts (mc_writers_summary)',
    'ocm_all5': '8 rows: all-five OCM chains of boot F1 (ocm_all5_summary, ocm_all5_by_boot)',
    'ocm_cells': '20 rows: one line per page, one region, boot F1 (ocm_cells_summary)',
    'ocm_route': "dict boot -> 20 rows: every line of one region, boots B, D, E",
    'ocm_fit': 'dict: fits B, D, E, F1, B_one_slope, ports, flits, by_steps, mean_steps, all5_vs_cells',
    'ocm_pagemap': '4 rows: boot D over boot B (ocm_tlb: L1 TLB refills per pass)',
    'ocm_bw': '8 rows: OCM bandwidth of boot F1 (ocm_bw_summary)',
    'mesh_cmd': '51 rows: every core label of cmn-counts.csv of boot F1',
    'mesh_ctrl': '5 rows: the control commands',
    'mesh_share': '10 rows: share per home node of the DRAM-backed commands (mesh_summary)',
    'open_l3': '14 rows: boot F1 against boot R3 (open_l3_regions, open_l3_1core, open_l3_summary)',
    'open_ec': '3 rows: boots E and C, plain read and address-order chain',
    'not_measured': 'dict: row families by firmware state',
    'cmd_cmp': 'dict (boot a, boot b) -> the command lists of two boots compared (same, extra, commits)',
}


# ----------------------------------------------------------------------------- self-test

def selftest(verbose=False):
    D = load()
    n = [0]

    def ok(name, cond, got=None):
        n[0] += 1
        if verbose:
            print('[%03d] %-52s %s' % (n[0], name, got if got is not None else cond))
        assert cond, 'selftest failed: %s (got %r)' % (name, got)

    def near(name, got, want, tol=0.0006):
        ok(name, abs(got - want) <= tol, got)

    def rng(name, got, lo, hi, tol=0.0006):
        ok(name + ' lo', abs(got[0] - lo) <= tol, got[0])
        ok(name + ' hi', abs(got[1] - hi) <= tol, got[1])

    # ---- rules that hold for every boot (critic.md section 6, last paragraph)
    want_boot = {'F1': (137, 67, 70, 88, 247, 57), 'E': (138, 117, 21, 114, 532, 88),
                 'B': (116, 95, 21, 106, 415, 80), 'C': (138, 117, 21, 114, 532, 88),
                 'D': (122, 101, 21, 112, 452, 86), 'R3': (100, 67, 33, 80, 247, 57)}
    for b in BOOTS:
        I, r = D.integrity[b], D.boot[b]
        ok('best rows equal the min, latency, ' + b, I['lat_best_ok'] == I['lat_best_n'] > 0)
        ok('best rows equal the max, bandwidth, ' + b, I['bw_best_ok'] == I['bw_best_n'] > 0)
        ok('perf_cov 1.0000 on all counted rows, ' + b,
           I['cov_min'] == 1.0 and I['cov_max'] == 1.0 and I['cov_none'] == 0
           and I['perf_lines'] == 0)
        ok('checksums ' + b, r['sha_ok'] == r['sha_total'] == want_boot[b][3]
           and not D.verify_sha(b)['bad'], (r['sha_ok'], r['sha_total']))
        ok('commands ' + b, (r['n_cmd'], r['n_core'], r['n_cme']) == want_boot[b][:3],
           (r['n_cmd'], r['n_core'], r['n_cme']))
        ok('failed ' + b, r['n_failed'] == 0)
        ok('coverage rows ' + b, r['cov_rows'] == want_boot[b][4], r['cov_rows'])
        ok('core CSV files ' + b, r['n_core_csv'] == want_boot[b][5], r['n_core_csv'])
        ok('typed L3 state agrees with log.txt, ' + b,
           r['l3_from_log'] in (None, r['l3']), r['l3_from_log'])
        ok('no multiplexed mesh row, ' + b, I['cmn_multiplexed'] == 0)
    ok('F1 best rows', (D.integrity['F1']['lat_best_n'], D.integrity['F1']['bw_best_n']) == (60, 54))
    ok('every core CSV block has its log line',
       all(len(D._cmd_map(b)) == D.commands[b]['n_core'] for b in BOOTS))
    ok('log lines of a CSV file', D.log_lines('F1', 'latency-control-cpu2.csv') == [10, 11]
       and D.log_lines('F1', 'bandwidth-all8.csv') == [70, 72])
    cf, ce = D.commands['F1'], D.commands['E']
    ok('F1 core commands by program and wrapper', (cf['n_core_latency'], cf['n_core_bandwidth'],
                                                   cf['n_core_wrapped']) ==
       (39, 28, {'cmn': 50, 'cmn0': 1, 'xp': 0}), cf['n_core_wrapped'])
    ok('E core commands', (ce['n_core_latency'], ce['n_core_bandwidth'], ce['n_core_other'],
                           ce['n_core_wrapped']['xp']) == (83, 26, 8, 20), ce['n_core_wrapped'])
    ok('mesh node lines of the 2 MiB read', D.mesh_row('dram-read-2M-cpu2')['node_lines'] ==
       (321, 325))
    ok('F1 timed rows', D.integrity['F1']['timed_rows'] == 401, D.integrity['F1']['timed_rows'])
    ok('F1 pwrstat lines', [p['line'] for p in D.boot['F1']['pwrstat_lines']] == [146, 148]
       and D.boot['F1']['pwrstat_values'] == [0x70])
    ok('E pwrstat lines', [p['line'] for p in D.boot['E']['pwrstat_lines']] == [7, 9])
    ok('R3 has no pwrstat line', D.boot['R3']['pwrstat_lines'] == [])
    ok('map lines', [D.boot[b]['map_lines'] for b in BOOTS] == [109, 115, 110, 115, 115, None])
    ok('C1: boots C and D map with the contiguous hint',
       D.boot['C']['map_cont'] == {'64/64': 115} and D.boot['D']['map_cont'] == {'64/64': 115}
       and (D.boot['C']['map_first_line'], D.boot['C']['map_last_line']) == (204, 318))
    ok('F1 maps single 4 KiB entries', D.boot['F1']['map_cont'] == {'0/64': 109})
    ok('commits', [D.boot[b]['commit'] for b in BOOTS] ==
       ['0c190a1', 'b79dffa', '7921962', 'b79dffa', 'ed6056a', 'ba834c0'])
    ok('F1 bandwidth blocks with counters', D.integrity['F1']['bw_blocks_with_counters'] == 0)
    P = D.platform
    ok('cache lines', [c['line'] for c in P['caches']] == [101, 102, 103, 104])
    ok('cache sizes', P['cache_bytes'] == {'L1': 32 * KIB, 'L2': 128 * KIB, 'L3': 256 * KIB})
    ok('OCM ranges', [o['line'] for o in P['ocm_iomem']] == [165, 166, 167, 168, 169]
       and all(o['bytes'] == REGION_BYTES for o in P['ocm_iomem']))
    ok('timer', P['timer']['value'] == 1000.0 and P['timer']['line'] == 76)
    ok('log flags line', P['log_flags']['line'] == 3 and P['log_flags']['value']['spm'] == 0)
    ok('cpu3 lines', [(c['line'], c['online']) for c in P['cpu3']][:2] == [(4, 0), (64, 1)])
    ok('mesh map lines', (P['mesh_map']['line'], P['mesh_map']['last_line']) == (489, 551),
       (P['mesh_map']['line'], P['mesh_map']['last_line']))

    # ---- #11 clock (D2), bracket
    c = D.clock['F1']
    near('#11 clock pooled', c['pooled'], 2.00025, 0.000006)
    ok('#11 clock rows', c['n_rows'] == 79, c['n_rows'])
    rng('#11 clock range', (c['min'], c['max']), 2.0000, 2.0199, 0.00006)
    near('D2 clock is 2.000 cycles per ns', c['pooled'], CYCLES_PER_NS, 0.0006)
    ok('clock rows by boot', [D.clock[b]['n_rows'] for b in BOOTS] == [79, 163, 161, 163, 163, 79])
    br = D.bracket
    ok('bracket', (br['n_cmd'], br['min'], br['median'], br['max'], br['max_file']) ==
       (39, 39.0, 39.0, 59.0, 'latency-ocm-all5-cpu6.csv'), br)
    near('bracket per load of a 64-load row est.', br['per_load_64_est'], 0.61, 0.005)

    # ---- mesh map (D1) and steps
    ok('mesh grid', (D.mesh['grid_x'], D.mesh['grid_y']) == (6, 6))
    ok('mesh devices', D.mesh['device_counts']['HN-S'] == 5 and D.mesh['device_counts']['RN-F'] == 5
       and D.mesh['device_counts']['SBSX'] == 10, D.mesh['device_counts'])
    ok('ports and home nodes are on the map', D.mesh['ports_ok'] and D.mesh['homes_ok'])
    ok('port node ids', [p['node'] for p in D.mesh['ports']] == [152, 208, 280, 336, 80])
    ok('D1 fifth port id 80', D.mesh['ports'][4]['node'] == 80 and not D.mesh['ports'][4]['used'])
    ok('steps CPU 2', [(s['dx'], s['dy']) for s in D.steps if s['cpu'] == 2] ==
       [(1, 0), (0, 1), (1, 0), (2, 1), (3, 0)])
    ok('steps CPU 8', [(s['dx'], s['dy']) for s in D.steps if s['cpu'] == 8] ==
       [(4, 1), (3, 2), (2, 1), (1, 2), (0, 1)])
    ok('mean steps', [(D.steps_mean[c]['x'], D.steps_mean[c]['y']) for c in CPUS] ==
       [(1.4, 0.4), (1.2, 1.4), (1.4, 0.4), (2.0, 1.4)])

    # ---- #1 to #3, #6, #8, #9, #12: the sweep
    sw = {(r['size'], r['kind'] == 'every line flushed first'): r for r in D.lat_sweep}
    ok('sweep rows', len(D.lat_sweep) == 24)
    r = sw[(4 * KIB, False)]
    ok('#1 L1 chain load', (r['best'], r['cycles'], r['line'], r['best_line']) ==
       (2.002, 4.01, 5, 8), (r['best'], r['cycles'], r['line']))
    r = sw[(128 * KIB, False)]
    ok('#2 128 KiB chain', (r['best'], r['cycles'], r['line']) == (6.014, 12.03, 45))
    near('#2 L1 refills per load', r['l1'], 0.9861, 0.00006)
    r = sw[(384 * KIB, False)]
    ok('#3 384 KiB chain', (r['best'], r['cycles'], r['reps'], r['line'], r['best_line']) ==
       (10.986, 21.98, [12.004, 11.054, 10.986], 62, 63), r['reps'])
    near('#3 spread', r['spread_pct'], 9.27, 0.006)
    near('C10 refills from outside at 384 KiB', r['a2'], 0.0297, 0.00006)
    r = sw[(2 * MIB, False)]
    ok('#6 2 MiB chain', (r['best'], r['line']) == (23.714, 22))
    near('#6 L3 read refills', r['a2'], 0.9817, 0.00006)
    r = D.lat_flushed
    ok('#8 DRAM-model row', (r['best'], r['cycles'], r['reps'], r['line'], r['best_line']) ==
       (52.658, 105.32, [52.658, 52.658], 5, 7))
    ok('#9 32 MiB and 8 MiB walked once', (sw[(32 * MIB, False)]['best'], sw[(32 * MIB, False)]['line'],
                                          sw[(8 * MIB, False)]['best'], sw[(8 * MIB, False)]['line'])
       == (52.212, 45, 44.485, 37))
    ok('#12 spread under 0.7 % on 21 of 24', D.lat_sweep_summary['n_spread_under_0_7'] == 21)
    near('#12 spread 512 KiB', sw[(512 * KIB, False)]['spread_pct'], 2.79, 0.006)
    near('#12 spread 768 KiB', sw[(768 * KIB, False)]['spread_pct'], 4.44, 0.006)
    u = sw[(192 * KIB, False)]['unacc_l2']
    ok('unaccounted L2 refills at 192 KiB', all(abs(a - b) < 0.00006 for a, b in
                                                 zip(u, (0.4612, 0.4696, 0.4672))), u)
    u = sw[(384 * KIB, False)]['unacc_l2']
    ok('unaccounted L2 refills at 384 KiB', all(abs(a - b) < 0.00006 for a, b in
                                                 zip(u, (0.8327, 0.9215, 0.9051))), u)
    ok('bands', len(D.lat_bands) == 7 and sum(b['n'] for b in D.lat_bands) == 23)
    rng('band 1.5 to 3 MiB ns', D.lat_bands[5]['ns'], 23.502, 25.157)
    near('C7 L2 prefetch refills at 512 KiB', sw[(512 * KIB, False)]['l2pf'], 0.0830, 0.00006)
    ok('C7 prefetch refills 0.0000 from 768 KiB up',
       all(max(r[k + '_reps']) < 0.00005 for r in D.lat_sweep if r['size'] >= 768 * KIB
           and r['kind'] == 'walked once' for k in PF_KEYS))

    # ---- #4, #5: the hit set and the L3 estimate (C9)
    hit = {r['size']: r for r in D.lat_hit}
    ok('hit rows', len(D.lat_hit) == 7)
    rng('#4 L3 hits 192 KiB', hit[192 * KIB]['l3hit_rng'], 0.4651, 0.4708, 0.00006)
    rng('#4 L3 hits 256 KiB', hit[256 * KIB]['l3hit_rng'], 0.7508, 0.7712, 0.00006)
    rng('#4 L3 hits 384 KiB', hit[384 * KIB]['l3hit_rng'], 0.9152, 0.9236, 0.00006)
    rng('C9 384 KiB row ns', D.l3_est_summary['direct_ns'], 10.906, 11.147)
    rng('C9 384 KiB L2 hits', hit[384 * KIB]['l2hit_rng'], 0.0466, 0.0569, 0.00006)
    rng('C9 384 KiB refills from outside', hit[384 * KIB]['a2_rng'], 0.0198, 0.0315, 0.00006)
    ok('C9 identities within 0.0003', D.lat_hit_check['id_access_max'] <= 0.00015
       and D.lat_hit_check['id_l1_max'] <= 0.00035, D.lat_hit_check)
    ok('C9 L3 hits 0.0000 in 21 rows of B, C, D',
       all(D.lat_hit_check['boots'][b] == dict(D.lat_hit_check['boots'][b], n_rows=21,
                                               l3hit_max=0.0) for b in ('B', 'C', 'D')))
    ok('C9 512 KiB hit row is walked many times', hit[512 * KIB]['kind'] == 'walked many times'
       and sw[(512 * KIB, False)]['kind'] == 'walked once')
    s = D.l3_est_summary
    near('#5 tL1', s['tL1'], 2.002)
    near('#5 tL2 est.', s['tL2'], 6.003)
    near('#5 tOUT', s['tOUT'], 24.177)
    rng('#5 L3-served load est.', (s['lo'], s['hi']), 10.62, 10.96, 0.006)
    rng('#5 192 KiB est.', s['est_192k'], 9.89, 9.92, 0.006)
    rng('C9 512 KiB est.', s['est_512k'], 10.65, 10.92, 0.006)
    ok('l3_est rows', [r['majority_l3'] for r in D.l3_est] == [False, True, True, False])

    # ---- #7, #10: the other clusters (C8)
    ch = D.lat_cluster['chain2m']
    ok('#7 2 MiB chain by CPU', [r['best'] for r in ch] == [23.714, 24.828, 24.390, 26.202])
    ok('#7 lines', [r['line'] for r in ch] == [22, 5, 5, 5])
    ok('#10 background control', [r['best'] for r in D.lat_cluster['control'] if r['counted']] ==
       [2.015, 2.016, 2.017, 2.020])
    ok('controls', len(D.lat_cluster['control']) == 5
       and all(r['line'] in (5, 11) for r in D.lat_cluster['control']))
    near('C8 CPU 8 measured', ch[3]['diff_cpu2'], 2.488)
    near('C8 CPU 8 from the fit', ch[3]['fit_diff_cpu2'], 2.149)
    near('C8 CPU 6 measured', ch[2]['diff_cpu2'], 0.676)
    near('C8 CPU 4 measured', ch[1]['diff_cpu2'], 1.114)
    near('C8 CPU 4 from the fit', ch[1]['fit_diff_cpu2'], 0.553)

    # ---- #13: boot E over boot F1
    q = D.repeat_summary
    ok('repeat rows', len(D.repeat) == 34 and [g['n'] for g in D.repeat_groups] ==
       [12, 11, 1, 2, 2, 2, 2, 2], [g['n'] for g in D.repeat_groups])
    rng('#13 E over F1, 12 rows', q['small'], 0.9995, 1.0019, 0.00006)
    near('#13 flushed', q['flushed'], 1.0000, 0.00006)
    rng('#13 walked once', q['walked_once'], 0.964, 1.102)
    near('G1 768 KiB', q['r768k'], 1.102)
    near('G1 4 MiB', q['r4m'], 0.964)
    # The reps of the row itself on each boot: a ratio of two best rows is judged against them.
    rp = {r['id']: r for r in D.repeat}
    p2, p8 = rp['ocm-page-cpu2'], rp['ocm-page-cpu8']
    ok('own reps: CPU 2 one line per page, boot F1 reps', (p2['f1_lo'], p2['f1_hi']) == (23.700, 24.641))
    ok('own reps: CPU 2 one line per page, boot E reps', (p2['e_lo'], p2['e_hi']) == (25.013, 26.825))
    near('own reps: CPU 2 one line per page, gap', p2['gap'], 0.372)
    near('own reps: CPU 2 spread on boot F1', p2['f1_spread_pct'], 3.970)
    near('own reps: CPU 2 spread on boot E', p2['e_spread_pct'], 7.244)
    ok('own reps: CPU 2 ranges do not overlap', p2['disjoint'])
    ok('own reps: CPU 8 ranges overlap', not p8['disjoint'] and p8['gap'] < 0)
    ok('own reps: CPU 8 one line per page reps', (p8['f1_lo'], p8['f1_hi'], p8['e_lo'], p8['e_hi']) ==
       (26.334, 27.122, 25.634, 26.491))
    near('own reps: CPU 2 every line, gap', rp['ocm-every-cpu2']['gap'], 0.543)
    ok('own reps: gap sign equals disjoint', all((r['gap'] > 0) == r['disjoint'] for r in D.repeat))
    # The command lists and builds of two boots: what differs beside the condition under test.
    cc = D.cmd_cmp
    ok('builds and commands: boots E and C: one build, one command list',
       cc[('E', 'C')]['same'] and cc[('E', 'C')]['same_commit'] and cc[('E', 'C')]['n_a'] == 138)
    ok('builds and commands: boot D: six commands that boot B does not have',
       cc[('D', 'B')]['extra'] == [40, 41, 42, 43, 44, 45] and not cc[('D', 'B')]['same_commit'],
       cc[('D', 'B')]['extra'])
    ok('builds and commands: boot C: the commands of boot D and 16 more',
       cc[('C', 'D')]['extra'] == list(range(123, 139)), cc[('C', 'D')]['extra'])
    ok('builds and commands: boot C against boot B', cc[('C', 'B')]['extra'] == [40, 41, 42, 43, 44, 45] + list(range(123, 139))
       and not cc[('C', 'B')]['same_commit'], cc[('C', 'B')]['extra'])
    ok('builds and commands: boot F1 against boot E: other builds, other command lists',
       not cc[('F1', 'E')]['same'] and cc[('F1', 'E')]['extra'] is None and not cc[('F1', 'E')]['same_commit'])
    ok('builds and commands: boot F1 against boot R3', not cc[('F1', 'R3')]['same_commit'], cc[('F1', 'R3')])

    # ---- #14: address order (C6)
    sq = {r['boot']: r for r in D.lat_seq}
    ok('#14 address order', [sq[b]['best'] for b in ('E', 'C', 'B')] == [2.492, 6.917, 52.762])
    ok('#14 L1 prefetch refills', [sq[b]['l1pf'] for b in ('E', 'C', 'B')] == [0.9997, 0.9999, 0.0])
    ok('#14 lines', all(sq[b]['line'] in (5, 6) for b in sq))
    near('C6 prefetchers, L3 holding no data', D.lat_seq_cmp['pf_effect'], 7.63, 0.006)
    near('C6 L3 step', D.lat_seq_cmp['l3_effect'], 2.78, 0.006)
    near('C6 B over E', D.lat_seq_cmp['b_over_e'], 21.17, 0.006)
    ok('L5 gaps', ['%.2f' % sq[b]['ratio'] for b in ('E', 'C', 'B')] == ['21.13', '7.61', '1.00'],
       [sq[b]['ratio'] for b in sq])
    near('C7 0xA2 on the address-order chain of E', sq['E']['a2'], 0.0001, 0.00006)

    # ---- #15: random chains, boot B over boot F1 (C8)
    p = D.lat_pfoff_summary
    ok('lat_pfoff rows', len(D.lat_pfoff) == 18 and sum(1 for r in D.lat_pfoff if r['callout']) == 2)
    rng('#15 4 to 128 KiB', p['small'], 0.9965, 1.0067, 0.00006)
    near('#15 32 KiB', p['r32k'], 0.9594, 0.00006)
    rng('#15 1.5 to 32 MiB', p['large'], 1.0007, 1.0192, 0.00006)
    near('#15 4 MiB', p['r4m'], 0.9585, 0.00006)
    near('#15 flushed', p['flushed'], 1.0015, 0.00006)
    r32 = next(r for r in D.lat_pfoff if r['size'] == 32 * KIB)
    ok('C8 32 KiB', (r32['f1_ns'], r32['b_ns']) == (2.117, 2.031))
    near('C8 32 KiB L1 refills F1', r32['f1_l1'], 0.040, 0.0006)
    near('C8 32 KiB L1 refills B', r32['b_l1'], 0.009, 0.0006)
    rng('C8 32 KiB prefetchers on', p['ns32k_pf_on'], 2.108, 2.121)
    rng('C8 32 KiB prefetchers off', p['ns32k_pf_off'], 2.031, 2.036)

    # ---- #16 to #19: one-core bandwidth
    o = D.one_core
    r = o('read', 16 * KIB)
    ok('#16 read 16 KiB', (r['best'], r['line'], r['best_line']) == (56.085, 6, 7))
    near('#16 bytes per cycle', r['bytes_per_cycle'], 28.04, 0.006)
    near('#16 % of documented', r['pct_doc'], 87.6, 0.06)
    ok('#16 read sweep', [o('read', s)['best'] for s in
                          (48 * KIB, 96 * KIB, 256 * KIB, 2 * MIB, 32 * MIB)] ==
       [27.299, 26.877, 26.297, 25.044, 24.575])
    ok('#16 read lines', [o('read', s)['line'] for s in
                          (48 * KIB, 96 * KIB, 256 * KIB, 2 * MIB, 32 * MIB)] == [19, 35, 51, 66, 79])
    rng('#16 effective cycles per 64 bytes', D.bw_steps['read_eff_cycles_48k_up'], 4.69, 5.21, 0.006)
    ok('#17 write 16 KiB', o('write', 16 * KIB)['best'] == 30.608)
    rng('#17 write 48 KiB to 32 MiB', D.bw_steps['write_48k_up'], 31.437, 31.997)
    near('#17 effective cycles at 32 MiB', o('write', 32 * MIB)['eff_cycles_64'], 4.000)
    ok('#17 write lines', [o('write', s)['line'] for s in
                           (16 * KIB, 48 * KIB, 96 * KIB, 256 * KIB, 2 * MIB, 32 * MIB)] ==
       [9, 25, 40, 55, 70, 84])
    ok('#18 copy', (o('copy', 16 * KIB)['best'], o('copy', 32 * MIB)['best'],
                    o('copy', 16 * KIB)['line'], o('copy', 32 * MIB)['line']) ==
       (39.433, 31.438, 12, 87))
    ok('#19 documented', (D.doc['read_gbps'], D.doc['write_gbps']) == (64.0, 32.0))
    near('B1 read -51 % from 16 to 48 KiB', D.bw_steps['read_16k_to_48k_pct'], -51.3, 0.06)
    near('B1 read -10 % to 32 MiB', D.bw_steps['read_48k_to_32m_pct'], -10.0, 0.06)
    near('C13 write % of documented at 32 MiB', o('write', 32 * MIB)['pct_doc'], 99.99, 0.006)

    # ---- #20 to #23: fits and L1 forms (C14)
    fit = {(f['boot'], f['form'], f['kernel']): f for f in D.bw_fit}
    ok('fit rows', len(D.bw_fit) == 7 and len(D.bw_fit_extra) == 2)
    f = fit[('F1', 'looped', 'write')]
    near('#20 F1 write intercept', f['intercept_ns'], 25.12, 0.006)
    near('#20 F1 write rate', f['rate'], 31.982)
    near('#20 largest residual', f['max_res'], 2.12, 0.006)
    near('#20 limit', f['limit'], 10.71, 0.006)
    ok('#20 valid', f['valid'])
    f = fit[('E', 'looped', 'write')]
    near('#21 E looped write intercept', f['intercept_ns'], 25.70, 0.006)
    near('#21 E looped write rate', f['rate'], 32.016)
    near('#21 E looped write residual %', f['max_res_pct'], 0.28, 0.006)
    ok('#21 E looped write valid', f['valid'])
    f = fit[('E', 'single-call', 'write')]
    near('#21 E single-call write intercept', f['intercept_ns'], 13.97, 0.006)
    near('#21 E single-call write rate', f['rate'], 32.108)
    near('#21 E single-call write residual %', f['max_res_pct'], 0.73, 0.006)
    ok('#21 E single-call write valid', f['valid'])
    f = fit[('E', 'looped', 'read')]
    near('#21 E looped read residual %', f['max_res_pct'], 2.93, 0.006)
    ok('#21 E looped read fit fails the 2 % rule', not f['valid'] and f['verdict'] == 'void')
    f = fit[('E', 'single-call', 'read')]
    near('#21 E single-call read residual %', f['max_res_pct'], 2.14, 0.006)
    ok('#21 E single-call read fit fails the 2 % rule', not f['valid'])
    near('C14 boot C looped write intercept', fit[('C', 'looped', 'write')]['intercept_ns'],
         23.71, 0.006)
    near('C14 boot C single-call write intercept',
         fit[('C', 'single-call', 'write')]['intercept_ns'], 9.05, 0.006)
    ok('C14 boot C read fits void', all(not f['valid'] for f in D.bw_fit_extra))
    rng('#22 looped minus single-call, read', D.bw_l1_summary['diff_read'], 20.95, 23.58, 0.006)
    rng('#22 looped minus single-call, write', D.bw_l1_summary['diff_write'], 11.96, 14.73, 0.006)
    b = D.bw_l1_summary['best_single_read']
    ok('#23 best single-call read', (b['best'], b['size']) == (60.586, 24 * KIB))
    near('#23 read % of documented', b['pct_doc'], 94.7, 0.06)
    b = D.bw_l1_summary['best_single_write']
    ok('#23 best single-call write', (b['best'], b['size']) == (31.558, 24 * KIB))
    near('#23 write % of documented', b['pct_doc'], 98.6, 0.06)
    ok('L1 rows', len(D.bw_l1) == 16 and all(r['n_reps'] == 5 for r in D.bw_l1))
    ok('O7 4 KiB looped read on E and C', D.bw_l1_summary['looped_read_4k'] ==
       {'E': 40.910, 'C': 46.180})

    # ---- #24, #25: read variants (C6, C7)
    v = D.var
    ok('var rows', len(D.bw_var) == 30)
    ok('#24 plain 32 MiB read', [v(b, 'read', 32 * MIB)['best'] for b in ('E', 'C', 'B')] ==
       [24.546, 9.196, 2.377])
    ok('#24 L1 prefetch refills per line',
       [v(b, 'read', 32 * MIB)['l1pf'] for b in ('E', 'C', 'B')] == [0.9994, 0.9994, 0.0])
    ok('#24 lines', all(v(b, 'read', 32 * MIB)['line'] in (39, 40, 41)
                        and v(b, 'read', 32 * MIB)['best_line'] == 42 for b in ('E', 'C', 'B')))
    near('C6 prefetchers 3.87 times', D.bw_var_cmp['pf_effect'], 3.87, 0.006)
    near('C6 L3 2.67 times', D.bw_var_cmp['l3_effect'], 2.67, 0.006)
    ks = ('read-pf4', 'read-pf8', 'read-pf16', 'read-2s')
    for k, w in zip(ks, (-17.1, -24.7, -25.5, -23.0)):
        near('#25 E ' + k, v('E', k, 32 * MIB)['change_pct'], w, 0.06)
    for k, w in zip(ks, (2.665, 2.400, 2.069, 0.997)):
        near('#25 B ' + k, v('B', k, 32 * MIB)['ratio_plain'], w)
    ok('C7 0xA2 on the plain read of boot C', max(v('C', 'read', s)['a2'] for s in
                                                  (2 * MIB, 32 * MIB)) <= 0.0008)
    near('S5 boot D within 0.48 % of boot B', D.bw_var_cmp['d_vs_b_max_pct'], 0.48, 0.006)

    # ---- #26: stream over chain (C17)
    sc = {r['size']: r for r in D.stream_chain}
    near('#26 32 MiB est.', sc[32 * MIB]['ratio_est'], 20.0, 0.06)
    near('#26 2 MiB est.', sc[2 * MIB]['ratio_est'], 9.3, 0.06)

    # ---- #27 to #31: multi-core
    ok('mc rows', len(D.mc_rows) == 21)
    m = D.mc
    g = 'one core per cluster'
    ok('#27 one core per cluster', [m(g, k, 2 * MIB)['best'] for k in ('read', 'write', 'copy')] ==
       [100.200, 127.919, 125.331])
    for k, w in zip(('read', 'write', 'copy'), (4.001, 4.000, 3.984)):
        near('#27 scaling ' + k, m(g, k, 2 * MIB)['scaling'], w)
    g = 'all eight cores'
    ok('#28 all eight cores', [m(g, k, 2 * MIB)['best'] for k in ('read', 'write', 'copy')] ==
       [108.733, 165.154, 142.036])
    for k, w in zip(('read', 'write', 'copy'), (4.342, 5.164, 4.515)):
        near('#28 scaling ' + k, m(g, k, 2 * MIB)['scaling'], w)
    sec = {(r['kernel'], r['size']): r['gain_pct'] for r in D.mc_second_core}
    for (k, s), w in zip((('read', 2 * MIB), ('read', 16 * MIB), ('copy', 2 * MIB),
                          ('copy', 16 * MIB), ('write', 2 * MIB), ('write', 16 * MIB)),
                         (8.5, 9.7, 13.3, 12.5, 29.1, 19.5)):
        near('#29 second core %s %s' % (k, fmt_size(s)), sec[(k, s)], w, 0.06)
    ok('#30 writers', [r['best'] for r in D.mc_writers] ==
       [63.985, 63.987, 40.949, 127.965, 85.833, 84.184])
    ok('#30 writer lines', all(r['best_line'] == 6 and r['line'] in (4, 5) for r in D.mc_writers))
    wr = {r['list']: r for r in D.mc_writers}
    for l, w in (('2-3', 0.640), ('2-3-4-5', 0.671), ('2-3-8-9', 0.658)):
        near('#30 ratio ' + l, wr[l]['ratio_control'], w)
    ws = D.mc_writers_summary['per_cluster_two_writers']
    ok('C5 rate per cluster with two writers',
       ['%.3f' % x for x in (ws['one cluster busy'],) + ws['two clusters busy']
        + (ws['four clusters busy'],)] == ['40.949', '42.916', '42.092', '38.241'])
    g = 'pair'
    for k, s, a, sc_ in (('read', 16 * KIB, 112.409, 2.004), ('read', 48 * KIB, 43.135, 1.580),
                         ('write', 16 * KIB, 60.755, 1.985), ('write', 48 * KIB, 61.943, 1.970),
                         ('copy', 16 * KIB, 79.106, 2.006), ('copy', 48 * KIB, 45.920, 1.338)):
        ok('#31 pair %s %s' % (k, fmt_size(s)), m(g, k, s)['best'] == a)
        near('#31 pair scaling %s %s' % (k, fmt_size(s)), m(g, k, s)['scaling'], sc_)
    ok('TM3 160 KiB rows have no one-core row',
       all(m(g, k, 160 * KIB)['one_core'] is None for k in ('read', 'write', 'copy')))
    ok('cpus of the multi-core rows', m('pair', 'read', 16 * KIB)['cpus'] == [2, 3]
       and m('all eight cores', 'read', 2 * MIB)['cpus'] == [2, 3, 4, 5, 6, 7, 8, 9])

    # ---- #32, #33: OCM chains of boot F1 (C7, C8)
    ev = [r for r in D.ocm_all5 if r['shape'] == 'every line']
    ok('#32 OCM row', [r['best'] for r in ev] == [25.536, 25.932, 25.445, 27.702])
    ok('#32 lines', all(r['line'] in (5, 6) and r['best_line'] == 7 for r in ev))
    a = D.ocm_all5_summary
    rng('#32 L1 refills', a['l1'], 1.0004, 1.0007, 0.00006)
    rng('#32 L2 refills', a['l2'], 1.0003, 1.0006, 0.00006)
    rng('#32 L3 read refills', a['a2'], 1.0005, 1.0012, 0.00006)
    ok('#32 prefetch refills 0.0000', a['pf_max'] < 0.00005, a['pf_max'])
    rng('C8 above the fit of boot B', a['above_fit'], 1.45, 1.63, 0.006)
    cs = D.ocm_cells_summary
    ok('cells', len(D.ocm_cells) == 20 and cs['n_passes'] == 140)
    rng('#33 one line per page, 20 cells', cs['best'], 17.266, 22.609)
    rng('#33 spread', cs['spread'], 19.9, 59.7, 0.06)
    rng('#33 all five', a['one_line_per_page'], 23.700, 26.334)
    rng('C7 L2 prefetch refills per load', cs['l2pf'], 1.00, 3.28, 0.006)
    rng('C7 L3 read refills per load', cs['a2'], 0.20, 1.12, 0.006)
    near('C7 unaccounted L2 refills', cs['unacc_max'], 0.48, 0.006)
    near('D4 at most 0.0156 on boots B, C, D', cs['unacc_max_bcd'], 0.0156, 0.00006)
    ok('O6 unaccounted by CPU', ['%.3f' % cs['unacc_by_cpu'][c] for c in (4, 6, 8)] ==
       ['0.484', '0.469', '0.453'])
    ok('fit of the F1 cells is void', not D.ocm_fit['F1']['valid'])

    # ---- #34, #35: boot B per-region rows and the fit (C2, C23, D7)
    fb = D.ocm_fit['B']
    rng('#34 per-region rows, boot B', (fb['smallest'], fb['largest']), 21.697, 29.804)
    near('#35 fit a', fb['a'], 20.752)
    near('#35 fit per X step', fb['bx'], 1.994)
    near('#35 fit per Y step', fb['cy'], 0.952)
    near('#35 rms', fb['rms'], 0.095)
    near('#35 largest residual', fb['max_res'], 0.173)
    near('#35 residual %', fb['pct_of_smallest'], 0.80, 0.006)
    ok("#35 boot B's fit passes the 2 % rule", fb['valid'])
    ok("boot D's fit fails the 2 % rule", not D.ocm_fit['D']['valid'])
    near('boot D residual %', D.ocm_fit['D']['pct_of_smallest'], 2.14, 0.006)
    ok("boot E's fit is void", not D.ocm_fit['E']['valid'])
    rng('S7b boot E L2 prefetch refills per load', D.ocm_fit['E']['l2pf'], 0.16, 0.65, 0.006)
    near('#35 one slope rms', D.ocm_fit['B_one_slope']['rms'], 0.643)
    pt = D.ocm_fit['ports']
    ok('C2 documented ports rank 1 of 120', pt['rank'] == 1 and pt['n_perm'] == 120)
    near('C2 second best rms', pt['second_rms'], 1.085)
    ok('C2 flit directions 20 of 20', D.ocm_fit['flits']['B'] ==
       dict(D.ocm_fit['flits']['B'], n=20, cluster_ok=20, node_ok=20))
    ok('boot B route rows count no prefetch refill', fb['pf_max'] == 0.0)
    near('D7 all five above the mean of five, CPU 2', D.ocm_fit['all5_vs_cells'][2]['diff'], 1.70,
         0.006)
    near('D7 all five above the mean of five, CPU 8', D.ocm_fit['all5_vs_cells'][8]['diff'], 1.59,
         0.006)
    ok('route cells', len(D.ocm_route['B']) == 20 and len(D.ocm_route['D']) == 20
       and all(c['line'] in (5, 6) for c in D.ocm_route['B']))

    # ---- #36: page mapping
    pm = {r['key']: r for r in D.ocm_pagemap}
    near('#36 every line, 20 cells', pm['route']['geo'], 0.996)
    ok('#36 cells', pm['route']['n'] == 20 and pm['page']['n'] == 10)
    near('#36 one line per page', pm['page']['geo'], 0.973)
    ok('#36 10 of 10 lower', pm['page']['n_faster_d'] == 10)
    rng('#36 all five', (pm['all5-every']['min'], pm['all5-every']['max']), 0.976, 0.980)
    t = D.ocm_tlb['every line']
    ok('#36 L1 TLB refills per pass', (round(t['B']['min']), round(t['B']['max']),
                                       round(t['D']['min']), round(t['D']['max'])) ==
       (163, 599, 12, 15), t)
    near('O4 TLB means, every line', t['B']['mean'], 287.0, 0.06)
    near('O4 TLB means, one line per page', D.ocm_tlb['one line per page']['B']['mean'], 42.3, 0.06)

    # ---- #37, #38: OCM bandwidth
    ob = D.ocm_bw_summary
    ok('ocm bw rows', len(D.ocm_bw) == 8)
    rng('#37 read per region', ob['region'], 19.883, 20.143)
    near('#37 regions apart %', ob['region_apart_pct'], 1.29, 0.006)
    ok('#37 all five, write, four cores', [D.ocm_bw[i]['best'] for i in (5, 6, 7)] ==
       [19.822, 20.326, 80.314])
    near('#37 four cores over the sum', ob['four_core_ratio_sum'], 1.002)
    near('#38 read ratio', ob['read_ratio'], 0.791)
    near('#38 write ratio', ob['write_ratio'], 0.636)

    # ---- #39 to #43: mesh counters (D3, D5, C12)
    ms = D.mesh_summary
    ok('mesh labels', (ms['n_labels'], ms['n_core_labels'], ms['n_rows'], ms['multiplexed']) ==
       (66, 51, 587, 0) and len(D.mesh_cmd) == 51 and len(D.mesh_ctrl) == 5)
    ok('#39 control', ms['ctrl'] == (7348, 10118), ms['ctrl'])
    ok('#40 own node highest in 25 of 25', (ms['own_highest'], ms['n_one_region']) == (25, 25))
    rng('#40 D5 own over the mean of the others, latency', ms['ratio_lat'], 4.57, 6.13, 0.006)
    rng('#40 D5 own over the mean of the others, read', ms['ratio_bw'], 7.59, 8.14, 0.006)
    rng('#41 D3 share per node, 10 commands', ms['share'], 19.81, 20.10, 0.006)
    rng('D3 share per node, 7 bandwidth commands', ms['share_bw'], 19.98, 20.04, 0.006)
    ok('#42 sent on to memory', (ms['n_ocm'], ms['ocm_mc'], ms['ctrl_mc'], ms['dram_mc']) ==
       (35, (4717, 13105), (6732, 11014), (123161, 5608913)),
       (ms['n_ocm'], ms['ocm_mc'], ms['ctrl_mc'], ms['dram_mc']))
    ok('mesh_share rows', len(D.mesh_share) == 10)
    near('C12 sent on to memory per line and pass est., read', ms['mc_est_read'], 1.02, 0.006)
    rng('C12 sent on to memory per line and pass est., writes', ms['mc_est_writes'], 1.02, 1.07,
        0.006)
    ok('helper cost', ms['helper_cost_ns'] == 579353 and ms['child_diff_ns'] == -29839)
    I = D.integrity['F1']
    ok('#43 integrity of boot F1', (D.boot['F1']['n_cmd'], D.boot['F1']['n_core'],
                                    D.boot['F1']['n_cme'], D.boot['F1']['n_failed'],
                                    D.boot['F1']['sha_ok'], D.boot['F1']['sha_total'],
                                    I['cov_rows'], I['cmn_multiplexed']) ==
       (137, 67, 70, 0, 88, 88, 247, 0))

    # ---- #44: open 8.1
    os_ = D.open_l3_summary
    ok('open_l3 rows', len(D.open_l3) == 14)
    for got, w in zip(os_['read'], (1.561, 2.229, 2.587, 2.690, 2.679)):
        near('#44 one-core read F1 over R3', got, w)
    near('#44 write', os_['write_32m'], 1.000)
    rng('#44 four readers', os_['four_readers'], 2.888, 2.895)
    rng('#44 eight readers', os_['eight_readers'], 1.605, 1.614)
    rng('#44 OCM read', os_['ocm_regions'], 1.206, 1.358)
    near('#44 mesh requests of the 2 MiB read', os_['mesh_ratio'], 0.975)
    ok('#44 mesh sums', (os_['mesh_f1'], os_['mesh_r3']) == (427991, 438961))
    ec = {r['id']: r for r in D.open_ec}
    ok('open_ec rows', len(D.open_ec) == 3)
    near('TP2 plain 32 MiB read, E over C', ec['read-%d' % (32 * MIB)]['l3_gain'], 2.669)
    near('O2 address order, C over E', ec['seq-8m']['l3_gain'], 2.78, 0.006)

    # ---- headline, scope, grid
    ok('H1 headline', [h['ns'] for h in D.headline] ==
       [2.002, 6.014, 10.986, 23.714, 25.536, 52.658])
    ok('H1 cycles', [h['cycles'] for h in D.headline] == [4.01, 12.03, 21.98, 47.44, 51.10, 105.32])
    nm = {r['family']: r['cells'] for r in D.not_measured['rows']}
    ok('P2 grid states', [s['boots'] for s in D.not_measured['states']] ==
       [['F1', 'E'], [], ['C', 'R3'], ['B', 'D']])
    ok('P2 no core row with the L3 on and the prefetchers off',
       all(c[1] is None for c in nm.values()))
    ok('P2 cells', nm['L3 hit set'] == [['E'], None, ['C'], ['B', 'D']]
       and nm['one-core bandwidth sweep'] == [['F1'], None, ['R3'], None]
       and nm['L1 forms'] == [['E'], None, ['C'], None])
    ok('boot F2 has no core CSV file', D.not_measured['f2_non_cme_files'] ==
       ['all.txt', 'cmn-counts.csv', 'log.txt'])
    ok('every table name is an attribute', all(hasattr(D, k) for k in TABLES))
    for name in ('lat_sweep', 'lat_hit', 'l3_est', 'lat_seq', 'lat_pfoff', 'repeat',
                 'spread_groups', 'bw_1core', 'bw_fit', 'bw_l1', 'bw_var', 'stream_chain',
                 'mc_rows', 'mc_second_core', 'mc_writers', 'ocm_all5', 'ocm_cells', 'ocm_pagemap',
                 'ocm_bw', 'mesh_cmd', 'mesh_share', 'open_l3', 'open_ec', 'headline'):
        ok('rows of %s carry boot, file, line, best_line' % name,
           all(all(k in r for k in ('boot', 'file', 'line', 'best_line'))
               for r in getattr(D, name)))
    print('selftest OK: %d checks' % n[0])
    return n[0]


if __name__ == '__main__':
    import sys
    selftest(verbose='-v' in sys.argv[1:])
