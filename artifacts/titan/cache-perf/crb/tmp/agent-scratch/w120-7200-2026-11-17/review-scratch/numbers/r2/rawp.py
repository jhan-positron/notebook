#!/usr/bin/env python3
"""Round 2 reviewer parser (lens NUMBERS). Reads only raw files under R. No facts.json, no author code."""
import os, re, statistics

R = '/home/jhan/workspace/titan/cache-perf/crb/results'
med = statistics.median


def bw_procs(path):
    """bandwidth.c csv. One process = one '-- ' header line. Returns list of dicts."""
    out, cur = [], None
    with open(path) as fh:
        for ln, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if line.startswith('-- '):
                cur = {'hdr': line, 'hline': ln, 'iv': []}
                m = re.match(r'-- binary (\S+) kernel (\S+) threads (\S+) cpus (\S+) bytes (\S+) round (\S+) load (\S+) utc (\S+)$', line)
                if m:
                    cur.update(binary=m.group(1), kernel=m.group(2), round=int(m.group(6)), load=float(m.group(7)), utc=m.group(8), tag=None, minms=500)
                else:
                    m = re.match(r'-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) logins (\S+) utc (\S+) args (.*)$', line)
                    assert m, line
                    args = m.group(11)
                    cur.update(binary=m.group(3), tag=m.group(2), load=float(m.group(5)), utc=m.group(10),
                               kernel=re.search(r'--kernel (\S+)', args).group(1),
                               minms=int(re.search(r'--min-ms (\S+)', args).group(1)), args=args)
                    mr = re.search(r'-r?([0-9]+)$', m.group(2))
                    cur['round'] = int(mr.group(1)) if mr else None
                out.append(cur)
                continue
            p = line.split(',')
            if len(p) == 10 and p[3].isdigit() and p[0] != 'kernel':
                assert cur is not None
                cur['iv'].append({'v': float(p[6]), 'line': ln, 'kernel': p[0], 'rep': int(p[3]),
                                  'bytes': int(p[4]), 'bpt': int(p[2]), 'el': float(p[5]),
                                  'passes': int(p[4]) / int(p[2])})
    return out


def bwx_ivs(path):
    """bwx csv. Returns list of intervals in file order. total = sum over T rows of bytes/elapsed_s/1e9."""
    d, order = {}, []
    with open(path) as fh:
        for ln, line in enumerate(fh, 1):
            if line.startswith('#'):
                continue
            p = line.rstrip('\n').split(',')
            if p[0] not in ('I', 'T'):
                continue
            key = (int(p[1]), int(p[2]), p[3])
            if key not in d:
                d[key] = {'round': key[0], 'pos': key[1], 'kernel': key[2], 'total': 0.0, 'n': 0, 'cpus': [],
                          'h0': 0.0, 'h1': 0.0, 'ts': [], 'te': [], 'Tlines': [], 'file': path}
                order.append(key)
            e = d[key]
            if p[0] == 'I':
                e['Iline'] = ln
                e['Iagg'] = float(p[8])
                e['Ithreads'] = int(p[5])
            else:
                r = float(p[6]) / float(p[7]) / 1e9
                cpu = int(p[5])
                e['total'] += r
                e['n'] += 1
                e['cpus'].append(cpu)
                e['h0' if cpu < 64 else 'h1'] += r
                e['ts'].append(float(p[9]))
                e['te'].append(float(p[10]))
                e['Tlines'].append(ln)
    out = [d[k] for k in order]
    for i, e in enumerate(out):
        e['prev'] = out[i - 1]['kernel'] if i else None
        e['ok'] = (e['n'] == 120 and len(set(e['cpus'])) == 120 and max(e['cpus']) <= 119
                   and sum(1 for c in e['cpus'] if c < 64) == 64)
    return out


def launches(folder):
    """launches.txt of a bwx folder: list of (line, text)."""
    return [(i, l.rstrip('\n')) for i, l in enumerate(open(os.path.join(R, folder, 'launches.txt')), 1)]


BWX = {
    'T72L1': 'w120-T72L1-20261117T221329Z/a6456.csv',
    'T72L2': 'w120-T72L2-20261117T221638Z/a6456.csv',
    'T72L3': 'w120-T72L3-20261117T221947Z/a6456.csv',
    'T72C1': 'w120-T72C1-20261117T221436Z/cfwd.csv',
    'T72C2': 'w120-T72C2-20261117T221745Z/crev.csv',
    'T72C3': 'w120-T72C3-20261117T222054Z/cfwd.csv',
    'T72C4': 'w120-T72C4-20261117T222136Z/crev.csv',
    'T72I1': 'w120-T72I1-20261117T222700Z/a6456.csv',
    'T72I2': 'w120-T72I2-20261117T223227Z/a6456.csv',
    'F72d12': 'w120-w120-F72d12-20261117T200231Z/a6456.csv',
    'L-1': 'w120-R8-20261117T020549Z/a6456.csv',
    'L-2a': 'w120-R1-20261115T185140Z/p1nop.csv',
    'L-2b': 'w120-R1-20261115T185140Z/p2add.csv',
    'L-3': 'w120-R5-20261115T203152Z/thp.csv',
    'L-4a': 'w120-R6-20261115T203438Z/st1.csv',
    'L-4b': 'w120-R6-20261115T203438Z/st2.csv',
    'L-4c': 'w120-R6-20261115T203438Z/st3.csv',
}
PARTA = {1: 'k120-T72A1-20261117T221209Z', 2: 'k120-T72A2-20261117T221518Z', 3: 'k120-T72A3-20261117T221827Z'}


def load_all():
    D = {k: bwx_ivs(os.path.join(R, v)) for k, v in BWX.items()}
    A = {}
    for s, d in PARTA.items():
        for p in bw_procs(f'{R}/{d}/threads120.csv'):
            if p['kernel'] == 'read':
                assert (s, p['round'], p['binary']) not in A
                A[(s, p['round'], p['binary'])] = p
    B = {}
    for p in bw_procs(f'{R}/kernels-20261113T181222Z/threads120.csv'):
        if p['kernel'] == 'read':
            B[('A-1', p['round'], p['binary'])] = p
    for p in bw_procs(f'{R}/partA-20261113T205055Z/A1.csv'):
        if p['kernel'] == 'read':
            B[('A-2', p['round'], p['binary'])] = p
    for p in bw_procs(f'{R}/partA-20261113T205055Z/A3.csv'):
        if p['tag'].startswith('onebuf-ms500-'):
            B[('A-3', p['round'], p['binary'])] = p
    return D, A, B
