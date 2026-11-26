#!/usr/bin/env python3
"""Own parser of the raw result files (independent of build_facts.py and stat_*.py)."""
import re
import statistics

R = '/home/jhan/workspace/titan/cache-perf/crb/results'


def bwx(path):
    """Intervals of a bwx / bwx11 / bwx12 csv file.

    Returns a list of dicts in file order. A file can hold several processes (runner bwx: header lines
    that start with '-- '). For rx.sh files there is one process per file.
    total = sum over T rows of bytes / elapsed_s / 1e9.
    """
    out = []
    proc = None
    hdr = {}
    cur = None
    with open(path) as fh:
        for ln, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if line.startswith('-- '):
                proc = line
                hdr = {}
                continue
            if line.startswith('#'):
                for key in ('seq', 'rounds', 'stop', 'start', 'count', 'min_ms'):
                    m = re.search(r'\b%s=(\S+)' % key, line)
                    if m:
                        hdr[key] = m.group(1).rstrip(';')
                continue
            p = line.split(',')
            if p[0] == 'I':
                cur = dict(file=path, proc=proc, hdr=dict(hdr), line=ln, round=int(p[1]), pos=int(p[2]), kernel=p[3],
                           I_agg=float(p[8]), total=0.0, m0=0.0, m1=0.0, n=0, n0=0, n1=0, t0=None, t1=None, flags=0)
                out.append(cur)
            elif p[0] == 'T':
                if cur is None or (int(p[1]), int(p[2]), p[3]) != (cur['round'], cur['pos'], cur['kernel']):
                    raise SystemExit('T row without its I row: %s line %d' % (path, ln))
                r = float(p[6]) / float(p[7]) / 1e9
                cpu = int(p[5])
                cur['total'] += r
                cur['n'] += 1
                if cpu < 64:
                    cur['m0'] += r
                    cur['n0'] += 1
                else:
                    cur['m1'] += r
                    cur['n1'] += 1
                ts, te = float(p[9]), float(p[10])
                cur['t0'] = ts if cur['t0'] is None else min(cur['t0'], ts)
                cur['t1'] = te if cur['t1'] is None else max(cur['t1'], te)
                if p[-1] != '-':
                    cur['flags'] += 1
    return out


def parta(path):
    """Processes of a bandwidth.c csv file: list of dict(header, line, binary, kernel, round, load, utc, iv=[(line, rate, passes, avg)])."""
    out = []
    cur = None
    with open(path) as fh:
        for ln, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if line.startswith('-- '):
                cur = dict(header=line, line=ln, iv=[])
                m = re.search(r'binary (\S+)', line)
                cur['binary'] = m.group(1)
                m = re.search(r'kernel (\S+)', line)
                cur['kernel'] = m.group(1) if m else None
                m = re.search(r' round (\S+)', line)
                cur['round'] = m.group(1) if m else None
                m = re.search(r' tag (\S+)', line)
                cur['tag'] = m.group(1) if m else None
                m = re.search(r' load(?:avg)? (\S+)', line)
                cur['load'] = float(m.group(1)) if m else None
                m = re.search(r' utc (\S+)', line)
                cur['utc'] = m.group(1) if m else None
                out.append(cur)
                continue
            if line.startswith('#') or line.startswith('kernel,') or line.startswith('thread,'):
                continue
            p = line.split(',')
            if len(p) >= 10 and p[3].isdigit():
                cur['iv'].append(dict(line=ln, kernel=p[0], rate=float(p[6]), passes=int(p[4]) // int(p[2]),
                                      avg=float(p[9])))
    return out


def med(v):
    return statistics.median(v)


def rng(v):
    return min(v), max(v)
